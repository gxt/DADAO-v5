# DADAO-v5 全流程复现计划

本计划参照 DADAO-0628 的完整实现流程，基于 DADAO-v5/wiki 的 11 份规范文档（SimRISC 0.5.3），规划从零开始的完整全栈实现。

## 项目定位

**DADAO-v5** 基于更新版本的规范文档（SimRISC 0.5.3 vs 0.4.1），相比 DADAO-0628 新增了：
- **完整浮点支持**：SimRISC-03 定义了 ~60 条浮点指令（运算、转换、块操作）
- **系统指令扩展**：fence、LR-SC 原子操作、cfx 特权指令族
- **RA 寄存器操作**：ldo-ra/sto-ra、rd2ra/ra2rd
- **RF 寄存器操作**：ldt/stt/ldmt/stmt、ldmo/stmo-rf

## 11 阶段总览

| 阶段 | 名称 | 对应 DADAO-0628 | 关键交付物 | 估算 |
|------|------|----------------|-----------|------|
| **Phase 0** | 基础设施与规范锁定 | M0 + ADR-0001/0002 | 锁文件、Makefile、ADRs、目录结构 | ~3 个 agent |
| **Phase 1** | ISA 规范合约与编码表 | Phase 0.5A + DL-001a/b | spec.md、opcodes.yaml、legality_rules.yaml | ~3 个 agent |
| **Phase 2** | 测试向量基础设施 | DL-001c/019a/020a | schema、inventory、YAML 向量文件 | ~3 个 agent |
| **Phase 3** | Python Golden Model | ADR-0009 M2a + DL-040b | dadao_interp.py、validate_interp.py | ~3 个 agent |
| **Phase 4** | ABI 合约与架构决策 | DL-002a/003a/004a | abi/elf/sbi spec、ADRs | ~3 个 agent |
| **Phase 5** | 组件基线 | DL-005a/006a | 组件锁、补丁目录、Docker | ~2 个 agent |
| **Phase 6** | LLVM MC 后端 | DL-007a~012a | LLVM MC 补丁 | ~3 个 agent |
| **Phase 7** | QEMU 模拟器 | DL-013a~018a + 023a~030a | QEMU 补丁 | ~3 个 agent |
| **Phase 8** | 集成测试与差分验证 | Phase 4 (MC↔QEMU) | 差分运行器、E2E 测试 | ~3 个 agent |
| **Phase 9** | gem5 第二参考 | DG-001a~005a | gem5 补丁 | ~3 个 agent |
| **Phase 10** | Sail 形式化规范 | SL-001a~003a | sail 模块、Sail C 模拟器 | ~3 个 agent |
| **Phase 11** | LLVM CodeGen | Phase 5 (Basic CodeGen) | CodeGen 补丁、E2E 测试 | ~4 个 agent |

## 依赖关系图

```
Phase 0 (Foundation)
  ├──→ Phase 1 (ISA Contract + Encoding)
  │     ├──→ Phase 2 (Test Vectors)
  │     │     └──→ Phase 3 (Golden Model)
  │     │           ├──→ Phase 8 (Integration & Differential) ←─── Phase 7 (QEMU)
  │     │           │     ├──→ Phase 9 (gem5) ──→ Phase 10 (Sail)
  │     │           │     └──→ Phase 11 (CodeGen) ←── Phase 6 (LLVM MC)
  │     │           │
  │     └──→ Phase 6 (LLVM MC) ──→ Phase 11 (CodeGen)
  │
  ├──→ Phase 4 (ABI/ELF/SBI Contract)
  │     ├──→ Phase 6 (LLVM MC)
  │     └──→ Phase 11 (CodeGen)
  │
  └──→ Phase 5 (Component Baseline)
        ├──→ Phase 6 (LLVM MC)
        ├──→ Phase 7 (QEMU)
        ├──→ Phase 9 (gem5)
        └──→ Phase 11 (CodeGen)
```

## 关键原则（来自 DADAO-0628 经验）

