#include "../socket-server/blocking_ticket_server.h"

int main(int argc, char* argv[]) {
    // Same protocol/implementation as Demo 4: one blocking worker per client.
    return ticket_demo::run_blocking_server(argc, argv, 8081, "Blocking Server");
}
