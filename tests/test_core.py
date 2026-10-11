"""Offline regression tests. Fabricated fixtures exist only inside these tests."""
import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
import pandas as pd
import requests
from src.core.data import prepare_observations,timestamp,latest_observations
from src.production.aqi_analysis import assess,concentration_index,get_aqi_category,build_aqi
from src.production._forecast import forecast_group,backtest,hourly_series,trailing_history
from src.production.intelligence.station_analysis import build_stations
from src.production.risk.risk_analysis import build_risk
from src.production.warning.warning_analysis import build_warnings
from src.trend_analysis import build_trends
from src.validate_forecast import validate_forecasts
from src.collect_historical import fetch_records
from src.pipeline.run_pipeline import run_pipeline

NOW=timestamp('2026-09-29 12:00:00')


def record(station='Test A',pollutant='PM2.5',value=30,time=None):
    t=timestamp(time) if time is not None else NOW
    return dict(station=station,pollutant_id=pollutant,avg_value=value,last_update=t,collection_time=t,latitude=28.6,longitude=77.2,unit='ug/m3',value_kind='concentration',averaging_hours=24,valid_hours=24)


def history(count=160,station='Test A',value=30):
    return prepare_observations(pd.DataFrame([record(station=station,value=value,time=t) for t in pd.date_range(end=NOW,periods=count,freq='h')]),NOW)[0]

class AQITests(unittest.TestCase):
    def test_published_finite_breakpoints(self):
        for c,v in [(0,0),(30,50),(31,51),(60,100),(61,101),(90,200),(120,300),(250,400)]:
            self.assertEqual(concentration_index(c,'PM2.5').value,v)
    def test_gap_is_explicit_estimate(self):
        r=concentration_index(30.5,'PM2.5'); self.assertEqual(r.value,50.5); self.assertIn('gap',r.reason)
    def test_bad_values(self):
        for v in [None,'NA',float('inf'),-1,float('nan')]:
            self.assertTrue(math.isnan(concentration_index(v,'PM2.5').value))
    def test_no_severe_extrapolation(self):
        r=concentration_index(300,'PM2.5'); self.assertTrue(math.isnan(r.value)); self.assertEqual(r.category,'Severe')
    def test_co_unknown_units(self):
        self.assertTrue(math.isnan(assess(record(pollutant='CO',value=30)).value))
    def test_unknown_meaning(self):
        r=record(); r['value_kind']='unverified'; self.assertTrue(math.isnan(assess(r).value))
    def test_period_diagnostics(self):
        r=record(); r['valid_hours']=2; self.assertEqual(assess(r).status,'Analytical estimate')
    def test_category_invalid(self):
        self.assertEqual(get_aqi_category(float('nan')),'Data unavailable')

class ObservationTests(unittest.TestCase):
    def test_duplicate_retrieval_not_new_observation(self):
        a=record(); b={**a,'collection_time':NOW+pd.Timedelta(minutes=5)}
        df,q=prepare_observations(pd.DataFrame([a,b]),NOW)
        self.assertEqual(len(df),1); self.assertEqual(q['duplicate_observation_keys'],1)
        self.assertEqual(df.collection_time.iloc[0],NOW)
    def test_conflict_is_quarantined(self):
        a=record(); b={**a,'avg_value':60}
        df,q=prepare_observations(pd.DataFrame([a,b]),NOW)
        self.assertTrue(pd.isna(df.avg_value.iloc[0])); self.assertEqual(q['conflicting_records'],2)
    def test_negative_invalid_coordinates_and_missing_station(self):
        a=record(value=-2); a['latitude']=200
        b=record(station='')
        df,q=prepare_observations(pd.DataFrame([a,b]),NOW)
        self.assertEqual(len(df),1); self.assertTrue(pd.isna(df.latitude.iloc[0])); self.assertTrue(pd.isna(df.avg_value.iloc[0]))
    def test_aliases_and_source_datetime(self):
        self.assertEqual(timestamp('08-09-2026 12:00:00').month,9)
        a=record(pollutant='OZONE'); df,_=prepare_observations(pd.DataFrame([a]),NOW)
        self.assertEqual(df.pollutant_id.iloc[0],'O3')
    def test_invalid_latest_does_not_hide_behind_old_value(self):
        df,_=prepare_observations(pd.DataFrame([record(time=NOW-pd.Timedelta(hours=1)),record(value=None)]),NOW)
        self.assertTrue(pd.isna(latest_observations(df).avg_value.iloc[0]))
    def test_schema_rejected(self):
        with self.assertRaises(ValueError): prepare_observations(pd.DataFrame({'x':[1]}),NOW)
    def test_conflicting_units_are_quarantined(self):
        a=record(); b={**a,'unit':'mg/m3'}
        df,q=prepare_observations(pd.DataFrame([a,b]),NOW)
        self.assertTrue(df.avg_value.isna().all())
        self.assertEqual(q['conflicting_records'],2)

