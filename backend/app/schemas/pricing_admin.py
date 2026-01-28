"""
定价管理 Schema 定义
用于模型规格与价格的 CRUD 操作
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


# ===== 请求 Schema =====

class PricingModelCreateRequest(BaseModel):
    """创建模型请求"""
    category_id: int = Field(..., description="分类ID")
    model_code: str = Field(..., max_length=100, description="模型代码")
    model_name: str = Field(..., max_length=200, description="模型名称")
    display_name: str = Field(..., max_length=200, description="显示名称")
    mode: Optional[str] = Field(None, max_length=50, description="模式")
    token_tier: Optional[str] = Field(None, max_length=50, description="Token阶梯")
    resolution: Optional[str] = Field(None, max_length=20, description="分辨率")
    supports_batch: bool = Field(False, description="支持Batch半价")
    supports_cache: bool = Field(False, description="支持上下文缓存")
    remark: Optional[str] = Field(None, description="备注")


class PricingModelUpdateRequest(BaseModel):
    """更新模型请求（所有字段可选）"""
    category_id: Optional[int] = Field(None, description="分类ID")
    model_name: Optional[str] = Field(None, max_length=200, description="模型名称")
    display_name: Optional[str] = Field(None, max_length=200, description="显示名称")
    mode: Optional[str] = Field(None, max_length=50, description="模式")
    token_tier: Optional[str] = Field(None, max_length=50, description="Token阶梯")
    resolution: Optional[str] = Field(None, max_length=20, description="分辨率")
    supports_batch: Optional[bool] = Field(None, description="支持Batch半价")
    supports_cache: Optional[bool] = Field(None, description="支持上下文缓存")
    remark: Optional[str] = Field(None, description="备注")
    status: Optional[str] = Field(None, max_length=20, description="状态")


class PricingModelPriceCreateRequest(BaseModel):
    """添加价格维度请求"""
    dimension_code: str = Field(..., max_length=50, description="维度代码")
    unit_price: Decimal = Field(..., ge=0, description="单价")
    unit: str = Field(..., max_length=50, description="单位")
    currency: str = Field(default="CNY", max_length=10, description="货币")
    mode: Optional[str] = Field(None, max_length=50, description="模式")
    token_tier: Optional[str] = Field(None, max_length=50, description="Token阶梯")
    resolution: Optional[str] = Field(None, max_length=20, description="分辨率")


class PricingModelPriceUpdateRequest(BaseModel):
    """更新价格请求"""
    unit_price: Optional[Decimal] = Field(None, ge=0, description="单价")
    unit: Optional[str] = Field(None, max_length=50, description="单位")
    currency: Optional[str] = Field(None, max_length=10, description="货币")
    mode: Optional[str] = Field(None, max_length=50, description="模式")
    token_tier: Optional[str] = Field(None, max_length=50, description="Token阶梯")
    resolution: Optional[str] = Field(None, max_length=20, description="分辨率")


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""
    model_ids: List[int] = Field(..., min_length=1, description="模型ID列表")


# ===== 响应 Schema =====

class PricingModelPriceResponse(BaseModel):
    """价格维度响应"""
    id: int = Field(..., description="价格ID")
    model_id: int = Field(..., description="模型ID")
    dimension_code: str = Field(..., description="维度代码")
    unit_price: float = Field(..., description="单价")
    unit: str = Field(..., description="单位")
    currency: str = Field(..., description="货币")
    mode: Optional[str] = Field(None, description="模式")
    token_tier: Optional[str] = Field(None, description="Token阶梯")
    resolution: Optional[str] = Field(None, description="分辨率")
    created_at: Optional[datetime] = Field(None, description="创建时间")

    class Config:
        from_attributes = True


class PricingModelAdminResponse(BaseModel):
    """管理端模型响应（包含完整信息）"""
    id: int = Field(..., description="模型ID")
    snapshot_id: Optional[int] = Field(None, description="快照ID")
    category_id: Optional[int] = Field(None, description="分类ID")
    category_name: Optional[str] = Field(None, description="分类名称")
    model_code: Optional[str] = Field(None, description="模型代码")
    model_name: str = Field(..., description="模型名称")
    display_name: str = Field(..., description="显示名称")
    mode: Optional[str] = Field(None, description="模式")
    token_tier: Optional[str] = Field(None, description="Token阶梯")
    resolution: Optional[str] = Field(None, description="分辨率")
    supports_batch: bool = Field(False, description="支持Batch半价")
    supports_cache: bool = Field(False, description="支持上下文缓存")
    remark: Optional[str] = Field(None, description="备注")
    status: str = Field(..., description="状态")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    prices: List[PricingModelPriceResponse] = Field(default_factory=list, description="价格列表")

    class Config:
        from_attributes = True


class PaginatedPricingModelResponse(BaseModel):
    """分页模型列表响应"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    data: List[PricingModelAdminResponse] = Field(..., description="数据列表")


class CategoryResponse(BaseModel):
    """分类响应"""
    id: int = Field(..., description="分类ID")
    code: str = Field(..., description="分类代码")
    name: str = Field(..., description="分类名称")
    parent_code: Optional[str] = Field(None, description="父分类代码")
    sort_order: int = Field(0, description="排序")
    is_active: bool = Field(True, description="是否激活")

    class Config:
        from_attributes = True


class OperationResponse(BaseModel):
    """操作结果响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
    affected_count: Optional[int] = Field(None, description="影响的记录数")
