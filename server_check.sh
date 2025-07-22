#!/bin/bash
echo "========== 监控脚本启动 $(date) =========="
while true; do
    echo ""
    echo "[$(date)] 开始检查服务器状态..."
    
    # 检查第一个服务器
    echo "[$(date)] 正在检查 hime.iwara.tv..."
    if curl -s --connect-timeout 5 -o /dev/null hime.iwara.tv; then
        echo "[$(date)] ✓ hime.iwara.tv 正常"
    else
        echo "[$(date)] ✗ hime.iwara.tv 无法访问"
        
        # 第一个不通，检查第二个
        echo "[$(date)] 正在检查 mikoto.iwara.tv..."
        if curl -s --connect-timeout 5 -o /dev/null mikoto.iwara.tv; then
            echo "[$(date)] ✓ mikoto.iwara.tv 正常"
        else
            echo "[$(date)] ✗ mikoto.iwara.tv 也无法访问"
            echo "[$(date)] !!! 两个服务器都挂了，准备杀死jupyter进程"
            sleep 30
            # 查找进程
            PID=$(ps aux | grep "jupyter-lab.*--port=52001" | grep -v grep | awk '{print $2}')
            if [ -n "$PID" ]; then
                echo "[$(date)] 找到jupyter进程 PID: $PID"
                kill $PID
                echo "[$(date)] 已发送kill -9信号到进程 $PID"
            else
                echo "[$(date)] 没有找到jupyter进程"
            fi
        fi
    fi
    
    echo "[$(date)] 等待60秒后继续检查..."
    echo "----------------------------------------"
    sleep 600
done