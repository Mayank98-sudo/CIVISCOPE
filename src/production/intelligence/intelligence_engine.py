"""Explicit report schema; no recursive key guessing or fabricated readiness."""

from pathlib import Path as _Path
import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))

from src.core.config import SOURCE_URL


def build_report(stations,forecasts,quality,warnings):
    valid=stations[stations.station_aqi.notna()]
    # A labelled station statistic is not an official Delhi city AQI.
    city_value=float(valid.station_aqi.median()) if len(valid) else None
    return {'schema_version':2,'project':'CIVISCOPE','city':'Delhi','generated_at':quality['generated_at'],
        'latest_observation':quality['latest_observation'],'source':SOURCE_URL,
        'city_summary':{'metric':'Median of eligible current station AQI estimates','value':city_value,'eligible_stations':len(valid),'total_stations':len(stations),'status':'Analytical estimate' if city_value is not None else 'Data unavailable'},
        'forecast_summary':{'available':int(forecasts.forecast_value.notna().sum()),'total':len(forecasts),'status':'Experimental forecasts' if forecasts.forecast_value.notna().any() else 'Data unavailable'},
        'warning_summary':{'active_data_quality':int(((warnings.status=='Active') & (warnings.severity=='Data quality')).sum()),'active_analytical':int(((warnings.status=='Active') & (warnings.severity!='Data quality')).sum())},
        'limitations':['Source value meaning and units must be verified before AQI conversion.','No source values are imputed.','Forecasts require contiguous history and chronological held-out evaluation.','CIVISCOPE risk is not an official health classification.','Missing analytical warnings do not establish safe conditions.']}


def main():
    from src.pipeline.run_pipeline import run_pipeline
    run_pipeline()

if __name__=='__main__':
    main()
