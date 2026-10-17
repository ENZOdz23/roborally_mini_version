"""Loads the 48x48 PNG images and picks the right one for a tile or a robot."""
from pathlib import Path
import tkinter as tk

from ..model import BonusTile, CheckpointTile, ConveyorTile, HoleTile, Robot, Rotation, Tile, WallTile

ASSETS_DIR = Path(__file__).parent / "assets"
CELL = 48                       # pixels per cell, the size of every image
_DIR_LETTER = {0: "N", 1: "E", 2: "S", 3: "W"}


class Assets:
    def __init__(self):
        # Tkinter forgets an image if no Python variable keeps it, so they all live in this dict.
        self.images = {path.stem: tk.PhotoImage(file=str(path)) for path in ASSETS_DIR.glob("*.png")}
        if not self.images:
            raise FileNotFoundError(f"no images in {ASSETS_DIR}")

    def tile(self, tile: Tile, used_bonus: bool = False) -> tk.PhotoImage:
        if isinstance(tile, WallTile):
            return self.images["wall"]
        if isinstance(tile, HoleTile):
            return self.images["hole"]
        if isinstance(tile, CheckpointTile):
            return self.images[f"checkpoint_{tile.number}"]
        if isinstance(tile, BonusTile) and not used_bonus:
            return self.images[f"bonus_{tile.bonus.value}"]
        if isinstance(tile, ConveyorTile):
            d = _DIR_LETTER[tile.direction.value]
            if tile.turn is None:
                return self.images[f"conveyor_{d}"]
            return self.images[f"conveyor_{'r' if tile.turn is Rotation.RIGHT else 'l'}_{d}"]
        return self.images["floor"]

    def robot(self, robot: Robot) -> tk.PhotoImage:
        return self.images[f"robot_{robot.label}_{_DIR_LETTER[robot.direction.value]}"]
