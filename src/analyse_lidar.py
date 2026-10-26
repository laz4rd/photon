
import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data" / "experiments" / "lidar_measurements.csv"
RESULTS = ROOT / "results"
OUTPUT_CSV = RESULTS / "lidar_accuracy_results.csv"
OUTPUT_PNG = RESULTS / "lidar_accuracy.png"

REQUIRED_COLUMNS = {
    "object",
    "scan_id",
    "dimension",
    "reference_mm",
    "scan_mm",
}


def main():
    if not INPUT.exists():
        print(f"Measurements file not found:\n  {INPUT}")
        print("\nCreate it with this header:")
        print("object,scan_id,dimension,reference_mm,scan_mm")
        print("\nAdd your real ruler and LiDAR measurements.")
        sys.exit(1)

    with INPUT.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(
            reader.fieldnames
        ):
            print("Invalid CSV header.")
            print("Required columns:", ", ".join(sorted(REQUIRED_COLUMNS)))
            sys.exit(1)

        rows = []
        for line_number, row in enumerate(reader, start=2):
            try:
                reference = float(row["reference_mm"])
                scanned = float(row["scan_mm"])

                if reference <= 0:
                    raise ValueError("reference_mm must be greater than zero")

                rows.append({
                    "object": row["object"].strip(),
                    "scan_id": row["scan_id"].strip(),
                    "dimension": row["dimension"].strip(),
                    "reference_mm": reference,
                    "scan_mm": scanned,
                    "absolute_error_mm": abs(scanned - reference),
                    "percentage_error": (
                        abs(scanned - reference) / reference * 100
                    ),
                })
            except (ValueError, TypeError) as error:
                print(f"Invalid data on CSV line {line_number}: {error}")
                sys.exit(1)

    if not rows:
        print("No measurements found. No results were generated.")
        print(f"Add real measurements to:\n  {INPUT}")
        sys.exit(1)

    RESULTS.mkdir(parents=True, exist_ok=True)

    fields = [
        "object",
        "scan_id",
        "dimension",
        "reference_mm",
        "scan_mm",
        "absolute_error_mm",
        "percentage_error",
    ]

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    labels = [
        f"{row['object']} · {row['scan_id']} · {row['dimension']}"
        for row in rows
    ]
    errors = [row["percentage_error"] for row in rows]

    fig, ax = plt.subplots(figsize=(max(9, len(rows) * 1.2), 5))
    ax.bar(range(len(rows)), errors)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("Absolute percentage error (%)")
    ax.set_title("PHOTON — LiDAR Dimensional Accuracy")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUTPUT_PNG, dpi=180)
    plt.close(fig)

    mean_error = sum(errors) / len(errors)

    print(f"Measurements analysed: {len(rows)}")
    print(f"Mean absolute percentage error: {mean_error:.2f}%")
    print(f"CSV results: {OUTPUT_CSV}")
    print(f"Accuracy graph: {OUTPUT_PNG}")
    print("\nOnly measurements supplied in the input CSV were analysed.")


if __name__ == "__main__":
    main()

