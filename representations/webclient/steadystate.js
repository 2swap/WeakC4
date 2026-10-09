// Standalone page for a single steady state, reached by ?pos=<leaf rep>.
// Draws the diagram as client.js does, then exhaustively validates it
// against a yellow who plays every move, except that when red threatens an
// immediate win, yellow only plays the blocking move(s), and yellow never
// hands red an immediate win unless it has no other choice. Along the way it
// collects, over every distinct final board, how often each cell ends up
// red/yellow/empty and how often it is part of red's winning line.

const boardcanvas = document.getElementById(`board`);
const boardctx = boardcanvas.getContext(`2d`);
const status_text = document.getElementById(`status`);

const ROWS = 6;
const COLUMNS = 7;
var square_sz = 52;
const DISK_COLORS = ["#026", "#900", "#760"];

const url_pos = new URLSearchParams(window.location.search).get('pos') || "";
const nodes = dataset.nodes_to_use;
const start_board = construct_board_arr(url_pos);

// Node names are reps, but accept a transposition of a leaf too.
function find_node(board) {
    if (nodes[url_pos]) return nodes[url_pos];
    const key = JSON.stringify(board);
    for (const name in nodes) {
        if (JSON.stringify(construct_board_arr(nodes[name].rep)) === key) return nodes[name];
    }
    return null;
}
const node = find_node(start_board);
const steady_state = node && !node.neighbors ? node.data.ss : null;

// Per-cell tallies, indexed [y][x], filled in by validate().
let num_terminals = 0;
let red_counts = null;
let yellow_counts = null;
let win_counts = null;

let mode = "diagram";

function zero_grid() {
    return Array.from({length: ROWS}, () => new Array(COLUMNS).fill(0));
}

function column_height(board, x) {
    for (let y = 0; y < ROWS; y++) {
        if (board[y][x] === 0) return y;
    }
    return -1;
}

// The cells of every line of 4+ that the disk at (x, y) completes.
function winning_cells(board, x, y) {
    const player = board[y][x];
    const cells = [];
    for (const [dx, dy] of [[1, 0], [0, 1], [1, 1], [1, -1]]) {
        const run = [[x, y]];
        for (const sign of [-1, 1]) {
            let nx = x + dx * sign, ny = y + dy * sign;
            while (nx >= 0 && nx < COLUMNS && ny >= 0 && ny < ROWS && board[ny][nx] === player) {
                run.push([nx, ny]);
                nx += dx * sign;
                ny += dy * sign;
            }
        }
        if (run.length >= 4) cells.push(...run);
    }
    return cells;
}

// Returns null on success, or a string describing the first failure.
function validate(diagram) {
    const board = start_board.map(row => row.slice());
    const visited = new Set();
    let path = "";
    red_counts = zero_grid();
    yellow_counts = zero_grid();
    win_counts = zero_grid();
    num_terminals = 0;

    function is_full() {
        for (let x = 0; x < COLUMNS; x++) if (column_height(board, x) !== -1) return false;
        return true;
    }

    function wins_at(x, player) {
        const y = column_height(board, x);
        if (y === -1) return false;
        board[y][x] = player;
        const won = winning_cells(board, x, y).length > 0;
        board[y][x] = 0;
        return won;
    }

    // Whether yellow playing x leaves red a winning move anywhere.
    function gives_red_win(x) {
        const y = column_height(board, x);
        board[y][x] = 2;
        let result = false;
        for (let rx = 0; rx < COLUMNS && !result; rx++) result = wins_at(rx, 1);
        board[y][x] = 0;
        return result;
    }

    // Red wins with the disk just placed at (x, y): tally the final board.
    // Red's move is a function of the board, and each red-to-move board is
    // visited once, so every final board is tallied exactly once.
    function record_terminal(x, y) {
        num_terminals++;
        for (let ty = 0; ty < ROWS; ty++) {
            for (let tx = 0; tx < COLUMNS; tx++) {
                if (board[ty][tx] === 1) red_counts[ty][tx]++;
                else if (board[ty][tx] === 2) yellow_counts[ty][tx]++;
            }
        }
        const marked = new Set();
        for (const [wx, wy] of winning_cells(board, x, y)) {
            if (marked.has(wy * COLUMNS + wx)) continue;
            marked.add(wy * COLUMNS + wx);
            win_counts[wy][wx]++;
        }
    }

    function red_turn() {
        const key = board.map(row => row.join("")).join("");
        if (visited.has(key)) return null;
        visited.add(key);

        const move = querySteadyState(board, diagram);
        if (move < 1) return "the diagram gives red no move after " + (url_pos + path);
        const x = move - 1;
        const y = column_height(board, x);
        if (y === -1) return "the diagram plays into a full column after " + (url_pos + path);
        board[y][x] = 1;
        path += move;
        let result = null;
        if (winning_cells(board, x, y).length > 0) record_terminal(x, y);
        else if (is_full()) result = "the game is drawn at " + (url_pos + path);
        else result = yellow_turn();
        board[y][x] = 0;
        path = path.slice(0, -1);
        return result;
    }

    function yellow_turn() {
        const playable = [];
        for (let x = 0; x < COLUMNS; x++) if (column_height(board, x) !== -1) playable.push(x);

        for (const x of playable) {
            if (wins_at(x, 2)) return "yellow wins by playing " + (x + 1) + " after " + (url_pos + path);
        }
        const blocks = playable.filter(x => wins_at(x, 1));
        const candidates = blocks.length > 0 ? blocks : playable;
        // Skip moves that hand red an immediate win, unless every move does.
        const safe = candidates.filter(x => !gives_red_win(x));
        const moves = safe.length > 0 ? safe : candidates;

        for (const x of moves) {
            const y = column_height(board, x);
            board[y][x] = 2;
            path += (x + 1);
            const result = is_full() ? "the game is drawn at " + (url_pos + path) : red_turn();
            board[y][x] = 0;
            path = path.slice(0, -1);
            if (result) return result;
        }
        return null;
    }

    if (checkForWin(board)) return "the position is already won";
    return url_pos.length % 2 === 0 ? red_turn() : yellow_turn();
}

