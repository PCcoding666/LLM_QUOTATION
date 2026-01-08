"""
智价引擎 E2E 可视化测试界面
模拟真实用户操作流程的最小化 UI

核心流程：
1. 新建报价单 → 筛选商品 → 勾选模型 → 配置参数 → 设置折扣 → 保存生成
2. 修改报价单 → 增/删/改商品 → 调整折扣 → 保存更新

启动方式：
    cd backend
    streamlit run e2e_ui_demo.py --server.port 8502
"""
import streamlit as st
import httpx
from typing import Dict, List, Any, Optional
from datetime import datetime


# ==================== API 请求封装 ====================
API_BASE_URL = "http://localhost:8000/api/v1"


def api(method: str, path: str, params: Dict = None, json_data: Dict = None) -> Dict:
    """发送 API 请求"""
    url = f"{API_BASE_URL}{path}"
    try:
        with httpx.Client(timeout=30, proxy=None, trust_env=False) as client:
            resp = client.request(method=method, url=url, params=params, json=json_data)
            if resp.status_code >= 400:
                st.error(f"API 错误: {resp.status_code} - {resp.text[:200]}")
                return None
            return resp.json()
    except Exception as e:
        st.error(f"连接错误: {e}")
        return None


# ==================== 状态初始化 ====================
def init_state():
    """初始化 session state"""
    defaults = {
        "page": "list",           # 当前页面: list / workspace
        "current_quote": None,    # 当前编辑的报价单
        "selected_models": [],    # 已勾选的模型
        "pending_items": [],      # 待添加的配置项
        "filters": {},            # 筛选条件缓存
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ==================== 页面：报价单列表 ====================
def page_quote_list():
    """报价单列表页"""
    st.header("📋 我的报价单")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.caption("管理您的所有报价单，点击进入编辑")
    with col2:
        if st.button("➕ 新建报价单", type="primary", use_container_width=True):
            create_new_quote()
    
    # 筛选条件
    with st.expander("🔍 筛选", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            status_filter = st.selectbox("状态", ["全部", "draft", "confirmed", "expired"])
        with col2:
            customer_filter = st.text_input("客户名称")
        with col3:
            st.write("")
            if st.button("搜索"):
                st.session_state.search_triggered = True
    
    # 加载报价单列表
    params = {"page_size": 20}
    if status_filter != "全部":
        params["status"] = status_filter
    if customer_filter:
        params["customer_name"] = customer_filter
    
    result = api("GET", "/quotes/", params=params)
    if not result:
        st.info("暂无报价单，点击「新建报价单」开始")
        return
    
    quotes = result.get("data", [])
    if not quotes:
        st.info("暂无报价单，点击「新建报价单」开始")
        return
    
    # 报价单列表
    for quote in quotes:
        render_quote_card(quote)


def render_quote_card(quote: Dict):
    """渲染报价单卡片"""
    with st.container(border=True):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1.5, 1.5, 1.5])
        
        with col1:
            st.markdown(f"**{quote.get('quote_no', 'N/A')}**")
            st.caption(quote.get('customer_name', '未填写客户'))
        
        with col2:
            st.caption(quote.get('project_name', '未填写项目'))
            created = quote.get('created_at', '')[:10]
            st.caption(f"创建: {created}")
        
        with col3:
            status = quote.get('status', 'unknown')
            status_map = {"draft": "🟡 草稿", "confirmed": "🟢 已确认", "expired": "🔴 已过期"}
            st.write(status_map.get(status, f"⚪ {status}"))
        
        with col4:
            total = float(quote.get('total_amount', 0))
            st.metric("总金额", f"¥{total:,.2f}", label_visibility="collapsed")
        
        with col5:
            quote_id = quote.get('quote_id')
            if st.button("编辑", key=f"edit_{quote_id}", use_container_width=True):
                enter_workspace(quote_id)


