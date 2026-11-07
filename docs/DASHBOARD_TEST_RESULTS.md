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

## Ubuntu CI

The workflow `.github/workflows/dashboard.yml` runs `make`, `make test`, and
`make test-demo-ui` on Ubuntu 24.04. Linux results are pending in this initial
implementation record and must be read from an actual completed workflow run;
this paragraph does not claim that 100/500 connections have passed.

GitHub repository metadata now confirms the connected user has push permission.
However, actual Git data writes and branch creation both returned HTTP 403,
`Resource not accessible by integration`. Therefore the workflow has not been
pushed or run, and no Ubuntu results can be reported. A temporary local Ubuntu
VM attempt also could not start under the host's execution restrictions. The
required 100-client comparison, 500 epoll clients, complete `make` / `make test`,
and Linux process/FD cleanup remain unverified until Ubuntu execution is available.
