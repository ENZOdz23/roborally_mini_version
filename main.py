"""Robo Rally (mini version) - entry point.

    python main.py                                  open the window (Tkinter)
    python main.py --console                        AI vs random, printed in the terminal
    python main.py --console --team1 ai --team2 ai --seed 7
    python main.py --console --robots ai,oracle,ai,oracle    one player per robot
    python main.py --benchmark 100                  measure the AI over 100 games (vs random)
    python main.py --benchmark 200 --team1 ai --team2 oracle   perceptron vs oracle
"""
import argparse
from pathlib import Path

from robo_rally.model import Board

MAP = Path(__file__).parent / "maps" / "level1.txt"


def main():
    parser = argparse.ArgumentParser(description="Robo Rally - mini version")
    parser.add_argument("--console", action="store_true", help="play in the terminal instead of the window")
    parser.add_argument("--benchmark", type=int, metavar="GAMES", help="play GAMES games team1 vs team2 (sides swapped each game), print stats")
    parser.add_argument("--team1", default="ai", help="human, random, ai or oracle (default: ai)")
    parser.add_argument("--team2", default="random", help="human, random, ai or oracle (default: random)")
    parser.add_argument("--robots", metavar="P1,P2,P3,P4",
                        help="one player per robot, in the order R1_E1,R2_E1,R1_E2,R2_E2 (console only)")
    parser.add_argument("--seed", type=int, default=None, help="same seed = same game")
    parser.add_argument("--map", default=str(MAP), help="board file")
    args = parser.parse_args()

    board = Board.from_file(args.map)
    if args.benchmark:
        from robo_rally.console import benchmark
        benchmark(board, args.benchmark, args.team1, args.team2)
    elif args.console:
        from robo_rally.console import parse_robots, play_in_console
        robots = parse_robots(args.robots) if args.robots else None
        play_in_console(board, args.team1, args.team2, args.seed, robots=robots)
    else:
        from robo_rally.ui.app import run_app
        run_app(args.map)


if __name__ == "__main__":
    main()
