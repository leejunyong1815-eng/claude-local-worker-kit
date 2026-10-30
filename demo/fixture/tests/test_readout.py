import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labdemo.readout import distribution_fidelity


class ReadoutTests(unittest.TestCase):
    def test_exact_distribution(self):
        self.assertAlmostEqual(distribution_fidelity([1, 3], [0.25, 0.75]), 1.0)

    def test_disjoint_distributions(self):
        self.assertEqual(distribution_fidelity([10, 0], [0.0, 1.0]), 0.0)

    def test_known_overlap(self):
        self.assertAlmostEqual(distribution_fidelity([10, 0], [0.5, 0.5]), 0.5)

    def test_no_mutation(self):
        counts, probabilities = [1, 2, 3], [0.2, 0.3, 0.5]
        before = (counts[:], probabilities[:])
        value = distribution_fidelity(counts, probabilities)
        self.assertTrue(0 <= value <= 1)
        self.assertEqual((counts, probabilities), before)

    def test_shape_and_empty(self):
        for counts, probabilities in (([], []), ([1], [0.5, 0.5]), ([1, 2], [1])):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                distribution_fidelity(counts, probabilities)

    def test_invalid_counts(self):
        for counts in ([0, 0], [-1, 3], [1.0, 2], [True, 2]):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                distribution_fidelity(counts, [0.5, 0.5])

    def test_invalid_probabilities(self):
        for probabilities in ([-0.1, 1.1], [0.2, 0.2], [math.nan, 1], [math.inf, 0], [True, 0]):
            with self.subTest(probabilities=probabilities), self.assertRaises(ValueError):
                distribution_fidelity([1, 2], probabilities)

    def test_zero_bin_and_roundoff(self):
        self.assertAlmostEqual(distribution_fidelity([0, 7], [0.0, 1.0]), 1.0)
        value = distribution_fidelity([1, 1], [0.5, 0.500000000001])
        self.assertLessEqual(value, 1.0)


if __name__ == "__main__":
    unittest.main()
