"""Money in integer minor units: shared cases, refusals and seeded random invariants."""

from __future__ import annotations

import random
from decimal import Decimal

import pytest

from floating_point_and_money import conformance
from floating_point_and_money.money import CURRENCIES, MAX_MINOR, Money, MoneyError
from floating_point_and_money.vectors import load

CASES = load("money.tsv")


@pytest.mark.parametrize(("op", "a", "a_cur", "b", "b_cur", "want"), CASES)
def test_shared_case(op: str, a: str, a_cur: str, b: str, b_cur: str, want: str) -> None:
    assert conformance.money_case(op, a, a_cur, b, b_cur) == want


def test_shared_cases_cover_every_error_kind() -> None:
    kinds = {row[5] for row in CASES if row[5].startswith("error:")}
    assert kinds == {"error:parse", "error:currency", "error:overflow", "error:mismatch"}


def test_currency_table_matches_shared_file() -> None:
    assert conformance.currencies().failures == []


def test_floats_are_refused() -> None:
    with pytest.raises(TypeError, match="floats are not money"):
        Money.parse(0.1, "USD")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Money.of_minor(10.0, "USD")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Money.parse("1.00", "USD").times(1.5)  # type: ignore[arg-type]


def test_bools_are_not_ints() -> None:
    with pytest.raises(TypeError):
        Money.of_minor(True, "USD")
    with pytest.raises(TypeError):
        Money.parse("1.00", "USD").times(True)


def test_currency_must_be_str() -> None:
    with pytest.raises(TypeError):
        Money.parse("1", None)  # type: ignore[arg-type]


def test_direct_construction_is_validated() -> None:
    with pytest.raises(MoneyError) as exc:
        Money(MAX_MINOR + 1, "USD")
    assert exc.value.kind == "overflow"
    with pytest.raises(MoneyError) as cur:
        Money(1, "ABC")
    assert cur.value.kind == "currency"


def test_overlong_text_is_a_parse_error() -> None:
    with pytest.raises(MoneyError) as exc:
        Money.parse("1" * 65, "USD")
    assert exc.value.kind == "parse"


def test_empty_text_is_a_parse_error() -> None:
    with pytest.raises(MoneyError) as exc:
        Money.parse("", "USD")
    assert exc.value.kind == "parse"


def test_operators_match_methods() -> None:
    a, b = Money.parse("0.10", "USD"), Money.parse("0.20", "USD")
    assert a + b == a.plus(b) == Money.parse("0.30", "USD")
    assert b - a == Money.parse("0.10", "USD")
    assert a * 3 == Money.parse("0.30", "USD")
    assert -a == Money.parse("-0.10", "USD")
    assert a < b <= b
    assert b > a >= a


def test_ordering_across_currencies_is_refused() -> None:
    with pytest.raises(MoneyError):
        assert Money.parse("1", "USD") < Money.parse("1", "EUR")


def test_plus_rejects_non_money() -> None:
    with pytest.raises(TypeError):
        Money.parse("1", "USD").plus(1)  # type: ignore[arg-type]


def test_equality_includes_currency() -> None:
    assert Money.of_minor(100, "USD") != Money.of_minor(100, "EUR")
    assert hash(Money.of_minor(5, "JPY")) == hash(Money.parse("5", "JPY"))


def test_total_of_ten_dimes_is_one_dollar() -> None:
    dime = Money.parse("0.10", "USD")
    assert str(Money.total([dime] * 10, "USD")) == "1.00 USD"
    assert str(Money.total([], "KWD")) == "0.000 KWD"
    with pytest.raises(MoneyError):
        Money.total([dime], "EUR")


def _random_money(rng: random.Random, currency: str) -> Money:
    """Amount spread over small and huge magnitudes."""
    bound = 10 ** rng.randint(0, 18)
    return Money.of_minor(rng.randint(-min(bound, MAX_MINOR), min(bound, MAX_MINOR)), currency)


@pytest.mark.parametrize("currency", sorted(CURRENCIES))
def test_random_invariants(currency: str) -> None:
    rng = random.Random(20261114)  # noqa: S311 - seeded test data, not security
    scale = Decimal(10) ** -CURRENCIES[currency]
    for _ in range(2_000):
        a, b = _random_money(rng, currency), _random_money(rng, currency)
        assert Money.parse(a.amount(), currency) == a
        assert Decimal(a.amount()) == a.minor * scale
        assert a.compare(b) == -b.compare(a)
        if abs(a.minor + b.minor) > MAX_MINOR:
            with pytest.raises(MoneyError, match="64-bit"):
                a.plus(b)
            continue
        total = a.plus(b)
        assert Decimal(total.amount()) == Decimal(a.amount()) + Decimal(b.amount())
        assert total.minus(b) == a
