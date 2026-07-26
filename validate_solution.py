"""Check a WeakC4 solution: the shape of the graph and every diagram in it.

Standalone, Python standard library only. This file is the machine-readable
definition of "valid solution" for this repository.

    python validate_solution.py                 # check all of c4_full.js
    python validate_solution.py --entries       # check steady_states.txt
    python validate_solution.py --self-test 200 # check this code itself

Red's move follows the priority list from the explanation page: win, block,
'!' urgent, '@' miai (only when exactly one is playable), '|' claimodd on an
odd row or claimeven (space) on an even row, '+', '=', '-'. A diagram is valid
at a position when Red wins from there against every legal Yellow reply.

The site guarantees the applicable level always identifies exactly one move, so
a tie invalidates the diagram, and claimodd/claimeven share one level. The
original generator agreed: SteadyState.cpp returned an error code on a tie. It
lived in swaptube until 2swap/swaptube@e46484b removed it.

The viewer, client.js, is looser and takes the leftmost of a tie, so a
diagram can work on the site and still be rejected here.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import random
import re
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
DEFAULT_GRAPH = HERE / "c4_full.js"
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


def verify_leaf(position, diagram):
    """True iff Red, following the diagram, beats every Yellow continuation.

    Depends on nothing but its two arguments, which is why a diagram already in
    the graph never needs rechecking when a different one is added.
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

    board = board_from_position(position)
    if board_has_four(board):
        return False  # somebody has already won; nothing to play for
    return red_turn(board)


def _verify_one(item):
    # multiprocessing pickles the worker by qualified name, so this has to be a
    # module-level function. A lambda or a closure over verify_leaf will not
    # pickle. It exists only to unpack one tuple per task.
    return verify_leaf(*item)


def verify_all(items, jobs):
    """Verify [(position, diagram)], optionally across processes."""
    if jobs > 1 and len(items) > 1:
        with multiprocessing.Pool(jobs) as pool:
            return list(pool.imap(_verify_one, items, chunksize=8))
    return [_verify_one(item) for item in items]


# --------------------------------------------------------------------------
# graph and entry-file I/O
# --------------------------------------------------------------------------

def load_dataset(path):
    text = Path(path).read_text(encoding="utf-8")
    match = re.fullmatch(r"\s*var\s+dataset\s*=\s*(\{.*\})\s*;?\s*", text, re.S)
    if not match:
        raise ValueError(f"{path} is not a recognizable WeakC4 dataset")
    return json.loads(match.group(1))


def diagram_from_ss(ss):
    """Graph representation (rows of ordinals, top row first) -> list of str."""
    return ["".join(chr(value) for value in row) for row in ss]


def ss_from_diagram(diagram):
    """List of str -> graph representation. '.' is normalized to a space."""
    return [[ord(" " if ch == "." else ch) for ch in row] for row in diagram]


