# m18-linux-012: ISS-503 K6 门控五条 finding 订正

**模块**：linux
**项目里程碑**：M18
**依赖**：`m18-linux-003`（K6 门控）
**可并行分片**：否
**预估**：1–2 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为门控断言/文档订正，取 1–1.5× 中位）
**档位**：中改（门控断言）
**状态**：已验证
**执行环境**：本地

## 背景

`ISS-503`【P3】（`m18-linux-003` 复核五条非阻断 finding）：

- F1：`check_k6.py` C 组 11 条「rc 标记是脚本期望的…」在 `region()` 成功分支内恒真（应并入 region 断言）。
- F2：完成区「musl 18 项」不准（实为 10 problem；18 是证据脚本按非 linux 前缀行的统计，标签 `non-linux problems` 亦失准）。
- F3：完成区/`Process-07` 的「5 次翻转（S/C/E/R×2）」与「四组各一次」不符。
- F4：`run.sh` 有未使用的 `check_absent_lines`。
- F5：§4a.3 表符号名 `dadao_umon_frame` 应为 `dadao_umon_save`。

## 目标

逐条订正；**不放松 K6 判据**，恒真断言改为可达 FAIL；文档数字与实况一致。

## 验收（逐条贴真实 rc）

1. F1：11 条恒真断言并入 `region()` 的有效断言（或删除并由 region 缺失断言覆盖），注入「C 组期望行缺失」可判红。
2. F2：证据脚本非 linux 问题计数口径与标签准确；`check-patch-tree` 实况（musl 10 problem）与打印一致。
3. F3：任务书完成区与 `Process-07` 的翻转计数改为实况（S/C/E 各 1 + R 2 = 5，四组表述订正）。
4. F4：删除孤儿 `check_absent_lines`。
5. F5：§4a.3 表符号名改为 `dadao_umon_save`（`trap.S` 单帧实体）。
6. `check-linux-k6` rc=0（71/71 或现场打印项数）；`--selfcheck`/`--inject` 仍可翻转；`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
7. `ISS-503` 关闭；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`tests/unit/linux/check_k6.py`、`docs/Process-07*.md`、`.tao/tasks/linux/m18-linux-003-K6收口门控.md`（仅订正 F2/F3 事实，不改审阅记录）、`.tao/knowledge/issues.yaml`、本任务书。
3. 不改内核/组件；不改版本号；术语「bank = 寄存器组」。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`。

## 待裁定

无。

## 完成区

