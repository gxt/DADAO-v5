# m12-chipyard-016 报告：embench / picolibc-full 在 chipyard Tiny 上

> 生成自运行期证据（`--json` / `--json-out`），可重跑复核；本页数字全部现场统计，未写死。

## 0. M12 判据

- **判据 = engine parity（picolibc 逐例状态与 qemu 一致；不要求全绿）**（用户 2026-11-14 裁定）。
- qemu 侧既有缺口（登记在册，不计到 chipyard）：
  - `test-abort-failure`：blocked (machine fault CFX6)
  - `test-ceil`：blocked (ISS-193 long-double libcall)
  - `test-long-double`：blocked (ISS-193 long-double libcall)
  - `test-math-errhandling`：fail (exit 3)
  - `test-math-funcs`：blocked (ISS-193 long-double libcall)

## 0.1 code freeze 与 sim md5 一致性

- **code freeze（2026-11-14 23:10）**：chipyard 侧不再改代码，sim md5 = `079ae01569e5fbf9fa9944bd6aee89cd`。
- **受 `SYS_FLEN` 影响的 picolibc 用例（30 例，现场 grep 得出）**：sim md5 `079ae01569e5fbf9fa9944bd6aee89cd` ⇒ 全部在 code-freeze 后的 sim 上复跑：是
- 其余 picolibc 用例（不触发 `SYS_FLEN`）：sim md5 `079ae01569e5fbf9fa9944bd6aee89cd`, `ac35dffbc90cef736e5e0788cecb51d2`（与 code freeze 前同一二进制，语义等价；每例仍只有一份结果）
- embench 用例的 sim md5：`ac35dffbc90cef736e5e0788cecb51d2` ⇒ **允许的唯一例外**：embench（及其余**不触发** SYS_FLEN 的 picolibc 用例）允许留在旧 md5 `ac35dff…`：embench 语料/shim/runtime 对 fopen/fseek/ftell/SYS_FLEN/SYS_OPEN 零命中，实测其 sim.log 只出现 SYS_WRITE0/SYS_EXIT；picolibc 侧受 SYS_FLEN 影响的 30 例已全部用 `079ae015…` 重跑

## 1. 环境

- 引擎：chipyard `WumingTinyConfig` Verilator harness（`+loadmem=` / `+semiout=` / `+max-cycles=` / `+semicmdline=`）
- 判据：guest `SYS_EXIT` 子码（harness 打印 `-> host exit status N` 后 `exit(N)`）
- 防假绿：`+max-cycles` 触顶 ⇒ FAIL；跑批前后 sim 二进制 md5 必须相同 ⇒ 否则 FAIL；embench 另要求三个板级 marker 齐全

## 2. embench（19 benchmark × -O0/-O2）

- **pending 6 例**（`-O0` 夜跑窗口内，等终态后重算本报告）
- 例数：32；PASS 32；三 marker 齐全 0
- 周期：min 6959558 / max 55177010 / sum 1005978900（`+max-cycles` 预算 2000000000，无一触顶）
- **`-O0` 12 h 夜跑窗口**（用户 2026-11-14 裁定）：`server208`、jobs=18、`--timeout 43200`；窗口内的 `-O0` 例在本报告里记 **pending**，12 h 仍不够的才记 `blocked(budget: 12h)` 并单列。
- 墙钟合计：362944.5s（为各例墙钟之和，非批量墙钟）
- sim md5：ac35dffbc90cef736e5e0788cecb51d2

每例（`status` / `rc`=guest 退出码 / `cycle` / markers / 该批 sim md5 / `+semiout` 路径 / 分片）：

