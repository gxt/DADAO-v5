# TESTCASES-098t: M11 矩阵重生成与 Node 历史归类

**模块**：testcases
**项目里程碑**：M11
**依赖**：M11 收口条件满足（`SPEC-186t`、退出码迁移、完整 llvm-ts 回归）
**状态**：已验证

## 执行环境
本地；只重生成矩阵与归类历史结果，不改实现、不改 spec。

## 背景

`tests/parity/matrix-M11.md` 仍是 `GEM5-017t` 的旧快照；M11 收口需要原地重生成。同时用户已定：`GEM5-016t`/`QEMU-080t` 的 Node `inst`/`embench` 结果**转历史**，不计入 M11 Node 验收；M11 Node 只验收 cfx/arch/PTW/模式；Embench 归属 Tiny（system/bare-metal）与 SE（user static/dynamic），Node 不跑 Embench。

## 目标

1. 以 M11 收口时的 QEMU/gem5 现场结果，**原地重生成** `tests/parity/matrix-M11.md`：
   - 覆盖 Tiny/Node 的 `inst`/`arch` 与 SE 的 tset 矩阵；
   - 保留 `AGREE_PASS`/`DIFF`/`QEMU_ONLY_FAIL`/`GEM5_ONLY_FAIL`/`BLOCKED` 分类与计数；
   - `math_test` 的 B7 已知差异保留 `BLOCKED` 及计数，不写 PASS。
2. 在矩阵/README 中标注历史归类：
   - `GEM5-016t`/`QEMU-080t` 的 Node `inst`/`embench` 结果标“历史、不计入 M11 Node 验收”；
   - M11 Node 验收范围写明 cfx/arch/PTW/模式；
   - Node 不跑 Embench；Tiny/SE 的 Embench 归属写明。
3. 不修改任何测试期望值、不改引擎实现；只改矩阵快照与说明。

## 接口规范

- 矩阵由 `tools/testcases/parity/run_parity.py` 现场生成，禁手改 JSON/Markdown 计数。
- Node 历史结果只作说明，不进入 M11 Node 通过/失败统计。
- `math_test` 若有差异，保留 `BLOCKED` 与 `errors/total` 现场数字；不把 blocked 计入通过数。
- 不改 `tests/parity/matrix-M11.md` 之外的矩阵快照（除非任务书现场确认需要同步索引）。

## 范围 / 非范围

**在范围内**：`tests/parity/matrix-M11.md`、`tools/testcases/parity/README.md`（仅历史归类/Node 范围说明）、本任务书、`milestones.md`、运行期证据。

**不在范围内**：QEMU/gem5/LLVM 实现、`spec/**`、`contracts/**`、`tests/inst/**`/`tests/arch/**` 期望值、`Makefile`、门控脚本。

## 验收标准

1. **现场重生成**：`run_parity.py` 用 M11 收口时的引擎身份（QEMU/gem5 md5/版本、fs.py、bootrom）生成矩阵；矩阵含引擎身份与命令；不引用旧临时目录/旧快照冒充。
2. **计数自洽**：行数 = 各分类之和；`AGREE_PASS`/`DIFF`/`QEMU_ONLY_FAIL`/`GEM5_ONLY_FAIL`/`BLOCKED` 计数由脚本现场统计；`DIFF` 必须逐条归因或登记 issue。
3. **Node 历史归类**：矩阵/README 明写 Node `inst`/`embench` 为历史、不计入 M11 Node 验收；M11 Node 只验收 cfx/arch/PTW/模式；Node 不跑 Embench。
4. **math_test**：若仍 BLOCKED，保留现场 `errors/total` 与 QEMU/gem5 对照；不得写 PASS 或从通过数中抹掉。
5. **llvm-ts**：M11 收口前完整 llvm-ts 回归结果纳入矩阵/说明；QEMU user 为基线，gem5 不能少通过；gem5 通过而 QEMU 未通过须定位到一致。
6. **门控**：`make check-tests-index`、`check-case-ledger`、`check-run-artifacts`、`make check`（L1）rc=0；矩阵文件格式与索引一致。
7. **反例可达 FAIL**：手改矩阵计数/删一行 ⇒ 校验脚本 FAIL；`cp`+`md5sum -c` 还原后回绿。
8. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务在 M11 收口时执行；未收口前不得用旧结果预生成。
- 若现场发现 spec/引擎语义不一致，保留现场并留问，不自行改期望值。
- 历史归类只写“不计入 M11 Node 验收”，不删除旧任务书的历史证据。

