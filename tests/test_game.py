"""Tests for the turn loop (engine/game.py)."""
import random
import unittest
from pathlib import Path

from robo_rally import config
from robo_rally.ai import HumanStrategy, RandomStrategy
from robo_rally.engine import EventType, Game
from robo_rally.engine.game import CardPhase, DrawPhase, ProgrammingPhase
from robo_rally.model import Board, RobotStatus

LEVEL1 = Path(__file__).parent.parent / "maps" / "level1.txt"


def random_game(seed=1):
    board = Board.from_file(LEVEL1)
    return Game(board, {1: RandomStrategy(random.Random(seed)), 2: RandomStrategy(random.Random(seed + 1))},
                seed=seed)


class TestTurnLoop(unittest.TestCase):
    def test_phases_follow_each_other(self):
        game = random_game()
        self.assertIsInstance(game.phase, DrawPhase)
        game.step()
        self.assertIsInstance(game.phase, ProgrammingPhase)
        self.assertEqual(game.state.turn, 1)
        self.assertTrue(all(len(h) == config.HAND_SIZE for h in game.hands.values()))
        game.step()
        self.assertIsInstance(game.phase, CardPhase)
        self.assertTrue(all(len(r.program) == 3 for r in game.state.robots()))

    def test_one_step_plays_one_card(self):
        game = random_game()
        game.step()
        game.step()
        played = []
        game.bus.subscribe(played.append, EventType.CARD_PLAYED)
        game.step()
        self.assertEqual(len(played), 1)

    def test_play_order_alternates_teams(self):
        game = random_game()
        game.step()
        order = [r.id for r in game.play_order()]
        self.assertEqual([r[-2:] for r in order], [order[0][-2:], order[1][-2:]] * 2)   # E1 E2 E1 E2 or E2 E1 E2 E1
        self.assertNotEqual(order[0][-2:], order[1][-2:])
        self.assertEqual(order, [r.id for r in game.play_order()])                        # fixed for the turn

    def test_first_team_is_drawn_fairly(self):
        firsts = []
        for seed in range(200):
            game = random_game(seed)
            game.step()
            firsts.append(game.play_order()[0].team_id)
        self.assertTrue(70 < firsts.count(1) < 130)

    def test_play_turn_stops_at_the_next_turn(self):
        game = random_game(3)
        game.play_turn()
        self.assertTrue(game.state.over or isinstance(game.phase, DrawPhase))
        self.assertEqual(game.state.turn, 1)

    def test_games_always_end(self):
        for seed in range(30):
            state = random_game(seed).play_to_end()
            self.assertTrue(state.over)
            self.assertLessEqual(state.turn, config.MAX_TURNS)

    def test_no_card_is_lost(self):
        game = random_game(5)
        for _ in range(4):
            game.play_turn()
        for deck in game.decks.values():
            self.assertEqual(len(deck), 20)

    def test_same_seed_same_game(self):
        a, b = random_game(9).play_to_end(), random_game(9).play_to_end()
        self.assertEqual([(r.position, r.status) for r in a.robots()], [(r.position, r.status) for r in b.robots()])

    def test_damaged_robot_plays_two_cards(self):
        game = random_game()
        game.step()
        robot = game.state.robot_by_id("R1_E1")
        robot.status = RobotStatus.DAMAGED
        self.assertEqual(game.program_size(robot), 2)


class TestHumanPlayer(unittest.TestCase):
    def setUp(self):
        self.game = Game(Board.from_file(LEVEL1), {1: HumanStrategy(), 2: RandomStrategy(random.Random(0))}, seed=0)
        self.game.step()                        # draw

    def test_game_waits_for_the_person(self):
        self.assertEqual([r.id for r in self.game.waiting_for()], ["R1_E1", "R2_E1"])
        self.assertFalse(self.game.step())      # cannot go on
        self.assertTrue(self.game.state.robot_by_id("R1_E2").program)   # but the AI already chose

    def test_submit_program_lets_the_game_continue(self):
        for robot in self.game.waiting_for():
            self.game.submit_program(robot.id, self.game.hands[robot.id][:3])
        self.assertEqual(self.game.waiting_for(), [])
        self.assertTrue(self.game.step())
        self.assertIsInstance(self.game.phase, CardPhase)

    def test_wrong_program_is_refused(self):
        hand = self.game.hands["R1_E1"]
        with self.assertRaises(ValueError):
            self.game.submit_program("R1_E1", hand[:2])                    # too few
        with self.assertRaises(ValueError):
            self.game.submit_program("R1_E1", self.game.hands["R2_E1"][:3])   # not its cards


if __name__ == "__main__":
    unittest.main()
