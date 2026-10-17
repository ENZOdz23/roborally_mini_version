"""Text mode: play a game in the terminal, or measure the AI over many games."""
import random
import time
from collections import Counter

from .ai import PerceptronStrategy, RandomStrategy, make_strategy
from .engine import EventType, Game
from .model import Board

# Events worth printing in the terminal (the full list is in engine/events.py)
SHOWN = {EventType.CARD_PLAYED, EventType.ELIMINATED, EventType.CHECKPOINT, EventType.FINISHED,
         EventType.PUSHED, EventType.BONUS_PICKED, EventType.DAMAGED, EventType.GAME_WON, EventType.GAME_DRAW}


def play_in_console(board: Board, team1: str, team2: str, seed=None, quiet=False) -> Game:
    if "human" in (team1.lower(), team2.lower()):
        raise SystemExit("Human players need the window: run  python main.py")
    game = Game(board, {1: make_strategy(team1), 2: make_strategy(team2)}, seed=seed)
    if not quiet:
        game.bus.subscribe(lambda e: print("   ", e) if e.type in SHOWN else None)
        print(game.state.render())
    while not game.state.over:
        if not quiet:
            print(f"\n=== Turn {game.state.turn + 1} ===")
        game.play_turn()
        if not quiet:
            print(game.state.render())
    winner = game.state.winner.name if game.state.winner else "nobody (draw)"
    print(f"\nGame over after {game.state.turn} turns. Winner: {winner}")
    return game


def benchmark(board: Board, games: int = 100) -> None:
    """Perceptron AI against random play, swapping sides every game."""
    wins, lost, turns, start = 0, 0, 0, time.time()
    results = Counter()
    for seed in range(games):
        ai_team = 1 + seed % 2
        strategies = {ai_team: PerceptronStrategy(rng=random.Random(seed)),
                      3 - ai_team: RandomStrategy(random.Random(seed + 10_000))}
        state = Game(board, strategies, seed=seed).play_to_end()
        won = state.winner is not None and state.winner.id == ai_team
        wins += won
        lost += sum(1 for r in state.robots() if r.team_id == ai_team and not r.on_board())
        turns += state.turn
        results["AI wins" if won else ("draw" if state.winner is None else "random wins")] += 1
    print(f"{games} games, Perceptron AI vs Random")
    print(f"  results:              {dict(results)}")
    print(f"  AI win rate:          {100 * wins / games:.0f}%")
    print(f"  AI robots lost/game:  {lost / games:.2f} (out of 2)")
    print(f"  average game length:  {turns / games:.1f} turns")
    print(f"  time per game:        {(time.time() - start) / games:.2f}s")
