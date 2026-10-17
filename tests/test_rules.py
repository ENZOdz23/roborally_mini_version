"""Tests for the rules engine. Each test builds a tiny situation on an empty board.

Run with:  python -m unittest discover tests
"""
import unittest

from robo_rally.engine import EventBus, EventType, RulesEngine
from robo_rally.model import (BackUpCard, Board, BonusTile, BonusType, Direction, GameState, MoveCard,
                              Position, RobotStatus, Rotation, TurnCard)

E, W, N, S = Direction.EAST, Direction.WEST, Direction.NORTH, Direction.SOUTH


def make_game(tiles=None, robots=None):
    """Empty 12x12 board with checkpoints at (11,0), (11,1), (11,2) unless `tiles` says otherwise.

    tiles:  {(x, y): token}            e.g. {(5, 5): "#"}
    robots: {"R1_E1": (x, y, Direction)}  robots not listed are parked out of the way.
    """
    grid = [["."] * 12 for _ in range(12)]
    for (x, y), token in {(11, 0): "1", (11, 1): "2", (11, 2): "3", **(tiles or {})}.items():
        grid[y][x] = token
    board = Board.from_text("\n".join(" ".join(row) for row in grid))
    state = GameState.new_game(board)
    parking = {"R1_E1": (0, 11), "R2_E1": (2, 11), "R1_E2": (4, 11), "R2_E2": (6, 11)}
    for robot in state.robots():
        x, y, d = (robots or {}).get(robot.id, (*parking[robot.id], N))
        robot.position, robot.direction = Position(x, y), d
    return state, RulesEngine(state)


def pos(state, robot_id):
    return state.robot_by_id(robot_id).position


class TestMoves(unittest.TestCase):
    def test_move_3_on_free_cells(self):
        state, engine = make_game(robots={"R1_E1": (2, 5, E)})
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(3))
        self.assertEqual(pos(state, "R1_E1"), Position(5, 5))

    def test_wall_on_first_cell_means_zero_moves(self):
        state, engine = make_game({(3, 5): "#"}, {"R1_E1": (2, 5, E)})
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(3))
        self.assertEqual(pos(state, "R1_E1"), Position(2, 5))

    def test_wall_on_third_cell_stops_after_two(self):
        state, engine = make_game({(5, 5): "#"}, {"R1_E1": (2, 5, E)})
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(3))
        self.assertEqual(pos(state, "R1_E1"), Position(4, 5))

    def test_hole_eliminates_and_cancels_the_rest(self):
        state, engine = make_game({(3, 5): "O"}, {"R1_E1": (2, 5, E)})
        robot = state.robot_by_id("R1_E1")
        engine.execute_card(robot, MoveCard(3))
        self.assertEqual(robot.status, RobotStatus.ELIMINATED)
        self.assertEqual(robot.position, Position(3, 5))

    def test_leaving_the_board_eliminates(self):
        state, engine = make_game(robots={"R1_E1": (1, 5, W)})
        robot = state.robot_by_id("R1_E1")
        engine.execute_card(robot, MoveCard(3))
        self.assertEqual(robot.status, RobotStatus.ELIMINATED)

    def test_eliminated_robot_plays_nothing(self):
        state, engine = make_game(robots={"R1_E1": (5, 5, E)})
        robot = state.robot_by_id("R1_E1")
        robot.status = RobotStatus.ELIMINATED
        engine.execute_card(robot, MoveCard(1))
        self.assertEqual(robot.position, Position(5, 5))

    def test_back_up_keeps_direction(self):
        state, engine = make_game(robots={"R1_E1": (5, 5, E)})
        robot = state.robot_by_id("R1_E1")
        engine.execute_card(robot, BackUpCard())
        self.assertEqual((robot.position, robot.direction), (Position(4, 5), E))

    def test_turn_cards_only_rotate(self):
        state, engine = make_game({(6, 5): "#"}, {"R1_E1": (5, 5, E)})
        robot = state.robot_by_id("R1_E1")
        engine.execute_card(robot, TurnCard(Rotation.RIGHT))
        self.assertEqual((robot.position, robot.direction), (Position(5, 5), S))
        engine.execute_card(robot, TurnCard(Rotation.U_TURN))
        self.assertEqual(robot.direction, N)
        engine.execute_card(robot, TurnCard(Rotation.LEFT))
        self.assertEqual(robot.direction, W)


