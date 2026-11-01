import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from automation.core import Store
from automation.providers import OfflineProvider
from automation.server import make_server, secrets_from_environment
from tests.test_core import invoice


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.secrets = {"INGEST_TOKEN": "i" * 40, "REVIEWER_A_TOKEN": "a" * 40,
                       "REVIEWER_B_TOKEN": "b" * 40, "AUDIT_KEY": "k" * 40}
        cls.store = Store(str(Path(cls.tmp.name) / "test.sqlite"), cls.secrets["AUDIT_KEY"].encode())
        cls.server = make_server(cls.store, cls.secrets, OfflineProvider(), 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()
        cls.server.server_close()
        cls.tmp.cleanup()

    def request(self, path, body=None, token="INGEST_TOKEN", headers=None, method="POST"):
        h = {"Content-Type": "application/json", "Authorization": "Bearer " + self.secrets.get(token, token)} | (headers or {})
        c = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=3)
        c.request(method, path, body=json.dumps(body or invoice()), headers=h)
        r = c.getresponse(); result = (r.status, json.loads(r.read()), dict(r.headers)); c.close()
        return result

    def test_bad_auth_denied(self):
        self.assertEqual(self.request('/v1/invoices', token='invalid')[0], 401)

    def test_review_token_cannot_ingest(self):
        self.assertEqual(self.request('/v1/invoices', token='REVIEWER_A_TOKEN')[0], 403)

    def test_ingest_token_cannot_review_or_read(self):
        r = self.request('/v1/invoices')[1]
        path = '/v1/jobs/' + r['id']
        self.assertEqual(self.request(path, method='GET')[0], 403)
        self.assertEqual(self.request(path + '/decision', {'decision': 'approve'})[0], 403)

    def test_browser_origin_rebinding_and_query_rejected(self):
        self.assertEqual(self.request('/v1/invoices', headers={'Origin':'https://evil.invalid'})[0], 403)
        self.assertEqual(self.request('/v1/invoices', headers={'Host':'evil.invalid'})[0], 403)
        self.assertEqual(self.request('/v1/invoices?token=x')[0], 404)

    def test_content_type_and_body_limit(self):
        self.assertEqual(self.request('/v1/invoices', headers={'Content-Type':'text/plain'})[0], 415)
        self.assertEqual(self.request('/v1/invoices', {'x': 'x' * 13000})[0], 413)

    def test_complete_review_flow_and_cache_control(self):
        status, result, headers = self.request('/v1/invoices', invoice(event_id='http-demo-001', invoice_ref='http-invoice-001'))
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        path = '/v1/jobs/' + result['id'] + '/decision'
        self.assertEqual(self.request(path, {'decision':'approve'}, token='REVIEWER_A_TOKEN')[1]['state'], 'awaiting_second_review')
        self.assertEqual(self.request(path, {'decision':'approve'}, token='REVIEWER_B_TOKEN')[1]['state'], 'approved')

    def test_configuration_has_no_weak_or_shared_default(self):
        with patch.dict('os.environ', {}, clear=True), self.assertRaises(ValueError):
            secrets_from_environment()
        with patch.dict('os.environ', self.secrets, clear=True):
            self.assertEqual(secrets_from_environment(), self.secrets)
        with patch.dict('os.environ', self.secrets | {'INGEST_TOKEN':self.secrets['REVIEWER_A_TOKEN']}, clear=True), self.assertRaises(ValueError):
            secrets_from_environment()
