import pytest
from expr import evaluate, ParseError, EvalError


def test_precedence():
    assert evaluate("1 + 2 * 3") == 7
    assert evaluate("(1 + 2) * 3") == 9


def test_power_right_assoc_and_unary():
    assert evaluate("2 ^ 3 ^ 2") == 512
    assert evaluate("-2 ^ 2") == -4
    assert evaluate("(-2) ^ 2") == 4


def test_division_is_float_and_modulo():
    assert evaluate("7 / 2") == 3.5
    assert evaluate("7 % 3") == 1
    assert isinstance(evaluate("6 / 3"), float)


def test_variables_and_functions():
    assert evaluate("max(a, 2 * b, 3)", {"a": 1, "b": 2}) == 4
    assert evaluate("abs(-x)", {"x": 5}) == 5
    assert evaluate("min(1)") == 1


def test_parse_error_position():
    with pytest.raises(ParseError) as e:
        evaluate("1 + * 2")
    assert e.value.pos == 4


def test_eval_errors():
    with pytest.raises(EvalError):
        evaluate("1 / 0")
    with pytest.raises(EvalError):
        evaluate("y + 1", {})
