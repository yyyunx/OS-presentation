# From Click to Checkout: An Operating System Perspective on Online Ticketing

專案名稱：`ticket-rush-os-demo`

這是 OS 課程的 terminal 實作 Demo，以熱門演唱會搶票展示作業系統概念。
不是實際售票網站，沒有 GUI、Web framework 或支付功能。
第一階段已完成 concurrency、CPU scheduling、race condition 與 mutex；
另外三個目錄先保留下一階段規劃。

## 專案結構

```text
ticket-rush-os-demo/
├── concurrency/
│   └── concurrency_demo.cpp
├── scheduling/
│   └── scheduling_demo.cpp
├── race-condition/
│   ├── race_demo.cpp
│   └── mutex_demo.cpp
├── socket-server/
│   └── README.md                  # 下一階段規劃
├── epoll-server/
│   └── README.md                  # 下一階段規劃
├── resource-management/
│   └── README.md                  # 下一階段規劃
├── Makefile
├── README.md
├── TEST_RESULTS.md
├── .gitignore
├── .gitattributes                # 固定文字檔使用 Linux LF 換行
└── bin/                          # make 自動產生，忽略於 Git
```

## 1. Compile：Ubuntu / Linux

需要 C++11、g++、GNU make 和 pthread。Ubuntu 尚未安裝編譯工具時：

```bash
sudo apt update
sudo apt install build-essential
```

切換到專案目錄後一次編譯：

```bash
cd ticket-rush-os-demo
make
```

本專案會由 Windows 的 VMware Shared Folder 分享到 Ubuntu。
在你的 VMware Ubuntu terminal 中可直接使用：

```bash
cd /mnt/hgfs/ticket-rush-os-demo
make
./bin/concurrency_demo
./bin/scheduling_demo
./bin/race_demo
./bin/mutex_demo
```

Windows 原始碼位置：`C:\Users\User\Desktop\大三上\OS\presentation\ticket-rush-os-demo`。
不需要安裝或使用 WSL。

Makefile 使用 `-std=c++11 -O2 -Wall -Wextra -Wpedantic -pthread`。
可用 `make -j4` 平行編譯；清除產物用 `make clean`。
不需要 Python，第一階段全部是 C++。

## 2. 執行方式

```bash
./bin/concurrency_demo
./bin/scheduling_demo
./bin/race_demo
./bin/mutex_demo
```

四支程式都無需參數，也不需要額外資料或服務。
Concurrency 約需 2 秒；其他程式很快結束，適合直接在課堂重複展示。

## 3. Demo 1：Ticket Rush — Processes & Concurrency

```bash
./bin/concurrency_demo
```

程式依序執行 Sequential 與 Multithread，兩者各模擬 20 位使用者。
每個 request 用 `sleep_for(100 ms)` 模擬等待庫存或付款服務，並印出
`User N enters ticket system`、thread ID 和 `Total execution time`。

應觀察：

- Sequential：主執行緒一次處理一位使用者，通常約 2,000 ms。
- Multithread：20 個 worker threads 的等待時間可以重疊，通常約 100 ms 加上建立／排程成本。
- 同一次執行的兩個版本屬於同一個 process，開頭會顯示 PID。
- Sequential 的 thread ID 相同；Multithread 有不同的 thread ID，進入順序可能改變，也可能恰好照順序。
- 時間與加速比會因機器負載而變動；這不是 CPU 密集工作的 benchmark。

可以這樣講：

> 啟動 executable 時，OS 建立一個 process，提供位址空間與資源。
> 同一 process 裡的 threads 共用記憶體；當某個 thread 等待 I/O，其他
> runnable threads 可以繼續執行，所以很多 request 的生命週期能重疊。

**Concurrency** 是工作期間重疊；**Parallelism** 是多核心上真的同時執行。
這個範例即使只有一個 CPU core，也能透過重疊等待展現 concurrency。
它沒有另外 `fork()` 多個 processes；process 概念以啟動程式與 PID 展示。

**Context Switching** 是 OS 切換執行中的 threads／processes，需要保存、
恢復執行狀態。程式註解指出 `sleep_for`、排程與 `join` 的關係；
log 順序或 thread ID **不能直接量測切換次數**。
若 Ubuntu 已安裝 GNU time，可以額外觀察整個程式的切換統計：

