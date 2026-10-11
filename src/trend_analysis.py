"""Per-station time changes; comparisons stop at gaps and metadata changes."""

from pathlib import Path as _Path
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd


def build_trends(observations):
    out=observations.sort_values(['station','pollutant_id','observation_time']).copy()
    groups=out.groupby(['station','pollutant_id'])
    out['previous_value']=groups.avg_value.shift()
    delta=(out.observation_time-groups.observation_time.shift()).dt.total_seconds()/3600
    comparable=delta.gt(0)&delta.le(3)&out.unit.eq(groups.unit.shift())&out.value_kind.eq(groups.value_kind.shift())
    out.loc[~comparable,'previous_value']=np.nan
    out['absolute_change']=out.avg_value-out.previous_value
    out['percentage_change']=100*out.absolute_change/out.previous_value.abs().replace(0,np.nan)
    out['trend']='Data unavailable'
    valid=out.percentage_change.notna()
    out.loc[valid,'trend']='Stable'
    out.loc[out.percentage_change>5,'trend']='Increasing'
    out.loc[out.percentage_change < -5,'trend']='Decreasing'
    return out


def main():
    from src.pipeline.run_pipeline import run_pipeline
    run_pipeline()

if __name__=='__main__':
    main()
