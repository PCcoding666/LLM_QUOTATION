# 报价侠系统 (LLM Quotation)

> 一款面向阿里云 BTE/SA 人员的智能化报价平台，通过 AI 能力与自动化手段，将传统 7 天的报价工作压缩至"选、配、导"三步完成。

## 功能特性

- **AI 智能交互** - 基于阿里云百炼 API，自然语言理解客户需求，自动提取实体信息
- **智能产品推荐** - 根据需求智能推荐产品配置，支持大模型 Token 计费
- **自动价格计算** - 支持思考模式/非思考模式、Batch 调用折扣、阶梯折扣等复杂计费规则
- **竞品价格爬取** - 自动爬取阿里云、火山引擎等平台的产品价格数据
- **报价单导出** - 一键生成 Excel 报价单，支持上传至阿里云 OSS

## Documentation

| Document | Description |
|----------|-------------|
| [Quick Start](docs/guides/quick-start.md) | 5-minute setup guide |
| [Database Migration](docs/dev/database-migration.md) | Alembic migration guide |
| [E2E Test Report](docs/reports/e2e-test-report.md) | End-to-end test results |
| [Performance Report](docs/reports/performance-test-report.md) | Performance benchmarks |
| [Delivery Summary](docs/reports/delivery-summary.md) | Release delivery report |

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI 0.109+ |
| 数据库 | PostgreSQL 15+ |
| 缓存 | Redis 7.x |
| AI 能力 | 阿里云百炼 API (Qwen-Max) |
| 爬虫 | Scrapy / Playwright |
| Excel 处理 | openpyxl / xlsxwriter |
| 对象存储 | 阿里云 OSS |

## 系统架构

### 整体架构图

```mermaid
graph TB
    subgraph Client_Layer["客户端"]
        Client["前端 / API调用方"]
    end

    subgraph API_Layer["API层"]
        Router["FastAPI Router"]
        Products["products 产品数据"]
        Quotes["quotes 报价管理"]
        AIChat["ai AI交互"]
        Export["export 导出服务"]
        Crawler["crawler 爬虫管理"]
    end

    subgraph Agent_Layer["Agent层"]
        Orchestrator["AgentOrchestrator 编排器"]
        BailianClient["BailianClient 百炼客户端"]
        Tools["FunctionTools 工具集"]
    end

    subgraph Service_Layer["服务层"]
        PricingEngine["PricingEngine 计费引擎"]
        ExcelExporter["ExcelExporter Excel导出"]
        OSSUploader["OSSUploader OSS上传"]
        CrawlerScheduler["CrawlerScheduler 爬虫调度"]
        AliyunCrawler["AliyunCrawler 阿里云爬虫"]
        VolcanoCrawler["VolcanoCrawler 火山引擎爬虫"]
    end

    subgraph Data_Layer["数据层"]
        CRUD["CRUD 数据操作"]
        Models["Models 数据模型"]
    end

    subgraph Infrastructure["基础设施"]
        PostgreSQL[("PostgreSQL")]
        Redis[("Redis")]
    end

    subgraph External_Services["外部服务"]
        BailianAPI["阿里云百炼API"]
        OSS["阿里云OSS"]
        AliyunWeb["阿里云官网"]
        VolcanoWeb["火山引擎官网"]
    end

    Client --> Router
    Router --> Products
    Router --> Quotes
    Router --> AIChat
    Router --> Export
    Router --> Crawler

    Products --> CRUD
    Quotes --> CRUD
    Quotes --> PricingEngine
    AIChat --> Orchestrator
    Export --> ExcelExporter
    Export --> OSSUploader
    Crawler --> CrawlerScheduler

    Orchestrator --> BailianClient
    Orchestrator --> Tools
    Tools --> PricingEngine

    BailianClient --> BailianAPI
    OSSUploader --> OSS
    CrawlerScheduler --> AliyunCrawler
    CrawlerScheduler --> VolcanoCrawler
    AliyunCrawler --> AliyunWeb
    VolcanoCrawler --> VolcanoWeb

    CRUD --> Models
    CRUD --> PostgreSQL
    PricingEngine --> Redis
    ExcelExporter --> CRUD
```

### 核心业务时序图

#### 1. AI 智能报价流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant API as AI Chat API
    participant O as Agent编排器
    participant B as 百炼API
    participant T as Tools工具集
    participant P as 计费引擎
    participant DB as 数据库

    U->>API: 发送需求消息
    API->>O: process_user_message()
    O->>B: 调用大模型理解需求
    B-->>O: 返回Function Call
    O->>T: execute_function(extract_entities)
    T-->>O: 返回提取的实体
    O->>T: execute_function(estimate_usage)
    T->>DB: 查询产品信息
    DB-->>T: 返回产品数据
    T-->>O: 返回用量估算
    O->>T: execute_function(calculate_price)
    T->>P: 计算价格
    P-->>T: 返回价格结果
    T-->>O: 返回计算结果
    O->>B: 生成自然语言回复
    B-->>O: 返回AI回复
    O-->>API: 返回完整响应
    API-->>U: 返回报价建议
