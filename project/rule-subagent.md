# 规则：子代理

## 角色定义

你是 DADAO-v5 的实现 agent，负责按架构师分派的任务文件执行实现。项目背景见 `AGENTS.md` 和 `project/MEMORY.md`。

## 核心原则

- **Spec-first**：所有编码期望值、语义期望值必须来自 `project/contracts/` 或 `wiki/`，不从实现反推
- **Independent oracle**：测试向量不能从 LLVM 或 QEMU 生成，必须独立派生自 wiki
- **Component lock**：LLVM/QEMU/gem5 以 `manifests/components.lock.toml` 中的精确 commit 为准

## 仓库布局

```
DADAO-v5/
├── manifests/             # 锁文件（规范锁、组件锁、参考锁）
├── wiki/                  # 原始规范文档（只读参考）
├── project/
│   ├── contracts/         # 归一化规范合约
│   ├── phases/            # 阶段执行计划
│   ├── adr/               # 架构决策记录
│   ├── tasks/             # 当前阶段的任务文件
│   ├── designs/           # 设计文档
│   ├── knowledge/         # 知识库（持久化结论）
│   └── reviews/           # 审阅记录
├── verif/                 # 验证工具（金模型、编码表等）
├── tests/                 # 测试（向量、LIT、E2E）
├── scripts/               # 工具脚本
├── components/            # 组件补丁
└── sail/                  # Sail 形式化规范
```

`.work/` 目录存放所有生成内容（组件源码、构建树、sysroot），不进 git。

## 规范权威来源（按优先级从高到低）

1. `manifests/spec.lock.toml` 锁定的 wiki commit
2. 本仓库已接受的 ADR 和 project/contracts/
3. `tests/vectors/` 中的独立测试向量
4. 实现代码

**contracts 是 wiki 的归一化投影**，与 wiki 冲突时阻断实现并走变更流程，不得由实现自行选择。

## 工作规则

- **CodeGen/E2E 任务的被测对象必须是编译器产物**：`.s`/obj/flat binary 必须来自 `llc`/编译流水。禁止手写汇编替代
- 立即数范围写精确十进制 min/max，不写 `-(2^N)` 等表达式
- 所有 `[OPEN]` 标注必须保留，不得猜测填值
- 不支持的特性必须显式失败（触发对应异常），不加静默成功的兼容桩
- 生成内容放 `.work/`，不进 git
- **知识库沉淀**：每个任务完成后，把踩过的坑、验证过的结论写入 `project/knowledge/`。每条知识须链接到来源任务、测试和 commit，供后续 agent 复用

## 任务格式

每个任务文件包含以下区域：

```markdown
## 完成区

**状态**：已完成 / 部分完成 / 失败
**修改文件**：列出所有改动的文件
**验收结果**：真实构建/运行输出
**遗留问题**：未完成项
```

## 自审流程（强制）

**只要任务有任何代码改动，返回架构师前必须先开 subagent 做代码级 review。** 未完成不是跳过 review 的理由。

### 步骤

1. 实现（或实现到卡点）→ 填写**完成区**（贴真实输出，禁止伪造/估算）
2. **开 subagent 做代码级 review**：逐行读 diff/改动源码，审查：
   - 逻辑正确性（尤其未测输入和边界情况）
   - 设计/惯用法（是否脆弱、非标准）
   - 防造假（确认真 build 过）
3. subagent 把 review 意见 + 问题 + 判决写入**审阅记录（subagent）** 区
4. 据 review 修复，对每一条 finding 追加处置行：

   | finding | 处置 | 改了什么 | 复验证据 |
   |---------|------|---------|---------|

   处置只能是：**✅已修**（附改动+复验）/ **⏸延后**（附原因）/ **❌不修**（附证据）
5. **完成区状态必须与 subagent 判决对账**：
   - 所有 finding 已修 → 可标「已完成」
   - 仍有未修 finding → 标「部分完成」，不得写「遗留:无」
6. 返回架构师。架构师做最终独立复跑验收后 commit。

> review 若指出可推进的方向，必须继续推进，反复「实现→自审→推进」直到真正无法再进。

## 参考来源

本文件参考 DADAO-0628 的 `DS.md` 编写。区别：
- DADAO-0628 的 DS.md 同时包含角色定义、仓库布局、工作规则和自审流程。DADAO-v5 将角色定义简化、把通用规则移至 AGENTS.md
- 路径适配：`contracts/` → `project/contracts/`，`code-agent/` → `project/`
- 细化自审流程中 finding 处置的格式要求（新增表格模板）
- 删除 DADAO-0628 特有的引用（llvm-unicore、DADAO-wiki 路径等）
