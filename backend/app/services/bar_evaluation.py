"""Post-hoc benchmark labels. This module is never imported by the controller."""

from app.services.bar_scenarios import Scenario


def evaluate(scenario: Scenario, episode: dict) -> dict:
    gates = set(scenario.evaluation_gates)
    if not gates:
        return {"gate_entry_length": None, "gate_retreat_length": None,
                "gate_retreat_ratio": None, "gate_bound_verified": None,
                "gate_entries": 0, "gate_exits": 0,
                "bar_evaluation_status": "no_gate"}
    previous = scenario.start
    moves = 0
    entry_at = retreat_at = None
    entry_length = retreat_length = None
    entries = exits = 0
    certified_exit = False
    for frame in episode["frames"]:
        if frame["event"] == "recover_start" and entry_at is not None:
            retreat_at = moves
            entry_length = moves - entry_at
        elif frame["event"] == "recover_end":
            retreat_at = None
        if frame["event"] != "move":
            continue
        current = (frame["position"]["row"], frame["position"]["col"])
        moves += 1
        if (previous, current) in gates:
            entries += 1
            entry_at = moves - 1
        elif (current, previous) in gates:
            exits += 1
            if retreat_at is not None and frame["phase"] == "retreat":
                retreat_length = moves - retreat_at
                certified_exit = True
                retreat_at = None
        previous = current
    verified = (retreat_length <= entry_length + 1e-9
                if certified_exit and entry_length is not None and retreat_length is not None else None)
    status = ("no_entry" if entries == 0 else
              "entered_no_exit" if exits == 0 else
              "uncertified_exit" if not certified_exit else
              "certified" if verified else "bound_failed")
    return {"gate_entry_length": entry_length, "gate_retreat_length": retreat_length,
            "gate_retreat_ratio": retreat_length / entry_length
            if entry_length and retreat_length is not None else None,
            "gate_bound_verified": verified, "gate_entries": entries, "gate_exits": exits,
            "bar_evaluation_status": status}
