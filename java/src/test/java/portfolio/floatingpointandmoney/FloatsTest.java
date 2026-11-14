package portfolio.floatingpointandmoney;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigDecimal;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class FloatsTest {
    @Test
    void pointOneIsNotOneTenth() {
        Floats.Stored s = Floats.explain("0.1");
        assertEquals("3fb999999999999a", s.bits());
        assertEquals("0.1000000000000000055511151231257827021181583404541015625", s.exact());
        assertEquals("0.0000000000000000055511151231257827021181583404541015625", s.error());
        assertEquals("0.00000000000000001387778780781445675529539585113525390625", s.ulp());
    }

    @Test
    void exactlyRepresentableHasZeroError() {
        assertEquals("0", Floats.explain("0.5").error());
        assertEquals("100", Floats.explain("100").exact());
    }

    @Test
    void integersAboveTwoToThe53Collapse() {
        Floats.Stored s = Floats.explain("9007199254740993");
        assertEquals("9007199254740992", s.exact());
        assertEquals("-1", s.error());
        assertEquals("2", s.ulp());
    }

    @Test
    void doublesVectorsAllAgree() {
        Conformance.Score s = Conformance.doubles(Vectors.defaultDir());
        assertEquals(19, s.cases());
        assertEquals(java.util.List.of(), s.failures());
    }

    @Test
    void opsVectorsAllAgree() {
        Conformance.Score s = Conformance.ops(Vectors.defaultDir());
        assertEquals(13, s.cases());
        assertEquals(java.util.List.of(), s.failures());
    }

    @Test
    void sumsVectorsAllAgree() {
        Conformance.Score s = Conformance.sums(Vectors.defaultDir());
        assertEquals(12, s.cases());
        assertEquals(java.util.List.of(), s.failures());
    }

    @Test
    void famousSum() {
        assertNotEquals(0.3, Floats.apply(0.1, "+", 0.2));
        assertEquals(0.30000000000000004, Floats.apply(0.1, "+", 0.2));
        assertEquals(0, new BigDecimal("0.3").compareTo(Floats.trueResult("0.1", "+", "0.2")));
    }

    @Test
    void naiveSumOfTenTenthsMissesOne() {
        assertEquals(0.9999999999999999, Floats.naiveSum(0.1, 10));
        assertEquals(1.0, Floats.kahanSum(0.1, 10));
        assertTrue(Floats.sumError(Floats.naiveSum(0.1, 10), "0.1", 10).startsWith("-0.000000000000000111"));
        assertEquals(0.0, Floats.naiveSum(0.1, 0));
        assertEquals(0.0, Floats.kahanSum(0.1, 0));
    }

    @Test
    void sumErrorOfExactTotalIsZero() {
        assertEquals("0", Floats.sumError(1.0, "0.25", 4));
    }

    @ParameterizedTest
    @ValueSource(strings = {"", " 1", "1 ", "+1", "1e3", ".5", "5.", "0x10", "NaN", "Infinity", "1,0",
        "١٢", "1d", "1f"})
    void parseLiteralRejectsOtherForms(String bad) {
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class, () -> Floats.parseLiteral(bad));
        assertTrue(e.getMessage().startsWith("not a plain decimal literal"));
    }

    @Test
    void parseLiteralRejectsNullOverlongAndOverflow() {
        assertThrows(IllegalArgumentException.class, () -> Floats.parseLiteral(null));
        assertThrows(IllegalArgumentException.class, () -> Floats.parseLiteral("1".repeat(401)));
        IllegalArgumentException e = assertThrows(IllegalArgumentException.class,
                () -> Floats.parseLiteral("1" + "0".repeat(309)));
        assertTrue(e.getMessage().endsWith("overflows a double"));
    }

    @Test
    void nonFiniteHasNoExactValue() {
        for (double x : new double[] {Double.NaN, Double.POSITIVE_INFINITY, Double.NEGATIVE_INFINITY}) {
            assertThrows(IllegalArgumentException.class, () -> Floats.exact(x));
            assertThrows(IllegalArgumentException.class, () -> Floats.bits(x));
            assertThrows(IllegalArgumentException.class, () -> Floats.ulp(x));
        }
    }

    @Test
    void unknownOp() {
        assertThrows(IllegalArgumentException.class, () -> Floats.apply(1, "/", 2));
        assertThrows(IllegalArgumentException.class, () -> Floats.trueResult("1", "/", "2"));
    }

    @Test
    void sumCountOutOfRange() {
        assertThrows(IllegalArgumentException.class, () -> Floats.naiveSum(0.1, -1));
        assertThrows(IllegalArgumentException.class, () -> Floats.kahanSum(0.1, Floats.MAX_TERMS + 1));
    }

    @Test
    void plainDropsTrailingZerosAndExponent() {
        assertEquals("0", Floats.plain(new BigDecimal("-0.000")));
        assertEquals("1.25", Floats.plain(new BigDecimal("1.2500")));
        assertEquals("1000", Floats.plain(new BigDecimal("1E+3")));
        assertFalse(Floats.exact(1e23).contains("E"));
    }
}
