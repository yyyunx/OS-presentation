# From Click to Checkout: An Operating System Perspective on Online Ticketing

專案名稱：`ticket-rush-os-demo`

## Concert Ticket Rush Dashboard

### 左邊 Dashboard、右邊真正 Ubuntu Terminal（建議報告模式）

兩個 Terminal 都先 `cd` 到**同一份 Ubuntu 專案**，例如
`/mnt/hgfs/presentation/ticket-rush-os-demo`。事先執行：

```bash
make
make test
make test-demo-ui
make test-demo-proof
```

```bash
# Terminal A：保留在背景，啟動 Dashboard 控制器
make demo-ui
```

```bash
# Terminal B：真正的 Ubuntu Terminal，放在畫面右邊
make demo-proof
```

在**同一台 Ubuntu VM** 的瀏覽器開啟 **http://127.0.0.1:8765**，放在左邊。
Ubuntu GNOME 可選取瀏覽器按 `Super+Left`，選取 Terminal B 按 `Super+Right`；
其他桌面可直接拖曳到螢幕左右邊緣。Terminal A 留在背景，視需要調小字體／瀏覽器縮放。
Terminal B 是獨立 Python 監看程式，沒有嵌入網頁的假 Terminal。

依序操作左側 **Ticket Safety → Run experiment**、
**Connection Rush → 100 idle connections → Run experiment**、
**Traffic Control → Run experiment**，右側會同步顯示：

- 真實 executable／argv、PID、UTC 啟動與結束觀測時間、Exit Code 和清理結果。
- Race/Mutex 的購票／剩餘票／超賣結果；程式即使很快結束，也不會被狀態輪詢漏掉。
- 保持連線期間每約 0.8 秒讀取 Linux `/proc` 的 Threads／FDs，搭配 client 實際輸出的 Connected／Failures。
- Queue 的 Incoming／Processed／Rejected／Max Queue／Workers，以及守恆檢查。

終端只列關鍵摘要，不列出每條 client 連線。完整 stdout/stderr 保存在忽略於 Git 的
`.runtime/demo-proof/`；Technical Logs 可開啟完整輸出（頁內預覽仍限最後 24,000 字元）。
`Completed` 表示驗證與清理結束；之後保留的數字標成 `Historical`。
`Error` 保留失敗／取消證據；Reset 清除瀏覽器卡片，但不清空 Terminal。
Terminal B 按 `Ctrl+C` 只停止監看；全部展示結束後，在 Terminal A 按 `Ctrl+C` 才停止控制器。

詳細機制、重啟／歷史／故障處理見 [Terminal 證據模式](docs/DEMO_PROOF.md)；
完整英文逐字稿見 [3–4 分鐘雙視窗展示流程](presentation/Dashboard_Terminal_4min_Demo.md)。
這次修改的測試狀態見 [Terminal proof 測試紀錄](docs/DEMO_PROOF_TEST_RESULTS.md)，
下方 2026-11-07 的舊 CI 成績不能代替本次修改的測試。
Windows 要直接連入現有 VMware Ubuntu 執行測試，見
[VMware SSH 設定與測試](docs/VMWARE_SSH.md)；這不影響報告使用真正 Ubuntu Terminal。

Ubuntu 專案根目錄執行 `make demo-ui`，再以同一台 VM 的瀏覽器開啟
**http://127.0.0.1:8765**。三個場景為 Ticket Safety、Connection Rush、Traffic Control；
所有數字來自既有程式輸出與 Linux `/proc`，動畫另外標示為教學示意。
2026-11-07 已在 GitHub Ubuntu 24.04 CI 通過 `make`、`make test` 與
`make test-demo-ui`，包括 100／500 idle connections 及停止／清理；詳見下方實測紀錄。

- [啟動、展示、停止／清理及測試步驟](docs/DASHBOARD.md)
- [三分鐘英文 Demo 操作稿與 PPT P14 修改建議](presentation/Dashboard_3min_Demo_and_P14.md)
- [本次實際測試紀錄](docs/DASHBOARD_TEST_RESULTS.md)

執行 `make test-demo-ui` 可驗證 Race/Mutex、100 idle clients 對照、500 epoll
idle clients、1000 requests、取消與 port 衝突，並保存原始輸出和測量紀錄。

## 報告與展示資料

15 分鐘英文報告的中英對照講稿、Ubuntu Demo 指令和 P5 計時來源整理於
[presentation/](presentation/README.md)。本次修訂統一 Demo 為 Race/Mutex、
8081 與 8082 各 100 條 idle connections、`--hold 60`，最後比較資源統計。
P5 使用使用者於 2026-11-07 回報的 Ubuntu VM 結果：Sequential 2009.97 ms、
Multithread 111.85 ms、17.97x；加速來自模擬 I/O 等待重疊，不是 CPU 本身變快。

