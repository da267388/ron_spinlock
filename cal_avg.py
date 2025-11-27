#!/usr/bin/env python3
"""
計算多次core-to-core latency測量的平均值
輸入：下三角矩陣CSV（無行列標題）
輸出：完整對稱矩陣CSV（無行列標題）
使用方式: python3 calculate_average.py <measurement_folder> <output_file> [measurement_count]
"""

import csv
import os
import sys
import numpy as np
from pathlib import Path

def filter_outliers(values, trim_percent=7.5):
    """
    過濾極值（異常值）- 使用百分位數截尾平均法
    
    參數:
        values: 數值列表
        trim_percent: 要過濾的百分比（總共），預設7.5%
                     會從兩端各過濾 trim_percent/2
                     例如 7.5% 表示過濾最低3.75%和最高3.75%
    
    返回:
        過濾後的數值列表
    """
    if len(values) <= 2:
        # 數量太少，不過濾
        return values
    
    values_array = np.array(values)
    
    # 只考慮非零值
    non_zero_values = values_array[values_array > 0]
    if len(non_zero_values) <= 2:
        return values
    
    # 計算要過濾的百分位數
    lower_percentile = trim_percent / 2
    upper_percentile = 100 - (trim_percent / 2)
    
    # 計算界限
    lower_bound = np.percentile(non_zero_values, lower_percentile)
    upper_bound = np.percentile(non_zero_values, upper_percentile)
    
    # 過濾極值
    filtered = [v for v in values if v == 0 or (lower_bound <= v <= upper_bound)]
    
    # 如果過濾後沒有值了，返回原始值
    if not any(v > 0 for v in filtered):
        return values
    
    return filtered

def read_lower_triangle_csv(file_path):
    """
    讀取下三角矩陣格式的CSV檔案（無行列標題）
    預期格式:
    0,0,0
    10.5,0,0
    15.3,20.1,0
    
    返回: numpy 2D array
    """
    try:
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            data = []
            for line in reader:
                row = []
                for value in line:
                    try:
                        row.append(float(value))
                    except ValueError:
                        row.append(0.0)
                data.append(row)
        
        if not data:
            print(f'[錯誤] 檔案為空: {file_path}')
            return None
        
        # 轉換為numpy矩陣
        matrix = np.array(data)
        return matrix
        
    except Exception as e:
        print(f'[錯誤] 讀取檔案失敗: {file_path} - {e}')
        return None

