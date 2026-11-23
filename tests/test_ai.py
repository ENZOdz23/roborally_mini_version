"""Tests for the AI (ai/)."""
import random
import tempfile
import unittest
from pathlib import Path

from robo_rally.ai import OracleStrategy, Perceptron, PerceptronStrategy, RandomStrategy, make_strategy
from robo_rally.ai.features import FEATURES, extract
from robo_rally.ai.pathfinding import UNREACHABLE, DistanceMap
from robo_rally.ai.simulator import simulate
from robo_rally.engine import Game
from robo_rally.model import BackUpCard, Board, MoveCard, Position, Rotation, TurnCard

try:                                   # python -m unittest tests.test_ai
    from .test_rules import E, N, make_game
except ImportError:                    # python -m unittest discover tests
    from test_rules import E, N, make_game

LEVEL1 = Path(__file__).parent.parent / "maps" / "level1.txt"


class TestDistanceMap(unittest.TestCase):
    def test_walks_around_walls(self):
        # wall between (4,5) and CP1 at (6,5): Manhattan says 2, walking takes 4
        state, _ = make_game({(6, 5): "1", (5, 5): "#", (11, 0): "."})
        distances = DistanceMap(state.board)
        self.assertEqual(Position(4, 5).manhattan(Position(6, 5)), 2)
        self.assertEqual(distances.distance(Position(4, 5), 1), 4)
        self.assertEqual(distances.distance(Position(6, 5), 1), 0)

    def test_walls_and_holes_are_unreachable(self):
        state, _ = make_game({(5, 5): "#", (6, 6): "O"})
        distances = DistanceMap(state.board)
        self.assertEqual(distances.distance(Position(5, 5), 1), UNREACHABLE)
        self.assertEqual(distances.distance(Position(6, 6), 1), UNREACHABLE)

    def test_remaining_counts_the_whole_race(self):
        distances = DistanceMap(Board.from_file(LEVEL1))
        start = Position(0, 0)
        self.assertEqual(distances.remaining(start, 1),
                         distances.distance(start, 1) + distances.leg[1] + distances.leg[2])
        self.assertEqual(distances.remaining(start, 4), 0)


class TestSimulator(unittest.TestCase):
    def test_simulation_does_not_touch_the_real_game(self):
        state, _ = make_game({(5, 5): "O"}, {"R1_E1": (3, 5, E)})
        result = simulate(state, "R1_E1", [MoveCard(3)])
        self.assertFalse(result.robot.on_board())
        self.assertTrue(state.robot_by_id("R1_E1").on_board())
        self.assertEqual(state.robot_by_id("R1_E1").position, Position(3, 5))

    def test_simulation_runs_the_conveyors(self):
        state, _ = make_game({(4, 5): ">"}, {"R1_E1": (3, 5, E)})
        result = simulate(state, "R1_E1", [MoveCard(1)])
        self.assertEqual(result.robot.position, Position(5, 5))


class TestFeatures(unittest.TestCase):
    def test_feature_values(self):
        state, _ = make_game({(5, 5): "O"}, {"R1_E1": (3, 5, E)})
        distances = DistanceMap(state.board)
        dead = extract(state, simulate(state, "R1_E1", [MoveCard(3)]), distances)
        self.assertEqual(dead["eliminated"], 1.0)
        safe = extract(state, simulate(state, "R1_E1", [TurnCard(Rotation.LEFT)]), distances)
        self.assertEqual(safe["eliminated"], 0.0)
        self.assertEqual(set(safe), set(FEATURES))

    def test_danger_ahead_and_next_turn_risk(self):
        state, _ = make_game(robots={"R1_E1": (11, 5, N)})
        distances = DistanceMap(state.board)
        f = extract(state, simulate(state, "R1_E1", [TurnCard(Rotation.RIGHT)]), distances)   # faces the edge
        self.assertEqual(f["danger_ahead"], 1.0)
        self.assertGreater(f["next_turn_risk"], 0)


class TestPerceptron(unittest.TestCase):
    def test_score_follows_the_weights(self):
        p = Perceptron()
        good = [0.0] * len(FEATURES)
        bad = list(good)
        bad[FEATURES.index("eliminated")] = 1.0
        good[FEATURES.index("progress")] = 1.0
        self.assertGreater(p.score(good), p.score(bad))
        self.assertTrue(-1 < p.score(bad) < 1)          # tanh keeps the score in ]-1, 1[

    def test_save_and_load(self):
        p = Perceptron({"progress": 2.5}, bias=0.1)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "w.json"
            p.save(path)
            q = Perceptron.load(path)
        self.assertEqual(q.as_dict()["progress"], 2.5)
        self.assertEqual(q.bias, 0.1)


