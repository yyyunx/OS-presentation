"""Portable regressions for the Ubuntu smoke-test startup synchronization."""

from contextlib import redirect_stderr
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location(
    "ubuntu_smoke", Path(__file__).with_name("ubuntu_smoke.py"))
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class Peer:
    def __init__(self, replies=None):
        self.replies = list(replies or [b"REQUEST ", b"RECEIVED\n"])
        self.sent = []
        self.acknowledged = False
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, size):
        data = self.replies.pop(0)
        if not self.replies:
            self.acknowledged = True
        return data


class StartupRegressionTests(unittest.TestCase):
    def process(self, *args, **kwargs):
        process = Mock()
        process.pid = 123
        process.returncode = 0
        process.poll.return_value = None
        process.wait.return_value = 0
        kwargs["stdout"].write("TEST SERVER OUTPUT\n")
        kwargs["stdout"].flush()
        return process

    def test_waits_for_reply_and_peer_close_before_reading_fd_baseline(self):
        peer = Peer()

        def count_fds(pid):
            # Before accept, an FD count of 5 can look like a clean epoll server.
            # That count is not a stable baseline until the probe was handled.
            self.assertTrue(peer.acknowledged,
                            "FD baseline read before server handled the startup probe")
            self.assertTrue(peer.closed, "startup client still open")
            return 5

        with patch.object(smoke.subprocess, "Popen", side_effect=self.process), \
             patch.object(smoke.socket, "create_connection", return_value=peer), \
             patch.object(smoke, "fd_count", side_effect=count_fds):
            with smoke.running_server("epoll_server"):
                self.assertEqual(peer.sent, [b"BUY\n"])

    def test_rejects_invalid_startup_response(self):
        peer = Peer([b"WRONG RESPONSE\n"])
        with patch.object(smoke.subprocess, "Popen", side_effect=self.process), \
             patch.object(smoke.socket, "create_connection", return_value=peer), \
             patch.object(smoke, "fd_count", return_value=5), \
             redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(AssertionError, "startup.*reply"):
                with smoke.running_server("epoll_server"):
                    pass

    def test_test_failure_keeps_server_log_even_on_clean_shutdown(self):
        diagnostic = io.StringIO()
        with patch.object(smoke.subprocess, "Popen", side_effect=self.process), \
             patch.object(smoke.socket, "create_connection", return_value=Peer()), \
             patch.object(smoke, "fd_count", return_value=5), \
             redirect_stderr(diagnostic):
            with self.assertRaisesRegex(AssertionError, "simulated FD timeout"):
                with smoke.running_server("epoll_server"):
                    raise AssertionError("simulated FD timeout")
        self.assertIn("TEST SERVER OUTPUT", diagnostic.getvalue())


if __name__ == "__main__":
    unittest.main()
