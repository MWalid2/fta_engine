from .model import FaultTree, Gate

def minimal_cut_sets(tree: FaultTree):
    pending = [frozenset({tree.root})]
    completed = set()
    while pending:
        row = pending.pop()
        gate_id = None
        for node_id in row:
            node = tree.nodes[node_id]
            if isinstance(node, Gate):
                gate_id = node_id
                break
        if gate_id is None:
            completed.add(row)
            continue
        gate = tree.nodes[gate_id]
        rest = row - {gate_id}
        if gate.operator == 'AND':
            pending.append(rest.union(gate.inputs))
        else:
            for child_id in gate.inputs:
                pending.append(rest | {child_id})

    minimal = set()
    for candidate in sorted(completed, key=len):
        if any(kept < candidate for kept in minimal):
            continue
        minimal.add(candidate)

    return minimal