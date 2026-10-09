# SPEC-126t: 系统调用/半托管返回寄存器统一 `rd8`

**模块**：spec
**项目里程碑**：M6
**依赖**：`SPEC-124t`（函数返回 `rd8` 契约已收口；本任务与其它改 `spec/`/锁任务**串行**）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户裁定（原话）

> **「统一为 rd8」**（系统调用与函数 ABI 统一；此前 `rd31`）。**不立 ADR**（用户既定）。

## 变更边界（两个独立变更，**分别验收**）

1. **「函数返回」改动**（已完成）：`SPEC-124t`——函数返回寄存器 `rd31/rb31/rf31 → rd8/rb8/rf8`、声明序递增、每 bank `K=8`。**不在本任务范围**。
2. **「系统调用返回」改动**（本任务）：系统调用（`DADAO-22`/`DADAO-23`/`DADAO-21 §系统调用规范`）与半托管（`Machine-01 §5`）的**服务返回**寄存器 `rd31 → rd8`。两者**独立**、**分别验收**；不得把 1 的结论当作 2 的依据、亦不得因 1 已改而跳过 2 的逐条核。

## 接口规范

- **输入**：
  - `.tao/knowledge/contract-see.md §5`（SBI 调用约定：标量返回 `rd31`）、`.tao/knowledge/contract-semihosting.md §2/§4`（semihosting 返回 `rd31`）。
  - `spec/DADAO-21-ABI-应用程序二进制接口.md §系统调用规范`（`返回值放在 RD31`）。
  - `spec/DADAO-22-SBI-主管系统二进制接口.md`（`rd31 = result/version/base/…` 返回表 + 代码示例，**十余处**）。
  - `spec/DADAO-23-HBI-超管系统二进制接口.md`（`HBI_GET_VERSION → rd31 = version`）。
  - `spec/Machine-01-测试机运行环境.md §5.2/§5.4`（semihosting 返回 `rd31`）。
  - `manifests/spec-readonly.lock.toml`（`DADAO-21/22/23`、`Machine-01` 的 `sha256`）。
  - 参考：`contract-abi.md §4.4/§4.6`（返回区 `rd8–rd15`，`SPEC-124t` 落点）。
- **输出**：
  1. 上述 **4 册 `spec/`** 正文中，**「调用/服务返回」用途**的返回寄存器 `rd31` 统一为 **`rd8`**；**逐条分类**（见约束）。
  2. `.tao/knowledge/contract-see.md §5`、`.tao/knowledge/contract-semihosting.md §2/§4` 同步返回寄存器 `rd8`。
  3. `manifests/spec-readonly.lock.toml` 中**被改册**的 `sha256` **同变更内**更新（改毕 `sha256sum` 实测）。
- **约束**：
  - **只改「调用/服务返回」用途**：改 = `DADAO-22` 各返回表中 `rd31 = result/version/base/ppn/ch/…`、`DADAO-23` `rd31 = version`、`DADAO-21 §系统调用规范`「返回值放在 RD31」、`Machine-01 §5.2/§5.4` semihosting 返回、`contract-see §5`/`contract-semihosting §2/§4` 返回寄存器。**不改**：`rd15 = nr`（系统调用号**入参**）、`rd16 = cfx/idx/len`、`rb16` 等**入参**、参数寄存器区（`rd16–rd31`/`rb16–rb31`）、寄存器角色表、指令语义（`cfx2rd … rd31` 中 `rd31` 若为**目标暂存/返回槽**须按用途判定，见下）。
  - **`rd15 = nr` 与返回区 `rd8–rd15` 重叠 —— 判断：需要澄清**：`rd15` 在**系统调用域**是调用号**入参**（`rd15 = nr`，**不改**），在**函数 ABI 域**是返回区第 8 槽（`rd8–rd15`）；二者分属**不同调用域**、不得混用。本任务**只改返回寄存器为 `rd8`、不改 `rd15 = nr` 约定本身**。若须在册内加**最小**区分说明（不得改变既有入参约定），须在完成区**逐条披露**其文本与理由；**勿擅自改动册**。
  - **逐条分类 + 修一类**：全仓 grep `rd31`（必要时 `rb31`）命中**逐条**判定「`调用/服务返回` → 改 `rd8`」或「非返回 → 不改（给理由）」；分类表入完成区，**计数由脚本现场统计、不写死**（`ISS-148` 教训）。
  - **不含实现**：`components/**`/`tools/**`/`tests/**` 归 `QEMU-055t`/`TESTCASES-041t`，本任务**`git diff` 与实现侧交集为空**。
  - **门控全绿**：`make check`（含 `check-spec-refs`/`check-spec-readonly`/`check-contracts`）EXIT=0。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-126t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-126t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/spec/SPEC-126t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **逐条分类表**：完成区给「改 / 不改」逐条分类（`文件:行 + 用途 + 理由`），计数脚本现场统计（不写死）。
