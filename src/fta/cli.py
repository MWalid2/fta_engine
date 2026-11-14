import argparse
from pathlib import Path

from .bdd import build_bdd
from .io import load_tree
from .monte_carlo import simulate
from .mocus import minimal_cut_sets
from .zbdd import build_zbdd

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Static fault tree analysis")
    commands = parser.add_subparsers(dest="command", required=True)

    validate = commands.add_parser("validate", help="Validate a JSON model")
    validate.add_argument("model", type=Path)

    cuts = commands.add_parser("cutsets", help="Find minimal cut sets")
    cuts.add_argument("model", type=Path)
    cuts.add_argument("--method", choices=("mocus", "zbdd"), default="mocus")
    cuts.add_argument("--order", nargs="+", metavar="EVENT", help="ZBDD variable order")

    probability = commands.add_parser("probability", help="Compute exact BDD probability")
    probability.add_argument("model", type=Path)
    probability.add_argument("--order", nargs="+", metavar="EVENT", help="BDD variable order")

    simulation = commands.add_parser("simulate", help="Estimate probability by sampling")
    simulation.add_argument("model", type=Path)
    simulation.add_argument("--trials", type=int, default=100_000)
    simulation.add_argument("--seed", type=int)

    args = parser.parse_args(argv)

    tree = load_tree(args.model)

    if args.command == "validate":
        print(f"Valid model. Root: {tree.root}")
        print(f"Reachable basic events: {len(tree.basic_ids)}")

    elif args.command == "cutsets":
        if args.method == "mocus":
            if args.order is not None:
                parser.error("--order requires --method zbdd for cutsets")
            cut_sets = minimal_cut_sets(tree)
        else:
            zbdd, root = build_zbdd(tree, args.order)
            cut_sets = zbdd.iter_sets(root)
        rows = sorted(
            (tuple(sorted(cut_set)) for cut_set in cut_sets),
            key=lambda row: (len(row), row),
        )
        for row in rows:
            print("{" + ", ".join(row) + "}")
        print(f"Minimal cut sets: {len(rows)}")

    elif args.command == "probability":
        bdd, root = build_bdd(tree, args.order)
        probabilities = {
            event_id: tree.nodes[event_id].probability
            for event_id in tree.basic_ids
        }
        print(f"P({tree.root}) = {bdd.probability(root, probabilities):.10g}")
    else:
        result = simulate(tree, args.trials, args.seed)
        print(f"Failures: {result.failures}/{result.trials}")
        print(f"P({tree.root}) estimate: {result.estimate:.10g}")
        print(f"95% Wilson interval: [{result.ci_low:.10g}, {result.ci_high:.10g}]")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())