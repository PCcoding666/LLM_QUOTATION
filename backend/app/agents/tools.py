"""
Function Calling Tools
Provides tools for AI agent to extract entities, estimate usage, and calculate prices
"""
import json
from typing import Dict, Any, List, Optional
from decimal import Decimal
from loguru import logger

from app.services.pricing_engine import pricing_engine
from app.services.competitor_service import competitor_service
from app.core.database import async_session_maker
from sqlalchemy import select, text


class FunctionTools:
    """Function Calling tool collection for AI agents"""
    
    @staticmethod
    def get_tool_definitions() -> list:
        """Get all tool definitions for Function Calling"""
        return [
            {
                "name": "extract_and_respond",
                "description": "Extract product requirement entities from user input and generate response. Call this when user describes their product needs.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_name": {
                            "type": "string",
                            "description": "Product or model name (e.g., qwen-max, qwen-plus, gpt-4, A10, V100)"
                        },
                        "product_type": {
                            "type": "string",
                            "enum": ["llm", "gpu", "storage", "network", "other"],
                            "description": "Product type category"
                        },
                        "use_case": {
                            "type": "string",
                            "description": "Usage scenario (e.g., customer service, content generation, training, inference)"
                        },
                        "quantity": {
                            "type": "integer",
                            "description": "Number of units/instances needed"
                        },
                        "duration_months": {
                            "type": "integer",
                            "description": "Duration in months"
                        },
                        "call_frequency": {
                            "type": "integer",
                            "description": "Expected monthly API call count (for LLM products)"
                        },
                        "estimated_tokens_per_call": {
                            "type": "integer",
                            "description": "Estimated tokens per API call (for LLM products)"
                        },
                        "region": {
                            "type": "string",
                            "description": "Deployment region (e.g., cn-beijing, cn-shanghai)"
                        },
                        "additional_requirements": {
                            "type": "string",
                            "description": "Any additional requirements mentioned"
                        }
                    },
                    "required": ["product_name", "product_type"]
                }
            },
            {
                "name": "search_models",
                "description": "搜索大模型产品，支持按名称、类别、功能搜索。用于回答用户关于有哪些模型、模型推荐等问题",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词，如模型名称(qwen、通义)、类别(文本、语音、视觉)、场景(客服、写作)"
                        },
                        "category": {
                            "type": "string",
                            "description": "产品类别，如：文本生成、视觉理解、语音、向量"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回数量限制，默认5"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_model_price",
                "description": "查询指定模型的价格信息。用于回答用户关于某个模型多少钱的问题",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model_name": {
                            "type": "string",
                            "description": "模型名称，如qwen-max、qwen-plus"
                        }
                    },
                    "required": ["model_name"]
                }
            },
            {
                "name": "calculate_monthly_cost",
                "description": "根据用量估算月费用。用于回答用户关于每月花费多少钱的问题",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model_name": {
                            "type": "string",
                            "description": "模型名称"
                        },
                        "daily_calls": {
                            "type": "integer",
                            "description": "每日调用次数"
                        },
                        "avg_input_tokens": {
                            "type": "integer",
                            "description": "平均每次输入token数，默认1000"
                        },
                        "avg_output_tokens": {
                            "type": "integer",
                            "description": "平均每次输出token数，默认500"
                        }
                    },
                    "required": ["model_name", "daily_calls"]
                }
            },
            {
                "name": "recommend_model",
                "description": "根据用户场景和预算推荐合适的模型",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "use_case": {
                            "type": "string",
                            "description": "使用场景，如：智能客服、内容生成、代码助手、数据分析"
                        },
                        "budget": {
                            "type": "number",
                            "description": "月预算(元)，可选"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["cost", "performance", "balanced"],
                            "description": "优先考虑因素：cost=成本优先, performance=效果优先, balanced=均衡"
                        }
                    },
                    "required": ["use_case"]
                }
            },
            {
                "name": "extract_entities",
                "description": "从用户输入文本中提取产品需求实体信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "用户输入的原始文本"
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "estimate_llm_usage",
                "description": "Estimate LLM product usage based on use case and workload. Returns token estimates, call frequency, and mode recommendations.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "use_case": {
                            "type": "string",
                            "description": "Usage scenario description"
                        },
                        "workload": {
                            "type": "string",
                            "description": "Workload description (e.g., high frequency, batch processing)"
                        },
                        "product_name": {
                            "type": "string",
                            "description": "LLM product name"
                        }
                    },
                    "required": ["use_case", "workload"]
                }
            },
            {
                "name": "calculate_price",
                "description": "Calculate product price with support for Token pricing, thinking mode, Batch discount, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_type": {
                            "type": "string",
                            "enum": ["llm", "standard"],
                            "description": "Product type"
                        },
                        "product_name": {
                            "type": "string",
                            "description": "Product name for price lookup"
                        },
                        "context": {
                            "type": "object",
                            "description": "Pricing context including tokens, call frequency, quantity, etc."
                        }
                    },
                    "required": ["product_type", "product_name", "context"]
                }
            },
            {
                "name": "generate_quote_item",
                "description": "生成报价项，将模型配置转换为可添加到报价单的结构化数据。当用户确认要添加某个模型到报价单时调用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model_name": {
                            "type": "string",
                            "description": "模型名称"
                        },
                        "daily_calls": {
                            "type": "integer",
                            "description": "每日调用次数"
                        },
                        "avg_input_tokens": {
                            "type": "integer",
                            "description": "平均输入token数，默认1000"
                        },
                        "avg_output_tokens": {
                            "type": "integer",
                            "description": "平均输出token数，默认500"
                        },
                        "duration_months": {
                            "type": "integer",
                            "description": "使用时长(月)，默认1"
                        }
                    },
                    "required": ["model_name"]
                }
            },
            {
                "name": "create_quote_summary",
                "description": "生成报价单摘要，汇总所有已添加的报价项。当用户要求查看报价单或确认报价时调用",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "description": "报价项列表",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "model_name": {"type": "string"},
                                    "monthly_cost": {"type": "number"}
                                }
                            }
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "客户名称"
                        }
                    },
                    "required": ["items"]
                }
            }
        ]
    
    @staticmethod
    async def extract_and_respond(
        product_name: str,
        product_type: str,
        use_case: Optional[str] = None,
        quantity: Optional[int] = None,
        duration_months: Optional[int] = None,
        call_frequency: Optional[int] = None,
        estimated_tokens_per_call: Optional[int] = None,
        region: Optional[str] = None,
        additional_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process extracted entities from user input and generate response with price estimation.
        This is called by the AI model with structured entities extracted from natural language.
        """
        logger.info(f"[Tools] extract_and_respond called: product={product_name}, type={product_type}")
        
        # Build entities dict
        entities = {
            "product_name": product_name,
            "product_type": product_type,
            "use_case": use_case,
            "quantity": quantity or 1,
            "duration_months": duration_months or 1,
            "call_frequency": call_frequency,
            "estimated_tokens_per_call": estimated_tokens_per_call,
            "region": region or "cn-beijing",
            "additional_requirements": additional_requirements
        }
        
        # Get product price from mock data
        price_info = FunctionTools._get_product_price(product_name, product_type)
        
        # Calculate price based on product type
        if product_type == "llm":
            # LLM products: token-based pricing
            tokens_per_call = estimated_tokens_per_call or 1000
            monthly_calls = call_frequency or 10000
            total_tokens = tokens_per_call * monthly_calls * (duration_months or 1)
            
            price_result = pricing_engine.calculate(
                Decimal(str(price_info["input_price"])),
                {
                    "product_type": "llm",
                    "input_token_price": price_info["input_price"],
                    "output_token_price": price_info["output_price"],
                    "input_tokens": int(total_tokens * 0.7),  # 70% input
                    "output_tokens": int(total_tokens * 0.3),  # 30% output
                    "thinking_mode_ratio": 0.0,
                    "batch_call_ratio": 0.0
                }
            )
        else:
            # Standard products: quantity * duration pricing
            price_result = pricing_engine.calculate(
                Decimal(str(price_info.get("unit_price", 100))),
                {
                    "product_type": "standard",
                    "quantity": quantity or 1,
                    "duration_months": duration_months or 1
                }
            )
        
        return {
            "entities": entities,
            "price_info": price_info,
            "price_calculation": price_result,
            "summary": FunctionTools._generate_summary(entities, price_result)
        }
    
    @staticmethod
    def _get_product_price(product_name: str, product_type: str) -> Dict[str, Any]:
        """
        Get product price from mock data (will be replaced with database lookup)
        """
        # Mock LLM product prices (per 1000 tokens, in CNY)
        llm_prices = {
            "qwen-max": {"input_price": 0.02, "output_price": 0.06, "name": "Qwen-Max"},
            "qwen-plus": {"input_price": 0.004, "output_price": 0.012, "name": "Qwen-Plus"},
            "qwen-turbo": {"input_price": 0.002, "output_price": 0.006, "name": "Qwen-Turbo"},
            "qwen-long": {"input_price": 0.0005, "output_price": 0.002, "name": "Qwen-Long"},
            "qwen-vl-max": {"input_price": 0.02, "output_price": 0.06, "name": "Qwen-VL-Max"},
            "qwen-vl-plus": {"input_price": 0.008, "output_price": 0.02, "name": "Qwen-VL-Plus"},
        }
        
        # Mock GPU prices (per hour, in CNY)
        gpu_prices = {
            "a10": {"unit_price": 15.0, "name": "NVIDIA A10", "memory": "24GB"},
            "v100": {"unit_price": 25.0, "name": "NVIDIA V100", "memory": "32GB"},
            "a100": {"unit_price": 45.0, "name": "NVIDIA A100", "memory": "80GB"},
        }
        
        product_key = product_name.lower().replace("-", "-").replace("_", "-")
        
        if product_type == "llm":
            return llm_prices.get(product_key, llm_prices["qwen-plus"])
        elif product_type == "gpu":
            return gpu_prices.get(product_key, gpu_prices["a10"])
        else:
            return {"unit_price": 100.0, "name": product_name}
    
    @staticmethod
    def _generate_summary(entities: Dict[str, Any], price_result: Dict[str, Any]) -> str:
        """Generate a summary message"""
        product = entities.get("product_name", "Unknown")
        final_price = price_result.get("final_price", 0)
        
        summary_parts = [f"Product: {product}"]
        
        if entities.get("use_case"):
            summary_parts.append(f"Use case: {entities['use_case']}")
        if entities.get("call_frequency"):
            summary_parts.append(f"Monthly calls: {entities['call_frequency']:,}")
        if entities.get("quantity") and entities.get("quantity") > 1:
            summary_parts.append(f"Quantity: {entities['quantity']}")
        if entities.get("duration_months"):
            summary_parts.append(f"Duration: {entities['duration_months']} months")
        
        summary_parts.append(f"Estimated cost: ¥{final_price:,.2f}")
        
        return " | ".join(summary_parts)
    
    @staticmethod
    async def extract_entities(text: str) -> Dict[str, Any]:
        """
        Legacy entity extraction using regex (kept for backward compatibility)
        """
        import re
        
        entities = {
            "product_name": None,
            "product_type": None,
            "quantity": None,
            "duration_months": None,
            "use_case": None,
            "region": None
        }
        
        # Extract quantity
        quantity_match = re.search(r'(\d+)\s*[张个台块万]', text)
        if quantity_match:
            entities["quantity"] = int(quantity_match.group(1))
        
        # Extract duration
        duration_match = re.search(r'(\d+)\s*[个]?月', text)
        if duration_match:
            entities["duration_months"] = int(duration_match.group(1))
        
        # Extract call frequency
        freq_match = re.search(r'(\d+)\s*万?\s*次', text)
        if freq_match:
            freq = int(freq_match.group(1))
            if '万' in text:
                freq *= 10000
            entities["call_frequency"] = freq
        
        # Detect product type and name
        text_lower = text.lower()
        if any(x in text_lower for x in ['qwen', 'gpt', '大模型', '对话', 'llm']):
            entities["product_type"] = "llm"
            if 'qwen-max' in text_lower or 'qwen max' in text_lower:
                entities["product_name"] = "qwen-max"
            elif 'qwen-plus' in text_lower or 'qwen plus' in text_lower:
                entities["product_name"] = "qwen-plus"
            else:
                entities["product_name"] = "qwen-plus"  # default
        elif any(x in text_lower for x in ['a10', 'v100', 'a100', 'gpu', '显卡']):
            entities["product_type"] = "gpu"
            if 'a10' in text_lower:
                entities["product_name"] = "a10"
            elif 'v100' in text_lower:
                entities["product_name"] = "v100"
            elif 'a100' in text_lower:
                entities["product_name"] = "a100"
        
        # Detect use case
        if '训练' in text:
            entities["use_case"] = "training"
        elif '推理' in text:
            entities["use_case"] = "inference"
        elif '客服' in text or '对话' in text:
            entities["use_case"] = "customer_service"
        elif '内容' in text or '生成' in text:
            entities["use_case"] = "content_generation"
        
        return entities
    
    @staticmethod
    async def estimate_llm_usage(
        use_case: str,
        workload: str,
        product_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate LLM product usage based on use case and workload.
        """
        logger.info(f"[Tools] estimate_llm_usage: use_case={use_case}, workload={workload}")
        
        # Usage templates by scenario
        usage_templates = {
            "customer_service": {
                "estimated_tokens_per_call": 800,
                "call_frequency": 50000,
                "thinking_mode_ratio": 0.0,
                "batch_call_ratio": 0.0,
                "recommended_model": "qwen-turbo"
            },
            "content_generation": {
                "estimated_tokens_per_call": 2000,
                "call_frequency": 10000,
                "thinking_mode_ratio": 0.3,
                "batch_call_ratio": 0.5,
                "recommended_model": "qwen-plus"
            },
            "code_generation": {
                "estimated_tokens_per_call": 1500,
                "call_frequency": 5000,
                "thinking_mode_ratio": 0.5,
                "batch_call_ratio": 0.2,
                "recommended_model": "qwen-max"
            },
            "data_analysis": {
                "estimated_tokens_per_call": 3000,
                "call_frequency": 2000,
                "thinking_mode_ratio": 0.4,
                "batch_call_ratio": 0.6,
                "recommended_model": "qwen-long"
            },
            "default": {
                "estimated_tokens_per_call": 1000,
                "call_frequency": 10000,
                "thinking_mode_ratio": 0.2,
                "batch_call_ratio": 0.3,
                "recommended_model": "qwen-plus"
            }
        }
        
        # Match use case to template
        use_case_lower = use_case.lower()
        if any(x in use_case_lower for x in ['客服', 'customer', 'chat', '对话']):
            template = usage_templates["customer_service"]
        elif any(x in use_case_lower for x in ['内容', 'content', '生成', 'writing']):
            template = usage_templates["content_generation"]
        elif any(x in use_case_lower for x in ['代码', 'code', '编程', 'programming']):
            template = usage_templates["code_generation"]
        elif any(x in use_case_lower for x in ['数据', 'data', '分析', 'analysis']):
            template = usage_templates["data_analysis"]
        else:
            template = usage_templates["default"]
        
        # Adjust based on workload
        workload_lower = workload.lower()
        if any(x in workload_lower for x in ['高频', 'high', '大量', 'heavy']):
            template["call_frequency"] = int(template["call_frequency"] * 2)
        elif any(x in workload_lower for x in ['低频', 'low', '少量', 'light']):
            template["call_frequency"] = int(template["call_frequency"] * 0.5)
        
        template["use_case"] = use_case
        template["workload"] = workload
        template["recommendation"] = (
            f"Based on '{use_case}' scenario and '{workload}' workload:\n"
            f"- Estimated tokens per call: {template['estimated_tokens_per_call']:,}\n"
            f"- Monthly call frequency: {template['call_frequency']:,}\n"
            f"- Thinking mode ratio: {template['thinking_mode_ratio']*100:.0f}%\n"
            f"- Batch call ratio: {template['batch_call_ratio']*100:.0f}%\n"
            f"- Recommended model: {template['recommended_model']}"
        )
        
        return template
    
    @staticmethod
    async def calculate_price(
        product_type: str,
        product_name: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate price for a product.
        """
        logger.info(f"[Tools] calculate_price: type={product_type}, name={product_name}")
        
        # Get product price
        price_info = FunctionTools._get_product_price(product_name, product_type)
        
        if product_type == "llm":
            # Use input price as base for LLM
            base_price = Decimal(str(price_info.get("input_price", 0.01)))
            context["input_token_price"] = price_info.get("input_price", 0.01)
            context["output_token_price"] = price_info.get("output_price", 0.03)
        else:
            base_price = Decimal(str(price_info.get("unit_price", 100)))
        
        result = pricing_engine.calculate(
            base_price,
            {**context, "product_type": product_type}
        )
        
        result["product_name"] = product_name
        result["price_info"] = price_info
        
        return result
    
    @staticmethod
    async def search_models(
        keyword: str = None,
        category: str = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """搜索模型"""
        try:
            async with async_session_maker() as session:
                sql = """
                    SELECT p.product_code, p.product_name, p.category, p.vendor,
                           pp.unit_price, pp.unit, pp.pricing_variables
                    FROM products p
                    LEFT JOIN product_prices pp ON p.product_code = pp.product_code
                    WHERE p.status = 'active'
                """
                params = {}
                
                if keyword:
                    sql += " AND (p.product_name ILIKE :keyword OR p.category ILIKE :keyword)"
                    params["keyword"] = f"%{keyword}%"
                
                if category:
                    sql += " AND p.category ILIKE :category"
                    params["category"] = f"%{category}%"
                
                sql += " LIMIT :limit"
                params["limit"] = limit
                
                result = await session.execute(text(sql), params)
                rows = result.fetchall()
                
                models = []
                for row in rows:
                    pricing_vars = row.pricing_variables or {}
                    models.append({
                        "model_id": row.product_code,
                        "model_name": row.product_name,
                        "category": row.category,
                        "vendor": row.vendor,
                        "input_price": pricing_vars.get("input_price"),
                        "output_price": pricing_vars.get("output_price"),
                        "unit": row.unit or "千Token"
                    })
                
                return {
                    "found": len(models),
                    "models": models,
                    "message": f"找到 {len(models)} 个模型" if models else "未找到匹配的模型"
                }
        except Exception as e:
            logger.error(f"搜索模型失败: {e}")
            return {"found": 0, "models": [], "error": str(e)}
    
    @staticmethod
    async def get_model_price(model_name: str) -> Dict[str, Any]:
        """查询模型价格"""
        try:
            async with async_session_maker() as session:
                sql = """
                    SELECT p.product_code, p.product_name, p.category,
                           pp.unit_price, pp.unit, pp.billing_mode, pp.pricing_variables
                    FROM products p
                    LEFT JOIN product_prices pp ON p.product_code = pp.product_code
                    WHERE p.product_code ILIKE :name OR p.product_name ILIKE :name
                """
                result = await session.execute(text(sql), {"name": f"%{model_name}%"})
                rows = result.fetchall()
                
                if not rows:
                    return {"found": False, "message": f"未找到模型: {model_name}"}
                
                row = rows[0]
                pricing_vars = row.pricing_variables or {}
                
                return {
                    "found": True,
                    "model_id": row.product_code,
                    "model_name": row.product_name,
                    "category": row.category,
                    "pricing": {
                        "input_price": pricing_vars.get("input_price"),
                        "output_price": pricing_vars.get("output_price"),
                        "unit": row.unit or "千Token",
                        "billing_mode": row.billing_mode
                    },
                    "message": f"{row.product_name} 价格: 输入 {pricing_vars.get('input_price', 'N/A')}元/{row.unit or '千Token'}, 输出 {pricing_vars.get('output_price', 'N/A')}元/{row.unit or '千Token'}"
                }
        except Exception as e:
            logger.error(f"查询价格失败: {e}")
            return {"found": False, "error": str(e)}
    
    @staticmethod
    async def calculate_monthly_cost(
        model_name: str,
        daily_calls: int,
        avg_input_tokens: int = 1000,
        avg_output_tokens: int = 500
    ) -> Dict[str, Any]:
        """计算月费用"""
        price_info = await FunctionTools.get_model_price(model_name)
        
        if not price_info.get("found"):
            return price_info
        
        pricing = price_info.get("pricing", {})
        input_price = pricing.get("input_price", 0) or 0
        output_price = pricing.get("output_price", 0) or 0
        
        # 计算月费用
        monthly_calls = daily_calls * 30
        input_cost = (avg_input_tokens / 1000) * input_price * monthly_calls
        output_cost = (avg_output_tokens / 1000) * output_price * monthly_calls
        total_cost = input_cost + output_cost
        
        return {
            "model_name": price_info["model_name"],
            "daily_calls": daily_calls,
            "monthly_calls": monthly_calls,
            "avg_input_tokens": avg_input_tokens,
            "avg_output_tokens": avg_output_tokens,
            "input_cost": round(input_cost, 2),
            "output_cost": round(output_cost, 2),
            "total_monthly_cost": round(total_cost, 2),
            "message": f"预估月费用: ¥{total_cost:,.2f} (输入: ¥{input_cost:,.2f}, 输出: ¥{output_cost:,.2f})"
        }
    
    @staticmethod
    async def recommend_model(
        use_case: str,
        budget: float = None,
        priority: str = "balanced"
    ) -> Dict[str, Any]:
        """推荐模型（含竞品对比优势）"""
        # 场景到模型的推荐映射
        recommendations = {
            "客服": ["qwen-plus", "qwen-turbo"],
            "智能客服": ["qwen-plus", "qwen-turbo"],
            "对话": ["qwen-plus", "qwen-max"],
            "内容生成": ["qwen-max", "qwen-plus"],
            "写作": ["qwen-max", "qwen-plus"],
            "代码": ["qwen-coder-plus", "qwen-max"],
            "代码助手": ["qwen-coder-plus", "qwen-max"],
            "数据分析": ["qwen-max", "qwen-plus"],
            "图像理解": ["qwen-vl-max", "qwen-vl-plus"],
            "视觉": ["qwen-vl-max", "qwen-vl-plus"],
            "语音": ["cosyvoice-v2", "paraformer-v2"],
        }
        
        # 匹配场景
        matched_models = []
        for key, models in recommendations.items():
            if key in use_case:
                matched_models = models
                break
        
        if not matched_models:
            matched_models = ["qwen-plus", "qwen-max"]  # 默认推荐
        
        # 查询推荐模型的详细信息
        result_models = []
        for model_id in matched_models:
            price_info = await FunctionTools.get_model_price(model_id)
            if price_info.get("found"):
                # 获取竞品优势信息
                competitor_insight = competitor_service.get_insight_for_ai(model_id)
                
                model_result = {
                    "model_id": price_info["model_id"],
                    "model_name": price_info["model_name"],
                    "pricing": price_info["pricing"],
                    "recommendation_reason": f"适合{use_case}场景" if priority == "performance" else "性价比高"
                }
                
                # 如果有竞品数据，添加到推荐理由中
                if competitor_insight:
                    model_result["competitor_advantage"] = competitor_insight
                    model_result["recommendation_reason"] += f"。{competitor_insight}"
                
                result_models.append(model_result)
        
        return {
            "use_case": use_case,
            "priority": priority,
            "recommendations": result_models,
            "message": f"为'{use_case}'场景推荐以下模型" if result_models else "暂无推荐模型"
        }
    
    @staticmethod
    async def generate_quote_item(
        model_name: str,
        daily_calls: int = 1000,
        avg_input_tokens: int = 1000,
        avg_output_tokens: int = 500,
        duration_months: int = 1
    ) -> Dict[str, Any]:
        """生成报价项"""
        # 获取模型价格
        price_info = await FunctionTools.get_model_price(model_name)
        
        if not price_info.get("found"):
            return {"success": False, "error": f"未找到模型: {model_name}"}
        
        # 计算月费用
        cost_info = await FunctionTools.calculate_monthly_cost(
            model_name, daily_calls, avg_input_tokens, avg_output_tokens
        )
        
        monthly_cost = cost_info.get("total_monthly_cost", 0)
        total_cost = monthly_cost * duration_months
        
        # 生成报价项
        quote_item = {
            "id": f"qi_{model_name}_{daily_calls}",
            "model_id": price_info["model_id"],
            "model_name": price_info["model_name"],
            "category": price_info.get("category", "AI-大模型"),
            "config": {
                "daily_calls": daily_calls,
                "avg_input_tokens": avg_input_tokens,
                "avg_output_tokens": avg_output_tokens,
                "duration_months": duration_months
            },
            "pricing": price_info.get("pricing", {}),
            "monthly_cost": monthly_cost,
            "total_cost": round(total_cost, 2),
            "duration_months": duration_months
        }
        
        return {
            "success": True,
            "quote_item": quote_item,
            "action": "add_to_quote",
            "message": f"✅ 已生成报价项:\n- 模型: {price_info['model_name']}\n- 日调用量: {daily_calls:,}次\n- 月费用: ¥{monthly_cost:,.2f}\n- 总费用({duration_months}个月): ¥{total_cost:,.2f}"
        }
    
    @staticmethod
    async def create_quote_summary(
        items: List[Dict[str, Any]],
        customer_name: str = ""
    ) -> Dict[str, Any]:
        """生成报价单摘要"""
        if not items:
            return {
                "success": False,
                "message": "报价单为空，请先添加产品"
            }
        
        total_monthly = sum(item.get("monthly_cost", 0) for item in items)
        total_amount = sum(item.get("total_cost", item.get("monthly_cost", 0)) for item in items)
        
        summary = {
            "success": True,
            "action": "show_quote_summary",
            "quote": {
                "customer_name": customer_name or "未填写",
                "items": items,
                "item_count": len(items),
                "total_monthly": round(total_monthly, 2),
                "total_amount": round(total_amount, 2)
            },
            "message": f"📝 **报价单摘要**\n\n客户: {customer_name or '未填写'}\n产品数: {len(items)}项\n月费用: ¥{total_monthly:,.2f}\n**总金额: ¥{total_amount:,.2f}**"
        }
        
        return summary
    
    @staticmethod
    async def execute_function(function_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a function call from the AI model.
        """
        logger.info(f"[Tools] Executing function: {function_name}")
        
        function_map = {
            "search_models": FunctionTools.search_models,
            "get_model_price": FunctionTools.get_model_price,
            "calculate_monthly_cost": FunctionTools.calculate_monthly_cost,
            "recommend_model": FunctionTools.recommend_model,
            "extract_and_respond": FunctionTools.extract_and_respond,
            "extract_entities": FunctionTools.extract_entities,
            "estimate_llm_usage": FunctionTools.estimate_llm_usage,
            "calculate_price": FunctionTools.calculate_price,
            "generate_quote_item": FunctionTools.generate_quote_item,
            "create_quote_summary": FunctionTools.create_quote_summary
        }
        
        func = function_map.get(function_name)
        if not func:
            logger.error(f"[Tools] Unknown function: {function_name}")
            raise ValueError(f"Unknown function: {function_name}")
        
        return await func(**arguments)


# 创建全局工具实例
function_tools = FunctionTools()
