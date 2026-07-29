"""Check the solution documented in branches.txt and steady_states.txt.

This file is the machine-readable definition of "valid solution" for this repository.

Specifically, we check that:
- All steady states pass validation.
- The graph contains the empty board.
- All red-to-move nodes either point to one neighbor or reflect a steady state.
- All yellow-to-move nodes have all valid children in the graph, except those which expose an immediate red win.
- No steady states are extraneous/unreachable in the solution.
- No branch entries are extraneous/unreachable in the solution.
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

# CLAIMEVEN is two characters because it is tested by membership: the graph
# stores claimeven as a space, the contribution file writes it as a dot.
MIAI, CLAIMEVEN, CLAIMODD = "@", " .", "|"
PLUS, EQUAL, MINUS, URGENT = "+", "=", "-", "!"
STONES = "12"
MARKERS = MIAI + CLAIMEVEN + CLAIMODD + PLUS + EQUAL + MINUS + URGENT
KNOWN = set(MARKERS + STONES)

HERE = Path(__file__).resolve().parent
DEFAULT_BRANCHES = HERE / "branches.txt"
DEFAULT_ENTRIES = HERE / "steady_states.txt"


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

    A diagram is the only record of its board now that steady_states.txt
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
    is the only record of its board now that steady_states.txt keeps one
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


def verify_all(diagrams, jobs):
    """Verify a list of diagrams, optionally across processes."""
    if jobs > 1 and len(diagrams) > 1:
        with multiprocessing.Pool(jobs) as pool:
            return pool.map(verify_leaf, diagrams, chunksize=8)
    return [verify_leaf(diagram) for diagram in diagrams]


# --------------------------------------------------------------------------
# graph and entry-file I/O
# --------------------------------------------------------------------------

def board_key(position):
    return tuple(tuple(row) for row in board_from_position(position))


def load_branches(path):
    """branches.txt -> {board_key: (position, committed_move_position)}.

    Only Red-to-move nodes are stored (see filter_branches.py); Yellow's
    replies are forced by the rules of the game rather than chosen, so they
    are re-derived on demand instead of being carried as data. Each line is
    `<position>-><move>` (see migrate_branches_format.py); the committed move
    position is simply position + move, since replaying one more move on top
    of a valid position always reaches the right board regardless of how any
    differently-ordered transposition elsewhere spells the same board.
    """
    red = {}
    path = Path(path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    for number, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip() or raw.startswith("#"):
            continue
        if "->" not in raw:
            raise ValueError(
                f"{path.name}:{number}: expected '<position>-><move>', got {raw!r}"
            )
        position, move = raw.split("->", 1)
        # `in` on a str is a substring test, so the length check is what stops
        # "12" and "" from passing as a single column.
        if len(move) != 1 or move not in "1234567":
            raise ValueError(
                f"{path.name}:{number}: move must be a single digit 1-7, got {move!r}"
            )
        key = board_key(position)
        if key in red:
            raise ValueError(f"{path.name}:{number}: duplicate board at {position!r}")
        red[key] = (position, position + move)
    return red


def load_leaves(path):
    """steady_states.txt -> {board_key_from_diagram(diagram): diagram}.

    No position string is stored: steady_states.txt keeps one representative
    per mirror-equivalent pair (see dedupe_mirrors.py), and many move
    sequences can reach the same board besides, so a diagram's own stones are
    the only reliable way to identify which board it belongs to.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    entries = parse_entries(text, source=path.name)
    leaves = {}
    for diagram, number in entries:
        key = board_key_from_diagram(diagram)
        if key in leaves:
            raise ValueError(f"{path.name}:{number}: diagram repeats an earlier board")
        leaves[key] = diagram
    return leaves


def diagram_from_ss(ss):
    """Graph representation (rows of ordinals, top row first) -> list of str."""
    return ["".join(chr(value) for value in row) for row in ss]


def ss_from_diagram(diagram):
    """List of str -> graph representation. '.' is normalized to a space."""
    return [[ord(" " if ch == "." else ch) for ch in row] for row in diagram]


