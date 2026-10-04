# SPEC-085t: 文档分层改造 — 投影落位、cfx 约定与缺口登记（T2）

**模块**：spec
**项目里程碑**：M2
**依赖**：`SPEC-084t`（**硬依赖**：`Toolchain-01`/`Process-0x` 就位、`docs/spec/` 已删）；按用户裁定与 [T3 `INFRA-026t`] **串行**（T3 非本任务能力依赖，仅为避免并发改共享文件）。
**状态**：已验证

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

**测试结果**：全通过。针对性门控 5/5 `EXIT=0`（`check-asm-list` / `check-asm-prose` / `check-cfx-aliases` / `check-spec-drift` / `check-patch-tree`）；全量 `make check` **`EXIT=0`**（lit 25/25 + `repository checks: PASS`）。反例门控两组均能 **FAIL**（见验收 #8）。日志：`.work/log/spec/SPEC-085t-*.log`（含 `SPEC-085t-acceptance.log`、`SPEC-085t-make-check.log`、`SPEC-085t-baseline-*.log`）。

**修改文件**（9 个 + 本任务书）：
- **重命名**（`git mv`，`git status` 记为 `R`）：`docs/assembly-list.md` → `.tao/knowledge/contract-asm-list.md`
- `tools/llvm/gen_asm_list.py`（默认输出路径 + docstring 引用）
- `tools/infra/check_spec_drift.py`（`EXCLUDED_CONTRACTS` 新增 `contract-asm-list.md`；改 dict 以逐文件说明理由）
- `spec/Toolchain-01-汇编语言.md`（L5/L39 路径同步 + 新增 **§13 cfx 别名约定**）
- `spec/README.md`（投影表 DADAO-12/13/22/23/Toolchain-01 行定稿 + 登记缺口表 + Rationale 去 `Toolchain-02` 字面）
- `spec/Process-02-合约编写规范.md`（合约文件组织表 + 版本管理订正）
- `.tao/adr/adr-0017-cfx-assembly-aliases.md`（**仅追加** `## 修订` 指针）
- `docs/README.md`（`assembly-list.md` 行 → 新路径）
- `.tao/knowledge/MEMORY.md`（L16 路径指针）
- 本任务书（完成区/状态）

**验收结果**（真实输出）：

1. **搬迁就位**：`test -f .tao/knowledge/contract-asm-list.md && test ! -e docs/assembly-list.md` → `MOVE_OK`；`git status` → `R  docs/assembly-list.md -> .tao/knowledge/contract-asm-list.md`（重命名）。
2. **生成器一致**：`python3 tools/llvm/gen_asm_list.py` → `gen-asm-list: 227 entries -> /mnt/tao/DADAO-v5/.tao/knowledge/contract-asm-list.md`，`GEN_EXIT=0`；连续重跑 `diff`（重生成 vs 工作区）→ `DIFF_EXIT=0`（**逐字节一致**）。
   - **首次重生成相对 HEAD 有 2 行路径文本差异**（T1 改了生成器头但未重生成）：L5 `docs/spec/assembly-language.md`→`spec/Toolchain-01-汇编语言.md`、L9 同；`diff assembly-list.orig.md contract-asm-list.md` 仅此 2 行，已解释并采纳新内容。
