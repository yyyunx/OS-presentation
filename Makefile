CXX = g++
CXXFLAGS = -std=c++11 -O2 -Wall -Wextra -Wpedantic -pthread

# Linux defaults to extension-free executables.
# Optional override EXE=.exe is only for supplementary MinGW verification.
EXE ?=

PHASE1 = bin/concurrency_demo$(EXE) bin/scheduling_demo$(EXE) \
         bin/race_demo$(EXE) bin/mutex_demo$(EXE)
PHASE2 = bin/socket_server$(EXE) bin/blocking_server$(EXE) \
         bin/epoll_server$(EXE) bin/resource_uncontrolled_demo$(EXE) \
         bin/resource_protected_demo$(EXE)
NETWORK_HEADERS = socket-server/net_utils.h socket-server/blocking_ticket_server.h

.PHONY: all phase1 phase2 test demo-ui test-demo-ui clean
all: $(PHASE1) $(PHASE2)
phase1: $(PHASE1)
phase2: $(PHASE2)

bin:
	mkdir -p bin

bin/concurrency_demo$(EXE): concurrency/concurrency_demo.cpp | bin
	$(CXX) $(CXXFLAGS) $< -o $@

bin/scheduling_demo$(EXE): scheduling/scheduling_demo.cpp | bin
	$(CXX) $(CXXFLAGS) $< -o $@

bin/race_demo$(EXE): race-condition/race_demo.cpp | bin
	$(CXX) $(CXXFLAGS) $< -o $@

bin/mutex_demo$(EXE): race-condition/mutex_demo.cpp | bin
	$(CXX) $(CXXFLAGS) $< -o $@

bin/socket_server$(EXE): socket-server/socket_server.cpp $(NETWORK_HEADERS) | bin
	$(CXX) $(CXXFLAGS) $< -o $@

bin/blocking_server$(EXE): epoll-server/blocking_server.cpp $(NETWORK_HEADERS) | bin
	$(CXX) $(CXXFLAGS) $< -o $@

bin/epoll_server$(EXE): epoll-server/epoll_server.cpp socket-server/net_utils.h | bin
	$(CXX) $(CXXFLAGS) $< -o $@

bin/resource_uncontrolled_demo$(EXE): resource-management/resource_uncontrolled_demo.cpp resource-management/request_simulator.h | bin
	$(CXX) $(CXXFLAGS) $< -o $@

bin/resource_protected_demo$(EXE): resource-management/resource_protected_demo.cpp resource-management/request_simulator.h | bin
	$(CXX) $(CXXFLAGS) $< -o $@

# Linux integration checks; standard-library Python, no third-party packages.
test: all
	python3 -m unittest discover -s tests -p 'test_*.py'
	python3 tests/ubuntu_smoke.py

demo-ui: all
	python3 demo-ui/controller.py

test-demo-ui: all
	python3 tests/dashboard_integration.py --output docs/dashboard-ubuntu-results.json

clean:
	rm -rf bin
