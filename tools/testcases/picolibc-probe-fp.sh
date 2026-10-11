#!/usr/bin/env bash
# picolibc-probe FP harness (measurement only; writes nothing into the repo).
#
# Canonical location: tools/testcases/ (LLVM-080t rework; previously only under the
# gitignored .work/log/testcases/).  Reconstructed from the original probe inputs
# (/tmp/opencode/picolibc-probe/fp/*.c, which produced .work/log/testcases/picolibc-probe-fp.log);
# the driver itself was not persisted, so the snippets are embedded here to make the
# probe self-contained and re-runnable.  The probe set / labels / flags /
# classification match the original log.  Writes only under $OUT.
#
# For each probe it compiles with the DADAO clang at -O0/-O1/-O2 and classifies:
#   OK              rc == 0
#   CANNOT_SELECT   "Cannot select" (ISel gap)
#   NOLIBCALL       "no libcall available for ..." (DAG libcall gap)
#   ERROR           any other failure
CLANG=${CLANG:-/mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin/clang}
OUT=${OUT:-/tmp/opencode/picolibc-probe/fp}
mkdir -p "$OUT"

emit() { printf '%s\n' "$2" > "$OUT/$1.c"; }

#if defined probe set (name -> body)
emit cmp_dbl_eq      'int f(double x,double y){return x==y;}'
emit cmp_dbl_lt0     'int f(double x){return x<0.0;}'
emit cmp_dbl_store   'int r; void f(double x,double y){r=(x==y);}'
emit cmp_flt_eq      'int f(float x,float y){return x==y;}'
emit fabs_d          'double f(double x){return __builtin_fabs(x);}'
emit fabs_f          'float f(float x){return __builtin_fabsf(x);}'
emit copysign_d      'double f(double a,double b){return __builtin_copysign(a,b);}'
emit copysign_f      'float f(float a,float b){return __builtin_copysignf(a,b);}'
emit floor_d         'double f(double x){return __builtin_floor(x);}'
emit ceil_d          'double f(double x){return __builtin_ceil(x);}'
emit trunc_d         'double f(double x){return __builtin_trunc(x);}'
emit round_d         'double f(double x){return __builtin_round(x);}'
emit rint_d          'double f(double x){return __builtin_rint(x);}'
emit nearbyint_d     'double f(double x){return __builtin_nearbyint(x);}'
emit fma_d           'double f(double a,double b,double c){return __builtin_fma(a,b,c);}'
emit fmin_d          'double f(double a,double b){return __builtin_fmin(a,b);}'
emit fmax_d          'double f(double a,double b){return __builtin_fmax(a,b);}'
emit fmin_f          'float f(float a,float b){return __builtin_fminf(a,b);}'
emit isnan_d         'int f(double x){return __builtin_isnan(x);}'
emit isinf_d         'int f(double x){return __builtin_isinf(x);}'
emit isfinite_d      'int f(double x){return __builtin_isfinite(x);}'
emit signbit_d       'int f(double x){return __builtin_signbit(x);}'
emit fld2dbl_load    'double f(float *p){return *p;}'
emit fld2dbl_cast    'double f(float x){return x;}'
emit dbl2flt_cast    'float f(double x){return x;}'
emit dbl2int         'long f(double x){return (long)x;}'
emit int2dbl         'double f(long x){return (double)x;}'
emit u64_2dbl        'double f(unsigned long x){return (double)x;}'
emit i64_div         'long f(long a,long b){return a/b;}'
emit u64_div         'unsigned long f(unsigned long a,unsigned long b){return a/b;}'
emit i128_mul        '__int128 f(__int128 a,__int128 b){return a*b;}'
emit ldbl_arith      'long double f(long double a,long double b){return a*b;}'
emit ldbl_cmp        'int f(long double a,long double b){return a==b;}'
emit dbl_arith       'double f(double a,double b){return a*b+a/b-a+b;}'
emit flt_arith       'float f(float a,float b){return a*b+a/b-a+b;}'
emit dbl_sqrt        'double f(double x){return __builtin_sqrt(x);}'
emit bitcast_f32     'int f(float x){union{float f;int i;}u;u.f=x;return u.i;}'
emit bitcast_f64     'long f(double x){union{double d;long i;}u;u.d=x;return u.i;}'

classify() {
  local errf="$1"
  if grep -q "Cannot select" "$errf"; then echo "CANNOT_SELECT"; return; fi
  if grep -q "no libcall available" "$errf"; then echo "NOLIBCALL"; return; fi
  if grep -q "error" "$errf"; then echo "ERROR"; return; fi
  echo "OTHER"
}

for c in "$OUT"/*.c; do
  [ -e "$c" ] || continue
  name=$(basename "$c" .c)
  line="$name"
  for opt in O0 O1 O2; do
    errf="$OUT/.err.$name.$opt"
    timeout 60 "$CLANG" -target dadao-unknown-elf -ffreestanding -fno-builtin \
      "-$opt" -c "$c" -o /dev/null >"$errf" 2>&1
    rc=$?
    cls="OK"; [ $rc -ne 0 ] && cls=$(classify "$errf")
    line="$line $opt=$cls"
  done
  echo "$line"
done
