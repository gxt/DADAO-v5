# LLVM-115t: picolibc `ld128` 数学引擎（`__*_engine`）接入 —— `math_test` 链接解阻

**模块**：llvm
**项目里程碑**：M8
**依赖**：`LLVM-113t`（i128 ↔ f128 四转换 libcall：`__floatuntitf` 等；`atold_engine.c` 的 `_u128_to_ld` 直用）、`LLVM-114t`（f128 math libcall：`__multf3` 之外的 `floorl`/`rintl`… 已注册，`build-picolibc` 已回 rc=0）、`LLVM-106t` + `INFRA-090t`（`long double` = binary128，`ADR-0030`/`ADR-0031`）、`LLVM-109t`（现场暴露者；本册 = 其「遗留问题」落点）、`ISS-193`（(f) 类登记源）
**状态**：已验证

> **立册口径（2026-10-19，architect）**：这是 binary128 落地后的**消费侧链接缺口**（picolibc 自身源码未接进构建），不是新决策；不改 ADR、不改契约、**不扩过滤表**。归属（picolibc 自身源 vs 另一来源）**先诊断、后定落点**，禁止预设。

## 执行环境
**执行环境**：本地

## 问题根源

### 现场（逐字，2026-10-19）

`make check-picolibc-tests`：`build-picolibc` **PASS**（`libc.a` 2,025,904 B），逐例
`total=20 pass=17 fail=0 excluded=2 blocked=1` ⇒ **make rc=2**（`.work/log/testcases/LLVM-109t-leftover-picolibc.log`）。唯一 blocked：

```
math_test  newlib.math  blocked  undefined symbol: __atold_engine
           (source excluded by the backend-gap filter; see meson.build / ISS-193)
```

`nm -A .dadao/dadao-unknown-elf/lib/libc.a`（现场）：

```
libc_stdio_strtold.c.o:  U __atold_engine
libc_stdio_wcstold.c.o:  U __atold_engine
```

同 archive 内其余引擎符号均为 `T`：`__atod_engine` / `__atof_engine` / `__dtoa_engine` / `__dtox_engine` / `__ftoa_engine` / `__ftox_engine` / `__ldtoa_engine` / `__ldtox_engine` ⇒ **唯一缺 `__atold_engine`**。

### 根因链（本笔实读源码，`file:line`）

1. `long double` 由 `double` 改为 **IEEE binary128**（`ADR-0030`；`__SIZEOF_LONG_DOUBLE__ = 16`）。
2. `libc/stdio/strtold.c:67` `#include "conv_flt.c"`；`conv_flt.c:87-92` 对 `STRTOLD` 定义 `_NEED_IO_LONG_DOUBLE`。
3. `libc/stdio/dtoa.h:60-77`：`_NEED_IO_LONG_DOUBLE` 且 `__SIZEOF_LONG_DOUBLE__ > 8` ⇒ 定义 `_NEED_IO_FLOAT_LARGE`。
4. `libc/stdio/conv_flt.c:579-584`：`_NEED_IO_FLOAT_LARGE` 且 `CHECK_LONG_LONG() && __SIZEOF_LONG_DOUBLE__ > 8` ⇒ `flt = (FLOAT)__atold_engine(...)`；即 **`strtold` 的十进制→long double 路径**依赖该符号。
5. 定义在本树**唯一一处**：`libc/stdio/atold_engine.c:108`（`git grep` 全树核对；`local-stdio.h:409` / `atold_engine.c:110` 的 `_u128_to_ld` = `(long double)u128`，另有多条 `long double` 乘）。
6. 该 TU 被**我方 meson 补丁排除**：`components/picolibc/patches/meson.build.patch` 的 `_dadao_backend_blocked` 列表含
   `'atold_engine.c'`，注释 = `long-double strtod engine libcall unsupported; ISS-193 (f)`。
   历史上（`long double` = 64 位时）该源编译失败，签名 = `error in backend: unsupported library call operation`（`LLVM-088t`/`LLVM-089t` 现场复跑，见 `.tao/archive/M7/`）。

### 归属待现场判定（**不许预设**）

先对 `atold_engine.c` 做**单源重编诊断**（用安装根/构建树 clang，`-O2 -c`，输出落 `.work/log/llvm/LLVM-115t-*`），按结果三选一：

