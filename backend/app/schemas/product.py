"""
产品相关的Pydantic模式
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class ProductBase(BaseModel):
    """产品基础模式"""
    product_code: str = Field(..., description="产品代码")
    product_name: str = Field(..., description="产品名称")
    category: str = Field(..., description="产品类别")
    vendor: str = Field(default="aliyun", description="厂商")
    description: Optional[str] = Field(None, description="产品描述")


class ProductResponse(ProductBase):
    """产品响应模式"""
    status: str = Field(..., description="状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class PaginatedProductListResponse(BaseModel):
    """分页产品列表响应"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    data: List[ProductResponse] = Field(..., description="数据列表")


class ProductPriceResponse(BaseModel):
    """产品价格响应模式"""
    price_id: str = Field(..., description="价格ID")
    product_code: str = Field(..., description="产品代码")
    region: str = Field(..., description="地域")
    spec_type: Optional[str] = Field(None, description="规格类型")
    billing_mode: str = Field(..., description="计费模式")
    unit_price: float = Field(..., description="单价")
    unit: str = Field(..., description="单位")
    pricing_variables: Optional[Dict[str, Any]] = Field(None, description="定价变量")
    effective_date: datetime = Field(..., description="生效日期")
    
    class Config:
        from_attributes = True
