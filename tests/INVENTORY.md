# `tests/` 测试资产盘点（现场派生）

> **生成**：`TESTCASES-067t`（2026-10-26）｜**只读盘点**：本册未移动/改写任何测试、工具、Makefile。
> **迁移后状态（2026-10-27，`TESTCASES-072t`）**：inst 向量/探针/harness 已搬家 ——
> `tests/vectors/*` → `tests/inst/<ext>/`（`isa` → `base`）、`tests/{atomics,clmul,fma,minmax,roundint}/`
> → `tests/inst/<ext>/`、harness → `tools/testcases/{lib,inst}/`（`tests/scripts/` 留薄 wrapper，P6 已删除）。
> **P3 arch（2026-10-27，`TESTCASES-073t`）**：`tests/unit/llvm/codegen/m5/` → `tests/arch/umon/`、
> min-ROM 探针 `min_rom_probe_*` → `tools/testcases/arch/`、bootrom 三件 →
> `tests/shared/bootrom/`；门控 `test-semihost` → `check-arch-smoke`（别名保留）。
> **P4 unit（2026-10-27，`TESTCASES-074t`）**：`tests/unit/llvm/{lit,codegen,ir-lli}` →
> `tests/unit/llvm/`；picolibc 自测入口 → `tests/unit/picolibc/`
> （仍只在 picolibc 构建下跑）；门控收拢为 `check-unit`（L2），旧目标名保留。
> **P5 tset（2026-10-27，`TESTCASES-075t`）**：三个 user-mode 套件驱动 →
> `tools/testcases/tset/{libc-test,llvm-ts,embench}/`（旧扁平路径留薄 wrapper）；
> Embench 套件 glue → `tests/tset/embench/`（`tests/scripts/` 留符号链接，P6 已删除）；门控
> `check-tset-{libc,llvm,embench}-smoke`（L2）。
> **P6 收口（2026-10-27，`TESTCASES-076t`）**：`tests/scripts/`、`tests/qemu/` 已删除；共享
> glue → `tests/shared/{crt0,linker,runtime}/`；集成驱动 → `tools/testcases/{unit,tset}/` +
> `tools/infra/`；旧 Make 目标名已删。
> **P6 后清理（2026-10-28，`TESTCASES-084t`）**：顶层 `e2e/` → `tests/unit/llvm/e2e/`；
> 旧 `llvm/` 迁移期符号链接与旧 `min_rom_probe_*` 薄 wrapper 已删除；
> 5 个用例目录的 `.gitkeep` 与 `__pycache__` 已清。
> **下文 §1/§2/§3/§8 的路径与计数是迁移前快照**（067t 口径）；**P6/084t 后的现场值**见本节末
> 「P6 现场复核」「084t 现场复核」；最新布局与入口见 `tests/README.md`。
> **计数口径**：全部由命令现场统计（不含 `.git`、`.work`、`.cache`）；「文件数」= `find … -type f` 的**磁盘**文件（含被 `.gitignore` 忽略的 `__pycache__/*.pyc`）；「入库」另列 `git ls-files` 计数。
> **机器可核**：文末「计数锚点」块由 `.work/evidence/TESTCASES-067t/run.sh` 现场重算逐项比对；测试一改，锚点必须同步，否则证据脚本红。
> **层级**（本盘点用；正式定义见 `docs/Process-09-测试组织规范.md` §3.1）：**I** 指令级 · **S** 系统级 · **E** 端到端 · **U** 工具单测。
> **事实/推测分离**：标「推测」的条目未经验证；其余均有本页所附命令或门控日志支撑。

---

## 1. 总览

| 项 | 值 |
|---|---|
| `tests/` 文件总数 | **341**（迁移前快照；P6 后 343，见「P6 现场复核」） |
| `tests/` 体积 | 2,064,062 B（`du -sb`；迁移前快照） |
| `tests/` 顶层项 | **13**（迁移前快照；P6 后 14 = 7 目录 + 7 文件） |
| `.dadao/tests/` | **19,967** 文件 / **1,132,542,115 B**（`du -sh` 显示 1.2 G） |
| `.dadao/tests/` 子目录 | **18**（1 个空目录 `probes/`） |
| 运行目录（`YYYYMMDDTHHMMSSZ-<suite>-<档>`） | **144**（libc-test-user 118 / llvm-ts-user 20 / embench-user 6） |
| 向量用例 | **1,456** 例 / **193** 个 opcode 身份 / 22 个 YAML |
| 逐条身份清单 | **1,956** 行（vector 1,456 + lit pattern 500） |

