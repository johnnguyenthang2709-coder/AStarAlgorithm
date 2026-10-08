#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "astar/grid_problem.hpp"
#include "astar/road_problem.hpp"
#include "astar/edge_snapped_road_problem.hpp"
#include <cmath>
#include <stdexcept>

namespace py = pybind11;

namespace {
class VisibilityGraphProblem {
public:
    VisibilityGraphProblem(const std::vector<std::pair<double, double>>& points,
                           const std::vector<std::pair<int, int>>& links)
        : points_(points), adjacency_(points.size()) {
        if (points_.empty()) throw std::invalid_argument("visibility graph must have nodes");
        for (const auto& point : points_)
            if (!std::isfinite(point.first) || !std::isfinite(point.second))
                throw std::invalid_argument("visibility graph coordinates must be finite");
        for (const auto& link : links) {
            validate(link.first);
            validate(link.second);
            if (link.first == link.second) continue;
            const double cost = distance(link.first, link.second);
            if (!(cost > 0) || !std::isfinite(cost))
                throw std::invalid_argument("visibility graph links need distinct finite positions");
            adjacency_[link.first].push_back({link.second, cost});
            adjacency_[link.second].push_back({link.first, cost});
        }
    }
    void validate(int node) const {
        if (node < 0 || static_cast<std::size_t>(node) >= points_.size())
            throw std::invalid_argument("visibility graph node outside range");
    }
    std::vector<astar::Edge<int>> neighbors(int node) const {
        validate(node);
        return adjacency_[node];
    }
    double heuristic(int node, int goal) const { return distance(node, goal); }
    bool is_goal(int node, int goal) const { return node == goal; }
private:
    double distance(int a, int b) const {
        return std::hypot(points_[a].first - points_[b].first,
                          points_[a].second - points_[b].second);
    }
    std::vector<std::pair<double, double>> points_;
    std::vector<std::vector<astar::Edge<int>>> adjacency_;
};

class RoadEngine {
public:
    explicit RoadEngine(const std::string& path) : graph_(astar::RoadGraph::load_json(path)) {}
    const astar::RoadGraph& graph() const { return graph_; }
private:
    astar::RoadGraph graph_;
};

py::dict point_dict(astar::GeoPoint point) {
    py::dict value;
    value["lat"] = point.lat;
    value["lon"] = point.lon;
    return value;
}
py::object state_value(int state) { return py::int_(state); }
py::object state_value(astar::Cell state) {
    py::dict value;
    value["row"] = state.row;
    value["col"] = state.col;
    return value;
}
const char* event_name(astar::EventType type) {
    switch (type) {
        case astar::EventType::Discover: return "DISCOVER";
        case astar::EventType::Expand: return "EXPAND";
        case astar::EventType::Update: return "UPDATE";
        case astar::EventType::Close: return "CLOSE";
        case astar::EventType::GoalFound: return "GOAL_FOUND";
    }
    throw std::logic_error("unknown search event");
}
template <class State> py::dict metrics_dict(const astar::SearchResult<State>& result) {
    py::dict value;
    value["expanded_nodes"] = result.expanded_nodes;
    value["unique_expanded_states"] = result.unique_expanded_states;
    value["generated_nodes"] = result.generated_nodes;
    value["unique_discovered_states"] = result.unique_discovered_states;
    value["relaxed_edges"] = result.relaxed_edges;
    value["examined_edges"] = result.examined_edges;
    return value;
}
template <class State> py::list trace_list(const astar::SearchResult<State>& result) {
    py::list output;
    for (const auto& event : result.trace) {
        py::dict value;
        value["type"] = event_name(event.type);
        value["state"] = state_value(event.state);
        value["parent"] = event.parent ? state_value(*event.parent) : py::none();
        value["g"] = event.g;
        value["h"] = event.h;
        value["f"] = event.f;
        output.append(value);
    }
    return output;
}
py::dict snap_dict(const astar::RoadGraph& graph, double lat, double lon) {
    const auto snap = graph.snap_nearest({lat, lon});
    py::dict value = point_dict(snap.coordinate);
    value["node_id"] = snap.node_id;
    value["osm_id"] = graph.node(snap.node_id).osm_id;
    value["snap_distance_m"] = snap.distance_m;
    return value;
}
template <class RoadView> py::dict road_result(const RoadView& graph,
                     const astar::SearchResult<int>& result) {
    py::dict output;
    output["found"] = result.found;
    output["metrics"] = metrics_dict(result);
    output["trace"] = trace_list(result);
    if (!result.found) {
        output["route"] = py::none();
        return output;
    }
    const auto route = graph.reconstruct_route(result.path);
    py::dict route_data;
    route_data["cost_m"] = result.cost;
    route_data["node_path"] = result.path;
    py::list edges;
    for (std::size_t i = 0; i < route.edge_path.size(); ++i) {
        const auto& edge = route.edge_path[i];
        py::dict item;
        item["from_node"] = result.path[i];
        item["to_node"] = edge.to;
        item["length_m"] = edge.length_m;
        item["osm_key"] = edge.osm_key;
        item["osmid"] = py::module_::import("json").attr("loads")(edge.osmid_json);
        item["name"] = edge.name;
        edges.append(item);
    }
    route_data["edge_path"] = edges;
    py::list geometry;
    for (const auto& point : route.geometry) geometry.append(point_dict(point));
    route_data["geometry"] = geometry;
    output["route"] = route_data;
    return output;
}
py::dict grid_result(const astar::SearchResult<astar::Cell>& result) {
    py::dict output;
    output["found"] = result.found;
    output["metrics"] = metrics_dict(result);
    output["trace"] = trace_list(result);
    if (!result.found) {
        output["cost"] = py::none();
        output["path"] = py::list();
    } else {
        output["cost"] = result.cost;
        py::list path;
        for (const auto& cell : result.path) path.append(state_value(cell));
        output["path"] = path;
    }
    return output;
}
py::dict visibility_result(const astar::SearchResult<int>& result) {
    py::dict output;
    output["found"] = result.found;
    output["path"] = result.path;
    output["cost"] = result.found ? py::cast(result.cost) : py::none();
    output["metrics"] = metrics_dict(result);
    return output;
}
bool use_astar(const std::string& algorithm) {
    if (algorithm == "astar") return true;
    if (algorithm == "dijkstra") return false;
    throw std::invalid_argument("unsupported algorithm");
}
py::dict run_road(const RoadEngine& engine, int start, int goal,
                  const std::string& algorithm, bool trace) {
    const auto& graph = engine.graph();
    (void)graph.node(start);
    (void)graph.node(goal);
    const astar::RoadProblem problem(graph);
    const auto result = astar::search<int>(problem, start, goal, use_astar(algorithm), trace);
    return road_result(graph, result);
}
py::dict edge_snap_dict(const astar::RoadGraph& graph, const astar::EdgeSnapResult& snap) {
    auto value = point_dict(snap.coordinate);
    value["from_node"] = snap.from;
    value["to_node"] = snap.to;
    value["fraction"] = snap.fraction;
    value["snap_distance_m"] = snap.distance_m;
    const int endpoint = snap.fraction == 0 ? snap.from : snap.fraction == 1 ? snap.to : -1;
    value["node_id"] = endpoint >= 0 ? py::cast(endpoint) : py::none();
    value["osm_id"] = endpoint >= 0 ? py::cast(graph.node(endpoint).osm_id) : py::none();
    return value;
}
py::dict coordinate_result(const astar::RoadGraph& graph, const astar::EdgeSnappedRoadProblem& problem,
                           const astar::SearchResult<int>& result) {
    auto output = road_result(problem, result);
    py::list positions;
    for (int id : {problem.start(), problem.goal()}) {
        if (static_cast<std::size_t>(id) < graph.node_count()) continue;
        if (id == problem.goal() && id == problem.start() && py::len(positions)) continue;
        auto item = point_dict(problem.point(id));
        item["node_id"] = id;
        positions.append(item);
    }
    output["trace_nodes"] = positions;
    return output;
}
py::dict run_coordinates(const RoadEngine& engine, std::pair<double,double> start,
                         std::pair<double,double> goal, const std::string& algorithm, bool trace, bool compare) {
    const auto& graph = engine.graph();
    const astar::EdgeSnappedRoadProblem problem(graph, {start.first,start.second}, {goal.first,goal.second});
    const auto a = astar::search<int>(problem, problem.start(), problem.goal(), compare || use_astar(algorithm), trace);
    py::dict output;
    if (compare) {
        const auto d = astar::search<int>(problem, problem.start(), problem.goal(), false, trace);
        output["same_optimal_cost"] = a.found == d.found && (!a.found || std::abs(a.cost-d.cost) <= 1e-6);
        output["cost_difference_m"] = a.found && d.found ? py::cast(std::abs(a.cost-d.cost)) : py::none();
        output["astar"] = coordinate_result(graph, problem, a);
        output["dijkstra"] = coordinate_result(graph, problem, d);
    } else output = coordinate_result(graph, problem, a);
    output["start_snap"] = edge_snap_dict(graph, problem.start_snap());
    output["goal_snap"] = edge_snap_dict(graph, problem.goal_snap());
    return output;
}
py::dict run_grid(const std::vector<std::vector<int>>& cells,
                  std::pair<int, int> start, std::pair<int, int> goal,
                  int movement, const std::string& algorithm, bool trace) {
    if (movement != 4 && movement != 8) throw std::invalid_argument("movement must be 4 or 8");
    if (cells.empty()) throw std::invalid_argument("grid must be nonempty");
    std::vector<std::string> rows;
    rows.reserve(cells.size());
    for (const auto& row : cells) {
        std::string tiles;
        for (int value : row) {
            if (value != 0 && value != 1) throw std::invalid_argument("grid values must be 0 or 1");
            tiles += value == 0 ? '.' : '#';
        }
        rows.push_back(std::move(tiles));
    }
    const astar::GridProblem problem(std::move(rows), movement == 4 ?
        astar::GridMovement::Four : astar::GridMovement::Eight);
    const astar::Cell from{start.first, start.second};
    const astar::Cell to{goal.first, goal.second};
    problem.validate_endpoint(from);
    problem.validate_endpoint(to);
    const auto result = astar::search<astar::Cell, astar::GridProblem, astar::CellHash>(
        problem, from, to, use_astar(algorithm), trace);
    return grid_result(result);
}
}

