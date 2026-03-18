const boardcanvas = document.getElementById(`board`);
const graphcanvas = document.getElementById(`graph`);
const boardctx = boardcanvas.getContext(`2d`);
const graphctx = graphcanvas.getContext(`2d`);
const w = graphcanvas.width = window.innerWidth;
const h = graphcanvas.height = window.innerHeight;
// Loading message while the data is being fetched and processed
document.getElementById("loading-message").style.display = "block";

var EMPTY       = "#049";
var RED         = "#f00";
var YELLOW      = "#ff0";

function get_color(name, neighbor_name){
    return Math.min(nodes[name].rep.length, nodes[neighbor_name].rep.length)%2==1?YELLOW:RED
}

let board_arr = 0;

var square_sz = 40;
var extraMoves = "";

function hash_a_board(board_to_hash) {
    let a = 1;
    let semihash = 0;
    for (let i = 0; i < dataset.board_h; i++) {
        for (let j = 0; j < dataset.board_w; j++) {
            semihash += board_to_hash[dataset.board_h-1-i][j] * a;
            a *= 1.021813947;
        }
    }

    var closedist = 0.00000001;
    var closename = -1;
    for(name in nodes){
        var dist = Math.abs(semihash-name);
        if(dist < closedist){
            closename = name;
            closedist = dist;
        }
    }
    return closename;
}

function construct_board_arr(board_string) {
    let board_arr = [];
    for (let y = 0; y < 6; y++) {
        board_arr[y] = [];
        for (let x = 0; x < 7; x++) {
            board_arr[y][x] = 0;
        }
    }

    for (var i = 0; i < board_string.length; i++) {
        var x = String.fromCharCode(board_string.charCodeAt(i)) - 1;

        // Place the piece
        for (var y = 0; y < 6; y++) {
            if (board_arr[y][x] === 0) {
                board_arr[y][x] = i % 2 + 1;
                break;
            }
        }
    }

    return board_arr;
}

function render_board () {
    boardcanvas.width = parseInt(dataset.board_w) * square_sz;
    boardcanvas.height = parseInt(dataset.board_h) * square_sz + 80;
    boardctx.font = "24px Arial";
    boardctx.textAlign = "center";
    board_arr = construct_board_arr(repstr());

    // Detect winning lines
    const winningLine = checkForWin(board_arr);

    // Draw the board
    for (var x = 0; x < 7; x++) {
        for (var y = 0; y < 6; y++) {
            drawStone(x, y, board_arr[y][x], winningLine);
        }
    }

    boardctx.font = "15px Arial";
    boardctx.textAlign = "left";
    boardctx.fillStyle = "white";
    var dy = 0;
    opening = nodes[hash].prefix;
    boardctx.fillText("Opening name: " + opening, 8, (dy+=16)+square_sz * dataset.board_h);
    if(winningLine)
        boardctx.fillText("Press 'r' to reset!", 8, (dy+=16)+square_sz * dataset.board_h);
    else if(extraMoves == "") {
        boardctx.fillText("Click to play against the weak solution!", 8, (dy+=16)+square_sz * dataset.board_h);
    } else {
        boardctx.fillText("This is a Steady State Diagram,"  , 8, (dy+=16)+square_sz * dataset.board_h);
        boardctx.fillText("which instructs the agent to play", 8, (dy+=16)+square_sz * dataset.board_h);
        boardctx.fillText("perfectly from here on."          , 8, (dy+=16)+square_sz * dataset.board_h);
    }
}

