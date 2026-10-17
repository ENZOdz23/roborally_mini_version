"""Directions a robot can face, and rotations that change them."""
from enum import Enum


class Rotation(Enum):
    """How a turn card or a curved conveyor rotates a robot."""
    RIGHT = 1     # +90 degrees, clockwise
    LEFT = -1     # -90 degrees, counter-clockwise
    U_TURN = 2    # 180 degrees


class Direction(Enum):
    """The 4 cardinal directions, numbered as in the spec."""
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    def rotate(self, rotation: Rotation) -> "Direction":
        return Direction((self.value + rotation.value) % 4)

    def turn_right(self) -> "Direction":
        return self.rotate(Rotation.RIGHT)

    def turn_left(self) -> "Direction":
        return self.rotate(Rotation.LEFT)

    def opposite(self) -> "Direction":
        return self.rotate(Rotation.U_TURN)

    def delta(self) -> tuple:
        """(dx, dy) of one step. y grows towards the SOUTH: (0, 0) is the north-west corner."""
        return _DELTAS[self]

    @property
    def arrow(self) -> str:
        return _ARROWS[self]

    @staticmethod
    def from_arrow(char: str) -> "Direction":
        for direction, arrow in _ARROWS.items():
            if arrow == char:
                return direction
        raise ValueError(f"not an arrow: {char!r}")


_DELTAS = {
    Direction.NORTH: (0, -1),
    Direction.EAST: (1, 0),
    Direction.SOUTH: (0, 1),
    Direction.WEST: (-1, 0),
}

_ARROWS = {
    Direction.NORTH: "^",
    Direction.EAST: ">",
    Direction.SOUTH: "v",
    Direction.WEST: "<",
}
