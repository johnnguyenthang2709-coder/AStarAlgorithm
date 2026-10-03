#pragma once
#include "road_problem.hpp"

namespace astar {
struct EdgeSnapResult {
    int from;
    int to;
    double fraction;
    double distance_m;
    GeoPoint coordinate;
};

EdgeSnapResult snap_road_edge(const RoadGraph& graph, GeoPoint point);
std::vector<GeoPoint> slice_road_geometry(const std::vector<GeoPoint>& geometry,
                                        double begin, double end);

// A tiny, immutable-base overlay for one coordinate-to-coordinate request.
class EdgeSnappedRoadProblem {
public:
    EdgeSnappedRoadProblem(const RoadGraph& graph, GeoPoint start, GeoPoint goal);
    std::vector<Edge<int>> neighbors(int state) const;
    double heuristic(int state, int goal) const;
    bool is_goal(int state, int goal) const { return state == goal; }
    GeoPoint point(int state) const;
    RoadRoute reconstruct_route(const std::vector<int>& path) const;
    int start() const { return start_; }
    int goal() const { return goal_; }
    const EdgeSnapResult& start_snap() const { return start_snap_; }
    const EdgeSnapResult& goal_snap() const { return goal_snap_; }
private:
    struct TemporaryEdge { int from; RoadEdge edge; };
    void add_partial(int from, int to, const RoadEdge& edge, double begin, double end);
    const RoadGraph& graph_;
    EdgeSnapResult start_snap_, goal_snap_;
    int start_, goal_;
    double scale_;
    std::vector<TemporaryEdge> temporary_;
};
}
