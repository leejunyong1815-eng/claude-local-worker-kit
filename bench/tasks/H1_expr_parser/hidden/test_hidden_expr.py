import pytest
from expr import evaluate, ParseError, EvalError


@pytest.mark.parametrize("src,pos", [("", 0), ("   ", 3), ("1 +", 3), ("(1 + 2", 6), ("1 2", 2), ("2 ^", 3),
                                     ("max(1,)", 6), ("1 + $", 4), ("abs 1", 4), ("1 ) ", 2)])
def test_parse_error_positions(src, pos):
    with pytest.raises(ParseError) as e:
        evaluate(src)
    assert e.value.pos == pos


def test_nested_calls_and_unary_chain():
    assert evaluate("max(min(4, 9), abs(-7), 2)") == 7
    assert evaluate("--3") == 3
    assert evaluate("2 * -3") == -6


def test_int_float_rules():
    assert evaluate("2 ^ 10") == 1024 and isinstance(evaluate("2 ^ 10"), int)
    assert isinstance(evaluate("2 ^ -1"), float) and evaluate("2 ^ -1") == 0.5
    assert isinstance(evaluate("2 ^ 0.5"), float)
    assert evaluate("1.5 + 1") == 2.5
    assert evaluate("10 % 4 * 2") == 4


def test_function_arity_and_unknown_function():
    with pytest.raises(EvalError):
        evaluate("abs(1, 2)")
    with pytest.raises(EvalError):
        evaluate("foo(1)")
    with pytest.raises(EvalError):
        evaluate("5 % 0")


def test_env_not_required_and_identifier_chars():
    assert evaluate("x_1 + y2", {"x_1": 1, "y2": 2}) == 3
    assert evaluate("3") == 3
