"""Projection view of the SAME durable proof events; no experiments or fake data."""
from datetime import datetime
import re
import shlex
import sys
import time
import unicodedata

WIDTH = 58
COLORS = {'yellow': '33', 'green': '32', 'red': '31', 'gray': '90', 'bold': '1'}
TITLES = {'safety': '01 / TICKET SAFETY',
          'connections100': '02 / CONNECTION RUSH',
          'connections500': '02 / CONNECTION RUSH',
          'traffic': '03 / TRAFFIC CONTROL'}


def clean(value):
    return re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', str(value))


def cells(text):
    return sum(0 if unicodedata.combining(c) else
               2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in text)


def wrapped(text, width=WIDTH):
    text = clean(text)
    if cells(text) <= width:
        return [text]
    words = text.split()
    lines, line = [], ''
    for word in words:
        if line and cells(line + ' ' + word) > width:
            lines.append(line)
            line = ''
        while cells(word) > width:
            chunk = ''
            while word and cells(chunk + word[0]) <= width:
                chunk, word = chunk + word[0], word[1:]
            lines.append(chunk)
        line = (line + ' ' + word).strip()
    if line:
        lines.append(line)
    return lines or ['']


def clock(value):
    if value is None:
        return '--:--'
    if isinstance(value, (float, int)):
        stamp = datetime.fromtimestamp(value).astimezone()
    else:
        stamp = datetime.fromisoformat(value).astimezone()
    return stamp.strftime('%H:%M')


def compact_command(child):
    argv = list(child.get('argv', []))
    if not argv:
        return '--'
    name = child['name']
    if name == 'load_clients.py':
        # Controller's exact fixed argv: python -u <script> <actual arguments>.
        script = next(i for i, arg in enumerate(argv) if str(arg).replace('\\', '/').endswith('/load_clients.py'))
        return shlex.join(['python3', 'socket-server/load_clients.py'] + argv[script + 1:])
    return shlex.join(['./bin/' + name] + argv[1:])


