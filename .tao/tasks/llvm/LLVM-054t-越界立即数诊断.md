# LLVM-054t: 越界立即数诊断（禁静默环绕）

**模块**：llvm
**项目里程碑**：M4
**依赖**：`LLVM-051t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/knowledge/contract-asm.md` §2.4（立即数范围；地址立即数 `%4==0` 校验）、§9（诊断：未知助记符/越界寄存器/立即数越界等须报错）、§11（**缺陷**：越界立即数**静默环绕**；实例 `add.si rd8, 131072` → 编码为 −131072；`cmp.ui …, 4096` → 0）；`.tao/adr/adr-0013-assembly-syntax.md` D3（装配器 `%4` + 范围校验，非 4 倍数或越界 ⇒ 报错）。
  - `.tao/knowledge/contract-asm-list.md` 的「立即数范围速查」（各立即数字段位宽/取值范围）；`contracts/opcodes.yaml`（字段位宽）。
  - 现有 AsmParser（`AsmParser/DADAOAsmParser.cpp`）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  - AsmParser 对**每个**立即数字段做**范围校验**：越界 MUST **报错**（`Error`，非零退出），**MUST NOT** 静默按位截断/环绕；地址类立即数同时校验 `%4==0`。
  - 诊断文本 SHOULD 含位置（文件:行:列）与「期望范围」提示（`contract-asm §9`）。
  - 覆盖所有受影响指令族（`add.si`/`cmp.ui` 等 riii；分支/call/jump 的 `imms14/20/26`；访存 `imms12`；`ret imms18`；`orri immu6`；`rwii immu16` 等，按 `contract-asm-list.md` 速查逐一核对）。
- **约束**：
  - **不静默环绕**：越界一律报错；**合法边界值**（如 `imms18` 的 −131072/131071、`imms14` 的 −8192/8188、`add.si` 的合法 18 位范围）必须**接受**（不得误杀）。
  - `%4==0` 仅对**地址类**（跳转/分支目标与 escape/访存？按 `contract-asm §2.4`/§3.2：跳转/分支目标偏移与 escape 偏移单位为字节且须 `%4==0`）适用；勿误加到非地址立即数（`ret imms18` 值非地址、`orri immu6` 非地址）。
  - **reloc/fixup 坑预防（5 条，同 `LLVM-050t`）**：符号/可重定位操作数不得被范围校验误判（不可在汇编期求值者交链接期）。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建/串行/临时目录/留证纪律同 `LLVM-050t`；`ninja -j8`；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-054t/`；**不提交 git**。

## 验收标准

1. 构建 EXIT=0。
2. **越界报错（反例）**：`add.si rd8, 131072`、`cmp.ui rd8, rd9, 4096` 等（`contract-asm §11` 实例）→ `llvm-mc` 报告越界错误、非零退出；逐例给出真实 stderr 输出。
3. **边界接受**：各字段的**最小/最大合法值**（含负边界）→ `llvm-mc` EXIT=0 且编码正确（逐条 oracle 核对）。
4. **对齐**：地址类非 4 倍数（如 `jump [rb0, 6]`）→ 报错；`ret` 非地址 立即数**不**受 `%4` 约束。
5. **无静默环绕**：任选 ≥3 个字段注入越界值，均报错（不再出现「编码成 −x / 0」的静默环绕）。
6. **lit 向量**：`tests/llvm/lit/MC/DADAO/` 新增反例用例（`%not` + `expected-error` 或等价）；`make check-lit` EXIT=0 不回归；`make check` EXIT=0；`make test-codegen` 不回归。
7. 一键证据脚本 `.work/evidence/LLVM-054t/run.sh`（含 `--inject`：把某字段范围校验改宽/删掉 → 该用例由报错变接受 → 期望 FAIL → 还原+重建 → 回绿）；完成区贴真实输出。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
