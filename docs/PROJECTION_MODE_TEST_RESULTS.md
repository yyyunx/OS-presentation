# Projection Terminal and video v2 — 2026-11-08

Implemented `make demo-proof-present`, leaving detailed `make demo-proof`, raw
logs, full timestamps and controller/C++ measurement logic unchanged.

## Actual VMware Ubuntu tests

Direct SSH to the user's running VMware Ubuntu 24.04.5 LTS, Linux
7.0.0-42-generic x86_64; project in the same Windows Shared Folder, user-mounted
at `/home/ubuntu/os-demo-share/presentation/ticket-rush-os-demo`.

- `make test`: all 21 regressions and all original Linux smoke checks passed.
- `make test-demo-ui`: all real safety/traffic/100/500-connection and cleanup
  checks passed.
- `make test-demo-proof`: all 10 checks passed, including actual detailed and
  presentation CLI followers; real C++ output/proc values; LIVE versus stale,
  replay and completion; occupied ports, nonzero exit, cancel/reset/rerun.
- Seven new portable projection regressions passed on Windows as well. Values in
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

Visual QA then caught short-line/blank-row suffixes on the actual native TTY.
Each row is now erased before repaint. A VT screen-state regression checks that
shorter and blank rows remove old contents; a new five-second actual C++ Safety
capture was inspected and confirmed clean. All 21 regressions and real proof
integration were rerun successfully after this final renderer correction.

## Video verification

Final code commit `267021d6e268fbfbfa5ee46f3d9897d667a908c3` also passed
[Ubuntu CI](https://github.com/yyyunx/OS-presentation/actions/runs/42437811672).

Delivered local artifact:
`presentation/demo-video/Concert_Ticket_Rush_150s_Demo_v2.mp4`.

| Check | Actual result |
|---|---|
| Duration | 150.000 seconds |
| Video | H.264 / avc1, 1920×1080, 30 FPS, yuv420p |
| Frames / playback | All 4,500 frames decoded without errors |
| Size | 4,341,976 bytes |
| Audio / subtitle tracks | None; one video track only |
| Desktop | Actual VMware Ubuntu GNOME Wayland screen recording |
| Layout / font | Dashboard 60%, native GNOME Terminal 40%, Monospace 13 pt (~17.3 px at 96 DPI) |
| Projection panel | Actual maximum 30 lines / 58 cells per line |
| Visual checks | Final MP4 frames at 10, 42, 60, 105 and 140 seconds inspected |
| Live evidence | 20 real /proc samples while server PIDs were alive |
| Cleanup | All 8 experiment child PIDs absent; 8081/8082 reusable; recorder stopped |

The three real final-take Run IDs are:

- Safety: `af278d4d2d5f4ed989045ac2e0d0db5f`.
- Connections: `ed5ed9b0792e4d7a80d089e36b84e1af`.
- Traffic: `dd67867151a249b387e686ac308470ec`.

Dashboard prefixes and the Terminal's full Run IDs match in the reviewed frames.
Thread comparison, PIDs, exit codes and summaries are readable without wrapping
or old-line suffixes at the reviewed 1080p frame size. This is frame review,
not a claim of testing a physical classroom projector.

The final recording measured protected Processed 384 / Rejected 616, Max Queue
20 and Workers 4; the source output was reparsed and matched to the event data.
These are historical measurements from this take, never formatter constants.
All three experiments Completed, with actual exit 0 and successful cleanup.

Two rejected attempts were retained under `.runtime/video-v2/`: one had an
expired Firefox local token after controller restart (no experiment launched),
and another revealed the old-row repaint problem. The browser was refreshed,
renderer fixed/tested, a five-second real Safety rehearsal inspected, then the
entire 150 seconds recorded fresh with new Run IDs. No rejected frames, previous
take values, inserted screenshots, stitching, narration, music or subtitles were
used in the final video.

Full verification is saved locally alongside the movie as
`presentation/demo-video/Recording_Verification_v2.json`. Raw current-take output,
events, captures and QA frames remain in `.runtime/video-v2/` and
`.runtime/demo-proof/`, ignored by Git. Detailed `make demo-proof` and Technical
Logs still expose complete original output. Idle Dashboard and the native
presentation viewer remain available; experiment servers/clients are stopped.

The v2 SHA-256 is
`35cbb91a792e79e1fdb50e9c80b7a3a8d39a23afebc4205bc7c868dda126e2f6`.
The v1 MP4 is preserved with SHA-256
`10e4629f23b706b7da7657129a588dffcc9a4a3df56fc3b886f273e46cd4b7a2`
(11,899,896 bytes), rechecked after v2 encoding. It was not overwritten.
