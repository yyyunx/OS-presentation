# Computer Systems Performance Lab

從資料排列、指令、快取一致性和 OS scheduler 分析執行時間。每個 C++ kernel 都先驗證
運算結果，再輸出單筆量測。Python 負責安排 trial、整理分布、可選擇讀取 Linux perf，
並匯出可重跑的資料。這是 CPU 上的軟體實驗，可用來練習分析 Hardware/Software Co-design
的資料移動與平行化取捨。

## 架構與重現

```text
C++ kernels → checksum / monotonic clock / getrusage / procfs
                  ↓
Python runner → warm-ups / interleaved trials / optional Linux perf
                  ↓
results.json + results.csv → loopback Dashboard / Python plot

Concert Ticket Rush → 原課程 C++ demos、Dashboard、Terminal proof
```

環境使用 Linux、GCC g++（C++17）、GNU Make、Python 3.10+。SSE2 實驗需要支援該 ISA 的建置。
其他需要拓撲及 cache line 的實驗會明確回報 `unavailable`。建議先測試，再在空閒機器量測。

```bash
make lab
make test-lab
python3 performance-lab/bench.py --environment-label vm --perf
```

- `--profile quick --warmups 1 --trials 3` 適合確認流程。預設 `standard` 用 2 次 warm-up、9 次 trial。
- 每節的實驗 ID 可傳給 `--experiment`，也可重複指定。例：`python3 performance-lab/bench.py --experiment cache-locality --perf`。
- `--seed 2026` 為預設。相同輸入在同一種標準函式庫實作下可重現排列；硬體及排程會影響時間。
- 預設輸出至 `.runtime/performance-lab/runs/<run-id>/`，同時更新 Dashboard 的本機快照。
  `--output <新目錄>` 將資料封存到指定位置。JSON 含原始 trial、摘要、perf、設定與環境，
  CSV 提供每個有效 trial 一列，無法執行的版本也會輸出狀態。
- `make demo-ui` 開啟原 Dashboard 後，點選 **Computer Systems Performance Lab · Benchmark results**。
  效能頁可切換實驗，顯示中位數、P95、標準差、CPU 使用率、Peak RSS、切換數與 perf 狀態。
  本機快照優先使用，首次開啟可直接查看 repository 隨附的 VM 實測。
- 產出圖片可使用 Matplotlib。安裝後執行
  `python3 performance-lab/plot.py docs/benchmarks/vmware-ubuntu/results.json comparison.png`。

## 量測契約

- 每個版本每次啟動一個子程序。Warm-up 執行同樣的負載，以暖機並暴露執行錯誤，但排除於統計。
  每一輪依 seed 洗牌版本順序，減少固定排序與系統溫度的偏差。Warm-up 與 trial 之間各自建立並預觸資料，
  不保證逐次 CPU cache 的初始熱度相同。標準 memory-bandwidth large 需要約 256 MiB 陣列空間。
- `steady_clock` 量 kernel wall time。資料配置、初始化與輸出在外。多執行緒先準備並設定 affinity，
  計時含喚醒與 join。CPU 用 `getrusage(RUSAGE_SELF)` 的 user + system 時間差，
  100% 約等於一個 logical CPU 滿載。短試驗可能受 OS 記帳粒度和快照邊界影響。
  Context switch 的 voluntary／involuntary 計數也取兩個快照的差。
- Peak RSS 為子程序的 Linux `/proc/self/status` 中 `VmHWM`，包含 kernel 前的初始化與準備資料。
  比較大陣列時，同時讀取 `working_set_bytes`，避免把暫存陣列或程式映像當成 kernel working set。
  無法用單一陣列或固定結構定義 working set 的實驗，該欄位以 0 表示未估算。
- Latency 用每個 trial 的時間除以操作數。除依賴載入及 handoff 等特殊設計，這通常是批次攤銷值，
  不是單一指令的 intrinsic latency。Throughput 是每秒操作數。含 `logical_bytes` 的實驗另提供 GiB/s。
  百分位數取自各 trial，以線性內插計算。標準差使用樣本定義，只有一筆時標記為 null。
- `--perf` 先逐組探測事件。每個可用事件組對各版本另外量一次完整程序，含準備流程。
  `cycles:u` 與 `instructions:u` 成組量測以計算 IPC。cache misses、branch misses 也用 user mode，
  context switches、CPU migrations 則為 software events。可用值附 counter running percentage。
  權限不足、事件缺失、group 無法配對或沒有計數時保留 `unavailable` 原因。
  Hybrid PMU 若回報拆分的事件，本框架保留 unavailable 狀態。需要逐 PMU 結果時可在裸機
  直接透過 `perf stat` 對指定 PMU 收集成組事件。
