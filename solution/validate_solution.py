"""Check the solution documented in branches.json and steady_states.json.

This file is the machine-readable definition of "valid solution" for this repository.

Specifically, we check that:
(0) JSON structure of steady_states.json is valid
(1) JSON structure of branches.json is valid
(2) branches.json contains the empty board
(3) No two steady states start from the same board, or mirror boards.
(4) No two branch entries start from the same board, or mirror boards.
(5) For each yellow-to-move node, all children satisfy exactly one of the following:
    (a) being present as a key in branches,
    (b) being a steady state,
    (c) red is able to win on the next move.
[During step 6, compute coverage over the branches keyset and steadystate boardset]
(6) No branch entries are extraneous/unreachable in the solution.
(7) No steady states are extraneous/unreachable in the solution.
(8) All steady states pass validation.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import random
import sys
import time
from pathlib import Path

sys.setrecursionlimit(100_000)
ROWS, COLS = 6, 7

MIAI, CLAIMEVEN, CLAIMODD = "@", " ", "|"
PLUS, EQUAL, MINUS, URGENT = "+", "=", "-", "!"
STONES = "12"
MARKERS = MIAI + CLAIMEVEN + CLAIMODD + PLUS + EQUAL + MINUS + URGENT
KNOWN = set(MARKERS + STONES)

HERE = Path(__file__).resolve().parent
BRANCHES = HERE / "branches.json"
STEADY_STATES = HERE / "steady_states.json"


# --------------------------------------------------------------------------
# board mechanics
# --------------------------------------------------------------------------

def board_from_position(position):
    """Board as board[y][x], y=0 bottom row; 0 empty, 1 Red, 2 Yellow."""
    board = [[0] * COLS for _ in range(ROWS)]
    heights = [0] * COLS
    for ply, character in enumerate(position):
        x = int(character) - 1
        if not 0 <= x < COLS or heights[x] >= ROWS:
            raise ValueError(f"illegal position {position!r}")
        board[heights[x]][x] = (ply % 2) + 1
        heights[x] += 1
    return board


def col_height(board, x):
    for y in range(ROWS):
        if board[y][x] == 0:
            return y
    return ROWS


def makes_four(board, x, y, player):
    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        count = 1
        for sign in (1, -1):
            nx, ny = x + sign * dx, y + sign * dy
            while 0 <= nx < COLS and 0 <= ny < ROWS and board[ny][nx] == player:
                count += 1
                nx += sign * dx
                ny += sign * dy
        if count >= 4:
            return True
    return False


def mirror_position(position):
    return "".join(str(8 - int(ch)) for ch in position)


def mirror_diagram(diagram):
    return [row[::-1] for row in diagram]


def board_from_diagram(diagram):
    """The stones a diagram draws, as a board[y][x] (y=0 bottom row).

    A diagram is the only record of its board now that steady_states.json
    keeps one representative per mirror-equivalent pair (see
    dedupe_mirrors.py) and stores no position string at all: many move
    sequences, and now also both mirror images, can lead to the same board.
    """
    board = [[0] * COLS for _ in range(ROWS)]
    for row_from_top, row in enumerate(diagram):
        y = ROWS - 1 - row_from_top
        for x, ch in enumerate(row):
            if ch in STONES:
                board[y][x] = STONES.index(ch) + 1
    return board


def board_key_from_diagram(diagram):
    return tuple(tuple(row) for row in board_from_diagram(diagram))


# --------------------------------------------------------------------------
# the policy and the exhaustive check
# --------------------------------------------------------------------------

def query_steady_state(board, diagram):
    """Red's move per the priority list; None = invalid (tie or no instruction)."""
    heights = [col_height(board, x) for x in range(COLS)]

    def wins(x, player):
        y = heights[x]
        if y >= ROWS:
            return False
        board[y][x] = player
        won = makes_four(board, x, y, player)
        board[y][x] = 0
        return won

    for player in (1, 2):
        for x in range(COLS):
            if wins(x, player):
                return x + 1

    def playable(marker_chars, parity=None):
        found = []
        for x in range(COLS):
            y = heights[x]
            if y >= ROWS:
                continue
            yt = ROWS - 1 - y
            if diagram[yt][x] in marker_chars and (parity is None or yt % 2 == parity):
                found.append(x + 1)
        return found

    miai = playable(MIAI)
    levels = (
        playable(URGENT),
        miai if len(miai) == 1 else [],
        playable(CLAIMEVEN, parity=0) + playable(CLAIMODD, parity=1),
        playable(PLUS),
        playable(EQUAL),
        playable(MINUS),
    )
    for valid in levels:
        if len(valid) == 1:
            return valid[0]
        if len(valid) > 1:
            return None
    return None


