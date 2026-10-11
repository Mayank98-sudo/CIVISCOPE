import unittest
import pandas as pd

from src.import_cpcb import SOURCE, table_records
from src.core.data import prepare_observations
from src.production.aqi_analysis import build_aqi


def table(hours=24):
    start=pd.Timestamp('2026-10-08 00:00')
    rows=[]
    for i in range(hours*4):
        left=start+pd.Timedelta(minutes=15*i)
        rows.append([left.strftime('%d-%m-%Y %H:%M'),(left+pd.Timedelta(minutes=15)).strftime('%d-%m-%Y %H:%M'),'30','1.2','5'])
    return {'metadata':{'source':SOURCE,'state':'Delhi','city':'Delhi','station':'Example, Delhi',
            'collected_at':(start+pd.Timedelta(hours=hours)).tz_localize('Asia/Kolkata').isoformat(),
            'interval_minutes':15,'reported_rows':len(rows)},
            'headers':['Date From⇅','Date To⇅','PM2.5 (µg/m³)⇅','CO (mg/m³)⇅','NO (µg/m³)⇅'],'rows':rows}


class CPCBTests(unittest.TestCase):
    def test_official_hourly_interval_supported(self):
        payload=table(2)
        payload['metadata']['interval_minutes']=60
        payload['rows']=[['08-10-2026 00:00','08-10-2026 01:00','30','1.2','5'],['08-10-2026 01:00','08-10-2026 02:00','40','1.3','6']]
        payload['metadata']['reported_rows']=2
        records,_=table_records(payload)
        self.assertEqual(len(records),4)
        self.assertEqual(records[1]['avg_value'],40)
    def test_correct_units_and_distinct_species(self):
        records,diagnostics=table_records(table(2))
        self.assertEqual(len(records),4)
        self.assertEqual({r['pollutant_id'] for r in records},{'PM2.5','CO'})
        self.assertEqual(diagnostics['unsupported_parameters'],['NO'])
        self.assertEqual(next(r for r in records if r['pollutant_id']=='CO')['unit'],'mg/m3')

    def test_partial_hour_and_future_interval_withheld(self):
        payload=table(2)
        payload['metadata']['collected_at']='2026-10-08T01:30:00+05:30'
        records,diagnostics=table_records(payload)
        self.assertEqual(len(records),2)
        self.assertEqual(diagnostics['excluded_future_intervals'],2)
        self.assertTrue(all(r['last_update']=='2026-10-08T01:00:00+05:30' for r in records))

    def test_missing_quarter_does_not_become_full_hour(self):
        payload=table(2); payload['rows'][0][2]=''
        records,_=table_records(payload)
        first=next(r for r in records if r['pollutant_id']=='PM2.5')
        self.assertIsNone(first['avg_value']); self.assertEqual(first['valid_hours'],0)

    def test_wrong_unit_and_duplicate_intervals_rejected(self):
        payload=table(2); payload['headers'][3]='CO (µg/m³)⇅'
        with self.assertRaises(ValueError):table_records(payload)
        payload=table(2); payload['rows'][1]=payload['rows'][0]
        with self.assertRaises(ValueError):table_records(payload)

    def test_aqi_uses_required_window_without_rewriting_history(self):
        records,_=table_records(table())
        for row in records:row['collection_time']='2026-10-09T00:00:00+05:30'
        observations,_=prepare_observations(pd.DataFrame(records),now='2026-10-09T00:00:00+05:30')
        result=build_aqi(observations)
        pm=result[result.pollutant_id=='PM2.5'].iloc[0]
        co=result[result.pollutant_id=='CO'].iloc[0]
        self.assertEqual(pm.averaging_hours,24); self.assertEqual(pm.valid_hours,24)
        self.assertEqual(co.averaging_hours,8); self.assertEqual(co.valid_hours,8)
        self.assertEqual(pm.aqi_status,'CIVISCOPE calculation')
        self.assertTrue(observations.averaging_hours.eq(1).all())

    def test_insufficient_aqi_window_withheld(self):
        records,_=table_records(table(2))
        observations,_=prepare_observations(pd.DataFrame(records),now='2026-10-08T03:00:00+05:30')
        self.assertTrue(build_aqi(observations).aqi_sub_index.isna().all())


if __name__=='__main__':unittest.main()
