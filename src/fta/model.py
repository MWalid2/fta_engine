from dataclasses import dataclass
from graphlib import TopologicalSorter
from types import MappingProxyType

@dataclass(frozen=True)
class BasicEvent:
    id: str
    probability: float

@dataclass(frozen=True)
class Gate:
    id: str
    operator: str
    inputs: tuple[str, ...] # a tuple of any length, all strings
class FaultTree:
    def __init__(self, root:str, definitions):
        nodes = {}
        for node in definitions:
            if not isinstance(node.id, str) or not node.id.strip():
                raise ValueError("Node IDs must be nonempty strings")
            if node.id in nodes:
                raise ValueError(f"Duplicate node ID: {node.id}")
            if isinstance(node, BasicEvent):
                p = node.probability
                if type(p) not in (int, float) or not 0 <= p <= 1:
                    raise ValueError(f"Invalid probability for {node.id}")
            elif not isinstance(node.operator, str) or node.operator not in ("AND", "OR") or not node.inputs:
                raise ValueError(f"Invalid gate: {node.id}")
            nodes[node.id] = node

        if not isinstance(root, str) or root not in nodes:
            raise ValueError(f"Unknown root: {root!r}")

        dependencies = {}
        for node_id, node in nodes.items():
            inputs = node.inputs if isinstance(node, Gate) else ()   # basic events depend on nothing
            for child in inputs:
                if not isinstance(child, str) or child not in nodes:
                    raise ValueError(f"Unknown input {child!r} on {node_id}")
            dependencies[node_id] = inputs

        order = tuple(TopologicalSorter(dependencies).static_order())
        # DFS to get all the elements used actually by root
        reachable = set()
        pending = [root]
        while pending:
            node_id = pending.pop()
            if node_id not in reachable:
                reachable.add(node_id)
                pending.extend(dependencies[node_id])

        self.root = root
        self.nodes = MappingProxyType(nodes)    # read-only view of the dict
        self.order = tuple(node_id for node_id in order if node_id in reachable)
        self.basic_ids = tuple(node_id for node_id in self.order if isinstance(self.nodes[node_id], BasicEvent))
        