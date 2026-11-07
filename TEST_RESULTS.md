# 測試紀錄：Phase 1 / Phase 2

日期：2026-10-04（Asia/Taipei）。以下先保留 Phase 1 的原始測試紀錄；Phase 2 在後段。

最新狀態（2026-11-07）：使用者回報 Ubuntu VM 的 concurrency 計時為 2009.97 ms / 111.85 ms，17.97x；詳見本文末段。2026-10-29 的 Phase 2 `make test` 全部通過紀錄仍保留。
詳細數字與驗證範圍見本文末段。前段「尚未實測」為初次交付時的歷史紀錄。

## 測試範圍與環境

- 實際執行環境：Windows PowerShell。
- 編譯器：MinGW-W64 g++ 13.3.0，POSIX threads 版本。
- 建置工具：GNU Make 4.4.1（`mingw32-make`）。
- 編譯參數：`-std=c++11 -O2 -Wall -Wextra -Wpedantic -pthread`。
- 使用 Git 的 Unix utilities 讓本機 make 執行 Linux Makefile 的 `mkdir -p`。
- **Ubuntu VM 尚未實測**。Windows 結果是額外驗證，不代表 Ubuntu runtime 的實際結果。

## 編譯

在專案根目錄實際呼叫 `make`（PowerShell alias 指向 `mingw32-make.exe`）：

```powershell
$env:PATH = 'C:\Program Files\Git\usr\bin;' + $env:PATH
Set-Alias -Name make -Value mingw32-make.exe
make 'SHELL=C:/Program Files/Git/bin/sh.exe' EXE=.exe
```

四個 targets 均成功產生，make exit code 為 0；沒有 compilation error 或 warning。
`EXE=.exe` 與 shell override 只用於這次 Windows 額外驗證，Ubuntu 不需要這些參數。

## 實際執行結果

四支程式都實際執行，exit code 全部為 0。

| Demo | 觀察到的結果 |
|---|---|
| Concurrency — Sequential | 20 位使用者依序進入，同一 thread ID；總時間 **2207.51 ms** |
| Concurrency — Multithread | 20 位使用者、不同 thread IDs、進入順序交錯；總時間 **111.89 ms** |
| Concurrency — 比較 | 顯示加速比 **19.73x**，來自模擬 I/O 等待重疊 |
| Scheduling — FCFS | A/B/C/D waiting = 0/7/8/11；平均 **6.50** |
| Scheduling — SJF | A/B/C/D waiting = 0/8/9/5；平均 **5.50** |
| Scheduling — RR | A/B/C/D waiting = 7/1/5/5；平均 **4.50**；quantum = 2 |
| Race | 四人都看到 1，四人購票成功，庫存 **−3** |
| Mutex | 一人購票成功，三人 SOLD OUT，庫存 **0** |

Scheduling 的 Waiting、Completion 與 Gantt Chart 已與手算結果比對：

```text
FCFS: | A [0,8) | B [8,10) | C [10,14) | D [14,15) |
SJF:  | A [0,8) | D [8,9) | B [9,11) | C [11,15) |
RR:   | A [0,2) | B [2,4) | C [4,6) | A [6,8) | D [8,9) |
      | C [9,11) | A [11,13) | A [13,15) |
```

## 超賣與鎖的重複驗證

除了上述各一次的展示執行，另以迴圈分別再跑 25 次，檢查 exit status 與輸出：

- Race：**25/25 通過**。每次四人看到 1、四次成功購票、庫存 −3。
- Mutex：**25/25 通過**。每次一次成功購票、三次 SOLD OUT、庫存 0。
- Mutex 的 25 次獲勝者：Alice 6 次、Bob 9 次、Charlie 6 次、David 4 次。

Race 使用 rendezvous 固定「所有人先檢查，之後才扣票」的時序；不是只靠 delay 碰運氣。
Atomic 避免 C++ data race 的未定義行為，但 check-then-act 流程仍有邏輯競爭。
Mutex 將完整檢查與扣票包在 `// Critical Section` 中，維持庫存正確。

## 在 VMware Ubuntu 取得 Linux 結果

Windows 與 Ubuntu 透過 VMware Shared Folder 使用同一份原始碼。
請在 Ubuntu terminal 執行：