| 原则 | 说明 |
|------|------|
| **Spec-first** | 所有编码/语义期望值来自 contracts/，不从实现反推 |
| **Independent oracle** | 测试向量不能从 LLVM 或 QEMU 生成，必须独立派生自 wiki |
| **四路差分** | interp/QEMU/gem5/Sail 四路一致才算语义正确 |
| **非复用** | 不复制 DADAO-0628 的实现代码，只参考工程经验 |
| **精确异常** | fault 触发时无副作用，PC 停在触发指令 |
| **编译器产物原则** | CodeGen 测试必须使用 llc 产物，禁止手写汇编替代 |
| **subagent 自审** | 所有改动必须经过 subagent code review |

# Phase 0：基础设施与规范锁定

> 对应 DADAO-0628 的 M0（Reproducible Foundation）+ ADR-0001/0002

## 目标

建立 DADAO-v5 仓库的可复现基础设施：目录结构、锁文件、构建脚本、工作规则和核心决策记录。这是所有后续阶段的基石。

## 输入文件（DADAO-v5/wiki）

| 文件 | 用途 |
|------|------|
| `README.md` | 项目描述、版本号信息 |
| `AGENTS.md` | 命名约定、异常路由规则 |
| 所有 11 个 wiki 文档 | 用于确定 scope 边界 |

## 参考文件（DADAO-0628）

| 文件 | 用途 |
|------|------|
| `CODEX.md` | 工作规则模板 |
| `DS.md` | 子代理规范模板 |
| `Makefile` | 构建脚本模板 |
| `manifests/spec.lock.toml` | 锁文件格式模板 |
| `manifests/components.lock.toml` | 组件锁文件格式模板 |
| `docs/repository-layout.md` | 仓库布局模板 |
| `docs/definition-of-done.md` | 完成标准模板 |
| `docs/architecture-boundaries.md` | 架构边界模板 |
| `docs/greenfield-charter.md` | Greenfield 宪章模板 |
| `docs/adr/0001-greenfield-rebuild.md` | ADR-0001 模板 |
| `docs/adr/0002-build-orchestration.md` | ADR-0002 模板 |
| `docs/development-roadmap.md` | 路线图模板 |
| `docs/test-strategy.md` | 测试策略模板 |
| `scripts/doctor.py` | 环境检查脚本 |
| `scripts/manifest_check.py` | manifest 验证脚本 |
| `scripts/fetch.py` | 组件获取脚本 |
| `scripts/apply_series.py` | 补丁应用脚本 |
| `scripts/status.py` | 状态报告脚本 |

## 输出文件

```
DADAO-v5/
├── AGENTS.md                    # 通用规则（重写，精简版）
├── Makefile                     # 主构建入口
├── .gitignore                   # 忽略 .work/、__pycache__ 等
├── manifests/
│   ├── spec.lock.toml           # 规范锁定（锁定当前 wiki 状态）
│   ├── components.lock.toml     # 组件锁定（初始全部 disabled）
│   └── references.toml          # 参考仓库引用（DADAO-0628 等）
├── project/
│   ├── adr/
│   │   ├── 0001-greenfield-rebuild.md
│   │   └── 0002-build-orchestration.md
│   ├── rule-architect.md        # 架构师角色规范
│   ├── rule-subagent.md         # 子代理角色规范
│   ├── rule-reviewer.md         # 审查者角色规范
│   ├── MEMORY.md                # 跨会话快速定位
│   ├── repository-layout.md     # 仓库布局说明
│   ├── definition-of-done.md    # 完成标准
│   ├── architecture-boundaries.md
│   ├── greenfield-charter.md
│   ├── development-roadmap.md
│   ├── test-strategy.md
│   ├── designs                 # 设计文档目录（空）
│   │   └── 0001-foundation-scope.md
│   ├── tasks                   # 任务文件目录（空）
│   └── knowledge               # 知识库目录（空）
├── verif/README.md             # 验证工具目录占位
├── tests/README.md             # 测试目录占位
├── components/README.md        # 组件目录占位
├── scripts/
│   ├── doctor.py               # 环境健康检查
│   ├── manifest_check.py       # manifest 验证
│   ├── fetch.py                # 组件获取
│   ├── apply_series.py         # 补丁应用
│   ├── status.py               # 状态报告
│   ├── clean_work.py           # 清理 .work 目录
│   └── validate_vectors.py     # 向量验证（骨架）
└── .git/
```

