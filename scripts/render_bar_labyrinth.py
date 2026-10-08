"""Export comparable geometry renders and an observation-only navigation trace.

These are explanatory SVG figures, not screenshots or data supplied to the robot.
"""

import sys
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.bar_continuous import simulate_continuous
from app.services.bar_labyrinth import BLIND_ALLEY, EXPLORATION, generate_labyrinth
from app.services.bar_maze import SHOWCASE, generate_maze

OUT = ROOT / "docs" / "images"
OUT.mkdir(exist_ok=True)


def transform(point, origin, side, world_size):
    x, y = point
    return origin[0] + side * x / world_size, origin[1] + side * (1 - y / world_size)


def polygon_paths(geometry, origin, side, world_size):
    parts = geometry.geoms if hasattr(geometry, "geoms") else (geometry,)
    paths = []
    for part in parts:
        if part.geom_type != "Polygon":
            continue
        rings = (part.exterior, *part.interiors)
        commands = []
        for ring in rings:
            for index, point in enumerate(ring.coords):
                x, y = transform(point, origin, side, world_size)
                commands.append(f"{'M' if index == 0 else 'L'}{x:.2f} {y:.2f}")
            commands.append("Z")
        paths.append(" ".join(commands))
    return paths


def header(title, subtitle, width, height):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            f'width="{width}" height="{height}"><rect width="100%" height="100%" fill="#edf1f1"/>'
            f'<text x="28" y="37" font-family="Arial" font-size="21" font-weight="700" fill="#243b47">{title}</text>'
            f'<text x="28" y="59" font-family="Arial" font-size="12" fill="#516673">{subtitle}</text>')


def markers(world, origin, side):
    scale = world.bounds[2]
    items = []
    for point, color, label in ((world.start, "#1e6b83", "S"),
                                (world.goal, "#d1614b", "G")):
        x, y = transform(point, origin, side, scale)
        items.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="8" fill="{color}" stroke="white" stroke-width="2"/>')
        items.append(f'<text x="{x:.2f}" y="{y+3.5:.2f}" text-anchor="middle" font-family="Arial" font-size="10" font-weight="700" fill="white">{label}</text>')
    return "".join(items)


def comparison():
    old = generate_maze(SHOWCASE)
    new = generate_labyrinth(EXPLORATION)
    side = 540
    result = [header("Maze 3 geometry comparison", "Same topology seed 17 and 25 × 25 world scale · simulator ground truth, not robot knowledge", 1180, 660)]
    for layout, origin, title, caption in ((old, (28, 93), "Before · room boundaries", "65 separate rectangular walls"),
                                          (new, (612, 93), "After · winding corridors", "2 coherent polygon walls with interior rings")):
        world = layout.world
        result.append(f'<rect x="{origin[0]}" y="{origin[1]}" width="{side}" height="{side}" fill="#f8f8f2"/>')
        for path in polygon_paths(world.obstacles, origin, side, world.bounds[2]):
            result.append(f'<path d="{path}" fill="#263d49" fill-rule="evenodd"/>')
        result.append(markers(world, origin, side))
        result.append(f'<text x="{origin[0]}" y="654" font-family="Arial" font-size="14" font-weight="700" fill="#243b47">{title}</text>')
        result.append(f'<text x="{origin[0]+245}" y="654" font-family="Arial" font-size="12" fill="#61727b">{caption}</text>')
    result.append("</svg>")
    (OUT / "maze3-before-after.svg").write_text("".join(result), encoding="utf-8")


def trace():
    layout = generate_labyrinth(BLIND_ALLEY)
    episode = simulate_continuous(layout.world, 5, prefer_novelty=True,
                                  complete_frontier_route=True)
    world, side, origin = layout.world, 600, (30, 90)
    regions = unary_union([shape(frame["region"]) for frame in episode["frames"]
                           if frame["event"] == "sense"])
    output = [header("Blind-Alley Labyrinth · observed trajectory",
                     "Seed 23 · radius 5 · gray remains unknown · plotted from sensor and execution frames", 660, 750)]
    output.append(f'<rect x="{origin[0]}" y="{origin[1]}" width="{side}" height="{side}" fill="#bdc9cf"/>')
    for path in polygon_paths(regions, origin, side, world.bounds[2]):
        output.append(f'<path d="{path}" fill="#f8f8f2" fill-rule="evenodd"/>')
    for frame in episode["frames"]:
        if frame["event"] == "sense":
            for a, b in frame["obstacle_edges"]:
                x1, y1 = transform((a["x"], a["y"]), origin, side, world.bounds[2])
                x2, y2 = transform((b["x"], b["y"]), origin, side, world.bounds[2])
                output.append(f'<path d="M{x1:.2f} {y1:.2f} L{x2:.2f} {y2:.2f}" fill="none" stroke="#263d49" stroke-width="5" stroke-linecap="round"/>')
        elif frame["event"] == "move":
            a, b = frame["from"], frame["position"]
            x1, y1 = transform((a["x"], a["y"]), origin, side, world.bounds[2])
            x2, y2 = transform((b["x"], b["y"]), origin, side, world.bounds[2])
            color = "#368c6e" if frame["phase"] == "retreat" else "#297d9e"
            output.append(f'<path d="M{x1:.2f} {y1:.2f} L{x2:.2f} {y2:.2f}" fill="none" stroke="{color}" stroke-width="2.4" opacity=".85"/>')
    output.append(markers(world, origin, side))
    output.append(f'<text x="30" y="724" font-family="Arial" font-size="13" fill="#243b47">Goal: {episode["status"]} · '
                  f'Distance: {episode["metrics"]["executed_distance"]:.1f} · '
                  f'Certified branch returns: {len(episode["recoveries"])} · '
                  f'A* calls: {episode["metrics"]["replanning_count"]}</text>')
    output.append("</svg>")
    (OUT / "labyrinth-observed-trace.svg").write_text("".join(output), encoding="utf-8")


if __name__ == "__main__":
    comparison()
    trace()