def parse_entries(text, source="steady_states.txt"):
    """Parse the diagram file: blocks of six grid rows, top row first.

    Blank lines and '#' comments are ignored between blocks. There is no
    position line: a diagram's own stones are its board, since one diagram
    can serve several move sequences and steady_states.txt keeps only one
    representative per mirror-equivalent pair (see dedupe_mirrors.py).
    Returns [(diagram, line_number)]. Raises ValueError with a line number on
    any format error, including two diagrams that draw the same board.
    """
    lines = []
    for number, raw in enumerate(text.splitlines(), start=1):
        # Trailing spaces are kept, because a space is a legal claimeven and a
        # row ending in one must be reported rather than silently becoming
        # short. A stripped comment, though, leaves whitespace that was never the
        # contributor's, so drop that.
        content, hash_mark, _ = raw.partition("#")
        content = content.rstrip() if hash_mark else content.rstrip("\r\n")
        if content.strip():
            lines.append((number, content))

    entries = []
    index = 0
    while index < len(lines):
        first_number = lines[index][0]
        if len(lines) - index < ROWS:
            raise ValueError(
                f"{source}:{first_number}: fewer than {ROWS} grid rows remain"
            )
        diagram = []
        for offset in range(ROWS):
            row_number, row = lines[index + offset]
            if " " in row:
                raise ValueError(
                    f"{source}:{row_number}: write claimeven as '.', not a space "
                    "(trailing spaces are invisible and get stripped)"
                )
            if len(row) != COLS:
                raise ValueError(
                    f"{source}:{row_number}: grid row must be exactly {COLS} "
                    f"characters, got {len(row)} ({row!r})"
                )
            unknown = set(row) - KNOWN
            if unknown:
                raise ValueError(
                    f"{source}:{row_number}: unknown characters {sorted(unknown)}"
                )
            diagram.append(row)
        entries.append((diagram, first_number))
        index += ROWS

    # Keyed by the board the diagram draws, not by position: there is no
    # position here to key by, and this is the only way to notice two
    # diagrams that describe the same board.
    seen = {}
    for diagram, number in entries:
        key = board_key_from_diagram(diagram)
        if key in seen:
            raise ValueError(
                f"{source}:{number}: diagram repeats the board from line {seen[key]}"
            )
        seen[key] = number
    return entries


def board_has_four(board):
    for y in range(ROWS):
        for x in range(COLS):
            player = board[y][x]
            if player and makes_four(board, x, y, player):
                return True
    return False


def entry_problem(diagram):
    """Check a diagram is a sane place to plant a steady state; message or None.

    There is no position to cross-check the stones against any more: the
    diagram's own stones are its board (see board_from_diagram).
    """
    board = board_from_diagram(diagram)
    if board_has_four(board):
        return "the game is already over at this board"
    return None


# --------------------------------------------------------------------------
# modes
# --------------------------------------------------------------------------

def _red_wins_now(board, x):
    y = col_height(board, x)
    if y >= ROWS:
        return False
    board[y][x] = 1
    won = makes_four(board, x, y, 1)
    board[y][x] = 0
    return won


