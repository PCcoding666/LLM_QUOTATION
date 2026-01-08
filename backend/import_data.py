"""
数据导入脚本
将 JSON 数据导入到 PostgreSQL 数据库
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import engine, async_session_maker, Base
from app.models.product import Product, ProductPrice, ProductSpec


# 数据文件路径
DATA_DIR = Path(__file__).parent
BAILIAN_MODELS_FILE = DATA_DIR / "bailian_models.json"
CRAWLER_OUTPUT_FILE = DATA_DIR / "crawler_output.json"


async def create_tables():
    """创建数据库表"""
    logger.info("创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")


async def clear_tables(session: AsyncSession):
    """清空现有数据（可选）"""
    logger.info("清空现有数据...")
    await session.execute(text("TRUNCATE TABLE product_prices CASCADE"))
    await session.execute(text("TRUNCATE TABLE product_specs CASCADE"))
    await session.execute(text("TRUNCATE TABLE products CASCADE"))
    await session.commit()
    logger.info("数据清空完成")


async def import_bailian_models(session: AsyncSession):
    """导入百炼大模型数据"""
    if not BAILIAN_MODELS_FILE.exists():
        logger.warning(f"文件不存在: {BAILIAN_MODELS_FILE}")
        return
    
    logger.info(f"读取百炼模型数据: {BAILIAN_MODELS_FILE}")
    with open(BAILIAN_MODELS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    models = data.get("models", [])
    logger.info(f"共 {len(models)} 个模型待导入")
    
    imported_products = 0
    imported_prices = 0
    imported_specs = 0
    
    for model in models:
        try:
            # 1. 导入产品主表
            product_code = model.get("model_id", "")
            if not product_code:
                continue
            
            # 检查是否已存在
            existing = await session.execute(
                text("SELECT 1 FROM products WHERE product_code = :code"),
                {"code": product_code}
            )
            if existing.scalar():
                logger.debug(f"产品已存在，跳过: {product_code}")
                continue
            
            # 创建产品
            product = Product(
                product_code=product_code,
                product_name=model.get("model_name", product_code),
                category=map_category(model.get("category", "text_generation")),
                vendor=model.get("vendor", "aliyun"),
                status=model.get("status", "active"),
                description=model.get("description", f"{model.get('model_name', '')} - {model.get('vendor', 'aliyun')}大模型")
            )
            session.add(product)
            imported_products += 1
            
            # 2. 导入价格信息
            pricing_list = model.get("pricing", [])
            for pricing in pricing_list:
                if not pricing.get("input_price"):
                    continue
                
                input_price = pricing.get("input_price", {})
                output_price = pricing.get("output_price", {})
                
                # 构建pricing_variables
                pricing_variables = {
                    "billing_type": pricing.get("billing_type", "token"),
                    "supports_thinking_mode": pricing.get("supports_thinking_mode", False),
                    "thinking_mode_same_price": pricing.get("thinking_mode_same_price", True),
                    "has_context_tiered_pricing": pricing.get("has_context_tiered_pricing", False),
                    "input_price": input_price.get("price", 0),
                    "output_price": output_price.get("price", 0) if output_price else 0,
                    "unit": input_price.get("unit", "千Token"),
                    "unit_quantity": input_price.get("unit_quantity", 1000),
                    "batch_discount": pricing.get("batch_discount", 0.5)
                }
                
                price_record = ProductPrice(
                    product_code=product_code,
                    region=pricing.get("region", "cn-beijing"),
                    spec_type=product_code,  # 模型ID作为规格类型
                    billing_mode="pay-as-you-go",
                    unit_price=str(input_price.get("price", 0)),
                    unit=input_price.get("unit", "千Token"),
                    pricing_variables=pricing_variables,
                    effective_date=datetime.now()
                )
                session.add(price_record)
                imported_prices += 1
            
            # 3. 导入规格信息
            specs = model.get("specs")
            if specs:
                spec_record = ProductSpec(
                    product_code=product_code,
                    spec_name=f"{product_code}_spec",
                    spec_values={
                        "max_context_length": specs.get("max_context_length"),
                        "max_input_tokens": specs.get("max_input_tokens"),
                        "max_output_tokens": specs.get("max_output_tokens"),
                        "max_thinking_tokens": specs.get("max_thinking_tokens")
                    },
                    constraints={}
                )
                session.add(spec_record)
                imported_specs += 1
        
        except Exception as e:
            logger.error(f"导入模型失败 {model.get('model_id')}: {e}")
            continue
    
    await session.commit()
    logger.info(f"百炼模型导入完成: {imported_products} 个产品, {imported_prices} 条价格, {imported_specs} 条规格")


async def import_crawler_output(session: AsyncSession):
    """导入爬虫输出数据"""
    if not CRAWLER_OUTPUT_FILE.exists():
        logger.warning(f"文件不存在: {CRAWLER_OUTPUT_FILE}")
        return
    
    logger.info(f"读取爬虫输出数据: {CRAWLER_OUTPUT_FILE}")
    with open(CRAWLER_OUTPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    imported_products = 0
    imported_prices = 0
    
    # 处理阿里云数据
    aliyun_data = data.get("aliyun", {})
    products = aliyun_data.get("products", [])
    prices = aliyun_data.get("prices", [])
    
    logger.info(f"阿里云: {len(products)} 个产品, {len(prices)} 条价格")
    
    # 导入产品
    for product_data in products:
        try:
            product_code = product_data.get("product_code", "")
            if not product_code:
                continue
            
            # 检查是否已存在
            existing = await session.execute(
                text("SELECT 1 FROM products WHERE product_code = :code"),
                {"code": product_code}
            )
            if existing.scalar():
                logger.debug(f"产品已存在，跳过: {product_code}")
                continue
            
            product = Product(
                product_code=product_code,
                product_name=product_data.get("product_name", product_code),
                category=product_data.get("category", "其他"),
                vendor=product_data.get("vendor", "aliyun"),
                status=product_data.get("status", "active"),
                description=product_data.get("description", "")
            )
            session.add(product)
            imported_products += 1
        
        except Exception as e:
            logger.error(f"导入产品失败 {product_data.get('product_code')}: {e}")
            continue
    
    # 导入价格
    for price_data in prices:
        try:
            product_code = price_data.get("product_code", "")
            if not product_code:
                continue
            
            price_record = ProductPrice(
                product_code=product_code,
                region=price_data.get("region", "cn-hangzhou"),
                spec_type=price_data.get("spec_type", ""),
                billing_mode=price_data.get("billing_mode", "pay-as-you-go"),
                unit_price=str(price_data.get("unit_price", "0")),
                unit=price_data.get("unit", ""),
                pricing_variables=price_data.get("pricing_variables", {}),
                effective_date=datetime.now()
            )
            session.add(price_record)
            imported_prices += 1
        
        except Exception as e:
            logger.error(f"导入价格失败: {e}")
            continue
    
    await session.commit()
    logger.info(f"爬虫数据导入完成: {imported_products} 个产品, {imported_prices} 条价格")


def map_category(category: str) -> str:
    """映射模型类别到产品类别"""
    category_map = {
        "text_generation": "AI-大模型-文本生成",
        "vision": "AI-大模型-视觉理解",
        "multimodal": "AI-大模型-多模态",
        "audio": "AI-大模型-语音",
        "embedding": "AI-大模型-向量",
        "rerank": "AI-大模型-重排序",
        "image_generation": "AI-大模型-图像生成",
        "video_generation": "AI-大模型-视频生成",
        "speech_synthesis": "AI-大模型-语音合成",
        "speech_recognition": "AI-大模型-语音识别",
    }
    return category_map.get(category, f"AI-大模型-{category}")


async def get_import_stats(session: AsyncSession) -> Dict[str, int]:
    """获取导入统计"""
    stats = {}
    
    result = await session.execute(text("SELECT COUNT(*) FROM products"))
    stats["products"] = result.scalar() or 0
    
    result = await session.execute(text("SELECT COUNT(*) FROM product_prices"))
    stats["prices"] = result.scalar() or 0
    
    result = await session.execute(text("SELECT COUNT(*) FROM product_specs"))
    stats["specs"] = result.scalar() or 0
    
    return stats


async def main(clear_existing: bool = False):
    """主函数"""
    logger.info("=" * 50)
    logger.info("开始数据导入")
    logger.info("=" * 50)
    
    # 1. 创建表
    await create_tables()
    
    async with async_session_maker() as session:
        # 2. 可选：清空现有数据
        if clear_existing:
            await clear_tables(session)
        
        # 3. 导入百炼模型数据
        await import_bailian_models(session)
        
        # 4. 导入爬虫输出数据
        await import_crawler_output(session)
        
        # 5. 显示统计
        stats = await get_import_stats(session)
        logger.info("=" * 50)
        logger.info("导入完成，数据统计:")
        logger.info(f"  - 产品数: {stats['products']}")
        logger.info(f"  - 价格数: {stats['prices']}")
        logger.info(f"  - 规格数: {stats['specs']}")
        logger.info("=" * 50)


if __name__ == "__main__":
    import sys
    
    # 支持命令行参数 --clear 清空现有数据
    clear_existing = "--clear" in sys.argv
    
    if clear_existing:
        logger.warning("将清空现有数据后重新导入!")
    
    asyncio.run(main(clear_existing=clear_existing))
