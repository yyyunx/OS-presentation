#!/usr/bin/env python3
"""Real Linux C++/proc -> journal -> real terminal transcript; no fake binaries."""
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('proof_controller', ROOT / 'demo-ui/controller.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
from proof import EventReader, render


def wait_for(predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError('Timed out waiting for actual experiment evidence')


def finish(app, expected='Completed'):
    app.worker.join(40)
    assert not app.worker.is_alive(), 'Controller worker did not finish'
    assert app.snapshot()['status'] == expected, app.snapshot()
    assert not app.children


def verify_run(events):
    starts = [e for e in events if e['kind'] == 'process_start']
    for start in starts:
        exits = [e for e in events if e['kind'] == 'process_exit' and e['pid'] == start['pid']]
        clean = [e for e in events if e['kind'] == 'process_cleanup' and e['pid'] == start['pid']]
        assert len(exits) == len(clean) == 1, (start, exits, clean)
        assert exits[0]['ended_at'] >= start['started_at']
        assert clean[0]['cleanup'] == 'PASS'
        assert not Path('/proc/{}'.format(start['pid'])).exists(), 'Child survived cleanup'
        assert Path(start['log_path']).is_file()
    for event in events:
        if event['kind'] == 'result':
            output = Path(event['source']).read_text()
            parsed = (controller.parse_safety(output) if event['scene'] == 'safety' else
                      controller.parse_traffic(output, event['name'] == 'resource_protected_demo'))
            assert parsed == event['values'], 'Terminal differs from real C++ output'
            assert 'PASS' in render(event)
    assert events[-1]['kind'] == 'run_end'
    assert events[-1]['cleanup'].startswith('PASS')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '.runtime/proof-test-results.json')
    args = parser.parse_args()
    evidence = {'platform': platform.platform(), 'tests': [], 'runs': []}
    if not sys.platform.startswith('linux'):
        print('NOT RUN: real C++/proc proof integration requires Linux', flush=True)
        return 2
    with tempfile.TemporaryDirectory(prefix='os-proof-') as directory:
        journal = Path(directory) / 'events.jsonl'
        app = controller.Dashboard(journal)
        reader = EventReader(journal)
        viewer_path = Path(directory) / 'terminal.txt'
        viewer_log = viewer_path.open('w')
        viewer = subprocess.Popen([sys.executable, str(ROOT / 'demo-ui/proof.py'),
                                  '--journal', str(journal)], stdout=viewer_log,
                                  stderr=subprocess.STDOUT)

        def collect(label):
            events = reader.read()
            verify_run(events)
            evidence['runs'].append({'test': label, 'events': events,
                'raw': {e['log_path']: Path(e['log_path']).read_text() for e in events if e['kind'] == 'process_start'}})
            evidence['tests'].append(label)
            print('PASS ' + label, flush=True)
            return events

        try:
            wait_for(lambda: 'Waiting for Dashboard' in viewer_path.read_text())
            # Deliberately do not read the journal until BOTH short processes exit.
            for scene in ('safety', 'traffic'):
                app.start(scene)
                finish(app)
                events = collect('late reader: real ' + scene)
                assert len([e for e in events if e['kind'] == 'result']) == 2

            for scene, count in (('connections100', 100), ('connections500', 500)):
                offset = reader.offset
                app.start(scene)
                observed = []

                def sample_observed():
                    observed.extend(reader.read())
                    samples = [e for e in observed if e['kind'] == 'proc_sample']
                    if not samples:
                        return False
                    latest = samples[-1]
                    pid = latest['pid']
                    # Independent reads of real /proc, while sockets are held.
                    actual = controller.proc_metrics(pid)
                    assert (actual['threads'], actual['fds']) == (latest['threads'], latest['fds'])
                    assert latest['connected'] == count and latest['failures'] == 0
                    command = Path('/proc/{}/cmdline'.format(pid)).read_bytes().split(b'\0')[:-1]
                    started = next(e for e in observed if e['kind'] == 'process_start' and e['pid'] == pid)
                    assert [arg.decode() for arg in command] == started['argv']
                    names = {e['name'] for e in samples}
                    return len(samples) >= 4 and len(names) == (2 if count == 100 else 1)

                wait_for(sample_observed)
                finish(app)
                # Re-read complete run for verification and a shareable transcript.
                reader.offset = offset
                events = collect('live /proc and real argv: ' + scene)
                for name in {e['name'] for e in events if e['kind'] == 'proc_sample'}:
                    samples = [e for e in events if e['kind'] == 'proc_sample' and e['name'] == name]
                    gaps = [b['sampled_at'] - a['sampled_at'] for a, b in zip(samples, samples[1:])]
                    assert len(samples) >= 3
                    assert all(.5 <= gap < 2 for gap in gaps), gaps
                    for sample in samples:
                        assert sample['fds'] == count + (5 if name == 'epoll_server' else 4)
                        assert sample['threads'] == (1 if name == 'epoll_server' else count + 1)
                assert len([e for e in events if e['kind'] == 'fd_cleanup']) == (2 if count == 100 else 1)

            app.start('connections100')
            wait_for(lambda: len(app.snapshot()['results']) == 2)
            app.stop()
            assert app.snapshot()['status'] == 'Error'
            collect('cancel during actual held sockets; all children reaped')
            app.stop(reset=True)
            assert app.snapshot()['status'] == 'Waiting'
            assert reader.read()[-1]['kind'] == 'reset'
            app.start('safety')
            finish(app)
            collect('rerun after reset: new run id and real short programs')
            with socket.socket() as occupied:
                occupied.bind(('127.0.0.1', 8081))
                occupied.listen()
                app.start('connections100')
                finish(app, 'Error')
                events = collect('occupied port: visible error, existing listener preserved')
                assert not any(e['kind'] == 'process_start' for e in events)

            class InvalidArguments(controller.Dashboard):
                def spawn(self, name, args=()):
                    return super().spawn(name, ['0'])  # real C++ usage error, no replacement binary

            app = InvalidArguments(journal)
            app.start('traffic')
            finish(app, 'Error')
            events = collect('real C++ nonzero exit: recorded exit 1 and cleanup')
            assert next(e for e in events if e['kind'] == 'process_exit')['exit_code'] == 1
            assert not any(e['kind'] == 'result' for e in events)
            transcript = subprocess.check_output([sys.executable, str(ROOT / 'demo-ui/proof.py'),
                         '--journal', str(journal), '--once', '--all'], text=True)
            assert 'Purchases=4 Remaining=-3 Oversold=YES' in transcript
            assert 'Exit Code=1' in transcript and 'Original outcome=Error' in transcript
            assert 'Client connected' not in transcript and 'Client disconnected' not in transcript
            assert 'LIVE sample' not in transcript and '\x1b[2J' not in transcript
            assert 'Workers=4' in transcript and 'Threads=101' in transcript
            assert 'Threads=1 FDs=505' in transcript
            assert app.full_logs() and 'Usage:' in app.full_logs()
            wait_for(lambda: 'Exit Code=1' in viewer_path.read_text() and
                     'Original outcome=Error' in viewer_path.read_text())
            viewer.send_signal(signal.SIGINT)
            viewer.wait(timeout=3)
            live_transcript = viewer_path.read_text()
            assert 'Running / LIVE sample' in live_transcript
            assert 'Client connected' not in live_transcript
            assert 'Viewer stopped' in live_transcript
            for run in evidence['runs']:
                run_id = run['events'][0]['run_id']
                assert live_transcript.count('id=' + run_id) == 1, run_id
            evidence['terminal_transcript'] = live_transcript
            evidence['historical_replay'] = transcript
            evidence['status'] = 'PASS'
            print('All real terminal proof integration checks passed.', flush=True)
            return 0
        except Exception as exc:
            evidence['status'] = 'FAIL'
            evidence['failure'] = repr(exc)
            raise
        finally:
            app.stop()
            if viewer.poll() is None:
                viewer.send_signal(signal.SIGINT)
                viewer.wait(timeout=3)
            viewer_log.close()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(evidence, indent=2) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
