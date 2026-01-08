# 报价侠系统 - 快速上手指南

## 🚀 5分钟快速启动

### 步骤1: 安装Python环境

```bash
# 确认Python版本 (需要3.10+)
python3 --version

# 进入后端目录
cd backend
```

### 步骤2: 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate

# Windows:
# venv\Scripts\activate
```

### 步骤3: 安装依赖

```bash
pip install -r requirements.txt
```

### 步骤4: 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置文件
vim .env  # 或使用其他编辑器
```

**必填配置项:**
```env
# 数据库 (如果本地没有PostgreSQL,可以先用SQLite测试)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/quote_system

# Redis
REDIS_URL=redis://localhost:6379/0

# 百炼API (必须填写真实的API Key)
DASHSCOPE_API_KEY=your_api_key_here

# OSS (可选,不影响主要功能)
OSS_ACCESS_KEY_ID=your_key
OSS_ACCESS_KEY_SECRET=your_secret
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_BUCKET_NAME=quote-system-files
```

### 步骤5: 初始化数据库

```bash
# 安装Alembic
pip install alembic

# 初始化Alembic
alembic init alembic

# 修改alembic/env.py中的target_metadata
# 添加: from app.core.database import Base
# 修改: target_metadata = Base.metadata

# 创建初始迁移
alembic revision --autogenerate -m "Initial schema"

# 执行迁移
alembic upgrade head
```

### 步骤6: 启动服务

```bash
# 直接运行
python main.py

# 或使用uvicorn
uvicorn main:app --reload
```

### 步骤7: 访问API文档

打开浏览器访问:
- **Swagger文档**: http://localhost:8000/api/docs
- **ReDoc文档**: http://localhost:8000/api/redoc
- **健康检查**: http://localhost:8000/health

## 📝 API测试示例

### 1. 测试AI对话功能

```bash
curl -X POST "http://localhost:8000/api/v1/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "需要100张A10卡训练3个月",
    "session_id": "test_session_001"
  }'
```

**预期响应:**
```json
{
  "response": "我理解您的需求如下:\n- 产品类型: GPU实例\n- 数量: 100\n- 使用时长: 3个月",
  "session_id": "test_session_001"
}
```

### 2. 测试需求解析

```bash
curl -X POST "http://localhost:8000/api/v1/ai/parse-requirement?requirement_text=需要100张A10卡训练3个月"
```

### 3. 测试产品列表

```bash
curl "http://localhost:8000/api/v1/products?category=GPU&page=1&size=10"
```

### 4. 测试创建报价单

```bash
curl -X POST "http://localhost:8000/api/v1/quotes" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "测试客户",
    "project_name": "AI训练项目"
  }'
```

## 🧪 功能验证清单

- [ ] 服务启动成功
- [ ] API文档可访问
- [ ] AI对话功能正常
- [ ] 产品查询正常
- [ ] 报价单创建正常
- [ ] 价格计算正常

## 🔧 常见问题

### Q1: 数据库连接失败

**问题**: `could not connect to server`

**解决**:
```bash
# 检查PostgreSQL是否运行
# macOS:
brew services list

# 启动PostgreSQL
brew services start postgresql

# 或者临时使用SQLite (开发测试用)
# 修改DATABASE_URL为:
# DATABASE_URL=sqlite+aiosqlite:///./test.db
```

### Q2: Redis连接失败

**问题**: `Error connecting to Redis`

**解决**:
```bash
# 安装Redis (macOS)
brew install redis

# 启动Redis
brew services start redis

# 或者临时启动
redis-server
```

### Q3: 百炼API调用失败

**问题**: `API key not configured`

**解决**:
1. 访问阿里云百炼平台获取API Key
2. 在.env文件中正确配置DASHSCOPE_API_KEY
3. 重启服务

### Q4: 依赖安装失败

**问题**: `No matching distribution found`

**解决**:
```bash
# 升级pip
pip install --upgrade pip

# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 📚 下一步学习

1. **阅读API文档**: http://localhost:8000/api/docs
2. **查看数据模型**: `backend/app/models/`
3. **理解计费引擎**: `backend/app/services/pricing_engine.py`
4. **研究Agent架构**: `backend/app/agents/`

## 🎯 核心代码示例

### 使用计费引擎

```python
from app.services.pricing_engine import pricing_engine
from decimal import Decimal

# 计算大模型价格
result = pricing_engine.calculate(
    base_price=Decimal("0.01"),  # Token单价
    context={
        "product_type": "llm",
        "estimated_tokens": 1000,      # 预估Token数
        "call_frequency": 10000,       # 调用次数
        "thinking_mode_ratio": 0.3,    # 30%使用思考模式
        "batch_call_ratio": 0.5        # 50%使用Batch调用
    }
)

print(f"最终价格: {result['final_price']}")
print(f"折扣明细: {result['discount_details']}")
```

### 使用Agent编排器

```python
from app.agents.orchestrator import agent_orchestrator

# 处理用户消息
response = await agent_orchestrator.process_user_message(
    message="需要为客户推荐一个GPU训练方案",
    session_id="user_123"
)

print(response['response'])  # AI回复
print(response['entities'])  # 提取的实体
```

### 使用CRUD操作

```python
from app.crud.product import product_crud
from app.core.database import get_db

async def example():
    async for db in get_db():
        # 查询产品列表
        products = await product_crud.get_products(
            db,
            category="GPU",
            keyword="A10",
            skip=0,
            limit=10
        )
        
        for product in products:
            print(f"{product.product_name}: {product.description}")
```

## 💬 需要帮助?

- 查看设计文档: `.qoder/quests/quote-system-backend-design.md`
- 查看实现总结: `IMPLEMENTATION_SUMMARY.md`
- 查看README: `backend/README.md`

---

祝使用愉快! 🎉
