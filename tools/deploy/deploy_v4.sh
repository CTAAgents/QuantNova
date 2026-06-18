#!/bin/bash
# =============================================================================
# Trend-Scanner-Agent v4.0 部署脚本
# =============================================================================
# 用途: 自动化部署、验证和测试 Trend-Scanner-Agent 系统
# 作者: Trend-Scanner Team
# 日期: 2026-06-15
# =============================================================================

set -e  # 遇到错误立即退出

# =============================================================================
# 颜色定义
# =============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # 无颜色

# =============================================================================
# 全局变量
# =============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$PROJECT_ROOT/logs/deploy_${TIMESTAMP}.log"

# Python 路径 (Windows Git Bash 兼容)
PYTHON_PATH="/c/Program Files/Python312/python.exe"

# 标志变量
DRY_RUN=false
SKIP_TESTS=false
DEPLOY_SUCCESS=true

# =============================================================================
# 辅助函数
# =============================================================================

# 打印带颜色的消息
print_success() {
    echo -e "${GREEN}[✓] $1${NC}"
}

print_error() {
    echo -e "${RED}[✗] $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}[!] $1${NC}"
}

print_info() {
    echo -e "${BLUE}[i] $1${NC}"
}

print_header() {
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${CYAN} $1${NC}"
    echo -e "${CYAN}========================================${NC}\n"
}

# 记录日志
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# 执行或模拟命令
execute_cmd() {
    local cmd="$1"
    local description="$2"

    if [ "$DRY_RUN" = true ]; then
        print_warning "[模拟] $description"
        print_info "  命令: $cmd"
        log "DRY-RUN" "$description: $cmd"
    else
        print_info "$description"
        eval "$cmd"
        local exit_code=$?
        if [ $exit_code -eq 0 ]; then
            print_success "$description - 完成"
            log "SUCCESS" "$description"
        else
            print_error "$description - 失败 (退出码: $exit_code)"
            log "ERROR" "$description 失败，退出码: $exit_code"
            DEPLOY_SUCCESS=false
        fi
    fi
}

# =============================================================================
# 检查函数
# =============================================================================

# 检查 Python 版本
check_python_version() {
    print_header "检查 Python 版本"

    if [ ! -f "$PYTHON_PATH" ]; then
        print_error "Python 未找到: $PYTHON_PATH"
        log "ERROR" "Python 路径不存在: $PYTHON_PATH"
        DEPLOY_SUCCESS=false
        return 1
    fi

    local python_version=$("$PYTHON_PATH" --version 2>&1 | awk '{print $2}')
    local major=$(echo "$python_version" | cut -d. -f1)
    local minor=$(echo "$python_version" | cut -d. -f2)

    print_info "检测到 Python 版本: $python_version"

    if [ "$major" -ge 3 ] && [ "$minor" -ge 12 ]; then
        print_success "Python 版本满足要求 (>= 3.12)"
        log "SUCCESS" "Python 版本检查通过: $python_version"
    else
        print_error "Python 版本过低，需要 3.12+，当前: $python_version"
        log "ERROR" "Python 版本不满足要求: $python_version"
        DEPLOY_SUCCESS=false
        return 1
    fi
}

# 安装/验证 pip 依赖
check_dependencies() {
    print_header "检查 pip 依赖"

    local requirements_file="$PROJECT_ROOT/requirements.txt"

    if [ ! -f "$requirements_file" ]; then
        print_error "requirements.txt 不存在"
        log "ERROR" "requirements.txt 文件缺失"
        DEPLOY_SUCCESS=false
        return 1
    fi

    print_info "正在安装/验证依赖..."
    execute_cmd "\"$PYTHON_PATH\" -m pip install -r \"$requirements_file\" --quiet" "安装 pip 依赖"
}

# 运行测试套件
run_tests() {
    print_header "运行测试套件"

    if [ "$SKIP_TESTS" = true ]; then
        print_warning "跳过测试 (--skip-tests 标志)"
        log "WARNING" "测试已跳过"
        return 0
    fi

    local tests_dir="$PROJECT_ROOT/tests"

    if [ ! -d "$tests_dir" ]; then
        print_error "测试目录不存在: $tests_dir"
        log "ERROR" "测试目录缺失"
        DEPLOY_SUCCESS=false
        return 1
    fi

    execute_cmd "cd \"$PROJECT_ROOT\" && \"$PYTHON_PATH\" -m pytest tests/ -v --tb=short" "运行 pytest 测试套件"
}

# 验证配置文件
validate_config() {
    print_header "验证配置文件"

    local config_files=(
        "$PROJECT_ROOT/config/config.json"
        "$PROJECT_ROOT/config/positions.json"
    )

    local all_valid=true

    for config_file in "${config_files[@]}"; do
        if [ -f "$config_file" ]; then
            print_success "配置文件存在: $(basename "$config_file")"
            log "SUCCESS" "配置文件验证通过: $config_file"

            # 验证 JSON 格式
            if "$PYTHON_PATH" -c "import json; json.load(open('$config_file'))" 2>/dev/null; then
                print_success "  JSON 格式有效"
            else
                print_warning "  JSON 格式可能有问题"
                log "WARNING" "JSON 格式异常: $config_file"
            fi
        else
            print_error "配置文件缺失: $config_file"
            log "ERROR" "配置文件不存在: $config_file"
            all_valid=false
            DEPLOY_SUCCESS=false
        fi
    done

    if [ "$all_valid" = false ]; then
        return 1
    fi
}

