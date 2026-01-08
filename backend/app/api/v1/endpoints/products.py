"""
产品数据API端点
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.product import ProductResponse, ProductPriceResponse, PaginatedProductListResponse
from app.schemas.quote import (
    FilterOptionsResponse, PaginatedModelListResponse,
    ModelDetailResponse, ProductSearchRequest, ProductSearchResponse
)
from app.services.product_filter_service import product_filter_service

router = APIRouter()


@router.get("/filters", response_model=FilterOptionsResponse)
async def get_filter_options(
    db: AsyncSession = Depends(get_db)
):
    """
    获取筛选条件选项
    
    返回所有可用的筛选维度及其选项
    """
    try:
        return await product_filter_service.get_filter_options(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取筛选选项失败: {str(e)}")


@router.get("/models", response_model=PaginatedModelListResponse)
async def get_models(
    region: Optional[str] = Query(None, description="地域筛选"),
    modality: Optional[str] = Query(None, description="模态筛选（多选逗号分隔）"),
    capability: Optional[str] = Query(None, description="能力筛选"),
    model_type: Optional[str] = Query(None, description="类型筛选"),
    vendor: Optional[str] = Query(None, description="厂商筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取大模型商品列表
    
    支持多条件筛选和关键词搜索
    """
    try:
        return await product_filter_service.filter_models(
            db=db,
            region=region,
            modality=modality,
            capability=capability,
            model_type=model_type,
            vendor=vendor,
            keyword=keyword,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询模型列表失败: {str(e)}")


@router.post("/search", response_model=ProductSearchResponse)
async def search_products(
    request: ProductSearchRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    批量名称搜索
    
    支持精确匹配和模糊匹配
    """
    try:
        return await product_filter_service.search_by_names(
            db=db,
            names=request.names,
            region=request.region
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索产品失败: {str(e)}")


@router.get("/models/{model_id}", response_model=ModelDetailResponse)
async def get_model_detail(
    model_id: str,
    region: Optional[str] = Query("cn-beijing", description="地域"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取模型详情
    
    返回模型的完整信息，包括规格和价格
    """
    try:
        return await product_filter_service.get_model_detail(
            db=db,
            model_id=model_id,
            region=region
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型详情失败: {str(e)}")


@router.get("/", response_model=PaginatedProductListResponse)
async def get_products(
    category: Optional[str] = Query(None, description="产品类别"),
    vendor: Optional[str] = Query(None, description="厂商筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query("active", description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取产品列表
    
    支持按类别、厂商和关键词搜索，返回分页结果
    """
    try:
        from sqlalchemy import select, func, or_
        from app.models.product import Product
        
        # 构建查询
        query = select(Product)
        
        if status:
            query = query.where(Product.status == status)
        if category:
            query = query.where(Product.category == category)
        if vendor:
            query = query.where(Product.vendor == vendor)
        if keyword:
            query = query.where(
                or_(
                    Product.product_name.ilike(f"%{keyword}%"),
                    Product.product_code.ilike(f"%{keyword}%"),
                    Product.description.ilike(f"%{keyword}%")
                )
            )
        
        # 计算总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # 分页
        offset = (page - 1) * size
        query = query.order_by(Product.vendor, Product.product_name)
        query = query.offset(offset).limit(size)
        
        result = await db.execute(query)
        products = result.scalars().all()
        
        # 转换为响应格式
        data = [
            ProductResponse(
                product_code=p.product_code,
                product_name=p.product_name,
                category=p.category,
                vendor=p.vendor,
                description=p.description,
                status=p.status,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in products
        ]
        
        return PaginatedProductListResponse(
            total=total,
            page=page,
            page_size=size,
            data=data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取产品列表失败: {str(e)}")


@router.get("/{product_code}", response_model=ProductResponse)
async def get_product(
    product_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取产品详情
    
    根据产品代码获取完整的产品信息
    """
    try:
        from sqlalchemy import select
        from app.models.product import Product
        
        query = select(Product).where(Product.product_code == product_code)
        result = await db.execute(query)
        product = result.scalars().first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"产品不存在: {product_code}")
        
        return ProductResponse(
            product_code=product.product_code,
            product_name=product.product_name,
            category=product.category,
            vendor=product.vendor,
            description=product.description,
            status=product.status,
            created_at=product.created_at,
            updated_at=product.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取产品详情失败: {str(e)}")


@router.get("/{product_code}/price", response_model=ProductPriceResponse)
async def get_product_price(
    product_code: str,
    region: Optional[str] = Query("cn-beijing", description="地域"),
    spec_type: Optional[str] = Query(None, description="规格类型"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取产品价格信息
    
    根据产品代码和地域获取价格详情
    """
    try:
        from sqlalchemy import select, and_, or_
        from datetime import datetime
        from app.models.product import ProductPrice
        
        # 构建查询
        query = select(ProductPrice).where(
            ProductPrice.product_code == product_code
        )
        
        if region:
            query = query.where(ProductPrice.region == region)
        
        if spec_type:
            query = query.where(ProductPrice.spec_type == spec_type)
        
        # 获取有效期内的价格
        query = query.where(
            and_(
                ProductPrice.effective_date <= datetime.now(),
                or_(
                    ProductPrice.expire_date.is_(None),
                    ProductPrice.expire_date > datetime.now()
                )
            )
        )
        
        query = query.order_by(ProductPrice.effective_date.desc())
        result = await db.execute(query)
        price = result.scalars().first()
        
        if not price:
            raise HTTPException(
                status_code=404, 
                detail=f"产品 {product_code} 在地域 {region} 的价格信息不存在"
            )
        
        return ProductPriceResponse(
            price_id=str(price.price_id),
            product_code=price.product_code,
            region=price.region,
            spec_type=price.spec_type,
            billing_mode=price.billing_mode,
            unit_price=float(price.unit_price),
            unit=price.unit or "千Token",
            pricing_variables=price.pricing_variables,
            effective_date=price.effective_date
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取价格信息失败: {str(e)}")


@router.get("/{product_code}/prices", response_model=List[ProductPriceResponse])
async def get_product_prices(
    product_code: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取产品所有地域的价格信息
    
    返回产品在各个地域的价格列表
    """
    try:
        from sqlalchemy import select, and_, or_
        from datetime import datetime
        from app.models.product import ProductPrice
        
        query = select(ProductPrice).where(
            and_(
                ProductPrice.product_code == product_code,
                ProductPrice.effective_date <= datetime.now(),
                or_(
                    ProductPrice.expire_date.is_(None),
                    ProductPrice.expire_date > datetime.now()
                )
            )
        ).order_by(ProductPrice.region)
        
        result = await db.execute(query)
        prices = result.scalars().all()
        
        return [
            ProductPriceResponse(
                price_id=str(p.price_id),
                product_code=p.product_code,
                region=p.region,
                spec_type=p.spec_type,
                billing_mode=p.billing_mode,
                unit_price=float(p.unit_price),
                unit=p.unit or "千Token",
                pricing_variables=p.pricing_variables,
                effective_date=p.effective_date
            )
            for p in prices
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取价格列表失败: {str(e)}")


@router.get("/categories/list")
async def get_product_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有产品类别
    
    返回系统中所有产品类别的列表
    """
    try:
        from sqlalchemy import select
        from app.models.product import Product
        
        query = select(Product.category).distinct()
        result = await db.execute(query)
        categories = result.scalars().all()
        
        return {
            "categories": sorted(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取类别列表失败: {str(e)}")


@router.get("/vendors/list")
async def get_product_vendors(
    db: AsyncSession = Depends(get_db)
):
    """
    获取所有厂商列表
    
    返回系统中所有产品厂商的列表
    """
    try:
        from sqlalchemy import select
        from app.models.product import Product
        
        query = select(Product.vendor).distinct()
        result = await db.execute(query)
        vendors = result.scalars().all()
        
        return {
            "vendors": sorted(vendors)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取厂商列表失败: {str(e)}")