**测试结果**：运行期证据目录内 `run.sh`（full）**61 项、failed=0、skipped=1、rc=0**；`run.sh --inject`（注入/FAIL 路径单独复跑）**40 项、rc=0**。`make check-linux-k6` **82/82、rc=0**（S 14/14 C 30/30 E 4/4 R 34/34，items=82；相对 003 的 71 为 **S +2、R +9**，C 组仍 30）；`check_k6 --only R` rc=0；`--selfcheck` rc=0（现场 S1/C1/E1/R2）；`check-tests-index` rc=0；`check-patch-tree` rc=0（源树按本仓 lock+series 重放）；`check-knowledge-refs` rc=2 但悬空集与基线逐行相同、本树无 ISS-352；`make -k check` 两树 rc=2，本树多出的失败门控除 `check-milestones-fresh` 外为 0。
**修改文件**：`tests/unit/linux/check_k6.py`（F1 判据；第 1 轮形态未回退）；`docs/Process-07-门控分层规范.md`（K6 翻转计数、§4a.3 符号）；`.tao/tasks/linux/m18-linux-003-K6收口门控.md`（仅完成区 F2/F3 事实，审阅记录未动）；`.tao/knowledge/issues.yaml`（ISS-503 closed / M18）；本任务书。本轮返工只改运行期证据脚本 + 本任务书，未动 `components/**`、`Makefile`、`spec/`、版本号；未提交 git。
**验收结果**（本轮修正的三条断言，各自怎么失败）：① **基线 VIOLATION**：旧 `grep -c '^VIOLATION'` 在缩进日志上恒 0（合成夹具实证 1 vs 2；现场 `^` 锚定 0、去锚定 7）；改为 A1/R1 台账归因行 + 集合差，谓词用合成输入证红（非本任务违规 ⇒ 命中 1）；违规集差为空 ⇒ 显式 SKIP（本次即 SKIP，理由已打印）。② **F2**：改独立 oracle —— 003 运行期日志中工具自报 `10 problem(s)` == 逐行 `assertion` 消息（两条不同路径），旧口径 18 分解为 10 断言 + 8 patch 行 + 0 absent（residue 0）；注入（一条 `musl: assertion` 改写为 `musl: 26 patch(es)`，oracle 本体 md5 `d07513f3…`（注入副本 `02b41a44…`））⇒ summary 10 ≠ assertion 9 ⇒ 判红；`cp` 还原 ⇒ 回绿；`check_absent_old`（完成区无「18 项」）另做注入 0→1 → 还原 0。③ **milestones 归因**：删掉「唯一 VIOLATION=1 / 基线 0」；改单册直调 `tools/infra/check_milestones_fresh.py --file .tao/knowledge/milestones-m18.md`（本树 rc=1 且指名 `m18-linux-012: MISMATCH`；基线树 rc=0），不写入他人在途 worktree 状态。
**新发现/坑**：① 安装根 qemu 与 HEAD 内核不同模型（旧模型 `f734b701…` 可用，新模型 `7148dbca…` 在 K1 ptw 探针处 `unknown cause`）；② 共享源码树漂移会让 patch-tree 假红（须按本仓 lock+series 重放）；③ 干净树构建顺序 `build-busybox → linux-initramfs → linux-defconfig`（否则空 rootfs panic；④ 证据脚本自注入不能用脚本里出现过的名字）；⑤ **共享态不可作期望值**：`make -k check` 的 VIOLATION 集含磁盘占用等波动行与并发 worktree 的 R1 行，两树同一时刻也不同 ⇒ 只取台账归因行、差集为空即 SKIP，判据的可达 FAIL 用合成输入证明；⑥ 基线树审计必须用**基线树自己的** `tools/infra/*`（用本树脚本会按脚本所在仓解析）。
**遗留问题**：① qemu 安装根模型不一致（根因需 architect 裁定；按 reviewer 意见「重跑 `install-host` 大概率无效」）；② 003 运行期脚本的孤儿 `check_absent_lines` 未回改（历史证据、非仓库文件）；③ m17 悬空 ADR-0063 为预存项（与基线相同）；④ 本 worktree 台账仍列 m18-linux-012 于「待开始」（基线 HEAD 版本），合并期由主会话更新。

## 审阅记录

### 第 1 轮 engineer 自审

按「实现 → 跑门控 → 注入证红 → 还原 → 复跑」推进；判决：可交付（`待验收`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 C 组 11 条 `marker in text` 在 `region()` 成功分支内恒真 | ✅已修 | 判据上移为 `rep.check(..., lines is not None)`，失败即 `continue`（C 组项数仍 30） | 删标记行 ⇒ 该条 FAIL；判据肢解 ⇒ 不再红；还原 ⇒ 再红 |
| F2 完成区「musl 18 项」与 `non-linux problems` 标签失准 | ✅已修 | 003 完成区两处改 10 problem(s) + 口径说明；本证据脚本按 `assertion` 行计数 | 夹具 10 vs 旧 18；完成区「18 项/18 problem」0 命中 |
| F3 翻转计数「S/C/E/R×2」与「四组各一次」 | ✅已修 | 003 完成区与 `Process-07` K6 行均改「5 次翻转（S/C/E 各 1 + R 2）」 | selfcheck 现场 S1/C1/E1/R2=5；注入旧表述 ⇒ 判红 ⇒ 还原 |
| F4 证据脚本孤儿 `check_absent_lines` | ✅已修（本任务脚本）+ ⏸历史脚本不改 | 本任务 run.sh 无孤儿；新增「未调用函数」机械自审 | 审计 0；向副本注入 `zz_unused_<pid>` ⇒ 判出 |
| F5 §4a.3 符号 `dadao_umon_frame` | ✅已修 | 改 `dadao_umon_save`（`trap.S` 的 `.globl` 实体，`.zero PT_REGS_SIZE`） | 文档 0 处旧名；源码 2 处实体 + `setup.h` C 声明 1 处；注入旧名 ⇒ 判红 ⇒ 还原 |

