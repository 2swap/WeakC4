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

def build_dataset(js_path):
    print(f"Reading: {js_path}")
    text = Path(js_path).read_text()
    json_str = strip_js_prefix(text)
    data = json.loads(json_str)
    node_map = data["nodes_to_use"]

    cards_added = 0

    for h, node_json in node_map.items():
        # Only for red-to-move nodes
        if len(node_json["rep"]) % 2 == 0 and node_json["neighbors"] is not None:
            # There should be only one neighbor (the best move)
            assert(len(node_json["neighbors"]) == 1)
            setup = node_json["rep"]

            neighbor_hash = node_json["neighbors"][0]
            move = node_map[neighbor_hash]["rep"]
            move = move[len(setup):]
            assert(len(move) == 1)
            anki_add_note(setup, move)
            cards_added += 1

    print(f"Added {cards_added} cards to Anki.")

create_anki_deck()
build_dataset("../c4_full.js")
