#include "astar/edge_snapped_road_problem.hpp"
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

namespace astar {
namespace {
constexpr double pi = 3.14159265358979323846;
GeoPoint interpolate(GeoPoint a, GeoPoint b, double t) {
    return {a.lat + (b.lat - a.lat) * t, a.lon + (b.lon - a.lon) * t};
}
void validate(GeoPoint p) {
    if (!std::isfinite(p.lat) || !std::isfinite(p.lon) || std::abs(p.lat) > 90 || std::abs(p.lon) > 180)
        throw std::invalid_argument("invalid geographic coordinate");
}
std::vector<double> distances(const std::vector<GeoPoint>& geometry) {
    std::vector<double> result(geometry.size(), 0);
    for (std::size_t i = 1; i < geometry.size(); ++i)
        result[i] = result[i-1] + haversine_m(geometry[i-1], geometry[i]);
    return result;
}
EdgeSnapResult project(const RoadEdge& edge, int from, GeoPoint point) {
    const auto lengths = distances(edge.geometry);
    EdgeSnapResult best{from, edge.to, 0, std::numeric_limits<double>::infinity(), edge.geometry.front()};
    const double longitude_scale = std::cos(point.lat * pi / 180);
    for (std::size_t i = 1; i < edge.geometry.size(); ++i) {
        const auto a = edge.geometry[i-1], b = edge.geometry[i];
        const double dx = (b.lon-a.lon) * longitude_scale, dy = b.lat-a.lat;
        const double px = (point.lon-a.lon) * longitude_scale, py = point.lat-a.lat;
        const double squared = dx*dx + dy*dy;
        const double t = squared > 0 ? std::clamp((px*dx + py*dy)/squared, 0.0, 1.0) : 0;
        const auto coordinate = interpolate(a, b, t);
        const double distance = haversine_m(point, coordinate);
        if (distance < best.distance_m) {
            best.coordinate = coordinate;
            best.distance_m = distance;
            best.fraction = lengths.back() > 0 ?
                (lengths[i-1] + t*(lengths[i]-lengths[i-1]))/lengths.back() : 0;
        }
    }
    return best;
}
std::vector<EdgeSnapResult> directions(const RoadGraph& graph, const EdgeSnapResult& snap) {
    std::vector<EdgeSnapResult> result{snap};
    const auto& forward = graph.edge_between(snap.from, snap.to);
    for (const auto& neighbor : graph.neighbors(snap.to)) {
        if (neighbor.to != snap.from) continue;
        const auto& reverse = graph.edge_between(snap.to, snap.from);
        // Opposite endpoint order alone does not identify the same physical road.
        bool same_geometry = forward.geometry.size() == reverse.geometry.size();
        for (std::size_t i = 0; same_geometry && i < forward.geometry.size(); ++i)
            same_geometry = haversine_m(forward.geometry[i], reverse.geometry[reverse.geometry.size()-1-i]) < 0.01;
        if (same_geometry) result.push_back(project(reverse, snap.to, snap.coordinate));
    }
    return result;
}
int endpoint(const EdgeSnapResult& snap, int virtual_id) {
    if (snap.fraction == 0) return snap.from;
    if (snap.fraction == 1) return snap.to;
    return virtual_id;
}
}

EdgeSnapResult snap_road_edge(const RoadGraph& graph, GeoPoint point) {
    validate(point);
    EdgeSnapResult best{0, 0, 0, std::numeric_limits<double>::infinity(), point};
    bool found = false;
    for (std::size_t from = 0; from < graph.node_count(); ++from) {
        for (const auto& neighbor : graph.neighbors(static_cast<int>(from))) {
            auto candidate = project(graph.edge_between(static_cast<int>(from), neighbor.to), static_cast<int>(from), point);
            // Stable endpoint ordering also resolves reversed copies of a polyline.
            if (!found || candidate.distance_m < best.distance_m - 1e-7 ||
                (std::abs(candidate.distance_m-best.distance_m) <= 1e-7 &&
                 std::pair<int,int>{candidate.from,candidate.to} < std::pair<int,int>{best.from,best.to})) {
                best = candidate;
                found = true;
            }
        }
    }
    if (!found) throw std::invalid_argument("road graph has no edges to snap to");
    return best;
}

std::vector<GeoPoint> slice_road_geometry(const std::vector<GeoPoint>& geometry, double begin, double end) {
    if (geometry.size() < 2 || begin < 0 || end > 1 || begin > end)
        throw std::invalid_argument("invalid road geometry slice");
    const auto lengths = distances(geometry);
    const double first = begin*lengths.back(), last = end*lengths.back();
    auto at = [&](double distance) {
        if (distance <= 0) return geometry.front();
        if (distance >= lengths.back()) return geometry.back();
        auto next = std::upper_bound(lengths.begin(), lengths.end(), distance);
        const auto i = static_cast<std::size_t>(next-lengths.begin());
        return interpolate(geometry[i-1], geometry[i], (distance-lengths[i-1])/(lengths[i]-lengths[i-1]));
    };
    std::vector<GeoPoint> result{at(first)};
    for (std::size_t i = 1; i+1 < geometry.size(); ++i)
        if (lengths[i] > first && lengths[i] < last) result.push_back(geometry[i]);
    if (last > first) result.push_back(at(last));
    return result;
}

EdgeSnappedRoadProblem::EdgeSnappedRoadProblem(const RoadGraph& graph, GeoPoint start, GeoPoint goal)
    : graph_(graph), start_snap_(snap_road_edge(graph, start)), goal_snap_(snap_road_edge(graph, goal)),
      start_(0), goal_(0), scale_(graph.heuristic_scale()) {
    if (graph.node_count() > static_cast<std::size_t>(std::numeric_limits<int>::max()-2))
        throw std::invalid_argument("road graph exceeds state ID capacity");
    const int count = static_cast<int>(graph.node_count());
    start_ = endpoint(start_snap_, count);
    goal_ = endpoint(goal_snap_, count+1);
    if (start_snap_.from == goal_snap_.from && start_snap_.to == goal_snap_.to &&
        start_snap_.fraction == goal_snap_.fraction) goal_ = start_;
    const auto starts = directions(graph, start_snap_), goals = directions(graph, goal_snap_);
    if (start_ >= count)
        for (const auto& snap : starts)
            add_partial(start_, snap.to, graph.edge_between(snap.from, snap.to), snap.fraction, 1);
    if (goal_ >= count && goal_ != start_)
        for (const auto& snap : goals)
            add_partial(snap.from, goal_, graph.edge_between(snap.from, snap.to), 0, snap.fraction);
    if (start_ != goal_ && (start_ >= count || goal_ >= count))
        for (const auto& a : starts) for (const auto& b : goals)
            if (a.from == b.from && a.to == b.to && b.fraction >= a.fraction)
                add_partial(start_, goal_, graph.edge_between(a.from, a.to), a.fraction, b.fraction);
}
GeoPoint EdgeSnappedRoadProblem::point(int state) const {
    if (state == start_ && static_cast<std::size_t>(state) >= graph_.node_count()) return start_snap_.coordinate;
    if (state == goal_ && static_cast<std::size_t>(state) >= graph_.node_count()) return goal_snap_.coordinate;
    return graph_.node(state).point;
}
void EdgeSnappedRoadProblem::add_partial(int from, int to, const RoadEdge& original, double begin, double end) {
    RoadEdge edge = original;
    edge.to = to;
    edge.length_m = (end-begin)*original.length_m;
    edge.geometry = slice_road_geometry(original.geometry, begin, end);
    // Use the snapped coordinates exactly at the visual boundaries.
    edge.geometry.front() = point(from);
    edge.geometry.back() = point(to);
    const double straight = haversine_m(point(from), point(to));
    if (straight > 0) scale_ = std::min(scale_, edge.length_m/straight);
    for (auto& existing : temporary_) {
        if (existing.from == from && existing.edge.to == to) {
            if (edge.length_m < existing.edge.length_m) existing.edge = std::move(edge);
            return;
        }
    }
    temporary_.push_back({from, std::move(edge)});
}
std::vector<Edge<int>> EdgeSnappedRoadProblem::neighbors(int state) const {
    std::vector<Edge<int>> result;
    if (state >= 0 && static_cast<std::size_t>(state) < graph_.node_count()) result = graph_.neighbors(state);
    for (const auto& edge : temporary_)
        if (edge.from == state) result.push_back({edge.edge.to, edge.edge.length_m});
    return result;
}
double EdgeSnappedRoadProblem::heuristic(int state, int goal) const {
    return scale_*haversine_m(point(state), point(goal));
}
RoadRoute EdgeSnappedRoadProblem::reconstruct_route(const std::vector<int>& path) const {
    if (path.empty()) throw std::invalid_argument("cannot reconstruct an empty route");
    RoadRoute route;
    route.node_path = path;
    if (path.size() == 1) route.geometry.push_back(point(path.front()));
    for (std::size_t i = 1; i < path.size(); ++i) {
        const RoadEdge* chosen = nullptr;
        for (const auto& edge : temporary_)
            if (edge.from == path[i-1] && edge.edge.to == path[i]) chosen = &edge.edge;
        if (!chosen) chosen = &graph_.edge_between(path[i-1], path[i]);
        route.edge_path.push_back(*chosen);
        route.distance_m += chosen->length_m;
        route.geometry.insert(route.geometry.end(), chosen->geometry.begin() + (i > 1 ? 1 : 0), chosen->geometry.end());
    }
    return route;
}
}
