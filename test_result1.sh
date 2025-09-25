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
    python3 -c "
import csv
import os
from collections import defaultdict
import numpy as np

measurement_folder = '$MEASUREMENT_FOLDER'
base_path = '$BASE_PATH'
required_measurements = $REQUIRED_MEASUREMENTS

# 讀取所有測量檔案
all_latencies = defaultdict(list)
csv_files = [f for f in os.listdir(measurement_folder) if f.startswith('output_') and f.endswith('.csv')]
csv_files.sort()  # 確保順序一致

print(f'[Server] 找到 {len(csv_files)} 個測量檔案，將使用前 {required_measurements} 個進行計算')

# 只使用前N個檔案來確保一致性
csv_files = csv_files[:required_measurements]

for csv_file in csv_files:
    file_path = os.path.join(measurement_folder, csv_file)
    print(f'[Server] 處理檔案: {csv_file}')
    
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                core1 = int(row['core1'])
                core2 = int(row['core2'])
                latency = float(row['latency'])
                
                # 使用sorted tuple作為key以確保一致性
                key = tuple(sorted([core1, core2]))
                all_latencies[key].append(latency)
    except Exception as e:
        print(f'[Server] 讀取檔案 {csv_file} 時出錯: {e}')
        continue

if not all_latencies:
    print('[Server] 錯誤：沒有找到有效的測量資料')
    exit(1)

# 計算平均latency
output_file = os.path.join(base_path, 'RON_TSP', 'tsp_order', 'output.csv')
with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['core1', 'core2', 'latency'])
    
    processed_pairs = 0
    for (core1, core2), latencies in sorted(all_latencies.items()):
        if len(latencies) > 0:
            avg_latency = np.mean(latencies)
            std_latency = np.std(latencies) if len(latencies) > 1 else 0
            writer.writerow([core1, core2, avg_latency])
            processed_pairs += 1
            
            # 輸出統計資訊
            print(f'[Server] Core {core1}-{core2}: {len(latencies)} 次測量, 平均 {avg_latency:.2f}, 標準差 {std_latency:.2f}')

print(f'[Server] 成功處理 {processed_pairs} 個core pair')
print(f'[Server] 平均latency已寫入: {output_file}')
"
    
    # 檢查平均latency檔案是否成功產生
    AVERAGE_FILE="$BASE_PATH/RON_TSP/tsp_order/output.csv"
    if [ -f "$AVERAGE_FILE" ]; then
        echo "[Server] 執行 TSP 計算..."
        
        # 執行 TSP 計算
        python3 ~/toTSP.py 
        
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
