# RFC 0001: floating-point-and-money design

- **Status:** Accepted (M1 built)
- **Author:** EquinoxWN
- **Created:** 2026-11-14

## Problem

Binary floating point cannot store most decimal fractions: `0.1` is stored as
0.1000000000000000055511151231257827021181583404541015625. Each operation then rounds to the
nearest double, so `0.1 + 0.2 == 0.3` is false, `19.99 * 100` is 1998.9999999999998, and a
truncation to whole cents turns it into 1998. Code that keeps money in `double` (Java), `float`
(Python) or `number` (JavaScript) loses or invents cents in totals, comparisons and conversions,
and the error is invisible in the default printed form.

Who has the problem: engineers who build invoices, carts, payments or reports in Java, Python or
JavaScript, and reviewers who need to show a team, with numbers, why amounts must not be floats.

## Critical-to-quality measures (Define)

| CTQ | Target (M1) |
|---|---|
| The three languages agree, bit for bit, on how each literal is stored and on every float operation and sum in the experiments | 100% of shared vector cases in each language |
| Expected values are independent of the code under test | Computed with exact rationals (`fractions.Fraction`) in `spec/generate_vectors.py`; drift fails `make lint` |
| The Money API never rounds silently and never accepts a float | Every shared Money case passes; float input is a type error in Python and JS and has no overload in Java |
| Overflow is an error, never a wrap-around | Shared overflow cases at the signed 64-bit edge pass in all three languages |
| Tests can fail | At least 6 hand mutations on core functions, all killed |

## Goals (M1)

- Experiments show exactly how binary floating point stores 0.1, where precision is lost and how
  errors grow in sums.
- Each language implements money with integer minor units, never floats, behind the same small API.

## Non-goals (M1)

- Rounding modes and invoice comparisons (M2), fair allocation of a remainder (M2).
- The full ISO 4217 list and locale-aware formatting (M3); M1 knows five currencies.
- Multiplying by a non-integer rate (tax, FX), which needs a rounding mode (M2).
- A hosted service.

## Design

```
spec/generate_vectors.py (Fraction, exact) --> spec/vectors/{doubles,ops,sums}.tsv
hand-written                               --> spec/vectors/{money,currencies}.tsv
                                                   |
        java/ (BigDecimal for exact values, long minor units)
        python/ (decimal with Inexact trapped, int minor units)
        js/ (own BigInt decimal, BigInt minor units)
```

**Experiments.** For each literal in `doubles.tsv`: the 64-bit pattern, the exact decimal value
of the stored double, its ulp and the representation error (stored minus literal), all as exact
plain decimals. `ops.tsv` holds one double operation per row with the result's bits and exact
value, whether it equals the double nearest the true result, and the true result in USD.
`sums.tsv` adds 0.1 or 0.01 to a double total 10 to 1,000,000 times, naively and with Kahan
compensation, and stores both totals' bits and exact errors. IEEE 754 binary64 arithmetic is
deterministic, so every language must reproduce every bit.

**Money.** An amount is a signed count of minor units plus an ISO 4217 code
([ADR 0002](../adr/0002-integer-minor-units.md)). The range is -(2^63-1)..2^63-1 in every language
(Java `long`; Python `int` and JS `BigInt` are checked against the same bound), so results agree
and `negate` never overflows. API, same in each language (Python uses snake_case):
`parse(text, currency)`, `ofMinor(minor, currency)`, `total(items, currency)`, `plus`, `minus`,
`times(integer)`, `negate`, `compare`, `amount()`, `toString()` (`12.34 USD`). Errors carry a kind:
`parse`, `currency`, `overflow`, `mismatch`. `parse` refuses more fraction digits than the
currency has instead of rounding ([ADR 0003](../adr/0003-refuse-instead-of-round.md)).

## Alternatives considered

| Option | Why not (yet) |
|---|---|
| Arbitrary-precision decimals (`BigDecimal`, `decimal.Decimal`, a JS decimal library) as the amount type | Exact too, but scale and rounding context travel with each value: `new BigDecimal("1.10").equals(new BigDecimal("1.1"))` is false in Java, Python's context precision is global, and JS has no built-in decimal. Integer minor units make the scale a property of the currency. See ADR 0002. |
| JSR 354 / Moneta, py-moneyed, dinero.js | Complete libraries, but three different APIs and rounding rules make a cross-language comparison impossible, and they hide what this project exists to show. Moneta stays the upstream target. |
| Doubles rounded to cents after every operation | The approach the experiments disprove: `Math.round(1.005 * 100) / 100` gives 1.00 because 1.005 is stored as 1.00499999999999989…; rounding after each step also compounds. |
| Generating expected values in each language | Would test a language against itself. One independent exact generator (Fraction) and a `--check` drift gate give one source of truth. |

## Measurement plan

- `make test` runs every shared vector case in Java, Python and JavaScript; `make report` prints
  passed / cases per suite and language, and CI prints the same as a `::notice`.
- Seeded random invariants (2,000 pairs per currency per language): parse(amount()) round trip,
  exact sum against a decimal or BigInt reference, `(a + b) - b == a`, overflow exactly when the
  true sum leaves the range.
- Hand mutations on core functions (`docs/quality/2026-11-01.md`).
- M3: a catalogue of real money bugs reproduced in each language, each guarded by a property test.

## Milestones

- **M1 (done):** experiments on storage, operations and sums; the Money API in three languages.
- **M2:** rounding modes compared on invoices; splitting 100 three ways with deterministic leftover cents.
- **M3:** full ISO 4217 minor units and locale formatting; property tests over millions of amounts; the bug catalogue.

## Risks and open questions

- A signed 64-bit minor-unit range is enough for any real amount in five currencies but not for
  currencies with very small units or for intermediate results of rate calculations (M2 may need
  a wider type for intermediates).
- The experiment results are deterministic only because no language uses extended precision or
  fused multiply-add here; CI on Linux will confirm the same bits on another platform.
