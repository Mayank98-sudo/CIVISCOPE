"""Import a preserved official CPCB table; no CAPTCHA or endpoint bypass."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

import pandas as pd

from src.core.config import DATA, POLLUTANTS, TIMEZONE, normalize_pollutant
from src.core.data import normalize_unit, timestamp

SOURCE='https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/advance-search'


def table_records(payload, latitude=None, longitude=None):
    meta=payload['metadata']
    if meta.get('source')!=SOURCE or meta.get('state')!='Delhi' or meta.get('city')!='Delhi':
        raise ValueError('Expected a preserved Delhi CPCB table with source provenance')
    station=str(meta.get('station','')).strip()
    interval=meta.get('interval_minutes')
    if not station or interval not in (15,60):
        raise ValueError('Station identity or supported interval evidence missing')
    collected=timestamp(meta.get('collected_at'))
    if pd.isna(collected):
        raise ValueError('Collection timestamp missing')
    headers=payload['headers']; rows=payload['rows']
    if len(rows)!=meta.get('reported_rows') or not rows or any(len(r)!=len(headers) for r in rows):
        raise ValueError('Incomplete or malformed preserved table')
    if [re.sub('⇅','',h).strip() for h in headers[:2]]!=['Date From','Date To']:
        raise ValueError('Date interval headers changed')
    frame=pd.DataFrame(rows,columns=headers)
    starts=pd.to_datetime(frame.iloc[:,0],format='%d-%m-%Y %H:%M',errors='raise').dt.tz_localize(TIMEZONE)
    ends=pd.to_datetime(frame.iloc[:,1],format='%d-%m-%Y %H:%M',errors='raise').dt.tz_localize(TIMEZONE)
    if not (ends-starts).eq(pd.Timedelta(minutes=interval)).all() or ends.duplicated().any():
        raise ValueError('Duplicate or unexpected source intervals')
    if not starts.dt.minute.isin([0,15,30,45] if interval==15 else [0]).all():
        raise ValueError('Source intervals do not align with fifteen-minute bins')
    if not starts.is_monotonic_increasing:
        raise ValueError('Source table is not chronologically ordered')
    records=[]; skipped=[]
    for column in headers[2:]:
        match=re.fullmatch(r'(.+?)\s*\((.+)\)⇅?',column.strip())
        if not match:
            raise ValueError('Concentration unit header missing')
        pollutant=normalize_pollutant(match[1]); unit=normalize_unit(match[2])
        if pollutant not in POLLUTANTS:
            skipped.append(match[1]); continue
        if unit!=POLLUTANTS[pollutant]['unit']:
            raise ValueError('Unexpected pollutant concentration unit')
        values=pd.to_numeric(frame[column].replace({'':None,'NA':None,'N/A':None}),errors='raise')
        values=values.where(values.ge(0) & values.map(lambda x:pd.isna(x) or math.isfinite(x)))
        intervals=pd.DataFrame({'start':starts,'end':ends,'value':values})
        intervals=intervals[intervals.end<=collected].copy()
        intervals['hour_start']=intervals.start.dt.floor('h')
        for hour,g in intervals.groupby('hour_start'):
            if hour+pd.Timedelta(hours=1)>collected:
                continue
            # Every quarter must exist and be usable; partial hours stay missing.
            expected=60//interval
            complete=len(g)==expected and g.value.notna().sum()==expected
            records.append({'country':'India','state':'Delhi','city':'Delhi','station':station,
                'last_update':(hour+pd.Timedelta(hours=1)).isoformat(),'avg_value':float(g.value.mean()) if complete else None,
                'min_value':float(g.value.min()) if complete else None,'max_value':float(g.value.max()) if complete else None,
                'latitude':latitude,'longitude':longitude,'pollutant_id':pollutant,'unit':unit,
                'value_kind':'concentration','averaging_hours':1,'valid_hours':1 if complete else 0,
                'interval_start':hour.isoformat(),'interval_end':(hour+pd.Timedelta(hours=1)).isoformat(),
                'aggregation':'Mean of complete, equal-duration official intervals; interval minutes='+str(interval)})
    if not records:
        raise ValueError('No supported completed concentration intervals')
    return records,{'excluded_future_intervals':int((ends>collected).sum()),'unsupported_parameters':skipped,
                    'incomplete_hour_records':sum(r['avg_value'] is None for r in records)}


def import_table(path, directory=DATA/'historical', latitude=None, longitude=None):
    path=Path(path)
    payload=json.loads(path.read_text(encoding='utf-8'))
    records,diagnostics=table_records(payload,latitude,longitude)
    meta={**payload['metadata'],'raw_artifact':path.name,'raw_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
          'import_diagnostics':diagnostics,'coordinate_provenance':'Caller-supplied station coordinates; not inferred from measurements'}
    stamp=timestamp(meta['collected_at']).strftime('%Y%m%d_%H%M%S')
    directory.mkdir(parents=True,exist_ok=True)
    identity=hashlib.sha256(meta['station'].encode()).hexdigest()[:8]
    target=directory/f'delhi_snapshot_{stamp}_cpcb_{identity}.json'
    with target.open('x',encoding='utf-8') as handle:
        json.dump({'metadata':meta,'records':records},handle,indent=2,allow_nan=False)
    return target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('table',type=Path)
    parser.add_argument('--latitude',type=float)
    parser.add_argument('--longitude',type=float)
    args=parser.parse_args()
    print('Imported:',import_table(args.table,latitude=args.latitude,longitude=args.longitude))


if __name__=='__main__':
    main()