def verify_leaf(diagram):
    """True iff Red, following the diagram, beats every Yellow continuation.

    Depends on nothing but the diagram, which is why a diagram already in the
    graph never needs rechecking when a different one is added. The board it
    starts from is the diagram's own stones, not a position string: a diagram
    is the only record of its board now that steady_states.json keeps one
    representative per mirror-equivalent pair and carries no position at all.
    """
    memo = {}

    def red_turn(board):
        key = tuple(tuple(row) for row in board)
        if key in memo:
            return memo[key]
        move = query_steady_state(board, diagram)
        if move is None:
            return False
        x = move - 1
        y = col_height(board, x)
        if y >= ROWS:
            return False
        board[y][x] = 1
        try:
            if makes_four(board, x, y, 1):
                memo[key] = True
                return True
            if all(col_height(board, c) >= ROWS for c in range(COLS)):
                return False  # draw: not a Red win
            for yx in range(COLS):
                yy = col_height(board, yx)
                if yy >= ROWS:
                    continue
                board[yy][yx] = 2
                try:
                    if makes_four(board, yx, yy, 2):
                        return False
                    if all(col_height(board, c) >= ROWS for c in range(COLS)):
                        return False  # draw
                    if not red_turn(board):
                        return False
                finally:
                    board[yy][yx] = 0
        finally:
            board[y][x] = 0
        memo[key] = True
        return True

    board = board_from_diagram(diagram)
    if board_has_four(board):
        return False  # somebody has already won; nothing to play for
    return red_turn(board)


# --------------------------------------------------------------------------
# graph and entry-file I/O
# --------------------------------------------------------------------------

def board_key(position):
    return tuple(tuple(row) for row in board_from_position(position))


def mirror_key(key):
    return tuple(row[::-1] for row in key)


def load_branches(path):
    with open(path, "r") as f:
        return json.load(f)


def load_steady_states(path):
    with open(path, "r") as f:
        return json.load(f)


def board_has_four(board):
    for y in range(ROWS):
        for x in range(COLS):
            player = board[y][x]
            if player and makes_four(board, x, y, player):
                return True
    return False


def _red_wins_now(board, x):
    y = col_height(board, x)
    if y >= ROWS:
        return False
    board[y][x] = 1
    won = makes_four(board, x, y, 1)
    board[y][x] = 0
    return won


# --------------------------------------------------------------------------
# checks 0-8
# --------------------------------------------------------------------------

def check_steady_state_json_valid(steady_states):
    """(0) JSON structure of steady_states.json is valid."""
    if not isinstance(steady_states, list):
        raise ValueError("steady_states.json must be a JSON array")
    for i, diagram in enumerate(steady_states):
        if not isinstance(diagram, list) or len(diagram) != ROWS:
            raise ValueError(
                f"steady_states.json[{i}]: expected a list of {ROWS} rows, got {diagram!r}"
            )
        for row in diagram:
            if not isinstance(row, str) or len(row) != COLS:
                raise ValueError(
                    f"steady_states.json[{i}]: each row must be a {COLS}-character "
                    f"string, got {row!r}"
                )
            unknown = set(row) - KNOWN
            if unknown:
                raise ValueError(
                    f"steady_states.json[{i}]: unknown characters {sorted(unknown)}"
                )


def check_branches_json_valid(branches):
    """(1) JSON structure of branches.json is valid."""
    if not isinstance(branches, dict):
        raise ValueError("branches.json must be a JSON object")
    for position, move in branches.items():
        if not isinstance(move, str) or move not in "1234567":
            raise ValueError(
                f"branches.json[{position!r}]: move must be one of '1'-'7', got {move!r}"
            )
        if len(position) % 2:
            raise ValueError(
                f"branches.json: position {position!r} is Yellow to move; branches "
                "are only defined for Red to move (even length)"
            )
        try:
            board_from_position(position)
        except ValueError:
            raise ValueError(
                f"branches.json: position {position!r} overflows a column"
            ) from None


def check_branches_contains_empty_board(branches):
    """(2) branches.json contains the empty board."""
    if "" not in branches:
        raise AssertionError("branches.json does not contain the empty board (the root)")


def check_steady_states_unique(steady_states):
    """(3) No two steady states start from the same board, or mirror boards."""
    seen = {}
    failures = []
    for i, diagram in enumerate(steady_states):
        canon = min(board_key_from_diagram(diagram), mirror_key(board_key_from_diagram(diagram)))
        if canon in seen:
            failures.append([i, f"duplicates the board at index {seen[canon]} (up to mirroring)"])
        else:
            seen[canon] = i
    return failures


def check_branches_unique(branches):
    """(4) No two branch entries start from the same board, or mirror boards."""
    seen = {}
    failures = []
    for position in branches:
        key = board_key(position)
        canon = min(key, mirror_key(key))
        if canon in seen:
            failures.append(
                [position, f"duplicates the board at {seen[canon]!r} (up to mirroring)"]
            )
        else:
            seen[canon] = position
    return failures


