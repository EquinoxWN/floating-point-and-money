"""Command line output and exit codes; the vector generator and its drift check."""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

import generate_vectors as gen
import pytest

from floating_point_and_money.cli import main
from floating_point_and_money.vectors import default_dir


def test_explain(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["explain", "0.1"]) == 0
    out = capsys.readouterr().out
    assert "bits\t3fb999999999999a" in out
    assert "exact\t0.1000000000000000055511151231257827021181583404541015625" in out


def test_explain_rejects_bad_literal(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["explain", "1e3"]) == 1
    assert "error: not a plain decimal literal" in capsys.readouterr().err


def test_ops(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ops"]) == 0
    out = capsys.readouterr().out
    assert "0.1 + 0.2\t0.30000000000000004\tfalse\t0.30 USD" in out
    assert "19.99 * 100\t1998.9999999999998\tfalse\t1999.00 USD" in out


def test_sums(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["sums"]) == 0
    assert (
        "0.1\t10\t0.9999999999999999\t-0.00000000000000011102230246251565404236316680908203125\t0\n"
        in (capsys.readouterr().out)
    )


def test_report(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["report"]) == 0
    out = capsys.readouterr().out
    assert "python\tmoney\t78\t78" in out
    assert "python\tdoubles\t19\t19" in out


def test_report_fails_on_wrong_vectors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    for f in default_dir().glob("*.tsv"):
        (tmp_path / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    money = tmp_path / "money.tsv"
    money.write_text(
        money.read_text(encoding="utf-8").replace("12.34 USD\n", "12.35 USD\n", 1), encoding="utf-8"
    )
    assert main(["--vectors", str(tmp_path), "report"]) == 1
    assert "python\tmoney\t77\t78" in capsys.readouterr().out


def test_missing_vectors_dir(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--vectors", str(tmp_path / "nope"), "ops"]) == 1
    assert "error:" in capsys.readouterr().err


def test_committed_vectors_are_current() -> None:
    assert gen.main(["--check"]) == 0


def test_check_detects_drift_and_write_repairs_it(tmp_path: Path) -> None:
    assert gen.main(["--check", "--out", str(tmp_path)]) == 1
    assert gen.main(["--out", str(tmp_path)]) == 0
    assert gen.main(["--check", "--out", str(tmp_path)]) == 0
    assert sorted(p.name for p in tmp_path.iterdir()) == ["doubles.tsv", "ops.tsv", "sums.tsv"]


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (Fraction(1, 10), "0.1"),
        (Fraction(-3, 8), "-0.375"),
        (Fraction(0), "0"),
        (Fraction(12), "12"),
        (Fraction(1, 2**3) - Fraction(1, 10), "0.025"),
    ],
)
def test_exact_decimal(value: Fraction, text: str) -> None:
    assert gen.exact_decimal(value) == text


def test_exact_decimal_rejects_thirds() -> None:
    with pytest.raises(ValueError, match="no finite decimal"):
        gen.exact_decimal(Fraction(1, 3))


def test_money_column_must_be_whole_cents() -> None:
    assert gen.money(Fraction(-7, 100)) == "-0.07"
    with pytest.raises(ValueError, match="cents"):
        gen.money(Fraction(1, 1000))


def test_write_atomic_replaces_whole_file(tmp_path: Path) -> None:
    target = tmp_path / "x.tsv"
    gen.write_atomic(target, "a\n")
    gen.write_atomic(target, "b\n")
    assert target.read_text(encoding="utf-8") == "b\n"
    assert [p.name for p in tmp_path.iterdir()] == ["x.tsv"]


def test_generator_ops_unknown() -> None:
    with pytest.raises(ValueError, match="unknown op"):
        gen.apply(Fraction(1), "/", Fraction(2))