```bash
/usr/bin/time -v ./bin/concurrency_demo
```

觀察 `Voluntary context switches` 和 `Involuntary context switches`；
這是 Sequential + Multithread 整次執行的統計，不是兩個版本分別的數字。

原始碼中的 `output_mutex` 只保護一行輸出，100 ms 等待在鎖外，
避免把所有 requests 意外串行化。

## 4. Demo 2：Who Runs First? — CPU Scheduling

```bash
./bin/scheduling_demo
```

固定使用以下四個 requests，時間單位是模擬 CPU time units：

| Request | Arrival Time | Burst Time |
|---|---:|---:|
| A | 0 | 8 |
| B | 1 | 2 |
| C | 2 | 4 |
| D | 3 | 1 |

每種策略都印出 Arrival、Burst、Waiting、Completion、Average Waiting Time
以及含時間區間的 Gantt Chart，例如 `| A [0,8) | B [8,10) | ... |`。
`[start,end)` 表示 start 含、end 不含，每格長度由區間決定，並非一律一個時間單位。

| 策略 | 預期執行順序 | A/B/C/D 的 Waiting | 平均 Waiting |
|---|---|---|---:|
| FCFS | A → B → C → D | 0 / 7 / 8 / 11 | 6.50 |
| SJF（non-preemptive） | A → D → B → C | 0 / 8 / 9 / 5 | 5.50 |
| Round Robin（quantum = 2） | A → B → C → A → D → C → A → A | 7 / 1 / 5 / 5 | 4.50 |

應觀察：

- **FCFS**：先到先服務，A 很長，使後面的短 requests 等待。
- **SJF**：只從「已到達」的 requests 選最短者。本例是 non-preemptive，
  所以 A 在 time 0 開始後不會被 B、C、D 中斷；time 8 才輪到 D。
- **Round Robin**：一次最多執行 2 time units；未完成的 request 回到 ready queue 尾端。
  某片段期間到達的 requests（包含片段結束時到達者）會先入隊，再放回目前的 request。
- A 最後兩段相鄰，是 queue 只剩 A；可接續執行，不代表每段都真的發生 thread 切換。

公式：`Waiting = Completion - Arrival - Burst`。
輸入需依 Arrival 排序，Burst > 0，quantum > 0；可在 `main()` 修改固定數值。
同 Arrival 或同 Burst 時保留輸入順序，沒有隱藏的隨機選擇。

這是**單顆 CPU 的演算法模擬器**，沒有修改 Linux 實際排程政策。
假設 Burst 已知、沒有 I/O、context-switch overhead 為 0。
本資料的 RR 平均等待最低，不代表它對所有 workloads 都最低。

## 5. Demo 3：The Last Ticket — Race Conditions & Locks

先執行無 Mutex 版本，再執行 Mutex 版本：

```bash
./bin/race_demo
./bin/mutex_demo
```

### Version A：Race Condition

起始庫存為 1，Alice、Bob、Charlie、David 同時購票。
各 thread 先讀庫存；教學用 rendezvous 等到四個人都完成檢查，
再等待 10 ms、各自扣票。這個安排保證重現「都先看到有票」的時序。

```text
Alice sees ticket = 1
Bob sees ticket = 1
Charlie sees ticket = 1
David sees ticket = 1
...四位買家皆 purchased ticket...
Successful purchases = 4
Tickets remaining = -3
```

**Race Condition**：檢查庫存時的值，到實際扣票時可能已不再有效。
錯誤發生在「讀取 → 判斷 → 更新」這個多步驟操作沒有一起被保護。

庫存使用 `std::atomic<int>`，沒有使用 Mutex。這刻意區分兩件事：

- 單次 `load` 與 `fetch_sub` 安全，不會造成 C++ 未定義行為。
- 多步驟的購票流程仍有**邏輯競爭**，atomic 不會自動把檢查與扣票變成同一個操作。

若直接讓普通 `int` 被多個 threads 無同步讀寫，那會是 C++ data race，
屬於未定義行為；可能出現 lost updates，也不能保證負庫存。
本版本選擇可解釋、可穩定重現的 overselling。
只有 delay 並不能保證每次超賣；rendezvous 才固定了要展示的競爭時序。