def check_yellow_children(branches, steady_states):
    used_branches = set()
    used_steady_states = set()
    failures = []
    steady_keys = {board_key_from_diagram(diagram): i for i, diagram in enumerate(steady_states)}
    steady_canon = {}
    for key, i in steady_keys.items():
        steady_canon[min(key, mirror_key(key))] = i
    branch_canon = {}
    for p in branches:
        key = board_key(p)
        branch_canon[min(key, mirror_key(key))] = p

    for position, rmove in branches.items():
        board = board_from_position(position + rmove)
        for ymove in '1234567':
            x = int(ymove) - 1
            y = col_height(board, x)
            if y >= ROWS:
                continue
            child = [row[:] for row in board]
            child[y][x] = 2
            # Red's committed move lost the game, so nothing below matters.
            if makes_four(child, x, y, 2):
                failures.append([position, rmove, ymove,
                                 "Yellow wins the game with this reply"])
                continue
            child_key = tuple(tuple(row) for row in child)
            canon = min(child_key, mirror_key(child_key))

            has_steady_state = canon in steady_canon
            has_branch = canon in branch_canon
            has_rtw = False
            if has_steady_state:
                used_steady_states.add(steady_canon[canon])
            if has_branch:
                used_branches.add(branch_canon[canon])
            for rx in range(COLS):
                if _red_wins_now(child, rx):
                    has_rtw = True
                    break
            if sum(bool(v) for v in (has_branch, has_steady_state, has_rtw)) != 1:
                failures.append([position, rmove, ymove, "does not satisfy exactly one of", has_branch, has_steady_state, has_rtw])
    return failures, used_branches, used_steady_states


def check_no_extraneous_branches(branches, used_branches):
    failures = []
    for position in branches:
        if position != "" and position not in used_branches:
            failures.append([position, "branch is extraneous/unreachable"])
    return failures


def check_no_extraneous_steady_states(steady_states, used_steady_states):
    failures = []
    for i in range(len(steady_states)):
        if i not in used_steady_states:
            failures.append([i, "steady state is extraneous/unreachable"])
    return failures


def check_steady_states_correct(steady_states, jobs):
    """(8) All steady states pass validation."""
    if jobs > 1 and len(steady_states) > 1:
        with multiprocessing.Pool(jobs) as pool:
            verdicts = pool.map(verify_leaf, steady_states, chunksize=8)
    else:
        verdicts = [verify_leaf(diagram) for diagram in steady_states]

    failures = []
    for i, ok in enumerate(verdicts):
        if not ok:
            failures.append([i, "diagram fails against some Yellow line"])
    return failures


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--jobs", type=int, default=0, metavar="N",
                        help="parallel processes (default: one per core)")
    args = parser.parse_args()

    # On Windows stdout falls back to the ANSI codepage whenever it is not a
    # console (a pipe, a redirect, Git Bash), and cp1252 cannot encode the
    # marks the table below is drawn with.
    sys.stdout.reconfigure(encoding="utf-8")

    jobs = args.jobs or (os.cpu_count() or 1)
    started = time.time()

    branches = load_branches(BRANCHES)
    steady_states = load_steady_states(STEADY_STATES)

    # Each check below runs independently of the others' outcome, so one
    # failing check never hides or blocks the rest - a check either raises
    # (ValueError/AssertionError) to report a single all-or-nothing verdict,
    # or returns a list of individual failures to report many at once.
    checks = []

    def record(number, description, fn):
        try:
            result = fn()
        except (ValueError, AssertionError) as error:
            checks.append((number, description, False, [str(error)]))
            return None
        if isinstance(result, list):
            checks.append((number, description, not result, [str(row) for row in result]))
            return result
        checks.append((number, description, True, []))
        return result

    record(0, "steady_states.json is structurally valid",
           lambda: check_steady_state_json_valid(steady_states))
    record(1, "branches.json is structurally valid",
           lambda: check_branches_json_valid(branches))
    record(2, "branches.json contains the empty board",
           lambda: check_branches_contains_empty_board(branches))
    record(3, "no two steady states share a board (up to mirroring)",
           lambda: check_steady_states_unique(steady_states))
    record(4, "no two branches share a board (up to mirroring)",
           lambda: check_branches_unique(branches))
    yellow_failures, used_branches, used_steady_states = check_yellow_children(branches, steady_states)
    checks.append((
        5, "every Yellow reply is covered by exactly one of branch/steady-state/immediate-win",
        not yellow_failures, [str(row) for row in yellow_failures],
    ))
    record(6, "no branch is extraneous/unreachable",
           lambda: check_no_extraneous_branches(branches, used_branches))
    record(7, "no steady state is extraneous/unreachable",
           lambda: check_no_extraneous_steady_states(steady_states, used_steady_states))
    record(8, "all steady states pass validation",
           lambda: check_steady_states_correct(steady_states, jobs))

    ok = all(passed for _, _, passed, _ in checks)
    elapsed = time.time() - started

    lines = [
        "# Solution validation", "",
        f"_completed in {elapsed:.1f}s_", "",
        "| # | check | result |",
        "|---|---|---|",
    ]
    for number, description, passed, _details in checks:
        lines.append(f"| {number} | {description} | {'✅' if passed else '❌'} |")
    for number, description, passed, details in checks:
        if passed:
            continue
        lines.append("")
        lines.append(f"<details><summary>({number}) {description} — failures</summary>")
        lines.append("")
        for detail in details[:50]:
            lines.append(f"- {detail}")
        if len(details) > 50:
            lines.append(f"- ... and {len(details) - 50} more")
        lines.append("")
        lines.append("</details>")
    print("\n".join(lines))

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
