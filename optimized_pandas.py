from time import perf_counter

import pandas as pd

from baseline import INPUT_FILE


def summarize_orders(input_file):
    orders = pd.read_csv(
        input_file,
        usecols=["city", "amount_cents", "status"],
        dtype={"amount_cents": "int64"},
    )
    completed = orders.loc[orders["status"].eq("completed")]
    summary = completed.groupby("city", sort=True).agg(
        order_count=("amount_cents", "size"),
        amount_total=("amount_cents", "sum"),
    )
    return list(summary.itertuples(index=True, name=None))


def main():
    start = perf_counter()
    summary = summarize_orders(INPUT_FILE)
    elapsed = perf_counter() - start

    print("城市\t已完成订单数\t交易总额（分）")
    for city, count, amount in summary:
        print(f"{city}\t{count:,}\t{amount:,}")
    print(f"pandas 串行优化耗时：{elapsed:.6f} 秒")


if __name__ == "__main__":
    main()
