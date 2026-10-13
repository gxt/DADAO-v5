# SPEC-112t: 去 `FILEHDR PHDRS` 与 64 KiB 页大小决策落地（`ADR-0003 §D5` 修订）

**模块**：spec
**项目里程碑**：M4
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（v5 自身知识，**执行依赖**）：
  - `.tao/adr/adr-0003-object-abi.md`（当前 `Accepted`，§D5 + `## 修订`；**就地修订体例参照** `.tao/adr/adr-0004-test-machine.md` 的 `rev. 2026-10-06` 条目与 §D2.2/§D2.3 行内注记写法）。
  - `.tao/knowledge/contract-elf.md` §5（段对齐/VA=PA）、§6.1.2（M4 ELF 路径）、§6.3、附录 A（均为 `SPEC-107t` 后版本）。
  - `.tao/knowledge/milestones.md:78`（M4 范围段，含「`FILEHDR PHDRS` 使 `.text` 落在 file offset 0」措辞）。
  - `.tao/knowledge/issues.yaml` 的 `ISS-155`（`scope: [qemu, integ]`）。
  - `spec/DADAO-12-SEE-主管系统运行环境.md §2.2.1`（普通页 `64 KiB`：`VA[15:00]` 页内偏移、普通页 64 KiB 对齐）。
  - `spec/DADAO-22-SBI-主管系统二进制接口.md §4`（地址转换 `cfx_ptw`；`SBI_PTW_HANDLE_FAULT` 返回 `page_mask` 例 `0xFFFFFFFFFFFF0000` = 64 KiB）。
  - `spec/Process-03-ADR编写规范.md`（ADR 修订流程：就地修订须用户逐条确认 + `## 修订` 记录）。
  - `.tao/tasks/llvm/LLVM-056t-DADAO-LLD-target与链接脚本.md`（**内容溯源，非执行必需**：`FILEHDR PHDRS` 副作用实测——首个 `PT_LOAD` 落 `0xFFFEFFFFF000`、`.text` `sh_offset=0x1000`；`FILEHDR` 用户裁定 F6/F7）。
  - `.tao/tasks/llvm/LLVM-058t-*.md`（下游实现任务；本任务为其 spec-first 前置）。
- **输出**（**只做决策/正文文本，不实现、不改组件源码**）：
  1. `.tao/adr/adr-0003-object-abi.md`：`**状态**` 行加 `rev. 2026-10-06`；§D5 加就地修订注 + 新增「M4 ELF 路径补充」小节；`## 修订` 加 `rev. 2026-10-06` 条目（三条 decision + 被否方案 + scope 限定 + 不变项）。三条 decision 内容见下「用户裁定 / 决策正文」。
  2. `.tao/knowledge/contract-elf.md §6.1.2`：删除「**文件偏移**：链接脚本 `FILEHDR PHDRS` 使 `.text` file-offset 0（`SPEC-104k`/`LLVM-056t`）。[ADR-0004 §修订 rev. 2026-10-06]」这一 bullet，改为「**首段与文件偏移**：M4 裸机路径 `dadao.lds` **不使用 `FILEHDR PHDRS`**——ELF 头/程序头表**只存在于文件中、不进入 guest 内存**（加载器从**文件**解析 `Ehdr`/`Phdr`）；首个 `PT_LOAD` 从 `.text` 起（VA=PA），其 `p_offset` **不做要求**（**不要求为 0、也不禁止为 0**）。[ADR-0003 §修订 rev. 2026-10-06]」。
  3. `.tao/knowledge/contract-elf.md §5`：补一条 **`PT_LOAD` 的 `p_align` 口径**——**目标默认 = 64 KiB**（`defaultMaxPageSize = 0x10000`），**可被 `-z max-page-size` 覆写**（**目标默认、非硬编码不变式**）。带**可机械解析**的 spec 引用（见「约束 · 引用可解析」）。同步「附录 A：来源对照」中 §5/§6 行，补 `ADR-0003 §修订 rev. 2026-10-06`（保持来源对照与正文一致）。
  4. `.tao/knowledge/milestones.md:78`：删除「`FILEHDR PHDRS` 使 `.text` 落在 file offset 0」，改为「M4 路径 `dadao.lds` **不使用 `FILEHDR PHDRS`**（头/程序头表只在文件中，不进 guest 内存）；`p_align` **目标默认 64 KiB（可被 `-z max-page-size` 覆写）**」。
  5. `.tao/knowledge/issues.yaml` `ISS-155`：改写为**结案**——`status: open` → **`status: closed`**（该文件字段约束为 `open | closed`，**无** `resolved` 取值），`resolved_by: null` → **`resolved_by: SPEC-112t`**，`notes` **追加**（不改写原有内容）处置记录（含日期与理由）。
- **约束**：
  - **不实现、不改组件源码**（不改 `DADAO.cpp`、不改 `tests/scripts/dadao.lds`）；`tests/scripts/dadao.lds` 的实改与重建归 `LLVM-058t`。
  - **不新增/不修改任何未经用户逐条确认的 decision**。本任务落地的三条 decision 已由用户确认（原话见「用户裁定」）；若发现需额外 decision 才能自洽，**停下报告**，不得自行定稿（`AGENTS.md`「ADR decision 逐条确认」）。
  - **`ADR-0004` 全部 decision 不变**；`ADR-0019` 的「本期禁用 relaxation / 4 类 reloc」保持原样。
  - **硬约束——中性/不约束完整 linker**（用户本轮原话，务必逐条贯彻，详见 §硬约束清单）：
    - 表述必须是「**M4 裸机路径的 `tests/scripts/dadao.lds` 不使用 `FILEHDR PHDRS`**」；**LLD 的 `FILEHDR PHDRS` 能力原样保留**。**不得**写成「DADAO ELF 头永不进内存」。
    - `p_offset`：写成「**不要求**为 0；**不禁止**为 0」。
    - `p_align`：写成「**目标默认** = 64 KiB，**可被 `-z max-page-size` 覆写**」；**不得**写成硬编码不变式。
    - 只约束「M4 路径级脚本 + 可覆写目标默认值」，**不得**影响后续完整 linker 实现。
  - **引用可解析**：写入 `contract-elf.md` 的 spec 引用必须能过 `make check` 的 `check-spec-refs`（Check 1：`[DADAO-XX §...]` 须解析到 `spec/` 真实标题/粗体引子/正文行）。**注意**：`SBI_PTW_HANDLE_FAULT` 是 `DADAO-22 §4` 内的一行功能调用名、**非**标题/粗体引子 ⇒ 引用请用 `[DADAO-22 §4]`，把 `SBI_PTW_HANDLE_FAULT`/`page_mask` 放在正文；`[DADAO-12 §2.2.1]` 可解析（`#### 2.2.1 超页的地址转换`）。
  - **门控**：`.tao/**` 改动属**纯文档/台账**，按 `AGENTS.md`「收尾检查 1」**豁免 `make check`**；但 `contract-elf.md` 是 `check-spec-drift`/`check-spec-refs` 的审计对象，须**主动跑** `make check-spec-drift` 与 `make check-spec-refs` 确认 EXIT=0（`contract-elf.md` 的来源头/ADR 引用不被破坏）。
  - **临时目录** `/tmp/opencode/SPEC-112t/`；**不提交 git**；失败即停、禁自动重试；完成区与真实输出逐条对齐（见「硬约束清单」）。

