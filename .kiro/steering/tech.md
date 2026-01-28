# Technology Stack & Build System

## Backend Stack

- **Web Framework**: FastAPI 0.109+ with Uvicorn/Gunicorn
- **Database**: PostgreSQL 15+ (ADB PG) with SQLAlchemy 2.0+ ORM
- **Database Migrations**: Alembic for schema versioning
- **Caching**: Redis 7.x with hiredis for performance
- **AI Integration**: Alibaba Cloud Bailian API (Qwen-Max model)
- **Web Scraping**: Scrapy + Playwright for competitor price crawling
- **Excel Processing**: openpyxl + xlsxwriter for report generation
- **Cloud Storage**: Alibaba Cloud OSS for file uploads
- **Task Scheduling**: APScheduler for automated crawling
- **Logging**: Loguru for structured logging

## Frontend Stack

- **Framework**: React 18.2+ with Vite 5.0 build system
- **Styling**: Tailwind CSS 3.3+
- **HTTP Client**: Axios for API communication
- **Routing**: React Router DOM 6.20+
- **Production Server**: Express.js with proxy middleware

## Development Tools

- **Code Quality**: Black (formatting), Flake8 (linting), MyPy (type checking)
- **Testing**: pytest with asyncio support, 80+ test cases with 96.25% pass rate
- **API Documentation**: Automatic OpenAPI/Swagger generation via FastAPI

## Common Commands

### Backend Development
```bash
# One-click startup (recommended)
./start.sh dev          # Development mode with hot reload
./start.sh prod         # Production mode with multiple workers
./start.sh test         # Run test suite only
./start.sh check        # Health check

# Manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Database operations
alembic revision --autogenerate -m "migration message"
alembic upgrade head

# Testing
pytest tests/ -v
pytest --cov=app tests/  # With coverage
```

### Frontend Development
```bash
npm install
npm run dev              # Development server on port 3000
npm run build            # Production build
npm run preview          # Preview production build
```

### Production Deployment
```bash
# Backend
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Frontend
npm run build
node server.js           # Express server with proxy
```

## Environment Configuration

Required environment variables in `.env`:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string  
- `DASHSCOPE_API_KEY`: Alibaba Cloud Bailian API key
- `OSS_*`: Alibaba Cloud OSS configuration for file uploads

## Performance Benchmarks

- **Pricing Engine**: 0.3ms average, 3300+ ops/s
- **Quote Calculation**: 2.6ms average, 387 ops/s  
- **Product Filtering**: 0.05ms average, 20000+ ops/s
- **Excel Export**: 3.3ms average, 299 ops/s