#include <atomic>
#include <chrono>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

int main() {
    const std::vector<std::string> buyers = {"Alice", "Bob", "Charlie", "David"};
    const int buyer_count = static_cast<int>(buyers.size());
    int tickets = 1;
    int purchases = 0;
    std::mutex ticket_mutex;
    std::atomic<int> ready(0);
    std::atomic<bool> start(false);
    std::vector<std::thread> workers;

    std::cout << "=== The Last Ticket: Mutex ===\n"
              << "Tickets remaining = " << tickets << "\n";

    for (int i = 0; i < buyer_count; ++i) {
        workers.emplace_back([&, i]() {
            ready.fetch_add(1);
            // Release all buyers together so they compete for the same mutex.
            while (!start.load()) {
                std::this_thread::yield();
            }

            // Critical Section
            // Mutual exclusion protects BOTH the check and the update.
            // lock_guard releases the mutex automatically at scope exit (RAII).
            std::lock_guard<std::mutex> lock(ticket_mutex);
            if (tickets > 0) {
                // Match the race demo's delay, now inside the protected region.
                // Keep real production critical sections as short as possible.
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
                --tickets;
                ++purchases;
                std::cout << buyers[i] << " purchased the last ticket\n";
            } else {
                std::cout << buyers[i] << ": SOLD OUT\n";
            }
        });
    }

    while (ready.load() < buyer_count) {
        std::this_thread::yield();
    }
    start.store(true);
    for (auto& worker : workers) {
        worker.join();
    }

    // After join there are no writers, so main can read the ordinary int safely.
    std::cout << "\nSuccessful purchases = " << purchases << "\n"
              << "Tickets remaining = " << tickets << "\n"
              << "The winner depends on scheduling; std::mutex does not promise FIFO.\n";
    return (purchases == 1 && tickets == 0) ? 0 : 1;
}
