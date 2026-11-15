from .model import BasicEvent, FaultTree

def evaluate(tree: FaultTree, state: dict[str, bool]):
    values = {}
    for node_id in tree.order:          # children always come before parents
        node = tree.nodes[node_id]
        if isinstance(node, BasicEvent):
            value = state.get(node_id)
            if type(value) is not bool:
                raise ValueError(f"Expected a Boolean assignment for {node_id}")
        elif node.operator == "AND":
            value = all(values[child] for child in node.inputs)
        else:
            value = any(values[child] for child in node.inputs)
        values[node_id] = value
    return values[tree.root]