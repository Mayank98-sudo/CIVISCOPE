"""Station intelligence derived exclusively from each station's observations."""
from __future__ import annotations

from pathlib import Path as _Path
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))

import numpy as np
import pandas as pd
from src.core.data import coverage_table
from src.production.aqi_analysis import calculate_subindex as calculate_aqi_sub_index, get_aqi_category
from src.core.config import normalize_pollutant

COLUMNS=['station','latitude','longitude','latest_measurement','freshness','pollutants_available','valid_pollutants','station_aqi','station_category','aqi_status','dominant_pollutant','dominant_concentration','coverage_percent','forecast_status']


def build_stations(observations: pd.DataFrame, aqi: pd.DataFrame, forecasts: pd.DataFrame) -> pd.DataFrame:
    coverage=coverage_table(observations)
    rows=[]
    for station,g in aqi.groupby('station'):
        last=g.sort_values('observation_time').iloc[-1]
        # Comparable same-hour measurements only; stale values never count as current.
        aligned=g[(g.observation_time.dt.floor('h')==last.observation_time.floor('h')) & g.freshness.eq('Fresh')]
        valid=aligned[aligned.aqi_sub_index.notna()]
        eligible=len(valid)>=3 and valid.pollutant_id.isin(['PM2.5','PM10']).any()
        dominant=valid.loc[valid.aqi_sub_index.idxmax()] if eligible else None
        unsupported=aligned.category.eq('Severe').any() | aligned.aqi_reason.str.contains('Higher ozone',na=False).any()
        if unsupported:
            dominant=None
        available_forecasts=forecasts[(forecasts.station==station) & forecasts.forecast_value.notna()]
        rows.append(dict(station=station,latitude=last.latitude,longitude=last.longitude,latest_measurement=last.observation_time,
            freshness=last.freshness,pollutants_available=', '.join(sorted(g.pollutant_id)),valid_pollutants=int(g.avg_value.notna().sum()),
            station_aqi=dominant.aqi_sub_index if dominant is not None else np.nan,
            station_category=dominant.category if dominant is not None else 'Data unavailable',
            aqi_status=('Analytical estimate' if (valid.aqi_status=='Analytical estimate').any() else 'CIVISCOPE calculation') if dominant is not None else ('Stale observations' if last.freshness=='Stale' else 'Insufficient eligible aligned pollutants or unsupported numeric range'),
            dominant_pollutant=dominant.pollutant_id if dominant is not None else 'Data unavailable',
            dominant_concentration=dominant.avg_value if dominant is not None else np.nan,
            coverage_percent=coverage.loc[coverage.station==station,'coverage_percent'].mean(),
            forecast_status='Experimental forecast available' if len(available_forecasts) else 'Data unavailable'))
    return pd.DataFrame(rows,columns=COLUMNS)


def main():
    from src.pipeline.run_pipeline import run_pipeline
    run_pipeline()

if __name__=='__main__':
    main()
