#!/usr/bin/env python3
"""Phase 2 Linux integration checks. Run from the repository with make test."""

from contextlib import contextmanager
from pathlib import Path
import os
import re
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def wait_until(predicate, message, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError(message() if callable(message) else message)


def fd_count(pid):
    return len(os.listdir("/proc/{}/fd".format(pid)))


def thread_count(pid):
    text = Path("/proc/{}/status".format(pid)).read_text()
    return int(re.search(r"^Threads:\s+(\d+)", text, re.M).group(1))


@contextmanager
def running_server(name):
    # Reserve an unused localhost port briefly, then launch the test server.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    with tempfile.TemporaryFile(mode="w+") as log:
        # File output avoids a full stdout pipe blocking the server during load.
        process = subprocess.Popen([str(ROOT / "bin" / name), str(port)],
                                   stdout=log, stderr=subprocess.STDOUT)
        failed = False
        try:
            def listening():
                require(process.poll() is None, "{} exited during startup".format(name))
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=1) as probe:
                        # connect() only completes the TCP handshake: accept() may
                        # still be pending. Require an application reply first.
                        probe.sendall(b"BUY\n")
                        require(read_lines(probe, 1) == [b"REQUEST RECEIVED"],
                                "{} startup probe reply mismatch".format(name))
                        return True
                except OSError:
                    return False
            wait_until(listening, "{} did not start".format(name))
            base_fds = 5 if name == "epoll_server" else 4
            # The acknowledged probe has now been accepted and its client closed.
            # Only now can this count prove that the server cleaned up its FD.
            # Without the reply, the same count could mean accept is STILL pending,
            # allowing a transient probe FD to inflate check_network's baseline.
            wait_until(lambda: fd_count(process.pid) == base_fds, "startup probe FD leaked")
            yield process, port
        except BaseException:
            failed = True
            raise
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
            shutdown_timed_out = False
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                shutdown_timed_out = True
            log.seek(0)
            output = log.read()
            # Assertion failures matter even if the server exits cleanly afterward.
            if failed or shutdown_timed_out or process.returncode != 0:
                print("\n--- {} server log (last 4000 characters) ---\n{}"
                      .format(name, output[-4000:]), file=sys.stderr)
            if not failed:
                require(not shutdown_timed_out,
                        "{} could not shut down with idle clients".format(name))
                require(process.returncode == 0,
                        "{} exit {}".format(name, process.returncode))


def connect(port):
    sock = socket.create_connection(("127.0.0.1", port), timeout=3)
    sock.settimeout(3)
    return sock


def read_lines(sock, count):
    data = b""
    while data.count(b"\n") < count:
        chunk = sock.recv(4096)
        require(chunk, "EOF before complete replies")
        data += chunk
        require(len(data) <= 65536, "unexpectedly large reply")
    return data.splitlines()


def check_network(name):
    with running_server(name) as (process, port):
        base_fds = fd_count(process.pid)
        # Fragmented request, multiple requests in one write, unknown command,
        # and half-close: buffered responses must be delivered before EOF.
        with connect(port) as sock:
            sock.sendall(b"B")
            time.sleep(0.02)
            sock.sendall(b"UY\nBUY\nNOPE\n")
            sock.shutdown(socket.SHUT_WR)
            require(read_lines(sock, 3) == [b"REQUEST RECEIVED", b"REQUEST RECEIVED",
                                          b"UNKNOWN COMMAND"], "protocol/framing error")
            require(sock.recv(1) == b"", "half-closed client not closed after replies")
        with connect(port) as sock:
            sock.sendall(b"X" * 1025 + b"\n")
            require(read_lines(sock, 1) == [b"ERROR: LINE TOO LONG"], "line limit missing")
        # An abrupt client reset must not terminate the server with SIGPIPE.
        with connect(port) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))
            sock.sendall(b"BUY\n")
        with connect(port) as sock:
            sock.sendall(b"BUY\n")
            require(read_lines(sock, 1) == [b"REQUEST RECEIVED"], "server failed after reset")

        # Drain earlier protocol/reset connections before testing exact FD growth.
        wait_until(lambda: fd_count(process.pid) == base_fds,
                   "{}: previous protocol clients not cleaned up".format(name))

        idle = []
        try:
            for _ in range(32):
                idle.append(connect(port))
            wait_until(lambda: fd_count(process.pid) >= base_fds + 32,
                       lambda: "{}: idle clients not accepted; baseline={}, expected >= {}, observed={}"
                       .format(name, base_fds, base_fds + 32, fd_count(process.pid)))
            if name == "epoll_server":
                require(thread_count(process.pid) == 1, "epoll created per-client threads")
            else:
                wait_until(lambda: thread_count(process.pid) >= 33,
                           "blocking server did not create client threads")
        finally:
            for sock in idle:
                sock.close()
        wait_until(lambda: fd_count(process.pid) == base_fds, "disconnected socket FD leak")

        # Leave idle peers open during SIGINT; workers must be woken and joined.
        idle = [connect(port) for _ in range(4)]
        try:
            wait_until(lambda: fd_count(process.pid) >= base_fds + 4, "shutdown clients not accepted")
            process.send_signal(signal.SIGINT)
            process.wait(timeout=5)
            require(process.returncode == 0, "server shutdown failed")
        finally:
            for sock in idle:
                sock.close()
    print("PASS {}: framing, half-close, reset, 32 idle FDs/threads, cleanup, SIGINT".format(name))


def check_resources(name, incoming):
    result = subprocess.run([str(ROOT / "bin" / name), str(incoming)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            universal_newlines=True, timeout=15)
    require(result.returncode == 0, result.stdout)
    values = dict((key, int(value)) for key, value in
                  re.findall(r"^([A-Za-z ]+): (\d+)$", result.stdout, re.M))
    require(values["Incoming"] == incoming, "incoming count mismatch")
    require(values["Processed"] == values["Accepted"], "admitted work not drained")
    require(values["Processed"] + values["Rejected"] == incoming, "requests lost")
    require(values["Pending after drain"] == 0 and values["Worker threads"] == 4,
            "queue/worker invariant failed")
    if name == "resource_protected_demo":
        require(values["Max queue size"] <= 20, "bounded queue overflow")
    else:
        require(values["Rejected"] == 0, "uncontrolled mode rejected requests")
    print("PASS {}: {}".format(name, values))


def main():
    require(sys.platform.startswith("linux"), "Run these checks in VMware Ubuntu, not Windows.")
    for name in ("socket_server", "blocking_server", "epoll_server"):
        check_network(name)
        for invalid_port in ("0", "65536", "not-a-port"):
            result = subprocess.run([str(ROOT / "bin" / name), invalid_port],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3)
            require(result.returncode != 0, "invalid port accepted")
    for name in ("resource_uncontrolled_demo", "resource_protected_demo"):
        check_resources(name, 1000)
        check_resources(name, 1)
    print("All Phase 2 Ubuntu smoke checks passed.")


if __name__ == "__main__":
    main()
