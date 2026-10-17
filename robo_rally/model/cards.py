"""Program cards (Command pattern) and the deck each robot draws from.

A card does not move the robot itself. It tells the engine what to do:
the engine owns the rules (walls, holes, pushes), the card only says
"move 2 forward" or "turn left". The engine is passed in, so this file
never imports the engine.
"""
import random
from typing import List, Optional

from .direction import Rotation


class Card:
    name = "card"

    def execute(self, robot, engine) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return self.name


class MoveCard(Card):
    def __init__(self, steps: int):
        if steps not in (1, 2, 3):
            raise ValueError("a move card moves 1, 2 or 3 cells")
        self.steps = steps
        self.name = f"Move {steps}"

    def execute(self, robot, engine) -> None:
        engine.move(robot, robot.direction, self.steps)


class BackUpCard(Card):
    name = "Back Up"

    def execute(self, robot, engine) -> None:
        engine.move(robot, robot.direction.opposite(), 1)


class TurnCard(Card):
    _NAMES = {Rotation.RIGHT: "Turn Right", Rotation.LEFT: "Turn Left", Rotation.U_TURN: "U-Turn"}

    def __init__(self, rotation: Rotation):
        self.rotation = rotation
        self.name = self._NAMES[rotation]

    def execute(self, robot, engine) -> None:
        engine.rotate(robot, self.rotation)


def standard_deck_cards() -> List[Card]:
    """20 cards per robot. Change the numbers here to tune the game."""
    cards: List[Card] = []
    cards += [MoveCard(1) for _ in range(5)]
    cards += [MoveCard(2) for _ in range(3)]
    cards += [MoveCard(3) for _ in range(2)]
    cards += [BackUpCard() for _ in range(2)]
    cards += [TurnCard(Rotation.RIGHT) for _ in range(3)]
    cards += [TurnCard(Rotation.LEFT) for _ in range(3)]
    cards += [TurnCard(Rotation.U_TURN) for _ in range(2)]
    return cards


class Deck:
    """A robot's own deck: draw pile + discard pile. The discard is reshuffled when the draw pile runs out."""

    def __init__(self, cards: Optional[List[Card]] = None, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.draw_pile: List[Card] = list(cards if cards is not None else standard_deck_cards())
        self.discard: List[Card] = []
        self.rng.shuffle(self.draw_pile)

    def draw(self, n: int) -> List[Card]:
        hand = []
        for _ in range(n):
            if not self.draw_pile:
                self._reshuffle()
                if not self.draw_pile:
                    break
            hand.append(self.draw_pile.pop())
        return hand

    def discard_all(self, cards: List[Card]) -> None:
        self.discard.extend(cards)

    def _reshuffle(self) -> None:
        self.draw_pile, self.discard = self.discard, []
        self.rng.shuffle(self.draw_pile)

    def __len__(self) -> int:
        return len(self.draw_pile) + len(self.discard)
