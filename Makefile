CXX = g++
CXXFLAGS = -std=c++11 -O2 -Wall -Wextra -Wpedantic -pthread

# Linux defaults to extension-free executables.
# Optional override EXE=.exe is only for supplementary MinGW verification.
EXE ?=

TARGETS = bin/concurrency_demo$(EXE) bin/scheduling_demo$(EXE) \
          bin/race_demo$(EXE) bin/mutex_demo$(EXE)

.PHONY: all clean
all: $(TARGETS)

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

clean:
	rm -rf bin
