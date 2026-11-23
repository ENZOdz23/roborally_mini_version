"""AI layer: how robots choose their cards."""
from .strategy import HumanStrategy, RandomStrategy, Strategy
from .perceptron import Perceptron
from .perceptron_strategy import PerceptronStrategy
from .oracle import OracleStrategy

# Names used on the command line and in the window's menus.
STRATEGY_NAMES = {"human": HumanStrategy, "random": RandomStrategy, "ai": PerceptronStrategy,
                  "oracle": OracleStrategy}


def make_strategy(name: str, rng=None) -> Strategy:
    """Factory: 'human', 'random', 'ai' or 'oracle' -> a new strategy object.
    rng (a random.Random) makes the player repeatable; a person needs none."""
    try:
        kind = STRATEGY_NAMES[name.lower()]
    except KeyError:
        raise ValueError(f"unknown player type {name!r}, choose from {sorted(STRATEGY_NAMES)}") from None
    return kind() if rng is None or kind is HumanStrategy else kind(rng=rng)