def check_graph(branches_path, entries_path, jobs):
    """Structural integrity of solution/, plus an exhaustive check of every
    diagram leaf. Combinatorial: no search, no solver.

    branches.txt only records Red's committed moves (see filter_branches.py);
    Yellow's replies are forced by the rules of the game, not chosen, so they
    are re-derived here by enumerating Yellow's legal moves rather than read
    from a file. Together with a verified diagram at every leaf, this IS the
    proof that Red wins: Red commits to one legal move, Yellow's replies are
    all covered except the ones that hand Red an immediate win, and every line
    ends in a diagram that wins. Nothing here needs to know whether a move is
    objectively best; the subtree below it is its own certificate.
    """
    red = load_branches(branches_path)
    leaves = load_leaves(entries_path)

    def mirror_key(key):
        return tuple(row[::-1] for row in key)

    def canon(key):
        return min(key, mirror_key(key))

    def is_leaf(key):
        # steady_states.txt keeps only one representative per mirror-equivalent
        # pair (see dedupe_mirrors.py), so the mirror image of a stored leaf is
        # just as much a leaf even though it has no entry of its own.
        return key in leaves or mirror_key(key) in leaves

    def red_lookup(key):
        """(position, child) for a Red board, reflecting branches.txt's own
        mirror-equivalent representative (see migrate_branches_format.py) if
        the board is only stored under its mirror image.
        """
        if key in red:
            return red[key]
        mirror_entry = red.get(mirror_key(key))
        if mirror_entry is None:
            return None
        rep_position, rep_child = mirror_entry
        position = mirror_position(rep_position)
        move = str(8 - int(rep_child[-1]))
        return position, position + move

    def label(diagram):
        return "/".join(diagram)

    failures = []

    def report(identifier, message):
        print(f"FAILURE: {identifier}: {message}", file=sys.stderr)
        failures.append([identifier, message])

    for key in red:
        if is_leaf(key):
            report(red[key][0], "position is both a branch and a leaf")

    root_key = board_key("")
    if red_lookup(root_key) is None:
        raise AssertionError("the root (empty board) is not a Red branching node")

    # A single traversal proves reachability, edge legality, and Yellow
    # coverage together: any board this walk cannot reach or explain is a
    # structural failure, and nothing outside this walk is part of the proof.
    seen = set()
    stack = [root_key]
    while stack:
        key = stack.pop()
        if key in seen:
            continue
        seen.add(key)
        if is_leaf(key):
            continue
        entry = red_lookup(key)
        if entry is None:
            # Neither a branch nor a leaf is required at a Red-to-move node
            # where Red can just win on the spot; there is nothing to commit
            # to or prove beyond that.
            board = [list(row) for row in key]
            if any(_red_wins_now(board, x) for x in range(COLS)):
                continue
            report(None, f"board reachable from root has no entry: {key}")
            continue

        position, child = entry
        board = board_from_position(position)
        legal = set()
        for x in range(COLS):
            y = col_height(board, x)
            if y >= ROWS:
                continue
            board[y][x] = 1
            legal.add(tuple(tuple(row) for row in board))
            board[y][x] = 0

        child_key = board_key(child)
        if child_key not in legal:
            report(position, "edge is not a single legal Red move")
            continue

        yellow_board = board_from_position(child)
        for x in range(COLS):
            y = col_height(yellow_board, x)
            if y >= ROWS:
                continue
            yellow_board[y][x] = 2
            won = makes_four(yellow_board, x, y, 2)
            after_key = tuple(tuple(row) for row in yellow_board)
            # A reply that wins refutes the branch outright, so it has to be
            # rejected before anything else is consulted. An entry for the board
            # it leaves behind describes a game that is already over.
            if won:
                yellow_board[y][x] = 0
                report(child, f"Yellow wins with the reply in column {x + 1}")
                continue
            if red_lookup(after_key) is not None or is_leaf(after_key):
                yellow_board[y][x] = 0
                stack.append(after_key)
                continue
            # only excusable reason to omit a reply: it hands Red an instant win.
            # Checked with Yellow's stone still on the board, since that move is
            # exactly what creates Red's winning reply.
            excused = any(_red_wins_now(yellow_board, c) for c in range(COLS))
            yellow_board[y][x] = 0
            if not excused:
                report(child, f"Yellow reply in column {x + 1} is uncovered")

    # A branch or leaf may be visited only in its mirror orientation, since its
    # twin was dropped from branches.txt/steady_states.txt, so compare
    # canonical (mirror-folded) keys instead of requiring the exact stored
    # board to have been seen.
    seen_canon = {canon(key) for key in seen}
    unreachable_red = [key for key in red if canon(key) not in seen_canon]
    unreachable_leaves = [key for key in leaves if canon(key) not in seen_canon]

    for key in unreachable_red:
        report(red[key][0], "unreachable from root")
    for key in unreachable_leaves:
        report(label(leaves[key]), "unreachable from root")

    items, item_labels = [], []
    for diagram in leaves.values():
        unknown = {ch for row in diagram for ch in row} - KNOWN
        if unknown:
            report(label(diagram), f"unknown diagram characters {sorted(unknown)}")
            continue
        items.append(diagram)
        item_labels.append(label(diagram))

    verdicts = verify_all(items, jobs)
    for item_label, ok in zip(item_labels, verdicts):
        if not ok:
            report(item_label, "diagram fails against some Yellow line")

    return {
        "mode": "graph",
        "nodes": len(red) + len(leaves),
        "diagram_leaves_verified": sum(verdicts),
        "failures": failures[:20],
        "failure_count": len(failures),
    }


