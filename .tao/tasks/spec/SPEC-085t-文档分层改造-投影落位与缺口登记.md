# SPEC-085t: 文档分层改造 — 投影落位、cfx 约定与缺口登记（T2）

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`SPEC-084t`（**硬依赖**：`Toolchain-01`/`Process-0x` 就位、`docs/spec/` 已删）；按用户裁定与 [T3 `INFRA-026t`] **串行**（T3 非本任务能力依赖，仅为避免并发改共享文件）。
**状态**：待开始

> 本任务是「文档分层改造」的 **T2**。T1 = `SPEC-084t`（已完成），T3 = `INFRA-026t`。
> **本任务书为 T1 完成前的完整草案**；T1 落盘后须**复核以下路径与文件是否存在**，若 T1 实际产出与草案不符（如路径/编号变化）**先报告再调整**，不得自行改契约。

## 执行环境
**执行环境**：本地

## 一、已定决策（真源，逐条已经用户确认；不得增删、不得重新决策）

- **决策 3（本任务主责）**：cfx 别名——**约定正文并入 `spec/Toolchain-01-汇编语言.md`**（原在 `ADR-0017`，**取消** Toolchain-02）；**别名表**归**投影层**，不进 `spec/`。
- **决策 5（本任务承担 assembly-list 部分）**：`docs/assembly-list.md`（生成表）→ **`.tao/knowledge/contract-asm-list.md`**。
  （`docs/spec/cfx-aliases.md` → `.tao/knowledge/contract-cfx-aliases.md` 已由 T1 完成。）
- **决策 8**：**每册规范都必须有投影**；投影类型 ∈ ①叙述合约 `contract-*.md` ②机器数据 `contracts/*` ③机械门控 ④可执行 lit/oracle/向量；**缺失登记为缺口**。本任务把**缺口登记**定稿：`contract-asm.md`、`contract-sbi.md`、`contract-exception.md`、`contract-mmu.md`。
- **决策 2（末条）**：`.tao/knowledge/` 今后只放 **合约（投影）+ 台账**（MEMORY/changelog/deferred/milestones）；**ADR 归决策层、在独立目录 `.tao/adr/`**（由 T1 完成搬迁）——本任务据此更新 `Process-02` 的合约清单，并注意 `adr-0017` 的**新路径**为 `.tao/adr/adr-0017-cfx-assembly-aliases.md`。
- **决策 6/9 不在本任务**：`Process-03` 判据修订归 T3；本改造不立 ADR，理由在 `spec/README.md` 的 Rationale（T1 已建）。

## 二、接口规范

### 输入
- `spec/Toolchain-01-汇编语言.md`（T1 产出）、`spec/Process-02-合约编写规范.md`（T1 产出）、`spec/README.md`（T1 产出）
- `docs/assembly-list.md`（待搬迁）、`tools/llvm/gen_asm_list.py`
- `.tao/adr/adr-0017-cfx-assembly-aliases.md`（**T1 已迁至 `.tao/adr/`；只读，仅可追加指针，不得改正文**）
- `.tao/knowledge/contract-cfx-aliases.md`（T1 产出）
- `.tao/knowledge/{contract-isa.md,contract-abi.md,contract-elf.md}`（现行合约清单来源）
- `contracts/{opcodes.yaml,abi.yaml,legality_rules.yaml}`、`tools/spec/{check_asm_list_consistency.py,check_cfx_aliases.py,check_asm_prose.py}`、`tools/infra/check_spec_drift.py`
- `Makefile`、`docs/README.md`

### 输出
1. `docs/assembly-list.md` → **`.tao/knowledge/contract-asm-list.md`**（`git mv`），并同步生成器输出路径与各处引用。
2. `spec/Toolchain-01-汇编语言.md`：新增 **cfx 别名约定正文**一节（源自 `ADR-0017` 的**汇编书写约定**部分：D1 归属、D2 形态、D3 标量别名、D4 寄存器别名、D5 两种拼写、D6 往返、D7 文档示例、D10 数组单下标；**引用**别名表投影与 ADR）。
3. `spec/README.md` 投影表：**定稿**各册四类型落点 + **缺口登记**（`contract-asm.md`、`contract-sbi.md`、`contract-exception.md`、`contract-mmu.md`）。
4. `spec/Process-02-合约编写规范.md`：更新「合约文件组织」表 → 反映当前 `contract-*.md` 清单（含 `contract-asm-list.md`、`contract-cfx-aliases.md`；标注缺口）。
5. `.tao/adr/adr-0017-cfx-assembly-aliases.md`（**T1 已迁至此路径**）：**仅追加**一条指针（说明 D9 落点已迁至 `.tao/knowledge/contract-cfx-aliases.md`、约定正文已入 `spec/Toolchain-01`），**正文与 decision 不改**。

