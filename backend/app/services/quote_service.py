"""
报价单管理服务
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.quote import QuoteSheet, QuoteItem, QuoteVersion
from app.models.product import Product, ProductPrice, ProductSpec
from app.schemas.quote import (
    QuoteCreateRequest, QuoteUpdateRequest,
    QuoteItemCreateRequest, QuoteItemUpdateRequest,
    QuoteDetailResponse, QuoteListResponse, QuoteItemResponse,
    PaginatedQuoteListResponse, QuoteItemBatchResult,
    QuoteVersionResponse
)
from app.services.pricing_engine import pricing_engine
from app.services.product_filter_service import ProductFilterService
from app.core.redis_client import get_redis


class QuoteService:
    """报价单管理服务"""
    
    def __init__(self):
        self.product_filter_service = ProductFilterService()
    
    async def generate_quote_no(self, db: AsyncSession) -> str:
        """
        生成唯一报价单编号
        格式：QT{YYYYMMDD}{4位序号}
        """
        today = datetime.now().strftime("%Y%m%d")
        redis = await get_redis()
        
        # 使用Redis生成序号
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Redis自增
                key = f"quote_no:{today}"
                seq = await redis.incr(key)
                
                # 设置过期时间（2天后过期）
                await redis.expire(key, 172800)
                
                # 格式化报价单编号
                quote_no = f"QT{today}{seq:04d}"
                
                # 检查唯一性
                check_query = select(QuoteSheet).where(QuoteSheet.quote_no == quote_no)
                result = await db.execute(check_query)
                existing = result.scalars().first()
                
                if not existing:
                    return quote_no
                    
                logger.warning(f"报价单编号 {quote_no} 已存在，重试...")
            except Exception as e:
                logger.error(f"生成报价单编号失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    raise
        
        raise Exception("生成报价单编号失败：达到最大重试次数")
    
    async def create_quote(
        self,
        db: AsyncSession,
        data: QuoteCreateRequest
    ) -> QuoteDetailResponse:
        """创建报价单草稿"""
        try:
            # 生成报价单编号
            quote_no = await self.generate_quote_no(db)
            
            # 计算有效期
            valid_until = datetime.now() + timedelta(days=data.valid_days)
            
            # 创建报价单
            quote = QuoteSheet(
                quote_no=quote_no,
                customer_name=data.customer_name,
                project_name=data.project_name,
                created_by=data.created_by,
                sales_name=data.sales_name,
                customer_contact=data.customer_contact,
                customer_email=data.customer_email,
                remarks=data.remarks,
                status="draft",
                global_discount_rate=Decimal("1.0000"),
                total_amount=Decimal("0"),
                total_original_amount=Decimal("0"),
                valid_until=valid_until
            )
            
            db.add(quote)
            await db.flush()
            
            # 创建初始版本快照
            await self._create_version_snapshot(db, quote.quote_id, "create")
            
            await db.commit()
            await db.refresh(quote)
            
            # 返回详情
            return await self.get_quote_detail(db, quote.quote_id)
        except Exception as e:
            await db.rollback()
            logger.error(f"创建报价单失败: {e}")
            raise
    
    async def get_quote_detail(
        self,
        db: AsyncSession,
        quote_id: UUID
    ) -> QuoteDetailResponse:
        """获取报价单完整详情"""
        try:
            # 查询报价单
            quote_query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
            quote_result = await db.execute(quote_query)
            quote = quote_result.scalars().first()
            
            if not quote:
                raise ValueError(f"报价单不存在: {quote_id}")
            
            # 查询报价项
            items_query = select(QuoteItem).where(
                QuoteItem.quote_id == quote_id
            ).order_by(QuoteItem.sort_order)
            items_result = await db.execute(items_query)
            items = items_result.scalars().all()
            
            # 转换为响应格式
            item_responses = [
                QuoteItemResponse(
                    item_id=item.item_id,
                    product_code=item.product_code,
                    product_name=item.product_name,
                    region=item.region,
                    region_name=item.region_name,
                    modality=item.modality,
                    capability=item.capability,
                    model_type=item.model_type,
                    context_spec=item.context_spec,
                    input_tokens=item.input_tokens,
                    output_tokens=item.output_tokens,
                    inference_mode=item.inference_mode,
                    quantity=item.quantity,
                    duration_months=item.duration_months,
                    original_price=item.original_price,
                    discount_rate=item.discount_rate,
                    final_price=item.final_price,
                    billing_unit=item.billing_unit,
                    sort_order=item.sort_order
                )
                for item in items
            ]
            
            # 获取最新版本号
            version_query = select(func.max(QuoteVersion.version_number)).where(
                QuoteVersion.quote_id == quote_id
            )
            version_result = await db.execute(version_query)
            version = version_result.scalar() or 1
            
            return QuoteDetailResponse(
                quote_id=quote.quote_id,
                quote_no=quote.quote_no,
                customer_name=quote.customer_name,
                project_name=quote.project_name,
                created_by=quote.created_by,
                sales_name=quote.sales_name,
                customer_contact=quote.customer_contact,
                customer_email=quote.customer_email,
                status=quote.status,
                remarks=quote.remarks,
                terms=quote.terms,
                global_discount_rate=quote.global_discount_rate,
                global_discount_remark=quote.global_discount_remark,
                total_original_amount=quote.total_original_amount,
                total_final_amount=quote.total_amount,
                currency=quote.currency,
                valid_until=quote.valid_until,
                created_at=quote.created_at,
                updated_at=quote.updated_at,
                items=item_responses,
                version=version
            )
        except Exception as e:
            logger.error(f"获取报价单详情失败: {e}")
            raise
    
    async def update_quote(
        self,
        db: AsyncSession,
        quote_id: UUID,
        data: QuoteUpdateRequest
    ) -> QuoteDetailResponse:
        """更新报价单基本信息"""
        try:
            # 查询报价单
            quote_query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
            quote_result = await db.execute(quote_query)
            quote = quote_result.scalars().first()
            
            if not quote:
                raise ValueError(f"报价单不存在: {quote_id}")
            
            # 检查状态
            if quote.status != "draft" and data.status is None:
                raise ValueError("只有草稿状态的报价单可以修改基本信息")
            
            # 更新字段
            update_data = data.model_dump(exclude_unset=True)
            
            # 状态流转校验
            if "status" in update_data:
                new_status = update_data["status"]
                if quote.status == "draft":
                    if new_status not in ["confirmed", "cancelled"]:
                        raise ValueError(f"草稿状态不能转换为: {new_status}")
                else:
                    raise ValueError(f"当前状态 {quote.status} 不允许转换")
            
            for key, value in update_data.items():
                setattr(quote, key, value)
            
            # 创建版本快照
            await self._create_version_snapshot(db, quote_id, "update")
            
            await db.commit()
            
            return await self.get_quote_detail(db, quote_id)
        except Exception as e:
            await db.rollback()
            logger.error(f"更新报价单失败: {e}")
            raise
    
    async def delete_quote(
        self,
        db: AsyncSession,
        quote_id: UUID
    ) -> bool:
        """删除报价单（软删除）"""
        try:
            quote_query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
            quote_result = await db.execute(quote_query)
            quote = quote_result.scalars().first()
            
            if not quote:
                raise ValueError(f"报价单不存在: {quote_id}")
            
            # 软删除：设置状态为deleted
            quote.status = "deleted"
            
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"删除报价单失败: {e}")
            raise
    
    async def add_item(
        self,
        db: AsyncSession,
        quote_id: UUID,
        item_data: QuoteItemCreateRequest
    ) -> QuoteItemResponse:
        """添加单个商品到报价单"""
        try:
            # 查询报价单
            quote_query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
            quote_result = await db.execute(quote_query)
            quote = quote_result.scalars().first()
            
            if not quote:
                raise ValueError(f"报价单不存在: {quote_id}")
            
            if quote.status != "draft":
                raise ValueError("只有草稿状态的报价单可以添加商品")
            
            # 查询商品信息
            product_query = select(Product).where(
                Product.product_code == item_data.product_code
            )
            product_result = await db.execute(product_query)
            product = product_result.scalars().first()
            
            if not product:
                raise ValueError(f"商品不存在: {item_data.product_code}")
            
            # 查询价格信息
            price_query = select(ProductPrice).where(
                and_(
                    ProductPrice.product_code == item_data.product_code,
                    ProductPrice.region == item_data.region
                )
            )
            price_result = await db.execute(price_query)
            price = price_result.scalars().first()
            
            if not price:
                raise ValueError(f"商品 {item_data.product_code} 在地域 {item_data.region} 的价格信息不存在")
            
            # 计算价格
            price_result = await self._calculate_item_price(
                product=product,
                price=price,
                item_data=item_data,
                global_discount_rate=quote.global_discount_rate
            )
            
            # 获取当前最大排序号
            max_sort_query = select(func.max(QuoteItem.sort_order)).where(
                QuoteItem.quote_id == quote_id
            )
            max_sort_result = await db.execute(max_sort_query)
            max_sort = max_sort_result.scalar() or 0
            
            # 创建报价项
            item = QuoteItem(
                quote_id=quote_id,
                product_code=item_data.product_code,
                product_name=product.product_name,
                region=item_data.region,
                region_name=self.product_filter_service.REGION_NAMES.get(item_data.region, item_data.region),
                modality=self.product_filter_service.map_category_to_modality(product.category),
                capability=self.product_filter_service.map_category_to_capability(product.category),
                model_type=self.product_filter_service.map_category_to_model_type(product.category),
                input_tokens=item_data.input_tokens,
                output_tokens=item_data.output_tokens,
                inference_mode=item_data.inference_mode,
                quantity=item_data.quantity,
                duration_months=item_data.duration_months,
                original_price=price_result["original_price"],
                discount_rate=Decimal("1.0000"),
                final_price=price_result["final_price"],
                billing_unit=price.unit or "千Token",
                sort_order=max_sort + 1
            )
            
            db.add(item)
            await db.flush()
            
            # 重新计算总金额
            await self._recalculate_total(db, quote_id)
            
            # 创建版本快照
            await self._create_version_snapshot(db, quote_id, "add_item")
            
            await db.commit()
            await db.refresh(item)
            
            return QuoteItemResponse(
                item_id=item.item_id,
                product_code=item.product_code,
                product_name=item.product_name,
                region=item.region,
                region_name=item.region_name,
                modality=item.modality,
                capability=item.capability,
                model_type=item.model_type,
                context_spec=item.context_spec,
                input_tokens=item.input_tokens,
                output_tokens=item.output_tokens,
                inference_mode=item.inference_mode,
                quantity=item.quantity,
                duration_months=item.duration_months,
                original_price=item.original_price,
                discount_rate=item.discount_rate,
                final_price=item.final_price,
                billing_unit=item.billing_unit,
                sort_order=item.sort_order
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"添加商品失败: {e}")
            raise
    
    async def _calculate_item_price(
        self,
        product: Product,
        price: ProductPrice,
        item_data: QuoteItemCreateRequest,
        global_discount_rate: Decimal
    ) -> Dict[str, Decimal]:
        """计算报价项价格"""
        # 构建计价上下文
        context = {
            "product_type": "llm" if "大模型" in product.category else "standard",
            "quantity": item_data.quantity,
            "duration_months": item_data.duration_months,
        }
        
        # 获取基础价格
        base_price = Decimal(str(price.unit_price))
        
        # 如果是大模型，计算token成本
        if context["product_type"] == "llm" and item_data.input_tokens and item_data.output_tokens:
            pricing_vars = price.pricing_variables or {}
            input_price = Decimal(str(pricing_vars.get("input_price", 0)))
            output_price = Decimal(str(pricing_vars.get("output_price", 0)))
            
            # 基础费用 = (input_price × input_tokens + output_price × output_tokens) / 1000
            base_cost = (
                input_price * Decimal(str(item_data.input_tokens)) +
                output_price * Decimal(str(item_data.output_tokens))
            ) / Decimal("1000")
            
            # 如果启用思考模式
            if item_data.inference_mode == "thinking":
                thinking_multiplier = Decimal(str(pricing_vars.get("thinking_multiplier", 1.5)))
                base_cost = base_cost * thinking_multiplier
            
            # 原价 = 基础费用 × 数量 × 时长
            original_price = base_cost * Decimal(str(item_data.quantity)) * Decimal(str(item_data.duration_months))
        else:
            # 传统产品计价
            original_price = base_price * Decimal(str(item_data.quantity)) * Decimal(str(item_data.duration_months))
        
        # 应用全局折扣
        final_price = original_price * global_discount_rate
        
        return {
            "original_price": original_price,
            "final_price": final_price
        }
    
    async def _recalculate_total(
        self,
        db: AsyncSession,
        quote_id: UUID
    ) -> Decimal:
        """重新计算报价单总金额"""
        # 查询所有报价项
        items_query = select(QuoteItem).where(QuoteItem.quote_id == quote_id)
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()
        
        # 汇总
        total_original = sum(item.original_price for item in items)
        total_final = sum(item.final_price for item in items)
        
        # 更新报价单
        quote_query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
        quote_result = await db.execute(quote_query)
        quote = quote_result.scalars().first()
        
        if quote:
            quote.total_original_amount = Decimal(str(total_original))
            quote.total_amount = Decimal(str(total_final))
        
        return Decimal(str(total_final))
    
    async def _create_version_snapshot(
        self,
        db: AsyncSession,
        quote_id: UUID,
        change_type: str
    ):
        """创建版本快照"""
        # 获取当前最大版本号
        version_query = select(func.max(QuoteVersion.version_number)).where(
            QuoteVersion.quote_id == quote_id
        )
        version_result = await db.execute(version_query)
        max_version = version_result.scalar() or 0
        
        # 查询报价单和报价项
        quote_query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
        quote_result = await db.execute(quote_query)
        quote = quote_result.scalars().first()
        
        items_query = select(QuoteItem).where(QuoteItem.quote_id == quote_id)
        items_result = await db.execute(items_query)
        items = items_result.scalars().all()
        
        # 序列化快照数据
        snapshot_data = {
            "quote": {
                "quote_no": quote.quote_no,
                "customer_name": quote.customer_name,
                "project_name": quote.project_name,
                "status": quote.status,
                "total_amount": str(quote.total_amount),
                "global_discount_rate": str(quote.global_discount_rate),
            },
            "items": [
                {
                    "product_code": item.product_code,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "original_price": str(item.original_price),
                    "final_price": str(item.final_price),
                }
                for item in items
            ]
        }
        
        # 生成变更摘要
        changes_summary = self._generate_changes_summary(change_type, len(items))
        
        # 创建版本记录
        version = QuoteVersion(
            quote_id=quote_id,
            version_number=max_version + 1,
            change_type=change_type,
            changes_summary=changes_summary,
            snapshot_data=snapshot_data
        )
        
        db.add(version)
    
    def _generate_changes_summary(self, change_type: str, items_count: int) -> str:
        """生成变更摘要"""
        summaries = {
            "create": "创建报价单",
            "update": "更新报价单信息",
            "add_item": f"添加商品，当前共{items_count}个商品",
            "update_item": "更新商品信息",
            "delete_item": f"删除商品，当前剩余{items_count}个商品",
            "apply_discount": "应用批量折扣",
            "recalculate": "重新计算价格",
            "clone": "克隆报价单"
        }
        return summaries.get(change_type, "未知变更")
    
    async def update_item(
        self,
        db: AsyncSession,
        quote_id: UUID,
        item_id: UUID,
        item_data: QuoteItemUpdateRequest
    ) -> QuoteItemResponse:
        """更新报价项"""
        try:
            # 查询报价单
            quote_query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
            quote_result = await db.execute(quote_query)
            quote = quote_result.scalars().first()
            
            if not quote:
                raise ValueError(f"报价单不存在: {quote_id}")
            
            if quote.status != "draft":
                raise ValueError("只有草稿状态的报价单可以修改商品")
            
            # 查询报价项
            item_query = select(QuoteItem).where(
                and_(
                    QuoteItem.item_id == item_id,
                    QuoteItem.quote_id == quote_id
                )
            )
            item_result = await db.execute(item_query)
            item = item_result.scalars().first()
            
            if not item:
                raise ValueError(f"报价项不存在: {item_id}")
            
            # 更新字段
            update_data = item_data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(item, key, value)
            
            # 如果更新了影响价格的字段，重新计算价格
            price_fields = {'input_tokens', 'output_tokens', 'quantity', 'duration_months', 'inference_mode'}
            if price_fields & set(update_data.keys()):
                # 查询价格信息
                price_query = select(ProductPrice).where(
                    and_(
                        ProductPrice.product_code == item.product_code,
                        ProductPrice.region == item.region
                    )
                )
                price_result = await db.execute(price_query)
                price = price_result.scalars().first()
                
                product_query = select(Product).where(Product.product_code == item.product_code)
                product_result = await db.execute(product_query)
                product = product_result.scalars().first()
                
                if price and product:
                    # 构造更新后的数据用于计算
                    calc_data = QuoteItemCreateRequest(
                        product_code=item.product_code,
                        region=item.region,
                        input_tokens=item.input_tokens,
                        output_tokens=item.output_tokens,
                        inference_mode=item.inference_mode,
                        quantity=item.quantity,
                        duration_months=item.duration_months
                    )
                    price_result = await self._calculate_item_price(
                        product=product,
                        price=price,
                        item_data=calc_data,
                        global_discount_rate=quote.global_discount_rate
                    )
                    item.original_price = price_result["original_price"]
                    item.final_price = price_result["final_price"]
            
            # 重新计算总金额
            await self._recalculate_total(db, quote_id)
            
            # 创建版本快照
            await self._create_version_snapshot(db, quote_id, "update_item")
            
            await db.commit()
            await db.refresh(item)
            
            return QuoteItemResponse(
                item_id=item.item_id,
                product_code=item.product_code,
                product_name=item.product_name,
                region=item.region,
                region_name=item.region_name,
                modality=item.modality,
                capability=item.capability,
                model_type=item.model_type,
                context_spec=item.context_spec,
                input_tokens=item.input_tokens,
                output_tokens=item.output_tokens,
                inference_mode=item.inference_mode,
                quantity=item.quantity,
                duration_months=item.duration_months,
                original_price=item.original_price,
                discount_rate=item.discount_rate,
                final_price=item.final_price,
                billing_unit=item.billing_unit,
                sort_order=item.sort_order
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"更新报价项失败: {e}")
            raise
    
    async def delete_item(
        self,
        db: AsyncSession,
        quote_id: UUID,
        item_id: UUID
    ) -> bool:
        """删除报价项"""
        try:
            # 查询报价单
            quote_query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
            quote_result = await db.execute(quote_query)
            quote = quote_result.scalars().first()
            
            if not quote:
                raise ValueError(f"报价单不存在: {quote_id}")
            
            if quote.status != "draft":
                raise ValueError("只有草稿状态的报价单可以删除商品")
            
            # 查询并删除报价项
            item_query = select(QuoteItem).where(
                and_(
                    QuoteItem.item_id == item_id,
                    QuoteItem.quote_id == quote_id
                )
            )
            item_result = await db.execute(item_query)
            item = item_result.scalars().first()
            
            if not item:
                raise ValueError(f"报价项不存在: {item_id}")
            
            await db.delete(item)
            
            # 重新计算总金额
            await self._recalculate_total(db, quote_id)
            
            # 创建版本快照
            await self._create_version_snapshot(db, quote_id, "delete_item")
            
            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"删除报价项失败: {e}")
            raise
    
    async def add_items_batch(
        self,
        db: AsyncSession,
        quote_id: UUID,
        items_data: List[QuoteItemCreateRequest]
    ) -> QuoteItemBatchResult:
        """批量添加商品到报价单"""
        success_items = []
        failed_items = []
        
        try:
            # 查询报价单
            quote_query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
            quote_result = await db.execute(quote_query)
            quote = quote_result.scalars().first()
            
            if not quote:
                raise ValueError(f"报价单不存在: {quote_id}")
            
            if quote.status != "draft":
                raise ValueError("只有草稿状态的报价单可以添加商品")
            
            # 获取当前最大排序号
            max_sort_query = select(func.max(QuoteItem.sort_order)).where(
                QuoteItem.quote_id == quote_id
            )
            max_sort_result = await db.execute(max_sort_query)
            current_sort = max_sort_result.scalar() or 0
            
            for item_data in items_data:
                try:
                    # 查询商品信息
                    product_query = select(Product).where(
                        Product.product_code == item_data.product_code
                    )
                    product_result = await db.execute(product_query)
                    product = product_result.scalars().first()
                    
                    if not product:
                        failed_items.append({
                            "product_code": item_data.product_code,
                            "error": f"商品不存在: {item_data.product_code}"
                        })
                        continue
                    
                    # 查询价格信息
                    price_query = select(ProductPrice).where(
                        and_(
                            ProductPrice.product_code == item_data.product_code,
                            ProductPrice.region == item_data.region
                        )
                    )
                    price_result = await db.execute(price_query)
                    price = price_result.scalars().first()
                    
                    if not price:
                        failed_items.append({
                            "product_code": item_data.product_code,
                            "error": f"价格信息不存在: {item_data.region}"
                        })
                        continue
                    
                    # 计算价格
                    price_calc = await self._calculate_item_price(
                        product=product,
                        price=price,
                        item_data=item_data,
                        global_discount_rate=quote.global_discount_rate
                    )
                    
                    current_sort += 1
                    
                    # 创建报价项
                    item = QuoteItem(
                        quote_id=quote_id,
                        product_code=item_data.product_code,
                        product_name=product.product_name,
                        region=item_data.region,
                        region_name=self.product_filter_service.REGION_NAMES.get(item_data.region, item_data.region),
                        modality=self.product_filter_service.map_category_to_modality(product.category),
                        capability=self.product_filter_service.map_category_to_capability(product.category),
                        model_type=self.product_filter_service.map_category_to_model_type(product.category),
                        input_tokens=item_data.input_tokens,
                        output_tokens=item_data.output_tokens,
                        inference_mode=item_data.inference_mode,
                        quantity=item_data.quantity,
                        duration_months=item_data.duration_months,
                        original_price=price_calc["original_price"],
                        discount_rate=Decimal("1.0000"),
                        final_price=price_calc["final_price"],
                        billing_unit=price.unit or "千Token",
                        sort_order=current_sort
                    )
                    
                    db.add(item)
                    await db.flush()
                    
                    success_items.append(QuoteItemResponse(
                        item_id=item.item_id,
                        product_code=item.product_code,
                        product_name=item.product_name,
                        region=item.region,
                        region_name=item.region_name,
                        modality=item.modality,
                        capability=item.capability,
                        model_type=item.model_type,
                        context_spec=item.context_spec,
                        input_tokens=item.input_tokens,
                        output_tokens=item.output_tokens,
                        inference_mode=item.inference_mode,
                        quantity=item.quantity,
                        duration_months=item.duration_months,
                        original_price=item.original_price,
                        discount_rate=item.discount_rate,
                        final_price=item.final_price,
                        billing_unit=item.billing_unit,
                        sort_order=item.sort_order
                    ))
                except Exception as e:
                    failed_items.append({
                        "product_code": item_data.product_code,
                        "error": str(e)
                    })
            
            # 重新计算总金额
            await self._recalculate_total(db, quote_id)
            
            # 创建版本快照
            await self._create_version_snapshot(db, quote_id, "add_item")
            
            await db.commit()
            
            return QuoteItemBatchResult(
                success_count=len(success_items),
                failed_count=len(failed_items),
                success_items=success_items,
                failed_items=failed_items
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"批量添加商品失败: {e}")
            raise
    
    async def list_quotes(
        self,
        db: AsyncSession,
        customer_name: Optional[str] = None,
        status: Optional[str] = None,
        created_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedQuoteListResponse:
        """分页查询报价单列表"""
        try:
            # 构建查询
            query = select(QuoteSheet).where(QuoteSheet.status != "deleted")
            
            if customer_name:
                query = query.where(QuoteSheet.customer_name.ilike(f"%{customer_name}%"))
            
            if status:
                query = query.where(QuoteSheet.status == status)
            
            if created_by:
                query = query.where(QuoteSheet.created_by == created_by)
            
            # 计算总数
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
            
            # 分页
            offset = (page - 1) * page_size
            query = query.order_by(desc(QuoteSheet.created_at)).offset(offset).limit(page_size)
            
            result = await db.execute(query)
            quotes = result.scalars().all()
            
            # 转换为响应格式
            data = [
                QuoteListResponse(
                    quote_id=q.quote_id,
                    quote_no=q.quote_no,
                    customer_name=q.customer_name,
                    project_name=q.project_name,
                    status=q.status,
                    total_amount=q.total_amount,
                    created_by=q.created_by,
                    created_at=q.created_at,
                    updated_at=q.updated_at
                )
                for q in quotes
            ]
            
            return PaginatedQuoteListResponse(
                total=total,
                page=page,
                page_size=page_size,
                data=data
            )
        except Exception as e:
            logger.error(f"查询报价单列表失败: {e}")
            raise
    
    async def clone_quote(
        self,
        db: AsyncSession,
        quote_id: UUID,
        new_customer_name: Optional[str] = None,
        new_project_name: Optional[str] = None
    ) -> QuoteDetailResponse:
        """克隆报价单"""
        try:
            # 查询原报价单
            quote_detail = await self.get_quote_detail(db, quote_id)
            
            # 生成新报价单编号
            new_quote_no = await self.generate_quote_no(db)
            
            # 创建新报价单
            new_quote = QuoteSheet(
                quote_no=new_quote_no,
                customer_name=new_customer_name or quote_detail.customer_name,
                project_name=new_project_name or quote_detail.project_name,
                created_by=quote_detail.created_by,
                sales_name=quote_detail.sales_name,
                customer_contact=quote_detail.customer_contact,
                customer_email=quote_detail.customer_email,
                remarks=f"克隆自 {quote_detail.quote_no}",
                status="draft",
                global_discount_rate=quote_detail.global_discount_rate,
                total_amount=Decimal("0"),
                total_original_amount=Decimal("0"),
                valid_until=datetime.now() + timedelta(days=30)
            )
            
            db.add(new_quote)
            await db.flush()
            
            # 克隆报价项
            for idx, item in enumerate(quote_detail.items, 1):
                new_item = QuoteItem(
                    quote_id=new_quote.quote_id,
                    product_code=item.product_code,
                    product_name=item.product_name,
                    region=item.region,
                    region_name=item.region_name,
                    modality=item.modality,
                    capability=item.capability,
                    model_type=item.model_type,
                    context_spec=item.context_spec,
                    input_tokens=item.input_tokens,
                    output_tokens=item.output_tokens,
                    inference_mode=item.inference_mode,
                    quantity=item.quantity,
                    duration_months=item.duration_months,
                    original_price=item.original_price,
                    discount_rate=item.discount_rate,
                    final_price=item.final_price,
                    billing_unit=item.billing_unit,
                    sort_order=idx
                )
                db.add(new_item)
            
            await db.flush()
            
            # 重新计算总金额
            await self._recalculate_total(db, new_quote.quote_id)
            
            # 创建版本快照
            await self._create_version_snapshot(db, new_quote.quote_id, "clone")
            
            await db.commit()
            
            return await self.get_quote_detail(db, new_quote.quote_id)
        except Exception as e:
            await db.rollback()
            logger.error(f"克隆报价单失败: {e}")
            raise
    
    async def get_quote_versions(
        self,
        db: AsyncSession,
        quote_id: UUID
    ) -> List[QuoteVersionResponse]:
        """获取报价单版本历史"""
        try:
            versions_query = select(QuoteVersion).where(
                QuoteVersion.quote_id == quote_id
            ).order_by(desc(QuoteVersion.version_number))
            
            versions_result = await db.execute(versions_query)
            versions = versions_result.scalars().all()
            
            return [
                QuoteVersionResponse(
                    version_id=v.version_id,
                    version_number=v.version_number,
                    change_type=v.change_type,
                    changes_summary=v.changes_summary,
                    created_at=v.created_at
                )
                for v in versions
            ]
        except Exception as e:
            logger.error(f"获取版本历史失败: {e}")
            raise
    
    async def apply_global_discount(
        self,
        db: AsyncSession,
        quote_id: UUID,
        discount_rate: Decimal,
        remark: Optional[str] = None
    ) -> QuoteDetailResponse:
        """应用全局折扣"""
        try:
            # 查询报价单
            quote_query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
            quote_result = await db.execute(quote_query)
            quote = quote_result.scalars().first()
            
            if not quote:
                raise ValueError(f"报价单不存在: {quote_id}")
            
            if quote.status != "draft":
                raise ValueError("只有草稿状态的报价单可以应用折扣")
            
            # 更新全局折扣率
            quote.global_discount_rate = discount_rate
            if remark:
                quote.global_discount_remark = remark
            
            # 重新计算所有报价项的价格
            items_query = select(QuoteItem).where(QuoteItem.quote_id == quote_id)
            items_result = await db.execute(items_query)
            items = items_result.scalars().all()
            
            for item in items:
                item.final_price = item.original_price * discount_rate
            
            # 重新计算总金额
            await self._recalculate_total(db, quote_id)
            
            # 创建版本快照
            await self._create_version_snapshot(db, quote_id, "apply_discount")
            
            await db.commit()
            
            return await self.get_quote_detail(db, quote_id)
        except Exception as e:
            await db.rollback()
            logger.error(f"应用折扣失败: {e}")
            raise


# 创建全局服务实例
quote_service = QuoteService()