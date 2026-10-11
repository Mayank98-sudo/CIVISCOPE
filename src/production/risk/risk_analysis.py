"""Transparent CIVISCOPE analytical risk; never an official health classification."""

from pathlib import Path as _Path
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))

import numpy as np
import pandas as pd


def aqi_risk_score(aqi):
    if pd.isna(aqi) or not np.isfinite(aqi) or aqi<0:
        return np.nan
    return next((score for bound,score in [(50,10),(100,25),(200,50),(300,70),(400,85),(500,100)] if aqi<=bound),np.nan)


def get_risk_level(score):
    if pd.isna(score):
        return 'Data unavailable'
    return next((label for bound,label in [(20,'Low'),(40,'Moderate'),(60,'High'),(80,'Very High'),(101,'Critical')] if score<bound),'Data unavailable')


def build_risk(aqi, trends):
    """Preserve existing AQI tier score and +/- trend adjustment, scoped to station.

    Forecast adjustment is withheld until concentration forecast averaging windows
    can be validated. Missing/old comparisons never imply stable conditions.
    """
    out=aqi[['station','pollutant_id','observation_time','aqi_sub_index','aqi_status','freshness']].copy()
    latest=trends.sort_values('observation_time').groupby(['station','pollutant_id'],as_index=False).tail(1)
    out=out.merge(latest[['station','pollutant_id','observation_time','percentage_change','trend']],on=['station','pollutant_id','observation_time'],how='left',validate='one_to_one')
    out['base_score']=out.aqi_sub_index.map(aqi_risk_score)
    out['trend_adjustment']=out.trend.map({'Increasing':15.,'Decreasing':-10.,'Stable':0.})
    out['risk_score']=(out.base_score+out.trend_adjustment.fillna(0)).clip(0,100)
    out.loc[out.freshness.ne('Fresh'),'risk_score']=np.nan
    out['risk_level']=out.risk_score.map(get_risk_level)
    out['risk_status']=np.where(out.risk_score.notna(),'CIVISCOPE analytical score','Data unavailable')
    out['components']=np.where(out.trend_adjustment.notna(),'AQI tier + observed trend; forecast unavailable','AQI tier only; trend and forecast unavailable')
    return out


def main():
    from src.pipeline.run_pipeline import run_pipeline
    run_pipeline()

if __name__=='__main__':
    main()
