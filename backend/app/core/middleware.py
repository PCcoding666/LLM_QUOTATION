"""
统一异常处理和日志中间件

提供：
1. 全局异常捕获和友好错误响应
2. 请求/响应日志记录
3. 请求追踪ID
4. 性能监控
"""
import time
import uuid
import traceback
from typing import Callable, Any
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError
from loguru import logger
import sys


# ==================== 自定义异常类 ====================

class AppException(Exception):
    """应用基础异常类"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        status_code: int = 500,
        details: dict = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationException(AppException):
    """数据验证异常"""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class NotFoundException(AppException):
    """资源不存在异常"""
    
    def __init__(self, resource: str, resource_id: str = None):
        message = f"{resource}不存在"
        if resource_id:
            message = f"{resource} [{resource_id}] 不存在"
        super().__init__(
            message=message,
            error_code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "resource_id": resource_id}
        )


class BusinessException(AppException):
    """业务逻辑异常"""
    
    def __init__(self, message: str, error_code: str = "BUSINESS_ERROR", details: dict = None):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=400,
            details=details
        )


class AuthenticationException(AppException):
    """认证异常"""
    
    def __init__(self, message: str = "认证失败"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AuthorizationException(AppException):
    """授权异常"""
    
    def __init__(self, message: str = "无权限访问"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403
        )


# ==================== 日志配置 ====================

def configure_logging(app_name: str = "报价侠"):
    """配置loguru日志"""
    # 移除默认处理器
    logger.remove()
    
    # 控制台输出格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<blue>[{extra[request_id]}]</blue> - "
        "<level>{message}</level>"
    )
    
    # 文件输出格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "[{extra[request_id]}] | "
        "{message}"
    )
    
    # 添加控制台处理器
    logger.add(
        sys.stderr,
        format=console_format,
        level="INFO",
        colorize=True,
        filter=lambda record: record["extra"].setdefault("request_id", "-")
    )
    
    # 添加文件处理器 - 一般日志
    logger.add(
        f"logs/{app_name}_{{time:YYYY-MM-DD}}.log",
        format=file_format,
        level="INFO",
        rotation="00:00",
        retention="30 days",
        compression="gz",
        filter=lambda record: record["extra"].setdefault("request_id", "-")
    )
    
    # 添加文件处理器 - 错误日志
    logger.add(
        f"logs/{app_name}_error_{{time:YYYY-MM-DD}}.log",
        format=file_format,
        level="ERROR",
        rotation="00:00",
        retention="60 days",
        compression="gz",
        filter=lambda record: record["extra"].setdefault("request_id", "-")
    )
    
    return logger


# ==================== 请求上下文 ====================

class RequestContext:
    """请求上下文管理"""
    
    _context = {}
    
    @classmethod
    def set(cls, key: str, value: Any):
        cls._context[key] = value
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        return cls._context.get(key, default)
    
    @classmethod
    def clear(cls):
        cls._context.clear()
    
    @classmethod
    def get_request_id(cls) -> str:
        return cls.get("request_id", "-")


# ==================== 中间件 ====================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        RequestContext.set("request_id", request_id)
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取请求信息
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query = str(request.query_params) if request.query_params else ""
        
        # 日志绑定请求ID
        with logger.contextualize(request_id=request_id):
            # 记录请求开始
            logger.info(f"请求开始 | {method} {path} | IP: {client_ip} | Query: {query}")
            
            try:
                # 处理请求
                response = await call_next(request)
                
                # 计算耗时
                process_time = round((time.time() - start_time) * 1000, 2)
                
                # 记录请求完成
                logger.info(
                    f"请求完成 | {method} {path} | "
                    f"Status: {response.status_code} | "
                    f"耗时: {process_time}ms"
                )
                
                # 添加响应头
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Process-Time"] = f"{process_time}ms"
                
                return response
                
            except Exception as e:
                # 计算耗时
                process_time = round((time.time() - start_time) * 1000, 2)
                
                # 记录异常
                logger.error(
                    f"请求异常 | {method} {path} | "
                    f"Error: {str(e)} | "
                    f"耗时: {process_time}ms"
                )
                raise
            finally:
                RequestContext.clear()


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""
    
    # 慢请求阈值（毫秒）
    SLOW_REQUEST_THRESHOLD = 1000
    
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = (time.time() - start_time) * 1000
        
        # 记录慢请求
        if process_time > self.SLOW_REQUEST_THRESHOLD:
            request_id = getattr(request.state, "request_id", "-")
            with logger.contextualize(request_id=request_id):
                logger.warning(
                    f"慢请求警告 | {request.method} {request.url.path} | "
                    f"耗时: {process_time:.2f}ms"
                )
        
        return response


# ==================== 异常处理器 ====================

def create_error_response(
    request: Request,
    error_code: str,
    message: str,
    status_code: int,
    details: dict = None
) -> JSONResponse:
    """创建统一的错误响应"""
    request_id = getattr(request.state, "request_id", "-")
    
    response_body = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "path": str(request.url.path)
        }
    }
    
    return JSONResponse(
        status_code=status_code,
        content=response_body
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理应用自定义异常"""
    request_id = getattr(request.state, "request_id", "-")
    
    with logger.contextualize(request_id=request_id):
        logger.error(f"应用异常 | {exc.error_code}: {exc.message}")
    
    return create_error_response(
        request=request,
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """处理HTTP异常"""
    request_id = getattr(request.state, "request_id", "-")
    
    with logger.contextualize(request_id=request_id):
        logger.warning(f"HTTP异常 | {exc.status_code}: {exc.detail}")
    
    # 映射状态码到错误码
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        408: "REQUEST_TIMEOUT",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = error_code_map.get(exc.status_code, "HTTP_ERROR")
    
    return create_error_response(
        request=request,
        error_code=error_code,
        message=str(exc.detail),
        status_code=exc.status_code
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """处理请求验证异常"""
    request_id = getattr(request.state, "request_id", "-")
    
    # 提取验证错误详情
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    with logger.contextualize(request_id=request_id):
        logger.warning(f"验证错误 | {errors}")
    
    # 生成友好的错误消息
    if len(errors) == 1:
        message = f"参数验证失败: {errors[0]['field']} - {errors[0]['message']}"
    else:
        message = f"多个参数验证失败，请检查请求参数"
    
    return create_error_response(
        request=request,
        error_code="VALIDATION_ERROR",
        message=message,
        status_code=422,
        details={"validation_errors": errors}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的异常"""
    request_id = getattr(request.state, "request_id", "-")
    
    # 获取异常堆栈
    tb = traceback.format_exc()
    
    with logger.contextualize(request_id=request_id):
        logger.error(f"未捕获异常 | {type(exc).__name__}: {str(exc)}\n{tb}")
    
    return create_error_response(
        request=request,
        error_code="INTERNAL_SERVER_ERROR",
        message="服务器内部错误，请稍后重试",
        status_code=500,
        details={"exception_type": type(exc).__name__}
    )


# ==================== 注册函数 ====================

def register_exception_handlers(app: FastAPI):
    """注册异常处理器"""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)


def register_middlewares(app: FastAPI):
    """注册中间件"""
    # 注意：中间件按照添加的相反顺序执行
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(RequestLoggingMiddleware)


def setup_error_handling(app: FastAPI):
    """
    设置完整的错误处理和日志系统
    
    在main.py中调用：
    from app.core.middleware import setup_error_handling
    setup_error_handling(app)
    """
    # 配置日志
    configure_logging()
    
    # 注册中间件
    register_middlewares(app)
    
    # 注册异常处理器
    register_exception_handlers(app)
    
    logger.info("错误处理和日志中间件已初始化")