class TestPushes(unittest.TestCase):
    def test_push_one_cell(self):
        state, engine = make_game(robots={"R1_E1": (2, 5, E), "R1_E2": (3, 5, N)})
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(1))
        self.assertEqual(pos(state, "R1_E1"), Position(3, 5))
        self.assertEqual(pos(state, "R1_E2"), Position(4, 5))
        self.assertEqual(state.robot_by_id("R1_E2").direction, N)   # pushed robot keeps its direction

    def test_push_into_hole_then_keep_moving(self):
        # The example of the design doc: Move 2 from (3,5), opponent at (5,5), hole at (6,5)
        state, engine = make_game({(6, 5): "O"}, {"R1_E1": (3, 5, E), "R2_E2": (5, 5, N)})
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(2))
        self.assertEqual(state.robot_by_id("R2_E2").status, RobotStatus.ELIMINATED)
        self.assertEqual(pos(state, "R1_E1"), Position(5, 5))

    def test_push_off_the_board(self):
        state, engine = make_game(robots={"R1_E1": (9, 5, E), "R1_E2": (11, 5, N)})
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(2))
        self.assertEqual(state.robot_by_id("R1_E2").status, RobotStatus.ELIMINATED)
        self.assertEqual(pos(state, "R1_E1"), Position(11, 5))

    def test_push_against_wall_stops_both_and_damages(self):
        state, engine = make_game({(5, 5): "#"}, {"R1_E1": (2, 5, E), "R1_E2": (4, 5, N)})
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(3))
        self.assertEqual(pos(state, "R1_E1"), Position(3, 5))
        self.assertEqual(pos(state, "R1_E2"), Position(4, 5))
        self.assertEqual(state.robot_by_id("R1_E2").status, RobotStatus.DAMAGED)

    def test_chain_push(self):
        state, engine = make_game(robots={"R1_E1": (2, 5, E), "R1_E2": (3, 5, N), "R2_E2": (4, 5, N)})
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(1))
        self.assertEqual([pos(state, r) for r in ("R1_E1", "R1_E2", "R2_E2")],
                         [Position(3, 5), Position(4, 5), Position(5, 5)])

    def test_shield_blocks_one_push(self):
        state, engine = make_game(robots={"R1_E1": (2, 5, E), "R1_E2": (3, 5, N)})
        target = state.robot_by_id("R1_E2")
        target.bonuses.append(BonusType.SHIELD)
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(1))
        self.assertEqual(pos(state, "R1_E1"), Position(2, 5))
        self.assertEqual(target.position, Position(3, 5))
        self.assertFalse(target.has_bonus(BonusType.SHIELD))       # used up
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(1))
        self.assertEqual(target.position, Position(4, 5))           # second push works


class TestBonuses(unittest.TestCase):
    def test_bonus_picked_when_stopping_and_used_once(self):
        state, engine = make_game({(4, 5): "S"}, {"R1_E1": (2, 5, E), "R1_E2": (4, 3, S)})
        a, b = state.robot_by_id("R1_E1"), state.robot_by_id("R1_E2")
        engine.execute_card(a, MoveCard(2))
        self.assertEqual(a.bonuses, [BonusType.SHIELD])
        self.assertFalse(state.bonus_available(Position(4, 5)))
        engine.execute_card(a, MoveCard(1))
        engine.execute_card(b, MoveCard(2))
        self.assertEqual(b.bonuses, [])

    def test_passing_over_a_bonus_does_not_pick_it(self):
        state, engine = make_game({(3, 5): "T"}, {"R1_E1": (2, 5, E)})
        robot = state.robot_by_id("R1_E1")
        engine.execute_card(robot, MoveCard(3))
        self.assertEqual(robot.bonuses, [])

    def test_boost_adds_one_cell_on_forward_move_only(self):
        state, engine = make_game(robots={"R1_E1": (5, 5, E)})
        robot = state.robot_by_id("R1_E1")
        robot.bonuses.append(BonusType.BOOST)
        engine.execute_card(robot, BackUpCard())                    # backwards: boost not used
        self.assertEqual(robot.position, Position(4, 5))
        engine.execute_card(robot, MoveCard(1))
        self.assertEqual(robot.position, Position(6, 5))
        self.assertFalse(robot.has_bonus(BonusType.BOOST))

    def test_jump_over_wall_and_hole(self):
        state, engine = make_game({(3, 5): "#", (6, 5): "O"}, {"R1_E1": (2, 5, E)})
        robot = state.robot_by_id("R1_E1")
        robot.bonuses += [BonusType.JUMP, BonusType.JUMP]
        engine.execute_card(robot, MoveCard(1))                     # leaps over the wall
        self.assertEqual(robot.position, Position(4, 5))
        engine.execute_card(robot, MoveCard(2))                     # (5,5) then leaps over the hole
        self.assertEqual(robot.position, Position(7, 5))
        self.assertEqual(robot.status, RobotStatus.ACTIVE)
        self.assertEqual(robot.bonuses, [])

    def test_jump_kept_when_landing_is_unsafe(self):
        state, engine = make_game({(3, 5): "O", (4, 5): "#"}, {"R1_E1": (2, 5, E)})
        robot = state.robot_by_id("R1_E1")
        robot.bonuses.append(BonusType.JUMP)
        engine.execute_card(robot, MoveCard(1))
        self.assertEqual(robot.status, RobotStatus.ELIMINATED)     # no safe landing: normal rules

    def test_repair_kit(self):
        state, engine = make_game({(3, 5): "K"}, {"R1_E1": (2, 5, E)})
        robot = state.robot_by_id("R1_E1")
        robot.status = RobotStatus.DAMAGED
        engine.execute_card(robot, MoveCard(1))
        self.assertEqual(robot.status, RobotStatus.ACTIVE)
        self.assertEqual(robot.bonuses, [])


