#include "../socket-server/net_utils.h"
#include <cstdint>
#include <map>
#include <sys/epoll.h>

using namespace ticket_demo;

struct Client {
    std::string input;
    std::string output;
    bool read_closed = false;
};

// Bound per-client buffered output, even when a peer stops reading replies.
const std::size_t MAX_OUTPUT = 64 * 1024;

bool read_requests(int fd, Client& client) {
    char buffer[4096];
    // A small per-event budget also prevents one busy FD monopolizing the loop.
    for (int reads = 0; reads < 16; ++reads) {
        // recv() on a non-blocking socket never waits for future data.
        const ssize_t received = recv(fd, buffer, sizeof(buffer), 0);
        if (received == 0) {
            client.read_closed = true;
            break; // Flush buffered replies before closing after peer EOF.
        }
        if (received == -1) {
            if (errno == EINTR) {
                --reads;
                continue;
            }
            // EAGAIN/EWOULDBLOCK means "nothing more ready now", not failure.
            return errno == EAGAIN || errno == EWOULDBLOCK;
        }
        client.input.append(buffer, static_cast<std::size_t>(received));
        std::size_t newline;
        while ((newline = client.input.find('\n')) != std::string::npos) {
            if (newline > MAX_LINE) {
                break;
            }
            client.output += reply_for(client.input.substr(0, newline));
            client.input.erase(0, newline + 1);
            if (client.output.size() > MAX_OUTPUT) {
                return false; // Slow consumer: do not accumulate unlimited data.
            }
        }
        if (client.input.size() > MAX_LINE) {
            client.output += "ERROR: LINE TOO LONG\n";
            client.input.clear();
            client.read_closed = true;
            return client.output.size() <= MAX_OUTPUT;
        }
    }
    return true;
}

bool flush_replies(int fd, Client& client) {
    while (!client.output.empty()) {
        // send() may write only part of the buffer. Keep the unsent suffix.
        const ssize_t sent = send(fd, client.output.data(), client.output.size(),
                                  MSG_NOSIGNAL);
        if (sent > 0) {
            client.output.erase(0, static_cast<std::size_t>(sent));
        } else if (sent == -1 && errno == EINTR) {
            continue;
        } else if (sent == -1 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            return true; // Subscribe to EPOLLOUT and try again when writable.
        } else {
            return false;
        }
    }
    return true;
}

int main(int argc, char* argv[]) {
    const int port = parse_port(argc, argv, 8082);
    if (port == -1 || !install_stop_handlers()) {
        return 1;
    }
    const int listener = create_listener(port, true);
    if (listener == -1) {
        return 1;
    }
    // epoll_create1(): obtain an FD for the kernel's readiness event set.
    const int epoll_fd = epoll_create1(EPOLL_CLOEXEC);
    if (epoll_fd == -1) {
        std::perror("epoll_create1");
        close(listener);
        return 1;
    }
    epoll_event registration = {};
    registration.events = EPOLLIN; // Default is level-triggered, not EPOLLET.
    registration.data.fd = listener;
    // epoll_ctl(ADD): register the listener for incoming connections.
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, listener, &registration) == -1) {
        std::perror("epoll_ctl listener");
        close(epoll_fd);
        close(listener);
        return 1;
    }

    std::cout << std::unitbuf << "epoll server started on port " << port
              << "\nPID = " << getpid() << ", listening FD = " << listener
              << ", epoll FD = " << epoll_fd
              << "\nI/O worker threads: 1 (the main event loop)\n";
    std::map<int, Client> clients;
    epoll_event events[64];
    int status = 0;
    while (!stop_requested.load(std::memory_order_relaxed)) {
        // epoll_wait(): sleep until registered FDs are ready, or timeout for stop.
        const int count = epoll_wait(epoll_fd, events, 64, 250);
        if (count == -1 && errno == EINTR) {
            continue;
        }
        if (count == -1) {
            std::perror("epoll_wait");
            status = 1;
            break;
        }
        if (count > 0) {
            std::cout << "Ready events: " << count << "\n";
        }
        for (int i = 0; i < count; ++i) {
            const int fd = events[i].data.fd;
            if (fd == listener) {
                // Drain pending accepts. Level-triggering reports remaining work again.
                for (int accepted = 0; accepted < 64; ++accepted) {
                    // accept(): each connection still needs its OWN socket FD.
                    const int client_fd = accept(listener, NULL, NULL);
                    if (client_fd == -1) {
                        if (errno == EINTR || errno == ECONNABORTED) {
                            continue;
                        }
                        if (errno != EAGAIN && errno != EWOULDBLOCK) {
                            std::perror("accept (check ulimit -n)");
                            status = 1;
                            stop_requested.store(true, std::memory_order_relaxed);
                        }
                        break;
                    }
                    // Linux accept() does not inherit O_NONBLOCK from the listener.
                    if (!set_nonblocking(client_fd)) {
                        std::perror("fcntl client");
                        close(client_fd);
                        continue;
                    }
                    registration.events = EPOLLIN | EPOLLRDHUP;
                    registration.data.fd = client_fd;
                    // epoll_ctl(ADD): monitor readable data and peer half-close.
                    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, client_fd, &registration) == -1) {
                        std::perror("epoll_ctl client");
                        close(client_fd);
                        continue;
                    }
                    clients.emplace(client_fd, Client());
                    std::cout << "Client connected, FD = " << client_fd
                              << "\nMonitoring " << clients.size() << " connections\n";
                }
                continue;
            }

            auto found = clients.find(fd);
            if (found == clients.end()) {
                continue;
            }
            std::cout << "Handling FD " << fd << "\n";
            Client& client = found->second;
            const uint32_t flags = events[i].events;
            bool healthy = !(flags & EPOLLERR);
            if (healthy && !client.read_closed &&
                (flags & (EPOLLIN | EPOLLRDHUP | EPOLLHUP))) {
                healthy = read_requests(fd, client);
            }
            if (healthy) {
                healthy = flush_replies(fd, client);
            }
            if (healthy && !(client.read_closed && client.output.empty())) {
                registration.events = client.read_closed ? 0 : EPOLLIN | EPOLLRDHUP;
                if (!client.output.empty()) {
                    // Only watch EPOLLOUT when needed; otherwise writable sockets spin.
                    registration.events |= EPOLLOUT;
                }
                registration.data.fd = fd;
                // epoll_ctl(MOD): adjust readiness interests for buffered output.
                healthy = epoll_ctl(epoll_fd, EPOLL_CTL_MOD, fd, &registration) != -1;
            } else {
                healthy = false;
            }
            if (!healthy) {
                // epoll_ctl(DEL)/close(): remove monitoring and release the socket FD.
                epoll_ctl(epoll_fd, EPOLL_CTL_DEL, fd, NULL);
                close(fd);
                clients.erase(found);
                std::cout << "Client disconnected, FD = " << fd
                          << "\nMonitoring " << clients.size() << " connections\n";
            }
        }
    }
    for (const auto& client : clients) {
        close(client.first);
    }
    close(listener);
    close(epoll_fd);
    std::cout << "Server stopped. Monitoring 0 connections\n";
    return status;
}
