#pragma once

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <functional>
#include <limits>
#include <optional>
#include <queue>
#include <stdexcept>
#include <unordered_map>
#include <utility>
#include <vector>

namespace astar {

template <class State> struct Edge {
    State to;
    double cost;
};

enum class EventType { Discover, Expand, Update, Close, GoalFound };

template <class State> struct SearchEvent {
    EventType type;
    State state;
    std::optional<State> parent;
    double g;
    double h;
    double f;
};

template <class State> struct SearchResult {
    bool found = false;
    std::vector<State> path;
    double cost = std::numeric_limits<double>::infinity();
    std::size_t expanded_nodes = 0; // valid pops, including the goal and re-expansions
    std::size_t generated_nodes = 0; // OPEN entries pushed, including the start
    std::size_t relaxed_edges = 0;  // successful improvements (preserved API)
    std::size_t unique_expanded_states = 0;
    std::size_t unique_discovered_states = 0;
    std::size_t examined_edges = 0; // outgoing edges examined, whether improved or not
    std::vector<SearchEvent<State>> trace;
};

// Problem supplies neighbors(state), heuristic(state, goal), and is_goal(state, goal).
// Edge cost is kept with each neighbor so sparse graphs and implicit grids share this core.
// Optimality requires nonnegative finite edge costs and an admissible, finite heuristic.
template <class State, class Problem, class Hash = std::hash<State>,
          class Equal = std::equal_to<State>>
SearchResult<State> search(const Problem& problem, const State& start,
                           const State& goal, bool use_heuristic = true,
                           bool record_trace = true) {
    struct Record {
        double g = std::numeric_limits<double>::infinity();
        std::optional<State> parent;
        std::optional<double> expanded_g;
    };
    struct Entry {
        State state;
        double g, h, f;
        std::size_t order;
    };
    struct Worse {
        bool operator()(const Entry& a, const Entry& b) const {
            if (a.f < b.f) return false;
            if (a.f > b.f) return true;
            if (a.h < b.h) return false;
            if (a.h > b.h) return true;
            return a.order > b.order;
        }
    };
    auto estimate = [&](const State& state) {
        const double h = use_heuristic ? problem.heuristic(state, goal) : 0.0;
        if (!std::isfinite(h) || h < 0) throw std::invalid_argument("heuristic must be finite and nonnegative");
        return h;
    };
    SearchResult<State> result;
    std::unordered_map<State, Record, Hash, Equal> records;
    std::priority_queue<Entry, std::vector<Entry>, Worse> open;
    std::size_t order = 0;
    const double start_h = estimate(start);
    records[start].g = 0;
    open.push({start, 0, start_h, start_h, order++});
    result.generated_nodes++;
    result.unique_discovered_states++;
    if (record_trace) result.trace.push_back({EventType::Discover, start, std::nullopt, 0, start_h, start_h});

    while (!open.empty()) {
        const Entry current = open.top();
        open.pop();
        auto record_it = records.find(current.state);
        Record& record = record_it->second;
        if (current.g > record.g ||
            (record.expanded_g && current.g >= *record.expanded_g)) continue;
        if (!record.expanded_g) result.unique_expanded_states++;
        record.expanded_g = current.g;
        result.expanded_nodes++;
        if (record_trace) result.trace.push_back({EventType::Expand, current.state, record.parent,
                                                  current.g, current.h, current.f});

        if (problem.is_goal(current.state, goal)) {
            result.found = true;
            result.cost = current.g;
            if (record_trace) result.trace.push_back({EventType::GoalFound, current.state, record.parent,
                                                      current.g, current.h, current.f});
            State step = current.state;
            while (true) {
                result.path.push_back(step);
                const auto& step_record = records.at(step);
                if (!step_record.parent) break;
                step = *step_record.parent;
            }
            std::reverse(result.path.begin(), result.path.end());
            return result;
        }

        for (const auto& edge : problem.neighbors(current.state)) {
            result.examined_edges++;
            if (!std::isfinite(edge.cost) || edge.cost < 0)
                throw std::invalid_argument("edge cost must be finite and nonnegative");
            const double tentative = current.g + edge.cost;
            if (!std::isfinite(tentative)) throw std::overflow_error("path cost overflow");
            auto [it, inserted] = records.try_emplace(edge.to);
            if (tentative < it->second.g) {
                const double h = estimate(edge.to);
                it->second.g = tentative;
                it->second.parent = current.state;
                const double f = tentative + h;
                if (!std::isfinite(f)) throw std::overflow_error("priority overflow");
                open.push({edge.to, tentative, h, f, order++});
                result.generated_nodes++;
                if (inserted) result.unique_discovered_states++;
                result.relaxed_edges++;
                if (record_trace) result.trace.push_back({inserted ? EventType::Discover : EventType::Update,
                                                           edge.to, current.state, tentative, h, f});
            }
        }
        if (record_trace) result.trace.push_back({EventType::Close, current.state, records.at(current.state).parent,
                                                  current.g, current.h, current.f});
    }
    return result;
}

template <class State, class Problem, class Hash = std::hash<State>,
          class Equal = std::equal_to<State>>
SearchResult<State> dijkstra(const Problem& problem, const State& start,
                             const State& goal, bool record_trace = true) {
    return search<State, Problem, Hash, Equal>(problem, start, goal, false, record_trace);
}
} // namespace astar
