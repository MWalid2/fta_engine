import json
from pathlib import Path

from .model import BasicEvent, FaultTree, Gate

def load_tree(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("nodes"), list):
        raise ValueError("Expected an object containing a nodes list")
    if "root" not in data:
        raise ValueError("Expected a 'root' field in the fault tree")

    definitions = []
    for record in data["nodes"]:
        if not isinstance(record, dict):
            raise ValueError("Each node definition must be an object")
        kind = record.get("kind")
        if kind == "basic":
            definitions.append(BasicEvent(record.get("id"), record.get("probability")))
        elif kind == "gate" and isinstance(record.get("inputs"), list):
            definitions.append(Gate(
                record.get("id"), record.get("operator"), tuple(record["inputs"])
            ))
        else:
            raise ValueError(f"Invalid node definition: {record!r}")
    return FaultTree(data.get("root"), definitions)