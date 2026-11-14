"""Run this package against the shared vectors and count what agrees."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import floats
from .money import CURRENCIES, Money, MoneyError
from .vectors import load


@dataclass
class Score:
    """Cases checked and the ones that disagreed."""

    suite: str
    cases: int = 0
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> int:
        """Cases that agreed."""
        return self.cases - len(self.failures)

    def check(self, label: str, got: object, want: object) -> None:
        """Count one case; record it when got differs from want."""
        self.cases += 1
        if got != want:
            self.failures.append(f"{label}: got {got!r}, want {want!r}")


def doubles(directory: Path | None = None) -> Score:
    """Bits, exact value, ulp and error of each literal."""
    score = Score("doubles")
    for row in load("doubles.tsv", directory):
        s = floats.explain(row[0])
        score.check(row[0], [s.bits, s.exact, s.ulp, s.error], row[1:])
    return score


def ops(directory: Path | None = None) -> Score:
    """Each float operation, its equality with the true result, and the money result."""
    score = Score("ops")
    for a, op, b, want_bits, want_exact, want_same, want_money in load("ops.tsv", directory):
        x = floats.apply(floats.parse_literal(a), op, floats.parse_literal(b))
        true = floats.true_result(a, op, b)
        same = "true" if x == float(true) else "false"
        cash = money_op(Money.parse(a, "USD"), op, b)
        got = [floats.bits(x), floats.exact(x), same, cash.amount()]
        score.check(f"{a} {op} {b}", got, [want_bits, want_exact, want_same, want_money])
    return score


def money_op(a: Money, op: str, b: str) -> Money:
    """The ops table's operation done with Money (b is an integer for *)."""
    if op == "*":
        return a.times(int(b))
    other = Money.parse(b, a.currency)
    return a.plus(other) if op == "+" else a.minus(other)


def sums(directory: Path | None = None) -> Score:
    """Naive and Kahan totals and their exact errors."""
    score = Score("sums")
    for summand, n_text, *want in load("sums.tsv", directory):
        x, n = floats.parse_literal(summand), int(n_text)
        naive, kahan = floats.naive_sum(x, n), floats.kahan_sum(x, n)
        got = [
            floats.bits(naive),
            floats.sum_error(naive, summand, n),
            floats.bits(kahan),
            floats.sum_error(kahan, summand, n),
        ]
        score.check(f"{summand} x {n}", got, want)
    return score


def money_case(op: str, a: str, a_cur: str, b: str, b_cur: str) -> str:
    """Result of one money.tsv row as text, or error:<kind>."""
    try:
        if op == "ofminor":
            return str(Money.of_minor(int(a), a_cur))
        x = Money.parse(a, a_cur)
        if op == "parse":
            return str(x)
        if op == "minor":
            return str(x.minor)
        if op == "negate":
            return str(x.negate())
        if op == "times":
            return str(x.times(int(b)))
        y = Money.parse(b, b_cur)
        if op == "plus":
            return str(x.plus(y))
        if op == "minus":
            return str(x.minus(y))
        if op == "compare":
            return str(x.compare(y))
    except MoneyError as exc:
        return f"error:{exc.kind}"
    raise ValueError(f"unknown money op {op!r}")


def money(directory: Path | None = None) -> Score:
    """Every shared Money case."""
    score = Score("money")
    for op, a, a_cur, b, b_cur, want in load("money.tsv", directory):
        score.check(f"{op} {a} {a_cur} {b} {b_cur}", money_case(op, a, a_cur, b, b_cur), want)
    return score


def currencies(directory: Path | None = None) -> Score:
    """The built-in currency table equals currencies.tsv."""
    score = Score("currencies")
    rows = load("currencies.tsv", directory)
    score.check("codes", sorted(CURRENCIES), sorted(code for code, _ in rows))
    for code, digits in rows:
        score.check(code, CURRENCIES.get(code), int(digits))
    return score


SUITES = (doubles, ops, sums, money, currencies)


def report(directory: Path | None = None) -> list[Score]:
    """Every suite's score."""
    return [suite(directory) for suite in SUITES]
