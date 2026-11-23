import csv
from collections import defaultdict
from pathlib import Path
from time import perf_counter


INPUT_FILE = Path(__file__).with_name("orders_100k.csv")


def summarize_orders(input_file):
    order_counts = defaultdict(int)
    amount_totals = defaultdict(int)

    with input_file.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row["status"] == "completed":
                city = row["city"]
                order_counts[city] += 1
                amount_totals[city] += int(row["amount_cents"])

    return [
        (city, order_counts[city], amount_totals[city])
        for city in sorted(order_counts)
    ]


def main():
    start = perf_counter()
    summary = summarize_orders(INPUT_FILE)
    elapsed = perf_counter() - start

    print("城市\t已完成订单数\t交易总额（分）")
    for city, count, amount in summary:
        print(f"{city}\t{count:,}\t{amount:,}")
    print(f"串行基线耗时：{elapsed:.6f} 秒")


if __name__ == "__main__":
    main()
