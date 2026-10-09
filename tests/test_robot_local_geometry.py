"""Focused checks for the frozen-sight local benchmark adapter."""

import hashlib
import json
from pathlib import Path
import sys


BENCHMARK = Path(__file__).resolve().parents[1] / "experiments" / "benchmarks"
sys.path.insert(0, str(BENCHMARK))
from robot_local_geometry import point_visible, segment_certified


def sight(center, blockers=()):
    return {"center": center, "closed_sights": [[a, b] for a, b in blockers]}


def test_blocking_segment_rejects_hidden_link():
    observation = sight((0, 0), [((1, -1), (1, 1))])
    assert point_visible((0.5, 0), observation, 5)
    assert not point_visible((2, 0), observation, 5)
    assert not segment_certified((0, 0), (2, 0), [observation], 5)[0]


def test_accumulated_second_sight_can_certify_return_link():
    first = sight((0, 0), [((1, -1), (1, 1))])
    second = sight((2, 2))
    assert segment_certified((0, 0), (2, 0), [first, second], 5)[0]


def test_unobserved_gap_between_sensing_disks_is_not_certified():
    left, right = sight((0, 0)), sight((3, 0))
    assert not segment_certified((0, 0), (3, 0), [left, right], 1)[0]
    assert segment_certified((0, 0), (1.5, 0), [left, sight((1.5, 0))], 1)[0]


def test_frozen_manifest_has_every_decision_and_fixed_selection():
    directory = BENCHMARK / "robot-local-benchmark"
    manifest = json.loads((directory / "robot-local-benchmark-manifest.json").read_text())
    content = (directory / manifest["snapshot_file"]).read_bytes()
    snapshots = json.loads(content)["snapshots"]
    assert hashlib.sha256(content).hexdigest() == manifest["snapshot_sha256"]
    assert len(snapshots) == manifest["captured_decisions"] == 43
    assert {item["snapshot_id"] for item in snapshots if len(item["skeleton_path"]) > 2} == set(manifest["eligible_ids"])
