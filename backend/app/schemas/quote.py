"""
报价单相关的Pydantic模式
"""
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict


# ===== 枚举值定义 =====
class QuoteStatus:
    """报价单状态"""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Modality:
    """模态类型"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MULTIMODAL = "multimodal"


class Capability:
    """能力类型"""
    UNDERSTANDING = "understanding"
    GENERATION = "generation"
    BOTH = "both"


class ModelType:
    """模型类型"""
    LLM = "llm"
    TEXT_EMBEDDING = "text_embedding"
    MULTIMODAL_EMBEDDING = "multimodal_embedding"
    RERANK = "rerank"


class InferenceMode:
    """推理方式"""
    THINKING = "thinking"
    NON_THINKING = "non_thinking"


# ===== 请求 Schema =====
class QuoteCreateRequest(BaseModel):
    """创建报价单请求"""
    customer_name: str = Field(..., min_length=1, max_length=255, description="客户名称")
    project_name: Optional[str] = Field(None, max_length=255, description="项目名称")
    created_by: str = Field(..., min_length=1, description="创建人")
    sales_name: Optional[str] = Field(None, max_length=100, description="销售负责人")
    customer_contact: Optional[str] = Field(None, max_length=100, description="客户联系人")
    customer_email: Optional[EmailStr] = Field(None, description="客户邮箱")
    remarks: Optional[str] = Field(None, description="备注信息")
    valid_days: int = Field(default=30, ge=1, description="有效期天数")


class QuoteUpdateRequest(BaseModel):
    """更新报价单请求"""
    customer_name: Optional[str] = Field(None, max_length=255, description="客户名称")
    project_name: Optional[str] = Field(None, max_length=255, description="项目名称")
    sales_name: Optional[str] = Field(None, max_length=100, description="销售负责人")
    customer_contact: Optional[str] = Field(None, max_length=100, description="客户联系人")
    customer_email: Optional[EmailStr] = Field(None, description="客户邮箱")
    remarks: Optional[str] = Field(None, description="备注信息")
    terms: Optional[str] = Field(None, description="条款说明")
    status: Optional[str] = Field(None, description="状态")

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = [QuoteStatus.DRAFT, QuoteStatus.CONFIRMED, QuoteStatus.EXPIRED, QuoteStatus.CANCELLED]
            if v not in valid_statuses:
                raise ValueError(f"状态必须是以下之一: {', '.join(valid_statuses)}")
        return v


class QuoteItemCreateRequest(BaseModel):
    """添加商品到报价单请求"""
    product_code: str = Field(..., description="产品代码")
    region: str = Field(default="cn-beijing", description="地域代码")
    quantity: int = Field(default=1, ge=1, description="数量")
    input_tokens: Optional[int] = Field(None, ge=0, description="预估输入tokens")
    output_tokens: Optional[int] = Field(None, ge=0, description="预估输出tokens")
    inference_mode: Optional[str] = Field(None, description="推理模式")
    duration_months: int = Field(default=1, ge=1, description="时长（月）")

    @field_validator('inference_mode')
    @classmethod
    def validate_inference_mode(cls, v):
        if v is not None:
            valid_modes = [InferenceMode.THINKING, InferenceMode.NON_THINKING]
            if v not in valid_modes:
                raise ValueError(f"推理模式必须是以下之一: {', '.join(valid_modes)}")
        return v


class QuoteItemUpdateRequest(BaseModel):
    """更新报价项请求"""
    quantity: Optional[int] = Field(None, ge=1, description="数量")
    input_tokens: Optional[int] = Field(None, ge=0, description="预估输入tokens")
    output_tokens: Optional[int] = Field(None, ge=0, description="预估输出tokens")
    inference_mode: Optional[str] = Field(None, description="推理模式")
    discount_rate: Optional[Decimal] = Field(None, ge=0.01, le=1.0, description="折扣率")


class QuoteItemBatchCreateRequest(BaseModel):
    """批量添加商品请求"""
    items: List[QuoteItemCreateRequest] = Field(..., min_length=1, max_length=100, description="商品列表")


class QuoteDiscountRequest(BaseModel):
    """设置折扣请求"""
    discount_rate: Decimal = Field(..., ge=0.01, le=1.0, description="折扣率")
    remark: Optional[str] = Field(None, max_length=255, description="折扣备注")


class ProductSearchRequest(BaseModel):
    """批量名称搜索请求"""
    names: List[str] = Field(..., min_length=1, max_length=50, description="模型名称列表")
    region: str = Field(default="cn-beijing", description="地域")


# ===== 响应 Schema =====
class QuoteItemResponse(BaseModel):
    """报价项响应"""
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
    
    item_id: UUID = Field(..., description="明细ID")
    product_code: str = Field(..., description="产品代码")
    product_name: str = Field(..., description="产品名称")
    region: str = Field(..., description="地域代码")
    region_name: Optional[str] = Field(None, description="地域显示名称")
    modality: str = Field(..., description="模态类型")
    capability: Optional[str] = Field(None, description="能力类型")
    model_type: Optional[str] = Field(None, description="模型类型")
    context_spec: Optional[str] = Field(None, description="context规格")
    input_tokens: Optional[int] = Field(None, description="预估输入tokens")
    output_tokens: Optional[int] = Field(None, description="预估输出tokens")
    inference_mode: Optional[str] = Field(None, description="推理方式")
    quantity: int = Field(..., description="数量")
    duration_months: int = Field(..., description="时长（月）")
    original_price: Decimal = Field(..., description="原价（元）")
    discount_rate: Decimal = Field(..., description="单项折扣率")
    final_price: Decimal = Field(..., description="折后价（元）")
    billing_unit: str = Field(..., description="计费单位")
    sort_order: int = Field(..., description="排序顺序")


class QuoteDetailResponse(BaseModel):
    """报价单详情响应"""
    quote_id: UUID = Field(..., description="报价单ID")
    quote_no: str = Field(..., description="报价单编号")
    customer_name: str = Field(..., description="客户名称")
    project_name: Optional[str] = Field(None, description="项目名称")
    created_by: str = Field(..., description="创建人")
    sales_name: Optional[str] = Field(None, description="销售负责人")
    customer_contact: Optional[str] = Field(None, description="客户联系人")
    customer_email: Optional[str] = Field(None, description="客户邮箱")
    status: str = Field(..., description="状态")
    remarks: Optional[str] = Field(None, description="备注信息")
    terms: Optional[str] = Field(None, description="条款说明")
    global_discount_rate: Decimal = Field(..., description="全局折扣率")
    global_discount_remark: Optional[str] = Field(None, description="折扣备注说明")
    total_original_amount: Optional[Decimal] = Field(None, description="总原价")
    total_final_amount: Optional[Decimal] = Field(None, description="总最终价格")
    currency: str = Field(..., description="币种")
    valid_until: Optional[datetime] = Field(None, description="有效期")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    items: List[QuoteItemResponse] = Field(default_factory=list, description="报价项列表")
    version: int = Field(default=1, description="版本号")

    class Config:
        from_attributes = True


class QuoteListResponse(BaseModel):
    """报价单列表项响应"""
    quote_id: UUID = Field(..., description="报价单ID")
    quote_no: str = Field(..., description="报价单编号")
    customer_name: str = Field(..., description="客户名称")
    project_name: Optional[str] = Field(None, description="项目名称")
    status: str = Field(..., description="状态")
    total_amount: Optional[Decimal] = Field(None, description="总最终价格")
    created_by: str = Field(..., description="创建人")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class PaginatedQuoteListResponse(BaseModel):
    """分页报价单列表响应"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    data: List[QuoteListResponse] = Field(..., description="数据列表")


