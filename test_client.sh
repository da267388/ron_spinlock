#!/bin/bash
SERVER="172.16.1.72"
USER="yunhsihsu"
CPU_MODEL=$(lscpu | grep "Model name" | cut -d ':' -f 2 | sed 's/^ *//')
echo "[Client] CPU 型號：$CPU_MODEL"

RESPONSE=$(ssh ${USER}@${SERVER} "bash ~/RON_TSP/test_server.sh \"$CPU_MODEL\"")

if [[ "$RESPONSE" == FOUND* ]]; then
    echo "[Client] Server 查到 TSP 排序："
    echo "$RESPONSE"
else
    echo "[Client] Server 沒有資料，準備測量 core-to-core latency..."

    if ! command -v cargo &> /dev/null; then
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
    ./target/release/core-to-core-latency 5000 --csv > output.csv
    cd ..

    echo "[Client] 傳送 output.csv 到 server"
    scp core-to-core-latency/output.csv ${USER}@${SERVER}:~/RON_TSP/tmp/output.csv

    TSP_RESULT=$(ssh ${USER}@${SERVER} "bash ~/RON_TSP/test_result.sh \"$CPU_MODEL\" ~/server/tmp/output.csv")

    echo "[Client] 收到的 TSP 排序結果："
    echo "$TSP_RESULT"
fi

