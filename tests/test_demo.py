import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile
from src.core.config import ROOT
from src.demo import prepare_demo
from src.dashboard.data_access import load_run


class DemoTests(unittest.TestCase):
    def test_clean_start_has_verified_snapshot_and_no_forecasts(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            shutil.copyfile(ROOT/'demo-data.zip',root/'demo-data.zip')
            data,reference=prepare_demo(root)
            manifest=json.loads((data/'processed/latest_run.json').read_text())
            frames,quality,_=load_run(data/'processed',manifest)
            self.assertEqual(quality['unique_observations'],14899)
            self.assertEqual(frames['stations'].station_aqi.notna().sum(),47)
            self.assertEqual(frames['forecasts'].forecast_value.notna().sum(),0)
            self.assertTrue(reference.startswith('2026-10-09'))
            self.assertEqual(prepare_demo(root),(data,reference))

    def test_unexpected_member_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            shutil.copyfile(ROOT/'demo-data.zip',root/'demo-data.zip')
            with zipfile.ZipFile(root/'demo-data.zip','a') as archive:
                archive.writestr('../unexpected.txt','not allowed')
            with self.assertRaises(ValueError):prepare_demo(root)
            self.assertFalse((root/'data').exists())
