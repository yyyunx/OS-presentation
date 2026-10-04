#include <deque>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

struct Request {
    std::string name;
    int arrival;
    int burst;
};

struct Slice {
    std::string name;
    int start;
    int end;
};

struct Result {
    std::vector<int> completion;
    std::vector<Slice> chart;
};

void show_result(const std::string& title,
                 const std::vector<Request>& requests, const Result& result) {
    std::cout << "\n=== " << title << " ===\n\n"
              << std::left << std::setw(12) << "Request"
              << std::setw(12) << "Arrival" << std::setw(12) << "Burst"
              << std::setw(12) << "Waiting" << "Completion\n";

    double total_waiting = 0;
    for (std::size_t i = 0; i < requests.size(); ++i) {
        // Turnaround = completion - arrival.
        // Waiting = turnaround - CPU burst (also works for preemptive RR).
        const int waiting = result.completion[i] - requests[i].arrival
                            - requests[i].burst;
        total_waiting += waiting;
        std::cout << std::setw(12) << requests[i].name
                  << std::setw(12) << requests[i].arrival
                  << std::setw(12) << requests[i].burst
                  << std::setw(12) << waiting << result.completion[i] << "\n";
    }
    std::cout << std::fixed << std::setprecision(2)
              << "Average Waiting Time: " << total_waiting / requests.size()
              << " time units\n\nGantt Chart (each block is one CPU slice):\n|";
    for (const auto& slice : result.chart) {
        std::cout << " " << slice.name << " [" << slice.start << ","
                  << slice.end << ") |";
    }
    std::cout << "\n";
}

Result fcfs(const std::vector<Request>& requests) {
    Result result;
    result.completion.resize(requests.size());
    int time = 0;
    // The fixed input is sorted by arrival. Equal arrivals keep input order.
    for (std::size_t i = 0; i < requests.size(); ++i) {
        if (time < requests[i].arrival) {
            result.chart.push_back({"IDLE", time, requests[i].arrival});
            time = requests[i].arrival;
        }
        // FCFS is non-preemptive: run an arrived request until it finishes.
        result.chart.push_back({requests[i].name, time, time + requests[i].burst});
        time += requests[i].burst;
        result.completion[i] = time;
    }
    return result;
}

Result sjf(const std::vector<Request>& requests) {
    Result result;
    result.completion.resize(requests.size());
    std::vector<bool> done(requests.size(), false);
    int time = 0;
    std::size_t completed = 0;

    while (completed < requests.size()) {
        int best = -1;
        int next_arrival = std::numeric_limits<int>::max();
        for (std::size_t i = 0; i < requests.size(); ++i) {
            if (done[i]) {
                continue;
            }
            // Pick only requests that have arrived, never a future request.
            if (requests[i].arrival <= time) {
                if (best == -1 || requests[i].burst < requests[best].burst) {
                    best = static_cast<int>(i);
                }
            } else if (requests[i].arrival < next_arrival) {
                next_arrival = requests[i].arrival;
            }
        }
        if (best == -1) {
            result.chart.push_back({"IDLE", time, next_arrival});
            time = next_arrival;
            continue;
        }
        // Non-preemptive SJF: a newly arrived short job cannot interrupt
        // the current job. Equal bursts keep input (arrival) order.
        result.chart.push_back({requests[best].name, time,
                                time + requests[best].burst});
        time += requests[best].burst;
        result.completion[best] = time;
        done[best] = true;
        ++completed;
    }
    return result;
}

Result round_robin(const std::vector<Request>& requests, int quantum) {
    Result result;
    result.completion.resize(requests.size());
    std::vector<int> remaining;
    for (const auto& request : requests) {
        remaining.push_back(request.burst);
    }

    std::deque<int> ready_queue;
    std::size_t next = 0;
    int time = 0;
    // Input is sorted by arrival; each request enters the queue once initially.
    const auto enqueue_arrivals = [&]() {
        while (next < requests.size() && requests[next].arrival <= time) {
            ready_queue.push_back(static_cast<int>(next));
            ++next;
        }
    };

    while (next < requests.size() || !ready_queue.empty()) {
        if (ready_queue.empty() && time < requests[next].arrival) {
            result.chart.push_back({"IDLE", time, requests[next].arrival});
            time = requests[next].arrival;
        }
        enqueue_arrivals();
        const int current = ready_queue.front();
        ready_queue.pop_front();
        const int duration = remaining[current] < quantum
                             ? remaining[current] : quantum;
        result.chart.push_back({requests[current].name, time, time + duration});
        time += duration;
        remaining[current] -= duration;

        // Preemption: after a time quantum, unfinished work goes to the tail.
        // Arrivals during this slice (INCLUDING its end) queue before requeue.
        enqueue_arrivals();
        if (remaining[current] > 0) {
            ready_queue.push_back(current);
        } else {
            result.completion[current] = time;
        }
    }
    return result;
}

int main() {
    // Arrival-sorted, positive bursts; values are simulated CPU time units.
    const std::vector<Request> requests = {
        {"A", 0, 8}, {"B", 1, 2}, {"C", 2, 4}, {"D", 3, 1}
    };
    const int quantum = 2;
    std::cout << "Who Runs First? CPU Scheduling Simulator\n"
              << "One simulated CPU; no I/O and zero context-switch overhead.\n"
              << "Round Robin time quantum = " << quantum << " time units\n";

    show_result("FCFS", requests, fcfs(requests));
    show_result("SJF (non-preemptive)", requests, sjf(requests));
    show_result("Round Robin", requests, round_robin(requests, quantum));

    // This is a teaching simulator, not a change to the Linux CPU scheduler.
    // Real burst lengths are unknown, and switching has a nonzero cost.
}
