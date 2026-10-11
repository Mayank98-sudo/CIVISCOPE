"""Strict forecast target matching; no before-target nearest-neighbour fallback."""

from pathlib import Path as _Path
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

import pandas as pd


def validate_forecasts(forecasts,observations):
    rows=[]
    for r in forecasts.to_dict('records'):
        if pd.isna(r.get('forecast_value')):
            continue
        target=pd.Timestamp(r['forecast_target_time'])
        issued=pd.Timestamp(r['forecast_time'])
        trained=pd.Timestamp(r['last_observation_time'])
        if target<=issued or target<=trained:
            continue
        match=observations[(observations.station==r['station']) & (observations.pollutant_id==r['pollutant_id']) & (observations.observation_time==target)]
        if len(match)!=1 or pd.isna(match.iloc[0].avg_value):
            continue
        actual=match.iloc[0]
        if actual.unit!=r['unit'] or actual.value_kind!=r['value_kind']:
            continue
        error=r['forecast_value']-actual.avg_value
        rows.append(dict(station=r['station'],pollutant_id=r['pollutant_id'],forecast_time=issued,forecast_target_time=target,actual_time=actual.observation_time,forecast_value=r['forecast_value'],actual_value=actual.avg_value,absolute_error=abs(error),squared_error=error**2))
    return pd.DataFrame(rows,columns=['station','pollutant_id','forecast_time','forecast_target_time','actual_time','forecast_value','actual_value','absolute_error','squared_error'])


def main():
    from src.pipeline.run_pipeline import run_pipeline
    run_pipeline()

if __name__=='__main__':
    main()
