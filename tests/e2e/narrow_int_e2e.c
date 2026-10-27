/*
 * Narrow (i8/i16/i32) integer semantics end-to-end for LLVM-127t.
 *
 * Since LLVM-127t i8/i16/i32 are legal DADAO types, so the IA's narrow
 * arithmetic/compare/shift instructions are selected directly
 * (add/sub/mul.{sb,sw,st}, div/rem.{ub,uw,ut,sb,sw,st},
 *  shl.{b,w,t}, shr.{ub,uw,ut,sb,sw,st}, cmp.{sb,sw,st,ub,uw,ut}).
 * Their results are always written canonical (`.s*` sign-extends, `.u*`
 * zero-extends, contract-isa.md §10/§11/§12), and every 64-bit consumer
 * extends explicitly (ext.so / ext.uo, contract-abi.md §4.2).
 *
 * The structural half of this contract is pinned by
 * tests/unit/llvm/lit/CodeGen/DADAO/narrow-int.ll and bitops-narrow.ll; this
 * program checks the *values* at run time.  Each failing case returns its own
 * non-zero exit code; 0 means every check passed.
 *
 * The `volatile` seeds keep the operations out of the constant folder.  The
 * expected values are derived from C integer semantics (two's complement
 * wraparound of the narrow type, division truncating toward zero, arithmetic
 * right shift of a negative value), never read back from a toolchain.
 */

/* Assembly probes (tests/e2e/narrow_int_e2e_abi.s): return the *full* 64-bit
 * rd16 argument register, so a caller-side canonical extension is observable
 * (ISS-310).  Declared with the signedness whose extension is under test. */
extern long ext_reg(int x);
extern long ext_reg_u(unsigned int x);

/* The ISS-310 repro shape: an `int` parameter (upper register half not known
 * to the backend) passed straight on.  The call site must canonicalise it. */
long pass_s(int x)
{
    return ext_reg(x);
}

long pass_u(unsigned int x)
{
    return ext_reg_u(x);
}

volatile int seed = 37;
volatile int nseed = -37;
volatile unsigned int useed = 0xdeadbeefu;
volatile short s1 = -20000;
volatile short s2 = 12345;
volatile unsigned short us1 = 40000;
volatile signed char c1 = -100;
volatile signed char c2 = 55;
volatile unsigned char uc1 = 200;
volatile unsigned char uc2 = 100;

