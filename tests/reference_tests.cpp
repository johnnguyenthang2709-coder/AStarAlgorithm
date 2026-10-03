#include "../reference/2550216/Algo.h"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
void check(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
void close_to(double actual, double expected) {
    check(std::abs(actual - expected) < 1e-9, "unexpected path cost");
}
std::vector<std::string> collect(PathNode* head) {
    std::vector<std::string> path;
    for (PathNode* node = head; node; node = node->next) path.push_back(node->name);
    return path;
}
void release(PathNode* head) {
    while (head) { PathNode* next = head->next; delete head; head = next; }
}
void test_directed_and_relaxation() {
    double weights[100][100]{};
    int coords[100][2]{};
    coords[0][0] = 0; coords[1][0] = 1; coords[2][0] = 2;
    weights[0][1] = 2.2;
    weights[0][2] = 0.7;
    weights[2][1] = 0.7;
    PathNode* path = findDronePath(weights, coords, 0, 1, 0);
    check(path != nullptr, "weighted path missing");
    check(collect(path) == std::vector<std::string>({"(0,0)", "(2,0)", "(1,0)"}), "relaxation did not change parent/path");
    close_to(path->next->next->g, 1.4);
    release(path);
    path = findDronePath(weights, coords, 1, 0, 0);
    check(path == nullptr, "directed edge incorrectly traversed backward");
}
void test_reopening_counterexample() {
    // h(A)=0, h(B)=2 are admissible, but h(B)>cost(B,A)+h(A).
    // S->A(2), S->B(1), B->A(0.5), A->G(2): optimum 3.5.
    double weights[100][100]{};
    int coords[100][2]{};
    coords[2][0] = 2;
    weights[0][1] = 2;
    weights[0][2] = 1;
    weights[2][1] = 0.5;
    weights[1][3] = 2;
    PathNode* path = findDronePath(weights, coords, 0, 3, 3);
    check(path != nullptr, "counterexample path missing");
    close_to(path->next->next->g, 4.0); // documents the reference failure
    release(path);
}
void test_boundaries_and_ties() {
    double weights[100][100]{};
    int coords[100][2]{};
    PathNode* path = findDronePath(weights, coords, 0, 0, 0);
    check(collect(path) == std::vector<std::string>({"(0,0)"}), "reference start=goal");
    close_to(path->g, 0);
    release(path);
    check(findDronePath(weights, coords, 0, 1, 0) == nullptr, "reference unreachable");
    weights[0][1] = weights[0][2] = weights[1][3] = weights[2][3] = 1.5;
    coords[1][0] = 1; coords[2][0] = 2; coords[3][0] = 3;
    path = findDronePath(weights, coords, 0, 3, 0);
    check(collect(path) == std::vector<std::string>({"(0,0)", "(1,0)", "(3,0)"}), "reference insertion-order tie");
    close_to(path->next->next->g, 3);
    release(path);
    int grid[100][100]{};
    check(findWarehousePath(grid, 2, 2, 0, 0, 0, 0, 2) == nullptr, "reference warehouse start=goal behavior changed");
}
}

int main() {
    try {
        test_directed_and_relaxation();
        test_reopening_counterexample();
        test_boundaries_and_ties();
        std::cout << "reference tests passed (including documented defects)\n";
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
