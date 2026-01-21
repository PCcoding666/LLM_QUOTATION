"""
V1版本API路由聚合
"""
from fastapi import APIRouter

from app.api.v1.endpoints import products, quotes, ai_chat, export, crawler, doubao

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(products.router, prefix="/products", tags=["产品数据"])
api_router.include_router(quotes.router, prefix="/quotes", tags=["报价管理"])
api_router.include_router(ai_chat.router, prefix="/ai", tags=["AI交互"])
api_router.include_router(export.router, prefix="/export", tags=["导出服务"])
api_router.include_router(crawler.router, prefix="/crawler", tags=["爬虫管理"])
api_router.include_router(doubao.router, prefix="/doubao", tags=["豆包定价"])
