"""
Print basic statistics about the solution and about how the graph is drawn.
Reads steady_states.json and branches.json independently.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import validate_solution as solution

HERE = Path(__file__).resolve().parent
STEADY_STATES = HERE / "steady_states.json"
BRANCHES = HERE / "branches.json"

RESET = "\033[0m"
COLOR_STEADY_STATES = "\033[33m"   # yellow
COLOR_BRANCHES = "\033[32m"        # green
COLOR_SECTION = "\033[1m"          # bold


def cprint(color, *args):
    print(color + " ".join(str(a) for a in args) + RESET)


def data_lines(path):
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip() and not raw.startswith("#"):
            yield raw


def print_steady_states_stats():
    with open(STEADY_STATES, "r") as f:
        steady_states = json.load(f)

        by_length = {}
        for diagram in steady_states:
            stones = sum(1 for row in diagram for ch in row if (ch == '1' or ch == '2'))
            by_length[stones] = by_length.get(stones, 0) + 1

        cprint(COLOR_STEADY_STATES, f"total steady states: {len(steady_states)}")
        cprint(COLOR_STEADY_STATES, "by ply count:")
        for length in sorted(by_length):
            cprint(COLOR_STEADY_STATES, f"  {length:3d}-ply: {by_length[length]}")


def print_branches_stats():
    with open(BRANCHES, "r") as f:
        red = set()
        yellow_edges = []
        branches = json.load(f)
        for k,v in branches.items():
            red.add(k)
            yellow_edges.append(solution.board_key(k + v))

        yellow = set(yellow_edges)
        incoming = {}
        for kid in yellow_edges:
            incoming[kid] = incoming.get(kid, 0) + 1

        by_incoming_count = {}
        for count in incoming.values():
            by_incoming_count[count] = by_incoming_count.get(count, 0) + 1

        cprint(COLOR_BRANCHES, f"Red-to-move nodes: {len(red)}")
        cprint(COLOR_BRANCHES, f"Yellow-to-move nodes (Red's move destinations): {len(yellow)}")
        cprint(COLOR_BRANCHES, f"total nodes identified: {len(red) + len(yellow)}")
        cprint(COLOR_BRANCHES, "")
        cprint(COLOR_BRANCHES, f"Yellow nodes by number of incoming red edges:")
        for count in sorted(by_incoming_count):
            cprint(COLOR_BRANCHES, f"  {count} incoming edges: {by_incoming_count[count]} nodes")


def main():
    print()
    cprint(COLOR_SECTION, "================= steady_states ===================")
    print_steady_states_stats()
    cprint(COLOR_SECTION, "=============== end steady_states =================")
    print()
    cprint(COLOR_SECTION, "=================== branches ======================")
    print_branches_stats()
    cprint(COLOR_SECTION, "================= end branches ====================")
    print()


if __name__ == "__main__":
    main()
