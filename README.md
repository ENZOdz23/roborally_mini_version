# Robo Rally (mini version)

12 x 12 board, 2 teams of 2 robots, 3 cards per turn, a perceptron AI and a Tkinter window.
Design and UML: `docs/DESIGN.md`. Report: `docs/Rapport_Robo_Rally.docx`.

## Run it

Python 3.10 or newer. Only the standard library is used (Tkinter comes with Python on Windows and macOS;
on Linux install `python3-tk`).

```
python main.py                                   # the window
python main.py --console                         # AI vs random, printed in the terminal
python main.py --console --team1 ai --team2 ai --seed 7
python main.py --benchmark 200                   # AI vs random over 200 games, with statistics
python -m unittest discover tests                # 90 tests
python -m robo_rally.ai.train                    # optional: tune the AI's weights by playing games
```

In the window: choose who plays each team (Human, Random, Perceptron AI), press **Start**, then
**Step** (one card), **Play turn**, or **Auto**. A human player clicks 3 cards in order; a dashed square
shows where the robot will end up, then **Confirm program**.

## Project layout

```
robo_rally/
  config.py        game settings (the open points of the spec, one line each)
  model/           the data: Direction, Position, tiles, Board, Robot, Team, cards, Deck, GameState
  engine/          the rules (rules.py), the turn loop (game.py), the events (events.py)
  ai/              strategies: random, human, perceptron (+ simulator, features, pathfinding, training)
  ui/              the Tkinter window and its images (assets/)
  console.py       text mode and benchmark
maps/level1.txt    the board (edit it in any text editor, legend at the top)
tests/             unit tests, one file per layer
tools/             make_assets.py draws the images (needs Pillow, only to change the look)
main.py            entry point
```

Each layer only uses the layers below it: `ui -> ai -> engine -> model`. The model and the engine
never import Tkinter, so the whole game runs and is tested without a window.

## Results (200 games, `python main.py --benchmark 200`)

| | Perceptron AI vs Random |
|---|---|
| AI win rate | 97.5% (195 of 200; the other 5 are draws, no losses) |
| AI robots lost per game | 0.36 out of 2 |
| Average game length | 30 turns |
| Time per game | 0.3 s |

Random against random: every robot falls in a hole or off the board in about 5 turns.
