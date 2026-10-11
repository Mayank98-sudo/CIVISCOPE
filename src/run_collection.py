"""Background official-source monitoring with atomic, credential-free status."""
from pathlib import Path
from datetime import timedelta
import argparse
import json
import os
import sys
import time

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline.run_pipeline import run_pipeline
from dotenv import load_dotenv
from src.core.config import DATA, ROOT
from src.core.data import now_local
from src.readiness import probe_source


def save_status(path, status):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(status,indent=2),encoding='utf-8')
    os.replace(temporary,path)


def cycle(status,path,interval,probe=probe_source,pipeline=run_pipeline):
    """Failures retain the previous run and successful update time."""
    now=now_local()
    status.update(state='Checking source',checked_at=now.isoformat(),
                  next_check_at=(now+timedelta(seconds=interval)).isoformat())
    save_status(path,status)
    result=probe(os.getenv('OGD_API_KEY',''))
    status.update(source_status=result['status'],reason=result['reason'])
    if result['status']!='Reachable':
        status['state']='Connection blocked'
    else:
        status['state']='Collecting and validating'
        save_status(path,status)
        try:
            directory=pipeline(collect=True)
            manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
            status.update(state='Monitoring',last_success_at=now_local().isoformat(),
                          published_run=manifest['run_id'],reason='Complete collection and analytical run published')
        except Exception as error:
            status.update(state='Collection failed',reason=f'Collection or validation failed ({type(error).__name__}); previous run retained')
    finished=now_local()
    status.update(updated_at=finished.isoformat(),next_check_at=(finished+timedelta(seconds=interval)).isoformat())
    save_status(path,status)
    return status


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interval',type=int,default=900,help='Seconds between cycles; minimum 60')
    parser.add_argument('--once',action='store_true')
    args=parser.parse_args()
    if args.interval<60: parser.error('interval must be at least 60 seconds')
    load_dotenv(ROOT/'.env')
    runtime=DATA/'runtime'; runtime.mkdir(parents=True,exist_ok=True)
    lock=(runtime/'monitor.lock').open('a+b')
    lock.seek(0); lock.write(b'0'); lock.flush(); lock.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        print('An official-source collector is already running.')
        lock.close(); return
    path=runtime/'monitor_status.json'
    status={'pid':os.getpid(),'started_at':now_local().isoformat(),'interval_seconds':args.interval,
            'source':'Official OGD API','last_success_at':None,'published_run':None}
    if path.exists():
        try:
            previous=json.loads(path.read_text(encoding='utf-8'))
            for key in ('last_success_at','published_run'): status[key]=previous.get(key)
        except (OSError,ValueError): pass
    try:
        while True:
            cycle(status,path,args.interval)
            print(f"{status['updated_at']} | {status['state']}",flush=True)
            if args.once: break
            time.sleep(args.interval)
    except KeyboardInterrupt: pass
    finally:
        status.update(state='Stopped',updated_at=now_local().isoformat(),next_check_at=None)
        save_status(path,status)
        lock.close()

if __name__ == '__main__':
    main()
