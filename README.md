# Robo Rally (mini version)

12 x 12 board, 2 teams of 2 robots, 3 cards per turn, a perceptron AI, a hand-written oracle and a Tkinter window.
Design and UML: `docs/DESIGN.md`. Report: `docs/Rapport_Robo_Rally.docx`.

## Run it

Python 3.10 or newer. Only the standard library is used (Tkinter comes with Python on Windows and macOS;
on Linux install `python3-tk`).

```
python main.py                                   # the window
python main.py --console                         # AI vs random, printed in the terminal
python main.py --console --team1 ai --team2 ai --seed 7
python main.py --console --robots ai,oracle,ai,oracle   # one player per robot (R1_E1,R2_E1,R1_E2,R2_E2)
python main.py --benchmark 200                   # AI vs random over 200 games, with statistics
python main.py --benchmark 200 --team1 ai --team2 oracle  # perceptron vs oracle
python -m unittest discover tests                # 96 tests
python -m robo_rally.ai.train                    # optional: tune the AI's weights by playing games
```

In the window: choose who plays each robot (Human, Random, Perceptron AI, Oracle), press **Start**, then
**Step** (one card), **Play turn**, or **Auto**. A human player clicks 3 cards in order; a dashed square
shows where the robot will end up, then **Confirm program**.

## Project layout

```
robo_rally/
  config.py        game settings (the open points of the spec, one line each)
  model/           the data: Direction, Position, tiles, Board, Robot, Team, cards, Deck, GameState
  engine/          the rules (rules.py), the turn loop (game.py), the events (events.py)
  ai/              strategies: random, human, perceptron, oracle (+ simulator, features, pathfinding, training)
  ui/              the Tkinter window and its images (assets/)
  console.py       text mode and benchmark
maps/level1.txt    the board (edit it in any text editor, legend at the top)
tests/             unit tests, one file per layer
tools/             make_assets.py draws the images (needs Pillow, only to change the look)
main.py            entry point
```

Each layer only uses the layers below it: `ui -> ai -> engine -> model`. The model and the engine
never import Tkinter, so the whole game runs and is tested without a window.

## The two players

- **Perceptron AI** (`ai/perceptron_strategy.py`): tries every order of 3 cards from its hand (up to 60),
  simulates each one with the real rules, describes the result with 13 numbers and scores it with a perceptron.
- **Oracle** (`ai/oracle.py`): the "ideal player written by hand". It reads the shortest path (BFS) to the
  next checkpoint and picks, card by card, the one that brings it closest, while making sure the cards left
  can still fill the program without falling. No simulation, no learning, ignores conveyors and other robots.

## Results (200 games each, sides swapped every game)

| | Perceptron vs Random | Oracle vs Random |
|---|---|---|
| Win rate | 97.5% (rest are draws) | 87.5% (rest are draws) |
| Own robots lost per game | 0.34 out of 2 | 0.84 out of 2 |
| Average game length | 30 turns | 29 turns |
| Time per game | 0.3 s | 0.01 s |

Perceptron against oracle: 130 wins for the perceptron, 67 for the oracle, 3 draws
(perceptron loses 0.63 robots per game: the oracle pushes it more than random play does).

Random against random: every robot falls in a hole or off the board in about 5 turns.