// Helper function to draw a stone
function drawStone(x, y, col, winningLine) {
    col = ["#026", "#900", "#760"][col];
    const px = (x + 0.5) * square_sz;
    const py = (5 - y + 0.5) * square_sz;

    boardctx.fillStyle = col;
    boardctx.beginPath();
    boardctx.arc(px, py, 18, 0, 2 * Math.PI, false);
    boardctx.fill();

    // Highlight winning stones
    if (winningLine && winningLine.some(([wy, wx]) => wx === x && wy === y)) {
        boardctx.fillStyle = "gold"; // Highlight color
        boardctx.beginPath();
        boardctx.arc(px, py, 10, 0, 2 * Math.PI, false);
        boardctx.fill();
    }

    boardctx.fillStyle = "white";

    // Draw steady state markers if needed
    const ss = String.fromCharCode(nodes[hash].data.ss[5 - y][x]);
    if (ss !== '1' && ss !== '2') {
        boardctx.fillText(ss, px, py + 9);
    }
}

// Return true if Board equals subBoard in all non-zero positions
function isSubBoard(superBoard, subBoard) {
    for (let y = 0; y < 6; y++) {
        for (let x = 0; x < 7; x++) {
            if (subBoard[y][x] !== 0 && superBoard[y][x] !== subBoard[y][x]) {
                return false;
            }
        }
    }
    return true;
}

// Helper function to check for a win
function checkForWin(board) {
    const directions = [
        { dx: 1, dy: 0 }, // Horizontal
        { dx: 0, dy: 1 }, // Vertical
        { dx: 1, dy: 1 }, // Diagonal down-right
        { dx: 1, dy: -1 } // Diagonal up-right
    ];

    for (let y = 0; y < 6; y++) {
        for (let x = 0; x < 7; x++) {
            const player = board[y][x];
            if (player === 0) continue; // Skip empty cells

            for (let { dx, dy } of directions) {
                const line = [[y, x]];

                for (let step = 1; step < 4; step++) {
                    const nx = x + dx * step;
                    const ny = y + dy * step;

                    if (nx < 0 || nx >= 7 || ny < 0 || ny >= 6 || board[ny][nx] !== player) {
                        break;
                    }

                    line.push([ny, nx]);
                }

                if (line.length === 4) {
                    return line; // Return the winning line
                }
            }
        }
    }

    return null; // No winning line found
}

boardcanvas.addEventListener('click', handleClick);

function handleClick(event) {
    // Get the mouse click coordinates relative to the canvas
    const rect = boardcanvas.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;

    // Calculate the column where the player clicked
    const column = Math.floor(mouseX / square_sz);

    // Call a function to handle the player's move in this column
    makeMoveAsYellow(column + 1);
}

function makeMoveAsRed(){
    if(repstr().length%2 == 1) return;
    var thishash = hash_a_board(board_arr);
    if(nodes[thishash] && nodes[thishash].neighbors){
        for(var neighbor_id in nodes[thishash].neighbors){
            var neighbor_hash = nodes[thishash].neighbors[neighbor_id];
            var neighbor = nodes[neighbor_hash];
            if(neighbor.rep.length > nodes[thishash].rep.length){
                hash = neighbor_hash;
                extraMoves = "";
                on_board_change();
                update_opacity();
                return;
            }
        }
    }
    else {
        extraMoves += querySteadyState(board_arr, nodes[hash].data.ss);
        on_board_change();
    }
}