### 约束
- 全程中文；**不提交 git**；只动任务书范围，越界须披露。
- **不得改 `adr-*` 决策正文**（仅按输出 5 对 `.tao/adr/adr-0017-*.md` 追加指针）；**不得改已验收历史任务书**；**不得改 `spec/SimRISC-0.5.3/`**；`spec/SimRISC-*`/`spec/DADAO-*` 正文不动（cfx 约定只入 `Toolchain-01`）。
- 临时产物 `/tmp/opencode/SPEC-085t/`；日志留 `.work/log/spec/`。
- 遵循 `AGENTS.md`「子代理硬约束」。

## 三、实施步骤

### 0. 预检与复核
- `git status --porcelain` 干净。
- 复核 T1 产出：`test -f spec/Toolchain-01-汇编语言.md && test -f spec/Process-02-合约编写规范.md && test -f spec/README.md && test -f .tao/knowledge/contract-cfx-aliases.md && test ! -e docs/spec && test -d .tao/adr && test -f .tao/adr/adr-0017-cfx-assembly-aliases.md`。
- 记录基线门控：`make check-asm-list`、`make check-cfx-aliases`、`make check-spec-drift`、`make check-asm-prose`（各 `rc` 单独捕获）。

### 1. 搬迁 `docs/assembly-list.md` → `.tao/knowledge/contract-asm-list.md`
- `git mv docs/assembly-list.md .tao/knowledge/contract-asm-list.md`。
- `tools/llvm/gen_asm_list.py`：
  - 默认输出（L683）→ `ROOT / ".tao/knowledge/contract-asm-list.md"`；
  - docstring/生成头中 `docs/assembly-list.md`（L4）与 `docs/spec/assembly-language.md`→`spec/Toolchain-01-汇编语言.md`（T1 已改则核对；L658/662 的生成文本引用同步）。
- **重生成并核对幂等**：`python3 tools/llvm/gen_asm_list.py`（默认写新路径）→ `git diff -- .tao/knowledge/contract-asm-list.md` 为空；若因路径文本变化而有 diff，须解释并确认仅路径相关。
- 同步活引用：`Makefile`、`docs/README.md`（`assembly-list.md` 行）、`README.md`（若命中）、`.tao/README.md`、**`spec/Toolchain-01-汇编语言.md`（其头部依赖与 §2.4/§12 的 `docs/assembly-list.md` 引用）**、`.tao/knowledge/{MEMORY.md,contract-*.md}`（**只改路径指针；`changelog.md`/`deferred.md` 等历史台账不改**）、`tools/**`、`tests/**`（若命中）。执行时全仓 `grep -rn "docs/assembly-list\.md"` 穷尽核对。
- `tools/infra/check_spec_drift.py` 的 `EXCLUDED_CONTRACTS` **新增** `contract-asm-list.md`（机械生成投影、无来源头）。
- `tools/spec/check_asm_list_consistency.py` 复用 `gen_asm_list` 的内存输出（不读该文件路径），确认**无需改**；若改则披露。

