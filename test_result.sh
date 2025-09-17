#!/bin/bash
# 用來儲存 client 傳來的 CSV 檔案，並執行 TSP 計算
BASE_PATH=$HOME
CPU_MODEL="$1"
CSV_PATH="$2"

RESULT_DIR=$BASE_PATH/RON_TSP/tsp_order
mkdir -p $RESULT_DIR

SAFE_MODEL=$(echo "$CPU_MODEL" | tr ' ' '_' | tr -d '()')
DEST_FILE="$BASE_PATH/RON_TSP/tsp_order/output.csv"

# 存 latency 的原始輸出
mv "$CSV_PATH" "$DEST_FILE"

echo "[Server] 已存檔：$DEST_FILE"

while [ ! -f "$DEST_FILE" ]; do
    sleep 1
done

# 執行 TSP 計算
echo "[Server] 執行 TSP 計算..."
python3 ~/toTSP.py 

# 假設 toTSP.py 會產生 ~/server/tsp_order.csv
TSP_FILE=$BASE_PATH/RON_TSP/tsp_order.csv
FINAL_TSP_FILE="$RESULT_DIR/$SAFE_MODEL/tsp_order.csv"

if [ -f "$TSP_FILE" ]; then
    mv "$TSP_FILE" "$FINAL_TSP_FILE"
    echo "[Server] TSP 結果已產生：$FINAL_TSP_FILE"
    # 回傳結果給 client
    #tr '\n' ' ' < "$FINAL_TSP_FILE"
    paste -sd' ' "$FINAL_TSP_FILE"

else
    echo "[Server] 錯誤：沒有產生 tsp_order.csv"
    exit 1
fi

