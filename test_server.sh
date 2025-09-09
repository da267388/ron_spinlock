#!/bin/bash
# 用來儲存 client 傳來的 CSV 檔案，並執行 TSP 計算
# 參數：
#   $1 = CPU 型號
#   $2 = CSV 檔案路徑 (client scp 上來的)

CPU_MODEL="$1"
CSV_PATH="$2"

RESULT_DIR=~/server/results
mkdir -p $RESULT_DIR

# 把 CPU 型號轉換成檔名可接受的格式（避免空白、括號等）
SAFE_MODEL=$(echo "$CPU_MODEL" | tr ' ' '_' | tr -d '()')

# 最終存檔名稱
DEST_FILE="$RESULT_DIR/${SAFE_MODEL}_$(date '+%Y%m%d_%H%M%S').csv"

# 移動 client 上傳的 output.csv 到正式路徑
mv "$CSV_PATH" "$DEST_FILE"

echo "[Server] 已存檔：$DEST_FILE"

# 執行 TSP 計算
echo "[Server] 執行 TSP 計算..."
python3 ~/server/toTSP.py "$DEST_FILE" > /dev/null

# 假設 toTSP.py 輸出的結果一定是 ~/server/tsp_order.csv
TSP_FILE=~/server/tsp_order.csv

if [ -f "$TSP_FILE" ]; then
    echo "[Server] TSP 結果已產生：$TSP_FILE"
    # 將 csv 內容轉成單一字串回傳給 client
    tr '\n' ' ' < "$TSP_FILE"
else
    echo "[Server] 錯誤：沒有產生 tsp_order.csv"
    exit 1
fi

