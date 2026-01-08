"""
产品数据模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

from app.core.database import Base


class Product(Base):
    """产品主表"""
    __tablename__ = "products"
    
    product_code = Column(String(100), primary_key=True, comment="产品代码")
    product_name = Column(String(255), nullable=False, comment="产品名称")
    category = Column(String(100), nullable=False, index=True, comment="产品类别")
    vendor = Column(String(50), nullable=False, default="aliyun", comment="厂商")
    status = Column(String(50), default="active", comment="状态")
    description = Column(Text, comment="产品描述")
    # 向量字段：有pgvector时使用Vector类型，否则使用Text
    if HAS_PGVECTOR:
        description_vector = Column(Vector(1536), comment="描述向量")
    else:
        description_vector = Column(Text, comment="描述向量(文本存储)")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index('ix_product_category_vendor', 'category', 'vendor'),
        {'comment': '产品主表'}
    )


class ProductPrice(Base):
    """产品价格表"""
    __tablename__ = "product_prices"
    
    price_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="价格记录ID")
    product_code = Column(String(100), nullable=False, index=True, comment="产品代码")
    region = Column(String(50), nullable=False, comment="地域")
    spec_type = Column(String(100), comment="规格类型")
    billing_mode = Column(String(50), nullable=False, comment="计费模式")
    unit_price = Column(String(20), nullable=False, comment="单价")
    unit = Column(String(50), comment="单位")
    pricing_variables = Column(JSONB, comment="定价变量")
    effective_date = Column(DateTime(timezone=True), nullable=False, comment="生效日期")
    expire_date = Column(DateTime(timezone=True), comment="失效日期")
    
    __table_args__ = (
        Index('ix_price_product_region', 'product_code', 'region'),
        {'comment': '产品价格表'}
    )


class ProductSpec(Base):
    """产品规格配置表"""
    __tablename__ = "product_specs"
    
    spec_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="规格ID")
    product_code = Column(String(100), nullable=False, index=True, comment="产品代码")
    spec_name = Column(String(100), nullable=False, comment="规格名称")
    spec_values = Column(JSONB, comment="规格值")
    constraints = Column(JSONB, comment="约束条件")
    
    __table_args__ = (
        {'comment': '产品规格配置表'}
    )


class CompetitorMapping(Base):
    """竞品映射表"""
    __tablename__ = "competitor_mappings"
    
    mapping_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="映射ID")
    ali_product_code = Column(String(100), nullable=False, index=True, comment="阿里云产品代码")
    competitor_name = Column(String(50), nullable=False, comment="竞品厂商")
    comp_product_code = Column(String(100), nullable=False, comment="竞品产品代码")
    mapping_type = Column(String(50), comment="映射类型")
    confidence_score = Column(String(5), comment="映射置信度")
    created_by = Column(String(50), comment="创建方式")
    
    __table_args__ = (
        Index('ix_mapping_ali_competitor', 'ali_product_code', 'competitor_name'),
        {'comment': '竞品映射表'}
    )
