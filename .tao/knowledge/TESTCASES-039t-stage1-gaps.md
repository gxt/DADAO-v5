> **升格指针**（INFRA-058t，用户 2026-10-11 裁定「被引用材料不得只放 `.work/`」）：本文档由 `.work/log/testcases/` 下同名文件升格至 `.tao/knowledge/`（原 `.work/` 副本已移出，该目录 gitignored、不再保留）。
# TESTCASES-039t — 阶段 1 编译矩阵 + 后端缺口分析（现场统计）

> 证据：`TESTCASES-039t-stage1-matrix.log`（-O2）、`TESTCASES-039t-stage1-matrix-O0.log`（-O0）。
> 命令：`bash /tmp/opencode/TESTCASES-039t/matrix.sh`（`-O2`）与 `matrix_O0.sh`。
> 计数现场统计（不写死）：**-O2 = 6/19 通过；-O0 = 10/19 通过**。
> 判据恒定 = 编译+链接 rc（阶段 1 不跑 QEMU）。

## 逐基准结果

| 基准 | -O2 | -O0 | 首个错误（-O2 / -O0） |
|---|---|---|---|
| aha-mont64 | FAIL | FAIL | `umul_lohi`（128 位乘）|
| crc32 | FAIL | FAIL | 尾调用断言 / 大常量比较 |
| depthconv | **PASS** | **PASS** | — |
| edn | FAIL | FAIL | 大常量 select/setcc comp / branch comp |
| huffbench | **PASS** | **PASS** | — |
| matmult-int | **PASS** | **PASS** | — |
| md5sum | FAIL | FAIL | 尾调用断言 / 大常量 select/setcc comp |
| nettle-aes | **PASS** | **PASS** | — |
| nettle-sha256 | **PASS** | **PASS** | — |
| nsichneu | FAIL | **PASS** | 分支/跳转目标超 12 位（-O2）|
| picojpeg | FAIL | FAIL | `br_jt`（跳转表）|
| qrduino | FAIL | FAIL | `br_jt`（跳转表）|
| sglib-combined | FAIL | FAIL | 大常量 branch comp |
| slre | FAIL | FAIL | 大常量 select/setcc comp |
| statemate | **PASS** | **PASS** | — |
| tarfind | FAIL | **PASS** | 尾调用断言（-O2）|
| ud | FAIL | **PASS** | 尾调用断言（-O2）|
| wikisort | FAIL | FAIL | 大常量 select/setcc comp / `mulhu` |
| xgboost | FAIL | **PASS** | 尾调用断言（-O2）|

## 后端缺口（5 类；1 类为已知遗留，4 类为新发现）

**G1（已知遗留）大常量比较超 12 位立即数** — `select/setcc compare ... does not fit a 12-bit immediate`
最小复现：`int f(long a){ return a < 5000; }` → `-O2` `clang` rc=1。
命中：edn / slre / wikisort（select/setcc），crc32 / edn / sglib-combined / slre / md5sum（branch）。

**G2（新）128 位乘 `umul_lohi` / `mulhu` 不可 select**
最小复现：`unsigned long f(unsigned long a, unsigned long b){ return a*b/3; }`
→ `Cannot select: ... mulhu t5, Constant:i64<-6148914691236517205>`（rc=134）。
可进一步收窄：`return a*b / c`（非 2 的幂除数）触发 128 位乘高半；aha-mont64 `mulul64` 直接用 `unsigned long long`。
命中：aha-mont64（-O2/-O0），wikisort（-O0 的 `mulhu`）。

**G3（新）`br_jt`（跳转表 / `switch` 密集分发）不可 select**
最小复现：`switch(x)` 含 16 个 case（含 fallthrough 全分支）→
`Cannot select: t4: ch = br_jt t2:1, JumpTable:i64<0>, t2`（`-O0` 即触发）。
命中：picojpeg / qrduino。

**G4（新）尾调用 LowerCall 断言 `LowerCall emitted a return value for a tail call!`**
最小复现：`extern long g(void); long f(void){ return g(); }` → `-O2` clang 断言失败（rc=134）。
命中：crc32 / md5sum / tarfind / ud / xgboost（**仅 -O2**；-O0 全部消失）。

**G5（新）分支/跳转目标超 12 位 PC 相对范围**
最小复现：nsichneu（-O2）→ `error: branch/jump target out of range for a 12-bit PC-relative immediate`。
命中：nsichneu（-O2）。

**G6（新）`-O2` 运行时误编译导致死循环（非编译期失败，运行期 hang）**
- 现象：`huffbench` / `matmult-int` / `nettle-sha256` / `statemate` 在 `-O2` **编译成功**，但 QEMU 运行**超时（rc=124）**；`-O0`/`-O1` 均 exit=0。
- 最小复现：`.work/source/embench-iot/src/matmult-int/matmult-int.c` 仅把 `LOCAL_SCALE_FACTOR 39` 改 `3`（`/tmp/opencode/TESTCASES-039t/red/mm.c`），`-O2` 死循环、`-O0`/`-O1` exit=0。
- 执行轨迹（`-d exec`）：停在 `memcpy` 的两条指令（PC 0x4e0/0x4f4）反复自转，`rd4`（i）持续自增而 `rd5`（n）=0，即循环不推进。属 **-O2 优化级误编译**，非算法死循环。

## 结论
- 阶段 1 失败**不集中于**已知遗留（G1）：4 类新缺口（G2–G6）独立存在。
- 首验收判据（≥1 最小基准 exit 0）**可达**（-O2: 2 个；-O0: 10 个）⇒ 继续阶段 2。
- 未改 `components/llvm-project/**`（越界）；G1–G5 建议各立新 LLVM 任务；G6 建议并入尾调用/大常量修复后的 -O2 回归。
