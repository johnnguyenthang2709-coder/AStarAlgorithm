"""Deterministic point-robot sensing on unit cells with conservative occlusion."""

from math import hypot, inf

Cell = tuple[int, int]
UNKNOWN, FREE, BLOCKED = -1, 0, 1


def cardinal(cell: Cell, height: int, width: int) -> list[Cell]:
    r, c = cell
    return [(y, x) for y, x in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1))
            if 0 <= y < height and 0 <= x < width]


def ray_cells(start: Cell, target: Cell) -> list[Cell]:
    """Supercover center-to-center ray; at a corner both touching cells count."""
    y, x = start
    dy, dx = target[0] - y, target[1] - x
    sx, sy = (1 if dx > 0 else -1 if dx < 0 else 0), (1 if dy > 0 else -1 if dy < 0 else 0)
    tx = 0.5 / abs(dx) if dx else inf
    ty = 0.5 / abs(dy) if dy else inf
    step_x = 1 / abs(dx) if dx else inf
    step_y = 1 / abs(dy) if dy else inf
    out: list[Cell] = []
    while (y, x) != target:
        if tx < ty:
            x += sx
            tx += step_x
            out.append((y, x))
        elif ty < tx:
            y += sy
            ty += step_y
            out.append((y, x))
        else:
            out.extend(((y, x + sx), (y + sy, x)))
            x += sx
            y += sy
            tx += step_x
            ty += step_y
            out.append((y, x))
    return out


def sense(rows: tuple[str, ...], discovered: list[list[int]], position: Cell,
          radius: float) -> list[tuple[Cell, int]]:
    if radius < 1:
        raise ValueError("sensor radius must be at least one cell")
    changes: list[tuple[Cell, int]] = []
    for r in range(len(rows)):
        for c in range(len(rows[0])):
            target = (r, c)
            if discovered[r][c] != UNKNOWN or hypot(r - position[0], c - position[1]) > radius:
                continue
            ray = ray_cells(position, target)
            if any(rows[y][x] == "#" for y, x in ray[:-1]):
                continue
            value = BLOCKED if rows[r][c] == "#" else FREE
            discovered[r][c] = value
            changes.append((target, value))
    return changes
