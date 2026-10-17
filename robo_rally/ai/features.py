"""Turns "the situation after a simulated turn" into numbers the perceptron can weigh.

Each feature is one number. The perceptron multiplies each one by its weight and adds them up.
To add a feature: add its name to FEATURES, compute it in extract(), give it a weight in perceptron.py.
"""
from typing import Dict, List

from ..engine import EventType
from ..model import (BackUpCard, ConveyorTile, Direction, GameState, MoveCard, Position, RobotStatus, Rotation,
                     TurnCard)
from .pathfinding import DistanceMap
from .simulator import SimResult, simulate

ONE_OF_EACH = [MoveCard(1), MoveCard(2), MoveCard(3), BackUpCard(),
               TurnCard(Rotation.RIGHT), TurnCard(Rotation.LEFT), TurnCard(Rotation.U_TURN)]

FEATURES = [
    "progress",        # cells gained on the whole race (real walking distance), divided by 6
    "checkpoint",      # checkpoints validated during the turn
    "eliminated",      # 1 if the robot fell in a hole or off the board
    "blocked",         # how many times a wall stopped the robot
    "danger_around",   # holes or board edges among the 4 neighbouring cells
    "danger_ahead",    # 1 if the cell in front is a hole or off the board
    "next_turn_risk",  # share of the 7 card types that would kill the robot if played first next turn
    "conveyor_trap",   # 1 if the robot ends on a conveyor that carries it into a hole or off the board
    "facing_goal",     # 1 if one step forward gets closer to the next checkpoint
    "bonus",           # bonuses picked up
    "damaged",         # 1 if the robot ends the turn damaged
    "opponents_out",   # opponents eliminated during the turn (pushed into a hole...)
    "teammates_out",   # teammates eliminated during the turn
]


def _deadly(state: GameState, pos: Position) -> bool:
    return not state.board.in_bounds(pos) or state.board.tile_at(pos).is_hole()


def extract(before: GameState, result: SimResult, distances: DistanceMap) -> Dict[str, float]:
    robot = result.robot
    start = before.robot_by_id(robot.id)
    mine = [e for e in result.events if e.robot_id == robot.id]
    eliminated_ids = [e.robot_id for e in result.events if e.type is EventType.ELIMINATED]
    teammates = {r.id for r in result.state.robots() if r.team_id == robot.team_id and r.id != robot.id}

    f = dict.fromkeys(FEATURES, 0.0)
    f["checkpoint"] = sum(1 for e in mine if e.type is EventType.CHECKPOINT)
    f["blocked"] = sum(1 for e in mine if e.type is EventType.BLOCKED)
    f["bonus"] = sum(1 for e in mine if e.type is EventType.BONUS_PICKED)
    f["opponents_out"] = sum(1 for rid in eliminated_ids if rid != robot.id and rid not in teammates)
    f["teammates_out"] = sum(1 for rid in eliminated_ids if rid in teammates)

    if not robot.on_board():
        f["eliminated"] = 1.0
        return f

    before_left = distances.remaining(start.position, start.next_cp)
    after_left = distances.remaining(robot.position, robot.next_cp)
    f["progress"] = (before_left - after_left) / 6.0

    pos = robot.position
    f["danger_around"] = sum(1 for d in Direction if _deadly(result.state, pos.step(d)))
    ahead = pos.step(robot.direction)
    f["danger_ahead"] = 1.0 if _deadly(result.state, ahead) else 0.0

    tile = result.state.board.tile_at(pos)
    if isinstance(tile, ConveyorTile) and _deadly(result.state, pos.step(tile.direction)):
        f["conveyor_trap"] = 1.0

    if not robot.finished() and not _deadly(result.state, ahead):
        if distances.distance(ahead, robot.next_cp) < distances.distance(pos, robot.next_cp):
            f["facing_goal"] = 1.0

    # one card of look-ahead: is the robot ending the turn in a spot where many cards are fatal?
    deadly_cards = sum(1 for card in ONE_OF_EACH
                       if not simulate(result.state, robot.id, [card]).robot.on_board())
    f["next_turn_risk"] = deadly_cards / len(ONE_OF_EACH)

    f["damaged"] = 1.0 if robot.status is RobotStatus.DAMAGED else 0.0
    return f


def as_vector(features: Dict[str, float]) -> List[float]:
    return [features[name] for name in FEATURES]
