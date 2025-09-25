#!/bin/bash
# 檢查是否有足夠的測量資料
BASE_PATH=$HOME
CPU_MODEL="$1"
REQUIRED_MEASUREMENTS=${2:-5}  # 預設需要5次測量

cd $HOME
if [ ! -d "RON_TSP" ]; then
    mkdir RON_TSP
fi
cd ./RON_TSP
if [ ! -d "measurements" ]; then
    mkdir measurements
fi
if [ ! -d "tsp_order" ]; then
    mkdir tsp_order
fi
if [ ! -d "tmp" ]; then
    mkdir tmp
fi
cd $HOME

RESULT_DIR=$BASE_PATH/RON_TSP/tsp_order
MEASUREMENTS_DIR=$BASE_PATH/RON_TSP/measurements
SAFE_MODEL=$(echo "$CPU_MODEL" | tr ' ' '_' | tr -d '()')

echo "[Server] CPU型號: $CPU_MODEL" >&2
echo "[Server] 安全檔名: $SAFE_MODEL" >&2
echo "[Server] 測量目錄: $MEASUREMENTS_DIR/$SAFE_MODEL" >&2

# 檢查是否已有足夠的測量資料
MEASUREMENT_COUNT=0
if [ -d "$MEASUREMENTS_DIR/$SAFE_MODEL" ]; then
    MEASUREMENT_COUNT=$(ls "$MEASUREMENTS_DIR/$SAFE_MODEL"/output_*.csv 2>/dev/null | wc -l)
fi

echo "[Server] 當前測量次數: $MEASUREMENT_COUNT, 需要次數: $REQUIRED_MEASUREMENTS" >&2

TSP_FILE="$RESULT_DIR/$SAFE_MODEL/tsp_order.csv"
echo "[Server] TSP檔案路徑: $TSP_FILE" >&2
echo "[Server] TSP檔案存在: $([ -f "$TSP_FILE" ] && echo "是" || echo "否")" >&2

# 如果測量次數足夠且已有TSP結果，直接回傳
if [ $MEASUREMENT_COUNT -ge $REQUIRED_MEASUREMENTS ] && [ -f "$TSP_FILE" ]; then
    echo "SUFFICIENT"
    paste -sd' ' "$TSP_FILE"
else
    echo "INSUFFICIENT"
    # 確保目錄存在
    mkdir -p "$MEASUREMENTS_DIR/$SAFE_MODEL"
    mkdir -p "$RESULT_DIR/$SAFE_MODEL"
fi
