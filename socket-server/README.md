# Demo 4 — Too Many Connections

在 Ubuntu、專案根目錄執行：

```bash
make
./bin/socket_server
# 另一個 terminal
python3 socket-server/load_clients.py 100
```

預設 localhost:8080，協定 `BUY\n` → `REQUEST RECEIVED\n`。
每條已接受的 connection 有獨立 socket FD；stdout 顯示 active count、FD 與 worker thread。
`socket_server.cpp` 是入口，`blocking_ticket_server.h` 包含 accept / blocking recv / shutdown，
`net_utils.h` 包含 socket / bind / listen、protocol 與 partial-send 處理。
這些實作也提供 Demo 5 的 blocking baseline。

Client 預設保持連線 20 秒；`--idle` 不送 BUY，`--hold 0` 收完回覆立即結束。
Ctrl+C 關閉 server。更多 FD 上限、`/proc` 與現場解釋見 [根 README](../README.md#4-socket--file-descriptor)。
