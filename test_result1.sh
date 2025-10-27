#!/bin/bash
# 用來處理 client 傳來的測量檔案，並在達到要求時執行 TSP 計算
BASE_PATH=$HOME
CPU_MODEL="$1"
REQUIRED_MEASUREMENTS="$2"  # 需要的總測量次數

RESULT_DIR=$BASE_PATH/RON_TSP/tsp_order
MEASUREMENTS_DIR=$BASE_PATH/RON_TSP/measurements
mkdir -p "$RESULT_DIR"
mkdir -p "$MEASUREMENTS_DIR"

SAFE_MODEL=$(echo "$CPU_MODEL" | tr ' ' '_' | tr -d '()')
MEASUREMENT_FOLDER="$MEASUREMENTS_DIR/$SAFE_MODEL"
mkdir -p "$MEASUREMENT_FOLDER"

echo "[Server] 處理 CPU: $CPU_MODEL (安全檔名: $SAFE_MODEL)"
echo "[Server] 需要總測量次數: $REQUIRED_MEASUREMENTS"

# 移動 tmp 目錄中的所有相關檔案到 measurements 目錄
TMP_DIR="$BASE_PATH/RON_TSP/tmp"
MOVED_FILES=0

if [ -d "$TMP_DIR" ]; then
    # 尋找所有以 output_ 開頭的 CSV 檔案
    for file in "$TMP_DIR"/output_*.csv; do
        if [ -f "$file" ]; then
            FILENAME=$(basename "$file")
            DEST_FILE="$MEASUREMENT_FOLDER/$FILENAME"
            mv "$file" "$DEST_FILE"
            if [ -f "$DEST_FILE" ]; then
                echo "[Server] 已移動測量檔案：$DEST_FILE"
                MOVED_FILES=$((MOVED_FILES + 1))
            fi
        fi
    done
fi

echo "[Server] 本次移動 $MOVED_FILES 個測量檔案"

# 計算當前總測量次數
TOTAL_MEASUREMENT_COUNT=$(ls "$MEASUREMENT_FOLDER"/output_*.csv 2>/dev/null | wc -l)
echo "[Server] 當前總測量次數: $TOTAL_MEASUREMENT_COUNT"

if [ $TOTAL_MEASUREMENT_COUNT -ge $REQUIRED_MEASUREMENTS ]; then
    echo "[Server] 測量次數已足夠，開始計算平均latency並執行TSP計算..."
    
    # 使用Python腳本來計算所有測量的平均值
    python3 $BASE_PATH/cal_avg.py $MEASUREMENT_FOLDER $BASE_PATH/RON_TSP/tsp_order/output.csv
    
    # 檢查平均latency檔案是否成功產生
    AVERAGE_FILE="$BASE_PATH/RON_TSP/tsp_order/output.csv"
    if [ -f "$AVERAGE_FILE" ]; then
        echo "[Server] 執行 TSP 計算..."
        
        # 執行 TSP 計算
        source $BASE_PATH/venv/bin/activate
        python3 $BASE_PATH/tsp.py 
        
        # 假設 toTSP.py 會產生 ~/RON_TSP/tsp_order.csv
        TSP_FILE="$BASE_PATH/RON_TSP/tsp_order.csv"
        FINAL_TSP_FILE="$RESULT_DIR/$SAFE_MODEL/tsp_order.csv"
        
        if [ -f "$TSP_FILE" ]; then
            # 確保目錄存在
            mkdir -p "$RESULT_DIR/$SAFE_MODEL"
            mv "$TSP_FILE" "$FINAL_TSP_FILE"
            echo "[Server] TSP 結果已產生：$FINAL_TSP_FILE"
            echo "[Server] 基於 $REQUIRED_MEASUREMENTS 次測量的平均結果"
            
            # 回傳結果給 client
            paste -sd' ' "$FINAL_TSP_FILE"
        else
            echo "[Server] 錯誤：沒有產生 tsp_order.csv"
            exit 1
        fi
        
        # 清理臨時的平均檔案
        rm -f "$AVERAGE_FILE"
    else
        echo "[Server] 錯誤：無法產生平均latency檔案"
        exit 1
    fi
else
    echo "[Server] 測量次數仍然不足"
    echo "[Server] 當前: $TOTAL_MEASUREMENT_COUNT, 需要: $REQUIRED_MEASUREMENTS"
    STILL_NEEDED=$((REQUIRED_MEASUREMENTS - TOTAL_MEASUREMENT_COUNT))
    echo "[Server] 還需要 $STILL_NEEDED 次測量"
    exit 1
fi
