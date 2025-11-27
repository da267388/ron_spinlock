#!/usr/bin/env python3
import csv
import math
import statistics
import sys
from scipy.stats import gmean  # 需要 scipy

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <csv_file>")
        sys.exit(1)

    csv_file = sys.argv[1]
    avg_waits = []

    # 讀取 CSV
    with open(csv_file, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                avg_waits.append(float(row["avg_wait_ns"]))
            except KeyError:
                print("CSV 欄位缺少 avg_wait_ns")
                sys.exit(1)
            except ValueError:
                print(f"無法轉換數值: {row['avg_wait_ns']}")
                sys.exit(1)

    if not avg_waits:
        print("沒有讀取到任何 avg_wait_ns 數值")
        sys.exit(1)

    # 算術平均
    arithmetic_mean = sum(avg_waits) / len(avg_waits)

    # 幾何平均
    geometric_mean_value = gmean(avg_waits)

    # 公平性指標
    std_dev = statistics.stdev(avg_waits)
    max_min_ratio = max(avg_waits) / min(avg_waits)

    # 輸出結果
    print("===== TSP Spinlock Benchmark Statistics =====")
    print(f"Number of threads: {len(avg_waits)}")
    print(f"Arithmetic mean of avg_wait_ns: {arithmetic_mean:.2f} ns")
    print(f"Geometric mean of avg_wait_ns: {geometric_mean_value:.2f} ns")
    print(f"Standard deviation: {std_dev:.2f} ns")
    print(f"Max/Min ratio: {max_min_ratio:.2f}")
    print("=============================================")

if __name__ == "__main__":
    main()
