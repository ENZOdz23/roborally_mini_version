"""Robo Rally (mini version) - entry point.

    python main.py                                  open the window (Tkinter)
    python main.py --console                        AI vs random, printed in the terminal
    python main.py --console --team1 ai --team2 ai --seed 7
    python main.py --benchmark 100                  measure the AI over 100 games
"""
import argparse
from pathlib import Path

from robo_rally.model import Board

MAP = Path(__file__).parent / "maps" / "level1.txt"


def main():
    parser = argparse.ArgumentParser(description="Robo Rally - mini version")
    parser.add_argument("--console", action="store_true", help="play in the terminal instead of the window")
    parser.add_argument("--benchmark", type=int, metavar="GAMES", help="play GAMES games AI vs random, print stats")
    parser.add_argument("--team1", default="ai", help="human, random or ai (default: ai)")
    parser.add_argument("--team2", default="random", help="human, random or ai (default: random)")
    parser.add_argument("--seed", type=int, default=None, help="same seed = same game")
    parser.add_argument("--map", default=str(MAP), help="board file")
    args = parser.parse_args()

    board = Board.from_file(args.map)
    if args.benchmark:
        from robo_rally.console import benchmark
        benchmark(board, args.benchmark)
    elif args.console:
        from robo_rally.console import play_in_console
        play_in_console(board, args.team1, args.team2, args.seed)
    else:
        from robo_rally.ui.app import run_app
        run_app(args.map)


if __name__ == "__main__":
    main()