def parse_entries(text, source="steady_states.txt"):
    """Parse the contribution file: a position line then six grid rows.

    Blank lines and '#' comments are ignored. Returns [(position, diagram,
    line_number)]. Raises ValueError with a line number on any format error.
    """
    lines = []
    for number, raw in enumerate(text.splitlines(), start=1):
        # Trailing spaces are kept, because a space is a legal claimeven and a
        # row ending in one must be reported rather than silently becoming
        # short. A stripped comment, though, leaves whitespace that was never the
        # contributor's, so drop that.
        content, _, comment = raw.partition("#")
        content = content.rstrip() if comment else content.rstrip("\r\n")
        if content.strip():
            lines.append((number, content))

    entries = []
    index = 0
    while index < len(lines):
        number, position = lines[index]
        position = position.strip()
        if not all(ch in "1234567" for ch in position) or not position:
            raise ValueError(
                f"{source}:{number}: expected a position (digits 1-7), got {position!r}"
            )
        if len(position) % 2:
            raise ValueError(
                f"{source}:{number}: position {position} is Yellow to move; "
                "diagrams are only defined for Red to move (even length)"
            )
        try:
            board_from_position(position)
        except ValueError:
            raise ValueError(
                f"{source}:{number}: position {position} overflows a column"
            ) from None
        if len(lines) - index - 1 < ROWS:
            raise ValueError(
                f"{source}:{number}: position {position} has fewer than {ROWS} grid rows"
            )
        diagram = []
        for offset in range(ROWS):
            row_number, row = lines[index + 1 + offset]
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
        entries.append((position, diagram, number))
        index += 1 + ROWS

    # Keyed by board, not by the move string: two different move orders can
    # reach the same position, and the second would otherwise silently
    # overwrite the first when the graph is built.
    seen = {}
    for position, _diagram, number in entries:
        key = tuple(tuple(row) for row in board_from_position(position))
        if key in seen:
            first_position, first_line = seen[key]
            same = " " if first_position == position else " the same board as "
            raise ValueError(
                f"{source}:{number}: position {position} repeats{same}"
                f"{first_position} from line {first_line}"
            )
        seen[key] = (position, number)
    return entries


def board_has_four(board):
    for y in range(ROWS):
        for x in range(COLS):
            player = board[y][x]
            if player and makes_four(board, x, y, player):
                return True
    return False


def entry_problem(position, diagram):
    """Check an entry is a sane place for a diagram; returns a message or None."""
    board = board_from_position(position)
    if board_has_four(board):
        return "the game is already over at this position"
    for y in range(ROWS):
        for x in range(COLS):
            drawn = diagram[ROWS - 1 - y][x]
            actual = board[y][x]
            if actual and drawn != STONES[actual - 1]:
                return (
                    f"cell column {x + 1} row {y + 1} holds "
                    f"{'Red' if actual == 1 else 'Yellow'} but the grid shows {drawn!r}"
                )
            if not actual and drawn in STONES:
                return f"cell column {x + 1} row {y + 1} is empty but the grid shows a stone"
    return None


# --------------------------------------------------------------------------
# modes
# --------------------------------------------------------------------------

def check_structure(nodes):
    """Check the strategy's shape. Combinatorial: no search, no solver.

    Together with a verified diagram at every leaf, these four rules ARE the
    proof that Red wins: Red commits to one legal move, Yellow's replies are
    all covered except the ones that hand Red an immediate win, and every line
    ends in a diagram that wins. Nothing here needs to know whether a move is
    objectively best; the subtree below it is its own certificate.
    """
    def board_key(position):
        return tuple(tuple(row) for row in board_from_position(position))

    failures = []
    for node_hash, node in nodes.items():
        position, neighbors = node["rep"], node["neighbors"]
        red_to_move = len(position) % 2 == 0
        if neighbors is None:
            if not red_to_move:
                failures.append([node_hash, "leaf with Yellow to move"])
            continue

        board = board_from_position(position)
        player = 1 if red_to_move else 2
        legal = {}
        for x in range(COLS):
            y = col_height(board, x)
            if y >= ROWS:
                continue
            board[y][x] = player
            legal[x] = tuple(tuple(row) for row in board)
            board[y][x] = 0

        children = {board_key(nodes[target]["rep"]) for target in neighbors}
        if not children <= set(legal.values()):
            failures.append([node_hash, "an edge is not a single legal move"])
            continue
        if red_to_move:
            if len(neighbors) != 1:
                failures.append(
                    [node_hash, f"Red must commit to one move, has {len(neighbors)}"])
            continue

        for x, after in legal.items():
            if after in children:
                continue
            y = col_height(board, x)
            board[y][x] = 2
            # only excusable reason to omit a reply: it hands Red an instant win
            excused = not makes_four(board, x, y, 2) and any(
                _red_wins_now(board, c) for c in range(COLS))
            board[y][x] = 0
            if not excused:
                failures.append(
                    [node_hash, f"Yellow reply in column {x + 1} is uncovered"])
    return failures