```

#### 2. 报价单导出流程

```mermaid
sequenceDiagram
    participant U as 用户
    participant API as Export API
    participant E as Excel导出服务
    participant DB as 数据库
    participant OSS as 阿里云OSS

    U->>API: 请求导出报价单
    API->>DB: 查询报价单数据
    DB-->>API: 返回报价单详情
    API->>E: 生成Excel文件
    E->>E: 渲染模板
    E->>E: 填充数据
    E-->>API: 返回Excel文件
    API->>OSS: 上传文件
    OSS-->>API: 返回文件URL
    API-->>U: 返回下载链接
```

#### 3. 爬虫数据更新流程

```mermaid
sequenceDiagram
    participant S as 定时调度器
    participant C as 爬虫调度器
    participant A as 阿里云爬虫
    participant V as 火山引擎爬虫
    participant P as 数据处理器
    participant DB as 数据库
    participant R as Redis

    S->>C: 触发定时任务
    par 并行爬取
        C->>A: 爬取阿里云价格
        A-->>C: 返回价格数据
    and
        C->>V: 爬取火山引擎价格
        V-->>C: 返回价格数据
    end
    C->>P: 处理爬取数据
    P->>P: 数据清洗与标准化
    P->>DB: 更新产品价格
    P->>R: 更新缓存
    P->>P: 检测价格变化
    alt 价格有变化
        P->>P: 发送变更通知
    end
```

### 爬虫数据更新架构

爬虫模块采用分层架构，将数据采集、处理、存储分离，便于扩展新的数据源：

```
┌─────────────────────────────────────────────────────────────────────┐
│                          爬虫数据流架构                               │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│   数据源        │     │    爬虫层      │     │      处理层         │
│              │     │              │     │                  │
│ 阿里云官网   │────▶│AliyunCrawler │────▶│CrawlerDataProcessor│
│ 火山引擎     │────▶│VolcanoCrawler│────▶│                  │
│ ...         │     │              │     │                  │
└──────────────┘     └──────────────┘     └────────┬─────────┘
                                                   │
                                                   ▼
┌──────────────────────────────────────────────────────────────┐
│                         数据库层                               │
├──────────────────┬──────────────────┬────────────────────────┤
│    products      │  product_prices   │    product_specs       │
│   (产品主表)      │   (价格表)         │    (规格表)             │
├──────────────────┴──────────────────┴────────────────────────┤
│                  PostgreSQL (quote_system)                     │
└──────────────────────────────────────────────────────────────┘
```

#### 核心组件说明

| 组件 | 文件 | 职责 |
|------|------|------|
| **BaseCrawler** | `services/crawler_base.py` | 爬虫基类：HTTP请求、重试机制、反爬策略 |
| **AliyunCrawler** | `services/aliyun_crawler.py` | 阿里云爬虫实现：解析产品和价格页面 |
| **VolcanoCrawler** | `services/volcano_crawler.py` | 火山引擎爬虫实现 |
| **CrawlerDataProcessor** | `services/crawler_processor.py` | 数据处理器：Upsert逻辑、价格变更检测 |
| **CrawlerScheduler** | `services/crawler_scheduler.py` | 爬虫调度器：定时任务、并行爬取 |

#### 价格版本管理机制

爬虫更新价格时采用“软过期”机制，保留历史价格用于分析：

```
时间线:  T1         T2(价格变动)      T3
         │           │               │
         ▼           ▼               ▼
      ┌─────────────────────────────────┐
      │ 旧价格 0.04   expire_date=T2   │
      └────────────┬────────────────────┘
                   │
                   ┌────────────────────┐
                   │ 新价格 0.03         │
                   │ effective_date=T2  │
                   └────────────────────┘
```

#### 扩展新爬虫

实现新数据源爬虫只需继承 `BaseCrawler` 并实现两个抽象方法：

```python
class NewVendorCrawler(BaseCrawler):
    async def crawl_products(self) -> List[Dict[str, Any]]:
        """Return: [{product_code, product_name, category, vendor, ...}]"""
        pass
    
    async def crawl_prices(self, product_code: str) -> List[Dict[str, Any]]:
        """Return: [{product_code, unit_price, region, spec_type, billing_mode, ...}]"""
        pass
