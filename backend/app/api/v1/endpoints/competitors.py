"""
竞品分析API端点
提供竞品对标数据查询接口
"""
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from loguru import logger

from app.services.competitor_service import competitor_service


router = APIRouter()


class CompetitorMatchRequest(BaseModel):
    """批量匹配请求"""
    model_codes: List[str]


class CompetitorResponse(BaseModel):
    """竞品匹配响应"""
    has_competitor: bool
    message: Optional[str] = None
    model_code: Optional[str] = None
    data: Optional[dict] = None


@router.get("/match", response_model=CompetitorResponse, summary="匹配单个模型的竞品数据")
async def match_competitor(
    model_name: str = Query(..., description="模型代码，如qwen-plus, qvq-max"),
    category: Optional[str] = Query(None, description="可选类别过滤：text/image/video")
):
    """
    根据模型代码查询竞品对标数据
    
    - **model_name**: 模型代码（如qwen-plus, qvq-max, wanxiang-image等）
    - **category**: 可选的类别过滤（text/image/video）
    
    返回Qwen与Doubao的价格对比、竞争洞察话术等信息
    """
    try:
        logger.info(f"竞品查询请求: model_name={model_name}, category={category}")
        result = competitor_service.match_competitor(model_name, category)
        return result
    except Exception as e:
        logger.error(f"竞品查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"竞品数据查询失败: {str(e)}")


@router.post("/batch-match", summary="批量匹配多个模型的竞品数据")
async def batch_match_competitors(request: CompetitorMatchRequest):
    """
    批量查询多个模型的竞品对标数据
    
    - **model_codes**: 模型代码列表
    
    返回以model_code为key的竞品数据字典
    """
    try:
        logger.info(f"批量竞品查询请求: {len(request.model_codes)} 个模型")
        results = competitor_service.batch_match(request.model_codes)
        return {
            "success": True,
            "results": results,
            "update_time": competitor_service.get_data_update_time()
        }
    except Exception as e:
        logger.error(f"批量竞品查询失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量查询失败: {str(e)}")


@router.get("/mappings", summary="获取模型名称映射表")
async def get_model_mappings():
    """
    获取所有支持的模型名称映射表
    
    返回model_code到JSON model字段的映射关系
    """
    return {
        "success": True,
        "mappings": competitor_service.get_all_mappings()
    }


@router.post("/reload", summary="重新加载竞品数据")
async def reload_competitor_data():
    """
    重新加载竞品数据（热更新）
    
    用于在不重启服务的情况下更新竞品数据
    """
    try:
        success = competitor_service.reload_data()
        if success:
            return {
                "success": True,
                "message": "竞品数据重新加载成功",
                "update_time": competitor_service.get_data_update_time()
            }
        else:
            return {
                "success": False,
                "message": "竞品数据文件加载失败，请检查文件是否存在或格式是否正确"
            }
    except Exception as e:
        logger.error(f"重新加载竞品数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"重新加载失败: {str(e)}")


@router.get("/status", summary="获取竞品数据状态")
async def get_competitor_status():
    """
    获取竞品数据服务状态
    
    返回数据是否已加载、更新时间等信息
    """
    competitor_service.ensure_loaded()
    return {
        "loaded": competitor_service._data_loaded,
        "record_count": len(competitor_service._data),
        "update_time": competitor_service.get_data_update_time(),
        "file_path": competitor_service._file_path
    }