## 未决（下发前需确认）

1. **M11 收口条件**：`SPEC-186t`、退出码迁移、完整 llvm-ts 回归是否全部完成；未完成则本任务 BLOCKED。
2. **矩阵范围**：是否只重生成 `matrix-M11.md`，还是同时更新 README 的索引/统计说明。
3. **Node 历史归类的落点**：矩阵内注记 + README，是否还需要改 `GEM5-016t`/`QEMU-080t` 完成区（默认不改历史任务书）。

## 完成区

**测试结果**：
- `node/arch` 定点复核（`run_parity.py --profiles node --scopes arch`）：**rc=0**，total 269、agree_pass 249、gem5_only_fail 0、diff 0、qemu_only_fail 0、blocked 20。
- 全量矩阵（`tiny,node × inst,arch,picolibc`）：**rc=0**、`repro-check PASS`；node/arch 269=249+20、node/inst 1014=965+5+44、tiny/arch 269=269 N/A、tiny/inst 1014=1005+5+4、tiny/picolibc 20=17+1+2；`GEM5_ONLY_FAIL=0`、`DIFF=0`、`QEMU_ONLY_FAIL=0`、`AGREE_FAIL=0`。
- 原 14 条 `GEM5_ONLY_FAIL` 逐条转 `AGREE_PASS`（14/14，含 `m5_perm_badcombo_cfxreg`）；上一版红矩阵为 gem5 未对齐的历史快照，已由本次替换，旧矩阵/日志移至证据目录 `prev-red/`。
- `math_test` 仍 `BLOCKED`：QEMU 0 errors/76404 functions、gem5 238 errors/76404（exit 1），未计入 `AGREE_PASS`。llvm-ts（TESTCASES-100t 夜跑 2026-11-05-13，4/4 rc=0）：static/dynamic 均 discovered 222−excluded 8=214、pass 214/fail 0/blocked 0。
- 门控：`check-tests-index`/`check-case-ledger`/`check-run-artifacts` 真实 rc=0；`make check`(L1) **rc=0**（`GEM5-020t` 合入后 `check-patch-tree` 转绿）。
- 证据脚本：normal **37/37 rc=0**、`--inject` **30/30 rc=0**。
**修改文件**：`tests/parity/matrix-M11.md`（现场 Markdown `cp`，md5 对账，未手改计数）、`tools/testcases/parity/README.md`（M11 口径/Node 历史归类/Embench 归属/llvm-ts/math_test/红项历史）、`.tao/knowledge/milestones.md`（本任务流水行状态）、本任务书；运行期证据与 JSON 在证据目录（未入库）。
**现场裁定（用户原文摘要）**：“M11 L1/L3/夜跑均绿（夜跑 4/4、night-report rc=0；L3 8/8）。`SPEC-187t` 退出码规范已定稿，但 QEMU/gem5 退出码实现尚未迁移；本任务矩阵是当前引擎快照，在完成区明确写‘退出码实现迁移后需再重生成一次’，不得伪称最终。”；“gem5 已由 `GEM5-020t` 对齐 QEMU-083t 的 CFXREG 目标（10 处 `cfxha`→`s.runMode`），当前 gem5 二进制已重建。”
**验收结果**：
1) 现场重生成：矩阵含 QEMU md5/版本、gem5 md5（`d64b0f9…`，重建后二进制冻结副本）/fs.py md5/source commit（`1ad69d2…`）、三份 BootROM md5/size、toolchain md5；生成命令与身份另存证据。
2) 计数自洽：独立审计脚本从 JSON 行重算后与 JSON `counts`、Markdown 计数表、非 AGREE 行逐项比对一致；`GEM5_ONLY_FAIL=0`；`DIFF=0`；14 条前红行逐条复核为 `AGREE_PASS`。
3) Node 历史归类：README 明写 `GEM5-016t`/`QEMU-080t` 的 Node `inst`/`embench` = 历史，不计入 M11 Node 验收；M11 Node 只验收 `arch`（cfx/arch/PTW/模式）；Node 不跑 Embench；Tiny（system/bare-metal，`run_embench_e2e.py`/`make test-m6`）与 SE（`check-tset-embench-full`）归属写明。
4) 反例可达 FAIL：计数 249→250 ⇒ 审计 rc=1；删一行 ⇒ rc=1；README 反写 ⇒ rc=1；`cp`+`md5sum -c` 还原后均回绿。
**新发现/坑**：① `GEM5-020t` 合入后 L1 转绿；此前 `check-patch-tree` 红是共享源树先于本分支补丁更新的暂态，非本任务文件（`git status` 仅本任务 4 文件）。② 重跑期间 `GEM5-020t` 评审反复重建共享 gem5，两轮整轮矩阵分别报 1499/232 issue 作废（中途二进制 md5 变化）；最终改用重建后二进制冻结副本 + 源树 `fs.py` 重跑 rc=0，作废日志在 `prev-failed-race/`。③ 防磁盘：全量重跑用 `prlimit --fsize=2G` + `timeout 7200`，无 orphan gem5，`-d cpu` trace 未失控。④ 驱动标题/证据指针仍硬编码 `GEM5-017t`，未改驱动（范围外），已在 README/证据注明。⑤ `tests/parity/README.md` 旧 Node embench 口径未改（范围外）。
**遗留问题**：① `GEM5-020t` 已合入，`make check` 本轮已 rc=0，无待复跑项；② `SPEC-187t` 退出码实现迁移后需再重生成一次；③ `tests/parity/README.md` 旧 Node embench 行待订正；④ 驱动标题/证据指针参数化待后续小任务。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查矩阵、README、审计脚本与证据脚本，finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 矩阵 14 条 `GEM5_ONLY_FAIL`（node/arch cfx/PTW/模式） | ⏸延后（跨模块，另立 gem5 任务） | README 写明根因=QEMU-083t 已改、gem5 未跟随；矩阵保留红行不伪装 | 审计独立重算 14/14；README 红项段；`m5_perm_badcombo` gem5 timeout、13 探针观察值不符 |
| F2 驱动标题/证据指针硬编码 GEM5-017t | ⏸延后（驱动不在任务范围） | README 明示实际证据脚本；README/完成区披露 | `git diff` 仅矩阵+README；生成文件未手改 |
| F3 `tests/parity/README.md` 旧 Node embench 口径 | ⏸延后（范围外） | 以 `tools/testcases/parity/README.md` 为准并披露 | 仅改任务允许文件 |
| F4 首次 `check-run-artifacts` 因 `.EXIT` 命名 rc=2 | ✅已修 | 证据日志改 `<任务号>-<用途>.txt` | 单跑与 L1 均 rc=0 |
| F5 `--matrix-only` 输出落在逻辑仓库路径被拒 rc=2 | ✅已修 | 证据脚本解析 `.work` 物理路径 | 重判 rc=1、14 行、计数一致 |
| F6 审计若复用驱动计数则无法发现手改 | ✅已修 | 独立脚本从 JSON 行重算三处比对 | 改计数/删行/改 README 三类注入均 rc=1，还原回绿 |
| F7 工具链 md5 全量重算慢 | ✅已修 | 默认路径+记录值，`--check-toolchain` 可选全量 | normal 33/33、inject 29/29 |

