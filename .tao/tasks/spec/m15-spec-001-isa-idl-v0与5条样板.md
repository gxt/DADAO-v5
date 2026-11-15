# m15-spec-001: ISA IDL 语法 v0（UDB IDL 基线）+ 5 条样板 operation + `idlc` 复用评估

**模块**：spec
**项目里程碑**：M15
**依赖**：`m14-spec-001`/`m14-spec-003`（启动 ABI 与内核窗口，只作语义上下文，不阻塞）；无其它 M15 前置
**可并行分片**：否（单册单写者：`spec/SimRISC-*` + `contracts/isa/` + `tools/spec/`）
**预估**：3–5 天
**状态**：待开始

## 用户裁定（2026-11-13，渠道 = 主会话问答）

> 1. M15 = 「ISA 语义结构化」，把 spec 升级为「每条指令一段可解析的 operation」，**不执行**（执行归 M17）。
> 2. **以 `riscv-unified-db` 的 IDL 为准**；不合适处再扩展；不要自造"四不像"语法。
> 3. 执行方式：**边写边改**（先 5 条样板，语法随样板修正）。
> 4. 授权：本任务可修改 `spec/SimRISC-0x` 与 `spec/README.md`（只加 operation 块与说明，不改既有语义），并同笔更新只读锁。

## 背景与取向

- UDB 有正式 IDL 文档 `doc/idl.adoc`：强类型（`Bits<N>`）、`X(rs1)` 寄存器访问、`jump(...)`/`raise(ExceptionCode::...)`、`function` 定义、配置常量；工具侧有 `idlc`（IDL 编译器）与 VS Code `yamlidl` 语法高亮。
- 本仓 spec 目前只有散文 + 模板行（如 `ld.o rdHA, [rbHB, imms12]`），无 per-instruction operation。
- **本任务的产物是"第一版可运行的形态"，不是最终语法**；允许在 5 条样板上迭代修正语法，并把每次修正写进 `contracts/isa/idl-v0.md` 的变更记录。

## 交付物

1. `contracts/isa/idl-v0.md`：**语法说明（直接引用 UDB `doc/idl.adoc` 的规则，不复制其全文）+ 本仓扩展清单**：
   - 扩展一律优先用 IDL `function`（四 bank 读写、48 位地址/分区、大端访存、异常集、cfx 分发）；
   - 若必须改语言（例如新增类型/语法），**单列「扩展提案」**，写清动机、被否替代方案、对 `idlc` 兼容性的影响。
2. **5 条样板 operation**，写入对应 spec 分册的指令小节（fenced ```` ```idl ```` 块）：
   - `add.so_rrrr_rd`（`SimRISC-04`；双目的 + 符号扩展 128）
   - `ld.o_rrii_rd`（`SimRISC-01`；48 位地址、大端、对齐、`rd0⇒ILLI`）
   - `br.eq_rrii_rd`（`SimRISC-06`；**IP = 当前指令地址**、目标写回 `rb0`）
   - `lr.o.nn_rrri_rd`（`SimRISC-12`；保留标记键 = 精确地址 + 宽度）
   - `trap_ciii_cfx`（`SimRISC-11`；cfx 编号 + `immu18` 服务号，无 CSR/向量表）
3. `tools/spec/extract_idl.py` 原型：从 spec 抽取 ```` ```idl ```` 块 → `contracts/isa/idl/`（一指令一文件）；`--check` 逐字节比对，缺失/漂移即非零退出。
4. **`idlc` 复用评估报告**（写进完成区 + `contracts/isa/idl-v0.md` 一节）：许可证、能否离线运行、是否绑定 RISC-V CSR/`X[]` 模型、可否只复用**语法/解析器**而不引入其语义库；给出「直接复用 / 只借语法自写抽取器」的结论与证据（实际跑一次 `idlc`）。

## 验收

1. 5 条 operation 块存在且可被 `extract_idl.py` 抽取；抽取结果与 spec 内块**逐字节一致**；`--check` 幂等（两次运行同一结果）。
2. 5 条样板覆盖本任务声明的「DADAO 扩展点」：四 bank、48 位地址、大端、异常集、cfx 分发；每条至少出现一次。
3. `contracts/isa/idl-v0.md` 内每条扩展都能对应到「IDL 现有能力 / 新增 function / 扩展提案」三态之一，**无未分类项**。
4. `idlc` 评估有**真实命令与退出码**；「能否离线」用断网/离线方式实证（不得只凭 README 断言）。
5. 可达 FAIL 注入 ≥2 路（抽取值改错 / spec 块删一行 / 扩展清单漏项）⇒ 门控非零退出；`cp`+md5 还原回绿。
6. spec 门控（`check-spec-*`）+ `check-spec-readonly` + `check-contracts-dir` 全绿；锁 sha 同笔重算。
7. 完成区 ≤30 行、无运行期路径；不改台账 / `discussing.md`。

## 状态与推进口径（用户 2026-11-15）

- **肯定要做**，但**本轮不裁决**；先处理其它裁定项，M15 **最后**再议。
- 用户提出的两点前置要求：
  1. **要能看到"修改后的文件内容"** —— WIP 分支 `0584a64b`（17 文件 / +1005 行）目前只在 git 里，需要以**可读形式**摊开（建议：`contracts/isa/idl-v0.md` 全文 + 5 个 `.idl` + 6 册 operation 块 + `extract_idl.py` 关键函数，逐段过目）；
  2. **逐条语句如何定义需要展开分析** —— 即对每条 operation 块按语句逐条讲清"这句在定义什么、依据哪条 spec 散文、对应哪个编码字段/副作用"，而不是只看能否解析。
- 因此后续 M15 任务书须增加一节「逐条语句分析」，作为审阅的主要材料。
- 当前状态：分支落后 master 341 提交；任务书 `**状态**` 由主会话改回 **`待返工`**（原 `待验收` 为已终止子代理所留，不实）。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git。
3. 完成区与真实输出逐条对齐；计数现场统计。
4. 只动「交付物」列出的文件；越界须披露。
5. 需用户语义裁定写进「待裁定」段返回主会话（尤其：是否允许新增 IDL 语法）。
6. 禁 `git checkout/restore/stash` 还原注入；用 `cp`+md5。

## 待裁定

（实现中写：问题 + 选项 + 建议 + 自决的临时处置。）

## 审阅记录

（待填）
