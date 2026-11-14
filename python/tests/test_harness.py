"""The vector loader and the scoring harness fail when they should."""

from __future__ import annotations

from pathlib import Path

import pytest

from floating_point_and_money import conformance, floats
from floating_point_and_money.vectors import MAX_BYTES, VectorError, default_dir, load


def test_every_suite_passes_on_the_committed_vectors() -> None:
    scores = conformance.report()
    assert [s.suite for s in scores] == ["doubles", "ops", "sums", "money", "currencies"]
    assert all(s.failures == [] and s.cases > 0 for s in scores)


def test_default_dir_is_the_repo_spec() -> None:
    assert (default_dir() / "money.tsv").is_file()


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(VectorError, match=r"money.tsv"):
        load("money.tsv", tmp_path)


def test_unknown_name() -> None:
    with pytest.raises(VectorError, match="unknown"):
        load("../secrets.tsv")


def test_wrong_column_count(tmp_path: Path) -> None:
    (tmp_path / "sums.tsv").write_text("# c\n0.1\t10\n", encoding="utf-8")
    with pytest.raises(VectorError, match=r"sums.tsv:2: 2 columns, want 6"):
        load("sums.tsv", tmp_path)


def test_oversized_file(tmp_path: Path) -> None:
    (tmp_path / "ops.tsv").write_bytes(b"#" * (MAX_BYTES + 1))
    with pytest.raises(VectorError, match="larger than"):
        load("ops.tsv", tmp_path)


def test_file_without_rows(tmp_path: Path) -> None:
    (tmp_path / "currencies.tsv").write_text("# only comments\n\n", encoding="utf-8")
    with pytest.raises(VectorError, match="no rows"):
        load("currencies.tsv", tmp_path)


def test_wrong_expected_value_is_counted(tmp_path: Path) -> None:
    text = (default_dir() / "doubles.tsv").read_text(encoding="utf-8")
    (tmp_path / "doubles.tsv").write_text(
        text.replace("3fb999999999999a", "3fb9999999999999", 1), encoding="utf-8"
    )
    score = conformance.doubles(tmp_path)
    assert score.passed == score.cases - 1
    assert score.failures[0].startswith("0.1:")


def test_broken_kahan_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(floats, "kahan_sum", floats.naive_sum)
    score = conformance.sums()
    assert score.passed < score.cases


def test_broken_ulp_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(floats, "ulp", lambda x: "0")
    assert conformance.doubles().passed == 0


def test_wrong_money_column_is_caught(tmp_path: Path) -> None:
    for name in ("ops.tsv",):
        text = (default_dir() / name).read_text(encoding="utf-8")
        (tmp_path / name).write_text(text.replace("\t1999.00\n", "\t1998.99\n"), encoding="utf-8")
    assert len(conformance.ops(tmp_path).failures) == 1


def test_unknown_money_op() -> None:
    with pytest.raises(ValueError, match="unknown money op"):
        conformance.money_case("divide", "1", "USD", "2", "USD")
