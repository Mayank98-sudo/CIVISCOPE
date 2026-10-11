import pandas as pd
from pathlib import Path

INPUT_FILE = Path("data/processed/delhi_air_quality_clean.csv")


def main():
    print("=" * 60)
    print("CIVISCOPE — CLEAN DATA ANALYSIS")
    print("=" * 60)

    df = pd.read_csv(INPUT_FILE)

    print(f"\nTotal records: {len(df)}")
    print(f"Total columns: {len(df.columns)}")

    print("\nData types:")
    print(df.dtypes.to_string())

    print("\nPollutants:")
    print(df["pollutant_id"].value_counts().to_string())

    print("\nStations:")
    print(f"Unique stations: {df['station'].nunique()}")

    print("\nRecords per station:")
    print(
        df["station"]
        .value_counts()
        .to_string()
    )

    print("\nNumeric summary:")
    print(
        df[
            ["min_value", "max_value", "avg_value"]
        ].describe()
        .to_string()
    )

    print("\nMissing values:")
    print(
        df.isna()
        .sum()
        .to_string()
    )

    print("\nAverage pollutant values:")

    pollutant_summary = (
        df.groupby("pollutant_id")["avg_value"]
        .agg(["count", "mean", "min", "max"])
        .round(2)
    )

    print(pollutant_summary.to_string())

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()