# 下一階段：Too Many Connections

此目錄預留給 Linux TCP socket Demo，目前尚未實作。

規劃使用 C++11 的 `socket / bind / listen / accept / close`，以及 Python 大量 clients。
顯示每條連線的 file descriptor，搭配 `ulimit -n` 與 `/proc/<pid>/fd` 觀察限制。
收到 `EMFILE` 時清楚回報並釋放資源；預設只綁定 localhost。
