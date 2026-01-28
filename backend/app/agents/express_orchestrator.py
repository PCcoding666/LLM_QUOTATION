"""
极速报价对话编排器 - 通过Function Calling引导用户完成报价
"""
import json
import uuid
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bailian_express import bailian_express_client
from app.services.pricing_data_service import pricing_data_service


# Function Calling 工具定义
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_models",
            "description": "根据关键词搜索可用的大模型。当用户提到任何模型名称时调用此函数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "模型名称关键词，如 qwen3-max、qwen-plus、cosyvoice 等"
                    }
                },
                "required": ["keyword"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_model_variants",
            "description": "获取指定模型的所有定价规格（不同模式、Token阶梯等）。在search_models找到模型后调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_code": {
                        "type": "string",
                        "description": "模型代码，如 qwen3-max"
                    }
                },
                "required": ["model_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_model_to_quote",
            "description": "将用户选择的模型规格添加到报价单。用户说'第一个'、'全部'、'1和3'等时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_code": {
                        "type": "string",
                        "description": "模型代码"
                    },
                    "variant_indices": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "用户选择的规格序号列表（从1开始），如[1]表示第一个，[1,2,3]表示全部"
                    }
                },
                "required": ["model_code", "variant_indices"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_customer_info",
            "description": "设置客户信息。当用户提供客户名称、折扣等信息时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {
                        "type": "string",
                        "description": "客户名称"
                    },
                    "discount_percent": {
                        "type": "number",
                        "description": "折扣百分比，如10表示9折，15表示85折，0表示无折扣"
                    },
                    "quote_date": {
                        "type": "string",
                        "description": "报价日期，格式YYYY-MM-DD，不提供则默认今天"
                    },
                    "valid_days": {
                        "type": "integer",
                        "description": "有效期天数，默认30天"
                    }
                },
                "required": ["customer_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "set_daily_usage",
            "description": "设置某个模型规格的日估计用量。",
            "parameters": {
                "type": "object",
                "properties": {
                    "model_code": {"type": "string"},
                    "variant_index": {"type": "integer", "description": "规格序号（从1开始）"},
                    "usage": {"type": "number", "description": "日用量（千Token）"}
                },
                "required": ["model_code", "variant_index", "usage"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_quote_preview",
            "description": "生成报价单预览。当用户说'预览'、'看看'、'生成报价单'等时调用。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "export_quote",
            "description": "导出报价单为Excel。当用户说'导出'、'下载'、'生成Excel'等时调用。",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_category_models",
            "description": "获取某个分类下的所有模型。当用户说'文本模型'、'语音模型'、'视觉模型'时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["text", "voice", "vision", "video"],
                        "description": "模型分类：text文本、voice语音、vision视觉理解、video视频生成"
                    }
                },
                "required": ["category"]
            }
        }
    }
]

# System Prompt
SYSTEM_PROMPT = """你是"极速报价助手"，帮助用户快速完成阿里云大模型报价单制作。

## 你的工作流程：
1. **模型选择**：询问用户需要哪些模型，通过search_models搜索，用get_model_variants获取规格
2. **规格确认**：展示模型规格列表，让用户选择具体规格
3. **客户信息**：收集客户名称、折扣等信息
4. **预览导出**：生成预览并导出Excel

## 交互规则：
- 当用户提到模型名称时，先调用search_models搜索
- 搜索到模型后，自动调用get_model_variants获取规格详情
- 用清晰的编号列表展示规格选项，包含价格信息
- 用户说"第一个"、"全部"、"1和2"时，调用add_model_to_quote
- 收集完模型后，询问客户信息（名称必填，折扣可选）
- 用户说"9折"时，折扣百分比是10；"85折"时是15

## 价格展示格式：
- Token计费（price_type=token）：输入: ¥X.XX/千Token | 输出: ¥X.XX/千Token
- 非Token计费（price_type=image/video/audio）：使用fallback_price字段，格式为 ¥X.XX/{price_unit}
- 当input_price和output_price都为null时，必须使用fallback_price展示价格

## 注意事项：
- 保持简洁友好，每次只问一个问题
- 提供快捷选项帮助用户快速选择
- 价格数据从数据库实时获取，确保准确"""


