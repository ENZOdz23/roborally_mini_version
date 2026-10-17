"""How a robot chooses its cards (Strategy pattern).

The game only knows this interface. Who is behind it (random, perceptron AI,
a person clicking in the window) is decided when the game is created.
"""
import random
from abc import ABC, abstractmethod
from typing import List, Optional

from ..model import Card, GameState, Robot


class Strategy(ABC):
    name = "strategy"
    interactive = False      # True when a person chooses in the window

    @abstractmethod
    def choose(self, state: GameState, robot: Robot, hand: List[Card], size: int) -> Optional[List[Card]]:
        """Returns `size` cards taken from `hand`, in the order they will be played.

        Returns None if the answer is not ready yet (a person still has to click).
        """


class RandomStrategy(Strategy):
    """Phase 2 of the spec: random cards. Used to test the engine and as the AI's opponent."""
    name = "Random"

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()

    def choose(self, state, robot, hand, size):
        return self.rng.sample(hand, size)


class HumanStrategy(Strategy):
    """A person chooses in the window. The window calls Game.submit_program() when they confirm."""
    name = "Human"
    interactive = True

    def choose(self, state, robot, hand, size):
        return None
