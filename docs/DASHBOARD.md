# Concert Ticket Rush Dashboard

## Start on Ubuntu

From the repository root (the clone may be named `OS-presentation`):

```bash
sudo apt update
sudo apt install build-essential python3
make
make test
make demo-ui
```

Open **http://127.0.0.1:8765** in a browser **inside the same Ubuntu VM**.
Use that exact address, including `127.0.0.1`; do not use `localhost` or a LAN IP.
No pip packages, web framework, npm, remote assets, or internet are needed at runtime.
The controller and all C++ listeners bind only to loopback. The browser is an
experiment interface, not a working ticket shop.

If the VMware shared folder is mounted `noexec`, copy the whole repository into
the VM home directory, then run `make clean`, `make`, and `make test` there.
Do not share a `bin/` directory built on Windows/macOS with the Ubuntu run.

## Three scenes

1. **Ticket Safety → Run experiment.** Four named buyers compete for one ticket
   in the existing `race_demo` and `mutex_demo`. Cards parse the final successful
   purchase and remaining ticket lines. Overselling is derived from those values.
   The race demo uses atomic individual operations plus a teaching rendezvous;
   the complete check-and-decrement operation still needs mutual exclusion.
2. **Connection Rush → 100 idle connections → Run experiment.** The controller
   starts `blocking_server 8081` and `epoll_server 8082`, then one existing
   `load_clients.py` per server with `--idle --hold 8 --timeout 2`.
   It waits for an acknowledged startup probe and its FD cleanup before loading.
   Startup probes send one `BUY` for readiness only; load connections send none.
   It parses connected/closed/failure counts, confirms accepted FD growth, and
   samples `/proc/<pid>/status` Threads and `/proc/<pid>/fd` while sockets are held.
   Dynamic cards and shared-scale bars show threads and total FDs. FDs include
   standard streams, listener, and (for epoll) the epoll instance.
   Optional **500 idle connections · epoll only** uses the same methodology on
   port 8082. It measures waiting connections, never successful purchases.
3. **Traffic Control → Run experiment.** The controller invokes both original
   resource demos with `1000 0`: 1,000 incoming requests, no arrival delay, four
   workers. It checks Processed = Accepted, Processed + Rejected = Incoming,
   Pending after drain = 0, and protected Max Queue ≤ 20. The pending capacity
   excludes up to four requests already in progress. This is an independent local
   request simulation, not network purchasing. Actual rejection and queue peaks
   can vary across runs.

Each scene has Run, Reset, Live Metrics, Conclusion, and collapsed Technical
Logs. **—** means no result has been measured. Running results can be partial;
Completed means validation and process cleanup finished. Completed samples are
explicitly historical, with their sample time. On Error, inspect the message
and logs; never interpret partial cards as a successful experiment. Animation
is labeled conceptual and does not claim to trace measured buyer or queue events.
Technical Logs keep only the last 24,000 characters in the interface.
Switching scenes preserves this browser's earlier results; reloading retains
only the controller's latest experiment. Reset clears all browser cards.

## Stop, reset, and clean up

- **Stop** cancels the active experiment and reaps its processes; it appears as
  Error with a presenter-stop message, preserving evidence.
- **Reset** stops an active run, waits for cleanup, and returns to Waiting with
  empty metrics. Only one experiment runs at a time across browser tabs.
- Use **Ctrl+C** in the `make demo-ui` terminal to stop the controller and its
  owned children. Closing a browser tab does not stop a run; each run is bounded.
- Each run closes idle client sockets, waits for server FDs to return to their
  baseline, and shuts down its servers. SIGINT has a two-second grace period;
  unresponsive children are killed and reaped, with an error. No existing process
  is killed to reclaim a port.
- If 8081/8082 is occupied, stop the previously started terminal demo yourself.
  If 8765 is occupied, stop the earlier Dashboard instance. Do not run two
  Dashboard controllers together.
- `make clean` removes built executables; it does not stop running processes.

The controller has fixed scene names and fixed executable arguments; the API
cannot accept command strings, executable paths, ports, request counts, or shell
flags. It uses no `shell=True`. It validates Host/Origin and a local session token
for mutations, refuses arbitrary static paths, bounds request bodies and logs,
and applies per-stage deadlines. API clients use the same loopback origin.
This classroom server is intended for one presenter on a trusted local machine.

Connection Rush requires Linux with readable `/proc`; unsupported platforms show
an explicit error with no substitute numbers. For 500 connections, both the
server and client processes need sufficient `ulimit -n` (1024 is normally enough).
Failures remain visible and prevent Completed; no automatic limit changes occur.
The controller does not measure CPU use, memory use, throughput, latency, or
context-switch counts, and makes no benchmark claims about them.

## Verify and save real evidence

```bash
make
make test
make test-demo-ui
```

The last command runs Race/Mutex, both 1,000-request simulations, both 100-idle
servers, 500 epoll idle connections, stop/reset during held sockets, and an
occupied-port error. It asserts actual counts, thread/FD relationships, request
conservation, process exit, and reusable ports. It saves full process logs and
measured results to `docs/dashboard-ubuntu-results.json`. Failure returns nonzero
and preserves available evidence. It never installs a fake server or fabricated
`/proc`. The unchanged smoke tests still cover protocol framing, half-close,
reset peers, line limits, 32 idle connections, and graceful shutdown.

The GitHub Actions workflow **Ubuntu dashboard verification** runs the same steps
on Ubuntu 24.04 and uploads `dashboard-measurements`. It also prints a compact
measured summary in its log. See [test record](DASHBOARD_TEST_RESULTS.md) for what
was actually run during this implementation, rather than assuming these commands
already passed.

For the presentation use [the three-minute English script and P14 suggestions](../presentation/Dashboard_3min_Demo_and_P14.md).