這是 OS 課程的 terminal 實作 Demo，以熱門演唱會搶票展示作業系統概念。
不是實際售票網站；新增的本機 Dashboard 僅控制既有實驗，沒有 Web framework 或支付功能。
Phase 1 與 Phase 2 的六個 Demo 已完成實作。主要執行環境為 VMware Ubuntu，
使用 Linux API、C++11、g++、Makefile；Python 用於大量 clients、測試及標準函式庫本機 Dashboard 控制器。
Phase 1 的四份 C++ 原始碼與行為保留不變。
2026-10-29 使用者已在 VMware Ubuntu 完成 Phase 2 的 `make test`，全部通過。

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
│   ├── socket_server.cpp
│   ├── blocking_ticket_server.h   # Demo 4 / Demo 5 A 共用 blocking 實作
│   ├── net_utils.h                # Linux socket / protocol 小型共用函式
│   ├── load_clients.py
│   └── README.md
├── epoll-server/
│   ├── blocking_server.cpp
│   ├── epoll_server.cpp
│   └── README.md
├── resource-management/
│   ├── request_simulator.h
│   ├── resource_uncontrolled_demo.cpp
│   ├── resource_protected_demo.cpp
│   └── README.md
├── tests/
│   ├── ubuntu_smoke.py
│   └── test_smoke_startup.py      # 啟動握手與錯誤診斷的 portable 回歸測試
├── Makefile
├── README.md
├── TEST_RESULTS.md
├── .gitignore
├── .gitattributes                # 固定文字檔使用 Linux LF 換行
└── bin/                          # make 自動產生，忽略於 Git
```

## Compile：Ubuntu / Linux

需要 C++11、g++、GNU make、pthread 和 Python 3。Ubuntu 尚未安裝工具時：

```bash
sudo apt update
sudo apt install build-essential python3
```

切換到專案目錄後一次編譯：

```bash
cd ticket-rush-os-demo
make
```

本專案會由 Windows 的 VMware Shared Folder 分享到 Ubuntu。
2026-10-29 核對 VMware 設定：共享名稱為 `presentation`，host path 是本專案的上一層。
因此 Ubuntu 的專案路徑包含 `presentation/ticket-rush-os-demo`；
`~/Documents/ticket-rush-os-demo` 是不同的本機路徑，不會自動與 Windows 同步。
在你的 VMware Ubuntu terminal 中可直接使用：

```bash
cd /mnt/hgfs/presentation/ticket-rush-os-demo
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
`make` 建置全部九支 C++ executables；Python 不需要編譯或 pip 套件。
也可用 `make phase1` 或 `make phase2` 只建置一個階段。

## 快速執行

```bash
./bin/concurrency_demo
./bin/scheduling_demo
./bin/race_demo
./bin/mutex_demo

./bin/socket_server              # 8080，Ctrl+C 結束
./bin/blocking_server            # 8081，Ctrl+C 結束
./bin/epoll_server               # 8082，Ctrl+C 結束
./bin/resource_uncontrolled_demo
./bin/resource_protected_demo
```

以上是九支程式的獨立執行指令；三個 server 會持續執行，請分開 terminal 操作，
用 Ctrl+C 結束後再切換。Server 僅綁定 `127.0.0.1`，clients 也在同一台 Ubuntu VM 執行。
Server 可加 port 參數，例如 `./bin/epoll_server 9090`，client 對應加 `--port 9090`。
資源模擬器預設 1000 requests；可用 `[incoming] [arrival_delay_ms]` 改變負載。

## 1. Processes & Concurrency

**OS concepts：** Process、Thread、Concurrency、Context Switching。
**Ticketing scenario：** 20 位使用者進入售票系統，等待外部服務回應。
**執行：**

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

## 2. CPU Scheduling

**OS concepts：** FCFS、non-preemptive SJF、Round Robin、ready queue、preemption。
**Ticketing scenario：** 售票系統已收到 A–D 的 requests，哪一個先取得 CPU？
**執行：**

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

**報告可以這樣解釋：**

> FCFS 按到達順序，長 request 會拖住後面的人；SJF 在 CPU 空出來時挑最短的已到達工作。
> Round Robin 每人輪流使用一段時間，改善等待初次服務的機會，但切換也有成本。

## 3. Race Condition & Mutex

**OS concepts：** shared state、check-then-act race、atomic、Critical Section、mutual exclusion。
**Ticketing scenario：** 四位買家同時購買最後一張票。

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

