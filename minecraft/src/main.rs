pub mod dtypes;

use crate::dtypes::Graph;

fn main() {
    let mut graph = Graph::load();
    let ss_uses = graph.check();
    graph.populate_steady_state_blanks(ss_uses);
    graph.reduce_steady_state_values();
    graph.check();
    println!("Done");

    // println!("{:?}", graph);

    // let mut t = graph.start();

    // t.pprint();

    // t.play(Column::C1);

    // t.pprint();
}
