"""Publish a reproducible analytical run only after every stage validates."""
from __future__ import annotations
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import sys
import uuid

if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

import pandas as pd
from src.core.config import DATA, SOURCE_URL
from src.core.data import read_history,prepare_observations,coverage_table,now_local
from src.trend_analysis import build_trends
from src.production.aqi_analysis import build_aqi
from src.production._forecast import build_forecasts
from src.production.intelligence.station_analysis import build_stations
from src.production.risk.risk_analysis import build_risk
from src.production.warning.warning_analysis import build_warnings
from src.production.validate_aqi import validate_aqi
from src.production.intelligence.intelligence_engine import build_report


def json_write(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')


def run_pipeline(data_dir: Path=DATA,collect=False,now=None):
    now=now_local() if now is None else now
    if collect:
        from src.collect_historical import collect_snapshot
        collect_snapshot(directory=data_dir/'historical')
    history_dir=data_dir/'historical'
    input_files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(history_dir.glob('delhi_snapshot_*.json'))}
    raw=read_history(history_dir)
    observations,quality=prepare_observations(raw,now)
    trends=build_trends(observations)
    aqi=build_aqi(observations)
    forecasts,validation=build_forecasts(observations,now)
    stations=build_stations(observations,aqi,forecasts)
    risk=build_risk(aqi,trends)
    warnings=build_warnings(observations,aqi,trends,now)
    validate_aqi(aqi)
    if observations.duplicated(['station','pollutant_id','observation_time']).any():
        raise ValueError('Duplicate observations after validation')
    if forecasts.duplicated(['station','pollutant_id','horizon_hours']).any():
        raise ValueError('Duplicate forecast identities')
    report=build_report(stations,forecasts,quality,warnings)
    run_id=now.strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8]
    processed=data_dir/'processed'
    directory=processed/'runs'/run_id
    directory.mkdir(parents=True,exist_ok=False)
    frames={'observations':observations,'trends':trends,'aqi':aqi,'forecasts':forecasts,'validation':validation,'stations':stations,'risk':risk,'warnings':warnings,'coverage':coverage_table(observations)}
    for name,frame in frames.items():
        frame.to_csv(directory/f'{name}.csv',index=False)
        saved=pd.read_csv(directory/f'{name}.csv')
        if list(saved.columns)!=list(frame.columns) or len(saved)!=len(frame):
            raise ValueError('Output round-trip validation failed: '+name)
    quality['input_files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(history_dir.glob('delhi_snapshot_*.json'))}
    if quality['input_files'] != input_files:
        raise ValueError('Source snapshots changed during analysis; run not published')
    json_write(directory/'quality.json',quality)
    json_write(directory/'report.json',report)
    manifest={'schema_version':2,'run_id':run_id,'generated_at':now.isoformat(),'directory':f'runs/{run_id}','source':SOURCE_URL,'sources':quality['sources'],'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir() if p.is_file()}}
    json_write(directory/'manifest.json',manifest)
    temporary=processed/f'.latest_{run_id}.json'
    json_write(temporary,manifest)
    os.replace(temporary,processed/'latest_run.json')
    logs=data_dir/'logs'; logs.mkdir(exist_ok=True)
    with (logs/'pipeline.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'timestamp':now.isoformat(),'module':__name__,'event':'run_published','severity':'INFO','message':'All output contracts checked','run_id':run_id,'observations':len(observations)})+'\n')
    return directory


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collect',action='store_true',help='Fetch one official snapshot before rebuilding')
    args=parser.parse_args()
    try:
        directory=run_pipeline(collect=args.collect)
        print(f'Published validated output contracts: {directory}')
        print('Scientific eligibility and forecast availability are reported separately.')
    except Exception as error:
        # Request exception strings may contain credentials; report sanitized type.
        print(f'Pipeline failed ({type(error).__name__}); last successful run retained.',file=sys.stderr)
        raise SystemExit(1) from None

if __name__=='__main__':
    main()
