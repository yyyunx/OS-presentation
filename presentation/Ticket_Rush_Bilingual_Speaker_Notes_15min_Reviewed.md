# 搶票作業系統專案中英對照講稿

這份講稿對應 Canva 的 15 頁英文投影片。正式報告只念英文段落；中文是逐段理解與練習用，操作提示不必念出來。建議保留短 Demo，以實際輸出呈現程式的行為。目標在 14 分鐘完成內容，再保留 1 分鐘作切換緩衝或簡短問答。時長是排練目標，並非已實際量測的個人朗讀時間。

**時間安排：內容 10 分 40 秒 + 第 14 頁 Demo 3 分 20 秒 = 14 分鐘；另留 1 分鐘緩衝。**

| 投影片 | 主題 | 時長 | 報告時間軸 |
|---|---|---:|---|
| 第 1 頁 | From Click to Checkout An Operating System Perspective on Online Ticketing | 25 秒 | 00:00–00:25 |
| 第 2 頁 | Six Demos, One Ticketing Journey | 20 秒 | 00:25–00:45 |
| 第 3 頁 | The OS Behind a Ticket Request | 35 秒 | 00:45–01:20 |
| 第 4 頁 | Project Architecture: Terminal-Based Demos | 30 秒 | 01:20–01:50 |
| 第 5 頁 | Concurrency: Overlapping Waits | 60 秒 | 01:50–02:50 |
| 第 6 頁 | CPU Scheduling: Different Waiting Times | 70 秒 | 02:50–04:00 |
| 第 7 頁 | Race Condition: Four Buyers, One Ticket | 55 秒 | 04:00–04:55 |
| 第 8 頁 | Mutex: One Critical Section | 50 秒 | 04:55–05:45 |
| 第 9 頁 | Sockets and FDs: Connections Use Resources | 40 秒 | 05:45–06:25 |
| 第 10 頁 | Blocking vs. epoll | 55 秒 | 06:25–07:20 |
| 第 11 頁 | epoll: Handle Ready Connections | 55 秒 | 07:20–08:15 |
| 第 12 頁 | Resource Management: Bounded Workloads | 50 秒 | 08:15–09:05 |
| 第 13 頁 | Ubuntu Results: Queue Size Capped at 20 | 50 秒 | 09:05–09:55 |
| 第 14 頁 | Live Demo: Commands and Observations | 200 秒 | 09:55–13:15 |
| 第 15 頁 | Six OS Concepts Behind the Ticket Rush | 45 秒 | 13:15–14:00 |
| 保留 | 緩衝或簡短問答 | 60 秒 | 14:00–15:00 |

英文建議練習速度約每分鐘 100–115 字，預留指圖與停頓；以你實際計時排練為準。若老師把 15 分鐘全部計入問答，優先在 14:00 結束，不加 500 clients 或 FD 上限實驗。

## 第 1 頁 From Click to Checkout An Operating System Perspective on Online Ticketing

**時長 25 秒｜時間軸 00:00–00:25**

### English
Good morning. Our project is From Click to Checkout: An Operating System Perspective on Online Ticketing. We use concert ticket requests to demonstrate concurrency, synchronization, and resource management through small C++ programs.

### 中文對照
大家早安。我們的題目是 From Click to Checkout: An Operating System Perspective on Online Ticketing。我們透過小型 C++ 程式，以演唱會購票請求展示併發、同步與資源管理。

**操作提示：** 指向標題與右側 OS 圖案即可，不必介紹配色。

## 第 2 頁 Six Demos, One Ticketing Journey

**時長 20 秒｜時間軸 00:25–00:45**

### English
Our six demos cover concurrency, CPU scheduling, race conditions, mutexes, sockets, epoll, and resource management. I will explain the main ideas first, then show a short live comparison of the program behaviors.

### 中文對照
專案共有六個實驗。先介紹併發與 CPU 排程，再說明競爭條件與 Mutex，接著進入 Socket、epoll 與資源管理。我會先解釋主要概念，最後安排一段簡短的現場展示。

**操作提示：** 快速帶過六個主題，不逐一解釋術語。

## 第 3 頁 The OS Behind a Ticket Request

