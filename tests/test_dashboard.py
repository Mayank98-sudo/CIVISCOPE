"""Dashboard regression tests use local runs and never refresh the official API."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.core.config import ROOT,DATA
from src.dashboard.data_access import load_run

APP=str(ROOT/'src/dashboard/app.py')

class DashboardTests(unittest.TestCase):
    def test_every_page_and_filters(self):
        app=AppTest.from_file(APP).run(timeout=45)
        self.assertFalse(app.exception)
        for page in ['Overview','Live AQI','Stations','Forecast','Trends','Risk & Warnings','Spatial Intelligence','Data Quality','Methodology','About']:
            with self.subTest(page=page):
                app.radio(key='navigation').set_value(page).run(timeout=45)
                self.assertFalse(app.exception)
        app.radio(key='navigation').set_value('Trends').run(timeout=45)
        choice=app.selectbox(key='station_filter').options[1]
        app.selectbox(key='station_filter').set_value(choice).run(timeout=45)
        self.assertFalse(app.exception)
        aggregation=next(r for r in app.radio if r.label=='Aggregation')
        aggregation.set_value('Daily').run(timeout=45)
        self.assertFalse(app.exception)
        # Choose another pollutant using its labelled sidebar control.
        control=next(s for s in app.selectbox if s.label=='Pollutant')
        control.set_value(control.options[0]).run(timeout=45)
        self.assertFalse(app.exception)
        app.radio(key='navigation').set_value('Forecast').run(timeout=45)
        control=next(s for s in app.selectbox if s.label=='Forecast horizon (hours)')
        control.set_value(24).run(timeout=45)
        self.assertFalse(app.exception)
    def test_missing_run_graceful(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'CIVISCOPE_DATA_DIR':folder}):
            app=AppTest.from_file(APP).run(timeout=45)
            self.assertFalse(app.exception)
            self.assertTrue(any('Data unavailable' in w.value for w in app.warning))
    def test_corrupt_manifest_graceful(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'CIVISCOPE_DATA_DIR':folder}):
            processed=Path(folder)/'processed'; processed.mkdir()
            (processed/'latest_run.json').write_text('{invalid',encoding='utf-8')
            app=AppTest.from_file(APP).run(timeout=45)
            self.assertFalse(app.exception)
            self.assertTrue(app.warning)
    def test_complete_integrity_manifest_required(self):
        manifest=json.loads((DATA/'processed/latest_run.json').read_text())
        manifest['files'].pop('aqi.csv')
        with self.assertRaises(ValueError): load_run(DATA/'processed',manifest)
    def test_path_escape_rejected(self):
        manifest=json.loads((DATA/'processed/latest_run.json').read_text())
        manifest['directory']='../../'
        with self.assertRaises(ValueError): load_run(DATA/'processed',manifest)

if __name__=='__main__': unittest.main()