def create_new_quote():
    """创建新报价单并进入工作台"""
    result = api("POST", "/quotes/", json_data={
        "customer_name": "待填写",
        "project_name": "待填写",
        "created_by": "e2e_demo",
        "valid_days": 30
    })
    if result:
        st.session_state.current_quote = result
        st.session_state.selected_models = []
        st.session_state.pending_items = []
        st.session_state.page = "workspace"
        st.success(f"报价单 {result.get('quote_no')} 创建成功！")
        st.rerun()


def enter_workspace(quote_id: str):
    """进入报价工作台"""
    result = api("GET", f"/quotes/{quote_id}")
    if result:
        st.session_state.current_quote = result
        st.session_state.selected_models = []
        st.session_state.pending_items = []
        st.session_state.page = "workspace"
        st.rerun()


# ==================== 页面：报价工作台 ====================
def page_workspace():
    """报价工作台 - 核心编辑界面"""
    quote = st.session_state.current_quote
    if not quote:
        st.session_state.page = "list"
        st.rerun()
        return
    
    # 顶部导航
    col1, col2, col3 = st.columns([1, 6, 2])
    with col1:
        if st.button("← 返回列表"):
            st.session_state.page = "list"
            st.rerun()
    with col2:
        st.header(f"📝 报价工作台 - {quote.get('quote_no', '')}")
    with col3:
        status = quote.get('status', 'draft')
        st.write(f"状态: {'🟡 草稿' if status == 'draft' else '🟢 已确认'}")
    
    # 主要内容区 - 使用 tabs 组织流程
    tab1, tab2, tab3, tab4 = st.tabs([
        "① 基本信息", 
        "② 筛选并添加商品", 
        "③ 商品配置与折扣",
        "④ 预览与导出"
    ])
    
    with tab1:
        render_basic_info(quote)
    
    with tab2:
        render_product_selection()
    
    with tab3:
        render_item_config(quote)
    
    with tab4:
        render_preview(quote)


def render_basic_info(quote: Dict):
    """基本信息编辑"""
    st.subheader("📋 报价单基本信息")
    
    if quote.get('status') != 'draft':
        st.warning("已确认的报价单不可修改基本信息")
    
    with st.form("basic_info_form"):
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("客户名称 *", value=quote.get('customer_name', ''))
            sales_name = st.text_input("销售人员", value=quote.get('sales_name', ''))
            customer_contact = st.text_input("客户联系人", value=quote.get('customer_contact', ''))
        with col2:
            project_name = st.text_input("项目名称", value=quote.get('project_name', ''))
            customer_email = st.text_input("客户邮箱", value=quote.get('customer_email', ''))
            valid_until = st.date_input("有效期至", value=None)
        
        remarks = st.text_area("备注", value=quote.get('remarks', ''), height=80)
        
        if quote.get('status') == 'draft':
            submitted = st.form_submit_button("💾 保存基本信息", type="primary")
            if submitted:
                update_data = {
                    "customer_name": customer_name,
                    "project_name": project_name,
                    "sales_name": sales_name,
                    "customer_contact": customer_contact,
                    "customer_email": customer_email,
                    "remarks": remarks
                }
                result = api("PUT", f"/quotes/{quote.get('quote_id')}", json_data=update_data)
                if result:
                    st.session_state.current_quote = result
                    st.success("基本信息已保存")
                    st.rerun()