**時長 35 秒｜時間軸 00:45–01:20**

### English
This diagram follows a ticket request. First, the client connects to the server. The request then waits for processing, checks the available inventory, and receives a reply. Each step involves operating system mechanisms, such as file descriptors, thread scheduling, synchronization, and I/O. When many requests overlap, they compete for shared resources. Our separate demos isolate these mechanisms so that we can observe them clearly.

### 中文對照
這張圖呈現一筆購票請求的概念流程。Client 先連到 Server，等待處理、檢查剩餘庫存，最後收到回覆。各階段涉及檔案描述元、執行緒排程、同步與 I/O。大量請求重疊時，就會競爭共享資源。我們把這些機制拆成獨立實驗，方便觀察各自的影響。

**操作提示：** 沿著四個方塊從左往右指。這是概念串接，不要說成專案已有完整購票流程。

## 第 4 頁 Project Architecture: Terminal-Based Demos

**時長 30 秒｜時間軸 01:20–01:50**

### English
Our project runs in VMware Ubuntu with C++11 and Linux APIs. Python generates clients and runs tests. Clients appear on the left, blocking and epoll servers in the middle, and separate OS experiments on the right. These terminal demonstrations explain individual mechanisms. They do not implement a complete ticketing website or payment processing.

### 中文對照
專案在 VMware Ubuntu 執行，使用 C++11 與 Linux API。Python 用來產生 Client 連線與執行測試。左側是發送請求或保持閒置的 Clients；中間是採用不同連線處理方式的 Blocking 與 epoll Servers；右側則是獨立的概念實驗。這是終端機教學專案，尚未實作完整的售票網站或付款流程。

**操作提示：** 指左、中、右三區。說清楚網路 Server 與概念模擬器是分開執行。

## 第 5 頁 Concurrency: Overlapping Waits

**時長 60 秒｜時間軸 01:50–02:50**

### English
Both versions process twenty users, each with a simulated one-hundred-millisecond I/O wait. Sequential execution handles these waits one after another, while the multithreaded version overlaps them. In the reported Ubuntu VM test, sequential execution took two thousand nine point nine seven milliseconds, compared with one hundred eleven point eight five milliseconds for multithreading. That is a seventeen point nine seven times speedup. The improvement comes from overlapping I/O waits, not from making the CPU itself faster. Concurrency means progress during overlapping periods. Parallelism means simultaneous execution on different cores. This waiting-workload result does not predict the same speedup for CPU-intensive work.

### 中文對照
兩個版本都處理二十位使用者，每筆模擬等待一百毫秒的 I/O。循序版本依序等待，多執行緒版本則讓等待時間重疊。使用者回報的 Ubuntu VM 實測中，循序執行為 2009.97 毫秒，多執行緒為 111.85 毫秒，加速比為 17.97 倍。改善來自 I/O 等待時間重疊，並不是 CPU 本身變快。Concurrency 指工作在重疊期間推進；Parallelism 指不同核心上同時執行。這個等待型工作負載的結果，不能推論 CPU 密集工作也有相同加速比。

**操作提示：** 環境為 Ubuntu VM，Linux 7.0.0-38-generic。數據來源為 2026-11-07 使用者回報，不宣稱為助理直接執行；沒有原始重複量測紀錄，因此不要稱為三次中位數。

## 第 6 頁 CPU Scheduling: Different Waiting Times

**時長 70 秒｜時間軸 02:50–04:00**

### English
Next, we compare three scheduling algorithms using the same four requests. First Come, First Served follows arrival order. Because request A is long, the shorter requests must wait behind it. Non-preemptive Shortest Job First chooses the shortest available job only when the CPU becomes free. A still runs first because it is the only request available at time zero. Round Robin gives each request up to two time units before returning unfinished work to the queue. The average waiting times are six point five, five point five, and four point five. Round Robin performs best for this particular input, but that is not a universal result. These are simulated CPU time units, not measurements of the Linux scheduler.

