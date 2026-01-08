#!/usr/bin/env python3
"""
数据库连接验证脚本
用于验证 PostgreSQL 和 Redis 连接是否正常
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def verify_postgresql():
    """验证 PostgreSQL 连接"""
    print("=" * 50)
    print("正在验证 PostgreSQL 数据库连接...")
    print("=" * 50)
    
    try:
        from app.core.database import engine
        from sqlalchemy import text
        
        async with engine.connect() as conn:
            # 执行简单查询
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✓ PostgreSQL 连接成功!")
            print(f"  数据库版本: {version}")
            
            # 检查数据库大小
            result = await conn.execute(text("SELECT pg_database_size(current_database())"))
            size = result.scalar()
            print(f"  数据库大小: {size / 1024 / 1024:.2f} MB")
            
            return True
    except Exception as e:
        print(f"✗ PostgreSQL 连接失败: {e}")
        return False


async def verify_redis():
    """验证 Redis 连接"""
    print("\n" + "=" * 50)
    print("正在验证 Redis 连接...")
    print("=" * 50)
    
    try:
        from app.core.redis_client import init_redis, get_redis, close_redis
        
        # 初始化 Redis
        await init_redis()
        redis_client = await get_redis()
        
        # 测试 ping
        pong = await redis_client.ping()
        if pong:
            print("✓ Redis 连接成功!")
            
            # 获取 Redis 信息
            info = await redis_client.info("server")
            print(f"  Redis 版本: {info.get('redis_version', 'N/A')}")
            print(f"  运行模式: {info.get('redis_mode', 'N/A')}")
            
            # 测试读写
            await redis_client.set("test_key", "test_value", ex=60)
            value = await redis_client.get("test_key")
            if value == "test_value":
                print("  读写测试: 通过")
            await redis_client.delete("test_key")
            
            await close_redis()
            return True
        else:
            print("✗ Redis ping 失败")
            return False
    except Exception as e:
        print(f"✗ Redis 连接失败: {e}")
        return False


async def verify_all():
    """验证所有连接"""
    print("\n🔍 开始数据库连接验证\n")
    
    # 加载环境变量
    from dotenv import load_dotenv
    load_dotenv()
    
    results = []
    
    # 验证 PostgreSQL
    pg_result = await verify_postgresql()
    results.append(("PostgreSQL", pg_result))
    
    # 验证 Redis
    redis_result = await verify_redis()
    results.append(("Redis", redis_result))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("连接验证结果汇总")
    print("=" * 50)
    
    all_passed = True
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("🎉 所有连接验证通过!")
        return 0
    else:
        print("⚠️  部分连接验证失败，请检查配置")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(verify_all())
    sys.exit(exit_code)
