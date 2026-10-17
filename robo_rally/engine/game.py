"""The turn loop (State pattern).

A turn is a fixed cycle of phases:

    Draw -> Programming -> Cards (3 registers x every robot) -> End of turn -> Draw ...
                                                                            -> Game over

Each phase is a small class with one method, run(game), that does its work and
returns the next phase. Game.step() runs the current phase once. Each step plays at
most one card, so the window can redraw between steps and show the game move by move.
"""
import random
from typing import Dict, List, Optional

from .. import config
from ..model import Board, Card, Deck, GameState, Robot, RobotStatus
from .events import EventBus, EventType
from .rules import RulesEngine


class Game:
    def __init__(self, board: Board, strategies: Dict[int, object], seed: Optional[int] = None,
                 bus: Optional[EventBus] = None):
        """strategies: {team_id: Strategy} - both robots of a team use the same strategy."""
        self.rng = random.Random(seed)
        self.state = GameState.new_game(board)
        self.bus = bus or EventBus()
        self.engine = RulesEngine(self.state, self.bus)
        self.strategies = strategies
        self.decks = {r.id: Deck(rng=random.Random(self.rng.random())) for r in self.state.robots()}
        self.hands: Dict[str, List[Card]] = {}
        self.phase: Phase = DrawPhase()
        self.first_team: Optional[int] = None     # drawn by lot at the start of each turn

    # ---- driving the game -----------------------------------------------
    def step(self) -> bool:
        """Runs the current phase once. Returns False when nothing can happen (game over or waiting)."""
        if self.state.over:
            return False
        before = self.phase
        self.phase = self.phase.run(self)
        stuck = self.phase is before and isinstance(before, ProgrammingPhase)   # waiting for a person
        return not stuck

    def play_turn(self) -> None:
        """Steps until the turn is over (or the game ends, or a person must choose)."""
        while self.step():
            if isinstance(self.phase, DrawPhase):
                break

    def play_to_end(self) -> GameState:
        while self.step():
            pass
        return self.state

    # ---- programming ----------------------------------------------------
    def strategy_of(self, robot: Robot):
        return self.strategies[robot.team_id]

    def program_size(self, robot: Robot) -> int:
        return config.DAMAGED_PROGRAM_SIZE if robot.status is RobotStatus.DAMAGED else config.PROGRAM_SIZE

    def waiting_for(self) -> List[Robot]:
        """Robots whose (human) player still has to choose cards."""
        if not isinstance(self.phase, ProgrammingPhase):
            return []
        return [r for r in self.state.robots_on_board()
                if not r.program and r.id in self.hands and self.strategy_of(r).interactive]

    def submit_program(self, robot_id: str, cards: List[Card]) -> None:
        """Called by the window when a person confirms their cards."""
        robot = self.state.robot_by_id(robot_id)
        hand = self.hands[robot_id]
        if len(cards) != self.program_size(robot) or any(cards.count(c) > hand.count(c) for c in cards):
            raise ValueError(f"{robot_id} must choose {self.program_size(robot)} cards from its hand")
        self._lock_program(robot, cards)

    def _lock_program(self, robot: Robot, cards: List[Card]) -> None:
        robot.program = list(cards)
        self.engine.publish(EventType.PROGRAMMED, robot, cards=", ".join(c.name for c in cards))

    def play_order(self) -> List[Robot]:
        """No priority antenna in the mini version: robots alternate between teams, and the team
        that plays first is drawn by lot each turn (open question 2). Simply alternating turn by
        turn gave the team playing second on turn 1 a measurable edge (59% wins in AI vs AI)."""
        if self.first_team is None:
            self.first_team = self.rng.choice([1, 2])
        first = next(t for t in self.state.teams if t.id == self.first_team)
        second = next(t for t in self.state.teams if t.id != self.first_team)
        order = []
        for a, b in zip(first.robots, second.robots):
            order += [a, b]
        return order


# ======================================================================
# Phases
# ======================================================================
class Phase:
    name = "phase"

    def run(self, game: Game) -> "Phase":
        raise NotImplementedError


class DrawPhase(Phase):
    name = "Draw"

    def run(self, game):
        game.state.turn += 1
        game.first_team = None
        game.engine.publish(EventType.TURN_STARTED, None, turn=game.state.turn)
        game.hands = {}
        for robot in game.state.robots_on_board():
            robot.program = []
            game.hands[robot.id] = game.decks[robot.id].draw(config.HAND_SIZE)
        return ProgrammingPhase()


class ProgrammingPhase(Phase):
    name = "Programming"

    def run(self, game):
        waiting = False
        for robot in game.state.robots_on_board():
            if not robot.program:
                cards = game.strategy_of(robot).choose(game.state, robot, game.hands[robot.id],
                                                       game.program_size(robot))
                if cards is None:
                    waiting = True                # a person has not chosen yet
                else:
                    game._lock_program(robot, cards)
        if waiting:
            return self                           # stay in this phase until they confirm
        for robot in game.state.robots_on_board():   # unplayed cards go back to the discard pile
            leftover = list(game.hands[robot.id])
            for card in robot.program:
                leftover.remove(card)
            game.decks[robot.id].discard_all(leftover)
        return CardPhase(register=0, order=game.play_order())


class CardPhase(Phase):
    """Plays one card per step: register 1 for every robot, then register 2, then register 3."""
    name = "Cards"

    def __init__(self, register: int, order: List[Robot], index: int = 0):
        self.register, self.order, self.index = register, order, index

    def run(self, game):
        robot = self.order[self.index]
        if robot.on_board() and self.register < len(robot.program):
            card = robot.program[self.register]
            game.engine.publish(EventType.CARD_PLAYED, robot, card=card.name, register=self.register + 1)
            game.engine.execute_card(robot, card)

        if self.index + 1 < len(self.order):
            return CardPhase(self.register, self.order, self.index + 1)

        # every robot has played this register
        if config.CONVEYORS_AFTER_EACH_CARD:
            game.engine.publish(EventType.CONVEYORS, None)
            game.engine.activate_conveyors()
        if game.engine.check_victory():
            return GameOverPhase()
        if self.register + 1 < config.PROGRAM_SIZE:
            return CardPhase(self.register + 1, self.order)
        return EndOfTurnPhase()


class EndOfTurnPhase(Phase):
    name = "End of turn"

    def run(self, game):
        if not config.CONVEYORS_AFTER_EACH_CARD:
            game.engine.publish(EventType.CONVEYORS, None)
            game.engine.activate_conveyors()
        for robot in game.state.robots():
            game.decks[robot.id].discard_all(robot.program)
            robot.program = []
        if game.engine.check_victory():
            return GameOverPhase()
        if game.state.turn >= config.MAX_TURNS:
            game.state.over = True
            game.engine.publish(EventType.GAME_DRAW, None, reason="turn limit")
            return GameOverPhase()
        return DrawPhase()


class GameOverPhase(Phase):
    name = "Game over"

    def run(self, game):
        return self
