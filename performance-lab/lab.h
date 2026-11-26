#ifndef PERFORMANCE_LAB_LAB_H
#define PERFORMANCE_LAB_LAB_H

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstddef>
#include <stdexcept>
#include <string>
#include <vector>

namespace lab {
using Clock = std::chrono::steady_clock;

struct Unavailable : std::runtime_error {
    using std::runtime_error::runtime_error;
};

struct Config {
    bool quick;
    std::uint32_t seed;
};

struct Usage {
    double cpu_ns;
    std::uint64_t voluntary_switches;
    std::uint64_t involuntary_switches;
};

struct Result {
    std::uint64_t operations = 0;
    std::uint64_t logical_bytes = 0;
    std::uint64_t working_set_bytes = 0;
    std::uint64_t checksum = 0;
    std::uint64_t expected = 0;
    std::uint64_t elapsed_ns = 0;
    double cpu_ns = 0;
    std::uint64_t peak_rss_bytes = 0;
    std::uint64_t voluntary_switches = 0;
    std::uint64_t involuntary_switches = 0;
    unsigned threads = 1;
    std::vector<int> pinned_cpus;
    int input_offset_bytes = -1;
    long cache_line_bytes = -1;
};

Usage usage();
std::uint64_t peak_rss_bytes();
std::vector<int> allowed_cpus();

// GCC compiler barrier. It emits no CPU fence and makes memory visible to
// the compiler at this point. The printed, checked result is also observable.
inline void observe(const void* address = nullptr) {
    asm volatile("" : : "g"(address) : "memory");
}

template<class Work>
void measure(Result& result, Work work) {
    const auto before = usage();
    const auto start = Clock::now();
    observe();
    work();
    observe();
    const auto end = Clock::now();
    const auto after = usage();
    result.elapsed_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start).count();
    result.cpu_ns = after.cpu_ns - before.cpu_ns;
    result.peak_rss_bytes = peak_rss_bytes();
    result.voluntary_switches = after.voluntary_switches - before.voluntary_switches;
    result.involuntary_switches = after.involuntary_switches - before.involuntary_switches;
}

Result memory_experiment(const std::string& name, const std::string& variant, Config config);
Result cpu_experiment(const std::string& name, const std::string& variant, Config config);

inline bool choose(const std::string& variant, const char* first, const char* second) {
    if (variant == first) return true;
    if (variant == second) return false;
    throw std::invalid_argument("unknown variant: " + variant);
}
}
#endif
