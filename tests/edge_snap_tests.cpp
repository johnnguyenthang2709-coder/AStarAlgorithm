#include "astar/edge_snapped_road_problem.hpp"
#include <algorithm>
#include <cmath>
#include <iostream>
#include <stdexcept>

using namespace astar;
namespace {
void require(bool condition, const char* message) { if (!condition) throw std::runtime_error(message); }
void close(double a, double b) { require(std::abs(a-b) < 1e-6, "cost/fraction mismatch"); }
void same(GeoPoint a, GeoPoint b) { require(haversine_m(a,b) < 1e-6, "geometry boundary mismatch"); }
RoadGraph fixture(bool reverse = false, bool curved = false) {
    RoadGraph graph;
    const GeoPoint a{10,106}, b{10,106.002}, c{10.002,106.002};
    graph.add_node({1,a}); graph.add_node({2,b}); graph.add_node({3,c});
    std::vector<GeoPoint> line{a,b};
    if (curved) line = {a,{10.001,106.001},b};
    graph.add_edge(0,{1,400,"0","1","first",line});
    graph.add_edge(1,{2,300,"1","2","second",{b,c}});
    if (reverse) {
        std::reverse(line.begin(),line.end());
        graph.add_edge(1,{0,500,"0","1","first",line});
    }
    return graph;
}
SearchResult<int> verify(const RoadGraph& graph, GeoPoint a, GeoPoint b, bool found = true) {
    const auto node_count = graph.node_count(), edge_count = graph.edge_count();
    const auto scale = graph.heuristic_scale();
    const auto original = graph.edge_between(0,graph.neighbors(0).front().to);
    EdgeSnappedRoadProblem problem(graph,a,b);
    auto astar = search<int>(problem,problem.start(),problem.goal(),true,true);
    auto dijkstra = search<int>(problem,problem.start(),problem.goal(),false,true);
    if (astar.found != found || dijkstra.found != found)
        throw std::runtime_error("direction/reachability mismatch at " + std::to_string(a.lat) + "," +
            std::to_string(a.lon) + " -> " + std::to_string(b.lat) + "," + std::to_string(b.lon));
    if (found) {
        close(astar.cost,dijkstra.cost);
        const auto route = problem.reconstruct_route(astar.path);
        close(route.distance_m,astar.cost);
        same(route.geometry.front(),problem.start_snap().coordinate);
        same(route.geometry.back(),problem.goal_snap().coordinate);
    }
    require(graph.node_count() == node_count && graph.edge_count() == edge_count &&
            graph.heuristic_scale() == scale, "base graph mutated");
    const auto& after = graph.edge_between(0,original.to);
    require(after.length_m == original.length_m && after.geometry.size() == original.geometry.size(), "base edge mutated");
    for (std::size_t i = 0; i < original.geometry.size(); ++i) same(after.geometry[i],original.geometry[i]);
    return astar;
}
}
int main(int argc, char** argv) {
    try {
        const GeoPoint early{10,106.0005}, late{10,106.0015}, other{10.001,106.002};
        auto one_way = fixture();
        const auto snap = snap_road_edge(one_way,{10.0001,106.0005});
        require(snap.from == 0 && snap.to == 1, "nearest polyline mismatch");
        close(snap.fraction,.25); same(snap.coordinate,early);
        close(snap.distance_m,haversine_m({10.0001,106.0005},early));
        close(snap.fraction*400+(1-snap.fraction)*400,400);
        auto direct = verify(one_way,early,late);
        close(direct.cost,200); require(direct.path.size() == 2, "same edge detoured through intersection");
        close(verify(one_way,early,other).cost,450);
        verify(one_way,late,early,false);
        verify(one_way,other,early,false);
        close(verify(one_way,{10,106},early).cost,100);
        close(verify(one_way,late,{10,106.002}).cost,100);
        auto zero = verify(one_way,early,early); close(zero.cost,0);
        require(zero.path.size() == 1, "same point should have a singleton path");
        auto two_way = fixture(true);
        close(verify(two_way,late,early).cost,250); // reverse has its own 500 m cost
        close(verify(two_way,late,{10,106}).cost,375);
        close(verify(two_way,{10,106.002},early).cost,375);
        auto curve = fixture(true,true);
        const GeoPoint first{10.0005,106.0005}, last{10.0005,106.0015};
        const auto curved_snap = snap_road_edge(curve,{10.001,106.001});
        same(curved_snap.coordinate,{10.001,106.001}); close(curved_snap.fraction,.5);
        const auto result = verify(curve,first,last);
        EdgeSnappedRoadProblem curved_problem(curve,first,last);
        const auto route = curved_problem.reconstruct_route(result.path);
        require(route.geometry.size() == 3, "curved slice lost bend");
        same(route.geometry[1],{10.001,106.001}); close(result.cost,200);
        verify(curve,last,first);
        // An edge with reversed endpoints but a different physical geometry is not a reverse road.
        auto different = fixture();
        different.add_edge(1,{0,500,"x","9","different",{{10,106.002},{9.999,106.001},{10,106}}});
        close(verify(different,late,early).cost,700); // legal detour; no false reverse shortcut
        // Short exported costs still need an admissible Haversine scale after splitting.
        RoadGraph cheap;
        cheap.add_node({1,{10,106}}); cheap.add_node({2,{10,106.002}});
        cheap.add_edge(0,{1,100,"0","1","cheap curve",{{10,106},{10.001,106.001},{10,106.002}}});
        verify(cheap,first,last);
        if (argc > 1) {
            const auto real = RoadGraph::load_json(argv[1]);
            int checked = 0;
            for (std::size_t from = 0; from < real.node_count() && checked < 12; ++from) {
                if (real.neighbors(static_cast<int>(from)).empty()) continue;
                const auto& edge = real.edge_between(static_cast<int>(from),real.neighbors(static_cast<int>(from)).front().to);
                auto a = slice_road_geometry(edge.geometry,.25,.25).front();
                auto b = slice_road_geometry(edge.geometry,.75,.75).front();
                verify(real,a,b);
                ++checked;
            }
            require(checked == 12, "real road checks missing");
        }
        std::cout << "edge snapping checks passed\n";
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
