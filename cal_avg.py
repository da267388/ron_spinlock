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
    
    # 計算變異係數
    if len(matrices) > 1:
        std_matrix = np.std(matrices, axis=0)
        
        # 找出高變異的位置
        high_variance_count = 0
        for i in range(avg_matrix.shape[0]):
            for j in range(avg_matrix.shape[1]):
                if avg_matrix[i][j] > 0:
                    cv = (std_matrix[i][j] / avg_matrix[i][j]) * 100
                    if cv > 5:
                        high_variance_count += 1
                        if high_variance_count <= 5:  # 只顯示前5個
                            print(f'  高變異: ({i},{j}): 平均={avg_matrix[i][j]:.2f}, '
                                  f'標準差={std_matrix[i][j]:.2f}, CV={cv:.1f}%')
        
        if high_variance_count > 5:
            print(f'  ... 還有 {high_variance_count - 5} 個高變異位置')
        
        # 整體變異統計
        non_zero_mask = avg_matrix > 0
        if np.any(non_zero_mask):
            cv_values = (std_matrix[non_zero_mask] / avg_matrix[non_zero_mask]) * 100
            print(f'\n變異係數統計:')
            print(f'  平均: {np.mean(cv_values):.2f}%')
            print(f'  最大: {np.max(cv_values):.2f}%')
            print(f'  最小: {np.min(cv_values):.2f}%')
    
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
    
    # 統計非零值（排除對角線）
    non_diagonal = []
    for i in range(matrix_size):
        for j in range(matrix_size):
            if i != j and matrix[i][j] > 0:
                non_diagonal.append(matrix[i][j])
    
    if non_diagonal:
        print(f'\n距離統計 (非對角線):')
        print(f'  資料點數: {len(non_diagonal)}')
        print(f'  最小: {np.min(non_diagonal):.2f}')
        print(f'  最大: {np.max(non_diagonal):.2f}')
        print(f'  平均: {np.mean(non_diagonal):.2f}')
        print(f'  中位數: {np.median(non_diagonal):.2f}')
    
    # 檢查對稱性
    is_symmetric = np.allclose(matrix, matrix.T)
    print(f'  對稱性檢查: {"✓ 對稱" if is_symmetric else "✗ 不對稱"}')

def main():
    if len(sys.argv) < 3:
        print('使用方式: python3 calculate_average.py <measurement_folder> <output_file> [measurement_count]')
        print('\n範例:')
        print('  python3 calculate_average.py ~/RON_TSP/measurements/CPU_MODEL output.csv')
        print('  python3 calculate_average.py ~/RON_TSP/measurements/CPU_MODEL output.csv 5')
        print('\n輸入格式: 下三角矩陣CSV（無行列標題）')
        print('  0,0,0')
        print('  10.5,0,0')
        print('  15.3,20.1,0')
        print('\n輸出格式: 完整對稱矩陣CSV（無行列標題）')
        print('  0,10.5,15.3')
        print('  10.5,0,20.1')
        print('  15.3,20.1,0')
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
        
        # 顯示檔案預覽
        print('\n=== 檔案預覽 (前5行) ===')
        try:
            with open(output_file, 'r') as f:
                for i, line in enumerate(f):
                    if i < 5:
                        parts = line.strip().split(',')
                        if len(parts) > 10:
                            display = ','.join(parts[:10]) + ',...'
                        else:
                            display = line.strip()
                        print(f'  {display}')
                    else:
                        print(f'  ...')
                        break
        except:
            pass
        
        print(f'\n🎉 處理完成！')
        print(f'輸出檔案: {output_file}')
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
