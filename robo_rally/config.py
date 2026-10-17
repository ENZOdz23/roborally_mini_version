"""Game settings. The spec leaves these points open; each value is the proposal from docs/DESIGN.md.
Change a value here and the whole game follows."""

HAND_SIZE = 5                    # cards drawn per turn (open question 1)
PROGRAM_SIZE = 3                 # cards played per turn (spec)
DAMAGED_PROGRAM_SIZE = 2         # a DAMAGED robot plays only 2 cards (open question 6)

CONVEYORS_AFTER_EACH_CARD = False    # False = conveyors run once at the end of the turn, as in the spec (question 3)
CHECKPOINT_ON_CROSS = True           # True = crossing a checkpoint is enough; False = must stop on it (question 4)
PUSH_INTO_WALL_DAMAGES = True        # a robot pushed against a wall becomes DAMAGED (question 6)

MAX_TURNS = 100                  # after this, the game is a draw (question 10)
