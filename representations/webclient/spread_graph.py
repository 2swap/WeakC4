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
    "44444666662153332": (-43.4, -380.3),
    "44444732222265556": (43.4, -380.3),
    "4444466666233": (-22.2, -364.8),
    "4444422222655": (22.2, -364.8),
    "44444156666": (-49.6, -352.5),
    "44444732222": (49.6, -352.5),
    "4444466662222": (0.0, -348.2),
    "4444415662226": (-74.8, -345.9),
    "4444473226662": (74.8, -345.9),
    "44444666622": (-8.7, -340.8),
    "44444662222": (8.7, -340.8),
    "444441533": (-57.7, -328.8),
    "444447355": (57.7, -328.8),
    "444444355": (60.8, -315.8),
    "444444": (0.0, -312.7),
    "4444443": (49.0, -309.8),
    "44444432655": (83.5, -305.8),
    "44444": (0.0, -301.9),
    "4444436375555": (-151.7, -272.0),
    "4524444513333": (151.7, -272.0),
    "444443643": (-107.7, -252.7),
    "452444445": (107.7, -252.7),
    "4444436": (-126.5, -251.6),
    "4524444": (126.5, -251.6),
    "444443655": (-131.8, -240.3),
    "452444433": (131.8, -240.3),
    "4444436736766": (-84.4, -238.1),
    "4524444152122": (84.4, -238.1),
    "44444367333": (-110.4, -233.2),
    "45244441555": (110.4, -233.2),
    "444642442": (7.2, -217.5),
    "44464244": (0.0, -208.1),
    "4446424": (0.0, -204.8),
    "444": (0.0, -199.7),
    "44414": (-28.1, -180.4),
    "44474": (28.1, -180.4),
    "4441445": (-43.2, -167.5),
    "4447443": (43.2, -167.5),
    "44424": (-20.0, -165.5),
    "44464": (20.0, -165.5),
    "4366755535571": (-232.2, -162.0),
    "4522133353317": (232.2, -162.0),
    "4366755535551": (-237.8, -158.8),
    "4522133353337": (237.8, -158.8),
    "4442447": (-21.5, -158.4),
    "4446441": (21.5, -158.4),
    "44436": (-117.5, -155.9),
    "45244": (117.5, -155.9),
    "444642": (0.0, -154.0),
    "436675566535566": (-264.5, -153.1),
    "452213335332222": (264.5, -153.1),
    "4443667555355": (-216.1, -150.5),
    "4524421333533": (216.1, -150.5),
    "4443676": (-104.8, -149.7),
    "4524412": (104.8, -149.7),
    "4443626": (-109.9, -143.7),
    "4524462": (109.9, -143.7),
    "444367664": (-97.9, -139.0),
    "452441224": (97.9, -139.0),
    "444366755": (-167.3, -136.7),
    "452442133": (167.3, -136.7),
    "43667556623": (-270.8, -131.8),
    "45221332265": (270.8, -131.8),
    "43667556653": (-262.0, -129.8),
    "45221333522": (262.0, -129.8),
    "43667556663": (-260.1, -122.1),
    "45221332225": (260.1, -122.1),
    "43667556613": (-276.4, -121.0),
    "45221332275": (276.4, -121.0),
    "43667556635": (-286.2, -111.9),
    "45221332253": (286.2, -111.9),
    "43667556644": (-269.2, -96.6),
    "45221332244": (269.2, -96.6),
    "4366755": (-209.3, -91.6),
    "4522133": (209.3, -91.6),
    "436675535": (-229.4, -75.0),
    "452213353": (229.4, -75.0),
    "436675525": (-213.3, -68.6),
    "452213363": (213.3, -68.6),
    "": (0.0, -49.0),
    "4363756": (-185.1, -33.4),
    "4525132": (185.1, -33.4),
    "4363756566533": (-211.3, -31.3),
    "4525132553223": (211.3, -31.3),
    "436": (-120.7, 0.0),
    "452": (120.7, 0.0),
    "43676254664": (-180.2, 3.2),
    "46253124224": (180.2, 3.2),
    "43676": (-139.4, 3.2),
    "45212": (139.4, 3.2),
    "4367625": (-159.3, 4.5),
    "4625312": (159.3, 4.5),
    "43615": (-118.7, 7.3),
    "47352": (118.7, 7.3),
    "4367615": (-153.2, 15.7),
    "4735212": (153.2, 15.7),
    "426": (-94.7, 19.3),
    "462": (94.7, 19.3),
    "43676255665": (-185.5, 28.2),
    "46253123223": (185.5, 28.2),
    "4365615": (-110.2, 33.4),
    "4523273": (110.2, 33.4),
    "4367664": (-162.3, 41.2),
    "4521224": (162.3, 41.2),
    "4265675": (-111.8, 61.7),
    "4623213": (111.8, 61.7),
    "4265": (-93.3, 62.8),
    "4623": (93.3, 62.8),
    "4367664474644": (-207.5, 64.0),
    "4521224414244": (207.5, 64.0),
    "4365664": (-164.7, 69.6),
    "4523224": (164.7, 69.6),
    "4265655": (-124.2, 75.6),
    "4623233": (124.2, 75.6),
    "426566455": (-140.3, 77.9),
    "462323324": (140.3, 77.9),
    "426564664": (-97.0, 91.9),
    "462324224": (97.0, 91.9),
    "436566444": (-172.5, 93.3),
    "452322444": (172.5, 93.3),
    "4265664": (-140.5, 100.8),
    "4623224": (140.5, 100.8),
    "4265624": (-132.5, 122.8),
    "4623264": (132.5, 122.8),
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