**自审过程中自查出的问题（同轮修复）**

| 自审发现 | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 自审：证据脚本向自身注入 `dead_helper` 时，名字已出现在被拷贝脚本里 ⇒ 调用计数 >1 ⇒ 假绿 | ✅已修 | 注入名改运行时生成的 `zz_unused_<pid>` | 审计判出该名（`50/50`） |
| 自审：`check_present` 用双引号传含反引号的字符串 ⇒ 命令替换吃掉字样 | ✅已修 | 改单引号 | F5 项显示「\`dadao_umon_save\` 单帧」 |
| 自审：F5 `^\.globl` 不容忍行首制表符 ⇒ 期望 2 实际 1 | ✅已修 | 加 `[[:space:]]*` | 2/2 |
| 自审：F2 用「文档 10 == 现场」判错（10 是 003 当次运行值，现行按本仓 series 重放为 0） | ✅已修 | 改「夹具复现旧口径 18 = 10 断言 + 8 组件计数行」+ 完成区旧数字清除 | 10 vs 18；003 完成区 0 命中旧数字 |
| 自审：干净树上 `make linux-defconfig` 先于 cpio ⇒ 空 rootfs（`No working init found`, rc 124） | ✅已修 | run.sh 加 prep：`build-busybox → linux-initramfs → linux-defconfig` | prep rc=0；gate 82/82 |
| 自审：本任务书完成区写了具体运行期路径 ⇒ `check-knowledge-refs` 报 ISS-352 | ✅已修 | 改「运行期证据目录内的 `run.sh`」 | 本树 ISS-352 计数 0 |
| 自审：直接比 `make check` 整份日志会被「本任务状态翻转/扫描计数」污染 | ✅已修（**已被第 1 轮返工替换**，见下） | 改判「失败门控差集仅 `check-milestones-fresh`」+ 其唯一 VIOLATION 指名本任务 + 悬空集逐行相同 | 当时绿；但「基线 0 VIOLATION」被 reviewer 判为假绿 |

**自审补充**：`make linux-defconfig` 与 initramfs 的先后依赖已写进 run.sh 的 prep 段，证据脚本在干净构建树上可重跑；证据脚本自身用 `set -u`、逐项打印期望/实际/rc、失败即非零退出，无 `tee` 吞码。


### 第 1 轮 reviewer 验收

**重跑（本审查者现场执行，rc 取被检命令自身；未采信完成区转述）**：`make check-linux-k6` → **rc=0**、`S 14/14 C 30/30 E 4/4 R 34/34 items=82`、`82/82 passed`；`check_k6 --only R --no-build` → rc=0（`R 34/34`）；`check_k6 --selfcheck` → rc=0，翻转 `S=1 C=1 E=1 R=2` 合计 5；`make check-tests-index` → rc=0（500 条）；`make check-patch-tree` → rc=0（musl assertion 0 行）；`tools/infra/check_issues.py` → rc=0（96 open / 87 closed，closed 字段约束 OK）；`make check-knowledge-refs` → rc=2，`git archive HEAD` 基线树（同安装根）亦 rc=2，悬空集两树 `diff` rc=0（同为 1 条预存 m17 悬空项）。

**独立注入 → FAIL → 还原 → 回绿（不采信工程师自检）**：`cp` 备份后把 `judge_c` 的 region 断言整段回退到 HEAD 形态（md5 `f0b61bd7…`→`ca269768…`）⇒ 重跑运行期证据目录内 `run.sh` → **rc=1 / 6 FAIL**，其中 3 条正是 F1（可达 FAIL、肢解注入生效、还原后重新判红）；`cp` 还原 ⇒ md5 `f0b61bd7953b21c986caf19abcbdff36`、`git diff --stat` 仍 6+/3- ⇒ 再跑 `run.sh` → F1–F5 与全部门控断言 PASS（肢解 `6f3d0a09…`、还原 `f0b61bd7…`，与完成区一致）。

**F1**：`marker in text`（region 成功分支内恒真）已上移为 `rep.check(..., lines is not None)` 且失败即 `continue`；C 组现场 **30/30** 不变；新旧判定取值完全等价 ⇒ **不放松**（严格说并非「更严」）。
**F2**：自己数 003 运行期 patch-tree 日志 —— 旧口径 18 = **10** 条 `musl: assertion` + **8** 条组件 patch 计数行 ⇒ 说法成立；完成区扫描面 `18 项`/`18 problem` **0 命中**（残留 1 处在 `## 审阅记录` L77，按硬约束不改）。
**F3/F4/F5**：selfcheck 现场 S1/C1/E1/R2=5 与两处文档一致；003 运行期证据脚本 `check_absent_lines` 确为孤儿（仅定义 1 处）；`trap.S` `.globl dadao_umon_save`+标号 2 处、`setup.h:120` 的 `dadao_umon_frame(void)` 1 处、`docs/`+`spec/` 旧符号 0 命中。

