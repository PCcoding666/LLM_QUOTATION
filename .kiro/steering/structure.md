# Project Structure & Organization

## Repository Layout

```
LLM_QUOTATION/
├── backend/                    # Python FastAPI backend service
├── frontend/                   # React frontend application  
├── docs/                       # Documentation and reports
├── .kiro/                      # Kiro AI assistant configuration
├── .qoder/                     # Legacy tooling (deprecated)
├── openspec/                   # OpenSpec configuration
└── restart.sh                  # System restart script
```

## Backend Architecture (`backend/`)

### Core Application Structure
```
backend/
├── main.py                     # FastAPI application entry point
├── requirements.txt            # Python dependencies
├── start.sh                    # One-click startup script
├── alembic/                    # Database migration files
│   ├── versions/               # Migration scripts
│   └── env.py                  # Alembic configuration
└── app/                        # Main application package
    ├── core/                   # Core infrastructure
    │   ├── config.py           # Settings and configuration
    │   ├── database.py         # Database connection setup
    │   ├── redis_client.py     # Redis client initialization
    │   └── middleware.py       # Custom middleware
    ├── models/                 # SQLAlchemy data models
    ├── schemas/                # Pydantic request/response schemas
    ├── crud/                   # Database CRUD operations
    ├── api/v1/endpoints/       # REST API endpoints
    │   ├── products.py         # Product catalog API
    │   ├── quotes.py           # Quote management API
    │   ├── ai_chat.py          # AI interaction API
    │   ├── export.py           # Export services API
    │   └── crawler.py          # Web scraping API
    ├── services/               # Business logic layer
    │   ├── pricing_engine.py   # Complex billing calculations
    │   ├── excel_exporter.py   # Report generation
    │   ├── oss_uploader.py     # Cloud storage integration
    │   ├── crawler_scheduler.py # Automated scraping scheduler
    │   ├── aliyun_crawler.py   # Alibaba Cloud price scraper
    │   └── volcano_crawler.py  # Volcano Engine price scraper
    └── agents/                 # AI agent orchestration
        ├── orchestrator.py     # Main agent coordinator
        ├── bailian_client.py   # Bailian API client
        └── tools.py            # Function calling tools
```

### Key Architectural Patterns

- **Layered Architecture**: API → Services → CRUD → Models
- **Dependency Injection**: FastAPI's built-in DI for database sessions
- **Repository Pattern**: CRUD layer abstracts database operations
- **Service Layer**: Business logic separated from API controllers
- **Agent Pattern**: AI orchestration with tool-based function calling

## Frontend Architecture (`frontend/`)

```
frontend/
├── package.json                # Node.js dependencies and scripts
├── vite.config.js              # Vite build configuration
├── server.js                   # Production Express server
└── src/
    ├── App.jsx                 # Main application component
    ├── index.jsx               # React application entry point
    ├── api/                    # API client utilities
    ├── components/             # Reusable UI components
    │   ├── ChatWindow.jsx      # AI chat interface
    │   ├── PricingDrawer.jsx   # Pricing configuration panel
    │   └── CompetitorModal/    # Competitor analysis modal
    ├── pages/                  # Route-based page components
    │   ├── Home.jsx            # Landing page
    │   ├── ExpressQuote.jsx    # Quick quote generation
    │   ├── QuoteHistory.jsx    # Quote management
    │   └── PricingManagement.jsx # Admin pricing controls
    ├── context/                # React context providers
    ├── styles/                 # Global CSS and Tailwind config
    └── utils/                  # Utility functions
```

## Documentation Structure (`docs/`)

```
docs/
├── design/                     # Feature design documents
├── dev/                        # Development guides
├── guides/                     # User guides and tutorials
├── history/                    # Project history and summaries
├── reports/                    # Test and performance reports
└── test-reports/               # Detailed test documentation
```

## Configuration Management

- **Backend Config**: Environment variables via `.env` file, managed by `app/core/config.py`
- **Frontend Config**: Vite configuration with proxy setup for API calls
- **Database**: Alembic migrations in `backend/alembic/versions/`
- **AI Assistant**: Kiro configuration in `.kiro/steering/` and `.kiro/specs/`

## Data Flow Architecture

1. **Frontend** → API calls via Axios → **Backend API Layer**
2. **API Layer** → Business logic → **Service Layer** 
3. **Service Layer** → Data operations → **CRUD Layer**
4. **CRUD Layer** → Database queries → **PostgreSQL/Redis**
5. **AI Agents** → External APIs → **Bailian/OSS Services**
6. **Crawlers** → Web scraping → **Competitor Websites**

## Naming Conventions

- **Files**: snake_case for Python, camelCase for JavaScript
- **Classes**: PascalCase (e.g., `PricingEngine`, `BailianClient`)
- **Functions/Methods**: snake_case for Python, camelCase for JavaScript
- **Database Tables**: snake_case with descriptive names
- **API Endpoints**: RESTful conventions with kebab-case