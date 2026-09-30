"""Build representations/protobuf/solution.pb
from solution/, per format.proto.

Serializes solution/branches.json and solution/steady_states.json directly.
this is an equivalent but smaller encoding of exactly what those two files
already say, so that we can measure size of the weak solution.
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
OUT = HERE / "solution.pb"

SYMBOLS = {ch: i for i, ch in enumerate(solution.LEVEL_CHARS)}


def pack_steady_state(diagram):
    """42 cells, column-major, bottom to top, read as one base-10 integer (first
    cell most significant), big-endian in as few bytes as it needs: at most
    ceil(log2(10^42) / 8) = 18. The cell count is fixed, so the leading zeros
    a short encoding drops are recoverable."""
    value = 0
    board_h = len(diagram)
    board_w = len(diagram[0])
    for x in range(board_w):
        for y in range(board_h):
            value = value * len(SYMBOLS) + SYMBOLS[diagram[board_h - 1 - y][x]]
    num_bytes_needed = (value.bit_length() + 7) >> 3
    return value.to_bytes(num_bytes_needed, "big")


MOVE_BITS = 3


def build_branches(branches, num_steady_states):
    """One Branch per string entry of branches.json, in file order (so the
    empty board is index 0). Each stores Red's column and a reference per
    Yellow reply to the branch or steady state that reply reaches; the
    starting positions themselves are not stored."""
    red = [position for position, value in branches.items()
           if not solution.is_steady_state_entry(value)]
    assert red[0] == ""
    branch_id = {position: i for i, position in enumerate(red)}

    # Every entry's board and its mirror image, each pointing at the entry's
    # target id and whether the board is the mirror of the stored one.
    targets = {}
    for position, value in branches.items():
        target = (len(red) + value if solution.is_steady_state_entry(value)
                  else branch_id[position])
        key = solution.board_key(position)
        targets[key] = (target, 0)
        targets.setdefault(solution.mirror_key(key), (target, 1))

    width = (2 * (len(red) + num_steady_states)).bit_length()
    message = format_pb2.Branches()
    for position in red:
        move = branches[position]
        board = solution.board_from_position(position + move)
        value = int(move)
        for ymove in "1234567":
            reference = 0
            if solution.col_height(board, int(ymove) - 1) < solution.ROWS:
                target = targets.get(solution.board_key(position + move + ymove))
                if target is not None:
                    reference = 1 + 2 * target[0] + target[1]
            value = (value << width) | reference
        bits = MOVE_BITS + 7 * width
        num_bytes = (bits + 7) >> 3
        message.branches.add().node = (value << (8 * num_bytes - bits)).to_bytes(num_bytes, "big")
    return message


def build_steady_states(diagrams):
    message = format_pb2.SteadyStates()
    for diagram in diagrams:
        state = message.steadystates.add()
        state.steadystate = pack_steady_state(diagram)
    return message


def main():
    with open(BRANCHES, "r") as f:
        branches_data = json.load(f)
    with open(STEADY_STATES, "r") as f:
        steady_states_data = json.load(f)

    branches = build_branches(branches_data, len(steady_states_data))
    steady_states = build_steady_states(steady_states_data)

    combined = format_pb2.Solution()
    combined.branches.CopyFrom(branches)
    combined.steadystates.CopyFrom(steady_states)

    print(f"Branches size (bytes): {len(branches.SerializeToString())}")
    print(f"SteadySt size (bytes): {len(steady_states.SerializeToString())}")
    print(f"Combined size (bytes): {len(combined.SerializeToString())}")
    OUT.write_bytes(combined.SerializeToString())

if __name__ == "__main__":
    main()
