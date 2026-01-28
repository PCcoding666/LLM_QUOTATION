"""
定价管理服务层
提供模型规格与价格的 CRUD 操作
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, update, delete
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.pricing import PricingModel, PricingModelPrice, PricingCategory, PricingSnapshot
from app.schemas.pricing_admin import (
    PricingModelCreateRequest,
    PricingModelUpdateRequest,
    PricingModelPriceCreateRequest,
    PricingModelPriceUpdateRequest,
    PricingModelAdminResponse,
    PricingModelPriceResponse,
    PaginatedPricingModelResponse,
    CategoryResponse,
)


class PricingAdminService:
    """定价数据管理服务（CRUD 操作）"""

    async def get_latest_snapshot_id(self, db: AsyncSession) -> Optional[int]:
        """获取最新快照ID"""
        try:
            query = select(PricingSnapshot.id).where(
                PricingSnapshot.is_latest == True
            ).order_by(PricingSnapshot.captured_at.desc()).limit(1)
            result = await db.execute(query)
            snapshot_id = result.scalar()
            return snapshot_id
        except Exception as e:
            logger.error(f"获取最新快照ID失败: {e}")
            return None

    async def list_models(
        self,
        db: AsyncSession,
        category_id: Optional[int] = None,
        mode: Optional[str] = None,
        token_tier: Optional[str] = None,
        supports_batch: Optional[bool] = None,
        supports_cache: Optional[bool] = None,
        keyword: Optional[str] = None,
        status: Optional[str] = "active",
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedPricingModelResponse:
        """列表查询模型（支持筛选/分页）"""
        try:
            # 构建基础查询
            query = select(PricingModel)

            # 应用筛选条件
            if status:
                query = query.where(PricingModel.status == status)
            if category_id:
                query = query.where(PricingModel.category_id == category_id)
            if mode:
                query = query.where(PricingModel.mode == mode)
            if token_tier:
                query = query.where(PricingModel.token_tier == token_tier)
            if supports_batch is not None:
                query = query.where(PricingModel.supports_batch == supports_batch)
            if supports_cache is not None:
                query = query.where(PricingModel.supports_cache == supports_cache)
            if keyword:
                query = query.where(
                    or_(
                        PricingModel.model_name.ilike(f"%{keyword}%"),
                        PricingModel.model_code.ilike(f"%{keyword}%"),
                        PricingModel.display_name.ilike(f"%{keyword}%")
                    )
                )

            # 计算总数
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0

            # 分页
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            query = query.order_by(PricingModel.id.desc())

            # 执行查询
            result = await db.execute(query)
            models = result.scalars().all()

            # 批量获取价格信息
            model_ids = [m.id for m in models]
            prices_map = {}
            if model_ids:
                prices_query = select(PricingModelPrice).where(
                    PricingModelPrice.model_id.in_(model_ids)
                )
                prices_result = await db.execute(prices_query)
                for price in prices_result.scalars().all():
                    if price.model_id not in prices_map:
                        prices_map[price.model_id] = []
                    prices_map[price.model_id].append(PricingModelPriceResponse(
                        id=price.id,
                        model_id=price.model_id,
                        dimension_code=price.dimension_code or "",
                        unit_price=float(price.unit_price) if price.unit_price else 0,
                        unit=price.unit or "",
                        currency=price.currency or "CNY",
                        mode=price.mode,
                        token_tier=price.token_tier,
                        resolution=price.resolution,
                        created_at=price.created_at
                    ))

            # 批量获取分类信息
            category_ids = list(set(m.category_id for m in models if m.category_id))
            category_map = {}
            if category_ids:
                cat_query = select(PricingCategory).where(
                    PricingCategory.id.in_(category_ids)
                )
                cat_result = await db.execute(cat_query)
                for cat in cat_result.scalars().all():
                    category_map[cat.id] = cat.name

            # 构建响应
            data = []
            for model in models:
                item = PricingModelAdminResponse(
                    id=model.id,
                    snapshot_id=model.snapshot_id,
                    category_id=model.category_id,
                    category_name=category_map.get(model.category_id),
                    model_code=model.model_code,
                    model_name=model.model_name,
                    display_name=model.display_name,
                    mode=model.mode,
                    token_tier=model.token_tier,
                    resolution=model.resolution,
                    supports_batch=model.supports_batch or False,
                    supports_cache=model.supports_cache or False,
                    remark=model.remark,
                    status=model.status or "active",
                    created_at=model.created_at,
                    prices=prices_map.get(model.id, [])
                )
                data.append(item)

            return PaginatedPricingModelResponse(
                total=total,
                page=page,
                page_size=page_size,
                data=data
            )
        except Exception as e:
            logger.error(f"查询模型列表失败: {e}")
            raise

    async def get_model_detail(
        self,
        db: AsyncSession,
        model_id: int
    ) -> Optional[PricingModelAdminResponse]:
        """获取模型详情"""
        try:
            query = select(PricingModel).where(PricingModel.id == model_id)
            result = await db.execute(query)
            model = result.scalars().first()

            if not model:
                return None

            # 获取价格信息
            prices_query = select(PricingModelPrice).where(
                PricingModelPrice.model_id == model_id
            )
            prices_result = await db.execute(prices_query)
            prices = [
                PricingModelPriceResponse(
                    id=p.id,
                    model_id=p.model_id,
                    dimension_code=p.dimension_code or "",
                    unit_price=float(p.unit_price) if p.unit_price else 0,
                    unit=p.unit or "",
                    currency=p.currency or "CNY",
                    mode=p.mode,
                    token_tier=p.token_tier,
                    resolution=p.resolution,
                    created_at=p.created_at
                )
                for p in prices_result.scalars().all()
            ]

            # 获取分类名称
            category_name = None
            if model.category_id:
                cat_query = select(PricingCategory.name).where(
                    PricingCategory.id == model.category_id
                )
                cat_result = await db.execute(cat_query)
                category_name = cat_result.scalar()

            return PricingModelAdminResponse(
                id=model.id,
                snapshot_id=model.snapshot_id,
                category_id=model.category_id,
                category_name=category_name,
                model_code=model.model_code,
                model_name=model.model_name,
                display_name=model.display_name,
                mode=model.mode,
                token_tier=model.token_tier,
                resolution=model.resolution,
                supports_batch=model.supports_batch or False,
                supports_cache=model.supports_cache or False,
                remark=model.remark,
                status=model.status or "active",
                created_at=model.created_at,
                prices=prices
            )
        except Exception as e:
            logger.error(f"获取模型详情失败: {e}")
            raise

    async def create_model(
        self,
        db: AsyncSession,
        data: PricingModelCreateRequest
    ) -> PricingModel:
        """新增模型"""
        try:
            # 获取最新快照ID
            snapshot_id = await self.get_latest_snapshot_id(db)

            # 创建模型
            model = PricingModel(
                snapshot_id=snapshot_id,
                category_id=data.category_id,
                model_code=data.model_code,
                model_name=data.model_name,
                display_name=data.display_name,
                mode=data.mode,
                token_tier=data.token_tier,
                resolution=data.resolution,
                supports_batch=data.supports_batch,
                supports_cache=data.supports_cache,
                remark=data.remark,
                status="active"
            )

            db.add(model)
            await db.commit()
            await db.refresh(model)

            logger.info(f"创建模型成功: {model.model_code} (ID: {model.id})")
            return model
        except Exception as e:
            await db.rollback()
            logger.error(f"创建模型失败: {e}")
            raise

    async def update_model(
        self,
        db: AsyncSession,
        model_id: int,
        data: PricingModelUpdateRequest
    ) -> Optional[PricingModel]:
        """更新模型"""
        try:
            # 检查模型是否存在
            query = select(PricingModel).where(PricingModel.id == model_id)
            result = await db.execute(query)
            model = result.scalars().first()

            if not model:
                return None

            # 更新非空字段
            update_data = data.model_dump(exclude_unset=True, exclude_none=True)
            for field, value in update_data.items():
                setattr(model, field, value)

            await db.commit()
            await db.refresh(model)

            logger.info(f"更新模型成功: ID={model_id}")
            return model
        except Exception as e:
            await db.rollback()
            logger.error(f"更新模型失败: {e}")
            raise

    async def delete_model(
        self,
        db: AsyncSession,
        model_id: int
    ) -> bool:
        """删除模型（软删除）"""
        try:
            # 检查模型是否存在
            query = select(PricingModel).where(PricingModel.id == model_id)
            result = await db.execute(query)
            model = result.scalars().first()

            if not model:
                return False

            # 软删除：设置 status 为 inactive
            model.status = "inactive"
            await db.commit()

            logger.info(f"删除模型成功（软删除）: ID={model_id}")
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"删除模型失败: {e}")
            raise

    async def batch_delete_models(
        self,
        db: AsyncSession,
        model_ids: List[int]
    ) -> int:
        """批量删除模型（软删除）"""
        try:
            stmt = (
                update(PricingModel)
                .where(PricingModel.id.in_(model_ids))
                .values(status="inactive")
            )
            result = await db.execute(stmt)
            await db.commit()

            affected_count = result.rowcount
            logger.info(f"批量删除模型成功（软删除）: 影响 {affected_count} 条记录")
            return affected_count
        except Exception as e:
            await db.rollback()
            logger.error(f"批量删除模型失败: {e}")
            raise

    # ===== 价格管理 =====

    async def get_model_prices(
        self,
        db: AsyncSession,
        model_id: int
    ) -> List[PricingModelPriceResponse]:
        """获取模型价格列表"""
        try:
            query = select(PricingModelPrice).where(
                PricingModelPrice.model_id == model_id
            ).order_by(PricingModelPrice.id)
            result = await db.execute(query)
            prices = result.scalars().all()

            return [
                PricingModelPriceResponse(
                    id=p.id,
                    model_id=p.model_id,
                    dimension_code=p.dimension_code or "",
                    unit_price=float(p.unit_price) if p.unit_price else 0,
                    unit=p.unit or "",
                    currency=p.currency or "CNY",
                    mode=p.mode,
                    token_tier=p.token_tier,
                    resolution=p.resolution,
                    created_at=p.created_at
                )
                for p in prices
            ]
        except Exception as e:
            logger.error(f"获取模型价格列表失败: {e}")
            raise

    async def add_model_price(
        self,
        db: AsyncSession,
        model_id: int,
        data: PricingModelPriceCreateRequest
    ) -> PricingModelPrice:
        """添加价格维度"""
        try:
            # 检查模型是否存在
            model_query = select(PricingModel).where(PricingModel.id == model_id)
            model_result = await db.execute(model_query)
            model = model_result.scalars().first()

            if not model:
                raise ValueError(f"模型不存在: ID={model_id}")

            # 创建价格记录
            price = PricingModelPrice(
                snapshot_id=model.snapshot_id,
                model_id=model_id,
                dimension_code=data.dimension_code,
                unit_price=data.unit_price,
                unit=data.unit,
                currency=data.currency,
                mode=data.mode,
                token_tier=data.token_tier,
                resolution=data.resolution
            )

            db.add(price)
            await db.commit()
            await db.refresh(price)

            logger.info(f"添加价格维度成功: 模型ID={model_id}, 维度={data.dimension_code}")
            return price
        except Exception as e:
            await db.rollback()
            logger.error(f"添加价格维度失败: {e}")
            raise

    async def update_price(
        self,
        db: AsyncSession,
        price_id: int,
        data: PricingModelPriceUpdateRequest
    ) -> Optional[PricingModelPrice]:
        """更新价格"""
        try:
            query = select(PricingModelPrice).where(PricingModelPrice.id == price_id)
            result = await db.execute(query)
            price = result.scalars().first()

            if not price:
                return None

            # 更新非空字段
            update_data = data.model_dump(exclude_unset=True, exclude_none=True)
            for field, value in update_data.items():
                setattr(price, field, value)

            await db.commit()
            await db.refresh(price)

            logger.info(f"更新价格成功: ID={price_id}")
            return price
        except Exception as e:
            await db.rollback()
            logger.error(f"更新价格失败: {e}")
            raise

    async def delete_price(
        self,
        db: AsyncSession,
        price_id: int
    ) -> bool:
        """删除价格"""
        try:
            query = select(PricingModelPrice).where(PricingModelPrice.id == price_id)
            result = await db.execute(query)
            price = result.scalars().first()

            if not price:
                return False

            await db.delete(price)
            await db.commit()

            logger.info(f"删除价格成功: ID={price_id}")
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"删除价格失败: {e}")
            raise

    # ===== 分类管理 =====

    async def list_categories(
        self,
        db: AsyncSession
    ) -> List[CategoryResponse]:
        """获取分类列表"""
        try:
            query = select(PricingCategory).where(
                PricingCategory.is_active == True
            ).order_by(PricingCategory.sort_order)
            result = await db.execute(query)
            categories = result.scalars().all()

            return [
                CategoryResponse(
                    id=cat.id,
                    code=cat.code,
                    name=cat.name,
                    parent_code=cat.parent_code,
                    sort_order=cat.sort_order or 0,
                    is_active=cat.is_active or True
                )
                for cat in categories
            ]
        except Exception as e:
            logger.error(f"获取分类列表失败: {e}")
            raise

    async def get_filter_options(
        self,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """获取筛选选项"""
        try:
            # 获取所有模式
            modes_query = select(PricingModel.mode).where(
                PricingModel.mode.isnot(None),
                PricingModel.status == "active"
            ).distinct()
            modes_result = await db.execute(modes_query)
            modes = [m for m in modes_result.scalars().all() if m]

            # 获取所有 Token 阶梯
            tiers_query = select(PricingModel.token_tier).where(
                PricingModel.token_tier.isnot(None),
                PricingModel.status == "active"
            ).distinct()
            tiers_result = await db.execute(tiers_query)
            token_tiers = [t for t in tiers_result.scalars().all() if t]

            # 获取所有分辨率
            res_query = select(PricingModel.resolution).where(
                PricingModel.resolution.isnot(None),
                PricingModel.status == "active"
            ).distinct()
            res_result = await db.execute(res_query)
            resolutions = [r for r in res_result.scalars().all() if r]

            return {
                "modes": modes,
                "token_tiers": token_tiers,
                "resolutions": resolutions
            }
        except Exception as e:
            logger.error(f"获取筛选选项失败: {e}")
            raise


# 创建全局服务实例
pricing_admin_service = PricingAdminService()
