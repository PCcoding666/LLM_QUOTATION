"""
竞品分析服务测试
测试competitor_service的功能正确性、边界情况和异常处理
"""
import pytest
import json
import os
from datetime import datetime
from unittest.mock import patch, mock_open, MagicMock

from app.services.competitor_service import (
    CompetitorService,
    MODEL_NAME_MAPPING,
    competitor_service
)


@pytest.fixture
def mock_competitor_data():
    """模拟竞品数据（模块级fixture）"""
    return [
        {
            "category": "text",
            "family": "Qwen系列",
            "qwen": {
                "model": "Qwen-Plus(<128k)",
                "position": 2,
                "role": "主推性价比模型",
                "cost_1m_tokens_input_cny": 0.8,
                "cost_1m_tokens_output_cny": 2.0
            },
            "doubao": {
                "model": "Seed-1.6/1.5pro(<32k)",
                "position": 2,
                "cost_1m_tokens_input_cny": 0.8,
                "cost_1m_tokens_output_cny": 2.0
            },
            "baseline": {
                "model": "Gemini 2.5 Pro",
                "cost_ratio_vs_gemini": "1:57.9"
            },
            "insight": "Qwen-Plus 对标 Doubao Seed 主力模型，在输入/输出单价同一量级下，Qwen 可以通过更长上下文、更全生态（如百炼平台能力）来拉高整体价值，并强调国产可控和多场景覆盖。适合'算力敏感+效果要求高'的客户。"
        },
        {
            "category": "text",
            "family": "Qwen系列",
            "qwen": {
                "model": "Qwen-Flash(<128k)",
                "position": 3,
                "role": "高吞吐低成本模型",
                "cost_1m_tokens_input_cny": 0.15,
                "cost_1m_tokens_output_cny": 1.5
            },
            "doubao": {
                "model": "Seed-1.6-flash(<32k)",
                "position": 3,
                "cost_1m_tokens_input_cny": 0.15,
                "cost_1m_tokens_output_cny": 1.5
            },
            "baseline": {
                "model": "Gemini 2.5 Flash"
            },
            "insight": "在高吞吐、强并发、批量调用的场景（如日志分析、批量总结）中，Qwen-Flash 与 Doubao Seed-Flash 是直接对位，均主打极致性价比。此类场景推荐以'单任务体验略降但整体 TPS 和成本优势显著'为话术切入。"
        }
    ]


class TestModelNameMapping:
    """测试模型名称映射表"""
    
    def test_mapping_structure(self):
        """测试映射表结构完整性"""
        assert isinstance(MODEL_NAME_MAPPING, dict)
        assert len(MODEL_NAME_MAPPING) > 0
        
        # 验证所有值都是字符串
        for key, value in MODEL_NAME_MAPPING.items():
            assert isinstance(key, str)
            assert isinstance(value, str)
            assert key == key.lower()  # 所有key应该是小写
    
    def test_text_model_mappings(self):
        """测试文本模型映射"""
        assert "qwen-plus" in MODEL_NAME_MAPPING
        assert "qwen-flash" in MODEL_NAME_MAPPING
        assert "qvq-max" in MODEL_NAME_MAPPING
        
        assert MODEL_NAME_MAPPING["qwen-plus"] == "Qwen-Plus(<128k)"
        assert MODEL_NAME_MAPPING["qwen-flash"] == "Qwen-Flash(<128k)"
    
    def test_image_model_mappings(self):
        """测试图片模型映射"""
        assert "qwen-image" in MODEL_NAME_MAPPING
        assert "wanxiang-image" in MODEL_NAME_MAPPING or "wanx-image" in MODEL_NAME_MAPPING
        assert "z-image" in MODEL_NAME_MAPPING
    
    def test_video_model_mappings(self):
        """测试视频模型映射"""
        assert "wanxiang-video" in MODEL_NAME_MAPPING or "wanx-video" in MODEL_NAME_MAPPING


