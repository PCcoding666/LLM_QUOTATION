"""
CRUD 操作单元测试
测试产品和报价单的增删改查功能
"""
import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductPrice, ProductSpec, CompetitorMapping
from app.models.quote import QuoteSheet, QuoteItem, QuoteDiscount, QuoteVersion
from app.crud.product import ProductCRUD, product_crud
from app.crud.quote import QuoteCRUD, quote_crud


class TestProductCRUD:
    """产品 CRUD 测试"""
    
    @pytest.mark.asyncio
    async def test_create_product(self, db_session: AsyncSession):
        """测试创建产品"""
        product = Product(
            product_code="test-product-001",
            product_name="测试产品",
            category="大模型",
            vendor="aliyun",
            status="active",
            description="这是一个测试产品"
        )
        
        created_product = await ProductCRUD.create_product(db_session, product)
        
        assert created_product.product_code == "test-product-001"
        assert created_product.product_name == "测试产品"
        assert created_product.category == "大模型"
        assert created_product.vendor == "aliyun"
        assert created_product.status == "active"
    
    @pytest.mark.asyncio
    async def test_get_product(self, db_session: AsyncSession):
        """测试获取产品详情"""
        # 先创建产品
        product = Product(
            product_code="test-product-002",
            product_name="测试产品2",
            category="大模型",
            vendor="aliyun",
            status="active"
        )
        await ProductCRUD.create_product(db_session, product)
        
        # 获取产品
        fetched_product = await ProductCRUD.get_product(db_session, "test-product-002")
        
        assert fetched_product is not None
        assert fetched_product.product_code == "test-product-002"
        assert fetched_product.product_name == "测试产品2"
    
    @pytest.mark.asyncio
    async def test_get_product_not_found(self, db_session: AsyncSession):
        """测试获取不存在的产品"""
        product = await ProductCRUD.get_product(db_session, "non-existent-product")
        assert product is None
    
    @pytest.mark.asyncio
    async def test_get_products_list(self, db_session: AsyncSession):
        """测试获取产品列表"""
        # 创建多个产品
        for i in range(5):
            product = Product(
                product_code=f"test-list-product-{i}",
                product_name=f"列表测试产品{i}",
                category="大模型" if i < 3 else "向量检索",
                vendor="aliyun",
                status="active"
            )
            db_session.add(product)
        await db_session.commit()
        
        # 获取全部产品
        products = await ProductCRUD.get_products(db_session, limit=10)
        assert len(products) >= 5
        
        # 按类别过滤
        llm_products = await ProductCRUD.get_products(db_session, category="大模型")
        assert len(llm_products) >= 3
    
    @pytest.mark.asyncio
    async def test_get_products_with_keyword(self, db_session: AsyncSession):
        """测试关键字搜索产品"""
        product = Product(
            product_code="search-test-product",
            product_name="特殊搜索产品",
            category="大模型",
            vendor="aliyun",
            status="active",
            description="这是一个用于搜索测试的产品描述"
        )
        await ProductCRUD.create_product(db_session, product)
        
        # 按名称搜索
        products = await ProductCRUD.get_products(db_session, keyword="特殊搜索")
        assert len(products) >= 1
        assert any(p.product_code == "search-test-product" for p in products)
    
    @pytest.mark.asyncio
    async def test_update_product(self, db_session: AsyncSession):
        """测试更新产品"""
        # 创建产品
        product = Product(
            product_code="update-test-product",
            product_name="待更新产品",
            category="大模型",
            vendor="aliyun",
            status="active"
        )
        await ProductCRUD.create_product(db_session, product)
        
        # 更新产品
        updated = await ProductCRUD.update_product(
            db_session,
            "update-test-product",
            {"product_name": "已更新产品", "description": "新描述"}
        )
        
        assert updated is not None
        assert updated.product_name == "已更新产品"
        assert updated.description == "新描述"
    
    @pytest.mark.asyncio
    async def test_create_product_price(self, db_session: AsyncSession):
        """测试创建产品价格"""
        # 先创建产品
        product = Product(
            product_code="price-test-product",
            product_name="价格测试产品",
            category="大模型",
            vendor="aliyun",
            status="active"
        )
        db_session.add(product)
        await db_session.commit()
        
        # 创建价格
        price = ProductPrice(
            product_code="price-test-product",
            region="cn-beijing",
            billing_mode="按量付费",
            unit_price="0.0008",
            unit="千Token",
            effective_date=datetime.now()
        )
        db_session.add(price)
        await db_session.commit()
        
        # 获取价格
        fetched_price = await ProductCRUD.get_product_price(
            db_session, 
            "price-test-product",
            region="cn-beijing"
        )
        
        assert fetched_price is not None
        assert fetched_price.unit_price == "0.0008"


