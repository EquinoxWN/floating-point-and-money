package portfolio.floatingpointandmoney;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/** Loads the shared vectors in spec/vectors (tab-separated, '#' comments). */
public final class Vectors {
    /** Largest accepted vector file. */
    public static final long MAX_BYTES = 1_000_000;

    /** Column count of each known file. */
    static final Map<String, Integer> COLUMNS = Map.of(
            "doubles.tsv", 5, "ops.tsv", 7, "sums.tsv", 6, "money.tsv", 6, "currencies.tsv", 2);

    private Vectors() {}

    /** A vector file is missing, too large or malformed. */
    public static final class VectorException extends RuntimeException {
        private static final long serialVersionUID = 1L;

        /** New error with a message naming the file. */
        public VectorException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    /** System property fpm.vectors if set, else ../spec/vectors. */
    public static Path defaultDir() {
        String prop = System.getProperty("fpm.vectors");
        return Path.of(prop != null ? prop : "../spec/vectors");
    }

    /** Rows of one vector file, each with the expected number of columns. */
    public static List<String[]> load(Path dir, String name) {
        Integer want = COLUMNS.get(name);
        if (want == null) {
            throw new VectorException("unknown vector file " + name, null);
        }
        Path path = dir.resolve(name);
        List<String> lines;
        try {
            if (Files.size(path) > MAX_BYTES) {
                throw new VectorException(path + ": larger than " + MAX_BYTES + " bytes", null);
            }
            lines = Files.readAllLines(path, StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new VectorException(path + ": cannot read (" + e.getClass().getSimpleName() + ")", e);
        }
        List<String[]> rows = new ArrayList<>();
        for (int i = 0; i < lines.size(); i++) {
            String line = lines.get(i);
            if (line.isEmpty() || line.startsWith("#")) {
                continue;
            }
            String[] fields = line.split("\t", -1);
            if (fields.length != want) {
                throw new VectorException(path + ":" + (i + 1) + ": " + fields.length
                        + " columns, want " + want, null);
            }
            rows.add(fields);
        }
        if (rows.isEmpty()) {
            throw new VectorException(path + ": no rows", null);
        }
        return rows;
    }
}
