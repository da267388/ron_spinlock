import csv
import numpy as np
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

def read_distance_matrix_from_csv(csv_file):
    """
    從 CSV 檔案讀取距離矩陣
    
    參數:
        csv_file: CSV 檔案路徑
    
    返回:
        distance_matrix: 距離矩陣 (list of lists)
    """
    distance_matrix = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        # 跳過標題行（如果有的話）
        first_row = next(reader)
        
        # 檢查第一行是否為數字
        try:
            row_data = [float(x) for x in first_row]
            distance_matrix.append(row_data)
        except ValueError:
            # 第一行是標題，跳過
            pass
        
        # 讀取剩餘的行
        for row in reader:
            # 過濾空行
            if row:
                # 轉換為浮點數（如果是整數也可以用 int）
                row_data = [float(x) for x in row if x.strip()]
                if row_data:
                    distance_matrix.append(row_data)
    
    return distance_matrix

def validate_symmetric_matrix(matrix):
    """
    驗證矩陣是否為對稱矩陣
    
    參數:
        matrix: 距離矩陣
    
    返回:
        bool: 是否為對稱矩陣
    """
    n = len(matrix)
    
    # 檢查是否為方陣
    for row in matrix:
        if len(row) != n:
            return False
    
    # 檢查是否對稱
    for i in range(n):
        for j in range(i+1, n):
            if abs(matrix[i][j] - matrix[j][i]) > 1e-6:  # 允許小誤差
                return False
    
    return True

def solve_tsp(distance_matrix, start_node=0, time_limit=30):
    """
    解決 TSP 問題
    
    參數:
        distance_matrix: 對稱的距離矩陣
        start_node: 起始節點索引
        time_limit: 求解時間限制（秒）
    
    返回:
        route: 經過的點的順序列表
        total_distance: 總距離
    """
    # 建立資料
    data = {}
    data['distance_matrix'] = distance_matrix
    data['num_vehicles'] = 1
    data['depot'] = start_node
    
    # 建立 routing index manager
    manager = pywrapcp.RoutingIndexManager(
        len(data['distance_matrix']),
        data['num_vehicles'],
        data['depot']
    )
    
    # 建立 Routing Model
    routing = pywrapcp.RoutingModel(manager)
    
    # 定義距離回調函數
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return int(data['distance_matrix'][from_node][to_node])
    
    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
    
    # 設定搜尋參數
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = time_limit
    
    # 求解
    solution = routing.SolveWithParameters(search_parameters)
    
    if solution:
        # 提取路線
        route = []
        total_distance = 0
        index = routing.Start(0)
        
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            route.append(node)
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            total_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
        
        # 加入最後回到起點的節點
        route.append(manager.IndexToNode(index))
        
        return route, total_distance
    else:
        return None, None


def main():
    """主程式"""
    # CSV 檔案路徑
    csv_file = 'test.csv'
    
    try:
        # 讀取距離矩陣
        print(f"正在讀取 CSV 檔案: {csv_file}")
        distance_matrix = read_distance_matrix_from_csv(csv_file)
        
        print(f"矩陣大小: {len(distance_matrix)} x {len(distance_matrix[0])}")
        
        # 驗證是否為對稱矩陣
        if not validate_symmetric_matrix(distance_matrix):
            print("警告: 輸入矩陣不是對稱矩陣！")
            response = input("是否繼續執行？ (y/n): ")
            if response.lower() != 'y':
                return
        else:
            print("✓ 矩陣驗證通過（對稱矩陣）")
        
        # 求解 TSP
        print("\n正在求解 TSP 問題...")
        route, total_distance = solve_tsp(distance_matrix, start_node=0)
        
        if route:
            print("\n=== 結果 ===")
            print(f"經過的點的順序: {route}")
            print(f"不含返回起點: {route[:-1]}")
            print(f"總距離: {total_distance}")
            
            # 詳細路徑
            print("\n=== 詳細路徑 ===")
            for i in range(len(route) - 1):
                from_node = route[i]
                to_node = route[i + 1]
                dist = distance_matrix[from_node][to_node]
                print(f"節點 {from_node} -> 節點 {to_node}: 距離 {dist}")
        else:
            print("找不到解決方案！")
    
    except FileNotFoundError:
        print(f"錯誤: 找不到檔案 '{csv_file}'")
        print("\n請確保 CSV 檔案格式如下:")
        print("0,10,15,20")
        print("10,0,35,25")
        print("15,35,0,30")
        print("20,25,30,0")
    except Exception as e:
        print(f"錯誤: {e}")


if __name__ == '__main__':
    main()
