#pragma once

#include "search.hpp"
#include <cstdint>
#include <string>
#include <vector>

namespace astar {

struct GeoPoint {
    double lat;
    double lon;
};

struct RoadNode {
    std::int64_t osm_id;
    GeoPoint point;
};

struct RoadEdge {
    int to;
    double length_m;
    std::string osm_key;
    std::string osmid_json;
    std::string name;
    std::vector<GeoPoint> geometry;
};

struct SnapResult {
    int node_id;
    double distance_m;
    GeoPoint coordinate;
};

struct RoadRoute {
    std::vector<int> node_path;
    std::vector<RoadEdge> edge_path;
    double distance_m = 0;
    std::vector<GeoPoint> geometry;
};

double haversine_m(GeoPoint a, GeoPoint b);

class RoadGraph {
public:
    static RoadGraph load_json(const std::string& filename);
    int add_node(RoadNode node);
    void add_edge(int from, RoadEdge edge);
    const RoadNode& node(int id) const;
    const std::vector<Edge<int>>& neighbors(int id) const;
    const RoadEdge& edge_between(int from, int to) const;
    SnapResult snap_nearest(GeoPoint point) const;
    int nearest_node(GeoPoint point) const;
    RoadRoute reconstruct_route(const std::vector<int>& path) const;
    std::vector<GeoPoint> route_geometry(const std::vector<int>& path) const;
    std::size_t node_count() const { return nodes_.size(); }
    std::size_t edge_count() const { return edge_count_; }
    double heuristic_scale() const { return heuristic_scale_; }

private:
    std::vector<RoadNode> nodes_;
    std::vector<std::vector<RoadEdge>> edges_;
    std::vector<std::vector<Edge<int>>> routing_edges_;
    std::size_t edge_count_ = 0;
    double heuristic_scale_ = 1.0;
};

class RoadProblem {
public:
    explicit RoadProblem(const RoadGraph& graph) : graph_(graph) {}
    const std::vector<Edge<int>>& neighbors(int state) const { return graph_.neighbors(state); }
    double heuristic(int state, int goal) const {
        return graph_.heuristic_scale() * haversine_m(graph_.node(state).point, graph_.node(goal).point);
    }
    bool is_goal(int state, int goal) const { return state == goal; }

private:
    const RoadGraph& graph_;
};
} // namespace astar
