import csv
import random
from datetime import date, timedelta
from pathlib import Path


ROW_COUNT = 10000000
OUTPUT_FILE = Path(__file__).resolve().with_name("orders_10m.csv")
CITIES = ["Shenzhen", "Hangzhou", "Chengdu", "Shanghai", "Beijing"]
STATUSES = ["completed", "pending", "cancelled"]


def main():
    rng = random.Random(42)
    start_date = date(2026, 1, 1)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["order_id", "order_date", "city", "amount_cents", "status"])

        for order_id in range(1, ROW_COUNT + 1):
            order_date = start_date + timedelta(days=rng.randrange(365))
            city = rng.choice(CITIES)
            amount_cents = rng.randint(100, 100_000)
            status = rng.choices(STATUSES, weights=[80, 15, 5], k=1)[0]

            writer.writerow([
                order_id,
                order_date.isoformat(),
                city,
                amount_cents,
                status,
            ])

    print(f"已生成 {ROW_COUNT:,} 条订单：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()