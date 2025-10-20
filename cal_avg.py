#!/usr/bin/env python3
"""
計算多次core-to-core latency測量的平均值，並轉換為OR-Tools TSP格式
使用方式: python3 calculate_average.py <measurement_folder> <output_file> [measurement_count]
"""

import csv
import os
import sys
import numpy as np
from collections import defaultdict
from pathlib import Path

def read_latency_csv(file_path):
    """
    讀取latency CSV檔案，返回字典格式
    格式: {(core1, core2): latency}
    """
    latencies = {}
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                core1 = int(row['core1'])
                core2 = int(row['core2'])
                latency = float(row['latency'])
                latencies[(core1, core2)] = latency
        return latencies
    except Exception as e:
        print(f'[錯誤] 讀取檔案 {file_path} 失敗: {e}')
        return None

def calculate_average_matrix(measurement_folder, measurement_count):
    """
    計算多個CSV檔案的同位置平均值，保持矩陣結構
    返回格式: {(core1, core2): avg_latency}
    """
    csv_files = sorted([f for f in os.listdir(measurement_folder) 
                       if f.startswith('output_') and f.endswith('.csv')])
    
    if not csv_files:
        print('[錯誤] 沒有找到測量檔案')
        return None
    
    print(f'找到 {len(csv_files)} 個測量檔案')
    
    # 決定使用多少個檔案
    if measurement_count is None:
        files_to_use = csv_files
    else:
        files_to_use = csv_files[:measurement_count]
    
    print(f'使用前 {len(files_to_use)} 個檔案進行平均')
    
    # 讀取所有檔案並收集同位置的資料
    all_measurements = defaultdict(list)  # {(core1, core2): [值1, 值2, ...]}
    
    for i, csv_file in enumerate(files_to_use, 1):
        file_path = os.path.join(measurement_folder, csv_file)
        print(f'[{i}/{len(files_to_use)}] 讀取: {csv_file}')
        
        latencies = read_latency_csv(file_path)
        if latencies is None:
            continue
        
        for (core1, core2), latency in latencies.items():
            all_measurements[(core1, core2)].append(latency)
    
    if not all_measurements:
        print('[錯誤] 沒有成功讀取任何測量資料')
        return None
    
    # 計算平均值
    average_latencies = {}
    for (core1, core2), values in all_measurements.items():
        avg = np.mean(values)
        std = np.std(values) if len(values) > 1 else 0
        average_latencies[(core1, core2)] = avg
        
        if std / avg * 100 > 5:  # 標準差 > 5%
            print(f'  高變異: Core ({core1},{core2}): 平均={avg:.2f}, 標準差={std:.2f}')
    
    return average_latencies

def matrix_to_or_tools_format(average_latencies):
    """
    將矩陣轉換為OR-Tools TSP格式的完整方陣
    下三角 + 對角線 + 上三角 (使用對稱性)
    返回: [(core1, core2, latency), ...]
    """
    # 找出所有core編號
    cores = set()
    for core1, core2 in average_latencies.keys():
        cores.add(core1)
        cores.add(core2)
    
    max_core = max(cores)
    print(f'Core編號範圍: 0 到 {max_core}')
    
    # 創建完整的方陣
    matrix = []
    
    for i in range(max_core + 1):
        for j in range(max_core + 1):
            if i == j:
                # 對角線：設為0（TSP中通常為0）
                latency = 0
            elif (i, j) in average_latencies:
                # 下三角或上三角已有資料
                latency = average_latencies[(i, j)]
            elif (j, i) in average_latencies:
                # 利用對稱性：如果有(j,i)則使用該值（假設是對稱的）
                latency = average_latencies[(j, i)]
            else:
                # 缺失資料（不應該出現）
                latency = 0
                print(f'[警告] 缺失資料: ({i},{j})')
            
            matrix.append((i, j, latency))
    
    return matrix

def write_or_tools_csv(matrix, output_file):
    """
    寫入OR-Tools格式的CSV檔案
    格式: from,to,distance
    """
    try:
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['from', 'to', 'distance'])
            
            for core1, core2, latency in matrix:
                writer.writerow([core1, core2, latency])
        
        print(f'\n✅ OR-Tools格式CSV已儲存: {output_file}')
        return True
    except Exception as e:
        print(f'[錯誤] 寫入檔案失敗: {e}')
        return False

def print_matrix_info(matrix, max_core):
    """
    打印矩陣資訊
    """
    print(f'\n=== 矩陣資訊 ===')
    print(f'矩陣大小: {max_core + 1} x {max_core + 1}')
    print(f'總資料點: {len(matrix)}')
    
    # 提取距離值（排除對角線）
    distances = [latency for _, _, latency in matrix if latency > 0]
    if distances:
        print(f'距離統計:')
        print(f'  最小: {min(distances):.2f}')
        print(f'  最大: {max(distances):.2f}')
        print(f'  平均: {np.mean(distances):.2f}')
        print(f'  中位數: {np.median(distances):.2f}')

def main():
    if len(sys.argv) < 3:
        print('使用方式: python3 calculate_average.py <measurement_folder> <output_file> [measurement_count]')
        print('範例:')
        print('  python3 calculate_average.py ~/RON_TSP/measurements/CPU_MODEL output.csv')
        print('  python3 calculate_average.py ~/RON_TSP/measurements/CPU_MODEL output.csv 5')
        sys.exit(1)
    
    measurement_folder = sys.argv[1]
    output_file = sys.argv[2]
    measurement_count = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    print('=== Core-to-Core Latency 平均值計算工具 ===')
    print(f'測量目錄: {measurement_folder}')
    print(f'輸出檔案: {output_file}')
    if measurement_count:
        print(f'使用測量次數: {measurement_count}')
    print()
    
    # 檢查輸入目錄
    if not os.path.exists(measurement_folder):
        print(f'[錯誤] 目錄不存在: {measurement_folder}')
        sys.exit(1)
    
    # 計算平均矩陣
    print('步驟1: 計算同位置平均值...')
    average_latencies = calculate_average_matrix(measurement_folder, measurement_count)
    if average_latencies is None:
        sys.exit(1)
    
    print(f'  成功計算 {len(average_latencies)} 個位置的平均值')
    
    # 轉換為OR-Tools格式
    print('\n步驟2: 轉換為OR-Tools格式...')
    matrix = matrix_to_or_tools_format(average_latencies)
    
    max_core = max([core1 for core1, _, _ in matrix])
    print(f'  轉換完成，矩陣大小: {max_core + 1} x {max_core + 1}')
    
    # 寫入檔案
    print('\n步驟3: 寫入輸出檔案...')
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    if write_or_tools_csv(matrix, output_file):
        # 打印矩陣資訊
        print_matrix_info(matrix, max_core)
        
        # 顯示前幾行
        print('\n=== 檔案預覽 ===')
        with open(output_file, 'r') as f:
            for i, line in enumerate(f):
                if i < 6:
                    print(f'  {line.strip()}')
                else:
                    print(f'  ...')
                    break
        
        print(f'\n🎉 處理完成！')
        print(f'輸出檔案: {output_file}')
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
