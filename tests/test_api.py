"""Optional live API probe; importing or discovering tests never uses the network."""
import os
import unittest
from src.collect_historical import fetch_records

@unittest.skipUnless(os.getenv('CIVISCOPE_LIVE_API_TEST')=='1','Live API test is opt-in')
class LiveAPITest(unittest.TestCase):
    def test_official_api(self):
        from dotenv import load_dotenv
        from src.core.config import ROOT
        load_dotenv(ROOT/'.env')
        self.assertTrue(fetch_records(os.environ.get('OGD_API_KEY','')))

if __name__=='__main__': unittest.main()
