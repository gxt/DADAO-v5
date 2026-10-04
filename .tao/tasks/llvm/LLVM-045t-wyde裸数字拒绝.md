# LLVM-045t: wyde 位置仅接受 wp0–wp3（裸数字 0–3 须报错）

**模块**：llvm
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（需 `make build-mc` 重建 LLVM MC）

## 目标与 resolved_by

实现 1 条无依赖的 LLVM MC 解析收紧 issue（**需 LLVM 重建**）。用户 2026-10-04 已裁定。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-128 | `set.zw`/`set.ow`/`or.w`/`andn.w` 的 wyde 位置裸数字 0–3 被静默接受 ⇒ 只能写 `wp0`–`wp3`，裸数字须报错 |

`resolved_by`：本任务 `LLVM-045t`。

## 接口规范

- **输入**（已核实，现状）：
  - `components/llvm-project/patches/.../AsmParser/DADAOAsmParser.cpp.patch`：`parseWydePosToken()`（L400）正确解析 `wpN`；但 `parseOperand()`（L~650）对裸数字回退到 `parseImmediate()`，且 `DADAOInstrInfo.td.patch` 的 `DADAOWydePosAsmOperand`（L38-42）`PredicateMethod = isWydePosImm` 接受 `kImmediate && 0≤ImmVal≤3`。
  - 期望（用户裁定）：`set.zw rd1, 1, 0x1234` 等裸数字 0–3 须 **Error 级报错**；`set.zw rd1, wp1, 0x1234` 合法。裸 5/8 现状已正确报错。
  - 连带：`tests/e2e/smoke_add.s`、`smoke_arith.s`、`smoke_fp.s`（`smoke_jump.s` 若含实际指令）使用裸数字，须改 `wpN`；并修正其注释「wpN 被静默忽略、须用数值 0/1/2/3」（与事实相反）。`LLVM-035t:22` 旧表述**已在任务书中更正**（L27 已注明），本任务只需确认无其它残留。
- **输出**：
  - `DADAOAsmParser.cpp`（收紧 wydepos 匹配为仅接受 `parseWydePosToken` 产出的操作数）+ 必要时 `DADAOInstrInfo.td`；
  - `tests/e2e/smoke_add.s`/`smoke_arith.s`/`smoke_fp.s`（+`smoke_jump.s` 若有实际指令）改 `wpN` 并修正注释；
  - lit 正/反例（若有 MC lit 覆盖）；
  - `components/llvm-project/changelog.md` 补条目。
- **约束**：
  - **Spec-first**：以 `contract-isa.md` / `spec/Toolchain-01` 的 wyde 位置记法为真源；`ADR-0013 D9` 相关注释符（`;`）不受影响。
  - Error 级、不得降 warning。
  - 反汇编器打印 `wp0`–`wp3`（现状已正确）须回归「汇编↔反汇编往返」。
  - 与在飞 **`LLVM-034t`** 无文件交集（本任务改 AsmParser/e2e），但**构建串行**。

## 验收标准

1. `llvm-mc` 对 `set.zw rd1, 1, 0x1234`、`set.ow rd2, 0, 1`、`or.w rd3, 3, 0x1`、`andn.w rb4, 2, 0x1` → **EXIT≠0**、Error 级（裸数字被拒）。
2. `llvm-mc` 对 `set.zw rd1, wp1, 0x1234`、`or.w rd3, wp3, 0x1` 等 → EXIT=0，编码与修复前一致（wpN 语义不变）；反汇编回 `wpN`。
3. **反例门控**：恢复 `isWydePosImm` 接受裸数字（或 `parseImmediate` 兜底）后重建 → 验收 1 应 FAIL（旧“静默接受”行为）；还原并**重建** → 回绿。给出注入→FAIL→还原→重建→PASS 的真实输出（还原须含重建）。
4. `tests/e2e/*.s` 中所有**实际指令**不再使用裸数字 wyde 位置（`grep` 逐文件核对，注释中引用的说明文字须改为正确表述）；`make check-lit`、E2E smoke 全绿。
5. `make check` EXIT=0；`check-patch-tree` 通过。

## 硬约束

- 临时目录 `/tmp/opencode/LLVM-045t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- **重建成本申报**：重建 LLVM MC，预计 30–90 分钟；一次只跑一个；`JOBS` 默认 8。
- 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
- 复杂命令输出留存 `.work/log/llvm/LLVM-045t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/LLVM-045t/`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
