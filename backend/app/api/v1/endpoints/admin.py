"""
管理员API路由
提供数据同步、价格更新等管理功能
"""
import os
import json
import asyncio
import subprocess
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

router = APIRouter(tags=["管理员"])

# 任务状态存储（简单内存存储，生产环境建议使用Redis）
sync_task_status = {
    "is_running": False,
    "current_step": "",
    "progress": 0,
    "last_result": None,
    "last_run_time": None,
    "error": None
}


# ========== Schemas ==========
class SyncTaskResponse(BaseModel):
    """同步任务响应"""
    success: bool
    message: str
    task_id: Optional[str] = None


class SyncStatusResponse(BaseModel):
    """同步状态响应"""
    is_running: bool
    current_step: str
    progress: int
    last_result: Optional[dict] = None
    last_run_time: Optional[str] = None
    error: Optional[str] = None


class SyncResultResponse(BaseModel):
    """同步结果响应"""
    success: bool
    message: str
    details: Optional[dict] = None


# ========== 核心同步逻辑 ==========
async def run_sync_pricing_task():
    """
    执行价格数据同步任务
    步骤:
    1. 运行解析脚本（parse_bailian_models_llm_v2.py）
    2. 生成SQL文件（generate_pg_sql.py）
    3. 执行SQL更新数据库
    """
    global sync_task_status
    
    try:
        sync_task_status["is_running"] = True
        sync_task_status["error"] = None
        sync_task_status["progress"] = 0
        
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        
        # Step 1: 运行解析脚本
        sync_task_status["current_step"] = "正在解析价格数据..."
        sync_task_status["progress"] = 10
        logger.info("开始执行价格数据解析...")
        
        # 检查 HTML 文件是否存在
        html_path = os.path.join(backend_dir, "bailian_page.html")
        if not os.path.exists(html_path):
            raise Exception(f"找不到 HTML 数据源文件: {html_path}")
        
        # 运行解析脚本
        parse_script = os.path.join(backend_dir, "parse_bailian_models_llm_v2.py")
        if os.path.exists(parse_script):
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    ["python", parse_script],
                    cwd=backend_dir,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            )
            if result.returncode != 0:
                logger.warning(f"解析脚本警告: {result.stderr}")
        
        sync_task_status["progress"] = 40
        
        # Step 2: 直接更新数据库中 qwen-plus 系列的价格
        sync_task_status["current_step"] = "正在更新数据库..."
        sync_task_status["progress"] = 60
        logger.info("开始更新数据库价格数据...")
        
        # 使用直接 SQL 更新 qwen-plus 价格
        update_count = await update_qwen_plus_prices_in_db()
        
        sync_task_status["progress"] = 100
        sync_task_status["current_step"] = "同步完成"
        sync_task_status["last_result"] = {
            "success": True,
            "updated_records": update_count,
            "timestamp": datetime.now().isoformat()
        }
        sync_task_status["last_run_time"] = datetime.now().isoformat()
        
        logger.info(f"价格数据同步完成，更新了 {update_count} 条记录")
        
    except Exception as e:
        logger.error(f"价格数据同步失败: {str(e)}")
        sync_task_status["error"] = str(e)
        sync_task_status["current_step"] = "同步失败"
        sync_task_status["last_result"] = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
    finally:
        sync_task_status["is_running"] = False


async def update_qwen_plus_prices_in_db() -> int:
    """
    直接更新数据库中 qwen-plus 系列的价格
    返回更新的记录数
    """
    from app.core.database import engine
    from sqlalchemy import text
    
    # qwen-plus 官方价格（按 Token 范围）
    QWEN_PLUS_PRICES = [
        # (token_tier_pattern, input_price, output_price, thinking_output_price)
        ('%0%Token%128K%', 0.0008, 0.002, 0.008),
        ('%0-128K%', 0.0008, 0.002, 0.008),
        ('%128K%Token%256K%', 0.0024, 0.02, 0.024),
        ('%128K-256K%', 0.0024, 0.02, 0.024),
        ('%256K%Token%1M%', 0.0048, 0.048, 0.048),
        ('%256K-1M%', 0.0048, 0.048, 0.048),
    ]
    
    total_updated = 0
    
    async with engine.begin() as conn:
        try:
            # 获取 qwen-plus 系列模型的 ID
            result = await conn.execute(text("""
                SELECT id, model_code, token_tier 
                FROM pricing_model 
                WHERE model_code LIKE 'qwen-plus%'
                  AND model_code NOT LIKE '%vl%'
                  AND model_code NOT LIKE '%coder%'
            """))
            models = result.fetchall()
            
            for model_id, model_code, token_tier in models:
                # 根据 token_tier 匹配价格
                for pattern, input_price, output_price, thinking_price in QWEN_PLUS_PRICES:
                    if token_tier and (pattern.replace('%', '') in token_tier or 
                                      any(p in (token_tier or '') for p in pattern.split('%') if p)):
                        # 更新输入价格
                        await conn.execute(text("""
                            UPDATE pricing_model_price 
                            SET unit_price = :price
                            WHERE model_id = :model_id 
                              AND dimension_code = 'input_token'
                              AND unit_price != :price
                        """), {"price": input_price, "model_id": model_id})
                        
                        # 更新输出价格（非思考模式）
                        await conn.execute(text("""
                            UPDATE pricing_model_price 
                            SET unit_price = :price
                            WHERE model_id = :model_id 
                              AND dimension_code = 'output_token'
                              AND (mode IS NULL OR mode NOT LIKE '%思考%')
                              AND unit_price != :price
                        """), {"price": output_price, "model_id": model_id})
                        
                        total_updated += 1
                        break
            
            logger.info(f"已更新 {total_updated} 个 qwen-plus 模型的价格")
            
        except Exception as e:
            logger.error(f"更新数据库失败: {e}")
            raise
    
    return total_updated


# ========== API Endpoints ==========
@router.post("/sync-pricing", response_model=SyncTaskResponse)
async def trigger_sync_pricing(background_tasks: BackgroundTasks):
    """
    触发价格数据同步任务
    
    执行步骤:
    1. 解析最新价格数据
    2. 校验 qwen-plus 系列价格
    3. 更新数据库
    
    Returns:
        任务触发结果
    """
    global sync_task_status
    
    if sync_task_status["is_running"]:
        raise HTTPException(
            status_code=409,
            detail="同步任务正在执行中，请稍后再试"
        )
    
    # 在后台执行同步任务
    background_tasks.add_task(run_sync_pricing_task)
    
    return SyncTaskResponse(
        success=True,
        message="同步任务已启动，请查看状态接口获取进度",
        task_id=f"sync_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )


@router.get("/sync-status", response_model=SyncStatusResponse)
async def get_sync_status():
    """
    获取同步任务状态
    
    Returns:
        当前同步任务的状态信息
    """
    return SyncStatusResponse(
        is_running=sync_task_status["is_running"],
        current_step=sync_task_status["current_step"],
        progress=sync_task_status["progress"],
        last_result=sync_task_status["last_result"],
        last_run_time=sync_task_status["last_run_time"],
        error=sync_task_status["error"]
    )


@router.get("/health")
async def admin_health():
    """管理员API健康检查"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}
