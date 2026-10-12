"""Selected Delhi PM2.5 sensor feed; separate from government AQI analytics."""
import json
import math
import os
from datetime import datetime,timedelta,timezone
from pathlib import Path
import requests

LOCATION_IDS=(2860223,4663956,4712609,6145551)
API='https://api.openaq.org/v3'


def instant(value):
    result=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if result.tzinfo is None: raise ValueError('Source timezone missing')
    return result.astimezone(timezone.utc)


def pm_value(value):
    if isinstance(value,bool): return None
    try: number=float(value)
    except (TypeError,ValueError): return None
    return number if math.isfinite(number) and number>=0 else None


def request(session,path,params=None):
    try:
        response=session.get(API+'/'+path,params=params,timeout=(5,20))
        response.raise_for_status()
        payload=response.json()
    except (requests.RequestException,ValueError):
        raise RuntimeError('OpenAQ request failed; previous data retained') from None
    if not isinstance(payload,dict) or not isinstance(payload.get('results'),list):
        raise ValueError('OpenAQ response schema changed')
    if not all(isinstance(row,dict) for row in payload['results']):
        raise ValueError('OpenAQ records malformed')
    return payload['results']


def collect(api_key,session=None,now=None):
    if not api_key: raise ValueError('OPENAQ_API_KEY is not configured')
    now=now or datetime.now(timezone.utc)
    session=session or requests.Session()
    session.headers.update({'X-API-Key':api_key,'Accept':'application/json'})
    result={'schema_version':1,'collected_at':now.isoformat(),'locations':[], 'latest':[], 'history':[],
            'scope':'Four selected Delhi AirGradient PM2.5 sensors; not an official city AQI or government monitoring network.'}
    start=now-timedelta(hours=48)
    for location_id in LOCATION_IDS:
        locations=request(session,f'locations/{location_id}')
        if len(locations)!=1 or locations[0]['id']!=location_id: raise ValueError('Location identity changed')
        location=locations[0]
        coordinates=location['coordinates']
        if location['country']['code']!='IN' or not (28.45<=coordinates['latitude']<=28.8 and 77.0<=coordinates['longitude']<=77.35):
            raise ValueError('Selected location is outside the checked Delhi area')
        if location['provider']['name']!='AirGradient': raise ValueError('Provider identity changed')
        licenses=location.get('licenses') or []
        if not any(item.get('name')=='CC BY 4.0' and item.get('dateTo') is None for item in licenses):
            raise ValueError('Current reuse license unavailable')
        sensors=[sensor for sensor in location['sensors'] if sensor['parameter']['name']=='pm25']
        if len(sensors)!=1: raise ValueError('PM2.5 sensor identity ambiguous')
        sensor=sensors[0]; unit=sensor['parameter']['units']
        if unit.replace('µ','u').replace('μ','u').replace('³','3')!='ug/m3': raise ValueError('PM2.5 unit changed')
        meta={key:location.get(key) for key in ['id','name','coordinates','isMonitor','instruments','licenses','provider']}
        meta['source_url']=f'https://explore.openaq.org/locations/{location_id}'
        result['locations'].append(meta)
        common={'location_id':location_id,'sensor_id':sensor['id'],'station':location['name'],'pollutant':'PM2.5','unit':'ug/m3'}
        rows=request(session,f'locations/{location_id}/latest',{'limit':100})
        latest=[row for row in rows if row.get('sensorsId')==sensor['id'] and row.get('locationsId')==location_id]
        if len(latest)>1: raise ValueError('Duplicate latest measurement')
        if latest:
            row=latest[0]; observed=instant(row['datetime']['utc'])
            if observed>now: raise ValueError('Future source measurement')
            result['latest'].append({**common,'value':pm_value(row['value']),'observation_time':observed.isoformat()})
        history=request(session,f'sensors/{sensor["id"]}/hours',
                        {'datetime_from':start.isoformat(),'datetime_to':now.isoformat(),'limit':100})
        if len(history)>=100: raise ValueError('Unexpected hourly window size; no partial publication')
        seen=set()
        for row in history:
            parameter=row['parameter']
            if parameter['name']!='pm25' or parameter['units']!=unit: raise ValueError('Hourly measurement metadata changed')
            period=row['period']; left=instant(period['datetimeFrom']['utc']); right=instant(period['datetimeTo']['utc'])
            if period['interval']!='01:00:00' or right-left!=timedelta(hours=1): raise ValueError('Hourly interval changed')
            if right<start-timedelta(hours=2): raise ValueError('Hourly query returned unrelated historical data')
            if right<start or right>now: continue
            if right in seen: raise ValueError('Duplicate hourly interval')
            seen.add(right)
            flagged=row.get('flagInfo',{}).get('hasFlags',True)
            coverage=row.get('coverage') or {}
            result['history'].append({**common,'value':None if flagged else pm_value(row['value']),
                'interval_start':left.isoformat(),'observation_time':right.isoformat(),
                'flagged':bool(flagged),'percent_complete':coverage.get('percentComplete')})
    return result


def atomic_json(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    os.replace(temporary,path)


def update(directory,api_key,collector=collect):
    directory=Path(directory)
    try:
        payload=collector(api_key)
        atomic_json(directory/'latest.json',payload)
        status={'ok':True,'checked_at':datetime.now(timezone.utc).isoformat(),
                'collected_at':payload['collected_at'],'reason':'Complete selected-sensor collection published'}
    except Exception as error:
        status={'ok':False,'checked_at':datetime.now(timezone.utc).isoformat(),
                'reason':f'Collection failed ({type(error).__name__}); previous measurements retained'}
    atomic_json(directory/'status.json',status)
    return status


if __name__=='__main__':
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1]/'.env')
    status=update(Path(__file__).resolve().parents[1]/'live',os.getenv('OPENAQ_API_KEY',''))
    print(json.dumps(status))
