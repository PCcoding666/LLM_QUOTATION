#!/bin/bash
# 报价侠系统 - 一键启动脚本
# 用法: ./start.sh [dev|prod|test]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Python版本
check_python() {
    print_info "检查Python版本..."
    if ! command -v python3 &> /dev/null; then
        print_error "未找到Python3，请先安装Python 3.10+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    print_success "Python版本: $PYTHON_VERSION"
}

# 创建/激活虚拟环境
setup_venv() {
    print_info "设置虚拟环境..."
    
    if [ ! -d "venv" ]; then
        print_info "创建虚拟环境..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    print_success "虚拟环境已激活"
}

# 安装依赖
install_deps() {
    print_info "安装依赖包..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    print_success "依赖安装完成"
}

# 检查环境变量
check_env() {
    print_info "检查环境配置..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            print_warning ".env文件不存在，从示例文件创建..."
            cp .env.example .env
            print_warning "请编辑 .env 文件配置数据库和其他服务"
        else
            print_error ".env和.env.example都不存在"
            exit 1
        fi
    fi
    
    print_success "环境配置已就绪"
}

# 检查数据库连接
check_database() {
    print_info "检查数据库连接..."
    
    if python3 -c "from app.core.database import check_connection; import asyncio; asyncio.run(check_connection())" 2>/dev/null; then
        print_success "数据库连接正常"
    else
        print_warning "数据库连接失败，请检查配置"
    fi
}

# 运行数据库迁移
run_migrations() {
    print_info "运行数据库迁移..."
    
    if [ -d "alembic/versions" ] && [ "$(ls -A alembic/versions)" ]; then
        alembic upgrade head 2>/dev/null && print_success "数据库迁移完成" || print_warning "迁移跳过(可能已是最新)"
    else
        print_warning "无迁移文件"
    fi
}

# 运行测试
run_tests() {
    print_info "运行测试套件..."
    
    pytest tests/ -v --tb=short 2>&1 | tail -20
    
    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        print_success "所有测试通过"
    else
        print_warning "部分测试失败，请检查"
    fi
}

# 开发模式启动
start_dev() {
    print_info "以开发模式启动服务..."
    echo ""
    echo "======================================"
    echo "  报价侠系统 - 开发模式"
    echo "  API文档: http://localhost:8000/api/docs"
    echo "  健康检查: http://localhost:8000/health"
    echo "  按 Ctrl+C 停止服务"
    echo "======================================"
    echo ""
    
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
}

# 生产模式启动
start_prod() {
    print_info "以生产模式启动服务..."
    echo ""
    echo "======================================"
    echo "  报价侠系统 - 生产模式"
    echo "  Workers: 4"
    echo "  端口: 8000"
    echo "======================================"
    echo ""
    
    gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
}

# 仅测试模式
test_only() {
    print_info "仅运行测试..."
    setup_venv
    check_env
    run_tests
}

# 健康检查
health_check() {
    print_info "执行健康检查..."
    
    # 检查服务是否运行
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        print_success "服务运行正常"
    else
        print_error "服务未运行或不健康"
    fi
}

# 主函数
main() {
    echo ""
    echo "============================================"
    echo "    报价侠系统 - 一键启动脚本"
    echo "============================================"
    echo ""
    
    MODE=${1:-dev}
    
    case $MODE in
        dev)
            check_python
            setup_venv
            install_deps
            check_env
            run_migrations
            start_dev
            ;;
        prod)
            check_python
            setup_venv
            install_deps
            check_env
            run_migrations
            start_prod
            ;;
        test)
            check_python
            test_only
            ;;
        check)
            health_check
            ;;
        *)
            echo "用法: $0 [dev|prod|test|check]"
            echo ""
            echo "  dev   - 开发模式启动（热重载）"
            echo "  prod  - 生产模式启动（多worker）"
            echo "  test  - 仅运行测试"
            echo "  check - 健康检查"
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
