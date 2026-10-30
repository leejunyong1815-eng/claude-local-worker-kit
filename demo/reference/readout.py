"""Offline rehearsal solution. Not copied into the live demo workspace."""
import math
from numbers import Real


def distribution_fidelity(counts, probabilities):
    if not counts or len(counts) != len(probabilities):
        raise ValueError("shape mismatch")
    if any(not isinstance(x, int) or isinstance(x, bool) or x < 0 for x in counts) or sum(counts) <= 0:
        raise ValueError("nonnegative integer counts with positive total required")
    if any(not isinstance(p, Real) or isinstance(p, bool) or not math.isfinite(p) or p < 0 for p in probabilities):
        raise ValueError("invalid probability")
    if not math.isclose(math.fsum(probabilities), 1.0, rel_tol=0, abs_tol=1e-10):
        raise ValueError("probabilities must sum to one")
    total = sum(counts)
    value = math.fsum(math.sqrt((c / total) * p) for c, p in zip(counts, probabilities)) ** 2
    return min(1.0, max(0.0, value))