口径说明（易错点）：

- `.dadao/` 被 `.gitignore:8` 整体忽略 ⇒ `.dadao/tests/` **全部是生成物**，不入库。
- `tests/` 中 `__pycache__/` 被 `.gitignore:11` 忽略 ⇒ 9 个 `.pyc` 是**磁盘残留**而非资产（§7.5）。

---

## 2. `tests/` 顶层项

| 顶层项 | 文件数（入库） | 用途 | 层级 | 门控 / 入口 | 自动? | 覆盖对象 |
|---|---|---|---|---|---|---|
| `vectors/` | 25（25） | 独立 ISA 向量：22 YAML / 1,456 例；`inventory.md` 覆盖矩阵、`schema.md` 字段规范 | I | `validate-vectors`(L1)、`check-qemu-smoke`(L2 子集)、`check-qemu-semantics`(L3 全量) | 自动 | M1 152/156、`m9` 34、`m8` 7 个身份 |
| `llvm/` | 216（214） | LLVM 三档：lit MC 汇编、lit CodeGen 结构、CodeGen 执行程序 + ir-lli 差分清单 | I + E | `check-lit`(L2)、`check-lit-full`(L3)、`test-codegen`/`test-elf`(L2) | 自动（m6 除外，见 §7.3） | 汇编器编码、isel/帧/段结构、IR→运行 |
| `unit/llvm/e2e/` | 45（44） | 14 个 lit E2E（`.test`）+ 29 个 C/asm 源（含 9 个无 runner 引用，§7.4）；084t 由顶层 `e2e/` 归入 | U | `check-lit`（跑 `lit/`） | 自动（9 个源已死，§7.4） | 编译→链接→运行整体链路 |
| `scripts/` | 30（24） | 共享 harness：向量→二进制构建、QEMU 单例/批量运行、冒烟驱动、bootrom/lds/crt0、dump 校验 | U（+I/S 载体） | 被 `check-qemu-*`、`test-codegen/elf/semihost`、`semantics_gate.py` 调用 | 自动（含手工 CLI） | harness 自身正确性、测试机约定 |
| `atomics/` | 5（5） | C11/`__atomic`/LR-SC 并发探针源（5 个 C） | I | **无 make 目标**（§5.3） | 手工 | 原子内建、互斥、ABA、`a_barrier` |
| `clmul/` | 4（4） | clmul 边界/GHASH/CRC-32C 探针 + IR | I | `check-clmul-probe`(L3) | 自动 | `clmul.o`、GHASH、CRC-32C |
| `fma/` | 4（4） | FMA 单次舍入/点积/GEMM/Horner 探针 + 公共头 | I | `check-fma-probe`(L3) | 自动 | `ftfma`/`fofma` |
| `minmax/` | 4（4） | min/max NaN/±0/rounding 矩阵探针 | I | `check-minmax-probe`(L3) | 自动 | `ftmin/ftmax/fomin/fomax` |
| `roundint/` | 4（4） | `ftrnd/fornd` 六模式/标志/`rf0` 探针 | I | `check-rnd-probe`(L3) | 自动 | roundToIntegral |
| `qemu/` | 1（1） | 占位 README（QEMU 组件测试落点，暂无内容） | — | 无 | — | — |
| `case-ledger.tsv` | 1（1） | 逐条身份清单（生成物，`--write` 重生成） | — | `check-case-ledger`(L1) | 自动 | 删用例/pattern 的哨兵 |

`tests/` 体积分布：`llvm` 1.2 M / `vectors` 840 K / `scripts` 336 K / `unit/llvm/e2e` 204 K / 其余各 ≤ 88 K。

---

## 3. 子目录明细

### 3.1 `tests/vectors/`（25）

