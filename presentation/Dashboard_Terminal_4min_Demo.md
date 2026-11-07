# Dashboard + real Ubuntu Terminal: 3–4 minute English demo

Target: about 3:40, including clicks and waiting. Speak around 120–130 words per
minute. Read the values from **this** run; bracketed prompts are not fixed numbers.

## Before class

In the Ubuntu clone, run `make`, `make test`, `make test-demo-ui`, and
`make test-demo-proof`. Stop manual servers on 8081/8082. Terminal A runs
`make demo-ui` in the background. Terminal B runs `make demo-proof` on the right.
Open http://127.0.0.1:8765 in Ubuntu's browser on the left. Use Super+Left and
Super+Right or drag the windows. Keep enough vertical space for metrics; scroll
past the hero first and collapse Technical Logs. Rehearse browser zoom and native
Terminal font size on the actual projector. Keep the optional 500-client mode
for questions. No terminal webpage or manually typed fake output is involved.

## 0:00–0:25 — Introduce the two windows

**Action:** Point to the browser, then the real Terminal's waiting message.

**Say:** “This is a concert ticket rush, explained through three operating-system
experiments. The browser on the left controls the experiments. The Ubuntu
Terminal on the right shows evidence from real C++ processes. You will see their
commands, process IDs, exit codes, and cleanup results. The animation is only an
illustration; the measured numbers come from program output and Linux.”

## 0:25–1:15 — Ticket Safety: protect the whole operation

**Action:** Select Ticket Safety, click Run. Wait for Completed. Point to the
Terminal START/EXIT/RESULT for race_demo and mutex_demo, then the browser cards.

**Say:** “Four buyers compete for one remaining ticket. The first program uses
atomic reads and decrements, but the complete purchase is not protected. A
teaching rendezvous makes all four buyers check before any decrement. This run
shows **[purchases]** purchases and **[remaining]** remaining tickets: overselling.
With a mutex, one buyer succeeds and inventory becomes zero. The critical
section must protect the check and decrement together. These programs finish
quickly, but their start, output, and exit events are saved. The Terminal does
not need to catch them in a process-list poll.”

## 1:15–2:15 — Connection Rush: measure while processes are alive

**Action:** Select Connection Rush, keep 100 idle connections, click Run. During
the eight-second hold, point to fresh sample timestamps, PIDs, Threads and FDs.
Wait for FD cleanup and Completed. Point to Historical after completion.

**Say:** “Now each server holds one hundred idle connections. These clients are
waiting; they are not buying tickets. While the sockets are open, the controller
reads the servers' real Linux process information about every eight tenths of a
second. Here are the PIDs and fresh sample times. Blocking uses **[threads]**
threads, while epoll uses **[threads]**. Both still require a file descriptor for
each connection. The Terminal summarizes successful connections and failures
without printing every client event. After the hold, descriptors return to their
baseline and the processes stop. The retained measurements are now labeled
Historical, so we do not mistake an old sample for a running server.”

## 2:15–3:15 — Traffic Control: account for every request

**Action:** Select Traffic Control, click Run. Wait for both C++ summaries and
Completed. Point to commands with `1000 0`, Max Queue and the conservation check.

**Say:** “The final experiment is an independent local request simulation.
Both programs receive one thousand requests and use four workers. The
uncontrolled version accepts everything, allowing waiting work to accumulate.
The protected version limits the pending queue to twenty. It briefly waits for
space, then rejects work if the queue remains full. This run processed
**[processed]** and rejected **[rejected]**. Their sum equals the incoming count:
no request disappears. The protected maximum queue is **[max queue]**, within
twenty. That capacity excludes requests already being processed by the four
workers. Exact rejection counts depend on scheduling, so we read this run's
output rather than use a fixed number.”

## 3:15–3:40 — Close with evidence and the three mechanisms

**Action:** Point to Exit Code, cleanup, and the final Historical label. Briefly
open Technical Logs and its complete-output link if time permits.

**Say:** “Mutex protects shared inventory. epoll reduces the threads needed for
waiting connections. A bounded queue controls admitted work during a burst.
The Terminal keeps the real commands and measured results after each experiment,
and the original output remains available for inspection. Completed means the
checks and cleanup passed. If a run reports Error, we show that failure instead
of substituting expected numbers.”

## Failure or questions

If Error appears, say: “This experiment did not complete. These are partial or
historical measurements. I will inspect the recorded error and raw output.”
Stop or Reset, resolve the displayed cause, then rerun; do not read success text
for a failed experiment. New runs have new IDs. Stop the viewer with Ctrl+C only
after questions, then stop the background controller with Ctrl+C.

For the optional epoll 500 mode, explicitly call it **500 idle connections, no
purchases**, and wait for fresh `/proc` samples. For P14 use the existing
three-column content suggestions, change the demo duration to 3:40, and add the
caption “Browser controls · Real Ubuntu Terminal proves execution”. No slide
file is modified by this code change.
