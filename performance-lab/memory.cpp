#include "lab.h"

#include <algorithm>
#include <cstring>
#include <numeric>
#include <random>
#include <unistd.h>
#if defined(__SSE2__)
#include <emmintrin.h>
#endif

namespace lab {
namespace {
Result cache_locality(bool sequential, Config config) {
    const std::size_t count = config.quick ? (1U << 16) : (1U << 24);
    std::vector<std::uint32_t> next(count);
    if (sequential) {
        for (std::size_t i = 0; i < count; ++i) next[i] = (i + 1) % count;
    } else {
        std::vector<std::uint32_t> order(count);
        std::iota(order.begin(), order.end(), 0U);
        std::mt19937 random(config.seed);
        std::shuffle(order.begin(), order.end(), random);
        for (std::size_t i = 0; i < count; ++i) next[order[i]] = order[(i + 1) % count];
    }
    Result result;
    result.operations = count;
    result.working_set_bytes = result.logical_bytes = count * sizeof(next.front());
    result.expected = static_cast<std::uint64_t>(count) * (count - 1) / 2;
    std::uint32_t index = 0;
    measure(result, [&] {
        for (std::size_t i = 0; i < count; ++i) {
            index = next[index];
            result.checksum += index;
        }
    });
    if (index != 0) throw std::runtime_error("pointer chain did not return to start");
    return result;
}

__attribute__((noinline, optimize("no-tree-vectorize")))
std::uint64_t matrix_sum(const std::uint32_t* data, std::size_t side,
                         std::size_t outer_stride, std::size_t inner_stride) {
    std::uint64_t sum = 0;
    for (std::size_t outer = 0; outer < side; ++outer) {
        for (std::size_t inner = 0; inner < side; ++inner) {
            sum += data[outer * outer_stride + inner * inner_stride];
        }
    }
    return sum;
}

Result matrix_traversal(bool row_major, Config config) {
    const std::size_t side = config.quick ? 130 : 2048;
    std::vector<std::uint32_t> matrix(side * side);
    std::mt19937 random(config.seed);
    Result result;
    for (auto& value : matrix) {
        value = random() & 255U;
        result.expected += value;
    }
    result.operations = matrix.size();
    result.working_set_bytes = result.logical_bytes = result.operations * sizeof(matrix.front());
    const std::size_t outer_stride = row_major ? side : 1;
    const std::size_t inner_stride = row_major ? 1 : side;
    measure(result, [&] {
        result.checksum = matrix_sum(matrix.data(), side, outer_stride, inner_stride);
    });
    return result;
}

__attribute__((noinline, optimize("no-tree-vectorize")))
std::uint32_t scalar_sum(const std::uint32_t* data, std::size_t count) {
    std::uint32_t sum = 0;
    for (std::size_t i = 0; i < count; ++i) sum += data[i];
    return sum;
}

#if defined(__SSE2__)
__attribute__((noinline))
std::uint32_t vector_sum(const std::uint32_t* data, std::size_t count) {
    __m128i accumulator = _mm_setzero_si128();
    std::size_t i = 0;
    for (; i + 4 <= count; i += 4) {
        const auto values = _mm_loadu_si128(reinterpret_cast<const __m128i_u*>(data + i));
        accumulator = _mm_add_epi32(accumulator, values);
    }
    alignas(16) std::uint32_t lanes[4];
    _mm_store_si128(reinterpret_cast<__m128i*>(lanes), accumulator);
    std::uint32_t sum = lanes[0] + lanes[1] + lanes[2] + lanes[3];
    for (; i < count; ++i) sum += data[i];
    return sum;
}
#endif

Result sum_linear(bool vectorized, std::size_t offset, Config config) {
    auto kernel = scalar_sum;
    if (vectorized) {
#if defined(__SSE2__)
        kernel = vector_sum;
#else
        throw Unavailable("SSE2 is unavailable in this build");
#endif
    }
    const std::size_t count = (config.quick ? 32768 : 262144) + 3;  // exercise SIMD tail
    const std::size_t repetitions = config.quick ? 4 : 128;
    // Align an interior address of an array of live uint32_t objects. Offset is
    // expressed in whole objects, so the scalar tail is still naturally aligned.
    std::vector<std::uint32_t> storage(count + 16);
    const auto address = reinterpret_cast<std::uintptr_t>(storage.data());
    const auto alignment = (64 - address % 64) % 64 / sizeof(std::uint32_t);
    auto* data = storage.data() + alignment + offset;
    std::mt19937 random(config.seed);
    std::uint64_t expected = 0;
    for (std::size_t i = 0; i < count; ++i) {
        data[i] = random();
        expected += data[i];
    }
    Result result;
    result.input_offset_bytes = reinterpret_cast<std::uintptr_t>(data) % 64;
    result.cache_line_bytes = sysconf(_SC_LEVEL1_DCACHE_LINESIZE);
    result.operations = count * repetitions;
    result.working_set_bytes = count * sizeof(*data);
    result.logical_bytes = result.working_set_bytes * repetitions;
    result.expected = static_cast<std::uint32_t>(expected) * static_cast<std::uint64_t>(repetitions);
    measure(result, [&] {
        for (std::size_t run = 0; run < repetitions; ++run) {
            observe(data);  // Data may change between calls in the compiler's model.
            result.checksum += kernel(data, count);
        }
    });
    return result;
}

Result memory_bandwidth(bool small, Config config) {
    const std::size_t bytes = small ? (16U << 10) : (config.quick ? (1U << 20) : (128U << 20));
    const std::size_t repetitions = (config.quick ? (4U << 20) : (512U << 20)) / bytes;
    std::vector<unsigned char> source(bytes), destination(bytes, 0);
    std::uint64_t expected = 0;
    for (std::size_t i = 0; i < bytes; ++i) {
        source[i] = (i + (i >> 8) + config.seed) & 255U;
        expected += source[i];
    }
    Result result;
    result.operations = bytes * repetitions;  // one operation per payload byte
    result.working_set_bytes = bytes * 2;
    result.logical_bytes = result.operations * 2;  // one read plus one write
    result.expected = expected;
    measure(result, [&] {
        for (std::size_t run = 0; run < repetitions; ++run) {
            std::memcpy(destination.data(), source.data(), bytes);
            observe(destination.data());  // Keep each copy, not just the final one.
        }
    });
    if (source != destination) throw std::runtime_error("copy differs from source");
    result.checksum = std::accumulate(destination.begin(), destination.end(), std::uint64_t{0});
    return result;
}
}

Result memory_experiment(const std::string& name, const std::string& variant, Config config) {
    if (name == "cache-locality") return cache_locality(choose(variant, "sequential", "random"), config);
    if (name == "matrix-traversal") return matrix_traversal(choose(variant, "row", "column"), config);
    if (name == "simd") return sum_linear(!choose(variant, "scalar", "sse2"), 0, config);
    if (name == "memory-alignment") {
        return sum_linear(true, choose(variant, "aligned", "offset-4") ? 0 : 1, config);
    }
    return memory_bandwidth(choose(variant, "small", "large"), config);
}
}
