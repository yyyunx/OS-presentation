#ifndef TICKET_DEMO_BLOCKING_SERVER_H
#define TICKET_DEMO_BLOCKING_SERVER_H

#include "net_utils.h"
#include <exception>
#include <functional>
#include <mutex>
#include <poll.h>
#include <set>
#include <thread>
#include <vector>

namespace ticket_demo {
struct BlockingState {
    std::mutex mutex;
    std::set<int> connections;
};

inline void serve_client(int fd, int client_id, BlockingState& state) {
    {
        std::lock_guard<std::mutex> lock(state.mutex);
        std::cout << "Client " << client_id << " -> Thread "
                  << std::this_thread::get_id() << " (FD " << fd << ")\n";
    }
    std::string input;
    char buffer[1024];
    bool connected = true;
    while (connected) {
        // recv(): BLOCK this worker until data, EOF, or an error arrives.
        // An idle connection still has its own worker thread and socket FD.
        const ssize_t received = recv(fd, buffer, sizeof(buffer), 0);
        if (received == -1 && errno == EINTR) {
            continue;
        }
        if (received <= 0) {
            break; // recv() == 0 means the peer closed its sending side.
        }
        input.append(buffer, static_cast<std::size_t>(received));
        std::size_t newline;
        while ((newline = input.find('\n')) != std::string::npos) {
            if (newline > MAX_LINE) {
                send_all(fd, "ERROR: LINE TOO LONG\n");
                connected = false;
                break;
            }
            const std::string reply = reply_for(input.substr(0, newline));
            input.erase(0, newline + 1);
            if (!send_all(fd, reply)) {
                connected = false;
                break;
            }
        }
        if (connected && input.size() > MAX_LINE) {
            send_all(fd, "ERROR: LINE TOO LONG\n");
            connected = false;
        }
    }

    std::lock_guard<std::mutex> lock(state.mutex);
    state.connections.erase(fd);
    // close(): release the accepted socket FD; the OS may reuse its number.
    close(fd);
    std::cout << "Client disconnected, FD = " << fd
              << "\nActive connections: " << state.connections.size() << "\n";
}

inline int run_blocking_server(int argc, char* argv[], int default_port,
                               const char* title) {
    const int port = parse_port(argc, argv, default_port);
    if (port == -1 || !install_stop_handlers()) {
        return 1;
    }
    const int listener = create_listener(port, false);
    if (listener == -1) {
        return 1;
    }
    std::cout << std::unitbuf << title << " listening on port " << port
              << "\nPID = " << getpid() << ", listening FD = " << listener
              << "\nProtocol: BUY followed by newline; Ctrl+C to stop.\n";

    BlockingState state;
    std::vector<std::thread> workers;
    int client_id = 0;
    int status = 0;
    while (!stop_requested.load(std::memory_order_relaxed)) {
        // poll(): only lets the accept loop periodically check the stop flag.
        // Client I/O remains blocking and thread-per-client, not event-driven.
        pollfd pending = {listener, POLLIN, 0};
        const int ready = poll(&pending, 1, 250);
        if (ready == -1 && errno == EINTR) {
            continue;
        }
        if (ready == -1 || (ready > 0 && !(pending.revents & POLLIN))) {
            std::perror("poll listener");
            status = 1;
            break;
        }
        if (ready == 0) {
            continue;
        }
        // accept(): obtain a NEW connected socket FD; listener stays open.
        const int fd = accept(listener, NULL, NULL);
        if (fd == -1) {
            if (errno == EINTR || errno == ECONNABORTED) {
                continue;
            }
            std::perror("accept (check ulimit -n / available resources)");
            status = 1;
            break; // Avoid spinning forever on EMFILE/ENFILE.
        }
        {
            std::lock_guard<std::mutex> lock(state.mutex);
            state.connections.insert(fd);
            std::cout << "Client connected\nFD = " << fd
                      << "\nActive connections: " << state.connections.size() << "\n";
        }
        try {
            workers.emplace_back(serve_client, fd, ++client_id, std::ref(state));
        } catch (const std::exception& error) {
            std::cerr << "Cannot create worker: " << error.what() << "\n";
            std::lock_guard<std::mutex> lock(state.mutex);
            state.connections.erase(fd);
            close(fd);
            status = 1;
            break;
        }
    }

    close(listener);
    {
        std::lock_guard<std::mutex> lock(state.mutex);
        for (const int fd : state.connections) {
            // shutdown(): wake workers blocked in recv()/send() before join.
            // The worker owns close(); keeping the registry locked avoids FD reuse races.
            shutdown(fd, SHUT_RDWR);
        }
    }
    for (auto& worker : workers) {
        worker.join();
    }
    // Teaching baseline: finished joinable threads are retained until shutdown.
    // A production thread-per-client server would also reap finished workers.
    std::cout << "Server stopped. Active connections: 0\n";
    return status;
}
} // namespace ticket_demo
#endif
