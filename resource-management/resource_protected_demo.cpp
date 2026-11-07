#include "request_simulator.h"

int main(int argc, char* argv[]) {
    // Same workload/workers, but bounded queue + timed backpressure + rejection.
    return resource_demo::run_simulator(true, argc, argv);
}