function querySteadyState(boardArr, steadyState) {
    const ROWS = 6;
    const COLUMNS = 7;

    // Helper to get the state of a column
    function getColumnState(x) {
        for (let y = 0; y < ROWS; y++) {
            if (boardArr[y][x] === 0) return y; // Find the first empty spot in column x
        }
        return -1; // Column is full
    }

    // Check if placing a piece in column x wins the game for the given player
    function checkWin(board, x, player) {
        const y = getColumnState(x);
        if (y === -1) return false; // Column is full
        board[y][x] = player; // Temporarily place the piece
        const isWin = checkFourInARow(board, x, y, player); // Check win condition
        board[y][x] = 0; // Undo the temporary placement
        return isWin;
    }

    // Check if there are four in a row
    function checkFourInARow(board, x, y, player) {
        // Check horizontal, vertical, and two diagonals
        const directions = [
            { dx: 1, dy: 0 }, { dx: 0, dy: 1 },
            { dx: 1, dy: 1 }, { dx: 1, dy: -1 }
        ];
        for (let { dx, dy } of directions) {
            let count = 1;
            for (let sign = -1; sign <= 1; sign += 2) {
                for (let step = 1; step < 4; step++) {
                    const nx = x + dx * step * sign;
                    const ny = y + dy * step * sign;
                    if (nx < 0 || ny < 0 || nx >= COLUMNS || ny >= ROWS) break;
                    if (board[ny][nx] !== player) break;
                    count++;
                }
            }
            if (count >= 4) return true;
        }
        return false;
    }

    // Decode steady state character to priority
    function decodePriority(c) {
        switch (String.fromCharCode(c)) {
            case '@': return 'miai';
            case ' ': case '.': return 'claimeven';
            case '|': return 'claimodd';
            case '+': return 'plus';
            case '=': return 'equal';
            case '-': return 'minus';
            case '1': return 'red';
            case '2': return 'yellow';
            case '!': return 'urgent';
            default: throw new Error(`Invalid character in steadyState: ${String.fromCharCode(c)}`);
        }
    }

    // Identify instant wins
    for (let x = 0; x < COLUMNS; x++) {
        if (getColumnState(x) !== -1) {
            if (checkWin(boardArr, x, 1)) return x + 1; // Player 1 wins
        }
    }

    // Identify blocking moves
    for (let x = 0; x < COLUMNS; x++) {
        if (getColumnState(x) !== -1) {
            if (checkWin(boardArr, x, 2)) return x + 1; // Block Player 2's win
        }
    }

    // Priority order
    const priorities = ['urgent', 'miai', 'claimeven', 'claimodd', 'plus', 'equal', 'minus'];

    for (let priority of priorities) {
        let validMoves = [];
        for (let x = 0; x < COLUMNS; x++) {
            y = getColumnState(x);
            if(y == -1) continue;
            y = 5-y;
            const ch = steadyState[y][x];
            if (decodePriority(ch) === priority) {
                // Handle special cases
                if (priority === 'miai') {
                    validMoves.push(x);
                    if (validMoves.length > 1) break; // Ignore if more than one miai
                } else if (priority === 'claimeven') {
                    if (y % 2 === 0) return x + 1; // Only valid for even rows
                } else if (priority === 'claimodd') {
                    if (y % 2 === 1) return x + 1; // Only valid for odd rows
                } else {
                    return x + 1; // Return move for other priorities
                }
            }
        }
        // If only one valid miai, return it
        if (priority === 'miai' && validMoves.length === 1) return validMoves[0] + 1;
    }

    // No valid move found
    return -4;
}

setInterval(makeMoveAsRed, 300);

function update_opacity() {
    if(!nodes[hash]) return;
    if(!nodes[hash].neighbors) {
        for (const name in nodes) nodes[name].opacity = 1;
        return;
    }

    // Set all nodes' opacities to 0.2
    for (const name in nodes) nodes[name].opacity = .4;

    // Flood-fill algorithm to set reachable nodes' opacity to 1
    let stack = [hash];
    while (stack.length > 0) {
        let current = stack.pop();
        if (nodes[current].opacity === 1) continue;
        nodes[current].opacity = 1;
        if(!nodes[current].neighbors) continue;
        for (const neighbor_name of nodes[current].neighbors) {
            if (nodes[neighbor_name].opacity === .4) {
                stack.push(neighbor_name);
            }
        }
    }
}

function on_click_node(){ hash_stack = [{"hash":0,"extra":""}]; extraMoves = ""; update_opacity(); }

function repstr(){
    return nodes[hash].rep + extraMoves;
}

