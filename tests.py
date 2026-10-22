import random
import unittest

import main


class PocketCubeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solver = main.PocketCubeSolver()

    def apply_sticker_notation(self, stickers, move):
        quarter = main._build_sticker_permutation(move.face)
        power = 2 if move.name.endswith("2") else 3 if move.name.endswith("'") else 1
        composed = tuple(range(24))
        for _ in range(power):
            composed = tuple(quarter[composed[src]] for src in range(24))
        return main.apply_sticker_move(stickers, composed)

    def test_all_moves_and_inverse_restore_solved_state(self):
        for face in main.FACE_ORDER:
            state = main.apply_moves((main.SOLVED_PERM, main.SOLVED_ORI), [main.MOVE_BY_NAME[face], main.MOVE_BY_NAME[face + "'"]])
            self.assertEqual(state, (main.SOLVED_PERM, main.SOLVED_ORI))

    def test_cubie_moves_match_sticker_moves(self):
        rng = random.Random(42)
        for _ in range(100):
            stickers = main.SOLVED_STICKERS
            state = (main.SOLVED_PERM, main.SOLVED_ORI)
            for _ in range(rng.randint(0, 20)):
                move = rng.choice(main.MOVES)
                stickers = self.apply_sticker_notation(stickers, move)
                state = main.apply_move(state, move)
            self.assertEqual(main.decode_stickers(stickers), state)

    def test_rank_and_unrank_round_trip(self):
        for rank in (0, 1, 7, 89, 1000, 20160, 40319):
            self.assertEqual(main.permutation_rank(main.permutation_unrank(rank)), rank)

    def test_solver_solves_scrambles(self):
        rng = random.Random(99)
        for length in (0, 1, 2, 4, 7, 9, 12):
            scramble = main.random_scramble(length, rng)
            start = main.apply_moves((main.SOLVED_PERM, main.SOLVED_ORI), scramble)
            solution, _, _ = self.solver.solve(start)
            self.assertTrue(main.verify_solution(start, solution))

    def test_manual_sticker_encoding_round_trip(self):
        rng = random.Random(777)
        for _ in range(50):
            state = (main.SOLVED_PERM, main.SOLVED_ORI)
            for _ in range(rng.randint(0, 15)):
                state = main.apply_move(state, rng.choice(main.MOVES))
            self.assertEqual(main.decode_stickers(main.encode_stickers(*state)), state)

    def test_bad_twist_sum_is_rejected(self):
        stickers = list(main.SOLVED_STICKERS)
        stickers[0:3] = [main.SOLVED_STICKERS[1], main.SOLVED_STICKERS[2], main.SOLVED_STICKERS[0]]
        with self.assertRaises(ValueError):
            main.decode_stickers(tuple(stickers))


if __name__ == "__main__":
    unittest.main(verbosity=2)
