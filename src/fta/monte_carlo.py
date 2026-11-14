from dataclasses import dataclass
from math import sqrt
from random import Random

from .evaluate import evaluate

@dataclass(frozen=True)
class MonteCarloResult:
    trials: int
    failures: int
    estimate: float
    ci_low: float
    ci_high: float


def simulate(tree, trials, seed):
    if type(trials) is not int or trials <= 0:
        raise ValueError("trials must be a positive integer")
    rng = Random(seed)
    events = [
        (event_id, tree.nodes[event_id].probability)
        for event_id in tree.basic_ids
    ]
    failures = 0
    for _ in range(trials):
        state = {
            event_id: rng.random() < probability
            for event_id, probability in events
        }
        if evaluate(tree, state):
            failures += 1
    estimate = failures / trials
    # Wilson interval using the two-sided 95% normal critical value.
    z = 1.959963984540054
    z_squared = z * z
    denominator = 1 + z_squared / trials
    center = (estimate + z_squared / (2 * trials)) / denominator
    half_width = (
        z
        * sqrt(
            estimate * (1 - estimate) / trials
            + z_squared / (4 * trials * trials)
        )
        / denominator
    )
    return MonteCarloResult(
        trials=trials,
        failures=failures,
        estimate=estimate,
        ci_low=max(0.0, center - half_width),
        ci_high=min(1.0, center + half_width),
    )