function makeMoveAsYellow(column) {
    if(checkForWin(board_arr) != null) return;
    if(repstr().length%2 == 0) return;
    let x = column-1;

    let who = nodes[hash].rep.length%2 + 1

    // place the piece
    for (var y=0; y<6; y++) {
        if(board_arr[y][x] === 0){
            board_arr[y][x] = who;
            break;
        }
        if(y == 5) return false;
    }
    hash_stack.push({"hash": hash, "extra": extraMoves});
    newhash = hash_a_board(board_arr);
    if (newhash != -1) {
        hash = newhash;
        extraMoves = "";
    }
    else extraMoves += column;


    on_board_change();
    update_opacity();
    makeMoveAsRed();
    return newhash != -1;
}

var nodes_to_use = false;
let nodes = false;
var hash = 0;
var hash_stack = 0;
var openings_on = false;


let boardbutton = false;
let board_click_start = {x:0,y:0};
let diffcoords = {x:0,y:0};
let board_click_square = ';';

on_board_change = function(){};

const prefixList = [
    {"Two-bar": ["436766"]},
    {"Bent two-bar": ["436761663"]},
    {"Short Cup Opening": ["46213522"]},
    {"Tall Cup Opening": ["46213524224"]},
    {"No Cup Opening": ["46213523"]},
    {"6-1": ["4444445"]},
    {"47": ["47"]},
    {"426566": ["426566"]},
    {"426564": ["426564"]},
    {"Shoulder Spike": ["44444521", "44444524"]},
    {"4444452": ["4444452"]},
    {"True Candlesticks": ["44444222266"]},
    {"Half Candlesticks": ["444442222", "444446622"]},
    {"Crown Variations": ["44444"]},
    {"D3-D4 Openings": ["4442", "4441"]},
    {"4363": ["4363"]},
    {"Fist Variations": ["4366755535"]},
    {"Palm Variations": ["436556766"]},
    {"4366": ["4366"]},
    {"Triline": ["4623272", "4623262"]},
    {"Other 4367 Lines": ["4367"]},
    {"3-2": ["4443673", "4443613"]},
    {"Two-holes": ["4361"]},
    {"Other 462 Lines": ["462"]},
    {"Hills Opening": ["4443655", "4364455", "4365", "452443"]},
    {"Very Beginning": [""]}
]

// Set the prefix for each node based on the prefixList
function set_one_prefix(dict) {
    const pref = Object.keys(dict)[0];
    const sequence_list = dict[pref];
    for (const prefix_half of sequence_list) {
        const norm_and_inv = [prefix_half, invert_around_4(prefix_half)];
        for(const prefix of norm_and_inv) {
            const hash_of_prefix = hash_a_board(construct_board_arr(prefix));
            var stack = [hash_of_prefix];
            while (stack.length > 0) {
                let current = stack.pop();
                if(typeof nodes[current] == "undefined") continue;
                if(nodes[current].prefix) continue;
                nodes[current].prefix = pref;
                if (!nodes[current].neighbors) continue;
                for (const neighbor_name of nodes[current].neighbors) {
                    if(!nodes[neighbor_name].prefix)
                    stack.push(neighbor_name);
                }
            }
        }
    }
}

function set_prefixes() {
    for (const dict of prefixList) {
        set_one_prefix(dict);
    }

    // Copy prefixes onto dataset
    for (const name in nodes) {
        dataset.nodes_to_use[name].prefix = nodes[name].prefix;
    }
    document.getElementById("loading-message").style.display = "none";
}

// optional color mapping
var prefixColors = { };
// Make color mapping for each prefix, using a hash function to generate a color from the prefix string
for (const dict of prefixList) {
    const pref = Object.keys(dict)[0];
    let hash = 0;
    for (let i = 0; i < pref.length; i++) {
        hash = pref.charCodeAt(i) + (hash << 4);
        // Modulus by a large prime
        hash %= 100007;
    }
    hash = hash << 5;
    const color = `hsl(${hash % 359}, ${20 + (hash % 71)}%, ${30 + (hash % 53)}%)`;
    prefixColors[pref] = color;
}

