#!/usr/bin/env python3
"""Loopback-only dashboard. Python standard library; fixed experiment allowlist."""
import copy
import json
import os
from pathlib import Path
import re
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent.parent
STATIC = Path(__file__).resolve().parent / 'static'
sys.path.insert(0, str(STATIC.parent))
from proof import Journal, utc_now
BINARIES = {'race_demo', 'mutex_demo', 'resource_uncontrolled_demo',
            'resource_protected_demo', 'blocking_server', 'epoll_server'}
SCENES = {'safety', 'connections100', 'connections500', 'traffic'}
LOG_LIMIT = 24000


class ExperimentError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ExperimentError(message)


def proc_metrics(pid):
    status = Path('/proc/{}/status'.format(pid)).read_text()
    return {'threads': int(re.search(r'^Threads:\s+(\d+)', status, re.M)[1]),
            'fds': len(list(Path('/proc/{}/fd'.format(pid)).iterdir()))}


def parse_safety(output):
    purchases = re.findall(r'^Successful purchases = (\d+)$', output, re.M)
    tickets = re.findall(r'^Tickets remaining = (-?\d+)$', output, re.M)
    require(len(purchases) == 1 and len(tickets) == 2, 'Missing ticket statistics')
    return {'purchases': int(purchases[0]), 'remaining': int(tickets[-1]),
            'oversold': int(purchases[0]) > 1 or int(tickets[-1]) < 0}


def parse_traffic(output, protected):
    values = {key: int(value) for key, value in
              re.findall(r'^([A-Za-z ]+): (\d+)$', output, re.M)}
    keys = ['Incoming', 'Accepted', 'Processed', 'Rejected', 'Max queue size',
            'Worker threads', 'Pending after drain']
    require(all(key in values for key in keys), 'Missing queue statistics')
    require(values['Incoming'] == 1000 and values['Worker threads'] == 4,
            'Unexpected workload or worker count')
    require(values['Processed'] == values['Accepted'] and
            values['Processed'] + values['Rejected'] == values['Incoming'] and
            values['Pending after drain'] == 0, 'Request conservation failed')
    require(values['Max queue size'] <= 20 if protected else values['Rejected'] == 0,
            'Queue policy invariant failed')
    values['capacity'] = 20 if protected else None
    return values


class Child:
    def __init__(self, argv, label, log_path=None):
        self.label = label
        self.argv = argv
        self.log_path = log_path
        self.log = Path(log_path).open('w+b') if log_path else tempfile.TemporaryFile(mode='w+b')
        self.launch_requested_at = utc_now()
        self.ended_at = None
        self.exit_recorded = False
        self.cleanup = 'not checked'
        try:
            self.process = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL,
                                            stdout=self.log, stderr=subprocess.STDOUT,
                                            start_new_session=True, close_fds=True)
            self.started_at = utc_now()
        except BaseException:
            self.log.close()
            raise

    def output(self):
        # pread does not move the shared output offset used by the child.
        size = os.fstat(self.log.fileno()).st_size
        require(size <= 1024 * 1024, self.label + ': output limit exceeded')
        return os.pread(self.log.fileno(), size, 0).decode('utf-8', errors='replace')

    def terminate(self):
        self.cleanup = 'already exited; reaped'
        if self.process.poll() is None:
            self.cleanup = 'SIGINT; reaped'
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(timeout=2)
                self.cleanup = 'SIGKILL; reaped (graceful shutdown failed)'
                raise ExperimentError(self.label + ': graceful shutdown timed out; force-killed and reaped')


