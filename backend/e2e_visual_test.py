"""
E2E Visual Test - Interactive Testing Tool for Quotation System
A single-file Streamlit application for visual end-to-end testing.

Usage:
    cd backend
    streamlit run e2e_visual_test.py --server.port 8501
"""
import streamlit as st
import httpx
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal
from dataclasses import dataclass, field


# ==================== Configuration ====================
@dataclass
class TestConfig:
    """Test configuration"""
    api_base_url: str = "http://localhost:8000"
    timeout: int = 30
    
    @property
    def api_v1_url(self) -> str:
        return f"{self.api_base_url}/api/v1"


@dataclass 
class TestResult:
    """Single test result"""
    name: str
    success: bool
    status_code: int = 0
    response_time: float = 0.0
    response_data: Any = None
    error_message: str = ""


@dataclass
class TestSummary:
    """Test summary"""
    results: List[TestResult] = field(default_factory=list)
    
    @property
    def total(self) -> int:
        return len(self.results)
    
    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.success)
    
    @property
    def failed(self) -> int:
        return self.total - self.passed


# ==================== HTTP Client ====================
class TestClient:
    """Sync HTTP test client"""
    
    def __init__(self, config: TestConfig):
        self.config = config
    
    def request(
        self, 
        method: str, 
        path: str, 
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        use_api_prefix: bool = True
    ) -> TestResult:
        """Execute HTTP request and return result"""
        if use_api_prefix and path.startswith("/"):
            url = f"{self.config.api_v1_url}{path}"
        else:
            url = f"{self.config.api_base_url}{path}"
        
        start_time = time.time()
        try:
            # Disable proxy for localhost connections
            with httpx.Client(
                timeout=self.config.timeout,
                proxy=None,
                trust_env=False
            ) as client:
                response = client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data
                )
                response_time = time.time() - start_time
                
                try:
                    data = response.json()
                except:
                    data = response.text
                
                return TestResult(
                    name=f"{method} {path}",
                    success=response.status_code < 400,
                    status_code=response.status_code,
                    response_time=response_time,
                    response_data=data
                )
        except Exception as e:
            return TestResult(
                name=f"{method} {path}",
                success=False,
                response_time=time.time() - start_time,
                error_message=f"{type(e).__name__}: {e}"
            )


