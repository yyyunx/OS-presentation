# ENCORE — 150-Second V2 Video: Short English Speaker Script

**Purpose:** Speak live while playing the silent `Concert_Ticket_Rush_150s_Demo_v2.mp4`.  
**Video length:** 2:30 (150 seconds). **Speech length:** about 150 words; speak naturally and allow pauses while the results remain on screen.  
**Screen:** Dashboard (left) + real Ubuntu Terminal (right).  
**Important:** The numbers below belong to the *recorded v2 video*, not the separate Ubuntu Results slide.

## Short read-aloud script

### 0:00–0:15 — Introduction
> This is our ticket rush demo. The dashboard is on the left, and Ubuntu execution is on the right.

**中文提示：** 左邊 Dashboard，右邊 Ubuntu 執行證據。

### 0:15–0:37 — Race Condition & Mutex
> Four fans race for one ticket. Without a mutex, four purchases succeed, leaving minus three tickets. With a mutex, only one succeeds.

**中文提示：** 無 Mutex：4 人成功、剩 −3 張。有 Mutex：只有 1 人成功。

### 0:37–0:52 — Connection Rush
> Next, each server receives one hundred idle connections, not ticket purchases.

**中文提示：** 100 個閒置連線，不代表買票成功。

### 0:52–1:15 — Blocking vs epoll
> Blocking needs one hundred and one threads. Epoll handles the same connections with one thread. Both still use file descriptors.

**中文提示：** Blocking = 101 Threads / 104 FDs；epoll = 1 Thread / 105 FDs。兩邊各 100 條閒置連線。

### 1:15–1:31 — Linux Evidence
> These are real Linux measurements from slash proc, captured while the servers were running.

**中文提示：** 指向 Terminal 的 LIVE `/proc` 證據；Cleanup 後顯示的資料是 Historical。

### 1:31–1:47 — Traffic Control
> Finally, we send one thousand simulated requests to four workers. The uncontrolled queue keeps growing.

**中文提示：** 1,000 Requests、4 Workers，無限制 Queue 持續增加；這是本機模擬，不是真實售票交易。

### 1:47–2:15 — Protected Queue
> The protected queue stays at twenty. In this video, three hundred eighty-four requests were processed, and six hundred sixteen were rejected. This is load shedding.

**中文提示：** v2 影片：Protected = 384 Processed + 616 Rejected = 1,000，Max Queue = 20；拒絕是 Load Shedding。

### 2:15–2:30 — Conclusion
> Mutex protects inventory, epoll reduces threads, and bounded queues prevent overload. The terminal confirms execution and cleanup.

**中文提示：** Mutex、epoll、Bounded Queue 三個重點，結束時指向 Terminal 的 Completed、Exit Code、Cleanup 和 Historical。

---

## One-glance presenter cheat sheet

| Video time | Highlight | Key numbers |
|---|---|---|
| 0:00–0:37 | Ticket Safety | 4 purchases / −3 remaining → 1 purchase / 0 remaining |
| 0:37–1:31 | Blocking vs epoll | 100 idle connections each; 101 vs 1 Threads; 104 vs 105 FDs |
| 1:31–2:15 | Traffic Control | 1,000 incoming; 4 Workers; max protected queue 20; recorded v2 **384 + 616 = 1,000** |
| 2:15–2:30 | Terminal evidence | Real execution, exit codes, cleanup, historical results |

## Accuracy notes

- **Backpressure** = wait briefly when the queue is full (up to 1 ms in this implementation). **Load shedding** = reject with BUSY if the queue is still full after the wait.
- Do not say this proves better throughput: it demonstrates a bounded pending queue and controlled resource usage.
- **Video v2:** 384 processed / 616 rejected (max queue 20). **Separate Ubuntu Results slide:** 378 processed / 622 rejected (max queue 20, uncontrolled max queue 997). They are **different runs**, and their counts can vary with scheduling.
- `/proc` is pronounced “slash proc”; the measurements were LIVE while the servers existed, then labeled Historical after cleanup.
- Don't read the Chinese notes aloud. Pauses are intentional; do not rush to fill every second.