- **A（picolibc 自身源、过滤已陈旧）**：现在能编译 ⇒ 最小修法 = **只从 `_dadao_backend_blocked` 删 `atold_engine.c` 这一条**（同步注释/计数），`series` 条目数不变；picolibc 上游源零改动。
- **B（picolibc 自身源、仍缺后端能力）**：仍 `unsupported library call operation` / `Cannot select` ⇒ 记录**逐字签名 + DAG 节点/目标 libcall**；若缺的是 RTLIB 注册（如某 f128 运算），按 `LLVM-113t`/`LLVM-114t` 同法**只补该一条**（后端补丁 + 单跑 `install-host`），不得改过滤表扩面。
- **C（另一来源）**：若现场证明符号应由 musl / compiler-rt / 其它组件提供（例如 picolibc 本树定义不可用）⇒ **保留现场证据**并在完成区给「为什么不能用 picolibc 自身源 + 拟接入来源/落点」，交主会话裁定；**不得**在未证实前改组件边界或加 stub。

**禁止**：扩 `_dadao_backend_blocked`、加空实现/弱符号掩盖、改 picolibc 上游源（`.work/source/picolibc` 只读，改动一律走 `components/picolibc/patches/**`）。

## 接口规范

- **输入**：
  - `components/picolibc/patches/meson.build.patch`（过滤表现场为 2 条：`hash_page.c`= `ISS-193` (c)、`atold_engine.c`= (f)）、`components/picolibc/{series,changelog.md,README.md}`
  - `.work/source/picolibc/`（**只读**；诊断对象 `libc/stdio/atold_engine.c`）
  - 安装根 `.dadao/dadao-unknown-elf/`（`libc.a` 与头文件）+ `.dadao/cross-toolchain/`（clang；本册若动后端须先单跑 `make install-host`）
  - `tools/testcases/picolibc_tests.py`（`make check-picolibc-tests` = `--stage fast`）与 `tools/infra/build_picolibc.py`
  - `tests/scripts/{codegen_crt0.s,dadao.lds}`（harness 链接载体，现状可跑）
  - `TESTCASES-047t` 驱动 + 权威跑基线（只读参照）：静态 `.work/tests/authoritative/20261019T063001Z-libc-test-user-static/run.json`（`pass 309 / fail 0 / known-fail 4 / blocked 24`）、动态 `20261019T063847Z-libc-test-user-dynamic/run.json`（`312 / 0 / 4 / 21`）
- **输出**（按诊断结论取实际分支需要的）：
  - `components/picolibc/patches/meson.build.patch`（A：删 1 条 + 注释；B/C 不删）
  - 可能的 `components/llvm-project/patches/**` + `series` + `changelog.md`（仅 B）
  - `components/picolibc/changelog.md` 一条（M8；仅当改了 picolibc 补丁）
  - `.work/evidence/<任务ID>/run.sh`（`default` + `--inject`）+ `probe.*` + 独立 oracle 生成器 + 期望文件 + 日志
  - 本任务书完成区
- **约束**：只改与本缺陷直接相关的文件；**不动** `spec/`、`.tao/contracts/`、`contracts/`、picolibc 上游源、`ISS-193` 的 (c) 条目；`check-patch-tree` 计数须与改动一致（A 分支应仍为 **181**）。

## 验收标准

1. **`make check-picolibc-tests` rc=0**：`math_test` 由 `blocked` 转 **`pass`**，且 `blocked=0`、`fail=0`（预期 `total=20 pass=18 excluded=2`；计数若因 harness 枚举变化而不同，须现场派生并逐条解释）。若 C 分支证明不能修，须给出**有据**说明（逐字链接错误 + 归属 + 为何不能接入），且**不得**把 `blocked` 静默改成 `excluded`。
2. **`047t` 5 个 `long double` 例两档仍 `pass`**：`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`（基线见上；两档各 5/5 `pass`、各自 `fail=0`；带 `--json-out` 留档）。
3. **探针（独立 oracle，禁从被测实现反推）**：
   - `strtold`：至少 4 组十进制串（>53 位有效数字、恰半值 tie、极小/极大边界各 1），用 Python **精确有理数 + binary128 就近偶数舍入**（或等价可复算实现）算出 16 B 期望，与 guest 内 `long double` 的 `memcpy` 原始字节**逐字节**比对；
   - `long double` 数学：至少 2 个函数（如 `sqrtl`/`logl`/`powl`）用精确值或明确容差做独立 oracle（说明容差来源；libm 非正确舍入，禁伪称 bit-exact）；
   - 探针必须真实经过 `__atold_engine` 路径（`strtold` 入口），并给出改前/改后或断言的**可达 FAIL**。
