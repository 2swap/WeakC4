#!/usr/bin/env python3
"""Build the "2swap's Connect 4" Anki deck from solution/.
Reads solution/branches.json and solution/steady_states.json directly.
"""
import json
import random
import requests
import sys
from pathlib import Path

SOLUTION_DIR = Path(__file__).resolve().parent.parent.parent / "solution"
BRANCHES = SOLUTION_DIR / "branches.json"
STEADY_STATES = SOLUTION_DIR / "steady_states.json"

sys.path.insert(0, str(SOLUTION_DIR))
import validate_solution as solution  # noqa: E402

deck_name = "2swap's Connect 4"
branch_model_name = deck_name
steady_model_name = deck_name + " Steady State"

def anki_connect(action, params={}):
    try:
        if params is None:
            params = []
        request = json.dumps({"action": action, "version": 6, "params": params})
        response = requests.post("http://localhost:8765", data=request)
        resp_json = response.json()
        if 'error' in resp_json and resp_json['error']:
            print("AnkiConnect Error: " + str(resp_json['error']))
        return resp_json
    except requests.ConnectionError:
        print("AnkiConnect is not running. Please turn it on.")

def create_anki_deck(deck):
    anki_connect("createDeck", { "deck": deck } )

def build_branches():
    print("Building branch cards...")
    deck = deck_name + "::1. Branches"
    create_anki_deck(deck)

    branches = json.loads(BRANCHES.read_text())
    cards = [("learn:" + position, move) for position, move in branches.items()]
    cards.sort(key=lambda card: (len(card[0]), card[0]))

    notes = [{
        "deckName": deck,
        "modelName": branch_model_name,
        "fields": {
            "Setup": setup,
            "Move": move,
        },
        "options": {
            "allowDuplicate": False
        },
    } for setup, move in cards]
    anki_connect("addNotes", { "notes": notes } )
    print(f"Added {len(notes)} branch cards to Anki.")

def build_steady_states():
    print("Building steady state cards...")
    deck = deck_name + "::3. Leaves"
    create_anki_deck(deck)

    steady_states = json.loads(STEADY_STATES.read_text())
    notes = [{
        "deckName": deck,
        "modelName": steady_model_name,
        "fields": {
            "Diagram": ",".join(diagram),
        },
        "options": {
            "allowDuplicate": False
        },
    } for diagram in steady_states]
    anki_connect("addNotes", { "notes": notes } )
    print(f"Added {len(notes)} steady state cards to Anki.")

def _mirror_key(key):
    return tuple(row[::-1] for row in key)

def _canon(key):
    """A board, canonicalized up to mirroring, matching how
    branches.json/steady_states.json dedupe boards."""
    mkey = _mirror_key(key)
    return key if key <= mkey else mkey

def _legal_columns(board):
    return [c for c in range(solution.COLS) if solution.col_height(board, c) < solution.ROWS]

def _build_lookup(branches, steady_states):
    red = {solution.board_key(position): move for position, move in branches.items()}
    leaves = {solution.board_key_from_diagram(diagram) for diagram in steady_states}

    def red_lookup(key):
        if key in red:
            return red[key]
        mirror_move = red.get(_mirror_key(key))
        return None if mirror_move is None else str(8 - int(mirror_move))

    def is_leaf(key):
        return key in leaves or _mirror_key(key) in leaves

    return red_lookup, is_leaf

def _walk_forced(position, red_lookup, is_leaf):
    """Advance through Red's committed moves (and Yellow's already-decided
    reply, if any, from where this is called) until either the line ends or
    Yellow faces a real decision.

    Returns ('end', sequence) once Red wins or a steady state is reached, or
    ('yellow', (position, key)) at the next point Yellow has to choose a
    column.

    A line that reaches a steady state always ends on Yellow's move - Yellow
    is the one who walks into the leaf. That move is auto-played by the
    computer during practice, never clicked by the user, so keeping it
    distinguishes nothing: two lines that agree on every Red decision and
    differ only in which leaf Yellow's last move happened to land on (e.g.
    "4151" vs "4152") would otherwise produce two cards quizzing the exact
    same clicks. Trimming it collapses such pairs into one.
    """
    while True:
        key = solution.board_key(position)
        if len(position) % 2 == 0:
            if is_leaf(key):
                return 'end', position[:-1]
            move = red_lookup(key)
            if move is not None:
                position += move
                continue
            board = solution.board_from_position(position)
            win_col = next(c for c in range(solution.COLS) if solution._red_wins_now(board, c))
            return 'end', position + str(win_col + 1)
        return 'yellow', (position, key)

def _build_practice_sequences(red_lookup, is_leaf, rng):
    """Every practice line needed for full "high coverage" of Yellow's
    decisions: each reachable board (up to mirroring) is expanded into its
    legal Yellow replies exactly once. A reply that leads to a board already
    expanded elsewhere - a transposition - doesn't need expanding again, since
    its own replies are already covered by that earlier expansion; the line
    through it simply ends there (right after Red's own last move, itself a
    natural stopping point)."""
    fully_expanded = set()
    sequences = []

    def cover(position, key):
        fully_expanded.add(_canon(key))
        board = solution.board_from_position(position)
        cols = _legal_columns(board)
        rng.shuffle(cols)
        for col in cols:
            kind, val = _walk_forced(position + str(col + 1), red_lookup, is_leaf)
            if kind == 'end':
                sequences.append(val)
            else:
                ypos, ykey = val
                if _canon(ykey) in fully_expanded:
                    sequences.append(ypos)
                else:
                    cover(ypos, ykey)

    kind, val = _walk_forced("", red_lookup, is_leaf)
    if kind == 'end':
        sequences.append(val)
    else:
        ypos, ykey = val
        cover(ypos, ykey)
    return sequences

def build_practice():
    print("Building practice cards...")
    deck = deck_name + "::2. Opening Practice"
    create_anki_deck(deck)

    branches = json.loads(BRANCHES.read_text())
    steady_states = json.loads(STEADY_STATES.read_text())
    red_lookup, is_leaf = _build_lookup(branches, steady_states)

    sequences = sorted(set(_build_practice_sequences(red_lookup, is_leaf, random.Random(42))))

    notes = [{
        "deckName": deck,
        "modelName": branch_model_name,
        "fields": {
            "Setup": "practice:" + seq,
            "Move": "",
        },
        "options": {
            "allowDuplicate": False
        },
    } for seq in sequences]
    anki_connect("addNotes", { "notes": notes } )
    print(f"Added {len(notes)} practice cards to Anki.")

def build_instructions():
    print("Building instructions...")
    create_anki_deck(deck_name + "::0. Instructions")
    html = Path("InstructionCard.html").read_text()
    notes = [{
        "deckName": deck_name + "::0. Instructions",
        "modelName": "Basic",
        "fields": {
            "Front": "Turn the card to see how to use this deck!",
            "Back": html,
        },
        "options": {
            "allowDuplicate": False
        },
    }]
    anki_connect("addNotes", { "notes": notes } )
    print("Added instructions card to Anki.")

build_instructions()
build_branches()
build_practice()
build_steady_states()