### 中文對照
接著使用相同的四筆請求，比較三種排程演算法。FCFS 依到達順序執行，因此較長的 A 會讓後面的短工作等待。非搶占式 SJF 只在 CPU 空出來時，選擇已到達的最短工作；由於時間零只有 A 到達，所以仍由 A 先執行。Round Robin 則讓每筆工作一次最多使用兩個時間單位，未完成就放回佇列。三者的平均等待時間分別為六點五、五點五與四點五。RR 在這組輸入較好，但不能推論所有情況都最好。這是 CPU 時間單位的模擬，沒有修改或測量 Linux 實際排程器。

**操作提示：** 依序指三條甘特圖及右方平均值。不必逐格念完 A、B、C、D。

## 第 7 頁 Race Condition: Four Buyers, One Ticket

**時長 55 秒｜時間軸 04:00–04:55**

### English
Now suppose only one ticket remains, but four buyers check the inventory before anyone updates it. All four see one available ticket and continue with their purchase. The final result is four purchases and an inventory of negative three. Our demo deliberately coordinates the checks before the updates, so the problem is reproducible. Individual reads and decrements use atomic operations, which avoid a C++ data race. However, the overall check-then-act sequence still has a logical race. Making individual operations atomic does not automatically make the whole purchase transaction atomic.

### 中文對照
現在假設只剩一張票，但四位買家都在任何人更新庫存前完成檢查。四人都看到還有一張，因此繼續購買，最後出現四筆成功購票與負三張庫存。實驗刻意安排所有檢查先發生，讓問題能穩定重現。單次讀取與扣減使用 Atomic，避免 C++ 的資料競爭；但整段「先檢查再執行」仍有邏輯競爭。個別操作是原子的，不代表整個購票交易就自動具有原子性。

**操作提示：** 指四個 Read 1，再指右方 −3。這裡先解釋，現場跑程式統一留在第 14 頁。

## 第 8 頁 Mutex: One Critical Section

**時長 50 秒｜時間軸 04:55–05:45**

### English
To fix this problem, we protect the inventory check and update with the same mutex. Only one thread enters this critical section at a time. The first successful buyer reduces the inventory to zero. Later buyers acquire the lock, see zero, and receive SOLD OUT. The result is one purchase and no negative inventory. In C++, lock guard releases the mutex automatically when its scope ends. The winner can change between runs because a mutex does not guarantee first-come, first-served ordering. Correctness comes from protecting the whole shared operation.

### 中文對照
解法是使用同一個 Mutex，把庫存檢查與更新一起保護起來。一次只有一個執行緒能進入這個臨界區。第一位成功的買家把庫存降為零，之後的買家取得鎖時看到零，就會得到 SOLD OUT。結果是一筆成功購票，也不會出現負庫存。C++ 的 lock_guard 會在離開作用域時自動釋放 Mutex。每次獲勝者可能不同，因為 Mutex 並不保證先到先服務；正確性來自完整保護這個共享操作。

**操作提示：** 指程式碼中的 lock_guard 與 if 區塊，再指右方 1 purchase 和庫存 0。

## 第 9 頁 Sockets and FDs: Connections Use Resources

**時長 40 秒｜時間軸 05:45–06:25**

### English
A server uses a listening socket to receive new connections. When accept succeeds, it returns a new connected socket for that client. The server refers to each socket through a file descriptor, or FD. The kernel also maintains connection state and buffers. These resources are still needed when a client is idle and has not sent BUY. In our blocking implementation, each connected client also gets its own worker thread.

### 中文對照
Server 使用 Listening Socket 等待新連線。accept 成功後，會回傳專屬於該 Client 的 Connected Socket。Server 透過 File Descriptor，也就是 FD，參照這些 Socket；Kernel 也必須維護連線狀態與緩衝區。即使 Client 閒置、尚未送出 BUY，這些資源仍然存在。在我們的 Blocking 實作中，每個已連線的 Client 另外還有一個 Worker Thread。

**操作提示：** 沿著 Clients、Listening socket、Connected socket 指過去，強調 accept 產生新的 Socket。

## 第 10 頁 Blocking vs. epoll

**時長 55 秒｜時間軸 06:25–07:20**

