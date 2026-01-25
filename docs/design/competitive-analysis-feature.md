# 竞争分析功能 - 产品设计文档

> 生成时间：2026-01-25
> 设计原则：最小化改动、非侵入式、可选功能

---

## 📌 一、需求锚定（Why）

### 核心痛点
销售人员在使用报价系统为客户推荐通义千问(Qwen)系列模型时，缺少竞品对标数据作为支撑：
- **无法快速获取竞品价格对比**：不清楚Qwen与火山豆包(Doubao)、Gemini等竞品的价格差异
- **缺少说服客户的话术依据**：需要手动查找竞品信息并组织对比论述
- **对标信息分散**：竞品数据以JSON文件形式存在，无法在报价流程中直接使用

### 核心价值
在报价流程中自动提供竞品对标信息，帮助销售人员：
- **即时获取价格对比**：自动显示Qwen与Doubao的价格差异（输入/输出价格）
- **获得专业销售话术**：基于产品定位和市场分析的竞争洞察建议
- **提升报价说服力**：数据驱动的对比分析，增强客户信任

### 一句话定义
> "这是一个为 **LLM报价系统的销售人员** 设计的，通过 **在报价详情页自动显示竞品对标卡片** 来解决 **缺少竞品分析数据支撑** 的 **增强功能**。"

---

## ✂️ 二、功能剪枝（What）

### 功能清单
| 功能 | 优先级 | MVP | 说明 |
|------|--------|-----|------|
| 报价详情页竞品分析入口 | P0 | ✅ | 在现有"竞争分析"按钮上增强功能 |
| 基于Position对齐的竞品匹配 | P0 | ✅ | 按JSON中的position字段严格匹配 |
| 竞品分析卡片弹窗 | P0 | ✅ | 显示Qwen vs Doubao模型名、价格、话术 |
| AI助手推荐时提及竞品 | P1 | ✅ | AI在推荐模型时自动附带竞品优势 |
| 无匹配数据的空状态提示 | P0 | ✅ | 当JSON中无对应数据时友好提示 |
| Excel导出竞品分析sheet | P2 | ❌ | MVP暂不实现，后续迭代 |
| 竞品数据库化管理 | P2 | ❌ | MVP使用JSON文件，保持轻量 |

### MVP 范围
- ✅ **后端API**：新增竞品查询接口，启动时加载JSON到内存缓存，提供精确匹配查询
- ✅ **前端弹窗**：全局入口+模型列表选择+竞品详情展示，支持上/下切换
- ✅ **模型名映射**：维护model_code到JSON model字段的精确映射表
- ✅ **AI集成**：在AI编排器的推荐逻辑中注入竞品分析话术
- ✅ **空状态处理**：无匹配数据时显示"暂无竞品对比数据"
- ✅ **数据时效性**：显示竞品数据更新日期，提升可信度
- ❌ 暂不做：Excel导出、数据管理后台、Redis缓存

### 边界定义
- **本次只做**：
  - 基于现有JSON文件的竞品信息查询和展示
  - 支持文本类(Qwen系列)、图片类(通义图片创作)、视频类(通义万相视频创作)三大类
  - Position对齐匹配机制（精确匹配）
  
- **本次不做**：
  - 竞品数据的CRUD管理界面
  - 多竞品横向对比（仅限Qwen vs Doubao）
  - 竞品推荐算法优化（如模糊匹配、相似度计算）
  - 竞品分析数据的持久化存储

---

## 🔄 三、逻辑建模（How）

### 核心流程（Happy Path）

#### 场景1：报价详情页查看竞品分析
```
Step 1: 销售人员在报价详情页查看已选模型
    ↓
Step 2: 点击页面右下角的"竞争分析"全局按钮
    ↓
Step 3: 弹出竞品分析弹窗，显示报价单中所有模型的列表
    ↓
Step 4: 点击选择某个模型（或默认显示第一个模型）
    ↓
Step 5: 系统根据模型名称查询JSON，通过精确匹配model_code获取竞品数据
    ↓
Step 6: 在弹窗右侧显示竞品对比详情：
        - Qwen模型：名称、Position、角色、价格（输入/输出）
        - Doubao竞品：名称、Position、价格（输入/输出）
        - 竞争洞察：JSON中的insight话术（关键词高亮显示）
    ↓
Step 7: 销售人员可通过"上一个/下一个"按钮快速切换查看其他模型竞品
    ↓
Step 8: 关闭弹窗，返回报价详情页
```

