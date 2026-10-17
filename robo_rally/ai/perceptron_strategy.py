"""Phase 3 of the spec: choose cards with the perceptron instead of at random.

For every possible ordered choice of cards from the hand:
    1. simulate the turn on a copy of the game
    2. turn the result into features
    3. score it with the perceptron
and play the choice with the highest score.
"""
import random
from itertools import permutations
from typing import List, Optional

from .features import as_vector, extract
from .pathfinding import DistanceMap
from .perceptron import Perceptron
from .simulator import simulate
from .strategy import Strategy


class PerceptronStrategy(Strategy):
    name = "Perceptron AI"

    def __init__(self, perceptron: Optional[Perceptron] = None, rng: Optional[random.Random] = None):
        self.perceptron = perceptron or Perceptron.load()
        self.rng = rng or random.Random()
        self._distances = None            # computed once per board, on first use
        self.last_choice = []             # (score, card names) of every candidate, for the window/report

    def distances(self, board) -> DistanceMap:
        if self._distances is None or self._distances.board is not board:
            self._distances = DistanceMap(board)
        return self._distances

    def choose(self, state, robot, hand, size):
        distances = self.distances(state.board)
        best, best_score, seen, scored = None, None, set(), []
        for program in permutations(hand, size):
            names = tuple(card.name for card in program)
            if names in seen:              # two "Move 1" cards give the same result
                continue
            seen.add(names)
            result = simulate(state, robot.id, list(program))
            score = self.perceptron.score(as_vector(extract(state, result, distances)))
            score += self.rng.random() * 1e-6          # random tie-break between equal scores
            scored.append((score, names))
            if best_score is None or score > best_score:
                best, best_score = list(program), score
        self.last_choice = sorted(scored, reverse=True)
        return best