3. **cfx 约定落位**：`grep -nE "cfx_<cfxname>|cfxHA|契约|别名" spec/Toolchain-01-汇编语言.md` → 命中（含 §13），`grep_rc=0`；`grep -n "Toolchain-02\|docs/spec" spec/Toolchain-01-汇编语言.md` → `forbidden_rc=1`（零命中）；§13 含指向 `.tao/knowledge/contract-cfx-aliases.md` 与 `ADR-0017` 的引用。
4. **缺口登记**：`grep -nE "contract-asm\.md|contract-sbi\.md|contract-exception\.md|contract-mmu\.md" spec/README.md spec/Process-02-合约编写规范.md` → **13 行**命中，逐项标注「缺口」。
5. **门控通过**：`check-asm-list`/`check-asm-prose`/`check-cfx-aliases`/`check-spec-drift`/`check-patch-tree` 各 `EXIT=0`；`python3 tools/spec/gen_cfx_aliases.py` `EXIT=0` 且 `git diff --quiet -- .tao/knowledge/contract-cfx-aliases.md` `rc=0`（幂等）。
6. **活引用零残留**（任务书 §6 显式活文件范围）：`grep -rn "docs/assembly-list\.md"` → `rc=1`（零命中）；`grep -rn "Toolchain-02"` → `rc=1`（零命中）。
7. **ADR 未改正文**：`git diff --stat -- .tao/adr/adr-0017-cfx-assembly-aliases.md` → `4 ++++`、`0 ----`（仅新增 `## 修订` 指针；D1–D10 逐行未动）。
8. **反例门控**（真实输出）：
   - 注入①：`sed` 改 `contract-asm-list.md` 计数 `227 条`→`228 条` → `python3 tools/llvm/gen_asm_list.py -o /tmp/opencode/SPEC-085t/regen_injected.md` 后 `diff regen_injected.md contract-asm-list.md` → `INJECTED_DIFF_RC=1`（**FAIL**）；还原后 `diff` → `0`。
     **说明**：`make check-asm-list` 校验的是 **spec 内嵌速查表 vs 生成器内存输出**，**不读** `contract-asm-list.md` ⇒ 该文件的漂移检测方式为「生成器 diff」。
   - 注入②（证明 `check-asm-list` 承重、可失败）：改 `spec/SimRISC-01-取数存数.md` 内嵌表 `### 取数存数（38 条）`→`（39 条）` → `make check-asm-list` **`EXIT=2`**，输出 `FAIL: 取数存数: content mismatch in SimRISC-01-取数存数.md` → `git checkout` 还原 → 门控回绿 `EXIT=0`。
   - 还原证据：`git status --untracked-files=all` 无 `spec/SimRISC-01` 改动、仓库无残留；`contract-asm-list.md` 与还原快照 `after-run1.md` 逐字节一致。
9. **自包含**：不依赖外部仓库。
10. **全量 `make check`**：`MAKE_CHECK_EXIT=0`（`Total Discovered Tests: 25 / Passed: 25 (100.00%)`；`check_issues: 63 open, 11 closed (0 blocking M1-gate: 0)`；`repository checks: PASS`）；`python3 -m compileall -q tools` `EXIT=0`。

**新发现/坑**：
- **`contract-asm-list.md` 无专门漂移门控**：`make check-asm-list`（`check_asm_list_consistency.py`）比对的是 `spec/SimRISC-*` 内嵌表与生成器内存输出，**不读**该生成物；漂移只能靠「重跑生成器 + `diff`」人工核验。与 `contract-cfx-aliases.md`（有 `check-cfx-aliases` 门控）不对称。→ 建议登记 `deferred.md` 或后续任务。
- **T1 遗留陈旧计数**：`spec/Toolchain-01` §11「9 个 M1 格式类与 **177 条** M1 指令」（现算 M1=152），L3 状态行等仍陈旧；本次仅订正头部依赖行（251→227），其余**超本任务范围**未动。→ 建议后续订正任务。
- **`docs/README.md` 的 Toolchain-01 行**仍写「单位后缀 `i`」（`SPEC-082t` 已取消 `i`），属 T1 未同步的陈旧描述，非本任务范围。
- `check_spec_drift.py` 的排除名单由 `frozenset` 改为 `dict`（逐文件理由），`name in` / `len()` / `.items()` 三处用法均已同步。
- **越界披露**：(i) 为满足验收 #6「活文件范围 `Toolchain-02` 零命中」，改写 `spec/README.md` Rationale 两处 `Toolchain-02` 字面为等价描述（语义/决策不变）；(ii) 将 Toolchain-01 依赖行陈旧计数「251 条」订正为实际「227 条」，使路径引用自洽。其余改动均在任务书列明范围内。

**遗留问题**：
- （登记建议，非阻断）`contract-asm-list.md` 缺专门漂移门控 → 建议登记 `deferred.md` 或后续任务。
- （登记建议，非阻断）`spec/Toolchain-01` §11 等处陈旧计数（177/251 等）→ 建议后续订正任务。
- 无未完成项。

---

### 完成区补记（交叉复核修复轮，2026-10-03）

> 交叉复核发现 T2 **在范围内的遗漏**：搬迁 `contract-asm-list.md` 后仅给 `check_spec_drift.py` 加了排除，**漏给 `tools/infra/check_spec_refs.py`**（其按 `contract-*.md` 审计集收录生成物）⇒ Check2 由 T1 基线 `76(18+58)` 变为 `78(18+60)`，违反 `deferred.md` 已确立约定「新增任何生成投影务必同步**两处**排除名单」。**本轮当场修复，不留遗留**（除专门漂移门控一项仍建议后续任务）。

