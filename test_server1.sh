#!/bin/bash
# 檢查現有測量次數並回報狀態
BASE_PATH=$HOME
CPU_MODEL="$1"
REQUIRED_MEASUREMENTS=${2:-12}  # 需要的總測量次數

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
if [ ! -d "route" ]; then
    mkdir tsp_order
fi
if [ ! -d "tmp" ]; then
    mkdir tmp
fi
cd $HOME

RESULT_DIR=$BASE_PATH/RON_TSP
MEASUREMENTS_DIR=$BASE_PATH/RON_TSP/measurements
SAFE_MODEL=$(echo "$CPU_MODEL" | tr ' ' '_' | tr -d '()')

echo "[Server] CPU型號: $CPU_MODEL" >&2
echo "[Server] 安全檔名: $SAFE_MODEL" >&2
echo "[Server] 需要測量次數: $REQUIRED_MEASUREMENTS" >&2

# 檢查現有測量次數
CURRENT_MEASUREMENT_COUNT=0
if [ -d "$MEASUREMENTS_DIR/$SAFE_MODEL" ]; then
    CURRENT_MEASUREMENT_COUNT=$(ls "$MEASUREMENTS_DIR/$SAFE_MODEL"/output_*.csv 2>/dev/null | wc -l)
fi

echo "[Server] 當前測量次數: $CURRENT_MEASUREMENT_COUNT" >&2

TSP_FILE="$RESULT_DIR/tsp_order/$SAFE_MODEL/tsp_order.csv"
ROUTE_FILE="$RESULT_DIR/route/$SAFE_MODEL/route.csv"

# 如果測量次數足夠且已有TSP結果，直接回傳
if [ $CURRENT_MEASUREMENT_COUNT -ge $REQUIRED_MEASUREMENTS ] && [ -f "$TSP_FILE" ]; then
    echo "[Server] 測量次數足夠且已有TSP結果，直接回傳" >&2
    echo "SUFFICIENT"
    paste -sd' ' "$TSP_FILE"
    paste -sd' ' "$ROUTE_FILE"
    
elif [ $CURRENT_MEASUREMENT_COUNT -gt 0 ] && [ $CURRENT_MEASUREMENT_COUNT -lt $REQUIRED_MEASUREMENTS ]; then
    # 有一些測量但不足夠
    NEEDED_COUNT=$((REQUIRED_MEASUREMENTS - CURRENT_MEASUREMENT_COUNT))
    echo "[Server] 測量次數不足，還需要 $NEEDED_COUNT 次" >&2
    echo "NEED_MORE CURRENT:$CURRENT_MEASUREMENT_COUNT NEED:$NEEDED_COUNT"
    
elif [ $CURRENT_MEASUREMENT_COUNT -gt $REQUIRED_MEASUREMENTS ] ; then
    # 測量次數足夠
    echo "[Server] 測量次數足夠" >&2
    echo "NEXT"

else
    # 沒有測量資料或其他情況
    echo "[Server] 沒有測量資料，需要全部重新測量" >&2
    echo "NEED_ALL CURRENT:0 NEED:$REQUIRED_MEASUREMENTS"
fi

# 確保目錄存在
mkdir -p "$MEASUREMENTS_DIR/$SAFE_MODEL"
mkdir -p "$RESULT_DIR/tsp_order/$SAFE_MODEL"
mkdir -p "$RESULT_DIR/route/$SAFE_MODEL"
