import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import requests
from src.live_feed import instant,pm_value,request,update


class LiveFeedTests(unittest.TestCase):
    def test_bad_measurements_do_not_become_zero(self):
        for value in [None,-1,float('nan'),float('inf'),True,'bad']:
            self.assertIsNone(pm_value(value))
        self.assertEqual(pm_value('50.7'),50.7)

    def test_timezone_is_required(self):
        with self.assertRaises(ValueError): instant('2026-10-12T13:00:00')
        self.assertEqual(instant('2026-10-12T18:30:00+05:30'),instant('2026-10-12T13:00:00Z'))

    def test_request_failure_does_not_expose_key(self):
        session=Mock();session.get.side_effect=requests.ConnectionError('private-token')
        with self.assertRaises(RuntimeError) as error: request(session,'locations/1')
        self.assertNotIn('private-token',str(error.exception))

    def test_failed_collection_preserves_last_successful_feed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'latest.json';path.write_text('previous')
            status=update(folder,'key',Mock(side_effect=ValueError('private-token')))
            self.assertFalse(status['ok']);self.assertEqual(path.read_text(),'previous')
            self.assertNotIn('private-token',json.dumps(status))

    def test_successful_collection_publishes_status(self):
        with tempfile.TemporaryDirectory() as folder:
            payload={'collected_at':'2026-10-12T13:00:00Z'}
            status=update(folder,'key',Mock(return_value=payload))
            self.assertTrue(status['ok'])
            self.assertEqual(json.loads((Path(folder)/'latest.json').read_text()),payload)
