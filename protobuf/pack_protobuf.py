import json
import re
import c4_graph_pb2
from pathlib import Path
import gzip
import shutil
import os

mapping = {32: 0, 49: 1, 50: 2, 124: 3, 33: 4, 45: 5, 64: 6, 43: 7, 61: 8}
def flatten_ss(ss_2d):
    packed = bytearray()
    flat_list = []
    for row in ss_2d:
        for cell in row:
            if cell not in mapping:
                raise ValueError(f"Unexpected ss value: {cell}")
            flat_list.append(mapping[cell])
    # pack two values into one byte (4 bits each)
    for i in range(0, len(flat_list), 2):
        first = flat_list[i]
        second = flat_list[i + 1] if i + 1 < len(flat_list) else 0
        packed.append((first << 4) | second)
    return bytes(packed)

def pack_rep(rep_str):
    digits = [int(ch) for ch in rep_str]
    packed = bytearray()
    for i in range(0, len(digits), 2):
        first = digits[i]
        second = digits[i + 1] if i + 1 < len(digits) else 0
        packed.append((first << 3) | second)
    return bytes(packed)

def strip_js_prefix(js_text):
    match = re.match(r"\s*var\s+\w+\s*=\s*(\{.*\})\s*;?\s*$", js_text, re.DOTALL)
    if not match:
        raise ValueError("JS input must begin with 'var ... = { ... };'")
    return match.group(1)

def build_dataset(js_path, out_path):
    print(f"Reading: {js_path}")
    text = Path(js_path).read_text()
    json_str = strip_js_prefix(text)
    data = json.loads(json_str)

    node_map = data["nodes_to_use"]
    hash_list = list(node_map.keys())

    # Enumerate all hashes
    hash_to_id = {h: i for i, h in enumerate(hash_list)}
    id_to_hash = {i: h for h, i in hash_to_id.items()}  # optional, if you need to debug

    ds = c4_graph_pb2.Dataset()
    ds.root_node_id = hash_to_id[data["root_node_hash"]]

    for h, node_json in node_map.items():
        node_id = hash_to_id[h]
        node = ds.nodes.add()
        node.id = node_id
        node.rep = pack_rep(node_json["rep"])

        if node_json["neighbors"] is not None:
            neighbor_data = c4_graph_pb2.NeighborData()
            neighbor_data.neighbor_ids.extend([hash_to_id[nh] for nh in node_json["neighbors"]])
            node.neighbor_data.CopyFrom(neighbor_data)
        else:
            ss = node_json["data"]["ss"]
            node.flat_ss = flatten_ss(ss)

    with open(out_path, "wb") as f:
        f.write(ds.SerializeToString())

    pb_size = os.path.getsize(out_path)
    print(f"✅ Wrote intermediate .pb file to: {out_path} ({pb_size} bytes)")

    gz_out_path = out_path + ".gz"
    with open(out_path, "rb") as f_in:
        data = f_in.read()
    with gzip.open(gz_out_path, "wb") as f_out:
        f_out.write(data)
    os.remove(out_path)  # Remove the uncompressed file
    # remove pycache directory if it exists
    pycache_path = Path(__file__).parent / "__pycache__"
    if pycache_path.exists():
        shutil.rmtree(pycache_path)

    gz_size = os.path.getsize(gz_out_path)

    print(f"✅ Wrote compressed gzip file to: {gz_out_path} ({gz_size} bytes)")
    print(f"✅ Total nodes encoded: {len(ds.nodes)}")

if __name__ == "__main__":
    # Print out each key as a utf-8 character
    for key, value in mapping.items():
        print(f"Mapping {key} to {value} ({chr(key)})")
    build_dataset("../c4_full.js", "c4_full.pb")
