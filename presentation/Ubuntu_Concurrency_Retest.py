#!/usr/bin/env python3
"""Record three real Ubuntu concurrency runs for slide 5. Standard library only."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import re
import statistics
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
project = root if (root / "concurrency/concurrency_demo.cpp").is_file() else root / "ticket-rush-os-demo"
output = Path(__file__).resolve().parent / "ubuntu-concurrency-retest"

def main():
    if platform.system() != "Linux":
        raise SystemExit("Run this file inside the Ubuntu VM, not Windows.")
    os_info = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            os_info[k] = v.strip('"')
    if os_info.get("ID") != "ubuntu":
        raise SystemExit("This measurement is intended for the original Ubuntu VM.")
    output.mkdir(parents=True, exist_ok=True)
    built = subprocess.run(["make", "-B", "bin/concurrency_demo"], cwd=project,
                           text=True, capture_output=True)
    (output / "build.log").write_text(built.stdout + built.stderr)
    if built.returncode:
        print(built.stdout + built.stderr)
        raise SystemExit(built.returncode)
    runs = []
    for run in range(1, 4):
        proc = subprocess.run([str(project / "bin/concurrency_demo")], cwd=project,
                              text=True, capture_output=True, timeout=60)
        (output / ("run-%02d.log" % run)).write_text(proc.stdout + proc.stderr)
        if proc.returncode:
            raise SystemExit("Run %d failed. See the saved log." % run)
        times = re.findall(r"Total execution time:\s*([0-9]+(?:\.[0-9]+)?)\s*ms", proc.stdout)
        if len(times) != 2:
            raise SystemExit("Expected exactly two timing lines. See the saved log.")
        seq, multi = map(float, times)
        if seq <= 0 or multi <= 0:
            raise SystemExit("Invalid elapsed time in output.")
        runs.append({"run": run, "sequential_ms": seq, "multithread_ms": multi})
        print("Run %d: %.2f ms / %.2f ms" % (run, seq, multi), flush=True)
    seq = statistics.median(x["sequential_ms"] for x in runs)
    multi = statistics.median(x["multithread_ms"] for x in runs)
    result = {
        "recorded_at": datetime.datetime.now().astimezone().isoformat(),
        "environment": os_info.get("PRETTY_NAME"),
        "kernel": platform.release(),
        "source_sha256": hashlib.sha256((project / "concurrency/concurrency_demo.cpp").read_bytes()).hexdigest(),
        "measurement": "Median elapsed times over three runs; ratio of those medians",
        "requests": 20, "simulated_wait_ms_per_request": 100,
        "runs": runs,
        "median_sequential_ms": seq,
        "median_multithread_ms": multi,
        "ratio_of_medians": seq / multi,
        "limitation": "Simulated waiting workload, not a CPU-bound throughput benchmark"
    }
    (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print("Saved results to", output / "results.json")
    print("Median sequential: %.2f ms" % seq)
    print("Median multithread: %.2f ms" % multi)
    print("Ratio of medians: %.2fx" % (seq / multi))

if __name__ == "__main__":
    main()
