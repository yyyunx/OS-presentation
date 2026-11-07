#ifndef TICKET_DEMO_NET_UTILS_H
#define TICKET_DEMO_NET_UTILS_H

// Small Linux helpers shared by the blocking and epoll examples.
#include <arpa/inet.h>
#include <atomic>
#include <cerrno>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <fcntl.h>
#include <iostream>
#include <string>
#include <sys/socket.h>
#include <unistd.h>

namespace ticket_demo {
static std::atomic<bool> stop_requested(false);
const std::size_t MAX_LINE = 1024;

inline void request_stop(int) {
    // A signal handler only sets a flag: no iostreams or mutex operations here.
    // Lock-free atomic access is safe even if the signal reaches a worker thread.
    stop_requested.store(true, std::memory_order_relaxed);
}

inline bool install_stop_handlers() {
    // Confirm the atomic store cannot acquire an internal lock in a handler.
    if (!stop_requested.is_lock_free()) {
        std::cerr << "This demo requires a lock-free atomic stop flag.\n";
        return false;
    }
    struct sigaction action = {};
    action.sa_handler = request_stop;
    // sigemptyset()/sigaction(): stop gracefully on Ctrl+C or SIGTERM.
    sigemptyset(&action.sa_mask);
    if (sigaction(SIGINT, &action, NULL) == -1 ||
        sigaction(SIGTERM, &action, NULL) == -1) {
        std::perror("sigaction");
        return false;
    }
    return true;
}

inline int parse_port(int argc, char* argv[], int default_port) {
    if (argc == 1) {
        return default_port;
    }
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " [port: 1..65535]\n";
        return -1;
    }
    char* end = NULL;
    errno = 0;
    const long value = std::strtol(argv[1], &end, 10);
    if (errno || end == argv[1] || *end != '\0' || value < 1 || value > 65535) {
        std::cerr << "Port must be an integer from 1 to 65535.\n";
        return -1;
    }
    return static_cast<int>(value);
}

inline bool set_nonblocking(int fd) {
    // fcntl(): preserve existing flags, then add O_NONBLOCK.
    const int flags = fcntl(fd, F_GETFL, 0);
    return flags != -1 && fcntl(fd, F_SETFL, flags | O_NONBLOCK) != -1;
}

inline int create_listener(int port, bool nonblocking) {
    // socket(): create a TCP endpoint and obtain a File Descriptor.
    // File Descriptor: this integer indexes THIS process's open-FD table.
    const int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd == -1) {
        std::perror("socket");
        return -1;
    }
    const int reuse = 1;
    // setsockopt(): allow convenient restart after a previous run.
    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse)) == -1) {
        std::perror("setsockopt");
        close(fd);
        return -1;
    }
    sockaddr_in address = {};
    address.sin_family = AF_INET;
    address.sin_port = htons(static_cast<unsigned short>(port));
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    // bind(): associate this socket with 127.0.0.1 and a port.
    if (bind(fd, reinterpret_cast<sockaddr*>(&address), sizeof(address)) == -1) {
        std::perror("bind");
        close(fd);
        return -1;
    }
    // listen(): create a pending-connection queue, not a worker thread pool.
    if (listen(fd, SOMAXCONN) == -1 || (nonblocking && !set_nonblocking(fd))) {
        std::perror("listen/fcntl");
        close(fd);
        return -1;
    }
    return fd;
}

inline std::string reply_for(std::string line) {
    // TCP is a byte stream: newline, rather than recv() boundaries, frames BUY.
    if (!line.empty() && line.back() == '\r') {
        line.pop_back(); // Also allow CRLF from terminal clients.
    }
    return line == "BUY" ? "REQUEST RECEIVED\n" : "UNKNOWN COMMAND\n";
}

inline bool send_all(int fd, const std::string& message) {
    std::size_t offset = 0;
    while (offset < message.size()) {
        // send(): even blocking sockets can return a partial write.
        // MSG_NOSIGNAL prevents a disconnected client from causing SIGPIPE.
        const ssize_t sent = send(fd, message.data() + offset,
                                  message.size() - offset, MSG_NOSIGNAL);
        if (sent > 0) {
            offset += static_cast<std::size_t>(sent);
        } else if (sent == -1 && errno == EINTR) {
            continue;
        } else {
            return false;
        }
    }
    return true;
}
} // namespace ticket_demo
#endif
