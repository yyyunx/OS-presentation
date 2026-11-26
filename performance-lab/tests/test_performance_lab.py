import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import urlopen

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bench = load("bench", LAB / "bench.py")
controller = load("performance_dashboard_controller", ROOT / "demo-ui/controller.py")


class KernelTests(unittest.TestCase):
    def test_every_variant_matches_reference(self):
        expected = {
            "cache-locality": ("operations", 65536),
            "matrix-traversal": ("operations", 130**2),
            "false-sharing": ("checksum", 40000),
            "mutex-atomic": ("checksum", 40000),
            "cpu-affinity": ("operations", 400000),
            "memory-alignment": ("operations", (32768 + 3) * 4),
            "simd": ("operations", (32768 + 3) * 4),
            "memory-bandwidth": ("logical_bytes", 8 << 20),
            "branch-prediction": ("checksum", 65536),
            "context-switch": ("checksum", 1000),
        }
        optional = {
            ("false-sharing", "packed"), ("false-sharing", "padded"),
            ("cpu-affinity", "spread"), ("cpu-affinity", "same-cpu"),
            ("memory-alignment", "aligned"), ("memory-alignment", "offset-4"), ("simd", "sse2"),
            ("context-switch", "spread"), ("context-switch", "same-cpu"),
        }
        for name, (_, variants) in bench.EXPERIMENTS.items():
            checksums = set()
            for variant in variants:
                with self.subTest(experiment=name, variant=variant):
                    row = bench.kernel([bench.BINARY, name, variant, "quick", "42"])
                    if row["status"] == "unavailable":
                        self.assertIn((name, variant), optional)
                        self.assertTrue(row["reason"])
                        print(f"{name}/{variant}: unavailable ({row['reason']})", flush=True)
                        continue
                    field, value = expected[name]
                    self.assertEqual(row[field], value)
                    if name != "memory-bandwidth":
                        checksums.add(row["checksum"])
                    if name == "memory-alignment":
                        self.assertEqual(row["input_offset_bytes"], 0 if variant == "aligned" else 4)
                    if name == "false-sharing":
                        self.assertEqual(row["cache_line_bytes"], 64)
                        self.assertEqual(row["working_set_bytes"], 64 if variant == "packed" else 128)
                    pinned = row["pinned_cpus"]
                    if variant == "same-cpu":
                        self.assertEqual(len(pinned), 2)
                        self.assertEqual(len(set(pinned)), 1)
                    if variant == "spread" or name == "false-sharing":
                        self.assertEqual(len(set(pinned)), 2)
            self.assertLessEqual(len(checksums), 1, name)

    def test_invalid_inputs(self):
        for name, variant, profile, seed in (
            ("missing", "row", "quick", "1"), ("matrix-traversal", "missing", "quick", "1"),
            ("matrix-traversal", "row", "wrong", "1"), ("matrix-traversal", "row", "quick", "-1"),
            ("matrix-traversal", "row", "quick", "4294967296"),
        ):
            with self.subTest(name=name, variant=variant, profile=profile, seed=seed):
                result = bench.invoke([bench.BINARY, name, variant, profile, seed])
                self.assertNotEqual(result.returncode, 0)


class FrameworkTests(unittest.TestCase):
    def test_statistics_and_units(self):
        result = bench.summary([4, 1, 2, 3])
        self.assertEqual(result["mean"], 2.5)
        self.assertEqual(result["median"], 2.5)
        self.assertAlmostEqual(result["p95"], 3.85)
        self.assertAlmostEqual(result["stdev"], 1.2909944487)
        self.assertIsNone(bench.summary([3])["stdev"])
        metrics = bench.sample_metrics(dict(
            elapsed_ns=1000, cpu_ns=2000, operations=20, peak_rss_bytes=4096,
            logical_bytes=128, voluntary_switches=0, involuntary_switches=1,
        ))
        self.assertEqual(metrics["ns_per_op"], 50)
        self.assertEqual(metrics["ops_per_sec"], 20e6)
        self.assertEqual(metrics["cpu_utilization_pct"], 200)

    def test_perf_availability_and_ipc(self):
        process = SimpleNamespace(returncode=0, stderr=(
            "123;;cycles:u;1000;100.00\n"
            "246;;instructions:u;1000;100.00\n"
            "<not counted>;;cache-misses:u;0;0.00\n"
            "0;;context-switches;1000;100.00\n"
        ))
        measured = bench.perf_result(process, ["cycles", "instructions", "cache-misses", "context-switches"])
        self.assertEqual(measured["cache-misses"]["status"], "unavailable")
        self.assertEqual(measured["context-switches"]["value"], 0)
        self.assertEqual(bench.collect_perf([], measured, [])["ipc"], {"status": "ok", "value": 2.0})
        blocked = bench.perf_result(SimpleNamespace(returncode=255, stderr="Error:\nPermission denied"),
                                    ["cycles", "instructions"])
        self.assertEqual(blocked["cycles"], {"status": "unavailable", "reason": "Permission denied"})
        self.assertNotIn("value", bench.collect_perf([], blocked, [])["ipc"])

    def test_export_and_dashboard_http(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "measured"
            subprocess.run(["python3", str(LAB / "bench.py"), "--experiment", "matrix-traversal",
                            "--profile", "quick", "--warmups", "1", "--trials", "2",
                            "--output", str(path)], check=True, capture_output=True, timeout=30)
            report_file = path / "results.json"
            report = json.loads(report_file.read_text(encoding="utf-8"))
            with (path / "results.csv").open(newline="", encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), 4)
            self.assertEqual(len(report["order"]), 6)
            self.assertEqual({row["run_id"] for row in rows}, {report["run_id"]})
            for series in report["experiments"]["matrix-traversal"]["variants"].values():
                self.assertEqual(series["summary"]["ns_per_op"]["n"], 2)
                self.assertEqual(series["perf"]["cycles"]["status"], "unavailable")
            self.assertTrue(report["environment"]["flags"])
            with patch.object(controller, "PERFORMANCE_REPORTS", (root / "missing.json", report_file)):
                server = controller.make_server(port=0, journal_path=root / "journal.jsonl")
                worker = threading.Thread(target=server.serve_forever)
                worker.start()
                try:
                    url = f"http://127.0.0.1:{server.server_port}"
                    with urlopen(url + "/api/performance", timeout=3) as response:
                        self.assertEqual(json.load(response)["run_id"], report["run_id"])
                    with urlopen(url + "/performance", timeout=3) as response:
                        self.assertIn(b"Computer Systems Performance Lab", response.read())
                    report_file.unlink()
                    with self.assertRaises(HTTPError) as error:
                        urlopen(url + "/api/performance", timeout=3)
                    self.assertEqual(error.exception.code, 404)
                finally:
                    server.shutdown()
                    worker.join(timeout=3)
                    server.server_close()


if __name__ == "__main__":
    unittest.main()
