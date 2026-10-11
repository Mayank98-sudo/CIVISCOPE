"""Evidence-bearing data-quality and analytical warnings."""

from pathlib import Path as _Path
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))

import hashlib
import numpy as np
import pandas as pd
from src.core.data import latest_observations, now_local

COLUMNS=['warning_id','timestamp','station','pollutant_id','condition','severity','evidence','status','source_file']


def build_warnings(observations,aqi,trends,now=None):
    rows=[]
    now=now if now is not None else now_local()
    def add(row,condition,severity,evidence,status):
        identity=f"{row.station}|{row.pollutant_id}|{row.observation_time}|{condition}"
        rows.append(dict(warning_id=hashlib.sha256(identity.encode()).hexdigest()[:20],timestamp=row.observation_time,station=row.station,pollutant_id=row.pollutant_id,condition=condition,severity=severity,evidence=evidence,status=status,source_file=row.source_file))
    latest=latest_observations(trends)
    for _,r in latest.iterrows():
        if r.freshness=='Stale':
            add(r,'Stale observation','Data quality',f'Last source observation {r.observation_time}; older than 3 hours.','Active')
        if pd.isna(r.avg_value):
            add(r,'Unavailable measurement','Data quality',r.quality_status,'Active')
        if r.pollutant_id in ('PM2.5','PM10') and pd.notna(r.percentage_change) and r.percentage_change>=25:
            add(r,'Rapid source-value increase','Watch',f'Source value {r.previous_value:g} to {r.avg_value:g} ({r.percentage_change:.1f}%) within 3 hours; unit {r.unit}.','Active' if r.freshness=='Fresh' else 'Historical')
    for _,r in aqi.iterrows():
        if pd.notna(r.aqi_sub_index) and r.aqi_sub_index>=201:
            add(r,'Analytical AQI threshold','High',f'Sub-index {r.aqi_sub_index:.0f}; {r.aqi_status}. Threshold 201.','Active' if r.freshness=='Fresh' else 'Historical')
    # Causal rolling MAD: preceding values only; insufficient baseline means no flag.
    for _,g in observations.groupby(['station','pollutant_id']):
        g=g.sort_values('observation_time')
        for i in range(12,len(g)):
            r=g.iloc[i]
            baseline=g.iloc[max(0,i-24):i]
            if baseline.unit.nunique()!=1 or not baseline.unit.eq(r.unit).all():
                continue
            values=baseline.avg_value.dropna().to_numpy()
            if len(values)<12 or pd.isna(r.avg_value):
                continue
            med=np.median(values); mad=np.median(np.abs(values-med))
            if mad>0 and abs(r.avg_value-med)/(1.4826*mad)>4:
                add(r,'Potential anomaly','Watch',f'Value {r.avg_value:g}; preceding median {med:g}, MAD {mad:g}; robust deviation >4. Does not establish sensor failure.','Historical')
    return pd.DataFrame(rows,columns=COLUMNS).drop_duplicates('warning_id')


def main():
    from src.pipeline.run_pipeline import run_pipeline
    run_pipeline()

if __name__=='__main__':
    main()
