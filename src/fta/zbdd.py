from dataclasses import dataclass

from .model import BasicEvent
from .utils.iterative import iterate

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

    @staticmethod
    def _pair(left: int, right: int):
        # union and join are commutative, so store each pair canonically.
        return (min(left, right), max(left, right))
    
    # union

    def _union_trivial(self, left: int, right: int):
        if left == self.ZERO or left == right:
            return right
        if right == self.ZERO:
            return left
        return None

    def _union_dependencies(self, key):
        left, right = key
        if self._union_trivial(left, right) is not None:
            return []
        variable = self._first_variable(left, right)
        left_low, left_high = self._split(left, variable)
        right_low, right_high = self._split(right, variable)
        return [self._pair(left_low, right_low),
                self._pair(left_high, right_high)]

    def _union_combine(self, key):
        left, right = key
        trivial = self._union_trivial(left, right)
        if trivial is not None:
            return trivial
        variable = self._first_variable(left, right)
        left_low, left_high = self._split(left, variable)
        right_low, right_high = self._split(right, variable)
        low = self._union_cache[self._pair(left_low, right_low)]
        high = self._union_cache[self._pair(left_high, right_high)]
        return self.make_node(variable, low, high)

    def union(self, left: int, right: int):
        return iterate(self._union_cache, self._pair(left, right),
                       self._union_dependencies, self._union_combine)

    # join

    def _join_trivial(self, left: int, right: int):
        if left == self.ZERO or right == self.ZERO:
            return self.ZERO
        if left == self.ONE:
            return right
        if right == self.ONE:
            return left
        return None

    def _join_parts(self, left: int, right: int):
        variable = self._first_variable(left, right)
        left_low, left_high = self._split(left, variable)
        right_low, right_high = self._split(right, variable)
        return variable, left_low, left_high, right_low, right_high

    def _join_dependencies(self, key):
        left, right = key
        if self._join_trivial(left, right) is not None:
            return []
        _, ll, lh, rl, rh = self._join_parts(left, right)
        return [self._pair(ll, rl), self._pair(lh, rl),
                self._pair(ll, rh), self._pair(lh, rh)]

    def _join_combine(self, key):
        left, right = key
        trivial = self._join_trivial(left, right)
        if trivial is not None:
            return trivial
        variable, ll, lh, rl, rh = self._join_parts(left, right)
        cache = self._join_cache

        # The merged set omits the variable only if both sets omit it.
        low = cache[self._pair(ll, rl)]

        # The merged set includes the variable if either set includes it.
        # The union of the mixed products is a separate iterative call.
        high = self.union(
            self.union(cache[self._pair(lh, rl)], cache[self._pair(ll, rh)]),
            cache[self._pair(lh, rh)],
        )
        return self.make_node(variable, low, high)

    def join(self, left: int, right: int):
        return iterate(self._join_cache, self._pair(left, right),
                       self._join_dependencies, self._join_combine)
    
    # exclude supersets

    def _exclude_trivial(self, candidates: int, subsets: int):
        if candidates == self.ZERO or subsets == self.ONE:
            return self.ZERO
        if subsets == self.ZERO:
            return candidates
        return None

    def _exclude_parts(self, candidates: int, subsets: int):
        variable = self._first_variable(candidates, subsets)
        cand_low, cand_high = self._split(candidates, variable)
        sub_low, sub_high = self._split(subsets, variable)
        # The high branch may contain a subset from either side.
        merged = self.union(sub_low, sub_high)
        return variable, cand_low, cand_high, sub_low, merged

    def _exclude_dependencies(self, key):
        candidates, subsets = key
        if self._exclude_trivial(candidates, subsets) is not None:
            return []
        _, cand_low, cand_high, sub_low, merged = self._exclude_parts(
            candidates, subsets)
        return [(cand_low, sub_low), (cand_high, merged)]

    def _exclude_combine(self, key):
        candidates, subsets = key
        trivial = self._exclude_trivial(candidates, subsets)
        if trivial is not None:
            return trivial
        variable, cand_low, cand_high, sub_low, merged = self._exclude_parts(
            candidates, subsets)
        # A candidate omitting the variable can only contain a subset
        # that also omits it.
        low = self._exclude_cache[(cand_low, sub_low)]
        # A candidate including the variable can contain either kind.
        high = self._exclude_cache[(cand_high, merged)]
        return self.make_node(variable, low, high)

    def _exclude_supersets(self, candidates: int, subsets: int):
        return iterate(self._exclude_cache, (candidates, subsets),
                       self._exclude_dependencies, self._exclude_combine)
    # minimal sets

    def _minimize_dependencies(self, root):
        node = self.nodes[root]
        return [node.low, node.high]

    def _minimize_combine(self, root):
        node = self.nodes[root]
        low = self._minimal_cache[node.low]
        high = self._minimal_cache[node.high]
        # A full high-branch set includes the node variable. If its
        # remainder contains a low-branch set, the full set is redundant.
        high = self._exclude_supersets(high, low)
        return self.make_node(node.variable, low, high)

    def minimize(self, root: int):
        return iterate(self._minimal_cache, root,
                       self._minimize_dependencies, self._minimize_combine)

    # enumeration

    def iter_sets(self, root: int):
        stack = [(root, frozenset())]
        while stack:
            node_id, tail = stack.pop()
            if node_id == self.ZERO:
                continue
            if node_id == self.ONE:
                yield tail
                continue
            node = self.nodes[node_id]
            # Push high first so the low branch is popped (and yielded) first.
            stack.append((node.high, tail | {node.variable}))
            stack.append((node.low, tail))

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