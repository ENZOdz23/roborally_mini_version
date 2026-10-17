"""The perceptron: score = tanh(w . x + b).

x  = the feature vector of a simulated turn (see features.py)
w  = one weight per feature: positive = good for us, strongly negative = danger
b  = bias
tanh squashes the sum into ]-1, 1[ (the non-linear part). It never changes which program
has the highest score, so the choice only depends on w . x.
"""
import json
import math
from pathlib import Path
from typing import Dict, List

from .features import FEATURES

WEIGHTS_FILE = Path(__file__).parent / "weights.json"

DEFAULT_WEIGHTS: Dict[str, float] = {
    "progress": 1.0,
    "checkpoint": 0.8,
    "eliminated": -10.0,
    "blocked": -0.3,
    "danger_around": -0.15,
    "danger_ahead": -0.4,
    "next_turn_risk": -2.0,
    "conveyor_trap": -3.0,
    "facing_goal": 0.3,
    "bonus": 0.25,
    "damaged": -0.3,
    "opponents_out": 0.6,
    "teammates_out": -3.0,
}


class Perceptron:
    def __init__(self, weights: Dict[str, float] = None, bias: float = 0.0):
        weights = dict(DEFAULT_WEIGHTS, **(weights or {}))
        self.weights: List[float] = [weights[name] for name in FEATURES]
        self.bias = bias

    def weighted_sum(self, x: List[float]) -> float:
        return sum(w * xi for w, xi in zip(self.weights, x)) + self.bias

    def score(self, x: List[float]) -> float:
        return math.tanh(self.weighted_sum(x) / 5.0)   # /5 keeps typical sums out of tanh's flat zone

    # ---- saving / loading -----------------------------------------------
    def as_dict(self) -> Dict[str, float]:
        return dict(zip(FEATURES, self.weights))

    def save(self, path=WEIGHTS_FILE) -> None:
        Path(path).write_text(json.dumps({"weights": self.as_dict(), "bias": self.bias}, indent=2))

    @classmethod
    def load(cls, path=WEIGHTS_FILE) -> "Perceptron":
        """Loads trained weights if the file exists, otherwise uses the hand-chosen defaults."""
        path = Path(path)
        if not path.exists():
            return cls()
        data = json.loads(path.read_text())
        return cls(data["weights"], data.get("bias", 0.0))