class ForecastTests(unittest.TestCase):
    def test_station_specific_forecasts(self):
        a,_=forecast_group(history(value=30),1,NOW); b,_=forecast_group(history(station='Test B',value=80),1,NOW)
        self.assertEqual(a['forecast_value'],30); self.assertEqual(b['forecast_value'],80)
        self.assertEqual(a['forecast_method'],'Naive'); self.assertGreaterEqual(a['validation_samples'],12)
    def test_stale_no_live_forecast(self):
        r,_=forecast_group(history(),1,NOW+pd.Timedelta(days=1))
        self.assertTrue(pd.isna(r['forecast_value'])); self.assertIn('Stale',r['forecast_status'])
    def test_sparse_no_fabrication(self):
        r,_=forecast_group(history(count=5),24,NOW)
        self.assertTrue(pd.isna(r['forecast_value'])); self.assertEqual(r['confidence'],'Unavailable')
    def test_no_future_training(self):
        s=hourly_series(history()); origin=s.index[40]
        before=trailing_history(s,origin); s.loc[s.index>=origin,'avg_value']=9999
        np.testing.assert_array_equal(before,trailing_history(s,origin))
    def test_delayed_publication_excluded(self):
        s=hourly_series(history()); s['collection_time']=NOW+pd.Timedelta(days=1)
        self.assertEqual(len(trailing_history(s,NOW)),0)
    def test_holdout_embargo(self):
        _,v=backtest(hourly_series(history()),6)
        self.assertLess(v[v.split=='Model selection'].target_time.max(),v[v.split=='Held-out evaluation'].origin.min())
    def test_exact_target_matching(self):
        obs=history(count=5); f=pd.DataFrame([dict(station='Test A',pollutant_id='PM2.5',forecast_value=30,forecast_time=NOW-pd.Timedelta(hours=2),last_observation_time=NOW-pd.Timedelta(hours=3),forecast_target_time=NOW,unit='ug/m3',value_kind='concentration')])
        self.assertEqual(len(validate_forecasts(f,obs)),1)
        f.loc[0,'forecast_target_time']=NOW+pd.Timedelta(hours=1)
        self.assertTrue(validate_forecasts(f,obs).empty)
    def test_unsupported_horizon_rejected(self):
        with self.assertRaises(ValueError): forecast_group(history(count=5),0,NOW)
    def test_future_retrievals_cannot_influence_live_model(self):
        group=history()
        group.loc[group.index[-20:],'collection_time']=NOW+pd.Timedelta(days=1)
        r,_=forecast_group(group,1,NOW)
        self.assertTrue(pd.isna(r['forecast_value']))

class IntelligenceTests(unittest.TestCase):
    def test_station_minimum_pollutants(self):
        obs=history(count=2); aqi=build_aqi(obs)
        f=pd.DataFrame(columns=['station','forecast_value'])
        stations=build_stations(obs,aqi,f); self.assertTrue(stations.station_aqi.isna().all())
    def test_different_station_data(self):
        obs,_=prepare_observations(pd.DataFrame([record(station=s,pollutant=p,value=v) for s,v in [('A',30),('B',80)] for p in ['PM2.5','PM10','NO2']]),NOW)
        stations=build_stations(obs,build_aqi(obs),pd.DataFrame(columns=['station','forecast_value']))
        self.assertNotEqual(*stations.station_aqi.tolist())
    def test_unknown_risk_not_low(self):
        obs=history(count=2); obs['value_kind']='unverified'; risk=build_risk(build_aqi(obs),build_trends(obs))
        self.assertTrue(risk.risk_score.isna().all()); self.assertTrue(risk.risk_level.eq('Data unavailable').all())
    def test_gaps_do_not_make_trends(self):
        obs,_=prepare_observations(pd.DataFrame([record(value=10,time=NOW-pd.Timedelta(days=1)),record(value=80)]),NOW)
        self.assertTrue(build_trends(obs).percentage_change.isna().all())
    def test_stale_warning_evidence(self):
        obs,_=prepare_observations(pd.DataFrame([record(time=NOW-pd.Timedelta(days=1))]),NOW)
        warnings=build_warnings(obs,build_aqi(obs),build_trends(obs),NOW)
        self.assertIn('Stale observation',warnings.condition.tolist()); self.assertTrue(warnings.evidence.str.len().gt(0).all())

class IngestionTests(unittest.TestCase):
    def test_retry_limit_and_secret_redaction(self):
        session=Mock(); session.get.side_effect=requests.Timeout('https://example.test/?api-key=SECRET')
        with self.assertRaises(RuntimeError) as e: fetch_records('SECRET',session=session,sleep=lambda _:None)
        self.assertNotIn('SECRET',str(e.exception)); self.assertEqual(session.get.call_count,3)
    def test_invalid_response_schema(self):
        session=Mock(); session.get.return_value.json.return_value={'error':'bad'}
        with self.assertRaises(ValueError): fetch_records('x',session=session,sleep=lambda _:None)
    def test_pagination(self):
        session=Mock(); a=Mock(); b=Mock()
        a.json.return_value={'records':[{**record(),'state':'Delhi','last_update':'29-09-2026 12:00:00','collection_time':'29-09-2026 12:00:00'}],'total':2}
        b.json.return_value={'records':[{**a.json.return_value['records'][0],'station':'B'}],'total':2}
        session.get.side_effect=[a,b]
        self.assertEqual(len(fetch_records('x',session=session,sleep=lambda _:None,limit=1)),2)
    def test_no_network_at_test_import(self):
        import tests.test_api

class PipelineTests(unittest.TestCase):
    def test_atomic_publish_and_failure_preserves_last_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'historical').mkdir()
            payload={'metadata':{'collected_at':NOW.isoformat()},'records':[{**record(),'last_update':NOW.isoformat(),'collection_time':NOW.isoformat()}]}
            (root/'historical'/'delhi_snapshot_20260929_120000.json').write_text(json.dumps(payload),encoding='utf-8')
            directory=run_pipeline(root,now=NOW)
            manifest=(root/'processed'/'latest_run.json').read_text()
            self.assertTrue((directory/'observations.csv').exists())
            with patch('src.pipeline.run_pipeline.build_forecasts',side_effect=ValueError('test failure')):
                with self.assertRaises(ValueError): run_pipeline(root,now=NOW)
            self.assertEqual((root/'processed'/'latest_run.json').read_text(),manifest)

if __name__=='__main__': unittest.main()
