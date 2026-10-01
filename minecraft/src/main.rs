mod dtypes;

use cantor::{ArrayMap, Finite};
use dtypes::*;
use serde_json::Value;
use std::collections::BTreeMap;
use std::fmt::Write;
use std::{collections::HashMap, fmt::Debug, fs};

fn main() {
    let graph = Graph::load();

    let mut t = graph.start();

    t.pprint();

    t.play(Column::C1);

    t.pprint();
}