## 子代理分解

### Agent A1：仓库骨架与锁文件

**职责**：创建 manifests 目录结构、锁文件、Makefile

**提示词**：
```
你是 DADAO-v5 的基础设施工程师。基于 DADAO-v5/wiki 的 11 份规范文档创建仓库基础设施。

请执行以下操作：

1. 创建 `manifests/spec.lock.toml`：
   - format = 1
   - name = "DADAO-v5 wiki"
   - status = "frozen" 
   - 获取 DADAO-v5 仓库当前 git commit 作为锁定的 commit（git rev-parse HEAD）
   - 从 README.md 读取各版本号（SimRISC 0.5.1, AEE/ABI 0.9.2, SEE/SBI 0.7.1, HEE/HBI 0.1.2）
   - foundation_included 清单列出当前 wiki 覆盖的范围
   - foundation_excluded 列出尚未覆盖的范围（参考已有的 11 份文档边界）

2. 创建 `manifests/components.lock.toml`：
   - 参考 DADAO-0628 的格式
   - LLVM/QEMU/musl/linux 全部 disabled，留空 commit
   - 添加 chipyard 组件（DADAO-v5 新增目标）

3. 创建 `Makefile`：
   - manifest-check → 验证 manifests 格式
   - doctor → 检查 Python3, git 等依赖
   - status → 显示锁定版本
   - fetch → 获取组件（骨架，实际组件 disabled 时不执行）
   - check → manifest-check + doctor

4. 创建 `project/` 下的子目录：`adr/`、`tasks/`、`designs/`、`knowledge/`

5. 创建 `manifests/references.toml`：
   - 记录 DADAO-0628 作为参考仓库
   - 格式同 DADAO-0628 的 references.toml
   - 只作为参考引用，不复制代码

6. 创建空目录：`verif/`、`tests/`、`components/`、`project/reviews/`

参考 DADAO-0628 的对应文件格式和结构，但所有内容基于 DADAO-v5 规范（SimRISC 0.5.1）重新编写。

完成后返回创建的文件列表和关键决策。
```

### Agent A2：架构决策与设计文档

**职责**：创建 project/adr/、AGENTS.md（重写）、角色规则文件、参考文档

