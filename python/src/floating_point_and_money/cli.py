"""Command line: explain a literal, show the ops and sums experiments, score the shared vectors."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import conformance, floats
from .money import Money
from .vectors import load


def _explain(literal: str) -> None:
    """Print how one literal is stored."""
    s = floats.explain(literal)
    print(
        f"input\t{s.input}\nbits\t{s.bits}\nexact\t{s.exact}\nulp\t{s.ulp}\nstored-input\t{s.error}"
    )


def _ops(directory: Path | None) -> None:
    """Print each float operation next to the Money result."""
    print("expression\tdouble (repr)\t== true result\tMoney (USD)")
    for a, op, b, *_ in load("ops.tsv", directory):
        x = floats.apply(floats.parse_literal(a), op, floats.parse_literal(b))
        same = x == float(floats.true_result(a, op, b))
        print(
            f"{a} {op} {b}\t{x!r}\t{str(same).lower()}\t{conformance.money_op(Money.parse(a, 'USD'), op, b)}"
        )


def _sums(directory: Path | None) -> None:
    """Print the error of naive and Kahan sums."""
    print("summand\tn\tnaive total (repr)\tnaive error\tkahan error")
    for summand, n_text, *_ in load("sums.tsv", directory):
        x, n = floats.parse_literal(summand), int(n_text)
        naive = floats.naive_sum(x, n)
        kahan = floats.kahan_sum(x, n)
        print(
            f"{summand}\t{n}\t{naive!r}\t{floats.sum_error(naive, summand, n)}"
            f"\t{floats.sum_error(kahan, summand, n)}"
        )


def _report(directory: Path | None) -> int:
    """Print passed/cases per suite; exit 1 on any failure."""
    print("language\tsuite\tpassed\tcases")
    failed = 0
    for score in conformance.report(directory):
        print(f"python\t{score.suite}\t{score.passed}\t{score.cases}")
        for failure in score.failures[:5]:
            print(f"  {failure}", file=sys.stderr)
        failed += len(score.failures)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run one command."""
    parser = argparse.ArgumentParser(prog="fpm", description=__doc__)
    parser.add_argument("--vectors", type=Path, help="spec/vectors directory")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("explain", help="how a decimal literal is stored").add_argument("literal")
    sub.add_parser("ops", help="float operations next to Money")
    sub.add_parser("sums", help="error growth when adding 0.1 or 0.01 n times")
    sub.add_parser("report", help="passed/cases on the shared vectors")
    args = parser.parse_args(argv)
    try:
        if args.command == "explain":
            _explain(args.literal)
        elif args.command == "ops":
            _ops(args.vectors)
        elif args.command == "sums":
            _sums(args.vectors)
        else:
            return _report(args.vectors)
    except (ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
