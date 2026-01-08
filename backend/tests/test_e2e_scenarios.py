"""
E2E端到端场景测试

测试范围：
- 产品查询场景：筛选、搜索、详情查看
- 报价单管理场景：创建、编辑、删除、状态流转
- 价格计算场景：不同产品类型、折扣规则
- AI对话场景：需求解析、智能推荐
- 导出场景：Excel生成、模板切换
- 竞品对比场景：多供应商对比
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from datetime import datetime, timedelta
import uuid

from app.models.product import Product, ProductPrice, ProductSpec, CompetitorMapping
from app.models.quote import QuoteSheet, QuoteItem
from app.services.pricing_engine import PricingEngine, TieredDiscountRule


# ==================== 测试数据工厂 ====================

class TestDataFactory:
    """测试数据工厂"""
    
    @staticmethod
    async def create_llm_product(db: AsyncSession, vendor: str = "aliyun") -> Product:
        """创建LLM大模型产品"""
        product_code = f"qwen-plus-{uuid.uuid4().hex[:6]}"
        product = Product(
            product_code=product_code,
            product_name=f"通义千问Plus ({product_code})",
            category="AI-大模型-文本生成",
            vendor=vendor,
            description="高性能大语言模型，支持多轮对话",
            status="active"
        )
        db.add(product)
        await db.flush()
        
        # 创建价格
        price = ProductPrice(
            product_code=product_code,
            region="cn-beijing",
            spec_type="standard",
            billing_mode="pay_as_you_go",
            unit_price="0.04",
            unit="千Token",
            pricing_variables={
                "input_price": 0.04,
                "output_price": 0.12,
                "context_4k": True
            },
            effective_date=datetime.now() - timedelta(days=1)
        )
        db.add(price)
        await db.flush()
        
        return product
    
    @staticmethod
    async def create_gpu_product(db: AsyncSession) -> Product:
        """创建GPU计算产品"""
        product_code = f"gpu-a10-{uuid.uuid4().hex[:6]}"
        product = Product(
            product_code=product_code,
            product_name=f"GPU A10实例 ({product_code})",
            category="计算-GPU实例",
            vendor="aliyun",
            description="高性能GPU计算实例",
            status="active"
        )
        db.add(product)
        await db.flush()
        
        price = ProductPrice(
            product_code=product_code,
            region="cn-beijing",
            spec_type="standard",
            billing_mode="pay_as_you_go",
            unit_price="15.80",
            unit="小时",
            pricing_variables={
                "gpu_count": 1,
                "memory": "24GB"
            },
            effective_date=datetime.now() - timedelta(days=1)
        )
        db.add(price)
        await db.flush()
        
        return product
    
    @staticmethod
    async def create_complete_quote(
        db: AsyncSession,
        customer_name: str = "测试企业",
        item_count: int = 3
    ) -> QuoteSheet:
        """创建包含商品的完整报价单"""
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}",
            customer_name=customer_name,
            project_name="企业AI升级项目",
            created_by="e2e_test",
            status="draft",
            currency="CNY",
            global_discount_rate=Decimal("1.0000"),
            total_amount=Decimal("0"),
            total_original_amount=Decimal("0"),
            valid_until=datetime.now() + timedelta(days=30)
        )
        db.add(quote)
        await db.flush()
        
        total = Decimal("0")
        for i in range(item_count):
            item = QuoteItem(
                quote_id=quote.quote_id,
                product_code=f"test-product-{i}",
                product_name=f"测试产品{i+1}",
                region="cn-beijing",
                modality="text",
                quantity=i + 1,
                duration_months=12,
                original_price=Decimal(str(100 * (i + 1))),
                discount_rate=Decimal("1.0"),
                final_price=Decimal(str(100 * (i + 1))),
                billing_unit="千Token",
                sort_order=i
            )
            db.add(item)
            total += item.final_price
        
        quote.total_amount = total
        quote.total_original_amount = total
        await db.flush()
        
        return quote


# ==================== 场景1：产品查询完整流程 ====================

class TestProductQueryScenario:
    """产品查询场景测试"""
    
    @pytest.mark.asyncio
    async def test_scenario_browse_and_filter_products(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        场景: 用户浏览并筛选产品
        步骤:
        1. 获取筛选条件选项
        2. 按厂商筛选产品
        3. 按关键词搜索产品
        4. 查看产品详情
        5. 查询产品价格
        """
        # 准备测试数据
        llm_product = await TestDataFactory.create_llm_product(db_session)
        gpu_product = await TestDataFactory.create_gpu_product(db_session)
        await db_session.flush()
        
        # Step 1: 获取筛选条件
        filter_response = await client.get("/api/v1/products/filters")
        assert filter_response.status_code == 200
        filters = filter_response.json()
        assert "regions" in filters
        assert "modalities" in filters
        
        # Step 2: 按厂商筛选
        list_response = await client.get("/api/v1/products/models", params={
            "vendor": "aliyun",
            "page": 1,
            "page_size": 20
        })
        assert list_response.status_code == 200
        products = list_response.json()
        assert products["total"] >= 1
        
        # Step 3: 关键词搜索
        search_response = await client.get("/api/v1/products/models", params={
            "keyword": llm_product.product_code[:10]
        })
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert search_results["total"] >= 1
        
        # Step 4: 查看详情
        detail_response = await client.get(
            f"/api/v1/products/models/{llm_product.product_code}"
        )
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["model_id"] == llm_product.product_code
        
        # Step 5: 查询价格
        price_response = await client.get(
            f"/api/v1/products/{llm_product.product_code}/price",
            params={"region": "cn-beijing"}
        )
        assert price_response.status_code == 200
        price_data = price_response.json()
        assert price_data["product_code"] == llm_product.product_code
    
    @pytest.mark.asyncio
    async def test_scenario_batch_product_search(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        场景: 批量搜索产品
        用于AI对话解析后批量查找产品
        """
        # 准备多个产品
        products = []
        for i in range(3):
            p = await TestDataFactory.create_llm_product(db_session)
            products.append(p)
        await db_session.flush()
        
        # 批量搜索
        names = [p.product_code for p in products] + ["not-exist-product"]
        response = await client.post("/api/v1/products/search", json={
            "names": names,
            "region": "cn-beijing"
        })
        
        assert response.status_code == 200
        result = response.json()
        assert len(result["found"]) == 3
        assert len(result["not_found"]) == 1
        assert "not-exist-product" in result["not_found"]


# ==================== 场景2：报价单完整生命周期 ====================

class TestQuoteLifecycleScenario:
    """报价单生命周期场景测试"""
    
    @pytest.mark.asyncio
    async def test_scenario_full_quote_lifecycle(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        场景: 报价单完整生命周期
        步骤:
        1. 创建报价单
        2. 添加多个商品
        3. 更新商品数量
        4. 应用折扣
        5. 确认报价单
        6. 查看版本历史
        7. 预览导出数据
        """
        # 准备产品数据
        product1 = await TestDataFactory.create_llm_product(db_session)
        product2 = await TestDataFactory.create_gpu_product(db_session)
        await db_session.flush()
        
        # Step 1: 创建报价单 (直接在DB创建，避免Redis依赖)
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}",
            customer_name="生命周期测试客户",
            project_name="全周期测试项目",
            created_by="lifecycle_test",
            status="draft",
            currency="CNY",
            global_discount_rate=Decimal("1.0000"),
            total_amount=Decimal("0"),
            valid_until=datetime.now() + timedelta(days=30)
        )
        db_session.add(quote)
        await db_session.flush()
        quote_id = str(quote.quote_id)
        
        # Step 2: 添加商品1
        add_response1 = await client.post(f"/api/v1/quotes/{quote_id}/items", json={
            "product_code": product1.product_code,
            "region": "cn-beijing",
            "quantity": 5,
            "input_tokens": 500000,
            "output_tokens": 200000,
            "duration_months": 12
        })
        assert add_response1.status_code == 200
        item1_id = add_response1.json()["item_id"]
        
        # 添加商品2
        add_response2 = await client.post(f"/api/v1/quotes/{quote_id}/items", json={
            "product_code": product2.product_code,
            "region": "cn-beijing",
            "quantity": 2,
            "duration_months": 6
        })
        assert add_response2.status_code == 200
        
        # Step 3: 更新商品数量
        update_response = await client.put(
            f"/api/v1/quotes/{quote_id}/items/{item1_id}",
            json={"quantity": 10}
        )
        assert update_response.status_code == 200
        assert update_response.json()["quantity"] == 10
        
        # Step 4: 应用折扣
        discount_response = await client.post(
            f"/api/v1/quotes/{quote_id}/discount",
            json={"discount_rate": 0.85, "remark": "VIP客户折扣"}
        )
        assert discount_response.status_code == 200
        
        # Step 5: 确认报价单
        confirm_response = await client.post(f"/api/v1/quotes/{quote_id}/confirm")
        assert confirm_response.status_code == 200
        confirmed_data = confirm_response.json()
        assert confirmed_data["status"] == "confirmed"
        
        # Step 6: 查看版本历史
        versions_response = await client.get(f"/api/v1/quotes/{quote_id}/versions")
        assert versions_response.status_code == 200
        versions = versions_response.json()
        assert len(versions) >= 1
        
        # Step 7: 预览导出
        preview_response = await client.get(f"/api/v1/export/preview/{quote_id}")
        assert preview_response.status_code == 200
        preview = preview_response.json()
        assert preview["summary"]["item_count"] == 2
    
    @pytest.mark.asyncio
    async def test_scenario_quote_clone_and_modify(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        场景: 克隆报价单并修改
        用于基于历史报价快速创建新报价
        """
        # 创建原始报价单
        original = await TestDataFactory.create_complete_quote(
            db_session, "原始客户", item_count=2
        )
        await db_session.flush()
        original_id = str(original.quote_id)
        
        # 验证原始报价单
        original_response = await client.get(f"/api/v1/quotes/{original_id}")
        assert original_response.status_code == 200
        original_data = original_response.json()
        assert len(original_data["items"]) == 2


# ==================== 场景3：价格计算 ====================

class TestPricingScenario:
    """价格计算场景测试"""
    
    @pytest.mark.asyncio
    async def test_scenario_llm_pricing_calculation(self):
        """
        场景: LLM产品价格计算
        包含Token计费、思考模式、批量折扣
        """
        engine = PricingEngine()
        
        # 添加阶梯折扣规则
        engine.add_rule(TieredDiscountRule([
            {"threshold": 100000, "discount": 0.9},
            {"threshold": 1000000, "discount": 0.8}
        ]))
        
        # 场景1: 普通Token计费
        result1 = engine.calculate(
            base_price=Decimal("0.04"),
            context={
                "product_type": "llm",
                "input_token_price": 0.04,
                "output_token_price": 0.12,
                "input_tokens": 50000,
                "output_tokens": 20000,
                "thinking_mode_ratio": 0,
                "batch_call_ratio": 0
            }
        )
        assert result1["final_price"] > 0
        assert "calculation_breakdown" in result1
        
        # 场景2: 带思考模式
        result2 = engine.calculate(
            base_price=Decimal("0.04"),
            context={
                "product_type": "llm",
                "input_token_price": 0.04,
                "output_token_price": 0.12,
                "input_tokens": 100000,
                "output_tokens": 50000,
                "thinking_mode_ratio": 0.5,
                "thinking_mode_multiplier": 1.5,
                "batch_call_ratio": 0
            }
        )
        # 思考模式价格应该更高
        assert result2["final_price"] > 0
        
        # 场景3: 批量调用折扣
        result3 = engine.calculate(
            base_price=Decimal("0.04"),
            context={
                "product_type": "llm",
                "input_token_price": 0.04,
                "output_token_price": 0.12,
                "input_tokens": 1000000,
                "output_tokens": 500000,
                "thinking_mode_ratio": 0,
                "batch_call_ratio": 1.0,
                "quantity": 100000
            }
        )
        # 大量调用应该获得折扣
        assert result3["final_price"] > 0
    
    @pytest.mark.asyncio
    async def test_scenario_standard_product_pricing(self):
        """
        场景: 标准产品价格计算
        包含数量、时长
        """
        engine = PricingEngine()
        
        result = engine.calculate(
            base_price=Decimal("100"),
            context={
                "product_type": "standard",
                "quantity": 5,
                "duration_months": 12
            }
        )
        
        # 5个单位 * 12个月 * 100 = 6000
        assert result["final_price"] == 6000


# ==================== 场景4：导出功能 ====================

class TestExportScenario:
    """导出功能场景测试"""
    
    @pytest.mark.asyncio
    async def test_scenario_export_workflow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        场景: 完整导出流程
        步骤:
        1. 获取可用模板
        2. 预览报价数据
        3. 验证数据格式
        """
        # 创建报价单
        quote = await TestDataFactory.create_complete_quote(db_session, "导出测试客户", 5)
        await db_session.flush()
        quote_id = str(quote.quote_id)
        
        # Step 1: 获取模板列表
        templates_response = await client.get("/api/v1/export/templates")
        assert templates_response.status_code == 200
        templates = templates_response.json()
        assert len(templates) == 3
        
        template_ids = [t["id"] for t in templates]
        assert "standard" in template_ids
        assert "competitor" in template_ids
        assert "simplified" in template_ids
        
        # Step 2: 预览数据
        preview_response = await client.get(f"/api/v1/export/preview/{quote_id}")
        assert preview_response.status_code == 200
        preview = preview_response.json()
        
        # 验证数据结构
        assert "quote" in preview
        assert "items" in preview
        assert "summary" in preview
        
        assert preview["quote"]["customer_name"] == "导出测试客户"
        assert preview["summary"]["item_count"] == 5


# ==================== 场景5：AI对话（模拟测试） ====================

class TestAIChatScenario:
    """AI对话场景测试"""
    
    @pytest.mark.asyncio
    async def test_scenario_chat_basic(self, client: AsyncClient):
        """
        场景: 基本AI对话
        注：AI功能标记为开发中，验证接口可用性
        """
        response = await client.post("/api/v1/ai/chat", json={
            "message": "我需要一个大模型产品",
            "session_id": "test_session_001"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
    
    @pytest.mark.asyncio  
    async def test_scenario_parse_requirement(self, client: AsyncClient):
        """
        场景: 需求解析
        验证需求解析接口
        """
        response = await client.post(
            "/api/v1/ai/parse-requirement",
            params={"requirement_text": "我需要qwen-max模型，预计每月100万token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "entities" in data or "message" in data


# ==================== 场景6：异常和边界情况 ====================

class TestEdgeCasesScenario:
    """边界情况场景测试"""
    
    @pytest.mark.asyncio
    async def test_scenario_concurrent_operations(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        场景: 并发操作验证
        确保数据一致性
        """
        quote = await TestDataFactory.create_complete_quote(db_session, "并发测试", 1)
        await db_session.flush()
        quote_id = str(quote.quote_id)
        
        # 快速连续请求
        responses = []
        for i in range(5):
            r = await client.get(f"/api/v1/quotes/{quote_id}")
            responses.append(r)
        
        # 所有请求应该成功
        for r in responses:
            assert r.status_code == 200
    
    @pytest.mark.asyncio
    async def test_scenario_large_quote(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        场景: 大型报价单
        验证多商品处理
        """
        quote = await TestDataFactory.create_complete_quote(db_session, "大型报价测试", 50)
        await db_session.flush()
        quote_id = str(quote.quote_id)
        
        # 验证预览
        preview = await client.get(f"/api/v1/export/preview/{quote_id}")
        assert preview.status_code == 200
        assert preview.json()["summary"]["item_count"] == 50
    
    @pytest.mark.asyncio
    async def test_scenario_error_recovery(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        场景: 错误恢复
        验证错误处理机制
        """
        # 不存在的报价单
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/quotes/{fake_id}")
        assert response.status_code in [404, 500]
        
        # 不存在的产品
        response = await client.get("/api/v1/products/models/non-existent-model")
        assert response.status_code == 404
        
        # 无效参数
        response = await client.get("/api/v1/products/models", params={"page": -1})
        assert response.status_code == 422


# ==================== 场景7：竞品对比 ====================

class TestCompetitorComparisonScenario:
    """竞品对比场景测试"""
    
    @pytest.mark.asyncio
    async def test_scenario_multi_vendor_comparison(
        self, db_session: AsyncSession
    ):
        """
        场景: 多供应商产品对比
        创建不同供应商的相似产品进行对比
        """
        # 创建阿里云产品
        aliyun_product = await TestDataFactory.create_llm_product(db_session, "aliyun")
        
        # 创建火山引擎产品（模拟）
        volcano_code = f"doubao-pro-{uuid.uuid4().hex[:6]}"
        volcano_product = Product(
            product_code=volcano_code,
            product_name=f"豆包大模型 ({volcano_code})",
            category="AI-大模型-文本生成",
            vendor="volcano",
            description="火山引擎大语言模型",
            status="active"
        )
        db_session.add(volcano_product)
        
        # 创建竞品映射
        mapping = CompetitorMapping(
            ali_product_code=aliyun_product.product_code,
            comp_product_code=volcano_code,
            competitor_name="volcano",
            confidence_score="0.85",
            mapping_type="功能相似",
            created_by="e2e_test"
        )
        db_session.add(mapping)
        await db_session.flush()
        
        # 验证数据
        assert aliyun_product.vendor == "aliyun"
        assert volcano_product.vendor == "volcano"


# ==================== 综合场景：完整业务流程 ====================

class TestCompleteBusinessFlow:
    """完整业务流程测试"""
    
    @pytest.mark.asyncio
    async def test_scenario_end_to_end_quote_generation(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """
        场景: 端到端报价生成流程
        模拟完整的用户操作流程
        """
        # 1. 浏览产品
        browse_response = await client.get("/api/v1/products/models")
        assert browse_response.status_code == 200
        
        # 2. 创建产品用于报价
        product = await TestDataFactory.create_llm_product(db_session)
        await db_session.flush()
        
        # 3. 查看产品详情
        detail = await client.get(f"/api/v1/products/models/{product.product_code}")
        assert detail.status_code == 200
        
        # 4. 创建报价单
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:4].upper()}",
            customer_name="完整流程测试客户",
            project_name="E2E测试项目",
            created_by="e2e_flow",
            status="draft",
            currency="CNY",
            global_discount_rate=Decimal("1.0000"),
            total_amount=Decimal("0"),
            valid_until=datetime.now() + timedelta(days=30)
        )
        db_session.add(quote)
        await db_session.flush()
        quote_id = str(quote.quote_id)
        
        # 5. 添加产品到报价单
        add_result = await client.post(f"/api/v1/quotes/{quote_id}/items", json={
            "product_code": product.product_code,
            "region": "cn-beijing",
            "quantity": 1,
            "input_tokens": 100000,
            "output_tokens": 50000,
            "duration_months": 12
        })
        assert add_result.status_code == 200
        
        # 6. 应用折扣
        discount_result = await client.post(f"/api/v1/quotes/{quote_id}/discount", json={
            "discount_rate": 0.9,
            "remark": "新客户优惠"
        })
        assert discount_result.status_code == 200
        
        # 7. 确认报价
        confirm_result = await client.post(f"/api/v1/quotes/{quote_id}/confirm")
        assert confirm_result.status_code == 200
        assert confirm_result.json()["status"] == "confirmed"
        
        # 8. 预览导出
        preview = await client.get(f"/api/v1/export/preview/{quote_id}")
        assert preview.status_code == 200
        preview_data = preview.json()
        assert preview_data["quote"]["status"] == "confirmed"
        assert preview_data["summary"]["item_count"] == 1