**提示词**：
```
你是 DADAO-v5 的系统架构师。基于 DADAO-v5/wiki 的 11 份规范文档创建架构决策记录和设计文档。

请执行以下操作：

1. **重写 `AGENTS.md`**（根目录）：
   - 精简为所有角色共享的通用规则
   - 命名约定（/wpN/pmem/illi 等）
   - 指令格式后缀（rrrr/rrri/brrr 等）
   - 异常路由规则（IALIGN > ILLI > MALIGN > 页表 > FPEXCP）
   - 仓库结构概述
   - 引用 project 下的三个角色规则文件

2. 创建 `project/rule-architect.md`：
   - 架构师角色的职责定义
   - 任务创建和分配规则
   - 架构决策流程
   - 验收标准

3. 创建 `project/rule-subagent.md`：
   - 子代理（执行 agent）的职责定义
   - Spec-first 原则
   - 独立 oracle 原则
   - 任务编号格式（DL-NNNx）
   - 自审流程（subagent 强制）
   - 工作规则（CodeGen 任务的编译器产物规则等）

4. 创建 `project/rule-reviewer.md`：
   - 审查者职责
   - 审查流程（读 diff、验输出、写审阅记录）
   - 判决标准

5. 创建 `project/MEMORY.md`：
   - 项目概要和目录索引
   - 各阶段状态追踪
   - 关键决策速查
   - 已知问题和踩坑记录

6. 创建 `project/adr/0001-greenfield-rebuild.md`：
   - 与 DADAO-0628 ADR-0001 类似但不相同
   - 上下文：基于 SimRISC 0.5.1 规范的完整全栈实现
   - 决策：从干净上游 commit 开始，不复制旧实现
   - 影响：每个行为需可追溯规范

7. 创建 `project/adr/0002-build-orchestration.md`：
   - 决策：Make + Python 标准库脚本
   - 生成内容放 .work 目录

8. 创建 `project/designs/0001-foundation-scope.md`：
   - 定义 Phase 0-11 的完整 scope
   - 明确包含/排除项

9. 创建 `project/repository-layout.md`：
   - 基于 DADAO-0628 修改
   - 目录结构说明（参考当前 README.md 末尾的映射表）
   - 新增 chipyard 目录说明（DADAO-v5 新增硬件目标）

10. 创建 `project/definition-of-done.md`：
    - 7 条完成标准（同 DADAO-0628）
    - 编译成功、汇编器往返、单实现测试不足以作为证据

11. 创建 `project/architecture-boundaries.md`：
    - 合约矩阵（编码/语义/寄存器模型/调用约定/ELF/异常/MMU）
    - 列举 DADAO-v5 的 11 份 wiki 文档覆盖范围
    - 注意新增的浮点（SimRISC-03）和系统接口（SBI/HBI）边界

12. 创建 `project/greenfield-charter.md`：
    - 目标：可追溯到 11 份 wiki 规范的 LLVM/QEMU/Chipyard/Linux 栈
    - 非复用规则
    - 工程规则列表

13. 创建 `project/development-roadmap.md`：
    - M0：可复现基础 ← 当前阶段
    - M1：MC 汇编/反汇编 + QEMU 标量核心
    - M2：基本 CodeGen（标量整数/指针）
    - M3：浮点支持
    - M4：系统支持（异常/MMU/SBI）
    - 延后：Linux 内核、完整运行时

14. 创建 `project/test-strategy.md`：
    - 独立 oracle 规则
    - 测试层次（6 层）
    - 必需指令测试案例
    - 差分验证策略（interp/QEMU/gem5/Sail 四路一致）

完成后返回创建的文件列表。
```

### Agent A3：工具脚本与规范

**职责**：创建 scripts 下的工具脚本

**提示词**：
```
你是 DADAO-v5 的工具工程师。创建基础设施工具脚本。

创建以下脚本到 `scripts/` 目录：

1. `doctor.py`：环境健康检查
   - 检查 Python3 >= 3.8
   - 检查 git 可用
   - 检查 make 可用
   - 检查 `manifests/` 存在
   - 输出 PASS/FAIL 状态

2. `manifest_check.py`：manifest 验证
   - 读取 `manifests/spec.lock.toml`
   - 验证字段完整性（format, name, status, commit, 版本号）
   - 验证 `manifests/components.lock.toml`
   - 输出验证结果

3. `fetch.py`：组件获取（骨架）
   - 读取 `manifests/components.lock.toml`
   - 对 enabled 组件：git clone 到 `.work/source/<name>`
   - 对 disabled 组件：跳过
   - 支持 `--force` 重新获取

4. `apply_series.py`：补丁应用（骨架）
   - 读取组件 `patches/series` 顺序文件
   - 按序 `git am` 到 `.work/source/<name>`
   - 支持 `--dry-run` 预览

5. `status.py`：状态报告
   - 读取 spec.lock.toml 显示锁定版本
   - 读取 components.lock.toml 显示组件状态
   - 检查 `.work/` 目录下的各组件检出状态
   - 输出表格

6. `clean_work.py`：清理工作目录
   - 安全删除 `.work/` 目录的全部内容
   - 要求 `--force` 确认

使用 Python3 标准库（不依赖第三方包）。参考 DADAO-0628 中对应脚本的实现风格。
```

## 验证标准

- `make manifest-check` 通过
- `make doctor` 显示 PASS
- `make status` 显示正确的版本号
- `make check` 全部通过
- 目录结构与 `repository-layout.md` 一致

## 依赖关系

- 本阶段不依赖其他阶段
- 是后续所有阶段的前提条件
