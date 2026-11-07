# Dashboard implementation test record — 2026-11-07

C++ sources and existing test files are unchanged. The controller parses their
existing default output; no JSON/quiet mode was needed.

## macOS host (actual execution)

- Darwin arm64; Apple system g++/clang, C++11 with existing warning flags.
- `make`: attempted; compilation stopped at `sys/epoll.h` missing, as expected
  on macOS. This is not a successful full build.
- `make test`: attempted; stopped at the same build prerequisite. This is not
  a successful Linux smoke run.
- Portable binaries compiled via existing Makefile targets.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: 8 tests passed (three
  existing startup regressions plus five dashboard boundary tests).
- `python3 tests/dashboard_integration.py --output docs/dashboard-macos-results.json`:
  safety and traffic actually completed. Exit 2 explicitly records Linux cases
  NOT RUN. Exact results and raw process logs are in that JSON evidence file.

### Measured portable result (saved JSON run)

| Experiment | Successful purchases | Remaining | Oversold |
|---|---:|---:|---|
| Without mutex | 4 | -3 | Yes |
| With mutex | 1 | 0 | No |

| Local simulator | Incoming | Processed | Rejected | Max Queue | Workers |
|---|---:|---:|---:|---:|---:|
| Uncontrolled | 1000 | 1000 | 0 | 996 | 4 |
| Protected | 1000 | 355 | 645 | 20 | 4 |

Both simulations drained their queues. These are macOS measurements, not Ubuntu
results. A subsequent browser run measured a different protected split (354/646),
confirming why the UI must use each process's actual output.

### Browser verification

Used the real loopback controller in an in-app browser, at its default narrow
viewport. Verified initial Waiting/empty cards, Race/Mutex Completed values,
Traffic Control cards and conservation, scene switching, reset clearing, and
Linux-unavailable Error with empty connection metrics. Browser error/warning log
was empty. A screenshot of the actual completed safety run was saved separately.
No static placeholder data was inserted into the interface.

## Ubuntu 24.04 CI — actually passed

Source: [Ubuntu dashboard verification, run 1](https://github.com/yyyunx/OS-presentation/actions/runs/42379662932).
Tested commit: `63487ba1904cf19fadfe1b328af2689439ff4da9`.
Run date: 2026-11-07, approximately 22:02 Asia/Taipei (14:02 UTC).
Environment: GitHub-hosted Ubuntu 24.04.5 LTS x86_64,
Linux 7.0.0-1017-azure, glibc 2.39. This is a real Ubuntu CI runner, not the
user's VMware VM and not the macOS host.

- `make`: all nine original C++ executables compiled successfully.
- `make test`: eight Python regressions passed; all original Ubuntu smoke checks
  passed for three servers, protocol/framing, half-close, resets, line limits,
  invalid ports, 32 idle connections, FD cleanup, SIGINT, and resource invariants.
- `make test-demo-ui`: all four dashboard experiments completed, plus actual
  stop/reset during held sockets, process exit, reusable ports, and occupied-port
  rejection preserving the existing listener.

### Actual dashboard results

| Ticket experiment | Purchases | Remaining | Oversold |
|---|---:|---:|---|
| Without mutex | 4 | -3 | Yes |
| With mutex | 1 | 0 | No |

| Idle connection experiment | Connected | Failures | Threads | Total FDs | Baseline FDs |
|---|---:|---:|---:|---:|---:|
| Blocking, 100 attempted | 100 | 0 | 101 | 104 | 4 |
| epoll, 100 attempted | 100 | 0 | 1 | 105 | 5 |
| epoll only, 500 attempted | 500 | 0 | 1 | 505 | 5 |

These are held idle connections, not purchases. FD counts are whole-process
counts, including standard streams, listener, and epoll FD where applicable.
The tests also verified that client FDs returned to the server baseline before
shutdown and that the server PIDs no longer existed after each completed run.

| Local simulation | Incoming | Processed | Rejected | Max Queue | Workers |
|---|---:|---:|---:|---:|---:|
| Uncontrolled | 1000 | 1000 | 0 | 996 | 4 |
| Protected | 1000 | 326 | 674 | 20 | 4 |

Both queues drained; Processed = Accepted and Processed + Rejected = Incoming.
Protected maintained capacity 20. A separate smoke-test execution in the same CI
job produced 328 processed / 672 rejected, also valid. Counts are per-run
measurements and must not be hard-coded into the UI or presentation.

### Evidence

- [Compact measured JSON](dashboard-ubuntu-ci-summary.json), extracted from the
  actual workflow output with no replacement values.
- [Downloaded verification log](dashboard-ubuntu-ci.log), timestamps stripped
  for readability; includes build, smoke, and dashboard measurement output.
- [Full raw per-process output artifact](https://github.com/yyyunx/OS-presentation/actions/runs/42379662932/artifacts/13577680171),
  `dashboard-measurements`, containing `dashboard-ubuntu-results.json`.
  GitHub artifact retention applies; rerun `make test-demo-ui` to save new evidence.

The initial GitHub integration write attempts returned 403. After authorization
was updated, the implementation was successfully pushed to main and the above
workflow ran to success. The earlier Linux-pending status is superseded by this
actual run. The host's macOS build limitation remains recorded above rather than
being relabeled as a successful local Linux build.
