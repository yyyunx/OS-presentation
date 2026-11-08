# ENCORE — 150-Second V2 Video: English Speaker Script

**Purpose:** Speak live while playing the silent `Concert_Ticket_Rush_150s_Demo_v2.mp4`. This is not an audio/subtitle track.  
**Runtime:** 2:30 (150 seconds) · **Speaking pace:** approximately 105–115 words/minute, with natural pauses.  
**Visual:** Left = browser Dashboard (60%); right = actual Ubuntu GNOME Terminal running `make demo-proof-present` (40%).  
**Important:** This script describes the *recorded v2 run*. Do not substitute recorded numbers for fresh results when running the experiments live.

## Read-aloud English script (aligned to the actual video)

### 0:00–0:15 — Introduce the evidence (15 s)
> This is our concert ticket rush demo. The dashboard is on the left, and the real Ubuntu terminal on the right records the execution of our C++ programs.

**中文提示：** 左邊是控制與數據視覺化；右邊是真正 Ubuntu Terminal 的 C++ 執行證據。影片開始不需要等待首頁介紹。

### 0:15–0:37 — Ticket Safety: race condition and mutex (22 s)
> First, four fans compete for one remaining ticket. Without a mutex, all four purchases succeed, leaving minus three tickets. With a mutex, only one succeeds, and inventory reaches zero. This demonstrates a race condition and why the entire check-and-update operation must be protected.

**中文提示：** 指向左側 4 purchases / −3 remaining，接著 1 purchase / 0 remaining；右側對應 `race_demo`、`mutex_demo` 和 Exit Code。畫面約 0:04 已經出現結果，可以慢慢講。

### 0:37–0:52 — Connection Rush: workload (15 s)
> Next, one hundred clients establish idle connections to each server. These represent waiting fans, not completed ticket purchases. We compare the blocking server with the epoll server.

**中文提示：** 0:37 切換場景；0:42 左右可看到仍在執行的 LIVE `/proc` 樣本。強調「連線」不等於「成功買票」。

### 0:52–1:15 — Connection Rush: the main comparison (23 s)
> The blocking server uses one worker thread per client, resulting in one hundred and one threads. The epoll server handles the same number of connections with just one event-loop thread. Both still need socket file descriptors.

**中文提示：** 重點數據：Blocking = 100 connections / 101 Threads / 104 FDs；epoll = 100 connections / 1 Thread / 105 FDs；兩者 0 failures。不要說 epoll 不需要 FD。

### 1:15–1:31 — Connection Rush: real Linux proof (16 s)
> The terminal shows actual Linux process IDs and thread and file-descriptor measurements sampled from slash-proc while the servers were alive. After cleanup, the saved results are labeled historical.

**中文提示：** `/proc` 英文可唸「slash proc」。LIVE 量測是在程序還活著時取得；完成後顯示 Historical，不能當作即時數據。

### 1:31–1:47 — Traffic Control: burst of requests (16 s)
> Finally, we simulate a burst of one thousand requests using four workers. The uncontrolled version accepts them all, allowing the waiting queue to grow.

**中文提示：** 0:01:31 切 Traffic Control，約 1:38 出現結果。這是獨立本機請求模擬，並非真實售票網站交易。

### 1:47–2:15 — Traffic Control: bounded queue and accounting (28 s)
> The protected version limits the pending queue to twenty. In this recorded run, three hundred and eighty-four requests were processed, and six hundred and sixteen were rejected. Together, they equal one thousand, so every request is accounted for. Rejection is intentional backpressure, protecting the server from unlimited queue growth.

**中文提示：** v2 錄影當次：Uncontrolled = 1,000 processed；Protected = 384 processed + 616 rejected，Max Queue = 20。拒絕是負載保護，不代表已成功售票數。其他執行的 384/616 可能不同。

### 2:15–2:30 — Summary and execution evidence (15 s)
> In summary, mutexes protect shared inventory, epoll reduces thread overhead, and bounded queues control load. The terminal confirms real processes, exit codes, and cleanup.

**中文提示：** 最後停在結果頁與 Terminal 的 Completed、Exit Code、Cleanup、Historical；影片不需要字幕或配音。

---

## Presenter cheat sheet

| Video time | Point at | Remember |
|---|---|---|
| 0:00–0:37 | Safety cards + Terminal results | **4 → 1** successful purchases; remaining **−3 → 0** |
| 0:37–1:31 | Blocking / epoll metrics + LIVE `/proc` | **101 → 1 Threads**, each with **100 idle connections** |
| 1:31–2:15 | Queue results + Terminal accounting | **1,000 incoming**, **20 max pending**, **384 + 616 = 1,000** in the recorded v2 run |
| 2:15–2:30 | Completed / Exit Code / Cleanup / Historical | Real C++ evidence, not a UI-only animation |

### English pronunciations
- **Mutex:** “myoo-tex”
- **epoll:** “ee-poll”
- **`/proc`:** “slash proc”
- **FDs:** “file descriptors”
- **Backpressure:** “back-pressure”
- **384:** “three hundred and eighty-four”
- **616:** “six hundred and sixteen”

### Accuracy and rehearsal notes
- The **v2 video is already recorded**; do not say “I am running it now.” You may say “This recorded run shows...” or simply “This run shows...”.
- The safety race is an intentionally synchronized teaching experiment, not a production ticketing backend.
- The connection scene measures **idle socket connections**, not ticket purchases or throughput.
- The traffic scene independently simulates requests with a bounded pending queue; rejected requests are accounted for.
- The Terminal in the video is a real Ubuntu Terminal showing controller events and C++ process results; `/proc` data was sampled while the Linux server processes were alive. Afterward it is **Historical**.
- **Do not read the Chinese prompts aloud.** They are preparation cues; the spoken script is English only.
- The 150 seconds include substantial held result screens: use those seconds for explanation rather than asking Codex to add fake activity.
- Previous longer guide remains in `presentation/Dashboard_Terminal_4min_Demo.md`; this file is specifically for the finished 150-second v2 video.