function cell_center(x, y) {
    return [(x + 0.5) * square_sz, (ROWS - 1 - y + 0.5) * square_sz];
}

function fill_disk(px, py, radius, color) {
    boardctx.fillStyle = color;
    boardctx.beginPath();
    boardctx.arc(px, py, radius, 0, 2 * Math.PI, false);
    boardctx.fill();
}

function percent_label(px, py, fraction) {
    if (fraction <= 0) return;
    boardctx.fillStyle = "white";
    boardctx.font = "16px Arial";
    boardctx.fillText(Math.round(100 * fraction) + "%", px, py + 6);
}

// Same rendering as client.js's drawDisk.
function draw_diagram_cell(x, y) {
    const [px, py] = cell_center(x, y);
    fill_disk(px, py, 23, DISK_COLORS[start_board[y][x]]);
    const ss = steady_state[ROWS - 1 - y].charAt(x);
    if (ss !== 'R' && ss !== 'Y' && ss !== ' ') {
        boardctx.fillStyle = "white";
        boardctx.font = "31px Arial";
        boardctx.fillText(ss, px, py + 12);
    }
}

// A pie of how often the cell ends red, yellow, or empty.
function draw_color_cell(x, y) {
    const [px, py] = cell_center(x, y);
    const fractions = [
        [red_counts[y][x] / num_terminals, DISK_COLORS[1]],
        [yellow_counts[y][x] / num_terminals, DISK_COLORS[2]],
    ];
    fill_disk(px, py, 23, DISK_COLORS[0]);
    let angle = -Math.PI / 2;
    for (const [fraction, color] of fractions) {
        if (fraction <= 0) continue;
        boardctx.fillStyle = color;
        boardctx.beginPath();
        boardctx.moveTo(px, py);
        boardctx.arc(px, py, 23, angle, angle + 2 * Math.PI * fraction, false);
        boardctx.closePath();
        boardctx.fill();
        angle += 2 * Math.PI * fraction;
    }
}

// A neon blue ring around the disk, with opacity by frequency.
function draw_win_cell(x, y) {
    const [px, py] = cell_center(x, y);
    const fraction = win_counts[y][x] / num_terminals;
    fill_disk(px, py, 23, DISK_COLORS[start_board[y][x]]);
    if (fraction > 0) {
        boardctx.globalAlpha = fraction;
        boardctx.strokeStyle = "#1ef";
        boardctx.lineWidth = 3;
        boardctx.beginPath();
        boardctx.arc(px, py, 23.5, 0, 2 * Math.PI, false);
        boardctx.stroke();
        boardctx.globalAlpha = 1;
    }
    percent_label(px, py, fraction);
}

function render() {
    boardcanvas.width = COLUMNS * square_sz;
    boardcanvas.height = ROWS * square_sz;
    boardctx.textAlign = "center";
    const draw_cell = {diagram: draw_diagram_cell, color: draw_color_cell, win: draw_win_cell}[mode];
    for (let x = 0; x < COLUMNS; x++) {
        for (let y = 0; y < ROWS; y++) {
            draw_cell(x, y);
        }
    }
    for (const name of ["diagram", "color", "win"]) {
        document.getElementById("mode-" + name).classList.toggle("active", name === mode);
    }
}

for (const name of ["diagram", "color", "win"]) {
    document.getElementById("mode-" + name).addEventListener('click', function(){
        mode = name;
        render();
    });
}

if (!steady_state) {
    status_text.textContent = "No steady state found for position \"" + url_pos + "\".";
} else {
    render();
    // Let the "Validating..." text paint before the search blocks the page.
    setTimeout(function(){
        const failure = validate(steady_state);
        if (failure) {
            status_text.textContent = "Validation failed: " + failure + ".";
        } else {
            status_text.textContent = "Validated.";
            document.getElementById("mode-color").disabled = false;
            document.getElementById("mode-win").disabled = false;
        }
    }, 50);
}
