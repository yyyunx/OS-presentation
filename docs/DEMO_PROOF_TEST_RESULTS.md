# Terminal proof verification — 2026-11-08

## Windows host

- Reviewed controller, static HTML/JS/CSS, Makefile, README, all C++/shared
  headers, load client and existing tests before implementing.
- Six portable journal/terminal regressions passed with Python 3.13:
  `python -m unittest discover -s tests -p test_proof.py -v`.
- Three existing startup synchronization regressions and the three selected
  controller parser/allowlist regressions passed. Syntax compilation passed.
- The existing loopback HTTP test initially hit Windows sandbox WinError 10013;
  rerunning with socket access outside that sandbox passed.
- JavaScript syntax check (`node --check demo-ui/static/app.js`) passed.
- The user has a running VMware Ubuntu 64-bit guest. VMware Tools confirmed
  its IP as `192.168.139.128`, with Windows Host VMnet8 at `192.168.139.1`.
  Windows OpenSSH 9.5 is available. Initial SSH/TCP port 22 attempts were refused;
  after the user installed sshd and corrected public-key setup, SSH successfully
  logged in as uid 1000 `ubuntu`. No password was provided through chat.

## User's actual VMware Ubuntu — all passed over SSH

Tested source commit `08a9ad3e262734d421cdd127838e9570c40d49d5`, directly in
`/mnt/hgfs/presentation/ticket-rush-os-demo` on Ubuntu 24.04.5 LTS x86_64,
Linux `7.0.0-38-generic`, glibc 2.39. Started 2026-11-08 01:57 Asia/Taipei.
No Docker/WSL was used for this verification. Git is not installed in the Guest;
the evidence helper read the shared Git reference and saved source SHA-256 hashes.

| Actual command | Exit | Elapsed | Result |
|---|---:|---:|---|
| `make -B` | 0 | 10.799 s | All nine C++ executables rebuilt |
| `make test` | 0 | 5.675 s | 14 regressions and all original Linux smoke checks |
| `make test-demo-ui` | 0 | 21.557 s | Safety, traffic, 100/500 connections, stop/reset and port conflict |
| `make test-demo-proof` | 0 | 22.332 s | All nine proof checks, actual live viewer and historical replay |

The proof run produced these **historical VMware measurements**:

| Ticket executable | Purchases | Remaining | Oversold |
|---|---:|---:|---|
| race_demo | 4 | -3 | Yes |
| mutex_demo | 1 | 0 | No |

| Held idle connections | Threads | Total FDs | Connected | Failures |
|---|---:|---:|---:|---:|
| Blocking 100 | 101 | 104 | 100 | 0 |
| epoll 100 | 1 | 105 | 100 | 0 |
| epoll 500 | 1 | 505 | 500 | 0 |

| Simulator | Incoming | Processed | Rejected | Max Queue | Workers |
|---|---:|---:|---:|---:|---:|
| Uncontrolled | 1000 | 1000 | 0 | 1000 | 4 |
| Protected | 1000 | 404 | 596 | 20 | 4 |

Both queues drained and conserved requests. Another smoke execution measured
396/604 protected requests; per-run counts vary and must never be hard-coded.
Sampling checked real `/proc` while server PIDs were alive and compared actual
argv, not a saved CI file. Real cancellation, exit 1, reset/rerun and raw-output
retention checks passed. Tests use isolated temporary journals, so unit fixtures
and integration experiments do not pollute the presenter's production journal.

Evidence remains locally in the shared folder (ignored by Git):
`.runtime/vmware/verification.json`, `build.log`, `test.log`, `dashboard.log`,
`proof.log`, and `.runtime/proof-test-results.json` with events, raw output,
live Terminal transcript and historical replay. The existing Dashboard on 8765
still responded after tests; no demo servers/listeners remained on 8081/8082.
That previously running Python controller predates the changes and needs a normal
Ctrl+C / `make demo-ui` restart to load them. No GUI/projection rehearsal is claimed.

## Ubuntu CI for this change

Actually passed on GitHub-hosted Ubuntu 24.04, tested source commit
`08a9ad3e262734d421cdd127838e9570c40d49d5`:
[Ubuntu dashboard verification](https://github.com/yyyunx/OS-presentation/actions/runs/42398829549).
Execution completed 2026-11-08 around 01:58 Asia/Taipei.
This is CI evidence, separate from the user's VMware guest.

- `make`: all nine unchanged C++ executables compiled.
- `make test`: 14 Python regressions plus the original Linux smoke checks passed.
- `make test-demo-ui`: actual safety/traffic/100/500-connection experiments,
  stop/reset, FD cleanup and occupied-port checks passed.
- `make test-demo-proof`: all nine proof checks passed: late reading of real
  short safety/queue programs; live 100/500 connections with independent `/proc`
  and actual argv comparisons; HTTP complete raw output retaining all 501
  connection events (probe plus clients); cancellation/reaping; reset/rerun;
  preserving an occupied listener; and actual C++ exit 1 on invalid arguments.
  The real terminal follower and historical replay transcripts were checked.

The CI job/step success was checked through the GitHub API; earlier source
`3a6c6e2` also passed and its full artifact was downloaded and inspected,
including live timestamps, PIDs, argv, cancellation, exit codes and summaries.
Measured connection samples were Blocking 100: 101 Threads / 104 FDs; epoll 100:
1 Thread / 105 FDs; epoll 500: 1 Thread / 505 FDs. All connection failures were
zero. These are historical CI measurements, not fresh VMware readings.

The workflow's dashboard-measurements artifact includes
`.runtime/proof-test-results.json`: actual C++ raw output, journal events, live
terminal transcript, historical replay, errors, cancellation and rerun checks.
Runtime journals and raw output directories are ignored by Git.

## All modified files

| File | Purpose |
|---|---|
| `.github/workflows/dashboard.yml` | Run proof integration and export its evidence |
| `.gitignore` | Ignore runtime logs/keys and generated dashboard results |
| `Makefile` | Add `demo-proof` and `test-demo-proof` |
| `README.md` | Two Terminals, side-by-side layout, operations and tests |
| `demo-ui/controller.py` | Real lifecycle/result/proc events, persistent raw logs, complete-output endpoint |
| `demo-ui/proof.py` | Durable journal, native Terminal follower, historical/final summaries |
| `demo-ui/static/app.js` | Run ID correlation and offline historical provenance |
| `demo-ui/static/index.html` | Complete raw output link inside Technical Logs |
| `docs/DASHBOARD.md` | Link the new presentation mode |
| `docs/DEMO_PROOF.md` | Event semantics, timing, lifecycle, history and troubleshooting |
| `docs/DEMO_PROOF_TEST_RESULTS.md` | This actual test record and complete change list |
| `docs/VMWARE_SSH.md` | Existing VMware Guest SSH/key setup and test commands |
| `presentation/Dashboard_3min_Demo_and_P14.md` | Direct readers to the updated script |
| `presentation/Dashboard_Terminal_4min_Demo.md` | Full 419-word English script and actions, around 3:40 |
| `presentation/README.md` | Recommend browser plus real Ubuntu Terminal |
| `tests/dashboard_integration.py` | Isolate its journal from presenter data |
| `tests/proof_integration.py` | Real C++/proc/live follower/raw HTTP/cancel/failure/rerun tests |
| `tests/test_dashboard.py` | Isolate existing controller regression journals |
| `tests/test_proof.py` | Six portable journal/reader/replay/error regressions |

No C++ source or existing slideshow file changed. Runtime SSH keys, diagnostics,
raw event journals and execution logs are local artifacts, never tracked by Git.