def render_product_selection():
    """商品筛选与选择"""
    st.subheader("🔍 筛选大模型商品")
    
    # Step 1: 筛选条件
    with st.container(border=True):
        st.markdown("**筛选条件**")
        
        # 获取筛选选项
        filters = api("GET", "/products/filters")
        if not filters:
            st.error("无法加载筛选选项")
            return
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            regions = [{"code": "", "name": "全部地域"}] + filters.get("regions", [])
            region = st.selectbox(
                "地域", 
                options=[r["code"] for r in regions],
                format_func=lambda x: next((r["name"] for r in regions if r["code"] == x), x)
            )
        
        with col2:
            modalities = [{"code": "", "name": "全部模态"}] + filters.get("modalities", [])
            modality = st.selectbox(
                "模态",
                options=[m["code"] for m in modalities],
                format_func=lambda x: next((m["name"] for m in modalities if m["code"] == x), x)
            )
        
        with col3:
            capabilities = [{"code": "", "name": "全部能力"}] + filters.get("capabilities", [])
            capability = st.selectbox(
                "能力",
                options=[c["code"] for c in capabilities],
                format_func=lambda x: next((c["name"] for c in capabilities if c["code"] == x), x)
            )
        
        with col4:
            model_types = [{"code": "", "name": "全部类型"}] + filters.get("model_types", [])
            model_type = st.selectbox(
                "模型类型",
                options=[t["code"] for t in model_types],
                format_func=lambda x: next((t["name"] for t in model_types if t["code"] == x), x)
            )
        
        # 名称批量搜索
        col1, col2 = st.columns([3, 1])
        with col1:
            keyword = st.text_input(
                "名称搜索",
                placeholder="输入模型名称关键词，多个用逗号分隔",
                help="支持批量搜索：qwen-max, qwen-plus, deepseek"
            )
        with col2:
            st.write("")
            search_btn = st.button("🔍 搜索商品", type="primary", use_container_width=True)
    
    # Step 2: 商品列表
    if search_btn or "models_cache" in st.session_state:
        params = {"page": 1, "page_size": 50}
        if region:
            params["region"] = region
        if modality:
            params["modality"] = modality
        if capability:
            params["capability"] = capability
        if model_type:
            params["model_type"] = model_type
        if keyword:
            params["keyword"] = keyword
        
        result = api("GET", "/products/models", params=params)
        if result:
            st.session_state.models_cache = result.get("data", [])
    
    models = st.session_state.get("models_cache", [])
    
    if models:
        st.markdown(f"**找到 {len(models)} 个模型，勾选要添加的商品：**")
        
        # 全选/取消
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("全选本页"):
                st.session_state.selected_models = [m.get("model_id") for m in models]
                st.rerun()
        with col2:
            if st.button("取消全选"):
                st.session_state.selected_models = []
                st.rerun()
        with col3:
            selected_count = len(st.session_state.selected_models)
            st.info(f"已选择 {selected_count} 个模型")
        
        # 模型列表
        for model in models:
            render_model_checkbox(model)
        
        # 添加按钮
        st.divider()
        if st.session_state.selected_models:
            if st.button("➕ 将选中模型添加到报价单", type="primary", use_container_width=True):
                add_selected_to_pending()
    else:
        st.info("点击「搜索商品」加载模型列表")


def render_model_checkbox(model: Dict):
    """渲染单个模型选择项"""
    model_id = model.get("model_id", "")
    is_selected = model_id in st.session_state.selected_models
    
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([0.5, 3, 2, 2])
        
        with col1:
            checked = st.checkbox(
                "选择",
                value=is_selected,
                key=f"check_{model_id}",
                label_visibility="collapsed"
            )
            if checked and model_id not in st.session_state.selected_models:
                st.session_state.selected_models.append(model_id)
            elif not checked and model_id in st.session_state.selected_models:
                st.session_state.selected_models.remove(model_id)
        
        with col2:
            st.markdown(f"**{model.get('model_name', model_id)}**")
            st.caption(f"ID: {model_id}")
        
        with col3:
            st.caption(f"厂商: {model.get('vendor', 'N/A')}")
            st.caption(f"类别: {model.get('category', 'N/A')}")
        
        with col4:
            pricing = model.get("pricing") or {}
            input_p = pricing.get("input_price", 0)
            output_p = pricing.get("output_price", 0)
            if input_p or output_p:
                st.caption(f"输入: ¥{input_p}/千tokens")
                st.caption(f"输出: ¥{output_p}/千tokens")
            else:
                st.caption("价格待查询")


