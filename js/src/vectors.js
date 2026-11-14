// Load the shared vectors in spec/vectors (tab-separated, '#' comments).

import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

export const MAX_BYTES = 1_000_000;
export const COLUMNS = Object.freeze({
  "doubles.tsv": 5,
  "ops.tsv": 7,
  "sums.tsv": 6,
  "money.tsv": 6,
  "currencies.tsv": 2,
});

/** A vector file is missing, too large or malformed. */
export class VectorError extends Error {
  /** New error naming the file. */
  constructor(message, options) {
    super(message, options);
    this.name = "VectorError";
  }
}

/** spec/vectors of this checkout. */
export function defaultDir() {
  return fileURLToPath(new URL("../../spec/vectors", import.meta.url));
}

/** Rows of one vector file, each with the expected number of columns. */
export function load(name, dir = defaultDir()) {
  if (!Object.hasOwn(COLUMNS, name)) throw new VectorError(`unknown vector file ${name}`);
  const path = join(dir, name);
  let text;
  try {
    if (statSync(path).size > MAX_BYTES) throw new VectorError(`${path}: larger than ${MAX_BYTES} bytes`);
    text = readFileSync(path, "utf8");
  } catch (err) {
    if (err instanceof VectorError) throw err;
    throw new VectorError(`${path}: ${err.code ?? err.message}`, { cause: err });
  }
  const rows = [];
  text.split(/\r?\n/).forEach((line, i) => {
    if (line === "" || line.startsWith("#")) return;
    const fields = line.split("\t");
    if (fields.length !== COLUMNS[name]) {
      throw new VectorError(`${path}:${i + 1}: ${fields.length} columns, want ${COLUMNS[name]}`);
    }
    rows.push(fields);
  });
  if (rows.length === 0) throw new VectorError(`${path}: no rows`);
  return rows;
}