| 内容 | 数量 | 说明 |
|---|---|---|
| `isa/*.yaml` | 16 册 / 708 例 | M1 身份（`scope == m1`），`validate_vectors.py` 校验 |
| `rol/rol.yaml` | 1 册 / 64 例 | `rol.*`（`scope: m9`） |
| `atomics/{lrsc,fence}.yaml` | 2 册 / 127 例 | `lr/sc` 108 + `fence` 19（`scope: m9`） |
| `clmul/clmul.yaml` | 1 册 / 81 例 | `clmul.o`（`scope: m1`） |
| `rev/rev.yaml` | 1 册 / 62 例 | `rev.*`（`scope: m8`）——**不在任何门控** |
| `bitcnt/bitcnt.yaml` | 1 册 / 414 例 | `ctlz/cttz/ctpop`（`scope: m8`）——**不在任何门控** |
| `inventory.md` | — | M1 覆盖矩阵（156 行）+ 门控覆盖表（L2/L3 逐册） |
| `schema.md` | — | 字段/保留编码/状态语义规范 |
| `README.md` | — | 范围与校验入口 |

分类计数（现场 `class:` 字段）：semantic 595 / boundary 377 / legality 276 / encoding 187 / overlap 21；`status`：active 1,451 / deferred 5。

### 3.2 `tests/unit/llvm/`（216，入库 214）

| 子项 | 文件数 | 内容 | 门控 |
|---|---|---|---|
| `lit/MC/DADAO/` | 81 | 76 个 `.s`（417 条 `@@ RUN:`）、lit.cfg、2 个校验脚本/README | `check-lit`(L2) |
| `lit/MC/DADAO-gen/` | 13 | 12 个生成 `.s`（35 条 RUN），由 `contracts/opcodes.yaml` 机械生成 | `check-lit-full`(L3) |
| `lit/CodeGen/DADAO/` | 66 | 60 `.ll` + 3 `.mir`（65 条 RUN）+ cfg/README | `check-lit`(L2) |
| `lit/tools/DADAO/` | 2 | 占位（无测试，未接门控） | 无 |
| `codegen/`（M3） | 17 | 15 `.ll` + `expected.yaml`(15 程序) + README | `test-codegen`(L2) |
| `codegen/m4/` | 12 | 10 `.ll`（5 程序，main+lib 成对）+ 清单 | `test-elf`(L2) |
| `codegen/m5/` | 12 | 10 `.s`（semihost/CFX 权限）+ 清单 | `test-semihost`(L2) |
| `codegen/m6/` | 11 | 8 `.ll`（7 raw-bin + 1 ELF）+ 2 清单 | **无 make 目标**（§7.3） |
| `ir-lli/` | 2 | `manifest.yaml`：include **20** / exclude **79**（含理由分类；084t 补齐 M10 分类） | `test-m6`(L3) |

### 3.3 `tests/unit/llvm/e2e/`（45；084t 由顶层 `e2e/` 归入）

- `lit/`：14 个 `.test` / 96 条 RUN + `lit.cfg.py`；覆盖 smoke（add/arith/jump/fp）、FP p0/p1、FMA、clmul builtin、weak/undef、narrow-int、p2align、CM 模型、clang target。
- 顶层 29 个源：`.c` 24 / `.s` 4 / `.lds` 1；其中 **20 个被 `.test` 引用**、**9 个无 runner 引用**（§7.4）。

### 3.4 `tests/scripts/`（**P6 已删除**；此处只留去向）

| 原内容 | P6 后去向 |
|---|---|
| 运行/构建 harness（6：`build_test_binary`/`run_qemu_test`/`run_qemu_smoke`/`verify_harness_dump`/`test_harness_exit_path`/`gen_trampoline`） | `tools/testcases/{lib,inst}/`（迁移期薄 wrapper 已删） |
| 测试机夹具（bootrom 三件、`trampoline.bin`、`codegen_crt0.s`、`dadao.lds`、`dadao-dyn.lds`） | `tests/shared/bootrom/`、`tools/testcases/lib/trampoline.bin`、`tests/shared/{crt0,linker}/` |
| 运行时辅助（`dadao_mem_runtime.ll`、`dadao_user_dyn_probe.c`） | `tests/shared/runtime/` |
| Embench 套件 glue（`embench_runtime.c`/`embench_user_boardsupport.c`/`embench_include/`） | `tests/tset/embench/` |

### 3.5 `tests/tset/`（P5 后）

| 套件 | 内容 | 入口 |
|---|---|---|
| `libc-test/` | `README.md`（语料来源 + 代表集规则 + 运行目录） | `make check-tset-libc-smoke` |
| `llvm-ts/` | `README.md`（语料来源 + 代表集规则 + 运行目录） | `make check-tset-llvm-smoke` |
| `embench/` | `README.md` + `embench_runtime.c` / `embench_user_boardsupport.c` / `embench_include/` | `make check-tset-embench-smoke` |

