#!/usr/bin/env python3
import json
import requests
import re
from pathlib import Path

def anki_connect(action, params={}):
    try:
        if params is None:
            params = []
        request = json.dumps({"action": action, "version": 6, "params": params})
        response = requests.post("http://localhost:8765", data=request)
        resp_json = response.json()
        if 'error' in resp_json and resp_json['error']:
            print("Error: " + str(resp_json['error']))
        return resp_json
    except requests.ConnectionError:
        print("AnkiConnect is not running. Please turn it on.")

def create_anki_deck():
    deck_name = "2swap's Connect 4"
    resp_json = anki_connect("createDeck", { "deck": deck_name } )
    return deck_name

def anki_add_note(setup, move):
    notes = [{
        "deckName": "2swap's Connect 4",
        "modelName": "Connect4",
        "fields": {
            "Setup": setup,
            "Move": move,
        },
        "options": {
            "allowDuplicate": True
        },
        "tags": [],
    }]
    resp_json = anki_connect("addNotes", { "notes": notes } )

def strip_js_prefix(js_text):
    match = re.match(r"\s*var\s+\w+\s*=\s*(\{.*\})\s*;?\s*$", js_text, re.DOTALL)
    if not match:
        raise ValueError("JS input must begin with 'var ... = { ... };'")
    return match.group(1)

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
    print(f"Reading: {js_path}")
    text = Path(js_path).read_text()
    json_str = strip_js_prefix(text)
    data = json.loads(json_str)
    node_map = data["nodes_to_use"]

    # List of cards to add. We will first populate it,
    # then sort the cards lexicographically, then add to Anki.
    cards = []

    # Populate cards
    for h, node_json in node_map.items():
        # Only for red-to-move nodes
        if len(node_json["rep"]) % 2 == 0 and node_json["neighbors"] is not None:
            # There should be only one neighbor (the best move)
            assert(len(node_json["neighbors"]) == 1)
            setup = node_json["rep"]

            neighbor_hash = node_json["neighbors"][0]
            neighbor_rep = node_map[neighbor_hash]["rep"]
            move = find_move(setup, neighbor_rep)
            cards.append( (setup, move) )

    # Sort cards lexicographically by setup
    cards.sort( key=lambda x: x[0] )

    # Add cards to Anki
    for setup, move in cards:
        anki_add_note("nextmove:" + setup, move)

    print(f"Added {len(cards)} cards to Anki.")

create_anki_deck()
build_dataset("../c4_full.js")