**本轮修改文件**：`tools/infra/check_spec_refs.py`（**唯一**代码改动，最小改动：仅在 `_EXCLUDED_CONTRACTS` 加入 `contract-asm-list.md` 并同步理由注释；不改其它逻辑）+ 本任务书。

**本轮真实输出**：
1. **修复前**（`python3 tools/infra/check_spec_refs.py`）：`PRE_FIX_EXIT=1`，`结果: FAIL (78 violations: 18 Check1 + 60 Check2)`（`Check 2 命中数: 60`）。
2. **修复后**：`python3 tools/infra/check_spec_refs.py` → `POST_FIX_EXIT=1`，`结果: FAIL (76 violations: 18 Check1 + 58 Check2)`（`Check 2 命中数: 58`）——**恢复 T1 基线 76(18+58)**。
   - 独立佐证（证明 76 为 T1 基线而非本修复凑数）：临时目录仅含 T2 前合约（去掉 `contract-asm-list.md`）→ `--contract-dir /tmp/opencode/SPEC-085t/baseline-contracts` → `结果: FAIL (76 violations: 18 Check1 + 58 Check2)`（与 T1 基线一致）。
   - 注：该脚本为 **standalone 门控（不在 `make check` 内）**，基线即含 18 Check1 + 58 Check2 已知项 ⇒ `EXIT=1` 为 T1 既有状态，非本任务引入；本修复只保证**审计集与 T1 一致**。
3. **针对性门控抽跑**：`make check-asm-list` `EXIT=0`、`make check-spec-drift` `EXIT=0`、`make check-asm-prose` `EXIT=0`。
4. **反例门控（脚本非空转）**：临时向活合约 `.tao/knowledge/contract-elf.md` 追加一行 `TEST-INJECTION 必须 保留 reserved 无引用断言`（命中 Check2 且无 spec 引用）→ `python3 tools/infra/check_spec_refs.py`：`Check 2 命中数: 59`、`结果: FAIL (77 violations: 18 Check1 + 59 Check2)`，且报告中逐行打印该注入行（`CHECK2 命中明细` 第 72 行）；`git checkout -- .tao/knowledge/contract-elf.md` 还原后复跑 → `Check 2 命中数: 58`、`结果: FAIL (76 ...)`，报告内 `TEST-INJECTION` 出现 **0** 次（还原干净）。
5. **全量**：`make check` → `MAKE_CHECK_EXIT=0`（`Passed: 25 (100.00%)`、`repository checks: PASS`）；`python3 -m compileall -q tools` → `COMPILEALL_EXIT=0`。
6. 日志：`.work/log/spec/SPEC-085t-check-spec-refs-postfix.log`、`/tmp/opencode/SPEC-085t/check_spec_refs.{prefix,t1baseline,injected,restored}.log`、`.work/log/spec/SPEC-085t-make-check-round2.log`。

**本轮遗留（仅 1 项，非阻断）**：`contract-asm-list.md` 仍缺**专门漂移门控**（现有 `make check-asm-list` 不读该生成物；漂移仅「重跑生成器 + diff」人工核验）。**排除名单同步项已消解**。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**（自主逐行）：`tools/llvm/gen_asm_list.py`、`tools/infra/check_spec_drift.py`、`spec/Toolchain-01-汇编语言.md`、`spec/README.md`、`spec/Process-02-合约编写规范.md`、`.tao/adr/adr-0017-cfx-assembly-aliases.md`、`docs/README.md`、`.tao/knowledge/MEMORY.md`、`.tao/knowledge/contract-asm-list.md`（重命名）。