上游语料本体不入库（`.work/source/<suite>/`，`manifests/` 锁定）；`tests/tset.yaml`
每条 = 一个套件的受控运行配置。

---

## 4. `.dadao/tests/`（19,967 文件 / 1.2 G；全部为生成物）

| 子目录 | 文件数 | 体积 | 由谁生成 | 可重生成? | 备注 |
|---|---|---|---|---|---|
| `llvm-ts-user/` | 16,112 | 836 M | `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`（`--work-dir` 默认） | 是（需 llvm-test-suite 源 + 工具链，耗时长） | 20 个运行目录 + `static/`/`dynamic/` 脚手架 |
| `llvm-ts-user-050t/` | 826 | 209 M | **无脚本**：全仓 grep `llvm-ts-user-050t` 零命中（仅归档任务书 `TESTCASES-048t` 提及） | **否**（生成脚本已不在仓库） | 孤儿，建议清理 |
| `libc-test-user/` | 1,897 | 77 M | `tools/testcases/tset/libc-test/run_libc_test_user_suite.py` | 是 | 118 个运行目录（三件套）+ 脚手架 |
| `embench-user/` | 415 | 7.4 M | `tools/testcases/tset/embench/run_embench_user_suite.py` | 是 | 6 个运行目录 |
| `m6-embench/` | 312 | 3.3 M | `test-m6` [3/3] → `run_embench_e2e.py` | 是 | `rm -rf` 后重建 |
| `codegen-e2e/` | 60 | 264 K | `test-codegen` → `run_codegen_e2e.py` | 是 | 每次 `rm -rf` |
| `codegen-m6/` | 28 | 132 K | `run_codegen_e2e.py` 的**手工**调用（m6 README） | 是（手工） | 无 make 目标 |
| `elf-m6/` | 3 | 20 K | `run_elf_e2e.py` 的**手工**调用（m6 README） | 是（手工） | 无 make 目标 |
| `elf-e2e/` | 16 | 88 K | `test-elf` | 是 | 每次 `rm -rf` |
| `m5-e2e/` | 41 | 2.1 M | `test-semihost` | 是 | 每次 `rm -rf` |
| `ir-lli-diff/` | 76 | 340 K | `test-m6` [2/3] → `diff_ir_lli.py` | 是 | — |
| `lit-output/` | 143 | 680 K | `check-lit` / `check-lit-full`（4 个 lit suite 的 `test_exec_root`） | 部分（含 `.lit_test_times.txt` 时间戳 ⇒ **不可能逐字节**） | 见 §5.3 |
| `harness/` | 4 | 64 K | `check-qemu-semantics`（`gate/`）、`check-qemu-smoke`（`smoke/`）、`verify_harness_dump.py`（`dumps/`） | 是 | 3 种来源共用一目录 |
| `bootrom/` | 5 | 28 K | `build-bootrom` | 是 | — |
| `smoke/` | 2 | 48 K | `run_qemu_smoke.py` 的**默认** `--work-dir`（Makefile 传 `harness/smoke`） | 是 | 旧默认落点残留（2026-10-11） |
| `libc-argv-static/` | 13 | 136 K | **无脚本**：全仓 grep `libc-argv` 零命中（mtime 2026-10-18） | **否** | 孤儿 |
| `libc-argv-dynamic/` | 14 | 1.1 M | **无脚本**（同上） | **否** | 孤儿 |
| `probes/` | 0 | 4 K | `min_rom_probe_*.py` 的 `--work-dir` 默认 | 是 | 空目录 |

**清理现状（事实）**：`make clean-work`（`tools/infra/clean_work.py`）**只删 `.work/`**，**不碰 `.dadao/tests/`**；仓库**没有** `clean-tests` 一类目标 ⇒ 1.2 G 只能手工 `rm -rf`，且无「哪些可安全删」的清单（本表即候选清单）。

---

## 5. 现有 make 测试目标

### 5.1 分层成员（真源 `Makefile`；P6 重写后）

