"""Cloud connectivity diagnostic. Never prints request URLs, keys or response bodies."""
import json
import os
import socket
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

URL='https://api.data.gov.in/resource/3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69'


def probe(api_key='',opener=urlopen):
    report={'checked_at':datetime.now(timezone.utc).isoformat(),
            'network_reachable':False,'records_received':False,'key_configured':bool(api_key),
            'scope':'One sample request; connectivity alone does not establish live monitoring.'}
    params={'format':'json','limit':1,'filters[state]':'Delhi'}
    if api_key: params['api-key']=api_key
    try:
        with opener(Request(URL+'?'+urlencode(params),headers={'Accept':'application/json','User-Agent':'CIVISCOPE/0.2'}),timeout=20) as response:
            status=response.status
            body=response.read(150000)
    except HTTPError as error:
        status=error.code; body=error.read(150000)
    except (URLError,TimeoutError,OSError) as error:
        cause=getattr(error,'reason',error)
        if isinstance(cause,(TimeoutError,socket.timeout)):
            reason='Connection or response timed out'
        elif isinstance(cause,ssl.SSLError): reason='TLS verification failed'
        elif isinstance(cause,ConnectionRefusedError): reason='Connection refused before authentication'
        else: reason='Network connection failed'
        report['reason']=reason
        return report
    report.update(network_reachable=True,http_status=status)
    if status in (401,403):
        report['reason']='HTTP response received; authentication or access rejected'
        return report
    try:
        payload=json.loads(body)
        records=payload.get('records') if isinstance(payload,dict) else None
    except (ValueError,UnicodeError): records=None
    if status==200 and isinstance(records,list) and records and all(isinstance(r,dict) for r in records):
        report.update(records_received=True,sample_count=len(records),reason='Sample records returned',
                      latest_sample_observation=records[0].get('last_update'))
    else: report['reason']='HTTP response received; no valid nonempty records response'
    return report


if __name__=='__main__':
    result=probe(os.getenv('OGD_API_KEY',''))
    Path('live-source-probe.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
