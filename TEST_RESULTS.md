# 第一階段實際測試結果

日期：2026-10-04（Asia/Taipei）。

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
cd /mnt/hgfs/ticket-rush-os-demo
make
./bin/concurrency_demo
./bin/scheduling_demo
./bin/race_demo
./bin/mutex_demo
```

Ubuntu 預期產生不帶 `.exe` 的 binaries。Concurrency 時間與購票贏家可能不同；
排程表、Race 四次成功與 −3、Mutex 一次成功與 0 的結果應相同。
若有錯誤，保留 make／程式的 terminal 輸出，供後續修正。