| 层 | 目标 |
|---|---|
| L1 `make check` | 仓库完整性静态检查 + 组件可用性冒烟；P6 起含 `check-interface`（跨模块静态一致性）与 `check-code-range`（合成 fixture 自检） |
| L2 `make check-modules` | 四 scope **smoke**：`check-inst-smoke`、`check-arch-smoke`、`check-unit`、`check-tset-{libc,llvm,embench}-smoke`（**不含** FP 探针） |
| L3 `make check-full` | 全量（inst/arch/unit）+ 集成链：`check-inst`、`check-arch`、`check-unit-full`（= `check-unit` + `check-lit-full`）、4 个 **FP 探针**、`test-m6`；**tset 不直接列出**（smoke 仅在 L2、full 仅在夜跑；`test-m6` 的 Embench E2E 属集成步骤） |
| 夜跑（小时级） | `check-night`（tset full×3 + 长 arch）→ 报告 `.dadao/tests/night/<date>/`；`check-night-report` 由 `check-milestone` 消费 |
| 按需 / opt-in | `check-lit-full`、`check-picolibc-tests-full`、`check-testcases-suites(-full)`、`test-picolibc-smoke`、`build-bootrom`、`check-milestone`、`check-install-tools`、`clean-tests`、`test-repro` |

### 5.2 逐目标（跑什么 / 产物去哪 / 日志）

| 目标 | 层 | 跑的用例 | 产物落点 | 日志 |
|---|---|---|---|---|
| `validate-vectors` | L1 | `tests/inst` schema/inventory/覆盖（156 身份） | 无 | stdout |
| `check-case-ledger` | L1 | 清单 1,956 行 vs 现场 | 无 | stdout |
| `check-isa-coverage` | L1 | 264 身份 × 后端矩阵漂移 | 无 | stdout |
| `check-qemu-smoke` | L2 | 代表集 3 册（`aip-si`/`reg-compare`/`reg-shift-extend`） | `.dadao/tests/harness/smoke` | `.work/log/qemu/check-qemu-smoke.log` |
| `check-qemu-semantics` | L3 | 20 册全量（最近 975/980，5 deferred） | `.dadao/tests/harness/gate` | `.work/log/qemu/check-qemu-semantics.log` |
| `check-lit` | L2 | 76 MC + 63 CodeGen + 14 E2E = 153 个 lit 用例 | `.dadao/tests/lit-output/{DADAO-MC,DADAO-CodeGen,DADAO-E2E}` | stdout（逐例） |
| `check-lit-full` | L3 | `check_lit_gen.py` + 12 生成 MC 用例 | `.dadao/tests/lit-output/DADAO-MC-gen` | stdout |
| `test-codegen` | L2 | M3 15 程序 | `.dadao/tests/codegen-e2e` | `.work/log/integ/test-codegen.log` |
| `test-elf` | L2 | M4 5 程序（多 TU/段） | `.dadao/tests/elf-e2e` | `.work/log/integ/test-elf.log` |
| `check-arch-smoke` | L2 | arch 10 程序（`tests/arch/umon/`）+ 25 服务覆盖（原 `test-semihost`，判据未改） | `.dadao/tests/arch/m5-e2e`、`bootrom/` | `.work/log/arch/check-arch-smoke{,-svc}.log` |
| `check-arch` | L3 | `check-arch-smoke` + cfx min-ROM 探针 044/045/049 | 同上 | `.work/log/arch/check-arch*.log` |
| `test-semihost` | 别名 | → `check-arch-smoke`（旧前置 `test-elf`/`test-codegen`/`check` 保留） | 同上 | 同上 |
| `test-m6` | L3 | lit-full + ir-lli 19 + Embench 38 | `ir-lli-diff`、`m6-embench` | `.work/log/integ/test-m6-*.log` |
| `check-rnd-probe` | L3 | 785 例 × O0/O2 | `/tmp`+`--json-out` | `.work/log/testcases/TESTCASES-060t-*.{log,json}` |
| `check-minmax-probe` | L3 | 3,102 例 × O0/O2 | 同上 | `TESTCASES-059t-*` |
| `check-fma-probe` | L3 | 626 例 × O0/O2 | 同上 | `TESTCASES-058t-*` |
| `check-clmul-probe` | L3 | 627 例 × O0/O2 | 同上 | `TESTCASES-057t-*` |
| `check-picolibc-tests` | L2 | fast 档 20（18 pass / 2 excluded） | `.work/build/picolibc*` | stdout |
| `check-picolibc-tests-full` | opt | full 档 235（209 pass / 1 fail / 22 excluded / 3 blocked，最近日志） | 同上 | stdout |
| `check-testcases-suites` | opt | libc-test + llvm-test-suite fast 子集 | `.work/log/testcases/runs/fast.json` | stdout |
| `check-testcases-suites-full` | opt | 两套件全量可枚举 C 用例 | `runs/full.json` | stdout |
| `test-picolibc-smoke` | opt | `printf("hi")` 端到端 | `.work/build/picolibc-smoke` | stdout |
| `build-bootrom` | 前置 | `bootrom.S` + `bootrom_app.S` 汇编链接 | `.dadao/tests/bootrom` | stdout |

