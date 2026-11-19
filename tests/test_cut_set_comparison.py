import tracemalloc
from pathlib import Path
from time import perf_counter

import pytest

from fta.io import load_tree
from fta.mocus import minimal_cut_sets
from fta.zbdd import build_zbdd


EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
EXAMPLES = sorted(EXAMPLES_DIR.glob("*.json"))


def zbdd_cut_sets(tree):
    diagram, root = build_zbdd(tree, variable_order=None)
    return set(diagram.iter_sets(root))


def run_and_report(name, solve, tree):
    times = []
    for _ in range(5):
        start = perf_counter()
        solve(tree)
        times.append(perf_counter() - start)
    fastest_ms = min(times) * 1_000
    cut_sets = solve(tree)

    print(
        f"  {name}: {len(cut_sets)} cut sets, {fastest_ms:.3f} ms, "
    )
    return cut_sets


@pytest.mark.parametrize("example", EXAMPLES, ids=[path.stem for path in EXAMPLES])
def test_mocus_and_zbdd_agree(example):
    tree = load_tree(example)

    print(f"\n{example.name}")
    mocus = run_and_report("MOCUS", minimal_cut_sets, tree)
    zbdd = run_and_report("ZBDD", zbdd_cut_sets, tree)
    print(f"  Same cut sets: {mocus == zbdd}")

    assert mocus == zbdd, f"MOCUS only: {mocus - zbdd}\nZBDD only: {zbdd - mocus}"
