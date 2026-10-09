// Pure Connect-4 helpers shared by client.js and steadystate.js.
// Boards are board[y][x], y=0 the bottom row; 0 empty, 1 red, 2 yellow.

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

// Red's move from a steady state diagram, mirroring
// solution/validate_solution.py's query_steady_state.
function querySteadyState(boardArr, steadyState) {
    const ROWS = 6;
    const COLUMNS = 7;
    const LEVELS = "0123456789";

    function getColumnState(x) {
        for (let y = 0; y < ROWS; y++) {
            if (boardArr[y][x] === 0) return y; // Find the first empty spot in column x
        }
        return -1; // Column is full
    }

    function checkFourInARow(board, x, y, player) {
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

    function checkWin(board, x, player) {
        const y = getColumnState(x);
        if (y === -1) return false;
        board[y][x] = player;
        const isWin = checkFourInARow(board, x, y, player);
        board[y][x] = 0;
        return isWin;
    }

    // Take a win, otherwise block one.
    for (let player = 1; player <= 2; player++) {
        for (let x = 0; x < COLUMNS; x++) {
            if (getColumnState(x) !== -1 && checkWin(boardArr, x, player)) return x + 1;
        }
    }

    // Scan the priority levels; play the first with exactly one playable cell.
    for (const ch of LEVELS) {
        const found = [];
        for (let x = 0; x < COLUMNS; x++) {
            const yb = getColumnState(x);
            if (yb === -1) continue;
            const yt = ROWS - 1 - yb;
            if (steadyState[yt].charAt(x) === ch) found.push(x + 1);
        }
        if (found.length === 1) return found[0];
    }

    // No valid move found
    return -4;
}