#### 场景2：AI助手推荐模型时自动提及竞品
```
Step 1: 用户向AI助手描述需求（如"需要高性价比的文本模型"）
    ↓
Step 2: AI编排器调用recommend_model工具
    ↓
Step 3: 推荐逻辑查询竞品数据，将Doubao对标信息注入上下文
    ↓
Step 4: AI生成回复："推荐Qwen-Plus，性价比高，与Doubao Seed定价相同但支持更长上下文..."
    ↓
Step 5: 用户确认添加到报价单
```

### 异常处理
| 场景 | 处理方式 |
|------|----------|
| JSON文件缺失或损坏 | 后端启动时加载失败，记录错误日志，API返回空数组 |
| 选中的Qwen模型在映射表中不存在 | 弹窗显示"该模型暂无竞品对比数据"，不影响正常报价流程 |
| 映射表有model_code但JSON中无对应数据 | 返回空状态，提示"该模型暂未收录竞品对标信息" |
| Position字段不一致 | 严格按映射表+model精确匹配，无匹配则返回空 |
| 并发请求 | 使用内存缓存，启动时加载JSON到全局变量，无IO瓶颈 |

### 分支判断

#### 竞品匹配逻辑
```python
# 步骤1：通过映射表转换model_code
如果 [model_code 在 MODEL_NAME_MAPPING 中]:
    json_model_name = MODEL_NAME_MAPPING[model_code]
否则：
    返回 { "has_competitor": False, "message": "该模型未配置竞品映射" }

# 步骤2：在JSON数据中精确匹配
如果 [json_model_name 在 竞品JSON数据 中存在]:
    提取 qwen.model、qwen.position、qwen.role、doubao.model、insight
    返回完整的竞品对比数据
否则：
    返回 { "has_competitor": False, "message": "暂无竞品对比数据" }
```

#### 前端显示逻辑
```javascript
如果 [API返回 has_competitor = True]:
    渲染竞品对比卡片（模型名、价格表格、话术文本）
否则：
    显示空状态卡片（提示无数据，引导用户继续报价）
```

---

## 📊 四、数据抽象（Data）

### 数据源结构（JSON文件）
#### 竞品对标数据（常用模型友商定价对标.json）

**重要说明**：为确保精确匹配，需要维护一个模型名称映射表，将数据库中的`model_code`映射到JSON中的`qwen.model`字段。

**模型名称映射表**：
```python
# 在 competitor_service.py 中定义
MODEL_NAME_MAPPING = {
    "qvq-max": "Qwen3-Max(<32k)",           # 旗舰模型
    "qwen-plus": "Qwen-Plus(<128k)",       # 主推性价比模型
    "qwen-flash": "Qwen-Flash(<128k)",     # 高吞吐低成本模型
    "qwen-image": "Qwen-image (主推)",      # 主推图片模型
    "wanxiang-image": "万相生图",           # 高质量画面创作
    "z-image": "Z-Image",                  # 高端图片创作
    "wanxiang-video": "通义万相视频创作-旗舰", # 视频创作旗舰模型
}
```

#### 竞品对标数据（常用模型友商定价对标.json）
```json
{
  "category": "text",           // 模型类别：text/image/video
  "family": "Qwen系列",          // 产品线名称
  "qwen": {
    "model": "Qwen-Plus(<128k)",    // Qwen模型名称
    "position": 2,                  // 产品矩阵位置
    "role": "主推性价比模型",        // 定位
    "cost_1m_tokens_input_cny": 0.8,  // 输入价格（元/百万Token）
    "cost_1m_tokens_output_cny": 2.0  // 输出价格（元/百万Token）
  },
  "doubao": {
    "model": "Seed-1.6/1.5pro(<32k)", // Doubao竞品模型名称
    "position": 2,                    // 对齐位置
    "cost_1m_tokens_input_cny": 0.8,
    "cost_1m_tokens_output_cny": 2.0
  },
  "baseline": {
    "model": "Gemini 2.5 Pro",        // 基线参考模型
    "cost_ratio_vs_gemini": "1:57.9"  // 性价比对比
  },
  "insight": "Qwen-Plus 对标 Doubao Seed 主力模型..." // 销售话术
}
```