### 用户裁定（原话，原样落盘；用户本轮确认）

1. 「B1」= **采用方案 B1：去掉 `FILEHDR PHDRS`**（不采用 A「加载器放行头部页」、不采用 B2「`.text`/`e_entry` 抬 64 KiB 占位」）。
2. 「1」= 页大小问题**并入本波一起做**（选项①）：`DADAO` target 设 `defaultMaxPageSize = 0x10000`（DADAO 页 = 64 KiB，依据 `spec/DADAO-12 §2.2.1`、`spec/DADAO-22 §SBI_PTW_HANDLE_FAULT` 的 64 KiB page_mask）。
3. 「ADR落点不重要，重要的是，这些decision不应该影响后面的完整linker的实现」← **硬约束**。ADR 落点由主会话定为 **`ADR-0003 §D5`**。

### 决策正文（写入 `ADR-0003 ## 修订` 的三条 decision；措辞已按「中性/不约束完整 linker」定稿）

- **① M4 裸机路径不使用 `FILEHDR PHDRS`**：M4 裸机路径的 `tests/scripts/dadao.lds` **不使用** `FILEHDR PHDRS`——ELF 头/程序头表**只存在于文件中、不进入 guest 内存**。**理由**：M4 无运行期消费者（freestanding、无动态链接/libc/OS，无 `AT_PHDR`/自省），加载器（QEMU，**host 侧**）从**文件**解析 `Ehdr`/`Phdr`。**LLD 的 `FILEHDR PHDRS` 能力原样保留**（本 decision 不削弱 linker 能力；任何后续布局仍可自行启用）。
- **② `p_offset` 不做要求**：首个 `PT_LOAD` 的 `p_offset` **不要求**为 0（也**不禁止**为 0）——它是链接器文件布局的产物，**不是不变式**。
- **③ `p_align` 目标默认 64 KiB、可覆写**：`p_align` 的**目标默认** = 64 KiB（`DADAO` target `defaultMaxPageSize = 0x10000`，依据 DADAO 页 = 64 KiB），**可被 `-z max-page-size` 覆写**——**目标默认值，非硬编码不变式**。
- **被否方案**：
  - **A（加载器放行头部页）**：让 QEMU ELF 加载器忽略落在映射区外的一页——**否决**（把问题推给加载器，且与 `ADR-0004 §D2.3`「任一 `PT_LOAD` 越界 ⇒ 报错非零退出」冲突加深）。
  - **B2（`.text`/`e_entry` 抬 64 KiB 占位）**：把 `.text`/入口上抬 64 KiB 给头部留位——**否决**（改变 RAM 布局与 reloc 期望值，污染 M4 已验收产物）。
- **不变项**：§D5 段最小对齐 / VA=PA / M1 raw-bin pipeline；`ADR-0004` 全部 decision；`ADR-0019` 的「本期禁用 relaxation / 4 类 reloc」。

### 硬约束清单（下发/执行必带）

1. **只动任务书范围**：只改上文「输出」列出的 5 个文件；越界须披露。
2. **不提交 git**。
3. **完成区与真实输出逐条对齐**：命令一律 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，**禁** `cmd | tee log; echo $?`（管道后 `$?` 是 `tee` 的，恒 0）。
4. **失败即停、禁自动重试**（含换参数/换命令/改文本后重跑）；失败现场（命令、完整输出、退出码）保留并报用户。
5. **临时目录** `/tmp/opencode/SPEC-112t/`；不得污染仓库。
6. **一键证据脚本** `.work/evidence/SPEC-112t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入→预期 FAIL→还原→回绿**自检（见「验收标准」7）；结尾**不得用 `tee` 吞退出码**。
7. **`make check` 豁免但不豁免引用门控**：见「约束 · 门控」。

## 验收标准

> 逐条可执行、机械可判；证据落 `.work/evidence/SPEC-112t/` 与 `.work/log/spec/`（复杂命令完整输出留存）。

1. **`ADR-0003` 修订到位**（grep 证据）：
   - `**状态**` 行含 `rev. 2026-10-06`，且仍为 `Accepted`；
   - §D5 含就地修订注记 + 新增「M4 ELF 路径补充」小节；
   - `## 修订` 含 `rev. 2026-10-06` 条目，逐项含三条 decision（①②③）、被否方案（A、B2）、scope 限定、不变项。
