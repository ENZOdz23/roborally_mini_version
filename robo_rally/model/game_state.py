"""Everything that describes one moment of a game."""
from dataclasses import dataclass, field
from typing import List, Optional, Set

from .board import Board
from .tiles import BonusTile
from .direction import Direction
from .position import Position
from .robot import Robot, Team

# Start cells from the spec. Team 1 faces east, team 2 faces west (into the board).
START_POSITIONS = {
    1: [(Position(0, 0), Direction.EAST), (Position(0, 1), Direction.EAST)],
    2: [(Position(11, 11), Direction.WEST), (Position(11, 10), Direction.WEST)],
}


@dataclass
class GameState:
    board: Board
    teams: List[Team]
    turn: int = 0
    winner: Optional[Team] = None
    over: bool = False            # set by the engine when someone wins, or on a draw
    used_bonuses: Set[Position] = field(default_factory=set)   # bonus cells already picked up

    @classmethod
    def new_game(cls, board: Board) -> "GameState":
        teams = []
        for team_id, starts in START_POSITIONS.items():
            robots = [
                Robot(id=f"R{i}_E{team_id}", team_id=team_id, position=pos, direction=facing)
                for i, (pos, facing) in enumerate(starts, start=1)
            ]
            teams.append(Team(id=team_id, name=f"Team {team_id}", robots=robots))
        return cls(board=board, teams=teams)

    # ---- queries --------------------------------------------------------
    def robots(self) -> List[Robot]:
        return [r for team in self.teams for r in team.robots]

    def robots_on_board(self) -> List[Robot]:
        return [r for r in self.robots() if r.on_board()]

    def robot_at(self, pos: Position) -> Optional[Robot]:
        for robot in self.robots_on_board():
            if robot.position == pos:
                return robot
        return None

    def robot_by_id(self, robot_id: str) -> Robot:
        for robot in self.robots():
            if robot.id == robot_id:
                return robot
        raise KeyError(robot_id)

    def team_of(self, robot: Robot) -> Team:
        return next(t for t in self.teams if t.id == robot.team_id)

    def bonus_available(self, pos: Position) -> bool:
        return isinstance(self.board.tile_at(pos), BonusTile) and pos not in self.used_bonuses

    def clone(self) -> "GameState":
        """Independent copy. The AI plays on clones so the real game is never touched.

        The board never changes during a game, so it is shared; only robots and picked-up
        bonuses are copied. This makes a copy very cheap (the AI makes thousands per turn).
        """
        teams = [Team(t.id, t.name, [r.copy() for r in t.robots]) for t in self.teams]
        winner = next((t for t in teams if self.winner and t.id == self.winner.id), None)
        return GameState(self.board, teams, self.turn, winner, self.over, set(self.used_bonuses))

    # ---- console view ---------------------------------------------------
    def render(self) -> str:
        """Text picture of the board. Robots show as letter + arrow, e.g. 'a>' or 'C^'."""
        lines = ["    " + " ".join(f"{x:<2}" for x in range(Board.SIZE))]
        for y in range(Board.SIZE):
            cells = []
            for x in range(Board.SIZE):
                pos = Position(x, y)
                robot = self.robot_at(pos)
                if robot:
                    text = robot.label + robot.direction.arrow
                elif pos in self.used_bonuses:
                    text = "."
                else:
                    text = self.board.tile_at(pos).symbol
                cells.append(f"{text:<2}")
            lines.append(f"{y:>2}  " + " ".join(cells).rstrip())
        for robot in self.robots():
            status = robot.status.value if not robot.finished() else "finished"
            lines.append(
                f"  {robot.label} = {robot.id} at {robot.position} facing {robot.direction.name.lower()}, "
                f"next CP {min(robot.next_cp, 3) if not robot.finished() else '-'}, {status}"
                + (f", bonuses {[b.name for b in robot.bonuses]}" if robot.bonuses else "")
            )
        return "\n".join(lines)
