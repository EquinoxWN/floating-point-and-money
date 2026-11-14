import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, test } from "node:test";
import { run } from "../src/cli.js";
import * as conformance from "../src/conformance.js";
import * as floats from "../src/floats.js";
import { defaultDir, load, MAX_BYTES, VectorError } from "../src/vectors.js";

const tmpRoot = mkdtempSync(join(tmpdir(), "fpm-js-"));
after(() => rmSync(tmpRoot, { recursive: true, force: true }));
let tmpCount = 0;

/** Fresh temp dir, optionally with copies of the shared vectors. */
function tmpDir(copy = false) {
  const dir = join(tmpRoot, String(tmpCount++));
  mkdirSync(dir, { recursive: true });
  if (copy) {
    for (const f of readdirSync(defaultDir()).filter((n) => n.endsWith(".tsv"))) {
      writeFileSync(join(dir, f), readFileSync(join(defaultDir(), f)));
    }
  }
  return dir;
}

/** Replace the first occurrence of a text in one copied file. */
function corrupt(dir, name, from, to) {
  const p = join(dir, name);
  const text = readFileSync(p, "utf8");
  assert.ok(text.includes(from), from);
  writeFileSync(p, text.replace(from, to));
}

/** Output and status of one CLI run. */
function cli(...args) {
  const out = [];
  const err = [];
  const status = run(args, (l) => out.push(l), (l) => err.push(l));
  return { status, out: `${out.join("\n")}\n`, err: err.join("\n") };
}

test("0.1 is not one tenth", () => {
  const s = floats.explain("0.1");
  assert.equal(s.bits, "3fb999999999999a");
  assert.equal(s.exact, "0.1000000000000000055511151231257827021181583404541015625");
  assert.equal(s.error, "0.0000000000000000055511151231257827021181583404541015625");
  assert.equal(s.ulp, "0.00000000000000001387778780781445675529539585113525390625");
});

test("integers above 2^53 collapse", () => {
  const s = floats.explain("9007199254740993");
  assert.deepEqual([s.exact, s.error, s.ulp], ["9007199254740992", "-1", "2"]);
  assert.equal(floats.explain("0.5").error, "0");
});

test("negative literal keeps sign, ulp stays positive", () => {
  const s = floats.explain("-0.1");
  assert.ok(s.exact.startsWith("-0.1000000000000000055"));
  assert.ok(!s.ulp.startsWith("-"));
});

test("subnormal values have an exact expansion", () => {
  assert.equal(floats.bits(5e-324), "0000000000000001");
  assert.ok(floats.exact(5e-324).startsWith("0.00000"));
  assert.equal(floats.ulp(5e-324), floats.exact(5e-324));
});

for (const [suite, cases] of [
  ["doubles", 19],
  ["ops", 13],
  ["sums", 12],
]) {
  test(`${suite} vectors all agree`, () => {
    const s = conformance[suite]();
    assert.equal(s.cases, cases);
    assert.deepEqual(s.failures, []);
  });
}

test("famous sum and ten tenths", () => {
  assert.equal(floats.apply(0.1, "+", 0.2), 0.30000000000000004);
  assert.equal(floats.trueResult("0.1", "+", "0.2"), "0.3");
  assert.equal(floats.naiveSum(0.1, 10), 0.9999999999999999);
  assert.equal(floats.kahanSum(0.1, 10), 1);
  assert.equal(floats.naiveSum(0.1, 0), 0);
  assert.equal(floats.sumError(1, "0.25", 4), "0");
});

for (const bad of ["", " 1", "1 ", "+1", "1e3", ".5", "5.", "0x10", "NaN", "Infinity", "1,0", "١٢", "1".repeat(401)]) {
  test(`parseLiteral rejects ${JSON.stringify(bad.slice(0, 10))}`, () => {
    assert.throws(() => floats.parseLiteral(bad), /not a plain decimal literal/);
  });
}

test("parseLiteral rejects overflow and non-strings", () => {
  assert.throws(() => floats.parseLiteral(`1${"0".repeat(309)}`), /overflows a double/);
  assert.throws(() => floats.parseLiteral(0.1), TypeError);
});

test("non-finite and non-numbers have no exact value", () => {
  for (const x of [Number.NaN, Infinity, -Infinity]) {
    assert.throws(() => floats.exact(x), RangeError);
    assert.throws(() => floats.bits(x), RangeError);
    assert.throws(() => floats.ulp(x), RangeError);
  }
  assert.throws(() => floats.bits(1n), TypeError);
});