function sum_digits(str) {
    let sum = 0;
    for (let char of str) {
        sum += char.charCodeAt(0) - '0'.charCodeAt(0);
    }
    return sum;
}

// Used in the console to populate the anki deck's practice section
function get_one_opening_per_leaf(){
    // Here, by leaf, we mean red nodes for whom all neighbors are terminal.
    var leaves = {};
    var num_leaves_left = 0;
    for (const name in nodes) {
        // If this is red-to-play (even-length rep), skip
        if (nodes[name].rep.length % 2 === 0) continue;
        var is_leaf = true;
        for (const neighbor of nodes[name].neighbors) {
            if (nodes[neighbor].neighbors != null && Object.keys(nodes[neighbor].neighbors).length > 0) {
                is_leaf = false;
                break;
            }
        }
        if (is_leaf) {
            leaves[name] = 0;
            num_leaves_left++;
        }
    }

    console.log("There are " + num_leaves_left + " leaves in the graph. Getting one opening per leaf...");

    openings = [];
    while (num_leaves_left > 0) {
        // Randomly make moves until arriving at a leaf.
        // If the leaf's opening is already in the list, discard and try again, otherwise add it to the list.
        var hash_here = dataset.root_node_hash;
        var appendy_string = "";
        var digitsum = 0;
        while (nodes[hash_here].neighbors != null && Object.keys(nodes[hash_here].neighbors).length > 0) {
            const last_hash = hash_here;
            const last_digitsum = digitsum;
            const last_appendy_string = appendy_string;
            var neighbor_names = nodes[hash_here].neighbors;
            var random_neighbor_name = neighbor_names[Math.floor(Math.random() * neighbor_names.length)];
            var new_sum = sum_digits(nodes[random_neighbor_name].rep);
            var char_to_append = String.fromCharCode((new_sum - digitsum) + '0'.charCodeAt(0));
            appendy_string += char_to_append;
            hash_here = random_neighbor_name;
            digitsum = new_sum;

            // If we have hit a leaf
            if(leaves[hash_here] === 0){
                leaves[hash_here] = 1;
                num_leaves_left--;
                openings.push(appendy_string);
                console.log("There are " + num_leaves_left + " leaves left. Got opening: " + appendy_string);
                break;
            }
            // If we have already got an opening from this leaf, restart
            else if(leaves[hash_here] === 1) break;
            // If there are no neighbors from here, undo the last move
            else if(nodes[hash_here].neighbors == null || Object.keys(nodes[hash_here].neighbors).length == 0){
                hash_here = last_hash;
                digitsum = last_digitsum;
                appendy_string = last_appendy_string;
            }
        }
    }
    return openings;
}

function invert_around_4(str) {
    let result = "";
    for (let char of str) {
        const invertedDigit = 8 - (char.charCodeAt(0) - '0'.charCodeAt(0));
        result += String.fromCharCode(invertedDigit + '0'.charCodeAt(0));
    }
    return result;
}

