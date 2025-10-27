#!/bin/bash
SERVER="172.16.1.72"
USER="yunhsihsu"

# 檢查參數：需要的總測量次數（預設為5次）
REQUIRED_MEASUREMENTS=${1:-50}

CPU_MODEL=$(lscpu | grep "Model name" | cut -d ':' -f 2 | sed 's/^ *//')
echo "[Client] CPU 型號：$CPU_MODEL"
echo "[Client] 需要的總測量次數：$REQUIRED_MEASUREMENTS"

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

# 檢查server端現有的測量次數
echo "[Client] 檢查server端現有測量資料..."
RESPONSE=$(ssh ${USER}@${SERVER} "bash ~/test_server1.sh \"$CPU_MODEL\" $REQUIRED_MEASUREMENTS")

# 解析回應
if [[ "$RESPONSE" == SUFFICIENT* ]]; then
    echo "[Client] Server 已有足夠測量資料，直接使用現有結果："
    echo "$RESPONSE" | sed '1d' > result.txt
    cat result.txt
    echo "[Client] 結果已儲存至 result.txt"
    exit 0
    
elif [[ "$RESPONSE" == NEED_MORE* ]]; then
    # 解析還需要幾次測量
    CURRENT_COUNT=$(echo "$RESPONSE" | grep -o "CURRENT:[0-9]*" | cut -d: -f2)
    NEEDED_COUNT=$(echo "$RESPONSE" | grep -o "NEED:[0-9]*" | cut -d: -f2)
    
    echo "[Client] 當前測量次數：$CURRENT_COUNT"
    echo "[Client] 還需要測量：$NEEDED_COUNT 次"
    
    MEASUREMENT_TIMES=$NEEDED_COUNT
else
    echo "[Client] Server 沒有測量資料，需要進行 $REQUIRED_MEASUREMENTS 次測量"
    MEASUREMENT_TIMES=$REQUIRED_MEASUREMENTS
fi

# 如果需要測量，準備測量環境
if [ "$MEASUREMENT_TIMES" -gt 0 ]; then
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
    echo "export PATH=\"$HOME/.cargo/bin:$PATH\"" > $HOME/.bashrc
    source $HOME/.bashrc
    
    echo "[Client] 準備開始 $MEASUREMENT_TIMES 次測量，設置進程暫停機制..."
    
    # 設置陷阱以確保即使腳本異常退出也能恢復進程
    trap 'resume_processes; exit 1' INT TERM EXIT
    
    # 在測量前暫停進程
    pause_processes
    
    # 存儲所有測量檔案的名稱
    MEASUREMENT_FILES=()
    
    # 執行多次測量
    for i in $(seq 1 $MEASUREMENT_TIMES); do
        echo "[Client] 開始第 $i/$MEASUREMENT_TIMES 次測量..."
        sleep 2  # 讓系統穩定
        
        # 生成帶時間戳和序號的檔案名稱
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        OUTPUT_FILE="output_${TIMESTAMP}_${i}.csv"
        
        # 執行測量
        echo "[Client] 執行 core-to-core-latency..."
        core-to-core-latency 5000 --csv > "$OUTPUT_FILE"
        
        # 檢查檔案是否成功生成
        if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
            MEASUREMENT_FILES+=("$OUTPUT_FILE")
            echo "[Client] 第 $i 次測量完成：$OUTPUT_FILE"
        else
            echo "[Client] 第 $i 次測量失敗，檔案未生成或為空"
        fi
        
        # 如果不是最後一次測量，等待一下
        if [ $i -lt $MEASUREMENT_TIMES ]; then
            echo "[Client] 等待 3 秒後進行下一次測量..."
            sleep 3
        fi
    done
    
    # 測量完成後立即恢復進程
    resume_processes
    
    cd ..
    
    echo "[Client] 測量完成，共產生 ${#MEASUREMENT_FILES[@]} 個檔案"
    
    # 如果沒有成功的測量檔案，退出
    if [ ${#MEASUREMENT_FILES[@]} -eq 0 ]; then
        echo "[Client] 錯誤：沒有成功的測量檔案"
        trap - INT TERM EXIT
        exit 1
    fi
    
    # 將所有測量檔案傳送到server
    echo "[Client] 傳送測量檔案到 server..."
    for file in "${MEASUREMENT_FILES[@]}"; do
        echo "[Client] 傳送 $file"
        scp "core-to-core-latency/$file" ${USER}@${SERVER}:~/RON_TSP/tmp/$file
    done
    
    # 通知server處理這批測量資料並計算TSP
    echo "[Client] 通知 server 處理測量資料..."
    TSP_RESULT=$(ssh ${USER}@${SERVER} "bash ~/test_result1.sh \"$CPU_MODEL\" $REQUIRED_MEASUREMENTS")
    
    echo "[Client] 收到的TSP結果："
    echo "$TSP_RESULT"
    
    # 從結果中提取最後一行（TSP順序）
    echo "$TSP_RESULT" | awk 'NF{last=$0} END{print last}' > result.txt
    
    # 清除陷阱（因為正常執行完成）
    trap - INT TERM EXIT
    
    echo "[Client] 所有測量和計算完成，結果已儲存至 result.txt"
fi