class QuoteItemBatchResult(BaseModel):
    """批量添加商品结果"""
    success_count: int = Field(..., description="成功数量")
    failed_count: int = Field(default=0, description="失败数量")
    success_items: List[QuoteItemResponse] = Field(default_factory=list, description="成功项列表")
    failed_items: List[dict] = Field(default_factory=list, description="失败项列表")


class QuoteVersionResponse(BaseModel):
    """版本历史响应"""
    version_id: UUID = Field(..., description="版本ID")
    version_number: int = Field(..., description="版本号")
    change_type: Optional[str] = Field(None, description="变更类型")
    changes_summary: Optional[str] = Field(None, description="变更摘要")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


# ===== 商品筛选相关 Schema =====
class FilterOption(BaseModel):
    """筛选选项"""
    code: str = Field(..., description="代码")
    name: str = Field(..., description="显示名称")


class FilterOptionsResponse(BaseModel):
    """筛选条件选项响应"""
    model_config = ConfigDict(protected_namespaces=())
    
    regions: List[FilterOption] = Field(..., description="地域列表")
    modalities: List[FilterOption] = Field(..., description="模态列表")
    capabilities: List[FilterOption] = Field(..., description="能力列表")
    model_types: List[FilterOption] = Field(..., description="模型类型列表")


