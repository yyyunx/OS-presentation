# 下一階段：Surviving the Rush

此目錄預留給資源管理 Demo，目前尚未實作。

規劃展示 thread-per-request 與固定大小 thread pool 的差異，搭配 bounded queue、
連線上限、timeout 與 overload rejection。用同一份 Python client 負載測試，
觀察 latency、thread 數、FD 數與記憶體；超過容量時回覆 BUSY 並持續提供服務。
