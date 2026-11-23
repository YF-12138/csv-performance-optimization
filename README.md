# 大规模 CSV 交易流水统计的性能分析与优化

本项目模拟批量订单报表任务，从 CSV 中筛选已完成订单，按城市统计订单数和交易总额。金额以整数分保存，三种实现的结果可以逐项精确比较。

## 优化方案

1. **串行基线**：使用 Python 标准库 `csv.DictReader` 逐行筛选并累加。
2. **应用实现层**：使用 pandas，每批读取 25 万行，按列筛选后用 `groupby` 聚合。
3. **运行时并行层**：将输入分成 8 个文件，由 4 个工作进程复用同一套 pandas 汇总逻辑，最后合并各分片结果。

## 实验结果

三种方法读取同一组分片，各运行 3 轮。下表为耗时中位数，单位为秒。

| 数据规模 | CSV 串行 | pandas 串行 | pandas 4 进程 |
| --- | ---: | ---: | ---: |
| 10 万行 | 0.213353 | 0.050375 | 1.173043 |
| 1000 万行 | 21.277436 | 3.573597 | 2.168638 |

三种实现的逐城市汇总结果一致。1000 万行已有分片时，pandas 串行较基线加速 5.95 倍，4 进程较 pandas 串行再加速 1.65 倍。10 万行时 pandas 串行最快。

分片准备单独计时，进程池启动与关闭计入多进程耗时。1000 万行原始单文件直接使用 pandas 串行的中位耗时为 3.385187 秒。若每次都重新分片，按实测分片准备时间与并行处理中位数相加，估计共需约 23.78 秒。

## 复现实验

实验环境为 Windows 11、Python 3.12.4 和 pandas 3.1.1。以下命令在仓库根目录的 PowerShell 中执行。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pandas==3.1.1
.\.venv\Scripts\python.exe create_csv.py
```

`create_csv.py` 使用固定随机种子 42，默认生成 `orders_10m.csv`。生成 10 万行数据时，将脚本中的 `ROW_COUNT` 临时改为 `100_000`，并把输出文件名改为 `orders_100k.csv`，再运行一次。两份 CSV 均放在仓库根目录。同名输出会被覆盖，1000 万行分片测试需要额外预留约 420 MiB 磁盘空间。

```powershell
.\.venv\Scripts\python.exe test_100k.py
.\.venv\Scripts\python.exe benchmark_orders.py orders_10m.csv --repeats 3 --workers 4
.\.venv\Scripts\python.exe test_10m_single.py
```

实验脚本输出逐轮耗时、中位数和各城市汇总结果。分片测试会自动比较三种实现的输出，并在结束后清理临时分片。
