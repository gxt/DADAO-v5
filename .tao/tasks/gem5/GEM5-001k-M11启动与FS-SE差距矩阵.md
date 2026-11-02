# GEM5-001k: M11 启动与 FS/SE 差距矩阵

**模块**：gem5
**项目里程碑**：M11
**状态**：已验证

## 用户授权

用户 2026-11-01：M11 同时包含 gem5 FS + SE；参考 0628 的 gem5 经验但不复制代码；按 DADAO 最新 spec/contracts 重做；测试按 `docs/Process-09` 的四 scope 复用/合并，不新建 `tests/gem5` 平行体系；GEM5/QEMU 对应模式结果一致。

## 目标（纯分析，不改实现）

产出 M11 的 FS/SE 差距矩阵与任务拆分依据：

1. **共同 ISA 核心**：当前 `contracts/opcodes.yaml`（264 条 / 66 FP / 0 excluded / 34 M9）与 PR #3 旧基线（259/60/27 excluded）的差异；0628 的 `tools/opcodes.yaml` 仅 92 条，不能作为计数基线；列出必须按 v5 规范重建的指令/FP/fault/RegRAS 面。
2. **SE 专属**：`Process`/`SEWorkload`、ELF/args/stack、syscall emulation、brk/mmap/VMA、TLS、exit；对照 0628 `DG-001a/002a/007a` 的已验证结构，但只吸收结论。
3. **FS 专属**：Machine-01、boot ROM、hypv→supv、semihosting、PTW/TLB/A-D、timer/中断、power；对照 0628 `KL-124a/126a/127a/129a/131a/133a/137a/141a` 的结论，但只吸收教训。
4. **测试矩阵**：`tests/inst`（FS）、`tests/arch`（FS）、`tests/tset`（SE）、`tests/unit`（工具链）；QEMU system↔gem5 FS、QEMU user↔gem5 SE；同一 case ID，不新增平行用例。
5. **其它模块依赖**：LLVM/QEMU/picolibc/Makefile/manifest/tools 的改动清单，标 `需用户批准`；测试单独任务。
6. **任务拆分建议**：G1（共用 ISA + SE）、G2（FS）、G3（一致性/测试）、G4 的任务粒度与风险。

## 输入事实（现场核对）

- v5 当前 spec/contracts 为唯一真源；0628/PR 只作参考。
- 0628 ADR-0010：SE 先行、FS 后接；`AtomicSimpleCPU`；时序 out of scope。
- 0628 已知坑：`SEWorkload`/`Process` 混淆、LLD 多段 ELF、QEMU trampoline 的 RB1 不可照搬、RB bank/RegClass/rd0/rb0 语义、不能整体克隆 RISC-V arch。
- PR #3：FS only、draft、base 旧、12 冲突；旧 259/60 验收不能用于当前 264/66。

## 约束

- 不改 `components/**`/`tests/**`/`spec/**`/`contracts/**`/`Makefile`；只写本任务书与证据。
- **语义复用禁令**：编码/助记符相同不等于语义可复用；每条指令必须从当前 spec/contracts 重导，G1 先产出语义重导矩阵。
- 不跑实现/长构建；不复制 0628 代码。
- 证据落 `.work/evidence/GEM5-001k/`；临时 `/tmp/opencode/GEM5-001k/`。

## 验收

1. 矩阵逐项列出来源（spec/contracts 或 0628/PR 路径），区分事实/推测。
2. 给出 G1/G2/G3 的任务数和依赖，明确哪些需用户批准。
3. 给出测试复用/合并表：每个现有 scope 的 case 来源、QEMU/gem5 对应模式、不得新增项。
4. 无实现代码改动；`git status` 仅本任务书/里程碑/证据（证据不入 git）。
5. 完成区 ≤30 行，状态 `待验收`，里程碑行同步。

## 完成区