### English
This table compares our two server architectures under the same idle-client workload. The blocking server creates one thread per client. With one hundred connected clients, we expect about one hundred and one threads, including the main thread. The epoll server uses one event loop, so it can handle these idle connections with one thread. Both architectures still need a file descriptor for each connection. A blocked thread does not necessarily consume CPU continuously, but it still has resource and management costs. Our reported automated tests cover thirty-two idle clients. The one-hundred-client case is our planned live comparison, not a previously reported benchmark.

### 中文對照
這張表比較兩種 Server 在相同閒置連線負載下的架構。Blocking Server 為每位 Client 建立一個執行緒，因此一百條連線預期約有一百零一個執行緒，包含 Main Thread。epoll Server 使用單一 Event Loop，因此可以用一個執行緒處理這些閒置連線。不過兩者每條連線仍然都需要 FD。阻塞中的執行緒不代表持續消耗 CPU，但仍有資源與管理成本。已回報的自動測試涵蓋三十二條閒置連線；一百條是預定現場比較，並不是先前已回報的效能測試。

**操作提示：** 指第二列 thread 數與第三列 FD。若你已在報告前完成 100 clients 彩排，最後一句可說「We also rehearsed the one-hundred-client comparison.」

## 第 11 頁 epoll: Handle Ready Connections

**時長 55 秒｜時間軸 07:20–08:15**

### English
The epoll server waits for the operating system to report which connections are ready. It then tries to receive or send data on those sockets. The sockets use non-blocking mode, so an operation can return EAGAIN instead of waiting when it cannot currently proceed. The server preserves each client's state and continues monitoring. Readiness does not guarantee that a complete request has arrived, so partial reads and writes must be handled. Also, epoll wait itself can sleep while waiting for events. We monitor EPOLLOUT only when output is pending, to avoid repeatedly waking up for sockets that are already writable.

### 中文對照
epoll Server 先等待作業系統通知哪些連線已就緒，再對那些 Socket 嘗試接收或傳送資料。Socket 採用 Non-blocking 模式，當操作暫時無法繼續時，可以回傳 EAGAIN，而不在該 Socket 上等待。Server 保存各 Client 的狀態，接著持續監控。Ready 不代表完整請求已到達，所以必須處理部分讀取與寫入。另外，epoll_wait 本身可以在等待事件時睡眠。只有尚有資料要傳送時才監控 EPOLLOUT，避免因 Socket 持續可寫而反覆喚醒。

**操作提示：** 依圖走一圈即可。epoll_wait 可阻塞等待事件，不能說整個程式從不等待。

## 第 12 頁 Resource Management: Bounded Workloads

**時長 50 秒｜時間軸 08:15–09:05**

### English
Efficient connection handling does not remove capacity limits. This simulator receives one thousand requests but has four workers. The protected version limits its pending queue to twenty requests. A full queue triggers a wait with a one-millisecond timeout, providing brief backpressure. The actual waiting duration also depends on scheduling. If the queue remains full, the new request is rejected with BUSY, which is load shedding. The queue counts waiting requests only. Including up to four requests already being processed, the system retains at most twenty-four requests at once.

### 中文對照
有效率地處理連線，仍然無法消除容量限制。這個模擬器收到一千筆請求，但只有四個 Workers。保護版本把待處理佇列限制在二十筆。佇列滿時，會使用一毫秒的等待逾時設定來產生短暫回壓；實際等待長度也受排程影響。若仍然沒有空間，就以 BUSY 拒絕新請求，這是 Load Shedding。佇列只計算等待中的請求，再加上最多四筆執行中工作，系統同時保留的請求最多為二十四筆。

**操作提示：** 指 20、4 與 BUSY。不要把 queue 20 說成總共只接收或處理 20 筆。

## 第 13 頁 Ubuntu Results: Queue Size Capped at 20

**時長 50 秒｜時間軸 09:05–09:55**

### English
These results come from the recorded VMware Ubuntu run on October twenty-ninth. Both versions used four workers and received one thousand requests. The uncontrolled version processed all requests, and its maximum pending queue reached nine hundred and ninety-seven. The protected version processed three hundred and seventy-eight and rejected six hundred and twenty-two, while keeping the maximum queue at twenty. Both queues were empty after draining. Exact acceptance counts can vary with scheduling. The important checks are the queue limit and request accounting: processed plus rejected equals incoming.

