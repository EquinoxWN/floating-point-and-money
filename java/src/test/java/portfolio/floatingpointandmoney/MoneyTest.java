package portfolio.floatingpointandmoney;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.lang.reflect.Method;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Random;
import java.util.Set;
import java.util.TreeSet;
import java.util.stream.Collectors;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

class MoneyTest {
    /** Rows of money.tsv as test arguments. */
    static Stream<Arguments> cases() {
        return Vectors.load(Vectors.defaultDir(), "money.tsv").stream().map(r -> Arguments.of((Object[]) r));
    }

    @ParameterizedTest(name = "{0} {1} {2} {3} {4} -> {5}")
    @MethodSource("cases")
    void sharedCase(String op, String a, String aCur, String b, String bCur, String want) {
        assertEquals(want, Conformance.moneyCase(op, a, aCur, b, bCur));
    }

    @Test
    void sharedCasesCoverEveryErrorKind() {
        Set<String> kinds = cases().map(a -> (String) a.get()[5]).filter(s -> s.startsWith("error:"))
                .collect(Collectors.toCollection(TreeSet::new));
        assertEquals(Set.of("error:parse", "error:currency", "error:overflow", "error:mismatch"), kinds);
        assertEquals(78, cases().count());
    }

    @Test
    void currencyTableMatchesSharedFile() {
        assertEquals(List.of(), Conformance.currencies(Vectors.defaultDir()).failures());
    }

    @Test
    void noMethodAcceptsAFloatingPointValue() {
        for (Method m : Money.class.getDeclaredMethods()) {
            for (Class<?> p : m.getParameterTypes()) {
                assertTrue(p != double.class && p != float.class && p != Double.class && p != Float.class
                        && p != BigDecimal.class, m.toString());
            }
        }
    }

    @Test
    void directConstructionIsValidated() {
        assertEquals(MoneyException.Kind.OVERFLOW,
                assertThrows(MoneyException.class, () -> new Money(Long.MIN_VALUE, "USD")).kind());
        assertEquals(MoneyException.Kind.CURRENCY,
                assertThrows(MoneyException.class, () -> new Money(1, "ABC")).kind());
        assertThrows(NullPointerException.class, () -> new Money(1, null));
        assertThrows(NullPointerException.class, () -> Money.parse(null, "USD"));
    }

    @Test
    void overlongAndEmptyTextAreParseErrors() {
        assertEquals(MoneyException.Kind.PARSE,
                assertThrows(MoneyException.class, () -> Money.parse("1".repeat(65), "USD")).kind());
        assertEquals(MoneyException.Kind.PARSE,
                assertThrows(MoneyException.class, () -> Money.parse("", "USD")).kind());
    }

    @Test
    void equalityIncludesCurrency() {
        assertNotEquals(Money.ofMinor(100, "USD"), Money.ofMinor(100, "EUR"));
        assertEquals(Money.ofMinor(5, "JPY"), Money.parse("5", "JPY"));
        assertEquals(Money.ofMinor(5, "JPY").hashCode(), Money.parse("5", "JPY").hashCode());
    }

    @Test
    void sortingAmountsInOneCurrency() {
        List<Money> list = Arrays.asList(Money.parse("0.10", "USD"), Money.parse("-1", "USD"),
                Money.parse("0.09", "USD"));
        Collections.sort(list);
        assertEquals("[-1.00 USD, 0.09 USD, 0.10 USD]", list.toString());
    }

    @Test
    void totalOfTenDimesIsOneDollar() {
        Money dime = Money.parse("0.10", "USD");
        assertEquals("1.00 USD", Money.total(Collections.nCopies(10, dime), "USD").toString());
        assertEquals("0.000 KWD", Money.total(List.of(), "KWD").toString());
        assertThrows(MoneyException.class, () -> Money.total(List.of(dime), "EUR"));
    }

    @Test
    void randomInvariants() {
        Random rng = new Random(20261114L);
        BigInteger max = BigInteger.valueOf(Long.MAX_VALUE);
        for (String currency : new TreeSet<>(Money.CURRENCIES.keySet())) {
            BigDecimal scale = BigDecimal.ONE.movePointLeft(Money.CURRENCIES.get(currency));
            for (int i = 0; i < 2_000; i++) {
                Money a = random(rng, currency);
                Money b = random(rng, currency);
                assertEquals(a, Money.parse(a.amount(), currency));
                assertEquals(0, new BigDecimal(a.amount()).compareTo(BigDecimal.valueOf(a.minor()).multiply(scale)));
                assertEquals(a.compareTo(b), -b.compareTo(a));
                BigInteger sum = BigInteger.valueOf(a.minor()).add(BigInteger.valueOf(b.minor()));
                if (sum.abs().compareTo(max) > 0) {
                    assertEquals(MoneyException.Kind.OVERFLOW,
                            assertThrows(MoneyException.class, () -> a.plus(b)).kind());
                    continue;
                }
                Money total = a.plus(b);
                assertEquals(0, new BigDecimal(total.amount())
                        .compareTo(new BigDecimal(a.amount()).add(new BigDecimal(b.amount()))));
                assertEquals(a, total.minus(b));
            }
        }
    }

    /** Amount spread over small and huge magnitudes. */
    private static Money random(Random rng, String currency) {
        int digits = rng.nextInt(19);
        long bound = digits == 18 ? Long.MAX_VALUE : (long) Math.pow(10, digits);
        long v = rng.nextLong(bound) + (rng.nextBoolean() ? 1 : 0);
        return Money.ofMinor(rng.nextBoolean() ? -v : v, currency);
    }
}
