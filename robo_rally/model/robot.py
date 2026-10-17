"""Robots and teams."""
from dataclasses import dataclass, field
from enum import Enum
from typing import List

from .direction import Direction
from .position import Position
from .tiles import BonusType

LAST_CHECKPOINT = 3


class RobotStatus(Enum):
    ACTIVE = "active"
    DAMAGED = "damaged"
    ELIMINATED = "eliminated"   # fell in a hole or off the board: out for good


@dataclass
class Robot:
    id: str                     # "R1_E1", "R2_E1", "R1_E2", "R2_E2"
    team_id: int                # 1 or 2
    position: Position
    direction: Direction
    status: RobotStatus = RobotStatus.ACTIVE
    next_cp: int = 1            # checkpoint to reach next; 4 means all 3 are done
    bonuses: List[BonusType] = field(default_factory=list)
    program: list = field(default_factory=list)   # the 3 cards chosen this turn

    # ---- state ----------------------------------------------------------
    def on_board(self) -> bool:
        return self.status != RobotStatus.ELIMINATED

    def finished(self) -> bool:
        return self.next_cp > LAST_CHECKPOINT

    def validate_checkpoint(self, number: int) -> bool:
        """Called when the robot crosses checkpoint `number`. Only counts if it is the next one."""
        if number == self.next_cp:
            self.next_cp += 1
            return True
        return False

    # ---- bonuses --------------------------------------------------------
    def has_bonus(self, bonus: BonusType) -> bool:
        return bonus in self.bonuses

    def use_bonus(self, bonus: BonusType) -> bool:
        """Removes one bonus of this type. Returns False if the robot did not have it."""
        if bonus in self.bonuses:
            self.bonuses.remove(bonus)
            return True
        return False

    def copy(self) -> "Robot":
        """Independent copy (lists copied too). Used by GameState.clone()."""
        return Robot(self.id, self.team_id, self.position, self.direction, self.status,
                     self.next_cp, list(self.bonuses), list(self.program))

    @property
    def label(self) -> str:
        """One letter for the console view: team 1 = a, b ; team 2 = C, D."""
        number = int(self.id[1])          # R1_.. -> 1
        letter = "ab"[number - 1] if self.team_id == 1 else "CD"[number - 1]
        return letter


@dataclass
class Team:
    id: int
    name: str
    robots: List[Robot]

    def robots_on_board(self) -> List[Robot]:
        return [r for r in self.robots if r.on_board()]

    def is_out(self) -> bool:
        """No robot left on the board: this team can no longer win."""
        return not self.robots_on_board()

    def has_won(self) -> bool:
        """Relay rule: every robot still on the board has validated CP3 (open question 5)."""
        alive = self.robots_on_board()
        return bool(alive) and all(r.finished() for r in alive)
