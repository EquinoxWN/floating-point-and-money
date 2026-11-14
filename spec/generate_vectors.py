"""Build the shared floating-point vectors in spec/vectors from exact rational arithmetic.

usage: python spec/generate_vectors.py [--check]

The expected values are computed with fractions.Fraction (exact), independently of the packages
in java/, python/ and js/, which use BigDecimal, decimal and BigInt. --check exits 1 when a
committed file differs from what this script would write.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

OUT = Path(__file__).resolve().parent / "vectors"

# Decimal literals as a person would type them: how each one is stored as a double.
INPUTS = [
    "0.1",
    "0.2",
    "0.3",
    "0.5",
    "0.7",
    "1.1",
    "0.01",
    "0.05",
    "1.005",
    "1.15",
    "4.35",
    "19.99",
    "-0.1",
    "100",
    "123456789.12",
    "9007199254740992",
    "9007199254740993",
    "10000000000000001",
    "100000000000000000000000",
]

# (a, op, b): one float operation each; b is an integer for "*" so the money result is exact.
OPS = [
    ("0.1", "+", "0.2"),
    ("0.1", "*", "3"),
    ("0.3", "-", "0.1"),
    ("1", "-", "0.9"),
    ("1.1", "*", "3"),
    ("0.07", "*", "100"),
    ("1.15", "*", "100"),
    ("4.35", "*", "100"),
    ("19.99", "*", "100"),
    ("0.5", "+", "0.25"),
    ("2.5", "-", "0.5"),
    ("9007199254740992", "+", "1"),
    ("10000000000000000", "+", "1"),
]

# (summand, n): add the same double n times, naively and with Kahan compensation.
SUMS = [(s, n) for s in ("0.1", "0.01") for n in (10, 100, 1_000, 10_000, 100_000, 1_000_000)]

MONEY_SCALE = 2  # the ops table's money column is in a currency with two minor digits (USD)


def exact_decimal(value: Fraction) -> str:
    """Plain decimal string of a fraction whose denominator is a power of two or ten."""
    den = value.denominator
    k = 0
    while den % 2 == 0:
        den //= 2
        k += 1
    j = 0
    while den % 5 == 0:
        den //= 5
        j += 1
    if den != 1:
        raise ValueError(f"{value} has no finite decimal expansion")
    places = max(k, j)
    scaled = value * 10**places
    if scaled.denominator != 1:
        raise AssertionError("scaling did not clear the denominator")
    digits = str(abs(scaled.numerator)).rjust(places + 1, "0")
    text = (
        digits if places == 0 else f"{digits[:-places]}.{digits[-places:]}".rstrip("0").rstrip(".")
    )
    return "0" if text == "0" else ("-" if value < 0 else "") + text


def bits(x: float) -> str:
    """IEEE 754 binary64 bit pattern as 16 hex digits."""
    return struct.pack(">d", x).hex()


def ulp(x: float) -> Fraction:
    """Gap between |x| and the next larger double, from the exponent bits."""
    raw = struct.unpack(">Q", struct.pack(">d", x))[0]
    exponent = (raw >> 52) & 0x7FF
    if exponent == 0x7FF:
        raise ValueError("non-finite")
    return Fraction(1, 2**1074) if exponent == 0 else Fraction(2) ** (exponent - 1075)


def apply(a: float | Fraction, op: str, b: float | Fraction) -> float | Fraction:
    """One arithmetic operation on doubles or exact fractions."""
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    raise ValueError(f"unknown op {op!r}")


def money(value: Fraction) -> str:
    """Exact amount with two fraction digits (fails if it is not whole cents)."""
    cents = value * 10**MONEY_SCALE
    if cents.denominator != 1:
        raise ValueError(f"{value} is not a whole number of cents")
    sign = "-" if cents < 0 else ""
    whole, frac = divmod(abs(cents.numerator), 10**MONEY_SCALE)
    return f"{sign}{whole}.{frac:0{MONEY_SCALE}d}"


def naive_sum(x: float, n: int) -> float:
    """Add x to a running double total n times."""
    total = 0.0
    for _ in range(n):
        total += x
    return total


def kahan_sum(x: float, n: int) -> float:
    """Add x n times with Kahan's compensated summation."""
    total = 0.0
    comp = 0.0
    for _ in range(n):
        y = x - comp
        t = total + y
        comp = (t - total) - y
        total = t
    return total


def doubles_rows() -> list[str]:
    """input, bits, exact stored value, ulp and representation error for each literal."""
    rows = []
    for text in INPUTS:
        x = float(text)
        stored = Fraction(x)
        rows.append(
            "\t".join(
                [
                    text,
                    bits(x),
                    exact_decimal(stored),
                    exact_decimal(ulp(x)),
                    exact_decimal(stored - Fraction(text)),
                ]
            )
        )
    return rows


def ops_rows() -> list[str]:
    """Float result bits and exact value, whether it equals the double of the true result, money result."""
    rows = []
    for a, op, b in OPS:
        result = apply(float(a), op, float(b))
        true = apply(Fraction(a), op, Fraction(b))
        if not isinstance(result, float) or not isinstance(true, Fraction):
            raise AssertionError("type mix-up")
        same = "true" if result == float(true) else "false"
        rows.append(
            "\t".join([a, op, b, bits(result), exact_decimal(Fraction(result)), same, money(true)])
        )
    return rows


def sums_rows() -> list[str]:
    """Naive and Kahan totals and their exact signed errors."""
    rows = []
    for summand, n in SUMS:
        x = float(summand)
        target = Fraction(summand) * n
        naive = naive_sum(x, n)
        kahan = kahan_sum(x, n)
        rows.append(
            "\t".join(
                [
                    summand,
                    str(n),
                    bits(naive),
                    exact_decimal(Fraction(naive) - target),
                    bits(kahan),
                    exact_decimal(Fraction(kahan) - target),
                ]
            )
        )
    return rows


FILES = {
    "doubles.tsv": (
        "# How decimal literals are stored as IEEE 754 binary64 doubles. Generated by spec/generate_vectors.py.\n"
        "# input\tbits (hex)\texact stored value\tulp (exact)\terror = stored - input (exact)\n",
        doubles_rows,
    ),
    "ops.tsv": (
        "# One double operation each. Generated by spec/generate_vectors.py.\n"
        "# a\top\tb\tresult bits (hex)\tresult exact\tresult == double(true result)\ttrue result in USD\n",
        ops_rows,
    ),
    "sums.tsv": (
        "# Adding one double n times. Generated by spec/generate_vectors.py.\n"
        "# summand\tn\tnaive bits\tnaive error (exact)\tkahan bits\tkahan error (exact)\n",
        sums_rows,
    ),
}


def render(name: str) -> str:
    """Full text of one generated file."""
    header, rows = FILES[name]
    return header + "".join(row + "\n" for row in rows())


def write_atomic(path: Path, text: str) -> None:
    """Write through a temp file in the same directory, then rename over the target."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    """Write or check every generated vector file."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if a committed file is stale")
    parser.add_argument("--out", type=Path, default=OUT, help="vector directory")
    args = parser.parse_args(argv)
    stale = []
    for name in FILES:
        path = args.out / name
        text = render(name)
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        if args.check:
            stale.append(name)
        else:
            write_atomic(path, text)
    if stale:
        print(
            f"vectors: stale {', '.join(stale)}; run python spec/generate_vectors.py",
            file=sys.stderr,
        )
        return 1
    print(f"vectors: {len(FILES)} files up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
