import pandas as pd
from pathlib import Path


INPUT_FILE = Path("data/processed/delhi_historical.csv")
OUTPUT_FILE = Path("data/processed/historical_pollution_summary.csv")


def main():

    print("=" * 60)
    print("CIVISCOPE — HISTORICAL POLLUTION ANALYSIS")
    print("=" * 60)

    if not INPUT_FILE.exists():
        print("\nERROR: Historical dataset not found.")
        print(f"Expected: {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)

    print(f"\nRecords loaded: {len(df)}")

    # Convert numeric values
    df["avg_value"] = pd.to_numeric(
        df["avg_value"],
        errors="coerce"
    )

    df["last_update"] = pd.to_datetime(
        df["last_update"],
        errors="coerce"
    )

    # Remove records without usable measurements
    usable = df.dropna(
        subset=["avg_value"]
    ).copy()

    print(
        f"Usable pollution measurements: "
        f"{len(usable)}"
    )

    # ---------------------------------------------------------
    # Average pollution by timestamp and pollutant
    # ---------------------------------------------------------

    summary = (
        usable
        .groupby(
            [
                "last_update",
                "pollutant_id"
            ],
            as_index=False
        )
        .agg(
            average_value=("avg_value", "mean"),
            minimum_value=("avg_value", "min"),
            maximum_value=("avg_value", "max"),
            stations=("station", "nunique")
        )
    )

    # ---------------------------------------------------------
    # Sort chronologically
    # ---------------------------------------------------------

    summary = summary.sort_values(
        [
            "last_update",
            "pollutant_id"
        ]
    )

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    summary.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # Display
    # ---------------------------------------------------------

    print("\n" + "-" * 60)
    print("HISTORICAL POLLUTION SUMMARY")
    print("-" * 60)

    print(summary.to_string(index=False))

    print("\n" + "-" * 60)
    print("TIMESTAMP COVERAGE")
    print("-" * 60)

    print(
        f"Unique timestamps: "
        f"{summary['last_update'].nunique()}"
    )

    if not summary.empty:

        print(
            f"Earliest: "
            f"{summary['last_update'].min()}"
        )

        print(
            f"Latest: "
            f"{summary['last_update'].max()}"
        )

    print("\nSaved to:")
    print(OUTPUT_FILE)

    print("\n" + "=" * 60)
    print("HISTORICAL ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()