### API响应结构

#### 后端接口：GET /api/v1/competitors/match
**请求参数**
```typescript
{
  model_name: string,     // Qwen模型名称（如"qvq-max", "Qwen-Plus"）
  category?: string       // 可选：类别过滤（text/image/video）
}
```

**响应结构**
```typescript
{
  has_competitor: boolean,
  data: {
    qwen: {
      model: string,
      position: number,
      role: string,
      input_price: number,    // 转换为标准单位
      output_price: number
    },
    doubao: {
      model: string,
      position: number,
      input_price: number,
      output_price: number
    },
    insight: string,          // 竞争洞察话术
    category: string
  } | null
}
```

### 前端数据模型
```typescript
interface CompetitorAnalysis {
  hasCompetitor: boolean;
  qwen?: {
    model: string;
    position: number;
    role: string;
    inputPrice: number;
    outputPrice: number;
  };
  doubao?: {
    model: string;
    position: number;
    inputPrice: number;
    outputPrice: number;
  };
  insight?: string;
  category?: string;
}
```

### 实体关系
```
QuoteItem (现有) : CompetitorData (JSON) = N : 1
  - 一个报价项可能有0-1个竞品对标数据
  - 通过 model_name 字段关联查询
```

---

## 🎨 五、交互映射（Interface）

### 页面结构（报价详情页）

#### 竞品分析入口
```
┌─────────────────────────────────────────┐
│  报价单详情 - 共 3 项产品                 │
├─────────────────────────────────────────┤
│  1. qvq-max                   ¥12.80   │
├─────────────────────────────────────────┤
│  2. Qwen-Plus                 ¥2.00    │
├─────────────────────────────────────────┤
│  3. Qwen-Flash                ¥1.50    │
└─────────────────────────────────────────┘
│  [上一步]  [导出报价单]  [竞争分析]  ← 全局入口
```

#### 竞品分析弹窗卡片（全局入口+左右分栏布局）
```
┌──────────────────────────────────────────────────────────────┐
│  🔍 竞品对标分析              数据更新：2026-01-25      [×]  │
├────────────────┬─────────────────────────────────────────────┤
│ 📋 模型列表    │  📊 价格对比一览                            │
│                │  ┌────────────────────────────────────────┐ │
│ ✓ qvq-max      │  │      Qwen-Plus    vs    Doubao Seed   │ │
│ • Qwen-Plus ←  │  │ 输入  ¥0.8/M      ≈      ¥0.8/M    ✓  │ │
│ • Qwen-Flash   │  │ 输出  ¥2.0/M      ≈      ¥2.0/M    ✓  │ │
│                │  │ 上下文 128k       >      32k       ⭐  │ │
│                │  └────────────────────────────────────────┘ │
│                │                                             │
│                │  💡 销售话术建议                            │
│                │  ┌────────────────────────────────────────┐│
│                │  │ Qwen-Plus 对标 Doubao Seed 主力模型，  ││
│                │  │ 在输入/输出单价同一量级下，Qwen 可以    ││
│                │  │ 通过更长上下文、更全生态（如百炼平台   ││
│                │  │ 能力）来拉高整体价值...                ││
│                │  │                                         ││
│                │  │ 关键词：[更长上下文] [更全生态] [百炼]  ││
│                │  └────────────────────────────────────────┘│
├────────────────┴─────────────────────────────────────────────┤
│               [< 上一个]     [下一个 >]     [关闭]            │
└──────────────────────────────────────────────────────────────┘
```

#### 空状态提示
```
┌──────────────────────────────────────────────────────────────┐
│  🔍 竞品对标分析              数据更新：2026-01-25      [×]  │
├────────────────┬─────────────────────────────────────────────┤
│ 📋 模型列表    │                 💡                          │
│                │         该模型暂无竞品数据                  │
│ ✓ qvq-max      │                                             │
│ • Qwen-Plus    │  您可以：                                   │
│ • Qwen-Flash ← │  • 继续完成报价流程                         │
│                │  • 联系产品团队补充数据                     │
│                │                                             │
├────────────────┴─────────────────────────────────────────────┤
│               [< 上一个]     [下一个 >]     [关闭]            │
└──────────────────────────────────────────────────────────────┘
```