- Checksum、輸入不變量與實際觀測結果共同約束 dead-code elimination。
  `-fno-lto -fno-loop-interchange` 保留實驗設計，局部禁用 auto-vectorization／if-conversion，
  然後在實際 GCC 建置的反組譯查核。改 flags 時用 `make -B lab LAB_CXXFLAGS='…'` 重建。
  `objdump -C -d -Mintel bin/systems_lab` 可在 x86-64 檢查核心迴圈。
- 記錄 CPU 型號、OS、kernel、CPU mask／topology、虛擬化、compiler flags、binary SHA-256、seed、
  每個 trial 的 thread 數及 affinity。Virtual machine 與 GitHub Actions 的排程及 PMU 行為由環境限制。
  確認實體核心、SMT、頻率、NUMA 與環境負載後，再用同一套程式量裸機以延伸結論。

## 實測與資料

結果、環境和圖表見 [VMware Ubuntu 實測紀錄](benchmarks/vmware-ubuntu/README.md)。
以下十節的分析對應該次 standard run。重現指令假設已執行 `make lab`。

### 1. Cache Locality

- **目的與理論**：觀察 spatial locality、cache line fill、hardware prefetch 與 memory-level parallelism。
  順序的下一筆常落在同一條 cache line，隨機位址較少有這項優勢。
- **實驗設計**：`memory.cpp` 的 `cache_locality` 在相同 64 MiB 的 index array 上走訪一個完整環，
  兩種版本每一步都是 `index = next[index]`。Random 用 seeded permutation 串成環，
  以相同 visit count、index sum 與起點回環檢查。基準排除準備排列和串接時間。
- **預期與解讀**：相依鏈限制同時未完成的 loads，預期 random 有較多長延遲取數。
  VM 的 random 較慢，結果混合 cache、prefetch、TLB 與分頁配置的效果。
- **限制**：`random` 準備的 permutation 會增加 Peak RSS，計時核心仍讀取相同長度的陣列。
  此結論適用於相依存取，同時有多條獨立地址鏈時 MLP 會改變結果。
- **重現**：`python3 performance-lab/bench.py --experiment cache-locality --perf`
- **面試**：為什麼使用 dependent load？下一個位址由上一筆 load 產生，
  讓 out-of-order core 難以重疊多筆 misses，放大等待取數時間。

### 2. Matrix Traversal

- **目的與理論**：看相同 row-major layout 如何因 loop order 產生不同 stride。
  一個 64 B line 可容納 16 個 `uint32_t`，stride-1 可連續用到這些元素。
- **實驗設計**：`matrix_sum` 讀取相同的 2048 × 2048 row-major matrix，
  Row / Column 採用 4／8192 B 的 inner stride，兩者都維持 scalar sum、同 count 和 checksum。
- **預期與解讀**：預期 row traversal 通常較有 spatial locality。VM 的 column 成本較高，
  此 stride 同時可能壓到少數 cache sets，增加 TLB 與 cache conflict 壓力。
- **限制**：結果依矩陣尺寸、leading dimension、page size 與 blocking 而變。
  若改成 2049 或採 tiling，會改變訪問 pattern。
- **重現**：`python3 performance-lab/bench.py --experiment matrix-traversal --perf`
- **面試**：矩陣乘法如何利用這個現象？調整 loop order 或 cache tiling 能讓需要重用的資料
  保留在 cache，也應驗證相關矩陣的 layout 和維度。

### 3. False Sharing

- **目的與理論**：觀察 cache-coherence protocol 以整條 line 追蹤 ownership，
  同一 line 中的獨立寫入可能反覆失效。
- **實驗設計**：`false_sharing` 讓兩個 workers 各做 2M 次 relaxed、lock-free 64-bit RMW，
  綁到兩個 OS 所辨識的不同核心。Packed 把兩個 counter 放在同一條 64 B line，
  Padded 把兩者分開。逐一檢查每個 counter。
- **預期與解讀**：預期 packed 可能承擔較多 coherence 交通。VM 觀察到 padded 的每次更新成本較低。
  在這個量測中，兩者的 CPU 使用率都接近雙執行緒滿載，說明 CPU 有在工作時仍可能出現吞吐量差距。
- **限制**：要求 sysconf 回報 64 B L1 data cache line。Guest 拓撲不代表固定 host core。
  Atomic RMW 會增加 ownership 壓力，分離 cache line 也會擴大結構 footprint。
- **重現**：`python3 performance-lab/bench.py --experiment false-sharing --perf`
- **面試**：如何分辨 true sharing？兩執行緒寫同一個 counter 是 true sharing，
  這裡各自寫自己的 counter，硬體卻仍需協調同一個 line。

### 4. Mutex vs Atomic

- **目的與理論**：比較同一個 shared counter 的 mutual exclusion 與 atomic read-modify-write。
  Mutex 有 acquisition／release、競爭時可能睡眠喚醒；atomic RMW 仍須取得 cache line ownership。