PYBIND11_MODULE(astar_core, module) {
    module.doc() = "C++ A* and Dijkstra road/grid operations";
    py::class_<RoadEngine>(module, "RoadEngine")
        .def(py::init<const std::string&>(), py::arg("graph_path"))
        .def_property_readonly("node_count", [](const RoadEngine& e) { return e.graph().node_count(); })
        .def_property_readonly("edge_count", [](const RoadEngine& e) { return e.graph().edge_count(); });
    module.def("road_snap", [](const RoadEngine& e, double lat, double lon) {
        return snap_dict(e.graph(), lat, lon);
    }, py::arg("engine"), py::arg("lat"), py::arg("lon"));
    module.def("road_edge_snap", [](const RoadEngine& e, double lat, double lon) {
        return edge_snap_dict(e.graph(), astar::snap_road_edge(e.graph(), {lat,lon}));
    }, py::arg("engine"), py::arg("lat"), py::arg("lon"));
    module.def("road_search_coordinates", [](const RoadEngine& e, std::pair<double,double> start,
                                             std::pair<double,double> goal, const std::string& algorithm, bool trace) {
        return run_coordinates(e,start,goal,algorithm,trace,false);
    }, py::arg("engine"), py::arg("start"), py::arg("goal"), py::arg("algorithm") = "astar", py::arg("trace") = false);
    module.def("road_compare_coordinates", [](const RoadEngine& e, std::pair<double,double> start,
                                              std::pair<double,double> goal, bool trace) {
        return run_coordinates(e,start,goal,"astar",trace,true);
    }, py::arg("engine"), py::arg("start"), py::arg("goal"), py::arg("trace") = false);
    module.def("road_nodes", [](const RoadEngine& e) {
        py::list nodes;
        const auto& graph = e.graph();
        for (std::size_t id = 0; id < graph.node_count(); ++id) {
            py::dict item = point_dict(graph.node(static_cast<int>(id)).point);
            item["node_id"] = id;
            nodes.append(item);
        }
        return nodes;
    }, py::arg("engine"));
    module.def("road_search", &run_road, py::arg("engine"), py::arg("start_node"),
               py::arg("goal_node"), py::arg("algorithm") = "astar", py::arg("trace") = false);
    module.def("road_compare", [](const RoadEngine& engine, int start, int goal, bool trace) {
        const auto& graph = engine.graph();
        (void)graph.node(start);
        (void)graph.node(goal);
        const astar::RoadProblem problem(graph);
        const auto a = astar::search<int>(problem, start, goal, true, trace);
        const auto d = astar::search<int>(problem, start, goal, false, trace);
        py::dict output;
        const bool equal = a.found == d.found && (!a.found || std::abs(a.cost - d.cost) <= 1e-6);
        output["same_optimal_cost"] = equal;
        output["cost_difference_m"] = a.found && d.found ? py::cast(std::abs(a.cost - d.cost)) : py::none();
        output["astar"] = road_result(graph, a);
        output["dijkstra"] = road_result(graph, d);
        return output;
    }, py::arg("engine"), py::arg("start_node"), py::arg("goal_node"), py::arg("trace") = false);
    module.def("grid_search", &run_grid, py::arg("grid"), py::arg("start"), py::arg("goal"),
               py::arg("movement") = 8, py::arg("algorithm") = "astar", py::arg("trace") = false);
    module.def("visibility_search", [](const std::vector<std::pair<double, double>>& points,
                                        const std::vector<std::pair<int, int>>& links,
                                        int start, int goal, const std::string& algorithm) {
        const VisibilityGraphProblem problem(points, links);
        problem.validate(start);
        problem.validate(goal);
        return visibility_result(astar::search<int>(problem, start, goal, use_astar(algorithm), false));
    }, py::arg("points"), py::arg("links"), py::arg("start"), py::arg("goal"),
       py::arg("algorithm") = "astar");
}
