package portfolio.floatingpointandmoney;

/** A money operation was refused; {@link #kind()} says why. */
public final class MoneyException extends RuntimeException {
    private static final long serialVersionUID = 1L;

    /** Why an operation was refused (same names in every language). */
    public enum Kind {
        PARSE,
        CURRENCY,
        OVERFLOW,
        MISMATCH
    }

    /** The reason, serialisable because it is an enum. */
    private final Kind kind;

    /** New refusal of the given kind. */
    public MoneyException(Kind kind, String message) {
        super(message);
        this.kind = kind;
    }

    /** Why the operation was refused. */
    public Kind kind() {
        return kind;
    }
}
