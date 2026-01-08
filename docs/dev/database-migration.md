"""
数据库迁移说明

本次数据模型增强需要使用 Alembic 创建数据库迁移脚本。

## 迁移内容

### QuoteSheet 表新增字段：
- quote_no: String(50), unique, not null
- created_by: String(100), not null
- sales_name: String(100), nullable
- customer_contact: String(100), nullable
- customer_email: String(255), nullable
- remarks: Text, nullable
- terms: Text, nullable
- global_discount_rate: Numeric(5,4), not null, default 1.0000
- global_discount_remark: String(255), nullable
- total_original_amount: Numeric(20,6), nullable

### QuoteSheet 表字段类型修改：
- total_amount: String(20) → Numeric(20,6)

### QuoteSheet 表新增索引：
- ix_quote_no (quote_no)
- ix_quote_created_by (created_by)
- ix_quote_created_at (created_at)

### QuoteItem 表新增字段：
- region: String(50), not null, default 'cn-beijing'
- region_name: String(100), nullable
- modality: String(50), not null
- capability: String(50), nullable
- model_type: String(50), nullable
- context_spec: String(50), nullable
- input_tokens: BigInteger, nullable
- output_tokens: BigInteger, nullable
- inference_mode: String(50), nullable
- original_price: Numeric(20,6), not null
- discount_rate: Numeric(5,4), not null, default 1.0000
- final_price: Numeric(20,6), not null
- billing_unit: String(50), not null
- sort_order: Integer, not null, default 0

### QuoteItem 表字段类型修改：
- unit_price: String(20) → Numeric(20,6)
- subtotal: String(20) → Numeric(20,6)

### QuoteItem 表字段默认值修改：
- quantity: 增加 default 1
- duration_months: 增加 default 1

### QuoteItem 表新增索引：
- ix_item_sort_order (quote_id, sort_order)

### QuoteVersion 表新增字段：
- change_type: String(50), nullable
- changes_summary: String(500), nullable

### QuoteVersion 表新增索引：
- ix_version_number (quote_id, version_number)

## 执行迁移的步骤

1. 生成迁移脚本：
```bash
cd /Users/chengpeng/MyProject/LLM_QUOTATION/backend
alembic revision --autogenerate -m "enhance_quote_models_add_fields"
```

2. 检查生成的迁移脚本：
```bash
# 脚本位于 backend/alembic/versions/
# 检查 upgrade() 和 downgrade() 函数
```

3. 手动调整迁移脚本（如有必要）：
   - 为新增的 not null 字段设置临时默认值
   - 为已存在的报价单生成 quote_no
   - 数据回填逻辑

4. 执行迁移：
```bash
alembic upgrade head
```

5. 验证迁移：
```bash
# 连接数据库，检查表结构
psql -U <username> -d <database>
\\d quote_sheets
\\d quote_items
\\d quote_versions
```

## 数据回填建议

对于已存在的数据，需要回填以下字段：

### QuoteSheet:
- quote_no: 生成历史编号（如 QT20260101XXXX）
- created_by: 设置为默认值（如 "system"）
- global_discount_rate: 默认 1.0000
- total_original_amount: 从 items 汇总计算

### QuoteItem:
- region: 默认 "cn-beijing"
- modality: 根据 product 的 category 映射
- original_price: 复制 unit_price * quantity * duration_months
- discount_rate: 默认 1.0000
- final_price: 复制 original_price
- billing_unit: 默认 "千Token"
- sort_order: 按创建顺序自增

## 回滚计划

如果迁移失败，可以回滚：
```bash
alembic downgrade -1
```

## 注意事项

1. **备份数据库**：执行迁移前必须备份生产数据库
2. **测试环境验证**：先在测试环境执行并验证
3. **停机窗口**：生产环境迁移需要在维护窗口执行
4. **监控**：迁移后监控应用日志和数据库性能
5. **版本控制**：将迁移脚本提交到 Git

## 完成后验证清单

- [ ] 所有表结构正确
- [ ] 所有索引创建成功
- [ ] 旧数据可以正常访问
- [ ] 新建报价单功能正常
- [ ] 价格计算功能正常
- [ ] API 接口正常返回
