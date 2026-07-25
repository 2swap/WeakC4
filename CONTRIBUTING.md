# Contributing steady-state diagrams

Every steady-state diagram found at an expanded node makes the graph smaller,
because that node's private subtree stops being needed. That is what a
contribution is here, and it can be settled by machine: a diagram either beats
every Yellow reply or it does not. CI runs that check for you.

## The file you edit

**Only `steady_states.txt`.** One block per diagram:

```
4523321632
.-+@+!!
..!!...
--|12.@
==221..
--1211@
2211122
```

- First line: the move sequence from the empty board, columns `1`-`7`. Even
  length, since diagrams are defined with Red to move.
- Then exactly six rows of exactly seven characters, **top row first**.
- `!` urgent, `@` miai, `|` claimodd, `.` claimeven, `+` plus, `=` equal,
  `-` minus; `1` Red stone, `2` Yellow stone. The stones must match the
  position, which catches a mistyped move sequence.
- Write claimeven as `.`, not a space — the graph stores a space, but trailing
  spaces are invisible and get stripped.
- Blank lines and `#` comments are ignored; keep entries sorted by position.

`c4_full.js` and `protobuf/c4_full.pb.gz` are **generated** by `build_graph.py`
and rebuilt automatically after merge. A pull request that edits them is
rejected.

## What makes a diagram valid

Red's move follows the priority list from the
[explanation page](https://2swap.github.io/WeakC4/explanation/): win, block,
`!`, `@` (only when exactly one is playable), `|` on an odd row or `.` on an
even row, `+`, `=`, `-`. Red must win against *every* legal Yellow
continuation; a draw is not enough.

Two consequences of the site's guarantee that "there is always precisely one
unique move suggested by this priority list":

- **A tie is a failure, not a coin flip.** Two playable cells at the applicable
  level means the diagram is rejected. The viewer, `client.js`, is looser — it
  silently takes the leftmost — so a diagram can look fine on the website and
  still be rejected here.
- **Claimodd and claimeven are one level**, being a single numbered item on
  that list. A playable claimodd and a playable claimeven at once is a tie.

## What makes the graph valid

Four rules, all checked by `verify_steady_states.py`. The first, second and
fourth are structural and take about a tenth of a second; the third is the
exhaustive search and is what the runtime actually goes on:

- a Red node commits to exactly one move, and it must be legal;
- a Yellow node covers every legal reply, except ones that hand Red an
  immediate win;
- every leaf is Red to move and carries a diagram that wins;
- every node is reachable from the root and no edge dangles.

Together with the leaf diagrams these *are* the proof that Red wins, which is
why nothing here needs a solver: no rule asks whether a move is objectively
best, because the subtree below a move is its own certificate.

## Checking before you open a pull request

The verifier needs only the standard library:

```bash
python verify_steady_states.py --entries
```

To see how much the graph shrinks:

```bash
python build_graph.py --report
```

That is also standard library only. Building the artifacts for real needs
`pip install protobuf`, but CI does that for you.

`effective` counts the diagrams that remove something. A diagram can be valid
and remove nothing if it sits inside a subtree another diagram already
collapsed, or if its position is not a branching node.

## What CI does

Verifies every diagram you added or changed; self-tests the verifier by
checking that reflecting a board reflects the chosen move and nothing else;
reports the node count before and after; and rebuilds the graph. Adding a
diagram cannot invalidate an existing one — validity depends only on a
diagram's own position and markers — so the whole graph is rechecked only when
the verifier or the base graph changes.

Results appear in the **Summary** panel of the workflow run, linked from the
Checks tab. A first-time contribution needs a maintainer to approve the run, so
an empty Checks tab at first is normal.

With an empty `steady_states.txt`, `build_graph.py` reproduces the published
`c4_full.js` byte for byte, so a rebuild only ever shows real changes.
