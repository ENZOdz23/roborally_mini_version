"""Events the engine publishes (Observer pattern).

The engine says what happened ("R1_E1 moved to (4,5)") and does not care who listens.
Later the Tkinter view and a text log subscribe to the bus; the engine never imports them.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


class EventType(Enum):
    TURN_STARTED = "turn started"
    PROGRAMMED = "locked in its program"
    CARD_PLAYED = "plays"
    CONVEYORS = "conveyors run"
    MOVED = "moved"
    ROTATED = "rotated"
    BLOCKED = "blocked by a wall"
    JUMPED = "jumped"
    PUSHED = "pushed"
    CONVEYED = "carried by a conveyor"
    ELIMINATED = "eliminated"
    DAMAGED = "damaged"
    REPAIRED = "repaired"
    BONUS_PICKED = "picked up a bonus"
    SHIELD_USED = "blocked a push with its shield"
    CHECKPOINT = "validated a checkpoint"
    FINISHED = "finished the race"
    GAME_WON = "won the game"
    GAME_DRAW = "draw"


@dataclass
class GameEvent:
    type: EventType
    robot_id: Optional[str] = None
    data: dict = field(default_factory=dict)

    def __str__(self) -> str:
        who = self.robot_id or ""
        extra = ", ".join(f"{k}={v}" for k, v in self.data.items())
        text = f"{who} {self.type.value}".strip()
        return text + (f" ({extra})" if extra else "")


Listener = Callable[[GameEvent], None]


class EventBus:
    def __init__(self):
        self._listeners: Dict[Optional[EventType], List[Listener]] = {}

    def subscribe(self, listener: Listener, event_type: Optional[EventType] = None) -> None:
        """Listen to one event type, or to every event if event_type is None."""
        self._listeners.setdefault(event_type, []).append(listener)

    def publish(self, event: GameEvent) -> None:
        for listener in self._listeners.get(event.type, []) + self._listeners.get(None, []):
            listener(event)
