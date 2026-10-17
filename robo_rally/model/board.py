"""The 12 x 12 grid of tiles."""
from collections import Counter
from pathlib import Path
from typing import Dict, List

from .position import Position
from .tiles import CheckpointTile, Tile, tile_from_token


class Board:
    SIZE = 12

    def __init__(self, grid: List[List[Tile]]):
        if len(grid) != self.SIZE or any(len(row) != self.SIZE for row in grid):
            raise ValueError(f"board must be {self.SIZE} x {self.SIZE}")
        self._grid = grid  # grid[y][x]
        self.checkpoints: Dict[int, Position] = self._find_checkpoints()

    # ---- building -------------------------------------------------------
    @classmethod
    def from_text(cls, text: str) -> "Board":
        """One line per row, tokens separated by spaces. Lines starting with ';' are comments."""
        rows = []
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith(";"):
                continue
            rows.append([tile_from_token(token) for token in line.split()])
        return cls(rows)

    @classmethod
    def from_file(cls, path) -> "Board":
        return cls.from_text(Path(path).read_text(encoding="utf-8"))

    # ---- queries --------------------------------------------------------
    def in_bounds(self, pos: Position) -> bool:
        return 0 <= pos.x < self.SIZE and 0 <= pos.y < self.SIZE

    def tile_at(self, pos: Position) -> Tile:
        if not self.in_bounds(pos):
            raise IndexError(f"{pos} is outside the board")
        return self._grid[pos.y][pos.x]

    def positions(self):
        for y in range(self.SIZE):
            for x in range(self.SIZE):
                yield Position(x, y)

    def count_tiles(self) -> Counter:
        """How many tiles of each kind, e.g. {'NormalTile': 79, 'WallTile': 22, ...}."""
        return Counter(type(self.tile_at(p)).__name__ for p in self.positions())

    def _find_checkpoints(self) -> Dict[int, Position]:
        found = {}
        for pos in self.positions():
            tile = self.tile_at(pos)
            if isinstance(tile, CheckpointTile):
                if tile.number in found:
                    raise ValueError(f"checkpoint {tile.number} appears twice")
                found[tile.number] = pos
        if sorted(found) != [1, 2, 3]:
            raise ValueError(f"board needs checkpoints 1, 2 and 3, found {sorted(found)}")
        return found