### 2. cfx 约定正文并入 `spec/Toolchain-01-汇编语言.md`
- 在 `Toolchain-01` 增加一节：**建议独立成章**（如「**§13 cfx 别名约定**」）；**具体编号与层级由 engineer 据 T1 落盘后的文件实际章节结构定**，须与既有 § 编号不冲突、与「与上游关系」附录区分；执行时若文件结构已变，按实际结构落位并在完成区说明。
  - 归属与形态（D1/D2）：cfx 别名属汇编规范、由汇编器内置符号表解析、不引入 cpp、不加花括号；
  - 标量别名（D3）：`cfx_<cfxname>` ⇔ `cfxHA`；
  - 寄存器别名（D4）：`cfx_<cfxname>_<regname>` ⇔ `(cfxha, cg, rc)`，查 spec 寄存器表 `cg`/`rc` 列；
  - 两种拼写（D5）：规范长形 vs 别名形，解析到同一操作元组；
  - 往返（D6）：反汇编输出规范长形；
  - 文档示例（D7）：示例优先别名形；
  - 数组单下标（D10）：`cfx_<cfxname>_<regname>[N]`，`N ∈ [lo..hi]`，`rc = rc_base + N`。
  - **指向投影**：写明「别名表为机械生成的投影 → `.tao/knowledge/contract-cfx-aliases.md`（生成器 `tools/spec/gen_cfx_aliases.py`；门控 `tools/spec/check_cfx_aliases.py`）」，并指向 `ADR-0017` 作为决策记录。
- 与 `ADR-0017` 的分工：`Toolchain-01` 承载**规范正文（怎么写）**；`ADR-0017` 承载**决策与理由**（保留原状 + 追加指针）。**不得**在 `Toolchain-01` 引用不存在的 Toolchain-02。
- 门控复核：`make check-asm-prose`（新增正文含示例代码块，须为**新汇编格式**）exit 0。

### 3. 缺口登记与投影表定稿
- 在 `spec/README.md` 投影表中把下列四项登记为 **`缺口`**（①叙述合约列）：`contract-asm.md`、`contract-sbi.md`、`contract-exception.md`、`contract-mmu.md`。
  - 逐项标注**来源册**与**缺口类型**（如 `Toolchain-01`→`contract-asm.md`；`DADAO-12/22`→`contract-sbi.md`；`DADAO-13/23`→`contract-exception.md`；地址转换（`DADAO-12`）→`contract-mmu.md`）。映射**须据实核对 § 引用**，允许修正。
- 确保四类型列无空（缺失一律写「缺口」或「不适用」）。

### 4. 更新 `spec/Process-02-合约编写规范.md` 的合约清单
- 「合约文件组织」表更新为当前实际集合：
  - 现行：`contract-isa.md`、`contract-abi.md`、`contract-elf.md`、`contract-asm-list.md`（生成）、`contract-cfx-aliases.md`（生成）；
  - **缺口**：`contract-asm.md`、`contract-sbi.md`、`contract-exception.md`、`contract-mmu.md`（标注「缺口」）。
- 若文件内还有「合约版本号与 spec/ 一致、spec/ 更新走 ADR 变更流程」等**与决策 7（轻量修订流程：不强制记 ADR）冲突**的旧表述，**只做与本改造直接相关的订正**（保持一致），其余不动；订正处逐条在完成区列出。

### 5. `adr-0017` 仅追加指针
- 在 `.tao/adr/adr-0017-cfx-assembly-aliases.md`（T1 迁移后的新路径）的**末尾**（`## 状态说明` 之内或其后追加 `## 修订`）加一条：`2026-10-03 文档分层改造：D9 落点迁至 .tao/knowledge/contract-cfx-aliases.md；汇编书写约定正文并入 spec/Toolchain-01-汇编语言.md。决策不变，正文不改（依 adr-authoring 规则）。`
- **不得**改动 D1–D10 正文。

## 四、验收标准