2. **`contract-elf §6.1.2`**：原 `FILEHDR PHDRS` … file-offset 0 的 bullet **已不存在**；新 bullet 同时含「不使用 `FILEHDR PHDRS`」「ELF 头/程序头表只存在于文件中、不进入 guest 内存」「首段从 `.text` 起（VA=PA）」「`p_offset` 不做要求」。给正/反 grep 输出。
3. **`contract-elf §5`**：含 `p_align` = **64 KiB（目标默认、可覆写）** 口径；其 spec 引用可解析（`make check-spec-refs` EXIT=0）。
4. **`milestones.md:78`**：不含「`FILEHDR PHDRS` 使 `.text` 落在 file offset 0」；含「不使用 `FILEHDR PHDRS`」「`p_align` 目标默认 64 KiB（可覆写）」。给 grep 输出。
5. **`ISS-155` 结案**：`status: closed`、`resolved_by: SPEC-112t`、`notes` 追加处置记录（原内容保留）；`notes` 说明「去 `FILEHDR PHDRS` 后首段回到 RAM 内（`0xFFFF00000000`），原『头部页落在 RAM 之下』问题根除；`QEMU-042t`/`INTEG-016t` 无需再处理该页」；文件仍为合法 YAML（`python3 -c 'import yaml;yaml.safe_load(open(".tao/knowledge/issues.yaml"))'` EXIT=0）。
6. **引用门控**：`make check-spec-drift` EXIT=0；`make check-spec-refs` EXIT=0；`make check-no-residue` EXIT=0（真实输出 + 退出码）。
7. **反例门控（脚本必须能失败）**：`.work/evidence/SPEC-112t/run.sh --inject` 对以下三类反例分别注入 → 检查**报 FAIL** → 还原 → **回绿**：
   - ①把「`dadao.lds` **不使用** `FILEHDR PHDRS`」改为「DADAO ELF 头**永不**进内存」（过度约束措辞）→ 检查 FAIL；
   - ②把「`p_offset` 不要求为 0」改为「`p_offset` 必须为 0」→ 检查 FAIL；
   - ③把「`p_align` 目标默认、可覆写」改为「`p_align` 恒为 64 KiB」→ 检查 FAIL。
   给出注入→FAIL→还原→回绿的真实输出；**另一小项**：$1 脚本自身对「删掉 `contract-elf §6.1.2` 新 bullet」亦能 FAIL。
8. **中性表述核验（静态）**：`ADR-0003` 与 `contract-elf.md` 中**不存在**以下把路径级决策升格为 linker 不变式的措辞（grep 反证）：
   - 「ELF 头永不进内存」「头/程序头表永不进入内存」类；
   - 「`p_offset` 恒为 0」「`p_offset` 必须为 0」类；
   - 「`p_align` 恒为 64 KiB」「页大小固定为 64 KiB」类。
9. **能力保留的反向锚点**：`ADR-0003 §修订 rev. 2026-10-06` 明确写有「**LLD 的 `FILEHDR PHDRS` 能力原样保留**」与「`p_align` 可被 `-z max-page-size` 覆写」。其**行为层**证明由 `LLVM-058t` 验收 6/7 承担（本任务只核验文本，不重跑 LLD）。
10. **状态**：完成后 `**状态**` 置 `待验收`；提交前须经 `/complete` 收尾。

## 完成区

**测试结果**：
- `bash .work/evidence/SPEC-112t/run.sh`（正常）→ **EXIT=0**（C1–C10 全 PASS，逐项输出见 `.work/log/spec/SPEC-112t-run-normal.log`）
- `bash .work/evidence/SPEC-112t/run.sh --inject` → **EXIT=0**（4/4 反例：注入生效→检查 FAIL→还原→回绿，见 `.work/log/spec/SPEC-112t-run-inject.log`）
- `make check-spec-drift` → **EXIT=0**（`spec drift check: PASS`，`.work/log/spec/SPEC-112t-check-spec-drift.log`）
- `make check-spec-refs` → **EXIT=0**（`结果: PASS (0 violations)`，738 引用全解析，`.work/log/spec/SPEC-112t-check-spec-refs.log`）
- `make check-no-residue` → **EXIT=0**（`check-no-residue: PASS`，`.work/log/spec/SPEC-112t-check-no-residue.log`）
- `python3 tools/infra/check_issues.py` → **EXIT=0**（41 open, 1 closed；虽 `issues.yaml` 属 `.tao/**` 豁免，仍主动跑）
- `python3 -c 'import yaml;yaml.safe_load(...)'` → **EXIT=0**（`.work/log/spec/SPEC-112t-yaml.log`）

**修改文件**（4 个输出文件 + 证据脚本；均在任务书范围内）：
1. `.tao/adr/adr-0003-object-abi.md`（`**状态**` rev；§D5 就地修订注 + 「M4 ELF 路径补充」小节；`## 修订` rev. 2026-10-06 条目）
2. `.tao/knowledge/contract-elf.md`（§6.1.2 bullet 改写；新增 §5.3 `p_align` 口径；附录 A §5/§6 行；**另**：文件头「来源」行补 rev. 2026-10-06——见自审 finding G1）
3. `.tao/knowledge/milestones.md:78`（M4 范围段措辞）
4. `.tao/knowledge/issues.yaml`（ISS-155 结案）
- 证据：`.work/evidence/SPEC-112t/run.sh`；日志：`.work/log/spec/SPEC-112t-*.log`

