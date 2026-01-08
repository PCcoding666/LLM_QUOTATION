"""
报价单数据模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Index, Numeric, BigInteger, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class QuoteSheet(Base):
    """报价单主表"""
    __tablename__ = "quote_sheets"
    
    quote_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="报价单ID")
    quote_no = Column(String(50), unique=True, nullable=False, comment="报价单编号")
    customer_name = Column(String(255), nullable=False, comment="客户名称")
    project_name = Column(String(255), comment="项目名称")
    created_by = Column(String(100), nullable=False, comment="创建人ID或名称")
    sales_name = Column(String(100), comment="销售负责人姓名")
    customer_contact = Column(String(100), comment="客户联系人")
    customer_email = Column(String(255), comment="客户邮箱")
    status = Column(String(50), nullable=False, default="draft", comment="状态")
    remarks = Column(Text, comment="备注信息")
    terms = Column(Text, comment="条款说明")
    global_discount_rate = Column(Numeric(5, 4), nullable=False, default=1.0000, comment="全局折扣率")
    global_discount_remark = Column(String(255), comment="折扣备注说明")
    total_amount = Column(Numeric(20, 6), comment="报价总金额(折后)")
    total_original_amount = Column(Numeric(20, 6), comment="报价总金额(折前)")
    currency = Column(String(10), default="CNY", comment="币种")
    valid_until = Column(DateTime(timezone=True), comment="报价有效期")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index('ix_quote_no', 'quote_no'),
        Index('ix_quote_customer', 'customer_name'),
        Index('ix_quote_created_by', 'created_by'),
        Index('ix_quote_created_at', 'created_at'),
        Index('ix_quote_status', 'status'),
        {'comment': '报价单主表'}
    )


class QuoteItem(Base):
    """报价明细表"""
    __tablename__ = "quote_items"
    
    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="明细ID")
    quote_id = Column(UUID(as_uuid=True), ForeignKey('quote_sheets.quote_id', ondelete='CASCADE'), nullable=False, comment="所属报价单")
    product_code = Column(String(100), nullable=False, comment="产品代码")
    product_name = Column(String(255), nullable=False, comment="产品名称")
    region = Column(String(50), nullable=False, default="cn-beijing", comment="地域代码")
    region_name = Column(String(100), comment="地域显示名称")
    modality = Column(String(50), nullable=False, comment="模态类型")
    capability = Column(String(50), comment="能力类型")
    model_type = Column(String(50), comment="模型类型")
    context_spec = Column(String(50), comment="context规格")
    input_tokens = Column(BigInteger, comment="预估输入tokens数量")
    output_tokens = Column(BigInteger, comment="预估输出tokens数量")
    inference_mode = Column(String(50), comment="推理方式")
    spec_config = Column(JSONB, comment="规格配置")
    quantity = Column(Integer, nullable=False, default=1, comment="数量")
    duration_months = Column(Integer, default=1, comment="时长(月)")
    usage_estimation = Column(JSONB, comment="用量估算")
    unit_price = Column(Numeric(20, 6), comment="单价")
    original_price = Column(Numeric(20, 6), nullable=False, comment="原价(元)")
    discount_rate = Column(Numeric(5, 4), nullable=False, default=1.0000, comment="单项折扣率")
    final_price = Column(Numeric(20, 6), nullable=False, comment="折后价(元)")
    billing_unit = Column(String(50), nullable=False, comment="计费单位")
    subtotal = Column(Numeric(20, 6), comment="小计")
    discount_info = Column(JSONB, comment="折扣信息")
    sort_order = Column(Integer, nullable=False, default=0, comment="排序顺序")
    
    __table_args__ = (
        Index('ix_item_quote', 'quote_id'),
        Index('ix_item_sort_order', 'quote_id', 'sort_order'),
        {'comment': '报价明细表'}
    )


class QuoteDiscount(Base):
    """折扣记录表"""
    __tablename__ = "quote_discounts"
    
    discount_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="折扣ID")
    quote_id = Column(UUID(as_uuid=True), ForeignKey('quote_sheets.quote_id', ondelete='CASCADE'), nullable=False, comment="所属报价单")
    discount_type = Column(String(50), comment="折扣类型")
    discount_value = Column(String(20), comment="折扣值")
    apply_reason = Column(String(255), comment="应用原因")
    
    __table_args__ = (
        Index('ix_discount_quote', 'quote_id'),
        {'comment': '折扣记录表'}
    )


class QuoteVersion(Base):
    """版本快照表"""
    __tablename__ = "quote_versions"
    
    version_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="版本ID")
    quote_id = Column(UUID(as_uuid=True), ForeignKey('quote_sheets.quote_id', ondelete='CASCADE'), nullable=False, comment="所属报价单")
    version_number = Column(Integer, nullable=False, comment="版本号")
    change_type = Column(String(50), comment="变更类型")
    changes_summary = Column(String(500), comment="变更摘要")
    snapshot_data = Column(JSONB, comment="快照数据")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    
    __table_args__ = (
        Index('ix_version_quote', 'quote_id'),
        Index('ix_version_number', 'quote_id', 'version_number'),
        {'comment': '版本快照表'}
    )
