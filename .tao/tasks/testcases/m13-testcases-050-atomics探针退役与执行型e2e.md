# m13-testcases-050: `atomics` 探针退役 + 执行型 `atomics_e2e`（用户裁定 A）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-049`（`00-isa-design/atomic_rmw.S` 覆盖指令层 RMW 合成序）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：待开始

## 用户裁定（2026-11-15）

选 **A**：删 5 个 C 探针与驱动/oracle；指令层由 `atomic_rmw.S` 承担；**编译器语义层补一个执行型 e2e**；争用层记 GAP。

## 背景（现场）

- `tests/inst/atomics/` 5 个 C 探针（`aba_treiber`/`atomic_builtins`/`barrier_probe`/`c11_alltypes`/`counter`）+ `tools/testcases/run_atomics_probe.py` + `oracle_atomics.py`；
- **无任何门控**：`Makefile` 无 `check-atomics-probe`、`tools/testcases/l3_run.py` 无成员；只有 `tools/testcases/README.md` 教人手工跑；
- 分层归属：① 指令层 RMW 合成序 → `m13-testcases-049`（`.S`）；② **builtin/C11 运行期** → 本任务补 **1 个执行型 e2e**；③ 争用（ABA/计数/barrier）与内存序强度 → 单 hart 不可观测，记 GAP（挂 `ISS-440`/`ISS-443`）。

## 任务

1. **退役**：`git rm -r tests/inst/atomics/`、`tools/testcases/run_atomics_probe.py`、`tools/testcases/oracle_atomics.py`；删 `tests/inst.yaml` 里 5 条；`tools/testcases/README.md` 删该节；
2. **新增执行型 e2e**：`tests/unit/llvm/e2e/atomics_e2e.c` + `tests/unit/llvm/e2e/lit/atomics_e2e.test`，**照 `fma_e2e.test` 的形态**（clang `-S` + FileCheck 汇编断言 + **链接 crt0/lds 后用 `%qemu -machine dadao-tiny,bootrom-image=…` 真跑 guest，退出码即判据**）；
   - 覆盖：`__atomic_fetch_add/sub/and/or/xor`（返回值 = 旧值、内存 = 新值）、`__atomic_exchange`、`__atomic_compare_exchange`（成功/失败两路、失败时 memory 不变）、以及 **C11 `<stdatomic.h>`** 的 `atomic_fetch_add`/`atomic_exchange`/`atomic_compare_exchange_strong` 各一例（类型 + 对齐）；
   - 每例失败即 `return 非 0`，并打印可定位的序号（沿用既有 `fma_e2e.c` 风格）；
3. **GAP 登记**：`tests/inst/MIGRATION.md` 新增一节「多 hart / 内存序 GAP」：ABA、互斥计数、`a_barrier` 观测量、`fence` 顺序强度 ⇒ 待多 hart 机型；指 `ISS-440`/`ISS-443`；
4. `case-ledger` 重生成；`tests/inst.yaml` 条数减少（5 条）；`check-tests-index`/`validate-vectors` 计数同步。

## 验收（真实 rc）

1. **e2e 真跑**：`llvm-lit tests/unit/llvm/e2e/lit/atomics_e2e.test -v` ⇒ PASS，且贴 guest 退出码 0（不是只 FileCheck）；
2. **可达 FAIL ≥2 路**（`cp`+md5 还原）：① 把某例期望的"旧值"改错 ⇒ e2e 退出码非 0；② 让 `compare_exchange` 失败路径写入内存 ⇒ 退出码非 0；
3. 退役后：`tests/inst/atomics/`、两个工具文件不存在；`grep -rn "run_atomics_probe\|oracle_atomics" Makefile tools/ tests/ docs/` = 0（`.tao/archive/**`、`components/llvm-project/changelog.md` 历史记录豁免，需在完成区列出）；
4. 门控：`check-tests-index`（现场条数）、`validate-vectors`（载体数）、`check-case-ledger`、`check-inst-asm`（id 264 不变）、`check-lit`、`check-no-residue`、`check-knowledge-refs` rc=0；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `tests/inst/**`（删 5 个 C）、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tests/unit/llvm/e2e/**`、`tools/testcases/{README.md,run_atomics_probe.py（删）,oracle_atomics.py（删）}`、`tests/inst/MIGRATION.md`、本任务书；
- **不改** `spec/`、`contracts/`、`components/**`（`oracle_atomics` 若被组件 import ⇒ 停下写「待裁定」，先核 `grep -rn "import oracle_atomics" components/`）；
- 禁 `install-host`/`check-modules`/`build-*`；不 sync/reset 节点；不提交 git；注入还原 `cp`+md5。

## 待裁定

（实现中写）

## 审阅记录

（待填）