- **實驗設計**：`mutex_atomic` 中兩個 workers 各做 1M 次更新，沿用同一個 CPU mask。
  Mutex 保護 ordinary increment，Atomic 用 `fetch_add(relaxed)`，最後都驗證總數。
- **預期與解讀**：VM 上 atomic 的中位數較低，仍有 true sharing。該結果反映單一 counter
  在這個並行度及負載的成本。Mutex 等待方式、競爭程度或 critical section 大小改變時需重新量測。
- **限制**：Relaxed 只提供 atomicity 和該物件的 modification order。若有跨欄位不變量、
  發布資料或公平性需求，演算法還要定義完整的同步語意。
- **重現**：`python3 performance-lab/bench.py --experiment mutex-atomic --perf`
- **面試**：為何原售票案仍需要保護 check-then-act？兩次各自原子的存取不構成一次交易。
  可用 mutex 保護整段，或者用 compare-exchange 實作可重試的狀態轉換。

### 5. CPU Affinity 與 Thread Scheduling

- **目的與理論**：比較可排程的 CPU 範圍與可用平行度。Thread migration 可能改變 cache locality，
  鎖太窄的 affinity mask 也會讓 runnable threads 等待。
- **實驗設計**：`affinity` 讓兩個 workers 各算 24M 步獨立的整數相依 recurrence，
  另用 affine map 快速冪驗算。比較 inherited mask、兩個 workers 同 CPU、各固定到不同核心。
- **預期與解讀**：VM 的 spread 與 unpinned 都比 same-cpu 高吞吐。把兩份 CPU-bound 工作放上
  同一顆 vCPU 時約共用一個 logical CPU 的時間，spread 才有並行進展的機會。
- **限制**：在 guest，OS core ID 只表示 guest 看見的 CPU。P/E cores、SMT、NUMA 和背景負載
  都可能翻轉 unpinned／spread 的排序。此 VM 的 perf migrations 計數不可用。
- **重現**：`python3 performance-lab/bench.py --experiment cpu-affinity --perf`
- **面試**：Affinity 如何與 scheduler 互動？Mask 限制執行位置，scheduler 仍決定何時執行。
  與 I/O、鎖競爭、SMT 配置一起分析才知道 pinning 能否改善 throughput。

### 6. Memory Alignment

- **目的與理論**：觀察 vector load 起始位址對 cache-line crossing 的影響。
  x86 SSE2 的 unaligned load 可讀任意位址，在 64 B line／16 B load 條件下，
  +4 B 的連續向量位址使約四分之一的 loads 跨 line。
- **實驗設計**：`sum_linear` 把同樣的資料放在 64-byte aligned 位址或 +4 B，兩版都呼叫
  `vector_sum` 使用 `_mm_loadu_si128`。每個 scalar element 的自然對齊保留，checksum 相同。
- **預期與解讀**：跨 line 有時增加 load ports 或 cache line 存取壓力。
  VM 的中位數差距小，應同時看 P05–P95。這組資料只用一種 offset 與 input size。
- **限制**：同一個 load opcode，差異來自位址。不同 ISA、vector 寬度、跨 page、cache 層級、
  data layout 會改變成本。地址對齊 64 B，實際 line size 另寫在 trial metadata。
- **重現**：`python3 performance-lab/bench.py --experiment memory-alignment --perf`
- **面試**：為何 offset 是 4 而非 1？`uint32_t` 物件仍保持自然對齊，
  只變更 SIMD 寬度和 cache line 所見的相對位址。

### 7. SIMD Vectorization

- **目的與理論**：比較 scalar 與 single instruction, multiple data 的資料路徑，
  一條 packed 128-bit add 可更新四個 32-bit lanes。
- **實驗設計**：`scalar_sum` 局部停用 auto-vectorization，`vector_sum` 使用 SSE2 intrinsics。
  最後 horizontal reduction 與尾端元素納入 modulo 2³² checksum。
  Standard 每批 262147 個元素、重複 128 次，兩個版本都從同樣尺寸及對齊的資料開始。
- **預期與解讀**：VM 見 SSE2 中位數較低。單一批次仍須取數、做 reduction 和 scalar tail，
  可用 memory subsystem 與執行端口解釋達不到理想 lane 數比例的情況。
- **限制**：結果衡量特定 kernel，在 bandwidth-bound、短輸入或編譯器可自動向量化的程式，
  皆應重新量測。測試會驗證 tail 與 overflow 等價語意。
- **重現**：`python3 performance-lab/bench.py --experiment simd --perf`
- **面試**：如何確認 scalar baseline 確實是 scalar？查編譯器選項，再反組譯熱迴圈，
  確認 scalar add 與 SSE2 的 `paddd` 各自存在。

