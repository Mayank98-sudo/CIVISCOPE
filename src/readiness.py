"""Explicit live preflight; no network or credentials are read at import time."""
import argparse
import json
import os
from pathlib import Path
import tempfile

import pandas as pd
import requests
from dotenv import load_dotenv

from src.core.config import API_URL, DATA, ROOT, STALE_HOURS
from src.core.data import now_local
from src.dashboard.data_access import load_run


def connection_reason(error):
    """Classify exception types/errno without exposing request URLs or keys."""
    if isinstance(error, requests.exceptions.SSLError):
        return 'TLS verification failed'
    if isinstance(error, requests.exceptions.Timeout):
        return 'Connection or response timed out'
    visited=set()
    current=error
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if getattr(current, 'errno', None) in (10061, 111):
            return 'Connection refused before authentication'
        if type(current).__name__ in ('gaierror', 'NameResolutionError'):
            return 'DNS resolution failed'
        current=current.__cause__ or current.__context__
    return 'Network connection failed'


def probe_source(api_key, session=None):
    if not api_key:
        return {'status':'Unavailable', 'reason':'OGD_API_KEY is not configured'}
    try:
        response=(session or requests.Session()).get(
            API_URL, params={'api-key':api_key, 'format':'json', 'limit':1},
            headers={'Accept':'application/json','User-Agent':'CIVISCOPE/0.2'}, timeout=(5,15))
        if response.status_code != 200:
            reason='API authentication rejected' if response.status_code in (401,403) else 'Provider returned an HTTP error'
            return {'status':'Unavailable', 'reason':reason, 'http_status':response.status_code}
        payload=response.json()
        records=payload.get('records') if isinstance(payload,dict) else None
        if not isinstance(records,list) or not records or not all(isinstance(r,dict) for r in records):
            return {'status':'Unavailable','reason':'Expected nonempty records response was not returned'}
        return {'status':'Reachable','reason':'Authenticated sample request returned records',
                'http_status':200, 'sample_count':len(records)}
    except requests.RequestException as error:
        return {'status':'Unavailable','reason':connection_reason(error)}
    except ValueError:
        return {'status':'Unavailable','reason':'Provider response is not valid JSON'}


def assess_saved_run(processed=DATA/'processed', now=None):
    now=now_local() if now is None else pd.Timestamp(now)
    try:
        manifest=json.loads((processed/'latest_run.json').read_text(encoding='utf-8'))
        frames,quality,_=load_run(processed,manifest)
    except (OSError,ValueError,KeyError,TypeError):
        return {'status':'Unavailable','reason':'No complete verified analytical run'}
    obs=frames['observations']
    age=(now-obs.observation_time).dt.total_seconds()/3600
    fresh=obs[age.between(0,STALE_HOURS) & obs.avg_value.notna() & (obs.collection_time<=now)]
    stations=frames['stations']
    station_age=(now-stations.latest_measurement).dt.total_seconds()/3600
    eligible=stations.station_aqi.notna() & station_age.between(0,STALE_HOURS)
    forecasts=frames['forecasts']
    valid_forecasts=(forecasts.forecast_value.notna() & (forecasts.forecast_time<=now)
                     & (forecasts.forecast_target_time>now))
    return {'status':'Available', 'run_id':manifest['directory'],
            'latest_observation':quality['latest_observation'],
            'fresh_observations':int(len(fresh)),
            'unknown_unit_observations':int(obs.unit.eq('unknown').sum()),
            'unverified_value_kind_observations':int(obs.value_kind.eq('unverified').sum()),
            'current_station_aqi_estimates':int(eligible.sum()),
            'unexpired_forecasts':int(valid_forecasts.sum()),
            'forecast_status_counts':{str(k):int(v) for k,v in forecasts.forecast_status.value_counts().items()}}


def build_report(api_key='', processed=DATA/'processed', session=None, offline=False, now=None):
    now=now_local() if now is None else pd.Timestamp(now)
    source={'status':'Not checked','reason':'Offline preflight requested'} if offline else probe_source(api_key,session)
    saved=assess_saved_run(processed,now)
    gates=[
        {'requirement':'Official API sample request','passed':source['status']=='Reachable','evidence':source['reason']},
        {'requirement':'Fresh usable observations','passed':saved.get('fresh_observations',0)>0,'evidence':str(saved.get('fresh_observations',0))+' fresh observations'},
        {'requirement':'Eligible current station AQI','passed':saved.get('current_station_aqi_estimates',0)>0,'evidence':str(saved.get('current_station_aqi_estimates',0))+' eligible station estimates'},
        {'requirement':'Unexpired station forecasts','passed':saved.get('unexpired_forecasts',0)>0,'evidence':str(saved.get('unexpired_forecasts',0))+' unexpired predictions'},
    ]
    return {'schema_version':1,'checked_at':now.isoformat(),'source':source,'saved_run':saved,
            'minimum_live_gates_passed':all(g['passed'] for g in gates),'gates':gates,
            'scope':'Point-in-time minimum availability checks. Does not certify measurement accuracy, forecast skill or complete station coverage.'}


def save_report(report, directory=DATA/'diagnostics'):
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/'live_readiness.json'
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=directory,delete=False,suffix='.tmp') as handle:
        temporary=Path(handle.name)
        json.dump(report,handle,indent=2,allow_nan=False)
    try:
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def main():
    parser=argparse.ArgumentParser(description='Check live prerequisites without modifying source observations.')
    parser.add_argument('--offline',action='store_true',help='Check saved analytical outputs only')
    args=parser.parse_args()
    load_dotenv(ROOT/'.env')
    report=build_report(os.getenv('OGD_API_KEY',''),offline=args.offline)
    path=save_report(report)
    for gate in report['gates']:
        print(('PASS' if gate['passed'] else 'BLOCKED')+': '+gate['requirement']+' — '+gate['evidence'])
    print('Saved report:',path)
    return 0 if report['minimum_live_gates_passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