**验收结果**（逐条对应「验收标准」1–10；真实输出见上列日志）：
1. **ADR-0003 修订到位**：`C1a` 状态行仍 `Accepted`（rc=0）；`C1b` 含 `rev. 2026-10-06`（rc=0）；`C1c` §D5 含「M4 ELF 路径补充」小节（rc=0）；`C1d` §D5 含就地修订注（rc=0）；`C1e` `## 修订` 含 `rev. 2026-10-06（用户 2026-10-06 逐条确认；SPEC-112t）` 条目（rc=0）。`C3a–C3h`：①②③ decision、被否 A/B2、scope 限定、不变项齐备（rc=0）。全部 PASS。
2. **contract-elf §6.1.2**：`C4a` 旧 bullet「使 `.text` file-offset 0」已不存在（rc=0）；`C4b` 含「不使用 `FILEHDR PHDRS`」（rc=0）；`C4c` 含「只存在于文件中、不进入 guest 内存」（rc=0）；`C4d` 含「首个 `PT_LOAD` 从 `.text` 起」（rc=0）；`C4e` 含「`p_offset` **不做要求**」（rc=0）。全部 PASS。
3. **contract-elf §5**：新增 §5.3，`C5a` 含「`p_align` **目标默认 = 64 KiB**」（rc=0）；`C5b` 含「**可被链接选项 `-z max-page-size` 覆写**」（rc=0）；其 spec 引用 `[DADAO-12 §2.2.2 普通页的地址转换]`、`[DADAO-22 §4. 地址转换（cfx_ptw）]` 经 `C10b make check-spec-refs` EXIT=0 验证可解析（Check 1 失败=0）。全部 PASS。
4. **milestones.md:78**：`C6a` 不含「`FILEHDR PHDRS` 使 `.text` 落在 file offset 0」（rc=0）；`C6b` 含「不使用 `FILEHDR PHDRS`」（rc=0）；`C6c` 含「`p_align` **目标默认 64 KiB（可被 `-z max-page-size` 覆写）**」（rc=0）。全部 PASS。
5. **ISS-155 结案**：`C7`（python/yaml）`status=closed`、`resolved_by=SPEC-112t`、`notes` 含原「LLVM-056t F7」内容 + 追加「问题根除」「无需再处理该页」（rc=0）；YAML 合法（EXIT=0）。全部 PASS。
6. **引用门控**：`C10a check-spec-drift` rc=0；`C10b check-spec-refs` rc=0；`C10c check-no-residue` rc=0。全部 PASS。
7. **反例门控**：`run.sh --inject` EXIT=0，4/4：
   - ①「不使用 FILEHDR PHDRS」→「DADAO ELF 头永不进内存」⇒ C4b/C8b **FAIL** → 还原回绿；
   - ②「p_offset 不做要求」→「p_offset 必须为 0」⇒ C4e/C8f **FAIL** → 还原回绿；
   - ③「p_align 目标默认 = 64 KiB」→「p_align 恒为 64 KiB」⇒ C5a **FAIL** → 还原回绿；
   - ④ 删 §6.1.2 新 bullet ⇒ C4b/C4c/C4d/C4e **FAIL** → 还原回绿。
   每例均先经 `cmp` 证「注入生效（文件已变）」、再证「还原后与原文件 `cmp` 一致」。
8. **中性表述核验（静态）**：`C8a–C8h` 反证——ADR-0003 与 contract-elf 均**不含**「ELF 头永不进内存」「头/程序头表永不进入内存」「`p_offset` 恒为 0」「`p_offset` 必须为 0」「`p_align` 恒为 64 KiB」「页大小固定为 64 KiB」（rc=0）。全部 PASS。
9. **能力保留反向锚点**：`C9a` ADR-0003 修订条目含「LLD 的 `FILEHDR PHDRS` 能力原样保留」（rc=0）；`C9b` 含「`p_align` 可被 `-z max-page-size` 覆写」（rc=0）。本任务只核验文本，未重跑 LLD（行为层证明归 `LLVM-058t` 验收 6/7）。PASS。
10. **状态**：任务书 `**状态**` 已置 `待验收`；待主会话 `/complete` 收尾。

**新发现/坑**：
1. **任务书 §接口规范/硬约束给出的引用形态 `[DADAO-12 §2.2.1]`、`[DADAO-22 §4]` 实际无法被 `check_spec_refs.py` 解析**——该器 `resolve_section` 对数字小节要求引用文本 **含完整标题正文**，`[DADAO-XX §N]` 仅数字（后跟空格/点，非 lead-in 字符 `：:（(，,`）会判「节标题未找到」。**已改为可解析的完整标题形态**：`[DADAO-12 §2.2.2 普通页的地址转换]`、`[DADAO-22 §4. 地址转换（cfx_ptw）]`（与 `contract-abi.md`/`contract-isa.md` 既有约定一致，如 `[DADAO-21 §寄存器规范]`）。经 `make check-spec-refs` EXIT=0 验证。**建议沉淀**：`check_spec_refs` 的引用写法约定（数字小节须带标题正文）。
2. **任务书把「普通页 64 KiB / `VA[15:00]` 页内偏移」归到 §2.2.1，实际该内容在 §2.2.2「普通页的地址转换」**（§2.2.1 是「超页的地址转换」，512 MiB）。为准确引用，§5.3 改引 §2.2.2；依据说明仍成立（DADAO 普通页 = 64 KiB）。**建议沉淀**：DADAO-12 §2.2.1/§2.2.2 页码归属（超页/普通页）。
3. `contract-elf.md` 是 `check-spec-refs` 的审计对象；**新增 spec 引用即被机械解析**，故引用写法须一次写对（本轮靠 `make check-spec-refs` 兜底）。
4. **偏离披露**：除任务书列出的 `contract-elf §5/§6.1.2/附录A`，另改了同文件**文件头「来源」行**（补 `rev. 2026-10-06`），使来源头与正文/ADR 修订一致；未新增/改动任何 decision，未动 `ADR-0004`/`ADR-0019`/组件源码。

**遗留问题**：无（任务书范围 4 项全部完成；行为层 `FILEHDR PHDRS` 能力保留由 `LLVM-058t` 验收 6/7 承担，非本任务范围）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查方式**：自主逐行审查本任务 4 个改动文件的 diff（`/tmp/opencode/SPEC-112t/changes.diff`，120 行），并逐条对照任务书「验收标准 1–10」与「硬约束清单」；以 `run.sh` / `--inject` / 三门控真实退出码为证据。

**判决：通过（自审无未修 finding；1 项有意偏离已披露）**

**逐条断言核验**：
- 中性/不约束完整 linker：ADR-0003 D5 与修订条目均以「**M4 裸机路径的 `tests/scripts/dadao.lds` 不使用 `FILEHDR PHDRS`**」限定范围，且明写「**LLD 的 `FILEHDR PHDRS` 能力原样保留**」；`p_offset` 写「不要求为 0、也不禁止为 0」；`p_align` 写「目标默认 64 KiB、可被 `-z max-page-size` 覆写」。`C8a–C8h` 反证无过度约束措辞（rc=0）。
- 未改 `ADR-0004`/`ADR-0019`/组件源码：`git status --short` 仅 4 个目标文件被改（另有下发前既存的 SPEC-104k 修改与 SPEC-112t/LLVM-058t 未跟踪任务书，非本任务产出）。
- 未新增/修改任何未经用户逐条确认的 decision：仅落地任务书 §决策正文 的三条 decision + 被否 A/B2 + scope + 不变项。
- 无悬挂引用：新增 §5.3 后，§5.1/§5.2 既有被引（§6.1.1→§5.1、§6.1.2→§5.2）未受影响；`make check-spec-refs` 738 引用 0 失败。

