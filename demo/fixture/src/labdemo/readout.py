"""Task B: distribution fidelity, not signed quantum-state fidelity."""


def distribution_fidelity(counts, probabilities):
    """Return (sum(sqrt((count_i / total) * probability_i))) ** 2.

    Inputs are nonempty equal-length sequences. Counts must be nonnegative ints
    (not bools), with positive total. Probabilities must be finite nonnegative
    real numbers (not bools) summing to 1 within absolute tolerance 1e-10.
    Raise ValueError for invalid input. Do not mutate inputs. Clamp only the
    final floating-point result to [0, 1]. This quantity ignores amplitude signs
    and phases and must NOT be reported as quantum-state fidelity.
    """
    raise NotImplementedError("Task B: implement distribution_fidelity")
