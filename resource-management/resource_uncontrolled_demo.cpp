#include "request_simulator.h"

int main(int argc, char* argv[]) {
    // Unbounded pending queue: admit every request, even when workers are busy.
    return resource_demo::run_simulator(false, argc, argv);
}