**逐行审查意见**：
- `gen_asm_list.py`：默认输出（`ROOT / ".tao/knowledge/contract-asm-list.md"`）与 docstring（`.tao/knowledge/contract-asm-list.md`）均为新路径；全文件已无 `docs/assembly-list.md`/`docs/spec` 残留（grep 复核，rc=1）。✓
- `check_spec_drift.py`：改 dict 后 `name in EXCLUDED_CONTRACTS`（L291）、`len(...)`（L309）、`sorted(...items())`（L277）三处用法一致；排除 2 个、检查 3 个、错误 0。✓
- `Toolchain-01 §13`：正文取自 ADR-0017 **D1–D7、D10**；**未**搬运 D8/D9（生成/落点属决策层，改以指针指向 `ADR-0017` 与投影 `contract-cfx-aliases.md`）；未引用 `Toolchain-02`、未引用 `docs/spec`；示例代码块经 `check-asm-prose --strict` `EXIT=0`（别名形/长形/单下标/escape 均解析通过）。✓
- `spec/README.md`：投影表五处按任务 §3 映射据实落位（`DADAO-12` 同时含 `contract-sbi.md` 与 `contract-mmu.md`；`DADAO-13/23`→`contract-exception.md`）；「登记缺口」表补来源册/类型；Rationale 去字面 `Toolchain-02`（语义不变）。✓
- `Process-02`：合约清单反映实际集合（含 `contract-asm-list.md`/`contract-cfx-aliases.md` 两个生成投影 + 四个缺口）；版本管理订正消除与决策 7 的冲突（ADR 强制→轻量修订）。✓
- `adr-0017`：仅追加 `## 修订`（+4 行，0 删除），D1–D10 正文零改动（`git diff` 逐行可见）。✓
- 搬迁：`git mv` 保留历史；重生成仅 L5/L9 两行路径变化；二次重生成逐字节一致（`DIFF_EXIT=0`）。✓
- 防造假：所有结论均由本会话真实命令产生，日志留 `.work/log/spec/`；两组反例注入均以真实 FAIL 输出与还原证据佐证。✓

**判决**：无未修 finding（F1–F3 已修，F4 为范围外建议延后）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 验收 #6「活文件范围 `Toolchain-02` 零命中」与 T1 遗留的 `spec/README.md` Rationale 字面冲突 | ✅已修 | Rationale 两处改为「取消拆分独立的 cfx 规范分册」「把 cfx 拆为独立规范分册」（语义/决策不变） | `grep -rn "Toolchain-02" <活文件范围>` → `rc=1`（零命中） |
| F2 `contract-asm-list.md` 首次重生成相对 HEAD 有 2 行 diff（T1 改生成器未重生成） | ✅已修（采纳新内容） | 采用重生成结果（L5/L9 路径文本）；二次重生成逐字节一致 | `diff` 重生成 vs 工作区 → `0`；快照 `diff` 仅 L5/L9 |
| F3 头部依赖行陈旧计数「251 条」与生成物现算 227 矛盾 | ✅已修 | `spec/Toolchain-01` 依赖行 251→227 | 生成器输出「227 entries」；`grep -n "251" spec/Toolchain-01` 零命中 |
| F4 `contract-asm-list.md` 无专门漂移门控 | ⏸延后（超本任务范围） | — | 记入「新发现/遗留」，建议登记 `deferred.md` |

**交叉复核修复轮（2026-10-03，追加）**：

**审查范围**：`tools/infra/check_spec_refs.py`（本轮唯一代码改动）。

**逐行审查意见**：
- 排除集 `_EXCLUDED_CONTRACTS` 为 `frozenset`，加入 `"contract-asm-list.md"` 后 `p.name not in _EXCLUDED_CONTRACTS`（L286）用法不变；排除后审计集 = `contract-{isa,abi,elf}.md`，与 `check_spec_drift.py` 对同一生成物的处置**一致**（注释同步「务必同步两处排除名单」）。✓
- 未改 `--contract-dir`/`--spec-dir` 默认值与任何检查逻辑（`git diff` 仅 +3/−0）。✓
- 反例证明脚本**非空转**：注入活合约 → 命中并打印；还原 → 命中数回退、注入行 0 次。✓
- 防造假：全部输出真实，日志留 `.work/log/spec/` 与 `/tmp/opencode/SPEC-085t/`。✓

**判决**：F5 已修，无未修 finding。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F5 漏给 `tools/infra/check_spec_refs.py` 加生成投影排除，Check2 `58→60`（总 `76→78`） | ✅已修 | `_EXCLUDED_CONTRACTS` 加入 `contract-asm-list.md` + 同步理由注释 | 修复前 `78(18+60)` → 修复后 `76(18+58)`；独立基线（去该文件）`76(18+58)`；反例注入 `59` 并报出、还原 `58` |

#### 第 1 轮 reviewer 验收

**审查范围**：独立重跑全部验收命令，逐项核对完成区声明。

**重跑记录**（真实输出）：

