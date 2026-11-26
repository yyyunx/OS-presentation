#!/usr/bin/env python3
"""Run checked C++ kernels and publish measured trials as JSON and CSV."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime/performance-lab"
BINARY = ROOT / "bin/systems_lab"

# The primary metric is comparable within one experiment only.
EXPERIMENTS = {
    "cache-locality": ("dependent load", ("sequential", "random")),
    "matrix-traversal": ("element", ("row", "column")),
    "false-sharing": ("counter update", ("packed", "padded")),
    "mutex-atomic": ("counter update", ("mutex", "atomic")),
    "cpu-affinity": ("recurrence step", ("unpinned", "same-cpu", "spread")),
    "memory-alignment": ("element", ("aligned", "offset-4")),
    "simd": ("element", ("scalar", "sse2")),
    "memory-bandwidth": ("payload byte", ("small", "large")),
    "branch-prediction": ("branch input", ("sorted", "shuffled")),
    "context-switch": ("handoff", ("same-cpu", "spread")),
}
PERF_GROUPS = (
    ("{cycles:u,instructions:u}", ("cycles", "instructions")),
    ("cache-misses:u", ("cache-misses",)),
    ("branch-misses:u", ("branch-misses",)),
    ("context-switches", ("context-switches",)),
    ("cpu-migrations", ("cpu-migrations",)),
)
POSITIVE_FIELDS = ("elapsed_ns", "operations", "threads", "peak_rss_bytes")
NONNEGATIVE_FIELDS = ("cpu_ns", "working_set_bytes", "logical_bytes", "voluntary_switches",
                      "involuntary_switches", "checksum", "expected_checksum")


def invoke(argv, timeout=90):
    return subprocess.run(argv, check=False, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, env={**os.environ, "LC_ALL": "C"})


def kernel(argv):
    result = invoke(argv)
    if result.returncode:
        raise RuntimeError(f"{argv[0].name if isinstance(argv[0], Path) else argv[0]}: "
                           f"{result.stderr.strip() or f'exit {result.returncode}'}")
    row = json.loads(result.stdout)
    if row.get("status") == "unavailable" and row.get("reason"):
        return row
    if (row.get("status") != "ok" or row.get("checksum") != row.get("expected_checksum")
            or not all(type(row.get(k)) is int and row[k] > 0 for k in POSITIVE_FIELDS)
            or not all(type(row.get(k)) is int and row[k] >= 0 for k in NONNEGATIVE_FIELDS)):
        raise ValueError("invalid or incorrect kernel result")
    return row


def percentile(ordered, quantile):
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summary(samples):
    ordered = sorted(samples)
    return {
        "n": len(ordered), "median": statistics.median(ordered), "mean": statistics.mean(ordered),
        "stdev": statistics.stdev(ordered) if len(ordered) > 1 else None,
        "p05": percentile(ordered, 0.05), "p95": percentile(ordered, 0.95),
        "p99": percentile(ordered, 0.99),
    }


def sample_metrics(row):
    elapsed = row["elapsed_ns"]
    values = {
        "elapsed_ns": elapsed,
        "ns_per_op": elapsed / row["operations"],
        "ops_per_sec": row["operations"] * 1e9 / elapsed,
        "cpu_utilization_pct": row["cpu_ns"] * 100 / elapsed,
        "peak_rss_bytes": row["peak_rss_bytes"],
        "voluntary_switches": row["voluntary_switches"],
        "involuntary_switches": row["involuntary_switches"],
    }
    if row["logical_bytes"]:
        values["logical_gib_per_sec"] = row["logical_bytes"] * 1e9 / elapsed / (1 << 30)
    return values


def unavailable(reason):
    return {"status": "unavailable", "reason": reason}


def perf_result(process, expected):
    counts = {}
    if process.returncode:
        lines = [line.strip() for line in process.stderr.splitlines() if line.strip()]
        message = next((line for line in lines if line != "Error:" and not line.startswith("WARNING:")),
                       f"perf exited {process.returncode}")
        return {name: unavailable(message) for name in expected}
    for line in process.stderr.splitlines():
        fields = line.strip().split(";")
        if len(fields) < 5:
            continue
        count, _, event, _, running = fields[:5]
        name = event.strip().removesuffix(":u")
        if name in expected:
            try:
                value, percent = int(count), float(running)
                if value < 0 or not 0 < percent <= 100:
                    raise ValueError
                counts[name] = {"status": "ok", "value": value, "running_pct": percent}
            except ValueError:
                counts[name] = unavailable(count.strip() or "perf returned no value")
    return {name: counts.get(name, unavailable("perf did not report this event")) for name in expected}


def perf_command(event, argv):
    return ["perf", "stat", "--no-big-num", "-x", ";", "-e", event, "--", *argv]


def probe_perf(enabled):
    reason = "not requested (use --perf)" if not enabled else "Linux perf executable not found"
    if not enabled or not shutil.which("perf"):
        return {name: unavailable(reason) for _, names in PERF_GROUPS for name in names}, []
    counts = {}
    usable = []
    for event, names in PERF_GROUPS:
        probe = perf_result(invoke(perf_command(event, ["true"]), timeout=10), names)
        counts.update(probe)
        if any(value["status"] == "ok" for value in probe.values()):
            usable.append((event, names))
    return counts, usable


def collect_perf(argv, probe, usable):
    result = dict(probe)
    regrouped = False
    for event, names in usable:
        process = invoke(perf_command(event, argv))
        result.update(perf_result(process, names))
        if "cycles" in names:
            regrouped = "regrouped" in process.stderr
    cycles, instructions = result["cycles"], result["instructions"]
    if not regrouped and cycles["status"] == instructions["status"] == "ok" and cycles["value"] > 0:
        result["ipc"] = {"status": "ok", "value": instructions["value"] / cycles["value"]}
    else:
        result["ipc"] = unavailable("grouped cycles and instructions are required")
    return result


def sys_text(path):
    try:
        return Path(path).read_text(encoding="utf-8").strip()
    except OSError:
        return None


def metadata(binary):
    build = invoke([binary, "--build-info"])
    build.check_returncode()
    info = json.loads(build.stdout)
    allowed = info["allowed_cpus"]
    cpuinfo = sys_text("/proc/cpuinfo") or ""
    cpu_model = next((line.split(":", 1)[1].strip() for line in cpuinfo.splitlines()
                      if ":" in line and line.split(":", 1)[0].strip() in ("model name", "Hardware")),
                     platform.processor() or None)
    sys_cpus = Path("/sys/devices/system/cpu")
    topology = {}
    governors = {}
    for cpu in allowed:
        base = sys_cpus / f"cpu{cpu}"
        topology[str(cpu)] = {key: sys_text(base / "topology" / key)
                              for key in ("physical_package_id", "core_id", "thread_siblings_list")}
        governor = sys_text(base / "cpufreq/scaling_governor")
        if governor is not None:
            governors[str(cpu)] = governor
    cache = []
    if allowed:
        for entry in sorted((sys_cpus / f"cpu{allowed[0]}/cache").glob("index*")):
            cache.append({key: sys_text(entry / key)
                          for key in ("level", "type", "size", "coherency_line_size")})
    distro = platform.freedesktop_os_release().get("PRETTY_NAME") if Path("/etc/os-release").exists() else None
    virt = invoke(["systemd-detect-virt"], timeout=5).stdout.strip() if shutil.which("systemd-detect-virt") else None
    return {
        **info, "cpu_model": cpu_model, "machine": platform.machine(),
        "system": platform.system(), "kernel": platform.release(), "distribution": distro,
        "logical_cpus_visible": os.cpu_count(), "topology": topology, "cache_for_first_allowed_cpu": cache,
        "cpu_governors": governors, "virtualization": virt or None,
        "github_actions": os.environ.get("GITHUB_ACTIONS") == "true",
        "python": platform.python_version(),
        "perf_event_paranoid": sys_text("/proc/sys/kernel/perf_event_paranoid"),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
    }


def collect(args):
    environment = metadata(args.binary)
    started_at = datetime.now(timezone.utc)
    run_id = started_at.strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:12]
    profiles = {name: {
        "operation": EXPERIMENTS[name][0],
        "primary_metric": "logical_gib_per_sec" if name == "memory-bandwidth" else "ns_per_op",
        "variants": {variant: {"trials": []} for variant in EXPERIMENTS[name][1]},
    } for name in args.experiment}
    cases = [(name, variant) for name in args.experiment for variant in EXPERIMENTS[name][1]]
    randomizer = random.Random(args.seed)
    order = []
    for round_index in range(-args.warmups, args.trials):
        round_cases = list(cases)
        randomizer.shuffle(round_cases)
        for name, variant in round_cases:
            series = profiles[name]["variants"][variant]
            if series.get("status") == "unavailable":
                continue
            argv = [args.binary, name, variant, args.profile, str(args.seed)]
            row = kernel(argv)
            phase = "warmup" if round_index < 0 else "trial"
            ordinal = round_index + args.warmups + 1 if round_index < 0 else round_index + 1
            order.append({"phase": phase, "ordinal": ordinal, "experiment": name, "variant": variant})
            if row["status"] == "unavailable":
                if series.get("status") == "ok":
                    raise RuntimeError(f"{name}/{variant} became unavailable during the run: {row['reason']}")
                series.update(row)
            elif round_index >= 0:
                series["status"] = "ok"
                series["trials"].append({"trial": ordinal, **row, **sample_metrics(row)})
    probe, usable = probe_perf(args.perf)
    for name, variants in ((name, item["variants"]) for name, item in profiles.items()):
        print(name, flush=True)
        for variant, series in variants.items():
            if series["status"] == "unavailable":
                print(f"  {variant}: unavailable ({series['reason']})", flush=True)
                continue
            rows = series["trials"]
            series["summary"] = {key: summary([row[key] for row in rows])
                                 for key in sample_metrics(rows[0])}
            series["perf"] = collect_perf([args.binary, name, variant, args.profile, str(args.seed)],
                                          probe, usable)
            key = profiles[name]["primary_metric"]
            print(f"  {variant}: {series['summary'][key]['median']:.4g} {key}", flush=True)
    return {
        "schema_version": 1, "run_id": run_id, "started_at_utc": started_at.isoformat(),
        "settings": {"profile": args.profile, "warmups": args.warmups, "trials": args.trials,
                     "seed": args.seed, "perf_requested": args.perf,
                     "sample_scope": "in-process kernel; process peak RSS",
                     "perf_scope": "separate whole-process run per event group; CPU events user mode",
                     "environment_label": args.environment_label},
        "environment": environment, "order": order, "experiments": profiles,
    }


def csv_rows(report):
    for name, experiment in report["experiments"].items():
        for variant, series in experiment["variants"].items():
            prefix = {"run_id": report["run_id"], "experiment": name, "variant": variant,
                      "operation": experiment["operation"]}
            if series["status"] == "unavailable":
                yield {**prefix, "status": series["status"], "reason": series["reason"]}
            for row in series["trials"]:
                yield {**prefix, **row, "pinned_cpus": ",".join(map(str, row["pinned_cpus"]))}


def write_report(report, destination, publish=False):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".benchmark-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "run"
        staging.mkdir()
        with (staging / "results.json").open("w", encoding="utf-8") as output:
            json.dump(report, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write("\n")
        rows = list(csv_rows(report))
        keys = list(dict.fromkeys(key for row in rows for key in row))
        with (staging / "results.csv").open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, keys)
            writer.writeheader()
            writer.writerows(rows)
        # A completed bundle is visible as one directory rename, never partial files.
        staging.rename(destination)
    if publish:
        with tempfile.TemporaryDirectory(prefix=".dashboard-", dir=RUNTIME) as temporary:
            snapshot = Path(temporary) / "latest.json"
            shutil.copyfile(destination / "results.json", snapshot)
            snapshot.replace(RUNTIME / "latest.json")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", action="append", choices=tuple(EXPERIMENTS),
                        help="choose one experiment (repeatable); default: all")
    parser.add_argument("--profile", choices=("quick", "standard"), default="standard")
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--trials", type=int, default=9)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--perf", action="store_true")
    parser.add_argument("--environment-label", choices=("local", "vm", "ci", "bare-metal"),
                        default="local")
    parser.add_argument("--binary", type=Path, default=BINARY)
    parser.add_argument("--output", type=Path, help="new result directory; default updates the local Dashboard")
    args = parser.parse_args()
    args.experiment = list(dict.fromkeys(args.experiment or EXPERIMENTS))
    args.binary = args.binary.resolve()
    if not (0 <= args.warmups <= 20 and 1 <= args.trials <= 100 and 0 <= args.seed <= 0xFFFFFFFF):
        parser.error("use 0–20 warmups, 1–100 trials and an unsigned 32-bit seed")
    if args.output and args.output.exists():
        parser.error("--output must be a new directory")
    try:
        report = collect(args)
        path = args.output or RUNTIME / "runs" / report["run_id"]
        write_report(report, path, publish=args.output is None)
        print(f"JSON and CSV: {path}")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"benchmark failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
