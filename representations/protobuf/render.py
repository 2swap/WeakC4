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

# Steady states use 9 symbols; packed as a base-9 bignum rather than one byte
# (or even one nibble) per cell, since 42 cells only ever need
# ceil(log2(9**42)) = 134 bits, not 42*8 = 336 or even 42*4 = 168.
SYMBOLS = {" ": 0, "1": 1, "2": 2, "|": 3, "!": 4, "-": 5, "@": 6, "+": 7, "=": 8}
PACKED_SS_BYTES = (len(SYMBOLS) ** (solution.ROWS * solution.COLS)).bit_length() + 7 >> 3


def pack_steady_state(diagram):
    value = 0
    for row in diagram:
        for ch in row:
            value = value * len(SYMBOLS) + SYMBOLS[ch]
    return value.to_bytes(PACKED_SS_BYTES, "big")


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