def add_selected_to_pending():
    """将选中的模型添加到待配置列表"""
    models = st.session_state.get("models_cache", [])
    selected_ids = st.session_state.selected_models
    
    for model_id in selected_ids:
        model = next((m for m in models if m.get("model_id") == model_id), None)
        if model:
            # 添加到 pending_items
            item = {
                "model_id": model_id,
                "model_name": model.get("model_name", model_id),
                "vendor": model.get("vendor", ""),
                "pricing": model.get("pricing", {}),
                "region": "cn-beijing",
                "input_tokens": 100000,
                "output_tokens": 50000,
                "inference_mode": None,
                "quantity": 1,
                "duration_months": 12
            }
            # 避免重复
            if not any(p["model_id"] == model_id for p in st.session_state.pending_items):
                st.session_state.pending_items.append(item)
    
    st.session_state.selected_models = []
    st.success(f"已添加 {len(selected_ids)} 个模型到配置列表")
    st.rerun()


def render_item_config(quote: Dict):
    """商品配置与折扣设置"""
    st.subheader("⚙️ 商品参数配置")
    
    # 已有的报价项
    items = quote.get("items", [])
    pending = st.session_state.pending_items
    
    if not items and not pending:
        st.info("暂无商品，请先在「筛选并添加商品」中选择模型")
        return
    
    # Tab 区分：待添加 vs 已添加
    tab_pending, tab_added = st.tabs([
        f"📝 待添加 ({len(pending)})", 
        f"✅ 已在报价单 ({len(items)})"
    ])
    
    with tab_pending:
        render_pending_items(quote)
    
    with tab_added:
        render_existing_items(quote, items)
    
    # 批量折扣设置
    st.divider()
    render_global_discount(quote)


def render_pending_items(quote: Dict):
    """渲染待添加的商品配置"""
    pending = st.session_state.pending_items
    
    if not pending:
        st.info("暂无待添加商品")
        return
    
    for idx, item in enumerate(pending):
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{item['model_name']}**")
            with col2:
                if st.button("🗑️", key=f"del_pending_{idx}"):
                    st.session_state.pending_items.pop(idx)
                    st.rerun()
            
            # 参数配置
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                item["region"] = st.selectbox(
                    "地域",
                    options=["cn-beijing", "cn-hangzhou"],
                    format_func=lambda x: "北京" if x == "cn-beijing" else "杭州",
                    key=f"region_{idx}"
                )
            with col2:
                item["input_tokens"] = st.number_input(
                    "输入Tokens",
                    value=item["input_tokens"],
                    step=10000,
                    min_value=0,
                    key=f"input_{idx}"
                )
            with col3:
                item["output_tokens"] = st.number_input(
                    "输出Tokens",
                    value=item["output_tokens"],
                    step=10000,
                    min_value=0,
                    key=f"output_{idx}"
                )
            with col4:
                item["inference_mode"] = st.selectbox(
                    "推理方式",
                    options=[None, "thinking", "non_thinking"],
                    format_func=lambda x: "默认" if x is None else ("思考模式" if x == "thinking" else "非思考"),
                    key=f"mode_{idx}"
                )
            with col5:
                item["duration_months"] = st.number_input(
                    "时长(月)",
                    value=item["duration_months"],
                    min_value=1,
                    max_value=36,
                    key=f"duration_{idx}"
                )
            
            # 预估价格
            pricing = item.get("pricing", {})
            input_p = float(pricing.get("input_price", 0) or 0)
            output_p = float(pricing.get("output_price", 0) or 0)
            est_price = (input_p * item["input_tokens"] + output_p * item["output_tokens"]) / 1000 * item["duration_months"]
            st.caption(f"预估原价: ¥{est_price:,.2f}")
    
    # 批量添加到报价单
    st.divider()
    if st.button("📥 将所有待添加商品加入报价单", type="primary", use_container_width=True):
        add_pending_to_quote(quote)


