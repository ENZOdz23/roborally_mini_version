"""Text mode: play a game in the terminal, or compare two players over many games."""
import random
import time
from collections import Counter
from typing import Dict, Optional

from .ai import make_strategy
from .engine import EventType, Game
from .model import Board

# Events worth printing in the terminal (the full list is in engine/events.py)
SHOWN = {EventType.CARD_PLAYED, EventType.ELIMINATED, EventType.CHECKPOINT, EventType.FINISHED,
         EventType.PUSHED, EventType.BONUS_PICKED, EventType.DAMAGED, EventType.GAME_WON, EventType.GAME_DRAW}

ROBOT_IDS = ["R1_E1", "R2_E1", "R1_E2", "R2_E2"]


def parse_robots(text: str) -> Dict[str, str]:
    """"ai,oracle,random,ai" -> one player type per robot, in the order R1_E1, R2_E1, R1_E2, R2_E2."""
    kinds = [k.strip() for k in text.split(",")]
    if len(kinds) != 4:
        raise SystemExit("--robots needs 4 players, e.g. --robots ai,oracle,ai,oracle")
    return dict(zip(ROBOT_IDS, kinds))


def play_in_console(board: Board, team1: str, team2: str, seed=None, quiet=False,
                    robots: Optional[Dict[str, str]] = None) -> Game:
    kinds = robots or {"R1_E1": team1, "R2_E1": team1, "R1_E2": team2, "R2_E2": team2}
    if "human" in (k.lower() for k in kinds.values()):
        raise SystemExit("Human players need the window: run  python main.py")
    game = Game(board, {robot_id: make_strategy(kind) for robot_id, kind in kinds.items()}, seed=seed)
    if not quiet:
        print("Players:", ", ".join(f"{r}={k}" for r, k in kinds.items()))
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


def benchmark(board: Board, games: int = 100, player: str = "ai", opponent: str = "random") -> None:
    """`player` against `opponent` over many games, swapping sides every game so no side is favoured."""
    wins, lost, turns, start = 0, 0, 0, time.time()
    results = Counter()
    for seed in range(games):
        team = 1 + seed % 2                       # the team `player` controls in this game
        strategies = {team: make_strategy(player, random.Random(seed)),
                      3 - team: make_strategy(opponent, random.Random(seed + 10_000))}
        state = Game(board, strategies, seed=seed).play_to_end()
        won = state.winner is not None and state.winner.id == team
        wins += won
        lost += sum(1 for r in state.robots() if r.team_id == team and not r.on_board()
                    and not r.finished())
        turns += state.turn
        results[f"{player} wins" if won else ("draw" if state.winner is None else f"{opponent} wins")] += 1
    print(f"{games} games, {player} vs {opponent}")
    print(f"  results:                {dict(results)}")
    print(f"  {player} win rate:".ljust(28) + f"{100 * wins / games:.1f}%")
    print(f"  {player} robots lost/game:".ljust(28) + f"{lost / games:.2f} (out of 2)")
    print(f"  average game length:    {turns / games:.1f} turns")
    print(f"  time per game:          {(time.time() - start) / games:.3f}s")