判决：代码/证据 finding 均已处置；F1 为引擎侧跨模块差距，已归因并保留现场，交 reviewer 判定。

#### 第 2 轮 engineer 自审（GEM5-020t 后重跑）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R2-F1 上一版 14 条 `GEM5_ONLY_FAIL` | ✅已修复 | 用 GEM5-020t 重建后二进制的冻结副本重跑；旧红矩阵移 `prev-red/` | 定点 node/arch rc=0（269/249/0/0/0/20）；14/14 转 `AGREE_PASS`，含 `m5_perm_badcombo_cfxreg` |
| R2-F2 注入锚点仍为旧计数 235 | ✅已修 | 证据脚本锚点改 249→250 | 注入 rc=1，还原回绿；`--inject` 30/30 |
| R2-F3 `make check` 因 `check-patch-tree` rc=2 | ✅已修复（`GEM5-020t` 合入） | 证据脚本删除“L1 应红”断言，改为断言 rc=0/日志 PASS/无 patch-tree 失败 | `make check` rc=0；normal 37/37；`--inject` 30/30 |
| R2-F4 math_test/llvm-ts 需保持 | ✅已复核 | 未改期望值 | math QEMU 0/76404、gem5 238/76404 BLOCKED；llvm-ts 214/214、blocked 0 |
| R2-F5 共享 gem5 被评审反复重建，整轮矩阵中途换二进制 | ✅已处置 | 冻结重建后二进制（md5 `d64b0f9`）+ 源树 `fs.py` 重跑；作废两轮落 `prev-failed-race/` | 最终全量 rc=0、`repro-check PASS`；作废轮分别为 1499/232 issue |

