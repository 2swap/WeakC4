"""Force-directed 3D layout for solution/positions.txt.

Every pair of nodes repels, and every edge attracts.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEBCLIENT_DIR = HERE.parent / "representations" / "webclient"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WEBCLIENT_DIR))
import validate_solution as solution  # noqa: E402
import render  # noqa: E402

POSITIONS = HERE / "positions.txt"

DEFAULT_ITERATIONS = 10
DEFAULT_DT = 1


def mirror_key(key):
    return tuple(row[::-1] for row in key)


def repulsion_force(pi, pj):
    """Runs between every pair of nodes."""
    dx, dy, dz = pi[0] - pj[0], pi[1] - pj[1], pi[2] - pj[2]
    dist_sq = dx * dx + dy * dy + dz * dz + 1.0
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length < 1e-9:
        return 0.0, 0.0, 0.0
    scale = 1.0 / (length * (dist_sq * 10.0 + 2.0))
    return dx * scale, dy * scale, dz * scale


def attraction_force(pi, pj):
    """Runs between every pair of neighbors."""
    dx, dy, dz = pi[0] - pj[0], pi[1] - pj[1], pi[2] - pj[2]
    dist_sq = dx * dx + dy * dy + dz * dz
    length = math.sqrt(dist_sq)
    if length < 1e-9:
        return 0.0, 0.0, 0.0
    dist_6th = dist_sq * dist_sq * dist_sq * 0.05
    # Crosses zero at r = 60**(1/6) ~= 1.98: a pair further apart than that is
    # pulled together, a closer one is pushed apart.
    multiplier = 0.1 - (dist_6th - 1.0) / (dist_6th + 1.0) * 0.2
    scale = multiplier / length
    return dx * scale, dy * scale, dz * scale


def load_graph():
    """The same node set render.py builds: names -> (x, y, z), and the edges
    (Red's committed move, plus Yellow's covered replies) that connect them.
    """
    dataset = render.build_graph(render.BRANCHES, render.STEADY_STATES, render.POSITIONS)
    nodes = dataset["nodes_to_use"]
    positions = {name: (node["x"], node["y"], node["z"]) for name, node in nodes.items()}
    edges = [
        (name, neighbor)
        for name, node in nodes.items()
        if node["neighbors"]
        for neighbor in node["neighbors"]
    ]
    return positions, edges


def relax(positions, edges, iterations, dt):
    names = list(positions)
    index = {name: i for i, name in enumerate(names)}
    pos = [list(positions[name]) for name in names]
    edge_indices = [(index[a], index[b]) for a, b in edges]
    n = len(pos)

    # The root (the empty board) is pinned at the origin forever: every other
    # node's coordinates are relative to it, so nothing else about "the
    # spread" means anything if the root itself is free to drift.
    root_index = index.get("")
    if root_index is not None:
        pos[root_index] = [0.0, 0.0, 0.0]

    for step in range(iterations):
        force = [[0.0, 0.0, 0.0] for _ in range(n)]

        for i in range(n):
            pi = pos[i]
            for j in range(i + 1, n):
                fx, fy, fz = repulsion_force(pi, pos[j])
                force[i][0] += fx; force[i][1] += fy; force[i][2] += fz
                force[j][0] -= fx; force[j][1] -= fy; force[j][2] -= fz

        for i, j in edge_indices:
            fx, fy, fz = attraction_force(pos[i], pos[j])
            force[i][0] += fx; force[i][1] += fy; force[i][2] += fz
            force[j][0] -= fx; force[j][1] -= fy; force[j][2] -= fz

        for i in range(n):
            pos[i][0] += force[i][0] * dt
            pos[i][1] += force[i][1] * dt
            pos[i][2] += force[i][2] * dt

        if root_index is not None:
            pos[root_index] = [0.0, 0.0, 0.0]

        print(f"spread progress: {step + 1}/{iterations} iterations", file=sys.stderr)

    return {name: tuple(pos[index[name]]) for name in names}


def write_positions(path, board_to_xyz):
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.startswith("#"):
            lines.append(raw)
            continue
        position = raw.split(",", 1)[0]
        key = solution.board_key(position)
        if key in board_to_xyz:
            x, y, z = board_to_xyz[key]
        elif mirror_key(key) in board_to_xyz:
            x, y, z = board_to_xyz[mirror_key(key)]
            x = -x
        else:
            # Not part of the current (deduped) graph at all: nothing moved
            # it, so its old coordinates are kept as-is.
            lines.append(raw)
            continue
        lines.append(f"{position},{repr(x)},{repr(y)},{repr(z)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--dt", type=float, default=DEFAULT_DT)
    parser.add_argument("--positions", type=Path, default=POSITIONS)
    args = parser.parse_args()

    positions, edges = load_graph()
    print(f"loaded {len(positions):,} nodes and {len(edges):,} edges", file=sys.stderr)
    relaxed = relax(positions, edges, args.iterations, args.dt)

    board_to_xyz = {solution.board_key(name): xyz for name, xyz in relaxed.items()}
    write_positions(args.positions, board_to_xyz)
    print(f"wrote {args.positions}", file=sys.stderr)


if __name__ == "__main__":
    main()
