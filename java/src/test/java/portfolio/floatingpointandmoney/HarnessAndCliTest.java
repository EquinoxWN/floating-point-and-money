package portfolio.floatingpointandmoney;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class HarnessAndCliTest {
    @TempDir
    Path tmp;

    /** Copy every shared vector file into the temp dir. */
    private void copyVectors() throws IOException {
        try (var files = Files.list(Vectors.defaultDir())) {
            for (Path p : files.filter(f -> f.toString().endsWith(".tsv")).toList()) {
                Files.copy(p, tmp.resolve(p.getFileName()));
            }
        }
    }

    /** Replace the first occurrence of a text in one copied vector file. */
    private void corrupt(String name, String from, String to) throws IOException {
        Path p = tmp.resolve(name);
        String text = Files.readString(p, StandardCharsets.UTF_8);
        assertTrue(text.contains(from), from);
        Files.writeString(p, text.replaceFirst(java.util.regex.Pattern.quote(from), to), StandardCharsets.UTF_8);
    }

    /** Output and status of one CLI run. */
    private record Run(int status, String out, String err) {}

    private static Run cli(String... args) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        ByteArrayOutputStream err = new ByteArrayOutputStream();
        int status = App.run(args, new PrintStream(out, true, StandardCharsets.UTF_8),
                new PrintStream(err, true, StandardCharsets.UTF_8));
        return new Run(status, out.toString(StandardCharsets.UTF_8).replace("\r\n", "\n"),
                err.toString(StandardCharsets.UTF_8).replace("\r\n", "\n"));
    }

    @Test
    void everySuitePassesOnTheCommittedVectors() {
        List<Conformance.Score> scores = Conformance.report(Vectors.defaultDir());
        assertEquals(List.of("doubles", "ops", "sums", "money", "currencies"),
                scores.stream().map(Conformance.Score::suite).toList());
        for (Conformance.Score s : scores) {
            assertTrue(s.cases() > 0 && s.failures().isEmpty(), s.suite() + " " + s.failures());
        }
    }

    @Test
    void missingFile() {
        Vectors.VectorException e = assertThrows(Vectors.VectorException.class, () -> Vectors.load(tmp, "money.tsv"));
        assertTrue(e.getMessage().contains("money.tsv"));
    }

    @Test
    void unknownName() {
        assertThrows(Vectors.VectorException.class, () -> Vectors.load(tmp, "../secrets.tsv"));
    }

    @Test
    void wrongColumnCount() throws IOException {
        Files.writeString(tmp.resolve("sums.tsv"), "# c\n0.1\t10\n");
        Vectors.VectorException e = assertThrows(Vectors.VectorException.class, () -> Vectors.load(tmp, "sums.tsv"));
        assertTrue(e.getMessage().endsWith("sums.tsv:2: 2 columns, want 6"), e.getMessage());
    }

    @Test
    void oversizedFile() throws IOException {
        Files.write(tmp.resolve("ops.tsv"), new byte[(int) Vectors.MAX_BYTES + 1]);
        Vectors.VectorException e = assertThrows(Vectors.VectorException.class, () -> Vectors.load(tmp, "ops.tsv"));
        assertTrue(e.getMessage().contains("larger than"));
    }

    @Test
    void fileWithoutRows() throws IOException {
        Files.writeString(tmp.resolve("currencies.tsv"), "# only comments\n\n");
        assertThrows(Vectors.VectorException.class, () -> Vectors.load(tmp, "currencies.tsv"));
    }

    @Test
    void wrongExpectedValuesAreCounted() throws IOException {
        copyVectors();
        corrupt("doubles.tsv", "3fb999999999999a", "3fb9999999999999");
        corrupt("ops.tsv", "\t1999.00\n", "\t1998.99\n");
        corrupt("sums.tsv", "\t3ff0000000000000\t0\n", "\t3fefffffffffffff\t0\n");
        corrupt("currencies.tsv", "KWD\t3", "KWD\t2");
        for (Conformance.Score s : Conformance.report(tmp)) {
            int want = s.suite().equals("money") ? 0 : 1;
            assertEquals(want, s.failures().size(), s.suite());
        }
    }

    @Test
    void unknownMoneyOp() {
        assertThrows(IllegalArgumentException.class, () -> Conformance.moneyCase("divide", "1", "USD", "2", "USD"));
    }

    @Test
    void cliExplain() {
        Run r = cli("explain", "0.1");
        assertEquals(0, r.status());
        assertTrue(r.out().contains("bits\t3fb999999999999a"));
        assertTrue(r.out().contains("exact\t0.1000000000000000055511151231257827021181583404541015625"));
    }

    @Test
    void cliOpsAndSums() {
        Run ops = cli("ops");
        assertEquals(0, ops.status());
        assertTrue(ops.out().contains("0.1 + 0.2\t0.30000000000000004\tfalse\t0.30 USD"), ops.out());
        assertTrue(ops.out().contains("19.99 * 100\t1998.9999999999998\tfalse\t1999.00 USD"));
        Run sums = cli("sums");
        assertEquals(0, sums.status());
        assertTrue(sums.out().contains(
                "0.1\t10\t0.9999999999999999\t-0.00000000000000011102230246251565404236316680908203125\t0\n"));
    }

    @Test
    void cliReport() {
        Run r = cli("report");
        assertEquals(0, r.status());
        assertTrue(r.out().contains("java\tmoney\t78\t78"), r.out());
    }

    @Test
    void cliReportFailsOnWrongVectors() throws IOException {
        copyVectors();
        corrupt("money.tsv", "12.34 USD\n", "12.35 USD\n");
        Run r = cli("--vectors", tmp.toString(), "report");
        assertEquals(1, r.status());
        assertTrue(r.out().contains("java\tmoney\t77\t78"));
        assertTrue(r.err().contains("want 12.35 USD"));
    }

    @Test
    void cliErrors() {
        Run bad = cli("explain", "1e3");
        assertEquals(1, bad.status());
        assertTrue(bad.err().startsWith("error: not a plain decimal literal"));
        Run missing = cli("--vectors", tmp.resolve("nope").toString(), "ops");
        assertEquals(1, missing.status());
        assertEquals(2, cli().status());
        assertEquals(2, cli("divide").status());
        assertTrue(cli("explain").err().startsWith("usage:"));
    }
}