def _red_wins_now(board, x):
    y = col_height(board, x)
    if y >= ROWS:
        return False
    board[y][x] = 1
    won = makes_four(board, x, y, 1)
    board[y][x] = 0
    return won


def check_graph(graph_path, jobs):
    """Structural integrity, plus an exhaustive check of every diagram leaf."""
    dataset = load_dataset(graph_path)
    nodes = dataset["nodes_to_use"]

    # Everything below proves Red wins *from the root*, so the root has to be
    # the empty board for that to mean what it says.
    if nodes[dataset["root_node_hash"]]["rep"]:
        raise AssertionError("the graph root is not the empty board")

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

    failures = check_structure(nodes)
    items, item_hashes = [], []
    for node_hash, node in nodes.items():
        if node["neighbors"] is not None:
            continue
        position = node["rep"]
        ss = node["data"].get("ss")
        if ss is None:
            # check_structure already requires every leaf to be Red to move, so
            # there is no such thing here as a leaf that is a finished Red win.
            failures.append([node_hash, "leaf has no diagram"])
            continue
        diagram = diagram_from_ss(ss)
        unknown = {ch for row in diagram for ch in row} - KNOWN
        if unknown:
            failures.append([node_hash, f"unknown diagram characters {sorted(unknown)}"])
            continue
        items.append((position, diagram))
        item_hashes.append(node_hash)

    verdicts = verify_all(items, jobs)
    for node_hash, ok in zip(item_hashes, verdicts):
        if not ok:
            failures.append([node_hash, "diagram fails against some Yellow line"])

    return {
        "mode": "graph",
        "nodes": len(nodes),
        "diagram_leaves_verified": sum(verdicts),
        "failures": failures[:20],
        "failure_count": len(failures),
    }


def check_entries(entries_path, graph_path, jobs, baseline_path=None):
    path = Path(entries_path)
    entries = parse_entries(
        path.read_text(encoding="utf-8") if path.exists() else "", source=path.name
    )

    skipped = 0
    if baseline_path is not None:
        baseline = Path(baseline_path)
        unchanged = {
            (position, tuple(diagram))
            for position, diagram, _line in parse_entries(
                baseline.read_text(encoding="utf-8") if baseline.exists() else "",
                source=baseline.name,
            )
        }
        before = len(entries)
        entries = [e for e in entries if (e[0], tuple(e[1])) not in unchanged]
        skipped = before - len(entries)

    # Keyed by board, not by the move string: the graph stores one canonical
    # representative per position, and a contributor may well reach the same
    # board by a different order. build_graph.py matches the same way.
    branching = set()
    if Path(graph_path).exists():
        branching = {
            tuple(tuple(row) for row in board_from_position(node["rep"]))
            for node in load_dataset(graph_path)["nodes_to_use"].values()
            if node["neighbors"] is not None
        }

    problems = [entry_problem(position, diagram) for position, diagram, _ in entries]
    verdicts = verify_all(
        [(position, diagram) for (position, diagram, _), problem
         in zip(entries, problems) if problem is None],
        jobs,
    )
    verdicts = iter(verdicts)

    results, failures = [], []
    for (position, _diagram, number), problem in zip(entries, problems):
        if problem is None and not next(verdicts):
            problem = "diagram fails against some Yellow line"
        results.append({
            "position": position,
            "line": number,
            "valid": problem is None,
            "reduces": tuple(tuple(row) for row in board_from_position(position)) in branching,
        })
        if problem:
            failures.append([position, problem])
        print(f"{'OK  ' if problem is None else 'FAIL'} {position}"
              f"{'' if problem is None else '  ' + problem}", file=sys.stderr)

    return {
        "mode": "entries",
        "entries": len(entries),
        "unchanged_skipped": skipped,
        "verified": sum(1 for r in results if r["valid"]),
        "no_reduction": [r["position"] for r in results if r["valid"] and not r["reduces"]],
        "results": results,
        "failures": failures[:20],
        "failure_count": len(failures),
    }


