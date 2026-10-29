Task H1 (write a recursive-descent expression evaluator from a specification). Role: IMPLEMENTER.
Files to read: tests/test_expr.py. Do not read anything else. Create exactly one new file: expr.py (standard library only).
Specification:
- `evaluate(src: str, env: dict | None = None) -> int | float`.
- Tokens: numbers (`12`, `1.5`), identifiers (`[A-Za-z_][A-Za-z0-9_]*`), operators `+ - * / % ^`, parentheses, commas; spaces are skipped.
- Grammar, lowest to highest precedence: `+ -` (left assoc) < `* / %` (left assoc) < unary minus < `^` (RIGHT assoc).
  So `-2 ^ 2 == -4`, `2 ^ 3 ^ 2 == 512`, `--3 == 3`, and a unary minus may appear after a binary operator (`2 * -3`).
- Primary: number | identifier | identifier `(` args `)` | `(` expr `)`. Functions: `min`, `max` (one or more args), `abs` (exactly one).
- Numeric rules: `/` always returns float. `+ - * %` return int when both operands are int, else float.
  `^` with int base and int exponent >= 0 returns int (use `**`); any other case returns float.
- Errors: class `ParseError(Exception)` with attribute `pos` = index into `src` of the character where parsing
  failed (for unexpected end of input, `pos == len(src)`); it must have a message too. Trailing garbage after a
  complete expression is a ParseError at the position of the first unexpected character. An empty or
  whitespace-only input is a ParseError at `len(src)`. Calling a non-function name like `abs 1` (identifier followed
  by a number) is a ParseError at the number.
- Parse the whole input into a tree first and evaluate afterwards, so parse errors always win over runtime errors.
- class `EvalError(Exception)` for runtime problems: unknown variable, unknown function, wrong number of
  arguments, division or modulo by zero.
Rules: do not edit tests/, no other new files. When done, run `python3 -m pytest -q tests` and reply with its last line.
