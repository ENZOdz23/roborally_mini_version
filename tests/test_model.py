"""Tests for the model layer. Run with:  python -m unittest discover tests"""
import random
import unittest
from pathlib import Path

from robo_rally.model import (BackUpCard, Board, BonusTile, BonusType, CheckpointTile, ConveyorTile, Deck,
                              Direction, GameState, HoleTile, MoveCard, NormalTile, Position, Rotation,
                              TurnCard, WallTile)
from robo_rally.model.tiles import tile_from_token

LEVEL1 = Path(__file__).parent.parent / "maps" / "level1.txt"


class TestDirection(unittest.TestCase):
    def test_turn_right_goes_clockwise(self):
        self.assertEqual(Direction.NORTH.turn_right(), Direction.EAST)
        self.assertEqual(Direction.WEST.turn_right(), Direction.NORTH)

    def test_turn_left_goes_counter_clockwise(self):
        self.assertEqual(Direction.NORTH.turn_left(), Direction.WEST)
        self.assertEqual(Direction.EAST.turn_left(), Direction.NORTH)

    def test_four_right_turns_come_back(self):
        for d in Direction:
            self.assertEqual(d.turn_right().turn_right().turn_right().turn_right(), d)

    def test_u_turn_is_opposite(self):
        self.assertEqual(Direction.NORTH.rotate(Rotation.U_TURN), Direction.SOUTH)
        self.assertEqual(Direction.EAST.opposite(), Direction.WEST)

    def test_north_goes_up_the_grid(self):
        self.assertEqual(Direction.NORTH.delta(), (0, -1))
        self.assertEqual(Direction.SOUTH.delta(), (0, 1))


class TestPosition(unittest.TestCase):
    def test_step(self):
        self.assertEqual(Position(3, 5).step(Direction.EAST), Position(4, 5))
        self.assertEqual(Position(3, 5).step(Direction.NORTH, 2), Position(3, 3))

    def test_manhattan(self):
        self.assertEqual(Position(0, 0).manhattan(Position(5, 6)), 11)

    def test_positions_are_hashable_and_equal_by_value(self):
        self.assertEqual(len({Position(1, 1), Position(1, 1)}), 1)


class TestTiles(unittest.TestCase):
    def test_tokens(self):
        self.assertIsInstance(tile_from_token("."), NormalTile)
        self.assertTrue(tile_from_token("#").blocks())
        self.assertTrue(tile_from_token("O").is_hole())
        self.assertEqual(tile_from_token("2").number, 2)
        self.assertEqual(tile_from_token("J").bonus, BonusType.JUMP)

    def test_straight_conveyor(self):
        tile = tile_from_token(">")
        self.assertIsInstance(tile, ConveyorTile)
        self.assertEqual(tile.direction, Direction.EAST)
        self.assertFalse(tile.curved)

    def test_curved_conveyor(self):
        tile = tile_from_token("rv")
        self.assertEqual(tile.direction, Direction.SOUTH)
        self.assertEqual(tile.turn, Rotation.RIGHT)

    def test_symbol_round_trip(self):
        for token in [".", "#", "O", "1", "S", "<", "l^"]:
            self.assertEqual(tile_from_token(token).symbol, token)

    def test_unknown_token(self):
        with self.assertRaises(ValueError):
            tile_from_token("?")


class TestBoard(unittest.TestCase):
    def setUp(self):
        self.board = Board.from_file(LEVEL1)

    def test_proportions_match_spec(self):
        c = self.board.count_tiles()
        self.assertTrue(75 <= c["NormalTile"] <= 80)
        self.assertTrue(20 <= c["WallTile"] <= 25)
        self.assertTrue(20 <= c["ConveyorTile"] <= 24)
        self.assertTrue(10 <= c["HoleTile"] <= 12)
        self.assertTrue(6 <= c["BonusTile"] <= 8)
        self.assertEqual(c["CheckpointTile"], 3)
        self.assertEqual(sum(c.values()), 144)

    def test_checkpoints_found(self):
        self.assertEqual(self.board.checkpoints, {1: Position(5, 5), 2: Position(10, 1), 3: Position(1, 10)})

    def test_bounds(self):
        self.assertTrue(self.board.in_bounds(Position(11, 11)))
        self.assertFalse(self.board.in_bounds(Position(12, 0)))
        self.assertFalse(self.board.in_bounds(Position(0, -1)))
        with self.assertRaises(IndexError):
            self.board.tile_at(Position(-1, 0))

    def test_start_cells_are_normal(self):
        for pos in [Position(0, 0), Position(0, 1), Position(11, 11), Position(11, 10)]:
            self.assertIsInstance(self.board.tile_at(pos), NormalTile)

    def test_first_checkpoint_is_fair(self):
        from robo_rally.ai.pathfinding import DistanceMap
        distances = DistanceMap(self.board)          # real walking distance, around walls and holes
        self.assertEqual(distances.distance(Position(0, 0), 1), distances.distance(Position(11, 11), 1))
        self.assertEqual(distances.distance(Position(0, 1), 1), distances.distance(Position(11, 10), 1))

    def test_wrong_size_rejected(self):
        with self.assertRaises(ValueError):
            Board.from_text(". . .\n. . .")

    def test_missing_checkpoint_rejected(self):
        text = "\n".join(" ".join(["."] * 12) for _ in range(12))
        with self.assertRaises(ValueError):
            Board.from_text(text)


