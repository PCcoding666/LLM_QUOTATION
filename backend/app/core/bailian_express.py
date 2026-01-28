"""
百炼客户端配置 - 极速报价专用 (qwen3-max)
"""
import os
from typing import Optional
from openai import AsyncOpenAI
from loguru import logger


# 百炼配置
BAILIAN_EXPRESS_CONFIG = {
    "api_key": os.getenv("EXPRESS_QUOTE_API_KEY", "sk-fd63cbfb91c94e988a328c9730737025"),
    "model": os.getenv("EXPRESS_QUOTE_MODEL", "qwen-max"),
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
}


class BailianExpressClient:
    """百炼客户端 - 极速报价专用"""
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=BAILIAN_EXPRESS_CONFIG["api_key"],
            base_url=BAILIAN_EXPRESS_CONFIG["base_url"]
        )
        self.model = BAILIAN_EXPRESS_CONFIG["model"]
    
    async def chat(
        self,
        messages: list,
        tools: Optional[list] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> dict:
        """
        发送聊天请求
        
        Args:
            messages: 消息列表
            tools: Function Calling工具定义
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            响应字典，包含content和可能的tool_calls
        """
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
            
            response = await self.client.chat.completions.create(**kwargs)
            
            message = response.choices[0].message
            result = {
                "content": message.content or "",
                "role": "assistant"
            }
            
            # 处理tool_calls
            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            
            return result
            
        except Exception as e:
            logger.error(f"[BailianExpress] Chat error: {e}")
            raise


# 全局客户端实例
bailian_express_client = BailianExpressClient()
