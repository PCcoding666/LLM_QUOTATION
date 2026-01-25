"""
竞品分析服务模块
提供竞品对标数据的加载、匹配和查询功能
"""
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

from app.core.config import settings


# 模型名称映射表：将数据库中的model_code映射到JSON中的qwen.model字段
MODEL_NAME_MAPPING = {
    # 文本类模型
    "qvq-max": "Qwen3-Max(<32k)",
    "qwen-max": "Qwen3-Max(<32k)",
    "qwen3-max": "Qwen3-Max(<32k)",
    "qwen-plus": "Qwen-Plus(<128k)",
    "qwen3-plus": "Qwen-Plus(<128k)",
    "qwen-flash": "Qwen-Flash(<128k)",
    "qwen3-flash": "Qwen-Flash(<128k)",
    "qwen-turbo": "Qwen-Turbo(<1M)",
    "qwen3-turbo": "Qwen-Turbo(<1M)",
    # 图片类模型
    "qwen-image": "Qwen-image (主推)",
    "wanxiang-image": "万相生图",
    "wanx-image": "万相生图",
    "z-image": "Z-Image",
    # 视频类模型
    "wanxiang-video": "通义万相视频创作-旗舰",
    "wanx-video": "通义万相视频创作-旗舰",
}


class CompetitorService:
    """竞品分析服务"""
    
    def __init__(self):
        self._data: List[Dict[str, Any]] = []
        self._data_loaded: bool = False
        self._last_modified: Optional[datetime] = None
        self._file_path: str = ""
    
    def _get_data_file_path(self) -> str:
        """获取竞品数据文件路径"""
        # 优先使用配置中的路径
        if hasattr(settings, 'COMPETITOR_DATA_FILE') and settings.COMPETITOR_DATA_FILE:
            return settings.COMPETITOR_DATA_FILE
        
        # 默认路径
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(base_dir, "data", "competitor_comparison.json")
    
    def load_data(self) -> bool:
        """
        加载竞品数据到内存
        Returns:
            bool: 加载是否成功
        """
        try:
            file_path = self._get_data_file_path()
            self._file_path = file_path
            
            if not os.path.exists(file_path):
                logger.warning(f"竞品数据文件不存在: {file_path}")
                self._data = []
                self._data_loaded = True
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
            
            # 记录文件最后修改时间
            self._last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
            self._data_loaded = True
            
            logger.info(f"竞品数据加载成功: {len(self._data)} 条记录, 更新时间: {self._last_modified}")
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"竞品数据JSON格式错误: {e}")
            self._data = []
            self._data_loaded = True
            return False
        except Exception as e:
            logger.error(f"加载竞品数据失败: {e}")
            self._data = []
            self._data_loaded = True
            return False
    
    def ensure_loaded(self) -> None:
        """确保数据已加载"""
        if not self._data_loaded:
            self.load_data()
    
    def reload_data(self) -> bool:
        """
        重新加载竞品数据（热更新）
        Returns:
            bool: 重新加载是否成功
        """
        self._data_loaded = False
        return self.load_data()
    
    def get_data_update_time(self) -> Optional[str]:
        """
        获取数据更新时间
        Returns:
            str: 格式化的更新时间字符串
        """
        self.ensure_loaded()
        if self._last_modified:
            return self._last_modified.strftime("%Y-%m-%d")
        return None
    
    def match_competitor(self, model_code: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        根据模型代码匹配竞品数据
        
        Args:
            model_code: 模型代码（如 qwen-plus, qvq-max）
            category: 可选的类别过滤（text/image/video）
            
        Returns:
            Dict: 匹配结果，包含 has_competitor 和 data 字段
        """
        self.ensure_loaded()
        
        # 标准化model_code
        normalized_code = model_code.lower().strip()
        
        # 步骤1：通过映射表转换model_code
        if normalized_code not in MODEL_NAME_MAPPING:
            logger.debug(f"模型 {model_code} 未配置竞品映射")
            return {
                "has_competitor": False,
                "message": "该模型未配置竞品映射",
                "model_code": model_code
            }
        
        json_model_name = MODEL_NAME_MAPPING[normalized_code]
        
        # 步骤2：在JSON数据中精确匹配
        for item in self._data:
            qwen_model = item.get("qwen", {}).get("model", "")
            
            # 精确匹配
            if qwen_model == json_model_name:
                # 如果指定了category，检查是否匹配
                if category and item.get("category") != category:
                    continue
                
                return self._format_match_result(item, model_code)
        
        logger.debug(f"未找到模型 {json_model_name} 的竞品数据")
        return {
            "has_competitor": False,
            "message": "暂无竞品对比数据",
            "model_code": model_code
        }
    
    def _format_match_result(self, item: Dict[str, Any], original_model_code: str) -> Dict[str, Any]:
        """
        格式化匹配结果
        
        Args:
            item: JSON中的原始数据项
            original_model_code: 原始模型代码
            
        Returns:
            Dict: 格式化后的竞品对比数据
        """
        qwen = item.get("qwen", {})
        doubao = item.get("doubao", {})
        category = item.get("category", "text")
        
        # 根据类别处理价格字段
        if category == "text":
            qwen_data = {
                "model": qwen.get("model"),
                "position": qwen.get("position"),
                "role": qwen.get("role"),
                "input_price": qwen.get("cost_1m_tokens_input_cny"),
                "output_price": qwen.get("cost_1m_tokens_output_cny"),
                "price_unit": "元/百万Token"
            }
            doubao_data = {
                "model": doubao.get("model"),
                "position": doubao.get("position"),
                "input_price": doubao.get("cost_1m_tokens_input_cny"),
                "output_price": doubao.get("cost_1m_tokens_output_cny"),
                "price_unit": "元/百万Token"
            }
        elif category == "image":
            qwen_data = {
                "model": qwen.get("model"),
                "position": qwen.get("position"),
                "role": qwen.get("role"),
                "unit_price": qwen.get("cost_per_image_cny"),
                "price_unit": "元/张"
            }
            doubao_data = {
                "model": doubao.get("model"),
                "position": doubao.get("position"),
                "unit_price": doubao.get("cost_per_image_cny"),
                "price_unit": "元/张"
            }
        else:  # video
            qwen_data = {
                "model": qwen.get("model"),
                "position": qwen.get("position"),
                "role": qwen.get("role"),
                "unit_price": qwen.get("cost_per_second_cny"),
                "price_unit": "元/秒"
            }
            doubao_data = {
                "model": doubao.get("model"),
                "position": doubao.get("position"),
                "unit_price": doubao.get("cost_per_second_cny"),
                "price_unit": "元/秒"
            }
        
        return {
            "has_competitor": True,
            "data": {
                "qwen": qwen_data,
                "doubao": doubao_data,
                "insight": item.get("insight", ""),
                "category": category,
                "family": item.get("family", ""),
                "baseline": item.get("baseline", {}),
                "update_time": self.get_data_update_time()
            },
            "model_code": original_model_code
        }
    
    def batch_match(self, model_codes: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        批量匹配多个模型的竞品数据
        
        Args:
            model_codes: 模型代码列表
            
        Returns:
            Dict: 以model_code为key的匹配结果字典
        """
        results = {}
        for code in model_codes:
            results[code] = self.match_competitor(code)
        return results
    
    def get_all_mappings(self) -> Dict[str, str]:
        """
        获取所有模型名称映射
        Returns:
            Dict: 映射表副本
        """
        return MODEL_NAME_MAPPING.copy()
    
    def get_insight_for_ai(self, model_code: str) -> Optional[str]:
        """
        获取用于AI推荐的竞品洞察话术
        
        Args:
            model_code: 模型代码
            
        Returns:
            str: 竞品洞察话术，无数据则返回None
        """
        result = self.match_competitor(model_code)
        if result.get("has_competitor"):
            data = result.get("data", {})
            insight = data.get("insight", "")
            doubao_model = data.get("doubao", {}).get("model", "")
            
            if insight and doubao_model:
                return f"与竞品{doubao_model}对比：{insight}"
        return None


# 创建全局服务实例
competitor_service = CompetitorService()