| 验收项 | 命令 | 真实输出 | EXIT |
|--------|------|---------|------|
| 搬迁就位 | `test -f .tao/knowledge/contract-asm-list.md && test ! -e docs/assembly-list.md` | `MOVE_OK` | 0 |
| git 重命名 | `git status --porcelain -M` | `RM docs/assembly-list.md -> .tao/knowledge/contract-asm-list.md` | — |
| 生成器一致 | `python3 tools/llvm/gen_asm_list.py` | `gen-asm-list: 227 entries -> ...contract-asm-list.md` | 0 |
| 连续重生成 diff | `diff contract-asm-list.md regen.md` | 无输出（逐字节一致） | 0 |
| HEAD 对比 | `diff HEAD:docs/assembly-list.md contract-asm-list.md` | 仅 L5/L9 两行路径文本变更 | 1 |
| 活引用零残留 | `grep -rn "docs/assembly-list\.md" <活文件范围>` | 零命中 | 1 |
| check-asm-list | `make check-asm-list` | `12 spec files OK` | 0 |
| check-asm-prose | `make check-asm-prose` | `PASS (0 violations)` | 0 |
| check-cfx-aliases | `make check-cfx-aliases` | `PASS (byte-identical)` | 0 |
| check-spec-drift | `make check-spec-drift` | `检查 3 个，排除 2 个，错误 0 个` | 0 |
| check-patch-tree | `make check-patch-tree` | `2 component(s), 67 patches OK` | 0 |
| **make check 全量** | `make check` | 25/25 lit + 149/149 sem + 80/80 交叉 + repository checks: PASS | **0** |
| Toolchain-02 零残留 | `grep -rn "Toolchain-02" <活文件范围>` | 零命中 | 1 |
| ADR-0017 diff | `git diff -- .tao/adr/adr-0017-cfx-assembly-aliases.md` | +4 行（`## 修订`），0 删除 | — |

**反例门控**：

| 注入 | 操作 | 结果 | 还原 |
|------|------|------|------|
| ① `contract-asm-list.md` 改 `227 条`→`228 条` | 生成器 diff vs 注入文件 | `INJECTED_DIFF_RC=1`（FAIL）✅ | 还原后 `RESTORED_DIFF_RC=0` ✅ |
| ② `SimRISC-01` 改 `（38 条）`→`（39 条）` | `make check-asm-list` | `EXIT=2`，`FAIL: 取数存数: content mismatch` ✅ | 还原后 `RESTORED_EXIT=0` ✅ |

**约束核验**：

| 约束 | 结果 |
|------|------|
| `git status` 记为 `R` | ✅ `RM docs/assembly-list.md -> .tao/knowledge/contract-asm-list.md` |
| 重生成逐字节一致 | ✅ 连续重生成 `DIFF_RC=0`；首次 vs HEAD 仅 L5/L9 路径文本差异（合理） |
| cfx §13 覆盖 D1–D7/D10 | ✅ 逐条对照均语义一致，无缺项/改义 |
| adr-0017 仅追加指针 | ✅ +4 行 0 删除，D1–D10 未动 |
| 四处缺口登记 | ✅ `spec/README.md` + `spec/Process-02` 均登记，口径一致 |
| 活引用零残留 | ✅ `docs/assembly-list.md` + `Toolchain-02` 均零命中 |
| 门控全绿 | ✅ 5/5 针对性 + `make check` 全量 EXIT=0 |
| 反例可失败 | ✅ 两组注入均 FAIL，还原后回绿 |
| 越界披露 | ✅ 两处（Rationale 字面改写、依赖行 251→227）合理且最小，无未披露越界 |
| 完成区一致性 | ✅ 逐条核对，完成区声明与真实输出一致，无夸大 |

**判决**：**Accepted** —— 全部验收命令在独立重跑下通过，约束无违反，反例门控两组均可 FAIL 且还原回绿。

## 收尾与提交（用户裁定，2026-10-03）
- **执行期不提交**：engineer/reviewer 子代理**不得** `git commit`/`git add`。
- **收尾后各提交一次**：本任务经 `/complete`（reviewer 验收 + 架构师交叉复核 + 知识沉淀）通过、`**状态**` 置为 `已验证` 后，**主会话**为该任务做**一次独立提交**；**每任务完成、验收通过后各做一次提交**，不积压、不批量；**未收尾不得提交**。
- 提交前满足项目 `AGENTS.md`「任务收尾」的收尾检查。

## 决策裁定记录（用户 2026-10-03 裁定，已并入本任务书）
- **原开放问题 #6（cfx 章节编号）**：裁定 **执行时按 `Toolchain-01` 实际结构定**（本任务书已改，注明「建议独立成章」）。
- **原开放问题 #2（ADR 去留）**：由**新决策**覆盖——ADR 归 `.tao/adr/`（T1 完成），本任务 `adr-0017` 的**新路径**为 `.tao/adr/adr-0017-cfx-assembly-aliases.md`。
- 本任务**无待确认事项**。