**報告可以這樣解釋：**

> 單次讀寫是 atomic，並不等於整個購票流程是 atomic。Mutex 必須把「檢查＋扣票」
> 一起包住，下一個買家才會看到更新後的庫存。

## 4. Socket & File Descriptor

**OS concepts：** TCP、Client/Server、socket、bind、listen、accept、File Descriptor。
**Ticketing scenario：** 大量買家連到售票系統，每一條已接受的連線都需要一個 server socket FD。

**執行（兩個 Ubuntu terminals，各先 cd 到專案根目錄）：**

```bash
# Terminal A
./bin/socket_server
```

```bash
# Terminal B：建立 100 connections，送 BUY 並等待回覆，再保持 20 秒
python3 socket-server/load_clients.py 100
```

若在 `socket-server/` 目錄，可直接 `python3 load_clients.py 100`。
先用一位買家確認協定：

```bash
python3 socket-server/load_clients.py 1 --hold 0
```

Server 顯示 listening port、PID、listening FD、每位 client 的 connected FD 和 active count。
Client 顯示 `Replies: 100 / 100`，保持連線期間可觀察：

```bash
# Terminal C：把 server 啟動時顯示的 PID 填入
server_pid=12345
ls /proc/$server_pid/fd
ls /proc/$server_pid/fd | wc -l
grep Threads /proc/$server_pid/status
ulimit -n
```

**Demo 時觀察：** active count 上升到 100，clients 結束後下降到 0；
`/proc/<pid>/fd` 的總數還包含 stdin/stdout/stderr 和 listening socket，不能當作純 client 數量。
FD 數字只在同一 process 內有意義，server FD 與 Python client FD 不相同；關閉後數字可再利用。
`listen()` backlog 是尚未被 accept 的連線排隊，與已連線數／request queue 不同。

協定是純文字、每行一筆：`BUY\n` → `REQUEST RECEIVED\n`；未知指令回覆
`UNKNOWN COMMAND\n`。TCP 不保留訊息邊界，程式累積到 newline 才處理，
支援分段到達、多筆黏在一次 recv、CRLF。這只確認收到 request，沒有實際扣票。
單行最多 1024 bytes，超過會回覆 `ERROR: LINE TOO LONG` 並關閉。

**選用 FD 上限 Demo：** 只在 server 的 subshell 降低上限，讓 Python client 的上限不受影響。
先用 Ctrl+C 停止原 server，再執行：

```bash
# Terminal A
(ulimit -n 64; ./bin/socket_server)
# Terminal B
python3 socket-server/load_clients.py 100 --idle --hold 10 --timeout 3
```

達到 FD 上限時可能看到 `Too many open files`（EMFILE），server 會報錯、清理並結束，
client 的失敗與非零 exit status 是這個選用實驗的預期結果。此教學 baseline 並未實作持續服務的 EMFILE 恢復策略。

**報告可以這樣解釋：**

> Listening socket 負責等新連線；accept 產生另一個已連線 socket。
> 一萬位使用者不是一個 socket，而是很多個 FD 與 kernel socket 資源。
> 即使大家都還沒送 BUY，這些連線也已經占資源。

## 5. Non-blocking I/O & epoll

**OS concepts：** blocking、non-blocking、fcntl/O_NONBLOCK、readiness、epoll、partial I/O。
**Ticketing scenario：** 大量使用者保持連線，大部分時間都在等，只有少數人送出 request。

**Version A：blocking / thread-per-client**（預設 port 8081）：

```bash
# Terminal A
./bin/blocking_server
# Terminal B
python3 socket-server/load_clients.py 100 --port 8081 --idle --hold 30
```

Server 顯示 `Client N -> Thread ... (FD ...)`。用前章的 `/proc` 指令觀察，
約有 main + 100 個 client threads，多數 worker 阻塞在 `recv()`。
Demo 4 與 Version A **共用** `blocking_ticket_server.h`，差別是標題與預設 port，
確保比較時協定與 client 行為相同。Finished threads 的 join bookkeeping 會保留到 server 結束；
這是簡單教學 baseline，正式服務還需要回收已完成 workers。

**Version B：epoll**（預設 port 8082）：

```bash
# Terminal A
./bin/epoll_server
# Terminal B
python3 socket-server/load_clients.py 100 --port 8082 --idle --hold 30
# 再跑同樣的 100 connections，這次送出 BUY
python3 socket-server/load_clients.py 100 --port 8082 --hold 20
```

在另一個 terminal 用 PID 觀察 FD／Threads。先完成 100 的比較，再可加到 500：