**findings 及处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务书指定引用形态 `[DADAO-12 §2.2.1]`/`[DADAO-22 §4]` 经 `check_spec_refs.resolve_section` 实测**不可解析**（数字小节须带完整标题正文）；若照抄将致 `make check-spec-refs` FAIL | ✅已修 | §5.3 改引 `[DADAO-12 §2.2.2 普通页的地址转换]`、`[DADAO-22 §4. 地址转换（cfx_ptw）]`（完整标题形态，同 `contract-abi.md` 既有约定） | `make check-spec-refs` EXIT=0（Check 1 失败=0，738/738 解析，`.work/log/spec/SPEC-112t-check-spec-refs.log`）；C10b rc=0 |
| F2 任务书将「普通页 64 KiB / `VA[15:00]`」归到 §2.2.1，实测该内容在 §2.2.2（§2.2.1 为「超页」，512 MiB） | ✅已修 | 同 F1，改引 §2.2.2 以名实相符 | 同上；§2.2.2 line 126「普通页的页内偏移为 16 位，即 64KiB」 |
| F3 超越任务书字面列出项（§5/§6.1.2/附录A）：另改了 `contract-elf.md` 文件头「来源」行补 `rev. 2026-10-06` | ❌不修（非缺陷，有意为之） | 文件头来源行补 ADR-0003 `rev. 2026-10-06`，使来源头与正文/ADR 修订/附录 A 一致 | 已在完成区「修改文件」「新发现/坑·4」披露；`make check-spec-drift` EXIT=0 不因此变红 |
| F4 ADR-0003 `## 状态说明` 未提 rev. 2026-10-06（是否应同步） | ❌不修（遵循既有惯例） | 不改 | 同类先例 `ADR-0004 §状态说明` 亦仅记首评 + 首次 rev，未列后续 rev（adr-0004 line 357）；故 `## 状态说明` 稳态不动与惯例一致，变更记录由 `## 修订` 承载 |
| F5 反例脚本可能「恒真/空注入」 | ✅已修（设计即规避） | `run.sh --inject` 每例先 `cmp` 证文件已变（非空注入）、还原后再 `cmp` 证一致；`python` 注入前 `assert 锚点计数==1` | `--inject` EXIT=0，4/4 检出并回绿（`.work/log/spec/SPEC-112t-run-inject.log`） |

**防造假核验**：完成区所引命令输出均来自 `.work/log/spec/SPEC-112t-*.log` 的真实运行（`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`）；`run.sh` 正常模式与 `--inject` 模式的退出码均已实跑确认。

#### 第 1 轮 reviewer 验收（下发前预检）

**审查范围**：`SPEC-112t` + `LLVM-058t` 两份新建任务书 + `SPEC-104k` 本轮追加登记。按 AGENTS「下发前预检」4 项 + 本轮 7 项硬约束逐项核验。

**判决：Accepted**（可直接下发）

---

**逐项结论**：

**1. 任务书内部一致性** ✅

- `SPEC-112t` 三条 decision 与用户裁定**逐字一致**：
  - D1「B1」→「去掉 `FILEHDR PHDRS`」：任务书 line 44/50 一致 ✓
  - D2「1」→「页大小并入本波…`defaultMaxPageSize = 0x10000`」：任务书 line 45/52 一致 ✓
  - D3「ADR落点不重要…不应该影响后面的完整linker的实现」→ `ADR-0003 §D5`：任务书 line 46 一致 ✓
- `LLVM-058t`「只改 2 行」（`dadao.lds` 1行 + `DADAO.cpp` 1行）与验收标准 2/3 一致 ✓
- 目标/范围/约束/验收逐条无矛盾 ✓

**2. 依赖链实际可用性** ✅

- `LLVM-058t` 依赖 `SPEC-112t`（spec-first）正确且足够：`SPEC-112t` 产出 `contract-elf`/`ADR-0003` 修订文本，`LLVM-058t` 据此实现 ✓
- 前置存在性核实：
  - `make build-lld`：Makefile line 195 存在 ✓
  - `tools/infra/make_patch.py`：`spec/Process-01` 引用 ✓
  - `make check-patch-tree`：Makefile line 279 存在 ✓
  - `.work/evidence/LLVM-056t/inputs/`：11 个 `.s` 文件齐全（`data.s`/`ovf_*.s`/`ram_*.s`/`reloc.s`/`rom_*.s`）✓
  - `llvm-mc`/`ld.lld`/`llvm-readobj`：由 `make build-mc`/`make build-lld` 产出 ✓
  - `components/llvm-project/series`：57 项，含 `lld/ELF/Arch/DADAO.cpp.patch` ✓

**3. 验收可执行性** ✅

- Makefile 目标存在性核实（逐条 `grep Makefile`）：
  - `check-spec-drift`：line 275 ✓
  - `check-spec-refs`：line 304 ✓
  - `check-dirs`：line 313 ✓
  - `check-no-residue`：line 317 ✓
  - `check-patch-tree`：line 279 ✓
  - `check-lit`：line 346 ✓
  - `test-codegen`：line 364 ✓
  - `build-lld`：line 195 ✓
- SPEC-112t 验收：`check-spec-drift`/`check-spec-refs`/`check-no-residue` **现在可跑**（纯文档改动）；其余 grep 证据在工程师实现后可跑 ✓
- LLVM-058t 验收：`build-lld`/`check-patch-tree`/`check`/`test-codegen`/`check-lit` 需重建 lld（工程师职责，非 BLOCKED）；脚本级反向证明①不需重建 ✓
- `issues.yaml` `status` 合法取值确认：`status: open | closed`（line 31）；`resolved_by: closed 时必填`（line 38）；当前文件无 `closed` 条目（历史已归档至 `M1/M2/M3/issues-closed.md`）✓
- `.work/evidence/LLVM-056t/inputs/` 11 文件齐全 ✓