### 8. Memory Bandwidth

- **目的與理論**：比較 cache-resident copy 與超過 last-level cache 的 copy。
  Streaming workloads 的時間常受資料路徑、cache/write policy 及記憶體子系統限制。
- **實驗設計**：`memory_bandwidth` 使用 libc `memcpy`；Small 兩個 16 KiB 陣列，
  Large 兩個 128 MiB 陣列。各複製 512 MiB payload，計 logical bytes 為 read + write。
  Compiler barrier 保留每次 copy，結束後逐 byte 比較和核對 checksum。
- **預期與解讀**：VM 中 small 的 logical GiB/s 較高，符合快取尺寸差異的預期。
  Large 的 working set 超過 guest 報告的 24 MiB LLC；其數字同時反映 libc copy
  路徑、快取、預取與 guest/host 資源。
- **限制**：Logical bytes 無法對應唯一的 DRAM traffic，比如 write-allocate、
  non-temporal stores 或硬體壓縮會改變 bus 上的資料量。若要與標準 STREAM 比較，須用相同規範。
- **重現**：`python3 performance-lab/bench.py --experiment memory-bandwidth --perf`
- **面試**：如何檢查 kernel 是否受 memory-bound 限制？擴大 working set、
  使用相同的有效 byte 定義，觀察 throughput 與頻寬，並在有權限時補充相關 PMU。

### 9. Branch Prediction

- **目的與理論**：比較可預測與難預測分支。Misprediction 可能丟棄 speculative work，
  pipeline 需重新從正確路徑取指。
- **實驗設計**：`branch_sum` 的 4 MiB 資料一半為 0、一半為 1。Sorted／Shuffled 的資料量
  及 taken 次數相等，執行 10 遍。關閉 if-conversion／auto-vectorization，
  並在反組譯確認條件跳躍。
- **預期與解讀**：VM 中 shuffled 用時較長，方向符合 predictor 理論。
  原因分析仍不能拆出實際 branch misses，因為該 VM 的事件計數不可用。
- **限制**：Sorted 連續的結果重複、shuffled 較不規律，但微架構、模式的長度、
  predictor 訓練及資料大小都會影響結果。多批次平均不是單次 misprediction penalty。
- **重現**：`python3 performance-lab/bench.py --experiment branch-prediction --perf`
- **面試**：可否把分支改成 branchless expression？視語意和 workload 而定，
  好處是避開錯誤預測，代價可能是額外指令或額外相依。

### 10. Context Switch

- **目的與理論**：透過 thread 交接觀察 OS wakeup、scheduler、鎖及跨核心傳遞。
  Block 等待時可發生 voluntary switch，被 scheduler 中斷也會產生 involuntary switch。
- **實驗設計**：`context_switch` 讓兩個 threads 用 mutex＋condition variable 嚴格交替。
  每個 worker 30000 次，記錄每個 handoff 的平均 wall time、process context switch 計數差。
  比較固定在同一個 vCPU 及指定到兩個 OS 所辨識的核心。
- **預期與解讀**：兩種 placement 都會睡眠／喚醒。VM 的 same-cpu 出現較多非自願切換，
  spread 路徑另承擔跨 vCPU 喚醒；兩者的 timing 順序是該 VM 的觀測。
- **限制**：Handoff 涵蓋 CV、futex 實作、排程延遲與同步成本。每個 handoff 可對應不同數量
  的 context switches，數值不能當作 bare-metal switch 指令或 kernel 路徑的精確延遲。
- **重現**：`python3 performance-lab/bench.py --experiment context-switch --perf`
- **面試**：為何用兩個 counter 檢查？自願／非自願切換分開能看出 blocking 與排程行為，
  也能看出相同 handoff count 在兩種 placement 的切換負擔可能不同。

## 參考資料

- Cache、data alignment、SIMD 和 branch prediction。[Intel Optimization Reference Manual](https://www.intel.com/content/www/us/en/developer/articles/technical/intel64-and-ia32-architectures-optimization.html)
- GCC 優化與向量化選項。[GCC Optimize Options](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html)
- Linux affinity 及程序用量。[pthread_setaffinity_np(3)](https://man7.org/linux/man-pages/man3/pthread_setaffinity_np.3.html) · [getrusage(2)](https://man7.org/linux/man-pages/man2/getrusage.2.html)
- Linux perf CSV、PMU 安全及權限。[perf stat upstream](https://github.com/torvalds/linux/blob/master/tools/perf/Documentation/perf-stat.txt) · [Linux Kernel Perf Security](https://www.kernel.org/doc/html/latest/admin-guide/perf-security.html)
- Streaming memory benchmark 工作集與規格。[STREAM reference](https://www.cs.virginia.edu/stream/ref.html)
