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
    
    # 計算平均值（同位置取平均）
    print(f'\n計算 {len(matrices)} 個矩陣的同位置平均值...')
    avg_matrix = np.mean(matrices, axis=0)
    
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
        
        print(f'✅ 對稱矩陣CSV已儲存: {output_file}')
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
    
    # 檢查對稱性
    is_symmetric = np.allclose(matrix, matrix.T)
    print(f'  對稱性檢查: {"✓ 對稱" if is_symmetric else "✗ 不對稱"}')

def main():
    if len(sys.argv) < 3:
        print('使用方式: python3 cal_avg.py <measurement_folder> <output_file> [measurement_count]')
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

        print_matrix_info(symmetric_matrix)
        
        
        print(f'\n🎉 處理完成！')
        print(f'輸出檔案: {output_file}')
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
