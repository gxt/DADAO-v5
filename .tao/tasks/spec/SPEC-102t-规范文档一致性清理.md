# SPEC-102t: 规范/文档一致性清理（FP 文案、RB 加减澄清、RAS 描述、ret 符号、计数）

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目标与 resolved_by

合并 5 条无依赖的纯文档/计数 issue（无组件重建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-082 | `scope: fp` 的「未实现，decode ILLI」陈旧文案收口 |
| ISS-129 | `spec/SimRISC-05` §RB 加减「低 48 位」与「全 64 位」字面矛盾澄清 |
| ISS-121 | `contracts/legality_rules.yaml` 的 `excp_rasof`/`excp_rasuf` 描述同步 ADR-0012 D7（MemRAS 引用计数已取消） |
| ISS-107 | `spec/SimRISC-06 §函数返回` 补「符号/非常量操作数一并拒绝」 |
| ISS-131 | 5 处文档/注释的 opcodes 计数 227→228 |

`resolved_by`：本任务 `SPEC-102t`（若某条实际由既有任务修复，见「遗留问题」注）。

## 接口规范

- **输入**（改动对象，逐条）：
  - `spec/SimRISC-00-指令系统设计.md` L290、L379（`scope: fp`/`excluded` 分区说明）、`.tao/knowledge/contract-isa.md` L25、L821/L823（`§9 浮点运算指令`）。
  - `spec/SimRISC-05-64位地址运算.md` L35（`add.o`/`sub.o` 同段「全 64 位参与运算」+「地址计算仅在低 48 位有效，溢出丢弃」）及 L55 同类表述；并检查 `SimRISC-00` 等文件中 RB 加减/叠加的同类表述。
  - `contracts/legality_rules.yaml` L217–L235（`excp_rasof`/`excp_rasuf` description）。
  - `spec/SimRISC-06-控制流.md` §函数返回（L130–L155）。
  - 计数 5 处：`spec/Toolchain-01-汇编语言.md:5`、`docs/README.md:17`、`.tao/knowledge/contract-asm.md:8`、`tools/spec/gen_legality_list.py:7`、`tools/qemu/check_qemu_trans.py:85`。
- **输出**：上述文件按各 issue 目标修订后的版本（仅文本/注释；不改编码表、不改 `contracts/opcodes.yaml`）。
- **约束**：
  - **ISS-082 口径确认（下发前必做）**：issue 提到的「R1 口径」在仓库内**查无定义**（原 backlog 已删除）。期望语义（据 `contract-fp.md` 与 M2 达成记录）：`scope: fp` 60 条**语义已归一化于 `contract-fp.md`、执行层 60/60 已实现**（`QEMU-034t~038t`）；「未实现，decode ILLI」只应保留给 **`scope: excluded`**（cfx/LR-SC/fence）。**下发前须由用户确认目标措辞**，不得自行发明。
  - **ISS-129 口径**（用户 2026-10-04 已裁定）：RB 加减为**全 64 位运算、结果完整 64 位**；仅当以该值**访存**时硬件取 `rb[47:0]`，`rb[63:48]` 表示地址溢出。按此改写矛盾句。
  - **ISS-107**：仅补规范说明；`ret rd0, <符号>` 现由 `LLVM-027t` 保守拒绝（汇编期无法证明为 0），规范侧补「符号/非常量操作数一并拒绝」一句即可，**不改 LLVM 实现**。
  - **ISS-131**：目标计数 = `grep -c '^- id:' contracts/opcodes.yaml`（当前 **228**）。仅改这 5 处字面，不扩大。
  - 不触碰 `spec/SimRISC-0.5.3/`、`.tao/archive/**`、`docs/` 中的归档产物；**若用户正在并发归档 `docs/**`、`spec/**`，本任务须与其串行**（见「待用户拍板」）。

## 验收标准

1. **ISS-082**：`grep -n "未实现，decode ILLI" spec/SimRISC-00-指令系统设计.md .tao/knowledge/contract-isa.md` 在 **`scope: fp` 语境下 0 命中**；`scope: excluded` 保留处仍在且语义正确（人工核对 + 逐行输出）。
2. **ISS-129**：`spec/SimRISC-05-64位地址运算.md` 不再出现「地址计算仅在低 48 位有效」与「全 64 位参与运算」并列的**字面矛盾**；含「访存时取低 48 位、高 16 位表示溢出」的明确表述。
3. **ISS-121**：`grep -n "MemRAS 引用计数" contracts/legality_rules.yaml` → 0 命中；`excp_rasof`/`excp_rasuf` 描述与 ADR-0012 D7（有效性判据 `ra0[53:48]`）一致。
4. **ISS-107**：`spec/SimRISC-06-控制流.md` §函数返回含「符号/非常量操作数一并拒绝」表述，且与 `LLVM-027t` 行为一致。
5. **ISS-131**：`grep -rn "227"` 在上述 5 文件 → 0 命中；`grep -c '^- id:' contracts/opcodes.yaml` = 228，且 5 处文案均为 228。
6. **反例注入（证明门控/断言可失败）**：在隔离副本把任一处 228 改回 227 ⇒ 验收 5 的 grep 检出 FAIL；还原。对 ISS-082，在副本恢复一处「未实现，decode ILLI」⇒ 验收 1 检出 FAIL；还原后 byte-identical。
7. `tools/infra/check_issues.py` 对 `resolved_by` 字段无报错（若本任务顺带改 issues.yaml 则适用）；纯文档改动**豁免 `make check`**，但须 `git status` 干净。

## 硬约束

- 临时目录 `/tmp/opencode/SPEC-102t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- 复杂命令输出留存 `.work/log/spec/SPEC-102t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/SPEC-102t/`（可复用检查器落 `tools/spec/`）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
