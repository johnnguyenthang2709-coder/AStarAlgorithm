#include "../include/astar/road_problem.hpp"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>

namespace {
void check(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
void near(double actual, double expected, double tolerance = 1e-6) {
    check(std::abs(actual - expected) <= tolerance, "road cost mismatch");
}
bool compare(const astar::RoadGraph& graph, int start, int goal, bool report = false) {
    astar::RoadProblem problem(graph);
    const auto a = astar::search<int>(problem, start, goal);
    const auto d = astar::dijkstra<int>(problem, start, goal);
    check(a.found == d.found, "road A*/Dijkstra reachability mismatch");
    if (!a.found) {
        check(a.path.empty() && std::isinf(a.cost), "unreachable road result");
        return false;
    }
    near(a.cost, d.cost);
    check(a.path.front() == start && a.path.back() == goal, "road path endpoints");
    const auto route = graph.reconstruct_route(a.path);
    check(route.node_path == a.path && route.edge_path.size() + 1 == a.path.size(),
          "road edge reconstruction mismatch");
    near(route.distance_m, a.cost);
    double sum = 0;
    for (const auto& edge : route.edge_path) sum += edge.length_m;
    near(sum, a.cost);
    const auto& geometry = route.geometry;
    check(!geometry.empty(), "missing route geometry");
    near(astar::haversine_m(geometry.front(), graph.node(start).point), 0, 0.01);
    near(astar::haversine_m(geometry.back(), graph.node(goal).point), 0, 0.01);
    if (report) {
        std::cout << start << ',' << goal << ',' << std::setprecision(12) << a.cost << ','
                  << a.expanded_nodes << ',' << a.unique_expanded_states << ','
                  << a.generated_nodes << ',' << a.unique_discovered_states << ','
                  << d.expanded_nodes << ',' << d.unique_expanded_states << ','
                  << d.generated_nodes << ',' << d.unique_discovered_states << ','
                  << std::abs(a.cost - d.cost) << '\n';
    }
    return true;
}
void synthetic() {
    astar::RoadGraph graph;
    const astar::GeoPoint p0{10, 106}, p1{10, 106.001}, p2{10, 106.002};
    graph.add_node({100, p0});
    graph.add_node({200, p1});
    graph.add_node({300, p2});
    graph.add_edge(0, {1, 120, "0", "101", "First", {p0, {10.0001, 106.0005}, p1}});
    graph.add_edge(1, {2, 120, "0", "102", "Second", {p1, p2}});
    graph.add_edge(0, {2, 300, "0", "103", "Direct", {p0, p2}});
    check(graph.node_count() == 3 && graph.edge_count() == 3, "synthetic graph size");
    const auto snap = graph.snap_nearest({10, 106.0011});
    check(snap.node_id == 1 && snap.coordinate.lat == p1.lat &&
          snap.coordinate.lon == p1.lon, "nearest-node snapping");
    near(snap.distance_m, astar::haversine_m({10, 106.0011}, p1));
    check(graph.nearest_node({10, 106.0011}) == snap.node_id, "nearest-node ID helper");
    check(graph.neighbors(1).size() == 1 && graph.neighbors(2).empty(), "directionality");
    compare(graph, 0, 2);
    compare(graph, 2, 0);
    compare(graph, 1, 1);
    astar::RoadProblem problem(graph);
    const auto route = astar::search<int>(problem, 0, 2);
    check(route.path == std::vector<int>({0, 1, 2}), "synthetic shortest path");
    near(route.cost, 240);
    const auto reconstructed = graph.reconstruct_route(route.path);
    check(reconstructed.geometry.size() == 4 && reconstructed.edge_path.size() == 2,
          "selected-edge geometry lost");
    near(reconstructed.distance_m, route.cost);
    check(problem.heuristic(0, 2) <= route.cost + 1e-9, "heuristic overestimates path");
    near(astar::haversine_m(p0, p0), 0);
    near(astar::haversine_m({0, 0}, {0, 1}), 111195.080234, 0.001);
    near(astar::haversine_m({0, 0}, {1, 0}), 111195.080234, 0.001);
    near(astar::haversine_m({90, 0}, {-90, 0}), 20015114.442, 0.01);
    bool rejected = false;
    try { graph.add_edge(2, {0, -1, "0", "", "", {p2, p0}}); }
    catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "negative edge length accepted");
    rejected = false;
    try { graph.add_edge(2, {0, std::numeric_limits<double>::infinity(), "0", "", "", {p2, p0}}); }
    catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "nonfinite edge length accepted");
    rejected = false;
    try { graph.add_edge(2, {5, 1, "0", "", "", {p2, p0}}); }
    catch (const std::out_of_range&) { rejected = true; }
    check(rejected, "invalid node index accepted");
    rejected = false;
    try { graph.add_node({400, {std::numeric_limits<double>::quiet_NaN(), 106}}); }
    catch (const std::invalid_argument&) { rejected = true; }
    check(rejected, "NaN coordinate accepted");
    for (const char* filename : {"tests/data/invalid_road.json", "tests/data/malformed_road.json"}) {
        rejected = false;
        try { (void)astar::RoadGraph::load_json(filename); }
        catch (const std::exception&) { rejected = true; }
        check(rejected, "malformed road graph file accepted");
    }
}
void real_graph(const char* filename) {
    const auto graph = astar::RoadGraph::load_json(filename);
    check(graph.node_count() > 100 && graph.edge_count() > 100, "road export too small");
    const int n = static_cast<int>(graph.node_count());
    const std::vector<int> samples = {0, n / 5, 2 * n / 5, 3 * n / 5, 4 * n / 5, n - 1};
    constexpr double tolerance_m = 0.01;
    std::size_t edge_checks = 0, direct_violations = 0, consistency_violations = 0;
    double max_direct_gap = -std::numeric_limits<double>::infinity();
    double max_consistency_gap = -std::numeric_limits<double>::infinity();
    for (int from = 0; from < n; ++from) {
        for (const auto& edge : graph.neighbors(from)) {
            ++edge_checks;
            const double direct = astar::haversine_m(graph.node(from).point,
                                                       graph.node(edge.to).point);
            const double direct_gap = direct - edge.cost;
            max_direct_gap = std::max(max_direct_gap, direct_gap);
            if (direct_gap > tolerance_m) ++direct_violations;
            for (int goal : samples) {
                const double hu = astar::haversine_m(graph.node(from).point, graph.node(goal).point);
                const double hv = astar::haversine_m(graph.node(edge.to).point, graph.node(goal).point);
                const double gap = hu - edge.cost - hv;
                max_consistency_gap = std::max(max_consistency_gap, gap);
                if (gap > tolerance_m) ++consistency_violations;
            }
        }
    }
    std::cout << "heuristic_validation,edges=" << edge_checks
              << ",goals=" << samples.size() << ",tolerance_m=" << tolerance_m
              << ",direct_violations=" << direct_violations
              << ",max_direct_gap_m=" << max_direct_gap
              << ",consistency_violations=" << consistency_violations
              << ",max_consistency_gap_m=" << max_consistency_gap << '\n';
    check(direct_violations == 0 && consistency_violations == 0,
          "actual road data violates raw Haversine lower bound/consistency");
    std::cout << "start,goal,cost_m,astar_expansions,astar_unique_expanded,astar_queue_pushes,"
                 "astar_unique_discovered,dijkstra_expansions,dijkstra_unique_expanded,"
                 "dijkstra_queue_pushes,dijkstra_unique_discovered,cost_difference_m\n";
    int reachable = 0, unreachable = 0;
    for (int start : samples) for (int goal : samples) {
        if (compare(graph, start, goal, true)) ++reachable;
        else ++unreachable;
    }
    check(reachable >= 10, "too few reachable road comparison pairs");
    std::cout << "comparison_summary,reachable=" << reachable << ",unreachable=" << unreachable << '\n';
    std::cout << "real graph: " << graph.node_count() << " nodes, "
              << graph.edge_count() << " directed edges, heuristic scale "
              << graph.heuristic_scale() << '\n';
}
}

int main(int argc, char** argv) {
    try {
        synthetic();
        if (argc > 1) real_graph(argv[1]);
        std::cout << "road tests passed\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
