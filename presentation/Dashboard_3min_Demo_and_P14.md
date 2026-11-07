# Three-minute English dashboard demo

Preparation: in Ubuntu, run `make`, `make test`, and `make test-demo-ui` before
class. Start `make demo-ui`, open http://127.0.0.1:8765 inside Ubuntu, and keep
browser zoom around 80–90% if needed to fit the experiment cards. Stop any manual
servers on 8081/8082. Keep Technical Logs collapsed. Do not prefill cards or
present earlier screenshots as a new live run. This script follows actual cards;
read current values where indicated. Rehearse at about 120 words per minute.

## 0:00–0:15 — Introduce the stage

**Action:** Show the ENCORE heading and three scene tabs.

**Say:** “Imagine a concert sale opening now. Thousands of fans want to enter,
but only one seat remains. This dashboard connects three operating-system ideas
to that rush: inventory safety, waiting connections, and controlled request
queues. The cards use real process output; the labeled animations are teaching
illustrations.”

## 0:15–0:55 — Ticket Safety

**Action:** Click Ticket Safety → Run experiment. Wait for Completed. Point to
the two purchase counts and remaining inventory.

**Say:** “Four buyers compete for one ticket. Without a mutex, all four pass the
inventory check before any buyer decrements it. We get four purchases and minus
three remaining tickets. A teaching rendezvous makes this ordering repeatable.
Individual atomic operations are safe, but the whole purchase operation is not.
With the mutex, one buyer succeeds and the remaining inventory is zero. The
critical section must protect the check and the decrement together. The winner
can change with scheduling.”

If the actual run is Error, do not read the success claims: show the error and
explain that the experiment did not complete.

## 0:55–1:45 — Connection Rush

**Action:** Click Connection Rush, select 100 idle connections, and Run. Watch
cards during the eight-second hold. Wait for Completed and point to thread/FD bars.

**Say:** “Now we compare one hundred idle connections on each server. These fans
are waiting; they are not buying tickets. The blocking version gives each client
a worker thread. The epoll version uses an event loop to wait for readiness.
The cards read actual thread counts from Linux process status and count its open
file descriptors. We measured **[read blocking Threads]** versus **[read epoll
Threads]** threads, and **[read both Total FDs]** total descriptors. Both versions
still need a socket descriptor for each connection. epoll reduces waiting
threads; it does not remove descriptor limits. Completed means the clients and
servers have now been cleaned up.”

Keep the 500-connection option for questions after the timed demo; it is a
connection-capacity illustration, never 500 successful purchases.

## 1:45–2:40 — Traffic Control

**Action:** Click Traffic Control → Run. Wait for both summaries. Point to
Protected capacity 20, Max Queue, Processed, Rejected, and conservation check.

**Say:** “The final experiment is a separate local request simulation. It does
not send network purchase transactions. Both versions receive one thousand
requests and use four workers. The uncontrolled version accepts everything, so
waiting work grows. The protected version limits the pending queue to twenty.
When full, it waits briefly and may reject a request as busy. This run processed
**[read Protected Processed]** and rejected **[read Protected Rejected]**. Their
sum is one thousand, so no request disappears. The maximum pending queue is
**[read Protected Max Queue]**, within the capacity of twenty. Exact rejection
counts depend on scheduling; they are not hard-coded.”

## 2:40–3:00 — Close with the three guarantees

**Action:** Point to Conclusion; briefly expand Technical Logs to show the source
statistics, then collapse. Leave the result cards visible.

**Say:** “These experiments answer three different questions. Mutex protects the
last ticket. epoll handles waiting connections with fewer threads. A bounded
queue controls admitted work under a burst. They are separate mechanisms, and
none alone makes a production ticketing system. The evidence is in the process
logs, not in the animation.”

Failure fallback: “The controller stopped this experiment and displays its error.
I will not substitute expected numbers for a failed measurement.” Stop or Reset,
check Technical Logs, and use only clearly labeled earlier evidence if necessary.

# Suggested replacement for PPT P14

The repository does not contain an editable PPT/PPTX deck. These are replacement
content and layout suggestions for P14; no existing slide file was modified.

**Title:** Live Demo — The Concert Ticket Rush

Use three equal columns on a dark background, with mint and violet accents
matching ENCORE. Put one simple icon above each column (ticket, connections,
queue). Keep terminal commands off the main slide; they belong in backup notes.

| Ticket Safety | Connection Rush | Traffic Control |
|---|---|---|
| 4 buyers / 1 ticket | 100 idle connections per server | 1,000 simulated requests / 4 workers |
| Without mutex → With mutex | Blocking :8081 → epoll :8082 | Unbounded → Capacity 20 |
| Purchases · Remaining · Overselling | Connected · Threads · FDs · Failures | Processed · Rejected · Max Queue |
| Protect check + decrement | Reduce waiting threads; retain socket FDs | Bound pending work; account for every request |

Footer: **Real C++ output + Linux /proc · Animation is illustrative · Local demo,
not a production ticket platform.**

Presenter note: Open http://127.0.0.1:8765 and follow the 3-minute sequence above.
Do not put fixed protected Processed/Rejected values on the slide. If you add
screenshots, label them “Recorded run” with environment and date. The optional
500 epoll connections belongs on a backup slide, explicitly labeled “idle
connections, no purchases.” If P14 currently says 3:20, revise its demo duration
to 3:00 and allow the saved 20 seconds for transitions.
