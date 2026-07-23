"""Exhaustively verify every steady-state diagram in c4_full.js.

Standalone, Python standard library only:

    python verify_steady_states.py

Checks, using only the graph file itself:

1. Dataset integrity: every node is reachable from the root and no edge
   points at a missing node.
2. Every leaf node with a steady-state diagram defeats every legal Yellow
   continuation, following the original SteadyState.cpp semantics:
   immediate wins, then blocks, then marker priorities (urgent, miai,
   claimeven/claimodd combined, plus, equal, minus), where the applicable
   marker priority must identify exactly one move (a tie invalidates the
   diagram) and miai fires only when exactly one miai cell is playable.
3. Every leaf without a diagram is a completed Red win.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.setrecursionlimit(100_000)
ROWS, COLS = 6, 7

MIAI, CLAIMEVEN, CLAIMODD = "@", " .", "|"
PLUS, EQUAL, MINUS, URGENT = "+", "=", "-", "!"
STONES = "12"
KNOWN = set(MIAI + CLAIMEVEN + CLAIMODD + PLUS + EQUAL + MINUS + URGENT + STONES)


def load_dataset(path):
    text = path.read_text(encoding="utf-8")
    match = re.fullmatch(r"\s*var\s+dataset\s*=\s*(\{.*\})\s*;?\s*", text, re.S)
    if not match:
        raise ValueError(f"{path} is not a recognizable WeakC4 dataset")
    return json.loads(match.group(1))


def board_from_rep(rep):
    """Board as board[y][x], y=0 bottom row; 0 empty, 1 Red, 2 Yellow."""
    board = [[0] * COLS for _ in range(ROWS)]
    heights = [0] * COLS
    for ply, character in enumerate(rep):
        x = int(character) - 1
        if not 0 <= x < COLS or heights[x] >= ROWS:
            raise ValueError(f"illegal representative {rep!r}")
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


def query_steady_state(board, diagram):
    """Red's move per SteadyState.cpp; None = invalid (tie or no instruction)."""
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


def verify_leaf(rep, diagram):
    """True iff Red, following the diagram, beats every Yellow continuation."""
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

    return red_turn(board_from_rep(rep))


def main():
    started = time.time()
    dataset = load_dataset(Path(__file__).resolve().parent / "c4_full.js")
    nodes = dataset["nodes_to_use"]

    # 1. Graph integrity.
    seen = set()
    stack = [dataset["root_node_hash"]]
    while stack:
        node_hash = stack.pop()
        if node_hash in seen:
            continue
        seen.add(node_hash)
        neighbors = nodes[node_hash]["neighbors"]
        if neighbors is not None:
            missing = [target for target in neighbors if target not in nodes]
            if missing:
                raise AssertionError(f"dangling edges at {node_hash}: {missing}")
            stack.extend(neighbors)
    if seen != set(nodes):
        raise AssertionError(f"{len(set(nodes) - seen)} nodes unreachable from root")

    # 2 + 3. Verify every leaf.
    diagram_leaves = terminal_leaves = 0
    failures = []
    for node_hash, node in nodes.items():
        if node["neighbors"] is not None:
            continue
        rep = node["rep"]
        ss = node["data"].get("ss")
        if ss is None:
            board = board_from_rep(rep)
            x = int(rep[-1]) - 1
            y = col_height(board, x) - 1
            if len(rep) % 2 == 1 and makes_four(board, x, y, 1):
                terminal_leaves += 1
            else:
                failures.append((node_hash, "leaf is neither diagram nor Red win"))
            continue
        diagram = ["".join(chr(value) for value in row) for row in ss]
        unknown = {ch for row in diagram for ch in row} - KNOWN
        if unknown:
            failures.append((node_hash, f"unknown diagram characters {sorted(unknown)}"))
            continue
        if verify_leaf(rep, diagram):
            diagram_leaves += 1
        else:
            failures.append((node_hash, "diagram fails against some Yellow line"))
        total_done = diagram_leaves + len(failures)
        if total_done % 500 == 0:
            print(f"verified {total_done} diagrams...", file=sys.stderr)

    print(json.dumps({
        "status": "OK" if not failures else "FAILED",
        "nodes": len(nodes),
        "diagram_leaves_verified": diagram_leaves,
        "terminal_win_leaves": terminal_leaves,
        "failures": failures[:20],
        "seconds": round(time.time() - started, 1),
    }, indent=2, sort_keys=True))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
