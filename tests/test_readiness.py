import unittest
from unittest.mock import Mock
import requests

from src.readiness import connection_reason, probe_source, build_report


class ReadinessTests(unittest.TestCase):
    def test_refused_connection_does_not_expose_key(self):
        error=requests.ConnectionError('secret URL api-key=do-not-print')
        error.__cause__=ConnectionRefusedError(10061,'secret network detail')
        session=Mock()
        session.get.side_effect=error
        result=probe_source('do-not-print',session)
        self.assertEqual(result['reason'],'Connection refused before authentication')
        self.assertNotIn('do-not-print',str(result))

    def test_authentication_failure_distinct_from_network(self):
        response=Mock(status_code=403)
        session=Mock()
        session.get.return_value=response
        self.assertEqual(probe_source('secret',session)['reason'],'API authentication rejected')
        response.json.assert_not_called()

    def test_html_success_is_not_api_success(self):
        response=Mock(status_code=200)
        response.json.side_effect=ValueError('secret HTML')
        session=Mock()
        session.get.return_value=response
        self.assertEqual(probe_source('secret',session)['status'],'Unavailable')

    def test_timeout_and_tls_classified(self):
        self.assertEqual(connection_reason(requests.ReadTimeout()),'Connection or response timed out')
        self.assertEqual(connection_reason(requests.exceptions.SSLError()),'TLS verification failed')

    def test_reachable_source_is_not_operational_readiness(self):
        import tempfile
        from pathlib import Path
        response=Mock(status_code=200)
        response.json.return_value={'records':[{'station':'Example'}]}
        session=Mock()
        session.get.return_value=response
        with tempfile.TemporaryDirectory() as folder:
            report=build_report('secret',Path(folder),session)
        self.assertEqual(report['source']['status'],'Reachable')
        self.assertFalse(report['minimum_live_gates_passed'])


if __name__=='__main__':
    unittest.main()