### 中文對照
這些數字來自十月二十九日記錄的 VMware Ubuntu 執行結果。兩個版本都使用四個 Workers，並收到一千筆請求。無上限版本處理全部請求，最大待處理佇列達九百九十七。保護版本處理三百七十八筆、拒絕六百二十二筆，最大佇列則維持在二十。兩者排空後的佇列都是零。實際接收數會隨排程改變；檢查重點是佇列上限，以及「已處理加上已拒絕等於總請求數」的守恆關係。

**操作提示：** 先指左側 997 與 20，再指右側 378 + 622 = 1000。不要宣稱這些數字證明吞吐量提升。

## 第 14 頁 Live Demo: Commands and Observations

**時長 200 秒｜時間軸 09:55–13:15**

### English
Now I will demonstrate inventory protection, compare both servers with the same idle-client load, and check the queue statistics. The servers are already running.

### 中文對照
現在展示三組簡短比較。首先觀察 Mutex 如何避免超賣，再用相同數量的閒置連線比較執行緒數，最後檢查佇列上限與請求統計。Servers 已經事先啟動，因此可以直接觀察行為。

**操作提示：** 這段只是 Demo 開場，不是第 14 頁全部講稿。整頁 3 分 20 秒已包含開場、操作、解說與切回 Canva。逐步口條及指令見後面的 Demo 操作頁。

## 第 15 頁 Six OS Concepts Behind the Ticket Rush

**時長 45 秒｜時間軸 13:15–14:00**

### English
To conclude, the ticket rush helps us connect operating system concepts to visible behavior. Concurrency overlaps waiting time, and scheduling affects how long requests wait. A mutex protects shared inventory. Sockets and file descriptors explain why connections consume resources. Epoll reduces the need for a separate waiting thread for every client. Finally, a bounded queue keeps the amount of retained work under control. Together, these demonstrations show that a responsive system also needs correct shared-state handling and clear capacity limits. Thank you for listening.

### 中文對照
最後，搶票情境讓我們把作業系統概念對應到看得見的行為。Concurrency 讓等待時間重疊，Scheduling 影響請求的等待時間，Mutex 保護共享庫存，Socket 與 FD 說明連線為何消耗資源。epoll 減少為每條等待連線配置專屬執行緒的需求；Bounded Queue 則控制同時保留的工作量。這些實驗說明，系統要有良好反應，也需要正確處理共享狀態與明確的容量限制。謝謝大家。

**操作提示：** 用正常語速收尾。若已接近 14 分鐘，只念本頁第一句與最後兩句。第 15 頁留在畫面上接受問題。

## 第 14 頁 Demo 操作表

本頁的 3 分 20 秒包含開場、切換、操作與解說。與 P14 統一為 Race／Mutex、8081 和 8082 各 100 個 idle clients、hold 60 秒，再比較 Threads 與兩種 Queue 統計；本次不做 500 clients。

### Demo 00:00–00:15 切換至 Ubuntu

切到事先排好的 Ubuntu terminals。Servers 已在 A、B 執行，C 為 clients，D 為觀察與其餘 Demo。

**English:** Now I will demonstrate inventory protection, compare both servers with the same idle-client load, and check the queue statistics. The servers are already running.

**中文：** 現在展示三組簡短比較。首先觀察 Mutex 如何避免超賣，再用相同數量的閒置連線比較執行緒數，最後檢查佇列上限與請求統計。Servers 已經事先啟動，因此可以直接觀察行為。

### Demo 00:15–00:55 Race 與 Mutex

在 D 依序執行兩支程式，指輸出的 Successful purchases 與 Tickets remaining。

```bash
./bin/race_demo
./bin/mutex_demo
```

**English:** Without the mutex, all four buyers pass the inventory check. We get four purchases and negative three tickets. With the mutex, only one purchase succeeds, and the inventory ends at zero. The winning buyer may change, but the inventory remains correct.

**中文：** 沒有 Mutex 時，四人都通過庫存檢查，得到四筆購票與負三張票。加入 Mutex 後，只有一筆購票成功，庫存最後為零。成功者可能改變，但庫存仍然正確。