test("unknown op and bad counts", () => {
  assert.throws(() => floats.apply(1, "/", 2), /unknown op/);
  assert.throws(() => floats.trueResult("1", "/", "2"), /unknown op/);
  assert.throws(() => floats.naiveSum(0.1, -1), RangeError);
  assert.throws(() => floats.kahanSum(0.1, floats.MAX_TERMS + 1), RangeError);
  assert.throws(() => floats.naiveSum(0.1, 1.5), TypeError);
});

test("plain drops trailing zeros", () => {
  assert.equal(floats.plain({ n: 0n, s: 3 }), "0");
  assert.equal(floats.plain({ n: 12500n, s: 4 }), "1.25");
  assert.equal(floats.plain({ n: -5n, s: 3 }), "-0.005");
});

test("every suite passes on the committed vectors", () => {
  const scores = conformance.report();
  assert.deepEqual(
    scores.map((s) => s.suite),
    ["doubles", "ops", "sums", "money", "currencies"],
  );
  for (const s of scores) assert.ok(s.cases > 0 && s.failures.length === 0, s.suite);
});

test("loader errors", () => {
  const dir = tmpDir();
  assert.throws(() => load("money.tsv", dir), (e) => e instanceof VectorError && e.message.includes("money.tsv"));
  assert.throws(() => load("../secrets.tsv", dir), /unknown vector file/);
  writeFileSync(join(dir, "sums.tsv"), "# c\n0.1\t10\n");
  assert.throws(() => load("sums.tsv", dir), /sums\.tsv:2: 2 columns, want 6/);
  writeFileSync(join(dir, "ops.tsv"), Buffer.alloc(MAX_BYTES + 1));
  assert.throws(() => load("ops.tsv", dir), /larger than/);
  writeFileSync(join(dir, "currencies.tsv"), "# only comments\n\n");
  assert.throws(() => load("currencies.tsv", dir), /no rows/);
});

test("wrong expected values are counted", () => {
  const dir = tmpDir(true);
  corrupt(dir, "doubles.tsv", "3fb999999999999a", "3fb9999999999999");
  corrupt(dir, "ops.tsv", "\t1999.00\n", "\t1998.99\n");
  corrupt(dir, "sums.tsv", "\t3ff0000000000000\t0\n", "\t3fefffffffffffff\t0\n");
  corrupt(dir, "currencies.tsv", "KWD\t3", "KWD\t2");
  for (const s of conformance.report(dir)) {
    assert.equal(s.failures.length, s.suite === "money" ? 0 : 1, s.suite);
  }
});

test("cli explain, ops, sums, report", () => {
  const ex = cli("explain", "0.1");
  assert.equal(ex.status, 0);
  assert.ok(ex.out.includes("bits\t3fb999999999999a\n"));
  const ops = cli("ops");
  assert.ok(ops.out.includes("0.1 + 0.2\t0.30000000000000004\tfalse\t0.30 USD\n"));
  assert.ok(ops.out.includes("19.99 * 100\t1998.9999999999998\tfalse\t1999.00 USD\n"));
  const sums = cli("sums");
  assert.ok(sums.out.includes("0.1\t10\t0.9999999999999999\t-0.00000000000000011102230246251565404236316680908203125\t0\n"));
  const rep = cli("report");
  assert.equal(rep.status, 0);
  assert.ok(rep.out.includes("js\tmoney\t78\t78\n"));
});

test("cli report fails on wrong vectors, and errors", () => {
  const dir = tmpDir(true);
  corrupt(dir, "money.tsv", "12.34 USD\n", "12.35 USD\n");
  const rep = cli("--vectors", dir, "report");
  assert.equal(rep.status, 1);
  assert.ok(rep.out.includes("js\tmoney\t77\t78\n"));
  assert.ok(rep.err.includes('want "12.35 USD"'));
  const bad = cli("explain", "1e3");
  assert.equal(bad.status, 1);
  assert.ok(bad.err.startsWith("error: not a plain decimal literal"));
  assert.equal(cli("--vectors", join(dir, "nope"), "ops").status, 1);
  assert.equal(cli().status, 2);
  assert.equal(cli("divide").status, 2);
});