class TestCompetitorService:
    """测试竞品分析服务"""
    
    @pytest.fixture
    def service(self):
        """创建测试服务实例"""
        return CompetitorService()
    
    def test_init(self, service):
        """测试服务初始化"""
        assert service._data == []
        assert service._data_loaded == False
        assert service._last_modified is None
    
    def test_load_data_success(self, service, mock_competitor_data, tmp_path):
        """测试成功加载数据"""
        # 创建临时JSON文件
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            success = service.load_data()
            
            assert success == True
            assert service._data_loaded == True
            assert len(service._data) == 2
            assert service._last_modified is not None
    
    def test_load_data_file_not_exist(self, service):
        """测试文件不存在的情况"""
        with patch.object(service, '_get_data_file_path', return_value="/nonexistent/file.json"):
            success = service.load_data()
            
            assert success == False
            assert service._data_loaded == True
            assert service._data == []
    
    def test_load_data_json_error(self, service, tmp_path):
        """测试JSON格式错误"""
        # 创建无效的JSON文件
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json }", encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            success = service.load_data()
            
            assert success == False
            assert service._data_loaded == True
            assert service._data == []
    
    def test_ensure_loaded(self, service, mock_competitor_data, tmp_path):
        """测试确保数据已加载"""
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            assert service._data_loaded == False
            service.ensure_loaded()
            assert service._data_loaded == True
    
    def test_reload_data(self, service, mock_competitor_data, tmp_path):
        """测试重新加载数据"""
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            assert service._data_loaded == True
            
            success = service.reload_data()
            assert success == True
            assert service._data_loaded == True
    
    def test_get_data_update_time(self, service, mock_competitor_data, tmp_path):
        """测试获取数据更新时间"""
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            update_time = service.get_data_update_time()
            
            assert update_time is not None
            assert isinstance(update_time, str)
            # 验证日期格式 YYYY-MM-DD
            datetime.strptime(update_time, "%Y-%m-%d")
    
    def test_match_competitor_success(self, service, mock_competitor_data, tmp_path):
        """测试成功匹配竞品"""
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            
            result = service.match_competitor("qwen-plus")
            
            assert result["has_competitor"] == True
            assert result["model_code"] == "qwen-plus"
            assert "data" in result
            
            data = result["data"]
            assert data["qwen"]["model"] == "Qwen-Plus(<128k)"
            assert data["doubao"]["model"] == "Seed-1.6/1.5pro(<32k)"
            assert "insight" in data
            assert data["category"] == "text"
    
    def test_match_competitor_not_in_mapping(self, service, mock_competitor_data, tmp_path):
        """测试模型不在映射表中"""
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            
            result = service.match_competitor("unknown-model")
            
            assert result["has_competitor"] == False
            assert "该模型未配置竞品映射" in result["message"]
    
    def test_match_competitor_no_json_data(self, service, tmp_path):
        """测试JSON中无对应数据"""
        # 创建空数据
        test_file = tmp_path / "empty.json"
        test_file.write_text(json.dumps([]), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            
            result = service.match_competitor("qwen-plus")
            
            assert result["has_competitor"] == False
            assert "暂无竞品对比数据" in result["message"]
    
    def test_match_competitor_with_category_filter(self, service, mock_competitor_data, tmp_path):
        """测试带类别过滤的匹配"""
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            
            # 正确的类别
            result = service.match_competitor("qwen-plus", category="text")
            assert result["has_competitor"] == True
            
            # 错误的类别
            result = service.match_competitor("qwen-plus", category="image")
            assert result["has_competitor"] == False
    
    def test_match_competitor_case_insensitive(self, service, mock_competitor_data, tmp_path):
        """测试大小写不敏感"""
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            
            result1 = service.match_competitor("qwen-plus")
            result2 = service.match_competitor("QWEN-PLUS")
            result3 = service.match_competitor("Qwen-Plus")
            
            assert result1["has_competitor"] == True
            assert result2["has_competitor"] == True
            assert result3["has_competitor"] == True
    
    def test_batch_match(self, service, mock_competitor_data, tmp_path):
        """测试批量匹配"""
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            
            results = service.batch_match(["qwen-plus", "qwen-flash", "unknown-model"])
            
            assert len(results) == 3
            assert results["qwen-plus"]["has_competitor"] == True
            assert results["qwen-flash"]["has_competitor"] == True
            assert results["unknown-model"]["has_competitor"] == False
    
    def test_get_all_mappings(self, service):
        """测试获取所有映射"""
        mappings = service.get_all_mappings()
        
        assert isinstance(mappings, dict)
        assert len(mappings) > 0
        assert "qwen-plus" in mappings
    
    def test_get_insight_for_ai_success(self, service, mock_competitor_data, tmp_path):
        """测试获取AI话术成功"""
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            
            insight = service.get_insight_for_ai("qwen-plus")
            
            assert insight is not None
            assert "与竞品" in insight
            assert "Seed-1.6/1.5pro" in insight
    
    def test_get_insight_for_ai_no_data(self, service, tmp_path):
        """测试无竞品数据时的AI话术"""
        test_file = tmp_path / "empty.json"
        test_file.write_text(json.dumps([]), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            
            insight = service.get_insight_for_ai("qwen-plus")
            
            assert insight is None


class TestCompetitorServiceEdgeCases:
    """测试边界情况"""
    
    def test_empty_model_code(self):
        """测试空模型代码"""
        service = CompetitorService()
        service._data = []
        service._data_loaded = True
        
        result = service.match_competitor("")
        assert result["has_competitor"] == False
    
    def test_whitespace_model_code(self):
        """测试带空格的模型代码"""
        service = CompetitorService()
        service._data = []
        service._data_loaded = True
        
        result = service.match_competitor("  qwen-plus  ")
        # 应该被标准化处理
        assert result["model_code"] == "  qwen-plus  "
    
    def test_concurrent_access(self, mock_competitor_data, tmp_path):
        """测试并发访问（内存缓存应该无并发问题）"""
        import threading
        
        service = CompetitorService()
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            
            results = []
            
            def query():
                result = service.match_competitor("qwen-plus")
                results.append(result)
            
            # 创建多个线程并发查询
            threads = [threading.Thread(target=query) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            
            # 所有结果应该一致
            assert len(results) == 10
            for result in results:
                assert result["has_competitor"] == True


class TestResponseFormat:
    """测试响应格式"""
    
    def test_text_model_response_format(self, mock_competitor_data, tmp_path):
        """测试文本模型响应格式"""
        service = CompetitorService()
        test_file = tmp_path / "test_competitor.json"
        test_file.write_text(json.dumps(mock_competitor_data), encoding='utf-8')
        
        with patch.object(service, '_get_data_file_path', return_value=str(test_file)):
            service.load_data()
            
            result = service.match_competitor("qwen-plus")
            
            assert "has_competitor" in result
            assert "data" in result
            
            data = result["data"]
            assert "qwen" in data
            assert "doubao" in data
            assert "insight" in data
            assert "category" in data
            assert "update_time" in data
            
            # 文本模型应该有输入/输出价格
            assert "input_price" in data["qwen"]
            assert "output_price" in data["qwen"]
            assert "price_unit" in data["qwen"]
            assert data["qwen"]["price_unit"] == "元/百万Token"
    
    def test_error_response_format(self):
        """测试错误响应格式"""
        service = CompetitorService()
        service._data = []
        service._data_loaded = True
        
        result = service.match_competitor("unknown-model")
        
        assert "has_competitor" in result
        assert result["has_competitor"] == False
        assert "message" in result
        assert "model_code" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
