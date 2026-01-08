"""
报价单CRUD操作
"""
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.quote import QuoteSheet, QuoteItem, QuoteDiscount, QuoteVersion


class QuoteCRUD:
    """报价单数据库操作"""
    
    @staticmethod
    async def create_quote(db: AsyncSession, quote: QuoteSheet) -> QuoteSheet:
        """创建报价单"""
        db.add(quote)
        await db.commit()
        await db.refresh(quote)
        
        # 创建初始版本
        version = QuoteVersion(
            quote_id=quote.quote_id,
            version_number=1,
            snapshot_data={"status": "initial"}
        )
        db.add(version)
        await db.commit()
        
        return quote
    
    @staticmethod
    async def get_quotes(
        db: AsyncSession,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[QuoteSheet]:
        """获取报价单列表"""
        query = select(QuoteSheet)
        
        if status:
            query = query.where(QuoteSheet.status == status)
        
        query = query.order_by(QuoteSheet.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_quote(db: AsyncSession, quote_id: str) -> Optional[QuoteSheet]:
        """获取报价单详情"""
        query = select(QuoteSheet).where(QuoteSheet.quote_id == quote_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_quote(
        db: AsyncSession,
        quote_id: str,
        update_data: dict
    ) -> Optional[QuoteSheet]:
        """更新报价单"""
        quote = await QuoteCRUD.get_quote(db, quote_id)
        if not quote:
            return None
        
        # 创建版本快照
        latest_version = await QuoteCRUD.get_latest_version(db, quote_id)
        new_version_number = (latest_version.version_number + 1) if latest_version else 1
        
        version = QuoteVersion(
            quote_id=quote_id,
            version_number=new_version_number,
            snapshot_data=update_data
        )
        db.add(version)
        
        # 更新报价单
        for key, value in update_data.items():
            if hasattr(quote, key):
                setattr(quote, key, value)
        
        await db.commit()
        await db.refresh(quote)
        return quote
    
    @staticmethod
    async def delete_quote(db: AsyncSession, quote_id: str) -> bool:
        """删除报价单"""
        quote = await QuoteCRUD.get_quote(db, quote_id)
        if not quote:
            return False
        
        await db.delete(quote)
        await db.commit()
        return True
    
    @staticmethod
    async def add_quote_item(db: AsyncSession, item: QuoteItem) -> QuoteItem:
        """添加报价项"""
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item
    
    @staticmethod
    async def get_quote_items(db: AsyncSession, quote_id: str) -> List[QuoteItem]:
        """获取报价项列表"""
        query = select(QuoteItem).where(QuoteItem.quote_id == quote_id)
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_latest_version(db: AsyncSession, quote_id: str) -> Optional[QuoteVersion]:
        """获取最新版本"""
        query = select(QuoteVersion).where(
            QuoteVersion.quote_id == quote_id
        ).order_by(QuoteVersion.version_number.desc()).limit(1)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def clone_quote(db: AsyncSession, source_quote_id: str) -> Optional[QuoteSheet]:
        """克隆报价单"""
        from datetime import datetime
        import uuid
        
        source_quote = await QuoteCRUD.get_quote(db, source_quote_id)
        if not source_quote:
            return None
        
        # 生成新的报价单编号
        new_quote_no = f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"
        
        # 创建新报价单
        new_quote = QuoteSheet(
            quote_no=new_quote_no,
            customer_name=source_quote.customer_name,
            project_name=f"{source_quote.project_name} (副本)",
            created_by=source_quote.created_by or "system",
            status="draft",
            currency=source_quote.currency,
            global_discount_rate=source_quote.global_discount_rate
        )
        new_quote = await QuoteCRUD.create_quote(db, new_quote)
        
        # 复制报价项
        items = await QuoteCRUD.get_quote_items(db, source_quote_id)
        for item in items:
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
                spec_config=item.spec_config,
                quantity=item.quantity,
                duration_months=item.duration_months,
                usage_estimation=item.usage_estimation,
                unit_price=item.unit_price,
                original_price=item.original_price,
                discount_rate=item.discount_rate,
                final_price=item.final_price,
                billing_unit=item.billing_unit,
                subtotal=item.subtotal,
                discount_info=item.discount_info,
                sort_order=item.sort_order
            )
            await QuoteCRUD.add_quote_item(db, new_item)
        
        return new_quote


# 创建全局实例
quote_crud = QuoteCRUD()
