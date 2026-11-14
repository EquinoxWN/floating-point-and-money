# ADR 0002: Store money as integer minor units with a shared 64-bit range

- **Status:** Accepted

## Context

The Money API must be exact and must behave the same in Java, Python and JavaScript. The two
exact choices are a decimal type (`BigDecimal`, `decimal.Decimal`, a JS library) or an integer
count of minor units (cents). Python's `int` and JavaScript's `BigInt` are unbounded, Java's
`long` is not.

## Decision

An amount is an integer count of the currency's minor units plus an ISO 4217 code. The scale comes
from the currency (USD 2, JPY 0, KWD 3), never from the value. Every language enforces the same
range, -(2^63-1)..2^63-1, and reports anything outside it as an `overflow` error; Java uses
`Math.addExact` / `multiplyExact`.

## Consequences

- Equality, hashing and ordering are plain integer operations: `1.10 USD` and `1.1 USD` are the
  same value, unlike `BigDecimal.equals`.
- Results agree across languages, including at the edge: the shared vectors contain cases at
  ±92,233,720,368,547,758.07 USD.
- Python and JS refuse amounts their own integers could hold, to stay identical to Java.
- Multiplying by a non-integer (tax rate, exchange rate) cannot be expressed without choosing a
  rounding mode; that is deferred to M2 instead of guessing one now.
- The range is far beyond real amounts but could be too narrow for intermediate products in
  rate calculations; M2 will decide whether intermediates need a wider type.
