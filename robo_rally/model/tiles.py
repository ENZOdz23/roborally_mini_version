"""The 6 kinds of cells on the board.

Each tile answers two questions the engine asks while moving a robot:
  blocks()  -> does it stop a robot from entering? (walls)
  is_hole() -> does a robot that enters it get eliminated? (holes)
The engine never has to check "isinstance(tile, WallTile)".
"""
from enum import Enum
from typing import Optional

from .direction import Direction, Rotation


class BonusType(Enum):
    SHIELD = "S"   # protects against the next push
    BOOST = "T"    # +1 cell on the next move card (Turbo)
    REPAIR = "K"   # DAMAGED -> ACTIVE (repair Kit)
    JUMP = "J"     # leap over one wall or hole on the next move


class Tile:
    """Base class. A normal tile: nothing happens."""

    def blocks(self) -> bool:
        return False

    def is_hole(self) -> bool:
        return False

    @property
    def symbol(self) -> str:
        """Token used in map files and in the console view."""
        return "."


class NormalTile(Tile):
    pass


class WallTile(Tile):
    def blocks(self) -> bool:
        return True

    @property
    def symbol(self) -> str:
        return "#"


class HoleTile(Tile):
    def is_hole(self) -> bool:
        return True

    @property
    def symbol(self) -> str:
        return "O"


class ConveyorTile(Tile):
    """Moves a robot 1 cell towards `direction` at the end of the turn.

    A curved conveyor also rotates the robot by `turn` (RIGHT or LEFT).
    """

    def __init__(self, direction: Direction, turn: Optional[Rotation] = None):
        self.direction = direction
        self.turn = turn

    @property
    def curved(self) -> bool:
        return self.turn is not None

    @property
    def symbol(self) -> str:
        prefix = {None: "", Rotation.RIGHT: "r", Rotation.LEFT: "l"}[self.turn]
        return prefix + self.direction.arrow


class BonusTile(Tile):
    """Gives its bonus to the first robot that stops on it.

    Whether it was already picked up is stored in GameState.used_bonuses, not here:
    tiles never change during a game, so the board can be shared between copies of the game.
    """

    def __init__(self, bonus: BonusType):
        self.bonus = bonus

    @property
    def symbol(self) -> str:
        return self.bonus.value


class CheckpointTile(Tile):
    """Checkpoint 1, 2 or 3. Never disappears."""

    def __init__(self, number: int):
        if number not in (1, 2, 3):
            raise ValueError(f"checkpoint number must be 1, 2 or 3, got {number}")
        self.number = number

    @property
    def symbol(self) -> str:
        return str(self.number)


def tile_from_token(token: str) -> Tile:
    """Builds a tile from its map-file token. The legend is at the top of maps/level1.txt."""
    if token == ".":
        return NormalTile()
    if token == "#":
        return WallTile()
    if token == "O":
        return HoleTile()
    if token in ("1", "2", "3"):
        return CheckpointTile(int(token))
    for bonus in BonusType:
        if token == bonus.value:
            return BonusTile(bonus)
    if len(token) == 1:
        return ConveyorTile(Direction.from_arrow(token))
    if len(token) == 2 and token[0] in "rl":
        turn = Rotation.RIGHT if token[0] == "r" else Rotation.LEFT
        return ConveyorTile(Direction.from_arrow(token[1]), turn)
    raise ValueError(f"unknown map token: {token!r}")
