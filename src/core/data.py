"""Validate observations without filling measurements or assuming source units."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
from src.core.config import DATA, POLLUTANTS, SOURCE_URL, STALE_HOURS, TIMEZONE, normalize_pollutant

KEY = ["station", "pollutant_id", "observation_time"]


def timestamp(value: object) -> pd.Timestamp:
    """Interpret legacy Indian station/collection timestamps in Asia/Kolkata."""
    if value is None or pd.isna(value):
        return pd.NaT
    try:
        text = str(value)
        dayfirst = len(text) > 2 and text[2] == "-"
        t = pd.to_datetime(text, dayfirst=dayfirst, errors="coerce")
        if pd.isna(t):
            return pd.NaT
        return t.tz_localize(TIMEZONE) if t.tzinfo is None else t.tz_convert(TIMEZONE)
    except (ValueError, TypeError):
        return pd.NaT


def now_local() -> pd.Timestamp:
    return pd.Timestamp.now(tz=TIMEZONE)


def normalize_unit(value: object) -> str:
    unit = str(value).strip().lower().replace("µ", "u").replace("μ", "u").replace("³", "3").replace(" ", "")
    return "unknown" if unit in {"", "na", "n/a", "none", "nan", "null"} else unit


def prepare_observations(raw: pd.DataFrame, now=None) -> tuple[pd.DataFrame, dict]:
    """Return auditable unique observations and quality counts. Invalid values stay missing.

    Repeated source keys with conflicting measurements are quarantined, not resolved
    by taking the latest retrieval (which could introduce revision leakage).
    """
    now = timestamp(now) if now is not None else now_local()
    df = raw.copy()
    aliases = {"pollutant_avg": "avg_value", "pollutant_min": "min_value", "pollutant_max": "max_value", "pollutant_unit": "unit"}
    for old, new in aliases.items():
        if old in df and new not in df:
            df = df.rename(columns={old: new})
        elif old in df and new in df:
            same = df[old].astype(str).eq(df[new].astype(str)) | (df[old].isna() & df[new].isna())
            if not same.all():
                raise ValueError(f"Conflicting source aliases: {old}, {new}")
    required = {"station", "pollutant_id", "last_update", "avg_value"}
    missing = required - set(df)
    if missing:
        raise ValueError("Missing observation columns: " + ", ".join(sorted(missing)))
    quality = {"records": len(df), "missing_values": {k: int(v) for k, v in df.isna().sum().items()}}
    df["station"] = df.station.fillna("").astype(str).str.strip()
    df["pollutant_id"] = df.pollutant_id.map(normalize_pollutant)
    df["observation_time"] = pd.to_datetime(df.last_update.map(timestamp), utc=True).dt.tz_convert(TIMEZONE)
    df["collection_time"] = pd.to_datetime(df.get("collection_time", pd.Series(pd.NaT, index=df.index)).map(timestamp), utc=True).dt.tz_convert(TIMEZONE)
    for column in ["avg_value", "min_value", "max_value", "latitude", "longitude"]:
        df[column] = pd.to_numeric(df.get(column, pd.Series(np.nan, index=df.index)), errors="coerce")
    bad_value = ~np.isfinite(df.avg_value) | (df.avg_value < 0)
    bad_identity = (df.station == "") | ~df.pollutant_id.isin(POLLUTANTS) | df.observation_time.isna()
    future = df.observation_time > now + pd.Timedelta(minutes=5)
    bad_coords = ~df.latitude.between(-90, 90) | ~df.longitude.between(-180, 180)
    invalid_range = (df.min_value < 0) | (df.max_value < 0) | (df.min_value > df.max_value) | (df.avg_value < df.min_value) | (df.avg_value > df.max_value)
    quality.update(invalid_values=int(bad_value.sum()), invalid_identity=int(bad_identity.sum()), future_observations=int(future.sum()), invalid_coordinates=int(bad_coords.sum()), invalid_ranges=int(invalid_range.sum()))
    df["quality_status"] = np.where(bad_value | invalid_range, "Invalid measurement", "Usable source value")
    df.loc[bad_value | invalid_range, "avg_value"] = np.nan
    df.loc[bad_coords, ["latitude", "longitude"]] = np.nan
    df = df.loc[~bad_identity & ~future].copy()
    quality["duplicate_observation_keys"] = int(df.duplicated(KEY).sum())
    for col, default in [("unit", "unknown"), ("value_kind", "unverified"), ("averaging_hours", np.nan), ("valid_hours", np.nan)]:
        if col not in df:
            df[col] = default
    df["unit"] = df.unit.fillna("unknown").map(normalize_unit)
    conflict = pd.Series(False, index=df.index)
    for col in ["avg_value", "unit", "value_kind", "averaging_hours", "valid_hours"]:
        conflict |= df.groupby(KEY)[col].transform(lambda s: s.nunique(dropna=False) > 1).astype(bool)
    quality["conflicting_records"] = int(conflict.sum())
    df.loc[conflict, "avg_value"] = np.nan
    df.loc[conflict, "quality_status"] = "Conflicting source records"
    # Earliest retrieval preserves the first known availability of an observation.
    df = df.sort_values("collection_time", na_position="last").drop_duplicates(KEY, keep="first")
    for col, default in [("unit", "Unknown"), ("value_kind", "unverified"), ("averaging_hours", np.nan), ("valid_hours", np.nan), ("source", SOURCE_URL), ("source_file", "Unknown")]:
        if col not in df:
            df[col] = default
    df["unit"] = df.unit.fillna("Unknown").map(normalize_unit)
    df["value_kind"] = df.value_kind.fillna("unverified")
    for col in ["averaging_hours", "valid_hours"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["age_hours"] = (now - df.observation_time).dt.total_seconds() / 3600
    df["freshness"] = np.where(df.age_hours > STALE_HOURS, "Stale", "Fresh")
    df = df.sort_values(KEY).reset_index(drop=True)
    latest = latest_observations(df)
    quality.update(unique_observations=len(df), stations=int(df.station.nunique()), pollutants=sorted(df.pollutant_id.unique()), latest_observation=str(df.observation_time.max()) if len(df) else None,
                   stale_stations=int(latest.groupby("station").age_hours.min().gt(STALE_HOURS).sum()),
                   unknown_units=int(df.unit.eq("unknown").sum()), usable_values=int(df.avg_value.notna().sum()),
                   generated_at=now.isoformat(), source=SOURCE_URL, sources=sorted(df.source.dropna().unique()))
    return df, quality


def latest_observations(df: pd.DataFrame) -> pd.DataFrame:
    """Keep latest record even if invalid; never silently fall back to an older value."""
    return df.sort_values("observation_time").groupby(["station", "pollutant_id"], as_index=False).tail(1).copy()


def read_history(directory: Path = DATA / "historical") -> pd.DataFrame:
    rows = []
    for path in sorted(directory.glob("delhi_snapshot_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        records = payload.get("records") if isinstance(payload, dict) else payload
        if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
            raise ValueError(f"Invalid snapshot schema: {path.name}")
        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
        collected = metadata.get("collected_at")
        if not collected:
            collected = pd.to_datetime(path.stem.removeprefix("delhi_snapshot_"), format="%Y%m%d_%H%M%S", errors="coerce")
        source=metadata.get('source',SOURCE_URL)
        rows.extend({**r, "collection_time": collected, "source_file": path.name, "source": source} for r in records)
    if not rows:
        raise ValueError("No historical observations available")
    return pd.DataFrame(rows)


def coverage_table(df: pd.DataFrame) -> pd.DataFrame:
    """Observed hourly bins / elapsed hourly bins; a data coverage measure, not certainty."""
    rows = []
    for (station, pollutant), g in df.groupby(["station", "pollutant_id"]):
        hours = g.observation_time.dt.floor("h")
        expected = int((hours.max() - hours.min()).total_seconds() / 3600) + 1
        observed = g.loc[g.avg_value.notna(), "observation_time"].dt.floor("h").nunique()
        rows.append(dict(station=station, pollutant_id=pollutant, observed_hours=observed, expected_hours=expected, coverage_percent=100 * observed / expected))
    return pd.DataFrame(rows, columns=["station", "pollutant_id", "observed_hours", "expected_hours", "coverage_percent"])
