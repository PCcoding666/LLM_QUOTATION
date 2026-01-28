"""
极速报价API端点
"""
import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.agents.express_orchestrator import express_orchestrator


router = APIRouter()


# ==================== 请求/响应模型 ====================

class ExpressQuoteChatRequest(BaseModel):
    """极速报价对话请求"""
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID，不提供则创建新会话")


class CollectedDataResponse(BaseModel):
    """已收集数据"""
    selectedModels: List[Dict[str, Any]] = []
    modelConfigs: Dict[str, Any] = {}
    customerInfo: Dict[str, Any] = {}


class ExpressQuoteChatResponse(BaseModel):
    """极速报价对话响应"""
    response: str = Field(..., description="AI响应文本")
    session_id: str = Field(..., description="会话ID")
    current_step: int = Field(..., description="当前步骤 1:模型选择 2:客户信息 3:预览 4:导出")
    collected_data: CollectedDataResponse = Field(default_factory=CollectedDataResponse)
    preview_table: Optional[str] = Field(None, description="预览表格数据(JSON)")
    ready_to_export: bool = Field(False, description="是否可以导出")
    export_filename: Optional[str] = Field(None, description="导出文件名")
    suggested_options: List[str] = Field(default_factory=list, description="快捷选项")
    error: Optional[str] = Field(None, description="错误信息")


class ExpressQuoteExportRequest(BaseModel):
    """极速报价导出请求"""
    session_id: str = Field(..., description="会话ID")


class ExpressQuoteExportResponse(BaseModel):
    """极速报价导出响应"""
    success: bool
    filename: Optional[str] = None
    message: str = ""
    download_url: Optional[str] = None


# ==================== API端点 ====================

@router.post("/chat", response_model=ExpressQuoteChatResponse)
async def express_quote_chat(
    request: ExpressQuoteChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    极速报价AI对话接口
    
    通过多轮对话引导用户完成报价单制作：
    1. 模型选择：搜索并选择模型规格
    2. 客户信息：填写客户名称、折扣等
    3. 预览确认：查看报价单预览
    4. 导出下载：生成Excel文件
    """
    # 生成或使用会话ID
    session_id = request.session_id or f"eq_{uuid.uuid4().hex[:12]}"
    
    try:
        result = await express_orchestrator.process_message(
            message=request.message,
            session_id=session_id,
            db=db
        )
        
        return ExpressQuoteChatResponse(
            response=result.get("response", ""),
            session_id=session_id,
            current_step=result.get("current_step", 1),
            collected_data=CollectedDataResponse(
                selectedModels=result.get("collected_data", {}).get("selectedModels", []),
                modelConfigs=result.get("collected_data", {}).get("modelConfigs", {}),
                customerInfo=result.get("collected_data", {}).get("customerInfo", {})
            ),
            preview_table=result.get("preview_table"),
            ready_to_export=result.get("ready_to_export", False),
            export_filename=result.get("export_filename"),
            suggested_options=result.get("suggested_options", []),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"[ExpressQuote] Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"处理请求失败: {str(e)}")


@router.post("/export", response_model=ExpressQuoteExportResponse)
async def express_quote_export(
    request: ExpressQuoteExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    导出极速报价单为Excel
    
    复用现有的export API，确保格式一致
    """
    try:
        # 获取导出数据
        export_data = express_orchestrator.get_export_data(request.session_id)
        
        if not export_data.get("selectedModels"):
            return ExpressQuoteExportResponse(
                success=False,
                message="报价单为空，请先选择模型"
            )
        
        if not export_data.get("customerInfo", {}).get("customerName"):
            return ExpressQuoteExportResponse(
                success=False,
                message="请先填写客户信息"
            )
        
        # 调用现有的export preview函数
        from app.api.v1.endpoints.export import export_quote_preview, QuotePreviewRequest
        
        # 构建请求对象
        preview_request = QuotePreviewRequest(
            customerInfo=export_data.get("customerInfo", {}),
            selectedModels=export_data.get("selectedModels", []),
            modelConfigs=export_data.get("modelConfigs", {}),
            specDiscounts=export_data.get("specDiscounts", {}),
            dailyUsages=export_data.get("dailyUsages", {}),
            priceUnit=export_data.get("priceUnit", "thousand")
        )
        
        result = await export_quote_preview(preview_request)
        
        if result.get("success"):
            filename = result.get("filename")
            return ExpressQuoteExportResponse(
                success=True,
                filename=filename,
                message="报价单生成成功",
                download_url=f"/api/v1/export/download/file/{filename}"
            )
        else:
            return ExpressQuoteExportResponse(
                success=False,
                message=result.get("error", "导出失败")
            )
            
    except Exception as e:
        logger.error(f"[ExpressQuote] Export error: {e}")
        return ExpressQuoteExportResponse(
            success=False,
            message=f"导出失败: {str(e)}"
        )


@router.get("/session/{session_id}")
async def get_session_data(session_id: str):
    """
    获取会话数据
    
    用于前端恢复会话状态
    """
    try:
        export_data = express_orchestrator.get_export_data(session_id)
        return {
            "success": True,
            "session_id": session_id,
            "data": export_data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    清除会话
    
    重新开始报价流程
    """
    try:
        express_orchestrator.clear_session(session_id)
        return {"success": True, "message": "会话已清除"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/welcome")
async def get_welcome_message():
    """
    获取欢迎消息
    
    用于初始化对话界面
    """
    return {
        "message": "我是报价侠，我可以帮您快速生成大模型报价单。请告诉我您需要哪些模型？\n\n您可以：\n• 直接说模型名称（如 qwen3-max）\n• 选择具体规格信息，输出报单预览\n• 预览后可以继续追加模型规格",
        "suggested_options": ["qwen3-Max", "qwen-Plus", "qwen-Flash", "qwen3-vl-plus", "qwen3-vl-flash", "qwen3-asr-flash", "qwen3-tts-flash", "Qwen-image", "wan2.6-t2v"]
    }