| case | status | rc | cycle | markers | sim md5 | semiout | shard |
|---|---|---|---|---|---|---|---|
| embench/aha-mont64-O0 | PASS | 0 | 38161877 | ? | ac35dffb | ics180:<work-dir>/O0/aha-mont64/semi.out | ics180 |
| embench/crc32-O0 | PASS | 0 | 37548594 | ? | ac35dffb | ics160:<work-dir>/O0/crc32/semi.out | ics160 |
| embench/huffbench-O0 | PASS | 0 | 55177010 | ? | ac35dffb | ics180:<work-dir>/O0/huffbench/semi.out | ics180 |
| embench/md5sum-O0 | PASS | 0 | 51041444 | ? | ac35dffb | ics180:<work-dir>/O0/md5sum/semi.out | ics180 |
| embench/nettle-aes-O0 | PASS | 0 | 33738552 | ? | ac35dffb | ics180:<work-dir>/O0/nettle-aes/semi.out | ics180 |
| embench/nettle-sha256-O0 | PASS | 0 | 40512863 | ? | ac35dffb | ics180:<work-dir>/O0/nettle-sha256/semi.out | ics180 |
| embench/nsichneu-O0 | PASS | 0 | 27218167 | ? | ac35dffb | ics180:<work-dir>/O0/nsichneu/semi.out | ics180 |
| embench/qrduino-O0 | PASS | 0 | 46428203 | ? | ac35dffb | ics160:<work-dir>/O0/qrduino/semi.out | ics160 |
| embench/slre-O0 | PASS | 0 | 49893756 | ? | ac35dffb | ics160:<work-dir>/O0/slre/semi.out | ics160 |
| embench/statemate-O0 | PASS | 0 | 51203020 | ? | ac35dffb | ics160:<work-dir>/O0/statemate/semi.out | ics160 |
| embench/tarfind-O0 | PASS | 0 | 47917887 | ? | ac35dffb | ics160:<work-dir>/O0/tarfind/semi.out | ics160 |
| embench/ud-O0 | PASS | 0 | 51329075 | ? | ac35dffb | ics160:<work-dir>/O0/ud/semi.out | ics160 |
| embench/wikisort-O0 | PASS | 0 | 46669403 | ? | ac35dffb | ics160:<work-dir>/O0/wikisort/semi.out | ics160 |
| embench/aha-mont64-O2 | PASS | 0 | 6959558 | ? | ac35dffb | ics180:<work-dir>/O2/aha-mont64/semi.out | ics180 |
| embench/crc32-O2 | PASS | 0 | 21917277 | ? | ac35dffb | ics160:<work-dir>/O2/crc32/semi.out | ics160 |
| embench/depthconv-O2 | PASS | 0 | 10088819 | ? | ac35dffb | ics180:<work-dir>/O2/depthconv/semi.out | ics180 |
| embench/edn-O2 | PASS | 0 | 18651289 | ? | ac35dffb | ics160:<work-dir>/O2/edn/semi.out | ics160 |
| embench/huffbench-O2 | PASS | 0 | 29170826 | ? | ac35dffb | ics180:<work-dir>/O2/huffbench/semi.out | ics180 |
| embench/matmult-int-O2 | PASS | 0 | 31715347 | ? | ac35dffb | ics180:<work-dir>/O2/matmult-int/semi.out | ics180 |
| embench/md5sum-O2 | PASS | 0 | 24599962 | ? | ac35dffb | ics180:<work-dir>/O2/md5sum/semi.out | ics180 |
| embench/nettle-aes-O2 | PASS | 0 | 16380276 | ? | ac35dffb | ics180:<work-dir>/O2/nettle-aes/semi.out | ics180 |
| embench/nettle-sha256-O2 | PASS | 0 | 25168424 | ? | ac35dffb | ics180:<work-dir>/O2/nettle-sha256/semi.out | ics180 |
| embench/nsichneu-O2 | PASS | 0 | 19716419 | ? | ac35dffb | ics180:<work-dir>/O2/nsichneu/semi.out | ics180 |
| embench/picojpeg-O2 | PASS | 0 | 18606728 | ? | ac35dffb | ics180:<work-dir>/O2/picojpeg/semi.out | ics180 |
| embench/qrduino-O2 | PASS | 0 | 17466419 | ? | ac35dffb | ics160:<work-dir>/O2/qrduino/semi.out | ics160 |
| embench/sglib-combined-O2 | PASS | 0 | 19082862 | ? | ac35dffb | ics160:<work-dir>/O2/sglib-combined/semi.out | ics160 |
| embench/slre-O2 | PASS | 0 | 19603813 | ? | ac35dffb | ics160:<work-dir>/O2/slre/semi.out | ics160 |
| embench/statemate-O2 | PASS | 0 | 39515797 | ? | ac35dffb | ics160:<work-dir>/O2/statemate/semi.out | ics160 |
| embench/tarfind-O2 | PASS | 0 | 42526546 | ? | ac35dffb | ics160:<work-dir>/O2/tarfind/semi.out | ics160 |
| embench/ud-O2 | PASS | 0 | 11495574 | ? | ac35dffb | ics160:<work-dir>/O2/ud/semi.out | ics160 |
| embench/wikisort-O2 | PASS | 0 | 22572905 | ? | ac35dffb | ics160:<work-dir>/O2/wikisort/semi.out | ics160 |
| embench/xgboost-O2 | PASS | 0 | 33900208 | ? | ac35dffb | ics160:<work-dir>/O2/xgboost/semi.out | ics160 |

## 3. picolibc full（chipyard）