2. **返回寄存器统一**：4 册中被改条目的服务返回寄存器 == `rd8`（给 `grep`/摘录真实输出）；`rd15 = nr` 等**入参**约定**逐条未变**。
3. **contracts 侧同步**：`contract-see §5` / `contract-semihosting §2/§4` 返回寄存器 == `rd8`。
4. **锁同步**：被改册 `sha256` 改毕实测更新；`make check-spec-readonly` EXIT=0；**未被改册** `sha256` **逐条未变**（`git diff` 中既有 `sha256` 行 `-`/`+` 计数 = 0）。
5. **门控**：`make check` EXIT=0（含 `check-spec-refs`/`check-spec-readonly`/`check-contracts`）。
6. **一键证据脚本**：`.work/evidence/SPEC-126t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如把某返回 `rd8` 还原为 `rd31` ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`DADAO-21/22/23`、`Machine-01`、`manifests/spec-readonly.lock.toml`、`contract-see.md`、`contract-semihosting.md` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：`make check` EXIT=0（含 `check-spec-readonly` 21 册 OK、`check-spec-drift` PASS、`check-patch-tree` 92 patches OK）；`make check-spec-refs` EXIT=0（790 引用 / 0 失败）；`make check-patch-tree` EXIT=0；证据脚本 `RUN_EXIT=0`（全部断言 PASS，含注入自检）。真实输出见 `.work/log/spec/SPEC-126t-*.log`。
**修改文件**：① `spec/DADAO-22-SBI-主管系统二进制接口.md`；② `spec/DADAO-21-ABI-应用程序二进制接口.md`；③ `spec/DADAO-23-HBI-超管系统二进制接口.md`；④ `spec/Machine-01-测试机运行环境.md`；⑤ `.tao/knowledge/contract-see.md`；⑥ `.tao/knowledge/contract-semihosting.md`；⑦ `manifests/spec-readonly.lock.toml`；证据脚本 `.work/evidence/SPEC-126t/run.sh`（`.work/` 已 gitignore，不入库）。`git status --porcelain -uall` 仅上述 7 个已跟踪文件（+本任务书），无 `*_tmp*`/`*.orig`/`*.rej`。
**验收结果**：门控 EXIT=0；注入自检真实输出——DADAO-22 一处 `rd8 = result`→`rd31 = result`（md5 变）⇒ `param_inv` 断言 FAIL（total=2≠param=1）⇒ `cp` 还原、md5 与备份相等 ⇒ 回绿。见 `.work/log/spec/SPEC-126t-evidence.log`。
**新发现/坑（逐条分类表；计数脚本现场统计、不写死；明细 `.work/log/spec/SPEC-126t-classification.md`）**：

| 命中 | 用途 | 改/不改 | 依据 |
|------|------|--------|------|
| DADAO-22 返回表/实现示例/注释 rd31（非参数区全部） | 服务返回 | **改 rd8** | SBI 服务返回 |
| DADAO-22 L31 `rd16-rd31`/`rb16-rb31` | 参数寄存器区 | 不改 | 入参 |
| DADAO-21 §系统调用规范 `返回值放在 RD31` | 服务返回 | **改 RD8** | syscall 返回 |
| DADAO-21 `RD16 - RD31` / `RD15` | 参数区 / 调用号入参 | 不改 | `rd15 = nr` |
| DADAO-23 `rd31 = version` | 服务返回 | **改 rd8** | HBI 返回 |
| Machine-01 §5.2/§5.4 返回 rd31；§5.2 指针返回 rb31 | 服务返回 | **改 rd8 / rb8** | semihosting 返回；与函数 ABI 一致 |
| Machine-01 §5.2 `rd16–rd31` / `rb16–rb31` | 参数区 | 不改 | 入参 |
| contract-see §5 `rd31`/`rb31`；contract-semihosting §2/§4/附录 `rd31` | 服务返回 | **改 rd8/rb8；rd8** | 同步 |
| contract-abi §5「返回值 RD31」、Toolchain-01 `xnor.o …rd31`、ADR/lessons/project_M3 | 描述 / 暂存 / 历史 | 不改 | 未列入本任务文件 / 非返回 / 历史记录 |

**rd15 域澄清（约束）**：`rd15` 在系统调用域是「调用号入参」（不改），在函数 ABI 域是返回区第 8 槽（`rd8–rd15`）；分属不同调用域，本次只改返回、未动 `rd15 = nr`；未在册内加文字（遵「勿擅改册」）。
**遗留问题**：① `contract-abi.md:285`「系统调用规范（…返回值 RD31）」现陈旧——该文件**未列入本任务范围**（`只修改任务文件列出的文件`），故未改，建议 `/complete` 或后续同步；② `project_M3-codegen-choices.md:525`、`lessons.md:425` 的「系统调用/半托管仍 rd31」为 `SPEC-124t` 时点历史记录（不追溯重写）；③ 实现/向量侧涟漪归 `QEMU-055t`/`TESTCASES-041t`（本任务与实现侧 `git diff` 交集为空）。

### 完成区补充（第 2 轮 engineer：同类残留收口）

- **触发**：上一轮遗留① `contract-abi.md:285`「系统调用规范（…返回值 RD31）」。原任务 grep 为**小写** `\brd31\b|\brb31\b|\brf31\b`，该行用**大写** `RD31`，故机械扫描漏网；本轮补**大小写不敏感**重扫（`grep -rniE`）。
- **改**：`contract-abi.md:285` §5 边界索引行「`trap`、RD15 调用号、返回值 RD31」→「返回值 **RD8**」（`RD15 调用号`入参**不动**）。`.tao/knowledge/contract-*.md` 非 `spec/` 册、**无锁** ⇒ 锁无需同步。
- **修一类分类（大小写不敏感全扫；小写 49 行 + 仅大写新增 6 行为 60，脚本现场统计、不写死；明细 `.work/log/spec/SPEC-126t-classification.md` / `SPEC-126t-rescan-ci.txt`）**：
  - **改（唯一「返回」用途残留）**：`contract-abi.md:285` → `RD8`。
  - **不改·参数区/角色表**：`DADAO-21:377`（`RD16 - RD31`/`RB16 - RB31`/`RF16 - RF31`，返回处已 `RD8`）、`DADAO-22:31`、`Machine-01:124`、`contract-abi`(40/56/68/93/94/167-169/172/177/197/206/220/303)、`contract-see:53`、`contract-semihosting:25`。
  - **不改·非返回**：`Toolchain-01:205`（`xnor.o rd16, rd31, rd0` 指令暂存）。
  - **不改·历史/决策/台账**：`project_M3-codegen-choices.md`（15 行，含仅大写 33/35/198/201/439/444）、`lessons.md:425`、`milestones.md:10/41`（不追溯重写）。
- **验证**：`make check` EXIT=0（`check-spec-readonly` 21 册 OK、`check-patch-tree` 92 patches OK）；`run.sh` `RUN_EXIT=0`（新增 **B2** 断言 + **E2** 注入自检：`返回值 RD8）`→`RD31）` md5 变 ⇒ B2 两条断言 FAIL〔has=0 / absent=1〕⇒ `cp`+md5 还原 ⇒ 回绿）。日志 `.work/log/spec/SPEC-126t-{evidence-final2,make-check}.log`。
- **修改文件（本轮）**：`.tao/knowledge/contract-abi.md`；`.work/evidence/SPEC-126t/run.sh`、`.work/log/spec/SPEC-126t-{classification.md,evidence-final2.log,rescan-ci.txt,make-check.log}`（`.work/` 已 gitignore）。
- **遗留问题**：遗留① ✅已收口；实现/向量侧涟漪归 `QEMU-055t`/`TESTCASES-041t`（本轮与实现侧 `git diff` 交集为空）。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查（4 册 spec + 2 合约 + 锁 + 证据脚本）：

1. **DADAO-22 批量替换保护参数区**：以 `(?<!-)rd31` 替换，保护 L31 `rd16-rd31`；复验 L31 保留、`param_inv`（total==param）PASS。逻辑正确。
2. **`rb31 → rb8`**：Machine-01 §5.2、contract-see §5 的「指针返回」语句若只改标量则自相矛盾；依 `SPEC-124t` 函数 ABI（指针返回 `rb8`）一并改，已在完成区披露。判决：改。
3. **范围外陈旧引用** `contract-abi.md:285`：不改（未列入任务文件）；登记遗留①。
4. **防造假**：门控与脚本输出均为真实执行（`rc=$?`，结尾不 `tee`）；注入自检证明断言可失败。
5. **首轮脚本误报→修复**：`has` 断言模式 `rd16–rd31（数据）` 缺反引号致假 FAIL（actual=0），补反引号后 PASS——证明脚本非恒真。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 DADAO-22 批量替换须保护参数区 | ✅已修 | `(?<!-)rd31`，L31 保留 | `grep rd31` 仅 L31；`param_inv` PASS |
| F2 指针返回 `rb31` 与标量 `rd8` 不一致 | ✅已修 | Machine-01/contract-see 指针返回改 `rb8` | 断言行 PASS；完成区已披露 |
| F3 `contract-abi.md:285` 陈旧引用 | ⏸延后 | 未改（未列入任务文件） | 完成区「遗留问题①」 |
| F4 证据脚本断言模式缺反引号（假 FAIL） | ✅已修 | 补 `` ` `` | 首轮 FAIL→修后 `RUN_EXIT=0` |

