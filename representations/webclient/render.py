"""Build representations/webclient/graph.js from solution/.

    python render.py            # regenerate graph.js
    python render.py --report   # print node counts as JSON, write nothing

solution/branches.json and solution/steady_states.json only record what a Red
node commits to or which diagram it follows (see solution/validate_solution.py
for why). Everything else - Yellow's covered replies, and the mirror twin of
any node that was deduped away - is re-derived here exactly as
validate_solution.check_graph re-derives it, by walking the game from the
root. A Red-to-move board with no entry in either file needs neither, because
Red already has an immediate win there; such boards are simply not rendered,
since there is nothing further to click through to.
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
sys.path.insert(0, str(HERE))
import spread_graph  # noqa: E402

BRANCHES = SOLUTION_DIR / "branches.json"
STEADY_STATES = SOLUTION_DIR / "steady_states.json"
OUT_JS = HERE / "graph.js"

BOARD_H, BOARD_W, GAME_NAME = solution.ROWS, solution.COLS, "c4"
BLANK_SS = [" " * BOARD_W for _ in range(BOARD_H)]   # non-leaf node: no diagram


def mirror_key(key):
    return tuple(row[::-1] for row in key)


def overlay_disks(board, diagram):
    """The diagram with each of the board's disks drawn in as R/Y, for display."""
    return ["".join("RY"[board[solution.ROWS - 1 - r][x] - 1] if board[solution.ROWS - 1 - r][x] else ch
                    for x, ch in enumerate(row))
            for r, row in enumerate(diagram)]


def build_graph(branches_path, entries_path):
    with open(entries_path, "r") as f:
        diagrams = json.load(f)
    with open(branches_path, "r") as f:
        pre = json.load(f)
    red = {}
    leaves = {}
    for bs, value in pre.items():
        if solution.is_steady_state_entry(value):
            # graph.js diagrams draw their own disks, as client.js expects.
            board = solution.board_from_position(bs)
            leaves[solution.board_key(bs)] = overlay_disks(board, diagrams[value])
        else:
            red[solution.board_key(bs)] = value

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
        red_to_move = len(position) % 2 == 0

        if red_to_move:
            if is_leaf(key):
                diagram = leaf_diagram(key)
                nodes[position] = {
                    "data": {"ss": diagram},
                    "neighbors": None,
                    "rep": position,
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
                "rep": position,
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
            "rep": position,
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


def place_nodes(nodes):
    """Give every node its x, y, z from a fresh force-directed layout."""
    edges = [
        (name, neighbor)
        for name, node in nodes.items()
        if node["neighbors"]
        for neighbor in node["neighbors"]
    ]
    by_board = {solution.board_key(name): name for name in nodes}
    mirrors = {}
    for name in nodes:
        twin = by_board.get(mirror_key(solution.board_key(name)))
        if twin is not None:
            mirrors[name] = twin
    for name, (x, y, z) in spread_graph.layout(list(nodes), edges, mirrors).items():
        nodes[name].update(x=x, y=y, z=z)


def count(nodes):
    leaves = sum(1 for node in nodes.values() if node["neighbors"] is None)
    return {"nodes": len(nodes), "leaves": leaves, "branches": len(nodes) - leaves}


def build(branches_path=BRANCHES, entries_path=STEADY_STATES):
    dataset = build_graph(branches_path, entries_path)
    nodes = dataset["nodes_to_use"]
    place_nodes(nodes)
    artifacts = {OUT_JS: render_js(dataset).encode("utf-8")}
    return artifacts, count(nodes)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branches", type=Path, default=BRANCHES)
    parser.add_argument("--entries", type=Path, default=STEADY_STATES)
    parser.add_argument("--report", action="store_true",
                        help="print node counts as JSON, write nothing")
    args = parser.parse_args()

    try:
        if args.report:
            # Counting needs only the graph, not the much slower layout.
            report = count(build_graph(args.branches, args.entries)["nodes_to_use"])
        else:
            artifacts, report = build(args.branches, args.entries)
    except (ValueError, AssertionError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)

    if not args.report:
        for path, content in artifacts.items():
            path.write_bytes(content)
        report["written"] = sorted(path.name for path in artifacts)
    report["status"] = "OK"

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
