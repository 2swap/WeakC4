"""Print basic statistics about the three solution/ source files.

    python solution/print_statistics.py

Reads positions.txt, steady_states.txt and branches.txt independently; each
section below stands on its own.
"""
from __future__ import annotations

import math
from pathlib import Path

import validate_solution as solution

HERE = Path(__file__).resolve().parent
POSITIONS = HERE / "positions.txt"
STEADY_STATES = HERE / "steady_states.txt"
BRANCHES = HERE / "branches.txt"

RESET = "\033[0m"
COLOR_POSITIONS = "\033[36m"       # cyan
COLOR_STEADY_STATES = "\033[33m"   # yellow
COLOR_BRANCHES = "\033[32m"        # green
COLOR_SECTION = "\033[1m"          # bold


def cprint(color, *args):
    print(color + " ".join(str(a) for a in args) + RESET)


def data_lines(path):
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip() and not raw.startswith("#"):
            yield raw


def print_positions_stats():
    rows = []
    root_xyz = None
    for line in data_lines(POSITIONS):
        position, x, y, z = line.split(",")
        x, y, z = float(x), float(y), float(z)
        rows.append((position, x, y, z))
        if position == "":
            root_xyz = (x, y, z)

    n = len(rows)
    cx = sum(r[1] for r in rows) / n
    cy = sum(r[2] for r in rows) / n
    cz = sum(r[3] for r in rows) / n

    farthest_position, farthest_distance = None, -1.0
    for position, x, y, z in rows:
        distance = math.sqrt(x * x + y * y + z * z)
        if distance > farthest_distance:
            farthest_position, farthest_distance = position, distance

    cprint(COLOR_POSITIONS, f"nodes with positions: {n}")
    cprint(COLOR_POSITIONS, f"center of mass: ({cx:.3f}, {cy:.3f}, {cz:.3f})")
    cprint(COLOR_POSITIONS, f"most distant node from origin: {farthest_position!r} "
           f"at distance {farthest_distance:.3f}")
    cprint(COLOR_POSITIONS, f"root node position: {root_xyz}")


def print_steady_states_stats():
    text = STEADY_STATES.read_text(encoding="utf-8")
    entries = solution.parse_entries(text, source=STEADY_STATES.name)

    # There is no position to read a ply count from any more (a diagram is
    # identified by its own stones, not a move string), so ply count is
    # derived from how many stones are actually drawn on the board.
    by_length = {}
    for diagram, _number in entries:
        stones = sum(1 for row in diagram for ch in row if ch in solution.STONES)
        by_length[stones] = by_length.get(stones, 0) + 1

    cprint(COLOR_STEADY_STATES, f"total steady states: {len(entries)}")
    cprint(COLOR_STEADY_STATES, "by ply count:")
    for length in sorted(by_length):
        cprint(COLOR_STEADY_STATES, f"  {length:3d}-ply: {by_length[length]}")


def print_branches_stats():
    red = set()
    yellow_edges = []
    for line in data_lines(BRANCHES):
        parent, move = line.split("->")
        red.add(parent)
        # The committed move's destination board, not the raw "parent+move"
        # string: two different parents can reach the same Yellow board by a
        # different move order, and only the board identifies that.
        yellow_edges.append(solution.board_key(parent + move))

    yellow = set(yellow_edges)
    incoming = {}
    for kid in yellow_edges:
        incoming[kid] = incoming.get(kid, 0) + 1

    by_incoming_count = {}
    for count in incoming.values():
        by_incoming_count[count] = by_incoming_count.get(count, 0) + 1
    transposed = sum(v for count, v in by_incoming_count.items() if count > 1)

    cprint(COLOR_BRANCHES, f"Red-to-move nodes: {len(red)}")
    cprint(COLOR_BRANCHES, f"Yellow-to-move nodes (Red's move destinations): {len(yellow)}")
    cprint(COLOR_BRANCHES, f"total nodes identified: {len(red) + len(yellow)}")
    cprint(COLOR_BRANCHES, "")
    cprint(COLOR_BRANCHES,
           "Yellow-to-move nodes reached by more than one Red move (transpositions):")
    cprint(COLOR_BRANCHES,
           "this only counts multiple Red moves converging on the same Yellow node -")
    cprint(COLOR_BRANCHES,
           "it says nothing about Yellow transposing onto Red, which this file does")
    cprint(COLOR_BRANCHES, "not show.")
    cprint(COLOR_BRANCHES, f"  Yellow nodes with a transposition: {transposed}")
    for count in sorted(by_incoming_count):
        if count > 1:
            cprint(COLOR_BRANCHES,
                   f"    {count} incoming edges: {by_incoming_count[count]} nodes")


def main():
    print()
    cprint(COLOR_SECTION, "==================== positions.txt ====================")
    print_positions_stats()
    cprint(COLOR_SECTION, "================== end positions.txt ==================")
    print()
    cprint(COLOR_SECTION, "================= steady_states.txt ===================")
    print_steady_states_stats()
    cprint(COLOR_SECTION, "=============== end steady_states.txt =================")
    print()
    cprint(COLOR_SECTION, "=================== branches.txt ======================")
    print_branches_stats()
    cprint(COLOR_SECTION, "================= end branches.txt ====================")
    print()


if __name__ == "__main__":
    main()