判决：全部 finding 已修/已登记，状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑**：`bash .work/evidence/SPEC-126t/run.sh` → 42 项全部 PASS，`RUN_EXIT=0`（含 A/B/B2/C/D/E/E2/F 各段）。

**独立注入**：`DADAO-21` `返回值放在 RD8`→`返回值放在 RD31`（python replace 1 处）；md5 变化 `56e477…→57f1be…`（非空注入 ✓）；断言 FAIL（`has(RD8)=0`、`absent(RD31)` count=1）；`cp`+md5 还原 = `56e477f2b8352e65cabc8fca8d709b23` ✓。

**独立全仓扫描**：`grep -rniE '\brd31\b|\brb31\b|\brf31\b' spec/ .tao/knowledge/ contracts/` 共 60+ 命中，逐条判类——全部为参数区（`rd16-rd31`/`rb16-rb31`）、角色表、指令暂存（`Toolchain-01:205`）、历史/决策/台账（`project_M3-*`/`lessons.md`/`milestones.md`）、ABI 范围描述（`contract-abi` 多行）。**无「调用/服务返回」用途残留**。`DADAO-21:377` 返回处已 `RD8` ✓。

**锁核验**：`manifests/spec-readonly.lock.toml` 21 册 `sha256` 全部与实测一致（逐册 OK）。

