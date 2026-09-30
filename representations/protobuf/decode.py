"""Decode representations/protobuf/solution.pb, per format.proto, and check
that it says exactly what solution/branches.json and solution/steady_states.json
say: the same steady states in the same order, and the same entries.

solution.pb does not store branches.json's keys, only the boards they reach, so
entries are compared by board rather than by the move string that spells it.
Run render.py first.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import format_pb2

SOLUTION_DIR = Path(__file__).resolve().parent.parent.parent / "solution"
sys.path.insert(0, str(SOLUTION_DIR))
import validate_solution as solution  # noqa: E402

HERE = Path(__file__).resolve().parent
BRANCHES = SOLUTION_DIR / "branches.json"
STEADY_STATES = SOLUTION_DIR / "steady_states.json"
SOLUTION_PB = HERE / "solution.pb"

CELLS = solution.ROWS * solution.COLS
MOVE_BITS = 3


def unpack_steady_state(packed):
    value = int.from_bytes(packed, "big")
    cells = []
    for _ in range(CELLS):
        value, cell = divmod(value, len(solution.LEVEL_CHARS))
        cells.append(solution.LEVEL_CHARS[cell])
    cells.reverse()  # column-major, bottom to top
    return ["".join(cells[x * solution.ROWS + (solution.ROWS - 1 - r)] for x in range(solution.COLS))
            for r in range(solution.ROWS)]


def unpack_branch(packed, width):
    """Red's column and the 7 references, in the node's own orientation."""
    bits = MOVE_BITS + 7 * width
    value = int.from_bytes(packed, "big") >> (8 * len(packed) - bits)
    references = []
    for _ in range(7):
        references.append(value & ((1 << width) - 1))
        value >>= width
    return value, references[::-1]


def decode(message):
    """(entries, steady_states): entries maps each board the solution stores,
    as a board_key in its stored orientation, to Red's column there (a string)
    or the index of its steady state (an int), as branches.json would."""
    steady_states = [unpack_steady_state(s.steadystate) for s in message.steadystates.steadystates]
    nodes = [b.node for b in message.branches.branches]
    num_branches = len(nodes)
    width = (2 * (num_branches + len(steady_states))).bit_length()

    entries = {}
    branch_board = {}  # branch id -> its stored board, which every reference must agree on

    def record(key, value):
        if entries.setdefault(key, value) != value:
            raise ValueError(f"board {key} decodes to both {entries[key]!r} and {value!r}")

    # Walk from the empty board, carrying the board actually reached and
    # whether it is the mirror image of the node's stored board.
    stack = [("", 0, False)]
    visited = set()
    while stack:
        position, branch, mirrored = stack.pop()
        stored = solution.board_key(position)
        if mirrored:
            stored = solution.mirror_key(stored)
        if branch_board.setdefault(branch, stored) != stored:
            raise ValueError(f"branch {branch} is reached as two different boards")
        if (branch, mirrored) in visited:
            continue
        visited.add((branch, mirrored))

        move, references = unpack_branch(nodes[branch], width)
        if not 1 <= move <= solution.COLS:
            raise ValueError(f"branch {branch} has column {move}")
        record(stored, str(move))
        if mirrored:  # play the node in the orientation actually reached
            move, references = solution.COLS + 1 - move, references[::-1]

        position += str(move)
        board = solution.board_from_position(position)
        for ymove, reference in zip("1234567", references):
            child = position + ymove
            if reference == 0:
                full = solution.col_height(board, int(ymove) - 1) >= solution.ROWS
                if not full and not any(solution._red_wins_now(solution.board_from_position(child), x)
                                        for x in range(solution.COLS)):
                    raise ValueError(f"{child!r}: no continuation, but Red has no immediate win")
                continue
            target, flip = divmod(reference - 1, 2)
            key = solution.board_key(child)
            child_mirrored = bool(flip) != mirrored and key != solution.mirror_key(key)
            if target < num_branches:
                stack.append((child, target, child_mirrored))
            elif target - num_branches < len(steady_states):
                record(solution.mirror_key(key) if child_mirrored else key, target - num_branches)
            else:
                raise ValueError(f"{child!r}: reference {reference} is out of range")

    unreached = sorted(set(range(num_branches)) - branch_board.keys())
    if unreached:
        raise ValueError(f"branches never reached from the empty board: {unreached}")
    return entries, steady_states


def main():
    message = format_pb2.Solution()
    message.ParseFromString(SOLUTION_PB.read_bytes())
    entries, steady_states = decode(message)

    expected_steady_states = json.loads(STEADY_STATES.read_text())
    branches = json.loads(BRANCHES.read_text())
    expected_entries = {solution.board_key(position): value for position, value in branches.items()}

    failures = []
    if steady_states != expected_steady_states:
        failures.append("steady states differ from steady_states.json")
    for key in expected_entries.keys() - entries.keys():
        failures.append(f"missing entry for board {key}")
    for key in entries.keys() - expected_entries.keys():
        failures.append(f"extra entry for board {key}")
    for key in expected_entries.keys() & entries.keys():
        if entries[key] != expected_entries[key]:
            failures.append(f"board {key}: decoded {entries[key]!r}, "
                            f"branches.json says {expected_entries[key]!r}")

    if failures:
        print("\n".join(failures))
        sys.exit(1)
    print(f"OK: solution.pb decodes to all {len(entries)} branches.json entries "
          f"and all {len(steady_states)} steady states")


if __name__ == "__main__":
    main()