**4. 与 spec/vectors 一致** ✅

- `contract-elf §5`（line 117）/`§6.1.2`（line 163）/附录A：存在且内容与任务书引用一致 ✓
- `ADR-0003 §D5`（line 58）：存在，当前不含 `rev. 2026-10-06`（待 SPEC-112t 修订）✓
- `ADR-0004 §D2.2`（line 73）/`§D2.3`（line 81）：存在，含「PT_LOAD 越出映射区域 ⇒ 报错非零退出」✓
- `DADAO-12 §2.2.1`：`#### 2.2.1 超页的地址转换`（line 79）可解析 ✓
- `DADAO-22 §4`：`## 4. 地址转换（cfx_ptw）`（line 122）可解析；`SBI_PTW_HANDLE_FAULT` 在 line 133 表格内（非标题，任务书约束已明确用 `[DADAO-22 §4]`）✓
- `milestones.md:78` 当前含「`FILEHDR PHDRS` 使 `.text` 落在 file offset 0」措辞，待 SPEC-112t 修正 ✓
- `ISS-155`（line 394）：`status: open`，待 SPEC-112t 结案 ✓
- 无冲突/漂移 ✓

**5. 中性/不约束完整 linker 硬约束** ✅

- 两份任务书均无以下残留措辞：
  - 「ELF 头永不进内存」类：未出现 ✓
  - 「`p_offset` 必须为 0」/「`p_offset` 恒为 0」类：未出现 ✓
  - 「`p_align` 恒为 64 KiB」/「页大小固定为 64 KiB」类：未出现 ✓
- `SPEC-112t` 硬约束清单（line 33-37）明确：
  - 表述为「M4 裸机路径 `dadao.lds` 不使用 `FILEHDR PHDRS`」；LLD 能力保留 ✓
  - `p_offset`「不要求为 0；不禁止为 0」✓
  - `p_align`「目标默认 = 64 KiB，可被 `-z max-page-size` 覆写」✓
  - 只约束「M4 路径级脚本 + 可覆写目标默认值」✓
- `LLVM-058t` 硬约束清单（line 28-31）：
  - `defaultMaxPageSize` 为默认值，非不变式 ✓
  - `p_offset` 实测值，非算法不变式 ✓
  - 不新增 linker 层硬编码约束 ✓
  - 不动 `DADAO.cpp` 其它函数 ✓
- `LLVM-058t` 验收 6/7（反向证明①②）保证能力保留：`FILEHDR PHDRS` 可加回仍链接成功；`-z max-page-size` 可覆写 ✓

**6. 反例门控可失败性** ✅

- SPEC-112t 验收 7（3 类措辞注入）：
  - ①「不使用 FILEHDR PHDRS」→「ELF 头永不进内存」：文本级注入，grep 可检测过度约束措辞 → FAIL ✓
  - ②「p_offset 不要求为 0」→「p_offset 必须为 0」：文本级注入 → FAIL ✓
  - ③「p_align 目标默认、可覆写」→「p_align 恒为 64 KiB」：文本级注入 → FAIL ✓
  - 附加：删 `contract-elf §6.1.2` 新 bullet → 检查缺失 → FAIL ✓
- LLVM-058t 验收 12（脚本级 + 源码级注入）：
  - (a) 脚本级：`dadao.lds` 改回 `FILEHDR PHDRS` → 首段越界 → FAIL（不需重建）✓
  - (b) 源码级：`defaultMaxPageSize` 改 `0x1000` → 重建 → `p_align` 检查 FAIL ✓
  - 注入有效性：`git diff --name-only` 非空检查 ✓
- 注入均为可执行且能真正 FAIL 的操作 ✓

**7. 落盘/编号** ✅

- `SPEC-112t`：未与既有冲突（`SPEC-111t` 存在，`SPEC-112t` 为下一个编号）✓
- `LLVM-058t`：未与既有冲突（`LLVM-057m` 存在，`LLVM-058t` 为下一个编号）✓
- `SPEC-104k` 本轮追加（修订记录 2026-10-06·4）：
  - 只追加，未改写正文/任务表（任务表仍为 27 行数据，不含 SPEC-112t/LLVM-058t；新任务仅在修订记录 §A 注册）✓
  - 与前几轮修订记录（·1/·2/·3）的追加模式一致 ✓

---

**关键命令输出**：

