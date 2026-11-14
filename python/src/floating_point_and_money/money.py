"""Money as an integer count of minor units (cents) plus a currency; floats are refused."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

# ISO 4217 minor-unit digits for the currencies M1 supports (checked against spec/vectors/currencies.tsv).
CURRENCIES: dict[str, int] = {"USD": 2, "EUR": 2, "GBP": 2, "JPY": 0, "KWD": 3}

# Same range in every language: a signed 64-bit count of minor units, symmetric so negate never overflows.
MAX_MINOR = 2**63 - 1
MAX_TEXT = 64
AMOUNT = re.compile(r"(-?)([0-9]+)(?:\.([0-9]+))?")

Kind = Literal["parse", "currency", "overflow", "mismatch"]


class MoneyError(ValueError):
    """A money operation was refused; kind is parse, currency, overflow or mismatch."""

    def __init__(self, kind: Kind, message: str) -> None:
        super().__init__(message)
        self.kind: Kind = kind


def _digits(currency: object) -> int:
    """Minor-unit digits of a supported currency code."""
    if not isinstance(currency, str):
        raise TypeError(f"currency must be str, not {type(currency).__name__}")
    try:
        return CURRENCIES[currency]
    except KeyError:
        raise MoneyError("currency", f"unsupported currency {currency[:8]!r}") from None


def _int(value: object, what: str) -> int:
    """Accept a real int (not bool, not float)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{what} must be int, not {type(value).__name__}")
    return value


def _checked(minor: int) -> int:
    """Fail on results outside the shared minor-unit range."""
    if not -MAX_MINOR <= minor <= MAX_MINOR:
        raise MoneyError("overflow", "amount outside the signed 64-bit minor-unit range")
    return minor


@dataclass(frozen=True)
class Money:
    """An exact amount: minor units (int) and an ISO 4217 currency code."""

    minor: int
    currency: str

    def __post_init__(self) -> None:
        _int(self.minor, "minor")
        _digits(self.currency)
        _checked(self.minor)

    @classmethod
    def of_minor(cls, minor: int, currency: str) -> Money:
        """Amount from a count of minor units, e.g. 1234 USD cents."""
        return cls(minor, currency)

    @classmethod
    def parse(cls, text: str, currency: str) -> Money:
        """Amount from plain decimal text; more fraction digits than the currency has is an error."""
        if not isinstance(text, str):
            raise TypeError(f"amount must be str, not {type(text).__name__}; floats are not money")
        digits = _digits(currency)
        m = AMOUNT.fullmatch(text) if len(text) <= MAX_TEXT else None
        if m is None:
            raise MoneyError("parse", f"not a plain decimal amount: {text[:MAX_TEXT]!r}")
        sign, whole, frac = m.group(1), m.group(2), m.group(3) or ""
        if len(frac) > digits:
            raise MoneyError("parse", f"{currency} has {digits} minor digits, got {len(frac)}")
        minor = int(whole + frac.ljust(digits, "0"))
        return cls(_checked(-minor if sign else minor), currency)

    @classmethod
    def total(cls, items: Iterable[Money], currency: str) -> Money:
        """Sum of amounts in one currency (zero when empty)."""
        acc = cls(0, currency)
        for item in items:
            acc = acc.plus(item)
        return acc

    def _same(self, other: object) -> Money:
        """Other operand, checked to be Money in this currency."""
        if not isinstance(other, Money):
            raise TypeError(f"expected Money, not {type(other).__name__}")
        if other.currency != self.currency:
            raise MoneyError("mismatch", f"{self.currency} and {other.currency} do not mix")
        return other

    def plus(self, other: Money) -> Money:
        """Exact sum in the same currency."""
        return Money(_checked(self.minor + self._same(other).minor), self.currency)

    def minus(self, other: Money) -> Money:
        """Exact difference in the same currency."""
        return Money(_checked(self.minor - self._same(other).minor), self.currency)

    def times(self, quantity: int) -> Money:
        """Exact product with an integer quantity."""
        return Money(_checked(self.minor * _int(quantity, "quantity")), self.currency)

    def negate(self) -> Money:
        """Same amount with the opposite sign."""
        return Money(-self.minor, self.currency)

    def compare(self, other: Money) -> int:
        """-1, 0 or 1; amounts in different currencies are not comparable."""
        o = self._same(other).minor
        return (self.minor > o) - (self.minor < o)

    def amount(self) -> str:
        """Plain decimal text with exactly the currency's minor digits."""
        digits = CURRENCIES[self.currency]
        sign = "-" if self.minor < 0 else ""
        whole, frac = divmod(abs(self.minor), 10**digits)
        return f"{sign}{whole}" + (f".{frac:0{digits}d}" if digits else "")

    def __str__(self) -> str:
        return f"{self.amount()} {self.currency}"

    __add__ = plus
    __sub__ = minus
    __mul__ = times
    __neg__ = negate

    def __lt__(self, other: Money) -> bool:
        return self.compare(other) < 0

    def __le__(self, other: Money) -> bool:
        return self.compare(other) <= 0

    def __gt__(self, other: Money) -> bool:
        return self.compare(other) > 0

    def __ge__(self, other: Money) -> bool:
        return self.compare(other) >= 0
