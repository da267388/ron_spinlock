#!/bin/bash
# 查詢是否已經有某 CPU 的 TSP 結果
CPU_MODEL="$1"

RESULT_DIR=~~/RON_TSP/tsp_order
SAFE_MODEL=$(echo "$CPU_MODEL" | tr ' ' '_' | tr -d '()')
TSP_FILE="$RESULT_DIR/${SAFE_MODEL}_tsp_order.csv"

if [ -f "$TSP_FILE" ]; then
    echo "FOUND"
    # 回傳檔案內容（轉成單一行字串）
    tr '\n' ' ' < "$TSP_FILE"
else
    echo "NOT_FOUND"
fi