```bash
cd /mnt/hgfs/presentation/ticket-rush-os-demo
make
./bin/concurrency_demo
./bin/scheduling_demo
./bin/race_demo
./bin/mutex_demo
```

Ubuntu 預期產生不帶 `.exe` 的 binaries。Concurrency 時間與購票贏家可能不同；
排程表、Race 四次成功與 −3、Mutex 一次成功與 0 的結果應相同。
若有錯誤，保留 make／程式的 terminal 輸出，供後續修正。

## Phase 2 — 已實際完成的 Windows 額外驗證

Linux-only 網路程式不在 Windows 強行編譯；沒有安裝或尋找 WSL。
以下只代表 portable 資源模擬器與 Python client 的本機驗證。
Phase 1 的四份 C++ 原始碼經 `git diff` 確認未變動，`make phase1` 仍可選擇原 targets。

實際建置：

```powershell
$env:PATH = 'C:\Program Files\Git\usr\bin;' + $env:PATH
mingw32-make 'SHELL=C:/Program Files/Git/bin/sh.exe' EXE=.exe phase1 bin/resource_uncontrolled_demo.exe bin/resource_protected_demo.exe
```

g++ 13.3.0、C++11、原本的 warning flags；兩支資源程式編譯成功，沒有 warning/error。

| 實際執行 | Incoming | Processed | Rejected | Max queue size | Workers |
|---|---:|---:|---:|---:|---:|
| Uncontrolled（預設） | 1000 | 1000 | 0 | 1000 | 4 |
| Protected（預設） | 1000 | 915 | 85 | 20 | 4 |

兩者 exit code = 0，Accepted = Processed，Pending after drain = 0。
Uncontrolled 觀察到 Pending 逐步上升至 200、500、900、1000。
Protected 印出 Queue full、1 ms backpressure wait 與 rejected (BUSY)。
實際 wait_for 時間受 OS timer／排程影響，Ubuntu 的接收／拒絕數可能明顯不同。
兩支程式各另驗證 1 request：Processed = 1、Rejected = 0；輸入 0 皆回傳非零狀態。

Python 驗證使用本機暫時的 **Python TCP fixture**，不是 Linux C++ server：

- Python 檔案 AST syntax check 通過。
- 8 clients × 3 BUY：收到 **24/24 replies**、Failures = 0；fixture 刻意分段傳送回覆。
- 4 idle clients：不送 BUY，連線與清理成功、Failures = 0。

## Phase 2 — 初次交付時的 Ubuntu 待驗證項目

以下為 2026-10-04 初次交付時的待驗證項目；2026-10-29 的驗證結果見末段：

- Linux g++ 編譯 `socket_server`、`blocking_server`、`epoll_server`。
- `make` 全九支程式的 Ubuntu 建置。
- Linux accept / fcntl / epoll / FD 與 thread 的實際行為。
- Ubuntu integration test、Ctrl+C 清理、100／500 client 負載、選用 EMFILE 實驗。

在 VM terminal：

```bash
cd /mnt/hgfs/presentation/ticket-rush-os-demo
make -j4
make test
```

`make test` 會自動啟動並清理三個 server，檢查 framing、half-close、client reset、
行長上限、32 idle client FD/thread 行為、關閉後的 FD 回收、SIGINT 清理、
無效 ports、資源統計守恆與 queue bound。它不檢查固定拒絕數，也不宣稱涵蓋所有 partial-send 情境。
README 各章另有手動 100／500 connections 的完整步驟。

目前程式碼準備好供 Ubuntu 驗證；沒有 git commit 或 push Phase 2 修改。

## 2026-10-29 — Ubuntu 回報與啟動探測修正

使用者提供的 terminal 截圖顯示：

- 建置已進入 `python3 tests/ubuntu_smoke.py`，未出現 compiler error。
- `socket_server`、`blocking_server` 的 smoke check 顯示 PASS。
- epoll 測試停在 32 idle clients 的 FD 數量等待，錯誤為 `idle clients not accepted`。
- 本輪尚未執行到資源模擬器的 Ubuntu 檢查。

