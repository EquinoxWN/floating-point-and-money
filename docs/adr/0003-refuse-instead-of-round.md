# ADR 0003: Parsing refuses extra fraction digits instead of rounding

- **Status:** Accepted

## Context

`Money.parse("12.345", "USD")` has more digits than USD has minor units. A parser can round it
(to 12.34 or 12.35, depending on the mode), truncate it, or refuse it. Silent rounding at the
boundary is one of the ways money code loses cents without anyone noticing, and the right
rounding mode depends on the business rule (M2 compares them).

## Decision

`parse` accepts only plain decimal text, `-?[0-9]+(\.[0-9]+)?` with ASCII digits, at most 64
characters, and at most as many fraction digits as the currency has. Anything else is a `parse`
error, including `12.340` USD (a trailing zero still exceeds the scale), `+1`, `1e3`, `.5`,
`1,000.00`, `NaN` and non-ASCII digits. Floats are a type error in Python and JS, and Java has no
`double` overload.

## Consequences

- No input can change value on the way in; a caller who has `12.345` must pick a rounding mode
  explicitly (M2 adds the API for that).
- Callers must format input first: thousands separators and locale formats are rejected (locale
  parsing is M3).
- `12.340` being refused is stricter than necessary; it keeps the rule a single digit count that
  is the same in every language and easy to test.
