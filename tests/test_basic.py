from itertools import product
import pytest

from fta.evaluate import evaluate
from fta.io import load_tree
from fta.mocus import minimal_cut_sets

tree = load_tree("examples/exp_basic.json")

print("Root:", tree.root)
print("Evaluation order:", tree.order)
print("Basic events:", tree.basic_ids)

assert tree.root == "TOP"
assert len(tree.nodes) == 6
assert sorted(tree.basic_ids) == ["A", "B", "C"]

for a, b, c in product((False, True), repeat=3):
    state = {"A": a, "B": b, "C": c}
    actual = evaluate(tree, state)
    expected = a and (b or c)
    print(state, "->", actual)
    assert actual == expected, f"Incorrect result for {state}"

assert minimal_cut_sets(tree) == {
    frozenset({"A", "B"}),
    frozenset({"A", "C"}),
}

print("All eight assignments passed.")