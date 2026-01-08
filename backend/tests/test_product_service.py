"""
产品数据服务测试
"""
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.models.product import Product, ProductPrice


class TestProductService:
    """产品数据服务测试"""
    
    @pytest.mark.asyncio
    async def test_create_product(self, db_session):
        """测试创建产品"""
        product = Product(
            product_code="test-product-001",
            product_name="测试产品",
            category="AI-大模型",
            vendor="aliyun",
            description="这是一个测试产品",
            status="active"
        )
        
        db_session.add(product)
        await db_session.flush()
        
        assert product.product_code == "test-product-001"
        assert product.product_name == "测试产品"
    
    @pytest.mark.asyncio
    async def test_create_product_price(self, db_session):
        """测试创建产品价格"""
        # 先创建产品
        product = Product(
            product_code="test-product-002",
            product_name="测试产品2",
            category="AI-大模型",
            vendor="aliyun"
        )
        db_session.add(product)
        
        # 创建价格
        price = ProductPrice(
            product_code="test-product-002",
            region="cn-hangzhou",
            spec_type="standard",
            billing_mode="pay-as-you-go",
            unit_price="10.50",
            unit="hour",
            pricing_variables={"token_based": False},
            effective_date=datetime.now() - timedelta(days=1)
        )
        db_session.add(price)
        
        await db_session.flush()
        
        assert price.product_code == "test-product-002"
        assert float(price.unit_price) == 10.50
    
    @pytest.mark.asyncio
    async def test_query_product(self, db_session):
        """测试查询产品"""
        # 创建测试数据
        product = Product(
            product_code="test-query-001",
            product_name="查询测试产品",
            category="计算-GPU实例",
            vendor="aliyun"
        )
        db_session.add(product)
        await db_session.flush()
        
        # 查询产品
        result = await db_session.get(Product, "test-query-001")
        
        assert result is not None
        assert result.product_name == "查询测试产品"
        assert result.category == "计算-GPU实例"