# ==================== Test Scenarios ====================
class TestScenarios:
    """Test scenario implementations"""
    
    def __init__(self, client: TestClient):
        self.client = client
    
    def health_check(self) -> TestResult:
        """Health check test"""
        return self.client.request("GET", "/health", use_api_prefix=False)
    
    def get_filter_options(self) -> TestResult:
        """Get product filter options"""
        return self.client.request("GET", "/products/filters")
    
    def get_models(
        self, 
        vendor: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> TestResult:
        """Query product models"""
        params = {"page": page, "page_size": page_size}
        if vendor:
            params["vendor"] = vendor
        if keyword:
            params["keyword"] = keyword
        return self.client.request("GET", "/products/models", params=params)
    
    def get_model_detail(self, model_id: str) -> TestResult:
        """Get model detail"""
        return self.client.request("GET", f"/products/models/{model_id}")
    
    def search_products(self, names: List[str], region: str = "cn-beijing") -> TestResult:
        """Batch search products"""
        return self.client.request(
            "POST", 
            "/products/search",
            json_data={"names": names, "region": region}
        )
    
    def create_quote(
        self,
        customer_name: str,
        project_name: str,
        created_by: str = "e2e_test"
    ) -> TestResult:
        """Create quote"""
        return self.client.request(
            "POST",
            "/quotes/",
            json_data={
                "customer_name": customer_name,
                "project_name": project_name,
                "created_by": created_by,
                "currency": "CNY"
            }
        )
    
    def get_quote(self, quote_id: str) -> TestResult:
        """Get quote detail"""
        return self.client.request("GET", f"/quotes/{quote_id}")
    
    def get_quotes(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> TestResult:
        """List quotes"""
        params = {"page": page, "page_size": page_size}
        if status:
            params["status"] = status
        return self.client.request("GET", "/quotes/", params=params)
    
    def add_quote_item(
        self,
        quote_id: str,
        product_code: str,
        quantity: int = 1,
        duration_months: int = 12,
        input_tokens: int = 100000,
        output_tokens: int = 50000
    ) -> TestResult:
        """Add item to quote"""
        return self.client.request(
            "POST",
            f"/quotes/{quote_id}/items",
            json_data={
                "product_code": product_code,
                "region": "cn-beijing",
                "quantity": quantity,
                "duration_months": duration_months,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        )
    
    def apply_discount(
        self,
        quote_id: str,
        discount_rate: float,
        remark: str = ""
    ) -> TestResult:
        """Apply discount to quote"""
        return self.client.request(
            "POST",
            f"/quotes/{quote_id}/discount",
            json_data={"discount_rate": discount_rate, "remark": remark}
        )
    
    def confirm_quote(self, quote_id: str) -> TestResult:
        """Confirm quote"""
        return self.client.request("POST", f"/quotes/{quote_id}/confirm")
    
    def get_quote_versions(self, quote_id: str) -> TestResult:
        """Get quote versions"""
        return self.client.request("GET", f"/quotes/{quote_id}/versions")
    
    def ai_chat(self, message: str, session_id: str = "test_session") -> TestResult:
        """AI chat"""
        return self.client.request(
            "POST",
            "/ai/chat",
            json_data={"message": message, "session_id": session_id}
        )
    
    def parse_requirement(self, requirement_text: str) -> TestResult:
        """Parse requirement text"""
        return self.client.request(
            "POST",
            "/ai/parse-requirement",
            params={"requirement_text": requirement_text}
        )
    
    def get_export_templates(self) -> TestResult:
        """Get export templates"""
        return self.client.request("GET", "/export/templates")
    
    def preview_export(self, quote_id: str) -> TestResult:
        """Preview export data"""
        return self.client.request("GET", f"/export/preview/{quote_id}")


# ==================== Pricing Engine Test ====================
def test_pricing_calculation(
    input_tokens: int,
    output_tokens: int,
    input_price: float,
    output_price: float,
    thinking_mode_ratio: float = 0.0,
    thinking_multiplier: float = 1.5,
    batch_ratio: float = 0.0
) -> Dict[str, Any]:
    """Test pricing calculation locally"""
    # Base token cost
    input_cost = Decimal(str(input_price)) * Decimal(str(input_tokens))
    output_cost = Decimal(str(output_price)) * Decimal(str(output_tokens))
    base_price = (input_cost + output_cost) / Decimal("1000")
    
    breakdown = {
        "input_cost": f"{input_tokens} tokens × ¥{input_price}/千token = ¥{float(input_cost/1000):.4f}",
        "output_cost": f"{output_tokens} tokens × ¥{output_price}/千token = ¥{float(output_cost/1000):.4f}",
        "base_price": float(base_price)
    }
    
    final_price = base_price
    
    # Thinking mode
    if thinking_mode_ratio > 0:
        thinking_cost = base_price * Decimal(str(thinking_multiplier - 1)) * Decimal(str(thinking_mode_ratio))
        final_price += thinking_cost
        breakdown["thinking_mode"] = f"Extra: ¥{float(thinking_cost):.4f} ({thinking_mode_ratio*100}% @ {thinking_multiplier}x)"
    
    # Batch discount
    if batch_ratio > 0:
        batch_discount = final_price * Decimal(str(batch_ratio)) * Decimal("0.5")
        saved = final_price * Decimal(str(batch_ratio)) - batch_discount
        final_price -= saved
        breakdown["batch_discount"] = f"Saved: ¥{float(saved):.4f} ({batch_ratio*100}% batch calls)"
    
    breakdown["final_price"] = float(final_price)
    
    return {
        "success": True,
        "final_price": float(final_price),
        "calculation_breakdown": breakdown
    }


# ==================== Streamlit UI ====================
def init_session_state():
    """Initialize session state"""
    if "test_summary" not in st.session_state:
        st.session_state.test_summary = TestSummary()
    if "last_quote_id" not in st.session_state:
        st.session_state.last_quote_id = ""


def display_result(result: TestResult):
    """Display single test result"""
    if result.success:
        st.success(f"✅ {result.name} - {result.status_code} ({result.response_time:.3f}s)")
    else:
        st.error(f"❌ {result.name} - {result.status_code or 'ERROR'} ({result.response_time:.3f}s)")
        if result.error_message:
            st.error(f"Error: {result.error_message}")
    
    # Response data
    if result.response_data:
        with st.expander("View Response", expanded=False):
            st.json(result.response_data)


def display_summary():
    """Display test summary panel"""
    summary = st.session_state.test_summary
    if summary.total > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total", summary.total)
        with col2:
            st.metric("Passed", summary.passed, delta=None)
        with col3:
            st.metric("Failed", summary.failed, delta=None if summary.failed == 0 else f"-{summary.failed}")
        
        # Progress bar
        if summary.total > 0:
            progress = summary.passed / summary.total
            st.progress(progress)


def run_async(coro):
    """Legacy function - no longer needed with sync client"""
    # Kept for compatibility, but now methods are synchronous
    return coro


def main():
    """Main Streamlit app"""
    st.set_page_config(
        page_title="E2E Visual Test - Quotation System",
        page_icon="📊",
        layout="wide"
    )
    
    init_session_state()
    
    # Header
    st.title("📊 Quotation System E2E Visual Test")
    st.markdown("---")
    
    # Sidebar - Configuration
    with st.sidebar:
        st.header("🔧 Configuration")
        api_url = st.text_input("API Base URL", value="http://localhost:8000")
        timeout = st.slider("Timeout (seconds)", 5, 60, 30)
        
        config = TestConfig(api_base_url=api_url, timeout=timeout)
        client = TestClient(config)
        scenarios = TestScenarios(client)
        
        st.markdown("---")
        
        # Test scenario selection
        st.header("📋 Test Scenarios")
        test_scenario = st.radio(
            "Select Scenario",
            [
                "🩺 Health Check",
                "📦 Product Query",
                "📝 Quote Lifecycle",
                "💰 Price Calculation",
                "🤖 AI Chat",
                "📤 Export Preview",
                "🚀 Run All Tests"
            ],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Summary panel
        st.header("📈 Test Summary")
        display_summary()
        
        if st.button("Clear Results"):
            st.session_state.test_summary = TestSummary()
            st.rerun()
    
    # Main content area
    if test_scenario == "🩺 Health Check":
        render_health_check(scenarios)
    elif test_scenario == "📦 Product Query":
        render_product_query(scenarios)
    elif test_scenario == "📝 Quote Lifecycle":
        render_quote_lifecycle(scenarios)
    elif test_scenario == "💰 Price Calculation":
        render_price_calculation()
    elif test_scenario == "🤖 AI Chat":
        render_ai_chat(scenarios)
    elif test_scenario == "📤 Export Preview":
        render_export_preview(scenarios)
    elif test_scenario == "🚀 Run All Tests":
        render_run_all_tests(scenarios)


def render_health_check(scenarios: TestScenarios):
    """Render health check scenario"""
    st.header("🩺 Health Check")
    st.markdown("Verify that the backend service is running and healthy.")
    
    if st.button("Run Health Check", type="primary"):
        with st.spinner("Checking health..."):
            result = run_async(scenarios.health_check())
            st.session_state.test_summary.results.append(result)
            display_result(result)
            
            if result.success and isinstance(result.response_data, dict):
                status = result.response_data.get("status", "unknown")
                if status == "healthy":
                    st.balloons()


def render_product_query(scenarios: TestScenarios):
    """Render product query scenario"""
    st.header("📦 Product Query")
    st.markdown("Test product listing, filtering, and search capabilities.")
    
    tab1, tab2, tab3 = st.tabs(["Filter Options", "Model List", "Model Detail"])
    
    with tab1:
        st.subheader("Get Filter Options")
        if st.button("Get Filters", key="get_filters"):
            with st.spinner("Loading filters..."):
                result = run_async(scenarios.get_filter_options())
                st.session_state.test_summary.results.append(result)
                display_result(result)
    
    with tab2:
        st.subheader("Query Models")
        col1, col2 = st.columns(2)
        with col1:
            vendor = st.selectbox("Vendor", ["", "aliyun", "volcano"], key="model_vendor")
            page = st.number_input("Page", min_value=1, value=1, key="model_page")
        with col2:
            keyword = st.text_input("Keyword", key="model_keyword")
            page_size = st.number_input("Page Size", min_value=1, max_value=100, value=10, key="model_page_size")
        
        if st.button("Search Models", key="search_models"):
            with st.spinner("Searching..."):
                result = run_async(scenarios.get_models(
                    vendor=vendor if vendor else None,
                    keyword=keyword if keyword else None,
                    page=page,
                    page_size=page_size
                ))
                st.session_state.test_summary.results.append(result)
                display_result(result)
                
                # Display models in table if available
                if result.success and isinstance(result.response_data, dict):
                    items = result.response_data.get("items", [])
                    if items:
                        st.dataframe(items, use_container_width=True)
    
    with tab3:
        st.subheader("Get Model Detail")
        model_id = st.text_input("Model ID (product_code)", key="model_id")
        
        if st.button("Get Detail", key="get_model_detail"):
            if not model_id:
                st.warning("Please enter a Model ID")
            else:
                with st.spinner("Loading..."):
                    result = run_async(scenarios.get_model_detail(model_id))
                    st.session_state.test_summary.results.append(result)
                    display_result(result)


def render_quote_lifecycle(scenarios: TestScenarios):
    """Render quote lifecycle scenario"""
    st.header("📝 Quote Lifecycle")
    st.markdown("Test the complete quote lifecycle: create → add items → apply discount → confirm.")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Create Quote", "List Quotes", "Quote Detail", "Full Lifecycle"])
    
    with tab1:
        st.subheader("Create New Quote")
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input("Customer Name", value="Test Enterprise", key="create_customer")
        with col2:
            project_name = st.text_input("Project Name", value="AI Upgrade Project", key="create_project")
        
        if st.button("Create Quote", key="create_quote", type="primary"):
            with st.spinner("Creating..."):
                result = run_async(scenarios.create_quote(customer_name, project_name))
                st.session_state.test_summary.results.append(result)
                display_result(result)
                
                if result.success and isinstance(result.response_data, dict):
                    quote_id = result.response_data.get("quote_id", "")
                    if quote_id:
                        st.session_state.last_quote_id = quote_id
                        st.info(f"Quote ID saved: {quote_id}")
    
    with tab2:
        st.subheader("List Quotes")
        col1, col2 = st.columns(2)
        with col1:
            status = st.selectbox("Status", ["", "draft", "confirmed", "expired"], key="list_status")
        with col2:
            list_page_size = st.number_input("Page Size", min_value=1, max_value=50, value=10, key="list_page_size")
        
        if st.button("List Quotes", key="list_quotes"):
            with st.spinner("Loading..."):
                result = run_async(scenarios.get_quotes(
                    status=status if status else None,
                    page_size=list_page_size
                ))
                st.session_state.test_summary.results.append(result)
                display_result(result)
    
    with tab3:
        st.subheader("Get Quote Detail")
        quote_id = st.text_input(
            "Quote ID",
            value=st.session_state.last_quote_id,
            key="detail_quote_id"
        )
        
        if st.button("Get Detail", key="get_quote_detail"):
            if not quote_id:
                st.warning("Please enter a Quote ID")
            else:
                with st.spinner("Loading..."):
                    result = run_async(scenarios.get_quote(quote_id))
                    st.session_state.test_summary.results.append(result)
                    display_result(result)
    
    with tab4:
        st.subheader("Full Lifecycle Test")
        st.markdown("""
        This will execute the complete quote lifecycle:
        1. Create a new quote
        2. Add an item to the quote
        3. Apply discount
        4. Confirm the quote
        5. Get version history
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            lc_customer = st.text_input("Customer Name", value="Lifecycle Test Corp", key="lc_customer")
            lc_product = st.text_input("Product Code", value="qwen-plus", key="lc_product")
        with col2:
            lc_project = st.text_input("Project Name", value="Full Lifecycle Test", key="lc_project")
            lc_discount = st.slider("Discount Rate", 0.5, 1.0, 0.9, 0.05, key="lc_discount")
        
        if st.button("Run Full Lifecycle", key="run_lifecycle", type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            steps = []
            
            # Step 1: Create quote
            status_text.text("Step 1/5: Creating quote...")
            result = run_async(scenarios.create_quote(lc_customer, lc_project))
            steps.append(("Create Quote", result))
            progress_bar.progress(20)
            
            if result.success and isinstance(result.response_data, dict):
                quote_id = result.response_data.get("quote_id", "")
                st.session_state.last_quote_id = quote_id
                
                # Step 2: Add item
                status_text.text("Step 2/5: Adding item...")
                result = run_async(scenarios.add_quote_item(quote_id, lc_product))
                steps.append(("Add Item", result))
                progress_bar.progress(40)
                
                if result.success:
                    # Step 3: Apply discount
                    status_text.text("Step 3/5: Applying discount...")
                    result = run_async(scenarios.apply_discount(quote_id, lc_discount, "Lifecycle test discount"))
                    steps.append(("Apply Discount", result))
                    progress_bar.progress(60)
                    
                    # Step 4: Confirm
                    status_text.text("Step 4/5: Confirming quote...")
                    result = run_async(scenarios.confirm_quote(quote_id))
                    steps.append(("Confirm Quote", result))
                    progress_bar.progress(80)
                    
                    # Step 5: Get versions
                    status_text.text("Step 5/5: Getting version history...")
                    result = run_async(scenarios.get_quote_versions(quote_id))
                    steps.append(("Get Versions", result))
                    progress_bar.progress(100)
            
            status_text.text("Lifecycle test complete!")
            
            # Display results
            st.markdown("### Results")
            for step_name, result in steps:
                result.name = step_name
                st.session_state.test_summary.results.append(result)
                display_result(result)


def render_price_calculation():
    """Render price calculation scenario"""
    st.header("💰 Price Calculation")
    st.markdown("Test the pricing engine with different parameters.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Token Parameters")
        input_tokens = st.number_input("Input Tokens", min_value=0, value=100000, step=10000)
        output_tokens = st.number_input("Output Tokens", min_value=0, value=50000, step=10000)
        input_price = st.number_input("Input Price (¥/千tokens)", min_value=0.0, value=0.04, step=0.01, format="%.4f")
        output_price = st.number_input("Output Price (¥/千tokens)", min_value=0.0, value=0.12, step=0.01, format="%.4f")
    
    with col2:
        st.subheader("Additional Options")
        thinking_mode = st.checkbox("Enable Thinking Mode")
        thinking_ratio = st.slider("Thinking Mode Ratio", 0.0, 1.0, 0.5, 0.1, disabled=not thinking_mode)
        thinking_multiplier = st.number_input("Thinking Multiplier", min_value=1.0, value=1.5, step=0.1, disabled=not thinking_mode)
        
        batch_mode = st.checkbox("Enable Batch Calls")
        batch_ratio = st.slider("Batch Call Ratio", 0.0, 1.0, 0.8, 0.1, disabled=not batch_mode)
    
    if st.button("Calculate Price", type="primary"):
        result = test_pricing_calculation(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_price=input_price,
            output_price=output_price,
            thinking_mode_ratio=thinking_ratio if thinking_mode else 0.0,
            thinking_multiplier=thinking_multiplier if thinking_mode else 1.5,
            batch_ratio=batch_ratio if batch_mode else 0.0
        )
        
        st.success(f"✅ Calculation Complete")
        
        # Display breakdown
        st.subheader("Calculation Breakdown")
        breakdown = result.get("calculation_breakdown", {})
        
        col1, col2 = st.columns([2, 1])
        with col1:
            for key, value in breakdown.items():
                if key != "final_price" and key != "base_price":
                    st.text(f"• {key}: {value}")
        
        with col2:
            st.metric("Base Price", f"¥{breakdown.get('base_price', 0):.4f}")
            st.metric("Final Price", f"¥{result.get('final_price', 0):.4f}")
        
        # Add to summary
        test_result = TestResult(
            name="Price Calculation",
            success=True,
            response_data=result
        )
        st.session_state.test_summary.results.append(test_result)


def render_ai_chat(scenarios: TestScenarios):
    """Render AI chat scenario"""
    st.header("🤖 AI Chat")
    st.markdown("Test AI chat and requirement parsing features.")
    
    tab1, tab2 = st.tabs(["Chat", "Parse Requirement"])
    
    with tab1:
        st.subheader("AI Chat")
        message = st.text_area(
            "Message",
            value="I need a large language model product for text generation",
            height=100,
            key="chat_message"
        )
        session_id = st.text_input("Session ID", value="test_session_001", key="chat_session")
        
        if st.button("Send Message", key="send_chat"):
            with st.spinner("Waiting for AI response..."):
                result = run_async(scenarios.ai_chat(message, session_id))
                st.session_state.test_summary.results.append(result)
                display_result(result)
    
    with tab2:
        st.subheader("Parse Requirement")
        requirement = st.text_area(
            "Requirement Text",
            value="I need qwen-max model, estimated 1 million tokens per month, with thinking mode enabled",
            height=100,
            key="parse_requirement"
        )
        
        if st.button("Parse", key="parse_req"):
            with st.spinner("Parsing requirement..."):
                result = run_async(scenarios.parse_requirement(requirement))
                st.session_state.test_summary.results.append(result)
                display_result(result)


def render_export_preview(scenarios: TestScenarios):
    """Render export preview scenario"""
    st.header("📤 Export Preview")
    st.markdown("Test export templates and preview functionality.")
    
    tab1, tab2 = st.tabs(["Templates", "Preview"])
    
    with tab1:
        st.subheader("Available Templates")
        if st.button("Get Templates", key="get_templates"):
            with st.spinner("Loading templates..."):
                result = run_async(scenarios.get_export_templates())
                st.session_state.test_summary.results.append(result)
                display_result(result)
                
                if result.success and isinstance(result.response_data, list):
                    for template in result.response_data:
                        with st.container():
                            st.markdown(f"**{template.get('name', 'Unknown')}** (`{template.get('id', '')}`)")
                            st.caption(template.get('description', ''))
    
    with tab2:
        st.subheader("Preview Quote Data")
        quote_id = st.text_input(
            "Quote ID",
            value=st.session_state.last_quote_id,
            key="preview_quote_id"
        )
        
        if st.button("Preview", key="preview_export"):
            if not quote_id:
                st.warning("Please enter a Quote ID")
            else:
                with st.spinner("Loading preview..."):
                    result = run_async(scenarios.preview_export(quote_id))
                    st.session_state.test_summary.results.append(result)
                    display_result(result)
                    
                    if result.success and isinstance(result.response_data, dict):
                        # Display structured preview
                        data = result.response_data
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Quote Info**")
                            quote_info = data.get("quote", {})
                            st.text(f"Quote No: {quote_info.get('quote_no', 'N/A')}")
                            st.text(f"Customer: {quote_info.get('customer_name', 'N/A')}")
                            st.text(f"Status: {quote_info.get('status', 'N/A')}")
                        
                        with col2:
                            st.markdown("**Summary**")
                            summary = data.get("summary", {})
                            st.metric("Items", summary.get("item_count", 0))
                            st.metric("Total", f"¥{summary.get('total_final', 0):.2f}")
                        
                        # Items table
                        items = data.get("items", [])
                        if items:
                            st.markdown("**Items**")
                            st.dataframe(items, use_container_width=True)


def render_run_all_tests(scenarios: TestScenarios):
    """Render run all tests scenario"""
    st.header("🚀 Run All Tests")
    st.markdown("Execute all test scenarios in sequence and get a comprehensive report.")
    
    st.warning("⚠️ This will run multiple API calls. Make sure the backend is running.")
    
    if st.button("Run All Tests", type="primary"):
        # Clear previous results
        st.session_state.test_summary = TestSummary()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        results_container = st.container()
        
        tests = [
            ("Health Check", lambda: scenarios.health_check()),
            ("Get Filter Options", lambda: scenarios.get_filter_options()),
            ("List Models", lambda: scenarios.get_models(page_size=5)),
            ("List Quotes", lambda: scenarios.get_quotes(page_size=5)),
            ("Get Export Templates", lambda: scenarios.get_export_templates()),
            ("AI Chat", lambda: scenarios.ai_chat("Hello, I need a model")),
        ]
        
        total = len(tests)
        
        with results_container:
            for i, (test_name, test_func) in enumerate(tests):
                status_text.text(f"Running: {test_name}...")
                
                result = run_async(test_func())
                result.name = test_name
                st.session_state.test_summary.results.append(result)
                
                display_result(result)
                
                progress_bar.progress((i + 1) / total)
        
        status_text.text("All tests completed!")
        
        # Final summary
        st.markdown("---")
        st.subheader("Final Summary")
        summary = st.session_state.test_summary
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tests", summary.total)
        with col2:
            st.metric("Passed", summary.passed)
        with col3:
            st.metric("Failed", summary.failed)
        with col4:
            pass_rate = (summary.passed / summary.total * 100) if summary.total > 0 else 0
            st.metric("Pass Rate", f"{pass_rate:.1f}%")
        
        if summary.failed == 0:
            st.success("🎉 All tests passed!")
            st.balloons()
        else:
            st.error(f"❌ {summary.failed} test(s) failed. Please check the results above.")


if __name__ == "__main__":
    main()
