"""Canonical concentration-to-index calculation and metadata eligibility.

All results are CIVISCOPE calculations. Source-reported values of unverified
meaning never enter the concentration interpolation function automatically.
"""
from __future__ import annotations

from pathlib import Path as _Path
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from dataclasses import dataclass
import math
import numpy as np
import pandas as pd
from src.core.config import POLLUTANTS, normalize_pollutant

# CPCB published finite ranges. Open severe bands have no invented upper endpoint.
RANGES = {
    'PM2.5': [(0,30),(31,60),(61,90),(91,120),(121,250)],
    'PM10': [(0,50),(51,100),(101,250),(251,350),(351,430)],
    'NO2': [(0,40),(41,80),(81,180),(181,280),(281,400)],
    'SO2': [(0,40),(41,80),(81,380),(381,800),(801,1600)],
    'NH3': [(0,200),(201,400),(401,800),(801,1200),(1201,1800)],
    'O3': [(0,50),(51,100),(101,168),(169,208)],
    'CO': [(0,1),(1.1,2),(2.1,10),(10.1,17),(17.1,34)],
    'Pb': [(0,.5),(.6,1),(1.1,2),(2.1,3),(3.1,3.5)],
}
INDEX_RANGES = [(0,50),(51,100),(101,200),(201,300),(301,400)]
CATEGORIES = ['Good','Satisfactory','Moderately Polluted','Poor','Very Poor','Severe']

@dataclass(frozen=True)
class AQIResult:
    value: float = math.nan
    category: str = 'Data unavailable'
    status: str = 'Data unavailable'
    reason: str = ''


def get_aqi_category(value) -> str:
    try:
        v = float(value)
    except (ValueError, TypeError):
        return 'Data unavailable'
    if not math.isfinite(v) or not 0 <= v <= 500:
        return 'Data unavailable'
    return CATEGORIES[next((i for i,b in enumerate([50,100,200,300,400,500]) if v <= b),5)]


def concentration_index(concentration, pollutant) -> AQIResult:
    """Pure analytical interpolation; caller must verify unit/meaning/averaging.

    Decimal gaps in published ranges use linear bridging, explicitly an analytical
    convention. Severe numeric extrapolation and O3 one-hour conversion are withheld.
    """
    pollutant = normalize_pollutant(pollutant)
    try:
        value = float(concentration)
    except (TypeError, ValueError):
        return AQIResult(reason='Invalid concentration')
    if not math.isfinite(value) or value < 0 or pollutant not in RANGES:
        return AQIResult(reason='Invalid concentration or unsupported pollutant')
    ranges = RANGES[pollutant]
    if value > ranges[-1][1]:
        if pollutant == 'O3':
            return AQIResult(reason='Higher ozone categories require separately verified one-hour methodology')
        return AQIResult(category='Severe', status='Category only', reason='Above finite CPCB range; numeric extrapolation withheld')
    for i, (lo, hi) in enumerate(ranges):
        il, ih = INDEX_RANGES[i]
        if lo <= value <= hi:
            result = il + (value-lo)*(ih-il)/(hi-lo)
            return AQIResult(round(result,2),get_aqi_category(round(result,2)),'Analytical estimate','CPCB finite breakpoint interpolation')
        if i and ranges[i-1][1] < value < lo:
            previous = ranges[i-1][1]
            result = INDEX_RANGES[i-1][1] + (value-previous)/(lo-previous)
            return AQIResult(round(result,2),get_aqi_category(round(result,2)),'Analytical estimate','Decimal gap bridged linearly; not an official rounding rule')
    return AQIResult(reason='Outside supported range')


def calculate_subindex(concentration, pollutant):
    """Compatibility API for explicit concentrations; metadata checks live in assess."""
    return concentration_index(concentration,pollutant).value


def assess(row) -> AQIResult:
    pollutant = normalize_pollutant(row.get('pollutant_id'))
    metadata = POLLUTANTS.get(pollutant)
    if metadata is None:
        return AQIResult(reason='Unsupported pollutant')
    if row.get('value_kind') != 'concentration' or row.get('unit') != metadata['unit']:
        return AQIResult(reason='Source value meaning or unit unverified')
    result = concentration_index(row.get('avg_value'),pollutant)
    if not math.isfinite(result.value):
        return result
    averaging = row.get('averaging_hours',np.nan)
    valid = row.get('valid_hours',np.nan)
    required_valid = 16 if metadata['hours'] == 24 else 8
    if averaging != metadata['hours'] or not pd.notna(valid) or valid < required_valid:
        return AQIResult(result.value,result.category,'Analytical estimate','Required averaging period or coverage unverified')
    return AQIResult(result.value,result.category,'CIVISCOPE calculation','Verified concentration metadata; not an official published AQI')


def build_aqi(observations: pd.DataFrame) -> pd.DataFrame:
    from src.core.data import latest_observations
    latest = latest_observations(observations)
    out = latest.copy()
    # Explicit one-hour concentrations can supply a trailing CPCB-period average.
    # Keep the original observation history intact; only AQI inputs are aggregated.
    for index,row in out.iterrows():
        metadata=POLLUTANTS.get(row.pollutant_id)
        if metadata is None or row.get('value_kind')!='concentration' or row.get('averaging_hours')!=1:
            continue
        hours=metadata['hours']; end=row.observation_time
        window=observations[(observations.station==row.station) & (observations.pollutant_id==row.pollutant_id)
            & (observations.observation_time>end-pd.Timedelta(hours=hours)) & (observations.observation_time<=end)
            & observations.unit.eq(metadata['unit']) & observations.value_kind.eq('concentration')
            & observations.averaging_hours.eq(1) & observations.valid_hours.eq(1)
            & observations.avg_value.notna()].copy()
        # Coverage counts distinct aligned full hours, never repeated retrievals.
        window=window[window.observation_time.eq(window.observation_time.dt.floor('h'))]
        count=window.observation_time.nunique()
        required=16 if hours==24 else 8
        out.loc[index,'averaging_hours']=hours
        out.loc[index,'valid_hours']=count
        out.loc[index,'avg_value']=window.avg_value.mean() if count>=required else np.nan
        out.loc[index,'min_value']=window.avg_value.min() if count>=required else np.nan
        out.loc[index,'max_value']=window.avg_value.max() if count>=required else np.nan
    results = [assess(r) for r in out.to_dict('records')]
    out['aqi_sub_index'] = [r.value for r in results]
    out['category'] = [r.category for r in results]
    out['aqi_status'] = [r.status for r in results]
    out['aqi_reason'] = [r.reason for r in results]
    return out


def main():
    from src.pipeline.run_pipeline import run_pipeline
    run_pipeline()

if __name__ == '__main__':
    main()
