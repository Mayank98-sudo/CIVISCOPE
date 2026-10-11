import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from src.run_collection import cycle


class MonitorTests(unittest.TestCase):
    def test_blocked_source_preserves_success_and_does_not_publish(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'status.json'
            pipeline=Mock()
            state={'last_success_at':'previous','published_run':'old'}
            cycle(state,path,900,probe=Mock(return_value={'status':'Unavailable','reason':'Connection refused'}),pipeline=pipeline)
            saved=json.loads(path.read_text())
            self.assertEqual(saved['state'],'Connection blocked')
            self.assertEqual(saved['published_run'],'old')
            self.assertEqual(saved['last_success_at'],'previous')
            pipeline.assert_not_called()

    def test_success_publishes_only_complete_run(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)
            (directory/'manifest.json').write_text(json.dumps({'run_id':'new'}))
            pipeline=Mock(return_value=directory)
            state={}
            cycle(state,directory/'status.json',900,probe=Mock(return_value={'status':'Reachable','reason':'Records returned'}),pipeline=pipeline)
            self.assertEqual(state['state'],'Monitoring')
            self.assertEqual(state['published_run'],'new')
            self.assertTrue(state['last_success_at'])
            pipeline.assert_called_once_with(collect=True)

    def test_collection_failure_does_not_leak_exception_or_replace_success(self):
        with tempfile.TemporaryDirectory() as folder:
            state={'published_run':'old','last_success_at':'previous'}
            cycle(state,Path(folder)/'status.json',900,
                  probe=Mock(return_value={'status':'Reachable','reason':'Records returned'}),
                  pipeline=Mock(side_effect=RuntimeError('api-key=secret')))
            self.assertEqual(state['state'],'Collection failed')
            self.assertEqual(state['published_run'],'old')
            self.assertNotIn('secret',json.dumps(state))


if __name__=='__main__': unittest.main()
