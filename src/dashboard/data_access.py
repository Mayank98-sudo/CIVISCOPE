"""Verified run loading, independent from Streamlit and its widget lifecycle."""
import hashlib
import json
from pathlib import Path
import pandas as pd

REQUIRED={
 'observations':{'station','pollutant_id','observation_time','avg_value','unit','freshness','latitude','longitude','value_kind','collection_time','quality_status','source_file'},
 'aqi':{'station','pollutant_id','observation_time','avg_value','aqi_sub_index','category','aqi_status','aqi_reason','freshness'},
 'stations':{'station','station_aqi','station_category','aqi_status','latest_measurement','coverage_percent','freshness','dominant_pollutant'},
 'forecasts':{'station','pollutant_id','horizon_hours','forecast_value','forecast_time','forecast_target_time','forecast_status','confidence','MAE','RMSE','MAPE_percent','forecast_method','validation_samples','historical_observations'},
 'trends':{'station','pollutant_id','observation_time','avg_value','trend','percentage_change'},
 'risk':{'station','pollutant_id','observation_time','risk_score','risk_level','components'},
 'warnings':{'timestamp','station','pollutant_id','condition','severity','evidence','status'},
 'coverage':{'station','pollutant_id','coverage_percent'},
 'validation':{'station','pollutant_id','horizon_hours','origin','target_time','method','forecast_value','actual_value','split'},
}


def load_run(processed: Path, manifest: dict):
    if manifest.get('schema_version')!=2:
        raise ValueError('Unsupported analytical schema; refresh required')
    expected={name+'.csv' for name in REQUIRED} | {'quality.json','report.json'}
    if not expected.issubset(manifest.get('files',{})):
        raise ValueError('Manifest is missing required output checksums')
    directory=(processed/manifest['directory']).resolve()
    if not directory.is_relative_to(processed.resolve()):
        raise ValueError('Invalid output directory')
    for name,digest in manifest['files'].items():
        path=(directory/name).resolve()
        if not path.is_relative_to(directory) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise ValueError('Analytical output integrity check failed')
    frames={}
    for name,columns in REQUIRED.items():
        frame=pd.read_csv(directory/f'{name}.csv')
        if not columns.issubset(frame):
            raise ValueError('Required columns unavailable in '+name)
        for col in ['observation_time','collection_time','latest_measurement','forecast_time','forecast_target_time','timestamp','origin','target_time']:
            if col in frame:
                frame[col]=pd.to_datetime(frame[col],errors='coerce',utc=True).dt.tz_convert('Asia/Kolkata')
        frames[name]=frame
    return frames,json.loads((directory/'quality.json').read_text(encoding='utf-8')),json.loads((directory/'report.json').read_text(encoding='utf-8'))
