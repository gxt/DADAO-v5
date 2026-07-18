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

## 命名约定

- bit position：`bpN`（非 `bmN`、`bitmask`），`bp63` = 全 64 位
- wyde position：`wpN`（非 `wN`、`ww`），编码 `00=wp0, 11=wp3`
- 物理内存：`pmem`（非 `phymem`）
- 非法指令助记符：`illi`（非 `unimp`）
- 寄存器 bank 前缀仅编码表使用（如 `add-rd-brrr`），汇编语法不体现

## 指令格式后缀

```
rrrr / rrri / rrii / riii / iiii / rwii        ← 无前缀
orrr / orri / oiii                              ← o=minor-opcode
ciii / crrr / crii                              ← c=cfxcode
brrr / brri                                     ← b=bit position (bpN)
```

## 异常路由规则

- 跨类别优先级：**IALIGN > ILLI/UNDI > MALIGN > 页表 > FPEXCP**
- 步骤 3/4 sync 被 mask 屏蔽 → `cause←ILLI` + 重定向到 monitor（不能直接 return）
- 步骤 5 sync 被 mask 屏蔽 → pending（仅 FPEXCP 可达）
- cfx mask 自身 cfxcode 硬件忽略
- escape 退出前检查 escape_cfx_mask

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
- **精确异常**：fault 触发时无副作用，PC 停在触发指令

## 角色规则引用

| 角色 | 规则文件 |
|------|---------|
| 架构师 | `project/rule-architect.md` |
| 子代理（执行 agent） | `project/rule-subagent.md` |
| 审查者 | `project/rule-reviewer.md` |