**范围/约束**：`git diff --name-only` 恰 5 文件、无 untracked、HEAD 仍 `89f0c072`（未提交）；003 `## 审阅记录`（L42–80）段级 md5 与 HEAD 相同；5 文件 md5 与审查前快照逐一相同；未动内核/组件/`Makefile`/`spec`/版本号。

**Needs Revision — 运行期证据目录内 `run.sh` 有 3 条不可达 FAIL 的断言**（`AGENTS.md §4`：禁恒真、禁同源自比；按规则 reviewer 不代改脚本）：
1. `check "基线树同一门控 0 VIOLATION"`：`grep -c '^VIOLATION'` 永不匹配缩进行（现场 base/mine 均 `'^VIOLATION'=0`、`'^  VIOLATION'=7`）⇒ 恒真；且基线当前确有 1 条 `check-milestones-fresh` 违规却仍绿（**假绿**）。改：去掉 `^` 锚定、只统计该门控段，并按「两树违规集差 ⊆ 本任务号」现场派生。
2. F2 夹具块 `旧口径 == 10 + 组件计数行`（两侧同源自比）与标称「可达 FAIL 路径」的 `退回旧口径 ⇒ FAIL`（18≠10 固定）均恒真 —— 标称的可达 FAIL 实际不可达。改：对 003 运行期 patch-tree 日志套两条规则（文件缺失即 FAIL），并给 `check_absent_old`（完成区无旧「18 项」）补一次注入→FAIL→还原。
3. 末 3 条 `check-milestones-fresh` 归因断言把并发共享状态写成期望值：`m16-testcases-014` worktree 建于 01:28:42（工程师 01:11 跑批之后）⇒ 本树与基线**同时**红、差集为空，重跑必红。改：`fails-*.txt` 求差判 `⊆ {check-milestones-fresh}`；A1 归因直接调 `check_milestones_fresh.py` 单册，绕开 Makefile 循环被他册 R1 中断。

**非阻断发现（建议收尾一并改）**：完成区「多出的 11 项来自基线已含的 R 组增补」归因不准（71→82 实为 **S +2、R +9**；`14+30+4+34=82` 自洽）；「同一输入不再红」措辞不精确（肢解后 C 组仍 2 条红，只是该断言不红）。

**阻断（供 architect 定夺，非本任务缺陷）**：安装根 `qemu-system-dadao` `7148dbca…`（mtime 2026-11-25 00:29）＝ HEAD 已合入的新模型序列（`m18-qemu-005/006`、`m17-qemu-001` 均为 HEAD 祖先），而 HEAD 内核仍旧模型（`m18-linux-022`/`-023` **待开始**）⇒ 本审查者用安装根 qemu 跑 `make check-linux-k1` 现场 **rc=2**、`cause=unknown(0x10000000000000)`。故用 `m18-infra-003` 备份旧模型 qemu（`f734b701…`）配 HEAD 内核**语义正确**；本任务只动 `check_k6.py`+文档+issues，与 qemu 模型无因果、**不构成掩盖**。但完成区建议的「重跑 install-host」大概率无效（源树 clean 单 commit，重建仍是新模型），根因需 architect 裁定。

