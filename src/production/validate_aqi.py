"""Output contract checks are distinct from official scientific certification."""

from pathlib import Path as _Path
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import numpy as np
from src.production.aqi_analysis import get_aqi_category


def validate_aqi(frame):
    required={'station','pollutant_id','aqi_sub_index','category','aqi_status','aqi_reason'}
    if not required.issubset(frame):
        raise ValueError('AQI schema missing required columns')
    if frame.duplicated(['station','pollutant_id']).any():
        raise ValueError('Duplicate station/pollutant AQI')
    present=frame.aqi_sub_index.notna()
    if not np.isfinite(frame.loc[present,'aqi_sub_index']).all() or not frame.loc[present,'aqi_sub_index'].between(0,500).all():
        raise ValueError('Invalid AQI numeric value')
    if not frame.loc[present,'aqi_sub_index'].map(get_aqi_category).eq(frame.loc[present,'category']).all():
        raise ValueError('AQI/category mismatch')
    if frame.aqi_reason.fillna('').eq('').any():
        raise ValueError('Missing AQI diagnostic')
    return True


def main():
    from src.pipeline.run_pipeline import run_pipeline
    run_pipeline()

if __name__=='__main__':
    main()
