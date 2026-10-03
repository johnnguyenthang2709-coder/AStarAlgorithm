#include "../include/astar/grid_problem.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <vector>

namespace {
using astar::Cell;
using astar::Edge;
using astar::EventType;
using astar::GridMovement;
using astar::GridProblem;

void check(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
void cost_is(double actual, double expected) {
    check(std::abs(actual - expected) < 1e-9, "incorrect cost");
}
struct Graph {
    std::vector<std::vector<Edge<int>>> edges;
    std::vector<double> estimates;
    std::vector<Edge<int>> neighbors(int state) const { return edges.at(state); }
    double heuristic(int state, int) const { return estimates.at(state); }
    bool is_goal(int state, int goal) const { return state == goal; }
};
void test_graph_basics() {
    Graph graph{{{{1, 2.2}, {2, 0.7}}, {}, {{1, 0.7}}}, {0, 0, 0}};
    const auto path = astar::search<int>(graph, 0, 1);
    check(path.found && path.path == std::vector<int>({0, 2, 1}), "relaxation path/parent");
    cost_is(path.cost, 1.4);
    check(path.relaxed_edges == 3 && path.generated_nodes == 4, "relaxation counters");
    check(path.unique_discovered_states == 3 && path.unique_expanded_states == 3 &&
          path.examined_edges == 3, "distinct/examined counters");
    check(!astar::search<int>(graph, 1, 0).found, "reverse directed edge invented");
    const auto same = astar::search<int>(graph, 1, 1);
    check(same.found && same.path == std::vector<int>({1}), "start=goal path");
    cost_is(same.cost, 0);
    const auto unreachable = astar::search<int>(graph, 1, 2);
    check(!unreachable.found && unreachable.path.empty() && std::isinf(unreachable.cost), "unreachable result");
}
void test_reopening_and_stale_entries() {
    Graph graph{{{{1, 2}, {2, 1}}, {{3, 2}}, {{1, 0.5}}, {}}, {0, 0, 2, 0}};
    const auto a = astar::search<int>(graph, 0, 3);
    const auto d = astar::dijkstra<int>(graph, 0, 3);
    check(a.found && d.found && a.path == std::vector<int>({0, 2, 1, 3}), "reopening path");
    cost_is(a.cost, 3.5);
    cost_is(a.cost, d.cost);
    std::size_t expansions_of_1 = 0;
    bool updated_1 = false;
    for (const auto& event : a.trace) {
        if (event.type == EventType::Expand && event.state == 1) ++expansions_of_1;
        if (event.type == EventType::Update && event.state == 1 && event.parent == 2) updated_1 = true;
    }
    check(expansions_of_1 == 2 && updated_1, "closed state was not reopened");
    check(a.expanded_nodes == a.unique_expanded_states + 1, "reopening metric semantics");

    // Worse OPEN entry for node 1 must be discarded after node 2 improves it.
    Graph stale{{{{1, 10}, {2, 1}}, {{3, 20}}, {{1, 1}}, {}}, {0, 0, 0, 0}};
    const auto result = astar::search<int>(stale, 0, 3);
    check(result.found && result.path == std::vector<int>({0, 2, 1, 3}), "stale entry path");
    cost_is(result.cost, 22);
    check(result.expanded_nodes == 4, "stale entry was expanded");
}
void test_ties_and_events() {
    Graph graph{{{{1, 1}, {2, 1}}, {{3, 1}}, {{3, 1}}, {}}, {0, 1, 1, 0}};
    const auto stable = astar::search<int>(graph, 0, 3);
    check(stable.path == std::vector<int>({0, 1, 3}), "insertion-order tie");
    graph.estimates[1] = 1;
    graph.estimates[2] = 0.5;
    graph.edges[0][1].cost = 1.5;
    graph.edges[2][0].cost = 0.5;
    const auto lower_h = astar::search<int>(graph, 0, 3);
    check(lower_h.path == std::vector<int>({0, 2, 3}), "lower-h tie behavior");
    bool discover = false, expand = false, close = false, goal = false;
    for (const auto& event : stable.trace) {
        discover |= event.type == EventType::Discover;
        expand |= event.type == EventType::Expand;
        close |= event.type == EventType::Close;
        goal |= event.type == EventType::GoalFound;
        cost_is(event.f, event.g + event.h);
    }
    check(discover && expand && close && goal, "missing trace event");
    const auto quiet = astar::search<int>(graph, 0, 3, true, false);
    check(quiet.found && quiet.trace.empty() && quiet.trace.capacity() == 0,
          "disabled trace allocated event storage");
    cost_is(quiet.cost, lower_h.cost);
}
void test_grid() {
    GridProblem four({"......", "......", "......", "......"}, GridMovement::Four);
    GridProblem eight({"......", "......", "......", "......"}, GridMovement::Eight);
    cost_is(four.heuristic({0, 0}, {1, 1}), 2);
    cost_is(eight.heuristic({0, 0}, {1, 1}), 1.5);
    cost_is(eight.heuristic({0, 0}, {3, 2}), 4);
    cost_is(eight.heuristic({0, 0}, {0, 5}), 5);
    for (const auto& rows : std::vector<std::vector<std::string>>{
             {"....", "....", "....", "...."},
             {"....", ".##.", "....", "...."},
             {".#..", "..#.", "....", "..#."}}) {
        for (auto movement : {GridMovement::Four, GridMovement::Eight}) {
            GridProblem grid(rows, movement);
            for (int sr = 0; sr < 4; ++sr) for (int sc = 0; sc < 4; ++sc)
                for (int gr = 0; gr < 4; ++gr) for (int gc = 0; gc < 4; ++gc) {
                    Cell start{sr, sc}, goal{gr, gc};
                    if (!grid.traversable(start) || !grid.traversable(goal)) continue;
                    const auto a = astar::search_grid(grid, start, goal);
                    const auto d = astar::dijkstra_grid(grid, start, goal);
                    check(a.found == d.found, "grid reachability differs from Dijkstra");
                    check(a.found || a.path.empty(), "unreachable grid has path");
                    if (a.found) {
                        cost_is(a.cost, d.cost);
                        check(a.path.front() == start && a.path.back() == goal, "grid endpoints");
                    }
                }
        }
    }
    GridProblem corner({"#.", ".#"}, GridMovement::Eight);
    check(!astar::search_grid(corner, {0, 1}, {1, 0}).found, "diagonal passed blocked corner");
    GridProblem one_side({"#.", ".."}, GridMovement::Eight);
    const auto detour = astar::search_grid(one_side, {0, 1}, {1, 0});
    check(detour.found && detour.path == std::vector<Cell>({{0, 1}, {1, 1}, {1, 0}}),
          "diagonal cut past one blocked side cell");
    cost_is(detour.cost, 2);
    check(astar::search_grid(eight, {1, 1}, {1, 1}).path == std::vector<Cell>({{1, 1}}), "grid start=goal");
}
}
int main() {
    try {
        test_graph_basics();
        test_reopening_and_stale_entries();
        test_ties_and_events();
        test_grid();
        std::cout << "core tests passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
