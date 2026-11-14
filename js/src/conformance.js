// Run this package against the shared vectors and count what agrees.

import { isDeepStrictEqual } from "node:util";
import * as floats from "./floats.js";
import { CURRENCIES, Money, MoneyError } from "./money.js";
import { load } from "./vectors.js";

/** Cases checked and the ones that disagreed. */
export class Score {
  /** Empty score for one suite. */
  constructor(suite) {
    this.suite = suite;
    this.cases = 0;
    this.failures = [];
  }

  /** Cases that agreed. */
  get passed() {
    return this.cases - this.failures.length;
  }

  /** Count one case; record it when got differs from want. */
  check(label, got, want) {
    this.cases += 1;
    if (!isDeepStrictEqual(got, want)) {
      this.failures.push(`${label}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`);
    }
  }
}

/** Bits, exact value, ulp and error of each literal. */
export function doubles(dir) {
  const score = new Score("doubles");
  for (const [input, ...want] of load("doubles.tsv", dir)) {
    const s = floats.explain(input);
    score.check(input, [s.bits, s.exact, s.ulp, s.error], want);
  }
  return score;
}

/** The ops table's operation done with Money (b is an integer for *). */
export function moneyOp(a, op, b) {
  if (op === "*") return a.times(BigInt(b));
  const other = Money.parse(b, a.currency);
  return op === "+" ? a.plus(other) : a.minus(other);
}

/** Each float operation, its equality with the true result, and the money result. */
export function ops(dir) {
  const score = new Score("ops");
  for (const [a, op, b, ...want] of load("ops.tsv", dir)) {
    const x = floats.apply(floats.parseLiteral(a), op, floats.parseLiteral(b));
    const same = String(x === Number(floats.trueResult(a, op, b)));
    const cash = moneyOp(Money.parse(a, "USD"), op, b).amount();
    score.check(`${a} ${op} ${b}`, [floats.bits(x), floats.exact(x), same, cash], want);
  }
  return score;
}

/** Naive and Kahan totals and their exact errors. */
export function sums(dir) {
  const score = new Score("sums");
  for (const [summand, nText, ...want] of load("sums.tsv", dir)) {
    const x = floats.parseLiteral(summand);
    const n = Number(nText);
    const naive = floats.naiveSum(x, n);
    const kahan = floats.kahanSum(x, n);
    const got = [floats.bits(naive), floats.sumError(naive, summand, n), floats.bits(kahan), floats.sumError(kahan, summand, n)];
    score.check(`${summand} x ${n}`, got, want);
  }
  return score;
}

/** Result of one money.tsv row as text, or error:<kind>. */
export function moneyCase(op, a, aCur, b, bCur) {
  try {
    if (op === "ofminor") return Money.ofMinor(BigInt(a), aCur).toString();
    const x = Money.parse(a, aCur);
    switch (op) {
      case "parse":
        return x.toString();
      case "minor":
        return x.minor.toString();
      case "negate":
        return x.negate().toString();
      case "times":
        return x.times(BigInt(b)).toString();
      case "plus":
        return x.plus(Money.parse(b, bCur)).toString();
      case "minus":
        return x.minus(Money.parse(b, bCur)).toString();
      case "compare":
        return String(x.compare(Money.parse(b, bCur)));
      default:
        break;
    }
  } catch (err) {
    if (err instanceof MoneyError) return `error:${err.kind}`;
    throw err;
  }
  throw new RangeError(`unknown money op ${op}`);
}

/** Every shared Money case. */
export function money(dir) {
  const score = new Score("money");
  for (const [op, a, aCur, b, bCur, want] of load("money.tsv", dir)) {
    score.check(`${op} ${a} ${aCur} ${b} ${bCur}`, moneyCase(op, a, aCur, b, bCur), want);
  }
  return score;
}

/** The built-in currency table equals currencies.tsv. */
export function currencies(dir) {
  const score = new Score("currencies");
  const rows = load("currencies.tsv", dir);
  score.check("codes", Object.keys(CURRENCIES).sort(), rows.map((r) => r[0]).sort());
  for (const [code, digits] of rows) score.check(code, CURRENCIES[code], Number(digits));
  return score;
}

/** Every suite's score. */
export function report(dir) {
  return [doubles(dir), ops(dir), sums(dir), money(dir), currencies(dir)];
}