### 页面清单
| 页面/组件 | 功能 | 核心元素 |
|-----------|------|----------|
| QuoteDetail（报价详情页） | 显示报价项列表 | 竞争分析按钮（已存在） |
| CompetitorModal（竞品分析弹窗） | 展示对比数据 | 模型卡片、价格表格、话术文本 |
| AIChatWindow（AI助手） | 增强推荐话术 | 竞品优势自动注入回复 |

### 状态反馈
| 状态 | 反馈形式 |
|------|----------|
| 加载竞品数据中 | 弹窗显示loading spinner + "正在加载竞品数据..." |
| 加载成功有数据 | 显示完整的对比卡片 |
| 加载成功无匹配 | 显示空状态提示卡片 |
| 加载失败 | Toast提示"竞品数据加载失败，请稍后重试" |

### 视觉风格
- **风格**：专业简洁，与现有报价系统保持一致
- **主色调**：沿用系统蓝色主题（#1890ff）
- **卡片设计**：白底卡片 + 灰色分割线，信息分区清晰
- **字体层级**：标题16px加粗，正文14px，价格数字使用等宽字体

---

## 🚀 六、Prompt 封装（Action）

### 技术栈选择
- **前端**：React 18 + Axios（沿用现有技术栈）
- **后端**：FastAPI（Python 3.10+）
- **数据源**：JSON文件（常用模型友商定价对标.json）
- **部署**：无额外部署要求，与现有系统一起部署

### 开发指令

#### 第一步：后端API开发

**任务**：新增竞品查询服务和API端点

1. 创建服务层：`app/services/competitor_service.py`
   - 读取JSON文件的函数
   - 根据model_name和position匹配竞品数据
   - 处理无匹配情况

2. 创建API端点：`app/api/v1/endpoints/competitors.py`
   - GET `/api/v1/competitors/match?model_name=xxx`
   - 返回标准化的竞品对比数据

3. 注册路由：在 `app/api/v1/__init__.py` 中注册competitors路由

**实现要点**：
- **内存缓存**：启动时加载JSON到全局变量，避免重复IO
- **精确匹配**：使用MODEL_NAME_MAPPING映射表进行精确匹配
- **路径配置**：在`config.py`中定义`COMPETITOR_DATA_FILE`环境变量
  ```python
  # app/core/config.py
  COMPETITOR_DATA_FILE = os.getenv(
      "COMPETITOR_DATA_FILE",
      os.path.join(BASE_DIR, "data/competitor_comparison.json")
  )
  ```
- **错误处理**：文件不存在、JSON格式错误、编码问题（UTF-8）
- **日志记录**：启动加载状态、查询请求、匹配结果
- **数据时效性**：记录JSON文件最后修改时间，返回给前端显示
- 不创建数据库表，保持轻量级

---

#### 第二步：前端组件开发

**任务**：创建竞品分析弹窗组件

1. 创建组件：`frontend/src/components/CompetitorModal.jsx`
   - Props接收：isOpen, onClose, modelName, quoteItem
   - 调用API获取竞品数据
   - 渲染对比卡片或空状态

2. 集成到报价详情页：`frontend/src/pages/QuoteDetail.jsx`
   - 在现有"竞争分析"按钮的点击事件上调用 `<CompetitorModal>`
   - 传递当前选中的模型信息

3. 样式优化：沿用现有UI组件库（如Ant Design）风格

**实现要点**：
- **左右分栏布局**：左侧模型列表（200px固定宽）+ 右侧竞品详情（自适应）
- **价格表格展示**：使用表格布局，输入/输出价格对比清晰
- **关键词高亮**：安全地高亮竞争话术中的关键词（避免XSS）
  ```javascript
  function HighlightText({ text, keywords }) {
    const parts = text.split(new RegExp(`(${keywords.join('|')})`, 'gi'));
    return parts.map((part, i) => 
      keywords.some(kw => kw.toLowerCase() === part.toLowerCase()) 
        ? <mark key={i} className="highlight">{part}</mark> 
        : part
    );
  }
  ```
