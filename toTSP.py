import numpy as np
import csv

# --- Step 1: 讀取下三角矩陣並補全對稱矩陣 ---
def read_lower_triangular_csv(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    data = []
    for line in lines:
        row = [float(x.strip()) for x in line.strip().split(',') if x.strip()]
        if row:
            data.append(row)

    n = len(data)
    matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(len(data[i])):
            matrix[i][j] = data[i][j]
            matrix[j][i] = data[i][j]
    return matrix

# --- Step 2: Nearest Neighbor TSP 啟發式解法 ---
def tsp_nearest_neighbor(matrix, start=0):
    n = len(matrix)
    visited = [False] * n
    path = [start]
    visited[start] = True
    cost = 0
    current = start

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

    return path, cost



# --- Step 3: 輸出為一列 CSV ---
def write_tsp_order_to_csv(order, output_file):
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(order)

# --- Step 4: 主程式 ---
if __name__ == "__main__":
    input_file = "./core-to-core-latency/output.csv"          # ← 輸入檔名
    output_file = "tsp_order.csv"       # ← 輸出檔名

    matrix = read_lower_triangular_csv(input_file)
    order, cost = tsp_nearest_neighbor(matrix)

    write_tsp_order_to_csv(order, output_file)

    print("TSP order 已輸出至:", output_file)
    print("Order:", order)
    print(f"Total Latency (approx): {cost:.2f} ns")

