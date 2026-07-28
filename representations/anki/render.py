#!/usr/bin/env python3
import json
import requests
import re
from pathlib import Path

board_width = 7
board_height = 6

indices = dict([(item, index) for index, item in enumerate(prefixes)])

def make_board_array_from_rep(rep):
    board = [[0]*board_width for _ in range(board_height)]
    for i, c in enumerate(rep):
        col = int(c) - 1
        row = 0
        while row < board_height and board[row][col] != 0:
            row += 1
        board[row][col] = 1 if i % 2 == 0 else 2
    return board

def is_equal(rep1, rep2):
    return make_board_array_from_rep(rep1) == make_board_array_from_rep(rep2)

def who_won(board):
    # Check horizontal, vertical, and diagonal for a winner
    for row in range(board_height):
        for col in range(board_width):
            if board[row][col] == 0:
                continue
            player = board[row][col]
            # Check horizontal
            if col <= board_width - 4 and all(board[row][col+i] == player for i in range(4)):
                return player
            # Check vertical
            if row <= board_height - 4 and all(board[row+i][col] == player for i in range(4)):
                return player
            # Check diagonal down-right
            if row <= board_height - 4 and col <= board_width - 4 and all(board[row+i][col+i] == player for i in range(4)):
                return player
            # Check diagonal down-left
            if row <= board_height - 4 and col >= 3 and all(board[row+i][col-i] == player for i in range(4)):
                return player
    return None

def is_immediate_danger(rep):
    board = make_board_array_from_rep(rep)
    # for each column, check if yellow can win on the next move by playing in that column
    for col in range(board_width):
        # Find the lowest empty row in this column
        row = 0
        while row < board_height and board[row][col] != 0:
            row += 1
        if row == board_height:
            continue
        copy_board = [r[:] for r in board]
        copy_board[row][col] = 2
        if who_won(copy_board) == 2:
            return True

deck_name = "2swap's Connect 4"

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
    resp_json = anki_connect("createDeck", { "deck": deck } )

def anki_add_notes(cards):
    notes = [{
        "deckName": deck,
        "modelName": deck_name, # Note type is the same name as the deck
        "fields": {
            "Setup": setup,
            "Move": move,
        },
        "options": {
            "allowDuplicate": False
        },
    } for deck, setup, move in cards]
    resp_json = anki_connect("addNotes", { "notes": notes } )

def find_move(setup, neighbor_rep):
    # Neighbor rep should have exactly one more move
    assert(len(neighbor_rep) == len(setup) + 1)
    # Find what move was different by finding the amount of pieces in each column
    move = None
    moves_per_column_setup = [0]*7
    moves_per_column_neighbor = [0]*7
    for i, col in enumerate(setup):
        moves_per_column_setup[int(col)-1] += 1
    for i, col in enumerate(neighbor_rep):
        moves_per_column_neighbor[int(col)-1] += 1
    for col in range(7):
        if moves_per_column_neighbor[col] > moves_per_column_setup[col]:
            # Check that the condition is only met for a single column
            assert(move is None)
            move = str(col+1)

    assert(move is not None)
    return move

def build_dataset(js_path):
    print(f"Building learn cards from dataset at {js_path}...")

    # if the file is not found, print an error message and exit
    if not Path(js_path).is_file():
        print(f"Error: no annotated graph found at {js_path}. Get the annotated graph by printing `dataset.nodes_to_use` in the console of the viewer, and copy that into {js_path}.")
        exit(0)
    text = Path(js_path).read_text()
    node_map = json.loads(text)

    # List of cards to add. We will first populate it,
    # then sort the cards lexicographically, then add to Anki.
    cards = []

    prefix_counts = {}

    # Populate cards
    for h, node_json in node_map.items():
        # Only for red-to-move nodes
        if len(node_json["rep"]) % 2 == 0 and node_json["neighbors"] is not None:
            # There should be only one neighbor (the best move)
            assert(len(node_json["neighbors"]) == 1)
            setup = node_json["rep"]
            if(is_immediate_danger(setup)): # No need to memorize forced moves
                print(f"Skipping immediate danger setup: {setup}")
                continue

            prefix = node_json["prefix"]
            index = indices[prefix] + 1
            prefix = ("0" if index < 10 else "") + str(index) + " - " + prefix
            neighbor_hash = node_json["neighbors"][0]
            neighbor_rep = node_map[neighbor_hash]["rep"]
            move = find_move(setup, neighbor_rep)
            deck = deck_name + f"::Learn::{prefix}"
            cards.append( (deck, "learn:" + setup, move) )
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1
            if(prefix is None):
                print(f"No prefix found for setup {setup}")

    for prefix in prefix_counts.keys():
        create_anki_deck(deck_name + "::Learn::" + prefix)

    for prefix, count in prefix_counts.items():
        print(f"Prefix: {prefix}, Count: {count}")

    # Sort cards by length of prefix, then lexicographically by setup.
    cards.sort(key=lambda x: (len(x[1]), x[1]))

    anki_add_notes(cards)

    print(f"Added {len(cards)} cards to Anki.")

def build_instructions():
    print("Building instructions...")
    create_anki_deck(deck_name + "::Instructions")
    html = Path("InstructionCard.html").read_text()
    notes = [{
        "deckName": deck_name + "::Instructions",
        "modelName": "Basic",
        "fields": {
            "Front": "Turn the card to see how to use this deck!",
            "Back": html,
        },
        "options": {
            "allowDuplicate": False
        },
    }]
    resp_json = anki_connect("addNotes", { "notes": notes } )
    print("Added instructions card to Anki.")

build_instructions()
build_dataset("../c4_full_prefixes.js")
