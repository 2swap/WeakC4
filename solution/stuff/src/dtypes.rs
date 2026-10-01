use cantor::{ArrayMap, Finite};
use serde_json::Value;
use std::collections::BTreeMap;
use std::fmt::Write;
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
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord, Finite)]
pub struct RowAndColumn {
    pub row: Row,
    pub column: Column,
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

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Board {
    state: LabelledBoard<Option<Player>>,
    turn: Player,
}

impl Board {
    pub fn pprint(&self) {
        for (ri, r) in Row::iter()
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
                        Some(Player::First) => "O",
                        Some(Player::Second) => "X",
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

    pub fn from_path(mut columns: Vec<Column>) -> Self {
        if let Some(last) = columns.pop() {
            let board = Self::from_path(columns);
            board.play(last).unwrap()
        } else {
            Self::empty()
        }
    }
}

#[derive(Debug, Clone)]
pub enum SteadyStateSymbol {
    Blank,
    Value(u8),
}

#[derive(Debug, Clone)]
pub struct Edge {
    pub flip: bool,
    pub node_idx: usize,
}

#[derive(Clone)]
pub enum Node {
    Steady { ss_idx: usize },
    Response(Column, ArrayMap<Column, Option<Edge>>),
}

impl std::fmt::Debug for Node {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Steady { ss_idx } => f.debug_struct("Steady").field("ss_idx", ss_idx).finish(),
            Self::Response(arg0, arg1) => f
                .debug_tuple("Response")
                .field(arg0)
                .field(
                    &Column::iter()
                        .map(|c| (c, &arg1[c]))
                        .collect::<HashMap<_, _>>(),
                )
                .finish(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct Graph {
    root: Edge,
    nodes: Vec<Node>,
    steady: Vec<LabelledBoard<SteadyStateSymbol>>,
}

#[derive(Debug, Clone)]
pub struct GraphTraversal<'g> {
    graph: &'g Graph,
    path: Vec<Column>,
    flip: bool,
}

impl<'g> GraphTraversal<'g> {
    pub fn pprint(&self) {
        let mut board = Board::from_path(self.path.clone());
        if self.flip {
            board = board.flip();
        }
        board.pprint();
    }
}

impl Graph {
    pub fn start<'g>(&'g self) -> GraphTraversal<'g> {
        GraphTraversal {
            graph: self,
            path: vec![],
            flip: false,
        }
    }
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

        let branches_json_string = fs::read_to_string("../branches.json").unwrap();
        let branches_json: HashMap<String, Value> =
            serde_json::from_str(&branches_json_string).unwrap();
        #[derive(Debug)]
        enum BranchesEdge {
            SteadyState { idx: usize },
            Move(Column),
        }
        let branches: BTreeMap<Board, BranchesEdge> = branches_json
            .into_iter()
            .map(|(path, edge)| {
                let path = path.chars().map(char_to_column).collect();
                (
                    Board::from_path(path),
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

        let steady_states_json_string = fs::read_to_string("../steady_states.json").unwrap();
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
            fn node(&mut self, board: Board) -> Edge {
                debug_assert_eq!(board.turn(), Player::First);

                for (idx, (existing_board, _)) in self.nodes.iter().enumerate() {
                    if &board == existing_board {
                        return Edge {
                            flip: false,
                            node_idx: idx,
                        };
                    }
                }
                for (idx, (existing_board, _)) in self.nodes.iter().enumerate() {
                    if board == existing_board.flip() {
                        return Edge {
                            flip: true,
                            node_idx: idx,
                        };
                    }
                }

                let (flip, node) = if let Some((flip, branch_edge)) =
                    if let Some(branch_edge) = self.branches.get(&board) {
                        Some((false, branch_edge))
                    } else if let Some(branch_edge) = self.branches.get(&board.flip()) {
                        Some((true, branch_edge))
                    } else {
                        None
                    } {
                    match branch_edge {
                        BranchesEdge::SteadyState { idx } => (flip, Node::Steady { ss_idx: *idx }),
                        BranchesEdge::Move(column) => {
                            let column = *column;
                            (
                                false,
                                Node::Response(
                                    column,
                                    ArrayMap::new(|response| {
                                        if let Some(next_board) =
                                            board.clone().play(column).unwrap().play(response)
                                        {
                                            Some(self.node(next_board))
                                        } else {
                                            None
                                        }
                                    }),
                                ),
                            )
                        }
                    }
                } else {
                    (false, Node::Steady { ss_idx: 0 })
                };

                // deduplicate nodes pointing at the same steady state
                for (idx, (_, existing_node)) in self.nodes.iter().enumerate() {
                    if let Node::Steady { ss_idx: a } = node
                        && let Node::Steady { ss_idx: b } = existing_node
                        && a == *b
                    {
                        return Edge {
                            flip,
                            node_idx: idx,
                        };
                    }
                }

                let node_idx = self.nodes.len();
                self.nodes.push((board, node));
                Edge { flip, node_idx }
            }
        }

        let mut loader = Loader {
            branches,
            steady_states,
            nodes: vec![],
        };

        let root = loader.node(Board::from_path(vec![]));
        Graph {
            root,
            nodes: loader.nodes.into_iter().map(|(_, node)| node).collect(),
            steady: loader.steady_states,
        }
    }
}
