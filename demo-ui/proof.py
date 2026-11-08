#!/usr/bin/env python3
"""Durable controller events and a real-terminal, append-only evidence viewer."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import threading
import time
import uuid

RUNTIME = Path(__file__).resolve().parent.parent / '.runtime' / 'demo-proof'
DEFAULT_JOURNAL = RUNTIME / 'events.jsonl'


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


class Journal:
    """One controller writer; flush each complete event before proceeding.

    The production HTTP bind prevents two controllers using this journal.
    Tests use isolated paths. No rotation/truncation while viewers are attached.
    """
    def __init__(self, path=DEFAULT_JOURNAL):
        self.path = Path(path)
        self.session = uuid.uuid4().hex
        self.sequence = 0
        self.lock = threading.Lock()

    def emit(self, kind, **data):
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            event = dict(data, kind=kind, session=self.session,
                         sequence=self.sequence + 1, time=utc_now(),
                         controller_pid=os.getpid())
            with self.path.open('a', encoding='utf-8', newline='\n') as stream:
                stream.write(json.dumps(event, ensure_ascii=True) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            self.sequence += 1
            return event


class EventReader:
    """Consume complete records, retaining the byte offset of a partial record."""
    def __init__(self, path=DEFAULT_JOURNAL):
        self.path = Path(path)
        self.offset = 0
        self.identity = None

    def read(self):
        try:
            stream = self.path.open('rb')
        except FileNotFoundError:
            return []
        events = []
        with stream:
            stat = os.fstat(stream.fileno())
            identity = (stat.st_dev, stat.st_ino)
            if self.identity is not None and (identity != self.identity or stat.st_size < self.offset):
                raise RuntimeError('Journal replaced/truncated. Restart demo-proof; do not delete an active journal.')
            self.identity = identity
            stream.seek(self.offset)
            while True:
                line = stream.readline()
                if not line.endswith(b'\n'):
                    break
                events.append(json.loads(line))
                self.offset = stream.tell()
        return events


def render(event, historical=False):
    """Format event data only. Never manufacture results or replay as live data."""
    kind = event['kind']
    prefix = 'Historical' if historical else event.get('status', 'Running')
    stamp = event['time']
    name = event.get('name', '')
    pid = event.get('pid', '—')
    head = '[{} {}]'.format(prefix, stamp)
    if kind == 'run_start':
        return '\n{} RUN {} id={}\n  controller PID={} | cwd={}'.format(
            head, event['scene'], event['run_id'], event['controller_pid'], event['cwd'])
    if kind == 'process_start':
        return '{} START {} PID={}\n  CMD {}\n  started={}\n  raw={}'.format(
            head, name, pid, shlex.join(event['argv']), event['started_at'], event['log_path'])
    if kind == 'process_exit':
        return '{} EXIT {} PID={} Exit Code={}\n  ended={} (controller observed exit)'.format(
            head, name, pid, event['exit_code'], event['ended_at'])
    if kind == 'process_cleanup':
        return '{} CLEANUP {} PID={} {} | {}'.format(
            head, name, pid, event['cleanup'], event['detail'])
    if kind == 'fd_cleanup':
        return '{} FD cleanup {} PID={} FDs={} baseline={} PASS'.format(
            head, name, pid, event['fds'], event['baseline_fds'])
    if kind == 'proc_sample':
        # A delayed tail must never call an old /proc observation live.
        age = time.time() - event['sampled_at']
        mode = 'Historical' if historical or age > 2 else 'Running / LIVE sample'
        return '[{} {}] {} PID={} Threads={} FDs={}\n  Connected={} Failures={} | /proc + client stdout | held idle sockets'.format(
            mode, stamp, name, pid, event['threads'], event['fds'],
            event['connected'], event['failures'])
    if kind == 'result':
        values = event['values']
        if event['scene'] == 'safety':
            summary = 'Purchases={} Remaining={} Oversold={}'.format(
                values['purchases'], values['remaining'], 'YES' if values['oversold'] else 'NO')
        else:
            summary = 'Incoming={} Processed={} Rejected={}\n  Max Queue={} Workers={} | {} + {} = {} PASS'.format(
                values['Incoming'], values['Processed'], values['Rejected'],
                values['Max queue size'], values['Worker threads'],
                values['Processed'], values['Rejected'], values['Incoming'])
        return '{} RESULT {} PID={} {}\n  Validation={} | source={}'.format(
            head, name, pid, summary, event['validation'], event['source'])
    if kind == 'run_end':
        summary = []
        for key, values in event.get('results', {}).items():
            if 'purchases' in values:
                name = 'race_demo' if key == 'without' else 'mutex_demo'
                text = '{} Purchases={} Remaining={} Oversold={}'.format(
                    name, values['purchases'], values['remaining'], 'YES' if values['oversold'] else 'NO')
            elif 'Incoming' in values:
                text = '{} Incoming={} Processed={} Rejected={} Max Queue={} Workers={}'.format(
                    key, values['Incoming'], values['Processed'], values['Rejected'],
                    values['Max queue size'], values['Worker threads'])
            else:
                text = '{} PID={} Threads={} FDs={} Connected={} Failures={}'.format(
                    key, values['pid'], values['threads'], values['fds'], values['connected'], values['failures'])
            summary.append('  ' + text)
        return '{} {}: {}\n  Cleanup={} | run={}\n[Historical] Retained measurements; no longer live. Original outcome={}\n{}\n  Full raw output: {}'.format(
            head, event['status'], event['message'], event['cleanup'], event['run_id'],
            event['status'], '\n'.join(summary) or '  No validated result available.', event['run_directory'])
    if kind == 'reset':
        return '{} RESET browser cards; previous terminal evidence retained.'.format(head)
    return '{} {} {}'.format(head, kind, event.get('message', ''))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal', type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument('--once', action='store_true', help='print saved evidence and exit')
    parser.add_argument('--all', action='store_true', help='replay all saved runs (default: latest run)')
    parser.add_argument('--present', action='store_true', help='compact projection panel from the same real events')
    parser.add_argument('--color', choices=('auto', 'always', 'never'), default='auto')
    args = parser.parse_args()
    if args.present:
        from proof_present import run_presentation
        raise SystemExit(run_presentation(args, EventReader))
    reader = EventReader(args.journal)
    print('OS DEMO PROOF | real Terminal | controller events + Linux /proc', flush=True)
    print('Journal: {}\nWaiting for Dashboard. Ctrl+C stops ONLY this viewer. No screen clearing.'.format(args.journal), flush=True)
    try:
        events = reader.read()
        if not args.all:
            starts = [i for i, event in enumerate(events) if event['kind'] == 'run_start']
            if starts:
                events = events[starts[-1]:]
        for event in events:
            print(render(event, historical=True), flush=True)
        if events and events[-1]['kind'] != 'run_end':
            print('[Historical] Replay above is saved evidence, not proof a process is still running.\nWaiting for fresh events; an interrupted controller may have no run_end.', flush=True)
        if args.once:
            return
        active = bool(events and events[-1]['kind'] not in ('run_end', 'reset'))
        last_fresh = time.monotonic()
        stale_notice = False
        while True:
            for event in reader.read():
                print(render(event), flush=True)
                active = event['kind'] not in ('run_end', 'reset')
                last_fresh = time.monotonic()
                stale_notice = False
            if active and not stale_notice and time.monotonic() - last_fresh > 3:
                print('[Historical / stale] No new controller events for 3 seconds.\n  Last output is recorded evidence; current process state and cleanup are unknown until fresh events arrive.', flush=True)
                stale_notice = True
            time.sleep(.1)
    except KeyboardInterrupt:
        print('\nViewer stopped. Dashboard and experiments are unaffected.', flush=True)


if __name__ == '__main__':
    main()
