#!/usr/bin/env python3
import json
import requests
import re
from pathlib import Path

prefix_list = {
    "02. 6-1": ["444444"],
    "436766": ["436766"],
    "4367": ["4367"],
    "47": ["47"],
    "426566": ["426566"],
    "426564": ["426564"],
    "05. 4444452": ["4444452", "4445244", "4524444"],
    "03. True Candlesticks": ["44444222266", "44444226622"],
    "04. Half Candlesticks": ["444442222"],
    "Crown Variations": ["44444"],
    "D3-D4 Openings": ["4442", "4441"],
    "Hand Variations": ["4366755535", "4365567535"],
    "Thumb Variations": ["436556766"],
    "Wrist Variations": ["44436675", "452332144", "43644675"],
    "Palm Variations": ["4365567"],
    "444367": ["444367", "436447"],
    "44436(1/2/3)": ["444361", "444362", "444363", "436441", "436442", "436443"],
    "4621": ["4621"],
    "Other 462 Variations": ["462"],
    "436(1/2)": ["4361", "4362"],
    "4363": ["4363"],
    "Hills Openings": ["4443655", "4364455", "4365544", "436553", "436555", "452337"],
    "01. Very Beginning": [""],
}
deck_name = "2swap's Connect 4"

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

def create_anki_deck(deck):
    resp_json = anki_connect("createDeck", { "deck": deck } )

def anki_add_note(deck, setup, move):
    notes = [{
        "deckName": deck,
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

def invert_around_4(setup):
    inverted = ""
    for c in setup:
        inverted += str(8 - int(c))
    return inverted

def determine_prefix(setup):
    for prefix, opening in prefix_list.items():
        for o in opening:
            if setup.startswith(o) or setup.startswith(invert_around_4(o)):
                return prefix
    return None

def build_dataset(js_path):
    print(f"Reading: {js_path}")
    text = Path(js_path).read_text()
    json_str = strip_js_prefix(text)
    data = json.loads(json_str)
    node_map = data["nodes_to_use"]

    # List of cards to add. We will first populate it,
    # then sort the cards lexicographically, then add to Anki.
    cards = []

    # Count of matched setups per prefix, or "None" for unmatched setups
    prefix_counts = { prefix: 0 for prefix in prefix_list.keys() }
    prefix_counts[None] = 0

    # Populate cards
    for h, node_json in node_map.items():
        # Only for red-to-move nodes
        if len(node_json["rep"]) % 2 == 0 and node_json["neighbors"] is not None:
            # There should be only one neighbor (the best move)
            assert(len(node_json["neighbors"]) == 1)
            setup = node_json["rep"]

            prefix = determine_prefix(setup)
            neighbor_hash = node_json["neighbors"][0]
            neighbor_rep = node_map[neighbor_hash]["rep"]
            move = find_move(setup, neighbor_rep)
            deck = deck_name + ("" if prefix is None else f"::{prefix}")
            cards.append( (deck, setup, move) )
            prefix_counts[prefix] += 1
            if(prefix is None):
                print(f"No prefix found for setup {setup}")

    for prefix, count in prefix_counts.items():
        print(f"Prefix: {prefix}, Count: {count}")

    # Sort cards lexicographically by setup
    cards.sort( key=lambda x: x[0] )

    # Add cards to Anki
    for deck, setup, move in cards:
        anki_add_note(deck, "nextmove:" + setup, move)

    print(f"Added {len(cards)} cards to Anki.")

for prefix in prefix_list.keys():
    create_anki_deck(deck_name + "::" + prefix)
build_dataset("../c4_full.js")
