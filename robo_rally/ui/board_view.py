"""Draws the 12 x 12 board and the robots on a Tkinter Canvas."""
import tkinter as tk
from typing import Optional

from ..model import Board, GameState, Position
from .assets import CELL, Assets

MARGIN = 22                     # room for the coordinates around the board


class BoardView(tk.Canvas):
    def __init__(self, master, assets: Assets):
        size = Board.SIZE * CELL + 2 * MARGIN
        super().__init__(master, width=size, height=size, bg="#2b2f33", highlightthickness=0)
        self.assets = assets

    def cell_origin(self, pos: Position):
        return MARGIN + pos.x * CELL, MARGIN + pos.y * CELL

    def draw(self, state: GameState, highlight: Optional[str] = None, ghost: Optional[Position] = None,
             message: Optional[str] = None) -> None:
        """Redraws everything. highlight = id of the robot whose player is choosing cards,
        ghost = where that robot would end its turn with the cards chosen so far."""
        self.delete("all")
        for i in range(Board.SIZE):                                   # coordinates
            c = MARGIN + i * CELL + CELL // 2
            self.create_text(c, MARGIN // 2, text=str(i), fill="#c9ced3", font=("Segoe UI", 9))
            self.create_text(MARGIN // 2, c, text=str(i), fill="#c9ced3", font=("Segoe UI", 9))

        for pos in state.board.positions():                           # tiles
            x, y = self.cell_origin(pos)
            image = self.assets.tile(state.board.tile_at(pos), used_bonus=pos in state.used_bonuses)
            self.create_image(x, y, image=image, anchor="nw")

        if ghost is not None and state.board.in_bounds(ghost):        # preview of the human's program
            x, y = self.cell_origin(ghost)
            self.create_rectangle(x + 3, y + 3, x + CELL - 3, y + CELL - 3, outline="#ffffff", width=3, dash=(6, 4))

        for robot in state.robots_on_board():                         # robots
            x, y = self.cell_origin(robot.position)
            if robot.id == highlight:
                self.create_rectangle(x + 1, y + 1, x + CELL - 1, y + CELL - 1, outline="#ffe14d", width=3)
            self.create_image(x, y, image=self.assets.robot(robot), anchor="nw")
            if robot.finished():
                self.create_text(x + CELL - 8, y + 9, text="✔", fill="#3dff7a", font=("Segoe UI", 11, "bold"))

        if message:                                                   # "Team 1 wins!"
            w = int(self["width"])
            self.create_rectangle(0, w // 2 - 40, w, w // 2 + 40, fill="#000000", stipple="gray50", outline="")
            self.create_text(w // 2, w // 2, text=message, fill="#ffe14d", font=("Segoe UI", 26, "bold"))
