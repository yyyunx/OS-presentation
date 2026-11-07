#ifndef TICKET_DEMO_REQUEST_SIMULATOR_H
#define TICKET_DEMO_REQUEST_SIMULATOR_H

#include <chrono>
#include <condition_variable>
#include <functional>
#include <iostream>
#include <mutex>
#include <queue>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace resource_demo {
const int WORKER_COUNT = 4;
const std::size_t QUEUE_CAPACITY = 20;
const int WORK_MS = 10;
const int BACKPRESSURE_MS = 1;

struct Server {
    std::mutex mutex;
    std::condition_variable work_available;
    std::condition_variable space_available;
    std::queue<int> pending;
    bool producer_done = false;
    int processed = 0;
    std::size_t max_queue = 0;
};

inline void worker(Server& server) {
    while (true) {
        {
            std::unique_lock<std::mutex> lock(server.mutex);
            // Sleep while idle; predicate handles spurious wakeups.
            server.work_available.wait(lock, [&]() {
                return server.producer_done || !server.pending.empty();
            });
            if (server.pending.empty()) {
                return; // Producer finished AND all queued requests were drained.
            }
            server.pending.pop();
        }
        // Backpressure: notify the producer that one queue slot became free.
        server.space_available.notify_one();
        // Work runs OUTSIDE the queue lock, allowing four requests in progress.
        std::this_thread::sleep_for(std::chrono::milliseconds(WORK_MS));
        {
            std::lock_guard<std::mutex> lock(server.mutex);
            ++server.processed;
        }
    }
}

inline int parse_number(const char* text, int minimum, int maximum) {
    std::size_t consumed = 0;
    const std::string value(text);
    const int number = std::stoi(value, &consumed);
    if (consumed != value.size() || number < minimum || number > maximum) {
        throw std::invalid_argument("out of range");
    }
    return number;
}

inline int run_simulator(bool protected_mode, int argc, char* argv[]) {
    int incoming = 1000;
    int arrival_ms = 0;
    try {
        if (argc > 3) {
            throw std::invalid_argument("too many arguments");
        }
        if (argc >= 2) {
            incoming = parse_number(argv[1], 1, 100000);
        }
        if (argc == 3) {
            arrival_ms = parse_number(argv[2], 0, 1000);
        }
    } catch (const std::exception&) {
        std::cerr << "Usage: " << argv[0]
                  << " [incoming: 1..100000] [arrival_delay_ms: 0..1000]\n";
        return 1;
    }
    std::cout << (protected_mode ? "=== Protected ===\n" : "=== Uncontrolled ===\n")
              << "Incoming requests: " << incoming
              << "\nWorker Threads = " << WORKER_COUNT
              << "\nQueue Capacity = "
              << (protected_mode ? "20" : "unbounded")
              << "\nProcessing time: " << WORK_MS << " ms/request"
              << "\nArrival delay: " << arrival_ms << " ms/request\n";

    Server server;
    std::vector<std::thread> workers;
    try {
        // Fixed Thread Pool: exactly four workers, no thread per request.
        for (int i = 0; i < WORKER_COUNT; ++i) {
            workers.emplace_back(worker, std::ref(server));
        }
    } catch (const std::exception& error) {
        {
            std::lock_guard<std::mutex> lock(server.mutex);
            server.producer_done = true;
        }
        server.work_available.notify_all();
        for (auto& thread : workers) {
            thread.join();
        }
        std::cerr << "Cannot start worker pool: " << error.what() << "\n";
        return 1;
    }

    int accepted = 0;
    int rejected = 0;
    bool explained_backpressure = false;
    for (int id = 1; id <= incoming; ++id) {
        bool admitted;
        std::size_t pending;
        {
            // Critical Section: queue size check and enqueue are one operation.
            std::unique_lock<std::mutex> lock(server.mutex);
            if (protected_mode && server.pending.size() >= QUEUE_CAPACITY) {
                if (!explained_backpressure) {
                    std::cout << "Queue full: backpressure waits up to "
                              << BACKPRESSURE_MS << " ms\n";
                    explained_backpressure = true;
                }
                // Backpressure actually slows this producer, but only briefly.
                // wait_for releases the mutex so workers can free queue slots.
                server.space_available.wait_for(lock,
                    std::chrono::milliseconds(BACKPRESSURE_MS), [&]() {
                        return server.pending.size() < QUEUE_CAPACITY;
                    });
            }
            admitted = !protected_mode || server.pending.size() < QUEUE_CAPACITY;
            if (admitted) {
                server.pending.push(id);
                ++accepted;
                if (server.pending.size() > server.max_queue) {
                    server.max_queue = server.pending.size();
                }
            } else {
                // Load Shedding: return BUSY instead of retaining more requests.
                ++rejected;
            }
            pending = server.pending.size();
        }
        if (admitted) {
            server.work_available.notify_one();
        }
        // Summarize the burst instead of printing 1000 lines and distorting timing.
        if (protected_mode && (id <= 8 || id % 100 == 0 ||
                               (!admitted && rejected <= 8))) {
            if (!admitted) {
                std::cout << "Queue full\n";
            }
            std::cout << "Request " << id
                      << (admitted ? " accepted\n" : " rejected (BUSY)\n");
        }
        if (id % 100 == 0 || id == incoming) {
            std::cout << "Pending requests: " << pending << "\n";
        }
        if (arrival_ms > 0) {
            std::this_thread::sleep_for(std::chrono::milliseconds(arrival_ms));
        }
    }

    {
        std::lock_guard<std::mutex> lock(server.mutex);
        server.producer_done = true;
    }
    server.work_available.notify_all();
    for (auto& thread : workers) {
        thread.join(); // Finish admitted work before printing statistics.
    }
    std::cout << "\n=== Server Statistics ===\n\n"
              << "Incoming: " << incoming << "\nAccepted: " << accepted
              << "\nProcessed: " << server.processed << "\nRejected: " << rejected
              << "\nMax queue size: " << server.max_queue
              << "\nWorker threads: " << workers.size()
              << "\nPending after drain: " << server.pending.size() << "\n";
    // Invariants matter more than a hardware-dependent exact acceptance count.
    const bool valid = accepted == server.processed &&
                       server.processed + rejected == incoming &&
                       server.pending.empty() &&
                       (!protected_mode || server.max_queue <= QUEUE_CAPACITY);
    return valid ? 0 : 1;
}
} // namespace resource_demo
#endif
