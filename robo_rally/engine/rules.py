"""The rules of the game: moving, pushing, conveyors, checkpoints, bonuses, victory.

One RulesEngine works on one GameState. The AI creates its own RulesEngine on a
clone of the state to test cards, so the simulation uses exactly the same rules.
The flowcharts "try_step" and "push" in docs/DESIGN.md describe the two core methods.
"""
from enum import Enum
from typing import List, Optional

from .. import config
from ..model import (BonusType, CheckpointTile, ConveyorTile, Direction, GameState, Position,
                     Robot, RobotStatus, Rotation)
from .events import EventBus, EventType, GameEvent


class StepResult(Enum):
    MOVED = "moved"
    BLOCKED = "blocked"     # wall, or a push that failed: the rest of the card is cancelled
    FELL = "fell"           # hole or off the board: the robot is eliminated


class RulesEngine:
    def __init__(self, state: GameState, bus: Optional[EventBus] = None):
        self.state = state
        self.board = state.board
        self.bus = bus
        self.events: List[GameEvent] = []   # everything that happened, in order (the AI reads this)

    # ==================================================================
    # Cards
    # ==================================================================
    def execute_card(self, robot: Robot, card) -> None:
        """Plays one program card for one robot, then applies the effects of the cell it stops on."""
        if not robot.on_board():
            return
        card.execute(robot, self)            # the card calls move() or rotate() below
        if robot.on_board():
            self.apply_stop_effects(robot)

    def rotate(self, robot: Robot, rotation: Rotation) -> None:
        """Turn cards: change direction only. No wall, hole or robot check (spec 3B)."""
        robot.direction = robot.direction.rotate(rotation)
        self.publish(EventType.ROTATED, robot, direction=robot.direction.name)

    def move(self, robot: Robot, direction: Direction, steps: int) -> int:
        """Moves cell by cell and stops at the first wall, failed push or fall. Returns cells moved."""
        if direction == robot.direction and robot.use_bonus(BonusType.BOOST):
            steps += 1                       # Turbo: +1 cell on a forward move (not on Back Up)
        moved = 0
        for _ in range(steps):
            if self.try_step(robot, direction) is not StepResult.MOVED:
                break
            moved += 1
        return moved

    # ==================================================================
    # One step (see flowchart "try_step")
    # ==================================================================
    def try_step(self, robot: Robot, direction: Direction) -> StepResult:
        target = robot.position.step(direction)

        if not self.board.in_bounds(target):
            self.eliminate(robot, "fell off the board")
            return StepResult.FELL

        tile = self.board.tile_at(target)

        if (tile.blocks() or tile.is_hole()) and self._can_jump(robot, target, direction):
            robot.use_bonus(BonusType.JUMP)
            robot.position = target.step(direction)
            self.publish(EventType.JUMPED, robot, over=str(target), to=str(robot.position))
            self._on_cell_entered(robot)
            return StepResult.MOVED

        if tile.blocks():
            self.publish(EventType.BLOCKED, robot, at=str(target))
            return StepResult.BLOCKED

        other = self.state.robot_at(target)
        if other is not None and not self.push(other, direction):
            return StepResult.BLOCKED

        robot.position = target
        self.publish(EventType.MOVED, robot, to=str(target))

        if tile.is_hole():
            self.eliminate(robot, "fell in a hole")
            return StepResult.FELL

        self._on_cell_entered(robot)
        return StepResult.MOVED

    def _can_jump(self, robot: Robot, obstacle: Position, direction: Direction) -> bool:
        """Jump is used only if the robot holds it and the landing cell behind the obstacle is safe and free."""
        if not robot.has_bonus(BonusType.JUMP):
            return False
        landing = obstacle.step(direction)
        if not self.board.in_bounds(landing):
            return False
        tile = self.board.tile_at(landing)
        return not tile.blocks() and not tile.is_hole() and self.state.robot_at(landing) is None

    # ==================================================================
    # Pushing (see flowchart "push")
    # ==================================================================
    def push(self, robot: Robot, direction: Direction) -> bool:
        """Pushes `robot` one cell. Returns False if it could not move (then the pusher stops too)."""
        if robot.use_bonus(BonusType.SHIELD):
            self.publish(EventType.SHIELD_USED, robot)
            return False

        target = robot.position.step(direction)

        if not self.board.in_bounds(target):
            self.publish(EventType.PUSHED, robot, to="off the board")
            self.eliminate(robot, "pushed off the board")
            return True

        tile = self.board.tile_at(target)
        if tile.blocks():
            if config.PUSH_INTO_WALL_DAMAGES:
                self.damage(robot, "pushed against a wall")
            return False

        other = self.state.robot_at(target)
        if other is not None and not self.push(other, direction):     # chain push
            return False

        robot.position = target                # direction does not change when pushed
        self.publish(EventType.PUSHED, robot, to=str(target))

        if tile.is_hole():
            self.eliminate(robot, "pushed into a hole")
            return True

        self._on_cell_entered(robot)
        return True

    # ==================================================================
    # Conveyors (end of turn)
    # ==================================================================
    def activate_conveyors(self) -> None:
        """Every robot on a conveyor moves 1 cell at the same time (curved ones also rotate).

        A conveyor never pushes: a robot stays where it is if its target is a wall,
        a robot that is not moving, or a cell another robot is also heading to.
        """
        plans = {}
        for robot in self.state.robots_on_board():
            tile = self.board.tile_at(robot.position)
            if isinstance(tile, ConveyorTile):
                plans[robot.id] = (robot, tile, robot.position.step(tile.direction))

        changed = True
        while changed:                     # drop moves that cannot happen until nothing changes
            changed = False
            targets = [t for (_, _, t) in plans.values()]
            for robot_id, (robot, tile, target) in list(plans.items()):
                blocked = False
                if self.board.in_bounds(target):
                    occupant = self.state.robot_at(target)
                    blocked = (self.board.tile_at(target).blocks()
                               or targets.count(target) > 1
                               or (occupant is not None and occupant.id not in plans))
                if blocked:
                    del plans[robot_id]
                    changed = True

        for robot, tile, target in plans.values():
            robot.position = target
            if tile.curved:
                robot.direction = robot.direction.rotate(tile.turn)
            self.publish(EventType.CONVEYED, robot, to=str(target), direction=robot.direction.name)

        for robot, tile, target in plans.values():
            if not self.board.in_bounds(target):
                self.eliminate(robot, "carried off the board")
            elif self.board.tile_at(target).is_hole():
                self.eliminate(robot, "carried into a hole")
            else:
                self.apply_stop_effects(robot)

    # ==================================================================
    # Cell effects, damage, elimination
    # ==================================================================
    def _on_cell_entered(self, robot: Robot) -> None:
        """Called on every cell a robot passes through."""
        if config.CHECKPOINT_ON_CROSS:
            self.check_checkpoint(robot)

    def apply_stop_effects(self, robot: Robot) -> None:
        """Called on the cell where a robot stops (end of a card, end of a conveyor move)."""
        self.check_checkpoint(robot)
        if self.state.bonus_available(robot.position):
            tile = self.board.tile_at(robot.position)
            self.state.used_bonuses.add(robot.position)
            robot.bonuses.append(tile.bonus)
            self.publish(EventType.BONUS_PICKED, robot, bonus=tile.bonus.name)
            if tile.bonus is BonusType.REPAIR and robot.status is RobotStatus.DAMAGED:
                self._repair(robot)

    def check_checkpoint(self, robot: Robot) -> None:
        tile = self.board.tile_at(robot.position)
        if isinstance(tile, CheckpointTile) and robot.validate_checkpoint(tile.number):
            self.publish(EventType.CHECKPOINT, robot, number=tile.number)
            if robot.finished():
                self.publish(EventType.FINISHED, robot)

    def damage(self, robot: Robot, reason: str) -> None:
        if robot.status is not RobotStatus.ACTIVE:
            return
        robot.status = RobotStatus.DAMAGED
        self.publish(EventType.DAMAGED, robot, reason=reason)
        if robot.has_bonus(BonusType.REPAIR):       # a held repair kit is used straight away
            self._repair(robot)

    def _repair(self, robot: Robot) -> None:
        robot.use_bonus(BonusType.REPAIR)
        robot.status = RobotStatus.ACTIVE
        self.publish(EventType.REPAIRED, robot)

    def eliminate(self, robot: Robot, reason: str) -> None:
        robot.status = RobotStatus.ELIMINATED
        self.publish(EventType.ELIMINATED, robot, reason=reason)

    # ==================================================================
    # Victory
    # ==================================================================
    def check_victory(self) -> bool:
        """Sets state.winner / state.over. Returns True when the game is over."""
        if self.state.over:
            return True
        winners = [team for team in self.state.teams if team.has_won()]
        if len(winners) == 1:
            self.state.winner = winners[0]
            self.state.over = True
            self.publish(EventType.GAME_WON, None, team=winners[0].name)
        elif len(winners) > 1 or all(team.is_out() for team in self.state.teams):
            self.state.over = True
            self.publish(EventType.GAME_DRAW, None)
        return self.state.over

    # ==================================================================
    def publish(self, event_type: EventType, robot: Optional[Robot], **data) -> None:
        event = GameEvent(event_type, robot.id if robot else None, data)
        self.events.append(event)
        if self.bus is not None:
            self.bus.publish(event)
