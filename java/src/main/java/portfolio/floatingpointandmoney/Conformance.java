package portfolio.floatingpointandmoney;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Objects;
import java.util.TreeSet;

/** Runs this package against the shared vectors and counts what agrees. */
public final class Conformance {
    private Conformance() {}

    /** Cases checked and the ones that disagreed. */
    public static final class Score {
        private final String suite;
        private int cases;
        private final List<String> failures = new ArrayList<>();

        /** Empty score for one suite. */
        Score(String suite) {
            this.suite = suite;
        }

        /** Count one case; record it when got differs from want. */
        void check(String label, Object got, Object want) {
            cases++;
            if (!Objects.equals(got, want)) {
                failures.add(label + ": got " + got + ", want " + want);
            }
        }

        /** Suite name. */
        public String suite() {
            return suite;
        }

        /** Cases checked. */
        public int cases() {
            return cases;
        }

        /** Cases that agreed. */
        public int passed() {
            return cases - failures.size();
        }

        /** Descriptions of the cases that disagreed. */
        public List<String> failures() {
            return List.copyOf(failures);
        }
    }

    /** Bits, exact value, ulp and error of each literal. */
    public static Score doubles(Path dir) {
        Score score = new Score("doubles");
        for (String[] r : Vectors.load(dir, "doubles.tsv")) {
            Floats.Stored s = Floats.explain(r[0]);
            score.check(r[0], List.of(s.bits(), s.exact(), s.ulp(), s.error()),
                    List.of(r[1], r[2], r[3], r[4]));
        }
        return score;
    }

    /** Each float operation, its equality with the true result, and the money result. */
    public static Score ops(Path dir) {
        Score score = new Score("ops");
        for (String[] r : Vectors.load(dir, "ops.tsv")) {
            double x = Floats.apply(Floats.parseLiteral(r[0]), r[1], Floats.parseLiteral(r[2]));
            String same = String.valueOf(x == Double.parseDouble(Floats.trueResult(r[0], r[1], r[2]).toString()));
            String cash = moneyOp(Money.parse(r[0], "USD"), r[1], r[2]).amount();
            score.check(r[0] + " " + r[1] + " " + r[2],
                    List.of(Floats.bits(x), Floats.exact(x), same, cash),
                    List.of(r[3], r[4], r[5], r[6]));
        }
        return score;
    }

    /** The ops table's operation done with Money (b is an integer for *). */
    public static Money moneyOp(Money a, String op, String b) {
        if (op.equals("*")) {
            return a.times(Long.parseLong(b));
        }
        Money other = Money.parse(b, a.currency());
        return op.equals("+") ? a.plus(other) : a.minus(other);
    }

    /** Naive and Kahan totals and their exact errors. */
    public static Score sums(Path dir) {
        Score score = new Score("sums");
        for (String[] r : Vectors.load(dir, "sums.tsv")) {
            double x = Floats.parseLiteral(r[0]);
            int n = Integer.parseInt(r[1]);
            double naive = Floats.naiveSum(x, n);
            double kahan = Floats.kahanSum(x, n);
            score.check(r[0] + " x " + n,
                    List.of(Floats.bits(naive), Floats.sumError(naive, r[0], n),
                            Floats.bits(kahan), Floats.sumError(kahan, r[0], n)),
                    List.of(r[2], r[3], r[4], r[5]));
        }
        return score;
    }

    /** Result of one money.tsv row as text, or error:kind. */
    public static String moneyCase(String op, String a, String aCur, String b, String bCur) {
        try {
            if (op.equals("ofminor")) {
                return Money.ofMinor(Long.parseLong(a), aCur).toString();
            }
            Money x = Money.parse(a, aCur);
            return switch (op) {
                case "parse" -> x.toString();
                case "minor" -> Long.toString(x.minor());
                case "negate" -> x.negate().toString();
                case "times" -> x.times(Long.parseLong(b)).toString();
                case "plus" -> x.plus(Money.parse(b, bCur)).toString();
                case "minus" -> x.minus(Money.parse(b, bCur)).toString();
                case "compare" -> Integer.toString(x.compareTo(Money.parse(b, bCur)));
                default -> throw new IllegalArgumentException("unknown money op " + op);
            };
        } catch (MoneyException e) {
            return "error:" + e.kind().name().toLowerCase(Locale.ROOT);
        }
    }

    /** Every shared Money case. */
    public static Score money(Path dir) {
        Score score = new Score("money");
        for (String[] r : Vectors.load(dir, "money.tsv")) {
            score.check(String.join(" ", Arrays.copyOf(r, 5)),
                    moneyCase(r[0], r[1], r[2], r[3], r[4]), r[5]);
        }
        return score;
    }

    /** The built-in currency table equals currencies.tsv. */
    public static Score currencies(Path dir) {
        Score score = new Score("currencies");
        List<String[]> rows = Vectors.load(dir, "currencies.tsv");
        TreeSet<String> codes = new TreeSet<>();
        rows.forEach(r -> codes.add(r[0]));
        score.check("codes", new TreeSet<>(Money.CURRENCIES.keySet()), codes);
        for (String[] r : rows) {
            score.check(r[0], Money.CURRENCIES.get(r[0]), Integer.valueOf(r[1]));
        }
        return score;
    }

    /** Every suite's score. */
    public static List<Score> report(Path dir) {
        return List.of(doubles(dir), ops(dir), sums(dir), money(dir), currencies(dir));
    }
}