（表中「最近」数字取自各目标最近一次日志，非本次重跑；`make` 本册未执行任何被测语义。）

### 5.3 未接线的测试资产（重要）

| 资产 | 现状 |
|---|---|
| `tests/atomics/*.c` + `run_atomics_probe.py` | 无 make 目标；手工跑最近 711/711（两档） |
| `tests/unit/llvm/codegen/m6/*`（8 程序） | 无 make 目标，仅 README 手工命令 |
| `tests/inst/{rev,bitcnt}`（476 例） | 不在 L2/L3 载体集（`inventory.md` 明示） |
| `tests/unit/llvm/lit/tools/DADAO/` | 占位，无测试 |
| `tools/testcases/lib/test_harness_exit_path.py`（迁移期旧路径 wrapper 已删除） | 单测 5/5 通过，但**不在任何门控** |
| `tools/testcases/lib/verify_harness_dump.py`（旧路径 wrapper） | 手工工具，无门控 |
| `tools/llvm/test_m1_asm.py`、`test_encoding_oracle.py`、`tools/testcases/test_anti_forgery_008t.py` | 单测脚本，**不在任何门控**（`grep` Makefile 无命中） |
| `tests/unit/llvm/e2e/*.c`（9 个） | 仅被归档任务书/changelog 引用，无 runner |

---

## 6. 覆盖现状（事实）

- **指令身份覆盖**：`contracts/opcodes.yaml` 共 **264** 身份；向量覆盖 **193**（`m1` 152/156、`m9` 34/34、`m8` 7/7）。未覆盖：`fp` 66、`m1` cfx 4（`cfx2rc`/`cfx2rd`/`escape`/`trap`，`deferred TESTCASES-033t`）、`m3` 1（`sub.o_orrr_dbb`，由 CodeGen lit 覆盖）。`excluded` 现 0 条（`cfxld`/`cfxst` 已删除）。
- **cfx**：`inventory.md:172-175` 明示 4 个 cfx 身份 deferred；`misc.yaml` 仅 2 例。
- **fp**：66 个 `fp` 身份**无向量**，语义由 lit CodeGen + `check-{fma,minmax,rnd,clmul}-probe`（L3）承担 ⇒ 覆盖信息分散在 3 处（`inventory.md`、`llvm-isa-backend-matrix.tsv`、各 probe 日志），**无单一覆盖矩阵**（用户痛点的直接原因）。
- **lit pattern 覆盖**：`case-ledger.tsv` 守护 500 条 `@@ OBJ:` pattern。
- **门控载体**：`check-qemu-semantics` 20 册（`isa` 16 + `rol` + `atomics` ×2 + `clmul`），`rev`/`bitcnt` 未纳入。

---

## 7. 已知问题清单（供重组方案决策；本册不修）

