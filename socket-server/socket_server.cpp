#include "blocking_ticket_server.h"

int main(int argc, char* argv[]) {
    // Demo 4 focuses on socket(), bind(), listen(), accept() and each socket FD.
    return ticket_demo::run_blocking_server(argc, argv, 8080, "Ticket Server");
}