```bash
python3 socket-server/load_clients.py 500 --port 8082 --hold 30
```

**Demo 時觀察：** epoll 一樣需要每條連線的 FD，但 `Threads: 1`。
Idle connections 會累積在 `Monitoring N connections`；有資料或斷線時才出現
`Ready events: N` 和 `Handling FD ...`。Ready events 包含 listener、資料、關閉通知，
不是一定有 N 個 BUY，也不是監控連線總數。斷線後 Monitoring 應回到 0。
如果 ulimit 低於實驗所需的 FDs，先減少 clients；epoll 不會移除 FD 上限。

- **Blocking I/O：** `recv()` 沒資料時讓呼叫它的 thread 睡眠等待。本例每 client 一個 worker；
  阻塞的 thread 不代表一直消耗 CPU，但仍有 stack、排程與管理成本。
- **Non-blocking I/O：** 加上 `O_NONBLOCK` 後，沒有資料／送不出去時立即回傳 `EAGAIN`，
  程式保留狀態，稍後再試，不在這個 FD 上等待。
- **epoll：** kernel 追蹤已登記的 FDs，`epoll_wait()` 等到有 readiness 再回傳事件。
  Event loop 的 `epoll_wait()` 可以睡眠等待，個別 socket 的 `recv/send` 則不阻塞。
- 使用 level-triggered 模式。`epoll_ctl(ADD/MOD/DEL)` 管理監控，`fcntl` 同時設定 listener
  與 accept 後的 sockets；Linux 的 accept 不會自動繼承 listener 的 O_NONBLOCK。
- Readiness 表示可以嘗試 I/O，不保證拿到完整指令。程式處理 partial reads/writes、
  `EINTR`、`EAGAIN`、EOF、peer half-close、錯誤與 FD 清理。
- 只有存在尚未送完的資料才登記 `EPOLLOUT`，避免一直可寫造成 busy loop。
  每個 client 的待傳回覆最多 64 KiB，避免慢速讀取者造成無限 buffer 累積。

三支 server 都可 Ctrl+C 關閉。Blocking 版本用 `shutdown()` 喚醒 recv/send 中的 workers，
再 join、close；epoll 版本清理 client sockets、listening socket 和 epoll FD。

**報告可以這樣解釋：**

> Thread-per-client 是每位客人安排一位服務人員，即使客人只是等待。
> epoll 讓一個服務人員先等 OS 通知哪幾位客人有事，再處理那些 ready sockets。
> 它減少等待型連線需要的 threads；CPU 密集或慢速工作仍應移到其他 workers。

這裡比較架構與資源，不以 terminal log 的執行速度當效能 benchmark。

## 6. Resource Management

**OS concepts：** fixed thread pool、producer/consumer、condition variable、bounded queue、backpressure、load shedding。
**Ticketing scenario：** 1000 個 requests 突然到達，但只有 4 個 worker threads。
這是本機 request server simulator，不是網路 server，也不會真的把 VM 撐到崩潰。

**執行：**

```bash
./bin/resource_uncontrolled_demo
./bin/resource_protected_demo
```

兩者都採用同樣的 4 workers，每筆工作模擬 10 ms 處理時間，隔離 queue policy 的差異。

| Version | 接收策略 | 應觀察 |
|---|---|---|
| Uncontrolled | 全收、沒有 pending queue 容量上限 | Pending 可能達 200／500／900 附近；1000 全部處理，Rejected = 0 |
| Protected | Pending queue 上限 20；滿時等至多 1 ms，仍滿就拒絕 | Queue full、rejected (BUSY)、Max queue size ≤ 20，總數守恆 |

**Fixed Thread Pool：** 只建立 4 workers，工作在 queue lock 外處理。
**Bounded Queue：** 檢查容量與 enqueue 在同一個 Critical Section。
**Backpressure：** queue 滿時，producer 透過 `condition_variable::wait_for` 短暫等待，
讓 request 的提交速度受到 worker 容量影響；等待時釋放 mutex。
**Load Shedding：** 等待期限到仍無容量，就回覆模擬的 BUSY 並丟棄該 request。
Workers 無工作時用 condition variable 睡眠，結束時排空已接收的工作再 join。

最後會印 Incoming、Accepted、Processed、Rejected、Max queue size、Worker threads、Pending after drain。
必須滿足 `Processed + Rejected = Incoming`、`Processed = Accepted`、`Pending after drain = 0`。
Queue size 只算等待中的 requests，不包含最多 4 筆正在處理的工作；protected 同時保留的工作最多 24 筆。
實際接受／拒絕數取決於排程與 timer，**不要期待固定是 350／650**。

