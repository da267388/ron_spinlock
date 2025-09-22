#!/bin/bash
# 用來儲存 client 傳來的 CSV 檔案，並在有足夠資料時執行 TSP 計算
BASE_PATH=$HOME
CPU_MODEL="$1"
CSV_PATH="$2"
REQUIRED_MEASUREMENTS=${3:-5}  # 預設需要5次測量

RESULT_DIR=$BASE_PATH/RON_TSP/tsp_order
MEASUREMENTS_DIR=$BASE_PATH/RON_TSP/measurements
mkdir -p "$RESULT_DIR"
mkdir -p "$MEASUREMENTS_DIR"

SAFE_MODEL=$(echo "$CPU_MODEL" | tr ' ' '_' | tr -d '()')
MEASUREMENT_FOLDER="$MEASUREMENTS_DIR/$SAFE_MODEL"
mkdir -p "$MEASUREMENT_FOLDER"

# 存儲這次的測量結果到measurements目錄
FILENAME=$(basename "$CSV_PATH")
DEST_FILE="$MEASUREMENT_FOLDER/$FILENAME"
mv "$CSV_PATH" "$DEST_FILE"
echo "[Server] 已存檔測量結果：$DEST_FILE"

# 等待檔案完全寫入
while [ ! -f "$DEST_FILE" ]; do
    sleep 1
done

# 計算當前測量次數
MEASUREMENT_COUNT=$(ls "$MEASUREMENT_FOLDER"/output_*.csv 2>/dev/null | wc -l)
echo "[Server] 當前測量次數: $MEASUREMENT_COUNT, 需要次數: $REQUIRED_MEASUREMENTS"

if [ $MEASUREMENT_COUNT -ge $REQUIRED_MEASUREMENTS ]; then
    echo "[Server] 測量次數足夠，開始計算平均latency並執行TSP計算..."
    
    # 使用Python腳本來計算所有測量的平均值
    python3 -c "
import csv
import os
from collections import defaultdict
import numpy as np

measurement_folder = '$MEASUREMENT_FOLDER'
base_path = '$BASE_PATH'

# 讀取所有測量檔案
all_latencies = defaultdict(list)
csv_files = [f for f in os.listdir(measurement_folder) if f.startswith('output_') and f.endswith('.csv')]
csv_files.sort()  # 確保順序一致

print(f'[Server] 找到 {len(csv_files)} 個測量檔案')

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

# 計算平均latency
output_file = os.path.join(base_path, 'RON_TSP', 'tsp_order', 'output.csv')
with open(output_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['core1', 'core2', 'latency'])
    
    for (core1, core2), latencies in all_latencies.items():
        if len(latencies) >= $REQUIRED_MEASUREMENTS:
            avg_latency = np.mean(latencies)
            writer.writerow([core1, core2, avg_latency])
        else:
            print(f'[Server] 警告: core {core1}-{core2} 只有 {len(latencies)} 次測量')

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
            mv "$TSP_FILE" "$FINAL_TSP_FILE"
            echo "[Server] TSP 結果已產生：$FINAL_TSP_FILE"
            echo "[Server] 基於 $MEASUREMENT_COUNT 次測量的平均結果"
            
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
    echo "[Server] 測量次數不足，需要更多測量資料"
    echo "[Server] 目前有 $MEASUREMENT_COUNT 次測量，需要 $REQUIRED_MEASUREMENTS 次"
fi
