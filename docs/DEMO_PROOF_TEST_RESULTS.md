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
  Guest SSH Server/key setup is pending. This does **not** mean Ubuntu is absent.
  No direct VMware test or visual rehearsal is claimed before SSH connects.

## Ubuntu CI for this change

Actually passed on GitHub-hosted Ubuntu 24.04, tested source commit
`3a6c6e2a661eb82bbefda4d5c3b47b9fffd7f124`:
[Ubuntu dashboard verification](https://github.com/yyyunx/OS-presentation/actions/runs/42398231177).
Execution completed 2026-11-08 around 01:50 Asia/Taipei (2026-11-07 17:50 UTC).
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

The artifact was downloaded and inspected, including actual live timestamps,
PIDs, argv, raw statistics, cancellation, exit codes and final summaries.
Measured connection samples were Blocking 100: 101 Threads / 104 FDs; epoll 100:
1 Thread / 105 FDs; epoll 500: 1 Thread / 505 FDs. All connection failures were
zero. These are historical CI measurements, not fresh VMware readings.

The workflow's dashboard-measurements artifact includes
`.runtime/proof-test-results.json`: actual C++ raw output, journal events, live
terminal transcript, historical replay, errors, cancellation and rerun checks.
Runtime journals and raw output directories are ignored by Git.
