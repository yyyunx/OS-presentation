"""Portable journal/terminal tests; no invented Linux measurements."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PROOF = Path(__file__).resolve().parents[1] / 'demo-ui/proof.py'
spec = importlib.util.spec_from_file_location('proof_test_module', PROOF)
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


class ProofTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'events.jsonl'

    def test_fast_events_survive_late_reader_and_restart(self):
        journal = proof.Journal(self.path)
        journal.emit('run_start', run_id='first', scene='safety', cwd='test')
        journal.emit('process_start', run_id='first', name='race_demo')
        journal.emit('process_exit', run_id='first', exit_code=0)
        reader = proof.EventReader(self.path)
        self.assertEqual([e['sequence'] for e in reader.read()], [1, 2, 3])
        self.assertEqual(reader.read(), [])
        restarted = proof.Journal(self.path)
        restarted.emit('run_start', run_id='second')
        events = reader.read()
        self.assertEqual(events[0]['sequence'], 1)
        self.assertNotEqual(events[0]['session'], journal.session)

    def test_partial_record_not_lost_or_duplicated(self):
        reader = proof.EventReader(self.path)
        self.assertEqual(reader.read(), [])
        self.path.write_bytes(b'{"kind":"a"}\n{"kind":')
        self.assertEqual(reader.read(), [{'kind': 'a'}])
        self.assertEqual(reader.read(), [])
        with self.path.open('ab') as stream:
            stream.write(b'"b"}\n')
        self.assertEqual(reader.read(), [{'kind': 'b'}])

    def test_replacement_is_explicit_error(self):
        proof.Journal(self.path).emit('test')
        reader = proof.EventReader(self.path)
        reader.read()
        self.path.write_bytes(b'')
        with self.assertRaisesRegex(RuntimeError, 'truncated'):
            reader.read()

    def test_historical_replay_never_claims_live_and_retains_error(self):
        journal = proof.Journal(self.path)
        journal.emit('run_start', scene='traffic', run_id='old', cwd='fixture')
        journal.emit('run_end', status='Error', message='nonzero exit', cleanup='PASS',
                     run_id='old', run_directory='fixture')
        output = subprocess.check_output([sys.executable, str(PROOF), '--journal', str(self.path), '--once'], text=True)
        self.assertIn('Historical', output)
        self.assertIn('Original outcome=Error', output)
        self.assertNotIn('\x1b[2J', output)
        self.assertNotIn('LIVE sample', output)

    def test_default_replays_latest_run_all_option_preserves_history(self):
        journal = proof.Journal(self.path)
        for run in ('old', 'new'):
            journal.emit('run_start', scene='safety', run_id=run, cwd='fixture')
        command = [sys.executable, str(PROOF), '--journal', str(self.path), '--once']
        latest = subprocess.check_output(command, text=True)
        self.assertNotIn('id=old', latest)
        self.assertIn('id=new', latest)
        self.assertIn('interrupted controller', latest)
        self.assertIn('id=old', subprocess.check_output(command + ['--all'], text=True))

    def test_controller_journal_error_still_cleans_up(self):
        spec = importlib.util.spec_from_file_location('controller_proof_test', PROOF.with_name('controller.py'))
        controller = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(controller)
        app = controller.Dashboard(self.path)
        # No subprocess fixture: failure after start must preserve Error status.
        with patch.object(app, 'connections', side_effect=OSError('injected read error')):
            app.start('connections100')
            app.worker.join(3)
        self.assertEqual(app.snapshot()['status'], 'Error')
        self.assertEqual(app.children, [])
        self.assertEqual(proof.EventReader(self.path).read()[-1]['status'], 'Error')
        broken = controller.Dashboard(self.path)
        with patch.object(broken.journal, 'emit', side_effect=OSError('disk unavailable')):
            with self.assertRaisesRegex(controller.ExperimentError, 'journal write failed'):
                broken.start('safety')
        self.assertEqual(broken.snapshot()['status'], 'Error')
        self.assertIsNone(broken.worker)


if __name__ == '__main__':
    unittest.main()
