"""Experiments: how a decimal literal is stored as a double, and how errors grow in sums."""

from __future__ import annotations

import math
import re
import struct
from dataclasses import dataclass
from decimal import Context, Decimal, Inexact

MAX_LITERAL = 400  # characters; longer plain literals overflow a double anyway
LITERAL = re.compile(r"-?[0-9]+(\.[0-9]+)?")
MAX_TERMS = 10_000_000

# Enough digits for any exact binary64 value or difference; Inexact is trapped, so never rounds.
_EXACT = Context(prec=2_000, traps=[Inexact])


@dataclass(frozen=True)
class Stored:
    """What one decimal literal becomes as a double."""

    input: str
    bits: str
    exact: str
    ulp: str
    error: str


def parse_literal(text: str) -> float:
    """Plain decimal literal to the nearest double; rejects other forms and overflow."""
    if not isinstance(text, str):
        raise TypeError(f"literal must be str, not {type(text).__name__}")
    if len(text) > MAX_LITERAL or not LITERAL.fullmatch(text):
        raise ValueError(f"not a plain decimal literal: {text[:40]!r}")
    x = float(text)
    if not math.isfinite(x):
        raise ValueError(f"{text[:40]} overflows a double")
    return x


def plain(value: Decimal) -> str:
    """Decimal as plain text without exponent or trailing zeros."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("0", "-0") else text


def _finite(x: float) -> float:
    """Reject NaN and infinities, which have no exact decimal value."""
    if not isinstance(x, float):
        raise TypeError(f"expected float, not {type(x).__name__}")
    if not math.isfinite(x):
        raise ValueError(f"{x} has no exact decimal value")
    return x


def bits(x: float) -> str:
    """IEEE 754 binary64 bit pattern as 16 hex digits."""
    return struct.pack(">d", _finite(x)).hex()


def exact(x: float) -> str:
    """Exact decimal value of the double x."""
    return plain(Decimal(_finite(x)))


def ulp(x: float) -> str:
    """Exact gap between |x| and the next larger double."""
    return plain(Decimal(math.ulp(_finite(x))))


def explain(text: str) -> Stored:
    """Bits, exact stored value, ulp and representation error of a literal."""
    x = parse_literal(text)
    error = _EXACT.subtract(Decimal(x), Decimal(text))
    return Stored(text, bits(x), exact(x), ulp(x), plain(error))


def apply(a: float, op: str, b: float) -> float:
    """One double operation: +, - or *."""
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    raise ValueError(f"unknown op {op!r}")


def true_result(a: str, op: str, b: str) -> Decimal:
    """Exact decimal result of a op b on the literals."""
    da, db = Decimal(a), Decimal(b)
    if op == "+":
        return _EXACT.add(da, db)
    if op == "-":
        return _EXACT.subtract(da, db)
    if op == "*":
        return _EXACT.multiply(da, db)
    raise ValueError(f"unknown op {op!r}")


def _terms(n: int) -> int:
    """Validate a repetition count."""
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be int")
    if not 0 <= n <= MAX_TERMS:
        raise ValueError(f"n must be in 0..{MAX_TERMS}")
    return n


def naive_sum(x: float, n: int) -> float:
    """Add x to a running double total n times."""
    total = 0.0
    for _ in range(_terms(n)):
        total += x
    return total


def kahan_sum(x: float, n: int) -> float:
    """Add x n times with Kahan's compensated summation."""
    total = 0.0
    comp = 0.0
    for _ in range(_terms(n)):
        y = x - comp
        t = total + y
        comp = (t - total) - y
        total = t
    return total


def sum_error(total: float, summand: str, n: int) -> str:
    """Exact signed error of a double total against n times the literal."""
    target = _EXACT.multiply(Decimal(summand), Decimal(n))
    return plain(_EXACT.subtract(Decimal(_finite(total)), target))