```
$ grep -n 'check-spec-drift\|check-spec-refs\|check-dirs\|check-no-residue\|check-patch-tree\|check-lit\|test-codegen\|build-lld' Makefile | head -15
39:        clean-work build-mc build-mc-lite build-mc-reconfig build-lld \
41:        validate-vectors check-spec-refs check-spec-drift check-asm-list \
44:        check-dirs check-no-residue check-cfx-aliases check-asm-prose check-lit \
45:        test-codegen \
46:        check-patch-tree check-index-blobs check-source-state check-asm-list-drift size-report \
69:	@echo "  make build-lld       Build LLD linker (bin/ld.lld)"
195:build-lld: manifest-check
275:check-spec-drift:
279:check-patch-tree:
304:check-spec-refs:
313:check-dirs:
317:check-no-residue:
346:check-lit:
364:test-codegen: build-mc build-qemu

$ ls .work/evidence/LLVM-056t/inputs/
data.s  ovf_abs48.s  ovf_abs48i.s  ovf_rel14.s  ovf_rel20.s  ovf_rel26.s
ram_fill.s  ram_ovf.s  reloc.s  rom_fill.s  rom_ovf.s
(11 files, EXIT=0)

$ grep -n 'status:' .tao/knowledge/issues.yaml | grep -v open | head -5
(无输出 — 当前 issues.yaml 无 closed 条目，历史已归档)

$ head -3 .tao/knowledge/issues.yaml | grep -A2 '字段约束'
# 字段约束：
#   status: open | closed
#   resolved_by: closed 时必填, open 时 null

$ grep -n 'DADAO-12.*2\.2\.1\|2\.2\.1' spec/DADAO-12-SEE-主管系统运行环境.md
79:#### 2.2.1 超页的地址转换

$ grep -n '## 4\.' spec/DADAO-22-SBI-主管系统二进制接口.md
122:## 4. 地址转换（cfx_ptw）

$ ls .tao/tasks/spec/SPEC-11[13]*.md .tao/tasks/llvm/LLVM-05[79]*.md 2>/dev/null
.tao/tasks/llvm/LLVM-057m-M4-llvm里程碑.md
.tao/tasks/spec/SPEC-111t-归档SimRISC-0.5.3至archive.md
(SPEC-112t/LLVM-058t 未存在 = 无编号冲突)

$ wc -l components/llvm-project/series
57

$ grep 'DADAO.cpp' components/llvm-project/series
lld/ELF/Arch/DADAO.cpp.patch

$ wc -l .work/source/llvm-project/lld/ELF/Arch/DADAO.cpp
193

$ grep -n 'defaultMaxPageSize' .work/source/llvm-project/lld/ELF/Arch/PPC64.cpp
605:  defaultMaxPageSize = 65536;

$ grep -n 'defaultMaxPageSize' .work/source/llvm-project/lld/ELF/Target.h
144:  unsigned defaultMaxPageSize = 4096;

$ sed -n '78p' .tao/knowledge/milestones.md
范围：…③ LLD 链接器（含链接脚本 `dadao.lds`：…`FILEHDR PHDRS` 使 `.text` 落在 file offset 0）；…
(确认 line 78 含待删除措辞)

$ sed -n '394,405p' .tao/knowledge/issues.yaml
- id: ISS-155
  title: "FILEHDR PHDRS 使 ELF 头落在 RAM 下方一页 + .text 字面 sh_offset≠0…"
  status: open
  scope: [qemu, integ]
  blocks: []
  resolved_by: null
  notes: "LLVM-056t F7：…"
```

#### 第 2 轮 reviewer 验收（实现后独立验收）

**审查范围**：engineer 产出 4 文件（ADR-0003 / contract-elf / milestones.md / issues.yaml）+ 证据脚本 `.work/evidence/SPEC-112t/run.sh`。

**判决：Accepted**

---

**1. 证据脚本审查**

- **FAIL 路径**：4 类注入各自触发的 `[FAIL]` 检查名均非恒真（①→C4b+C8b、②→C4e+C8f、③→C5a、④→C4b~C4e），FAIL 分支真实可达。✓
- **注入非空可还原**：每例先 `cmp` 证文件已变（非空注入），还原后再 `cmp` 证一致；Python 注入前 `assert s.count(x) == 1` 确保锚点唯一。✓
- **结尾无 `tee`**：脚本用 `exit 0`/`exit 1`（`IRC` 变量），不使用 `tee`。✓
- **无恒真断言**：每条 `present`/`absent` 检查独立于注入变量，注入后确有对应 `[FAIL]`。✓

**2. 重跑记录**

**正常模式** `run.sh` → **EXIT=0**（27/27 全 PASS）：
```
###### 正常校验 ######
== C1 ADR-0003 状态/修订 ==
  [PASS] C1a 状态行仍为 Accepted (期望: Accepted; rc=0)
  [PASS] C1b 状态行含 rev. 2026-10-06 (期望: 含 rev. 2026-10-06; rc=0)
  [PASS] C1c §D5 含「M4 ELF 路径补充」小节 (期望: 存在小节; rc=0)
  [PASS] C1d §D5 含就地修订注 (期望: 存在; rc=0)
  [PASS] C1e ## 修订 含 rev. 2026-10-06 条目 (期望: 存在; rc=0)
== C3 ## 修订 条目内容 ==
  [PASS] C3a–C3h 全部 PASS（8/8）
== C4 contract-elf §6.1.2 ==
  [PASS] C4a–C4e 全部 PASS（5/5）
== C5 contract-elf §5 ==
  [PASS] C5a–C5b 全部 PASS（2/2）
== C6 milestones.md ==
  [PASS] C6a–C6c 全部 PASS（3/3）
== C7 ISS-155 结案 ==
  [PASS] C7（1/1）
== C8 中性表述静态核验（反证） ==
  [PASS] C8a–C8h 全部 PASS（8/8）
== C9 能力保留反向锚点 ==
  [PASS] C9a–C9b 全部 PASS（2/2）
== C10 门控 ==
  [PASS] C10a make check-spec-drift (EXIT=0)
  [PASS] C10b make check-spec-refs (EXIT=0)
  [PASS] C10c make check-no-residue (EXIT=0)
###### 结果: PASS (全部检查通过) ######
```

**注入模式** `run.sh --inject` → **EXIT=0**（4/4 检出并回绿）：
```
###### 反例注入自检 ######
  -- 注入生效: ①『不使用 FILEHDR PHDRS』→『DADAO ELF 头永不进内存』
      [FAIL] C4b / C8b
  [PASS] 注入被检出 / 还原后回绿
  -- 注入生效: ②『p_offset 不做要求』→『p_offset 必须为 0』
      [FAIL] C4e / C8f
  [PASS] 注入被检出 / 还原后回绿
  -- 注入生效: ③『p_align 目标默认、可覆写』→『p_align 恒为 64 KiB』
      [FAIL] C5a
  [PASS] 注入被检出 / 还原后回绿
  -- 注入生效: ④ 删掉 contract-elf §6.1.2 新 bullet
      [FAIL] C4b / C4c / C4d / C4e
  [PASS] 注入被检出 / 还原后回绿
###### 注入自检: PASS (4/4 检出并回绿) ######
```

**3. 独立注入（与 engineer 4 例不同）**

注入：把 ADR-0003 里「`p_align` 可被 `-z max-page-size` 覆写」改为「`p_align` 不可被覆写（硬编码）」。

