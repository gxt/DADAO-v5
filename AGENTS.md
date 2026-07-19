# AGENTS.md — DADAO-v5 通用规则

所有角色（架构师、子代理、审查者）共同遵守的规则。角色特定规则见 `project/rule-*.md`。

## 仓库结构速览

```
DADAO-v5/
├── manifests/           # 锁文件（规范、组件、参考）
├── wiki/                # 11 份原始规范文档（SimRISC + DADAO 环境）
├── project/             # agent 中间文件集中目录
│   ├── phases/          # 阶段执行计划
│   ├── adr/             # 架构决策记录
│   ├── contracts/       # 从 wiki 提取/归一化的规范合约
│   ├── tasks/           # 任务文件
│   ├── designs/         # 设计文档
│   ├── knowledge/       # 知识库
│   ├── reviews/         # 审阅记录
│   └── rule-*.md        # 角色规则文件
├── verif/               # 验证工具（金模型、编码表、差分运行器）
├── tests/               # 测试（向量、LIT、E2E）
├── scripts/             # 工具脚本
├── components/          # 组件补丁系列
└── sail/                # Sail 形式化规范
```

## 方法论概述

本仓库的本质是一套让 AI Agent 正确工作的约束系统，而非传统意义上的"项目"。三个角色分工：

| 角色 | 做什么 |
|------|--------|
| **架构师** | 冻结规范、写合约、拆分任务、验收交付 |
| **子代理** | 读任务 → 实现 → 自审 → 提交 |
| **审查者** | 独立重跑验收命令 → 读 diff → 判决 |

**工作流**：冻结规范基线 → 提取合约 → 生成机器可读数据 → 锁定组件版本 → 逐任务推进实现 → 差分验证 → 沉淀知识库。

**核心原则**：Spec-first（所有期望值来自合约，不从实现反推）、Independent oracle（测试向量不从实现生成）、Component lock（精确 commit，不用 tag/branch）。

核心认知——"**不是你写代码、Agent 帮你，而是 Agent 写代码、你写约束**。" 你的工作变成了：写清楚"什么是对的"→ 拆成 Agent 能理解的小任务 → 验收 → 把经验沉淀到知识库。

## 命名约定

- wyde position：`wpN`（非 `wN`、`ww`），编码 `00=wp0, 11=wp3`
- 寄存器 bank 前缀仅编码表使用（如 `add.uo-rd-rrrr`），汇编语法不体现

## 指令命名规范

SimRISC 0.5.3 指令名通过多个后缀组合表达指令特性，按 `.` 分隔位宽/符号/条件后缀，按 `_` 分隔 acquire/release 后缀（仅 LR/SC 原子指令）。

### 位宽与符号后缀

指令名后缀区分数据位宽和符号类型：

| 后缀 | 含义 | 示例 |
|------|------|------|
| `.b` | byte（8 位） | `and.b`, `add.ub`, `add.sb` |
| `.w` | wyde（16 位） | `or.w`, `mul.uw`, `mul.sw` |
| `.t` | tetra（32 位） | `xor.t`, `div.ut`, `div.st` |
| `.o` | octa（64 位） | `xnor.o`, `cmp.uo`, `cmp.so` |
| `.ub`/`.sb` | unsigned/signed byte | `ext.ub`, `ext.sb` |
| `.uw`/`.sw` | unsigned/signed wyde | `shr.uw`, `shr.sw` |
| `.ut`/`.st` | unsigned/signed tetra | `shl.ut`, `shl.st` |
| `.uo`/`.so` | unsigned/signed octa | `add.uo`, `add.so` |
| `.ui`/`.si` | unsigned/signed immediate | `cmp.ui`, `cmp.si` |

### 条件后缀

条件判断出现在条件赋值、条件分支等指令名中：

| 后缀 | 条件 | 示例 |
|------|------|------|
| `.n` | 负数 | `cs.n`, `br.n` |
| `.nn` | 非负数 | `br.nn` |
| `.z` | 零 | `cs.z`, `br.z` |
| `.nz` | 非零 | `br.nz` |
| `.p` | 正数 | `cs.p`, `br.p` |
| `.np` | 非正数 | `br.np` |
| `.eq` | 相等 | `cs.eq`, `br.eq` |
| `.ne` | 不相等 | `cs.ne`, `br.ne` |