$(document).ready(async function() {
    if (/Mobi|Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
        document.body.style.margin = '0';
        document.body.style.padding = '0';
        document.body.style.fontFamily = "'Arial', sans-serif";
        document.body.style.color = '#bbf';
        document.body.style.backgroundColor = '#000';
        document.body.style.display = 'flex';
        document.body.style.justifyContent = 'center';
        document.body.style.alignItems = 'center';
        document.body.style.height = '100vh';
        document.body.style.textAlign = 'center';

        // Remove the canvas and other elements when on mobile
        const rootDiv = document.querySelector('div[style*="position: relative"]');
        if (rootDiv) {
          rootDiv.remove();
        }

        document.body.innerHTML = '<div style="padding: 20px;"><h1>Desktop Only</h1><p>This page is only available on desktop devices.</p></div>';
        return;
    }

    try {
        nodes_to_use = dataset.nodes_to_use;

        let tick = 0;
        let ox = 0; let oy = 100; let zoom = 1;
        let alpha = 0.8, beta=0;

        nodes = {};

        function reset_hash(){
            hash_stack = [{"hash":0, "extra":""}];
            hash = dataset.root_node_hash;
            for (const name in nodes) nodes[name].opacity = 1;
            on_click_node();
        }

        reset_hash();

        resizePointCloud();

        function resizePointCloud() {
            nodes = {};
            var sqrtwh = Math.sqrt(w * h);
            var min_x = Number.POSITIVE_INFINITY;
            var max_x = Number.NEGATIVE_INFINITY;
            var min_y = Number.POSITIVE_INFINITY;
            var max_y = Number.NEGATIVE_INFINITY;
            var min_z = Number.POSITIVE_INFINITY;
            var max_z = Number.NEGATIVE_INFINITY;

            // Compute the min and max values for x, y, and z
            for (const name in nodes_to_use) {
                const node = nodes_to_use[name];
                min_x = Math.min(min_x, node.x);
                max_x = Math.max(max_x, node.x);
                min_y = Math.min(min_y, node.y);
                max_y = Math.max(max_y, node.y);
                min_z = Math.min(min_z, node.z);
                max_z = Math.max(max_z, node.z);
            }

            // Calculate the center of the point cloud
            var center_x = (min_x + max_x) / 2;
            var center_y = (min_y + max_y) / 2;
            var center_z = (min_z + max_z) / 2;

            // Calculate the scale factor
            var max_dimension = Math.max(max_x - min_x, max_y - min_y, max_z - min_z);
            var scale_factor = sqrtwh * .5 / max_dimension;

            // Apply the transformation to each node
            for (const name in nodes_to_use) {
                var node = nodes_to_use[name];
                node.x = (node.x - center_x) * scale_factor;
                node.y = (node.y - center_y) * scale_factor;
                node.z = (node.z - center_z) * scale_factor;
                node.opacity = 1;
                nodes[name] = node;
            }

            // Call set_prefixes_async asynchronously
        }

        function render_blurb(){
            graphctx.textAlign = 'left';
            graphctx.globalAlpha = 1;
            var y = h - 196;
            graphctx.fillStyle = "white";
            graphctx.font = "16px Arial";
            graphctx.fillText("", 20, y+=16)
            // Replace the info html nodes count with the actual count
            let info = document.getElementById("info");
            info.innerHTML = info.innerHTML.replace(/<nodes>/g, Object.keys(nodes).length);
        }

        function render_graph() {
            graphctx.globalAlpha = 1;
            graphctx.lineWidth = 0.5;
            for (const name in nodes) get_node_coordinates(name);
            for (const name in nodes) {
                const node = nodes[name];
                for (const neighbor_idx in node.neighbors) {
                    const neighbor_name = node.neighbors[neighbor_idx];
                    const neighbor = nodes[neighbor_name];
                    if(typeof neighbor == "undefined") continue;
                    if(name < neighbor_name && (neighbor.neighbors != null && name in neighbor.neighbors)) continue;
                    graphctx.globalAlpha = openings_on?0.2:(node.opacity * neighbor.opacity);
                    graphctx.strokeStyle = get_color(name, neighbor_name);
                    graphctx.beginPath();
                    graphctx.moveTo(node.screen_x, node.screen_y);
                    graphctx.lineTo(neighbor.screen_x, neighbor.screen_y);
                    graphctx.stroke();
                    graphctx.globalAlpha = 1;
                }
                if(openings_on && (nodes[hash].rep.length < 2 || node.prefix == nodes[hash].prefix)){
                    graphctx.fillStyle = prefixColors[node.prefix];
                    graphctx.fillRect(node.screen_x-1, node.screen_y-1, 3, 3);
                }
            }
            graphctx.strokeStyle = `white`;
            graphctx.lineWidth = 2;
            graphctx.beginPath();
            graphctx.arc(nodes[hash].screen_x, nodes[hash].screen_y, 10, 0, 2*Math.PI);
            graphctx.stroke();
        }

        function uppercase_it(str){
            return str.charAt(0).toUpperCase() + str.slice(1);
        }

        function render() {
            graphctx.globalAlpha = 1;
            graphctx.fillStyle = `Black`;
            graphctx.fillRect(0, 0, w, h);
            graphctx.textBaseline = 'bottom';

            render_graph();
            render_blurb();
            document.getElementById("strongsolver").href = "https://connect4.gamesolver.org/?pos=" + nodes[hash].rep;
        }

        function get_node_coordinates (hash) {
            var node = nodes[hash];
            var rotatedX = node.x * Math.cos(alpha) + node.z * Math.sin(alpha);
            var rotatedZ = -node.x * Math.sin(alpha) + node.z * Math.cos(alpha);
            var rotatedY = rotatedZ * Math.sin(beta) + node.y * Math.cos(beta);

            node.screen_x = (rotatedX - ox) / zoom + w / 2;
            node.screen_y = (rotatedY - oy) / zoom + h / 2;
        }

        function get_closest_node_to (coords) {
            var min_dist = 100000000;
            var best_node = "";
            for (const name in nodes) {
                const node = nodes[name];
                var d = Math.hypot(node.screen_x-coords.x, node.screen_y-coords.y);
                if (d < min_dist) {
                    min_dist = d;
                    best_node = name;
                }
            }
            if(min_dist > 150) return hash;
            return best_node;
        }

        window.addEventListener(`wheel`,
            (event) => {
                zoom *= Math.pow(1.2, Math.sign(event.deltaY));
                render();
            }
        );
        graphcanvas.addEventListener(`mousedown`, function(e){
            var rect = graphcanvas.getBoundingClientRect();
            var screen_coords = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
            hash = get_closest_node_to(screen_coords);
            on_click_node();
            on_board_change();
        }, false);

        window.addEventListener(`keydown`, key, false);

        function key (e) {
            // if the user-input element is focused, ignore the key event
            if (document.activeElement.id === 'user-input') return;
            const c = e.keyCode;
            const ch = String.fromCharCode(c);
            if (c == 37) ox -= zoom * 100;
            if (c == 38) oy -= zoom * 100;
            if (c == 39) ox += zoom * 100;
            if (c == 40) oy += zoom * 100;
            if (ch == 'A') alpha -= .04;
            if (ch == 'D') alpha += .04;
            if (ch == 'S') beta -= .04;
            if (ch == 'W') beta += .04;
            if (ch == 'O') openings_on = !openings_on;
            if (ch == 'U') {
                if(hash_stack.length > 1) {
                    let obj = hash_stack.pop();
                    hash = obj.hash;
                    extraMoves = obj.extra;
                }
                update_opacity();
            }
            if (ch == 'R') {
                reset_hash();
                for (const name in nodes) nodes[name].opacity = 1;
            }
            on_board_change();
        }

        on_board_change = function(){
            render();
            render_board();
            console.log(hash + " / " + nodes[hash].rep);
            // Insert pos= into the URL for easy sharing
            const url = new URL(window.location);
            url.searchParams.set('pos', nodes[hash].rep);
            window.history.pushState({}, '', url);
        }

        set_prefixes();

        // If the user uses a URL ending in ?pos=4366, find url_pos = 4366
        var urlParams = new URLSearchParams(window.location.search);
        var url_pos = urlParams.get('pos');
        if(url_pos) {
            hash = hash_a_board(construct_board_arr(url_pos));
            if(hash == -1) hash = 0;
            extraMoves = "";
        }
        update_opacity();
        on_board_change();

    } catch (error) {
        console.error('Error loading or parsing data:', error);
    }
});

