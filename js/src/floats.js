// Experiments: how a decimal literal is stored as a double, and how errors grow in sums.

export const MAX_LITERAL = 400;
export const MAX_TERMS = 10_000_000;
const LITERAL = /^-?[0-9]+(\.[0-9]+)?$/;
const view = new DataView(new ArrayBuffer(8));

/** Exact decimal n / 10^s with a BigInt n. */
function dec(n, s) {
  return { n, s };
}

/** Exact decimal value of a plain literal. */
export function decimalOf(text) {
  const [whole, frac = ""] = text.replace("-", "").split(".");
  const n = BigInt(whole + frac);
  return dec(text.startsWith("-") ? -n : n, frac.length);
}

/** Two decimals brought to the same scale. */
function align(a, b) {
  const s = Math.max(a.s, b.s);
  return [a.n * 10n ** BigInt(s - a.s), b.n * 10n ** BigInt(s - b.s), s];
}

/** Exact a + b. */
export function add(a, b) {
  const [x, y, s] = align(a, b);
  return dec(x + y, s);
}

/** Exact a - b. */
export function sub(a, b) {
  const [x, y, s] = align(a, b);
  return dec(x - y, s);
}

/** Exact a * b. */
export function mul(a, b) {
  return dec(a.n * b.n, a.s + b.s);
}

/** Decimal as plain text without exponent or trailing zeros. */
export function plain(d) {
  if (d.n === 0n) return "0";
  const neg = d.n < 0n;
  let digits = (neg ? -d.n : d.n).toString();
  let s = d.s;
  while (s > 0 && digits.endsWith("0")) {
    digits = digits.slice(0, -1);
    s -= 1;
  }
  if (s > 0) {
    digits = digits.padStart(s + 1, "0");
    digits = `${digits.slice(0, -s)}.${digits.slice(-s)}`;
  }
  return (neg ? "-" : "") + digits;
}

/** Reject non-numbers, NaN and infinities, which have no exact decimal value. */
function finite(x) {
  if (typeof x !== "number") throw new TypeError(`expected number, not ${typeof x}`);
  if (!Number.isFinite(x)) throw new RangeError(`${x} has no exact decimal value`);
  return x;
}

/** Raw 64-bit pattern of a double. */
function raw(x) {
  view.setFloat64(0, finite(x));
  return view.getBigUint64(0);
}

/** Exact value of mant * 2^exp. */
function pow2(mant, exp) {
  return exp >= 0 ? dec(mant << BigInt(exp), 0) : dec(mant * 5n ** BigInt(-exp), -exp);
}

/** Exact decimal of the double x. */
function exactDec(x) {
  const r = raw(x);
  const e = Number((r >> 52n) & 0x7ffn);
  const f = r & ((1n << 52n) - 1n);
  const d = e === 0 ? pow2(f, -1074) : pow2(f | (1n << 52n), e - 1075);
  return r >> 63n ? dec(-d.n, d.s) : d;
}

/** Plain decimal literal to the nearest double; rejects other forms and overflow. */
export function parseLiteral(text) {
  if (typeof text !== "string") throw new TypeError(`literal must be a string, not ${typeof text}`);
  if (text.length > MAX_LITERAL || !LITERAL.test(text)) {
    throw new RangeError(`not a plain decimal literal: ${JSON.stringify(text.slice(0, 40))}`);
  }
  const x = Number(text);
  if (!Number.isFinite(x)) throw new RangeError(`${text.slice(0, 40)} overflows a double`);
  return x;
}

/** IEEE 754 binary64 bit pattern as 16 hex digits. */
export function bits(x) {
  return raw(x).toString(16).padStart(16, "0");
}

/** Exact decimal value of the double x. */
export function exact(x) {
  return plain(exactDec(x));
}

/** Exact gap between |x| and the next larger double. */
export function ulp(x) {
  const e = Number((raw(x) >> 52n) & 0x7ffn);
  return plain(pow2(1n, e === 0 ? -1074 : e - 1075));
}

/** Bits, exact stored value, ulp and representation error of a literal. */
export function explain(text) {
  const x = parseLiteral(text);
  return { input: text, bits: bits(x), exact: exact(x), ulp: ulp(x), error: plain(sub(exactDec(x), decimalOf(text))) };
}

/** One double operation: +, - or *. */
export function apply(a, op, b) {
  if (op === "+") return a + b;
  if (op === "-") return a - b;
  if (op === "*") return a * b;
  throw new RangeError(`unknown op ${op}`);
}

/** Exact decimal result of a op b on the literals, as plain text. */
export function trueResult(a, op, b) {
  const x = decimalOf(a);
  const y = decimalOf(b);
  if (op === "+") return plain(add(x, y));
  if (op === "-") return plain(sub(x, y));
  if (op === "*") return plain(mul(x, y));
  throw new RangeError(`unknown op ${op}`);
}

/** Validate a repetition count. */
function terms(n) {
  if (!Number.isInteger(n)) throw new TypeError("n must be an integer");
  if (n < 0 || n > MAX_TERMS) throw new RangeError(`n must be in 0..${MAX_TERMS}`);
  return n;
}

/** Add x to a running double total n times. */
export function naiveSum(x, n) {
  let total = 0;
  for (let i = terms(n); i > 0; i--) total += x;
  return total;
}

/** Add x n times with Kahan's compensated summation. */
export function kahanSum(x, n) {
  let total = 0;
  let comp = 0;
  for (let i = terms(n); i > 0; i--) {
    const y = x - comp;
    const t = total + y;
    comp = t - total - y;
    total = t;
  }
  return total;
}

/** Exact signed error of a double total against n times the literal. */
export function sumError(total, summand, n) {
  return plain(sub(exactDec(total), mul(decimalOf(summand), dec(BigInt(n), 0))));
}
