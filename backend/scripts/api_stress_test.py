#!/usr/bin/env python3
"""
API压力测试脚本

测试核心API接口的并发性能
使用方法:
    python scripts/api_stress_test.py --endpoint products --concurrency 10
    python scripts/api_stress_test.py --all
"""
import argparse
import asyncio
import time
import statistics
from typing import List, Dict, Any
from datetime import datetime
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
except ImportError:
    print("请安装httpx: pip install httpx")
    sys.exit(1)


class APIPerformanceMetrics:
    """API性能指标收集器"""
    
    def __init__(self, name: str):
        self.name = name
        self.times: List[float] = []
        self.errors: int = 0
        self.status_codes: Dict[int, int] = {}
    
    def record(self, elapsed: float, status_code: int):
        """记录一次请求"""
        self.times.append(elapsed)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
    
    def record_error(self, error: str = None):
        """记录一次错误"""
        self.errors += 1
    
    def report(self) -> Dict[str, Any]:
        """生成报告"""
        if not self.times:
            return {"name": self.name, "error": "没有测试数据"}
        
        successful_times = [t for t, sc in zip(self.times, [200, 201]) if sc in [200, 201]]
        
        return {
            "name": self.name,
            "total_requests": len(self.times),
            "successful": len([s for s in self.status_codes.keys() if s < 400]),
            "errors": self.errors,
            "status_codes": self.status_codes,
            "min_ms": round(min(self.times) * 1000, 2),
            "max_ms": round(max(self.times) * 1000, 2),
            "avg_ms": round(statistics.mean(self.times) * 1000, 2),
            "median_ms": round(statistics.median(self.times) * 1000, 2),
            "p95_ms": round(sorted(self.times)[int(len(self.times) * 0.95)] * 1000, 2) if len(self.times) >= 20 else "N/A",
            "p99_ms": round(sorted(self.times)[int(len(self.times) * 0.99)] * 1000, 2) if len(self.times) >= 100 else "N/A",
            "total_time_s": round(sum(self.times), 2),
            "rps": round(len(self.times) / sum(self.times), 2) if sum(self.times) > 0 else 0
        }


BASE_URL = "http://localhost:8000"


async def test_products_api(client: httpx.AsyncClient, iterations: int) -> APIPerformanceMetrics:
    """测试产品API"""
    metrics = APIPerformanceMetrics("Products API")
    
    endpoints = [
        ("GET", "/api/v1/products/filters", None),
        ("GET", "/api/v1/products/models?page=1&page_size=20", None),
        ("GET", "/api/v1/products/", None),
    ]
    
    for i in range(iterations):
        method, url, data = endpoints[i % len(endpoints)]
        try:
            start = time.perf_counter()
            if method == "GET":
                response = await client.get(f"{BASE_URL}{url}")
            else:
                response = await client.post(f"{BASE_URL}{url}", json=data)
            elapsed = time.perf_counter() - start
            metrics.record(elapsed, response.status_code)
        except Exception as e:
            metrics.record_error(str(e))
    
    return metrics


async def test_quotes_api(client: httpx.AsyncClient, iterations: int) -> APIPerformanceMetrics:
    """测试报价单API"""
    metrics = APIPerformanceMetrics("Quotes API")
    
    for i in range(iterations):
        try:
            start = time.perf_counter()
            response = await client.get(f"{BASE_URL}/api/v1/quotes/?page=1&page_size=20")
            elapsed = time.perf_counter() - start
            metrics.record(elapsed, response.status_code)
        except Exception as e:
            metrics.record_error(str(e))
    
    return metrics


async def test_export_api(client: httpx.AsyncClient, iterations: int) -> APIPerformanceMetrics:
    """测试导出API"""
    metrics = APIPerformanceMetrics("Export API")
    
    for i in range(iterations):
        try:
            start = time.perf_counter()
            response = await client.get(f"{BASE_URL}/api/v1/export/templates")
            elapsed = time.perf_counter() - start
            metrics.record(elapsed, response.status_code)
        except Exception as e:
            metrics.record_error(str(e))
    
    return metrics


async def test_health_api(client: httpx.AsyncClient, iterations: int) -> APIPerformanceMetrics:
    """测试健康检查API"""
    metrics = APIPerformanceMetrics("Health Check")
    
    for i in range(iterations):
        try:
            start = time.perf_counter()
            response = await client.get(f"{BASE_URL}/health")
            elapsed = time.perf_counter() - start
            metrics.record(elapsed, response.status_code)
        except Exception as e:
            metrics.record_error(str(e))
    
    return metrics


