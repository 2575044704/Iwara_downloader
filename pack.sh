#!/bin/bash
# 有组织的自动化打包脚本 - 按月份分目录存放（带进度记录功能）

SOURCE_DIR="/__modal/volumes/vo-ieu7V88l04V1sGny7d7ebd"
TARGET_DIR="/data3/2019-2014"
MAX_TAR_SIZE_GB=11
MAX_TAR_SIZE_BYTES=$((MAX_TAR_SIZE_GB * 1024 * 1024 * 1024))
PARALLEL_JOBS=$(nproc)

# ⭐ 临时文件目录（明确定义）
TEMP_BASE_DIR="/data3/2019-2014/2014/temp"

auto_intelligent_pack() {
    local month_dir=$1
    local month_path="$SOURCE_DIR/$month_dir"
    
    # ⭐ 为每个月份创建独立目录
    local month_target_dir="$TARGET_DIR/$month_dir"
    mkdir -p "$month_target_dir"
    
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] 开始处理: $month_dir"
    echo "目标目录: $month_target_dir"
    
    # 计算文件信息
    local total_size=$(du -sb "$month_path" | awk '{print $1}')
    local file_count=$(find "$month_path" -type f | wc -l)
    
    if [ $file_count -eq 0 ]; then
        echo "[WARNING] $month_dir 没有文件，跳过"
        return
    fi
    
    # 计算每包文件数
    local avg_file_size=$((total_size / file_count))
    local files_per_pack=$((MAX_TAR_SIZE_BYTES / avg_file_size))
    [ $files_per_pack -eq 0 ] && files_per_pack=1
    
    local total_packs=$(((file_count + files_per_pack - 1) / files_per_pack))
    
    echo "[INFO] $month_dir: ${file_count}个文件, $((total_size/1024/1024/1024))GB, 将创建${total_packs}个包"
    
    # ⭐ 检查已完成的包
    local completed_packs=0
    local skipped_packs=""
    for ((i=1; i<=total_packs; i++)); do
        if [ -f "$month_target_dir/part${i}" ]; then
            ((completed_packs++))
            skipped_packs="${skipped_packs} part${i}"
        fi
    done
    
    if [ $completed_packs -gt 0 ]; then
        echo "[INFO] 发现 ${completed_packs} 个已完成的包，将跳过:${skipped_packs}"
    fi
    
    # ⭐ 生成文件列表并按名称排序（使用持久化临时目录）
    mkdir -p "$TEMP_BASE_DIR"
    local temp_dir="$TEMP_BASE_DIR/auto_tar_$$_${month_dir}"
    mkdir -p "$temp_dir"
    echo "[INFO] 正在生成并排序文件列表..."
    echo "[INFO] 临时目录: $temp_dir"
    find "$month_path" -type f | sort > "$temp_dir/all_files.txt"
    
    # 显示前5个和后5个文件名以确认排序
    echo "[INFO] 文件列表已按名称排序"
    echo "前5个文件:"
    head -5 "$temp_dir/all_files.txt" | xargs -I {} basename "{}"
    echo "..."
    echo "后5个文件:"
    tail -5 "$temp_dir/all_files.txt" | xargs -I {} basename "{}"
    
    # 分批打包
    local current_line=0
    local pack_num=1
    local actual_created=0
    
    while [ $current_line -lt $file_count ]; do
        local tar_file="$month_target_dir/part${pack_num}.tar"
        local marker_file="$month_target_dir/part${pack_num}"
        
        # ⭐ 检查占位文件，如果存在则跳过
        if [ -f "$marker_file" ]; then
            echo "[$(date +%H:%M:%S)] ⏭️  跳过已完成: $month_dir/part${pack_num}.tar"
        else
            # ⭐ 如果tar文件存在但没有占位文件，删除并重新打包
            if [ -f "$tar_file" ]; then
                echo "[$(date +%H:%M:%S)] ⚠️  删除未完成的包: $tar_file"
                rm -f "$tar_file"
            fi
            
            # 生成批次文件列表
            sed -n "$((current_line + 1)),$((current_line + files_per_pack))p" "$temp_dir/all_files.txt" > "$temp_dir/batch_${pack_num}.txt"
            
            # ⭐ 打包并生成占位文件
            if tar -cf "$tar_file" \
                -T "$temp_dir/batch_${pack_num}.txt" \
                --ignore-failed-read \
                --warning=no-file-changed \
                2>/dev/null; then
                # 成功后创建占位文件
                touch "$marker_file"
                echo "[$(date +%H:%M:%S)] ✓ $month_dir/part${pack_num}.tar (已标记完成)"
                ((actual_created++))
            else
                echo "[$(date +%H:%M:%S)] ✗ $month_dir/part${pack_num}.tar 打包失败"
                rm -f "$tar_file"  # 删除失败的包
            fi
            rm -f "$temp_dir/batch_${pack_num}.txt" &
            
            if [ $(jobs -r | wc -l) -ge $PARALLEL_JOBS ]; then
                wait -n
            fi
        fi
        
        current_line=$((current_line + files_per_pack))
        ((pack_num++))
    done
    
    wait
    rm -rf "$temp_dir"
    
    # ⭐ 在月份目录中生成清单（包含进度信息）
    echo "[INFO] 生成 $month_dir 清单..."
    {
        echo "=== $month_dir 打包清单 ==="
        echo "打包时间: $(date)"
        echo "包数量: $((pack_num - 1))"
        echo "源大小: $((total_size/1024/1024/1024))GB"
        echo "文件排序: 按文件名字母顺序"
        echo "本次新建: ${actual_created} 个包"
        echo "本次跳过: ${completed_packs} 个包"
        echo ""
        echo "文件列表:"
        ls -lh "$month_target_dir"/*.tar 2>/dev/null | head -20
        echo ""
        echo "占位文件（标记已完成的包）:"
        local marker_count=$(ls -1 "$month_target_dir"/part* 2>/dev/null | grep -v '\.tar$' | wc -l)
        echo "已完成: ${marker_count} 个"
    } > "$month_target_dir/README.txt"
    
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] 完成: $month_dir (新建${actual_created}个包，跳过${completed_packs}个包)"
}

# 显示进度统计
show_progress() {
    echo ""
    echo "========== 当前进度统计 =========="
    for month in 2014-01 2014-02 2014-03 2014-04 2014-05 2014-06 2014-07 2014-08 2014-09 2014-10 2014-11 2014-12; do
        local month_target_dir="$TARGET_DIR/$month"
        if [ -d "$month_target_dir" ]; then
            local total_tars=$(ls -1 "$month_target_dir"/*.tar 2>/dev/null | wc -l)
            local completed_markers=$(ls -1 "$month_target_dir"/part* 2>/dev/null | grep -v '\.tar$' | wc -l)
            echo "$month: 已完成 $completed_markers 个包 (共 $total_tars 个tar文件)"
        fi
    done
    echo "=================================="
    echo ""
}

# 主函数
main() {
    echo "========== 开始打包2014年数据 =========="
    echo "源目录: $SOURCE_DIR"
    echo "目标根目录: $TARGET_DIR"
    echo "文件排序: 启用（按文件名排序）"
    echo "进度记录: 启用（使用占位文件）"
    echo "临时文件: $TEMP_BASE_DIR"
    echo "========================================"
    
    # 创建2014年目录
    mkdir -p "$TARGET_DIR/2014"
    TARGET_DIR="$TARGET_DIR/2014"
    
    # 清理可能存在的旧临时文件
    if [ -d "$TEMP_BASE_DIR" ]; then
        echo "[INFO] 清理旧的临时文件..."
        rm -rf "$TEMP_BASE_DIR"/auto_tar_*
    fi
    
    # 显示当前进度
    show_progress
    
    # 处理每个月
    for month in 2014-01 2014-02 2014-03 2014-04 2014-05 2014-06 2014-07 2014-08 2014-09 2014-10 2014-11 2014-12; do
        if [ -d "$SOURCE_DIR/$month" ]; then
            auto_intelligent_pack "$month"
        fi
    done
    
    # ⭐ 生成总览报告
    echo "生成总览报告..."
    {
        echo "=== 2014年打包总览 ==="
        echo "完成时间: $(date)"
        echo "文件排序: 按文件名字母顺序"
        echo "进度记录: 使用占位文件标记"
        echo "临时文件位置: $TEMP_BASE_DIR"
        echo ""
        for month in 2014-*; do
            if [ -d "$TARGET_DIR/$month" ]; then
                local total_tars=$(ls -1 "$TARGET_DIR/$month"/*.tar 2>/dev/null | wc -l)
                local completed_markers=$(ls -1 "$TARGET_DIR/$month"/part* 2>/dev/null | grep -v '\.tar$' | wc -l)
                echo "$month:"
                echo "  总包数: $total_tars"
                echo "  已完成: $completed_markers"
                echo "  总大小: $(du -sh $TARGET_DIR/$month | awk '{print $1}')"
                echo ""
            fi
        done
    } > "$TARGET_DIR/总览.txt"
    
    echo ""
    echo "========== 完成 =========="
    echo "最终进度统计："
    show_progress
    echo "目录结构："
    tree -L 2 "$TARGET_DIR" 2>/dev/null || ls -la "$TARGET_DIR"
}

# 清理占位文件功能（可选）
clean_markers() {
    echo "清理所有占位文件..."
    find "$TARGET_DIR/2014" -type f -name "part[0-9]*" ! -name "*.tar" -delete
    echo "占位文件已清理"
}

# 清理临时文件功能
clean_temp() {
    echo "清理所有临时文件..."
    if [ -d "$TEMP_BASE_DIR" ]; then
        rm -rf "$TEMP_BASE_DIR"
        echo "临时文件已清理"
    else
        echo "没有找到临时文件"
    fi
}

# 检查命令行参数
if [ "$1" = "clean" ]; then
    clean_markers
    exit 0
elif [ "$1" = "cleantemp" ]; then
    clean_temp
    exit 0
elif [ "$1" = "cleanall" ]; then
    clean_markers
    clean_temp
    exit 0
fi

trap 'echo "[ERROR] 脚本中断"; exit 1' INT TERM
main