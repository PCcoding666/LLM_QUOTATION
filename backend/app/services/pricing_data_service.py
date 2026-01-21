"""
定价数据服务 - 查询pricing_*表提供多维度定价数据
"""
from typing import List, Optional, Dict, Any
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, distinct
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.pricing import (
    PricingModel, PricingModelPrice, PricingCategory, PricingDimension
)


class PricingDataService:
    """定价数据服务 - 从pricing_*表查询多维度定价信息"""
    
    # 分类代码到模态的映射
    CATEGORY_TO_MODALITY = {
        "text_generation": "text",
        "vision_understanding": "image", 
        "audio": "audio",
        "multimodal": "multimodal",
        "embedding": "text_embedding",
        "rerank": "rerank",
        "video_generation": "video",
        "image_generation": "image_gen",
    }
    
    # 模态显示名称
    MODALITY_NAMES = {
        "text": "文本生成",
        "image": "视觉理解",
        "audio": "语音",
        "video": "视频",
        "multimodal": "全模态",
        "text_embedding": "文本向量",
        "rerank": "重排序",
        "image_gen": "图像生成",
    }
    
    async def get_filter_options(self, db: AsyncSession) -> Dict[str, Any]:
        """获取所有筛选维度的可选项"""
        try:
            # 获取所有分类
            categories_query = select(PricingCategory).where(PricingCategory.is_active == True)
            categories_result = await db.execute(categories_query)
            categories = [
                {"code": cat.code, "name": cat.name}
                for cat in categories_result.scalars().all()
            ]
            
            # 获取所有模式类型
            modes_query = select(distinct(PricingModel.mode)).where(PricingModel.mode.isnot(None))
            modes_result = await db.execute(modes_query)
            modes = [
                {"code": mode, "name": mode}
                for mode in modes_result.scalars().all() if mode
            ]
            
            # 获取所有Token阶梯
            tiers_query = select(distinct(PricingModel.token_tier)).where(PricingModel.token_tier.isnot(None))
            tiers_result = await db.execute(tiers_query)
            token_tiers = [
                {"code": tier, "name": tier}
                for tier in tiers_result.scalars().all() if tier
            ]
            
            # 获取所有分辨率
            res_query = select(distinct(PricingModel.resolution)).where(PricingModel.resolution.isnot(None))
            res_result = await db.execute(res_query)
            resolutions = [
                {"code": res, "name": res}
                for res in res_result.scalars().all() if res
            ]
            
            return {
                "categories": categories,
                "modes": modes,
                "token_tiers": token_tiers,
                "resolutions": resolutions,
                "batch_options": [
                    {"code": "true", "name": "支持Batch半价"},
                    {"code": "false", "name": "不支持Batch"}
                ],
                "cache_options": [
                    {"code": "true", "name": "支持上下文缓存"},
                    {"code": "false", "name": "不支持缓存"}
                ]
            }
        except Exception as e:
            logger.error(f"获取定价筛选选项失败: {e}")
            raise
    
    async def filter_models(
        self,
        db: AsyncSession,
        category: Optional[str] = None,
        mode: Optional[str] = None,
        token_tier: Optional[str] = None,
        resolution: Optional[str] = None,
        supports_batch: Optional[bool] = None,
        supports_cache: Optional[bool] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """根据筛选条件查询模型列表"""
        try:
            # 构建基础查询
            query = select(PricingModel).where(PricingModel.status == 'active')
            
            # 应用筛选条件
            if category:
                query = query.join(PricingCategory).where(PricingCategory.code == category)
                
            if mode:
                query = query.where(PricingModel.mode == mode)
                
            if token_tier:
                query = query.where(PricingModel.token_tier == token_tier)
                
            if resolution:
                query = query.where(PricingModel.resolution == resolution)
                
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
            query = query.order_by(PricingModel.model_name)
            
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
                    prices_map[price.model_id].append({
                        "dimension_code": price.dimension_code,
                        "unit_price": float(price.unit_price) if price.unit_price else None,
                        "unit": price.unit,
                        "currency": price.currency
                    })
            
            # 构建响应
            data = []
            for model in models:
                item = {
                    "id": model.id,
                    "model_code": model.model_code,
                    "model_name": model.model_name,
                    "display_name": model.display_name,
                    "sub_category": model.sub_category,
                    "mode": model.mode,
                    "token_tier": model.token_tier,
                    "resolution": model.resolution,
                    "supports_batch": model.supports_batch,
                    "supports_cache": model.supports_cache,
                    "remark": model.remark,
                    "prices": prices_map.get(model.id, [])
                }
                data.append(item)
            
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "data": data
            }
        except Exception as e:
            logger.error(f"筛选定价模型失败: {e}")
            raise
    
    async def get_model_pricing(
        self,
        db: AsyncSession,
        model_code: str
    ) -> Dict[str, Any]:
        """获取指定模型的完整定价信息"""
        try:
            # 查询所有匹配的模型记录（可能有多个变体）
            # 精确匹配 model_code 或 model_name
            models_query = select(PricingModel).where(
                or_(
                    PricingModel.model_code == model_code,
                    PricingModel.model_name == model_code,
                )
            )
            models_result = await db.execute(models_query)
            models = models_result.scalars().all()
            
            if not models:
                return {"found": False, "model_code": model_code, "variants": []}
            
            # 获取所有变体的价格
            model_ids = [m.id for m in models]
            prices_query = select(PricingModelPrice).where(
                PricingModelPrice.model_id.in_(model_ids)
            )
            prices_result = await db.execute(prices_query)
            
            prices_by_model = {}
            for price in prices_result.scalars().all():
                if price.model_id not in prices_by_model:
                    prices_by_model[price.model_id] = []
                prices_by_model[price.model_id].append({
                    "dimension_code": price.dimension_code,
                    "unit_price": float(price.unit_price) if price.unit_price else None,
                    "unit": price.unit,
                    "mode": price.mode,
                    "token_tier": price.token_tier,
                    "resolution": price.resolution
                })
            
            # 构建变体列表
            variants = []
            for model in models:
                variant = {
                    "id": model.id,
                    "model_name": model.model_name,
                    "display_name": model.display_name,
                    "mode": model.mode,
                    "token_tier": model.token_tier,
                    "resolution": model.resolution,
                    "supports_batch": model.supports_batch,
                    "supports_cache": model.supports_cache,
                    "remark": model.remark,
                    "rule_text": model.rule_text,
                    "prices": prices_by_model.get(model.id, [])
                }
                variants.append(variant)
            
            return {
                "found": True,
                "model_code": model_code,
                "variants_count": len(variants),
                "variants": variants
            }
        except Exception as e:
            logger.error(f"获取模型定价失败: {e}")
            raise
    
    async def get_pricing_summary(
        self,
        db: AsyncSession,
        model_code: str
    ) -> Dict[str, Any]:
        """获取模型定价摘要（用于前端快速展示）"""
        try:
            # 查询基础模型信息
            model_query = select(PricingModel).where(
                PricingModel.model_code == model_code
            ).limit(1)
            model_result = await db.execute(model_query)
            model = model_result.scalars().first()
            
            if not model:
                return {"found": False, "model_code": model_code}
            
            # 统计变体数量
            variants_query = select(func.count()).where(
                PricingModel.model_code == model_code
            )
            variants_result = await db.execute(variants_query)
            variants_count = variants_result.scalar() or 0
            
            # 获取价格范围
            price_query = select(
                func.min(PricingModelPrice.unit_price),
                func.max(PricingModelPrice.unit_price)
            ).join(PricingModel).where(
                PricingModel.model_code == model_code
            )
            price_result = await db.execute(price_query)
            price_row = price_result.first()
            
            min_price = float(price_row[0]) if price_row and price_row[0] else None
            max_price = float(price_row[1]) if price_row and price_row[1] else None
            
            return {
                "found": True,
                "model_code": model_code,
                "model_name": model.model_name,
                "display_name": model.display_name,
                "supports_batch": model.supports_batch,
                "supports_cache": model.supports_cache,
                "variants_count": variants_count,
                "price_range": {
                    "min": min_price,
                    "max": max_price,
                    "currency": "CNY"
                },
                "has_modes": variants_count > 1
            }
        except Exception as e:
            logger.error(f"获取定价摘要失败: {e}")
            raise
    
    async def search_models(
        self,
        db: AsyncSession,
        keyword: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """模型搜索（用于自动完成）"""
        try:
            query = select(PricingModel).where(
                or_(
                    PricingModel.model_code.ilike(f"%{keyword}%"),
                    PricingModel.model_name.ilike(f"%{keyword}%"),
                    PricingModel.display_name.ilike(f"%{keyword}%")
                )
            ).distinct(PricingModel.model_code).limit(limit)
            
            result = await db.execute(query)
            models = result.scalars().all()
            
            return [
                {
                    "model_code": m.model_code,
                    "model_name": m.model_name,
                    "display_name": m.display_name,
                    "supports_batch": m.supports_batch,
                    "supports_cache": m.supports_cache
                }
                for m in models
            ]
        except Exception as e:
            logger.error(f"搜索模型失败: {e}")
            raise
    
    async def get_categories_with_models(
        self,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """获取分类及其模型列表（树形结构）"""
        try:
            # 获取所有分类
            categories_query = select(PricingCategory).where(
                PricingCategory.is_active == True
            ).order_by(PricingCategory.sort_order)
            categories_result = await db.execute(categories_query)
            categories = categories_result.scalars().all()
            
            result = []
            for cat in categories:
                # 获取该分类下的模型
                models_query = select(PricingModel).where(
                    PricingModel.category_id == cat.id,
                    PricingModel.status == 'active'
                ).distinct(PricingModel.model_code)
                models_result = await db.execute(models_query)
                models = models_result.scalars().all()
                
                result.append({
                    "category_code": cat.code,
                    "category_name": cat.name,
                    "model_count": len(models),
                    "models": [
                        {
                            "model_code": m.model_code,
                            "model_name": m.model_name,
                            "display_name": m.display_name
                        }
                        for m in models
                    ]
                })
            
            return result
        except Exception as e:
            logger.error(f"获取分类模型树失败: {e}")
            raise


# 创建全局服务实例
pricing_data_service = PricingDataService()