可以調整輸入量、比較較平緩的到達速度：

```bash
./bin/resource_uncontrolled_demo 1000 1
./bin/resource_protected_demo 1000 1
./bin/resource_protected_demo 10
```

第二個參數為每筆提交之間的 delay（ms）。例如 `10` requests 通常全數接收，
負載較平緩時 queue 較不容易滿。Uncontrolled 的「unbounded」是策略無上限；
本次實驗是有限 1000 requests，並未量測記憶體耗盡或宣稱已觀察到 OOM。

**報告可以這樣解釋：**

> 當到達速度超過處理速度，全收只會累積等待與記憶體需求。
> 限制 workers 和 queue、短暫回壓、必要時拒絕新 request，能保留已接收工作的完成能力。
> 資源管理的目的，是讓 server 在高流量下仍能維持可控的工作量。

## Ubuntu 驗證步驟

```bash
cd /mnt/hgfs/presentation/ticket-rush-os-demo
make -j4
make test
```

`make test` 使用 Python standard library，在 localhost 自動啟動三個 server，
使用暫時選擇的 ports，驗證分段／多筆指令、未知指令、half-close、過長指令、
client reset、32 idle connections 的 FD／thread 行為、斷線回收、Ctrl+C 與資源統計。
也檢查無效 port 參數及小負載（1 request）。測試會清理自己啟動的 processes。
測試先執行啟動同步的回歸測試，再跑 Linux 整合測試。啟動探測會送 BUY、讀到回覆、
關閉探測連線並等待 server 清理其 FD，避免將尚待 accept／close 的探測 FD 誤算進基準。
失敗時會顯示 server log；idle 連線逾時會附上 baseline、expected、observed FD 數。
它不取代現場 100／500 clients 的 terminal 觀察，亦未模擬所有 slow-client／partial-send 情境。

Phase 1 仍可照原指令執行四支程式確認既有行為。
如果 VMware shared folder 上編譯成功、執行卻回報 Permission denied（noexec mount），
可只把 binaries 放到 Ubuntu home 的可執行檔案系統：

```bash
cp -r bin ~/ticket-rush-os-demo-bin
~/ticket-rush-os-demo-bin/epoll_server
```

自動 smoke test 需要根目錄的 `bin/` 可執行；若遇到 noexec，可將整份專案複製到 VM home，
在該份專案重新 make/test。將完整 compiler error 或 `make test` 輸出提供給 Codex 供後續修正。

## 建議現場順序（約 12–15 分鐘）

1. 提前 `make`、`make test`，再以 Phase 1 三個 Demo 開場。
2. Socket server＋1 client，說明協定與 listener / accepted FD。
3. 改成 100 clients、保持連線，觀察 active count 和 `/proc/<pid>/fd`。
4. Blocking server＋100 idle clients，觀察 Threads；Ctrl+C 結束。
5. epoll server＋同樣 100 idle clients，再送 BUY；觀察 Threads = 1 與 ready events。
6. 比較 uncontrolled / protected 統計，用 Max queue size 和拒絕數收尾。

FD 上限與 500 clients 是可選加分實驗；先確認 100 clients 在 VM 穩定。

## 實測狀態

既有歷史驗證詳見 [TEST_RESULTS.md](TEST_RESULTS.md)；Dashboard 新增驗證見
[本次紀錄](docs/DASHBOARD_TEST_RESULTS.md)。下段為舊有 Windows／VMware 紀錄。
Phase 1 沿用原本已通過的測試；Phase 2 的資源模擬器可以做 MinGW 額外驗證。
2026-10-29 修正啟動探測的 FD 基準時序漏洞後，使用者在 VMware Ubuntu 重跑 `make test`，
截圖顯示 **All Phase 2 Ubuntu smoke checks passed**：三支網路 server、
32 idle connections 的 FD/thread、protocol、清理、SIGINT 及資源統計檢查全部通過。
Uncontrolled：1000 processed、0 rejected、最大 queue 997；
Protected：378 processed、622 rejected、最大 queue 20，兩者皆為 4 workers 且完成後 queue 為 0。
兩種資源版本的單筆 request 也通過。這是使用者 VM 提供的實測證據，
不包含尚未回報的手動 100／500 clients 或 EMFILE 實驗。

Windows 額外驗證只建置 portable targets，不執行預設全部建置：

```powershell
$env:PATH = 'C:\Program Files\Git\usr\bin;' + $env:PATH
mingw32-make 'SHELL=C:/Program Files/Git/bin/sh.exe' EXE=.exe phase1 bin/resource_uncontrolled_demo.exe bin/resource_protected_demo.exe
```
