#!/bin/bash
# 批量执行 iwara_batch_downloader.py 脚本
# 可配置开始和结束日期

pip install playwright
playwright install chromium

# 批量执行 iwara_batch_downloader.py 脚本
# 可配置开始和结束日期

# 默认值（修正：开始日期应该早于结束日期）
DEFAULT_START_DATE="2014-02"
DEFAULT_END_DATE="2025-03"

# 初始化变量
START_DATE=""
END_DATE=""

# 解析命令行参数
for arg in "$@"; do
    case $arg in
        --start=*)
            START_DATE="${arg#*=}"
            shift
            ;;
        --end=*)
            END_DATE="${arg#*=}"
            shift
            ;;
        --help|-h)
            echo "使用方法: $0 [选项]"
            echo "选项:"
            echo "  --start=YYYY-MM    设置开始日期（较早的日期，默认: $DEFAULT_START_DATE）"
            echo "  --end=YYYY-MM      设置结束日期（较晚的日期，默认: $DEFAULT_END_DATE）"
            echo "  --help, -h         显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0 --start=2024-03 --end=2025-06"
            echo ""
            echo "注意：脚本将按时间倒序处理（从新到旧）"
            exit 0
            ;;
        *)
            echo "未知参数: $arg"
            echo "使用 $0 --help 查看帮助"
            exit 1
            ;;
    esac
done

# 如果没有提供参数，使用默认值
if [ -z "$START_DATE" ]; then
    START_DATE=$DEFAULT_START_DATE
fi
if [ -z "$END_DATE" ]; then
    END_DATE=$DEFAULT_END_DATE
fi

# 验证日期格式
validate_date() {
    local date=$1
    if ! [[ $date =~ ^[0-9]{4}-[0-9]{2}$ ]]; then
        echo "错误：日期格式不正确: $date"
        echo "正确格式应为: YYYY-MM"
        exit 1
    fi
    
    local year=$(echo $date | cut -d'-' -f1)
    local month=$(echo $date | cut -d'-' -f2)
    
    if [ $month -lt 1 ] || [ $month -gt 12 ]; then
        echo "错误：月份必须在 01-12 之间: $date"
        exit 1
    fi
}

# 验证输入的日期
validate_date "$START_DATE"
validate_date "$END_DATE"

# 解析开始和结束日期
START_YEAR=$(echo $START_DATE | cut -d'-' -f1)
START_MONTH=$(echo $START_DATE | cut -d'-' -f2)
END_YEAR=$(echo $END_DATE | cut -d'-' -f1)
END_MONTH=$(echo $END_DATE | cut -d'-' -f2)

# 验证日期范围逻辑
if [ $START_YEAR -gt $END_YEAR ] || ([ $START_YEAR -eq $END_YEAR ] && [ $((10#$START_MONTH)) -gt $((10#$END_MONTH)) ]); then
    echo "错误：开始日期不能晚于结束日期"
    echo "开始日期: $START_DATE"
    echo "结束日期: $END_DATE"
    exit 1
fi

# 安装依赖
echo "检查并安装依赖..."
pip install playwright
playwright install chromium

echo "开始批量下载任务..."
echo "从 $START_DATE 到 $END_DATE（按时间倒序处理）"
echo "================================"

# 生成所有的年月组合（从结束日期倒推到开始日期）
dates=()

# 从结束日期开始倒推
current_year=$END_YEAR
current_month=$((10#$END_MONTH))

# 循环生成日期，直到达到开始日期
while true; do
    # 格式化月份（确保是两位数）
    formatted_month=$(printf "%02d" $current_month)
    current_date="$current_year-$formatted_month"
    
    # 添加当前日期
    dates+=("$current_date")
    
    # 检查是否达到开始日期
    if [ $current_year -eq $START_YEAR ] && [ $current_month -eq $((10#$START_MONTH)) ]; then
        break
    fi
    
    # 月份递减
    current_month=$((current_month - 1))
    
    # 如果月份小于1，则年份递减，月份重置为12
    if [ $current_month -lt 1 ]; then
        current_month=12
        current_year=$((current_year - 1))
        
        # 额外的安全检查
        if [ $current_year -lt $START_YEAR ]; then
            echo "错误：日期计算出现问题"
            exit 1
        fi
    fi
done

# 显示生成的日期范围
echo "将处理以下日期（从新到旧）："
echo "${dates[@]}"
echo ""

# 计数器
total=${#dates[@]}
completed=0
group_num=1

# 按4个一组处理
for ((i=0; i<${#dates[@]}; i+=4)); do
    echo ""
    echo "执行第 $group_num 组任务..."
    echo "--------------------------------"
    
    # 存储当前组的进程ID
    pids=()
    
    # 启动当前组的任务（最多4个）
    for ((j=0; j<4 && i+j<${#dates[@]}; j++)); do
        date=${dates[$((i+j))]}
        dir="/data2/classification/$date"
        
        echo "启动任务: $date"
        python iwara_batch_downloader.py "$dir" "$date" &
        pids+=($!)
    done
    
    # 等待当前组的所有任务完成
    echo ""
    echo "等待第 $group_num 组任务完成..."
    
    for pid in ${pids[@]}; do
        wait $pid
        status=$?
        if [ $status -eq 0 ]; then
            ((completed++))
            echo "进程 $pid 完成 (成功)"
        else
            echo "进程 $pid 完成 (错误代码: $status)"
        fi
    done
    
    echo "第 $group_num 组任务完成！已完成: $completed/$total"
    echo "================================"
    
    ((group_num++))
    
    # 如果不是最后一组，稍作暂停
    if [ $((i+4)) -lt ${#dates[@]} ]; then
        echo "等待 5 秒后继续下一组..."
        sleep 5
    fi
done

echo ""
echo "所有任务执行完成！"
echo "总计完成: $completed/$total"
echo "================================"