**判决：Needs Revision** —— 仅上述证据脚本 3 条断言 + 2 处措辞；交付物本体（F1–F5 订正、5 文件范围、ISS-503 关闭、各门控 rc）均已由本审查者独立复现为绿。

### 第 1 轮 engineer 返工（Needs Revision 处置）

按 reviewer 三条阻断逐条重写判据，并各自给出可达 FAIL 的真实翻转。

| 阻断 | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1 `grep -c '^VIOLATION'` 永不匹配缩进行 ⇒ 基线 0 VIOLATION 假绿 | ✅已修 | 改 `^[[:space:]]*VIOLATION` 且只取 A1/R1 台账归因行；判「集合差内除本任务号外为 0」；差集空 ⇒ 显式 SKIP | 合成夹具 1 vs 2；现场去锚定 n=7；谓词合成输入：非本任务行 ⇒ 1、本任务行 ⇒ 0；违规集差空 ⇒ `[SKIP]` 打印原因 |
| 2 F2 夹具同源自比 + 标称可达 FAIL 不可达 | ✅已修 | 改用 003 运行期日志的**工具自报 problem 数 vs 逐行 assertion 消息**（两独立路径）+ 旧口径分解（断言/patch 行/absent，residue 0）；注入一条 `musl: assertion` → 组件计数行 | 现场 `summary=0 assertion=0 old=15=0+8+7 residue=0`；oracle `10=10`、`18=10+8+0`；注入后 `10≠9` 判红（oracle 本体 md5 `d07513f3…`（注入副本 `02b41a44…`））⇒ `cp` 还原回绿；`check_absent_old` 注入 0→1 → 还原 0 |
| 3 milestones 末 3 条断言写死并发共享状态 | ✅已修 | 删除「唯一 VIOLATION=1 / 基线 0 VIOLATION」；改单册直调（绕开 Makefile 循环被他册 R1 中断），只依赖两树内文件 | 本树单册 rc=1 且含 `m18-linux-012: MISMATCH`；基线树同册 rc=0；失败门控差集判据改「除 check-milestones-fresh 外为 0」 |
| 非阻断：完成区 71→82 归因不准 | ✅已修 | 改「S +2、R +9（14+30+4+34=82 自洽）」 | 完成区文字 |
| 非阻断：「同一输入不再红」措辞不精确 | ✅已修 | 改「该条不再红（C 组其余断言仍红）」，并新增断言证明肢解后 C 组仍有别的红 | `C fails=[顺序…, 没有中途停摆…]`（2 条，非空） |

**自审补充**：`run.sh` 新增 `--inject` 模式（只跑注入/FAIL 路径，不建不跑，40/40），full 模式 61/61（1 条 SKIP 为并发共享态、已打印理由）；未改 `components/**`、`Makefile`、`spec/`、契约，未动 003 审阅记录。

### 第 2 轮 reviewer 验收

**重跑（本审查者现场执行，rc 取被检命令自身；未采信完成区转述）**：运行期证据目录内 `run.sh`（full）→ **rc=0 / checks=61 / failed=0 / skipped=1**；`run.sh --inject` → **rc=0 / 40 / failed=0**；`make check-linux-k6` → rc=0、`S 14/14 C 30/30 E 4/4 R 34/34 items=82`、`82/82 passed`；`check_k6 --selfcheck` → rc=0（S1/C1/E1/R2 合计 5）；`make check-tests-index` → rc=0（500 条）；`make check-patch-tree` → rc=0（assertion 0 行）；`make check-knowledge-refs` → rc=2，`git archive HEAD` 基线树同安装根亦 rc=2、悬空集 `diff` rc=0（同 1 条预存 m17 项）、ISS-352=0。`--inject` 只跑注入/FAIL 路径属合理（三条修复的 **live** 断言依赖 `make -k check`，只在 full 模式跑；本轮以 full 为准）。

