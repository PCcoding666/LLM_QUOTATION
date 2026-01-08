"""
报价管理服务测试
"""
import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timedelta

from app.models.quote import QuoteSheet, QuoteItem


# 报价单状态常量（与模型中status字段的字符串值对应）
class QuoteStatus:
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    FINALIZED = "finalized"
    CANCELLED = "cancelled"


class TestQuoteService:
    """报价管理服务测试"""
    
    @pytest.mark.asyncio
    async def test_create_quote(self, db_session):
        """测试创建报价单"""
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d')}{uuid4().hex[:4].upper()}",
            customer_name="测试客户",
            project_name="测试项目",
            created_by="test_user",
            status=QuoteStatus.DRAFT,
            total_amount=Decimal("0.00"),
            currency="CNY"
        )
        
        db_session.add(quote)
        await db_session.flush()
        
        assert quote.customer_name == "测试客户"
        assert quote.status == QuoteStatus.DRAFT
    
    @pytest.mark.asyncio
    async def test_create_quote_item(self, db_session):
        """测试创建报价明细"""
        # 先创建报价单
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d')}{uuid4().hex[:4].upper()}",
            customer_name="测试客户",
            created_by="test_user",
            status=QuoteStatus.DRAFT,
            total_amount=Decimal("0.00")
        )
        db_session.add(quote)
        await db_session.flush()
        
        # 创建明细
        item = QuoteItem(
            quote_id=quote.quote_id,
            product_code="bailian",
            product_name="百炼大模型服务",
            region="cn-beijing",
            modality="text",
            spec_config={"model": "qwen-max"},
            quantity=1,
            duration_months=1,
            unit_price=Decimal("100.00"),
            original_price=Decimal("100.00"),
            final_price=Decimal("100.00"),
            billing_unit="千Token",
            subtotal=Decimal("100.00")
        )
        db_session.add(item)
        await db_session.flush()
        
        assert item.quote_id == quote.quote_id
        assert item.product_name == "百炼大模型服务"
        assert float(item.subtotal) == 100.00
    
    @pytest.mark.asyncio
    async def test_update_quote_status(self, db_session):
        """测试更新报价单状态"""
        quote = QuoteSheet(
            quote_no=f"QT{datetime.now().strftime('%Y%m%d')}{uuid4().hex[:4].upper()}",
            customer_name="测试客户",
            created_by="test_user",
            status=QuoteStatus.DRAFT,
            total_amount=Decimal("1000.00")
        )
        db_session.add(quote)
        await db_session.flush()
        
        # 更新状态
        quote.status = QuoteStatus.FINALIZED
        await db_session.flush()
        
        assert quote.status == QuoteStatus.FINALIZED