為保持 log 清楚，讀取／購買事件在 `join()` 後集中印出；
檢查行依姓名順序顯示，購買行依記錄順序顯示，並非 live tracing。
每個結果陣列元素只有一個 writer，主執行緒在所有 threads 結束後才讀取。

### Version B：Mutex

```text
Alice purchased the last ticket
Bob: SOLD OUT
Charlie: SOLD OUT
David: SOLD OUT
Successful purchases = 1
Tickets remaining = 0
```

這是可能的一次輸出；獲勝者與其他人的輸出順序可以不同。
一定只有一人買到、三人 SOLD OUT。`std::mutex` 不保證 FIFO 或固定贏家。

原始碼直接標示 `// Critical Section`。`std::lock_guard<std::mutex>`
保護「檢查 → 10 ms 延遲 → 扣票」，一次只有一個 thread 能進入。
其他 threads 取得鎖後會看見更新後的庫存 0，於是拒絕購買。
`lock_guard` 在離開 scope 時自動解鎖，這是 RAII。

可用下面的指令連續重跑，看到結果正確而贏家可能改變：

```bash
for i in 1 2 3; do ./bin/race_demo; ./bin/mutex_demo; done
```

兩支程式若最終結果不符合預期，會回傳非零 exit status。
Mutex 內的 delay 只為對照教學；正式服務應縮短 Critical Section，
不要在鎖內等待慢速網路或付款。

## 6. 課堂 Demo 順序（約 5–8 分鐘）

1. `make`：展示 C++11 和 pthread 編譯方式。
2. `./bin/concurrency_demo`：比較總時間、PID 與 thread IDs，說明 overlapping I/O waits。
3. `./bin/scheduling_demo`：用 A 的長工作解釋 FCFS 等待，再比較 SJF 與 RR。
4. `./bin/race_demo`：指出四個人都看到 1，但四個人都扣票，剩下 -3。
5. `./bin/mutex_demo`：打開 `// Critical Section` 的原始碼，再展示只剩一人成功。

## 7. 下一階段：Socket / epoll / Resource Management

| 主題 | 建議實作 | 可觀察的 OS 現象 |
|---|---|---|
| Too Many Connections | localhost TCP server + Python 大量 clients | 每條連線占 FD；`ulimit -n`、`/proc/<pid>/fd`、`EMFILE` |
| Handling Massive I/O | blocking server vs non-blocking + level-triggered epoll | readiness、`EAGAIN`、單執行緒管理多條連線、partial I/O |
| Surviving the Rush | 固定 worker pool、bounded queue、上限、timeout、BUSY 回應 | thread／FD／memory 限制、backpressure、過載時保留服務能力 |

先做 socket 基線，再做 epoll 比較，最後加入資源限制與同一套負載測試。
Python 只負責啟動大量 clients；server 與資源策略繼續使用 C++11。
三個目錄目前只有規劃，尚未宣稱具備伺服器功能。

## 8. 實測環境

詳細結果見 [TEST_RESULTS.md](TEST_RESULTS.md)。主要目標是你的 VMware Ubuntu。
Codex 目前只能在 Windows 工作區做 MinGW 額外驗證，無法直接操作 VM terminal；
Ubuntu 的實際編譯與執行結果由你在 VM 中取得，再提供給 Codex 修正。

Makefile 預設使用 Linux 的 `mkdir -p`、`rm -rf`、`g++` 與 pthread。
本機額外驗證時才傳入 `EXE=.exe` 和 Git Bash 的 shell 路徑，例如：

```powershell
$env:PATH = 'C:\Program Files\Git\usr\bin;' + $env:PATH
mingw32-make 'SHELL=C:/Program Files/Git/bin/sh.exe' EXE=.exe
./bin/concurrency_demo.exe
./bin/scheduling_demo.exe
./bin/race_demo.exe
./bin/mutex_demo.exe
```

Ubuntu 版本使用前述的 `make` 與不含 `.exe` 的名稱。
第一階段除顯示 PID 的平台分支外，其餘程式使用標準 C++11。
