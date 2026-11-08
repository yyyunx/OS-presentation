# Real Ubuntu Terminal evidence

Use the two-terminal instructions in the root README. The left browser triggers
the experiments; the right native Ubuntu Terminal runs `make demo-proof`.
The background Terminal A runs `make demo-ui`. Both must use the same clone,
filesystem, and VM; a Windows viewer cannot measure a VMware guest's `/proc`.

## Presentation Terminal mode

Use `make demo-proof-present` for a projector. The original `make demo-proof`
remains the detailed event viewer. Both consume exactly the same JSONL and real
raw outputs; the projection view never starts a substitute experiment or invents
data. No C++ or controller measurement logic changed.

Projection uses a 58-column panel (at most 38 lines in regression checks), a
numbered scene title, full Run ID, real PID, relative executable/actual arguments,
measured fields, exit code and cleanup. Times are local HH:MM; detailed UTC ISO
timestamps and full absolute paths remain in the original viewer and journal.
GNOME Terminal's Monospace 13 pt is about 17 px at 96 DPI. Use a 1920×1080 desktop,
browser on the left 60%, native Terminal on the right 40%.

In a real TTY, changed fields repaint the current panel in place. Identical
frames are suppressed. Only the next run replaces the scene; Completed/Error
summaries remain, and browser Reset does not erase them. This is formatting of
real events in a native terminal, not a terminal component in the webpage.
RUNNING/LIVE is yellow, COMPLETED/PASS green, ERROR red, Historical gray.
Use `--color never` for plain output or `--color always` for ANSI output.

Each /proc column has its own observed sample time. A sample is LIVE only after
a fresh event, within two seconds of its actual sample timestamp, while its
server has not exited and the run remains Running. Replay, stale samples,
server exit and completion all prevent LIVE claims. The event journal still
records every sampling interval even when identical displayed values are not
printed again. Child exit zero alone does not imply a Completed experiment.

```bash
make demo-proof-present
python3 demo-ui/proof.py --present --once --color never
python3 demo-ui/proof.py --present --once --all --color never
```

Portable tests cover width, no repeated frames, ANSI colors, stale/replayed
samples, exit/nonzero/error, reset retention, dynamic results and malformed
journals. `make test-demo-proof` also launches both real CLI followers against
actual C++/proc runs and compares projection summaries to their original output.

## What is measured

Every launched child, including load clients, gets a `process_start` event with
the executable label, exact `Popen` argv, PID, launch-request time, successful
launch-observation time, and raw stdout/stderr file. `process_exit` records the
exit code and the time the controller **observed** termination. These are UTC
wall-clock observations, not kernel-exact creation/death timestamps. Very short
programs can finish between these observations; their exit/output is still saved.
Cleanup records whether the child was already reaped, stopped with SIGINT, or
required SIGKILL. A forced kill remains an Error even when reaping succeeds.

Ticket results are parsed only after the real race/mutex child exits zero and
its final inventory passes validation. A PASS for `race_demo` means the intended
teaching outcome was reproduced, not that overselling is safe. Queue summaries
come from the unchanged C++ statistics, after checking Accepted = Processed,
Processed + Rejected = Incoming, zero pending work, four workers, and queue policy.
If parsing, a child exit, or validation fails, no successful result is substituted;
the run ends Error and the raw output is retained.

During held idle connections, the controller reads each living server's real
`/proc/<pid>/status` Threads and `/proc/<pid>/fd` approximately every 0.8 seconds
(0.75-second target with 0.2-second cancellation checks). Each record has a fresh
sample time. Connected is parsed from the actual client `Holding N sockets` line;
Failures = attempted minus held sockets, then verified against the client's
final Closed/Failures line. These counts describe the held cohort, not purchases
or new connections each interval. Sampling begins after both servers have
accepted the held cohort. Samples are not atomic across two servers or across
status/fd reads. Whole-process FDs include standard streams, listener and epoll FD.
Normal completion checks that FDs return to baseline before stopping servers.
Cancellation instead closes/reaps owned processes and retains Error evidence.

