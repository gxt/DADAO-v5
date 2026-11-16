# m15-testcases-008: 退役 clmul C/IR 探针（4 文件 + 驱动/oracle + L3 成员）

**模块**：testcases
**项目里程碑**：M15
**依赖**：无（`m15-testcases-005` 已合入）
**可并行分片**：否（改 `Makefile` / `tests/inst.yaml` / `tools/**` 共享文件，单写者）
**预估**：1.5–2 h
**档位**：中改（多文件 + 改门控组成；复核 ≥2 路注入 + 相关门控）
**状态**：待开始

## 背景（用户 2026-11-16 指令 + 两项裁定）

用户原话：「关于 clmul 的指令测试，`tests/inst/clmul/clmul_ir.ll` 你来判断要不要移动到 unit/llvm 中，其余三个可以删除」；随后两项裁定：**① L3 的 `fp-clmul` 成员直接删该行；② `run_clmul_probe.py` 与 `oracle_clmul.py` 两个都删**。

**`clmul_ir.ll` 判定 = 不搬、直接删**（现场对比）：

- `tests/inst/clmul/clmul_ir.ll` 定义 4 个函数（`clmul_generic_lo` / `clmul_intr_hi` / `clmul_pair_lo` / `clmul_pair_hi`），**文件内无断言**；结构核对在 Python 驱动（`objdump` + `ctx.add`）；
- `tests/unit/llvm/lit/CodeGen/DADAO/clmul.ll` 定义 **8 个**（上述 4 个的对应 + `clmul_pair` / `clmul_wide` / `clmul_wide_lo` / `clmul_wide_hi`），**有 `FileCheck` 结构断言**（`clmul.o {rd0, rd8}` / `{rd8, rd0}` / `{rd8, rd9}`，钉 ADR-0035 D2 的「高半在前」），跑在 **L2 `check-lit`**；
- 另有 `tests/unit/llvm/e2e/lit/clmul_builtin.test` 覆盖 `__builtin_dadao_clmul` 的编译产物。
⇒ 搬过去是**重复一份更弱的用例**，不搬。

**退役模式先例**：`m13-testcases-044`（fma/minmax/roundint）、`m13-testcases-050`（atomics 五探针）同一模式；`clmul` 是最后一个。

## 覆盖披露（须写进完成区，不得只写"退役"）

- **保住**：ISA 语义 = `tests/inst/04-arith-logic-octa/clmul.o_rrrr_rd.S`（12 检查点，三方跑）；编译器侧 = 上述 lit 两处；
- **丢掉**：① i128 **composite 的运行期**（把高低半拼回 128 位再比）只在 `clmul_edges.c`；② **GHASH、CRC-32C** 两条真实算法链路的运行期覆盖。

## 目标（一处不漏，否则门控红）

1. 删 `tests/inst/clmul/`（4 文件：`clmul_edges.c`、`clmul_ghash.c`、`clmul_crc32c.c`、`clmul_ir.ll`）；
2. `tests/inst.yaml`：删 `inst-clmul-002`…`inst-clmul-005` 四条；**头部注释**去掉 `check-{rnd,minmax,fma,clmul}-probe` 的 clmul 提法（改为「探针已全部退役」）；
3. `Makefile`：删 `check-clmul-probe` 目标（`_locked-check-clmul-probe` 及其 2 条 recipe）、`.PHONY` 清单、`reconfig` 清单、`help` 行；
4. 删 `tools/testcases/run_clmul_probe.py`（587 行）与 `tools/testcases/oracle_clmul.py`；
5. `tools/infra/check_writer_guards.py`：去掉 `tools/testcases/run_clmul_probe.py` 条目（**注意不改变其余被护栏脚本的行为**）；
6. `tools/testcases/l3_run.py`：`DEFAULT_MEMBERS` 删 `("inst", "fp-clmul", "make check-clmul-probe")`，并把上方注释改成「四类 FP 探针（rnd/minmax/fma/clmul）已全部退役，FP 由 `07-floating-point` 的 `.S` + lit + e2e 承担」（L3 余 3 成员：`check-arch` / `check-unit-full` / `test-m6`）；
7. `tests/README.md`、`tests/INVENTORY.md`：记录退役（**保留历史**，写明退役任务号与覆盖承接方），删掉"clmul 探针保留"这类过期口径；
8. `tools/qemu/user_mode_smoke.py` 第 629 行注释若仍以 `run_clmul_probe.py` 作参照，改写成不依赖已删文件的表述。

## 验收（真实 rc + 输出）

1. **零残留引用**：`git grep -n 'clmul-probe\|run_clmul_probe\|oracle_clmul\|inst-clmul-00'` = 0（`.tao/archive/**` 的历史记录**不算**残留，须显式排除并说明）；
2. `make check-tests-index` PASS，条数 = 476 − **4** = **472**（现场核）；
3. `make check-writer-guards` PASS（清理后仍能检出注入：临时给某被护栏脚本加未授权 writer 调用 ⇒ 红，`cp`+md5 还原 ⇒ 绿）；
4. `make -n check-full` 不再出现 `check-clmul-probe`；**L3 成员表 = 3 条**（`check-arch` / `check-unit-full` / `test-m6`），并核 `tools/testcases/l3_run.py` 无残余 `fp-clmul`；
5. `make check-inst-asm` **904/904**（`tests/inst` 其余载体不受影响）；`make check-inst-macro-scope`、`check-case-ledger`、`check-tests-index`、`check-dirs`、`check-no-residue` 全 rc=0；L1 `make check`（外部红须逐项归因）；
6. **2 路注入**（`cp`+md5 还原）：① 在 `tests/inst.yaml` 恢复一条 `inst-clmul-002` 指向已删文件 ⇒ `check-tests-index` 红；② 在 `Makefile` 恢复 `check-clmul-probe` 目标 ⇒ 其 recipe 报"找不到 `run_clmul_probe.py`"（红），证明依赖已断且未留假绿；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **不改变任何其它用例/门控的语义**；`check-full` 只因成员退役而少一项，不得顺带改其它成员；
- 只动：`tests/inst/clmul/**`（删）、`tests/inst.yaml`、`Makefile`、`tools/testcases/run_clmul_probe.py`（删）、`tools/testcases/oracle_clmul.py`（删）、`tools/infra/check_writer_guards.py`、`tools/testcases/l3_run.py`、`tests/README.md`、`tests/INVENTORY.md`、`tools/qemu/user_mode_smoke.py`（仅注释）、本任务书；
- **不动** `tests/unit/llvm/**`（lit 用例已覆盖，不改判据）、`tests/inst/04-arith-logic-octa/clmul.o_rrrr_rd.S`、`components/**`、`spec/`、`contracts/`；
- 不提交 git；注入还原 `cp`+md5（**禁 `git checkout/restore`**）；基线钉死 commit（`ISS-458`）。

## 审阅记录

（待填）