4. **可达 FAIL**：证据脚本 `default` 全绿；`--inject` 至少 3 处注入（如临时恢复过滤条目 / 错误期望字节 / 错误计数）各自能转红，`cp` 备份 + md5 对账还原（**禁** `git checkout/restore/stash`）。
5. **`install-host` 前置**：若改后端补丁，单跑 `make install-host` 并用安装根复验；若仅改 picolibc 补丁，记录安装根 `clang --version` / 时间戳证明未用陈旧工具链。**不与其它 build/任务并发**。
6. **L2 由主会话复跑**（engineer 不跑 `check-modules`/`check-full`；本册只跑 `check-picolibc-tests` + L1 + 047t 子集）。

## 完成区
**测试结果**：`make build-picolibc JOBS=8` **rc=0**（`libc.a` 2,025,904→**2,028,044 B**；`nm` = `libc_stdio_atold_engine.c.o: T __atold_engine`）；`make check-picolibc-tests JOBS=8` **rc=0**，`total=20 pass=18 fail=0 excluded=2 blocked=0`，`math_test` **pass**（改前 blocked/`undefined symbol: __atold_engine`）；047t 5 例（`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`）两档各 **5/5 pass、fail=0**（`--json-out /tmp/opencode/LLVM-115t/047t-{static,dynamic}.json`）；独立 oracle 探针 **11/11 PASS**（strtold 逐字节 7/7 + `sqrtl`/`logl`/`powl`×2 4/4）；证据 `default 18/18 rc=0`、`--inject 38/38 rc=0`（I1 恢复过滤条目 ⇒ build rc=0 但 `T`=0、tests rc=2/blocked=1；I2/I3 改期望字节 ⇒ probe rc=1；均 `cp`+md5 还原回绿）。
**修改文件**：`components/picolibc/patches/meson.build.patch`（过滤表 2→**1**：删 `atold_engine.c` 及其注释，加 LLVM-115t 说明）；`components/picolibc/changelog.md`（M8 一条）；本任务书。gitignored：`.work/evidence/LLVM-115t/{run.sh,probe.c,gen_expected.py,check_probe.py,oracle_binary128.py,expected_*.txt,stress_strtold.txt,probe_inputs.h}`、`.work/log/{llvm,testcases}/LLVM-115t-*`、`/tmp/opencode/LLVM-115t/`。
**验收结果**：诊断 = **A**（picolibc 自身源、过滤条目陈旧）：单源 `clang -target dadao-unknown-elf … -c libc/stdio/atold_engine.c` **rc=0**、`llvm-objdump` 无 unsupported libcall；`git grep`/目标树 grep 唯一实现在 `atold_engine.c:108`（`conv_flt.c:582` 的 `strtold` 路径），**非** musl 来源、无需外部提供。门控全 **rc=0**：`check-patch-tree`（**181** patches OK）、`check-index-blobs`、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`check-musl-freshness`、`check_issues.py`、`make check`(L1)。E1：组件树 clean、base+1（本地 `8428005`→`ae6a7f8` amend 后经 `make_patch.py` 重导出）。安装根 clang `23.1.3`（`.cache/llvm-project.git 2125f048…`）；仅改 picolibc 补丁，**未**跑 `install-host`（stamp 保护，工具链非陈旧）。
**新发现/坑**：① picolibc `conv_flt.c` 对 long double 只累计 **32 位十进制**（`uintdigitsmax_10_long_double=32`），`atold_engine` 再按 2 的幂表逐步乘 ⇒ >32 位十进制或中间量落到次正规时**非正确舍入**（实测 1–7 ulp；`1e-4940` 因中间乘积次正规，结果约为精确值一半）。故探针门控取精确可复现向量（71 位长尾→1.0、32 位尾数、tie-to-even、上/下溢），另 6 条仅报 INFO ulp（不伪称 bit-exact）；修上游不在本笔范围。② 改组件补丁须在 `.work/source` 改→`commit --amend`→`tools/infra/make_patch.py`，**禁**手改 patch（Process-01 §6.1.1）。③ `check-run-artifacts` 要求日志名 `<TASK-ID>-<purpose>.log|json|txt` 或 `check-*.log`，`.stdout` 不合规。④ `components/picolibc/README.md` 仍写 `long double=f64`（ADR-0030 前口径）。
**遗留问题**：picolibc ld128 `strtold` 的 >32 位十进制/次正规精度限制（上游行为，非本任务门控；`math_test` 已 pass）；`components/picolibc/README.md` 的 long double 口径待文档任务更新；未跑 `install-host`/`build-qemu`/L2/L3（按派单），未 commit/push，未改 `**状态**`。

## 审阅记录