class ExpressQuoteOrchestrator:
    """极速报价对话编排器"""
    
    # 会话存储（生产环境应使用Redis）
    _sessions: Dict[str, Dict] = {}
    
    def __init__(self):
        self.client = bailian_express_client
    
    def _get_session(self, session_id: str) -> Dict:
        """获取或创建会话"""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "messages": [],
                "context": {
                    "selectedModels": [],
                    "modelConfigs": {},
                    "customerInfo": {},
                    "dailyUsages": {},
                    "specDiscounts": {},
                    "currentStep": 1  # 1:模型选择 2:客户信息 3:预览 4:导出
                },
                "temp_variants": {}  # 临时存储查询到的规格
            }
        return self._sessions[session_id]
    
    async def process_message(
        self,
        message: str,
        session_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        处理用户消息
        
        Args:
            message: 用户消息
            session_id: 会话ID
            db: 数据库会话
            
        Returns:
            响应字典
        """
        session = self._get_session(session_id)
        context = session["context"]
        messages = session["messages"]
        
        # 添加用户消息
        messages.append({"role": "user", "content": message})
        
        # 构建完整消息列表
        full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages[-20:]  # 保留最近20条
        
        try:
            # 调用LLM
            response = await self.client.chat(
                messages=full_messages,
                tools=TOOLS,
                temperature=0.7
            )
            
            # 处理tool_calls
            if response.get("tool_calls"):
                tool_results = []
                for tool_call in response["tool_calls"]:
                    func_name = tool_call["function"]["name"]
                    try:
                        args = json.loads(tool_call["function"]["arguments"])
                    except json.JSONDecodeError:
                        args = {}
                    
                    # 执行函数
                    result = await self._execute_function(
                        func_name, args, session, db
                    )
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                
                # 将tool结果添加到消息
                messages.append({
                    "role": "assistant",
                    "content": response.get("content", ""),
                    "tool_calls": response["tool_calls"]
                })
                messages.extend(tool_results)
                
                # 再次调用LLM生成最终响应
                full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages[-20:]
                final_response = await self.client.chat(
                    messages=full_messages,
                    tools=TOOLS,
                    temperature=0.7
                )
                
                ai_response = final_response.get("content", "")
                messages.append({"role": "assistant", "content": ai_response})
            else:
                ai_response = response.get("content", "")
                messages.append({"role": "assistant", "content": ai_response})
            
            # 确定当前步骤
            current_step = self._determine_step(context)
            
            # 生成快捷选项
            suggested_options = self._get_suggested_options(context, current_step)
            
            return {
                "response": ai_response,
                "session_id": session_id,
                "current_step": current_step,
                "collected_data": {
                    "selectedModels": context.get("selectedModels", []),
                    "modelConfigs": context.get("modelConfigs", {}),
                    "customerInfo": context.get("customerInfo", {})
                },
                "preview_table": context.get("preview_table"),
                "ready_to_export": context.get("ready_to_export", False),
                "export_filename": context.get("export_filename"),
                "suggested_options": suggested_options
            }
            
        except Exception as e:
            logger.error(f"[ExpressQuote] Error processing message: {e}")
            return {
                "response": f"抱歉，处理请求时出现错误。请重试。",
                "session_id": session_id,
                "current_step": context.get("currentStep", 1),
                "collected_data": {},
                "error": str(e)
            }
    
    async def _execute_function(
        self,
        func_name: str,
        args: dict,
        session: dict,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """执行Function Call"""
        context = session["context"]
        temp_variants = session["temp_variants"]
        
        try:
            if func_name == "search_models":
                keyword = args.get("keyword", "")
                results = await pricing_data_service.search_models(db, keyword, limit=10)
                return {
                    "success": True,
                    "models": results,
                    "message": f"找到 {len(results)} 个匹配的模型" if results else "未找到匹配的模型"
                }
            
            elif func_name == "get_model_variants":
                model_code = args.get("model_code", "")
                result = await pricing_data_service.get_model_pricing(db, model_code)
                
                if result.get("found"):
                    variants = result.get("variants", [])
                    # 缓存规格信息
                    temp_variants[model_code] = variants
                    
                    # 格式化返回
                    formatted_variants = []
                    for i, v in enumerate(variants):
                        prices = v.get("prices", [])
                        input_price = next((p["unit_price"] for p in prices if "input" in p.get("dimension_code", "")), None)
                        output_price = next((p["unit_price"] for p in prices if "output" in p.get("dimension_code", "")), None)
                        
                        # 确定价格类型和单位（fallback 逻辑，与 QuoteStep2 保持一致）
                        price_type = "token"
                        price_unit = "千Token"
                        fallback_price = None
                        
                        if input_price is None and output_price is None and prices:
                            # 非 Token 计费模型（图像/视频/语音等），使用第一个价格
                            first_price = prices[0]
                            fallback_price = first_price.get("unit_price")
                            price_unit = first_price.get("unit", "")
                            dimension = first_price.get("dimension_code", "")
                            # 根据维度确定价格类型
                            if "image" in dimension:
                                price_type = "image"
                            elif "video" in dimension:
                                price_type = "video"
                            elif "audio" in dimension or "character" in dimension:
                                price_type = "audio"
                            else:
                                price_type = "other"
                        
                        formatted_variants.append({
                            "index": i + 1,
                            "id": v.get("id"),
                            "mode": v.get("mode", "标准"),
                            "token_tier": v.get("token_tier", "全量"),
                            "input_price": input_price,
                            "output_price": output_price,
                            "fallback_price": fallback_price,
                            "price_type": price_type,
                            "price_unit": price_unit,
                            "supports_batch": v.get("supports_batch", False),
                            "remark": v.get("remark", "")
                        })
                    
                    return {
                        "success": True,
                        "model_code": model_code,
                        "variants_count": len(variants),
                        "variants": formatted_variants
                    }
                else:
                    return {"success": False, "message": f"未找到模型: {model_code}"}
            
            elif func_name == "add_model_to_quote":
                model_code = args.get("model_code", "")
                variant_indices = args.get("variant_indices", [])
                
                if model_code not in temp_variants:
                    return {"success": False, "message": "请先查询模型规格"}
                
                all_variants = temp_variants[model_code]
                selected_variants = []
                selected_ids = []
                
                for idx in variant_indices:
                    if 1 <= idx <= len(all_variants):
                        v = all_variants[idx - 1]
                        selected_variants.append(v)
                        selected_ids.append(v.get("id"))
                
                if not selected_variants:
                    return {"success": False, "message": "未选择有效的规格"}
                
                # 更新context
                context.setdefault("modelConfigs", {})[model_code] = {
                    "variantIds": selected_ids,
                    "variants": selected_variants
                }
                
                # 添加到selectedModels（如果不存在）
                model_names = [m.get("model_code") for m in context.get("selectedModels", [])]
                if model_code not in model_names:
                    context.setdefault("selectedModels", []).append({
                        "model_code": model_code,
                        "model_name": selected_variants[0].get("model_name", model_code),
                        "display_name": selected_variants[0].get("display_name", model_code)
                    })
                
                return {
                    "success": True,
                    "message": f"已添加 {len(selected_variants)} 个规格到报价单",
                    "model_code": model_code,
                    "added_count": len(selected_variants)
                }
            
            elif func_name == "set_customer_info":
                customer_name = args.get("customer_name", "")
                discount_percent = args.get("discount_percent", 0)
                quote_date = args.get("quote_date") or date.today().isoformat()
                valid_days = args.get("valid_days") or 30
                
                valid_until = (date.fromisoformat(quote_date) + timedelta(days=valid_days)).isoformat()
                
                context["customerInfo"] = {
                    "customerName": customer_name,
                    "quoteDate": quote_date,
                    "validUntil": valid_until,
                    "discountPercent": discount_percent,
                    "discountRate": (100 - discount_percent) / 100
                }
                context["currentStep"] = 3
                
                return {
                    "success": True,
                    "message": "客户信息已保存",
                    "customerInfo": context["customerInfo"]
                }
            
            elif func_name == "set_daily_usage":
                model_code = args.get("model_code", "")
                variant_index = args.get("variant_index", 1)
                usage = args.get("usage", 0)
                
                if model_code in temp_variants and variant_index <= len(temp_variants[model_code]):
                    variant_id = temp_variants[model_code][variant_index - 1].get("id")
                    context.setdefault("dailyUsages", {}).setdefault(model_code, {})[str(variant_id)] = usage
                    return {"success": True, "message": f"已设置日用量: {usage} 千Token"}
                
                return {"success": False, "message": "规格不存在"}
            
            elif func_name == "generate_quote_preview":
                # 生成预览表格
                preview_html = self._render_preview_table(context)
                context["preview_table"] = preview_html
                context["ready_to_export"] = True
                context["currentStep"] = 4
                
                return {
                    "success": True,
                    "message": "报价单预览已生成",
                    "preview": preview_html
                }
            
            elif func_name == "export_quote":
                # 标记为可导出，实际导出在API层处理
                context["ready_to_export"] = True
                return {
                    "success": True,
                    "message": "请点击下方导出按钮下载报价单",
                    "ready_to_export": True
                }
            
            elif func_name == "get_category_models":
                category = args.get("category", "text")
                category_map = {
                    "text": "text_",
                    "voice": "audio",
                    "vision": "vision",
                    "video": "video"
                }
                
                # 搜索该分类的模型
                keyword = category_map.get(category, "")
                results = await pricing_data_service.search_models(db, keyword, limit=20)
                
                return {
                    "success": True,
                    "category": category,
                    "models": results,
                    "count": len(results)
                }
            
            else:
                return {"success": False, "message": f"未知函数: {func_name}"}
                
        except Exception as e:
            logger.error(f"[ExpressQuote] Function execution error: {func_name}, {e}")
            return {"success": False, "error": str(e)}
    
    def _determine_step(self, context: dict) -> int:
        """确定当前步骤"""
        if context.get("ready_to_export"):
            return 4
        if context.get("customerInfo", {}).get("customerName"):
            return 3
        if context.get("selectedModels"):
            return 2
        return 1
    
    def _get_suggested_options(self, context: dict, step: int) -> List[str]:
        """获取快捷选项"""
        if step == 1:
            return []
        elif step == 2:
            return ["继续添加模型", "填写客户信息"]
        elif step == 3:
            return ["预览报价单", "修改模型", "填写日用量"]
        elif step == 4:
            return ["导出Excel", "修改内容", "重新开始"]
        return []
    
    def _render_preview_table(self, context: dict) -> str:
        """渲染预览表格HTML"""
        customer_info = context.get("customerInfo", {})
        model_configs = context.get("modelConfigs", {})
        
        rows = []
        idx = 1
        
        for model_code, config in model_configs.items():
            variants = config.get("variants", [])
            for v in variants:
                prices = v.get("prices", [])
                input_price = next((p["unit_price"] for p in prices if "input" in p.get("dimension_code", "")), None)
                output_price = next((p["unit_price"] for p in prices if "output" in p.get("dimension_code", "")), None)
                
                # 非Token类价格处理（图像/视频/语音等）
                fallback_price = None
                price_unit = "千Token"
                if input_price is None and output_price is None and prices:
                    first_price = prices[0]
                    fallback_price = first_price.get("unit_price")
                    price_unit = first_price.get("unit", "次")
                
                discount_rate = customer_info.get("discountRate", 1)
                
                # 计算折后价
                if input_price is not None:
                    input_discounted = f"¥{float(input_price) * discount_rate:.4f}"
                elif fallback_price is not None:
                    input_discounted = f"¥{float(fallback_price) * discount_rate:.4f}"
                else:
                    input_discounted = "-"
                    
                output_discounted = f"¥{float(output_price) * discount_rate:.4f}" if output_price is not None else "-"
                
                # 构建价格显示
                if input_price is not None:
                    display_input = f"¥{input_price}"
                elif fallback_price is not None:
                    display_input = f"¥{fallback_price}"
                else:
                    display_input = "-"
                    
                display_output = f"¥{output_price}" if output_price is not None else "-"
                
                rows.append({
                    "idx": idx,
                    "model": model_code,
                    "mode": v.get("mode", "-"),
                    "token_tier": v.get("token_tier", "-"),
                    "input_price": display_input,
                    "output_price": display_output,
                    "input_discounted": input_discounted,
                    "output_discounted": output_discounted,
                    "price_unit": price_unit,
                    "is_token_based": input_price is not None or output_price is not None
                })
                idx += 1
        
        # 生成简单的文本表格（前端会渲染成美观的表格）
        table_data = {
            "customerInfo": customer_info,
            "rows": rows,
            "totalModels": len(model_configs),
            "totalVariants": len(rows)
        }
        
        return json.dumps(table_data, ensure_ascii=False)
    
    def get_export_data(self, session_id: str) -> Dict[str, Any]:
        """获取导出数据（格式与现有export API兼容）"""
        session = self._get_session(session_id)
        context = session["context"]
        
        return {
            "customerInfo": context.get("customerInfo", {}),
            "selectedModels": context.get("selectedModels", []),
            "modelConfigs": context.get("modelConfigs", {}),
            "specDiscounts": context.get("specDiscounts", {}),
            "dailyUsages": context.get("dailyUsages", {}),
            "priceUnit": "thousand"
        }
    
    def clear_session(self, session_id: str):
        """清除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]


# 全局编排器实例
express_orchestrator = ExpressQuoteOrchestrator()