class TestQuoteCRUD:
    """报价单 CRUD 测试"""
    
    @pytest.mark.asyncio
    async def test_create_quote(self, db_session: AsyncSession):
        """测试创建报价单"""
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}001",
            customer_name="测试客户",
            project_name="测试项目",
            created_by="test_user",
            status="draft",
            currency="CNY"
        )
        
        created_quote = await QuoteCRUD.create_quote(db_session, quote)
        
        assert created_quote.quote_id is not None
        assert created_quote.customer_name == "测试客户"
        assert created_quote.status == "draft"
        
        # 验证初始版本创建
        version = await QuoteCRUD.get_latest_version(db_session, str(created_quote.quote_id))
        assert version is not None
        assert version.version_number == 1
    
    @pytest.mark.asyncio
    async def test_get_quote(self, db_session: AsyncSession):
        """测试获取报价单详情"""
        # 创建报价单
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}002",
            customer_name="获取测试客户",
            project_name="获取测试项目",
            created_by="test_user",
            status="draft"
        )
        created = await QuoteCRUD.create_quote(db_session, quote)
        
        # 获取报价单
        fetched = await QuoteCRUD.get_quote(db_session, str(created.quote_id))
        
        assert fetched is not None
        assert fetched.customer_name == "获取测试客户"
    
    @pytest.mark.asyncio
    async def test_get_quotes_list(self, db_session: AsyncSession):
        """测试获取报价单列表"""
        # 创建多个报价单
        for i in range(3):
            quote = QuoteSheet(
                quote_no=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}{i:03d}",
                customer_name=f"列表客户{i}",
                project_name=f"列表项目{i}",
                created_by="test_user",
                status="draft" if i < 2 else "submitted"
            )
            await QuoteCRUD.create_quote(db_session, quote)
        
        # 获取全部
        all_quotes = await QuoteCRUD.get_quotes(db_session, limit=10)
        assert len(all_quotes) >= 3
        
        # 按状态过滤
        draft_quotes = await QuoteCRUD.get_quotes(db_session, status="draft")
        assert len(draft_quotes) >= 2
    
    @pytest.mark.asyncio
    async def test_update_quote(self, db_session: AsyncSession):
        """测试更新报价单"""
        # 创建报价单
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}UPD",
            customer_name="待更新客户",
            project_name="待更新项目",
            created_by="test_user",
            status="draft"
        )
        created = await QuoteCRUD.create_quote(db_session, quote)
        
        # 更新报价单
        updated = await QuoteCRUD.update_quote(
            db_session,
            str(created.quote_id),
            {"customer_name": "已更新客户", "status": "submitted"}
        )
        
        assert updated is not None
        assert updated.customer_name == "已更新客户"
        assert updated.status == "submitted"
        
        # 验证版本记录
        version = await QuoteCRUD.get_latest_version(db_session, str(created.quote_id))
        assert version.version_number == 2
    
    @pytest.mark.asyncio
    async def test_delete_quote(self, db_session: AsyncSession):
        """测试删除报价单"""
        # 创建报价单
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}DEL",
            customer_name="待删除客户",
            project_name="待删除项目",
            created_by="test_user",
            status="draft"
        )
        created = await QuoteCRUD.create_quote(db_session, quote)
        quote_id = str(created.quote_id)
        
        # 删除报价单
        result = await QuoteCRUD.delete_quote(db_session, quote_id)
        assert result is True
        
        # 验证已删除
        deleted = await QuoteCRUD.get_quote(db_session, quote_id)
        assert deleted is None
    
    @pytest.mark.asyncio
    async def test_add_quote_item(self, db_session: AsyncSession):
        """测试添加报价项"""
        # 创建报价单
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}ITM",
            customer_name="报价项测试客户",
            project_name="报价项测试项目",
            created_by="test_user",
            status="draft"
        )
        created = await QuoteCRUD.create_quote(db_session, quote)
        
        # 添加报价项
        item = QuoteItem(
            quote_id=created.quote_id,
            product_code="qwen-max",
            product_name="通义千问Max",
            region="cn-beijing",
            modality="文本生成",
            original_price=Decimal("100.00"),
            final_price=Decimal("80.00"),
            discount_rate=Decimal("0.8000"),
            billing_unit="千Token",
            quantity=1
        )
        created_item = await QuoteCRUD.add_quote_item(db_session, item)
        
        assert created_item.item_id is not None
        assert created_item.product_name == "通义千问Max"
        
        # 获取报价项列表
        items = await QuoteCRUD.get_quote_items(db_session, str(created.quote_id))
        assert len(items) == 1
    
    @pytest.mark.asyncio
    async def test_clone_quote(self, db_session: AsyncSession):
        """测试克隆报价单"""
        # 创建原始报价单
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}CLN",
            customer_name="克隆测试客户",
            project_name="克隆测试项目",
            created_by="test_user",
            status="submitted",
            currency="CNY"
        )
        created = await QuoteCRUD.create_quote(db_session, quote)
        
        # 添加报价项
        item = QuoteItem(
            quote_id=created.quote_id,
            product_code="qwen-max",
            product_name="通义千问Max",
            region="cn-beijing",
            modality="文本生成",
            original_price=Decimal("100.00"),
            final_price=Decimal("80.00"),
            discount_rate=Decimal("0.8000"),
            billing_unit="千Token",
            quantity=1
        )
        await QuoteCRUD.add_quote_item(db_session, item)
        
        # 克隆报价单
        cloned = await QuoteCRUD.clone_quote(db_session, str(created.quote_id))
        
        assert cloned is not None
        assert cloned.quote_id != created.quote_id
        assert cloned.customer_name == "克隆测试客户"
        assert "(副本)" in cloned.project_name
        assert cloned.status == "draft"  # 克隆后状态应为草稿
        
        # 验证报价项也被复制
        cloned_items = await QuoteCRUD.get_quote_items(db_session, str(cloned.quote_id))
        assert len(cloned_items) == 1


class TestDataIntegrity:
    """数据完整性测试"""
    
    @pytest.mark.asyncio
    async def test_quote_item_cascade_delete(self, db_session: AsyncSession):
        """测试报价单删除时报价项级联删除"""
        # 创建报价单
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d%H%M%S')}CAS",
            customer_name="级联删除测试",
            project_name="级联删除项目",
            created_by="test_user",
            status="draft"
        )
        created = await QuoteCRUD.create_quote(db_session, quote)
        quote_id = str(created.quote_id)
        
        # 添加多个报价项
        for i in range(3):
            item = QuoteItem(
                quote_id=created.quote_id,
                product_code=f"product-{i}",
                product_name=f"产品{i}",
                region="cn-beijing",
                modality="文本生成",
                original_price=Decimal("100.00"),
                final_price=Decimal("80.00"),
                discount_rate=Decimal("0.8000"),
                billing_unit="千Token",
                quantity=1
            )
            await QuoteCRUD.add_quote_item(db_session, item)
        
        # 删除报价单
        await QuoteCRUD.delete_quote(db_session, quote_id)
        
        # 验证报价项也被删除
        items = await QuoteCRUD.get_quote_items(db_session, quote_id)
        assert len(items) == 0
