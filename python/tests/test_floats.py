"""How literals are stored as doubles, and how sums drift."""

from __future__ import annotations

import math

import pytest

from floating_point_and_money import conformance, floats


def test_point_one_is_not_one_tenth() -> None:
    s = floats.explain("0.1")
    assert s.bits == "3fb999999999999a"
    assert s.exact == "0.1000000000000000055511151231257827021181583404541015625"
    assert s.error == "0.0000000000000000055511151231257827021181583404541015625"
    assert s.ulp == "0.00000000000000001387778780781445675529539585113525390625"


def test_exactly_representable_has_zero_error() -> None:
    assert floats.explain("0.5").error == "0"
    assert floats.explain("100").exact == "100"


def test_integers_above_two_to_the_53_collapse() -> None:
    s = floats.explain("9007199254740993")
    assert s.exact == "9007199254740992"
    assert s.error == "-1"
    assert s.ulp == "2"


def test_negative_literal_keeps_sign_and_positive_ulp() -> None:
    s = floats.explain("-0.1")
    assert s.exact.startswith("-0.1000000000000000055")
    assert not s.ulp.startswith("-")


def test_doubles_vectors_all_agree() -> None:
    score = conformance.doubles()
    assert score.cases == 19
    assert score.failures == []


def test_ops_vectors_all_agree() -> None:
    score = conformance.ops()
    assert score.cases == 13
    assert score.failures == []


def test_sums_vectors_all_agree() -> None:
    score = conformance.sums()
    assert score.cases == 12
    assert score.failures == []


def test_famous_sum() -> None:
    assert 0.1 + 0.2 != 0.3
    assert floats.apply(0.1, "+", 0.2) == 0.30000000000000004
    assert floats.true_result("0.1", "+", "0.2") == floats.true_result("0.3", "*", "1")


def test_naive_sum_of_ten_tenths_misses_one() -> None:
    assert floats.naive_sum(0.1, 10) == 0.9999999999999999
    assert floats.kahan_sum(0.1, 10) == 1.0
    assert floats.sum_error(floats.naive_sum(0.1, 10), "0.1", 10).startswith(
        "-0.000000000000000111"
    )


def test_kahan_differs_from_naive_only_by_compensation() -> None:
    assert floats.kahan_sum(0.5, 4) == floats.naive_sum(0.5, 4) == 2.0
    assert floats.naive_sum(0.1, 0) == floats.kahan_sum(0.1, 0) == 0.0


def test_sum_error_of_exact_total_is_zero() -> None:
    assert floats.sum_error(1.0, "0.25", 4) == "0"


@pytest.mark.parametrize(
    "bad",
    [
        "",
        " 1",
        "1 ",
        "+1",
        "1e3",
        ".5",
        "5.",
        "0x10",
        "NaN",
        "inf",
        "1,0",
        "\u0661\u0662",
        "1" * 401,
    ],
)
def test_parse_literal_rejects_other_forms(bad: str) -> None:
    with pytest.raises(ValueError, match="plain decimal literal"):
        floats.parse_literal(bad)


def test_parse_literal_rejects_overflow() -> None:
    with pytest.raises(ValueError, match="overflows"):
        floats.parse_literal("1" + "0" * 309)


def test_parse_literal_rejects_non_str() -> None:
    with pytest.raises(TypeError):
        floats.parse_literal(0.1)  # type: ignore[arg-type]


@pytest.mark.parametrize("x", [math.nan, math.inf, -math.inf])
def test_non_finite_has_no_exact_value(x: float) -> None:
    with pytest.raises(ValueError, match="no exact decimal"):
        floats.exact(x)
    with pytest.raises(ValueError, match="no exact decimal"):
        floats.bits(x)


def test_bits_rejects_int() -> None:
    with pytest.raises(TypeError):
        floats.bits(1)


def test_unknown_op() -> None:
    with pytest.raises(ValueError, match="unknown op"):
        floats.apply(1.0, "/", 2.0)
    with pytest.raises(ValueError, match="unknown op"):
        floats.true_result("1", "/", "2")


@pytest.mark.parametrize("n", [-1, floats.MAX_TERMS + 1])
def test_sum_count_out_of_range(n: int) -> None:
    with pytest.raises(ValueError, match="n must be in"):
        floats.naive_sum(0.1, n)
    with pytest.raises(ValueError, match="n must be in"):
        floats.kahan_sum(0.1, n)


def test_sum_count_must_be_int() -> None:
    with pytest.raises(TypeError):
        floats.naive_sum(0.1, True)
    with pytest.raises(TypeError):
        floats.kahan_sum(0.1, 2.0)  # type: ignore[arg-type]


def test_plain_drops_negative_zero_and_trailing_zeros() -> None:
    from decimal import Decimal

    assert floats.plain(Decimal("-0.000")) == "0"
    assert floats.plain(Decimal("1.2500")) == "1.25"
    assert floats.plain(Decimal("1E+3")) == "1000"
