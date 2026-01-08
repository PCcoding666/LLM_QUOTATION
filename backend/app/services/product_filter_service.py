"""
商品筛选服务
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.product import Product, ProductPrice, ProductSpec
from app.schemas.quote import (
    FilterOption, FilterOptionsResponse, 
    ModelListItem, PaginatedModelListResponse,
    ModelDetailResponse, ModelSpecs, ModelPricingDetail,
    ProductSearchResultItem, ProductSearchResponse,
    ModelPricing
)


class ProductFilterService:
    """商品筛选服务"""
    
    # 类别到模态的映射
    CATEGORY_TO_MODALITY = {
        "AI-大模型-文本生成": "text",
        "AI-大模型-视觉理解": "image",
        "AI-大模型-语音": "audio",
        "AI-大模型-多模态": "multimodal",
        "AI-大模型-向量": "text_embedding",
        "AI-大模型-重排序": "rerank",
    }
    
    # 模态显示名称映射
    MODALITY_NAMES = {
        "text": "文本",
        "image": "图片",
        "audio": "音频",
        "video": "视频",
        "multimodal": "全模态",
    }
    
    # 能力显示名称映射
    CAPABILITY_NAMES = {
        "understanding": "理解",
        "generation": "生成",
        "both": "理解并生成",
    }
    
    # 模型类型显示名称映射
    MODEL_TYPE_NAMES = {
        "llm": "大语言模型",
        "text_embedding": "文本向量",
        "multimodal_embedding": "多模态向量",
        "rerank": "重排序",
    }
    
    # 地域显示名称映射
    REGION_NAMES = {
        "cn-beijing": "中国内地（北京）",
        "cn-shanghai": "中国内地（上海）",
        "cn-hangzhou": "中国内地（杭州）",
        "cn-shenzhen": "中国内地（深圳）",
        "ap-southeast-1": "国际（新加坡）",
        "us-west-1": "国际（美国西部）",
    }
    
    @staticmethod
    def map_category_to_modality(category: str) -> str:
        """将数据库category映射为前端modality"""
        return ProductFilterService.CATEGORY_TO_MODALITY.get(category, "unknown")
    
    @staticmethod
    def map_category_to_capability(category: str) -> Optional[str]:
        """根据类别推断能力类型"""
        if "生成" in category:
            return "generation"
        elif "理解" in category:
            return "understanding"
        elif "大模型" in category:
            return "both"
        return None
    
    @staticmethod
    def map_category_to_model_type(category: str) -> Optional[str]:
        """根据类别推断模型类型"""
        if "向量" in category or "embedding" in category.lower():
            if "多模态" in category:
                return "multimodal_embedding"
            return "text_embedding"
        elif "重排序" in category or "rerank" in category.lower():
            return "rerank"
        elif "大模型" in category or "llm" in category.lower():
            return "llm"
        return None
    
    async def get_filter_options(self, db: AsyncSession) -> FilterOptionsResponse:
        """获取所有筛选维度的可选项"""
        try:
            # 获取所有地域
            regions_query = select(ProductPrice.region).distinct()
            regions_result = await db.execute(regions_query)
            regions = [
                FilterOption(
                    code=region,
                    name=self.REGION_NAMES.get(region, region)
                )
                for region in regions_result.scalars().all()
            ]
            
            # 获取所有模态（从category映射）
            categories_query = select(Product.category).distinct()
            categories_result = await db.execute(categories_query)
            modalities_set = set()
            for category in categories_result.scalars().all():
                modality = self.map_category_to_modality(category)
                if modality != "unknown":
                    modalities_set.add(modality)
            
            modalities = [
                FilterOption(code=m, name=self.MODALITY_NAMES.get(m, m))
                for m in sorted(modalities_set)
            ]
            
            # 能力类型（固定列表）
            capabilities = [
                FilterOption(code="understanding", name="理解"),
                FilterOption(code="generation", name="生成"),
                FilterOption(code="both", name="理解并生成"),
            ]
            
            # 模型类型（固定列表）
            model_types = [
                FilterOption(code="llm", name="大语言模型"),
                FilterOption(code="text_embedding", name="文本向量"),
                FilterOption(code="multimodal_embedding", name="多模态向量"),
                FilterOption(code="rerank", name="重排序"),
            ]
            
            return FilterOptionsResponse(
                regions=regions,
                modalities=modalities,
                capabilities=capabilities,
                model_types=model_types
            )
        except Exception as e:
            logger.error(f"获取筛选选项失败: {e}")
            raise
    
    async def filter_models(
        self,
        db: AsyncSession,
        region: Optional[str] = None,
        modality: Optional[str] = None,
        capability: Optional[str] = None,
        model_type: Optional[str] = None,
        vendor: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedModelListResponse:
        """根据筛选条件查询模型列表"""
        try:
            # 构建基础查询
            query = select(Product).where(Product.status == "active")
                
            # 应用筛选条件
            if vendor:
                query = query.where(Product.vendor == vendor)
                
            if keyword:
                query = query.where(
                    or_(
                        Product.product_name.ilike(f"%{keyword}%"),
                        Product.product_code.ilike(f"%{keyword}%")
                    )
                )
                
            # 根据modality筛选（需要映射category）
            if modality:
                modalities = [m.strip() for m in modality.split(",")]
                category_filters = []
                for mod in modalities:
                    for cat, mod_value in self.CATEGORY_TO_MODALITY.items():
                        if mod_value == mod:
                            category_filters.append(Product.category == cat)
                if category_filters:
                    query = query.where(or_(*category_filters))
                
            # 根据capability筛选
            if capability:
                capability_filters = []
                for cap in capability.split(","):
                    cap = cap.strip()
                    if cap == "generation":
                        capability_filters.append(Product.category.ilike("%生成%"))
                    elif cap == "understanding":
                        capability_filters.append(Product.category.ilike("%理解%"))
                    elif cap == "both":
                        capability_filters.append(Product.category.ilike("%大模型%"))
                if capability_filters:
                    query = query.where(or_(*capability_filters))
                
            # 根据model_type筛选
            if model_type:
                type_filters = []
                for mt in model_type.split(","):
                    mt = mt.strip()
                    if mt == "text_embedding":
                        type_filters.append(and_(
                            Product.category.ilike("%向量%"),
                            ~Product.category.ilike("%多模态%")
                        ))
                    elif mt == "multimodal_embedding":
                        type_filters.append(and_(
                            Product.category.ilike("%向量%"),
                            Product.category.ilike("%多模态%")
                        ))
                    elif mt == "rerank":
                        type_filters.append(Product.category.ilike("%重排序%"))
                    elif mt == "llm":
                        type_filters.append(and_(
                            Product.category.ilike("%大模型%"),
                            ~Product.category.ilike("%向量%"),
                            ~Product.category.ilike("%重排序%")
                        ))
                if type_filters:
                    query = query.where(or_(*type_filters))
                
            # 计算总数
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await db.execute(count_query)
            total = total_result.scalar() or 0
                
            # 分页
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)
            query = query.order_by(Product.vendor, Product.product_name)
                
            # 执行查询
            result = await db.execute(query)
            products = result.scalars().all()
                
            if not products:
                return PaginatedModelListResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    data=[]
                )
                
            # 批量获取价格和规格信息（解决N+1查询问题）
            product_codes = [p.product_code for p in products]
                
            # 批量查询价格
            target_region = region or "cn-beijing"
            prices_query = select(ProductPrice).where(
                and_(
                    ProductPrice.product_code.in_(product_codes),
                    ProductPrice.region == target_region
                )
            )
            prices_result = await db.execute(prices_query)
            prices_map = {p.product_code: p for p in prices_result.scalars().all()}
                
            # 批量查询规格
            specs_query = select(ProductSpec).where(
                ProductSpec.product_code.in_(product_codes)
            )
            specs_result = await db.execute(specs_query)
            specs_by_product = {}
            for spec in specs_result.scalars().all():
                if spec.product_code not in specs_by_product:
                    specs_by_product[spec.product_code] = []
                specs_by_product[spec.product_code].append(spec)
                
            # 构建响应数据
            data = []
            for product in products:
                # 获取价格信息
                price = prices_map.get(product.product_code)
                pricing_data = None
                if price and price.pricing_variables:
                    pricing_data = ModelPricing(
                        region=price.region,
                        input_price=price.pricing_variables.get("input_price"),
                        output_price=price.pricing_variables.get("output_price"),
                        unit=price.unit or "千Token"
                    )
                    
                # 获取规格信息
                specs = specs_by_product.get(product.product_code, [])
                context_specs = []
                supports_thinking = False
                for spec in specs:
                    if spec.spec_values:
                        if "context" in spec.spec_name.lower():
                            context_specs.append(str(spec.spec_values.get("value", "")))
                        if spec.spec_values.get("supports_thinking"):
                            supports_thinking = True
                    
                item = ModelListItem(
                    model_id=product.product_code,
                    model_name=product.product_name,
                    vendor=product.vendor,
                    category=product.category,
                    modality=self.map_category_to_modality(product.category),
                    capability=self.map_category_to_capability(product.category),
                    context_specs=context_specs,
                    supports_thinking=supports_thinking,
                    pricing=pricing_data,
                    status=product.status
                )
                data.append(item)
                
            return PaginatedModelListResponse(
                total=total,
                page=page,
                page_size=page_size,
                data=data
            )
        except Exception as e:
            logger.error(f"筛选模型失败: {e}")
            raise
    
    async def search_by_names(
        self,
        db: AsyncSession,
        names: List[str],
        region: str = "cn-beijing"
    ) -> ProductSearchResponse:
        """批量名称搜索"""
        found = []
        not_found = []
        
        for name in names:
            try:
                # 精确匹配
                exact_query = select(Product).where(
                    or_(
                        func.lower(Product.product_code) == name.lower(),
                        func.lower(Product.product_name) == name.lower()
                    )
                )
                exact_result = await db.execute(exact_query)
                product = exact_result.scalars().first()
                
                if product:
                    found.append(ProductSearchResultItem(
                        model_id=product.product_code,
                        model_name=product.product_name,
                        match_type="exact",
                        search_term=name
                    ))
                    continue
                
                # 模糊匹配
                fuzzy_query = select(Product).where(
                    Product.product_name.ilike(f"%{name}%")
                ).limit(1)
                fuzzy_result = await db.execute(fuzzy_query)
                product = fuzzy_result.scalars().first()
                
                if product:
                    found.append(ProductSearchResultItem(
                        model_id=product.product_code,
                        model_name=product.product_name,
                        match_type="fuzzy",
                        search_term=name
                    ))
                else:
                    not_found.append(name)
            except Exception as e:
                logger.error(f"搜索 {name} 失败: {e}")
                not_found.append(name)
        
        return ProductSearchResponse(found=found, not_found=not_found)
    
    async def get_model_detail(
        self,
        db: AsyncSession,
        model_id: str,
        region: Optional[str] = None
    ) -> ModelDetailResponse:
        """获取模型详情"""
        try:
            # 查询产品基础信息
            product_query = select(Product).where(Product.product_code == model_id)
            product_result = await db.execute(product_query)
            product = product_result.scalars().first()
            
            if not product:
                raise ValueError(f"模型不存在: {model_id}")
            
            # 查询规格
            specs_query = select(ProductSpec).where(
                ProductSpec.product_code == model_id
            )
            specs_result = await db.execute(specs_query)
            specs_list = specs_result.scalars().all()
            
            # 解析规格
            max_context_length = None
            max_input_tokens = None
            max_output_tokens = None
            supports_thinking = False
            
            for spec in specs_list:
                if spec.spec_values:
                    if "context" in spec.spec_name.lower():
                        max_context_length = spec.spec_values.get("max_context_length")
                    if "input" in spec.spec_name.lower():
                        max_input_tokens = spec.spec_values.get("max_input_tokens")
                    if "output" in spec.spec_name.lower():
                        max_output_tokens = spec.spec_values.get("max_output_tokens")
                    if spec.spec_values.get("supports_thinking"):
                        supports_thinking = True
            
            model_specs = ModelSpecs(
                max_context_length=max_context_length,
                max_input_tokens=max_input_tokens,
                max_output_tokens=max_output_tokens,
                supports_thinking=supports_thinking
            )
            
            # 查询价格
            price_query = select(ProductPrice).where(
                ProductPrice.product_code == model_id
            )
            if region:
                price_query = price_query.where(ProductPrice.region == region)
            
            price_result = await db.execute(price_query)
            prices = price_result.scalars().all()
            
            # 解析价格
            pricing_list = []
            for price in prices:
                if price.pricing_variables:
                    pricing_detail = ModelPricingDetail(
                        region=price.region,
                        region_name=self.REGION_NAMES.get(price.region, price.region),
                        input_price=price.pricing_variables.get("input_price"),
                        output_price=price.pricing_variables.get("output_price"),
                        thinking_input_price=price.pricing_variables.get("thinking_input_price"),
                        thinking_output_price=price.pricing_variables.get("thinking_output_price"),
                        batch_discount=price.pricing_variables.get("batch_discount"),
                        unit=price.unit or "千Token"
                    )
                    pricing_list.append(pricing_detail)
            
            return ModelDetailResponse(
                model_id=product.product_code,
                model_name=product.product_name,
                vendor=product.vendor,
                description=product.description,
                category=product.category,
                specs=model_specs,
                pricing=pricing_list,
                status=product.status
            )
        except Exception as e:
            logger.error(f"获取模型详情失败: {e}")
            raise


# 创建全局服务实例
product_filter_service = ProductFilterService()