async def run_concurrent_test(
    test_func,
    concurrency: int,
    iterations_per_worker: int
) -> APIPerformanceMetrics:
    """并发运行测试"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 创建多个并发任务
        tasks = []
        for _ in range(concurrency):
            tasks.append(test_func(client, iterations_per_worker))
        
        # 并发执行
        results = await asyncio.gather(*tasks)
        
        # 合并结果
        combined = APIPerformanceMetrics(results[0].name)
        for r in results:
            combined.times.extend(r.times)
            combined.errors += r.errors
            for code, count in r.status_codes.items():
                combined.status_codes[code] = combined.status_codes.get(code, 0) + count
        
        return combined


def print_report(metrics: APIPerformanceMetrics, threshold_ms: float = 500):
    """打印性能报告"""
    report = metrics.report()
    
    print(f"\n{'='*60}")
    print(f"📈 {report['name']} 性能报告")
    print(f"{'='*60}")
    
    if "error" in report:
        print(f"❌ {report['error']}")
        return False
    
    print(f"  总请求数: {report['total_requests']}")
    print(f"  错误次数: {report['errors']}")
    print(f"  状态码分布: {report['status_codes']}")
    print(f"  最小响应: {report['min_ms']} ms")
    print(f"  最大响应: {report['max_ms']} ms")
    print(f"  平均响应: {report['avg_ms']} ms")
    print(f"  中位数: {report['median_ms']} ms")
    print(f"  P95: {report['p95_ms']} ms")
    print(f"  P99: {report['p99_ms']} ms")
    print(f"  总耗时: {report['total_time_s']} s")
    print(f"  吞吐量(RPS): {report['rps']}")
    
    # 检查是否满足性能要求
    if isinstance(report['avg_ms'], (int, float)) and report['avg_ms'] < threshold_ms:
        print(f"\n  ✅ 性能达标 (平均响应时间 < {threshold_ms}ms)")
        return True
    else:
        print(f"\n  ⚠️ 性能需关注 (平均响应时间 >= {threshold_ms}ms)")
        return False


async def check_server_available():
    """检查服务器是否可用"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{BASE_URL}/health")
            return response.status_code == 200
    except:
        return False


async def main():
    parser = argparse.ArgumentParser(description="API压力测试")
    parser.add_argument("--endpoint", choices=["products", "quotes", "export", "health"],
                        help="指定要测试的端点")
    parser.add_argument("--all", action="store_true", help="测试所有端点")
    parser.add_argument("--concurrency", type=int, default=10, help="并发数")
    parser.add_argument("--iterations", type=int, default=50, help="每个worker的迭代次数")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 报价侠系统 - API压力测试")
    print(f"⏱️  开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔧 并发数: {args.concurrency}")
    print(f"🔄 每worker迭代: {args.iterations}")
    print("=" * 60)
    
    # 检查服务器是否可用
    if not await check_server_available():
        print(f"\n❌ 无法连接到服务器 {BASE_URL}")
        print("请确保后端服务已启动:")
        print("  cd backend && source venv/bin/activate && uvicorn main:app --reload")
        return
    
    print(f"\n✅ 服务器连接成功: {BASE_URL}")
    
    results = []
    all_passed = True
    
    test_map = {
        "products": test_products_api,
        "quotes": test_quotes_api,
        "export": test_export_api,
        "health": test_health_api
    }
    
    if args.all:
        endpoints = ["health", "products", "quotes", "export"]
    elif args.endpoint:
        endpoints = [args.endpoint]
    else:
        print("\n请指定 --endpoint 或 --all 参数")
        parser.print_help()
        return
    
    for endpoint in endpoints:
        print(f"\n🔍 测试 {endpoint} API ({args.concurrency} 并发 × {args.iterations} 迭代)...")
        
        test_func = test_map[endpoint]
        metrics = await run_concurrent_test(
            test_func,
            args.concurrency,
            args.iterations
        )
        
        passed = print_report(metrics)
        if not passed:
            all_passed = False
        results.append(metrics)
    
    # 汇总报告
    print("\n" + "=" * 60)
    print("📊 测试汇总")
    print("=" * 60)
    
    for metrics in results:
        report = metrics.report()
        if "error" not in report:
            status = "✅" if report['avg_ms'] < 500 else "⚠️"
            print(f"  {status} {report['name']}: {report['avg_ms']}ms (avg), {report['rps']} RPS")
    
    print(f"\n⏱️  结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if all_passed:
        print("\n✅ 所有API性能达标!")
    else:
        print("\n⚠️ 部分API需要性能优化")


if __name__ == "__main__":
    asyncio.run(main())