class TestCheckpoints(unittest.TestCase):
    def test_crossing_counts_in_order(self):
        tiles = {(3, 5): "1", (4, 5): "3", (5, 5): "2", (11, 0): ".", (11, 1): ".", (11, 2): "."}
        state, engine = make_game(tiles, {"R1_E1": (2, 5, E)})
        robot = state.robot_by_id("R1_E1")
        engine.execute_card(robot, MoveCard(3))                     # crosses 1, 3 (too early), 2
        self.assertEqual(robot.next_cp, 3)
        engine.execute_card(robot, BackUpCard())                    # back onto 3
        self.assertTrue(robot.finished())

    def test_pushed_robot_validates_too(self):
        state, engine = make_game({(4, 5): "1", (11, 0): "."}, {"R1_E1": (2, 5, E), "R1_E2": (3, 5, N)})
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(1))
        self.assertEqual(state.robot_by_id("R1_E2").next_cp, 2)


class TestConveyors(unittest.TestCase):
    def test_straight_conveyor(self):
        state, engine = make_game({(5, 5): ">"}, {"R1_E1": (5, 5, N)})
        engine.activate_conveyors()
        self.assertEqual(pos(state, "R1_E1"), Position(6, 5))
        self.assertEqual(state.robot_by_id("R1_E1").direction, N)

    def test_curved_conveyor_moves_and_rotates(self):
        state, engine = make_game({(5, 5): "rv"}, {"R1_E1": (5, 5, E)})
        engine.activate_conveyors()
        robot = state.robot_by_id("R1_E1")
        self.assertEqual((robot.position, robot.direction), (Position(5, 6), S))

    def test_conveyor_into_wall_does_nothing(self):
        state, engine = make_game({(5, 5): ">", (6, 5): "#"}, {"R1_E1": (5, 5, N)})
        engine.activate_conveyors()
        self.assertEqual(pos(state, "R1_E1"), Position(5, 5))

    def test_conveyor_into_hole(self):
        state, engine = make_game({(5, 5): ">", (6, 5): "O"}, {"R1_E1": (5, 5, N)})
        engine.activate_conveyors()
        self.assertEqual(state.robot_by_id("R1_E1").status, RobotStatus.ELIMINATED)

    def test_conveyor_does_not_push(self):
        state, engine = make_game({(5, 5): ">"}, {"R1_E1": (5, 5, N), "R1_E2": (6, 5, N)})
        engine.activate_conveyors()
        self.assertEqual(pos(state, "R1_E1"), Position(5, 5))
        self.assertEqual(pos(state, "R1_E2"), Position(6, 5))

    def test_robots_in_a_row_on_a_belt_all_move(self):
        state, engine = make_game({(4, 5): ">", (5, 5): ">"}, {"R1_E1": (4, 5, N), "R1_E2": (5, 5, N)})
        engine.activate_conveyors()
        self.assertEqual(pos(state, "R1_E1"), Position(5, 5))
        self.assertEqual(pos(state, "R1_E2"), Position(6, 5))

    def test_two_robots_to_the_same_cell_both_stay(self):
        state, engine = make_game({(4, 5): ">", (6, 5): "<"}, {"R1_E1": (4, 5, N), "R1_E2": (6, 5, N)})
        engine.activate_conveyors()
        self.assertEqual(pos(state, "R1_E1"), Position(4, 5))
        self.assertEqual(pos(state, "R1_E2"), Position(6, 5))


class TestVictory(unittest.TestCase):
    def test_team_wins_when_last_robot_finishes(self):
        state, engine = make_game()
        a, b = state.teams[0].robots
        a.next_cp = 4
        self.assertFalse(engine.check_victory())
        b.next_cp = 4
        self.assertTrue(engine.check_victory())
        self.assertIs(state.winner, state.teams[0])

    def test_survivor_can_win_alone(self):
        state, engine = make_game()
        a, b = state.teams[1].robots
        a.status = RobotStatus.ELIMINATED
        b.next_cp = 4
        self.assertTrue(engine.check_victory())
        self.assertIs(state.winner, state.teams[1])

    def test_everyone_eliminated_is_a_draw(self):
        state, engine = make_game()
        for robot in state.robots():
            robot.status = RobotStatus.ELIMINATED
        self.assertTrue(engine.check_victory())
        self.assertIsNone(state.winner)


class TestEvents(unittest.TestCase):
    def test_listeners_receive_events(self):
        state, _ = make_game({(6, 5): "O"}, {"R1_E1": (3, 5, E), "R2_E2": (5, 5, N)})
        bus = EventBus()
        everything, eliminations = [], []
        bus.subscribe(everything.append)
        bus.subscribe(eliminations.append, EventType.ELIMINATED)
        engine = RulesEngine(state, bus)
        engine.execute_card(state.robot_by_id("R1_E1"), MoveCard(2))
        self.assertEqual([e.type for e in everything],
                         [EventType.MOVED, EventType.PUSHED, EventType.ELIMINATED, EventType.MOVED])
        self.assertEqual([e.robot_id for e in eliminations], ["R2_E2"])
        self.assertEqual(engine.events, everything)


if __name__ == "__main__":
    unittest.main()
