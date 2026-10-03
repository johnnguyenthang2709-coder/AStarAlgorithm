#pragma once

#include "search.hpp"
#include <cstdlib>
#include <string>
#include <vector>

namespace astar {

struct Cell {
    int row;
    int col;
    bool operator==(const Cell& other) const {
        return row == other.row && col == other.col;
    }
};

struct CellHash {
    std::size_t operator()(Cell c) const noexcept {
        const std::size_t a = std::hash<int>{}(c.row);
        const std::size_t b = std::hash<int>{}(c.col);
        return a ^ (b + 0x9e3779b97f4a7c15ULL + (a << 6) + (a >> 2));
    }
};

enum class GridMovement { Four, Eight };

class GridProblem {
public:
    // '.' is traversable; '#' is blocked. Diagonals require both side cells free.
    explicit GridProblem(std::vector<std::string> rows,
                         GridMovement movement = GridMovement::Eight)
        : rows_(std::move(rows)), movement_(movement) {
        if (rows_.empty() || rows_[0].empty())
            throw std::invalid_argument("grid must be nonempty");
        for (const auto& row : rows_) {
            if (row.size() != rows_[0].size())
                throw std::invalid_argument("grid must be rectangular");
            for (char tile : row)
                if (tile != '.' && tile != '#')
                    throw std::invalid_argument("grid tiles must be '.' or '#'");
        }
    }

    bool traversable(Cell cell) const {
        return cell.row >= 0 && cell.col >= 0 &&
               static_cast<std::size_t>(cell.row) < rows_.size() &&
               static_cast<std::size_t>(cell.col) < rows_[0].size() &&
               rows_[cell.row][cell.col] == '.';
    }
    void validate_endpoint(Cell cell) const {
        if (!traversable(cell)) throw std::invalid_argument("start and goal must be traversable grid cells");
    }
    std::vector<Edge<Cell>> neighbors(Cell from) const {
        validate_endpoint(from);
        static constexpr int dr[8] = {-1, 1, 0, 0, -1, -1, 1, 1};
        static constexpr int dc[8] = {0, 0, -1, 1, -1, 1, -1, 1};
        std::vector<Edge<Cell>> out;
        for (int i = 0; i < (movement_ == GridMovement::Four ? 4 : 8); ++i) {
            const Cell next{from.row + dr[i], from.col + dc[i]};
            if (!traversable(next)) continue;
            const bool diagonal = dr[i] != 0 && dc[i] != 0;
            if (diagonal && (!traversable({from.row + dr[i], from.col}) ||
                             !traversable({from.row, from.col + dc[i]}))) continue;
            out.push_back({next, diagonal ? 1.5 : 1.0});
        }
        return out;
    }
    double heuristic(Cell state, Cell goal) const {
        const double dx = std::abs(state.row - goal.row);
        const double dy = std::abs(state.col - goal.col);
        if (movement_ == GridMovement::Four) return dx + dy;
        return std::max(dx, dy) + 0.5 * std::min(dx, dy);
    }
    bool is_goal(Cell state, Cell goal) const { return state == goal; }

private:
    std::vector<std::string> rows_;
    GridMovement movement_;
};

inline SearchResult<Cell> search_grid(const GridProblem& problem, Cell start, Cell goal) {
    problem.validate_endpoint(start);
    problem.validate_endpoint(goal);
    return search<Cell, GridProblem, CellHash>(problem, start, goal);
}
inline SearchResult<Cell> dijkstra_grid(const GridProblem& problem, Cell start, Cell goal) {
    problem.validate_endpoint(start);
    problem.validate_endpoint(goal);
    return dijkstra<Cell, GridProblem, CellHash>(problem, start, goal);
}
} // namespace astar
