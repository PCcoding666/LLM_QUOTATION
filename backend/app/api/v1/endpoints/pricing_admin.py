"""
定价管理 API 端点
提供模型规格与价格的 CRUD 操作接口
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.pricing_admin import (
    PricingModelCreateRequest,
    PricingModelUpdateRequest,
    PricingModelPriceCreateRequest,
    PricingModelPriceUpdateRequest,
    PricingModelAdminResponse,
    PricingModelPriceResponse,
    PaginatedPricingModelResponse,
    CategoryResponse,
    BatchDeleteRequest,
    OperationResponse,
)
from app.services.pricing_admin_service import pricing_admin_service

router = APIRouter()


# =====================================================
# 模型管理 CRUD
# =====================================================

@router.get("/models", response_model=PaginatedPricingModelResponse)
async def list_models(
    category_id: Optional[int] = Query(None, description="分类ID"),
    mode: Optional[str] = Query(None, description="模式"),
    token_tier: Optional[str] = Query(None, description="Token阶梯"),
    supports_batch: Optional[bool] = Query(None, description="支持Batch半价"),
    supports_cache: Optional[bool] = Query(None, description="支持上下文缓存"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    status: Optional[str] = Query("active", description="状态"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取模型列表
    
    支持多条件筛选和关键词搜索，返回分页结果
    """
    try:
        return await pricing_admin_service.list_models(
            db=db,
            category_id=category_id,
            mode=mode,
            token_tier=token_tier,
            supports_batch=supports_batch,
            supports_cache=supports_cache,
            keyword=keyword,
            status=status,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@router.get("/models/{model_id}", response_model=PricingModelAdminResponse)
async def get_model_detail(
    model_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取模型详情
    
    返回模型的完整信息，包括价格列表
    """
    try:
        result = await pricing_admin_service.get_model_detail(db, model_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"模型不存在: ID={model_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型详情失败: {str(e)}")


@router.post("/models", response_model=PricingModelAdminResponse)
async def create_model(
    data: PricingModelCreateRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    新增模型
    
    创建新的定价模型记录
    """
    try:
        model = await pricing_admin_service.create_model(db, data)
        return await pricing_admin_service.get_model_detail(db, model.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建模型失败: {str(e)}")


@router.put("/models/{model_id}", response_model=PricingModelAdminResponse)
async def update_model(
    model_id: int,
    data: PricingModelUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    更新模型
    
    更新指定模型的信息
    """
    try:
        model = await pricing_admin_service.update_model(db, model_id, data)
        if not model:
            raise HTTPException(status_code=404, detail=f"模型不存在: ID={model_id}")
        return await pricing_admin_service.get_model_detail(db, model_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新模型失败: {str(e)}")


@router.delete("/models/{model_id}", response_model=OperationResponse)
async def delete_model(
    model_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除模型（软删除）
    
    将模型状态设置为 inactive
    """
    try:
        success = await pricing_admin_service.delete_model(db, model_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"模型不存在: ID={model_id}")
        return OperationResponse(
            success=True,
            message="删除成功",
            affected_count=1
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除模型失败: {str(e)}")


@router.post("/models/batch-delete", response_model=OperationResponse)
async def batch_delete_models(
    data: BatchDeleteRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    批量删除模型（软删除）
    
    将多个模型状态设置为 inactive
    """
    try:
        affected_count = await pricing_admin_service.batch_delete_models(db, data.model_ids)
        return OperationResponse(
            success=True,
            message=f"批量删除成功，影响 {affected_count} 条记录",
            affected_count=affected_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量删除失败: {str(e)}")


# =====================================================
# 价格管理
# =====================================================

@router.get("/models/{model_id}/prices", response_model=List[PricingModelPriceResponse])
async def get_model_prices(
    model_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取模型价格列表
    
    返回指定模型的所有价格维度
    """
    try:
        return await pricing_admin_service.get_model_prices(db, model_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取价格列表失败: {str(e)}")


@router.post("/models/{model_id}/prices", response_model=PricingModelPriceResponse)
async def add_model_price(
    model_id: int,
    data: PricingModelPriceCreateRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    添加价格维度
    
    为指定模型添加新的价格维度
    """
    try:
        price = await pricing_admin_service.add_model_price(db, model_id, data)
        return PricingModelPriceResponse(
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
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加价格维度失败: {str(e)}")


@router.put("/prices/{price_id}", response_model=PricingModelPriceResponse)
async def update_price(
    price_id: int,
    data: PricingModelPriceUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    更新价格
    
    更新指定价格维度的信息
    """
    try:
        price = await pricing_admin_service.update_price(db, price_id, data)
        if not price:
            raise HTTPException(status_code=404, detail=f"价格记录不存在: ID={price_id}")
        return PricingModelPriceResponse(
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
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新价格失败: {str(e)}")


@router.delete("/prices/{price_id}", response_model=OperationResponse)
async def delete_price(
    price_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除价格
    
    删除指定的价格维度记录
    """
    try:
        success = await pricing_admin_service.delete_price(db, price_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"价格记录不存在: ID={price_id}")
        return OperationResponse(
            success=True,
            message="删除成功",
            affected_count=1
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除价格失败: {str(e)}")


# =====================================================
# 分类管理
# =====================================================

@router.get("/categories", response_model=List[CategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    获取分类列表
    
    返回所有激活状态的分类
    """
    try:
        return await pricing_admin_service.list_categories(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分类列表失败: {str(e)}")


@router.get("/filters")
async def get_filter_options(
    db: AsyncSession = Depends(get_db)
):
    """
    获取筛选选项
    
    返回所有可用的筛选维度（模式、Token阶梯、分辨率）
    """
    try:
        return await pricing_admin_service.get_filter_options(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取筛选选项失败: {str(e)}")