int main(void)
{
    /* --- i32 arithmetic (add.st / sub.st / mul.st / div.st / rem.st) ------ */
    int a = seed - 100; /* -63 */
    int b = seed + 11;  /*  48 */

    if (a + b != -15)
        return 1;
    if (a - b != -111)
        return 2;
    if (a * b != -3024)
        return 3;
    if (b / 5 != 9) /* truncate toward zero */
        return 4;
    if (a % 5 != -3) /* remainder takes the dividend's sign */
        return 5;

    /* --- i32 shifts (shl.t / shr.ut / shr.st), variable and constant ----- */
    if ((a << 3) != -504)
        return 6;
    if ((a >> 2) != -16) /* arithmetic */
        return 7;
    if (((unsigned)b >> 2) != 12) /* logical */
        return 8;
    {
        int n = seed & 7; /* 5: runtime amount, not a constant */
        if ((a << n) != -2016) /* -63 << 5 */
            return 9;
        if (((unsigned)b >> n) != 1) /* 48 >> 5 */
            return 10;
        if ((b >> 3) != 6)
            return 11;
    }

    /* --- i16 arithmetic (add.sw / sub.sw / mul.sw / div.sw / rem.sw) ------ */
    {
        short r = (short)(s1 + s2); /* -7655 */
        if (r != -7655)
            return 12;
        r = (short)(s1 - s2); /* -32345 */
        if (r != -32345)
            return 13;
        r = (short)(s1 * s2); /* -246900000 -> low 16 bits */
        if (r != -25888)
            return 14;
        r = (short)(s1 / 7); /* truncate toward zero: -2857 */
        if (r != -2857)
            return 15;
        r = (short)(s1 % 7); /* -1 */
        if (r != -1)
            return 16;
        r = (short)(s1 >> 2); /* arithmetic: -5000 */
        if (r != -5000)
            return 17;
        r = (short)(us1 >> 3); /* 40000 >> 3 = 5000 */
        if (r != 5000)
            return 18;
    }

    /* --- i8 arithmetic (add.sb / sub.sb / mul.sb / div.sb / rem.sb) ------ */
    {
        signed char r = (signed char)(c1 + c2); /* -45 */
        if (r != -45)
            return 19;
        r = (signed char)(c1 - c2); /* -155 -> 101 */
        if (r != 101)
            return 20;
        r = (signed char)(c1 * c2); /* -5500 -> -124 */
        if (r != -124)
            return 21;
        r = (signed char)(c1 / 3); /* -33 */
        if (r != -33)
            return 22;
        r = (signed char)(c1 % 3); /* -1 */
        if (r != -1)
            return 23;
        unsigned char ur = (unsigned char)(uc1 + uc2); /* 300 -> 44 */
        if (ur != 44)
            return 24;
        ur = (unsigned char)(uc1 * 2); /* 400 -> 144 */
        if (ur != 144)
            return 25;
    }

    /* --- i32 compares (cmp.st / cmp.ut), signed and unsigned ------------- */
    if (!(nseed < seed))
        return 26;
    if (!(-1 < 0))
        return 27;
    if (!(useed > 1u))
        return 28; /* top bit set: unsigned compare, not signed */
    if (!(0x80000000u > 0x7fffffffu))
        return 29; /* the exact case little-endian/signed compares get wrong */
    if (!(0xffffffffu > 0x80000000u))
        return 30;
    if (a >= b)
        return 31;
    if (0x7fffffffu >= 0x80000000u)
        return 32;

    /* --- i16/i8 compares ------------------------------------------------ */
    if (!(us1 > (unsigned short)30000))
        return 33;
    if (!(s1 < s2))
        return 34;
    if (!((unsigned char)0xff > (unsigned char)0x7f))
        return 35;
    if (!(c1 < 0))
        return 36;

    /* --- sign/zero extension of narrow values (ext.so / ext.uo) --------- */
    if ((long)a != -63)
        return 37;
    if ((long)(unsigned int)0xffffffffu != 4294967295L)
        return 38;
    if ((long)(short)-2 != -2)
        return 39;
    if ((long)(unsigned short)0xfffe != 65534L)
        return 40;
    if ((long)(signed char)-128 != -128)
        return 41;
    if ((long)(unsigned char)255 != 255L)
        return 42;

    /* --- ABI canonical extension (ISS-310) ------------------------------ */
    /* The callee returns the full rd16 register: a signed `int` argument must
     * arrive sign-extended (0xFFFF...FFFF for -1), an unsigned one
     * zero-extended (contract-abi.md §4.2 "保持符号位不变"). */
    if (ext_reg(-1) != -1L)
        return 43;
    if (ext_reg(-2147483647 - 1) != -2147483648L)
        return 44;
    if (ext_reg(0x12345678) != 0x12345678L)
        return 45;
    if (ext_reg_u(0xffffffffu) != 4294967295L)
        return 46;
    if (ext_reg_u(0x80000000u) != 2147483648L)
        return 47;
    /* A runtime (volatile) argument forces the extension into a real
     * instruction, which the assembly check in narrow_int_e2e.test pins. */
    if (ext_reg(nseed) != -37L)
        return 48;
    if (ext_reg_u(useed) != 0xdeadbeefL)
        return 49;
    /* The same through a parameter (the ISS-310 `int f(int x){ ext(x,...); }`
     * shape): the backend must extend the parameter at the call site. */
    if (pass_s(-1) != -1L)
        return 50;
    if (pass_s(-2147483647 - 1) != -2147483648L)
        return 51;
    if (pass_u(0xffffffffu) != 4294967295L)
        return 52;

    return 0;
}
