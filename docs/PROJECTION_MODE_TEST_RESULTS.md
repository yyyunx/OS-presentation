# Projection Terminal and video v2 — 2026-11-08

Implemented `make demo-proof-present`, leaving detailed `make demo-proof`, raw
logs, full timestamps and controller/C++ measurement logic unchanged.

## Actual VMware Ubuntu tests

Direct SSH to the user's running VMware Ubuntu 24.04.5 LTS, Linux
7.0.0-42-generic x86_64; project in the same Windows Shared Folder, user-mounted
at `/home/ubuntu/os-demo-share/presentation/ticket-rush-os-demo`.

- `make test`: all 20 regressions and all original Linux smoke checks passed.
- `make test-demo-ui`: all real safety/traffic/100/500-connection and cleanup
  checks passed.
- `make test-demo-proof`: all 10 checks passed, including actual detailed and
  presentation CLI followers; real C++ output/proc values; LIVE versus stale,
  replay and completion; occupied ports, nonzero exit, cancel/reset/rerun.
- Six new portable projection regressions passed on Windows as well. Values in
  formatting fixtures differ deliberately from demo measurements, to check that
  the formatter displays data instead of hard-coded results.

Actual integration evidence is `.runtime/proof-test-results.json` (ignored by
Git), including original output, events, live panels, projection summaries,
both CLI transcripts and historical replays. Every checked panel fits 58 display
cells per line and at most 38 lines. Repeated identical frames are suppressed.

The first pass succeeded; a subsequent rerun and the first CI attempt exposed
an existing port-probe issue: TCP TIME_WAIT could be mistaken for a live listener.
Controller preflight and test probes now use SO_REUSEADDR, matching the unchanged
C++ listener. Real listening sockets are still rejected and preserved (no
SO_REUSEPORT). The full VMware suite was rerun successfully after this fix.
First-frame TTY repaint also clears any echoed command suffix; subsequent
Completed summaries stay on screen until a new run.

## Video verification

Recording/verification pending. The v1 MP4 is preserved with SHA-256
`10e4629f23b706b7da7657129a588dffcc9a4a3df56fc3b886f273e46cd4b7a2`
(11,899,896 bytes). v2 uses a separate output filename and separate runtime capture.