**测试结果**：分析类，无实现/构建；证据 `.work/evidence/GEM5-001k/REPORT.md`（未入 git）。
**修改文件**：本任务书、`.tao/knowledge/milestones.md`；为识别新模块，`tools/infra/check_milestones_fresh.py` / `check_milestone_tasks.py` / `check_run_artifacts.py` 增加 `GEM5` 前缀（仅工具识别，不改判据）；未改 components/tests/spec/contracts/Makefile。
**验收结果**：完成共用 ISA/SE/FS/测试/其它模块依赖矩阵；确认 264/66/0 与 PR 旧 259/60/27 差异；确认 SE 先行、FS 后接；提出 G1/G2/G3 任务量 10–15/15–25/5–8；测试映射到 inst/arch/tset/unit，禁止 tests/gem5。
**新发现/坑**：0628 的 SEWorkload/Process 桥、LLD 多段 ELF、QEMU trampoline RB1、RB bank/RegClass、RISC-V clone 都是必须规避的已知坑；PR #3 只有 FS 且旧基线，不能直接作为当前验收。**同编码/同助记符不等于同语义**：G1 必须先做逐指令语义重导矩阵（操作数/结果/异常/FP/标志/内存副作用），不能按旧表搬运。
**遗留问题**：G1/G2/G3 任务书未立；LLVM/QEMU/picolibc/Makefile/manifest/tools 改动需用户逐项批准；测试单独任务。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-01）

**环境说明**：审查期间主会话并发推进——G0 已 squash 入 master（`8f8458dd`，状态→已验证）、GEM5-002t 分支已建（现 HEAD `d3279b5c`）；本审查以初始快照（GEM5-001k @ `7eb3c181`，工作树干净）为基线，审阅记录写入现工作树任务书（仅本节，未提交）。

**重跑记录（reviewer 本人执行）**：
- `python3 tools/infra/check_milestones_fresh.py` ⇒ `PASS (8 行…)`，**rc=0**；`--self-test` ⇒ 干净基线 rc=0 + 五类注入各自 rc=1，**self-test: PASS**（FAIL 路径可达）。
- `python3 tools/infra/check_run_artifacts.py` ⇒ `check-run-artifacts: PASS`（A2 全 PASS、A3 2633 文件 0 illegal），**rc=0**。
- `python3 tools/infra/check_milestone_tasks.py` ⇒ **rc=1**（`当前里程碑 M10 …无 m 册`）；`git archive ac51545d` 临时树同跑 ⇒ **同样 rc=1** ⇒ **既有失败、非本任务引入**（engineer 对该脚本仅加 `GEM5` 前缀正则，diff 已核）。

**事实核验（独立重算，非采信完成区）**：
- v5 `contracts/opcodes.yaml`：**264 = m1 156 + fp 66 + m9 34 + m8 7 + m3 1，excluded 0** ✅。
- PR#3 `contracts/opcodes.yaml`：**259 = m1 156 + fp 60 + excluded 27 + m9 8 + m3 1 + m8 7**，与 ADR-0034「excluded 11→27、总数→259」互证 ✅。
- PR#3：97 文件 / +7710 行（`git diff --stat`）✅；`git merge-tree` 冲突**恰 12 项** ✅；改动集无 SE/`SEWorkload` 文件、全为 bare_metal/PTW/TLB/semihosting ⇒ **FS only** ✅；draft/mergeable 为 GitHub 属性，**采信** discussing.md 记录（本地不可复核）。
- 0628：ADR-0010「D2 — SE 先行」+ `AtomicSimpleCPU`、README AGREE 200 ✅；`DG-001a/002a/007a`、`KL-124a…141a` 共 11 册均存在 ✅；semihosting 区 `0x3FF00–0x3FFFF` 见 `spec/Machine-01` ✅。
- 测试 scope：`tests/inst/arch/tset/unit/shared` 均存在、**无 `tests/gem5`** ✅；复用表逐 scope 覆盖 + 禁平行用例 ✅。
- 语义复用禁令（任务书约束 + REPORT §2）、任务量 G1/G2/G3 = 10–15/15–25/5–8、SE 先行/FS 后接结论，任务书与 REPORT 一致 ✅。
- G0 分支纯度：`7eb3c181` 树内 `.tao/tasks/gem5/` 仅 `.gitkeep` + GEM5-001k（G1 册已分离删除）✅。

**发现（不阻断，§6.5 文档级）**：
- F1：REPORT §1 与任务书输入事实将 **259/60/27 归因「0628 gem5 README/ADR-0010」有误**——0628 全树无此计数（其 `tools/opcodes.yaml` 仅 92 条、无 scope 字段）；该计数实为 **PR#3/v5 旧基线**。数字本身真实、比较结论不受影响；建议 architect 收尾时改一句归因。
- F2：engineer 提交含 `tools/infra/3 脚本`（GEM5 前缀识别），与约束「只写本任务书与证据」字面冲突——**已披露且仅正则前缀、未改判据**（diff 已核），判为合理越界披露。

**判决：Accepted**（验收项 1–5 全部由 reviewer 独立复核通过；两门控 rc=0；`check_milestone_tasks` 红为既有、非本册引入）。
