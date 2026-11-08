#!/usr/bin/env python3
"""Real dashboard experiments + cancellation/port-conflict checks. Ubuntu only.

Writes evidence (including raw process output) to the chosen JSON file.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import socket
import sys
import tempfile
import time

spec = importlib.util.spec_from_file_location('dashboard', Path(__file__).resolve().parents[1] / 'demo-ui/controller.py')
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)


def run(app, scene):
    app.start(scene)
    app.worker.join(45)
    if app.worker.is_alive():
        app.stop()
        raise AssertionError(scene + ': outer deadline exceeded')
    result = app.snapshot()
    print(scene + ': ' + result['status'], flush=True)
    if result['status'] != 'Completed':
        raise AssertionError(result['message'] + '\n' + result['logs'])
    assert not app.children
    return result


def ports_free():
    for port in (8081, 8082):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(('127.0.0.1', port))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='dashboard-results.json')
    args = parser.parse_args()
    evidence = {'platform': platform.platform(), 'time_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'experiments': {}}
    runtime = tempfile.TemporaryDirectory(prefix='dashboard-integration-')
    app = dashboard.Dashboard(Path(runtime.name) / 'events.jsonl')
    try:
        for scene in ('safety', 'traffic'):
            evidence['experiments'][scene] = run(app, scene)
        if not sys.platform.startswith('linux'):
            evidence['linux_status'] = 'NOT RUN: Linux /proc and epoll unavailable'
            print(evidence['linux_status'])
            return 2
        ports_free()
        for scene, count in [('connections100', 100), ('connections500', 500)]:
            result = run(app, scene)
            evidence['experiments'][scene] = result
            for name, values in result['results'].items():
                assert values['connected'] == count and values['failures'] == 0
                assert values['fds'] == values['baseline_fds'] + count
                assert values['threads'] == (1 if name == 'epoll_server' else count + 1)
                assert not Path('/proc/{}'.format(values['pid'])).exists(), 'Server left running'
            ports_free()
        # Stop during actual held connections, then prove immediate reuse works.
        app.start('connections100')
        deadline = time.monotonic() + 15
        while len(app.snapshot()['results']) != 2 and app.worker.is_alive() and time.monotonic() < deadline:
            time.sleep(.05)
        assert len(app.snapshot()['results']) == 2, app.snapshot()
        pids = [v['pid'] for v in app.snapshot()['results'].values()]
        app.stop(reset=True)
        assert app.snapshot()['status'] == 'Waiting' and not app.children
        assert all(not Path('/proc/{}'.format(pid)).exists() for pid in pids)
        ports_free()
        evidence['cancellation'] = 'PASS: stopped held connections, no servers remain, ports reusable'
        with socket.socket() as occupied:
            occupied.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            occupied.bind(('127.0.0.1', 8081))
            occupied.listen()
            app.start('connections100')
            app.worker.join(5)
            assert app.snapshot()['status'] == 'Error'
            assert 'in use' in app.snapshot()['message'] and not app.children
        evidence['port_conflict'] = 'PASS: existing listener preserved; no experiment child launched'
        ports_free()
        evidence['linux_status'] = 'PASS'
        return 0
    except Exception as exc:
        evidence['failure'] = str(exc)
        evidence['failed_state'] = app.snapshot()
        raise
    finally:
        app.stop()
        Path(args.output).write_text(json.dumps(evidence, indent=2) + '\n')
        runtime.cleanup()


if __name__ == '__main__':
    raise SystemExit(main())
