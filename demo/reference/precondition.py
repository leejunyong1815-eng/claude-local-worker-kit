"""Offline rehearsal solution. Not copied into the live demo workspace."""
import math
from numbers import Real


def row_scale(matrix, rhs):
    n = len(matrix)
    if not n or len(rhs) != n or any(len(row) != n for row in matrix):
        raise ValueError("shape mismatch")
    def finite(value):
        return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)
    if not all(finite(value) for row in matrix for value in row) or not all(finite(v) for v in rhs):
        raise ValueError("finite real numbers required")
    scales = [max(abs(x) for x in row) for row in matrix]
    if any(s == 0 for s in scales):
        raise ValueError("zero row")
    return ([[float(x / scale) for x in row] for row, scale in zip(matrix, scales)],
            [float(x / scale) for x, scale in zip(rhs, scales)])
