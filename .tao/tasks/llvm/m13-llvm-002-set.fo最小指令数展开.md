# m13-llvm-002: `set.fo rf, imm64` 最小指令数展开（rd0 清零 + 只改非零 wyde）

**模块**：llvm
**项目里程碑**：M13
**依赖**：`m13-spec-011`（已合；`set.*` 伪指令正文在 `SimRISC-00 §5`）
**可并行分片**：否
**预估**：1.5–2 h（构建 ~2–5 min）
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：待开始

## 用户裁定（2026-11-15，原话）

> 「set.fo rf, imm64完全可以进行优化，先用rd0初始化为64位全0，然后修改非零的wyde，可能节省一至两条指令，而对于正0，则只需一条」

## 现状（doc 与实现不一致）

- **spec 已是优化口径**：`Toolchain-01 §6.1` 明确「`set.fo rf, imm64` 展开为 `rd2rf rf, rd0` + 仅对**非零** wyde 的 `set.w`；`set.fo rf, 0` ⇒ **1 条**」；
- **实现没跟上**：`DADAOAsmParser::expandPseudoInstruction` 现在是「`imm==0` ⇒ `rd2rf`；否则 **4 条 `set.w`**」（源码注释也这么写）；
- **契约陈旧**：`.tao/contracts/contract-asm.md:188` 写「`set.fo rf, imm64`（4 条 `set.w`）」，与 `Toolchain-01` 冲突。

## 任务

1. **实现最小指令数展开**（`k` = 非零 16 位 wyde 个数，0–4）：
   - `cost_rd0 = 1 + k`（`rd2rf rf, rd0` + k 条 `set.w`）；`cost_w4 = 4`（4 条 `set.w`）；
   - **取较小者**：`k ≤ 3` 用 `rd0` 方案、`k == 4` 用 4 条 `set.w`（避免出现 5 条的反向优化）；
   - `imm == 0` ⇒ 仅 `rd2rf rf, rd0`（1 条）；
   - **`set.ft rf, imm32` 不变**（仍 2 条 `set.w`）：它是**窄写**（高 32 必须保持），**不得**用 `rd2rf` 清零；
2. **同步契约**：`.tao/contracts/contract-asm.md:188` 的「4 条 `set.w`」改为「`rd2rf rd0` + 非零 wyde 的 `set.w`；`k=4` 时退回 4 条 `set.w`（最小指令数）」，并指 `Toolchain-01 §6.1`；
3. **lit 期望更新**：`tests/unit/llvm/e2e/...` 与 `tests/unit/llvm/lit/MC/DADAO/{m4-pseudo-set.s,set-ft-fo.s}` 里 `set.fo` 的期望按新展开改（含 `imm=0`、k=1、k=2、k=3、k=4 五种形态各一例）；
4. 补丁 `make_patch.py llvm` 导出 + `check-patch-tree` **llvm 段 0 问题** + `--source-state` llvm OK + `check-component-changelog`。

## 验收（真实 rc）

1. `llvm-mc` 实测五种形态的**指令条数**与操作数序列：`imm=0` ⇒ 1 条；k=1 ⇒ 2 条；k=2 ⇒ 3 条；k=3 ⇒ 4 条；k=4 ⇒ 4 条（**不是 5**）；`set.ft rf, imm32` ⇒ **仍 2 条**；
2. 语义不变：`set.fo` 写入值与 `imm64` 逐位相等（抽 3 例 dump 目的 rf）；
3. lit：`check-lit`（现场计数）、`check_lit_gen`、`validate_mc_vectors` rc=0；
4. **≥2 路注入**（`cp`+md5 还原）：① 把 `k==4` 误判成走 `rd0` 方案 ⇒ 应出现 5 条（断言红）；② 让 `set.ft` 也走 `rd0` 清零 ⇒ 高 32 被破坏（应红）；
5. 门控：`check-lit`、`check-patch-tree`（llvm 段）、`--source-state` llvm、`check-component-changelog`、`check-asm-list-drift`、`check-asm-prose`、`check-isa-coverage`；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/llvm-project/**`、`tests/unit/llvm/**`、`.tao/contracts/contract-asm.md`（仅该条）、本任务书；
- **不改** `spec/`（`Toolchain-01` 已是优化口径）、`tests/inst/**`、其它组件；
- 构建 `JOBS=32`（申报耗时）；禁 `install-host`/`check-modules`（用构建树 `llvm-mc`/`llvm-lit`）；不 sync/reset 节点；不提交 git；注入还原 `cp`+md5。

## 待裁定

（实现中写）

## 审阅记录

（待填）