class Dashboard:
    def __init__(self, journal_path=None):
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.worker = None
        self.children = []
        self.state = self.empty()
        self.journal = Journal() if journal_path is None else Journal(journal_path)
        self.run_id = None
        self.run_directory = None
        self.log_paths = []
        self.journal_error = None

    def event(self, kind, **data):
        # Evidence failure must make the run Error, but must NEVER skip cleanup.
        try:
            self.journal.emit(kind, run_id=self.run_id, scene=self.state['scene'], **data)
        except OSError as exc:
            self.journal_error = 'Proof journal write failed: ' + str(exc)

    def record_exit(self, child):
        code = child.process.poll()
        if code is not None and not child.exit_recorded:
            child.ended_at = utc_now()
            self.event('process_exit', name=child.label, pid=child.process.pid,
                       exit_code=code, ended_at=child.ended_at)
            child.exit_recorded = True

    def full_logs(self):
        with self.lock:
            paths = list(self.log_paths)
        return '\n'.join('--- {} ---\n{}'.format(path.name,
                        path.read_bytes().decode('utf-8', errors='replace'))
                        for path in paths)

    @staticmethod
    def empty():
        return {'status': 'Waiting', 'scene': None, 'results': {}, 'logs': '',
                'message': 'Choose a scene and run a real experiment.', 'sampled_at': None,
                'run_id': None}

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.state)

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def result(self, name, value):
        with self.lock:
            self.state['results'][name] = value
            self.state['sampled_at'] = time.time()

    def refresh_logs(self):
        self.update(logs='\n'.join('--- {} (PID {}) ---\n{}'.format(
            c.label, c.process.pid, c.output()) for c in self.children)[-LOG_LIMIT:])

    def start(self, scene):
        require(scene in SCENES, 'Unknown experiment')
        with self.lock:
            require(not self.worker or not self.worker.is_alive(), 'An experiment is already running')
            self.cancel.clear()
            self.state = self.empty()
            self.state.update(status='Running', scene=scene, message='Starting real processes…')
            self.run_id = uuid.uuid4().hex
            self.state['run_id'] = self.run_id
            self.journal_error = None
            self.run_directory = self.journal.path.parent / self.journal.session / self.run_id
            self.log_paths = []
            try:
                self.run_directory.mkdir(parents=True)
                self.event('run_start', status='Running', cwd=str(ROOT))
                require(not self.journal_error, self.journal_error)
            except (OSError, ExperimentError) as exc:
                self.state.update(status='Error', message=str(exc))
                raise ExperimentError(str(exc))
            self.worker = threading.Thread(target=self.run, args=(scene,), daemon=False)
            self.worker.start()

    def stop(self, reset=False):
        # Serialize stop/start so a new run cannot race with an older reset.
        with self.lock:
            self.cancel.set()
            worker = self.worker
        if worker and worker.is_alive():
            worker.join(timeout=15)
            require(not worker.is_alive(), 'Cleanup still in progress; retry shortly')
        with self.lock:
            if reset:
                self.event('reset', status='Waiting')
                self.state = self.empty()

    def check(self):
        require(not self.cancel.is_set(), 'Stopped by presenter; processes cleaned up')
        require(not self.journal_error, self.journal_error)

    def spawn(self, name, args=()):
        self.check()
        require(name in BINARIES or name == 'load_clients.py', 'Command is not allowed')
        if name == 'load_clients.py':
            argv = [sys.executable, '-u', str(ROOT / 'socket-server/load_clients.py')]
        else:
            path = ROOT / 'bin' / name
            require(path.is_file(), 'Missing {}. Run make on Ubuntu first.'.format(name))
            argv = [str(path)]
        log_path = self.run_directory / '{}-{}.log'.format(len(self.children) + 1, name)
        child = Child(argv + list(args), name, log_path)
        self.children.append(child)
        with self.lock:
            self.log_paths.append(log_path)
        self.event('process_start', name=name, pid=child.process.pid, argv=child.argv,
                   started_at=child.started_at, launch_requested_at=child.launch_requested_at,
                   log_path=str(log_path))
        return child

    def until(self, predicate, timeout, message):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.check()
            self.refresh_logs()
            if predicate():
                return
            self.cancel.wait(0.05)
        raise ExperimentError(message)

    def finished(self, child, timeout=12):
        self.until(lambda: child.process.poll() is not None, timeout,
                   child.label + ': timed out')
        self.record_exit(child)
        require(child.process.returncode == 0,
                '{} exited {}; inspect Technical Logs'.format(child.label, child.process.returncode))
        return child.output()

    def run(self, scene):
        self.children = []
        error = None
        try:
            if scene == 'safety':
                for name, key, expected in [('race_demo', 'without', (4, -3)),
                                            ('mutex_demo', 'with', (1, 0))]:
                    child = self.spawn(name)
                    values = parse_safety(self.finished(child))
                    require((values['purchases'], values['remaining']) == expected,
                            'Unexpected ticket result')
                    self.result(key, values)
                    self.event('result', name=name, pid=child.process.pid, values=values,
                               validation='PASS (expected teaching outcome)', source=str(child.log_path))
            elif scene == 'traffic':
                for name, key, protected in [('resource_uncontrolled_demo', 'uncontrolled', False),
                                              ('resource_protected_demo', 'protected', True)]:
                    child = self.spawn(name, ['1000', '0'])
                    values = parse_traffic(self.finished(child), protected)
                    self.result(key, values)
                    self.event('result', name=name, pid=child.process.pid, values=values,
                               validation='PASS (conservation, drain, policy)', source=str(child.log_path))
            else:
                self.connections(100 if scene == 'connections100' else 500)
            self.check()
        except Exception as exc:
            error = str(exc)
        finally:
            self.update(message='Cleaning up experiment processes…')
            cleanup_ok = True
            for child in reversed(self.children):
                detail = ''
                try:
                    child.terminate()
                    if child.label in ('blocking_server', 'epoll_server'):
                        require(child.process.returncode == 0,
                                child.label + ': server shutdown returned nonzero')
                except Exception as exc:
                    detail = str(exc)
                    error = error or 'Cleanup failed: ' + str(exc)
                finally:
                    self.record_exit(child)
                    reaped = child.process.poll() is not None
                    cleanup_ok = cleanup_ok and reaped
                    self.event('process_cleanup', name=child.label, pid=child.process.pid,
                               cleanup='PASS' if reaped else 'FAIL',
                               detail=detail or child.cleanup, exit_code=child.process.returncode)
            try:
                self.refresh_logs()
            except Exception as exc:
                error = error or str(exc)
            for child in self.children:
                child.log.close()
            self.children = []
            error = error or self.journal_error
            self.event('run_end', status='Error' if error else 'Completed',
                       message=error or 'Validated experiment; all children stopped.',
                       cleanup='PASS: all children reaped' if cleanup_ok else 'FAIL: process remains',
                       run_directory=str(self.run_directory))
            error = error or self.journal_error
            self.update(status='Error' if error else 'Completed',
                        message=error or 'Measured results saved. All experiment processes stopped.')

    def connections(self, count):
        require(sys.platform.startswith('linux') and Path('/proc/self/status').is_file(),
                'Connection Rush requires Ubuntu/Linux with /proc. No substitute metrics are shown.')
        specs = [('blocking_server', 8081), ('epoll_server', 8082)] if count == 100 else [('epoll_server', 8082)]
        # Fail without touching other applications when a demo port is occupied.
        for _, port in specs:
            with socket.socket() as probe:
                try:
                    probe.bind(('127.0.0.1', port))
                except OSError:
                    raise ExperimentError('Port {} is in use. Stop your existing demo server first.'.format(port))
        servers = []
        for name, port in specs:
            server = self.spawn(name, [str(port)])

            def ready():
                require(server.process.poll() is None, name + ': failed to start; inspect logs')
                if not re.search(r'(started|listening) on port ' + str(port), server.output()):
                    return False
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=0.3) as sock:
                        sock.sendall(b'BUY\n')
                        data = b''
                        while b'\n' not in data and len(data) < 1024:
                            block = sock.recv(1024)
                            if not block:
                                break
                            data += block
                        require(data == b'REQUEST RECEIVED\n', 'Startup handshake failed')
                    return True
                except OSError:
                    return False

            self.until(ready, 4, name + ': startup timed out')
            baseline = 5 if name == 'epoll_server' else 4
            self.until(lambda: proc_metrics(server.process.pid)['fds'] == baseline,
                       3, name + ': startup probe FD not released')
            servers.append((name, port, server, baseline))
        clients = []
        for name, port, server, baseline in servers:
            client = self.spawn('load_clients.py', [str(count), '--port', str(port),
                                '--idle', '--hold', '8', '--timeout', '2'])
            clients.append((name, server, client, baseline))
        for name, server, client, baseline in clients:
            self.until(lambda: 'Holding ' in client.output() or client.process.poll() is not None,
                       12, name + ': clients did not reach hold phase')
            match = re.search(r'Holding (\d+) sockets', client.output())
            require(match is not None, name + ': no client sockets held; inspect logs')
            connected = int(match[1])
            self.until(lambda: proc_metrics(server.process.pid)['fds'] == baseline + connected,
                       3, name + ': not all client connections were accepted')
            self.result(name, dict(proc_metrics(server.process.pid), connected=connected,
                        failures=count-connected, requested=count, pid=server.process.pid,
                        baseline_fds=baseline, phase='Live / held idle connections'))
        self.update(message='Sampling real Linux processes while idle sockets remain open…')
        next_sample = 0
        deadline = time.monotonic() + 15
        while any(c.process.poll() is None for _, _, c, _ in clients):
            self.check()
            require(time.monotonic() < deadline, 'Load clients timed out')
            sample_now = time.monotonic() >= next_sample
            for name, server, client, baseline in clients:
                require(server.process.poll() is None, name + ': server exited during load')
                # Preserve the last held sample when client teardown begins.
                if sample_now and client.process.poll() is None and 'Closed ' not in client.output():
                    metrics = proc_metrics(server.process.pid)
                    previous = self.snapshot()['results'][name]
                    if metrics['fds'] == baseline + previous['connected']:
                        self.result(name, dict(previous, **metrics))
                        self.event('proc_sample', name=name, pid=server.process.pid,
                                   sampled_at=time.time(), **metrics,
                                   connected=previous['connected'], failures=previous['failures'],
                                   source='/proc/{0}/status + /proc/{0}/fd; {1}'.format(
                                       server.process.pid, client.log_path))
            if sample_now:
                next_sample = time.monotonic() + .75
            self.refresh_logs()
            self.cancel.wait(0.2)
        for name, server, client, baseline in clients:
            output = client.output()
            final = re.search(r'Closed (\d+) client sockets\. Failures: (\d+)', output)
            require(final is not None, name + ': missing final client statistics')
            previous = self.snapshot()['results'][name]
            require(int(final[1]) == previous['connected'], 'Client connection count mismatch')
            self.result(name, dict(previous, failures=int(final[2]), phase='Final held sample / historical'))
            self.until(lambda: proc_metrics(server.process.pid)['fds'] == baseline,
                       3, name + ': disconnected client FD leak')
            self.event('fd_cleanup', name=name, pid=server.process.pid,
                       fds=proc_metrics(server.process.pid)['fds'], baseline_fds=baseline)
            require(client.process.returncode == 0 and int(final[2]) == 0,
                    name + ': connection failures; inspect logs and ulimit -n')


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, data, content_type='application/json; charset=utf-8'):
        body = json.dumps(data).encode() if isinstance(data, dict) else data
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(body)

    def local_request(self):
        expected = '127.0.0.1:{}'.format(self.server.server_port)
        return (self.headers.get('Host') == expected and
                self.headers.get('Origin', 'http://' + expected) == 'http://' + expected)

    def do_GET(self):
        if not self.local_request():
            return self.reply(403, {'error': 'Use the exact 127.0.0.1 dashboard URL'})
        if self.path == '/api/state':
            return self.reply(200, self.server.dashboard.snapshot())
        if self.path == '/api/session':
            return self.reply(200, {'token': self.server.token})
        if self.path == '/api/logs':
            return self.reply(200, self.server.dashboard.full_logs().encode('utf-8'),
                              'text/plain; charset=utf-8')
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8')}
        if self.path not in files:
            return self.reply(404, {'error': 'Not found'})
        name, mime = files[self.path]
        self.reply(200, (STATIC / name).read_bytes(), mime)

    def do_POST(self):
        if not self.local_request() or self.headers.get('X-Demo-Token') != self.server.token:
            return self.reply(403, {'error': 'Invalid local session'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            require(0 <= length <= 256, 'Request body too large')
            self.connection.settimeout(2)
            body = json.loads(self.rfile.read(length) or b'{}')
            require(isinstance(body, dict), 'Expected an object')
            with self.server.actions:
                if self.path == '/api/run':
                    self.server.dashboard.start(body.get('scene'))
                elif self.path in ('/api/stop', '/api/reset'):
                    self.server.dashboard.stop(reset=self.path == '/api/reset')
                else:
                    return self.reply(404, {'error': 'Not found'})
            self.reply(200, self.server.dashboard.snapshot())
        except (ExperimentError, ValueError, TypeError, OSError) as exc:
            self.reply(400, {'error': str(exc)})

    def log_message(self, *args):
        pass


def make_server(port=8765):
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.dashboard = Dashboard()
    server.token = secrets.token_urlsafe(32)
    server.actions = threading.Lock()
    return server


def main():
    server = make_server()
    def shutdown(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, shutdown)
    print('Concert Ticket Rush Dashboard: http://127.0.0.1:8765', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.dashboard.stop()
        server.server_close()


if __name__ == '__main__':
    main()