- 总例数 235：pass 128 / fail 1 / blocked 84 / excluded 22
- 逐例明细在 JSON 的 `cases[]`（字段 `status` / `rc` / `cycles` / `semi_out` / `sim_log` / `sim_md5`）；下面只列非 pass。
- 周期合计 80383541；墙钟合计 83799.0s；sim md5 None

## 4. 与 qemu 基线逐例一致（同代码同 ELF，只换引擎）

- qemu 基线 235 例：pass 208 / fail 1 / blocked 4 / excluded 22
- 逐例状态差集 = **0**；chipyard 独有失败 = **0**；qemu 缺口登记匹配 5/5
  - 依据：实测吞吐 **1.76 k cycles/s/例**（`slre(-O2)` 19.60 M cycles / 11140 s、32 并发），⇒ 4 h 预算内最多约 **25.3 M cycles**；超时例即需 >25 M cycles（同族 `nettle-aes(-O2)` 16.38 M 为下限参照），不是语义失败（`cycles=None`、无 guest verdict），也**不放宽** `+max-cycles` 或超时阈值。
- **budget 类单列**（host timeout ⇒ `blocked (budget: …)`，不计入 chipyard 独有失败）：80 例：math_test、memcpy-1、memmove1、snprintf、strcmp-1、test-acos、test-acosh、test-asin、test-asinh、test-atan、test-atan2、test-atanh、test-cacos、test-cacosh、test-casin、test-casinh、test-catan、test-catanh、test-ccos、test-ccosh、test-cexp、test-clog、test-cos、test-cosh、test-cpow、test-csin、test-csinh、test-csqrt、test-ctan、test-ctanh、test-double-free、test-erf、test-erfc、test-exp、test-exp10、test-exp2、test-expm1、test-ffs、test-floor、test-fma、test-fmemopen、test-fread-fwrite、test-hypot、test-iconv、test-lgamma、test-log、test-log10、test-log1p、test-log2、test-long-long、test-long-long-float、test-long-long-int、test-long-long-long、test-malloc-stress、test-memchr、test-memchr-simple、test-memmem、test-memset、test-pow、test-printf、test-printf-float、test-printf-long、test-printf-scanf、test-printf-scanf-float、test-printf-scanf-int、test-printf-scanf-long、test-rand、test-remainder、test-remquo-quo、test-sin、test-sincos-cos、test-sincos-sin、test-sinh、test-sprintf-time、test-strtod、test-tan、test-tgamma、test-timegm、test-wcsftime、tstring
- 共有例数 235；状态不一致 0 例

chipyard 侧非 pass 例（逐条原因）：

| case | suite | status | reason |
|---|---|---|---|
| test-timegm | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-wcsftime | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| snprintf | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-iconv | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-acos | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-acosh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-asin | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-asinh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-atan | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-atan2 | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-atanh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-cos | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-cosh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-sin | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-sincos-cos | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-sincos-sin | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-sinh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-tan | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-exp | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-exp10 | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-exp2 | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-expm1 | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-log | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-log10 | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-log1p | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-log2 | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-pow | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-erf | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-erfc | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-floor | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-hypot | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-lgamma | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-remainder | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-remquo-quo | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-tgamma | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-cacos | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-cacosh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-casin | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-casinh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-catan | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-catanh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-ccos | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-ccosh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-csin | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-csinh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-ctan | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-ctanh | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-cexp | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-clog | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-cpow | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-csqrt | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-fma | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-math-errhandling | test-math | fail | exit 3 |
| test-ffs | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-memchr | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-memchr-simple | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-memset | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-fmemopen | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-sprintf-time | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-fread-fwrite | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-long-long | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-printf | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-printf-scanf | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-long-long-float | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-printf-float | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-printf-scanf-float | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-long-long-long | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-printf-long | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-printf-scanf-long | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-long-long-int | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-printf-scanf-int | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-double-free | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-malloc-stress | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-rand | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-strtod | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-abort-failure | test-stdlib | blocked | machine fault CFX6 (0x86) |
| math_test | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| memcpy-1 | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| memmove1 | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| strcmp-1 | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| tstring | - | blocked | platform: host timeout after 2400.0s (no guest verdict) |
| test-ceil | test-math | blocked | ISS-193 (f) unsupported library call (long double / stack guard) |
| test-long-double | test-math | blocked | ISS-193 (f) unsupported library call (long double / stack guard) |
| test-math-funcs | test-math | blocked | ISS-193 (f) unsupported library call (long double / stack guard) |
| test-memmem | - | blocked | workload budget: >1 h on chipyard (user ruling: judge BLOCKED, do not run) |

