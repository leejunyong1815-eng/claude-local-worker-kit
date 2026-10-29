"""Duration string parsing."""


def parse_duration(s: str) -> int:
    """Parse a human duration string into a number of seconds.

    Grammar: one or more components ``<integer><unit>`` with unit one of
    ``d`` (86400 s), ``h`` (3600 s), ``m`` (60 s), ``s`` (1 s). Components may
    appear in any order and may be separated by spaces, e.g. ``"1h30m"``,
    ``"30m 1h"``, ``"2d"``, ``"45s"``. Leading/trailing whitespace is ignored.
    The string ``"0"`` (no unit) means 0 seconds.

    Raise ``ValueError`` for: empty string, unknown unit, non-integer numbers
    (``"1.5h"``), a unit used twice (``"1h2h"``), or a number without a unit
    other than the special ``"0"``.
    """
    raise NotImplementedError
