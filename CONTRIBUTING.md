# Contributing steady-state diagrams

Every steady-state diagram found at a non-leaf node makes the solution
smaller, because that node's private subtree stops being needed. That is what a
contribution is here, and it can be settled by machine: a diagram either beats
every Yellow reply or it does not. CI runs that check for you.

## The files you edit

Everything that defines the solution lives in `solution/`. Two files are
hand-edited.

**`solution/steady_states.json`** is a list of diagrams, each a list of six
rows, top row first:

```json
[
  [
    "   |   ",
    "       ",
    "   | | ",
    "  =| + ",
    "2 =!1@-",
    "2 21112"
  ]
]
```

- Exactly six rows of exactly seven characters.
- `!` urgent, `@` miai, `|` claimodd, a space claimeven, `+` plus, `=` equal,
  `-` minus; `1` is a Red stone and `2` a Yellow stone.
- The stones say which board a block belongs to, so it carries no separate
  identifier.
- A `|` means different things on different rows. On an odd row it is a
  claimodd and can be played. On an even row it can never be played, and its
  only effect is to stop that cell being a claimeven. A space is the mirror of
  this, playable on an even row and silent on an odd one, so neither character
  is a blank.
- A run of bars therefore marks the whole column as claimodd, each odd-row bar
  becoming playable as the column fills to that height, with the even-row bars
  between them suppressing the claimevens. Most such columns hold several
  claimodds rather than one.
- A claimeven is a space, and the quoting keeps trailing ones intact, so count
  the characters rather than trusting the eye: `"2      "` is a full row.
- Only one of each mirror-equivalent pair is stored. The other orientation is
  re-derived when a representation is rendered, so do not add both.

**`solution/branches.json`** maps each non-leaf Red-to-move node to the single
column Red commits to there. The empty string is the empty board:

```json
{
  "": "4",
  "41": "5",
  "4153": "5"
}
```

The two files interact. A node that gains a diagram stops being a non-leaf
node, so its entry comes out of `branches.json`. Anything that was only
reachable through it comes out too, both its branches and its diagrams. The
validator rejects entries it cannot reach, so a contribution that only adds is
usually incomplete. It reports the frontier rather than the whole set, so
expect to run it, delete what it names, and run it again until it is quiet.

A diagram contribution edits those two files and nothing else. Each
subdirectory of `representations/` builds its artifacts from them with a
`render.py`, and those are rebuilt automatically after a change lands, so a
pull request should leave them alone. The webclient's 3D layout is a separate
case: `spread_graph.py` nudges `representations/webclient/positions.txt`
rather than deriving it, so nothing regenerates it automatically.

## What makes a diagram valid

Red's move follows the priority list from the
[explanation page](https://2swap.github.io/WeakC4/explanation/): win, block,
`!`, `@` (only when exactly one is playable), `|` on an odd row or a space on
an even row, `+`, `=`, `-`. Red must win against *every* legal Yellow
continuation; a draw is not enough.

Two consequences of the site's guarantee that "there is always precisely one
unique move suggested by this priority list":

- **A tie between two markers at the same priority level is a failure**, not a
  coin flip. This has nothing to do with a drawn game. Two playable cells at
  the applicable level means the diagram is rejected, with one exception: two
  playable `@` do not tie, they cancel, and the next level decides instead.
  Note that the viewer does
  not enforce this, since it only has to play a move and takes the leftmost of
  a tie, so watching the site play an ambiguous diagram will not reveal that it
  is ambiguous. Nothing there is checking.
- **Claimodd and claimeven are one level**, being a single numbered item on
  that list. A playable claimodd and a playable claimeven at once is a tie.

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
