"""The oracle: a player written by hand that follows the shortest path.

It does not learn and does not simulate the rules. It knows the answer from the map:
the BFS of pathfinding.py gives, for every cell, the number of steps left to the next
checkpoint. The oracle builds its program one card at a time, always taking the card
that brings it closest to the goal along that shortest path, as long as the cards left
in its hand can still fill the next slots without falling.

To judge a card it only "walks" on the map: a wall stops it, a hole or the edge is
fatal, a checkpoint on the way counts. It ignores the other robots and the conveyors
(that is what keeps it simple and fast). Walking on the map takes a few additions per
card, against a full simulation of the rules for each of the perceptron's 60 programs.
"""
import random
from typing import List, Optional, Tuple

from ..model import BackUpCard, Board, Card, Direction, MoveCard, Position, TurnCard
from .pathfinding import UNREACHABLE, DistanceMap
from .strategy import Strategy

DEAD = 10_000          # cost of a card that would make the robot fall


class OracleStrategy(Strategy):
    name = "Oracle"

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self._distances = None

    def distances(self, board: Board) -> DistanceMap:
        if self._distances is None or self._distances.board is not board:
            self._distances = DistanceMap(board)
        return self._distances

    # ------------------------------------------------------------------
    def choose(self, state, robot, hand, size):
        dm = self.distances(state.board)
        pos, facing, next_cp = robot.position, robot.direction, robot.next_cp
        remaining, program = list(hand), []
        for slot in range(size):
            # cards from best to worst; on a tie, the first one in the hand comes first
            ranked = sorted(remaining, key=lambda card: self.cost(card, pos, facing, next_cp, dm))
            # keep the best card that still leaves a safe way to fill the slots after it
            best = next((card for card in ranked
                         if self.leaves_a_safe_way(card, remaining, size - slot - 1, pos, facing, next_cp, dm)),
                        ranked[0])
            pos, facing, next_cp, _ = self.walk(best, pos, facing, next_cp, dm.board)
            program.append(best)
            remaining.remove(best)
        return program

    def leaves_a_safe_way(self, card, remaining, slots_after, pos, facing, next_cp, dm) -> bool:
        """True if playing `card` now does not kill the robot AND some order of the other cards
        can fill the `slots_after` next slots without falling. Without this check, the oracle
        sometimes kept a good first card and was left with only fatal cards for the last slot."""
        pos, facing, next_cp, dead = self.walk(card, pos, facing, next_cp, dm.board)
        if dead:
            return False
        if slots_after == 0:
            return True
        others = list(remaining)
        others.remove(card)
        return any(self.leaves_a_safe_way(other, others, slots_after - 1, pos, facing, next_cp, dm)
                   for other in others)

    def cost(self, card: Card, pos: Position, facing: Direction, next_cp: int, dm: DistanceMap) -> int:
        """Cells still to walk after this card + quarter turns still needed to face the path."""
        pos, facing, next_cp, dead = self.walk(card, pos, facing, next_cp, dm.board)
        if dead:
            return DEAD
        if next_cp > 3:                       # race finished: any safe card is fine
            return 0
        return dm.remaining(pos, next_cp) + self.turns_needed(pos, facing, next_cp, dm)

    @staticmethod
    def walk(card: Card, pos: Position, facing: Direction, next_cp: int,
             board: Board) -> Tuple[Position, Direction, int, bool]:
        """Where the card takes the robot on an empty board: (position, facing, next checkpoint, dead)."""
        if isinstance(card, TurnCard):
            return pos, facing.rotate(card.rotation), next_cp, False
        if isinstance(card, MoveCard):
            direction, steps = facing, card.steps
        elif isinstance(card, BackUpCard):
            direction, steps = facing.opposite(), 1
        else:
            return pos, facing, next_cp, False
        for _ in range(steps):
            nxt = pos.step(direction)
            if not board.in_bounds(nxt) or board.tile_at(nxt).is_hole():
                return nxt, facing, next_cp, True
            tile = board.tile_at(nxt)
            if tile.blocks():
                break
            pos = nxt
            if getattr(tile, "number", None) == next_cp:      # a checkpoint crossed in the right order
                next_cp += 1
        return pos, facing, next_cp, False

    @staticmethod
    def turns_needed(pos: Position, facing: Direction, next_cp: int, dm: DistanceMap) -> int:
        """0 if the robot faces a cell of the shortest path, 1 if it must turn left/right, 2 for a U-turn."""
        here = dm.distance(pos, next_cp)
        best = None
        for direction in Direction:
            d = dm.distance(pos.step(direction), next_cp)
            if d < here and d != UNREACHABLE and (best is None or d < best[0]):
                best = (d, direction)
        if best is None:
            return 0
        diff = (best[1].value - facing.value) % 4
        return {0: 0, 1: 1, 2: 2, 3: 1}[diff]
