#include "lab.h"

#include <algorithm>
#include <condition_variable>
#include <fstream>
#include <mutex>
#include <pthread.h>
#include <random>
#include <thread>
#include <utility>
#include <unistd.h>

namespace lab {
namespace {
constexpr std::size_t line_bytes = 64;

std::pair<int, int> core_of(int cpu) {
    const std::string base = "/sys/devices/system/cpu/cpu" + std::to_string(cpu) + "/topology/";
    std::pair<int, int> id{-1, -1};
    std::ifstream(base + "physical_package_id") >> id.first;
    std::ifstream(base + "core_id") >> id.second;
    return id;
}

std::vector<int> separate_cores() {
    const auto allowed = allowed_cpus();
    for (const int first : allowed) {
        const auto core = core_of(first);
        if (core.first < 0 || core.second < 0) continue;
        for (const int second : allowed) {
            if (second <= first) continue;
            const auto other = core_of(second);
            if (other.first >= 0 && other.second >= 0 && core != other) return {first, second};
        }
    }
    throw Unavailable("two allowed CPUs on distinct OS-reported cores are required");
}

int one_cpu() {
    const auto allowed = allowed_cpus();
    if (allowed.empty()) throw Unavailable("no allowed CPU was found");
    return allowed.front();
}

int pin(int cpu) {
    cpu_set_t mask;
    CPU_ZERO(&mask);
    CPU_SET(cpu, &mask);
    return pthread_setaffinity_np(pthread_self(), sizeof(mask), &mask);
}

template<class Work>
void run_workers(Result& result, Work work) {
    std::mutex mutex;
    std::condition_variable all_ready;
    std::condition_variable release;
    unsigned ready = 0;
    int pin_error = 0;
    bool start = false;
    bool cancelled = false;
    std::vector<std::thread> workers;
    workers.reserve(result.threads);

    const auto release_workers = [&](bool cancel) {
        {
            std::lock_guard<std::mutex> lock(mutex);
            cancelled = cancel;
            start = true;
        }
        release.notify_all();
        for (auto& worker : workers) worker.join();
    };

    try {
        for (unsigned i = 0; i < result.threads; ++i) {
            workers.emplace_back([&, i] {
                const int error = result.pinned_cpus.empty() ? 0 : pin(result.pinned_cpus[i]);
                {
                    std::unique_lock<std::mutex> lock(mutex);
                    if (error) pin_error = error;
                    ++ready;
                    all_ready.notify_one();
                    release.wait(lock, [&] { return start; });
                    if (cancelled) return;
                }
                work(i);
            });
        }
        {
            std::unique_lock<std::mutex> lock(mutex);
            all_ready.wait(lock, [&] { return ready == result.threads; });
        }
        if (pin_error) throw Unavailable("pthread_setaffinity_np error " + std::to_string(pin_error));
        // Thread construction and pinning precede timing. Wakeup and join are included.
        measure(result, [&] { release_workers(false); });
    } catch (...) {
        if (!start) release_workers(true);
        throw;
    }
}

using Counter = std::atomic<std::uint64_t>;

struct alignas(line_bytes) PaddedCounter {
    Counter value{0};
};

struct alignas(line_bytes) SharedCounters {
    Counter value[2]{};
};

static_assert(sizeof(SharedCounters::value) <= line_bytes, "counters must fit in one line");
static_assert(sizeof(PaddedCounter) == line_bytes, "padded counters must occupy separate lines");

Result false_sharing(bool packed, Config config) {
    Result result;
    result.cache_line_bytes = sysconf(_SC_LEVEL1_DCACHE_LINESIZE);
    if (result.cache_line_bytes != line_bytes) {
        throw Unavailable("this layout requires a detected 64-byte L1 data cache line");
    }
    result.pinned_cpus = separate_cores();
    result.threads = 2;
    const std::uint64_t updates = config.quick ? 20000 : 2000000;
    SharedCounters shared;
    PaddedCounter padded[2];
    Counter* counters[] = {packed ? &shared.value[0] : &padded[0].value,
                           packed ? &shared.value[1] : &padded[1].value};
    if (!counters[0]->is_lock_free()) throw Unavailable("64-bit atomic is not lock-free");
    result.operations = result.expected = result.threads * updates;
    result.working_set_bytes = packed ? sizeof(shared) : sizeof(padded);
    run_workers(result, [&](unsigned i) {
        for (std::uint64_t j = 0; j < updates; ++j) counters[i]->fetch_add(1, std::memory_order_relaxed);
    });
    for (auto* counter : counters) {
        const auto value = counter->load(std::memory_order_relaxed);
        if (value != updates) throw std::runtime_error("worker counter does not match");
        result.checksum += value;
    }
    return result;
}

Result mutex_atomic(bool use_mutex, Config config) {
    Result result;
    result.threads = 2;
    const std::uint64_t updates = config.quick ? 20000 : 1000000;
    std::mutex mutex;
    std::uint64_t plain = 0;
    Counter atomic{0};
    result.operations = result.expected = result.threads * updates;
    // Both variants inherit the same affinity mask. There is one logical
    // counter in both cases, so contention here is true sharing.
    run_workers(result, [&](unsigned) {
        if (use_mutex) {
            for (std::uint64_t i = 0; i < updates; ++i) {
                std::lock_guard<std::mutex> lock(mutex);
                ++plain;
            }
        } else {
            for (std::uint64_t i = 0; i < updates; ++i) atomic.fetch_add(1, std::memory_order_relaxed);
        }
    });
    result.checksum = use_mutex ? plain : atomic.load(std::memory_order_relaxed);
    return result;
}

constexpr std::uint64_t multiplier = 6364136223846793005ULL;
constexpr std::uint64_t increment = 1442695040888963407ULL;

__attribute__((noinline))
std::uint64_t recurrence(std::uint64_t value, std::uint64_t steps) {
    for (std::uint64_t i = 0; i < steps; ++i) value = value * multiplier + increment;
    return value;
}

// Independent reference: compose affine maps by powers of two modulo 2^64.
std::uint64_t recurrence_reference(std::uint64_t value, std::uint64_t steps) {
    auto scale = multiplier;
    auto add = increment;
    for (; steps; steps >>= 1) {
        if (steps & 1) value = value * scale + add;
        add = add * scale + add;
        scale *= scale;
    }
    return value;
}

Result affinity(const std::string& variant, Config config) {
    Result result;
    result.threads = 2;
    if (variant == "same-cpu") {
        const auto cpu = one_cpu();
        result.pinned_cpus = {cpu, cpu};
    } else if (variant == "spread") {
        result.pinned_cpus = separate_cores();
    } else if (variant != "unpinned") {
        throw std::invalid_argument("unknown affinity variant: " + variant);
    }
    const std::uint64_t steps = config.quick ? 200000 : 24000000;
    std::uint64_t values[2]{};
    result.operations = result.threads * steps;
    for (unsigned i = 0; i < result.threads; ++i) {
        result.expected += recurrence_reference(static_cast<std::uint64_t>(config.seed) + i, steps);
    }
    run_workers(result, [&](unsigned i) {
        values[i] = recurrence(static_cast<std::uint64_t>(config.seed) + i, steps);
    });
    result.checksum = values[0] + values[1];
    return result;
}

__attribute__((noinline, optimize("no-tree-vectorize,no-if-conversion,no-if-conversion2")))
std::uint64_t branch_sum(const unsigned char* data, std::size_t size) {
    std::uint64_t sum = 0;
    for (std::size_t i = 0; i < size; ++i) {
        if (data[i]) {
            // Prevent if-conversion or replacing the branch with a count.
            asm volatile("" : : "r"(i));
            sum += 1;
        }
    }
    return sum;
}

Result branch_prediction(bool sorted, Config config) {
    const std::size_t count = config.quick ? (1U << 15) : (1U << 22);
    const unsigned repetitions = config.quick ? 4 : 10;
    std::vector<unsigned char> data(count, 0);
    std::fill(data.begin() + count / 2, data.end(), 1);
    if (!sorted) {
        std::mt19937 random(config.seed);
        std::shuffle(data.begin(), data.end(), random);
    }
    Result result;
    result.operations = result.logical_bytes = count * repetitions;
    result.working_set_bytes = count;
    result.expected = result.operations / 2;
    measure(result, [&] {
        for (unsigned i = 0; i < repetitions; ++i) {
            observe(data.data());
            result.checksum += branch_sum(data.data(), data.size());
        }
    });
    return result;
}

Result context_switch(bool same_cpu, Config config) {
    Result result;
    result.threads = 2;
    if (same_cpu) {
        const auto cpu = one_cpu();
        result.pinned_cpus = {cpu, cpu};
    } else {
        result.pinned_cpus = separate_cores();
    }
    const std::uint64_t rounds = config.quick ? 500 : 30000;
    result.operations = result.expected = result.threads * rounds;
    std::mutex mutex;
    std::condition_variable handoff;
    unsigned turn = 0;
    run_workers(result, [&](unsigned worker) {
        std::unique_lock<std::mutex> lock(mutex);
        for (std::uint64_t i = 0; i < rounds; ++i) {
            handoff.wait(lock, [&] { return turn == worker; });
            ++result.checksum;
            turn = 1 - worker;
            handoff.notify_one();
        }
    });
    return result;
}
}

Result cpu_experiment(const std::string& name, const std::string& variant, Config config) {
    if (name == "false-sharing") return false_sharing(choose(variant, "packed", "padded"), config);
    if (name == "mutex-atomic") return mutex_atomic(choose(variant, "mutex", "atomic"), config);
    if (name == "cpu-affinity") return affinity(variant, config);
    if (name == "branch-prediction") return branch_prediction(choose(variant, "sorted", "shuffled"), config);
    if (name == "context-switch") return context_switch(choose(variant, "same-cpu", "spread"), config);
    throw std::invalid_argument("unknown experiment: " + name);
}
}
