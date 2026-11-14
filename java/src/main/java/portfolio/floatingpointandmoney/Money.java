package portfolio.floatingpointandmoney;

import java.math.BigInteger;
import java.util.Map;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * An exact amount: a count of minor units (cents) in a {@code long} plus an ISO 4217 code.
 *
 * <p>There is deliberately no factory that takes a {@code double}: amounts come from text or minor
 * units. The range is symmetric, -(2^63-1)..2^63-1, so {@link #negate()} never overflows.
 */
public record Money(long minor, String currency) implements Comparable<Money> {
    /** ISO 4217 minor-unit digits of the supported currencies (checked against currencies.tsv). */
    public static final Map<String, Integer> CURRENCIES =
            Map.of("USD", 2, "EUR", 2, "GBP", 2, "JPY", 0, "KWD", 3);

    /** Longest accepted amount text. */
    public static final int MAX_TEXT = 64;

    private static final Pattern AMOUNT = Pattern.compile("(-?)([0-9]+)(?:\\.([0-9]+))?");
    private static final BigInteger MAX = BigInteger.valueOf(Long.MAX_VALUE);

    /** Validates the currency and the shared range. */
    public Money {
        digits(currency);
        if (minor == Long.MIN_VALUE) {
            throw overflow();
        }
    }

    /** Minor-unit digits of a supported currency code. */
    private static int digits(String currency) {
        Objects.requireNonNull(currency, "currency");
        Integer d = CURRENCIES.get(currency);
        if (d == null) {
            throw new MoneyException(MoneyException.Kind.CURRENCY,
                    "unsupported currency " + Floats.clip(currency));
        }
        return d;
    }

    /** The shared out-of-range error. */
    private static MoneyException overflow() {
        return new MoneyException(MoneyException.Kind.OVERFLOW,
                "amount outside the signed 64-bit minor-unit range");
    }

    /** Amount from a count of minor units, e.g. 1234 USD cents. */
    public static Money ofMinor(long minor, String currency) {
        return new Money(minor, currency);
    }

    /** Amount from plain decimal text; more fraction digits than the currency has is an error. */
    public static Money parse(String text, String currency) {
        Objects.requireNonNull(text, "text");
        int digits = digits(currency);
        Matcher m = AMOUNT.matcher(text);
        if (text.length() > MAX_TEXT || !m.matches()) {
            throw new MoneyException(MoneyException.Kind.PARSE,
                    "not a plain decimal amount: " + Floats.clip(text));
        }
        String frac = m.group(3) == null ? "" : m.group(3);
        if (frac.length() > digits) {
            throw new MoneyException(MoneyException.Kind.PARSE,
                    currency + " has " + digits + " minor digits, got " + frac.length());
        }
        BigInteger units = new BigInteger(m.group(2) + frac + "0".repeat(digits - frac.length()));
        if (units.compareTo(MAX) > 0) {
            throw overflow();
        }
        long value = units.longValueExact();
        return new Money(m.group(1).isEmpty() ? value : -value, currency);
    }

    /** Sum of amounts in one currency (zero when empty). */
    public static Money total(Iterable<Money> items, String currency) {
        Money acc = new Money(0, currency);
        for (Money item : items) {
            acc = acc.plus(item);
        }
        return acc;
    }

    /** Other operand, checked to be in this currency. */
    private Money same(Money other) {
        Objects.requireNonNull(other, "other");
        if (!other.currency.equals(currency)) {
            throw new MoneyException(MoneyException.Kind.MISMATCH,
                    currency + " and " + other.currency + " do not mix");
        }
        return other;
    }

    /** Exact sum in the same currency. */
    public Money plus(Money other) {
        try {
            return new Money(Math.addExact(minor, same(other).minor), currency);
        } catch (ArithmeticException e) {
            throw overflow();
        }
    }

    /** Exact difference in the same currency. */
    public Money minus(Money other) {
        try {
            return new Money(Math.subtractExact(minor, same(other).minor), currency);
        } catch (ArithmeticException e) {
            throw overflow();
        }
    }

    /** Exact product with an integer quantity. */
    public Money times(long quantity) {
        try {
            return new Money(Math.multiplyExact(minor, quantity), currency);
        } catch (ArithmeticException e) {
            throw overflow();
        }
    }

    /** Same amount with the opposite sign. */
    public Money negate() {
        return new Money(-minor, currency);
    }

    /** -1, 0 or 1; amounts in different currencies are not comparable. */
    @Override
    public int compareTo(Money other) {
        return Long.compare(minor, same(other).minor);
    }

    /** Plain decimal text with exactly the currency's minor digits. */
    public String amount() {
        int digits = CURRENCIES.get(currency);
        String abs = Long.toString(Math.abs(minor));
        String sign = minor < 0 ? "-" : "";
        if (digits == 0) {
            return sign + abs;
        }
        String padded = "0".repeat(Math.max(0, digits + 1 - abs.length())) + abs;
        int cut = padded.length() - digits;
        return sign + padded.substring(0, cut) + "." + padded.substring(cut);
    }

    /** Canonical text such as {@code 12.34 USD}. */
    @Override
    public String toString() {
        return amount() + " " + currency;
    }
}