def add_pending_to_quote(quote: Dict):
    """将待添加商品批量添加到报价单"""
    quote_id = quote.get("quote_id")
    pending = st.session_state.pending_items
    
    success = 0
    for item in pending:
        result = api("POST", f"/quotes/{quote_id}/items", json_data={
            "product_code": item["model_id"],
            "region": item["region"],
            "quantity": item.get("quantity", 1),
            "input_tokens": item["input_tokens"],
            "output_tokens": item["output_tokens"],
            "inference_mode": item["inference_mode"],
            "duration_months": item["duration_months"]
        })
        if result:
            success += 1
    
    # 刷新报价单
    st.session_state.pending_items = []
    updated = api("GET", f"/quotes/{quote_id}")
    if updated:
        st.session_state.current_quote = updated
    
    st.success(f"成功添加 {success}/{len(pending)} 个商品")
    st.rerun()


def render_existing_items(quote: Dict, items: List[Dict]):
    """渲染已添加到报价单的商品"""
    if not items:
        st.info("报价单暂无商品")
        return
    
    quote_id = quote.get("quote_id")
    is_draft = quote.get("status") == "draft"
    
    for item in items:
        with st.container(border=True):
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 2, 1])
            
            with col1:
                st.markdown(f"**{item.get('product_name', 'N/A')}**")
                st.caption(f"ID: {item.get('product_code', '')}")
            
            with col2:
                st.caption(f"地域: {item.get('region_name', item.get('region', ''))}")
                st.caption(f"模态: {item.get('modality', 'N/A')}")
            
            with col3:
                st.caption(f"输入: {item.get('input_tokens', 0):,} tokens")
                st.caption(f"输出: {item.get('output_tokens', 0):,} tokens")
            
            with col4:
                original = float(item.get('original_price', 0))
                final = float(item.get('final_price', 0))
                discount = float(item.get('discount_rate', 1))
                st.metric("原价", f"¥{original:,.2f}")
                if discount < 1:
                    st.caption(f"折后: ¥{final:,.2f} ({discount*100:.0f}%)")
            
            with col5:
                if is_draft:
                    if st.button("🗑️", key=f"del_item_{item.get('item_id')}"):
                        api("DELETE", f"/quotes/{quote_id}/items/{item.get('item_id')}")
                        updated = api("GET", f"/quotes/{quote_id}")
                        if updated:
                            st.session_state.current_quote = updated
                        st.rerun()


def render_global_discount(quote: Dict):
    """全局折扣设置"""
    st.subheader("💰 批量折扣设置")
    
    if quote.get("status") != "draft":
        st.warning("已确认的报价单不可修改折扣")
        st.metric("当前折扣率", f"{float(quote.get('global_discount_rate', 1)) * 100:.0f}%")
        return
    
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        current_rate = float(quote.get("global_discount_rate", 1))
        discount_percent = st.slider(
            "折扣率",
            min_value=50,
            max_value=100,
            value=int(current_rate * 100),
            step=5,
            format="%d%%",
            help="100% = 原价，90% = 9折"
        )
    
    with col2:
        remark = st.text_input(
            "折扣备注",
            value=quote.get("global_discount_remark", ""),
            placeholder="如：战略客户专属折扣"
        )
    
    with col3:
        st.write("")
        st.write("")
        if st.button("应用折扣", type="primary"):
            result = api("POST", f"/quotes/{quote.get('quote_id')}/discount", json_data={
                "discount_rate": discount_percent / 100,
                "remark": remark
            })
            if result:
                st.session_state.current_quote = result
                st.success("折扣已应用")
                st.rerun()
    
    # 显示折扣后总金额
    items = quote.get("items", [])
    total_original = sum(float(i.get("original_price", 0)) for i in items)
    total_final = total_original * discount_percent / 100
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("原价合计", f"¥{total_original:,.2f}")
    with col2:
        st.metric("折后合计", f"¥{total_final:,.2f}")
    with col3:
        savings = total_original - total_final
        st.metric("节省", f"¥{savings:,.2f}")