# 验证数据目录结构
validate_data_directory() {
    print_header "验证数据目录结构"

    local data_dir="$PROJECT_ROOT/data"
    local required_files=(
        "factor_knowledge.json"
    )

    # 检查 data 目录
    if [ ! -d "$data_dir" ]; then
        print_error "数据目录不存在: $data_dir"
        log "ERROR" "数据目录缺失"
        DEPLOY_SUCCESS=false
        return 1
    fi

    print_success "数据目录存在: data/"

    # 检查必需文件
    local all_valid=true
    for file in "${required_files[@]}"; do
        local file_path="$data_dir/$file"
        if [ -f "$file_path" ]; then
            print_success "数据文件存在: $file"
            log "SUCCESS" "数据文件验证通过: $file_path"
        else
            print_error "数据文件缺失: $file"
            log "ERROR" "数据文件不存在: $file_path"
            all_valid=false
            DEPLOY_SUCCESS=false
        fi
    done

    # 列出数据目录内容
    print_info "数据目录内容:"
    ls -la "$data_dir" | grep -v "^total" | while read -r line; do
        echo "  $line"
    done

    if [ "$all_valid" = false ]; then
        return 1
    fi
}

# 检查 TqSdk 环境变量
check_tqsdk_env() {
    print_header "检查 TqSdk 环境变量"

    local env_vars=(
        "TQ_USER"
        "TQ_PASSWORD"
    )

    local all_set=true

    for var in "${env_vars[@]}"; do
        if [ -n "${!var}" ]; then
            print_success "环境变量已设置: $var"
            log "SUCCESS" "环境变量 $var 已设置"
        else
            print_warning "环境变量未设置: $var"
            print_info "  设置方法: export $var=your_value"
            log "WARNING" "环境变量 $var 未设置"
            all_set=false
        fi
    done

    if [ "$all_set" = false ]; then
        print_warning "部分环境变量未设置，TqSdk 数据源可能无法正常工作"
        print_info "请在运行扫描器前设置这些环境变量"
    fi
}

# 创建部署日志目录
setup_logging() {
    local logs_dir="$PROJECT_ROOT/logs"
    if [ ! -d "$logs_dir" ]; then
        mkdir -p "$logs_dir"
        print_info "创建日志目录: logs/"
    fi

    # 初始化日志文件
    echo "========================================" > "$LOG_FILE"
    echo "Trend-Scanner-Agent v4.0 部署日志" >> "$LOG_FILE"
    echo "时间: $(date)" >> "$LOG_FILE"
    echo "========================================" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"
}

# 打印部署摘要
print_summary() {
    print_header "部署摘要"

    echo -e "${CYAN}项目根目录:${NC} $PROJECT_ROOT"
    echo -e "${CYAN}Python 路径:${NC} $PYTHON_PATH"
    echo -e "${CYAN}日志文件:${NC}   $LOG_FILE"
    echo -e "${CYAN}时间戳:${NC}     $TIMESTAMP"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}运行模式: 模拟运行 (--dry-run)${NC}"
    fi

    if [ "$SKIP_TESTS" = true ]; then
        echo -e "${YELLOW}测试状态: 已跳过 (--skip-tests)${NC}"
    fi

    echo ""

    if [ "$DEPLOY_SUCCESS" = true ]; then
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN} 部署验证成功!${NC}"
        echo -e "${GREEN}========================================${NC}"
        log "SUCCESS" "部署验证完成，所有检查通过"
    else
        echo -e "${RED}========================================${NC}"
        echo -e "${RED} 部署验证失败!${NC}"
        echo -e "${RED} 请检查上述错误并修复后重试${NC}"
        echo -e "${RED}========================================${NC}"
        log "ERROR" "部署验证失败，存在错误"
    fi
}

# =============================================================================
# 主函数
# =============================================================================

show_help() {
    echo "用法: $0 [选项]"
    echo ""
    echo "Trend-Scanner-Agent v4.0 部署脚本"
    echo ""
    echo "选项:"
    echo "  --dry-run      模拟运行，显示将要执行的操作但不实际执行"
    echo "  --skip-tests   跳过测试套件"
    echo "  --help, -h     显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0                    # 完整部署验证"
    echo "  $0 --dry-run          # 模拟运行"
    echo "  $0 --skip-tests       # 跳过测试"
    echo "  $0 --dry-run --skip-tests  # 模拟运行并跳过测试"
    echo ""
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "未知选项: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

main() {
    # 解析命令行参数
    parse_args "$@"

    # 设置日志
    setup_logging

    # 打印标题
    echo -e "\n${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     Trend-Scanner-Agent v4.0 部署脚本                    ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}\n"

    if [ "$DRY_RUN" = true ]; then
        print_warning "运行模式: 模拟运行 (--dry-run)"
        echo ""
    fi

    log "INFO" "开始部署验证"
    log "INFO" "DRY_RUN=$DRY_RUN, SKIP_TESTS=$SKIP_TESTS"

    # 执行检查步骤
    check_python_version || true
    check_dependencies || true
    validate_config || true
    validate_data_directory || true
    check_tqsdk_env || true
    run_tests || true

    # 打印摘要
    print_summary

    # 返回适当的退出码
    if [ "$DEPLOY_SUCCESS" = true ]; then
        exit 0
    else
        exit 1
    fi
}

# =============================================================================
# 脚本入口
# =============================================================================
main "$@"
