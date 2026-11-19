from dataclasses import dataclass

from .model import BasicEvent
from .utils.iterative import iterate

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

    # apply
    
    @staticmethod
    def _apply_key(operator: str, left: int, right: int):
        # AND and OR are commutative, so store each pair in one canonical order.
        return (operator, min(left, right), max(left, right))

    def _apply_terminal(self, operator: str, left: int, right: int):
        """Return the result when it is trivial (left <= right), otherwise None."""
        if left == right:
            return left
        if left == self.FALSE:
            return self.FALSE if operator == "AND" else right
        if left == self.TRUE:
            return right if operator == "AND" else self.TRUE
        return None

    def _cofactors(self, left: int, right: int):
        """Split both operands on their earliest variable."""
        left_node, right_node = self.nodes[left], self.nodes[right]
        left_rank = self.rank[left_node.variable]
        right_rank = self.rank[right_node.variable]
        if left_rank == right_rank:
            return (left_node.variable,
                    (left_node.low, left_node.high),
                    (right_node.low, right_node.high))
        if left_rank < right_rank:
            return left_node.variable, (left_node.low, left_node.high), (right, right)
        return right_node.variable, (left, left), (right_node.low, right_node.high)

    def _apply_dependencies(self, key):
        operator, left, right = key
        if self._apply_terminal(operator, left, right) is not None:
            return []
        _, (ll, lh), (rl, rh) = self._cofactors(left, right)
        return [self._apply_key(operator, ll, rl), self._apply_key(operator, lh, rh)]

    def _apply_combine(self, key):
        operator, left, right = key
        trivial = self._apply_terminal(operator, left, right)
        if trivial is not None:
            return trivial
        variable, (ll, lh), (rl, rh) = self._cofactors(left, right)
        low = self._apply_cache[self._apply_key(operator, ll, rl)]
        high = self._apply_cache[self._apply_key(operator, lh, rh)]
        return self.make_node(variable, low, high)

    def apply(self, operator: str, left: int, right: int):
        if operator not in ("AND", "OR"):
            raise ValueError(f"Unsupported BDD operator: {operator!r}")
        return iterate(self._apply_cache,
                        self._apply_key(operator, left, right),
                        self._apply_dependencies,
                        self._apply_combine)

    # proability

    def probability(self, root: int, probabilities: dict[str, float]):
        memo = {self.FALSE: 0.0, self.TRUE: 1.0}

        def dependencies(node_id):
            node = self.nodes[node_id]
            return [node.low, node.high]

        def combine(node_id):
            node = self.nodes[node_id]
            p = probabilities[node.variable]
            return (1 - p) * memo[node.low] + p * memo[node.high]

        return iterate(memo, root, dependencies, combine)

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
    