def render_preview(quote: Dict):
    """预览与导出"""
    st.subheader("📄 报价单预览")
    
    quote_id = quote.get("quote_id")
    
    # 报价单汇总
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("报价单号", quote.get("quote_no", "N/A"))
        with col2:
            st.metric("客户", quote.get("customer_name", "未填写"))
        with col3:
            st.metric("商品数", len(quote.get("items", [])))
        with col4:
            st.metric("总金额", f"¥{float(quote.get('total_final_amount', 0)):,.2f}")
    
    # 商品明细表
    st.markdown("**📊 报价明细表**")
    items = quote.get("items", [])
    if items:
        # 表头
        cols = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1.5])
        headers = ["模型名称", "地域", "模态", "原价", "折扣", "折后价"]
        for col, header in zip(cols, headers):
            col.markdown(f"**{header}**")
        
        # 数据行
        for item in items:
            cols = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1.5])
            cols[0].write(item.get("product_name", "")[:25])
            cols[1].write(item.get("region_name", item.get("region", "")))
            cols[2].write(item.get("modality", ""))
            cols[3].write(f"¥{float(item.get('original_price', 0)):,.2f}")
            cols[4].write(f"{float(item.get('discount_rate', 1))*100:.0f}%")
            cols[5].write(f"¥{float(item.get('final_price', 0)):,.2f}")
        
        # 合计
        st.divider()
        total_original = sum(float(i.get("original_price", 0)) for i in items)
        total_final = sum(float(i.get("final_price", 0)) for i in items)
        cols = st.columns([3, 1.5, 1.5, 1.5, 1.5, 1.5])
        cols[0].markdown("**合计**")
        cols[3].markdown(f"**¥{total_original:,.2f}**")
        cols[5].markdown(f"**¥{total_final:,.2f}**")
    else:
        st.info("暂无商品")
    
    # 操作按钮
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if quote.get("status") == "draft":
            if st.button("✅ 确认报价单", type="primary", use_container_width=True):
                result = api("POST", f"/quotes/{quote_id}/confirm")
                if result:
                    st.session_state.current_quote = result
                    st.success("报价单已确认！")
                    st.balloons()
                    st.rerun()
    
    with col2:
        if st.button("📋 复制报价单", use_container_width=True):
            result = api("POST", f"/quotes/{quote_id}/clone")
            if result:
                st.session_state.current_quote = result
                st.success(f"已复制为新报价单: {result.get('quote_no')}")
                st.rerun()
    
    with col3:
        if st.button("📤 导出预览", use_container_width=True):
            preview = api("GET", f"/export/preview/{quote_id}")
            if preview:
                with st.expander("导出数据预览", expanded=True):
                    st.json(preview)
    
    with col4:
        if st.button("📜 版本历史", use_container_width=True):
            versions = api("GET", f"/quotes/{quote_id}/versions")
            if versions:
                with st.expander("版本历史", expanded=True):
                    for v in versions:
                        st.write(f"v{v.get('version_number')} - {v.get('change_type')} - {v.get('changes_summary')}")


# ==================== 主应用 ====================
def main():
    st.set_page_config(
        page_title="智价引擎 - E2E测试",
        page_icon="💰",
        layout="wide"
    )
    
    init_state()
    
    # 侧边栏 - 系统信息
    with st.sidebar:
        st.title("💰 智价引擎")
        st.caption("SmartPrice Engine E2E Test")
        st.divider()
        
        # 快捷操作
        if st.button("🏠 返回首页", use_container_width=True):
            st.session_state.page = "list"
            st.rerun()
        
        if st.button("➕ 新建报价单", use_container_width=True):
            create_new_quote()
        
        st.divider()
        
        # 当前状态
        st.caption("当前状态")
        st.write(f"页面: {st.session_state.page}")
        if st.session_state.current_quote:
            st.write(f"报价单: {st.session_state.current_quote.get('quote_no', 'N/A')}")
        st.write(f"待添加: {len(st.session_state.pending_items)} 项")
    
    # 主内容区
    if st.session_state.page == "list":
        page_quote_list()
    elif st.session_state.page == "workspace":
        page_workspace()


if __name__ == "__main__":
    main()
