from dataclasses import dataclass

from .model import BasicEvent

@dataclass(frozen=True)
class BDDNode:
    variable: str
    low: int
    high: int

class BDD:
    FALSE = 0
    TRUE = 1

    def __init__(self, variable_order):
        order = tuple(variable_order)
        self.rank = {variable: i for i, variable in enumerate(order)}
        if len(self.rank) != len(order):
            raise ValueError("The variable order contains duplicate IDs")
        self.nodes: dict[int, BDDNode] = {}
        self._unique: dict[BDDNode, int] = {}
        self._apply_cache: dict[tuple[str, int, int], int] = {}

    def make_node(self, variable: str, low: int, high: int):
        rank = self.rank[variable]

        for child in (low, high):
            if child not in (self.FALSE, self.TRUE):
                if self.rank[self.nodes[child].variable] <= rank:
                    raise ValueError("A child must test a later variable")

        if low == high:
            return low

        node = BDDNode(variable, low, high)
        if node not in self._unique:
            node_id = len(self.nodes) + 2
            self.nodes[node_id] = node
            self._unique[node] = node_id

        return self._unique[node]

    def apply(self, operator: str, left: int, right: int):
        if operator not in ("AND", "OR"):
            raise ValueError(f"Unsupported BDD operator: {operator!r}")
        if left > right:
            left, right = right, left
        if left == right:
            return left
        if left == self.FALSE:
            return self.FALSE if operator == "AND" else right
        if left == self.TRUE:
            return right if operator == "AND" else self.TRUE
        
        key = (operator, left, right)
        if key in self._apply_cache:
            return self._apply_cache[key]

        left_node = self.nodes[left]
        right_node = self.nodes[right]
        left_rank = self.rank[left_node.variable]
        right_rank = self.rank[right_node.variable]

        if left_rank == right_rank:
            variable = left_node.variable
            left_low, left_high = left_node.low, left_node.high
            right_low, right_high = right_node.low, right_node.high
        elif left_rank < right_rank:
            variable = left_node.variable
            left_low, left_high = left_node.low, left_node.high
            right_low = right_high = right
        else:
            variable = right_node.variable
            left_low = left_high = left
            right_low, right_high = right_node.low, right_node.high

        low = self.apply(operator, left_low, right_low)
        high = self.apply(operator, left_high, right_high)
        result = self.make_node(variable, low, high)

        self._apply_cache[key] = result
        return result

    def probability(self, root: int, probabilities: dict[str, float]):
        memo = {self.FALSE: 0.0, self.TRUE: 1.0}

        def visit(node_id: int):
            if node_id in memo:
                return memo[node_id]
            node = self.nodes[node_id]
            p = probabilities[node.variable]
            result = (1 - p) * visit(node.low) + p * visit(node.high)
            memo[node_id] = result
            return result
        return visit(root)

def build_bdd(tree, variable_order):
    order = tree.basic_ids if variable_order is None else tuple(variable_order)
    bdd = BDD(order)
    if set(bdd.rank) != set(tree.basic_ids):
        raise ValueError("Variable order must contain every reachable basic event")
    roots: dict[str, int] = {}
    for node_id in tree.order:
        node = tree.nodes[node_id]
        if isinstance(node, BasicEvent):
            roots[node_id] = bdd.make_node(node_id, bdd.FALSE, bdd.TRUE)
            continue
        first, *remaining = node.inputs
        result = roots[first]
        for child_id in remaining:
            result = bdd.apply(node.operator, result, roots[child_id])
        roots[node_id] = result
    return bdd, roots[tree.root]
    