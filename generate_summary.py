import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path


def generate_summary(raw_path, summary_path):
    grouped = defaultdict(list)

    with raw_path.open("r", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            key = (
                Path(row["input"]).name,
                row["version"],
                int(row["threads"])
            )

            grouped[key].append(
                float(row["time_seconds"])
            )

    summary = []

    inputs = sorted(set(key[0] for key in grouped))

    for input_name in inputs:
        seq_key = (input_name, "seq", 1)

        if seq_key not in grouped:
            raise ValueError(
                f"Tempo sequencial ausente: {input_name}"
            )

        seq_median = statistics.median(
            grouped[seq_key]
        )

        for (name, version, threads), times in grouped.items():
            if name != input_name:
                continue

            mean = statistics.mean(times)
            median = statistics.median(times)

            if median <= 0:
                speedup = None
                efficiency = None
            else:
                speedup = seq_median / median
                efficiency = speedup / threads * 100

            summary.append({
                "input": name,
                "version": version,
                "threads": threads,
                "samples": len(times),
                "mean_seconds": round(mean, 6),
                "median_seconds": round(median, 6),
                "speedup": (
                    round(speedup, 4)
                    if speedup is not None else ""
                ),
                "efficiency_percent": (
                    round(efficiency, 2)
                    if efficiency is not None else ""
                ),
            })

    summary.sort(
        key=lambda row: (
            row["input"],
            row["threads"],
            row["version"]
        )
    )

    columns = [
        "input",
        "version",
        "threads",
        "samples",
        "mean_seconds",
        "median_seconds",
        "speedup",
        "efficiency_percent",
    ]

    with summary_path.open("w", newline="") as file:
        writer = csv.DictWriter(
            file, fieldnames=columns
        )

        writer.writeheader()
        writer.writerows(summary)

    print(f"Resumo gerado: {summary_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "raw",
        help="Caminho do arquivo CSV bruto"
    )

    parser.add_argument(
        "--output",
        help="Caminho do CSV de resumo"
    )

    args = parser.parse_args()

    raw_path = Path(args.raw)

    if not raw_path.is_file():
        parser.error("Arquivo CSV nao encontrado.")

    if args.output:
        summary_path = Path(args.output)
    else:
        summary_path = raw_path.with_name(
            raw_path.name.replace(
                "_raw.csv", "_summary.csv"
            )
        )

    if summary_path == raw_path:
        parser.error(
            "O resumo deve ter nome diferente do CSV bruto."
        )

    generate_summary(raw_path, summary_path)
