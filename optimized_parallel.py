import csv
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from optimized_pandas import INPUT_FILE, summarize_orders


SHARD_COUNT = 8
WORKER_COUNTS = (1, 2, 4)


def split_csv(input_file, directory):
    paths = [directory / f"orders_{index}.csv" for index in range(SHARD_COUNT)]
    with ExitStack() as stack:
        source = stack.enter_context(input_file.open(encoding="utf-8", newline=""))
        reader = csv.reader(source)
        header = next(reader)
        writers = [
            csv.writer(stack.enter_context(path.open("w", encoding="utf-8", newline="")))
            for path in paths
        ]
        for writer in writers:
            writer.writerow(header)
        for index, row in enumerate(reader):
            writers[index % SHARD_COUNT].writerow(row)
    return paths


def merge_summaries(summaries):
    counts = Counter()
    amounts = Counter()
    for summary in summaries:
        for city, count, amount in summary:
            counts[city] += count
            amounts[city] += amount
    return [(city, counts[city], amounts[city]) for city in sorted(counts)]


def main():
    expected = summarize_orders(INPUT_FILE)
    with TemporaryDirectory(prefix="order_shards_") as directory:
        start = perf_counter()
        paths = split_csv(INPUT_FILE, Path(directory))
        print(f"CSV 分片准备耗时：{perf_counter() - start:.6f} 秒")

        start = perf_counter()
        result = merge_summaries(map(summarize_orders, paths))
        serial_elapsed = perf_counter() - start
        if result != expected:
            raise RuntimeError("分片串行汇总与原始 CSV 的汇总不一致")
        print(f"同一组分片串行耗时：{serial_elapsed:.6f} 秒")

        for workers in WORKER_COUNTS:
            start = perf_counter()
            with ProcessPoolExecutor(max_workers=workers) as pool:
                result = merge_summaries(pool.map(summarize_orders, paths))
            elapsed = perf_counter() - start
            if result != expected:
                raise RuntimeError(f"{workers} 个工作进程的汇总结果不一致")
            print(f"{workers} 个工作进程：{elapsed:.6f} 秒，分片串行耗时 / 并行耗时 = {serial_elapsed / elapsed:.2f} 倍")

    print("所有汇总结果一致。")


if __name__ == "__main__":
    main()
