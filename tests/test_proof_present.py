"""Synthetic formatting fixtures only; real C++ and /proc covered by integration."""
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'demo-ui'))
from proof_present import PresentationState, FramePrinter, WIDTH, cells, wrapped

ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]')


class PresentationTests(unittest.TestCase):
    def start(self, scene):
        state = PresentationState()
        self.apply(state, 'run_start', scene=scene, cwd='/private/source/project')
        return state

    def apply(self, state, kind, **data):
        event = dict(kind=kind, time='2026-11-08T02:17:00+00:00',
                     run_id='1234567890abcdef1234567890abcdef', scene=state.scene)
        event.update(data)
        state.apply(event)
        return event

    def child(self, state, name, pid=811, args=()):
        self.apply(state, 'process_start', name=name, pid=pid,
                   argv=['/private/source/project/bin/' + name] + list(args),
                   log_path='/private/raw/output.log')

    def assert_frame(self, frame):
        plain = ANSI.sub('', frame)
        self.assertTrue(all(cells(line) <= WIDTH for line in plain.splitlines()), plain)
        self.assertLessEqual(len(plain.splitlines()), 38)
        self.assertNotIn('/private', plain)
        self.assertNotRegex(plain, r'\d{4}-\d\d-\d\dT')
        return plain

    def test_safety_real_fields_and_lifecycle_preserved(self):
        state = self.start('safety')
        self.child(state, 'race_demo')
        self.apply(state, 'result', name='race_demo', pid=811,
                   values={'purchases': 7, 'remaining': -6, 'oversold': True})
        self.apply(state, 'process_exit', pid=811, exit_code=0)
        self.apply(state, 'process_cleanup', pid=811, cleanup='PASS', detail='reaped')
        self.apply(state, 'run_end', status='Completed', message='validated',
                   cleanup='PASS: all children reaped')
        plain = self.assert_frame(state.frame(color=True))
        for expected in ['01 / TICKET SAFETY', './bin/race_demo', 'PID 811',
                         'Exit Code 0', 'Cleanup PASS', 'Purchases 7',
                         'Remaining -6', 'Oversold YES', 'Historical', state.run_id]:
            self.assertIn(expected, plain)
        self.assertIn('\x1b[32m', state.frame(color=True))
        before = state.frame()
        self.assertEqual(state.frame(now=time.time() + 100), before)
        self.apply(state, 'reset')
        self.assertIn('summary retained', state.frame())
        self.assertIn('Purchases 7', state.frame())

    def test_proc_fresh_stale_exit_and_replay_are_distinct(self):
        state = self.start('connections100')
        self.child(state, 'blocking_server', args=['8081'])
        now = time.time()
        event = self.apply(state, 'proc_sample', name='blocking_server', pid=811,
                   connected=37, threads=38, fds=41, failures=2, sampled_at=now)
        fresh = self.assert_frame(state.frame(now=now))
        for value in ['37', '38', '41', 'Failures', 'Blocking LIVE']:
            self.assertIn(value, fresh)
        self.assertNotIn('Blocking LIVE', state.frame(now=now + 3))
        self.assertIn('Blocking Historical', state.frame(now=now + 3))
        state.apply(event, historical=True)
        self.assertNotIn('Blocking LIVE', state.frame(now=now))
        state.apply(event)
        self.apply(state, 'process_exit', pid=811, exit_code=0)
        self.assertNotIn('Blocking LIVE', state.frame(now=now))

    def test_traffic_dynamic_conservation_capacity_and_errors(self):
        state = self.start('traffic')
        name = 'resource_protected_demo'
        self.child(state, name, args=['1000', '0'])
        self.apply(state, 'result', name=name, pid=811, values={
            'Incoming': 71, 'Processed': 29, 'Rejected': 42,
            'Max queue size': 9, 'Worker threads': 3, 'capacity': 11})
        plain = self.assert_frame(state.frame())
        for expected in ['Incoming 71', 'Workers 3', 'Processed 29', 'Rejected 42',
                         'Max Queue 9', 'Capacity 11', '29 + 42 = 71 PASS',
                         './bin/resource_protected_demo 1000 0']:
            self.assertIn(expected, plain)
        state.results[name]['Rejected'] = 40
        self.assertIn('29 + 40 = 71 ERROR', state.frame())
        self.apply(state, 'process_exit', pid=811, exit_code=2)
        self.apply(state, 'run_end', status='Error', cleanup='PASS: all children reaped',
                   message='Failure for /private/source/project/bin/resource_protected_demo')
        plain = self.assert_frame(state.frame(color=True))
        self.assertIn('Exit Code 2', plain)
        self.assertIn('partial / failed', plain)
        self.assertIn('\x1b[31m', state.frame(color=True))

    def test_full_connection_panel_commands_fit_without_duplicates(self):
        state = self.start('connections100')
        for pid, name, args in [(811, 'blocking_server', ['8081']), (812, 'epoll_server', ['8082']),
                               (813, 'load_clients.py', ['100', '--port', '8081', '--idle', '--hold', '8', '--timeout', '2']),
                               (814, 'load_clients.py', ['100', '--port', '8082', '--idle', '--hold', '8', '--timeout', '2'])]:
            if name == 'load_clients.py':
                self.apply(state, 'process_start', name=name, pid=pid,
                    argv=['/usr/bin/python3', '-u', '/private/source/project/socket-server/load_clients.py'] + args)
            else:
                self.child(state, name, pid, args)
        frame = self.assert_frame(state.frame())
        self.assertEqual(frame.count('./bin/blocking_server 8081'), 1)
        self.assertEqual(frame.count('python3 socket-server/load_clients.py'), 2)
        stream = io.StringIO()
        printer = FramePrinter(stream, interactive=True)
        self.assertTrue(printer.show(frame, state.run_id))
        before = stream.getvalue()
        self.assertFalse(printer.show(frame, state.run_id))
        self.assertEqual(stream.getvalue(), before)
        printer.show(frame + '\nCompleted', state.run_id)
        self.assertEqual(stream.getvalue().count('\x1b[2J'), 1)

    def test_hostile_controls_and_wide_error_lines_are_bounded(self):
        state = self.start('safety')
        self.apply(state, 'run_end', status='Error', cleanup='FAIL',
                   message='\x1b[2J' + '錯誤' * 90)
        self.assert_frame(state.frame())
        self.assertNotIn('\x1b[2J', state.frame())

    def test_cli_old_journal_historical_and_nonzero_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'journal.jsonl'
            state = self.start('safety')
            start = self.apply(state, 'run_start', scene='safety')
            end = self.apply(state, 'run_end', status='Error', cleanup='PASS', message='real error')
            path.write_text('\n'.join(json.dumps(e) for e in [start, end]) + '\n')
            command = [sys.executable, str(ROOT / 'demo-ui/proof.py'), '--present', '--once',
                       '--color', 'never', '--journal', str(path)]
            output = subprocess.check_output(command, text=True)
            self.assertIn('Historical', output)
            self.assertIn('ERROR', output)
            self.assertNotIn('\x1b', output)
            path.write_text('{invalid}\n')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('ERROR | proof journal unavailable', result.stdout)


if __name__ == '__main__':
    unittest.main()