class TestPerceptronStrategy(unittest.TestCase):
    def test_avoids_the_hole_when_it_can(self):
        state, _ = make_game({(4, 5): "O"}, {"R1_E1": (3, 5, E)})
        hand = [MoveCard(1), MoveCard(2), TurnCard(Rotation.LEFT), TurnCard(Rotation.RIGHT), BackUpCard()]
        program = PerceptronStrategy(Perceptron(), random.Random(0)).choose(state, state.robot_by_id("R1_E1"), hand, 3)
        result = simulate(state, "R1_E1", program)
        self.assertTrue(result.robot.on_board())

    def test_goes_for_the_checkpoint(self):
        state, _ = make_game({(6, 5): "1", (11, 0): "."}, {"R1_E1": (3, 5, E)})
        hand = [MoveCard(3), TurnCard(Rotation.LEFT), TurnCard(Rotation.RIGHT), BackUpCard(), TurnCard(Rotation.U_TURN)]
        program = PerceptronStrategy(Perceptron(), random.Random(0)).choose(state, state.robot_by_id("R1_E1"), hand, 3)
        self.assertEqual(simulate(state, "R1_E1", program).robot.next_cp, 2)

    def test_beats_random_play(self):
        board = Board.from_file(LEVEL1)
        wins = 0
        for seed in range(10):
            game = Game(board, {1: PerceptronStrategy(rng=random.Random(seed)),
                                2: RandomStrategy(random.Random(seed))}, seed=seed)
            state = game.play_to_end()
            wins += state.winner is not None and state.winner.id == 1
        self.assertGreaterEqual(wins, 8)

    def test_factory(self):
        self.assertIsInstance(make_strategy("ai"), PerceptronStrategy)
        with self.assertRaises(ValueError):
            make_strategy("wizard")


if __name__ == "__main__":
    unittest.main()


class TestOracle(unittest.TestCase):
    """The oracle follows the shortest path to the next checkpoint without simulating the rules."""

    def choose(self, tiles, robot, hand, size=3):
        state, _ = make_game({(11, 0): ".", **tiles}, {"R1_E1": robot})
        return OracleStrategy().choose(state, state.robot_by_id("R1_E1"), hand, size)

    def test_goes_straight_to_the_checkpoint(self):
        # CP1 three cells east: Move 3 first, then nothing left to gain
        program = self.choose({(8, 5): "1"}, (5, 5, E),
                              [TurnCard(Rotation.LEFT), MoveCard(3), MoveCard(1), BackUpCard(), MoveCard(2)])
        self.assertEqual(program[0].name, "Move 3")

    def test_turns_toward_the_path(self):
        # CP1 is north while the robot faces east: turn left, then move
        program = self.choose({(5, 2): "1"}, (5, 5, E),
                              [MoveCard(1), TurnCard(Rotation.RIGHT), TurnCard(Rotation.LEFT), MoveCard(3), BackUpCard()])
        self.assertEqual([c.name for c in program[:2]], ["Turn Left", "Move 3"])

    def test_never_walks_into_a_hole(self):
        program = self.choose({(6, 5): "O", (9, 5): "1"}, (5, 5, E),
                              [MoveCard(1), MoveCard(2), TurnCard(Rotation.LEFT), TurnCard(Rotation.RIGHT), BackUpCard()])
        state, _ = make_game({(11, 0): ".", (6, 5): "O", (9, 5): "1"}, {"R1_E1": (5, 5, E)})
        result = simulate(state, "R1_E1", program)
        self.assertTrue(result.robot.on_board())

    def test_keeps_a_safe_card_for_the_last_slot(self):
        # robot on the north edge facing north: Move 1 first falls off the board,
        # so the oracle must find an order where Back Up or the turn comes before it.
        oracle = OracleStrategy()
        state, _ = make_game({(11, 0): ".", (5, 9): "1"}, {"R1_E1": (5, 0, N)})
        robot = state.robot_by_id("R1_E1")
        hand = [BackUpCard(), MoveCard(1), TurnCard(Rotation.LEFT)]
        dm = oracle.distances(state.board)
        self.assertFalse(oracle.leaves_a_safe_way(MoveCard(1), hand, 2, robot.position, N, 1, dm))
        program = oracle.choose(state, robot, hand, 3)
        self.assertTrue(simulate(state, "R1_E1", program).robot.on_board())

    def test_factory_and_per_robot_players(self):
        self.assertIsInstance(make_strategy("oracle"), OracleStrategy)
        board = Board.from_file(LEVEL1)
        players = {"R1_E1": make_strategy("ai"), "R2_E1": make_strategy("oracle"),
                   "R1_E2": make_strategy("oracle"), "R2_E2": make_strategy("random")}
        game = Game(board, players, seed=4)
        for robot in game.state.robots():
            self.assertIs(game.strategy_of(robot), players[robot.id])
        game.play_to_end()
        self.assertTrue(game.state.over)

    def test_team_players_still_work(self):
        game = Game(Board.from_file(LEVEL1), {1: make_strategy("oracle"), 2: make_strategy("random")}, seed=2)
        robot = game.state.robot_by_id("R2_E1")
        self.assertIsInstance(game.strategy_of(robot), OracleStrategy)
