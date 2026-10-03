"""Force-directed layout of the webclient graph, called by render.py.

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

PINS = {
    "44444666662153332": (-16.275, -142.6125),
    "44444732222265556": (16.275, -142.6125),
    "4444466666233": (-8.325, -136.8),
    "4444422222655": (8.325, -136.8),
    "44444156666": (-18.6, -132.1875),
    "44444732222": (18.6, -132.1875),
    "4444466662222": (0.0, -130.575),
    "4444415662226": (-28.05, -129.7125),
    "4444473226662": (28.05, -129.7125),
    "4444466": (-4.5, -120.5),
    "4444422": (4.5, -120.5),
    "444446": (-2.25, -116.5),
    "444442": (2.25, -116.5),
    "44444666622": (-3.2625, -127.8),
    "44444662222": (3.2625, -127.8),
    "444441533": (-21.6375, -123.3),
    "444447355": (21.6375, -123.3),
    "444444355": (22.8, -118.425),
    "444444": (0.0, -117.2625),
    "4444443": (18.375, -116.175),
    "44444432655": (31.3125, -114.675),
    "44444": (0.0, -113.2125),
    "4444436375555": (-56.8875, -102.0),
    "4524444513333": (56.8875, -102.0),
    "444443643": (-40.3875, -94.7625),
    "452444445": (40.3875, -94.7625),
    "4444436": (-47.4375, -94.35),
    "4524444": (47.4375, -94.35),
    "444443655": (-49.425, -90.1125),
    "452444433": (49.425, -90.1125),
    "4444436736766": (-31.65, -89.2875),
    "4524444152122": (31.65, -89.2875),
    "44444367333": (-41.4, -87.45),
    "45244441555": (41.4, -87.45),
    "444642442": (2.7, -81.5625),
    "44464244": (0.0, -78.0375),
    "4446424": (0.0, -76.8),
    "444": (0.0, -74.8875),
    "44414": (-10.5375, -67.65),
    "44474": (10.5375, -67.65),
    "4441445": (-16.2, -62.8125),
    "4447443": (16.2, -62.8125),
    "44424": (-7.5, -62.0625),
    "44464": (7.5, -62.0625),
    "4366755535571": (-87.075, -60.75),
    "4522133353317": (87.075, -60.75),
    "4366755535551": (-89.175, -59.55),
    "4522133353337": (89.175, -59.55),
    "4442447": (-8.0625, -59.4),
    "4446441": (8.0625, -59.4),
    "44436": (-44.0625, -58.4625),
    "45244": (44.0625, -58.4625),
    "444642": (0.0, -57.75),
    "436675566535566": (-99.1875, -57.4125),
    "452213335332222": (99.1875, -57.4125),
    "4443667555355": (-81.0375, -56.4375),
    "4524421333533": (81.0375, -56.4375),
    "4443676": (-39.3, -56.1375),
    "4524412": (39.3, -56.1375),
    "4443626": (-41.2125, -53.8875),
    "4524462": (41.2125, -53.8875),
    "444367664": (-36.7125, -52.125),
    "452441224": (36.7125, -52.125),
    "444366755": (-62.7375, -51.2625),
    "452442133": (62.7375, -51.2625),
    "43667556623": (-101.55, -49.425),
    "45221332265": (101.55, -49.425),
    "43667556653": (-98.25, -48.675),
    "45221333522": (98.25, -48.675),
    "43667556663": (-97.5375, -45.7875),
    "45221332225": (97.5375, -45.7875),
    "43667556613": (-103.65, -45.375),
    "45221332275": (103.65, -45.375),
    "43667556635": (-107.325, -41.9625),
    "45221332253": (107.325, -41.9625),
    "43667556644": (-100.95, -36.225),
    "45221332244": (100.95, -36.225),
    "4366755": (-78.4875, -34.35),
    "4522133": (78.4875, -34.35),
    "436675535": (-86.025, -28.125),
    "452213353": (86.025, -28.125),
    "436675525": (-79.9875, -25.725),
    "452213363": (79.9875, -25.725),
    "": (0.0, -18.375),
    "4363756": (-69.4125, -12.525),
    "4525132": (69.4125, -12.525),
    "4363756566533": (-79.2375, -11.7375),
    "4525132553223": (79.2375, -11.7375),
    "436": (-45.2625, 0.0),
    "452": (45.2625, 0.0),
    "43676254664": (-67.575, 1.2),
    "46253124224": (67.575, 1.2),
    "43676": (-52.275, 1.2),
    "45212": (52.275, 1.2),
    "4367625": (-59.7375, 1.6875),
    "4625312": (59.7375, 1.6875),
    "43615": (-44.5125, 2.7375),
    "47352": (44.5125, 2.7375),
    "4367615": (-57.45, 5.8875),
    "4735212": (57.45, 5.8875),
    "426": (-35.5125, 7.2375),
    "462": (35.5125, 7.2375),
    "43676255665": (-69.5625, 10.575),
    "46253123223": (69.5625, 10.575),
    "4365615": (-41.325, 12.525),
    "4523273": (41.325, 12.525),
    "4367664": (-60.8625, 15.45),
    "4521224": (60.8625, 15.45),
    "4265675": (-41.925, 23.1375),
    "4623213": (41.925, 23.1375),
    "4265": (-34.9875, 23.55),
    "4623": (34.9875, 23.55),
    "4367664474644": (-77.8125, 24.0),
    "4521224414244": (77.8125, 24.0),
    "4365664": (-61.7625, 26.1),
    "4523224": (61.7625, 26.1),
    "4265655": (-46.575, 28.35),
    "4623233": (46.575, 28.35),
    "426566455": (-52.6125, 29.2125),
    "462323324": (52.6125, 29.2125),
    "426564664": (-36.375, 34.4625),
    "462324224": (36.375, 34.4625),
    "436566444": (-64.6875, 34.9875),
    "452322444": (64.6875, 34.9875),
    "4265664": (-52.6875, 37.8),
    "4623224": (52.6875, 37.8),
    "4265624": (-49.6875, 46.05),
    "4623264": (49.6875, 46.05),
}

# Every node starts in a box around its nearest pin, whose half-width grows by
# NEAR_PIN_HALF_WIDTH for each edge between them.
NEAR_PIN_HALF_WIDTH = 2.0

# The pins are flat, so each one starts at a pseudorandom depth up to this far
# out of their plane, to give the layout some depth.
PIN_DEPTH = 50

# Reflection across the x = 0 plane, which is what mirroring a board does to
# its node's position.
MIRROR = np.array([-1.0, 1.0, 1.0])
FORCE_MIRRORING = True

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


def pin_depth(pin):
    """The pin's starting z, drawn from its name alone."""
    digest = hashlib.sha256(f"depth:{pin}".encode()).digest()
    return float(np.random.default_rng(int.from_bytes(digest[:8], "little")).uniform(-PIN_DEPTH, PIN_DEPTH))


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
        x, y, z = np.array(PINS[pin] + (pin_depth(pin),)) + rng.uniform(-half_width, half_width, 3)
        side = starting_side(name)
        if PINS[pin][0] == 0.0 and side:
            x = side * abs(x)
        positions[name] = (float(x), float(y), float(z))
    order = {name: i for i, name in enumerate(names)}
    for name in names:
        twin = mirrors.get(name)
        if twin == name:
            positions[name] = (0.0,) + positions[name][1:]
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

    for step in range(iterations):
        # Annealing: light damping early, then damped to a stop by the end.
        drag = DRAG_FLOOR + (1.0 - DRAG_FLOOR) * (step / iterations) ** 4
        force = mirrored_forces(pos, edge_indices, *groups)

        velocity *= 1.0 - drag
        velocity += force * dt
        pos += velocity

        print(f"spread progress: {step + 1}/{iterations} iterations", file=sys.stderr)

    return {name: tuple(float(c) for c in pos[index[name]]) for name in names}


def layout(names, edges, mirrors, iterations=DEFAULT_ITERATIONS, dt=DEFAULT_DT):
    """names -> (x, y, z), deterministic for a given graph. mirrors maps each name
    to its mirror image's name (itself for a symmetric board), and leaves out a
    node whose mirror image is not in the graph.
    """
    if not FORCE_MIRRORING:
        mirrors = {}
    positions = initial_positions(names, edges, mirrors)
    return relax(positions, edges, mirrors, iterations, dt)