1. **搬迁就位**：`test -f .tao/knowledge/contract-asm-list.md && test ! -e docs/assembly-list.md`；`git status`/`git diff --stat -M` 显示重命名。
2. **生成器一致**：`python3 tools/llvm/gen_asm_list.py` exit 0，且重跑后 `git diff -- .tao/knowledge/contract-asm-list.md` 为空（或仅路径文本差异，已解释）。
3. **cfx 约定落位**：`grep -nE "cfx_<cfxname>|cfxHA|契约|别名" spec/Toolchain-01-汇编语言.md` 命中约定正文；文中**无** `Toolchain-02`、无 `docs/spec/`；含指向 `contract-cfx-aliases.md` 与 `ADR-0017` 的引用。
4. **缺口登记**：`grep -nE "contract-asm\.md|contract-sbi\.md|contract-exception\.md|contract-mmu\.md" spec/README.md spec/Process-02-合约编写规范.md` 各命中且标注「缺口」。
5. **门控通过**（各贴 `rc`）：`make check-asm-list`、`make check-asm-prose`、`make check-cfx-aliases`、`make check-spec-drift`、`make check-patch-tree` 均 exit 0；`python3 tools/spec/gen_cfx_aliases.py` 后 `git diff -- .tao/knowledge/contract-cfx-aliases.md` 为空。
6. **活引用零残留**：在**活文件范围**内 `grep -rn "docs/assembly-list\.md"` 零命中；`grep -rn "Toolchain-02"`（活文件范围，除历史）零命中。
   活文件范围（显式列举）：`AGENTS.md Makefile README.md .tao/README.md docs/README.md tools tests spec/Toolchain-01-汇编语言.md spec/README.md .tao/knowledge/contract-*.md .tao/knowledge/MEMORY.md .tao/tasks/spec/SPEC-083t-*.md .tao/tasks/llvm/LLVM-027t-*.md .tao/tasks/qemu/QEMU-032t-*.md .tao/tasks/testcases/TESTCASES-022t-*.md`。
   **明确排除**历史：`.tao/knowledge/{changelog.md,deferred.md}`、`docs/{m1-retrospective.md,m2-spec-planning.md,...}`、`components/*/changelog.md`、全部已验收任务书。贴真实输出与 `EXIT`。
7. **ADR 未改正文**：`git diff -- .tao/adr/adr-0017-cfx-assembly-aliases.md` 仅新增指针行（`git diff` 逐行可见，无删除/改写 D1–D10）。
8. **反例门控**：临时改错 `contract-asm-list.md`（如改 1 个计数/1 行）→ `make check-asm-list`（或生成器 diff）**FAIL** → 还原 → PASS；给出注入前后真实输出与还原证据（`git diff --name-only` 先非空后仅本任务应有改动）。
9. **自包含**：不依赖外部仓库。

## 五、下发前四项预检（主会话下发时须逐条给结论；T1 完成后复核）

1. **任务书内部一致性**：✅ 目标（assembly-list 搬迁 + cfx 约定 + 缺口 + 合约清单 + ADR 指针）与验收 1–9 一致；明确「ADR 只追加指针」与约束一致。
2. **依赖链实际可用性**：依赖 `SPEC-084t`。**T1 完成后**须核实：`spec/Toolchain-01`、`spec/Process-02`、`spec/README.md`、`.tao/knowledge/contract-cfx-aliases.md` 存在且 `docs/spec/` 已删。**当前（T1 前）为 BLOCKED**。
3. **验收可执行性**：
   - 「现在可跑」（T1 后）：`make check-asm-list`、`make check-asm-prose`、`make check-cfx-aliases`、`make check-spec-drift`、`make check-patch-tree`、生成器重跑、grep 门控、反例门控。
   - **BLOCKED 项**：`make check` 全量（含 `check-lit`/`check-qemu-semantics`，需构建产物）。**替代证据**：上述针对性门控 + `python3 -m compileall -q tools`。
4. **与 spec/vectors 一致**：本任务**不改编码/期望值**；`contract-asm-list.md` 为生成的指令表投影，须与 `contracts/opcodes.yaml` 由同一生成器产出（重跑一致即证）。`tests/vectors/` 不动。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）

## 收尾与提交（用户裁定，2026-10-03）
- **执行期不提交**：engineer/reviewer 子代理**不得** `git commit`/`git add`。
- **收尾后各提交一次**：本任务经 `/complete`（reviewer 验收 + 架构师交叉复核 + 知识沉淀）通过、`**状态**` 置为 `已验证` 后，**主会话**为该任务做**一次独立提交**；**每任务完成、验收通过后各做一次提交**，不积压、不批量；**未收尾不得提交**。
- 提交前满足项目 `AGENTS.md`「任务收尾」的收尾检查。

## 决策裁定记录（用户 2026-10-03 裁定，已并入本任务书）
- **原开放问题 #6（cfx 章节编号）**：裁定 **执行时按 `Toolchain-01` 实际结构定**（本任务书已改，注明「建议独立成章」）。
- **原开放问题 #2（ADR 去留）**：由**新决策**覆盖——ADR 归 `.tao/adr/`（T1 完成），本任务 `adr-0017` 的**新路径**为 `.tao/adr/adr-0017-cfx-assembly-aliases.md`。
- 本任务**无待确认事项**。
