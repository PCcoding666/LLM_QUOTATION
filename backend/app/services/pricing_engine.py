"""
计费计算引擎
支持多种计费模式:标准计费、Token计费、思考模式、Batch折扣、阶梯折扣等
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
from loguru import logger


class PricingRule:
    """计费规则基类"""
    
    def apply(self, base_price: Decimal, context: Dict[str, Any]) -> Decimal:
        """应用规则"""
        raise NotImplementedError


class TokenPricingRule(PricingRule):
    """Token计费规则 - 支持输入/输出Token分别计费"""
    
    def apply(self, base_price: Decimal, context: Dict[str, Any]) -> Decimal:
        """
        Token计费:
        - 如果有分别的输入/输出价格: (input_price × input_tokens + output_price × output_tokens) / 1000
        - 否则使用统一token_price: token_price × estimated_tokens × call_frequency
        """
        # 检查是否有分别的输入/输出token价格
        input_token_price = context.get("input_token_price")
        output_token_price = context.get("output_token_price")
        input_tokens = context.get("input_tokens", 0)
        output_tokens = context.get("output_tokens", 0)
        
        if input_token_price is not None and output_token_price is not None:
            # 分别计费模式: (输入价格×输入tokens + 输出价格×输出tokens) / 1000
            input_cost = Decimal(str(input_token_price)) * Decimal(str(input_tokens))
            output_cost = Decimal(str(output_token_price)) * Decimal(str(output_tokens))
            total_price = (input_cost + output_cost) / Decimal("1000")
            
            logger.info(f"Token分别计费: 输入({input_token_price}×{input_tokens}) + 输出({output_token_price}×{output_tokens}) / 1000 = {total_price}")
            return total_price
        else:
            # 统一计费模式: token_price × estimated_tokens × call_frequency
            token_price = context.get("token_price", base_price)
            estimated_tokens = context.get("estimated_tokens", 0)
            call_frequency = context.get("call_frequency", 1)
            
            total_price = Decimal(str(token_price)) * Decimal(str(estimated_tokens)) * Decimal(str(call_frequency))
            logger.info(f"Token统一计费: {token_price} × {estimated_tokens} × {call_frequency} = {total_price}")
            return total_price


class ThinkingModeRule(PricingRule):
    """思考模式计费规则"""
    
    def apply(self, base_price: Decimal, context: Dict[str, Any]) -> Decimal:
        """
        思考模式: 基础价格 × 思考模式系数
        """
        thinking_mode_ratio = context.get("thinking_mode_ratio", 0.0)
        multiplier = context.get("thinking_mode_multiplier", 1.5)
        
        if thinking_mode_ratio > 0:
            additional_cost = base_price * Decimal(str(multiplier - 1)) * Decimal(str(thinking_mode_ratio))
            logger.info(f"思考模式额外成本: {base_price} × {multiplier - 1} × {thinking_mode_ratio} = {additional_cost}")
            return base_price + additional_cost
        
        return base_price


class BatchDiscountRule(PricingRule):
    """Batch调用折扣规则"""
    
    def apply(self, base_price: Decimal, context: Dict[str, Any]) -> Decimal:
        """
        Batch调用: 基础价格 × Batch比例 × 0.5 + 基础价格 × 非Batch比例
        """
        batch_ratio = context.get("batch_call_ratio", 0.0)
        batch_discount = Decimal("0.5")  # Batch调用半价
        
        if batch_ratio > 0:
            batch_price = base_price * Decimal(str(batch_ratio)) * batch_discount
            normal_price = base_price * Decimal(str(1 - batch_ratio))
            total_price = batch_price + normal_price
            logger.info(f"Batch折扣: Batch部分={batch_price}, 正常部分={normal_price}, 总计={total_price}")
            return total_price
        
        return base_price


class TieredDiscountRule(PricingRule):
    """阶梯折扣规则"""
    
    def __init__(self, tiers: List[Dict[str, Any]]):
        """
        tiers: [
            {"threshold": 1000, "discount": 0.9},  # 达到1000享9折
            {"threshold": 10000, "discount": 0.8}  # 达到10000享8折
        ]
        """
        self.tiers = sorted(tiers, key=lambda x: x["threshold"], reverse=True)
    
    def apply(self, base_price: Decimal, context: Dict[str, Any]) -> Decimal:
        """应用阶梯折扣"""
        quantity = context.get("quantity", 1)
        
        for tier in self.tiers:
            if quantity >= tier["threshold"]:
                discount = Decimal(str(tier["discount"]))
                discounted_price = base_price * discount
                logger.info(f"阶梯折扣: 数量{quantity} >= {tier['threshold']}, 折扣={discount}, 价格={discounted_price}")
                return discounted_price
        
        return base_price


class PackagePricingRule(PricingRule):
    """套餐计费规则"""
    
    def __init__(self, package_price: Decimal):
        self.package_price = package_price
    
    def apply(self, base_price: Decimal, context: Dict[str, Any]) -> Decimal:
        """使用固定套餐价格"""
        logger.info(f"套餐计费: 使用固定价格 {self.package_price}")
        return self.package_price


class CombinationDiscountRule(PricingRule):
    """组合优惠规则"""
    
    def __init__(self, discount_rate: Decimal):
        self.discount_rate = discount_rate
    
    def apply(self, base_price: Decimal, context: Dict[str, Any]) -> Decimal:
        """多产品组合优惠"""
        has_combination = context.get("has_combination", False)
        
        if has_combination:
            discounted_price = base_price * self.discount_rate
            logger.info(f"组合优惠: {base_price} × {self.discount_rate} = {discounted_price}")
            return discounted_price
        
        return base_price


class PricingEngine:
    """计费计算引擎"""
    
    def __init__(self):
        self.rules: List[PricingRule] = []
    
    def add_rule(self, rule: PricingRule):
        """添加计费规则"""
        self.rules.append(rule)
    
    def calculate(self, base_price: Decimal, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算最终价格
        
        Args:
            base_price: 基础单价
            context: 计费上下文 {
                "product_type": "llm" | "standard",
                "estimated_tokens": int,
                "call_frequency": int,
                "thinking_mode_ratio": float,
                "batch_call_ratio": float,
                "quantity": int,
                "duration_months": int,
                ...
            }
        
        Returns:
            {
                "original_price": Decimal,
                "final_price": Decimal,
                "discount_details": List[Dict],
                "calculation_breakdown": str
            }
        """
        logger.info(f"开始计算价格: 基础单价={base_price}, 上下文={context}")
        
        product_type = context.get("product_type", "standard")
        current_price = base_price
        discount_details = []
        
        # 根据产品类型选择计费路径
        if product_type == "llm":
            # 大模型产品计费流程
            current_price = self._calculate_llm_price(current_price, context, discount_details)
        else:
            # 传统产品计费流程
            current_price = self._calculate_standard_price(current_price, context, discount_details)
        
        # 应用通用折扣规则
        for rule in self.rules:
            new_price = rule.apply(current_price, context)
            if new_price != current_price:
                discount_details.append({
                    "rule": rule.__class__.__name__,
                    "original": float(current_price),
                    "discounted": float(new_price)
                })
                current_price = new_price
        
        result = {
            "original_price": float(base_price),
            "final_price": float(current_price),
            "discount_details": discount_details,
            "calculation_breakdown": self._generate_breakdown(base_price, current_price, discount_details)
        }
        
        logger.info(f"计算完成: {result}")
        return result
    
    def _calculate_llm_price(
        self,
        base_price: Decimal,
        context: Dict[str, Any],
        discount_details: List[Dict]
    ) -> Decimal:
        """大模型产品计费"""
        # 1. Token计费
        token_rule = TokenPricingRule()
        price = token_rule.apply(base_price, context)
        discount_details.append({
            "rule": "TokenPricing",
            "original": float(base_price),
            "calculated": float(price),
            "input_tokens": context.get("input_tokens", 0),
            "output_tokens": context.get("output_tokens", 0)
        })
        
        # 2. 思考模式系数
        original_price = price
        thinking_rule = ThinkingModeRule()
        price = thinking_rule.apply(price, context)
        if price != original_price:
            discount_details.append({
                "rule": "ThinkingMode",
                "original": float(original_price),
                "calculated": float(price),
                "thinking_ratio": context.get("thinking_mode_ratio", 0),
                "multiplier": context.get("thinking_mode_multiplier", 1.5)
            })
        
        # 3. Batch折扣
        original_price = price
        batch_rule = BatchDiscountRule()
        price = batch_rule.apply(price, context)
        if price != original_price:
            discount_details.append({
                "rule": "BatchDiscount",
                "original": float(original_price),
                "calculated": float(price),
                "batch_ratio": context.get("batch_call_ratio", 0),
                "discount": 0.5
            })
        
        return price
    
    def _calculate_standard_price(
        self,
        base_price: Decimal,
        context: Dict[str, Any],
        discount_details: List[Dict]
    ) -> Decimal:
        """传统产品计费"""
        quantity = context.get("quantity", 1)
        duration_months = context.get("duration_months", 1)
        
        # 基础计费: 单价 × 数量 × 时长
        price = base_price * Decimal(str(quantity)) * Decimal(str(duration_months))
        discount_details.append({
            "rule": "StandardPricing",
            "calculation": f"{base_price} × {quantity} × {duration_months}",
            "result": float(price)
        })
        
        return price
    
    def _generate_breakdown(
        self,
        original: Decimal,
        final: Decimal,
        details: List[Dict]
    ) -> str:
        """生成计费明细说明"""
        lines = [f"原始价格: ¥{original}"]
        
        for detail in details:
            rule_name = detail.get("rule", "Unknown")
            lines.append(f"  - {rule_name}: {detail}")
        
        discount_rate = ((original - final) / original * 100) if original > 0 else 0
        lines.append(f"最终价格: ¥{final} (优惠{discount_rate:.2f}%)")
        
        return "\n".join(lines)


# 创建全局引擎实例
pricing_engine = PricingEngine()
