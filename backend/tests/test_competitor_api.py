"""
竞品分析API测试
测试competitors API端点的功能、参数验证和错误处理
"""
import pytest
from httpx import AsyncClient
from fastapi import status

from app.services.competitor_service import competitor_service


class TestCompetitorMatchAPI:
    """测试单个模型竞品匹配API"""
    
    @pytest.mark.asyncio
    async def test_match_success(self, client: AsyncClient):
        """测试成功匹配竞品"""
        # 确保服务已加载数据
        competitor_service.ensure_loaded()
        
        response = await client.get(
            "/api/v1/competitors/match",
            params={"model_name": "qwen-plus"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "has_competitor" in data
        assert "model_code" in data
    
    @pytest.mark.asyncio
    async def test_match_with_category(self, client: AsyncClient):
        """测试带类别过滤的匹配"""
        response = await client.get(
            "/api/v1/competitors/match",
            params={
                "model_name": "qwen-plus",
                "category": "text"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        if data["has_competitor"]:
            assert data["data"]["category"] == "text"
    
    @pytest.mark.asyncio
    async def test_match_unknown_model(self, client: AsyncClient):
        """测试未知模型"""
        response = await client.get(
            "/api/v1/competitors/match",
            params={"model_name": "unknown-model-xyz"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["has_competitor"] == False
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_match_missing_param(self, client: AsyncClient):
        """测试缺少必需参数"""
        response = await client.get("/api/v1/competitors/match")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.asyncio
    async def test_match_empty_model_name(self, client: AsyncClient):
        """测试空模型名称"""
        response = await client.get(
            "/api/v1/competitors/match",
            params={"model_name": ""}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_competitor"] == False
    
    @pytest.mark.asyncio
    async def test_match_case_insensitive(self, client: AsyncClient):
        """测试大小写不敏感"""
        # 小写
        response1 = await client.get(
            "/api/v1/competitors/match",
            params={"model_name": "qwen-plus"}
        )
        
        # 大写
        response2 = await client.get(
            "/api/v1/competitors/match",
            params={"model_name": "QWEN-PLUS"}
        )
        
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        
        data1 = response1.json()
        data2 = response2.json()
        
        # 结果应该一致
        assert data1["has_competitor"] == data2["has_competitor"]


class TestBatchMatchAPI:
    """测试批量匹配API"""
    
    @pytest.mark.asyncio
    async def test_batch_match_success(self, client: AsyncClient):
        """测试批量匹配成功"""
        competitor_service.ensure_loaded()
        
        response = await client.post(
            "/api/v1/competitors/batch-match",
            json={
                "model_codes": ["qwen-plus", "qwen-flash", "qwen-image"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "success" in data
        assert data["success"] == True
        assert "results" in data
        assert "update_time" in data
        
        results = data["results"]
        assert len(results) == 3
        assert "qwen-plus" in results
        assert "qwen-flash" in results
        assert "qwen-image" in results
    
    @pytest.mark.asyncio
    async def test_batch_match_empty_list(self, client: AsyncClient):
        """测试空模型列表"""
        response = await client.post(
            "/api/v1/competitors/batch-match",
            json={"model_codes": []}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["results"] == {}
    
    @pytest.mark.asyncio
    async def test_batch_match_mixed_results(self, client: AsyncClient):
        """测试混合结果（有的有竞品，有的没有）"""
        response = await client.post(
            "/api/v1/competitors/batch-match",
            json={
                "model_codes": ["qwen-plus", "unknown-model"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        results = data["results"]
        assert len(results) == 2


class TestMappingsAPI:
    """测试映射表API"""
    
    @pytest.mark.asyncio
    async def test_get_mappings(self, client: AsyncClient):
        """测试获取映射表"""
        response = await client.get("/api/v1/competitors/mappings")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "success" in data
        assert data["success"] == True
        assert "mappings" in data
        
        mappings = data["mappings"]
        assert isinstance(mappings, dict)
        assert len(mappings) > 0
        
        # 验证必要的映射存在
        assert "qwen-plus" in mappings or "qwen3-plus" in mappings


class TestReloadAPI:
    """测试重新加载API"""
    
    @pytest.mark.asyncio
    async def test_reload_success(self, client: AsyncClient):
        """测试重新加载成功"""
        response = await client.post("/api/v1/competitors/reload")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "success" in data
        assert "message" in data
    
    @pytest.mark.asyncio
    async def test_reload_updates_data(self, client: AsyncClient):
        """测试重新加载后数据更新"""
        # 获取当前状态
        status1 = await client.get("/api/v1/competitors/status")
        data1 = status1.json()
        
        # 重新加载
        reload_response = await client.post("/api/v1/competitors/reload")
        assert reload_response.status_code == status.HTTP_200_OK
        
        # 再次获取状态
        status2 = await client.get("/api/v1/competitors/status")
        data2 = status2.json()
        
        # 数据应该已加载
        assert data2["loaded"] == True


class TestStatusAPI:
    """测试状态API"""
    
    @pytest.mark.asyncio
    async def test_get_status(self, client: AsyncClient):
        """测试获取状态"""
        response = await client.get("/api/v1/competitors/status")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "loaded" in data
        assert "record_count" in data
        assert "update_time" in data
        assert "file_path" in data
        
        assert isinstance(data["loaded"], bool)
        assert isinstance(data["record_count"], int)
        assert data["record_count"] >= 0


class TestAPIPerformance:
    """测试API性能"""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, client: AsyncClient):
        """测试并发请求"""
        import asyncio
        
        competitor_service.ensure_loaded()
        
        async def query():
            return await client.get(
                "/api/v1/competitors/match",
                params={"model_name": "qwen-plus"}
            )
        
        # 发起10个并发请求
        tasks = [query() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        # 所有请求都应该成功
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "has_competitor" in data
    
    @pytest.mark.asyncio
    async def test_response_time(self, client: AsyncClient):
        """测试响应时间（应该<100ms因为使用内存缓存）"""
        import time
        
        competitor_service.ensure_loaded()
        
        start = time.time()
        response = await client.get(
            "/api/v1/competitors/match",
            params={"model_name": "qwen-plus"}
        )
        end = time.time()
        
        assert response.status_code == status.HTTP_200_OK
        
        response_time = (end - start) * 1000  # 转为毫秒
        # 内存缓存响应应该很快
        assert response_time < 200  # 200ms以内


class TestAPIErrorHandling:
    """测试API错误处理"""
    
    @pytest.mark.asyncio
    async def test_invalid_category(self, client: AsyncClient):
        """测试无效的类别参数"""
        response = await client.get(
            "/api/v1/competitors/match",
            params={
                "model_name": "qwen-plus",
                "category": "invalid-category"
            }
        )
        
        # 应该正常返回，只是可能匹配失败
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.asyncio
    async def test_special_characters_in_model_name(self, client: AsyncClient):
        """测试模型名称中的特殊字符"""
        response = await client.get(
            "/api/v1/competitors/match",
            params={"model_name": "qwen-plus@#$%"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # 应该返回未匹配
        assert data["has_competitor"] == False
    
    @pytest.mark.asyncio
    async def test_very_long_model_name(self, client: AsyncClient):
        """测试超长模型名称"""
        long_name = "a" * 1000
        response = await client.get(
            "/api/v1/competitors/match",
            params={"model_name": long_name}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_competitor"] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
