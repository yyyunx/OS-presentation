#include <chrono>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

#ifdef _WIN32
#include <process.h>
#else
#include <unistd.h>
#endif

const int USER_COUNT = 20;
const int REQUEST_DELAY_MS = 100;
std::mutex output_mutex;

void handle_request(int user_id) {
    {
        // Threads share this process's memory and stdout.
        // This mutex only keeps each log line intact; work happens outside it.
        std::lock_guard<std::mutex> lock(output_mutex);
        std::cout << "User " << user_id << " enters ticket system"
                  << " (thread " << std::this_thread::get_id() << ")\n";
    }

    // Simulate waiting for I/O (e.g. inventory/payment service).
    // sleep_for blocks this thread, allowing the OS to schedule other threads.
    // This is NOT CPU-heavy work: overlapping waits explains the speedup.
    std::this_thread::sleep_for(std::chrono::milliseconds(REQUEST_DELAY_MS));
}

double run_demo(bool multithreaded) {
    // steady_clock measures elapsed time without wall-clock adjustments.
    const auto start = std::chrono::steady_clock::now();

    if (multithreaded) {
        std::vector<std::thread> workers;
        for (int id = 1; id <= USER_COUNT; ++id) {
            // Each request gets a thread inside the SAME process.
            workers.emplace_back(handle_request, id);
        }
        for (auto& worker : workers) {
            // join waits for completion; include it in the elapsed time.
            worker.join();
        }
    } else {
        for (int id = 1; id <= USER_COUNT; ++id) {
            handle_request(id); // Main thread handles one request at a time.
        }
    }

    const auto end = std::chrono::steady_clock::now();
    return std::chrono::duration<double, std::milli>(end - start).count();
}

int main() {
#ifdef _WIN32
    const int process_id = _getpid();
#else
    const int process_id = getpid();
#endif
    // A process owns an address space/resources; its threads share them.
    std::cout << "Ticket Rush: Processes & Concurrency\n"
              << "Process ID: " << process_id << "\n"
              << "Users: " << USER_COUNT << ", simulated I/O wait: "
              << REQUEST_DELAY_MS << " ms/request\n";

    std::cout << "\n=== Sequential ===\n";
    const double sequential_ms = run_demo(false);
    std::cout << std::fixed << std::setprecision(2)
              << "Total execution time: " << sequential_ms << " ms\n";

    std::cout << "\n=== Multithread ===\n";
    const double multithread_ms = run_demo(true);
    std::cout << "Total execution time: " << multithread_ms << " ms\n"
              << "\nSequential vs Multithread speedup: "
              << sequential_ms / multithread_ms << "x\n";

    // Concurrency = overlapping lifetimes; parallelism = simultaneous execution
    // on multiple cores. Concurrency is possible even with one CPU core.
    // Context switching occurs when the OS switches runnable threads.
    // Thread IDs/log order are NOT a direct count/trace of context switches.
    std::cout << "\nOne process, many threads, overlapping I/O waits.\n"
              << "Thread order and timing depend on the OS scheduler.\n";
}
