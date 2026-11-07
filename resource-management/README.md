# Demo 6 — Surviving the Rush

在 Ubuntu、專案根目錄執行：

```bash
./bin/resource_uncontrolled_demo
./bin/resource_protected_demo
```

預設 1000 requests、4 workers、10 ms 處理時間。
兩個入口共用 `request_simulator.h`，讓比較只改變 queue admission policy：

- Uncontrolled：無界 queue，全數接受，觀察 Pending 累積。
- Protected：queue 上限 20，producer 在滿載時等待至多 1 ms（backpressure），
  若仍然滿載就拒絕（load shedding），worker 數固定為 4。

結束時排空已接受的工作，印出統計；Processed + Rejected = Incoming。
Queue 上限不包含正在處理的 4 requests，拒絕數依排程與 timer 而變動。
可用 `./bin/resource_protected_demo 1000 1` 指定每筆到達的間隔為 1 ms。
這是本機 simulator，沒有 TCP listener。完整講解見 [根 README](../README.md#6-resource-management)。
