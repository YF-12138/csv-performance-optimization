import argparse
import csv
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from time import perf_counter


def split_csv(source, directory):
    paths = [directory / f"orders_{index}.csv" for index in range(8)]
    with ExitStack() as stack:
        file = stack.enter_context(source.open(encoding="utf-8", newline=""))
        reader = csv.reader(file)
        header = next(reader)
        writers = [
            csv.writer(stack.enter_context(path.open("w", encoding="utf-8", newline="")))
            for path in paths
        ]
        for writer in writers:
            writer.writerow(header)
        for index, row in enumerate(reader):
            writers[index % len(writers)].writerow(row)
    return paths


def merge_summaries(summaries):
    counts = Counter()
    amounts = Counter()
    for summary in summaries:
        for city, count, amount in summary:
            counts[city] += count
            amounts[city] += amount
    return [(city, counts[city], amounts[city]) for city in sorted(counts)]


def csv_summary(path):
    counts = Counter()
    amounts = Counter()
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            if row["status"] == "completed":
                city = row["city"]
                counts[city] += 1
                amounts[city] += int(row["amount_cents"])
    return [(city, counts[city], amounts[city]) for city in counts]


def pandas_summary(path):
    import pandas as pd

    partials = []
    with pd.read_csv(
        path,
        usecols=["city", "status", "amount_cents"],
        dtype={"amount_cents": "int64"},
        chunksize=250_000,
    ) as chunks:
        for chunk in chunks:
            completed = chunk.loc[chunk["status"].eq("completed")]
            summary = completed.groupby("city", sort=False)["amount_cents"].agg(["size", "sum"])
            partials.append(list(summary.itertuples(name=None)))
    return merge_summaries(partials)


def parallel_summary(paths, workers):
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return merge_summaries(pool.map(pandas_summary, paths))


def main():
    parser = argparse.ArgumentParser(description="比较三种 CSV 订单汇总方式")
    parser.add_argument("input", type=Path, nargs="?", default=Path(__file__).with_name("orders_10m.csv"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.repeats < 1 or not 1 <= args.workers <= 8:
        parser.error("--repeats 至少为 1，--workers 必须在 1 到 8 之间")
    if not args.input.is_file():
        parser.error(f"找不到输入 CSV：{args.input}")

    import pandas  # 在主进程计时前加载依赖

    with TemporaryDirectory(prefix="order_benchmark_", dir=args.input.resolve().parent) as directory:
        start = perf_counter()
        paths = split_csv(args.input, Path(directory))
        print(f"8 个分片准备耗时：{perf_counter() - start:.6f} 秒", flush=True)

        methods = [
            ("CSV 串行基线", lambda: merge_summaries(map(csv_summary, paths))),
            ("pandas 串行", lambda: merge_summaries(map(pandas_summary, paths))),
            (f"pandas 多进程（{args.workers} 个）", lambda: parallel_summary(paths, args.workers)),
        ]
        timings = {name: [] for name, _ in methods}
        expected = None
        for run in range(args.repeats):
            offset = run % len(methods)
            for name, measure in methods[offset:] + methods[:offset]:
                start = perf_counter()
                result = measure()
                elapsed = perf_counter() - start
                if expected is None:
                    expected = result
                if result != expected:
                    raise RuntimeError(f"{name} 的汇总结果与基线不一致")
                timings[name].append(elapsed)
                print(f"第 {run + 1} 轮 | {name} | {elapsed:.6f} 秒", flush=True)

        baseline = median(timings[methods[0][0]])
        print("\n各版本中位数")
        for name, samples in timings.items():
            elapsed = median(samples)
            print(f"{name}：{elapsed:.6f} 秒，相对基线 {baseline / elapsed:.2f} 倍")

        print("\n城市\t已完成订单数\t交易总额（分）")
        for city, count, amount in expected:
            print(f"{city}\t{count:,}\t{amount:,}")
        print("所有汇总结果一致。")


if __name__ == "__main__":
    main()
