As we approach a largely reduced Connect 4 solution tree, the remaining question is how to rebranch potentially poor early-game choices. For example, the variation `436` was chosen by myself, by hand, given the general consensus opinion among Connect 4 players that it is stronger than `437`. Note that these two choices are the only winning moves for Red following `43`. The question then becomes: How can we prove, measure, or otherwise estimate relative complexity of subgraphs of each option?

This folder is used to track an entire "upper umbrella" solution tree for Connect 4. Unlike the rest of this repository which is concerned with the weak solution tree, this folder treats the union of all weak solutions. By tracking "subtree weights" of each node as well as the amount of compute which has been dedicated to identifying a steady state for that node, we can use explore-vs-exploit techniques to direct search.

Specifically, we define:
- A red-to-move node with a steady state solution has a subtree weight of 1.
- A red-to-move node in which Red has an immediate winning move has a subtree weight of 0.
- Any other red-to-move node's subtree weight equals one plus the minimum weight of its yellow-to-move children,
- A yellow-to-move node's subtree weight equals one plus the sum of the weights of its red-to-move children.

These subtree weights are not final: it is possible that a node's weight may be reduced through steady-state search. We could, in theory, track lower bounds on subtree weights, as there exist ways to prove unsatisfiability via reduction to SAT. However, we choose to not do so, since it does not generalize to the potential of choosing a different steady state language. Thus, we can think of the subtree weights listed in this folder as known upper bounds.

We track this tree in an XML file, union_weak.xml, which can be viewed in a browser. Each node in the tree maintains a `weight` attribute which is the subtree weight of that node. Nodes with a steady state solution also contain a `solution` attribute which is the winning move for that node. Nodes with an immediate winning move contain a `winning_move` attribute which is the winning move for that node. Any other node contains a `children` attribute which recursively contains the child nodes of that node. The XML file can be used to visualize the entire solution tree and to explore the relative complexity of different subgraphs.

Certain nodes may be omitted: for example, if red-to-move parent node `p` has yellow-to-move children `a` and `b`, and `a` has a subtree weight of 1, then `b` is included in the tree but not expanded. Instead, we mark `b` with a `defer` attribute, marking it as deferring to `a`, since it could not possibly have a lower subtree weight than `a`. (Note that yellow-to-move nodes never have subtree-weight 0.)

In practice, we further acknowledge that it is not possible to expand this entire tree, so certain red-to-move nodes with relatively low weights are assumed best and their neighbors are left unexpanded (although without being marked as deferred.) Instead, we leave its weight as infinity, indicating that it has not been searched yet.

A validator is provided, validate_union_weak.py, which validates the XML file's correctness. Specifically, it validates:
- That the provided XML indeed contains the union of all weak solutions, capped by steady states. In other words, it ensures that all non-terminal nodes contain all children which are red-to-win.
- That the subtree weights are correctly calculated according to the rules defined above.

Run with `python3 validate_union_weak.py union_weak.xml`.
