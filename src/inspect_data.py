import json
from pathlib import Path
from collections import Counter


DATA_FILE = Path("data/raw/delhi_air_quality.json")


def main():
    print("=" * 60)
    print("CIVISCOPE — DELHI AIR QUALITY DATA INSPECTION")
    print("=" * 60)

    # Check whether the file exists
    if not DATA_FILE.exists():
        print(f"\nERROR: Data file not found: {DATA_FILE}")
        return

    # Load JSON
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        records = json.load(file)

    print(f"\nTotal records: {len(records)}")

    if not records:
        print("ERROR: Dataset is empty.")
        return

    # ---------------------------------------------------------
    # 1. Stations
    # ---------------------------------------------------------
    stations = sorted({
        record.get("station", "").strip()
        for record in records
        if record.get("station")
    })

    print(f"\nUnique stations: {len(stations)}")

    for station in stations:
        print(f"  - {station}")

    # ---------------------------------------------------------
    # 2. Cities
    # ---------------------------------------------------------
    cities = sorted({
        record.get("city", "").strip()
        for record in records
        if record.get("city")
    })

    print(f"\nCities represented: {len(cities)}")

    for city in cities:
        print(f"  - {city}")

    # ---------------------------------------------------------
    # 3. Pollutants
    # ---------------------------------------------------------
    pollutants = Counter(
        record.get("pollutant_id", "").strip()
        for record in records
        if record.get("pollutant_id")
    )

    print("\nPollutants:")
    for pollutant, count in sorted(pollutants.items()):
        print(f"  {pollutant}: {count} records")

    # ---------------------------------------------------------
    # 4. Timestamps
    # ---------------------------------------------------------
    timestamps = [
        record.get("last_update", "").strip()
        for record in records
        if record.get("last_update")
    ]

    print(f"\nUnique timestamps: {len(set(timestamps))}")

    if timestamps:
        print(f"Earliest timestamp: {min(timestamps)}")
        print(f"Latest timestamp:   {max(timestamps)}")

    # ---------------------------------------------------------
    # 5. Missing values
    # ---------------------------------------------------------
    fields = [
        "country",
        "state",
        "city",
        "station",
        "last_update",
        "latitude",
        "longitude",
        "pollutant_id",
        "min_value",
        "max_value",
        "avg_value",
    ]

    print("\nMissing values:")

    for field in fields:
        missing = sum(
            1
            for record in records
            if not str(record.get(field, "")).strip()
        )

        print(f"  {field}: {missing}")

    # ---------------------------------------------------------
    # 6. Duplicate detection
    # ---------------------------------------------------------
    keys = []

    for record in records:
        key = (
            record.get("station"),
            record.get("last_update"),
            record.get("pollutant_id"),
        )
        keys.append(key)

    duplicate_count = len(keys) - len(set(keys))

    print(f"\nDuplicate records: {duplicate_count}")

    # ---------------------------------------------------------
    # 7. Coordinate validation
    # ---------------------------------------------------------
    invalid_coordinates = []

    for record in records:
        try:
            latitude = float(record["latitude"])
            longitude = float(record["longitude"])

            if not (-90 <= latitude <= 90):
                invalid_coordinates.append(record)

            elif not (-180 <= longitude <= 180):
                invalid_coordinates.append(record)

        except (ValueError, TypeError, KeyError):
            invalid_coordinates.append(record)

    print(f"Invalid coordinates: {len(invalid_coordinates)}")

    # ---------------------------------------------------------
    # 8. Numeric value validation
    # ---------------------------------------------------------
    numeric_fields = [
        "min_value",
        "max_value",
        "avg_value",
    ]

    print("\nInvalid numeric values:")

    for field in numeric_fields:
        invalid = 0

        for record in records:
            try:
                float(record[field])
            except (ValueError, TypeError, KeyError):
                invalid += 1

        print(f"  {field}: {invalid}")

    # ---------------------------------------------------------
    # 9. Sample records
    # ---------------------------------------------------------
    print("\nSample records:")

    for index, record in enumerate(records[:3], start=1):
        print(f"\nRecord {index}:")
        print(json.dumps(record, indent=2, ensure_ascii=False))

    # ---------------------------------------------------------
    # Final summary
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("INSPECTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()