- **快速切换**："上一个/下一个"按钮，支持键盘左右箭头
- **状态管理**：使用本地useState + React Query缓存API结果
- **数据时效性**：顶部显示"数据更新：YYYY-MM-DD"
- **移动端适配**：改为底部抽屉（Bottom Sheet）形式
- **防滚动穿透**：弹窗打开时锁定body滚动
  ```javascript
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    }
    return () => { document.body.style.overflow = 'auto'; };
  }, [isOpen]);
  ```

---

#### 第三步：AI助手增强（可选）

**任务**：在AI推荐模型时自动附带竞品优势

1. 修改AI工具集：`app/agents/tools.py`
   - 在 `recommend_model` 函数中增加竞品查询逻辑
   - 将竞品insight注入到返回的推荐理由中

2. 修改AI提示词：`app/agents/orchestrator.py`
   - 在系统提示词中增加"当推荐Qwen模型时，主动对比Doubao竞品优势"

**实现要点**：
- 竞品数据加载失败不影响AI推荐流程
- 自然语言融合：避免生硬的数据堆砌
- 仅对有竞品数据的模型增强话术

---

### 最小化改动清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| 后端-新增 | `app/services/competitor_service.py` | 竞品服务（新文件） |
| 后端-新增 | `app/api/v1/endpoints/competitors.py` | 竞品API（新文件） |
| 后端-修改 | `app/core/config.py` | 增加COMPETITOR_DATA_FILE配置（+3行） |
| 后端-修改 | `app/api/v1/__init__.py` | 注册新路由（+1行） |
| 前端-新增 | `src/components/CompetitorModal/` | 竞品弹窗组件目录（~300行） |
| 前端-修改 | `src/pages/QuoteDetail.jsx` | 集成全局竞品分析按钮（+15行） |
| 配置-修改 | `.env.example` | 环境变量示例（+2行） |
| 可选-修改 | `app/agents/tools.py` | AI推荐增强（+30行） |

**文件结构**：
```
src/components/CompetitorModal/
├── index.jsx              // 主弹窗容器
├── ModelSelector.jsx      // 左侧模型列表
├── CompetitorDetail.jsx   // 右侧竞品详情
├── PriceTable.jsx         // 价格对比表格
├── InsightSection.jsx     // 话术展示区（含高亮）
└── styles.module.css      // 样式文件
```

**预估工作量**（修正）：
- 后端开发：3-4小时（增加了内存缓存和映射表）
- 前端开发：4-5小时（增加了左右分栏和快速切换）
- 联调测试：2小时
- 总计：**1-1.5个工作日**

---

## 📝 备注

### 后续迭代方向
1. **P1优化**：提供`/api/v1/competitors/reload`接口，支持热更新JSON数据（无需重启服务）
2. **P1优化**：自动扫描数据库Product表，生成MODEL_NAME_MAPPING映射表
3. **P2功能**：Excel导出时增加"竞品分析"sheet页
4. **P2功能**：在"选模型(Step1)"阶段，模型卡片上显示"有竞品对比"小标签
5. **P3功能**：竞品数据管理后台（CRUD界面）
6. **P3功能**：多竞品横向对比（Qwen vs Doubao vs Gemini三方对比）
7. **P3功能**：AI推荐时自然语言融合竞品信息，避免生硬粘贴

### 风险提示
- **映射表维护成本**：新增模型时需同步更新MODEL_NAME_MAPPING
- **JSON格式变更**：JSON结构调整需同步更新解析逻辑，建议使用Pydantic校验
- **数据更新机制**：竞品数据需定期更新，当前需重启服务生效，后续可考虑热更新接口
- **中文文件名问题**：建议将`常用模型友商定价对标.json`重命名为`competitor_comparison.json`避免跨平台编码问题
- **性能瓶颈已解决**：使用内存缓存后，高并发场景无IO瓶颈

### 测试要点
- 单元测试：JSON解析、Position匹配逻辑
- 集成测试：API接口返回正确性
- E2E测试：报价详情页弹窗显示流程
- 边界测试：文件缺失、JSON格式错误、无匹配数据

---

*本文档由 idea-to-design skill 生成*
*设计者：Qoder AI Assistant*
*审核者：待用户确认*