class PresentationState:
    def __init__(self):
        self.run_id = None
        self.scene = None
        self.status = 'Waiting'
        self.children = {}
        self.results = {}
        self.samples = {}
        self.time = None
        self.message = ''
        self.cleanup = None
        self.replay = True
        self.reset = False
        self.cwd = ''

    def apply(self, event, historical=False):
        kind = event['kind']
        if kind == 'run_start':
            self.__init__()
            self.run_id, self.scene = event['run_id'], event['scene']
            self.status = 'Running'
            self.cwd = event.get('cwd', '')
        self.replay = historical
        self.time = event.get('time', self.time)
        if kind == 'process_start':
            self.children[event['pid']] = dict(event, exit_code=None, cleanup=None)
        elif kind in ('process_exit', 'process_cleanup'):
            if event['pid'] in self.children:
                self.children[event['pid']].update(event)
        elif kind == 'result':
            self.results[event['name']] = event['values']
        elif kind == 'proc_sample':
            self.samples[event['name']] = dict(event)
        elif kind == 'run_end':
            self.status = event['status']
            self.message = event['message']
            self.cleanup = event['cleanup']
            aliases = {'without': 'race_demo', 'with': 'mutex_demo',
                       'uncontrolled': 'resource_uncontrolled_demo',
                       'protected': 'resource_protected_demo'}
            for key, value in event.get('results', {}).items():
                name = aliases.get(key, key)
                if 'connected' in value:
                    self.samples.setdefault(name, {}).update(value)
                else:
                    self.results[name] = value
        elif kind == 'reset':
            # Reset is a browser action; keep the last terminal evidence.
            self.reset = True

    def child(self, name):
        return next((c for c in self.children.values() if c['name'] == name), None)

    def frame(self, now=None, color=False):
        now = time.time() if now is None else now
        lines = []

        def add(text='', shade=None):
            for line in wrapped(text):
                lines.append('\x1b[{}m{}\x1b[0m'.format(COLORS[shade], line) if color and shade else line)

        def label(value, missing='--'):
            return missing if value is None else clean(value)

        def process(child):
            if not child:
                add('Not started')
                return
            add(compact_command(child))
            code, cleanup = child.get('exit_code'), child.get('cleanup')
            forced = 'SIGKILL' in child.get('detail', '') or 'force-killed' in child.get('detail', '')
            add('PID {} | Exit Code {} | Cleanup {}'.format(child['pid'], label(code),
                'FORCED' if forced else label(cleanup)),
                'red' if forced or code not in (None, 0) or cleanup == 'FAIL' else None)

        add(TITLES.get(self.scene, 'OS DEMO PROOF / PRESENTATION'), 'bold')
        add('=' * WIDTH, 'gray')
        status = {'Running': 'RUNNING', 'Completed': 'COMPLETED', 'Error': 'ERROR'}.get(self.status, self.status.upper())
        add('{} {}'.format(status, clock(self.time)),
            'green' if self.status == 'Completed' else 'red' if self.status == 'Error' else 'yellow')
        if self.run_id:
            add('Run ' + self.run_id)
        else:
            add('Waiting for Dashboard. No measurements yet.')
            return '\n'.join(lines)
        add()
        if self.scene == 'safety':
            for name, title in [('race_demo', 'WITHOUT MUTEX'), ('mutex_demo', 'WITH MUTEX')]:
                add(title, 'bold')
                process(self.child(name))
                values = self.results.get(name)
                if values:
                    add('Purchases {} | Remaining {} | Oversold {}'.format(
                        values['purchases'], values['remaining'], 'YES' if values['oversold'] else 'NO'))
                else:
                    add('Purchases -- | Remaining -- | Oversold --')
                add()
        elif self.scene and self.scene.startswith('connections'):
            names = ['blocking_server', 'epoll_server'] if self.scene == 'connections100' else ['epoll_server']
            add('LINUX /proc - HELD IDLE CONNECTIONS', 'bold')
            add('  {:<11}{:<25}{}'.format('', 'BLOCKING' if len(names) == 2 else 'EPOLL', 'EPOLL' if len(names) == 2 else ''))
            for key, title in [('pid', 'PID'), ('connected', 'Connected'), ('threads', 'THREADS'), ('fds', 'FDs'), ('failures', 'Failures')]:
                values = []
                for name in names:
                    sample = self.samples.get(name, {})
                    child = self.child(name)
                    values.append(label(sample.get(key, child['pid'] if child and key == 'pid' else None)))
                add('  {:<11}{:<25}{}'.format(title, values[0], values[1] if len(values) == 2 else ''),
                    'bold' if key == 'threads' else None)
            for name in names:
                sample, child = self.samples.get(name, {}), self.child(name)
                sampled_at = sample.get('sampled_at')
                live = (not self.replay and self.status == 'Running' and sampled_at is not None
                        and 0 <= now - sampled_at <= 2 and child is not None and child.get('exit_code') is None)
                add('{} {} | {}'.format('Blocking' if name == 'blocking_server' else 'epoll',
                    'LIVE' if live else 'Historical' if sampled_at is not None else 'Waiting', clock(sampled_at)),
                    'yellow' if live else 'gray')
            add()
            add('REAL PROCESSES / COMMANDS', 'bold')
            for child in self.children.values():
                process(child)
            add()
        elif self.scene == 'traffic':
            for name, title in [('resource_uncontrolled_demo', 'UNCONTROLLED'), ('resource_protected_demo', 'PROTECTED')]:
                add(title, 'bold')
                process(self.child(name))
                values = self.results.get(name)
                if values:
                    add('Incoming {} | Workers {}'.format(values['Incoming'], values['Worker threads']))
                    add('Processed {} | Rejected {}'.format(values['Processed'], values['Rejected']))
                    add('Max Queue {} | Capacity {}'.format(values['Max queue size'],
                        'unbounded' if values['capacity'] is None else values['capacity']))
                    valid = values['Processed'] + values['Rejected'] == values['Incoming']
                    add('{} + {} = {} {}'.format(values['Processed'], values['Rejected'], values['Incoming'],
                        'PASS' if valid else 'ERROR'), 'green' if valid else 'red')
                else:
                    add('Incoming -- | Processed -- | Rejected --')
                    add('Max Queue -- | Capacity --')
                add()
        if self.status in ('Completed', 'Error'):
            add('SUMMARY / {}'.format(status), 'green' if self.status == 'Completed' else 'red')
            add('Cleanup ' + label(self.cleanup), 'green' if str(self.cleanup).startswith('PASS') else 'red')
            if self.status == 'Error':
                message = self.message.replace(self.cwd, '.') if self.cwd else self.message
                for line in wrapped(message)[:3]:
                    add(line, 'red')
            add('Historical | {} output; not LIVE'.format('completed' if self.status == 'Completed' else 'partial / failed'), 'gray')
        elif self.replay:
            add('Historical | saved events; current state unknown', 'gray')
        else:
            add('RUNNING | waiting for exit and cleanup', 'yellow')
        if self.reset:
            add('Reset: browser cleared; summary retained.', 'gray')
        return '\n'.join(lines)


class FramePrinter:
    def __init__(self, stream, interactive=False):
        self.stream, self.interactive = stream, interactive
        self.previous, self.run_id = None, None

    def show(self, frame, run_id):
        if frame == self.previous:
            return False
        if self.interactive:
            # A new experiment replaces the panel. Completion never clears it.
            self.stream.write('\x1b[2J\x1b[H' if self.previous is None or run_id != self.run_id else '\x1b[H')
            self.stream.write(frame + '\x1b[0J')
        else:
            self.stream.write(frame + '\n\n')
        self.stream.flush()
        self.previous, self.run_id = frame, run_id
        return True


def run_presentation(args, reader_class):
    state = PresentationState()
    interactive = sys.stdout.isatty()
    color = args.color == 'always' or args.color == 'auto' and interactive
    printer = FramePrinter(sys.stdout, interactive)
    reader = reader_class(args.journal)
    try:
        events = reader.read()
        if not args.all:
            starts = [i for i, event in enumerate(events) if event['kind'] == 'run_start']
            if starts:
                events = events[starts[-1]:]
        for event in events:
            if args.all and event['kind'] == 'run_start' and state.run_id:
                printer.show(state.frame(color=color), state.run_id)
            state.apply(event, historical=True)
        printer.show(state.frame(color=color), state.run_id)
        if args.once:
            return 0
        while True:
            for event in reader.read():
                state.apply(event)
            printer.show(state.frame(color=color), state.run_id)
            time.sleep(.1)
    except KeyboardInterrupt:
        print('\nViewer stopped. Dashboard is unaffected.', flush=True)
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print('\nERROR | proof journal unavailable', flush=True)
        print('\n'.join(wrapped(str(exc))), flush=True)
        return 1
