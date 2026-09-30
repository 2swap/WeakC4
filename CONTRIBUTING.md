# Contributing steady-state diagrams

Every steady-state diagram found at a non-leaf node makes the solution
smaller, because that node's private subtree stops being needed. That is what a
contribution is here, and it can be settled by machine: a diagram either beats
every Yellow reply or it does not. CI runs that check for you.

## The files you edit

Everything that defines the solution lives in `solution/`. Two files are
hand-edited.

**`solution/branches.json`** maps Red-to-move nodes to what Red does there. The
empty string is the empty board. A string value is the single column Red
commits to; an integer value is the index of the steady-state diagram Red
follows from there on:

```json
{
  "": "4",
  "41": "5",
  "4153": "5",
  "43637563356651": 170
}
```

- Only one of each mirror-equivalent board is stored. The other orientation
  is re-derived (mirroring the move or the diagram), so do not add both.

**`solution/steady_states.json`** is a list of diagrams, each a list of six
rows, top row first:

```json
[
  [
    "2226222",
    "2222222",
    "2226262",
    "2246232",
    "0240015",
    "0200000"
  ]
]
```

- Exactly six rows of exactly seven characters, each a digit `0`-`9` giving
  that square's priority level in Red's policy, where `0` is the strongest
  level. There is no blank cell.

The two files interact. A node that gains a diagram has its string value
replaced by the diagram's index. Anything that was only reachable through it
comes out, both its entries and any diagrams nothing else points at. The
validator rejects entries it cannot reach, so a contribution that only adds is
usually incomplete. It reports the frontier rather than the whole set, so
expect to run it, delete what it names, and run it again until it is quiet.

A diagram contribution edits those two files and nothing else. Each
subdirectory of `representations/` builds its artifacts from them with a
`render.py`. These need not be run or edited locally.

## What makes a diagram valid

Red's move follows the priority list from the
[explanation page](https://2swap.github.io/WeakC4/explanation/): win, block,
then the numerical levels `0`, `1`, ... in order. At each level, look at the
squares carrying that digit that Red can play into right now:

- exactly one - play it;
- none - fall through to the next level;
- two or more - they cancel; fall through to the next level.

The first level that resolves to a single playable square wins. Red must win
against *every* legal Yellow continuation; a draw is not enough. If for some
reachable position the diagram falls through every level, it is rejected.

## What makes the solution valid

`solution/validate_solution.py` is the machine-readable definition. It checks
that every diagram wins, that the graph contains the empty board, that a
Red-to-move node either commits to one move or carries a diagram, that a
Yellow-to-move node covers every legal reply except those handing Red an
immediate win, and that no diagram or branch entry is unreachable.

Those rules together *are* the proof that Red wins, which is why none of this
needs a solver. No rule asks whether a move is objectively best, because the
subtree below a move is its own certificate.

## Checking before you open a pull request

CI runs this on your pull request, but running it first is quicker than
waiting. It needs only the standard library:

```bash
python solution/validate_solution.py
```

It validates the whole solution in a few seconds and prints a table of the
nine checks, with the failing entries listed underneath. To see the shape of
what you have changed:

```bash
python solution/print_statistics.py
```

## What CI does

Every pull request runs the whole-solution check, and the result appears in the
**Summary** panel of the run, linked from the Checks tab. Once a change is on
`main`, the same workflow re-renders the representations, publishes the site,
and commits whatever the render changed.

A first-time contribution needs a maintainer to approve the run, so an empty
Checks tab at first is normal.
