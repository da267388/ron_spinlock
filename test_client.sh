#!/bin/bash
SERVER="172.16.1.72"
USER="yunhsihsu"
CPU_MODEL=$(lscpu | grep "Model name" | cut -d ':' -f 2 | sed 's/^ *//')
echo "[Client] CPU 型號：$CPU_MODEL"

# 函數：暫停非關鍵進程
pause_processes() {
    echo "[Client] 正在暫停非關鍵進程以確保測量準確性..."
    
    # 停止不必要的服務
    sudo systemctl stop cron 2>/dev/null || true
    sudo systemctl stop rsyslog 2>/dev/null || true
    sudo systemctl stop systemd-journald 2>/dev/null || true
    
    # 設定 CPU governor 為 performance 模式
    echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true
    
    # 暫停用戶進程（排除關鍵系統進程和當前 shell）
    SUSPENDED_PIDS=()
    
    # 獲取當前用戶的所有進程，排除關鍵進程
    for pid in $(ps -u $(whoami) -o pid --no-headers | grep -v $$); do
        # 檢查進程是否存在且不是關鍵進程
        if kill -0 $pid 2>/dev/null; then
            COMM=$(ps -p $pid -o comm --no-headers 2>/dev/null || echo "")
            # 排除關鍵進程：ssh, bash, systemd 相關等
            if [[ ! "$COMM" =~ ^(ssh|sshd|bash|sh|systemd|kthreadd|ksoftirqd|migration|rcu_|watchdog).*$ ]]; then
                if kill -STOP $pid 2>/dev/null; then
                    SUSPENDED_PIDS+=($pid)
                fi
            fi
        fi
    done
    
    echo "[Client] 已暫停 ${#SUSPENDED_PIDS[@]} 個用戶進程"
}

# 函數：恢復進程
resume_processes() {
    echo "[Client] 正在恢復進程..."
    
    # 恢復暫停的用戶進程
    for pid in "${SUSPENDED_PIDS[@]}"; do
        if kill -0 $pid 2>/dev/null; then
            kill -CONT $pid 2>/dev/null || true
        fi
    done
    
    # 恢復服務
    sudo systemctl start cron 2>/dev/null || true
    sudo systemctl start rsyslog 2>/dev/null || true
    sudo systemctl start systemd-journald 2>/dev/null || true
    
    # 恢復 CPU governor（通常恢復為 ondemand 或 powersave）
    echo ondemand | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor 2>/dev/null || true
    
    echo "[Client] 已恢復 ${#SUSPENDED_PIDS[@]} 個進程和系統服務"
}

# 設置陷阱以確保即使腳本異常退出也能恢復進程
trap 'resume_processes; exit 1' INT TERM EXIT

RESPONSE=$(ssh ${USER}@${SERVER} "bash ~/test_server.sh \"$CPU_MODEL\"")
if [[ "$RESPONSE" == FOUND* ]]; then
    echo "[Client] Server 查到 TSP 排序："
    echo "$RESPONSE"
    echo "$RESPONSE" | awk 'NF{last=$0} END{print last}' > result.txt
else
    echo "[Client] Server 沒有資料，準備測量 core-to-core latency..."
    
    # 安裝依賴
    if ! command -v cargo &> /dev/null; then
        echo "[Client] 安裝 Rust 和相關依賴..."
        sudo apt update
        sudo apt install -y curl build-essential pkg-config libssl-dev cargo
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source $HOME/.cargo/env
    fi
    
    if [ ! -d "core-to-core-latency" ]; then
        git clone https://github.com/nviennot/core-to-core-latency.git
    fi
    cd core-to-core-latency
    cargo install core-to-core-latency
    
    # 在測量前暫停進程
    pause_processes
    
    echo "[Client] 開始測量 core-to-core latency（進程已暫停）..."
    sleep 2  # 讓系統穩定
    
    # 執行測量
    core-to-core-latency 5000 --csv > output.csv
    
    # 測量完成後立即恢復進程
    resume_processes
    
    cd ..
    echo "[Client] 傳送 output.csv 到 server"
    scp core-to-core-latency/output.csv ${USER}@${SERVER}:~/RON_TSP/tmp/output.csv
    TSP_RESULT=$(ssh ${USER}@${SERVER} "bash ~/test_result.sh \"$CPU_MODEL\" ~/RON_TSP/tmp/output.csv")
    echo "[Client] 收到的 TSP 排序結果："
    echo "$TSP_RESULT"
    echo "$TSP_RESULT" | awk 'NF{last=$0} END{print last}' > result.txt
fi

# 清除陷阱（因為正常執行完成）
trap - INT TERM EXIT
