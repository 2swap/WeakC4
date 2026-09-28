"""Force-directed 3D layout for representations/webclient/positions.txt.

Every pair of nodes repels, and every edge attracts.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SOLUTION_DIR = HERE.parent.parent / "solution"
sys.path.insert(0, str(SOLUTION_DIR))
sys.path.insert(0, str(HERE))
import validate_solution as solution  # noqa: E402
import render  # noqa: E402

POSITIONS = HERE / "positions.txt"

DEFAULT_ITERATIONS = 1
DEFAULT_DT = 5


def mirror_key(key):
    return tuple(row[::-1] for row in key)


def repulsion_forces(pos):
    """Runs between every pair of nodes. Returns the net force on each node."""
    d = pos[:, None, :] - pos[None, :, :]
    dist_sq = np.einsum("ijk,ijk->ij", d, d)
    length = np.sqrt(dist_sq)
    with np.errstate(divide="ignore"):
        scale = 1.0 / (length * ((dist_sq + 1.0) * 10.0 + 2.0))
    # Also zeroes the diagonal, where a node would repel itself.
    scale[length < 1e-9] = 0.0
    return np.einsum("ij,ijk->ik", scale, d)


def attraction_forces(pos, edges):
    """Runs between every pair of neighbors. Returns one force per edge, which
    pushes its first node and pulls its second.
    """
    d = pos[edges[:, 0]] - pos[edges[:, 1]]
    dist_sq = np.einsum("ij,ij->i", d, d)
    length = np.sqrt(dist_sq)
    dist_6th = dist_sq * dist_sq * dist_sq * 0.05
    # Crosses zero at r = 60**(1/6) ~= 1.98: a pair further apart than that is
    # pulled together, a closer one is pushed apart.
    multiplier = 0.1 - (dist_6th - 1.0) / (dist_6th + 1.0) * 0.2
    with np.errstate(divide="ignore", invalid="ignore"):
        scale = np.where(length < 1e-9, 0.0, multiplier / length)
    return d * scale[:, None]


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
    pos = np.array([positions[name] for name in names], dtype=float)
    edge_indices = np.array([(index[a], index[b]) for a, b in edges], dtype=np.intp).reshape(-1, 2)

    root_index = index.get("")
    crown_index = index.get("44444")

    for step in range(iterations):
        force = repulsion_forces(pos)

        edge_force = attraction_forces(pos, edge_indices)
        np.add.at(force, edge_indices[:, 0], edge_force)
        np.subtract.at(force, edge_indices[:, 1], edge_force)

        pos += force * dt

        # The root (the empty board) is pinned at the origin
        # Also pin the crown at the top
        pos[root_index] = [0.0, 0.0, 0.0]
        pos[crown_index] = [0.0, 144.0, 0.0]

        print(f"spread progress: {step + 1}/{iterations} iterations", file=sys.stderr)

    return {name: tuple(float(c) for c in pos[index[name]]) for name in names}


def write_positions(path, board_to_xyz):
    # newline="" keeps Windows from translating these to CRLF. The file is
    # marked -text in .gitattributes, so git stores whatever it is given, and a
    # coordinate change from a Windows machine would otherwise arrive with
    # every line of the file rewritten underneath it.
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write("# 3d layout of the graph.\n")
        handle.write("# Machine-written by spread_graph.py, do not hand-edit.\n")
        handle.write("# One line per node: position,x,y,z\n")
        for position in board_to_xyz:
            x, y, z = board_to_xyz[position]
            handle.write(f"\n{position},{repr(x)},{repr(y)},{repr(z)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--dt", type=float, default=DEFAULT_DT)
    args = parser.parse_args()

    positions, edges = load_graph()
    print(f"loaded {len(positions):,} nodes and {len(edges):,} edges", file=sys.stderr)
    relaxed = relax(positions, edges, args.iterations, args.dt)

    write_positions(POSITIONS, relaxed)
    print(f"wrote {POSITIONS}", file=sys.stderr)


if __name__ == "__main__":
    main()
