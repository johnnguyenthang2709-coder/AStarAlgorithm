// Search-only benchmark of the existing C++ RoadProblem and shared search core.
// Reads frozen pair IDs from benchmark-manifest.json; it does not alter routing.
#include "astar/road_problem.hpp"
#include "third_party/json.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;
using Result = astar::SearchResult<int>;

static double median(std::vector<double> samples) {
    std::sort(samples.begin(), samples.end());
    return samples[samples.size() / 2];
}

static double timed_batch(const astar::RoadProblem& problem, int start, int goal,
                          bool heuristic, int calls, double expected, double& checksum) {
    const auto begun = Clock::now();
    for (int i = 0; i < calls; ++i) {
        auto result = astar::search<int>(problem, start, goal, heuristic, false);
        if (!result.found || std::abs(result.cost - expected) > 1e-6)
            throw std::runtime_error("timed search changed reachability or cost");
        checksum += result.cost;
    }
    const auto elapsed = std::chrono::duration<double, std::micro>(Clock::now() - begun).count();
    return elapsed / calls;
}

static void write_row(std::ofstream& output, int id, const std::string& stratum,
                      int start, int goal, double offline, const char* algorithm,
                      const Result& result, int calls, const std::vector<double>& samples) {
    output << id << ',' << stratum << ',' << start << ',' << goal << ',' << offline << ','
           << algorithm << ',' << result.found << ',' << result.cost << ',' << result.path.size() << ','
           << result.expanded_nodes << ',' << result.generated_nodes << ','
           << result.unique_discovered_states << ',' << result.examined_edges << ','
           << result.relaxed_edges << ',' << calls << ',' << samples.size() << ','
           << median(samples) << ',' << *std::min_element(samples.begin(), samples.end()) << ','
           << *std::max_element(samples.begin(), samples.end()) << '\n';
}

int main(int argc, char** argv) {
    if (argc != 4) {
        std::cerr << "usage: academic_road_benchmark graph.json benchmark-manifest.json output.csv\n";
        return 2;
    }
    try {
        std::ifstream input(argv[2]);
        if (!input) throw std::runtime_error("cannot open manifest");
        nlohmann::json manifest = nlohmann::json::parse(input);
        const auto graph = astar::RoadGraph::load_json(argv[1]);
        if (graph.node_count() != manifest.at("road").at("graph_nodes").get<std::size_t>() ||
            graph.edge_count() != manifest.at("road").at("graph_directed_edges").get<std::size_t>())
            throw std::runtime_error("graph count differs from frozen manifest");
        const astar::RoadProblem problem(graph);
        std::ofstream output(argv[3]);
        if (!output) throw std::runtime_error("cannot open output CSV");
        output << "pair_id,stratum,start,goal,offline_cost_m,algorithm,found,cost_m,path_nodes,"
                  "expanded_nodes,generated_nodes,unique_discovered,examined_edges,relaxed_edges,"
                  "batch_calls,repeated_batches,median_search_us,min_search_us,max_search_us\n";
        output << std::setprecision(17);
        const auto& timing = manifest.at("road_timing");
        const int batches = timing.at("batches").get<int>();
        int id = 0;
        double checksum = 0;
        for (const std::string stratum : {"short", "medium", "long"}) {
            const int calls = timing.at("batch_calls_by_stratum").at(stratum).get<int>();
            for (const auto& pair : manifest.at("road").at("selected_pairs").at(stratum)) {
                const int start = pair.at("start").get<int>();
                const int goal = pair.at("goal").get<int>();
                const double offline = pair.at("offline_distance_m").get<double>();
                const Result a = astar::search<int>(problem, start, goal, true, false);
                const Result d = astar::search<int>(problem, start, goal, false, false);
                if (!a.found || !d.found || std::abs(a.cost - d.cost) > 1e-6 ||
                    std::abs(a.cost - offline) > 1e-6)
                    throw std::runtime_error("A*/Dijkstra/offline cost mismatch at pair " + std::to_string(id));
                std::vector<double> a_times, d_times;
                a_times.reserve(batches);
                d_times.reserve(batches);
                for (int batch = 0; batch < batches; ++batch) {
                    if (batch % 2 == 0) {
                        a_times.push_back(timed_batch(problem, start, goal, true, calls, offline, checksum));
                        d_times.push_back(timed_batch(problem, start, goal, false, calls, offline, checksum));
                    } else {
                        d_times.push_back(timed_batch(problem, start, goal, false, calls, offline, checksum));
                        a_times.push_back(timed_batch(problem, start, goal, true, calls, offline, checksum));
                    }
                }
                write_row(output, id, stratum, start, goal, offline, "astar", a, calls, a_times);
                write_row(output, id, stratum, start, goal, offline, "dijkstra", d, calls, d_times);
                ++id;
            }
        }
        std::cerr << "benchmarked " << id << " directed pairs; checksum=" << checksum << '\n';
        return id == 180 ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "benchmark failed: " << error.what() << '\n';
        return 1;
    }
}
