#include "../include/astar/road_problem.hpp"
#include "../include/third_party/json.hpp"
#include <algorithm>
#include <cmath>
#include <fstream>
#include <limits>
#include <stdexcept>

namespace astar {
namespace {
constexpr double earth_radius_m = 6371008.8;
constexpr double pi = 3.14159265358979323846;

void check_point(GeoPoint point) {
    if (!std::isfinite(point.lat) || !std::isfinite(point.lon) ||
        std::abs(point.lat) > 90 || std::abs(point.lon) > 180)
        throw std::invalid_argument("invalid latitude/longitude");
}
void check_id(int id, std::size_t count) {
    if (id < 0 || static_cast<std::size_t>(id) >= count)
        throw std::out_of_range("road node id out of range");
}
std::string display_name(const nlohmann::json& value) {
    if (value.is_null()) return {};
    if (value.is_string()) return value.get<std::string>();
    if (value.is_array()) {
        std::string joined;
        for (const auto& part : value) {
            if (!joined.empty()) joined += "; ";
            joined += part.is_string() ? part.get<std::string>() : part.dump();
        }
        return joined;
    }
    return value.dump();
}
}

double haversine_m(GeoPoint a, GeoPoint b) {
    check_point(a);
    check_point(b);
    const double lat1 = a.lat * pi / 180;
    const double lat2 = b.lat * pi / 180;
    const double dlat = (b.lat - a.lat) * pi / 180;
    const double dlon = (b.lon - a.lon) * pi / 180;
    const double x = std::pow(std::sin(dlat / 2), 2) +
                     std::cos(lat1) * std::cos(lat2) * std::pow(std::sin(dlon / 2), 2);
    return 2 * earth_radius_m * std::asin(std::sqrt(std::clamp(x, 0.0, 1.0)));
}

int RoadGraph::add_node(RoadNode node) {
    check_point(node.point);
    if (nodes_.size() >= static_cast<std::size_t>(std::numeric_limits<int>::max()))
        throw std::overflow_error("too many road nodes for int IDs");
    const int id = static_cast<int>(nodes_.size());
    nodes_.push_back(node);
    edges_.emplace_back();
    routing_edges_.emplace_back();
    return id;
}

void RoadGraph::add_edge(int from, RoadEdge edge) {
    check_id(from, nodes_.size());
    check_id(edge.to, nodes_.size());
    if (!std::isfinite(edge.length_m) || edge.length_m < 0)
        throw std::invalid_argument("invalid road edge length");
    if (edge.geometry.size() < 2)
        throw std::invalid_argument("road edge geometry needs at least two coordinates");
    for (const auto& point : edge.geometry) check_point(point);
    if (haversine_m(edge.geometry.front(), nodes_[from].point) > 0.1 ||
        haversine_m(edge.geometry.back(), nodes_[edge.to].point) > 0.1)
        throw std::invalid_argument("road edge geometry endpoints do not match its nodes");
    for (const auto& existing : edges_[from])
        if (existing.to == edge.to)
            throw std::invalid_argument("duplicate directed road edge; preprocess parallel edges");
    const double direct = haversine_m(nodes_[from].point, nodes_[edge.to].point);
    if (direct > 0)
        heuristic_scale_ = std::min(heuristic_scale_, edge.length_m / direct);
    routing_edges_[from].push_back({edge.to, edge.length_m});
    edges_[from].push_back(std::move(edge));
    edge_count_++;
}

const RoadNode& RoadGraph::node(int id) const {
    check_id(id, nodes_.size());
    return nodes_[id];
}
const std::vector<Edge<int>>& RoadGraph::neighbors(int id) const {
    check_id(id, nodes_.size());
    return routing_edges_[id];
}
const RoadEdge& RoadGraph::edge_between(int from, int to) const {
    check_id(from, nodes_.size());
    check_id(to, nodes_.size());
    for (const auto& edge : edges_[from]) if (edge.to == to) return edge;
    throw std::out_of_range("road path contains a missing directed edge");
}
SnapResult RoadGraph::snap_nearest(GeoPoint point) const {
    check_point(point);
    if (nodes_.empty()) throw std::invalid_argument("cannot snap to an empty graph");
    int best_id = 0;
    double best_distance = std::numeric_limits<double>::infinity();
    for (std::size_t id = 0; id < nodes_.size(); ++id) {
        const double distance = haversine_m(point, nodes_[id].point);
        if (distance < best_distance) {
            best_distance = distance;
            best_id = static_cast<int>(id);
        }
    }
    return {best_id, best_distance, nodes_[best_id].point};
}
int RoadGraph::nearest_node(GeoPoint point) const {
    return snap_nearest(point).node_id;
}
RoadRoute RoadGraph::reconstruct_route(const std::vector<int>& path) const {
    if (path.empty()) throw std::invalid_argument("cannot reconstruct an empty road path");
    RoadRoute route;
    route.node_path = path;
    if (path.size() == 1) {
        route.geometry.push_back(node(path.front()).point);
        return route;
    }
    for (std::size_t i = 1; i < path.size(); ++i) {
        const auto& edge = edge_between(path[i - 1], path[i]);
        route.edge_path.push_back(edge);
        route.distance_m += edge.length_m;
        const auto& segment = edge.geometry;
        const std::size_t start = route.geometry.empty() ? 0 : 1;
        route.geometry.insert(route.geometry.end(), segment.begin() + start, segment.end());
    }
    return route;
}
std::vector<GeoPoint> RoadGraph::route_geometry(const std::vector<int>& path) const {
    if (path.empty()) return {};
    return reconstruct_route(path).geometry;
}

RoadGraph RoadGraph::load_json(const std::string& filename) {
    std::ifstream input(filename);
    if (!input) throw std::runtime_error("cannot open road graph: " + filename);
    nlohmann::json data;
    input >> data;
    input >> std::ws;
    if (input.peek() != std::char_traits<char>::eof())
        throw std::invalid_argument("trailing content after road graph JSON");
    if (data.at("schema_version").get<int>() != 1)
        throw std::invalid_argument("unsupported road graph schema");
    if (!data.at("nodes").is_array() || data.at("nodes").empty() ||
        !data.at("edges").is_array() || data.at("edges").empty())
        throw std::invalid_argument("road graph needs nonempty node and edge arrays");
    RoadGraph graph;
    for (const auto& item : data.at("nodes")) {
        const int expected = static_cast<int>(graph.node_count());
        if (item.at("id").get<int>() != expected)
            throw std::invalid_argument("road nodes must use sequential dense IDs");
        graph.add_node({item.at("osm_id").get<std::int64_t>(),
                        {item.at("lat").get<double>(), item.at("lon").get<double>()}});
    }
    for (const auto& item : data.at("edges")) {
        RoadEdge edge;
        edge.to = item.at("to").get<int>();
        edge.length_m = item.at("length_m").get<double>();
        edge.osm_key = display_name(item.at("osm_key"));
        edge.osmid_json = item.at("osmid").dump();
        edge.name = display_name(item.at("name"));
        for (const auto& coord : item.at("geometry")) {
            if (!coord.is_array() || coord.size() != 2)
                throw std::invalid_argument("road geometry coordinate must be [lon,lat]");
            edge.geometry.push_back({coord.at(1).get<double>(), coord.at(0).get<double>()});
        }
        graph.add_edge(item.at("from").get<int>(), std::move(edge));
    }
    return graph;
}
} // namespace astar
