# m15-testcases-010: 01 册 ld/st 修正（opc 注释 + boundary 极值 + rb0 基址用例）

**模块**：testcases
**项目里程碑**：M15
**依赖**：无（`tests/inst/01-load-store/` 现状；`m15-testcases-009` 已合入）
**可并行分片**：否（同册共享 `.inc` 与布局）
**预估**：5–7 h
**档位**：中改（注释 1 行 + 4 个文件加用例 + 01 册加 rb0 用例；复核 diff + 1 路注入 + 受影响门控）
**状态**：待开始

## 背景（用户 2026-11-17 发现）

用户在 `tests/inst/01-load-store/ld.o_rrii_rd.S` 发现三处问题，均已核实：

1. **opc 注释错误**：`ld.o_rrii_rd.S:3` 写 `opc：0x16`，`contracts/opcodes.yaml` 的 `ld.o_rrii_rd` 是 `0x20`。全仓 272 个 `.S` 机械比对只有这一处不一致（`ld.t_rrii_rf` 的 0x16 是正确的，`ld.t` 真实 opc 就是 0x16）。
2. **boundary 极值不全**：`ld.o_rrii_{rd,rb,ra,rf}.S` 的 boundary 段已有 `0x7FFFFFFFFFFFFFFF`（正向极大）、`0x0000000000000080`、`0x0`、`0x5555…`、`-0x800`、`-0x7F8`，但**缺** `0xFFFF_FFFF_FFFF_FFFF`（无符号全 1）与 `0x8000_0000_0000_0000`（有符号极小；后者目前只在 `semantic` 段出现）。
3. **`rb0` 作基址未覆盖**：`spec/SimRISC-01` 只禁**目的** `rbHA = rb0`（ILLI）；**基址 `rbHB = rb0` 合法**（`spec/SimRISC-00`：`rb0` 读出 = 当前指令地址 IP，只读）。当前 01 册的 `rb0` 只出现在控制流 `[rb0, …]`，没有数据访问用例。

> 用户 2026-11-17 指示：**本任务只修这三处，不建门控**（不做 opc↔opcodes.yaml 的机械校验器）。

## 目标

1. **opc 注释**：`ld.o_rrii_rd.S:3` 的 `opc：0x16` → `opc：0x20`（只改注释，编码/mask 不变）。
2. **boundary 极值补全**（**01 册全部 38 个 `ld/st/ldm/stm` 文件**：`ld.o`×4、`ld.sb/st/sw/ub/ut/uw`+`ld.t_rrii_rf`=7、`ldm.o`×4、`ldm.sb/st/sw/t/ub/ut/uw`=7、`st.b`×1、`st.o`×4、`st.t`×2、`st.w`×1、`stm.b`×1、`stm.o`×4、`stm.t`×2、`stm.w`×1；按各自宽度）：按各自宽度补齐「正向极大 / 负向极小 / 全 1」三条（8 位 `0x7F`/`0x80`/`0xFF`；16 位 `0x7FFF`/`0x8000`/`0xFFFF`；32 位 `0x7FFFFFFF`/`0x80000000`/`0xFFFFFFFF`；64 位 `0x7FFF…`/`0x8000…`/全 1）。**`TEST_DATA` 已含全部所需值，不得改 `inst_test.inc`**；各条从现有 beat 偏移引用（8 位：`+0x30`(`0x80`)/`+0x59`(`0x7F`)/`+0x58`(`0xFF`)；16 位：`+0x50`/`+0x58`/`+0x48`；32 位：`+0x20`(高字 `0x80000000`)/`+0x2C`(高字 `0x7FFFFFFF`)/`+0x40`；64 位：`+0x20`/`+0x28`/`+0x88`）。每个文件至少补
   - `0xFFFF_FFFF_FFFF_FFFF`（无符号全 1）
   - `0x8000_0000_0000_0000`（有符号极小）
   期望值用**已有测试数据/现场派生**，禁在 `.S` 里写死「看起来对」的常量（现有 `TEST_DATA` 24 个 beat 的字面量见 `tests/inst/macros/inst_test.inc`；若目标 beat 已含上述值，直接引用其地址即可）。
3. **`rb0` 基址用例**（01 册**所有后缀形式**，每个 `ld/st/ldm/stm` 的 `.b/.w/.t/.o`）：**每条指令形式须覆盖 `imm` 的 `负 / 零 / 正` 三档**（用户 2026-11-17 要求）；
   - `ld.o rd, [rb0, imm]`、`st.o rd, [rb0, imm]`、`ldm.o {…}, [rb0, rdHC]`、`stm.o {…}, [rb0, rdHC]`；
   - EA = **当前指令地址 + imm**（`iprefix` 语义见 `spec/SimRISC-00`；`rb0` 读当前 IP、**不是**下一条）；
   - **期望值必须现场派生**：用链接期符号/`aip` 或已知布局计算目标地址上的内容（例如读回该地址的指令字），**不得写死**；写入用例同理（写到代码区需谨慎，优先选可写的只读无关区/预先布置的数据区）。
   - 若某条在现有布局下不可构造（例如 `st` 写入代码区会破坏执行），在完成区写明原因并给出替代（如 `ldm/stm` 只测 `[rb0]` 的 `ldm` 方向），**不得静默跳过**。
4. 不改任何非 01 册文件；不新增 `.S` 文件（用例加在现有文件内，保持镜像数不变）。

## 验收（逐条贴真实 rc）

1. `ld.o_rrii_rd.S:3` 的 opc = `0x20`；与 `contracts/opcodes.yaml` 一致。
2. 四个文件的 boundary 段各含 `0xFFFF…`/`0x8000…` 两条，期望值来源可追溯（测试数据 beat 地址或链接期计算），**不写死**。
3. 01 册存在 `[rb0, …]` 的数据访问用例（至少 `ld.o`/`st.o`/`ldm.o`/`stm.o` 各一），期望值现场派生；`ip=当前指令` 的语义被断言到（不是下一条）。
4. **镜像与门控**：`check-inst-asm` **272/272**（镜像数不变）、`check-case-ledger`、`check-tests-index`、`check-inst-macro-scope`（含 S9）、`check-dirs`、`check-no-residue` 全 rc=0。
5. **1 路注入**（`cp`+md5 还原）：把 opc 注释改回 `0x16` ⇒ 验收 1 的核对断言必红（用一次性脚本核对，不入仓）；还原后回绿。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 只动：`tests/inst/01-load-store/ld.o_rrii_{rd,rb,ra,rf}.S`（+ 若 rb0 用例需加在 `ld.o_rrii_rb.S`/`st.o_rrii_rb.S`/`ldm.o_rrri_rb.S`/`stm.o_rrri_rb.S` 内则一并）、本任务书。**不动** `spec/`、`contracts/`、`tools/`、`Makefile`、其它册。
3. **不改任何版本号**（版本号升级须用户认可，见 `AGENTS.md`）。
4. 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore/stash/show`、禁 `reset --hard`）。

## 待裁定

（无；用户 2026-11-17 已明确：只修三处、不建门控）

## 审阅记录

（待填）