def calculate_average_matrices(measurement_folder, measurement_count):
    """
    計算多個下三角矩陣的同位置平均值
    使用極值過濾：排除過高和過低的極值後再計算平均
    返回: numpy 2D array (平均後的下三角矩陣)
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
    
    # 收集所有矩陣
    matrices = []
    
    for i, csv_file in enumerate(files_to_use, 1):
        file_path = os.path.join(measurement_folder, csv_file)
        print(f'[{i}/{len(files_to_use)}] 讀取: {csv_file}')
        
        matrix = read_lower_triangle_csv(file_path)
        if matrix is None:
            print(f'  跳過此檔案')
            continue
        
        matrices.append(matrix)
        print(f'  矩陣大小: {matrix.shape}')
    
    if not matrices:
        print('[錯誤] 沒有成功讀取任何測量資料')
        return None
    
    # 確保所有矩陣大小相同
    shapes = [m.shape for m in matrices]
    if len(set(shapes)) > 1:
        print(f'[錯誤] 矩陣大小不一致: {shapes}')
        return None
    
    # 計算平均值（同位置取平均，使用極值過濾）
    # 過濾設定：總共過濾約7.5%的極值（最高3.75% + 最低3.75%）
    TRIM_PERCENT = 7.5  # 可調整為 5.0 到 10.0 之間
    
    print(f'\n計算 {len(matrices)} 個矩陣的同位置平均值')
    print(f'極值過濾設定: 過濾最高 {TRIM_PERCENT/2:.1f}% 和最低 {TRIM_PERCENT/2:.1f}% (總共 {TRIM_PERCENT:.1f}%)')
    
    matrix_size = matrices[0].shape[0]
    avg_matrix = np.zeros((matrix_size, matrix_size))
    
    outliers_filtered = 0
    total_positions = 0
    total_values = 0
    
    # 對每個位置單獨計算
    for i in range(matrix_size):
        for j in range(matrix_size):
            # 收集該位置的所有值
            values = [m[i][j] for m in matrices]
            
            # 只對非零值進行極值過濾
            if any(v > 0 for v in values):
                total_positions += 1
                total_values += len(values)
                
                filtered_values = filter_outliers(values, trim_percent=TRIM_PERCENT)
                
                if len(filtered_values) < len(values):
                    outliers_filtered += (len(values) - len(filtered_values))
                
                # 計算過濾後的平均值
                if filtered_values:
                    avg_matrix[i][j] = np.mean(filtered_values)
                else:
                    # 如果所有值都被過濾掉，使用原始平均值
                    avg_matrix[i][j] = np.mean(values)
            else:
                avg_matrix[i][j] = 0
    
    print(f'\n極值過濾結果:')
    #print(f'  處理的位置數: {total_positions}')
    #print(f'  總測量值數: {total_values}')
    #print(f'  過濾的極值數: {outliers_filtered}')
    if total_values > 0:
        actual_percent = (outliers_filtered / total_values) * 100
        print(f'  實際過濾比例: {actual_percent:.2f}%')
        #print(f'  保留的值數: {total_values - outliers_filtered}')
    
    return avg_matrix

def make_symmetric(lower_triangle_matrix):
    """
    將下三角矩陣轉換為完整對稱矩陣
    輸入: numpy array (下三角有資料)
    輸出: numpy array (完整對稱矩陣)
    """
    matrix_size = lower_triangle_matrix.shape[0]
    symmetric_matrix = np.copy(lower_triangle_matrix)
    
    # 利用對稱性填充上三角
    for i in range(matrix_size):
        for j in range(i + 1, matrix_size):
            # 上三角 = 下三角的轉置
            symmetric_matrix[i][j] = symmetric_matrix[j][i]
    
    # 確保對角線為0
    for i in range(matrix_size):
        symmetric_matrix[i][i] = 0
    
    return symmetric_matrix

def write_matrix_csv(matrix, output_file):
    """
    將矩陣寫入CSV檔案（無行列標題）
    格式:
    0,10.5,15.3
    10.5,0,20.1
    15.3,20.1,0
    """
    try:
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            
            for row in matrix:
                writer.writerow(row)
        
        print(f'對稱矩陣CSV已儲存: {output_file}')
        return True
    except Exception as e:
        print(f'[錯誤] 寫入檔案失敗: {e}')
        return False

def print_matrix_info(matrix):
    """
    打印矩陣統計資訊
    """
    matrix_size = matrix.shape[0]
    
    print(f'\n=== 矩陣資訊 ===')
    print(f'矩陣大小: {matrix_size} x {matrix_size}')
    
    # 統計非零值（排除對角線）
    non_diagonal = []
    for i in range(matrix_size):
        for j in range(matrix_size):
            if i != j and matrix[i][j] > 0:
                non_diagonal.append(matrix[i][j])
    
    if non_diagonal:
        #print(f'\n距離統計 (非對角線):')
        #print(f'  資料點數: {len(non_diagonal)}')
        #print(f'  最小: {np.min(non_diagonal):.2f}')
        #print(f'  最大: {np.max(non_diagonal):.2f}')
        #print(f'  平均: {np.mean(non_diagonal):.2f}')
        #print(f'  中位數: {np.median(non_diagonal):.2f}')
    
    # 檢查對稱性
    is_symmetric = np.allclose(matrix, matrix.T)
    print(f'  對稱性檢查: {"對稱" if is_symmetric else "✗ 不對稱"}')

def main():
    if len(sys.argv) < 3:
        print('使用方式: python3 calculate_average.py <measurement_folder> <output_file> [measurement_count]')
        print('\n範例:')
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
    else:
        print(f'使用測量次數: 全部')
    print()
    
    # 檢查輸入目錄
    if not os.path.exists(measurement_folder):
        print(f'[錯誤] 目錄不存在: {measurement_folder}')
        sys.exit(1)
    
    # 步驟1: 讀取並計算平均值
    print('步驟1: 讀取下三角矩陣並計算同位置平均值...')
    avg_lower_triangle = calculate_average_matrices(measurement_folder, measurement_count)
    if avg_lower_triangle is None:
        sys.exit(1)
    
    # 步驟2: 建立對稱矩陣
    print('\n步驟2: 建立完整對稱矩陣...')
    symmetric_matrix = make_symmetric(avg_lower_triangle)
    print(f'對稱矩陣大小: {symmetric_matrix.shape[0]} x {symmetric_matrix.shape[1]}')
    
    # 步驟3: 寫入CSV
    print('\n步驟3: 寫入CSV檔案...')
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    if write_matrix_csv(symmetric_matrix, output_file):
        # 打印統計資訊
        print_matrix_info(symmetric_matrix)
        print(f'\n處理完成！')
        print(f'輸出檔案: {output_file}')
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