### 存储访问后缀

LR/SC 原子指令的 acquire/release 标记：

| 后缀 | 含义 | 示例 |
|------|------|------|
| `_nn` | 无 acquire 无 release | `lr_nn.o`, `sc_nn.o` |
| `_nr` | 无 acquire 有 release | `lr_nr.o`, `sc_nr.o` |
| `_an` | 有 acquire 无 release | `lr_an.o`, `sc_an.o` |
| `_ar` | 有 acquire 有 release | `lr_ar.o`, `sc_ar.o` |

## 指令格式后缀

```
rrrr / rrri / rrii / riii / iiii / rwii   ← 无前缀
orrr / orri / oiii                        ← o=minor-opcode
ciii / crrr / crii                        ← c=cfxcode
```

操作数字段含义：
- `o`：六位 minor-opcode（在 `ha[5:0]`）
- `c`：六位 cfxcode（在 `ha[5:0]`）
- `r`：寄存器编号（6 位，编码 0-63）
- `i`：立即数（有符号或无符号，长度由格式决定）
- `w`：wyde-position（hb[5:4]，指定 16 位立即数写入 64 位寄存器的哪个 wyde）+ 16 位立即数（hb[3:0] 为高 4 位，hc[5:0] 为中 6 位，hd[5:0] 为低 6 位）
- `z`：SBZ（Should Be Zero）

## MISC 子表体系

SimRISC 0.5.3 将操作按位宽组织为多个 MISC 子表，每个子表对应一个 opcode：

| 子表 | opcode | 位宽 | 包含指令类 |
|------|--------|------|-----------|
| MISC-AMO | 0x00 | — | illi, fence, LR/SC 原子操作 |
| MISC-octa | 0x40 | 64 位 | and/o, xor/xnor, ext, shr/shl, add/sub, cmp, rd2rd/rd2ra/ra2rd, rb2rb/rd2rb/rb2rd, div/rem, rd2rf/rf2rd |
| MISC-tetra | 0x41 | 32 位 | and/o, xor/xnor, ext, shr/shl, add/sub, cmp, mul, div/rem |
| MISC-wyde | 0x42 | 16 位 | and/o, xor/xnor, ext, shr/shl, add/sub, cmp, mul, div/rem |
| MISC-byte | 0x43 | 8 位 | and/o, xor/xnor, ext, shr/shl, add/sub, cmp, mul, div/rem |
| MISC-RF | 0x44 | 浮点 | ftcls/focls, ft2fo/fo2ft, ft2ft/fo2fo, ftlog/folog, ftroot/foroot, 浮点运算, 格式转换 |

每个子表内的具体指令由 ha（minor-opcode）进一步区分。

## ABI 寄存器命名

| bank | 特殊寄存器 | 约定 |
|------|-----------|------|
| RD | rd0=zero, rd1=rderrno | rd2-7 reserved, rd8-15 temp, rd16-31 参数, rd32-63 callee-saved |
| RB | rb0=rbip, rb1=rbsp, rb2=rbfp, rb3=rbgp, rb4=rbtp | rb5-7 reserved, rb8-15 temp, rb16-31 参数, rb32-63 callee-saved |
| RF | rf0=FCSR | rf1-15 temp, rf16-31 参数, rf32-63 callee-saved |
| RA | ra0=RAS控制, ra63=RAS栈顶 | ra1-62 返回地址 slot |

## 文档对应关系

| 配对 | 版本同步要求 |
|------|-------------|
| AEE ↔ ABI | 必须一致 |
| SEE ↔ SBI | 必须一致 |
| HEE ↔ HBI | 必须一致 |
| 全部 | 基于同一 SimRISC 版本号 |

## 核心原则

- **Spec-first**：所有编码/语义期望值来自 `project/contracts/`，不从实现反推
- **Independent oracle**：测试向量不能从 LLVM 或 QEMU 生成，必须独立派生自 wiki
- **Component lock**：LLVM/QEMU/gem5 以精确 commit hash 锁定，不用 tag/branch
- **非复用**：不复制 DADAO-0628 的实现代码，只参考工程经验

## 角色规则引用

| 角色 | 规则文件 |
|------|---------|
| 架构师 | `project/rule-architect.md` |
| 子代理（执行 agent） | `project/rule-subagent.md` |
| 审查者 | `project/rule-reviewer.md` |
