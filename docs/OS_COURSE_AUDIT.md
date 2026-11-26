# 原課程專案審查

本次擴充以原有 Concert Ticket Rush 為課程基線。保留九支 C++ 程式、網路協定、
Dashboard 場景、Terminal proof、既有測試和課程講稿。新增的微基準使用獨立執行檔。

| 範圍 | 實作與正確性 | 閱讀效能結果時的邊界 |
|---|---|---|
| [Concurrency](../concurrency/concurrency_demo.cpp) | 20 位使用者各 `sleep_for(100 ms)`，有序／多執行緒比較；輸出鎖在等待區外。 | 提早完成來自等待重疊。計時涵蓋 thread 啟動、join 和輸出。 |
| [CPU Scheduling](../scheduling/scheduling_demo.cpp) | FCFS、non-preemptive SJF、RR 的明確 arrival、burst、completion 模型。 | 這裡的 CPU time unit 是模擬量。實際 affinity 與 handoff 見新實驗。 |
| [Race Condition](../race-condition/race_demo.cpp) 與 [Mutex](../race-condition/mutex_demo.cpp) | Rendezvous 先讓四個 thread 讀到相同庫存。個別 atomic 操作合法，但拆成 check-then-act 仍超賣。Mutex 保護整段交易。 | 延遲刻意放大競爭，用庫存和成功次數驗證語意。Mutex vs Atomic 微基準使用等價的單計數器更新。 |
| [Blocking I/O](../socket-server/blocking_ticket_server.h) | 每連線一個 worker，在 `recv` 阻塞。按換行解析，處理部分資料、送出和關閉。SIGINT 路徑 shutdown、join、close。 | Thread handle 在 server 結束前留待 join。長時間接入、斷線的資源回收屬於教學版限制。 |
| [epoll](../epoll-server/epoll_server.cpp) | Level-triggered 的 non-blocking event loop。處理 partial read/write、`EAGAIN` 和 half-close。只有待傳資料才訂閱 EPOLLOUT。 | 連線各自保留 FD 及狀態。教學 log 和 loopback workload 會影響 throughput，課程驗證主要觀察 FD／thread footprint。 |
| [Thread Pool 與 Backpressure](../resource-management/request_simulator.h) | 4 workers 在 queue lock 外處理。Protected 版限制 20 筆 pending，短暫等待、屆期拒絕，關閉時排空。 | 忙時 rejection 是 load shedding。精確接收數受排程影響，測試檢查守恆、排空及容量上限。 |
| [Linux 監控與 Dashboard](../demo-ui/controller.py) | Loopback controller 管理子程序及清理，從 `/proc/<pid>/status` 與 `fd/` 取樣。Terminal proof 保存獨立事件及 raw logs。 | Threads／FDs 是取樣快照。Dashboard 原先展示資源證據，新頁另展示 CPU 時間、RSS、切換次數和基準分布。 |
| [原 Benchmark 資料](DASHBOARD_TEST_RESULTS.md) | 課程留下 I/O 等待計時、連線資源比較、queue 統計及實際執行證據。 | 沒有統一的 warm-up、trial 分布、CPU／編譯器 metadata 或 PMU 探測。新增 runner 補上這些量測條件。 |
| [自動化測試](../tests/) 與 [Actions](../.github/workflows/dashboard.yml) | 原流程保留 smoke、dashboard regression、真實 Dashboard 實驗和 Terminal proof 整合測試。 | 新 job 檢查微基準正確性及結果匯出，另上傳共享 runner 的 quick smoke 供診斷。 |
| [README 與成果](../README.md#concert-ticket-rush-dashboard) | 保留課程環境、指令、展示流程、歷史結果和 [presentation](../presentation/README.md) 索引。 | 效能實測的環境及解讀另見 [Performance Lab](PERFORMANCE_LAB.md)。 |
