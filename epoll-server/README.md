# 下一階段：Handling Massive I/O

此目錄預留給 Linux non-blocking I/O / epoll Demo，目前尚未實作。

規劃以 `fcntl(O_NONBLOCK)` 和 level-triggered `epoll` 建立單執行緒事件迴圈，
與 blocking socket server 比較大量等待中的連線。
必須處理 `EAGAIN`、partial reads/writes、斷線與 FD 清理；epoll 的 readiness
表示現在可以嘗試 I/O，不保證一次就能讀完完整訊息。