程式檢查找到測試本身確定存在的 startup race：connect 成功不保證 accept 已完成；
在尚未 accept 時，server 的 FD 數也可能等於無連線基準。之後若正好在讀取 baseline 時
accept 探測連線，就可能記到短暫多出的 FD，造成 idle 連線門檻錯誤。
此漏洞可造成截圖中的誤報；截圖本身未提供實際 FD 數，仍需 Ubuntu 重跑確認這次失敗已解決。

修正：啟動探測送 `BUY\n` 並收到 `REQUEST RECEIVED\n`，才關閉 client、
等待 server FD 回到無 client 的基準。Protocol cases 結束後也先等 FD 清理，再建立 idle clients。
保留原本 32 條連線與 thread 數的要求，沒有降低門檻或單純延長 timeout。
失敗輸出新增 baseline／expected／observed 和 server log，並保留原始測試例外。

新增 `tests/test_smoke_startup.py`：驗證收到回覆前不能讀取 FD 基準、拒絕錯誤啟動回覆、
測試失敗但 server 正常關閉時仍保留 log。
Windows Python 實際執行：修正前 **3 failures**，修正後 **3 passed**。
這些是 portable mock 回歸測試，**不是修正後 Ubuntu epoll 整合測試已通過的證據**。

共享資料夾已直接同步修正。在 Ubuntu 重跑：

```bash
cd /mnt/hgfs/presentation/ticket-rush-os-demo
make test
```

本次沒有更動 Phase 1 或 C++ server，也沒有 commit／push。

## 2026-10-29 — VMware Ubuntu 重跑全部通過

證據來源：使用者提供的 Ubuntu terminal 截圖（畫面時間 15:04），不是 Codex 本機執行。
啟動同步回歸測試顯示 OK，接續的整合測試最後印出：

```text
PASS socket_server: framing, half-close, reset, 32 idle FDs/threads, cleanup, SIGINT
PASS blocking_server: framing, half-close, reset, 32 idle FDs/threads, cleanup, SIGINT
PASS epoll_server: framing, half-close, reset, 32 idle FDs/threads, cleanup, SIGINT
All Phase 2 Ubuntu smoke checks passed.
```

| 資源模擬器 | Incoming | Accepted / Processed | Rejected | Max queue size | Workers | Pending after drain |
|---|---:|---:|---:|---:|---:|---:|
| Uncontrolled | 1000 | 1000 | 0 | 997 | 4 | 0 |
| Uncontrolled（單筆） | 1 | 1 | 0 | 1 | 4 | 0 |
| Protected | 1000 | 378 | 622 | 20 | 4 | 0 |
| Protected（單筆） | 1 | 1 | 0 | 1 | 4 | 0 |

三個網路版本及資源模擬器的自動檢查均通過；epoll 的 idle FD 檢查在啟動同步修正後通過。
Protected 保持 queue 上限 20，378 + 622 = 1000，符合預期守恆；拒絕數不是固定規格。
此輪 make test 亦涵蓋無效 port 檢查，但不代表已實際操作手動 100／500 clients、
EMFILE、所有 slow-reader／partial-send 壓力情境，或重新執行 Phase 1 四支程式。

README 已更新至此實測狀態；本次僅更新文件，沒有 commit／push。

## 2026-11-07 Ubuntu Concurrency 使用者回報

資料來源：使用者在本次對話明確提供的 Ubuntu VM 實測結果。不是助理在 Windows 執行，也不是助理直接在 Ubuntu 重跑取得。

| 項目 | 使用者回報 |
|---|---|
| Environment | Ubuntu VM |
| Kernel | Linux 7.0.0-38-generic |
| Workload | 20 users，每筆 100 ms simulated I/O wait |
| Sequential | 2009.97 ms |
| Multithread | 111.85 ms |
| Speedup | 17.97x |

數值比對：2009.97 / 111.85 = 17.97022798，四捨五入至兩位為 17.97x。
改善來自模擬 I/O 等待時間重疊，不代表 CPU 本身執行速度提升，亦不是 CPU 密集工作吞吐量 benchmark。
沒有提供原始 log、重複執行次數或彙總方式，故不把本組數字宣稱為平均值或三次中位數。
簡報 P5 與本次 Reviewed 講稿使用這組 Ubuntu 結果；前面的 Windows MinGW 數字保留為歷史紀錄。
