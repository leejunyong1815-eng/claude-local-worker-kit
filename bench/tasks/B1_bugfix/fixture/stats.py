"""Small statistics helpers (pure Python, no dependencies)."""


def mean(xs):
    """Arithmetic mean. Raises ValueError on empty input."""
    if not xs:
        raise ValueError("mean of empty sequence")
    return sum(xs) / len(xs)


def median(xs):
    """Median of a sequence of numbers.

    For an odd count return the middle element; for an even count return the
    average of the two middle elements. Raises ValueError on empty input.
    The input must not be modified.
    """
    s = sorted(xs)
    n = len(s)
    return s[n // 2]


def variance(xs):
    """Population variance (divide by n). Raises ValueError on empty input."""
    m = mean(xs)
    return sum((x - m) ** 2 for x in xs) / len(xs)