判决：矩阵与 L1 均全绿（`GEM5-020t` 已合入）；R2-F3 已关闭；证据 normal 37/37、`--inject` 30/30。

#### 第 1 轮 reviewer 验收

**重跑（任务 worktree、相对路径，真实 rc，均为我方执行）**
- `make check-tests-index` **rc=0**（241 条 PASS）；`make check-case-ledger` **rc=0**（1997 条 PASS）；`make check-run-artifacts` 首轮 **rc=2**——根因是我自造日志名 `rev-098t-*.log` 违反 A3 命名（非交付物缺陷），改名 `TESTCASES-098t-review-*.log` 重跑 **rc=0**（2956 文件/0 illegal，重试 1 次）；`make check`(L1) **rc=0**，`repository checks (L1): PASS`、无 `check-patch-tree` 红。
- 运行期证据脚本 **rc=0，checks=37 failed=0**（`repo: 任务 worktree`；validator pre rc=0、`repro-check: PASS`、`run_parity: PASS`、rejudge 计数一致、4 门控 rc=0、三类注入 rc=1 后 md5 还原回绿）；`run.sh --inject` **rc=0，30/30**。
- **独立反例注入（我方，249→247，非复用 engineer 锚点）**：`run.sh` **rc=1**（`run.sh: FAIL`，validator pre rc=1 `committed matrix md5 == generated matrix md5`）→ `cp`+`md5sum -c` 还原（`fe035c6b…`/`096b7166…` 均 OK）→ 重跑 **rc=0，37/37**。

