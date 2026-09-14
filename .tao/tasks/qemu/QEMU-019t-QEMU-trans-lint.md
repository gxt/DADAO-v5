# QEMU-019t: QEMU trans lint

**模块**：qemu
**项目里程碑**：M1
**依赖**：`SPEC-003t`、`QEMU-013t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `contracts/opcodes.yaml`（M1 mnemonic 列表）
  - `components/qemu/patches/*.patch`（QEMU trans 函数来源）
- 输出：`tools/qemu/check_qemu_trans.py`：每个 M1 opcode 是否有 `trans_<mnemonic>`（lint，默认 exit 0）
- 约束：
  - `check_qemu_trans.py` 是 lint 不是 gate，默认 exit 0；可提供 `--strict` 使其 exit 1
  - mnemonic 标准化：`-` → `_`、全小写；同 mnemonic 多 opcode 只需一个匹配
  - 只读 `contracts/opcodes.yaml` 与 patch，不改组件源码
  - 脚本放 `tools/qemu/`

## 背景（完整）

### 目标

验证 `components/qemu/patches/` 中每条 M1 opcode 都有 `trans_<mnemonic>` 实现——缺失会走 ILLI stub 导致测试静默失败，目前只能人工逐个检查。

### 设计理由

翻译链里「QEMU trans 覆盖」此前靠人眼检查，容易漏。机械化为 lint，才能让 trans 缺失可见。

### 关键概念 / 数据

**`check_qemu_trans.py` 逻辑**：

1. 读 `contracts/opcodes.yaml`，收集 M1 mnemonic（排除 M1 scope 外项）
2. 每个 mnemonic：grep `components/qemu/patches/*.patch` 是否含 `trans_<normalized>`（`-`→`_`）
3. 收集缺失项输出警告
4. 打印 `check_qemu_trans: N/M mnemonics have trans impl`
5. 默认 exit 0；`--strict` 时 exit 1

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-023a-issue-registry-trans-lint.md`（trans lint 部分）
- DADAO-0628：`scripts/check_qemu_trans.py`（形态参考，禁止复制正文）

## 交付物

- `tools/qemu/check_qemu_trans.py`：trans 函数存在性 lint
- 完成区附真实 stdout 与 trans 覆盖统计

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **MISC 映射表重建**：0.5.3 没有 `MISC-Norm`，改为主表 + octa/tetra/wyde/byte/RF/AMO 子表体系。
2. **助记符全面变化**：`unimp`→`illi`、`setzw`→`set.zw`、`orw`→`or.w`、`brn`→`br.n`、`muls`→`mul.so` 等；trans 函数命名以 `QEMU-013t` 实际实现为准核对。
3. **trans 源码路径**：v5 以 `components/qemu/patches/*.patch` 与 `.work/` 构建树为准。
4. **脚本目录**：`scripts/` → `tools/qemu/`。

## 已知坑 / 结论

1. **trans lint 非阻断**：默认 exit 0，仅 lint 警告；`--strict` 才 exit 1。MISC 特殊指令（`swym`/`illi` 等）可能无独立 trans，属预期缺失。
2. **mnemonic 标准化**：`-`→`_`；同 mnemonic 多 opcode（如 `add.si` 的 RD/RB 变体）只需一个 trans 匹配。
3. **硬编码映射表易漂移**：v5 重建时须以 `QEMU-013t` 实际函数名为准，并考虑直接从 `opcodes.yaml` + 命名约定推导以减少硬编码。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-023a-issue-registry-trans-lint.md`
- DADAO-0628：`.work/DADAO-0628/scripts/check_qemu_trans.py`
- 本项目：`contracts/opcodes.yaml`、`components/qemu/patches/`、`.tao/knowledge/contract-isa.md`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 tools/qemu/check_qemu_trans.py` 输出 `N/M mnemonics have trans impl` 与 MISSING 明细，默认 exit 0
2. `--strict` 时缺失项导致 exit 1
3. 脚本只读 `opcodes.yaml` 与 patch，不改组件源码
4. 完成区粘贴真实 stdout

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
