#include <atomic>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <vector>

int main() {
    const std::vector<std::string> buyers = {"Alice", "Bob", "Charlie", "David"};
    const int buyer_count = static_cast<int>(buyers.size());

    // Atomic reads/decrements avoid undefined behavior in C++.
    // BUT a separate check followed by a decrement is still a logical race!
    std::atomic<int> tickets(1);
    std::atomic<int> checked(0);
    std::vector<int> observed(buyer_count, 0);
    std::vector<int> purchase_order(buyer_count, -1);
    std::atomic<int> purchases(0);
    std::vector<std::thread> workers;

    std::cout << "=== The Last Ticket: Race Condition (no mutex) ===\n"
              << "Tickets remaining = " << tickets.load() << "\n";

    for (int i = 0; i < buyer_count; ++i) {
        workers.emplace_back([&, i]() {
            // Broken Critical Section: check and update are NOT protected
            // together. Several buyers may all pass the same inventory check.
            observed[i] = tickets.load();
            checked.fetch_add(1);

            // Teaching-only rendezvous: force every buyer to check BEFORE
            // anyone decrements. This makes overselling reproducible.
            // yield lets other ready threads run; this is not a production gate.
            while (checked.load() < buyer_count) {
                std::this_thread::yield();
            }
            // A short delay illustrates the gap between checking and updating.
            std::this_thread::sleep_for(std::chrono::milliseconds(10));

            if (observed[i] > 0) {
                tickets.fetch_sub(1);
                const int slot = purchases.fetch_add(1);
                purchase_order[slot] = i;
            }
        });
    }

    for (auto& worker : workers) {
        worker.join();
    }

    // Print the collected trace AFTER join so output never interleaves.
    // All checks preceded all purchases because of the rendezvous above.
    // Each vector slot has one writer; join makes completed writes visible.
    for (int i = 0; i < buyer_count; ++i) {
        std::cout << buyers[i] << " sees ticket = " << observed[i] << "\n";
    }
    for (int slot = 0; slot < purchases.load(); ++slot) {
        std::cout << buyers[purchase_order[slot]] << " purchased ticket\n";
    }

    std::cout << "\nSuccessful purchases = " << purchases.load() << "\n"
              << "Tickets remaining = " << tickets.load() << "\n"
              << "OVERSELLING: checking and decrementing must be one operation.\n";

    // A repeatable demo should always produce 4 purchases and -3 tickets.
    return (purchases.load() == buyer_count &&
            tickets.load() == 1 - buyer_count) ? 0 : 1;
}