**独立复算（不采信完成区叙述）**
- 由 `matrix.json` 行重算：node/arch 269=249+20；node/inst 1014=965+5+44；tiny/arch 269 全 N/A；tiny/inst 1014=1005+5+4；tiny/picolibc 20=17+1+2；`GEM5_ONLY_FAIL/DIFF/QEMU_ONLY_FAIL/AGREE_FAIL` 全 0。md 侧：计数表逐行 total==各类之和；非 AGREE 行 **350 == JSON 350**（node/arch 20、node/inst 49、tiny/arch 269、tiny/inst 9、tiny/picolibc 3）。
- 14 条转绿：`prev-red/generation-red-2026-11-05.log` 恰 **14** 条 `FAIL: GEM5_ONLY_FAIL`，名单与 `former-red.txt` 14 条一致；JSON 中 14/14 `AGREE_PASS`，`arch/umon/m5_perm_badcombo_cfxreg` 双侧 **PASS/exit=83**（原始 `run-frozen2/arch-node-{qemu,gem5}.json` 同为 PASS/83；`probe-044t-cfxreg_badcombo` 双侧原始日志 `RESULT: PASS` rc=0）。全表 0 行「QEMU PASS 而 gem5 非 PASS 却记 AGREE_PASS」；`KNOWN_GEM5_BLOCKED={}`、`PICOLIBC_KNOWN_BLOCKED` 仅 math_test。
- 不降级：`math_test` 仍 `BLOCKED_SIDE`（QEMU PASS/0、gem5 BLOCKED/1），原始日志 QEMU `0 errors/76404`、gem5 `238 errors/76404`，未入 AGREE_PASS；llvm-ts 夜跑 `2026-11-05-13` static/dynamic 各 `222−8=214`、pass 214/fail 0/blocked 0、closure/classification ok，`make check-night-report` **rc=0**（manifest 4 行全 rc=0）。
- 引擎身份实测：gem5 冻结副本 `d64b0f9…`（==当前共享构建）、fs.py `dde8e3e5…`、源树 HEAD `1ad69d2…`==记录、QEMU `0a3b8ff6…`、三份 BootROM md5+size 全一致；`run-frozen2` 761 文件在位、exit 文件 0；矩阵 md5 **`fe035c6b…`** == 证据 `matrix.md` == `matrix.md5` 记录（未手改）。
- 范围/快照：`git diff --name-only master...HEAD` 恰 4 文件，无 `spec/`、`contracts/`、`tests` 期望值、`Makefile`、`components/` 改动；验收前后 `git status` 一致（worktree 仅本任务书 6 行未提交、主树 clean），与完成区「修改文件」对账一致。

**约束逐条**：现场重生成、计数自洽、Node 历史归类（README 五要素齐全）、math 不降级、llvm-ts 纳入说明、4 门控 rc=0、反例可达 FAIL+还原、完成区 18 行 ≤30 且无运行期路径、状态 `待验收`、含「退出码迁移后须再重生成一次」、遗留③④（`tests/parity/README.md` 旧口径、驱动硬编码 `GEM5-017t`）已登记 —— **全部守住**。

**findings（文档级，不阻断，交 architect 收尾）**：F1 `milestones.md` 流水行仍写「make check 待 `GEM5-020t` 补丁合入」，与现场 L1 rc=0 不符（登记时点早于最终复跑）。F2 矩阵尾 `Evidence script: 驱动硬编码的旧证据脚本指针` 为驱动硬编码**悬空指针**（该路径不存在），README 已披露并登记遗留④。F3 验收 1「矩阵含命令」：矩阵内仅 `Generated by run_parity.py`，完整生成命令在证据 `cmd.txt`（run.sh 第 0 段回显，含 worktree HEAD/分支/rc=0），信息链完整，判文档级。F4 任务书完成区 6 行未提交（rc=2→37/37 更新），architect 提交须显式 staging 并与「修改文件」对账。F5 `run.sh` 的 `ROOT` 随调用路径解析，须从 worktree 相对路径调用（否则审到 master 旧矩阵并报 FAIL，不会假绿）。

**采信声明**：未重跑全量引擎矩阵（约 2586 case，成本高）；「现场生成非手改」以生成日志/exit、证据 `matrix.md` 同 md5、`repro-check PASS`、`run-frozen2` 原始产物抽查比对为旁证，属采信 + 旁证，非逐 case 重跑。

**判决：Accepted**（我方重跑全部达标、约束无违反；架构师仍需终审）。

#### 收尾（architect，2026-11-05）

- F1：milestones 流水行已从“make check 待 GEM5-020t”改为 L1 已绿。
- F2：矩阵尾 `Evidence script` 为驱动硬编码旧路径，属悬空指针；已在遗留④/README 披露，另立小任务修驱动，不回写矩阵。
- F3：生成命令在证据 `cmd.txt`，矩阵 md5 `fe035c6b…` 一致。
- F4：完成区已显式 staging 提交。
- F5：证据脚本须从 worktree 相对路径调用，已记录。
- 判决 Accepted，状态置 `已验证`。
