from itertools import product

from fta.evaluate import evaluate
from fta.io import load_tree

tree = load_tree("examples/exp1.json")

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

print("All eight assignments passed.")