### Demo 00:55–01:10 建立相同負載

在 C 啟動兩組各 100 條 idle connections。& 表示背景執行；程式的 hold 為 60 秒。等兩組都顯示 Connected clients 100 後，立刻在 D 觀察。

```bash
python3 socket-server/load_clients.py 100 --port 8081 --idle --hold 60 &
python3 socket-server/load_clients.py 100 --port 8082 --idle --hold 60 &
```

**English:** I am connecting one hundred idle clients to each server. Both workloads use the same settings, with no BUY requests.

**中文：** 現在對每個 Server 各建立一百個閒置 Clients。兩邊設定相同，Clients 不送出 BUY。

### Demo 01:10–01:45 比較 Threads 與 FD

在 D 先執行 ps，再解說 NLWP，也就是每個 process 的執行緒數。主指令不需要 $ 變數，與 P14 一致。目標在 Demo 01:45 前完成讀取，早於最先一組 clients 約 01:55 到期；不要先講完才執行。原 grep 與 FD 指令另附於文件末端純文字區。

```bash
ps -C blocking_server,epoll_server -o pid,comm,nlwp
```

**English:** The blocking server has about one hundred and one threads, while the epoll server has one. Both still keep a socket file descriptor for each accepted connection. This shows the difference in thread management. It does not prove a specific throughput improvement.

**中文：** Blocking Server 約有一百零一個執行緒，epoll Server 則只有一個。兩者每條已接受的連線仍然都保留 Socket FD。這展示的是執行緒管理方式的差異，不代表已證明特定的吞吐量提升。

### Demo 01:45–02:30 比較 Queue 統計

在 D 各顯示最後 9 行統計。圈出 Max queue size、Worker threads 與 Pending after drain；接受與拒絕數以當次輸出為準。

```bash
./bin/resource_uncontrolled_demo | tail -n 9
./bin/resource_protected_demo | tail -n 9
```

**English:** Both versions use four workers. The protected queue stays at or below twenty. Processed plus rejected equals incoming, and pending work is zero after draining. Today's exact processed and rejected counts may differ from the recorded slide.

**中文：** 兩個版本都使用四個 Workers。保護版本的佇列維持在二十以下或等於二十；已處理加已拒絕等於總請求數，排空後 Pending 為零。今天的實際處理與拒絕數可能和投影片的記錄不同。

### Demo 02:30–03:05 Demo 重點回顧

保留統計畫面，簡短回顧後切回簡報。

**English:** The mutex keeps inventory correct. Epoll reduces the number of threads needed for idle connections. The bounded queue keeps pending work within a defined limit. These are the main behaviors we wanted to demonstrate.

**中文：** Mutex 維持庫存正確，epoll 減少閒置連線所需的執行緒數，Bounded Queue 則把等待中的工作維持在明確上限內。這就是我們要展示的主要行為。

### Demo 03:05–03:20 切回第 15 頁

切回 Canva 第 15 頁並開始結論。Server 可在報告結束後用 Ctrl+C 關閉，不占用這段時間。

## 報告前準備

報告前在 Ubuntu 完成 make 與 make test，並彩排 100 clients。預先開啟四個 Terminal 分頁 A、B、C、D，全部切到專案根目錄。A 跑 Blocking Server，B 跑 epoll Server，C 產生負載，D 做比較與執行其他實驗。A、B 在開始報告前先啟動，保持沒有測試 clients 連線；各自記下程式輸出的 PID。在 D 設定實際 PID，不要使用下面的範例數字。

```bash
cd /mnt/hgfs/presentation/ticket-rush-os-demo
make -j4
make test

# Terminal A
./bin/blocking_server

# Terminal B
./bin/epoll_server

# Terminal D: replace these example PIDs with the actual server PIDs
blocking_pid=12345
epoll_pid=12346
```

在 A、B、C 也各自執行相同 cd 指令；終端機的工作目錄與變數不會跨分頁自動同步。D 的 blocking_pid 與 epoll_pid 要保持在同一個 shell。Clients 結束後執行緒與 FD 會下降，所以要在 hold 的 60 秒內讀取。FD 總數也包含標準輸入輸出、Listening Socket，epoll 另有自己的 FD，不能把 FD 總數直接當 Client 數。

