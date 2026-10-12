import io
import json
import unittest
from urllib.error import URLError
from unittest.mock import Mock
from scripts.probe_live_source import probe


class CloudProbeTests(unittest.TestCase):
    def test_connection_failure_does_not_expose_key(self):
        result=probe('private-key',Mock(side_effect=URLError(ConnectionRefusedError(111,'refused'))))
        self.assertFalse(result['network_reachable'])
        self.assertNotIn('private-key',json.dumps(result))

    def test_html_is_not_a_live_sample(self):
        response=Mock(status=200)
        response.read.return_value=b'<html>not API records</html>'
        response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        result=probe(opener=Mock(return_value=response))
        self.assertTrue(result['network_reachable'])
        self.assertFalse(result['records_received'])
