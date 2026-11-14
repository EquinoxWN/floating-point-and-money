package portfolio.floatingpointandmoney;

import java.io.PrintStream;
import java.nio.file.Path;
import java.util.Arrays;

/** Command line: explain a literal, show the ops and sums experiments, score the shared vectors. */
public final class App {
    private static final String USAGE = "usage: App [--vectors DIR] explain LITERAL | ops | sums | report";

    private App() {}

    /** Entry point; exits with the command's status when it is not 0. */
    public static void main(String[] args) {
        int status = run(args, System.out, System.err);
        if (status != 0) {
            System.exit(status);
        }
    }

    /** Run one command and return its exit status. */
    public static int run(String[] args, PrintStream out, PrintStream err) {
        Path dir = Vectors.defaultDir();
        String[] rest = args;
        if (rest.length >= 2 && rest[0].equals("--vectors")) {
            dir = Path.of(rest[1]);
            rest = Arrays.copyOfRange(rest, 2, rest.length);
        }
        try {
            if (rest.length == 2 && rest[0].equals("explain")) {
                explain(rest[1], out);
                return 0;
            }
            if (rest.length == 1) {
                switch (rest[0]) {
                    case "ops" -> {
                        ops(dir, out);
                        return 0;
                    }
                    case "sums" -> {
                        sums(dir, out);
                        return 0;
                    }
                    case "report" -> {
                        return report(dir, out, err);
                    }
                    default -> {
                        // falls through to the usage message
                    }
                }
            }
        } catch (IllegalArgumentException | MoneyException | Vectors.VectorException e) {
            err.println("error: " + e.getMessage());
            return 1;
        }
        err.println(USAGE);
        return 2;
    }

    /** Print how one literal is stored. */
    private static void explain(String literal, PrintStream out) {
        Floats.Stored s = Floats.explain(literal);
        out.println("input\t" + s.input());
        out.println("bits\t" + s.bits());
        out.println("exact\t" + s.exact());
        out.println("ulp\t" + s.ulp());
        out.println("stored-input\t" + s.error());
    }

    /** Print each float operation next to the Money result. */
    private static void ops(Path dir, PrintStream out) {
        out.println("expression\tdouble (Double.toString)\t== true result\tMoney (USD)");
        for (String[] r : Vectors.load(dir, "ops.tsv")) {
            double x = Floats.apply(Floats.parseLiteral(r[0]), r[1], Floats.parseLiteral(r[2]));
            boolean same = x == Double.parseDouble(Floats.trueResult(r[0], r[1], r[2]).toString());
            Money cash = Conformance.moneyOp(Money.parse(r[0], "USD"), r[1], r[2]);
            out.println(r[0] + " " + r[1] + " " + r[2] + "\t" + x + "\t" + same + "\t" + cash);
        }
    }

    /** Print the error of naive and Kahan sums. */
    private static void sums(Path dir, PrintStream out) {
        out.println("summand\tn\tnaive total (Double.toString)\tnaive error\tkahan error");
        for (String[] r : Vectors.load(dir, "sums.tsv")) {
            double x = Floats.parseLiteral(r[0]);
            int n = Integer.parseInt(r[1]);
            double naive = Floats.naiveSum(x, n);
            double kahan = Floats.kahanSum(x, n);
            out.println(r[0] + "\t" + n + "\t" + naive + "\t" + Floats.sumError(naive, r[0], n)
                    + "\t" + Floats.sumError(kahan, r[0], n));
        }
    }

    /** Print passed/cases per suite; status 1 on any failure. */
    private static int report(Path dir, PrintStream out, PrintStream err) {
        out.println("language\tsuite\tpassed\tcases");
        int failed = 0;
        for (Conformance.Score s : Conformance.report(dir)) {
            out.println("java\t" + s.suite() + "\t" + s.passed() + "\t" + s.cases());
            s.failures().stream().limit(5).forEach(f -> err.println("  " + f));
            failed += s.failures().size();
        }
        return failed == 0 ? 0 : 1;
    }
}
