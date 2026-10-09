use cantor::{ArrayMap, Finite};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};
use std::fmt::Write;
use std::hash::Hash;
use std::{collections::HashMap, fmt::Debug, fs};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Finite)]
pub enum Row {
    R0, // bottom row
    R1,
    R2,
    R3,
    R4,
    R5, // top row
}

impl Row {
    pub fn to_num(&self) -> usize {
        match self {
            Row::R0 => 0,
            Row::R1 => 1,
            Row::R2 => 2,
            Row::R3 => 3,
            Row::R4 => 4,
            Row::R5 => 5,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Finite)]
pub enum Column {
    C1, // leftmost
    C2,
    C3,
    C4, // middle
    C5,
    C6,
    C7, // rightmost
}

impl Column {
    pub fn flip(self) -> Self {
        match self {
            Self::C1 => Self::C7,
            Self::C2 => Self::C6,
            Self::C3 => Self::C5,
            Self::C4 => Self::C4,
            Self::C5 => Self::C3,
            Self::C6 => Self::C2,
            Self::C7 => Self::C1,
        }
    }

    pub fn to_digit(&self) -> char {
        match self {
            Column::C1 => '1',
            Column::C2 => '2',
            Column::C3 => '3',
            Column::C4 => '4',
            Column::C5 => '5',
            Column::C6 => '6',
            Column::C7 => '7',
        }
    }

    pub fn to_num_1_to_7(&self) -> usize {
        match self {
            Column::C1 => 1,
            Column::C2 => 2,
            Column::C3 => 3,
            Column::C4 => 4,
            Column::C5 => 5,
            Column::C6 => 6,
            Column::C7 => 7,
        }
    }

    pub fn to_num_0_to_6(&self) -> usize {
        match self {
            Column::C1 => 0,
            Column::C2 => 1,
            Column::C3 => 2,
            Column::C4 => 3,
            Column::C5 => 4,
            Column::C6 => 5,
            Column::C7 => 6,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Finite)]
pub struct RowAndColumn {
    pub row: Row,
    pub column: Column,
}

fn winning_lines() -> Vec<[RowAndColumn; 4]> {
    let mut lines = Vec::new();

    // Horizontal
    for row in Row::iter() {
        for start in 0..4 {
            lines.push(std::array::from_fn(|i| RowAndColumn {
                row,
                column: Column::iter().nth(start + i).unwrap(),
            }));
        }
    }

    // Vertical
    for column in Column::iter() {
        for start in 0..3 {
            lines.push(std::array::from_fn(|i| RowAndColumn {
                row: Row::iter().nth(start + i).unwrap(),
                column,
            }));
        }
    }

    // Diagonal \
    for start_row in 0..3 {
        for start_column in 0..4 {
            lines.push(std::array::from_fn(|i| RowAndColumn {
                row: Row::iter().nth(start_row + i).unwrap(),
                column: Column::iter().nth(start_column + i).unwrap(),
            }));
        }
    }

    // Diagonal /
    for start_row in 0..3 {
        for start_column in 3..7 {
            lines.push(std::array::from_fn(|i| RowAndColumn {
                row: Row::iter().nth(start_row + i).unwrap(),
                column: Column::iter().nth(start_column - i).unwrap(),
            }));
        }
    }

    lines
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Player {
    First,
    Second,
}

impl Player {
    fn flip(self) -> Self {
        match self {
            Self::First => Self::Second,
            Self::Second => Self::First,
        }
    }
}

#[derive(Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct LabelledBoard<T> {
    entries: ArrayMap<RowAndColumn, T>,
}

impl<T: Clone> LabelledBoard<T> {
    pub fn new(mut f: impl FnMut(Row, Column) -> T) -> Self {
        Self {
            entries: ArrayMap::new(|RowAndColumn { row, column }| f(row, column)),
        }
    }

    pub fn map<S>(self, f: impl FnMut(&T) -> S) -> LabelledBoard<S> {
        LabelledBoard {
            entries: self.entries.map(f),
        }
    }

    pub fn flip(&self) -> Self {
        Self {
            entries: ArrayMap::new(|RowAndColumn { row, column }| {
                self.entries[RowAndColumn {
                    row,
                    column: column.flip(),
                }]
                .clone()
            }),
        }
    }
}

impl<T: Debug> Debug for LabelledBoard<T> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let mut entries = String::new();

        write!(entries, "[")?;
        for (ri, r) in Row::iter().enumerate() {
            if ri != 0 {
                write!(entries, ", ")?;
            }
            write!(entries, "[")?;
            for (ci, c) in Column::iter().enumerate() {
                if ci != 0 {
                    write!(entries, ", ")?;
                }
                write!(
                    entries,
                    "{:?}",
                    self.entries[RowAndColumn { row: r, column: c }]
                )?;
            }
            write!(entries, "]")?;
        }
        write!(entries, "]")?;

        f.debug_struct("LabelledBoard")
            .field("entries", &entries)
            .finish()
    }
}