class TestRobotsAndTeams(unittest.TestCase):
    def setUp(self):
        self.state = GameState.new_game(Board.from_file(LEVEL1))

    def test_four_robots_on_start_cells(self):
        ids = {r.id: r.position for r in self.state.robots()}
        self.assertEqual(ids, {"R1_E1": Position(0, 0), "R2_E1": Position(0, 1),
                               "R1_E2": Position(11, 11), "R2_E2": Position(11, 10)})

    def test_checkpoints_only_in_order(self):
        robot = self.state.robot_by_id("R1_E1")
        self.assertFalse(robot.validate_checkpoint(2))   # CP2 before CP1: no effect
        self.assertEqual(robot.next_cp, 1)
        self.assertTrue(robot.validate_checkpoint(1))
        self.assertTrue(robot.validate_checkpoint(2))
        self.assertFalse(robot.validate_checkpoint(2))   # same CP twice: no effect
        self.assertTrue(robot.validate_checkpoint(3))
        self.assertTrue(robot.finished())

    def test_team_wins_only_when_last_robot_finishes(self):
        team = self.state.teams[0]
        a, b = team.robots
        a.next_cp = 4
        self.assertFalse(team.has_won())
        b.next_cp = 4
        self.assertTrue(team.has_won())

    def test_team_out_when_no_robot_left(self):
        from robo_rally.model import RobotStatus
        team = self.state.teams[1]
        for r in team.robots:
            r.status = RobotStatus.ELIMINATED
        self.assertTrue(team.is_out())
        self.assertFalse(team.has_won())
        self.assertIsNone(self.state.robot_at(Position(11, 11)))

    def test_bonuses(self):
        robot = self.state.robot_by_id("R1_E2")
        robot.bonuses.append(BonusType.SHIELD)
        self.assertTrue(robot.has_bonus(BonusType.SHIELD))
        self.assertTrue(robot.use_bonus(BonusType.SHIELD))
        self.assertFalse(robot.use_bonus(BonusType.SHIELD))

    def test_clone_is_independent(self):
        copy = self.state.clone()
        copy.robot_by_id("R1_E1").position = Position(5, 5)
        self.assertEqual(self.state.robot_by_id("R1_E1").position, Position(0, 0))

    def test_render_shows_robots(self):
        text = self.state.render()
        self.assertIn("a>", text)
        self.assertIn("C<", text)


class FakeEngine:
    """Records what the cards ask for, so cards can be tested without the real engine."""
    def __init__(self):
        self.calls = []

    def move(self, robot, direction, steps):
        self.calls.append(("move", direction, steps))

    def rotate(self, robot, rotation):
        self.calls.append(("rotate", rotation))


class TestCards(unittest.TestCase):
    def setUp(self):
        self.robot = GameState.new_game(Board.from_file(LEVEL1)).robot_by_id("R1_E1")  # faces EAST
        self.engine = FakeEngine()

    def test_move_card_moves_forward(self):
        MoveCard(3).execute(self.robot, self.engine)
        self.assertEqual(self.engine.calls, [("move", Direction.EAST, 3)])

    def test_back_up_moves_backwards_without_turning(self):
        BackUpCard().execute(self.robot, self.engine)
        self.assertEqual(self.engine.calls, [("move", Direction.WEST, 1)])
        self.assertEqual(self.robot.direction, Direction.EAST)

    def test_turn_card(self):
        TurnCard(Rotation.LEFT).execute(self.robot, self.engine)
        self.assertEqual(self.engine.calls, [("rotate", Rotation.LEFT)])

    def test_deck_has_20_cards_and_never_loses_any(self):
        deck = Deck(rng=random.Random(1))
        self.assertEqual(len(deck), 20)
        for _ in range(10):
            hand = deck.draw(5)
            self.assertEqual(len(hand), 5)
            deck.discard_all(hand)
            self.assertEqual(len(deck), 20)

    def test_deck_is_reproducible_with_a_seed(self):
        a = [c.name for c in Deck(rng=random.Random(42)).draw(5)]
        b = [c.name for c in Deck(rng=random.Random(42)).draw(5)]
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
