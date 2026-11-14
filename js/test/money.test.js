import assert from "node:assert/strict";
import { test } from "node:test";
import * as conformance from "../src/conformance.js";
import { CURRENCIES, MAX_MINOR, Money, MoneyError } from "../src/money.js";
import { load } from "../src/vectors.js";

const CASES = load("money.tsv");

for (const [op, a, aCur, b, bCur, want] of CASES) {
  test(`${op} ${a} ${aCur} ${b} ${bCur} -> ${want}`, () => {
    assert.equal(conformance.moneyCase(op, a, aCur, b, bCur), want);
  });
}

/** Assert fn throws MoneyError of the given kind. */
function refused(fn, kind) {
  assert.throws(fn, (e) => e instanceof MoneyError && e.kind === kind);
}

test("shared cases cover every error kind", () => {
  const kinds = new Set(CASES.map((r) => r[5]).filter((w) => w.startsWith("error:")));
  assert.deepEqual([...kinds].sort(), ["error:currency", "error:mismatch", "error:overflow", "error:parse"]);
  assert.equal(CASES.length, 78);
});

test("currency table matches the shared file", () => {
  assert.deepEqual(conformance.currencies().failures, []);
});

test("floats are refused", () => {
  assert.throws(() => Money.parse(0.1, "USD"), /floats are not money/);
  assert.throws(() => Money.ofMinor(10.5, "USD"), TypeError);
  assert.throws(() => Money.ofMinor(2 ** 53, "USD"), TypeError);
  assert.throws(() => Money.parse("1.00", "USD").times(1.5), TypeError);
  assert.equal(Money.ofMinor(1234, "USD").toString(), "12.34 USD");
});

test("implicit coercion is refused", () => {
  const a = Money.parse("0.10", "USD");
  assert.throws(() => a + a, TypeError);
  assert.throws(() => a > 0, TypeError);
  assert.equal(`${a}`, "0.10 USD");
  assert.equal(JSON.stringify({ a }), '{"a":"0.10 USD"}');
});

test("inputs are validated", () => {
  assert.throws(() => Money.parse("1", null), TypeError);
  assert.throws(() => Money.parse("1", "USD").plus(1), TypeError);
  refused(() => new Money(MAX_MINOR + 1n, "USD"), "overflow");
  refused(() => new Money(1n, "ABC"), "currency");
  refused(() => new Money(1n, "toString"), "currency");
  refused(() => Money.parse("1".repeat(65), "USD"), "parse");
  refused(() => Money.parse("", "USD"), "parse");
});

test("instances are immutable", () => {
  const a = Money.parse("1", "JPY");
  assert.ok(Object.isFrozen(a));
  assert.throws(() => {
    a.extra = 1;
  }, TypeError);
});

test("equality includes currency", () => {
  assert.ok(!Money.ofMinor(100n, "USD").equals(Money.ofMinor(100n, "EUR")));
  assert.ok(Money.ofMinor(5n, "JPY").equals(Money.parse("5", "JPY")));
  assert.ok(!Money.ofMinor(5n, "JPY").equals("5 JPY"));
});

test("total of ten dimes is one dollar", () => {
  const dime = Money.parse("0.10", "USD");
  assert.equal(Money.total(Array(10).fill(dime), "USD").toString(), "1.00 USD");
  assert.equal(Money.total([], "KWD").toString(), "0.000 KWD");
  refused(() => Money.total([dime], "EUR"), "mismatch");
});

/** splitmix64: a seeded 64-bit generator. */
function* splitmix(seed) {
  let s = BigInt(seed);
  const mask = (1n << 64n) - 1n;
  for (;;) {
    s = (s + 0x9e3779b97f4a7c15n) & mask;
    let z = s;
    z = ((z ^ (z >> 30n)) * 0xbf58476d1ce4e5b9n) & mask;
    z = ((z ^ (z >> 27n)) * 0x94d049bb133111ebn) & mask;
    yield z ^ (z >> 31n);
  }
}

test("random invariants", () => {
  const rng = splitmix(20261114);
  const next = () => rng.next().value;
  const random = (currency) => {
    const bound = 10n ** (next() % 19n);
    const v = next() % (bound > MAX_MINOR ? MAX_MINOR : bound + 1n);
    return Money.ofMinor(next() & 1n ? -v : v, currency);
  };
  for (const currency of Object.keys(CURRENCIES).sort()) {
    const digits = CURRENCIES[currency];
    for (let i = 0; i < 2000; i++) {
      const a = random(currency);
      const b = random(currency);
      assert.ok(Money.parse(a.amount(), currency).equals(a));
      assert.equal(a.amount().replace(".", "").replace(/^(-?)0+(?=\d)/, "$1"), a.minor.toString());
      assert.equal(a.compare(b) + b.compare(a), 0);
      const sum = a.minor + b.minor;
      if (sum > MAX_MINOR || sum < -MAX_MINOR) {
        refused(() => a.plus(b), "overflow");
        continue;
      }
      const total = a.plus(b);
      assert.equal(total.minor, sum);
      assert.ok(total.minus(b).equals(a));
      assert.equal(total.amount().split(".")[1]?.length ?? 0, digits);
    }
  }
});
