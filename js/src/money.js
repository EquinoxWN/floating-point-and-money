// Money as a BigInt count of minor units (cents) plus a currency; numbers with fractions are refused.

/** ISO 4217 minor-unit digits of the supported currencies (checked against currencies.tsv). */
export const CURRENCIES = Object.freeze({ USD: 2, EUR: 2, GBP: 2, JPY: 0, KWD: 3 });

/** Same range in every language: signed 64-bit minor units, symmetric so negate never overflows. */
export const MAX_MINOR = 2n ** 63n - 1n;
export const MAX_TEXT = 64;
const AMOUNT = /^(-?)([0-9]+)(?:\.([0-9]+))?$/;

/** A money operation was refused; kind is parse, currency, overflow or mismatch. */
export class MoneyError extends Error {
  /** New refusal of the given kind. */
  constructor(kind, message) {
    super(message);
    this.name = "MoneyError";
    this.kind = kind;
  }
}

/** Minor-unit digits of a supported currency code. */
function digitsOf(currency) {
  if (typeof currency !== "string") throw new TypeError(`currency must be a string, not ${typeof currency}`);
  if (!Object.hasOwn(CURRENCIES, currency)) {
    throw new MoneyError("currency", `unsupported currency ${JSON.stringify(currency.slice(0, 8))}`);
  }
  return CURRENCIES[currency];
}

/** A BigInt, or a Number that is a safe integer, as BigInt. */
function integer(value, what) {
  if (typeof value === "bigint") return value;
  if (typeof value === "number" && Number.isSafeInteger(value)) return BigInt(value);
  throw new TypeError(`${what} must be a bigint or a safe integer, not ${String(value).slice(0, 40)}`);
}

/** Fail on results outside the shared minor-unit range. */
function checked(minor) {
  if (minor > MAX_MINOR || minor < -MAX_MINOR) {
    throw new MoneyError("overflow", "amount outside the signed 64-bit minor-unit range");
  }
  return minor;
}

/** An exact amount: BigInt minor units and an ISO 4217 currency code. */
export class Money {
  #minor;
  #currency;

  /** Use Money.ofMinor or Money.parse. */
  constructor(minor, currency) {
    digitsOf(currency);
    this.#minor = checked(integer(minor, "minor"));
    this.#currency = currency;
    Object.freeze(this);
  }

  /** Amount from a count of minor units, e.g. 1234n USD cents. */
  static ofMinor(minor, currency) {
    return new Money(minor, currency);
  }

  /** Amount from plain decimal text; more fraction digits than the currency has is an error. */
  static parse(text, currency) {
    if (typeof text !== "string") {
      throw new TypeError(`amount must be a string, not ${typeof text}; floats are not money`);
    }
    const digits = digitsOf(currency);
    const m = text.length <= MAX_TEXT ? AMOUNT.exec(text) : null;
    if (m === null) {
      throw new MoneyError("parse", `not a plain decimal amount: ${JSON.stringify(text.slice(0, MAX_TEXT))}`);
    }
    const frac = m[3] ?? "";
    if (frac.length > digits) {
      throw new MoneyError("parse", `${currency} has ${digits} minor digits, got ${frac.length}`);
    }
    const minor = BigInt(m[2] + frac.padEnd(digits, "0"));
    return new Money(checked(m[1] ? -minor : minor), currency);
  }

  /** Sum of amounts in one currency (zero when empty). */
  static total(items, currency) {
    let acc = new Money(0n, currency);
    for (const item of items) acc = acc.plus(item);
    return acc;
  }

  /** Minor units as a BigInt. */
  get minor() {
    return this.#minor;
  }

  /** ISO 4217 code. */
  get currency() {
    return this.#currency;
  }

  /** Other operand, checked to be Money in this currency. */
  #same(other) {
    if (!(other instanceof Money)) throw new TypeError("expected Money");
    if (other.currency !== this.#currency) {
      throw new MoneyError("mismatch", `${this.#currency} and ${other.currency} do not mix`);
    }
    return other;
  }

  /** Exact sum in the same currency. */
  plus(other) {
    return new Money(checked(this.#minor + this.#same(other).minor), this.#currency);
  }

  /** Exact difference in the same currency. */
  minus(other) {
    return new Money(checked(this.#minor - this.#same(other).minor), this.#currency);
  }

  /** Exact product with an integer quantity. */
  times(quantity) {
    return new Money(checked(this.#minor * integer(quantity, "quantity")), this.#currency);
  }

  /** Same amount with the opposite sign. */
  negate() {
    return new Money(-this.#minor, this.#currency);
  }

  /** -1, 0 or 1; amounts in different currencies are not comparable. */
  compare(other) {
    const o = this.#same(other).minor;
    return this.#minor < o ? -1 : this.#minor > o ? 1 : 0;
  }

  /** Same amount and currency. */
  equals(other) {
    return other instanceof Money && other.currency === this.#currency && other.minor === this.#minor;
  }

  /** Plain decimal text with exactly the currency's minor digits. */
  amount() {
    const digits = CURRENCIES[this.#currency];
    const neg = this.#minor < 0n;
    const abs = (neg ? -this.#minor : this.#minor).toString();
    const sign = neg ? "-" : "";
    if (digits === 0) return sign + abs;
    const padded = abs.padStart(digits + 1, "0");
    return `${sign}${padded.slice(0, -digits)}.${padded.slice(-digits)}`;
  }

  /** Canonical text such as 12.34 USD. */
  toString() {
    return `${this.amount()} ${this.#currency}`;
  }

  /** JSON as the canonical text. */
  toJSON() {
    return this.toString();
  }

  /** Refuse implicit arithmetic (m1 + m2, m > 0), which would silently use strings or NaN. */
  valueOf() {
    throw new TypeError("Money has no primitive value; use plus, minus, compare");
  }
}
