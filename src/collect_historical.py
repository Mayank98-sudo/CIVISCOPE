"""Bounded official OGD retrieval. Failures never publish partial snapshots."""
from __future__ import annotations

from pathlib import Path as _Path
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

import json
import os
import time
from pathlib import Path
import requests
from dotenv import load_dotenv
from src.core.config import ROOT, DATA, API_URL, RESOURCE, SOURCE_URL
from src.core.data import now_local


def fetch_records(api_key: str, session=None, sleep=time.sleep, limit=100, max_pages=200):
    if not api_key:
        raise ValueError('OGD_API_KEY is not configured')
    session=session or requests.Session()
    rows=[]; offset=0; seen_pages=set()
    for _ in range(max_pages):
        payload=None
        for attempt in range(3):
            try:
                response=session.get(API_URL,params={'api-key':api_key,'format':'json','offset':offset,'limit':limit},headers={'Accept':'application/json','User-Agent':'CIVISCOPE/0.2'},timeout=(10,30))
                response.raise_for_status()
                payload=response.json()
                break
            except (requests.RequestException,ValueError) as error:
                # Never interpolate an exception carrying a request URL/API key.
                if attempt==2:
                    status=getattr(getattr(error,'response',None),'status_code',None)
                    reason=f'HTTP {status}' if isinstance(status,int) else type(error).__name__
                    raise RuntimeError(f'OGD request failed after 3 attempts ({reason}); no snapshot published') from None
                sleep(2**attempt)
        if not isinstance(payload,dict) or not isinstance(payload.get('records'),list):
            raise ValueError('OGD response schema changed: records list missing')
        page=payload['records']
        if any(not isinstance(r,dict) for r in page):
            raise ValueError('Invalid OGD record schema')
        if not page:
            if offset < int(payload.get('total',offset)):
                raise ValueError('OGD returned an incomplete page sequence')
            break
        fingerprint=json.dumps(page,sort_keys=True)
        if fingerprint in seen_pages:
            raise ValueError('OGD repeated a page; pagination aborted')
        seen_pages.add(fingerprint)
        for record in page:
            if str(record.get('state','')).strip().lower()=='delhi':
                required={'station','pollutant_id','last_update'}
                if not required.issubset(record) or not ({'avg_value','pollutant_avg'} & set(record)):
                    raise ValueError('OGD station measurement schema changed')
                rows.append(record)
        offset+=len(page)
        total=int(payload.get('total',offset if len(page)<limit else offset+1))
        if offset>=total:
            break
        sleep(.2)
    else:
        raise RuntimeError('OGD page limit exceeded; snapshot withheld')
    if not rows:
        raise ValueError('No Delhi observations returned')
    # Only remove exact duplicates; conflicting keys must remain visible to validation.
    return list({json.dumps(r,sort_keys=True):r for r in rows}.values())


def collect_snapshot(api_key=None,directory: Path=DATA/'historical',session=None):
    load_dotenv(ROOT/'.env')
    records=fetch_records(api_key or os.getenv('OGD_API_KEY',''),session=session)
    now=now_local()
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/f"delhi_snapshot_{now.strftime('%Y%m%d_%H%M%S')}.json"
    payload={'metadata':{'project':'CIVISCOPE','source':SOURCE_URL,'resource':RESOURCE,'collected_at':now.isoformat(),'delhi_records':len(records)},'records':records}
    # Exclusive creation prevents accidental historical overwrite.
    with path.open('x',encoding='utf-8') as f:
        json.dump(payload,f,ensure_ascii=False,indent=2)
    return path


def main():
    try:
        print(f'Saved snapshot: {collect_snapshot().name}')
    except (RuntimeError, ValueError, OSError) as error:
        print(f'Collection failed ({type(error).__name__}); no partial snapshot published.')
        if isinstance(error,RuntimeError):
            print(str(error))
        raise SystemExit(1) from None

if __name__=='__main__':
    main()
