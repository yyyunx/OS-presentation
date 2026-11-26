#include "lab.h"

#include <fstream>
#include <iostream>
#include <sched.h>
#include <sys/resource.h>

#ifndef LAB_BUILD_FLAGS
#error Define LAB_BUILD_FLAGS with the actual compiler flags
#endif

namespace lab {
Usage usage() {
    rusage value{};
    if (getrusage(RUSAGE_SELF, &value) != 0) {
        throw std::runtime_error("getrusage(RUSAGE_SELF) failed");
    }
    const auto pr_ns = [](timeval t) { return t.tv_sec * 1e9 + t.tv_usec * 1000.0; };
    return {pr_ns(value.ru_utime) + pr_ns(value.ru_stime),
            static_cast<std::uint64_t>(value.ru_nvcsw),
            static_cast<std::uint64_t>(value.ru_nivcsw)};
}

std::uint64_t peak_rss_bytes() {
    // VmHWM is for this executable's memory image. Linux ru_maxrss can
    // retain a pre-exec high-water mark from the launching process.
    std::ifstream status("/proc/self/status");
    for (std::string line; std::getline(status, line);) {
        if (line.compare(0, 6, "VmHWM:") == 0) return std::stoull(line.substr(6)) * 1024;
    }
    throw std::runtime_error("VmHWM missing from /proc/self/status");
}

std::vector<int> allowed_cpus() {
    cpu_set_t mask;
    CPU_ZERO(&mask);
    if (sched_getaffinity(0, sizeof(mask), &mask) != 0) {
        return {};
    }
    std::vector<int> cpus;
    for (int cpu = 0; cpu < CPU_SETSIZE; ++cpu) {
        if (CPU_ISSET(cpu, &mask)) cpus.push_back(cpu);
    }
    return cpus;
}
}

namespace {
void string_json(const std::string& value) {
    std::cout << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') std::cout << '\\';
        if (c < 32) {
            const char* hex = "0123456789abcdef";
            std::cout << "\\u00" << hex[c / 16] << hex[c % 16];
        } else {
            std::cout << c;
        }
    }
    std::cout << '"';
}

void cpus_json(const std::vector<int>& value) {
    std::cout << '[';
    for (std::size_t i = 0; i < value.size(); ++i) {
        if (i != 0) std::cout << ',';
        std::cout << value[i];
    }
    std::cout << ']';
}

void print(const lab::Result& r) {
    std::cout << "{\"status\":\"ok\",\"elapsed_ns\":" << r.elapsed_ns
              << ",\"cpu_ns\":" << static_cast<std::uint64_t>(r.cpu_ns)
              << ",\"peak_rss_bytes\":" << r.peak_rss_bytes
              << ",\"voluntary_switches\":" << r.voluntary_switches
              << ",\"involuntary_switches\":" << r.involuntary_switches
              << ",\"operations\":" << r.operations
              << ",\"logical_bytes\":" << r.logical_bytes
              << ",\"working_set_bytes\":" << r.working_set_bytes
              << ",\"checksum\":" << r.checksum
              << ",\"expected_checksum\":" << r.expected
              << ",\"threads\":" << r.threads << ",\"pinned_cpus\":";
    cpus_json(r.pinned_cpus);
    std::cout << ",\"input_offset_bytes\":";
    if (r.input_offset_bytes >= 0) std::cout << r.input_offset_bytes;
    else std::cout << "null";
    std::cout << ",\"cache_line_bytes\":";
    if (r.cache_line_bytes > 0) std::cout << r.cache_line_bytes;
    else std::cout << "null";
    std::cout << "}\n";
}
}

int main(int argc, char* argv[]) {
    try {
        if (argc == 2 && std::string(argv[1]) == "--build-info") {
            std::cout << "{\"compiler\":";
            string_json(__VERSION__);
            std::cout << ",\"flags\":";
            string_json(LAB_BUILD_FLAGS);
            std::cout << ",\"allowed_cpus\":";
            cpus_json(lab::allowed_cpus());
            std::cout << "}\n";
            return 0;
        }
        if (argc != 5) {
            throw std::invalid_argument("usage: systems_lab EXPERIMENT VARIANT quick|standard SEED");
        }
        const std::string profile = argv[3], seed = argv[4], name = argv[1];
        if (profile != "quick" && profile != "standard") {
            throw std::invalid_argument("profile must be quick or standard");
        }
        if (seed.empty() || seed.find_first_not_of("0123456789") != std::string::npos) {
            throw std::invalid_argument("seed must be an unsigned 32-bit integer");
        }
        const auto number = std::stoull(seed);
        if (number > UINT32_MAX) throw std::invalid_argument("seed out of range");
        const lab::Config config{profile == "quick", static_cast<std::uint32_t>(number)};
        const auto r = name == "cache-locality" || name == "matrix-traversal" ||
                       name == "memory-alignment" || name == "simd" || name == "memory-bandwidth"
                         ? lab::memory_experiment(name, argv[2], config)
                         : lab::cpu_experiment(name, argv[2], config);
        if (r.elapsed_ns == 0 || r.operations == 0 || r.checksum != r.expected) {
            throw std::runtime_error("invalid timing or checksum " + std::to_string(r.checksum) +
                                     " (expected " + std::to_string(r.expected) + ")");
        }
        print(r);
        return 0;
    } catch (const lab::Unavailable& error) {
        std::cout << "{\"status\":\"unavailable\",\"reason\":";
        string_json(error.what());
        std::cout << "}\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
