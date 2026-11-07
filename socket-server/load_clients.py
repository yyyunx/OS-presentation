#!/usr/bin/env python3
"""Standard-library load generator: many sockets, no thread per client."""

import argparse
import selectors
import socket
import time


def positive_int(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clients", type=positive_int, help="number of TCP connections")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--hold", type=float, default=20, help="keep sockets open for N seconds")
    parser.add_argument("--idle", action="store_true", help="connect without sending BUY")
    parser.add_argument("--requests", type=positive_int, default=1, help="BUY requests per connection")
    parser.add_argument("--timeout", type=float, default=10, help="connect/reply timeout in seconds")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or args.hold < 0 or args.timeout <= 0:
        parser.error("invalid port, hold, or timeout")
    if args.requests > 100:
        parser.error("--requests is limited to 100 for this classroom generator")

    connections = []
    selector = selectors.DefaultSelector()
    replies = 0
    failures = 0
    try:
        print("Connecting {} clients to {}:{}".format(args.clients, args.host, args.port), flush=True)
        for _ in range(args.clients):
            try:
                # Each client socket also consumes an FD in THIS client process.
                sock = socket.create_connection((args.host, args.port), args.timeout)
                connections.append(sock)
                count = len(connections)
                if count == 1 or count % 50 == 0 or count == args.clients:
                    print("Connected clients: {}".format(count), flush=True)
            except OSError as error:
                failures += args.clients - len(connections)
                print("Connect stopped: {} (check server and ulimit -n)".format(error), flush=True)
                break

        if not args.idle:
            for sock in connections:
                try:
                    # TCP is a stream. Newlines delimit possibly coalesced requests.
                    sock.sendall(b"BUY\n" * args.requests)
                    sock.setblocking(False)
                    selector.register(sock, selectors.EVENT_READ, [b"", 0])
                except OSError as error:
                    failures += 1
                    print("Send failed: {}".format(error), flush=True)

            deadline = time.monotonic() + args.timeout
            while selector.get_map() and time.monotonic() < deadline:
                ready = selector.select(max(0, deadline - time.monotonic()))
                for key, _ in ready:
                    sock = key.fileobj
                    state = key.data  # partial reply buffer, replies on this FD
                    try:
                        data = sock.recv(4096)
                    except BlockingIOError:
                        continue
                    except OSError:
                        data = b""
                    if not data:
                        failures += 1
                        selector.unregister(sock)
                        continue
                    state[0] += data
                    invalid = False
                    while b"\n" in state[0]:
                        line, state[0] = state[0].split(b"\n", 1)
                        if line != b"REQUEST RECEIVED":
                            invalid = True
                            break
                        replies += 1
                        state[1] += 1
                    if invalid or len(state[0]) > 1024:
                        failures += 1
                        selector.unregister(sock)
                    elif state[1] == args.requests:
                        selector.unregister(sock)

            failures += len(selector.get_map())
            print("Replies: {} / {}".format(replies, len(connections) * args.requests), flush=True)
        else:
            print("Idle mode: no requests sent; server sockets stay connected.", flush=True)

        if connections:
            print("Holding {} sockets for {} seconds; inspect server FDs/threads now."
                  .format(len(connections), args.hold), flush=True)
            time.sleep(args.hold)
        else:
            print("No connected sockets to hold.", flush=True)
    except KeyboardInterrupt:
        print("\nStopping clients.", flush=True)
    finally:
        selector.close()
        for sock in connections:
            sock.close()
        print("Closed {} client sockets. Failures: {}".format(len(connections), failures), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
