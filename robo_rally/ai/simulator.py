"""Plays a program on a copy of the game (Prototype pattern: GameState.clone()).

The real RulesEngine runs on the copy, so the AI's predictions follow exactly the same
rules as the real game. The other robots are assumed to stand still: their cards are hidden.
"""
from dataclasses import dataclass
from typing import List

from .. import config
from ..engine import GameEvent, RulesEngine
from ..model import Card, GameState, Robot


@dataclass
class SimResult:
    state: GameState          # the copy, after the turn
    robot: Robot              # the robot inside the copy
    events: List[GameEvent]   # what happened during the simulated turn


def simulate(state: GameState, robot_id: str, program: List[Card]) -> SimResult:
    copy = state.clone()
    engine = RulesEngine(copy)          # no event bus: nobody watches a simulation
    robot = copy.robot_by_id(robot_id)
    for card in program:
        engine.execute_card(robot, card)
        if config.CONVEYORS_AFTER_EACH_CARD:
            engine.activate_conveyors()
        if not robot.on_board():
            break
    if not config.CONVEYORS_AFTER_EACH_CARD and robot.on_board():
        engine.activate_conveyors()
    return SimResult(copy, robot, engine.events)
