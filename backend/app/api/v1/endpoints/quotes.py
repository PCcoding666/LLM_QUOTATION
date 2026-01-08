"""
报价管理API端点
"""
from typing import List, Optional
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.quote import (
    QuoteCreateRequest, QuoteUpdateRequest,
    QuoteItemCreateRequest, QuoteItemUpdateRequest,
    QuoteItemBatchCreateRequest, QuoteDiscountRequest,
    QuoteDetailResponse, QuoteListResponse, QuoteItemResponse,
    PaginatedQuoteListResponse, QuoteItemBatchResult,
    QuoteVersionResponse, SuccessResponse
)
from app.services.quote_service import quote_service

router = APIRouter()


@router.post("/", response_model=QuoteDetailResponse)
async def create_quote(
    request: QuoteCreateRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    创建报价单
    
    生成唯一报价单编号，创建草稿状态的报价单
    """
    try:
        return await quote_service.create_quote(db, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建报价单失败: {str(e)}")


@router.get("/", response_model=PaginatedQuoteListResponse)
async def get_quotes(
    status: Optional[str] = Query(None, description="状态筛选"),
    customer_name: Optional[str] = Query(None, description="客户名称模糊搜索"),
    created_by: Optional[str] = Query(None, description="创建人精确筛选"),
    start_date: Optional[date] = Query(None, description="创建时间起"),
    end_date: Optional[date] = Query(None, description="创建时间止"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取报价单列表
    
    支持多条件筛选和分页
    """
    try:
        return await quote_service.list_quotes(
            db=db,
            customer_name=customer_name,
            status=status,
            created_by=created_by,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取报价单列表失败: {str(e)}")


@router.get("/{quote_id}", response_model=QuoteDetailResponse)
async def get_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    获取报价单详情
    
    返回完整的报价单信息，包括所有报价项
    """
    try:
        return await quote_service.get_quote_detail(db, quote_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取报价单详情失败: {str(e)}")


@router.put("/{quote_id}", response_model=QuoteDetailResponse)
async def update_quote(
    quote_id: UUID,
    request: QuoteUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    更新报价单
    
    只有草稿状态的报价单可以修改
    """
    try:
        return await quote_service.update_quote(db, quote_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新报价单失败: {str(e)}")


@router.delete("/{quote_id}", response_model=SuccessResponse)
async def delete_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    删除报价单
    
    采用软删除，将状态设置为deleted
    """
    try:
        await quote_service.delete_quote(db, quote_id)
        return SuccessResponse(message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除报价单失败: {str(e)}")


@router.post("/{quote_id}/items", response_model=QuoteItemResponse)
async def add_item_to_quote(
    quote_id: UUID,
    request: QuoteItemCreateRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    添加商品到报价单
    
    自动计算价格并更新总金额
    """
    try:
        return await quote_service.add_item(db, quote_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加商品失败: {str(e)}")


@router.put("/{quote_id}/items/{item_id}", response_model=QuoteItemResponse)
async def update_quote_item(
    quote_id: UUID,
    item_id: UUID,
    request: QuoteItemUpdateRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    更新报价项
    
    修改报价项的数量、tokens、折扣等信息，自动重新计算价格
    """
    try:
        return await quote_service.update_item(db, quote_id, item_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新报价项失败: {str(e)}")


@router.delete("/{quote_id}/items/{item_id}", response_model=SuccessResponse)
async def delete_quote_item(
    quote_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    删除报价项
    
    从报价单中移除商品，自动重新计算总金额
    """
    try:
        await quote_service.delete_item(db, quote_id, item_id)
        return SuccessResponse(message="删除成功")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除报价项失败: {str(e)}")


@router.post("/{quote_id}/items/batch", response_model=QuoteItemBatchResult)
async def add_items_batch(
    quote_id: UUID,
    request: QuoteItemBatchCreateRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    批量添加商品到报价单
    
    一次性添加多个商品，返回成功和失败的明细
    """
    try:
        return await quote_service.add_items_batch(db, quote_id, request.items)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量添加商品失败: {str(e)}")


@router.post("/{quote_id}/discount", response_model=QuoteDetailResponse)
async def apply_discount(
    quote_id: UUID,
    request: QuoteDiscountRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    应用全局折扣
    
    为报价单设置统一的折扣率，并重新计算所有报价项的价格
    """
    try:
        return await quote_service.apply_global_discount(
            db, quote_id, request.discount_rate, request.remark
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"应用折扣失败: {str(e)}")


@router.post("/{quote_id}/clone", response_model=QuoteDetailResponse)
async def clone_quote(
    quote_id: UUID,
    new_customer_name: Optional[str] = Query(None, description="新客户名称"),
    new_project_name: Optional[str] = Query(None, description="新项目名称"),
    db: AsyncSession = Depends(get_db)
):
    """
    克隆报价单
    
    复制现有报价单创建新的草稿
    """
    try:
        return await quote_service.clone_quote(
            db, quote_id, new_customer_name, new_project_name
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"克隆报价单失败: {str(e)}")


@router.get("/{quote_id}/versions", response_model=List[QuoteVersionResponse])
async def get_quote_versions(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    获取报价单版本历史
    
    查看报价单的所有历史版本记录
    """
    try:
        return await quote_service.get_quote_versions(db, quote_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取版本历史失败: {str(e)}")


@router.post("/{quote_id}/confirm", response_model=QuoteDetailResponse)
async def confirm_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    确认报价单
    
    将报价单状态从草稿变更为已确认
    """
    try:
        update_request = QuoteUpdateRequest(status="confirmed")
        return await quote_service.update_quote(db, quote_id, update_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"确认报价单失败: {str(e)}")


@router.post("/{quote_id}/cancel", response_model=QuoteDetailResponse)
async def cancel_quote(
    quote_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    取消报价单
    
    将报价单状态变更为已取消
    """
    try:
        update_request = QuoteUpdateRequest(status="cancelled")
        return await quote_service.update_quote(db, quote_id, update_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消报价单失败: {str(e)}")