def self_test(graph_path, samples):
    """Mirror invariance of the policy: reflecting the board and the diagram
    must reflect the chosen move and change nothing else.

    This is narrow on purpose, and it is worth being clear about what it does
    not cover. It tests one property, that no tie is silently broken by column
    order. It says nothing about whether the priority order is right, whether
    win and block really precede the markers, or whether the search in
    verify_leaf is correct. Those are checked by running the whole graph.

    The diagrams must be RANDOM for even that one property to be tested. A
    valid diagram never reaches a tie, which is what makes it valid, so
    replaying shipped diagrams exercises no tie handling and passes even
    against a deliberately left-biased policy. Random diagrams hit ties
    constantly.
    """
    nodes = load_dataset(graph_path)["nodes_to_use"]
    positions = sorted(node["rep"] for node in nodes.values())
    rng = random.Random(0)
    palette = MARKERS.replace(".", "")  # the charset as the graph stores it

    failures = []
    no_move = 0
    for _ in range(samples):
        position = rng.choice(positions)
        board = board_from_position(position)
        diagram = [
            "".join(
                STONES[board[ROWS - 1 - yt][x] - 1] if board[ROWS - 1 - yt][x]
                else rng.choice(palette)
                for x in range(COLS)
            )
            for yt in range(ROWS)
        ]
        direct = query_steady_state(board, diagram)
        reflected = query_steady_state(
            [row[::-1] for row in board], mirror_diagram(diagram)
        )
        expected = None if direct is None else 8 - direct
        no_move += direct is None
        if reflected != expected:
            failures.append(
                [position, f"chose {direct}, mirrored chose {reflected}, wanted {expected}"]
            )

    return {
        "mode": "self-test",
        "samples": samples,
        "no_move_states_sampled": no_move,
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
            out.append("| position | problem |")
            out.append("| --- | --- |")
            out += [f"| `{p}` | {why} |" for p, why in report["failures"]]
            out.append("")
        if report["no_reduction"]:
            out.append("Valid but not branching nodes of the current graph, so they "
                       "remove nothing: "
                       + ", ".join(f"`{p}`" for p in report["no_reduction"][:10]) + "\n")
    elif report["mode"] == "graph":
        out.append("### Whole-graph check\n")
        out.append(f"{report['nodes']:,} nodes, "
                   f"{report['diagram_leaves_verified']:,} diagram leaves verified, "
                   f"{report['failure_count']} failure(s).\n")
    else:
        out.append(f"### Verifier self-test\n\n{report['samples']} samples, "
                   f"{report['failure_count']} mismatch(es).\n")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--graph", default=DEFAULT_GRAPH, type=Path,
                        help="graph file to check (default: c4_full.js)")
    parser.add_argument("--entries", nargs="?", const=DEFAULT_ENTRIES, default=None,
                        type=Path, help="check steady_states.txt instead of the graph")
    parser.add_argument("--baseline", type=Path, default=None,
                        help="with --entries: skip entries unchanged from this file")
    parser.add_argument("--self-test", type=int, default=0, metavar="N",
                        help="mirror-invariance self-test over N random diagrams")
    parser.add_argument("--jobs", type=int, default=0, metavar="N",
                        help="parallel processes (default: one per core)")
    parser.add_argument("--markdown", action="store_true",
                        help="print a short report instead of JSON")
    args = parser.parse_args()

    jobs = args.jobs or (os.cpu_count() or 1)
    started = time.time()
    try:
        if args.self_test:
            report = self_test(args.graph, args.self_test)
        elif args.entries is not None:
            report = check_entries(args.entries, args.graph, jobs, args.baseline)
        else:
            report = check_graph(args.graph, jobs)
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
