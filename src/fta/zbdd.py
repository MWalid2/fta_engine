from dataclasses import dataclass

from .model import BasicEvent

@dataclass(frozen=True)
class ZBDDNode:
    variable: str
    low: int
    high: int


class ZBDD:
    ZERO = 0
    ONE = 1

    def __init__(self, variable_order):
        order = tuple(variable_order)
        self.rank = {variable: index for index, variable in enumerate(order)}
        if len(self.rank) != len(order):
            raise ValueError("The variable order contains duplicate IDs")

        self.nodes: dict[int, ZBDDNode] = {}
        self._unique: dict[ZBDDNode, int] = {}
        self._union_cache: dict[tuple[int, int], int] = {}
        self._join_cache: dict[tuple[int, int], int] = {}
        self._exclude_cache: dict[tuple[int, int], int] = {}
        self._minimal_cache: dict[int, int] = {
            self.ZERO: self.ZERO,
            self.ONE: self.ONE,
        }

    def _rank(self, root: int):
        if root in (self.ZERO, self.ONE):
            return len(self.rank)
        return self.rank[self.nodes[root].variable]

    def make_node(self, variable: str, low: int, high: int):
        rank = self.rank[variable]
        if self._rank(low) <= rank or self._rank(high) <= rank:
            raise ValueError("A child must test a later variable")

        if high == self.ZERO:
            return low

        node = ZBDDNode(variable, low, high)
        if node not in self._unique:
            node_id = len(self.nodes) + 2
            self.nodes[node_id] = node
            self._unique[node] = node_id

        return self._unique[node]

    def _first_variable(self, left: int, right: int):
        if self._rank(left) <= self._rank(right):
            return self.nodes[left].variable
        return self.nodes[right].variable

    def _split(self, root: int, variable: str):
        node = self.nodes.get(root)
        if node is not None and node.variable == variable:
            return node.low, node.high

        # The selected variable is absent from every set in this family.
        return root, self.ZERO

    def union(self, left: int, right: int):
        if left == self.ZERO or left == right:
            return right
        if right == self.ZERO:
            return left

        key = (min(left, right), max(left, right))
        if key in self._union_cache:
            return self._union_cache[key]

        variable = self._first_variable(left, right)
        left_low, left_high = self._split(left, variable)
        right_low, right_high = self._split(right, variable)

        low = self.union(left_low, right_low)
        high = self.union(left_high, right_high)
        result = self.make_node(variable, low, high)
        self._union_cache[key] = result
        return result

    def join(self, left: int, right: int):
        if left == self.ZERO or right == self.ZERO:
            return self.ZERO
        if left == self.ONE:
            return right
        if right == self.ONE:
            return left

        key = (min(left, right), max(left, right))
        if key in self._join_cache:
            return self._join_cache[key]

        variable = self._first_variable(left, right)
        left_low, left_high = self._split(left, variable)
        right_low, right_high = self._split(right, variable)

        # The merged set omits the variable only if both sets omit it.
        low = self.join(left_low, right_low)

        # The merged set includes the variable if either set includes it.
        high = self.union(
            self.join(left_high, right_low),
            self.join(left_low, right_high),
        )
        high = self.union(high, self.join(left_high, right_high))

        result = self.make_node(variable, low, high)
        self._join_cache[key] = result
        return result

    def _exclude_supersets(self, candidates: int, subsets: int):
        if candidates == self.ZERO or subsets == self.ONE:
            return self.ZERO
        if subsets == self.ZERO:
            return candidates

        key = (candidates, subsets)
        if key in self._exclude_cache:
            return self._exclude_cache[key]

        variable = self._first_variable(candidates, subsets)
        cand_low, cand_high = self._split(candidates, variable)
        sub_low, sub_high = self._split(subsets, variable)

        # A candidate omitting the variable can only contain a subset
        # that also omits it.
        low = self._exclude_supersets(cand_low, sub_low)

        # A candidate including the variable can contain either kind.
        high = self._exclude_supersets(
            cand_high, self.union(sub_low, sub_high)
        )

        result = self.make_node(variable, low, high)
        self._exclude_cache[key] = result
        return result

    def minimize(self, root: int):
        if root in self._minimal_cache:
            return self._minimal_cache[root]

        node = self.nodes[root]
        low = self.minimize(node.low)
        high = self.minimize(node.high)

        # A full high-branch set includes the node variable. If its
        # remainder contains a low-branch set, the full set is redundant.
        high = self._exclude_supersets(high, low)

        result = self.make_node(node.variable, low, high)
        self._minimal_cache[root] = result
        return result

    def iter_sets(self, root: int):
        if root == self.ZERO:
            return
        if root == self.ONE:
            yield frozenset()
            return

        node = self.nodes[root]
        yield from self.iter_sets(node.low)
        for tail in self.iter_sets(node.high):
            yield tail | {node.variable}


def build_zbdd(tree, variable_order):
    order = tree.basic_ids if variable_order is None else variable_order
    zbdd = ZBDD(order)
    if set(zbdd.rank) != set(tree.basic_ids):
        raise ValueError("Variable order must contain exactly the reachable basic events")

    roots: dict[str, int] = {}
    for node_id in tree.order:
        node = tree.nodes[node_id]
        if isinstance(node, BasicEvent):
            roots[node_id] = zbdd.make_node(node_id, zbdd.ZERO, zbdd.ONE)
            continue

        combine = zbdd.join if node.operator == "AND" else zbdd.union
        children = iter(node.inputs)
        result = roots[next(children)]

        for child_id in children:
            result = zbdd.minimize(combine(result, roots[child_id]))

        roots[node_id] = result

    return zbdd, roots[tree.root]