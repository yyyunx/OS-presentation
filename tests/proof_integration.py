#!/usr/bin/env python3
"""Real Linux C++/proc -> journal -> real terminal transcript; no fake binaries."""
import argparse
import http.client
import importlib.util
import json
from pathlib import Path
import platform
import re
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('proof_controller', ROOT / 'demo-ui/controller.py')
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)
from proof import EventReader, render
from proof_present import PresentationState, cells, WIDTH


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
    panel = PresentationState()
    live_panels = []
    for event in events:
        panel.apply(event)
        if event['kind'] == 'proc_sample':
            frame = panel.frame(now=event['sampled_at'])
            assert 'LIVE' in frame
            for key in ('pid', 'connected', 'threads', 'fds', 'failures'):
                assert str(event[key]) in frame
            live_panels.append(frame)
    final = panel.frame()
    assert panel.run_id in final and 'Historical' in final
    assert all(cells(line) <= WIDTH for line in final.splitlines())
    assert len(final.splitlines()) <= 38
    assert '/tmp/' not in final and '/home/' not in final
    for event in events:
        if event['kind'] == 'result':
            v = event['values']
            if event['scene'] == 'safety':
                assert 'Purchases {}'.format(v['purchases']) in final
                assert 'Remaining {}'.format(v['remaining']) in final
            else:
                assert '{} + {} = {} PASS'.format(v['Processed'], v['Rejected'], v['Incoming']) in final
    return final, live_panels


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
        present_path = Path(directory) / 'presentation.txt'
        present_log = present_path.open('w')
        present = subprocess.Popen([sys.executable, str(ROOT / 'demo-ui/proof.py'), '--present',
                                    '--color', 'always', '--journal', str(journal)],
                                    stdout=present_log, stderr=subprocess.STDOUT)

        def collect(label):
            events = reader.read()
            summary, live = verify_run(events)
            evidence['runs'].append({'test': label, 'events': events,
                'presentation_summary': summary, 'presentation_live_panels': live,
                'raw': {e['log_path']: Path(e['log_path']).read_text() for e in events if e['kind'] == 'process_start'}})
            evidence['tests'].append(label)
            print('PASS ' + label, flush=True)
            return events

        try:
            wait_for(lambda: 'Waiting for Dashboard' in viewer_path.read_text())
            wait_for(lambda: 'Waiting for Dashboard' in present_path.read_text())
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
                    status = Path('/proc/{}/status'.format(pid)).read_text()
                    actual = {'threads': int(re.search(r'^Threads:\s+(\d+)', status, re.M)[1]),
                              'fds': len(list(Path('/proc/{}/fd'.format(pid)).iterdir()))}
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
                        held = int(re.search(r'Holding (\d+) sockets', Path(sample['client_log']).read_text())[1])
                        assert sample['connected'] == held
                        assert sample['fds'] == count + (5 if name == 'epoll_server' else 4)
                        assert sample['threads'] == (1 if name == 'epoll_server' else count + 1)
                assert len([e for e in events if e['kind'] == 'fd_cleanup']) == (2 if count == 100 else 1)
                if count == 500:
                    # Technical Logs' complete-output route retains the noisy raw
                    # output that the native Terminal intentionally summarizes.
                    server = controller.make_server(0, Path(directory) / 'http-events.jsonl')
                    server.dashboard = app
                    thread = threading.Thread(target=server.serve_forever)
                    thread.start()
                    try:
                        connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                        connection.request('GET', '/api/logs')
                        response = connection.getresponse()
                        raw = response.read().decode()
                        connection.close()
                        assert response.status == 200 and raw == app.full_logs()
                        assert len(raw) > controller.LOG_LIMIT
                        assert raw.count('Client connected') == 501  # startup probe + actual clients
                        assert 'Connected clients: 500' in raw and 'Server stopped.' in raw
                        evidence['tests'].append('HTTP complete Technical Logs: all 501 raw connection events retained')
                    finally:
                        server.shutdown()
                        thread.join(3)
                        server.server_close()

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
            wait_for(lambda: 'Exit Code 1' in present_path.read_text() and
                     'partial / failed' in present_path.read_text())
            present.send_signal(signal.SIGINT)
            present.wait(timeout=3)
            projection = present_path.read_text()
            assert 'Blocking LIVE' in projection and 'epoll LIVE' in projection
            assert '\x1b[32m' in projection and '\x1b[31m' in projection
            assert '/home/' not in projection and '/tmp/' not in projection
            assert 'SUMMARY / COMPLETED' in projection
            assert 'SUMMARY / ERROR' in projection
            replay = subprocess.check_output([sys.executable, str(ROOT / 'demo-ui/proof.py'),
                '--present', '--color', 'never', '--once', '--all', '--journal', str(journal)], text=True)
            assert 'Blocking LIVE' not in replay and 'epoll LIVE' not in replay
            assert 'Historical' in replay and 'SUMMARY / ERROR' in replay
            evidence['presentation_transcript'] = projection
            evidence['presentation_historical_replay'] = replay
            evidence['tests'].append('projection mode: real fields, LIVE/Historical, compact width, cancellation/error/rerun')
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
            if present.poll() is None:
                present.send_signal(signal.SIGINT)
                present.wait(timeout=3)
            present_log.close()
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(evidence, indent=2) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
