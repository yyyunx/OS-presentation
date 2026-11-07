"""Controller boundaries; real binaries are exercised by dashboard_integration.py."""
import http.client
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('dashboard', Path(__file__).resolve().parents[1] / 'demo-ui/controller.py')
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)


class DashboardTests(unittest.TestCase):
    def test_ticket_parser_uses_final_inventory(self):
        values = dashboard.parse_safety('Tickets remaining = 1\nSuccessful purchases = 4\nTickets remaining = -3\n')
        self.assertEqual(values, dict(purchases=4, remaining=-3, oversold=True))
        with self.assertRaises(dashboard.ExperimentError):
            dashboard.parse_safety('Tickets remaining = 1\n')

    def test_traffic_rejects_lost_requests_and_capacity_overflow(self):
        output = 'Incoming: 1000\nAccepted: 400\nProcessed: 400\nRejected: 600\nMax queue size: 20\nWorker threads: 4\nPending after drain: 0\n'
        self.assertEqual(dashboard.parse_traffic(output, True)['Processed'], 400)
        for invalid in (output.replace('Rejected: 600', 'Rejected: 599'),
                        output.replace('Max queue size: 20', 'Max queue size: 21'),
                        output.replace('Pending after drain: 0', 'Pending after drain: 1')):
            with self.assertRaises(dashboard.ExperimentError):
                dashboard.parse_traffic(invalid, True)

    def test_allowlist_and_duplicate_runs(self):
        app = dashboard.Dashboard()
        with self.assertRaises(dashboard.ExperimentError):
            app.start('rm -rf /')
        with self.assertRaises(dashboard.ExperimentError):
            app.spawn('/bin/sh')
        with patch.object(app, 'run', side_effect=lambda scene: app.cancel.wait(2)):
            app.start('safety')
            with self.assertRaises(dashboard.ExperimentError):
                app.start('traffic')
            app.stop(reset=True)
        self.assertEqual(app.snapshot()['status'], 'Waiting')
        self.assertEqual(app.snapshot()['results'], {})

    def test_timeout_and_cancel_reap_real_child(self):
        app = dashboard.Dashboard()
        child = dashboard.Child([sys.executable, '-c', 'import time; time.sleep(30)'], 'timeout fixture')
        app.children.append(child)
        try:
            with self.assertRaisesRegex(dashboard.ExperimentError, 'timed out'):
                app.finished(child, timeout=.1)
            app.cancel.set()
            with self.assertRaisesRegex(dashboard.ExperimentError, 'Stopped'):
                app.check()
        finally:
            child.terminate()
            child.log.close()
        self.assertIsNotNone(child.process.poll())

    def test_http_rejects_cross_origin_and_arbitrary_commands(self):
        server = dashboard.make_server(0)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        host = '127.0.0.1:{}'.format(server.server_port)
        def request(method, path, body=None, headers=None):
            conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
            conn.request(method, path, body, headers or {})
            response = conn.getresponse()
            result = response.status, response.read()
            conn.close()
            return result
        try:
            self.assertEqual(request('GET', '/')[0], 200)
            self.assertEqual(request('GET', '/api/state', headers={'Host': 'attacker.invalid'})[0], 403)
            self.assertEqual(request('POST', '/api/run', '{}')[0], 403)
            headers = {'Host': host, 'X-Demo-Token': server.token, 'Origin': 'https://attacker.invalid'}
            self.assertEqual(request('POST', '/api/run', '{}', headers)[0], 403)
            headers['Origin'] = 'http://' + host
            self.assertEqual(request('POST', '/api/run', json.dumps({'scene': 'shell'}), headers)[0], 400)
            self.assertEqual(request('POST', '/api/run', '[]', headers)[0], 400)
            self.assertEqual(request('GET', '/../controller.py')[0], 404)
            self.assertEqual(server.dashboard.snapshot()['results'], {})
        finally:
            server.shutdown()
            thread.join(3)
            server.server_close()


if __name__ == '__main__':
    unittest.main()