**阻断 1 已修 + 我的反例**：`violations()` 改 `^[[:space:]]*VIOLATION: (A1|R1):`（旧 `^VIOLATION` 只剩在「盲区实证」夹具里），现场去锚定 `n=7`、旧锚定 `0`。我从 `run.sh` 抽出同一函数自造反例：仅本树多一条外部任务 `R1` 行 ⇒ `viol-new` 非空、`grep -vc m18-linux-012`=**1** ⇒ 判红；改成本任务号 ⇒ **0** ⇒ 绿；两树同红 ⇒ 差集 0 行 ⇒ 走 SKIP 分支。SKIP 现场属实：两树 `viol` 集均为同一条并发 worktree 的 `R1: m16-chipyard-027`，理由已打印且计入 `skipped=1`，**非掩盖**（本任务自身 A1 归因由不跳过的单册断言覆盖）。

**阻断 2 已修 + 我的反例（非其路径）**：改用 003 运行期日志作独立 oracle。我用 `grep` 独立数：工具自报 `check-patch-tree: 10 problem(s)` == 10 条 `assertion` 行；旧口径 18 = **10 断言 + 8 patch 行 + 0 absent**，residue 0（与完成区说法一致）。我自己的三条变异：追加 1 条断言行 ⇒ `summary=10 assertion=11` rc=**1**；删掉 summary 行 ⇒ `0 vs 10` rc=**1**；改写行型 ⇒ `10 vs 9` rc=**1**；本体 rc=0。该判据非恒真亦非同源自比（两侧是工具不同位置发出的不同量；旧口径分解是形状划分，任一形状漂移即破）。

**阻断 3 已修 + 我的独立注入**：删掉写死的「唯一 VIOLATION=1 / 基线 0 VIOLATION」；改单册直调（本树 rc=1、日志含 `A1: … m18-linux-012: MISMATCH 册=待验收`，基线同册 rc=0 且无 R1 噪声）；失败门控判据改「本树多出的除 `check-milestones-fresh` 外为 0」（现场 `extra=[]`）。**注入**：把本任务书 `**状态**` 改 `待开始`（md5 `a2d5831d…`→`09117776…`）⇒ 全量 `run.sh` **rc=1 / failed=2**，红的正是 `m18 台账单册审计 rc=1（期望 1 实际 0）` 与 `单册审计指名本任务 A1 不一致`；`cp`+md5 还原 ⇒ `a2d5831d…` ⇒ 复跑 **rc=0 / 61 / failed=0**。

**两条非阻断已改**：完成区改「71→82 = S +2、R +9，C 组仍 30」（与现场 `14+30+4+34=82` 自洽）；F1 措辞改「该条不再红（C 组其余断言仍红）」并新增断言 `F1 肢解后 C 组仍有别的红`（现场实证 2 条非空）。

**范围/约束**：`git diff --name-only` 恰 5 文件、无 untracked、HEAD 仍 `89f0c072`（未提交）；003 `## 审阅记录`（L42–80）段级 md5 与 HEAD 同（`1e577148…`），hunk 仅 L83/85/87；4 个受审文件 md5 与第 1 轮快照逐一相同；未动内核/组件/`Makefile`/`spec/`/版本号。

**遗留 finding（不阻断，建议收尾处置）**：① `去锚定模式能看见现场缩进 VIOLATION` 用 `n≥1` 把环境状态写成期望值（同一事实已有合成夹具证明，建议改 SKIP 或删，否则环境变干净会假红）；② 完成区「注入…oracle 本体 md5 `d07513f3…`（注入副本 `02b41a44…`）」标错对象——该值是 oracle **本体** md5，注入后副本为 `02b41a44…`（数字笔误，非验收判据）；③ F2 oracle 取自主仓运行期证据目录（本 worktree 外），缺失时判 FAIL（不静默），证据不完全自包含。

**阻断（沿用第 1 轮，供 architect 定夺，非本任务缺陷）**：安装根 `qemu-system-dadao` `7148dbca…` 与 HEAD 内核不同模型（`m18-linux-022`/`-023` 待开始），K1 在安装根 qemu 下必红；本任务只动 `check_k6.py`+文档+issues，与 qemu 模型无因果、不构成掩盖，「重跑 install-host」大概率无效。

**判决：Accepted** —— 三条阻断均已由本审查者独立构造反例证明「能失败」，并完成一次独立注入的「注入→红→`cp`+md5 还原→回绿」；交付物本体与全部门控经本人重跑全绿。