def check_entries(entries_path, branches_path, jobs, baseline_path=None):
    path = Path(entries_path)
    entries = parse_entries(
        path.read_text(encoding="utf-8") if path.exists() else "", source=path.name
    )

    skipped = 0
    if baseline_path is not None:
        baseline = Path(baseline_path)
        unchanged = {
            tuple(diagram)
            for diagram, _line in parse_entries(
                baseline.read_text(encoding="utf-8") if baseline.exists() else "",
                source=baseline.name,
            )
        }
        before = len(entries)
        entries = [e for e in entries if tuple(e[0]) not in unchanged]
        skipped = before - len(entries)

    # Keyed by board, not by a move string: there is no position here to key
    # by, and branches.txt itself only keys by board (see load_branches).
    branching = set(load_branches(branches_path))

    problems = [entry_problem(diagram) for diagram, _ in entries]
    verdicts = verify_all(
        [diagram for (diagram, _), problem in zip(entries, problems) if problem is None],
        jobs,
    )
    verdicts = iter(verdicts)

    results, failures = [], []
    for (diagram, number), problem in zip(entries, problems):
        if problem is None and not next(verdicts):
            problem = "diagram fails against some Yellow line"
        results.append({
            "line": number,
            "valid": problem is None,
            "reduces": board_key_from_diagram(diagram) in branching,
        })
        if problem:
            print(f"FAILURE: line {number}: {problem}", file=sys.stderr)
            failures.append([number, problem])

    return {
        "mode": "entries",
        "entries": len(entries),
        "unchanged_skipped": skipped,
        "verified": sum(1 for r in results if r["valid"]),
        "no_reduction": [r["line"] for r in results if r["valid"] and not r["reduces"]],
        "results": results,
        "failures": failures[:20],
        "failure_count": len(failures),
    }

def markdown(report):
    out = []
    if report["mode"] == "entries":
        out.append("### Diagram verification\n")
        out.append(f"**{report['verified']} of {report['entries']} new diagram(s) "
                   f"verified**, {report['unchanged_skipped']} unchanged skipped.\n")
        if report["failures"]:
            out.append("| line | problem |")
            out.append("| --- | --- |")
            out += [f"| `{line}` | {why} |" for line, why in report["failures"]]
            out.append("")
        if report["no_reduction"]:
            out.append("Valid but not branching boards of the current graph, so they "
                       "remove nothing (line numbers): "
                       + ", ".join(f"`{line}`" for line in report["no_reduction"][:10]) + "\n")
    elif report["mode"] == "graph":
        out.append("### Whole-graph check\n")
        out.append(f"{report['nodes']:,} nodes, "
                   f"{report['diagram_leaves_verified']:,} diagram leaves verified, "
                   f"{report['failure_count']} failure(s).\n")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branches", default=DEFAULT_BRANCHES, type=Path,
                        help="branch file to check (default: solution/branches.txt)")
    parser.add_argument("--baseline", type=Path, default=None,
                        help="with --entries: skip entries unchanged from this file")
    parser.add_argument("--jobs", type=int, default=0, metavar="N",
                        help="parallel processes (default: one per core)")
    parser.add_argument("--markdown", action="store_true",
                        help="print a short report instead of JSON")
    args = parser.parse_args()

    jobs = args.jobs or (os.cpu_count() or 1)
    started = time.time()
    try:
        report = check_graph(args.branches, DEFAULT_ENTRIES, jobs)
    except (ValueError, AssertionError) as error:
        # Malformed entries and broken graphs are ordinary results here, not
        # crashes: report them the way a contributor needs to read them.
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)

    report["status"] = "OK" if not report["failure_count"] else "FAILED"
    report["seconds"] = round(time.time() - started, 1)
    print(markdown(report) if args.markdown else json.dumps(report, indent=2, sort_keys=True))
    sys.exit(1 if report["failure_count"] else 0)


if __name__ == "__main__":
    main()
