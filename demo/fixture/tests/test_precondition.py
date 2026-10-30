import copy
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labdemo.precondition import row_scale


class RowScaleTests(unittest.TestCase):
    def test_known_scaling(self):
        self.assertEqual(row_scale([[4, -1], [-10, 40]], [2, 20]),
                         ([[1.0, -0.25], [-0.25, 1.0]], [0.5, 0.5]))

    def test_no_mutation(self):
        matrix, rhs = [[-2, 1], [1, 3]], [5, 6]
        before = copy.deepcopy((matrix, rhs))
        scaled, b = row_scale(matrix, rhs)
        self.assertEqual((matrix, rhs), before)
        self.assertIsNot(scaled, matrix)
        self.assertIsNot(scaled[0], matrix[0])
        self.assertIsNot(b, rhs)

    def test_negative_entries_use_absolute_max(self):
        self.assertEqual(row_scale([[-8, 2], [1, -4]], [16, -8]),
                         ([[-1, 0.25], [0.25, -1]], [2, -2]))

    def test_tuple_inputs(self):
        self.assertEqual(row_scale(((2,),), (6,)), ([[1.0]], [3.0]))

    def test_bad_shapes(self):
        for matrix, rhs in (([], []), ([[1, 2]], [1]), ([[1]], []), ([[1], [2]], [1, 2])):
            with self.subTest(matrix=matrix), self.assertRaises(ValueError):
                row_scale(matrix, rhs)

    def test_zero_row(self):
        with self.assertRaises(ValueError):
            row_scale([[1, 0], [0, 0]], [1, 0])

    def test_invalid_numbers(self):
        for bad in (True, "x", None, math.inf, math.nan):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                row_scale([[bad]], [1])
            with self.subTest(rhs=bad), self.assertRaises(ValueError):
                row_scale([[1]], [bad])


if __name__ == "__main__":
    unittest.main()