**越界**：`git status --porcelain -uall` 仅 8 文件（`DADAO-21/22/23`、`Machine-01`、`contract-see`/`contract-semihosting`/`contract-abi`、锁 + 任务书），无 `components/**`/`tools/**`/`tests/**`，无 `_tmp`/`_orig`/`_rej`。

**门控**：`make check-spec-readonly` EXIT=0；`make check-patch-tree` EXIT=0。

**判决：Accepted**

#### 第 2 轮 engineer 自审

自主逐行审查（`contract-abi.md:285` 单行 + `run.sh` B2/E2）：

1. **改对性**：`返回值 RD31` → `RD8`；`RD15 调用号`（入参）保留未动 —— 与 `DADAO-21 §系统调用规范`（`SPEC-126t` 已改 `RD8`）、`contract-abi §4.4/§6.1`（返回区 `rd8–rd15`）一致；`git diff` 仅 1 行。判决：正确。
2. **修一类**：任务给定 grep 为小写，目标行是大写 `RD31`；不补大小写不敏感扫描会再次漏网。已补扫，小写 49 行 + 仅大写新增 6 行逐条判类，唯一「返回」用途残留即本行。判决：已修一类。
3. **锁**：`contract-abi.md` 不在 `manifests/spec-readonly.lock.toml`（仅 21 册 `spec/`），无需同步。判决：无需改锁。
4. **脚本可失败性**：E2 注入后 B2 的 `has`(RD8)=0、`absent`(RD31)=1，两条断言均进 FAIL 支路；`cp`+md5 还原（`ac531d…`↔`b491e181…`，注入态 md5 恰等于改前行 md5）⇒ 回绿。结尾 `rc=$?`、非 `tee`。判决：可失败、可还原。
5. **范围**：未动 `components/**`/`tools/**`/`tests/**`；`git status --porcelain -uall` 仅本任务应有文件 + `contract-abi.md`，无 `*_tmp*`/`*.orig`/`*.rej`。判决：无越界。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 原 grep 小写漏大写 `RD31` | ✅已修 | 补大小写不敏感重扫 + B2 断言 | E2 注入 FAIL→还原回绿；`rescan-ci.txt` |
| F2 遗留① stale 行 | ✅已修 | `contract-abi.md:285` 改 `RD8` | B2 `has RD8`/`absent RD31` PASS；`make check` EXIT=0 |

判决：全部 finding 已修，状态置 `待验收`。

#### architect 提交留痕（2026-10-09）

- **档位**：**正常提交**（reviewer 第 1 轮判 `Accepted`，42/42 PASS EXIT=0；2 轮 engineer 修复均为同类残留收口）。
- **提交号**：`98d7463`（`SPEC-126t: 系统调用/半托管返回寄存器统一 rd8 …+ 锁同步`）。
- **文件集对账**（显式 staging，禁 `git add -A`；`git diff --cached --name-only` 9 项）：与完成区「修改文件」①-⑦ + 第 2 轮补充（`contract-abi.md`）+ 本任务书**逐条一致**——**无漏提、无多提、无越界**（无 `components/**`/`tools/**`/`tests/**`）。
- **交叉复核**：4 册 `sha256` 实测与锁文件**逐册相等**；锁内 `sha256` `-`/`+` 计数 = 4/4（仅被改 4 册，余未动）；全仓 `-i` 重扫返回用途**无残留**；`git status --porcelain -uall` 无 `*_tmp*`/`*.orig`/`*.rej`。
