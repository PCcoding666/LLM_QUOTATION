"""
测试配置和基础测试类
"""
import os
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from app.core.database import Base, get_db
from app.core.config import settings
from main import app

# 使用开发数据库进行测试（事务隔离）
# 也可以设置 TEST_DATABASE_URL 环境变量使用独立测试数据库
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", os.getenv("DATABASE_URL"))


# 创建测试引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool
)

# 创建测试会话工厂
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    """创建测试数据库会话，使用事务回滚隔离测试数据"""
    # 导入所有模型确保表结构完整
    from app.models.product import Product, ProductPrice, ProductSpec, CompetitorMapping
    from app.models.quote import QuoteSheet, QuoteItem, QuoteDiscount, QuoteVersion
    
    # 创建会话
    async with test_engine.connect() as conn:
        # 开始事务
        trans = await conn.begin()
        
        # 创建绑定到连接的会话
        session = AsyncSession(bind=conn, expire_on_commit=False)
        
        try:
            yield session
        finally:
            await session.close()
            # 回滚事务，清理测试数据
            await trans.rollback()


@pytest.fixture(scope="function")
async def client(db_session: AsyncSession):
    """创建测试客户端"""
    from httpx import AsyncClient, ASGITransport
    
    # 覆盖依赖
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # 使用 ASGITransport 来测试 FastAPI 应用
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # 清除依赖覆盖
    app.dependency_overrides.clear()
