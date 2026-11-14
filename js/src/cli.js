// Command line: explain a literal, show the ops and sums experiments, score the shared vectors.

import { argv, exit, stderr, stdout } from "node:process";
import { fileURLToPath } from "node:url";
import * as conformance from "./conformance.js";
import * as floats from "./floats.js";
import { Money, MoneyError } from "./money.js";
import { defaultDir, load, VectorError } from "./vectors.js";

const USAGE = "usage: node src/cli.js [--vectors DIR] explain LITERAL | ops | sums | report";

/** Print how one literal is stored. */
function explain(literal, out) {
  const s = floats.explain(literal);
  out(`input\t${s.input}\nbits\t${s.bits}\nexact\t${s.exact}\nulp\t${s.ulp}\nstored-input\t${s.error}`);
}

/** Print each float operation next to the Money result. */
function ops(dir, out) {
  out("expression\tdouble (String)\t== true result\tMoney (USD)");
  for (const [a, op, b] of load("ops.tsv", dir)) {
    const x = floats.apply(floats.parseLiteral(a), op, floats.parseLiteral(b));
    const same = x === Number(floats.trueResult(a, op, b));
    out(`${a} ${op} ${b}\t${x}\t${same}\t${conformance.moneyOp(Money.parse(a, "USD"), op, b)}`);
  }
}

/** Print the error of naive and Kahan sums. */
function sums(dir, out) {
  out("summand\tn\tnaive total (String)\tnaive error\tkahan error");
  for (const [summand, nText] of load("sums.tsv", dir)) {
    const x = floats.parseLiteral(summand);
    const n = Number(nText);
    const naive = floats.naiveSum(x, n);
    const kahan = floats.kahanSum(x, n);
    out(`${summand}\t${n}\t${naive}\t${floats.sumError(naive, summand, n)}\t${floats.sumError(kahan, summand, n)}`);
  }
}

/** Print passed/cases per suite; status 1 on any failure. */
function report(dir, out, err) {
  out("language\tsuite\tpassed\tcases");
  let failed = 0;
  for (const s of conformance.report(dir)) {
    out(`js\t${s.suite}\t${s.passed}\t${s.cases}`);
    for (const f of s.failures.slice(0, 5)) err(`  ${f}`);
    failed += s.failures.length;
  }
  return failed === 0 ? 0 : 1;
}

/** Run one command and return its exit status. */
export function run(args, out, err) {
  let dir = defaultDir();
  let rest = args;
  if (rest.length >= 2 && rest[0] === "--vectors") {
    dir = rest[1];
    rest = rest.slice(2);
  }
  try {
    if (rest.length === 2 && rest[0] === "explain") {
      explain(rest[1], out);
      return 0;
    }
    if (rest.length === 1 && rest[0] === "ops") {
      ops(dir, out);
      return 0;
    }
    if (rest.length === 1 && rest[0] === "sums") {
      sums(dir, out);
      return 0;
    }
    if (rest.length === 1 && rest[0] === "report") return report(dir, out, err);
  } catch (e) {
    if (e instanceof RangeError || e instanceof TypeError || e instanceof MoneyError || e instanceof VectorError) {
      err(`error: ${e.message}`);
      return 1;
    }
    throw e;
  }
  err(USAGE);
  return 2;
}

if (argv[1] && fileURLToPath(import.meta.url) === argv[1]) {
  const status = run(
    argv.slice(2),
    (line) => stdout.write(`${line}\n`),
    (line) => stderr.write(`${line}\n`),
  );
  if (status !== 0) exit(status);
}
