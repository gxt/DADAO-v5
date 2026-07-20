# MEMORY — DADAO-v5 项目记忆

## 这是什么

DADAO-v5 基于 11 份 wiki 规范文档（SimRISC 0.5.3），从零构建 LLVM/QEMU/Chipyard/Linux 全栈。核心方法是"Agent 写代码、你写约束"——角色分工见 AGENTS.md。

## 当前进度

| 项目 | 状态 |
|------|------|
| SimRISC 规范 | ✅ 0.5.3，已更新 |
| 基础设施（Phase 0） | ⏸ 待开始（等你确认后执行） |
| 后续阶段 | 待 Phase 0 完成后推进 |

## 关键目录速查

| 路径 | 用途 |
|------|------|
| `wiki/` | 11 份原始规范文档 |
| `manifests/` | 锁文件（规范/组件/参考） |
| `project/phases/` | 阶段执行计划 |
| `project/contracts/` | 归一化合约（待各阶段填充） |
| `project/tasks/` | 按阶段分的任务文件 |
| `project/knowledge/` | 已验证的知识沉淀 |
| `project/adr/` | 架构决策记录 |
| `project/reviews/` | 审阅记录 |
| `verif/` | 验证工具（金模型、编码表） |
| `tests/` | 测试向量 |
| `components/` | 组件补丁 |
| `scripts/` | 工具脚本 |
| `sail/` | Sail 形式化规范 |

## 重要决策

- `verif/` 替代 `tools/` 作为验证工具目录
- `project/` 集中存放所有 agent 中间文件
- 任务编号 `Dnnn`，按阶段分 `project/tasks/PhaseN/` 子目录
- 三条角色规则文件（架构师/子代理/审查者），放在 `project/` 下

## 如何参考 DADAO-0628

各阶段文件开头的"参考文件（DADAO-0628）"表格列出了该阶段需要的来源文件对应关系。按阶段查找即可。

## 规范版本对应

| 配对 | 版本 |
|------|------|
| SimRISC | 0.5.3 |
| AEE ↔ ABI | 0.9.2 |
| SEE ↔ SBI | 0.7.1 |
| HEE ↔ HBI | 0.1.2 |

## 关键差异提示（相比 DADAO-0628）

DADAO-v5 基于 SimRISC 0.5.3 规范，与 DADAO-0628（锁定在 SimRISC 0.4.1）相比有以下关键差异：

### 0.5.3 vs 0.4.1 的变化

1. **指令命名重构**：所有指令使用 `.b`/`.w`/`.t`/`.o` 位宽后缀，有符号/无符号用 `s`/`u` 区分（如 `add.uo`/`add.so`、`mul.uw`/`mul.sw`）。原 0.4.1 的 `add`/`sub`/`muls`/`mulu`/`divs`/`divu`/`cmps`/`cmpu`/`exts`/`extz`/`shrs`/`shru`/`shlu` 等命名已废弃。此外，LR/SC 原子指令使用 `_nn`/`_nr`/`_an`/`_ar` 后缀标记 acquire/release 语义

2. **格式体系重构**：引入 MISC-byte/wyde/tetra/octa 四个子表，通过 `orrr`/`orri` 格式覆盖各固定位宽的 and/or/xor/xnor/ext/shr/shl/add/sub/cmp/mul/div/rem 操作

3. **QFC 编码表重组**：opcode 分配完全改变（见 SimRISC-00 QFC 表），涉及所有指令的 mask/value

4. **新指令**：`add.si`（riii 格式自增自减）、`br.z-rb`/`br.nz-rb`（rb0 零/非零分支）、`cs.n-rf`/`cs.z-rf`/`cs.p-rf`/`cs.eq-rf`/`cs.ne-rf`（浮点条件赋值）

5. **寻址语义变化**：RB 算术改为全 64 位运算（原 48 位限制移除，bits[63:48] 为运算结果可用于溢出检测）

6. **立即数格式变化**：`add.si` 从 rrii（两寄存器 + 12 位 imm）改为 riii（一寄存器 + 18 位 imm）；`rela.si` 同理

7. **浮点扩展**：新增 `ft2ft`/`fo2fo`（浮点内部格式转换）

8. **命名风格统一**：`.` 作为命名分隔符（`cs.n`/`cs.z`/`cs.p`、`br.n`/`br.nn`/`br.z`、`set.zw`/`set.ow`、`or.w`/`andn.w`）

### 不变的差异（从 0.4.1 延续）

- 浮点架构完整定义（SimRISC-03），需 golden model 骨架和 LLVM 寄存器类
- 系统指令：cfx2rd/cfx2rc/cfxld/cfxst/trap/escape 指令族（SimRISC-04）
- 原子操作：lr/sc LR-SC 指令
- 命名规范：wpN（非 ww）、pmem（非 phymem）、illi（非 unimp）
- Scope 更广（含浮点/系统），实现优先级可先聚焦标量核心

## 文件映射：wiki → contracts

| wiki 文件 | 对应 contract（在 project/contracts/ 下） | 主要消费者 |
|-----------|------------------------------------------|-----------|
| SimRISC-00 ~ 04 | `isa-spec.md` | golden model, LLVM, QEMU, gem5, Sail |
| DADAO-11 AEE | `isa-spec.md` (§1) + `abi-spec.md` | golden model, LLVM |
| DADAO-12 SEE | `exception-contract.md`（推迟）+ `sbi-spec.md` | QEMU, Linux |
| DADAO-13 HEE | `exception-contract.md`（推迟） | Chipyard |
| DADAO-21 ABI | `abi-spec.md` | LLVM CodeGen |
| DADAO-22 SBI | `sbi-spec.md` | QEMU, Linux |
| DADAO-23 HBI | `sbi-spec.md` | Chipyard, Linux |