## Event journal and raw output

The standard-library controller writes append-only JSONL to
`.runtime/demo-proof/events.jsonl`, with a session ID, monotonically increasing
sequence within that session, unique run ID, controller PID, and UTC event time.
Each complete event is flushed and fsynced. An event-read cursor advances only
after a complete newline-terminated JSON record. The Terminal follows **events**,
not snapshots of currently running processes, so it does not miss short programs.
It can start before or after the Dashboard. The production controller's fixed
HTTP port prevents a second production writer. Do not run test controllers
against the production journal; integration tests use temporary journals.

Per-process raw files live under
`.runtime/demo-proof/<session>/<run-id>/<number>-<executable>.log` and survive
Stop, Reset, reruns, viewer restarts, and controller restarts. Technical Logs has
a link to `/api/logs` for the latest run's complete merged output, while its
inline preview remains bounded. Prior runs' files remain available on disk.
Neither the terminal nor the journal repeats every client-connected line.

The journal is local classroom evidence, not a tamper-resistant security audit.
It does not recover unsaved events after an abrupt power loss. If the controller
crashes before `run_end`, cleanup/completion is **unknown**, not Completed.
An unwritable journal prevents new launches; write failure during a run makes it
Error while process cleanup still executes. Disk retention is manual: after
stopping both controller and viewer, archive or remove `.runtime/demo-proof/`
if desired. No automatic truncation or rotation can erase the professor's view.
All runtime files are ignored by Git; CI exports only the test evidence JSON.

## States and presenting

- Running: a controller event from the active run. A LIVE sample includes its
  sample time and real PID; the reader labels samples older than two seconds
  Historical rather than presenting them as current.
- Completed: validation passed and owned child processes were cleaned up.
- Error: cancellation, startup/measurement/validation/cleanup failure; inspect
  the message and raw output. Partial measurements are not a successful demo.
- Historical: previously recorded evidence. At run end, final results remain
  visible with their original Completed/Error outcome. On viewer startup all
  replayed events are explicitly Historical, even if their original state was
  Running. If no final event exists, the viewer warns that completion is unknown.
  During following, three seconds without new events also prints a stale-evidence
  notice; this is not a failure verdict or proof a process has stopped.

The viewer never clears the screen. New runs append below old results, and each
has a new run ID. Use Terminal scrollback to compare. Reset appends a notice and
clears browser cards only. Closing the browser does not cancel an experiment.
Ctrl+C in Terminal B stops only the viewer. Ctrl+C in Terminal A cancels owned
experiments, reaps them, then stops the controller. An occupied demo port is an
Error; no unrelated process is killed. Stopping the viewer does not stop clients.

To replay without following (always Historical):

```bash
python3 demo-ui/proof.py --once           # latest saved run
python3 demo-ui/proof.py --once --all     # all saved runs
```

If a journal is replaced/truncated while following, the viewer errors explicitly;
restart it after resolving the file change. Never delete an active journal.
An unexpected controller crash can leave owned children running: inspect their
recorded PIDs and commands before stopping them yourself, then restart cleanly.
No Completed event is inferred from a vanished controller or missing `/proc`.

## Validation

```bash
make
make test
make test-demo-ui
make test-demo-proof
```

The last target runs actual short C++ programs before a reader attaches, live
100/500 connections with independent `/proc` and argv comparisons, FD baseline
checks, cancellation while sockets are held, reset/rerun, occupied ports, and a
real nonzero C++ usage exit. It also launches the actual terminal follower and
checks its live transcript, historical replay, exit metadata and lack of per-client
spam. Output, events and transcripts are saved to `.runtime/proof-test-results.json`.
It requires Linux and compiled executables; unsupported hosts explicitly return
NOT RUN/nonzero. Portable journal tests are part of `make test`.
