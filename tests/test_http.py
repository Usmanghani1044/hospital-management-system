"""HTTP contract checks against a temporary, fictional database."""
import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from hospital.service import Hospital
from main import make_handler


class HTTPContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = Hospital(Path(self.tmp.name) / 'demo.sqlite3')
        self.service.initialize()
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(self.service, 'test-token'))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, path, method='GET', payload=None, token=True, headers=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        request_headers = {'Content-Type': 'application/json'}
        if token:
            request_headers['X-Demo-Token'] = 'test-token'
        request_headers.update(headers or {})
        connection.request(method, path, body=json.dumps(payload) if payload is not None else None, headers=request_headers)
        response = connection.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        connection.close()
        return result

    def test_page_static_and_snapshot(self):
        status, body, headers = self.request('/')
        self.assertEqual(status, 200)
        self.assertIn(b'test-token', body)
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        for path in ['/app.js', '/style.css']:
            self.assertEqual(self.request(path)[0], 200)
        self.assertEqual(json.loads(self.request('/api/state')[1])['stats']['patients'], 8)

    def test_request_boundaries(self):
        self.assertEqual(self.request('/api/state', token=False)[0], 403)
        self.assertEqual(self.request('/', headers={'Host': 'untrusted.example'})[0], 403)
        self.assertEqual(self.request('/../hospital/service.py')[0], 404)
        self.assertEqual(self.request('/runtime/hospital.sqlite3')[0], 404)
        self.assertEqual(self.request('/api/export/unknown')[0], 400)
        for action in ['unknown', []]:
            self.assertEqual(self.request('/api/action', 'POST', {'action': action, 'payload': {}})[0], 400)

    def test_write_export_and_backup(self):
        data = {'action': 'patient', 'payload': {'name': "O'Brien <demo>", 'dob': '2000-01-01', 'gender': 'Other'}}
        status, body, _ = self.request('/api/action', 'POST', data)
        self.assertEqual(status, 200)
        self.assertGreater(json.loads(body)['id'], 8)
        self.assertIn(b"O'Brien <demo>", self.request('/api/export/patients')[1])
        status, body, _ = self.request('/api/backup')
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(b'SQLite format 3'))


if __name__ == '__main__':
    unittest.main()
