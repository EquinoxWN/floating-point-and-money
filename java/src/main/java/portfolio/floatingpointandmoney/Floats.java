package portfolio.floatingpointandmoney;

import java.math.BigDecimal;
import java.util.regex.Pattern;

/** Experiments: how a decimal literal is stored as a double, and how errors grow in sums. */
public final class Floats {
    /** Longest accepted literal; longer plain literals overflow a double anyway. */
    public static final int MAX_LITERAL = 400;
    /** Largest repetition count for the sum experiments. */
    public static final int MAX_TERMS = 10_000_000;

    private static final Pattern LITERAL = Pattern.compile("-?[0-9]+(\\.[0-9]+)?");

    private Floats() {}

    /** What one decimal literal becomes as a double. */
    public record Stored(String input, String bits, String exact, String ulp, String error) {}

    /** Plain decimal literal to the nearest double; rejects other forms and overflow. */
    public static double parseLiteral(String text) {
        if (text == null || text.length() > MAX_LITERAL || !LITERAL.matcher(text).matches()) {
            throw new IllegalArgumentException("not a plain decimal literal: " + clip(text));
        }
        double x = Double.parseDouble(text);
        if (!Double.isFinite(x)) {
            throw new IllegalArgumentException(clip(text) + " overflows a double");
        }
        return x;
    }

    /** At most 40 characters of a value for an error message. */
    static String clip(String text) {
        return text == null ? "null" : text.substring(0, Math.min(40, text.length()));
    }

    /** BigDecimal as plain text without exponent or trailing zeros. */
    public static String plain(BigDecimal value) {
        return value.signum() == 0 ? "0" : value.stripTrailingZeros().toPlainString();
    }

    /** Reject NaN and infinities, which have no exact decimal value. */
    private static double finite(double x) {
        if (!Double.isFinite(x)) {
            throw new IllegalArgumentException(x + " has no exact decimal value");
        }
        return x;
    }

    /** IEEE 754 binary64 bit pattern as 16 hex digits. */
    public static String bits(double x) {
        return String.format("%016x", Double.doubleToRawLongBits(finite(x)));
    }

    /** Exact decimal value of the double x. */
    public static String exact(double x) {
        return plain(new BigDecimal(finite(x)));
    }

    /** Exact gap between |x| and the next larger double. */
    public static String ulp(double x) {
        return plain(new BigDecimal(Math.ulp(finite(x))));
    }

    /** Bits, exact stored value, ulp and representation error of a literal. */
    public static Stored explain(String text) {
        double x = parseLiteral(text);
        BigDecimal error = new BigDecimal(x).subtract(new BigDecimal(text));
        return new Stored(text, bits(x), exact(x), ulp(x), plain(error));
    }

    /** One double operation: +, - or *. */
    public static double apply(double a, String op, double b) {
        return switch (op) {
            case "+" -> a + b;
            case "-" -> a - b;
            case "*" -> a * b;
            default -> throw new IllegalArgumentException("unknown op " + op);
        };
    }

    /** Exact decimal result of a op b on the literals. */
    public static BigDecimal trueResult(String a, String op, String b) {
        BigDecimal x = new BigDecimal(a);
        BigDecimal y = new BigDecimal(b);
        return switch (op) {
            case "+" -> x.add(y);
            case "-" -> x.subtract(y);
            case "*" -> x.multiply(y);
            default -> throw new IllegalArgumentException("unknown op " + op);
        };
    }

    /** Validate a repetition count. */
    private static int terms(int n) {
        if (n < 0 || n > MAX_TERMS) {
            throw new IllegalArgumentException("n must be in 0.." + MAX_TERMS);
        }
        return n;
    }

    /** Add x to a running double total n times. */
    public static double naiveSum(double x, int n) {
        double total = 0.0;
        for (int i = terms(n); i > 0; i--) {
            total += x;
        }
        return total;
    }

    /** Add x n times with Kahan's compensated summation. */
    public static double kahanSum(double x, int n) {
        double total = 0.0;
        double comp = 0.0;
        for (int i = terms(n); i > 0; i--) {
            double y = x - comp;
            double t = total + y;
            comp = (t - total) - y;
            total = t;
        }
        return total;
    }

    /** Exact signed error of a double total against n times the literal. */
    public static String sumError(double total, String summand, int n) {
        BigDecimal target = new BigDecimal(summand).multiply(BigDecimal.valueOf(n));
        return plain(new BigDecimal(finite(total)).subtract(target));
    }
}
