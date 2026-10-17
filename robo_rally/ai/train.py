"""Tunes the perceptron's weights by playing games (hill climbing).

    python -m robo_rally.ai.train --iterations 40 --games 40

1. Start from the current weights and measure their fitness over a fixed set of games.
2. Change one or two weights a little, at random, and measure again on the same games.
3. Keep the change if the fitness went up, otherwise undo it.
4. Repeat, then save the best weights to robo_rally/ai/weights.json (loaded automatically by the AI).

Fitness of one game, from the AI team's point of view (the opponent plays at random):
    +100 if the AI team wins, -1 per turn played, -15 per AI robot eliminated
Playing the same seeds for every candidate makes the comparison fair.
"""
import argparse
import random
from pathlib import Path

from ..engine import Game
from ..model import Board
from .features import FEATURES
from .perceptron import Perceptron
from .perceptron_strategy import PerceptronStrategy
from .strategy import RandomStrategy

MAP = Path(__file__).resolve().parents[2] / "maps" / "level1.txt"


def play(board, perceptron, seed, ai_team):
    strategies = {ai_team: PerceptronStrategy(perceptron, random.Random(seed)),
                  3 - ai_team: RandomStrategy(random.Random(seed + 10_000))}
    game = Game(board, strategies, seed=seed)
    game.play_to_end()
    return game.state


def fitness(board, perceptron, seeds):
    total = 0.0
    for i, seed in enumerate(seeds):
        ai_team = 1 + i % 2                          # play both sides of the board
        state = play(board, perceptron, seed, ai_team)
        won = state.winner is not None and state.winner.id == ai_team
        deaths = sum(1 for r in state.robots() if r.team_id == ai_team and not r.on_board())
        total += 100 * won - state.turn - 15 * deaths
    return total / len(seeds)


def train(iterations=40, games=40, seed=0, verbose=True):
    board = Board.from_file(MAP)
    rng = random.Random(seed)
    seeds = [rng.randrange(1_000_000) for _ in range(games)]
    best = Perceptron.load()
    best_fit = fitness(board, best, seeds)
    if verbose:
        print(f"start: fitness {best_fit:.1f}")
    for it in range(1, iterations + 1):
        weights = best.as_dict()
        for name in rng.sample(FEATURES, rng.choice([1, 2])):
            weights[name] += rng.gauss(0, 0.3 * abs(weights[name]) + 0.1)
        candidate = Perceptron(weights, best.bias)
        fit = fitness(board, candidate, seeds)
        if fit > best_fit:
            best, best_fit = candidate, fit
        if verbose:
            print(f"iteration {it:3}: candidate {fit:7.1f}   best {best_fit:7.1f}")
    return best, best_fit


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iterations", type=int, default=40)
    parser.add_argument("--games", type=int, default=40)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    best, fit = train(args.iterations, args.games, args.seed)
    best.save()
    print(f"saved weights (fitness {fit:.1f}):")
    for name, w in best.as_dict().items():
        print(f"  {name:14} {w:+.3f}")


if __name__ == "__main__":
    main()
