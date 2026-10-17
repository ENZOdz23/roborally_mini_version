"""A cell on the board."""
from dataclasses import dataclass

from .direction import Direction


@dataclass(frozen=True)
class Position:
    """Immutable (x, y) cell. x = column (0..11, west to east), y = row (0..11, north to south)."""
    x: int
    y: int

    def step(self, direction: Direction, n: int = 1) -> "Position":
        dx, dy = direction.delta()
        return Position(self.x + dx * n, self.y + dy * n)

    def manhattan(self, other: "Position") -> int:
        return abs(self.x - other.x) + abs(self.y - other.y)

    def __str__(self) -> str:
        return f"({self.x},{self.y})"
