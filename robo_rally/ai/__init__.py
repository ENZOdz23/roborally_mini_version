"""AI layer: how robots choose their cards."""
from .strategy import HumanStrategy, RandomStrategy, Strategy
from .perceptron import Perceptron
from .perceptron_strategy import PerceptronStrategy

# Names used on the command line and in the window's menus.
STRATEGY_NAMES = {"human": HumanStrategy, "random": RandomStrategy, "ai": PerceptronStrategy}


def make_strategy(name: str) -> Strategy:
    """Factory: 'human', 'random' or 'ai' -> a new strategy object."""
    try:
        return STRATEGY_NAMES[name.lower()]()
    except KeyError:
        raise ValueError(f"unknown player type {name!r}, choose from {sorted(STRATEGY_NAMES)}") from None
