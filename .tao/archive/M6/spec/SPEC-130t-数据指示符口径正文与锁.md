# SPEC-130t: 数据指示符口径（正文 + 锁）【`ISS-181` 拆分-①】

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-129t`（`Toolchain-01` 旧口径消除 + 锁同步，`已验证`）；无硬前置
**状态**：已验证

> **覆盖缺口**：**`ISS-181`** 的**规范正文 + 锁**部分。**说明（拆分）**：`ISS-181` 同时含「规范正文口径」与「工具链实现 + 用例跟改」，体量大且跨模块（spec 只读册 + llvm 后端 + tests）⇒ 按 Spec-first 拆为 **`SPEC-130t`（正文 + 锁，本文件）** + **`LLVM-078t`（工具链生成侧/受理侧 + 用例跟改）**，后者依赖本任务。

## 用户裁定（2026-10-10，经主会话转述的原话/结论，原样落纸）

> 用户 **2026-10-10 裁定：4 条缺口（`ISS-182` / `ISS-185` / `ISS-186` / `ISS-181`）全部纳入 M6**（「10 点前完不成 ⇒ 全加、跑一晚上」）。其中 **`ISS-181`（数据指示符口径）** 的裁定为：
> - **① 只留 `.dd.b08` / `.dd.w16` / `.dd.t32` / `.dd.o64`**（`.byte` / `.short` / `.long` / `.quad` / `.word` / `.octa` **全部禁**）。
> - **② 两侧一致**：`llc` **只生成** `.dd.*`，`llvm-mc` **拒绝** GAS 名（**受理侧可行性**归 `LLVM-078t` 评估）。
> - **③ 删 `.align`，只留 `.p2align`**（实测 `.align N` 是**字节数**语义、与 GAS 的 `2^N` 冲突）。
> - **④ 不立 ADR**：改 **v5 侧 `spec/Toolchain-01 §7`** + **`.tao/knowledge/contract-asm.md` 正文** + **同步 `manifests/spec-readonly.lock.toml` 的 `sha256`**；**不动上游 `DADAO-11`**（确需 ⇒ **停下报告**）。
> - **⑤ `.dd.128` 暂不加**（用户保留；如加为小改）。
> - **⑥ 跟改面**：`tests/**`（lit CHECK 行、e2e `.s`、`tests/scripts/*.s`）与 `components/llvm-project/patches/**` 内受影响的 DADAO 侧 directive 串（`DADAOMCAsmInfo`）——**归 `LLVM-078t`**。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现状**：`Toolchain-01 §7`（指导符）**只列** 4 条 `.dd.*`（Knuth/MMIX 长度定义），并注明「MUST NOT 使用 GAS 的 `.word`/`.octa`」，但**未显式禁** `.byte/.short/.long/.quad`，也**未涉 `.align`**。而实现侧 `DADAOMCAsmInfo` **未覆盖** data directive 串 ⇒ 继承 `MCAsmInfo` 默认 ⇒ `llc` 生成侧发 `.byte/.short/.long/.quad`（与 §7 的规范名不一致）；受理侧 `llvm-mc` 两套名字当前**都能汇编**（各 rc=0）。`.align N` 实测为**字节数**语义（与 GAS 的 `2^N` 冲突）。
- **目的**：把「DADAO 数据指示符口径」在**规范正文**上收口到**单一真源**（只 `.dd.*`；删 `.align` 只留 `.p2align`），供 `LLVM-078t` 实现侧对齐。
- **性质 = 规范口径收口（`spec` 模块）**；**不含实现**（实现归 `LLVM-078t`）。

**证据指针**：`.tao/knowledge/contract-asm.md`（当前 §指导符 行）、`spec/Toolchain-01-汇编语言.md §7`、`spec/DADAO-11-AEE-应用程序运行环境.md §汇编兼容性`（**只读引用，不改**）；issue `ISS-181`。

## 接口规范

- **输入**：
  - `spec/Toolchain-01-汇编语言.md §7`（**只读册，需用户授权**——授权见上「用户裁定」段，**须原样留档**）。
  - `.tao/knowledge/contract-asm.md`（v5 投影层正文）。
  - `manifests/spec-readonly.lock.toml`（`Toolchain-01` 的 `sha256` 锁）。
  - `spec/Process-06-spec目录保护规范.md`（只读册修改流程 + 锁同步要求）。
- **输出**：
  1. **`spec/Toolchain-01 §7`** 正文改对：① 只保留 4 条 `.dd.*` 为**唯一** DADAO 数据指示符；② 显式声明 **`.byte/.short/.long/.quad/.word/.octa` 全部禁**（`.word`/`.octa` 与 GAS 语义差异的既有注保留/加强）；③ **删 `.align`，只留 `.p2align`**（写清 `.p2align N` = 2^N 对齐）；④ `.dd.128` **不加**（可留一句「暂不引入」）。**不写死计数**。
  2. **`.tao/knowledge/contract-asm.md` 正文**：与 §7 **同口径**同步（只 `.dd.*` + 禁 GAS 名 + 删 `.align` 留 `.p2align`）。
  3. **`manifests/spec-readonly.lock.toml`**：`spec/Toolchain-01-汇编语言.md` 的 `sha256` **同步更新**（同一变更内），并在锁文件内注释本次变更理由。
- **约束**：
  - **不动上游 `DADAO-11`**（`spec/DADAO-11-*.md` 一字不改；确需 ⇒ **停下报告**）。
  - **不立 ADR**（用户裁定 ④）；本任务只改正文口径 + 锁。
  - **不改实现**（`components/**` 交集为空）；**不改 `tests/**`**（跟改归 `LLVM-078t`）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-130t/`；禁仓库内临时文件。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **用户授权留档**：`spec/Toolchain-01` 的修改授权（用户 2026-10-10 裁定，见上）须在完成区**原样留档**（子会话问答对父会话不可见，`lessons §7.3`）；未留授权 ⇒ reviewer 判 `Needs Revision`。
- **一键证据脚本** `.work/evidence/SPEC-130t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**（如改错锁 `sha256` ⇒ `make check-spec-readonly` FAIL；或把 §7 口径改回 GAS 名 ⇒ 一致性检查 FAIL）；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**。
- 复杂命令输出留 `.work/log/spec/SPEC-130t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **规范正文口径收口**：`spec/Toolchain-01 §7` 明确「唯一数据指示符 = `.dd.b08/.dd.w16/.dd.t32/.dd.o64`；`.byte/.short/.long/.quad/.word/.octa` 全部禁；`.align` 删、只留 `.p2align`（2^N）」；`.tao/knowledge/contract-asm.md` 同口径（给 `grep`/摘录证据）。
2. **锁同步**：`manifests/spec-readonly.lock.toml` 中 `spec/Toolchain-01-汇编语言.md` 的 `sha256` = **改后实测值**；`make check-spec-readonly`（或对应门控）EXIT=0（给真实命令 + rc）。
3. **不动上游**：`git -c core.quotepath=false diff --name-only | grep -E '^spec/DADAO-11'` → 无输出；`spec/` 改动**仅** `Toolchain-01` 一册；`components/**`/`tests/**` 交集为空。
4. **无 ADR**：本任务不新增/不修订 ADR（给 `git status` 证据）。
5. **一键证据脚本**：`.work/evidence/SPEC-130t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（`sha256` 写错 ⇒ 门控 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：`.work/evidence/SPEC-130t/run.sh` RUN_EXIT=0（C1–C6 全 PASS）；`make check-spec-readonly` rc=0；`make check-asm-prose`/`check-spec-codeblocks`/`check-rule-refs`/`check-no-residue`/`check-spec-drift`/`check-index-blobs`/`check-asm-list`/`check-asm-list-drift` 均 rc=0。
**修改文件**：`spec/Toolchain-01-汇编语言.md`（§7 重写为 §7.1 数据指示符唯一集合 + §7.2 对齐指示符）、`.tao/knowledge/contract-asm.md`（§7 同口径 + 删过时「尚未实现」）、`manifests/spec-readonly.lock.toml`（Toolchain-01 `sha256` 同步 + 变更注释）；新增（未跟踪）：`.work/evidence/SPEC-130t/run.sh`、`.work/log/spec/SPEC-130t-*.log`。
**验收结果**：
- **锁同步**：`sha256 = 3d129ba8c7391aea291059d788b015a6fb9a3f965728434d2530eeb144aa7a4a`（实测）；`make check-spec-readonly` → `21 read-only spec volume(s) OK` rc=0。
- **口径**：§7 表格 `.dd.*` 行数（现场统计，派生自正文）= 4；`.byte/.short/.long/.quad/.word/.octa` 禁用、`.p2align`、`.dd.128` 暂不引入均在两处 §7 命中；旧「v5 汇编器尚未实现（报 `unknown directive`）」在 §7 区域内 grep 为空（已删）。
- **范围**：`git -c core.quotepath=false status --porcelain -uall` 仅 3 个预期文件；`spec/` 改动集 = {`spec/Toolchain-01-汇编语言.md`}；`spec/DADAO-11` 命中 0；`components/`+`tests/` 命中 0；`.tao/adr/` 命中 0。
- **注入自检**：锁 `sha256` 置 0 ⇒ `make check-spec-readonly` rc=2（`MISMATCH spec/Toolchain-01…`）⇒ `cp` 还原 md5 一致（`7078f2a915e3448098b87a011ce5edc0`）⇒ rc=0。
**用户授权留档**（2026-10-10，原话/结论）：「用户 2026-10-10 裁定：4 条缺口（`ISS-182` / `ISS-185` / `ISS-186` / `ISS-181`）全部纳入 M6。其中 `ISS-181`（数据指示符口径）：① 只留 `.dd.b08`/`.dd.w16`/`.dd.t32`/`.dd.o64`（`.byte`/`.short`/`.long`/`.quad`/`.word`/`.octa` 全部禁）；② 两侧一致（`llc` 只生成 `.dd.*`，`llvm-mc` 拒绝 GAS 名）；③ 删 `.align`，只留 `.p2align`（实测 `.align N` 是字节数语义，与 GAS 的 `2^N` 冲突）；④ 不立 ADR：改 v5 侧 `spec/Toolchain-01 §7` + `.tao/knowledge/contract-asm.md` 正文 + 同步 `manifests/spec-readonly.lock.toml` 的 `sha256`；不动上游 `DADAO-11`（确需 ⇒ 停下报告）；⑤ `.dd.128` 暂不加（用户保留；如加为小改）；⑥ 跟改面（`tests/**`、`components/llvm-project/patches/**`）归 `LLVM-078t`。」
**新发现/坑**：
- llvm-mc 现状探针（`.work/log/spec/SPEC-130t-llvm-mc-probe.log`）：`.dd.b08/w16/t32/o64` 已受理（各 rc=0）；**`.byte/.short/.long/.quad` 当前仍受理（各 rc=0）**——须由 `LLVM-078t` 改为拒绝；`.word`/`.octa` 已被拒；`.dd.128` 报 unknown。
- `.align 8` 实测对齐到 **8 字节**（1B+`.align 8`+1B ⇒ `.text` 9 字节），确认**字节数**语义；`.align 3` 报 `alignment must be a power of 2`；`.p2align 3` 对齐 8 字节 rc=0。
- 陈旧项（转 `LLVM-078t`）：`.tao/knowledge/contract-asm.md §11` 状态表仍写「`.dd.*` 指导符 | 未实现」（该表为 2026-09-23 快照）；实测已受理 ⇒ 该行已陈旧。本任务范围仅 §7（不含实现），故未动该表。
**遗留问题**：无。§11 状态表刷新已登记为 `LLVM-078t` 跟改项（见「新发现/坑」）。

## 审阅记录

#### 第 1 轮 engineer 自审
**审查范围**：`spec/Toolchain-01 §7`、`.tao/knowledge/contract-asm.md §7`、锁注释、`.work/evidence/SPEC-130t/run.sh` 全文逐行。
**逐行审查发现与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 计数写死风险（SPEC-129t 同源回归）：正文不得硬编码「4 条」 | ✅已修 | 两处 §7 均改以表格/列举定义「唯一集合」，无基数词 | grep §7 区域无「4 条」 |
| F2 §6 伪指令展开的「尚未实现」属实（另一缺口），不得误删 | ✅确认 | 仅删 §7 处旧口径；§6 完整保留 | run.sh C2 限定 §7 区域断言 absent → PASS |
| F3 run.sh 初版整册 grep「尚未实现」误伤 §6 | ✅已修 | 断言改为仅在 §7 区域内 grep | 修前 FAIL（C2.spec-no-outdated-status）→ 修后 PASS |
| F4 run.sh `git status` 未关 quotepath ⇒ spec/ 路径带引号、C4 误判 | ✅已修 | 加 `-c core.quotepath=false` | 修前 C4 FAIL → 修后 PASS |
| F5 run.sh 注入正则未容忍 `group=` 行 ⇒ 0 匹配、**空注入假绿** | ✅已修 | 改为按 `[[spec]]` 切块定位 | 修前注入后 rc=0（假绿）→ 修后 rc=2（MISMATCH） |
| F6 「注入后 git diff 非空」断言被任务自身改动掩盖 | ✅已修 | 改为断言 bogus `sha256` 实际落盘 | C6.injection-effective PASS |
| F7 `contract-asm §11` 状态表「`.dd.*` 未实现」陈旧 | ⏸延后 | — | 归 `LLVM-078t`（本任务不含实现、范围仅 §7）；已在完成区披露 |

**判决**：全部 finding 已修（F1–F6）或延后登记（F7，附理由与承接任务），无未修阻断项；改变的文件与「修改文件」对账一致。独立验证由 `/complete` 的 `reviewer` 承担。

#### 第 1 轮 reviewer 验收

**重跑证据脚本**（独立执行 `.work/evidence/SPEC-130t/run.sh`）：
```
C1.lock-sha256-matches-file PASS (sha256=3d129ba8…aa7a4a)
C2 全部 22 项 PASS（.dd.b08/w16/t32/o64 各 present；.byte/.short/.long/.quad/.word/.octa 各 banned；.p2align/.align/.dd.128 均命中；旧「尚未实现」absent）
C3.check-spec-readonly PASS (rc=0, 21 volumes OK)
C4 改动范围 PASS（spec/ 仅 Toolchain-01；DADAO-11=0；components/tests=0；ADR=0）
C5.check-no-residue PASS (rc=0)
C6 注入自检 PASS（sha256 置 0 ⇒ rc=2 MISMATCH ⇒ cp 还原 md5 一致 ⇒ rc=0 回绿）
RUN_EXIT=0
```

**独立注入反例**（reviewer 自行执行，不依赖脚本 C6）：
- 备份 `manifests/spec-readonly.lock.toml` → `/tmp/opencode/SPEC-130t-review/lock.bak`，md5=`7078f2a915e3448098b87a011ce5edc0`
- 注入 sha256=`aaa…aaa`（64 个 a）→ `make check-spec-readonly` rc=2（`MISMATCH spec/Toolchain-01…`）
- `cp` 还原 → md5=`7078f2a915e3448098b87a011ce5edc0`（与备份一致）→ rc=0 回绿

**约束核验**：
| 约束 | 结果 |
|---|---|
| 正文口径与裁定一致（只 .dd.*；禁 GAS 名；删 .align 留 .p2align；.dd.128 暂不加） | ✅ spec §7 + contract §7 逐条命中 |
| 旧「v5 汇编器尚未实现」已删（§7 区域） | ✅ grep absent |
| 锁 sha256 = 实测值 | ✅ `3d129ba8…aa7a4a` 逐字相等 |
| `make check-spec-readonly` rc=0 | ✅ 21 volumes OK |
| 不动上游 DADAO-11 | ✅ 0 命中 |
| spec/ 仅改 Toolchain-01 | ✅ |
| components/tests 无交集 | ✅ |
| 无 ADR 改动 | ✅ |
| 无残留（_tmp/_orig/_rej） | ✅ |

**判决：Accepted** — C1–C6 全 PASS，注入→FAIL→还原→回绿验证通过，约束逐条守住。
