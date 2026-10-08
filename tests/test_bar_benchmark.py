"""The frozen BAR matrix is reproducible except for measured wall time."""

import csv
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from benchmark_bar import main


def test_frozen_benchmark_matrix():
    output = io.StringIO()
    with redirect_stdout(output):
        main()
    actual = list(csv.DictReader(io.StringIO(output.getvalue())))
    with (ROOT / "docs" / "bar-results.csv").open(newline="", encoding="utf-8") as source:
        frozen = list(csv.DictReader(source))
    assert len(actual) == len(frozen) == 18
    for current, expected in zip(actual, frozen):
        assert float(current.pop("planning_time_ms")) >= 0
        assert float(expected.pop("planning_time_ms")) >= 0
        assert current == expected
        if current["success"] == "True":
            assert float(current["full_map_shortest_distance"]) <= float(current["executed_distance"])
