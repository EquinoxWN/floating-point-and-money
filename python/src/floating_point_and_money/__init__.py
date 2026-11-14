"""floating-point-and-money: how doubles store decimals, and exact money in integer minor units."""

from .floats import Stored, explain, kahan_sum, naive_sum
from .money import CURRENCIES, Money, MoneyError

__version__ = "0.1.0"

__all__ = ["CURRENCIES", "Money", "MoneyError", "Stored", "explain", "kahan_sum", "naive_sum"]