1. **职责重叠**：顶层 `atomics/`、`clmul/`（探针源）与 `vectors/atomics/`、`vectors/clmul/`（向量）同名不同物；`tests/unit/llvm/codegen`（执行程序）与 `tests/unit/llvm/lit/CodeGen`（结构断言）也易混。
2. **无统一入口**：仓库没有「列出全部用例 / 按 ID 跑一个用例」的 runner；入口 = §5.2 的 21 个目标 + 手工 README 命令。
3. **m6 执行向量无门控**：`tests/unit/llvm/codegen/m6` 8 程序只能手工跑；`codegen-m6/`、`elf-m6/` 为手工产物目录。
4. **9 个 e2e 源无 runner**：`fp_codegen.c`、`fp_hfa.c`、`i1_load_e2e.c`、`large_const_cmp_e2e.c`、`mulhi_e2e.c`、`selectcc_e2e.c`、`setcc_e2e.c`、`smulhi_e2e.c`、`switch_jt_e2e.c`（仅归档任务书引用）。
5. **`.pyc` 残留**（084t 已清理）：`tests/**/__pycache__/` 仅运行期垃圾、不入库。
6. **孤儿生成物 1.2 G 中约 210 M 不可重生成**：`llvm-ts-user-050t/`（209 M，脚本已不存在）、`libc-argv-{static,dynamic}/`（1.2 M）、`smoke/`（48 K，旧默认落点）。
7. **`rev.yaml` 与生成器漂移**：`generate_rev_vectors.py --check` **FAIL**（62 例 `spec_cite` 仍是旧小节名，生成器现派生 `SimRISC-04: rev.o`）；因 `rev` 不在任何门控，漂移未被发现（实测见 `docs/Process-09…` §5.3）。
8. **`.dadao/tests` 无清理目标**：`clean-work` 不含它；1.2 G 只增不减。
9. **`lit-output` 含时间戳**（`.lit_test_times.txt`）⇒ 该目录**不可能**逐字节复现；确定性判据必须排除运行脚手架。

---

## 8. 计数锚点（证据脚本比对用）

<!-- INVENTORY-COUNTS:BEGIN -->
```text
tests_files_total=341
tests_files_excl_ledger=340
tests_pyc_files=9
dadao_tests_files=19967
vector_yaml_files=22
vector_cases=1456
vector_ids=193
ledger_entries=1956
ledger_vector_rows=1456
ledger_lit_rows=500
lit_mc_files=76
lit_mc_gen_files=12
lit_codegen_files=63
lit_e2e_files=14
probe_files=21
codegen_m3_programs=15
codegen_m4_programs=5
codegen_m5_programs=10
codegen_m6_programs=8
irlli_include=19
irlli_exclude=72
```
<!-- INVENTORY-COUNTS:END -->

> 生成树体积、运行目录数随门控运行变化，不作锚点。

### P6 现场复核（2026-10-27，`TESTCASES-076t`；上面锚点块保留 067t 口径）

现场命令与结果（逐条可重跑）：

```sh
find tests -type f | wc -l                     # 343（含 3 个 .pyc）
find tests -name '*.pyc' | wc -l               # 3
git ls-files tests | wc -l                     # 343（= 339 入库文件 + 4 符号链接；新增 shared/README.md 入库后 344）
find tests -maxdepth 1 -mindepth 1 | wc -l     # 14 = 7 目录 + 7 文件
grep -c '' tests/case-ledger.tsv               # 1,962 行（含 4 行注释）
make check-case-ledger                         # 现场身份 1,958 条（vector 1456 / lit 502）
```

- 迁移期符号链接（P6 遗留）已由 `TESTCASES-084t` 删除：`tools/llvm/{check_lit_bytes,gen_isa_coverage}.py`
  默认路径已改 `tests/unit/llvm/...` 并重派生 ISA 矩阵；旧 `min_rom_probe_*` 薄 wrapper（32 个）同步删除。

### 084t 现场复核（2026-10-28，`TESTCASES-084t`）

```sh
ls tests/unit/llvm/e2e/lit/*.test | wc -l     # 14
ls tools/testcases/arch/min_rom_probe_* | wc -l  # 32（旧 wrapper 0）
make check-lit                                # 158/158（现场统计）
```

### 附：本页计数所用命令

```sh
find tests -type f | wc -l                     # 341（含本册两份新文档）
find tests -name '*.pyc' | wc -l               # 9
git ls-files tests | wc -l                     # 332（含本册两文档）
find .dadao/tests -type f | wc -l              # 19967
du -sb .dadao/tests | cut -f1                  # 1132542115
grep -c '^- mnemonic:\|^- class:' tests/inst/**/*.yaml   # 逐册求和 = 1456（迁移前口径）
awk -F'\t' '!/^#/{c[$1]++} END{for(k in c) print k, c[k]}' tests/case-ledger.tsv  # vector 1456 / lit 500
ls tests/unit/llvm/lit/MC/DADAO/*.s | wc -l         # 76
ls tests/unit/llvm/lit/MC/DADAO-gen/*.s | wc -l     # 12
ls tests/unit/llvm/lit/CodeGen/DADAO/*.ll tests/unit/llvm/lit/CodeGen/DADAO/*.mir | wc -l  # 63
ls tests/unit/llvm/e2e/lit/*.test | wc -l      # 14
```