impl LabelledBoard<SteadyStateSymbol> {
    fn select_column(&self, board: &Board, ss_uses: &mut Vec<Vec<RowAndColumn>>) -> Column {
        debug_assert_eq!(board.turn(), Player::First);

        // select a winning move if available
        for column in Column::iter() {
            if let Some(next_board) = board.clone().play(column) {
                if next_board.has_four_in_a_row(Player::First) {
                    return column;
                }
            }
        }

        // select a column blocking an opponent win, if available
        for column in Column::iter() {
            if let Some(next_board) = board.clone().skip_turn().play(column) {
                if next_board.has_four_in_a_row(Player::Second) {
                    return column;
                }
            }
        }

        // if no winning move or block is available, select the column with the smallest number which occurs exactly once on top
        let filled = board.clone().state.map(|x| x.is_some());

        let tops: ArrayMap<Column, Option<Row>> = ArrayMap::new(|column| {
            for row in Row::iter() {
                if !filled.entries[RowAndColumn { row, column }] {
                    return Some(row);
                }
            }
            None
        });

        let top_state_symbols = Column::iter()
            .filter_map(|column| {
                if let Some(row) = tops[column] {
                    Some(RowAndColumn { row, column })
                } else {
                    None
                }
            })
            .collect::<Vec<_>>();
        ss_uses.push(top_state_symbols.clone());

        for pt in &top_state_symbols {
            if self.entries[*pt] == SteadyStateSymbol::Blank {
                panic!();
            }
        }
        for ss_sym in 0u8..16 {
            let mut columns = vec![];
            for pt in &top_state_symbols {
                if self.entries[*pt] == SteadyStateSymbol::Value(ss_sym) {
                    columns.push(pt.column);
                }
            }
            if columns.len() == 1 {
                return columns.pop().unwrap();
            }
        }

        panic!()
    }

    fn reduce_values(self) -> Self {
        let mut used_values = BTreeSet::new();
        for p in RowAndColumn::iter() {
            if let SteadyStateSymbol::Value(x) = self.entries[p] {
                used_values.insert(x);
            }
        }
        // these are sorted since we used a BTreeSet
        let used_values = used_values.into_iter().collect::<Vec<_>>();
        let value_map = used_values
            .iter()
            .enumerate()
            .map(|(i, x)| (*x, i as u8))
            .collect::<HashMap<_, _>>();
        self.map(|x| match x {
            SteadyStateSymbol::Blank => SteadyStateSymbol::Blank,
            SteadyStateSymbol::Value(x) => SteadyStateSymbol::Value(*value_map.get(x).unwrap()),
        })
    }

    pub fn pprint(&self) {
        for (_ri, r) in Row::iter()
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .enumerate()
        {
            for (ci, c) in Column::iter().enumerate() {
                if ci != 0 {
                    print!(" ");
                }
                print!(
                    "{}",
                    match self.entries[RowAndColumn { row: r, column: c }] {
                        SteadyStateSymbol::Value(value) => format!("{value}"),
                        SteadyStateSymbol::Blank => format!("-"),
                    }
                );
            }
            println!()
        }
    }

