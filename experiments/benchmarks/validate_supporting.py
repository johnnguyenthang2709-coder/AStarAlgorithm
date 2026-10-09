"""Validate paired supporting matrices and emit descriptive summaries."""

import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read(name):
    with (HERE / name).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def median(values):
    return statistics.median(values) if values else None


def main():
    ablation = defaultdict(dict)
    for row in read("exploration-ablation.csv"):
        ablation[(row["case"], row["radius"])][row["policy"]] = row
    assert len(ablation) == 20 and all(set(pair) == {"baseline", "radar"} for pair in ablation.values())
    cache = defaultdict(dict)
    for row in read("frontier-cache.csv"):
        cache[(row["case"], row["radius"])][row["variant"]] = row
    assert set(cache) == set(ablation) and all(set(pair) == {"full", "cached"} for pair in cache.values())
    assert all(row["equivalent_to_full"] == "True" for pair in cache.values() for row in pair.values())
    assert all(int(pair["full"]["eligible_snapshots"]) > 0 and
               pair["full"]["eligible_snapshots"] == pair["cached"]["eligible_snapshots"]
               for pair in cache.values())
    sensor = read("sensor-robustness.csv")
    assert len(sensor) == 12 and {(r["kind"], r["case"], r["radius"]) for r in sensor} == {
        (kind, case, radius) for kind, case in (("labyrinth", "seed_17"), ("labyrinth", "seed_23"),
                                                ("labyrinth", "seed_41"), ("indoor", "apartment"),
                                                ("indoor", "office"), ("indoor", "challenge"))
        for radius in ("5", "7")}
    diffs = [float(pair["radar"]["executed_distance"]) - float(pair["baseline"]["executed_distance"])
             for pair in ablation.values()]
    summary = {
        "ablation": {
            "paired_configurations": len(ablation),
            "baseline_success": sum(p["baseline"]["success"] == "True" for p in ablation.values()),
            "radar_success": sum(p["radar"]["success"] == "True" for p in ablation.values()),
            "radar_shorter": sum(d < -1e-6 for d in diffs),
            "radar_longer": sum(d > 1e-6 for d in diffs),
            "median_radar_minus_baseline_distance": median(diffs),
            "largest_radar_regression": max(((key, float(p["radar"]["executed_distance"]) -
                                                  float(p["baseline"]["executed_distance"]))
                                                 for key, p in ablation.items()), key=lambda item: item[1]),
            "baseline_wall_ms_median": median([float(p["baseline"]["wall_ms"]) for p in ablation.values()]),
            "radar_wall_ms_median": median([float(p["radar"]["wall_ms"]) for p in ablation.values()]),
        },
        "cache": {
            "paired_configurations": len(cache),
            "playback_equivalent": len(cache),
            "frontier_full_ms_median": median([float(p["full"]["frontier_total_ms"]) for p in cache.values()]),
            "frontier_cached_ms_median": median([float(p["cached"]["frontier_total_ms"]) for p in cache.values()]),
            "frontier_cached_faster": sum(float(p["cached"]["frontier_total_ms"]) <
                                          float(p["full"]["frontier_total_ms"]) for p in cache.values()),
            "cached_wall_mask_wkb_bytes_median": median([int(p["cached"]["wall_mask_wkb_bytes"]) for p in cache.values()]),
        },
        "sensor": {
            "episodes": len(sensor), "success": sum(r["success"] == "True" for r in sensor),
            "statuses": {status: sum(r["status"] == status for r in sensor)
                         for status in sorted({r["status"] for r in sensor})},
            "radius_5_median_distance": median([float(r["executed_distance"]) for r in sensor if r["radius"] == "5"]),
            "radius_7_median_distance": median([float(r["executed_distance"]) for r in sensor if r["radius"] == "7"]),
        },
    }
    (HERE / "supporting-validation.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