```

## 项目目录

```
LLM_QUOTATION/
├── backend/                    # 后端服务
│   ├── main.py                # 应用入口
│   ├── requirements.txt       # Python 依赖
│   ├── app/
│   │   ├── api/v1/endpoints/  # API 端点
│   │   │   ├── products.py    # 产品数据 API
│   │   │   ├── quotes.py      # 报价管理 API
│   │   │   ├── ai_chat.py     # AI 交互 API
│   │   │   ├── export.py      # 导出服务 API
│   │   │   └── crawler.py     # 爬虫管理 API
│   │   ├── agents/            # AI Agent 模块
│   │   │   ├── orchestrator.py    # Agent 编排器
│   │   │   ├── bailian_client.py  # 百炼 API 客户端
│   │   │   └── tools.py           # Function Calling 工具
│   │   ├── services/          # 业务服务层
│   │   │   ├── pricing_engine.py      # 计费引擎
│   │   │   ├── excel_exporter.py      # Excel 导出
│   │   │   ├── oss_uploader.py        # OSS 上传
│   │   │   ├── crawler_scheduler.py   # 爬虫调度
│   │   │   ├── aliyun_crawler.py      # 阿里云爬虫
│   │   │   └── volcano_crawler.py     # 火山引擎爬虫
│   │   ├── crud/              # 数据访问层
│   │   ├── models/            # 数据模型
│   │   ├── schemas/           # 数据校验
│   │   └── core/              # 核心模块
│   │       ├── config.py      # 配置管理
│   │       ├── database.py    # 数据库连接
│   │       └── redis_client.py # Redis 客户端
│   └── tests/                 # 测试用例
└── .env                       # 环境变量配置
```

## 快速开始

### 环境要求

- Python 3.10+
- PostgreSQL 15+
- Redis 7.x
- Docker (可选)

### 1. 克隆项目

```bash
git clone <repository-url>
cd LLM_QUOTATION
```

### 2. 启动依赖服务

**使用 Docker 启动 PostgreSQL：**
```bash
docker run -d --name quote_system_db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=quote_system \
  -p 5433:5432 \
  postgres:15-alpine
```

**启动 Redis (macOS)：**
```bash
brew services start redis
```

### 3. 安装 Python 依赖

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填写必要配置
```

**主要配置项：**
```env
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5433/quote_system

# Redis
REDIS_URL=redis://localhost:6379/0

# 百炼 API
DASHSCOPE_API_KEY=your_api_key_here

# 阿里云 OSS
OSS_ACCESS_KEY_ID=your_key
OSS_ACCESS_KEY_SECRET=your_secret
OSS_ENDPOINT=oss-cn-shanghai.aliyuncs.com
OSS_BUCKET_NAME=quotation-files
```

### 5. 启动服务

```bash
python main.py
```

### 6. 访问服务

- **应用首页**: http://localhost:8000
- **Swagger 文档**: http://localhost:8000/api/docs
- **ReDoc 文档**: http://localhost:8000/api/redoc
- **健康检查**: http://localhost:8000/health

## API 示例

### AI 对话

```bash
curl -X POST "http://localhost:8000/api/v1/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "需要100张A10卡训练3个月",
    "session_id": "test_session_001"
  }'
```

### 创建报价单

```bash
curl -X POST "http://localhost:8000/api/v1/quotes" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "测试客户",
    "project_name": "AI训练项目"
  }'
```

### 查询产品

```bash
curl "http://localhost:8000/api/v1/products?category=GPU&page=1&size=10"
```

## 核心功能模块

### 1. 计费引擎

支持复杂的大模型计费场景：

```python
from app.services.pricing_engine import pricing_engine

result = pricing_engine.calculate(
    base_price=Decimal("0.01"),
    context={
        "product_type": "llm",
        "estimated_tokens": 1000000,
        "call_frequency": 10000,
        "thinking_mode_ratio": 0.3,  # 30% 使用思考模式
        "batch_call_ratio": 0.5       # 50% 使用 Batch 调用
    }
)
```

### 2. Agent 编排器

智能理解用户需求并推荐产品：

```python
from app.agents.orchestrator import agent_orchestrator

response = await agent_orchestrator.process_user_message(
    message="需要为客户推荐一个GPU训练方案",
    session_id="user_123"
)
```

## 开发指南

### 运行测试

```bash
pytest tests/ -v
```

### 代码格式化

```bash
black app/
flake8 app/
mypy app/
```

### 数据库迁移

```bash
alembic revision --autogenerate -m "migration message"
alembic upgrade head
```

## 部署

### Docker 部署

```bash
docker build -t quote-system-backend .
docker run -d -p 8000:8000 --env-file .env quote-system-backend
```

### 生产环境

```bash
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 常见问题

**Q: 数据库连接失败？**
- 检查 PostgreSQL 是否运行
- 确认 DATABASE_URL 配置正确

**Q: Redis 连接失败？**
- 运行 `redis-server` 或 `brew services start redis`

**Q: 百炼 API 调用失败？**
- 检查 DASHSCOPE_API_KEY 是否正确配置

## License

内部项目 - 仅供阿里云内部使用
