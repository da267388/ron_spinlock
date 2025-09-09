#!/bin/bash
SERVER="your_server_ip"
USER="your_server_user"
CPU_MODEL=$(lscpu | grep "Model name" | cut -d ':' -f 2 | sed 's/^ *//')
echo "[Client] CPU 型號：$CPU_MODEL"

#RESPONSE=$(ssh ${USER}@${SERVER} "bash ~/server/test_server.sh \"$CPU_MODEL\"")

#if [[ "$RESPONSE" == FOUND* ]]; then
    #LATENCY=$(echo "$RESPONSE" | cut -d ' ' -f 2)
    #echo "[Client] Server 查到 latency：$LATENCY"
#else
    echo "[Client] Server 沒有資料，準備測量 core-to-core latency..."

    echo "[Client] 安裝 Rust (cargo) 與 Python 依賴..."
    if ! command -v cargo &> /dev/null; then
        sudo apt update
        sudo apt install -y curl build-essential pkg-config libssl-dev
        curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
        source $HOME/.cargo/env
    fi
    
    echo "[Client] 測量 core-to-core latency..."
    if [ ! -d "core-to-core-latency" ]; then
        git clone https://github.com/nviennot/core-to-core-latency.git
    fi
    cd core-to-core-latency
    cargo install core-to-core-latency
    core-to-core-latency 5000 --csv > output.csv
    
    #LATENCY=$(./core-to-core-latency)
    cd ..
    

    
    #echo "[Client] 測量結果：$LATENCY ns"

    # 回傳 latency 給 server
    #ssh ${USER}@${SERVER} "bash ~/server/save_result.sh \"$CPU_MODEL\" \"$LATENCY\""
    
    echo "[Client] 傳送 output.csv 到 server"
    # 通知 server 保存結果 + 執行 TSP，並接收回傳字串
    TSP_RESULT=$(ssh ${USER}@${SERVER} "bash ~/server/save_result.sh \"$CPU_MODEL\" ~/server/tmp/output.csv")

    echo "[Client] 收到的 TSP 排序結果："
    echo "$TSP_RESULT"

#fi

