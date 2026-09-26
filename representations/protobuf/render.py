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

SYMBOLS = {"R": 0, "Y": 1}
for _i, _ch in enumerate("0123456789abcdef"):
    SYMBOLS[_ch] = 2 + _i
BASE = len(SYMBOLS)


def pack_steady_state(diagram):
    """Base-18 encoding of all 42 cells, column-major, bottom to top."""
    value = 0
    board_h = len(diagram)
    board_w = len(diagram[0])
    for x in range(board_w):
        for y in range(board_h):
            value = value * BASE + SYMBOLS[diagram[board_h - 1 - y][x]]
    num_bytes_needed = (value.bit_length() + 7) >> 3
    return value.to_bytes(num_bytes_needed, "big")


def build_branches(branches):
    message = format_pb2.Branches()
    for position, move in branches.items():
        branch = message.branches.add()
        branch.rep = bytes(int(ch) for ch in position)
        branch.move = int(move)
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

    branches = build_branches(branches_data)
    steady_states = build_steady_states(steady_states_data)

    combined = format_pb2.Solution()
    combined.branches.CopyFrom(branches)
    combined.steady_states.CopyFrom(steady_states)

    print(f"Branches size (bytes): {len(branches.SerializeToString())}")
    print(f"SteadySt size (bytes): {len(steady_states.SerializeToString())}")
    print(f"Combined size (bytes): {len(combined.SerializeToString())}")
    OUT.write_bytes(combined.SerializeToString())

if __name__ == "__main__":
    main()
