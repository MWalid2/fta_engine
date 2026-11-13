from fta.io import load_tree
from fta.mocus import minimal_cut_sets

tree = load_tree("examples/exp2.json")

expected = {
    frozenset({"A"}),
    frozenset({"B", "C"}),
    frozenset({"D", "E"}),
    frozenset({"D", "F"}),
}

actual = minimal_cut_sets(tree)

assert actual == expected, f"Missing: {expected - actual}; extra: {actual - expected}"
print("MOCUS test passed.")