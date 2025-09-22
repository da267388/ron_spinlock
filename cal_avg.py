#!/usr/bin/env python3
"""
計算多次core-to-core latency測量的平均值
使用方式: python3 calculate_average.py <measurements_folder> <output_file> <required_measurements>
"""

import csv
import os
import sys
from collections import defaultdict
import numpy as np

def calculate_average_latencies(measurement_folder, output_file, required_measurements=5):
    """
    計算多次測量的平均latency
    
    Args:
        measurement_folder: 包含多個測量CSV檔案的目錄
        output_file: 輸出的平均latency CSV檔案
        required_measurements: 需要的最少測量次數
    """
    
    # 讀取所有測量檔案
    all_latencies = defaultdict(list)
    csv_files = [f for f in os.listdir(measurement_folder) 
                if f.startswith('output_') and f.endswith('.csv')]
    csv_files.sort()  # 確保順序一致
    
    print(f'找到 {len(csv_files)} 個測量檔案')
    
    for csv_file in csv_files:
        file_path = os.path.join(measurement_folder, csv_file)
        print(f'處理檔案: {csv_file}')
        
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
            print(f'讀取檔案 {csv_file} 時出錯: {e}')
            continue
    
    if not all_latencies:
        print('錯誤: 沒有找到有效的測量資料')
        return False
    
    # 檢查測量次數
    min_measurements = min(len(latencies) for latencies in all_latencies.values())
    max_measurements = max(len(latencies) for latencies in all_latencies.values())
    
    print(f'測量次數範圍: {min_measurements} - {max_measurements}')
    print(f'需要的最少測量次數: {required_measurements}')
    
    if min_measurements < required_measurements:
        print(f'警告: 某些core pair的測量次數不足 ({min_measurements} < {required_measurements})')
    
    # 計算並寫入平均latency
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['core1', 'core2', 'latency'])
        
        processed_pairs = 0
        for (core1, core2), latencies in sorted(all_latencies.items()):
            if len(latencies) >= required_measurements:
                avg_latency = np.mean(latencies)
                std_latency = np.std(latencies)
                writer.writerow([core1, core2, avg_latency])
                processed_pairs += 1
                
                # 輸出統計資訊（可選）
                if len(latencies) > required_measurements:
                    print(f'Core {core1}-{core2}: {len(latencies)} 次測量, '
                          f'平均 {avg_latency:.2f}, 標準差 {std_latency:.2f}')
            else:
                print(f'跳過 Core {core1}-{core2}: 只有 {len(latencies)} 次測量')
    
    print(f'成功處理 {processed_pairs} 個core pair')
    print(f'平均latency已寫入: {output_file}')
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('使用方式: python3 calculate_average.py <measurements_folder> <output_file> [required_measurements]')
        sys.exit(1)
    
    measurement_folder = sys.argv[1]
    output_file = sys.argv[2]
    required_measurements = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    if not os.path.exists(measurement_folder):
        print(f'錯誤: 目錄不存在 {measurement_folder}')
        sys.exit(1)
    
    success = calculate_average_latencies(measurement_folder, output_file, required_measurements)
    sys.exit(0 if success else 1)
