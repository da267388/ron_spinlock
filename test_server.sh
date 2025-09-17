#!/bin/bash
# 查詢是否已經有某 CPU 的 TSP 結果
BASE_PATH=$HOME
CPU_MODEL="$1"

cd $HOME
if [ ! -d "RON_TSP" ]; then
    mkdir RON_TSP
fi
cd ./RON_TSP
if [ ! -d "tsp_order" ]; then
    mkdir tsp_order
fi
if [ ! -d "tmp" ]; then
    mkdir tmp
fi
cd $HOME

RESULT_DIR=$BASE_PATH/RON_TSP/tsp_order
SAFE_MODEL=$(echo "$CPU_MODEL" | tr ' ' '_' | tr -d '()')
TSP_FILE="$RESULT_DIR/$SAFE_MODEL/tsp_order.csv"

if [ -d "./RON_TSP/tsp_order/$SAFE_MODEL" ]; then
    echo "FOUND"
    cd ./RON_TSP/tsp_order/$SAEE_MODEL
    # 回傳檔案內容（轉成單一行字串）
    #tr '\n' ' ' < "$TSP_FILE"
    paste -sd' ' "$TSP_FILE"
    cd $HOME

else
    cd ./RON_TSP/tsp_order
    echo "NOT_FOUND"
    mkdir $SAFE_MODEL
    cd $HOME
fi