#### 第 1 轮 engineer 自审

**审阅范围**：`components/picolibc/patches/meson.build.patch` diff（hunk 计数/过滤表语义）、`changelog.md` 体例、证据脚本的 rc 传递与 nm/摘要解析、probe/oracle 独立性与可达 FAIL。逐行核对 evidence 的每条断言与真实输出。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|----------|----------|
| `run_picolibc_tests` 末尾 `cat` 覆盖 make 退出码 ⇒ C02 与 I1「tests 转红」假绿 | ✅已修 | 局部 `rc=$?` 后 `return "$rc"` | `--inject` I1_tests_red actual=rc2；default C02 rc=0 |
| nm 断言按 `: +T` 匹配，实际格式为 `addr T sym` ⇒ C08/C13 假红 | ✅已修 | 正则改 ` T __atold_engine$` / ` U …` | default 18/18；C13 `T=1 U=0` |
| probe 初版把 >32 位十进制/次正规也当逐字节门控 ⇒ 与上游 32 位上限冲突（真实差异 1–7 ulp、次正规 ~0.5×） | ✅已修（测试设计） | 门控保留 7 条精确可复现向量；6 条改为 INFO ulp 并在脚本/完成区说明 | probe 11/11 PASS；INFO 距离 2/7/1/1/15443597764608243389206330/6 ulp |
| probe 用 `-nostdinc` 缺 `stddef.h`，且漏 `stdlib.h`（`strtold` 隐式声明） | ✅已修 | 去掉 `-nostdinc`、补 `#include <stdlib.h>` | 编译 rc=0、链接 rc=0、guest rc=0 |
| `check-run-artifacts` A3 判 `.stdout`/无任务前缀日志名不合规 | ✅已修 | 重命名并让 run.sh 输出 `<TASK-ID>-…`；`.stdout`→`-run.txt` | `make check` A3 `0 illegal`、L1 rc=0 |
| 手改补丁会破坏 hunk 计数（Process-01 §6.1.1） | ❌不修（改为合规流程） | 未手改：源树改→`commit --amend`→`make_patch.py` | `check-patch-tree` 181 patches OK（断言⑥） |
| `components/picolibc/README.md` 仍写 `long double=f64` | ⏸延后 | 未改（越本笔范围，仅记录） | 完成区「遗留问题」 |

**判决**：无未修 finding ⇒ 实现完成（按派单保持 `**状态**` 不变，待主会话收尾）。

#### 第 1 轮 reviewer 验收

**审阅范围**：meson.build.patch 过滤表、build-picolibc rc、check-picolibc-tests 计数、probe oracle、证据脚本 default+inject、check-patch-tree 计数、check_milestones_fresh。

**重跑记录**（真实输出/退出码）：

| 命令 | 期望 | 实际 | rc |
|------|------|------|----|
| `make build-picolibc JOBS=8` | rc=0, libc.a 2,028,044 B | rc=0, libc.a 2,028,044 B | 0 |
| `make check-picolibc-tests JOBS=8` | rc=0, total=20 pass=18 blocked=0, math_test pass | rc=0, total=20 pass=18 fail=0 excluded=2 blocked=0, math_test pass | 0 |
| `nm -A libc.a` grep `T __atold_engine` | 1 | 1 | 0 |
| `check-patch-tree` | 181 patches OK | 181 patches OK | 0 |
| `check_milestones_fresh.py` | PASS | PASS (71 行) | 0 |
| 证据脚本 default | 18/18 PASS | 18/18 PASS | 0 |
| 证据脚本 --inject | 38/38 PASS | 38/38 PASS | 0 |

**约束核验**：
- ✅ meson.build.patch 过滤表 2→1（仅剩 `hash_page.c`），`atold_engine.c` 条目已删
- ✅ `make check-picolibc-tests` rc=0，`math_test` 由 blocked 转 pass
- ✅ 047t 5 例（acoshl/asinhl/erfcl/lgammal/tgammal）两档各 5/5 pass
- ✅ 探针 11/11 PASS（strtold 逐字节 7/7 + sqrtl/logl/powl×2 4/4）
- ✅ 可达 FAIL：I1 恢复过滤条目 ⇒ tests rc=2/blocked=1；I2/I3 改期望字节 ⇒ probe rc=1；均 cp+md5 还原回绿
- ✅ picolibc source clean（git status 无改动）
- ✅ series 14 不变，check-patch-tree 181
- ✅ 未改 spec/contracts/picolibc 上游源

**判决**：**Accepted** — 验收命令块全部通过，约束无违反。