若彩排 100 clients 不穩定，事先改成兩邊各 32 clients，口條改為 thirty-two clients，Blocking 約 33 threads，epoll 仍為 1。現場不要臨時 debug，也不要提高負載到 500。

## 超時與失敗備案

到第 13 頁結束時應為 09:55。若已超過 11:00，第 14 頁只跑 Race／Mutex，再用既有截圖說明 thread 與 queue 比較，爭取在 13:15 回到第 15 頁。任何一步 10 秒內沒有預期畫面，立即改用已準備好的輸出截圖，不在現場修改程式。

**English fallback:** The live environment is not responding as expected, so I will use our recorded results. The key observations are one successful purchase with the mutex, fewer threads with epoll, and a protected queue capped at twenty.

**中文對照：** 現場環境沒有如預期回應，我改用已記錄的結果。主要觀察仍是 Mutex 只讓一筆購票成功、epoll 使用較少執行緒，以及保護版本的佇列上限為二十。

報告前保存 Race／Mutex 輸出、同一負載下的兩種 Threads 統計，以及 Queue 統計截圖。標明當次負載和日期；沒有手動驗證的 100 clients 結果不可假裝是已完成的實測。

## 常見問答備用

### Why do atomic operations not prevent this race?

**English:** Each individual operation is atomic, but the check and update are separate. Another thread can act between them. We protect the entire sequence with the same mutex.

**中文：** 單一操作是原子的，但檢查與更新是兩個分開的步驟；其他執行緒可以在兩步之間動作，因此要用同一把鎖保護完整流程。

### Does epoll remove the file descriptor limit?

**English:** No. Each accepted connection still needs a socket FD. Epoll changes how we wait for readiness, but it does not remove OS resource limits.

**中文：** 不會。每條已接受的連線仍需要 Socket FD；epoll 改變的是等待就緒通知的方式，沒有消除 OS 資源限制。

### Is Round Robin always the best scheduler?

**English:** No. It has the lowest average waiting time for this particular input. Different workloads and context-switch costs can change the result.

**中文：** 不是。它只在本例的輸入中具有最低平均等待時間；工作負載與切換成本改變時，結果也可能不同。

### Why reject requests instead of accepting all of them?

**English:** Accepting everything can accumulate an uncontrolled amount of pending work. Rejecting excess demand keeps admitted work within available capacity.

**中文：** 全部接收可能讓等待工作持續累積；拒絕超出容量的負載，可以讓已接收的工作維持在可處理範圍。

### Is this a complete online ticketing system?

**English:** No. It is a set of terminal demonstrations of OS mechanisms. The socket server acknowledges BUY requests, while inventory protection is demonstrated separately.

**中文：** 不是。這是展示 OS 機制的終端機實驗組合；Socket Server 確認收到 BUY 請求，庫存保護則由獨立實驗示範。

## 口說提示

epoll 可念 ee-poll；mutex 可念 myoo-teks；FD 念 F D；CPU 念 C P U；FIFO 念 first in, first out。EAGAIN 可以直接說 would block；lock_guard 可以念 lock guard。

資料依據：目前的 15 頁 Canva 英文簡報、ticket-rush-os-demo/README.md、TEST_RESULTS.md 與對應 C++ 原始碼。P5 使用 2026-11-07 使用者回報的 Ubuntu VM 計時，P13 為 2026-10-29 Ubuntu Queue 統計，現場數字以當次輸出為準。

## 原始 ASCII 指令備用

下列是程式碼，請從程式碼區塊複製，不要貼進公式編輯器。blocking_pid 與 epoll_pid 必須先設為實際 Server PID。也可直接使用同資料夾的 Demo_Commands_Ubuntu.txt。

```bash
grep -H Threads "/proc/$blocking_pid/status" "/proc/$epoll_pid/status"
ls "/proc/$blocking_pid/fd" | wc -l
ls "/proc/$epoll_pid/fd" | wc -l
```