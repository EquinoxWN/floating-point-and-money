"""Load the shared vectors in spec/vectors (tab-separated, '#' comments)."""

from __future__ import annotations

from pathlib import Path

MAX_BYTES = 1_000_000
COLUMNS = {"doubles.tsv": 5, "ops.tsv": 7, "sums.tsv": 6, "money.tsv": 6, "currencies.tsv": 2}


class VectorError(ValueError):
    """A vector file is missing, too large or malformed."""


def default_dir() -> Path:
    """spec/vectors next to the python/ folder of this checkout."""
    return Path(__file__).resolve().parents[3] / "spec" / "vectors"


def load(name: str, directory: Path | None = None) -> list[list[str]]:
    """Rows of one vector file, each with the expected number of columns."""
    if name not in COLUMNS:
        raise VectorError(f"unknown vector file {name!r}")
    path = (directory or default_dir()) / name
    try:
        if path.stat().st_size > MAX_BYTES:
            raise VectorError(f"{path}: larger than {MAX_BYTES} bytes")
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise VectorError(f"{path}: {exc.strerror or exc}") from exc
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != COLUMNS[name]:
            raise VectorError(f"{path}:{number}: {len(fields)} columns, want {COLUMNS[name]}")
        rows.append(fields)
    if not rows:
        raise VectorError(f"{path}: no rows")
    return rows
