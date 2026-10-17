"""Where a person chooses their cards: click cards of the hand in the order to play them."""
import tkinter as tk
from tkinter import ttk
from typing import Callable, List

from ..model import Card


class ProgramPanel(ttk.LabelFrame):
    def __init__(self, master, on_change: Callable[[List[Card]], None], on_confirm: Callable[[List[Card]], None]):
        super().__init__(master, text="Your cards", padding=8)
        self.on_change, self.on_confirm = on_change, on_confirm
        self.hand: List[Card] = []
        self.chosen: List[int] = []        # indexes in self.hand, in play order
        self.size = 3

        self.title = ttk.Label(self, text="", font=("Segoe UI", 10, "bold"))
        self.title.pack(anchor="w")
        self.hand_frame = ttk.Frame(self)
        self.hand_frame.pack(fill="x", pady=(6, 4))
        self.program_label = ttk.Label(self, text="", wraplength=330)
        self.program_label.pack(anchor="w")
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", pady=(6, 0))
        ttk.Button(buttons, text="Undo", command=self.undo).pack(side="left")
        self.confirm_button = ttk.Button(buttons, text="Confirm program", command=self.confirm)
        self.confirm_button.pack(side="right")
        self.card_buttons: List[ttk.Button] = []

    def show(self, robot_id: str, hand: List[Card], size: int) -> None:
        self.hand, self.chosen, self.size = hand, [], size
        self.title.config(text=f"{robot_id}: choose {size} cards, in order")
        for button in self.card_buttons:
            button.destroy()
        self.card_buttons = []
        for i, card in enumerate(hand):
            button = ttk.Button(self.hand_frame, text=card.name, width=11, command=lambda i=i: self.pick(i))
            button.grid(row=i // 3, column=i % 3, padx=2, pady=2)
            self.card_buttons.append(button)
        self._refresh()

    def pick(self, index: int) -> None:
        if index not in self.chosen and len(self.chosen) < self.size:
            self.chosen.append(index)
            self._refresh()

    def undo(self) -> None:
        if self.chosen:
            self.chosen.pop()
            self._refresh()

    def confirm(self) -> None:
        if len(self.chosen) == self.size:
            self.on_confirm(self.program())

    def program(self) -> List[Card]:
        return [self.hand[i] for i in self.chosen]

    def _refresh(self) -> None:
        for i, button in enumerate(self.card_buttons):
            button.state(["disabled"] if i in self.chosen else ["!disabled"])
        names = [f"{n + 1}. {card.name}" for n, card in enumerate(self.program())]
        names += [f"{n + 1}. ..." for n in range(len(names), self.size)]
        self.program_label.config(text="Program:  " + "   ".join(names))
        self.confirm_button.state(["!disabled"] if len(self.chosen) == self.size else ["disabled"])
        self.on_change(self.program())