class ModelPricing(BaseModel):
    """模型价格信息"""
    region: str = Field(..., description="地域")
    input_price: Optional[Decimal] = Field(None, description="输入价格")
    output_price: Optional[Decimal] = Field(None, description="输出价格")
    unit: Optional[str] = Field(None, description="计费单位")


class ModelListItem(BaseModel):
    """模型列表项"""
    model_config = ConfigDict(protected_namespaces=())
    
    model_id: str = Field(..., description="模型ID")
    model_name: str = Field(..., description="模型名称")
    vendor: str = Field(..., description="厂商")
    category: str = Field(..., description="类别")
    modality: str = Field(..., description="模态类型")
    capability: Optional[str] = Field(None, description="能力类型")
    context_specs: List[str] = Field(default_factory=list, description="context规格列表")
    supports_thinking: bool = Field(default=False, description="是否支持思考模式")
    pricing: Optional[ModelPricing] = Field(None, description="价格信息")
    status: str = Field(..., description="状态")


class PaginatedModelListResponse(BaseModel):
    """分页模型列表响应"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    data: List[ModelListItem] = Field(..., description="数据列表")


class ModelSpecs(BaseModel):
    """模型规格"""
    max_context_length: Optional[int] = Field(None, description="最大上下文长度")
    max_input_tokens: Optional[int] = Field(None, description="最大输入tokens")
    max_output_tokens: Optional[int] = Field(None, description="最大输出tokens")
    supports_thinking: bool = Field(default=False, description="是否支持思考模式")


class ModelPricingDetail(BaseModel):
    """模型详细价格信息"""
    region: str = Field(..., description="地域")
    region_name: str = Field(..., description="地域名称")
    input_price: Optional[Decimal] = Field(None, description="输入价格")
    output_price: Optional[Decimal] = Field(None, description="输出价格")
    thinking_input_price: Optional[Decimal] = Field(None, description="思考模式输入价格")
    thinking_output_price: Optional[Decimal] = Field(None, description="思考模式输出价格")
    batch_discount: Optional[Decimal] = Field(None, description="批量折扣")
    unit: Optional[str] = Field(None, description="计费单位")


class ModelDetailResponse(BaseModel):
    """模型详情响应"""
    model_config = ConfigDict(protected_namespaces=())
    
    model_id: str = Field(..., description="模型ID")
    model_name: str = Field(..., description="模型名称")
    vendor: str = Field(..., description="厂商")
    description: Optional[str] = Field(None, description="描述")
    category: str = Field(..., description="类别")
    specs: Optional[ModelSpecs] = Field(None, description="规格")
    pricing: List[ModelPricingDetail] = Field(default_factory=list, description="价格列表")
    status: str = Field(..., description="状态")


class ProductSearchResultItem(BaseModel):
    """搜索结果项"""
    model_config = ConfigDict(protected_namespaces=())
    
    model_id: str = Field(..., description="模型ID")
    model_name: str = Field(..., description="模型名称")
    match_type: str = Field(..., description="匹配类型")
    search_term: str = Field(..., description="搜索词")


class ProductSearchResponse(BaseModel):
    """批量搜索响应"""
    found: List[ProductSearchResultItem] = Field(..., description="找到的模型")
    not_found: List[str] = Field(..., description="未找到的名称")


# ===== 通用响应 =====
class SuccessResponse(BaseModel):
    """成功响应"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(default="操作成功", description="消息")


class ErrorResponse(BaseModel):
    """错误响应"""
    error_code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: Optional[dict] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")
