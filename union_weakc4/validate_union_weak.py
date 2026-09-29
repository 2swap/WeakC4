import argparse
import functools
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "solution"))
import validate_solution as V

# Fhourstones scores of shallow positions, which are slow to solve.
BOOK = HERE / "opening_book.txt"
BOOK_PLY = 5


def position(node, parents):
    moves = ""
    while node is not None:
        moves = node.get("move", "") + moves
        node = parents.get(node)
    return moves


def immediate_wins(board):
    return {str(x + 1) for x in range(V.COLS) if V._red_wins_now(board, x)}


def legal_moves(board):
    return {str(x + 1) for x in range(V.COLS) if V.col_height(board, x) < V.ROWS}


def lower_bound(moves):
    """No yellow-to-move node weighs less: every reply without an immediate Red win costs at least 1."""
    board = V.board_from_position(moves)
    return 1 + sum(not immediate_wins(V.board_from_position(moves + y)) for y in legal_moves(board))


@functools.cache
def is_steady_state(solution):
    return V.verify_leaf(solution.split("/"))


def winner(binary, position):
    """Winner of a yellow-to-move position under perfect play."""
    out = subprocess.run([binary], input=position + "\n", capture_output=True, text=True, check=True).stdout
    return {"1": "red", "3": "tie", "5": "yellow"}[out.split("score = ")[1].split()[0]]


def red_winning_moves(binary, red_positions):
    winners = dict(map(str.split, BOOK.read_text().splitlines())) if BOOK.exists() else {}
    queries = sorted({p + m for p in red_positions for m in legal_moves(V.board_from_position(p))} - winners.keys(), key=len)
    with ThreadPoolExecutor(os.cpu_count()) as pool, open(BOOK, "a") as book:
        for q, w in zip(queries, pool.map(lambda q: winner(binary, q), queries)):
            winners[q] = w
            if len(q) <= BOOK_PLY:
                book.write(f"{q} {w}\n")
                book.flush()
    return {p: {m for m in "1234567" if winners.get(p + m) == "red"} for p in red_positions}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("xml")
    parser.add_argument("--fhourstones", default=os.path.expanduser("~/Fhourstones/SearchGame"))
    args = parser.parse_args()

    root = ET.parse(args.xml).getroot()
    parents = {child: node for node in root.iter() for child in node}
    failures = []

    def fail(node, message):
        failures.append(f"{position(node, parents)!r}: {message}")

    if root.tag != "root" or "move" in root.attrib:
        fail(root, "root must be a <root> node without a move")

    expanded = {}
    for node in root.iter():
        moves = position(node, parents)
        board = V.board_from_position(moves)
        children = [child.get("move") for child in node]
        kept = [child for child in node if "defer" not in child.attrib]
        child_weights = [float(child.get("weight")) for child in kept]
        weight = float(node.get("weight", -1))
        expected_tag = "root" if not moves else "red" if len(moves) % 2 else "yellow"

        if node.tag != expected_tag:
            fail(node, f"expected <{expected_tag}>")
        elif "defer" in node.attrib:
            if node.tag != "red" or children or "weight" in node.attrib:
                fail(node, "only a <red> node may be deferred, without children or weight")
        elif weight == float("inf"):
            if node.tag != "red" or children:
                fail(node, "only a childless <red> may be left unexplored at weight inf")
        elif node.tag == "red":
            if set(children) != legal_moves(board) or len(children) != len(set(children)):
                fail(node, "children must be exactly the legal Yellow replies")
            if weight != 1 + sum(child_weights):
                fail(node, f"weight should be {1 + sum(child_weights)}")
        elif immediate_wins(board):
            if node.get("winning_move") not in immediate_wins(board) or children:
                fail(node, "needs a winning_move and no children")
            if weight != 0:
                fail(node, "weight should be 0")
        elif "solution" in node.attrib:
            solution = node.get("solution")
            if V.board_key_from_diagram(solution.split("/")) != V.board_key(moves) or not is_steady_state(solution):
                fail(node, "solution is not a valid steady state for this board")
            if children:
                fail(node, "a node with a solution has no children")
            if weight != 1:
                fail(node, "weight should be 1")
        else:
            expanded[node] = moves
            if len(children) != len(set(children)):
                fail(node, "duplicate children")
            if not kept or weight != 1 + min(child_weights):
                fail(node, "weight should be 1 + the minimum non-deferred child weight")
            for child in node:
                if "defer" in child.attrib and kept and lower_bound(moves + child.get("move")) < min(child_weights):
                    fail(child, "deferred, but its lower bound is below a sibling's weight")

    winning = red_winning_moves(args.fhourstones, set(expanded.values()))
    for node, moves in expanded.items():
        if {child.get("move") for child in node} != winning[moves]:
            fail(node, f"children must be exactly the red-to-win moves {sorted(winning[moves])}")

    print("\n".join(failures) or f"OK: {sum(1 for _ in root.iter())} nodes, root weight {root.get('weight')}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
