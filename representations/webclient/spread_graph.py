"""Force-directed 2D layout of the webclient graph, called by render.py.

Every pair of nodes repels, and every edge attracts.
"""
from __future__ import annotations

import hashlib
import sys
from collections import deque

import numpy as np

DEFAULT_ITERATIONS = 300
DEFAULT_DT = 4.4
DRAG_FLOOR = 0.05

# Nodes held in place for the first half of the run
PINS = {
    "": (0.0, 0.0),
    "444": (0.0, -199.7),
    "44444": (0.0, -527.2),
    "4444466": (-9.8, -565.9),
    "4444422": (9.8, -565.9),
    "4366755665355": (-292.4, -126.0),
    "4523335213322": (292.4, -126.0),
    "43676": (-254.4, 125.6),
    "45212": (254.4, 125.6),
    "436": (-162.8, -51.9),
    "452": (162.8, -51.9),
    "426566454": (-237.7, 71.7),
    "462322434": (237.7, 71.7),
    "44444432": (77.4, -531.3),
    "44444156666": (-87.4, -598.4),
    "44444732222": (87.4, -598.4),
    "4444415662222": (-113.6, -584.9),
    "4444473226666": (113.6, -584.9),
    "44414": (7.1, -196.5),
    "44474": (-7.1, -196.5),
}

# Every node starts in a box around its nearest pin, whose half-width grows by
# NEAR_PIN_HALF_WIDTH for each edge between them.
NEAR_PIN_HALF_WIDTH = 2.0


# Reflection across the y axis, which is what mirroring a board does to its
# node's position.
MIRROR = np.array([-1.0, 1.0])


def repulsion_forces(pos, sources=None):
    """Runs between every pair of nodes. Returns the net force on each node in
    pos from every node in sources (by default, pos itself).
    """
    if sources is None:
        sources = pos
    d = pos[:, None, :] - sources[None, :, :]
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


def nearest_pins(names, edges):
    """name -> (pin name, hops) to each node's nearest pin, ignoring edge
    direction. A tie goes to the pin listed first in PINS.
    """
    neighbors = {name: [] for name in names}
    for a, b in edges:
        neighbors[a].append(b)
        neighbors[b].append(a)
    nearest = {pin: (pin, 0) for pin in PINS if pin in neighbors}
    queue = deque(nearest)
    while queue:
        name = queue.popleft()
        pin, hops = nearest[name]
        for neighbor in neighbors[name]:
            if neighbor not in nearest:
                nearest[neighbor] = (pin, hops + 1)
                queue.append(neighbor)
    return nearest


def starting_side(name):
    """-1 (left) or +1 (right) by the first move off the center column, 4: a
    lower column is left of center and a higher one right. 0 if every move so
    far is in the center column.
    """
    for move in name:
        if move != "4":
            return -1 if move < "4" else 1
    return 0


def initial_positions(names, edges, mirrors):
    """A pseudorandom starting point for every node, near its nearest pin. A
    node whose nearest pin is on the y axis starts on the side given by
    starting_side. Each node's draw depends only on its own name. The second of
    a mirror pair starts as the reflection of the first.
    """
    nearest = nearest_pins(names, edges)
    positions = {}
    for name in names:
        digest = hashlib.sha256(name.encode()).digest()
        rng = np.random.default_rng(int.from_bytes(digest[:8], "little"))
        pin, hops = nearest[name]
        half_width = NEAR_PIN_HALF_WIDTH * hops
        x, y = np.array(PINS[pin]) + rng.uniform(-half_width, half_width, 2)
        side = starting_side(name)
        if PINS[pin][0] == 0.0 and side:
            x = side * abs(x)
        positions[name] = (float(x), float(y))
    order = {name: i for i, name in enumerate(names)}
    for name in names:
        twin = mirrors.get(name)
        if twin == name:
            positions[name] = (0.0, positions[name][1])
        elif twin is not None and order[twin] < order[name]:
            positions[name] = tuple(np.array(positions[twin]) * MIRROR)
    return positions


def mirror_groups(names, mirrors):
    """Index arrays: each mirror pair split into the node that is simulated and
    its twin, which just follows as its reflection; the nodes that are their own
    mirror; and the nodes whose mirror is not in the graph at all.
    """
    index = {name: i for i, name in enumerate(names)}
    leads, twins, selfs, lone = [], [], [], []
    for name in names:
        twin = mirrors.get(name)
        if twin is None:
            lone.append(index[name])
        elif twin == name:
            selfs.append(index[name])
        elif index[name] < index[twin]:
            leads.append(index[name])
            twins.append(index[twin])
    return tuple(np.array(group, dtype=np.intp) for group in (leads, twins, selfs, lone))


def mirrored_forces(pos, edge_indices, leads, twins, selfs, lone):
    force = np.zeros_like(pos)
    rows = np.concatenate([leads, selfs, lone])
    force[rows] = repulsion_forces(pos[rows], pos)
    if len(lone):
        # Averaging a lead with its reflected twin swaps each lone node for its
        # reflection in half of the sum.
        force[leads] += 0.5 * (repulsion_forces(pos[leads], pos[lone] * MIRROR)
                               - repulsion_forces(pos[leads], pos[lone]))
    force[twins] = force[leads] * MIRROR

    edge_force = attraction_forces(pos, edge_indices)
    pulled = np.zeros_like(pos)
    np.add.at(pulled, edge_indices[:, 0], edge_force)
    np.subtract.at(pulled, edge_indices[:, 1], edge_force)
    shared = 0.5 * (pulled[leads] + pulled[twins] * MIRROR)
    pulled[leads] = shared
    pulled[twins] = shared * MIRROR

    force += pulled
    force[selfs, 0] = 0.0
    return force


def relax(positions, edges, mirrors, iterations, dt):
    names = list(positions)
    index = {name: i for i, name in enumerate(names)}
    pos = np.array([positions[name] for name in names], dtype=float)
    edge_indices = np.array([(index[a], index[b]) for a, b in edges], dtype=np.intp).reshape(-1, 2)
    groups = mirror_groups(names, mirrors)

    velocity = np.zeros_like(pos)
    # Pins must be mirror symmetric themselves, or holding them breaks the pairs.
    pins = [(index[name], xy) for name, xy in PINS.items() if name in index]

    for step in range(iterations):
        # Annealing: light damping early, then damped to a stop by the end.
        drag = DRAG_FLOOR + (1.0 - DRAG_FLOOR) * (step / iterations) ** 4
        force = mirrored_forces(pos, edge_indices, *groups)

        velocity *= 1.0 - drag
        velocity += force * dt
        pos += velocity

        # The pins only hold for the first half of the run, then let go so the
        # graph can settle without them.
        if step < iterations // 3:
            for pin_index, pin_xy in pins:
                pos[pin_index] = pin_xy
                velocity[pin_index] = 0.0

        print(f"spread progress: {step + 1}/{iterations} iterations", file=sys.stderr)

    return {name: tuple(float(c) for c in pos[index[name]]) for name in names}


def layout(names, edges, mirrors, iterations=DEFAULT_ITERATIONS, dt=DEFAULT_DT):
    """names -> (x, y), deterministic for a given graph. mirrors maps each name
    to its mirror image's name (itself for a symmetric board), and leaves out a
    node whose mirror image is not in the graph.
    """
    positions = initial_positions(names, edges, mirrors)
    return relax(positions, edges, mirrors, iterations, dt)