    pub fn count_non_blank(&self) -> usize {
        let mut count = 0;
        for p in RowAndColumn::iter() {
            match self.entries[p] {
                SteadyStateSymbol::Blank => {}
                SteadyStateSymbol::Value(_) => count += 1,
            }
        }
        count
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Board {
    state: LabelledBoard<Option<Player>>,
    turn: Player,
}

impl Board {
    pub fn pprint(&self) {
        for (_ri, r) in Row::iter()
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .enumerate()
        {
            for (ci, c) in Column::iter().enumerate() {
                if ci != 0 {
                    print!(" ");
                }
                print!(
                    "{}",
                    match self.state.entries[RowAndColumn { row: r, column: c }] {
                        Some(Player::First) => "X",
                        Some(Player::Second) => "O",
                        None => "-",
                    }
                );
            }
            println!()
        }
    }

    pub fn empty() -> Self {
        Self {
            turn: Player::First,
            state: LabelledBoard {
                entries: ArrayMap::new(|_| None),
            },
        }
    }

    pub fn turn(&self) -> Player {
        self.turn
    }

    pub fn has_four_in_a_row(&self, player: Player) -> bool {
        winning_lines().into_iter().any(|line| {
            line.into_iter()
                .all(|position| self.state.entries[position] == Some(player))
        })
    }

    pub fn skip_turn(mut self) -> Self {
        self.turn = self.turn.flip();
        self
    }

    pub fn play(mut self, column: Column) -> Option<Self> {
        for row in Row::iter() {
            let entry = &mut self.state.entries[RowAndColumn { row, column }];
            if entry.is_none() {
                *entry = Some(self.turn);
                self.turn = self.turn.flip();
                return Some(self);
            }
        }
        None
    }

    pub fn flip(&self) -> Self {
        Self {
            state: self.state.flip(),
            turn: self.turn,
        }
    }

    pub fn from_path(mut columns: Vec<Column>) -> Option<Self> {
        if let Some(last) = columns.pop() {
            if let Some(board) = Self::from_path(columns) {
                board.play(last)
            } else {
                None
            }
        } else {
            Some(Self::empty())
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub enum SteadyStateSymbol {
    Blank,
    Value(u8),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub struct NodePtr {
    flip: bool,
    idx: usize,
}

#[derive(Debug, Clone, Copy)]
pub enum Response {
    ObviousSteady, // a winning move
    Steady { flip: bool, ss_idx: usize },
    Lookup { column: Column, node: NodePtr },
}

#[derive(Clone)]
pub struct Node {
    board: Board,
    responses: ArrayMap<Column, Option<Response>>,
}

impl std::fmt::Debug for Node {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("NodeTwo")
            .field(
                "responses",
                &Column::iter()
                    .map(|c| (c, &self.responses[c]))
                    .collect::<HashMap<_, _>>(),
            )
            .finish()
    }
}

#[derive(Debug, Clone)]
pub struct Graph {
    first_move: Column,
    first_node: NodePtr,
    nodes: Vec<Node>,
    steady: Vec<LabelledBoard<SteadyStateSymbol>>,
}

impl Graph {
    pub fn load() -> Self {
        let char_to_column = |c: char| -> Column {
            match c {
                '1' => Column::C1,
                '2' => Column::C2,
                '3' => Column::C3,
                '4' => Column::C4,
                '5' => Column::C5,
                '6' => Column::C6,
                '7' => Column::C7,
                _ => unreachable!(),
            }
        };

        let branches_json_string = fs::read_to_string("../../solution/branches.json").unwrap();
        let branches_json: HashMap<String, Value> =
            serde_json::from_str(&branches_json_string).unwrap();
        #[derive(Debug, Clone, Copy)]
        enum BranchesEdge {
            SteadyState { idx: usize },
            ObviousSteadyState,
            Move(Column),
        }
        let branches: BTreeMap<Board, BranchesEdge> = branches_json
            .into_iter()
            .map(|(path, edge)| {
                let path = path.chars().map(char_to_column).collect();
                (
                    Board::from_path(path).unwrap(),
                    if let Some(idx) = edge.as_u64() {
                        BranchesEdge::SteadyState { idx: idx as usize }
                    } else if let Some(c) = edge.as_str() {
                        debug_assert_eq!(c.len(), 1);
                        let c = c.chars().next().unwrap();
                        BranchesEdge::Move(char_to_column(c))
                    } else {
                        unreachable!()
                    },
                )
            })
            .collect();

        let steady_states_json_string =
            fs::read_to_string("../../solution/steady_states.json").unwrap();
        let steady_states_json: Vec<Vec<String>> =
            serde_json::from_str(&steady_states_json_string).unwrap();
        fn ascii_digit_to_u8(c: char) -> Option<u8> {
            if c.is_ascii_digit() {
                Some((c as u8) - b'0')
            } else {
                None
            }
        }
        let steady_states: Vec<LabelledBoard<SteadyStateSymbol>> = steady_states_json
            .into_iter()
            .map(|ss| {
                debug_assert_eq!(ss.len(), 6);
                for row in &ss {
                    debug_assert_eq!(row.len(), 7);
                }
                LabelledBoard::new(|r, c| {
                    let ri = Row::index_of(r);
                    let ci = Column::index_of(c);
                    SteadyStateSymbol::Value(
                        ascii_digit_to_u8(ss[5 - ri].chars().nth(ci).unwrap()).unwrap(),
                    )
                })
            })
            .collect();

        struct Loader {
            branches: BTreeMap<Board, BranchesEdge>,
            steady_states: Vec<LabelledBoard<SteadyStateSymbol>>,
            nodes: Vec<(Board, Node)>,
        }

        impl Loader {
            fn node(&mut self, board: Board) -> NodePtr {
                debug_assert_eq!(board.turn(), Player::Second);

                for (idx, (existing_board, _)) in self.nodes.iter().enumerate() {
                    if &board == existing_board {
                        return NodePtr { flip: false, idx };
                    }
                }
                for (idx, (existing_board, _)) in self.nodes.iter().enumerate() {
                    if board == existing_board.flip() {
                        return NodePtr { flip: true, idx };
                    }
                }

                let node = Node {
                    board: board.clone(),
                    responses: ArrayMap::new(|column| {
                        board.clone().play(column).map(|next_board| {
                            let (branch_edge, flip) = self
                                .branches
                                .get(&next_board)
                                .map(|branch_edge| (*branch_edge, false))
                                .unwrap_or_else(|| {
                                    self.branches
                                        .get(&next_board.flip())
                                        .map(|branches_edge| (*branches_edge, true))
                                        .unwrap_or_else(|| {
                                            (BranchesEdge::ObviousSteadyState, false)
                                        })
                                });

                            match branch_edge {
                                BranchesEdge::ObviousSteadyState => Response::ObviousSteady,
                                BranchesEdge::SteadyState { idx: ss_idx } => {
                                    Response::Steady { flip, ss_idx }
                                }
                                BranchesEdge::Move(mut column) => {
                                    if flip {
                                        column = column.flip();
                                    }
                                    let node = self.node(next_board.play(column).unwrap());
                                    Response::Lookup { column, node }
                                }
                            }
                        })
                    }),
                };

                let node_idx = self.nodes.len();
                self.nodes.push((board, node));
                NodePtr {
                    flip: false,
                    idx: node_idx,
                }
            }

            fn graph(mut self) -> Graph {
                let board = Board::empty();

                let first_move = match self.branches.get(&board) {
                    Some(BranchesEdge::Move(first_move)) => *first_move,
                    _ => panic!(),
                };

                let board = board.play(first_move).unwrap();

                let first_node = self.node(board);

                Graph {
                    first_move,
                    first_node,
                    nodes: self.nodes.into_iter().map(|(_, node)| node).collect(),
                    steady: self.steady_states,
                }
            }
        }

        let graph = Loader {
            branches,
            steady_states,
            nodes: vec![],
        }
        .graph();

        println!("Loaded graph");

        graph
    }

    fn print_stats(&self) {
        println!("Node count = {:?}", self.nodes.len());
        println!("Steady state count = {:?}", self.steady.len());
    }

    fn check_at_steady(
        &self,
        board: Board,
        steady: &LabelledBoard<SteadyStateSymbol>,
        done: &mut BTreeSet<(Board, LabelledBoard<SteadyStateSymbol>)>,
        ss_uses: &mut Vec<Vec<RowAndColumn>>,
    ) {
        debug_assert_eq!(board.turn(), Player::First);

        if done.contains(&(board.clone(), steady.clone())) {
            return;
        }
        done.insert((board.clone(), steady.clone()));

        assert!(!board.has_four_in_a_row(Player::First));
        assert!(!board.has_four_in_a_row(Player::Second));

        let column = steady.select_column(&board, ss_uses);
        let next_board = board.play(column).unwrap();

        if next_board.has_four_in_a_row(Player::First) {
            return; // player 1 wins
        }

        for column in Column::iter() {
            if let Some(next_next_board) = next_board.clone().play(column) {
                self.check_at_steady(next_next_board, steady, done, ss_uses);
            }
        }
    }

    fn check_at(
        &self,
        mut board: Board,
        node_ptr: &NodePtr,
        done: &mut BTreeSet<(Board, NodePtr)>,
        ss_uses: &mut Vec<SteadyStateUses>,
    ) {
        debug_assert_eq!(board.turn(), Player::Second);

        if done.contains(&(board.clone(), *node_ptr)) {
            return;
        }
        done.insert((board.clone(), node_ptr.clone()));

        println!("Checked {:?} nodes", done.len());

        if node_ptr.flip {
            board = board.flip();
        }

        assert!(!board.has_four_in_a_row(Player::First));
        assert!(!board.has_four_in_a_row(Player::Second));

        let node = &self.nodes[node_ptr.idx];
        for column in Column::iter() {
            if let Some(next_board) = board.clone().play(column) {
                assert_eq!(next_board.has_four_in_a_row(Player::Second), false);
                let response = *node.responses[column].as_ref().unwrap();
                match response {
                    Response::ObviousSteady => {
                        let steady = LabelledBoard::new(|_row, _column| SteadyStateSymbol::Blank);
                        let mut ss_uses_here = vec![];
                        self.check_at_steady(
                            next_board,
                            &steady,
                            &mut BTreeSet::new(),
                            &mut ss_uses_here,
                        );
                    }
                    Response::Steady { flip, ss_idx } => {
                        let next_board = if !flip { next_board } else { next_board.flip() };
                        let steady = self.steady[ss_idx].clone();
                        let mut ss_uses_here = vec![];
                        self.check_at_steady(
                            next_board,
                            &steady,
                            &mut BTreeSet::new(),
                            &mut ss_uses_here,
                        );
                        for ss_use_here in ss_uses_here {
                            ss_uses.push(SteadyStateUses {
                                ss_idx,
                                points: ss_use_here,
                            });
                        }
                    }
                    Response::Lookup {
                        column,
                        node: next_node_ptr,
                    } => {
                        let next_next_board = next_board.play(column).unwrap();
                        self.check_at(next_next_board, &next_node_ptr, done, ss_uses);
                    }
                }
            } else {
                assert!(node.responses[column].is_none());
            }
        }
    }

    pub fn check(&self) -> Vec<SteadyStateUses> {
        let mut ss_uses = vec![];
        self.check_at(
            Board::empty().play(self.first_move).unwrap(),
            &self.first_node,
            &mut BTreeSet::new(),
            &mut ss_uses,
        );

        for ss in &self.steady {
            for p in RowAndColumn::iter() {
                if let SteadyStateSymbol::Value(x) = ss.entries[p] {
                    if x >= 10 {
                        ss.pprint();
                        panic!();
                    }
                }
            }
        }

        println!("Checks passed :D");
        ss_uses
    }

    pub fn populate_steady_state_blanks(&mut self, ss_uses: Vec<SteadyStateUses>) {
        let mut usages = (0..self.steady.len())
            .map(|_| LabelledBoard::new(|_, _| false))
            .collect::<Vec<_>>();
        for SteadyStateUses { ss_idx, points } in ss_uses {
            for p in points {
                usages[ss_idx].entries[p] = true;
            }
        }
        for (ss_idx, usage) in usages.iter().enumerate() {
            for p in RowAndColumn::iter() {
                if !usage.entries[p] {
                    self.steady[ss_idx].entries[p] = SteadyStateSymbol::Blank;
                }
            }
        }
    }

    pub fn reduce_steady_state_values(&mut self) {
        for steady in &mut self.steady {
            *steady = steady.clone().reduce_values();
        }
    }

    pub fn eliminate_obvious_steadys(&mut self) {
        assert!(!self.steady.is_empty());
        for node in &mut self.nodes {
            for column in Column::iter() {
                if let Some(response) = &mut node.responses[column] {
                    match response {
                        Response::ObviousSteady => {
                            *response = Response::Steady {
                                flip: false,
                                ss_idx: 0,
                            };
                        }
                        Response::Steady { .. } => {}
                        Response::Lookup { .. } => {}
                    }
                }
            }
        }
    }

    pub fn make_steady_states_unique_per_leaf(&mut self) {
        let mut used_ss_indexes: BTreeSet<usize> = BTreeSet::new();

        for node in &mut self.nodes {
            for column in Column::iter() {
                match &mut node.responses[column] {
                    Some(Response::Steady {
                        flip: _flip,
                        ss_idx,
                    }) => {
                        if used_ss_indexes.contains(ss_idx) {
                            let new_ss_idx = self.steady.len();
                            self.steady.push(self.steady[*ss_idx].clone());
                            *ss_idx = new_ss_idx;
                            used_ss_indexes.insert(new_ss_idx);
                        } else {
                            used_ss_indexes.insert(*ss_idx);
                        }
                    }
                    Some(Response::Lookup { .. }) => {}
                    Some(Response::ObviousSteady) => {}
                    None => {}
                }
            }
        }
    }

    pub fn dedup_steady_states(&mut self) -> HashMap<usize, (usize, bool)> {
        let mut steady_state_reindexing = (0..self.steady.len()).map(|i| (i, (i, false))).collect();

        loop {
            let mut mergable = vec![];
            let n = self.steady.len();
            for a in 0..n {
                for b in 0..a {
                    for flip_b in [false, true] {
                        let ss_a = self.steady[a].clone();
                        let ss_b = if !flip_b {
                            self.steady[b].clone()
                        } else {
                            self.steady[b].flip()
                        };

                        let both = LabelledBoard::new(|row, column| {
                            let p = RowAndColumn { row, column };
                            ss_a.entries[p] != SteadyStateSymbol::Blank
                                && ss_b.entries[p] != SteadyStateSymbol::Blank
                        });

                        let ss_overlap_a = LabelledBoard::new(|row, column| {
                            let p = RowAndColumn { row, column };
                            if both.entries[p] {
                                ss_a.entries[p].clone()
                            } else {
                                SteadyStateSymbol::Blank
                            }
                        });
                        let ss_overlap_b = LabelledBoard::new(|row, column| {
                            let p = RowAndColumn { row, column };
                            if both.entries[p] {
                                ss_b.entries[p].clone()
                            } else {
                                SteadyStateSymbol::Blank
                            }
                        });

                        if ss_overlap_a.clone().reduce_values()
                            == ss_overlap_b.clone().reduce_values()
                        {
                            let ss_overlap_reduced = ss_overlap_a.reduce_values();

                            // map from overlap symbols to A symbols
                            let mut overlap_to_a = HashMap::new();
                            for p in RowAndColumn::iter() {
                                if let SteadyStateSymbol::Value(x) = ss_overlap_reduced.entries[p] {
                                    if let SteadyStateSymbol::Value(y) = ss_a.entries[p] {
                                        if let Some(existing_y) = overlap_to_a.get(&x) {
                                            assert_eq!(y, *existing_y);
                                        }
                                        overlap_to_a.insert(x, y);
                                    } else {
                                        unreachable!();
                                    }
                                }
                            }
                            let a_to_overlap = overlap_to_a
                                .iter()
                                .map(|(x, y)| (*y, *x))
                                .collect::<HashMap<_, _>>();

                            // map from overlap symbols to A symbols
                            let mut overlap_to_b = HashMap::new();
                            for p in RowAndColumn::iter() {
                                if let SteadyStateSymbol::Value(x) = ss_overlap_reduced.entries[p] {
                                    if let SteadyStateSymbol::Value(y) = ss_b.entries[p] {
                                        if let Some(existing_y) = overlap_to_b.get(&x) {
                                            assert_eq!(y, *existing_y);
                                        }
                                        overlap_to_b.insert(x, y);
                                    } else {
                                        unreachable!();
                                    }
                                }
                            }
                            let b_to_overlap = overlap_to_b
                                .iter()
                                .map(|(x, y)| (*y, *x))
                                .collect::<HashMap<_, _>>();

                            let mut a_to_b = HashMap::new();
                            for p in RowAndColumn::iter() {
                                if let SteadyStateSymbol::Value(x) = ss_a.entries[p] {
                                    let z =
                                        a_to_overlap.get(&x).map(|y| *overlap_to_b.get(y).unwrap());
                                    if let Some(existing_z) = a_to_b.get(&x) {
                                        assert_eq!(z, *existing_z);
                                    }
                                    a_to_b.insert(x, z);
                                }
                            }

                            let mut b_to_a = HashMap::new();
                            for p in RowAndColumn::iter() {
                                if let SteadyStateSymbol::Value(x) = ss_b.entries[p] {
                                    let z =
                                        b_to_overlap.get(&x).map(|y| *overlap_to_a.get(y).unwrap());
                                    if let Some(existing_z) = b_to_a.get(&x) {
                                        assert_eq!(z, *existing_z);
                                    }
                                    b_to_a.insert(x, z);
                                }
                            }

                            // println!("ss_a");
                            // ss_a.pprint();
                            // println!("ss_b");
                            // ss_b.pprint();
                            // println!("overlap reduced");
                            // ss_overlap_reduced.pprint();
                            // println!("{:?}", a_to_b);
                            // println!("{:?}", b_to_a);

                            let overlap_nonblank_count =
                                ss_overlap_reduced.count_non_blank() as i64;

                            drop(a_to_overlap);
                            drop(overlap_to_a);
                            drop(b_to_overlap);
                            drop(overlap_to_b);
                            drop(ss_overlap_reduced);

                            let mut a_to_merged = HashMap::new();
                            let mut b_to_merged = HashMap::new();
                            let mut a_counter = 0;
                            let mut b_counter = 0;
                            let mut m_counter = 0;
                            while a_to_b.contains_key(&a_counter) || b_to_a.contains_key(&b_counter)
                            {
                                if let Some(a_in_b) = a_to_b.get(&a_counter).unwrap_or(&None) {
                                    b_counter = std::cmp::min(*a_in_b, b_counter);
                                }
                                if let Some(b_in_a) = b_to_a.get(&b_counter).unwrap_or(&None) {
                                    a_counter = std::cmp::min(*b_in_a, a_counter);
                                }

                                a_to_merged.insert(a_counter, m_counter);
                                b_to_merged.insert(b_counter, m_counter);

                                a_counter += 1;
                                b_counter += 1;
                                m_counter += 1;
                            }

                            let ss_merged = LabelledBoard::new(|row, column| {
                                let p = RowAndColumn { row, column };
                                if let SteadyStateSymbol::Value(x) = ss_a.entries[p] {
                                    SteadyStateSymbol::Value(*a_to_merged.get(&x).unwrap())
                                } else if let SteadyStateSymbol::Value(x) = ss_b.entries[p] {
                                    SteadyStateSymbol::Value(*b_to_merged.get(&x).unwrap())
                                } else {
                                    SteadyStateSymbol::Blank
                                }
                            });

                            // don't merge if it would take the largest steady state symbol above 9
                            // m_counter is 1 greater than the largest non-blank value in ss_merged
                            if m_counter - 1 <= 9 {
                                // using overlap_nonblank_count as a score here seems to work reasonably well
                                // so we're merging things which look most similar first and least similar last
                                mergable.push(((a, b, flip_b, ss_merged), overlap_nonblank_count));
                            }
                        }
                    }
                }
            }

            if mergable.is_empty() {
                break;
            } else {
                mergable.sort_unstable_by_key(|(_, score)| *score);
                let ((a, b, flip_b, ss_merged), _) = mergable.pop().unwrap();
                println!("Merging steady states {a} and {b}");
                self.steady[b] = ss_merged;
                self.reroute_steady_state_idx(&mut steady_state_reindexing, a, b, flip_b);
            }
        }

        steady_state_reindexing
    }

    // everything currently pointing at `a` shall now point at `b`, and `a` gets deleted
    // if `flip_b` is set then any existing references to steady state `b` shall be flipped
    fn reroute_steady_state_idx(
        &mut self,
        // where each old steady state should point to and whether it gets flipped
        steady_state_reindexing: &mut HashMap<usize, (usize, bool)>,
        ss_idx_a: usize,
        ss_idx_b: usize,
        flip_b: bool,
    ) {
        let n = self.steady.len();
        assert!(ss_idx_a < n);
        assert!(ss_idx_b < n);
        assert!(ss_idx_b < ss_idx_a);

        let map_ss_idx = |ss_idx: usize| {
            if ss_idx < ss_idx_a {
                ss_idx
            } else if ss_idx == ss_idx_a {
                ss_idx_b // don't need to -1 here since ss_idx_b < ss_idx_a
            } else {
                assert!(ss_idx > ss_idx_a);
                ss_idx - 1
            }
        };

        let map_ss_flip = |flip: bool, ss_idx: usize| {
            if ss_idx == ss_idx_b && flip_b {
                !flip
            } else {
                flip
            }
        };

        self.steady.remove(ss_idx_a);
        for node in &mut self.nodes {
            node.responses = node.responses.map(|responses| {
                responses.map(|response| match response {
                    Response::ObviousSteady => Response::ObviousSteady,
                    Response::Steady { flip, ss_idx } => Response::Steady {
                        flip: map_ss_flip(flip, ss_idx),
                        ss_idx: map_ss_idx(ss_idx),
                    },
                    Response::Lookup { column, node } => Response::Lookup { column, node },
                })
            });
        }

        *steady_state_reindexing = steady_state_reindexing
            .into_iter()
            .map(|(x, (y, flip))| (*x, (map_ss_idx(*y), map_ss_flip(*flip, *y))))
            .collect();

        for (_, (y, _)) in steady_state_reindexing {
            assert!(*y < self.steady.len());
        }
    }

    pub fn to_json(&self) -> (String, String) {
        #[derive(Debug)]
        enum BranchNext {
            Column(Column),
            Steady(usize),
        }

        #[derive(Debug)]
        struct Branch {
            path: Vec<Column>,
            next: BranchNext,
        }

        fn populate_branches(
            graph: &Graph,
            branches: &mut Vec<Branch>,
            node_idx: usize,
            path: Vec<Column>,
        ) {
            let node = &graph.nodes[node_idx];
            'LOOP: for their_column in Column::iter() {
                let mut next_path = path.clone();
                next_path.push(their_column);

                // only store each node once
                if let Some(next_board) = Board::from_path(next_path.clone()) {
                    for branch in branches.iter() {
                        let branch_board = Board::from_path(branch.path.clone()).unwrap();
                        if next_board == branch_board || next_board == branch_board.flip() {
                            continue 'LOOP;
                        }
                    }

                    match node.responses[their_column] {
                        None => {}
                        Some(Response::ObviousSteady) => {}
                        Some(Response::Steady { flip, ss_idx }) => {
                            if !flip {
                                branches.push(Branch {
                                    path: next_path.clone(),
                                    next: BranchNext::Steady(ss_idx),
                                });
                            } else {
                                let next_path_flipped =
                                    next_path.iter().map(|c| c.flip()).collect::<Vec<_>>();
                                branches.push(Branch {
                                    path: next_path_flipped,
                                    next: BranchNext::Steady(ss_idx),
                                });
                            }
                        }
                        Some(Response::Lookup {
                            column: resp_column,
                            node: resp_node_ptr,
                        }) => {
                            branches.push(Branch {
                                path: next_path.clone(),
                                next: BranchNext::Column(resp_column),
                            });

                            let mut next_next_path = next_path.clone();
                            next_next_path.push(resp_column);

                            if resp_node_ptr.flip {
                                next_next_path =
                                    next_next_path.into_iter().map(|c| c.flip()).collect();
                            }

                            populate_branches(
                                graph,
                                branches,
                                resp_node_ptr.idx,
                                next_next_path.clone(),
                            );
                        }
                    }
                }
            }
        }

        let mut branches: Vec<Branch> = vec![Branch {
            path: vec![],
            next: BranchNext::Column(Column::C4),
        }];
        populate_branches(self, &mut branches, self.first_node.idx, vec![Column::C4]);

        let mut branches_json = String::new();
        let mut steady_states_json = String::new();

        write!(&mut branches_json, "{{\n").unwrap();
        for (branch_idx, branch) in branches.iter().enumerate() {
            let mut path_json = String::new();
            for column in &branch.path {
                write!(&mut path_json, "{}", column.to_digit()).unwrap();
            }
            let next_json = match branch.next {
                BranchNext::Column(column) => format!("\"{}\"", column.to_digit()),
                BranchNext::Steady(ss_idx) => format!("{ss_idx}"),
            };
            write!(
                &mut branches_json,
                "  \"{}\": {}{}\n",
                path_json,
                next_json,
                if branch_idx + 1 < branches.len() {
                    ","
                } else {
                    ""
                }
            )
            .unwrap();
        }
        write!(&mut branches_json, "}}\n").unwrap();

        write!(&mut steady_states_json, "[\n").unwrap();
        for (idx, steady) in self.steady.iter().enumerate() {
            write!(&mut steady_states_json, "  [\n").unwrap();
            for (row_idx, row) in Row::iter()
                .collect::<Vec<_>>()
                .into_iter()
                .rev()
                .enumerate()
            {
                let mut columns_json = String::new();
                for column in Column::iter() {
                    write!(
                        &mut columns_json,
                        "{}",
                        match steady.entries[RowAndColumn { row, column }] {
                            SteadyStateSymbol::Blank => "9".to_string(),
                            SteadyStateSymbol::Value(sym) => format!("{sym}"),
                        }
                    )
                    .unwrap();
                }
                write!(
                    &mut steady_states_json,
                    "    \"{columns_json}\"{}",
                    if row_idx < 5 { ",\n" } else { "\n" }
                )
                .unwrap();
            }
            write!(
                &mut steady_states_json,
                "  ]{}\n",
                if idx + 1 < self.steady.len() { "," } else { "" }
            )
            .unwrap();
        }
        write!(&mut steady_states_json, "]\n").unwrap();

        (branches_json, steady_states_json)
    }

    pub fn to_mc_schem(&self) {
        use redstone_schem::examples::rom_16kb_barrel::Rom;

        #[derive(Debug)]
        struct LookupColumn {
            flip: bool,
            response: Column,
            next: usize,
        }

        enum TableEntry {
            Lookup(ArrayMap<Column, Option<LookupColumn>>),
            Steady(LabelledBoard<SteadyStateSymbol>),
        }

        impl std::fmt::Debug for TableEntry {
            fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                match self {
                    Self::Lookup(arg0) => f
                        .debug_tuple("Lookup")
                        .field(
                            &Column::iter()
                                .map(|column| &arg0[column])
                                .collect::<Vec<_>>(),
                        )
                        .finish(),
                    Self::Steady(arg0) => f.debug_tuple("Steady").field(arg0).finish(),
                }
            }
        }

        #[derive(Debug)]
        struct Table {
            entries: Vec<TableEntry>,
            // graph ss_idx to entry idx
            steady_map: HashMap<usize, usize>,
            // node idx to entry idx
            node_map: HashMap<usize, usize>,
        }

        impl Table {
            fn add_steady_node(
                &mut self,
                graph: &Graph,
                ss_idx: usize,
                steady: &LabelledBoard<SteadyStateSymbol>,
            ) -> usize {
                if self.steady_map.contains_key(&ss_idx) {
                    *self.steady_map.get(&ss_idx).unwrap()
                } else {
                    let idx = self.entries.len();
                    self.entries.push(TableEntry::Steady(steady.clone()));
                    self.steady_map.insert(ss_idx, idx);
                    idx
                }
            }

            fn add_lookup_node(&mut self, graph: &Graph, node_idx: usize) -> usize {
                if self.node_map.contains_key(&node_idx) {
                    *self.node_map.get(&node_idx).unwrap()
                } else {
                    let node = &graph.nodes[node_idx];

                    let idx = self.entries.len();
                    self.entries
                        .push(TableEntry::Lookup(ArrayMap::new(|_column| None))); // placeholder to be populated
                    let mut lookup = ArrayMap::new(|column| None);
                    for column in Column::iter() {
                        let entry = if let Some(response) = node.responses[column] {
                            match response {
                                Response::ObviousSteady => {
                                    panic!("eliminate any ObviousSteady first")
                                }
                                Response::Steady { flip, ss_idx } => {
                                    let next =
                                        self.add_steady_node(graph, ss_idx, &graph.steady[ss_idx]);
                                    let mut steady = graph.steady[ss_idx].clone();
                                    if flip {
                                        steady = steady.flip();
                                    }
                                    LookupColumn {
                                        flip: flip,
                                        response: steady.select_column(
                                            &node.board.clone().play(column).unwrap(),
                                            &mut vec![],
                                        ),
                                        next,
                                    }
                                }
                                Response::Lookup { column, node } => {
                                    let next = self.add_lookup_node(graph, node.idx);
                                    LookupColumn {
                                        flip: node.flip,
                                        response: column,
                                        next,
                                    }
                                }
                            }
                        } else {
                            LookupColumn {
                                flip: false,
                                response: Column::C4,
                                next: 0,
                            }
                        };
                        lookup[column] = Some(entry);
                    }
                    self.entries[idx] = TableEntry::Lookup(lookup);
                    self.node_map.insert(node_idx, idx);
                    idx
                }
            }
        }

        let mut table = Table {
            entries: vec![],
            steady_map: HashMap::new(),
            node_map: HashMap::new(),
        };
        let idx = table.add_lookup_node(self, self.first_node.idx);
        assert_eq!(idx, 0); // assumed by MC implementation

        let entry_count = table.entries.len();

        let mut addr = 0;
        let mut entry_addrs = vec![];
        for entry in &table.entries {
            // an entry at addr skims off the most significant chunk of rom[addr..addr+32]
            match entry {
                TableEntry::Lookup(_) => {
                    addr += 4 * 4;
                }
                TableEntry::Steady(_) => {
                    addr += 4 * 7;
                }
            }
            entry_addrs.push(addr - 16); // rotate everything by 16 so that entry 0 has address 0
        }
        assert_eq!(entry_addrs[0], 0);
        assert_eq!(entry_addrs.len(), entry_count);

        let mut rom = Rom::default();
        let or_insert_u16 = |rom: &mut Rom, dest_addr: usize, value: u16| {
            for j in 0..16 {
                if (value >> j) & 1 == 1 {
                    rom.data[dest_addr - { if j % 2 == 0 { 0 } else { 1 } }] |= 1 << (j / 2);
                }
            }
        };
        for entry_idx in 0..entry_count {
            let entry = &table.entries[entry_idx];
            let addr = entry_addrs[entry_idx];
            match entry {
                // remember here the LSB is on the right (looking at the MC build from side on) so we need to do a lot of 31-stuff to put the stuff on the correct side
                TableEntry::Lookup(lookups) => {
                    rom.data[addr + 31] = 0b01111111; // top bit 0 for lookup
                    let mut i = 1; // start of lookup data
                    for column in Column::iter() {
                        rom.data[addr + 31 - i] = 0;
                        rom.data[addr + 31 - (i + 1)] = 0;
                        if let Some(lookup) = &lookups[column] {
                            let mut data16: u16 = (entry_addrs[lookup.next] >> 2) as u16;
                            assert_eq!(data16 & 0b1111000000000000, 0);
                            if lookup.flip {
                                data16 |= 0b0001000000000000; // this bit is the flip bit
                            }
                            data16 |= (lookup.response.to_num_1_to_7() as u16) << 13;
                            or_insert_u16(&mut rom, addr + 31 - i, data16);
                        }
                        i += 2;
                    }
                }
                TableEntry::Steady(labelled_board) => {
                    rom.data[addr + 31] = 0b10000000; // top bit 1 for steady
                    for column in Column::iter() {
                        for row in Row::iter() {
                            for b in 0..4 {
                                let symbol = &labelled_board.entries[RowAndColumn { row, column }];
                                if match symbol {
                                    SteadyStateSymbol::Blank => false,
                                    SteadyStateSymbol::Value(value) => (value >> b) & 1 == 1,
                                } {
                                    rom.data[addr + 31
                                        - ((3 - b) + 4 * (6 - column.to_num_0_to_6()))] |=
                                        1 << row.to_num();
                                }
                            }
                        }
                    }
                }
            }
        }

        let interlace_u8 = |a: u8, b: u8| -> u16 {
            let mut val16: u16 = 0;
            for i in 0..16 {
                if i % 2 == 0 {
                    if (a >> (i / 2)) & 1 == 1 {
                        val16 |= 1 << i;
                    }
                } else {
                    if (b >> (i / 2)) & 1 == 1 {
                        val16 |= 1 << i;
                    }
                }
            }
            val16
        };

        let idx = 26;

        let ptr = entry_addrs[idx];

        println!("ptr = {:016b}", ptr);

        for x in &rom.data[ptr..(ptr + 32)] {
            println!("{:08b}", x);
        }

        let val16 = interlace_u8(rom.data[ptr + 31 - 1], rom.data[ptr + 31 - 2]);
        println!("{:016b} {}", val16, 4 * (val16 & 0b0000111111111111));
        let val16 = interlace_u8(rom.data[ptr + 31 - 3], rom.data[ptr + 31 - 4]);
        println!("{:016b} {}", val16, 4 * (val16 & 0b0000111111111111));
        let val16 = interlace_u8(rom.data[ptr + 31 - 5], rom.data[ptr + 31 - 6]);
        println!("{:016b} {}", val16, 4 * (val16 & 0b0000111111111111));
        let val16 = interlace_u8(rom.data[ptr + 31 - 7], rom.data[ptr + 31 - 8]);
        println!("{:016b} {}", val16, 4 * (val16 & 0b0000111111111111));
        let val16 = interlace_u8(rom.data[ptr + 31 - 9], rom.data[ptr + 31 - 10]);
        println!("{:016b} {}", val16, 4 * (val16 & 0b0000111111111111));
        let val16 = interlace_u8(rom.data[ptr + 31 - 11], rom.data[ptr + 31 - 12]);
        println!("{:016b} {}", val16, 4 * (val16 & 0b0000111111111111));
        let val16 = interlace_u8(rom.data[ptr + 31 - 13], rom.data[ptr + 31 - 14]);
        println!("{:016b} {}", val16, 4 * (val16 & 0b0000111111111111));

        match &table.entries[idx] {
            TableEntry::Lookup(lookup) => {
                for column in Column::iter() {
                    let x = entry_addrs[lookup[column].as_ref().unwrap().next];
                    println!(
                        "{} : {:?} -> {:?}",
                        lookup[column].as_ref().unwrap().next,
                        column,
                        x
                    );
                }
            }
            TableEntry::Steady(steady) => {
                steady.pprint();
            }
        }

        for k in 0..8 {
            let schem = rom.to_partial_schem((4 * k)..(4 * (k + 1)));
            let mut file = std::fs::File::create(format!("rom{k}.schem")).unwrap();
            schem.finish(&mut file).unwrap();
        }
    }
}

#[derive(Debug, Clone)]
pub struct SteadyStateUses {
    ss_idx: usize,
    points: Vec<RowAndColumn>,
}

pub fn shrink() {
    let mut graph = Graph::load();
    graph.print_stats();
    graph.make_steady_states_unique_per_leaf();
    graph.reduce_steady_state_values();
    let ss_uses = graph.check();
    graph.populate_steady_state_blanks(ss_uses);
    graph.reduce_steady_state_values();
    graph.dedup_steady_states();
    graph.check();
    graph.print_stats();
    let (branches_json, steady_states_json) = graph.to_json();
    fs::write("branches.json", branches_json).unwrap();
    fs::write("steady_states.json", steady_states_json).unwrap();
    println!("Done");
}

pub fn make_mc_schem() {
    let mut graph = Graph::load();
    graph.reduce_steady_state_values();
    graph.eliminate_obvious_steadys();
    graph.print_stats();
    graph.to_mc_schem();
}

fn main() {
    make_mc_schem();
}
