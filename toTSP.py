import numpy as np
import csv

# --- Step 1: 讀取下三角矩陣並補全對稱矩陣 ---
def read_lower_triangular_csv(file_path):
    with open(file_path, 'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    n = len(lines)  # 矩陣大小就是行數
    matrix = np.zeros((n, n))
    
    # 逐行解析下三角矩陣
    for i in range(n):
        values = [x.strip() for x in lines[i].split(',')]
        # 填入這一行的數據（只考慮下三角部分）
        for j in range(i):  # j < i，下三角部分
            if j < len(values) and values[j]:  # 確保有數值
                val = float(values[j])
                matrix[i][j] = val
                matrix[j][i] = val  # 對稱填入
    
    return matrix

# --- Step 2: Nearest Neighbor TSP 啟發式解法 ---
def tsp_nearest_neighbor(matrix, start=0):
    n = len(matrix)
    visited = [False] * n
    path = [start]
    visited[start] = True
    cost = 0
    current = start
    
    # 訪問所有其他節點
    for _ in range(n - 1):
        next_node = None
        min_latency = float('inf')
        for i in range(n):
            if not visited[i] and matrix[current][i] < min_latency:
                min_latency = matrix[current][i]
                next_node = i
        if next_node is None:
            break
        path.append(next_node)
        visited[next_node] = True
        cost += min_latency
        current = next_node
    
    # 回到起點完成TSP循環
    cost += matrix[current][start]
    path.append(start)
    
    return path, cost

# --- Step 3: 將路徑轉換為執行順序 ---
def path_to_order(path):
    """
    將TSP路徑轉換為執行順序
    path: [0,3,1,2,0] -> order: [0,2,3,1]
    意思是: core 0 第0個執行, core 1 第2個執行, core 2 第3個執行, core 3 第1個執行
    """
    n = len(path) - 1  # 去掉最後回到起點的節點
    order = [0] * n
    for position, core_id in enumerate(path[:-1]):  # 排除最後的起點
        order[core_id] = position
    return order

# --- Step 4: 輸出為一列 CSV ---
def write_tsp_order_to_csv(order, output_file):
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(order)

# --- Step 5: 主程式 ---
if __name__ == "__main__":
    input_file = "./core-to-core-latency/output.csv"          # ← 輸入檔名
    output_file = "tsp_order.csv"       # ← 輸出檔名
    
    matrix = read_lower_triangular_csv(input_file)
    path, cost = tsp_nearest_neighbor(matrix)
    order = path_to_order(path)
    write_tsp_order_to_csv(order, output_file)
    
    print("TSP order 已輸出至:", output_file)
    print("TSP Path:", path[:-1])
    print("Execution Order:", order)
    print(f"Total Latency (approx): {cost:.2f} ns")
    
    # 驗證結果
    print("\n--- 驗證 ---")
    for core_id, execution_order in enumerate(order):
        print(f"Core {core_id} 在第 {execution_order} 個位置執行")
