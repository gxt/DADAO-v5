# LLVM-078t: 数据指示符口径（工具链生成侧/受理侧 + 用例跟改）【`ISS-181` 拆分-②】

**模块**：llvm
**项目里程碑**：M6
**依赖**：**`SPEC-130t`（正文口径 + 锁，`已验证`）**、`INFRA-050t`（一次构建 `DADAO;X86`）、`LLVM-062t`/`LLVM-063t`/`LLVM-065t`/`LLVM-069t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：已验证

> **覆盖缺口**：**`ISS-181`** 的**工具链实现 + 用例跟改**部分。**说明（拆分）**：`ISS-181` 拆为 **`SPEC-130t`（规范正文 + 锁）** + **`LLVM-078t`（本文件）**；**本任务依赖 `SPEC-130t`**（正文口径先落，再对齐实现，Spec-first）。

## 用户裁定（2026-10-10，经主会话转述的原话/结论，原样落纸）

> 用户 **2026-10-10 裁定：4 条缺口（`ISS-182` / `ISS-185` / `ISS-186` / `ISS-181`）全部纳入 M6**（「10 点前完不成 ⇒ 全加、跑一晚上」）。其中 **`ISS-181`（数据指示符口径）** 的裁定为：
> - **① 只留 `.dd.b08` / `.dd.w16` / `.dd.t32` / `.dd.o64`**（`.byte` / `.short` / `.long` / `.quad` / `.word` / `.octa` **全部禁**）。
> - **② 两侧一致**：`llc` **只生成** `.dd.*`，`llvm-mc` **拒绝** GAS 名（**若「受理侧拒」确需动 LLVM 通用 MC 代码，须先评估可行性并给结论**：可行则做；**确不可行 ⇒ 退回「只禁生成侧」并登记**）。
> - **③ 删 `.align`，只留 `.p2align`**（实测 `.align N` 是**字节数**语义、与 GAS 的 `2^N` 冲突）。
> - **④ 不立 ADR**：改 v5 侧 `spec/Toolchain-01 §7` + `.tao/knowledge/contract-asm.md` 正文 + 同步 `manifests/spec-readonly.lock.toml` 的 `sha256`；**不动上游 `DADAO-11`**（归 `SPEC-130t`）。
> - **⑤ `.dd.128` 暂不加**（用户保留；如加为小改）。
> - **⑥ 跟改面**：`tests/**`（lit CHECK 行、e2e `.s`、`tests/scripts/*.s`）与 `components/llvm-project/patches/**` 内受影响的 DADAO 侧 directive 串（`DADAOMCAsmInfo`）。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现状（实现侧，实测）**：
  - `llc` **生成侧**发 **GAS 名**：`i8→.byte`、`i16→.short`、`i32→.long`、`i64/指针→.quad`、`i128→两条 .quad`；数据段对齐发 **`.p2align N, 0x0`**。根因：`DADAOMCAsmInfo` **未覆盖** data directive 串 ⇒ 继承 `MCAsmInfo` 默认（`.byte/.short/.long/.quad`）。
  - **受理侧** `llvm-mc`：`.dd.b08/.dd.w16/.dd.t32/.dd.o64` 与 `.byte/.short/.long/.quad` **两套名字当前都能汇编**（各 rc=0）；`.word` 已被拒（`unknown directive`）；`.octa` 已被显式拒（提示 GAS 16 字节语义）。
- **目的**：按 `SPEC-130t` 收口的正文口径，把**实现侧**对齐——`llc` 只生成 `.dd.*`；受理侧尽量拒 GAS 名；删 `.align` 只留 `.p2align`；同步用例。
- **性质 = 工具链口径对齐（llvm 模块）**。

**证据指针**：`.work/log/integ/pending-registrations.md §R1`；`spec/Toolchain-01 §7`（`SPEC-130t` 改后）；issue `ISS-181`；`components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`）；重点 `MCTargetDesc/DADAOMCAsmInfo.{h,cpp}`（data directive 串 + alignment 串）、可能的 AsmParser/AsmPrinter。
  - `spec/Toolchain-01 §7`（`SPEC-130t` 改后 = 权威口径）；`.tao/knowledge/contract-asm.md`；`spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + `tests/**`）：
  1. **生成侧**：`llc` 对 `i8/i16/i32/i64`（及指针）**只生成** `.dd.b08/.dd.w16/.dd.t32/.dd.o64`（改 `DADAOMCAsmInfo` 的 `Data8/16/32/64bitsDirective` 等）；对 `i128` 保持**两条 `.dd.o64`**（`.dd.128` **不加**，用户裁定 ⑤）。
  2. **`.align`**：生成侧**不再发 `.align`**（保持/收紧为 `.p2align`）；受理侧对 `.align` 的处置按 ③ 与下述可行性评估。
  3. **受理侧（先评估可行性）**：使 `llvm-mc` **拒绝** GAS 名（`.byte/.short/.long/.quad`）——**先评估**：能否**target-scoped** 实现（不改 LLVM 通用 MC 代码）？
     - **可行** ⇒ 落地拒绝（rc≠0，给诊断信息）；
     - **确不可行（须动 `llvm/lib/MC/MCParser/AsmParser.cpp` 等通用 MC 代码）** ⇒ **退回「只禁生成侧」并登记**（在完成区 + `issues.yaml` 记「受理侧拒 GAS 名不可行/成本过高，暂只禁生成侧」），**不得擅自改通用 MC 层**（若确需 ⇒ **停下报告**）。
  4. **用例跟改**：`tests/**` 受影响处按新口径重派生/更新——lit CHECK 行、`tests/e2e/**` 的 `.s`、`tests/scripts/*.s`（**期望值按册/契约重新派生，不从实现反填**）；`components/llvm-project/patches/**` 内受影响的 DADAO 侧 directive 串同步。
  5. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 口径来自 `SPEC-130t` 的正文（**不从实现反推**，Spec-first）；**不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出；spec 侧归 `SPEC-130t`）。
  - **不引 libc/compiler-rt**（M6 约束）。
  - **不改 LLVM 通用 MC 代码**（`llvm/lib/MC/**`）；确需 ⇒ 停下报告（见上 3）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-078t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-078t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-078t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **生成侧只发 `.dd.*`**：`llc` 对一个含 `i8/i16/i32/i64/指针/全局` 的最小模块**只发** `.dd.b08/.dd.w16/.dd.t32/.dd.o64`，**不再发** `.byte/.short/.long/.quad`（给真实命令 + `llc -filetype=asm` 输出证据 + rc）；`i128` 仍两条 `.dd.o64`。
2. **受理侧（按评估结论）**：`.dd.*` 受理 rc=0；GAS 名（`.byte/.short/.long/.quad`）——**可行则拒绝（rc≠0 + 诊断）**；**不可行则如实登记**（完成区 + `issues.yaml`），并给「可行性评估结论 + 依据（为何须动通用 MC 代码）」。
3. **`.align` 删**：生成侧不再发 `.align`（给 grep 证据）；受理侧 `.align` 行为按 ③ 与评估结论如实记录（本任务**不裁决** `.align` 的受理与否超出裁定范围）。
4. **用例跟改**：`tests/**` 受影响处（lit CHECK 行 / e2e `.s` / `tests/scripts/*.s`）已按新口径更新；`make check-lit` 及相关门控 **EXIT=0**（通过数与改前**逐项相等 / 不下降**）。
5. **E2E**：一段含全局数据（`.dd.*`）的程序经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码；确保数据段字节正确）。
6. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
7. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出（spec 侧归 `SPEC-130t`）。
8. **一键证据脚本**：`.work/evidence/LLVM-078t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（**把 directive 串改回 GAS 名 ⇒ 生成侧断言 FAIL ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿**），给真实输出与退出码。
9. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**用户裁定落实**：无子会话用户问答（裁定见任务书 `§用户裁定` + 主会话下发）；①唯一数据指示符 `.dd.b08/.dd.w16/.dd.t32/.dd.o64`、②`llc` 只生成 `.dd.*` + `llvm-mc` 拒 GAS 名、③删 `.align` 只留 `.p2align`、⑤`.dd.128` 不加、⑥跟改面 全部落地；不改 `spec/`、不立 ADR、不动上游 `DADAO-11`。
**受理侧可行性评估结论**：**可行——能 target-scoped 拒绝，无需改通用 MC 代码**。依据：`llvm/lib/MC/MCParser/AsmParser.cpp:1941` 在通用 `DirectiveKindMap` 分派（L1958+）**之前**先调 `getTargetParser().parseDirective(ID)`；`DADAOAsmParser::parseDirective`（`DADAOAsmParser.cpp:1163`，`MCTargetAsmParser`）即该 target parser，已用同机制处理 `.octa`/`.dd.*`。故在其内对 `.byte/.short/.long/.quad/.align` 返回 `Error()`（=Failure）即 shadow 通用内建；`llvm/lib/MC/**` **未动**。
**测试结果**：`.work/evidence/LLVM-078t/run.sh` **14/14 PASS、RUN_EXIT=0**；`run.sh --inject` **RUN_EXIT=0**（注入 `Data64bitsDirective="\t.quad\t"` ⇒ 2 生成侧断言 FAIL ⇒ `cp`+md5 还原 ⇒ `ninja llc` 重建 ⇒ 回绿；md5 `f969584f8e79e94111023f7fd5263670` 对账一致）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{MCTargetDesc/DADAOMCAsmInfo.cpp.patch,AsmParser/DADAOAsmParser.cpp.patch}`、`components/llvm-project/changelog.md`、`.tao/knowledge/contract-asm.md`、`tools/testcases/validate_mc_vectors.py`、`tests/**` 14 文件（`lit/CodeGen/DADAO/br-jt.ll`；`lit/MC/DADAO/{README-m4.md,dd-reject.s,m4-directive-reject.s,m6-callconv.s,m6-data-narrow-reject.s,m6-ldst-symbol.s,p2align-degrees.s,p2align-rodata.s,p2align-text.s,rela-addend.s,rela.s,set-symbol.s}`；`tests/scripts/bootrom.S`），本任务书。`series` 仍 71（无新增文件）。
**验收结果**：①`llc` 产物 GAS 名=0、`.align`=0，`.dd.b08/.w16/.t32/.o64`=1/1/1/4，`i128`=2×`.dd.o64`，`.p2align`=5（min 模块，rc=0）；②`llvm-mc` rc：`.byte/.short/.long/.quad/.word/.octa/.align` **全 rc=1（拒）**；`.dd.b08/.w16/.t32/.o64/.p2align` **全 rc=0**；③E2E：`check-lit` **89/89**、`test-codegen` **15/15**、`test-elf` **5/5**、`test-semihost` **10/10** 全 EXIT=0；全局数据 C→lld→QEMU 退出码 0（O0/O2）、`.dd.*` 大端字节独立 oracle 相等；④门控 `build-mc`/`check`/`check-patch-tree`/`check-lit` 全 EXIT=0（lit 89 = 改前 `LLVM-077t-gate-check-lit.log` 89，**不下降**）；`spec|contracts` 交集空、无残留。
**新发现/坑**：（1）**target parser 先于通用分派**（`AsmParser.cpp:1941` vs L1958）是「目标级拒绝」的关键，无需碰 `llvm/lib/MC/**`；（2）改 `.dd.*` 后 `m6-data-narrow-reject.s` 的诊断从通用 `parseDirectiveValue` 文本（`a 1/2/4-byte data field`）切到 DADAO `parseDDDirective` 文本，故 NARROW 断言收敛为语义锚 `relocatable operand in`；（3）在组件源树 `commit --amend` 改 commit hash 会触发 LLVM `VCSRevision.h` 重生成（+重链）——属预期。
**遗留问题**：**超出用户裁定 4 名集合**的其他 LLVM 内建数据指导符（`.2byte/.4byte/.8byte/.value/.int/.dc.b/.single/.double`）仍被通用 parser 受理（实测 rc=0）——未在裁定范围内，**未动**；建议后续任务按 `Toolchain-01 §7` 口径一并收口（登记建议）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查方式**：全局 `subagent_depth=1`，engineer 自主逐行审查（无嵌套子代理）。范围：2 个 DADAO 源补丁（`DADAOMCAsmInfo.cpp`、`DADAOAsmParser.cpp`）、14 个 `tests/**`、`tools/testcases/validate_mc_vectors.py`、`.tao/knowledge/contract-asm.md §11`、`components/llvm-project/changelog.md`、证据脚本 `run.sh`；对照任务书验收 1–9 与硬约束逐条核验，并以真实执行（llc/llvm-mc/lit/lld/qemu/门控）验证。

**逐行审查要点与判决**：
- **生成侧**：`Data{8,16,32,64}bitsDirective` 字段名与默认值（`MCAsmInfo.h:245-248`）逐一核对，串格式 `"\t.dd.*\t"` 与默认 `"\t.byte\t"` 同构；不改构造签名。**判决：正确**。
- **受理侧**：`DADAOAsmParser::parseDirective` 顺序为 `.octa` → 4 个 GAS 数据名 → `.align` → `.dd.*` 分发；全部 `Error()` 早返回，不影响后续 `.dd.*`；`Twine` 拼接经编译验证（`-Werror` 未触发，仅既有无关 warning）。**判决：正确**。
- **可达 FAIL**：证据脚本每条断言均有可达 FAIL 路径——生成侧由 `--inject` 实测 FAIL（gas=4）；受理侧拒断言在改前实测 rc=0（可 FAIL）；字节 oracle 为独立 Python 大端派生（非恒真）。**判决：通过**。

| finding | 处置 | 说明 | 复验证据 |
|---------|------|------|---------|
| F1 `.word` 维持 `unknown directive`（非 "unsupported"）而非显式拒绝 | ❌不修 | 用户裁定仅要求「拒」；`llvm-mc` 对 `.word` **本就 rc≠0**（LLVM 无此内建）；且 `validate_mc_vectors.py` oracle 与 `m4-directive-reject.s` 期望为 `unknown`，显式拒绝会无谓扩大改动面 | 实测 `.word 1` rc=1；`validate_mc_vectors` 78 向量 0 错 |
| F2 `.align` 拒绝是否会误伤既有合法书写 | ✅已核 | 全仓 `grep '\.align\b'`（tests/tools）0 命中；`llc` 只发 `.p2align` | evidence `llc_gen_dd_only` align=0；`make check` EXIT=0 |
| F3 换 `.dd.*` 后 `m6-data-narrow-reject.s` 诊断文本变化 | ✅已修 | RUN 行改 `.dd.b08/w16/t32 ext` 以保留「窄字段可重定位拒」语义；NARROW 断言由实现文本收敛为语义锚 `relocatable operand in`（与 `dd-reject.s`/`m4-directive-reject.s` 一致） | `check-lit` 89/89 |
| F4 组件源树 `commit --amend` 改 hash 触发 `VCSRevision.h` 重生成 | ✅已核（预期） | amend 为补丁导出（E1）必需；重生成只影响少量 TU + 重链，行为无关 | `build-mc` 二次 EXIT=0；`check-source-state` OK |
| F5 其他 LLVM 内建数据指导符（`.2byte/.4byte/.8byte/.value/.int/.dc.b/.single/.double`）仍被受理 | ⏸延后 | **超出用户裁定 4 名集合**，未授权扩大；登记「遗留问题」+ 建议后续任务 | 实测 rc=0（见完成区） |

**判决**：所有 finding 已处置（F3 已修并复验，F1/F5 有据不修/延后，F2/F4 核实无问题）；任务状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑 `run.sh`（functional + inject 模式）+ 自行构造 `.ll`/逐个 `llvm-mc` 测试 + 逐条 `make` 门控 + 独立 Embench 扫描 + 独立反例注入（不同 surface：放开 `.byte` 受理）。全程禁 `git checkout/restore/stash`，cp+md5 还原并逐项对账。临时目录 `/tmp/opencode/LLVM-078t-review/`。

**重跑记录**（逐条真实输出/退出码）：

| 检查 | 期望 | 实际（reviewer 独立跑） | 备注 |
|------|------|------------------------|------|
| 生成侧 `llc` own `.ll` (i8/i16/i32/i64/ptr/i128/arr) | GAS=0, .align=0, .dd.*全现, i128=2×.dd.o64, .p2align≥1 | GAS=0, .align=0, .dd.b08=1, .dd.w16=4, .dd.t32=1, .dd.o64=4, .p2align=6, i128=2×dd.o64, llc rc=0 | 与 engineer 1/1/1/4 差异来自测试 .ll 多了 `[3 x i16]` 数组；关键断言（gas=0, .align=0, i128=2）一致 |
| `.byte` → rc | rc≠0 | rc=1, msg=`unsupported directive '.byte' (GAS data directive)` | |
| `.short` → rc | rc≠0 | rc=1, msg=`unsupported directive '.short' (GAS data directive)` | |
| `.long` → rc | rc≠0 | rc=1, msg=`unsupported directive '.long' (GAS data directive)` | |
| `.quad` → rc | rc≠0 | rc=1, msg=`unsupported directive '.quad' (GAS data directive)` | |
| `.word` → rc | rc≠0 | rc=1, msg=`unknown directive .word 1` | LLVM 无内建 `.word`；F1 有据不修 |
| `.octa` → rc | rc≠0 | rc=1, msg=`unsupported directive '.octa' (GAS 16-byte octa)` | |
| `.align 3` → rc | rc≠0 | rc=1, msg=`unsupported directive '.align' (byte-count semantics)` | |
| `.dd.b08 1` → rc | rc=0 | rc=0 | |
| `.dd.w16 1` → rc | rc=0 | rc=0 | |
| `.dd.t32 1` → rc | rc=0 | rc=0 | |
| `.dd.o64 1` → rc | rc=0 | rc=0 | |
| `.p2align 3` → rc | rc=0 | rc=0 | |
| `git diff \| grep llvm/lib/MC/` (worktree) | 0 hits | 0 hits, rc=1 | |
| `getTargetParser().parseDirective(ID)` 行号 | L1941（先于 generic dispatch） | L1941 confirmed; generic `switch (DirKind)` at L1961 | |
| `grep .byte/.short/… tests/ tools/` | 仅拒测文件 + 非汇编含义 | 见 item 4 分析 | |
| `make check-patch-tree` | rc=0 | rc=0, 3 components, 109 patches OK | |
| `make build-mc` | rc=0 | rc=0 | |
| `make check` | rc=0 | rc=0, 89 discovered/89 passed | |
| `make check-lit` | rc=0, 不下降 | rc=0, 89/89 (= LLVM-077t 89) | |
| `make test-codegen` | rc=0 | rc=0, 15/15 | |
| `make test-elf` | rc=0 | rc=0, 5/5 | |
| `make test-semihost` | rc=0 | rc=0, 10/10 | |
| Embench -O0 | 19/19 | 19/19（independent sweep） | |
| Embench -O2 | 19/19 | 19/19（independent sweep） | |
| `run.sh` (functional) | RUN_EXIT=0 | RUN_EXIT=0, 14/14 PASS | |
| `spec\|contracts` intersection | 0 hits | 0 hits | |
| `series` count | 71 | 71 | |

**target-scoped 核实**：`DADAOAsmParser::parseDirective`（AsmParser.cpp:1163）在 `getTargetParser().parseDirective(ID)`（AsmParser.cpp:1941）中被调用，先于通用 `switch (DirKind)`（L1961）。`.byte/.short/.long/.quad` → `Error("unsupported directive...")` 早返回 shadow 通用 DK_BYTE 等 case。`llvm/lib/MC/**` 未修改。

**跟改面核实**：`grep tests/ tools/` 命中全部为（a）拒测文件（dd-reject.s、m4-directive-reject.s 使用 `%not` + FileCheck EXPECT 拒绝）、（b）文档（README-m4.md）、（c）validate_mc_vectors.py `GAS_DIRECTIVES` 元组（oracle 分类为 unsupported）。无真需求使用 GAS 名。`encoding.word` 为向量 schema 字段名，非汇编指令。

**脚本审计**：run.sh 14 条断言均有可达 FAIL 路径——gen-side 由注入实测 FAIL（gas=4）；mc-reject/mc-accept 由反例实测 FAIL（rc=0 vs 期望≠0）；byte oracle 为独立 Python 大端派生；gdata e2e 退出码独立。脚本无 `tee`，退出码捕获无管道截断。`run.sh --inject` 模式：注入 `Data64bitsDirective="\t.quad\t"` → 2 gen-side 断言 FAIL → md5 `f969584f8e79e94111023f7fd5263670` 还原一致 → 重建回绿。

**独立反例注入**（surface 不同于 engineer 的 `.quad` gen-side）：
- 注入：修改 `DADAOAsmParser.cpp` 的 `.byte` 拒绝条件 → `ID == ".byteNOSUCH"` → `.byte` 不再被拦截（放开了一个 GAS 名）。
- `git diff --name-only` 确认注入非空（1 path）；md5 pre-inject=`d96d6155b58f7ab34bf4edeea4df9c33`。
- rebuild（setsid nohup，exit=0）→ `run.sh`：`llvm_mc_reject_gas` **FAIL**（`.byte 1 rc=0`，被接受）+ `check_patch_tree` **FAIL**（rc=2，patch-tree 检测到源树漂移）+ `make_check` **FAIL**（rc=2）；**RUN_EXIT=1** ✓。
- `cp` 还原 → md5 `d96d6155...` = pre-inject ✓ → rebuild（exit=0）→ `run.sh`：14/14 PASS，**RUN_EXIT=0** ✓。
- 工作区快照对账：`git status --porcelain -uall` pre==post ✓；4 个目标文件 md5 pre==post ✓。

**遗留核实**（item 8）：独立测试 `.2byte/.4byte/.8byte/.value/.int/.dc.b/.single/.double` → 全部 rc=0（仍被 llvm-mc 受理）。不在用户裁定 4 名集合内，未动。engineer 遗留登记属实。

**约束核验**：
- ✅ 生成侧只发 `.dd.*`（gas=0, .align=0）
- ✅ 受理侧拒 7 名（全 rc=1）、收 `.dd.*`+`.p2align`（全 rc=0）
- ✅ `llvm/lib/MC/**` 未修改（target-scoped 拒绝）
- ✅ `spec|contracts` 交集空
- ✅ 不回归：check-lit 89/89（=改前 89）、test-codegen 15/15、test-elf 5/5、test-semihost 10/10、Embench 19/19×2
- ✅ 证据脚本14/14 + 注入 FAIL + md5还原 + 回绿
- ✅ 补丁纪律：series=71、一文件一补丁、无残留
- ✅ 工作区快照对账一致

**判决：Accepted**