```
# 注入前还原确认
$ diff backup.md adr-0003-object-abi.md → 0 行差异

# 注入
$ python3 -c "替换 p_align 可被覆写 → 不可被覆写"
锚点出现次数: 1（仅 §D5 的③ decision）
注入完成

# 验证注入生效
$ git diff --name-only → .tao/adr/adr-0003-object-abi.md（非空）

# 检查 FAIL
$ run.sh → [FAIL] C9b ADR 含「p_align 可被 -z max-page-size 覆写」(rc=1)
run_checks EXIT=1

# 还原
$ cp backup.md adr-0003-object-abi.md → diff 0 行

# 回绿
$ run.sh → [PASS] C9b (rc=0)
run_checks EXIT=0
```

结论：注入检出 FAIL → 还原后回绿。独立注入有效。✓

**4. 独立复核（逐条真实输出）**

| 检查项 | 真实输出 | 判定 |
|--------|----------|------|
| ADR-0003 `**状态**` 含 `rev. 2026-10-06` 且仍 `Accepted` | line 3: `Accepted（rev. 2026-09-13: ...; rev. 2026-10-06: M4 ELF 路径 ...）` | ✓ |
| §D5 含就地修订注 + 「M4 ELF 路径补充」小节 | line 90-98: `#### M4 ELF 路径补充（M4；2026-10-06 就地修订）` + ①②③ + 不变项 | ✓ |
| `## 修订` rev. 2026-10-06 条目含三条 decision + 被否 A/B2 + scope + 不变项 | line 156-168: 完整条目，三条 decision 逐字与用户裁定一致 | ✓ |
| 三条 decision 与用户裁定逐字一致 | ①「B1→去掉 FILEHDR PHDRS」✓ ②「p_offset 不做要求」✓ ③「p_align 目标默认 64 KiB、可覆写」✓ | ✓ |
| contract-elf §6.1.2 旧 bullet 已删 | `absent '使 .text file-offset 0'` → PASS | ✓ |
| contract-elf §6.1.2 新 bullet 含全部要点 | line 180: 不使用 FILEHDR PHDRS / 只存在于文件中 / 从 .text 起 / p_offset 不做要求 | ✓ |
| contract-elf §5.3 p_align 口径 | line 140-142: 目标默认 64 KiB / 可被 -z max-page-size 覆写 / 非硬编码不变式 | ✓ |
| milestones.md:78 | line 78: 不使用 FILEHDR PHDRS / p_align 目标默认 64 KiB（可覆写） | ✓ |
| ISS-155 status=closed / resolved_by=SPEC-112t | line 396-399: `status: closed` / `resolved_by: SPEC-112t` | ✓ |
| ISS-155 notes 追加且原内容保留 | line 400: 含原「LLVM-056t F7」+ 追加「问题根除」「无需再处理该页」 | ✓ |
| issues.yaml 合法 YAML | `python3 yaml.safe_load` EXIT=0 | ✓ |

**5. 中性/不约束完整 linker 核验**

逐文件 grep 反证：
- `absent ADR 'ELF 头永不进内存'` → PASS（不存在过度约束措辞）✓
- `absent ADR '头/程序头表永不进入内存'` → PASS ✓
- `absent ADR/CE 'p_offset 恒为 0'` / `'p_offset 必须为 0'` → PASS ✓
- `absent ADR 'p_align 恒为 64 KiB'` / `'页大小固定为 64 KiB'` → PASS ✓
- 正向锚点：ADR-0003 line 94 含「LLD 的 FILEHDR PHDRS 能力原样保留」✓；line 96 含「可被 -z max-page-size 覆写」✓
- contract-elf line 180: 「M4 裸机路径 dadao.lds **不使用** FILEHDR PHDRS」（路径级限定）✓
- contract-elf line 142: 「**目标默认值，非硬编码不变式**」✓

**6. 不变项核验**

- `git diff --name-only`：**不含** `ADR-0004`/`ADR-0019`（`grep -E 'ADR-0004|ADR-0019'` 无输出）✓
- 改动文件仅 4 个目标文件 + SPEC-104k 追加登记（architect 所加，允许）✓

**7. 引用正确性核验**

- DADAO-12 §2.2.1 = `#### 2.2.1 超页的地址转换`（line 79，512 MiB 超页）——**非**普通页
- DADAO-12 §2.2.2 = `#### 2.2.2 普通页的地址转换`（line 119），含 `VA[15:00]` → 页内偏移 = 16 位 = 64 KiB
- engineer 披露「§2.2.1 是超页、普通页在 §2.2.2」**属实**；contract-elf §5.3 已改为 `[DADAO-12 §2.2.2 普通页的地址转换]` ✓
- `make check-spec-refs` EXIT=0（738 引用 0 violations）确认引用可解析 ✓

**8. 门控真实输出**

```
$ make check-spec-drift → EXIT=0（spec drift check: PASS）
$ make check-spec-refs → EXIT=0（结果: PASS (0 violations)）
$ make check-no-residue → EXIT=0（check-no-residue: PASS）
$ python3 tools/infra/check_issues.py → EXIT=0（41 open, 1 closed）
$ python3 yaml.safe_load → EXIT=0（合法 YAML）
```

**9. 未经用户确认的 decision 核验**

`git diff .tao/adr/adr-0003-object-abi.md | grep '^+'` 未出现 D6+ 新 decision。仅落地任务书 §决策正文 的①②③ + 被否 A/B2 + scope + 不变项。**无新增未经确认的 decision**。✓

**10. engineer 披露核验**

- 引用带完整标题（`[DADAO-12 §2.2.2 普通页的地址转换]`、`[DADAO-22 §4. 地址转换（cfx_ptw）]`）：属实且必需（`check_spec_refs` 要求完整标题形态）。✓
- §2.2.1→§2.2.2 修正：属实（§2.2.1=超页 512 MiB，§2.2.2=普通页 64 KiB）。✓
- 两处披露均非阻塞（引用正确性已由 `make check-spec-refs` EXIT=0 证实）。

---

**总结**：engineer 产出 4 文件改动全部在任务书范围内，三条 decision 与用户裁定逐字一致，中性/不约束完整 linker 硬约束全部守住，引用正确性经 `make check-spec-refs` 机械验证，反例脚本 FAIL 路径真实可达且注入非空可还原。**Accepted**。
