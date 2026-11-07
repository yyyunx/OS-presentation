# Demo 5 — Handling Massive I/O

在 Ubuntu、專案根目錄執行，兩個版本使用同一份 load generator：

```bash
./bin/blocking_server
# 另一個 terminal
python3 socket-server/load_clients.py 100 --port 8081 --idle --hold 30
# 用 Ctrl+C 結束 server 後換版本
./bin/epoll_server
# 另一個 terminal
python3 socket-server/load_clients.py 100 --port 8082 --idle --hold 30
python3 socket-server/load_clients.py 100 --port 8082 --hold 20
```

Blocking 版本每位 client 一個 worker，epoll 版本只有 main event loop。
使用 server 印出的 PID 查 `/proc/<pid>/status` 的 Threads 與 `/proc/<pid>/fd`。
兩者都需要每位 client 的 FD；epoll 減少等待中的 threads，不會消除 FD 或記憶體限制。

`epoll_server.cpp` 直接展示 fcntl/O_NONBLOCK、epoll_create1、epoll_ctl、epoll_wait。
採 level-triggered，保留 partial input/output、EAGAIN 時等待下一個 ready event，
只有未送完資料才訂閱 EPOLLOUT；peer half-close 會先送完已產生的回覆。
Client 單行上限 1024 bytes，待傳回覆上限 64 KiB。
詳細觀察與報告說詞見 [根 README](../README.md#5-non-blocking-io--epoll)。
