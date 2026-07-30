"""Build representations/webclient/graph.js from solution/.

    python render.py            # regenerate graph.js
    python render.py --check    # fail if the committed graph.js is stale
    python render.py --report   # print node counts as JSON, write nothing

solution/branches.json and solution/steady_states.json only record what a Red
node commits to and what a leaf's diagram is (see solution/validate_solution.py
for why). Everything else - Yellow's covered replies, and the mirror twin of
any node that was deduped away - is re-derived here exactly as
validate_solution.check_graph re-derives it, by walking the game from the
root. A Red-to-move board with no entry in either file needs neither, because
Red already has an immediate win there; such boards are simply not rendered,
since there is nothing further to click through to.

3D layout comes from representations/webclient/positions.txt, which still has
one entry per board of the original (undeduped) graph. A board only reachable
in its mirror orientation borrows its mirror twin's coordinates, with x
negated.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SOLUTION_DIR = Path(__file__).resolve().parent.parent.parent / "solution"
sys.path.insert(0, str(SOLUTION_DIR))
import validate_solution as solution  # noqa: E402

HERE = Path(__file__).resolve().parent
BRANCHES = SOLUTION_DIR / "branches.json"
STEADY_STATES = SOLUTION_DIR / "steady_states.json"
POSITIONS = HERE / "positions.txt"
OUT_JS = HERE / "graph.js"

BOARD_H, BOARD_W, GAME_NAME = solution.ROWS, solution.COLS, "c4"
BLANK_SS = ["       " for _ in range(BOARD_H)]


def mirror_key(key):
    return tuple(row[::-1] for row in key)


def load_positions(path):
    """positions.txt -> {board_key: (x, y, z)}, keyed by board rather than the
    stored position string, so a board reachable only through its mirror twin
    can still be found."""
    coords = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            continue
        position, x, y, z = raw.split(",")
        coords[solution.board_key(position)] = (float(x), float(y), float(z))
    return coords


def lookup_coords(coords, key):
    if key in coords:
        return coords[key]
    x, y, z = coords[mirror_key(key)]
    return -x, y, z


def build_graph(branches_path, entries_path, positions_path):
    with open(branches_path, "r") as f:
        pre = json.load(f)
        red = {}
        for bs, move in pre.items():
            red[solution.board_key(bs)] = move
    with open(entries_path, "r") as f:
        raw_leaves = json.load(f)
        leaves = {solution.board_key_from_diagram(diagram): diagram for diagram in raw_leaves}
    coords = load_positions(positions_path)

    def is_leaf(key):
        return key in leaves or mirror_key(key) in leaves

    def leaf_diagram(key):
        if key in leaves:
            return leaves[key]
        return solution.mirror_diagram(leaves[mirror_key(key)])

    def red_lookup(key):
        """Red's move at this board, reflecting branches.json's own
        mirror-equivalent representative if the board is only stored under
        its mirror image. Mirrors validate_solution.check_yellow_children.
        """
        if key in red:
            return red[key]
        mirror_move = red.get(mirror_key(key))
        if mirror_move is None:
            return None
        return str(8 - int(mirror_move))

    nodes = {}
    root_key = solution.board_key("")
    seen = set()
    # A board's name is assigned exactly once, at first discovery, and every
    # later edge into it - however it computes its own candidate string, and
    # transpositions mean two parents can compute different ones - reuses that
    # same name instead of inventing a second one nothing will ever build.
    canonical = {root_key: ""}

    def name_for(key, candidate_position):
        if key not in canonical:
            canonical[key] = candidate_position
            stack.append((key, candidate_position))
        return canonical[key]

    stack = [(root_key, "")]
    while stack:
        key, position = stack.pop()
        if key in seen:
            continue
        seen.add(key)
        x, y, z = lookup_coords(coords, key)
        red_to_move = len(position) % 2 == 0

        if red_to_move:
            if is_leaf(key):
                diagram = leaf_diagram(key)
                nodes[position] = {
                    "data": {"ss": diagram},
                    "neighbors": None,
                    "rep": position, "x": x, "y": y, "z": z,
                }
                continue
            move = red_lookup(key)
            if move is None:
                board = [list(row) for row in key]
                if any(solution._red_wins_now(board, c) for c in range(BOARD_W)):
                    continue  # instant win: nothing to render past here
                raise AssertionError(f"no branch or leaf for reachable board at {position!r}")
            child_key = solution.board_key(position + move)
            child_position = name_for(child_key, position + move)
            nodes[position] = {
                "data": {"ss": BLANK_SS},
                "neighbors": [child_position],
                "rep": position, "x": x, "y": y, "z": z,
            }
            continue

        # Yellow to move: enumerate legal replies, skipping the ones that hand
        # Red an immediate win (those need no node of their own either).
        board = solution.board_from_position(position)
        children = []
        for col in range(BOARD_W):
            row = solution.col_height(board, col)
            if row >= BOARD_H:
                continue
            board[row][col] = 2
            won = solution.makes_four(board, col, row, 2)
            after_key = tuple(tuple(r) for r in board)
            covered = not won and (red_lookup(after_key) is not None or is_leaf(after_key))
            excused = not won and any(solution._red_wins_now(board, c) for c in range(BOARD_W))
            board[row][col] = 0
            if covered:
                children.append(name_for(after_key, position + str(col + 1)))
            elif not excused:
                raise AssertionError(
                    f"Yellow reply in column {col + 1} at {position!r} is uncovered"
                )
        nodes[position] = {
            "data": {"ss": BLANK_SS},
            "neighbors": children,
            "rep": position, "x": x, "y": y, "z": z,
        }

    return {
        "board_h": BOARD_H,
        "board_w": BOARD_W,
        "game_name": GAME_NAME,
        "nodes_to_use": nodes,
        "root_node_hash": "",
    }


def render_js(dataset):
    return "var dataset = " + json.dumps(dataset, ensure_ascii=False, separators=(",", ":"))


def build(branches_path=BRANCHES, entries_path=STEADY_STATES, positions_path=POSITIONS):
    dataset = build_graph(branches_path, entries_path, positions_path)
    nodes = dataset["nodes_to_use"]
    leaves = sum(1 for node in nodes.values() if node["neighbors"] is None)
    report = {"nodes": len(nodes), "leaves": leaves, "branches": len(nodes) - leaves}
    artifacts = {OUT_JS: render_js(dataset).encode("utf-8")}
    return artifacts, report


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branches", type=Path, default=BRANCHES)
    parser.add_argument("--entries", type=Path, default=STEADY_STATES)
    parser.add_argument("--positions", type=Path, default=POSITIONS)
    parser.add_argument("--check", action="store_true",
                        help="compare against the committed graph.js, write nothing")
    parser.add_argument("--report", action="store_true",
                        help="print node counts as JSON, write nothing")
    args = parser.parse_args()

    try:
        artifacts, report = build(args.branches, args.entries, args.positions)
    except (ValueError, AssertionError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)

    if args.check:
        report["stale"] = [
            path.name for path, content in artifacts.items()
            if not path.exists() or path.read_bytes() != content
        ]
        report["status"] = "OK" if not report["stale"] else "STALE"
    elif args.report:
        report["status"] = "OK"
    else:
        for path, content in artifacts.items():
            path.write_bytes(content)
        report["written"] = sorted(path.name for path in artifacts)
        report["status"] = "OK"

    print(json.dumps(report, indent=2, sort_keys=True))
    sys.exit(1 if report["status"] != "OK" else 0)


if __name__ == "__main__":
    main()
