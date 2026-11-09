# INTEG-059t: G3 完整 tset 双向一致性（static + dynamic）

**模块**：integ
**项目里程碑**：M11
**依赖**：`GEM5-023t`～`GEM5-028t`（SE 文件 I/O/时钟、信号、IPC/多进程、线程/TLS、动态装载器、文件映射）、`TESTCASES-103t`（预算）、`TESTCASES-104t`（动态驱动与 QEMU 动态基线）
**可并行分片**：按套件（libc-test / llvm-ts / embench）
**状态**：已验证

## 背景与目标

`ADR-0048 D4` 要求 SE 最终覆盖**完整 tset**，且 gem5 与 QEMU 同模式双向一致。前置能力补齐后，本任务做收口级一致性验证：

1. **完整 tset**：`libc-test` / `llvm-ts` / `embench`，**static 与 dynamic 两档**，在 gem5 SE 与 QEMU user 上逐 case 对照。
2. **一致性判据**（同 `ADR-0048 D2/D5`）：
   - 同 case 的 pass/fail、退出码、架构可见结果一致；
   - `gem5_only_fail` / `qemu_only_fail` / `diff` 逐条列名并归因；
   - `gem5 通过而 QEMU 未通过` 必须定位到 spec/实现/测试资产之一，不得直接接受。
3. **矩阵重生成**：`docs/TestReports/M11-三平台一致矩阵.md` 增加 SE 段（或新增 `matrix-M11-SE.md`），计数由脚本现场统计，不手改。
4. **预算口径**：复用 `TESTCASES-103t` 的按套件预算；`timeout` 单列，不计入 PASS/BLOCKED 能力项。
5. **收口证据**：完整报告（JSON + Markdown）落 `.tao/knowledge/refs/`；L1/L2/L3 + 夜跑观测记录。

## 范围 / 非范围

**在范围内**：`tools/testcases/tset/gem5-se-baseline/**`（扩展为完整 tset 双档）、`tools/testcases/parity/**`（SE 段）、`docs/TestReports/**`（矩阵快照）、`.tao/knowledge/refs/**`、本任务书、`milestones.md`。

**不在范围**：能力实现（前置任务）、spec/contracts、M11 `m` 册（收口任务另立）、`mprotect` 真权限与主程序 PIE（本轮登记为限制/backlog）。

## 验收标准

1. 三套件 × 两档 × 两引擎全量跑完，报告存在且可复算；计数现场统计。
2. `diff = 0`；`qemu_only_fail` 逐条列名（若有）；`gem5_only_fail` 逐条列名 + 归因；不存在「无归因的失败」。
3. `run_parity` 自检 rc=0；`node/arch` 269 例仍 0 diff；`check-inst`/`check-arch`/`check-gem5-decode`/`check_b6`/`check_b7` 绿。
4. 矩阵快照重生成且与报告逐列一致；`make check`（L1）、`make check-modules`（L2）rc=0。
5. 反例：把某 case 的期望状态改错 ⇒ 矩阵/对照报告 FAIL；`cp`+`md5sum -c` 还原回绿。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务是 **G3 收口**，其完成是 M11 `m` 册的前置；不包含 `m` 册本身。
- 动态线依赖 `GEM5-027t`；若动态仍有 BLOCKED，须按 `ADR-0048 D4`「不得降级」明确列出并给关闭计划。
- 跑全量耗时长（小时级），按套件分批、落日志/EXIT，避免与构建并行。

## 完成区

**测试结果**：一键证据 25/26 绿（唯一红 = L1，外因见遗留）；5 个点名门控全绿；L2、L3（8/8 成员）rc=0。
**修改文件**：`tools/testcases/parity/se_tset_matrix.py`（新）、`tools/testcases/parity/README.md`、`docs/TestReports/M11-三平台一致矩阵.md`、`docs/TestReports/M11-三平台一致矩阵-凡例.md`、`.tao/knowledge/refs/INTEG-059t-se-parity-summary.{json,md}`（新）、本任务书；运行期证据/日志未入库。
**验收结果**：
1. 矩阵重生成：FS 段 `tiny/inst` 1029=1020 pass+5 deferred+4 skip、`vast/inst` 1029=980+5+44、`vast/arch` 269/269 agree_pass（0 diff/0 blocked/0 gem5_only_fail）、`tiny/arch` N/A 269；SE 段 static/dynamic 双档齐全（每档 3 套件 × total/qemu_pass/gem5_pass/both/blocked/timeout/skipped + 差异名单）。
2. 归因：`gem5_only_fail` static 9（ISS-357 4 + 环境缺口 5：popen/spawn/vfork/execle-env/unix-smail）、dynamic 4（全 ISS-357）；`qemu_only_fail` 0/0；`blocked` 8/43 逐条列名（capability → owner）；`timeout` 97/93 单列；无未归因行（脚本 fail-closed）。
3. `run_parity --self-test` rc=0（10/10 注入判出）；`vast/arch`（原 `node/arch`，`m12-testcases-001` 改名）269 例 0 diff。
4. `check-inst` / `check-arch` / `check-gem5-decode` / `check-gem5-b6` / `check-gem5-b7` rc=0。
5. `make check-modules`（L2）rc=0；`make check-full`（L3）rc=0（8/8 成员）。
6. 反例：基线**副本**改 1 例状态 ⇒ 报告 rc=1 且报 `has no attribution entry`；换回原基线重跑回绿；基线 md5 前后一致（不触碰入库文件，无需还原）。
7. 完成区无运行期路径。
**新发现/坑**：
- gem5 SE loader 拒绝字节对齐 `.bss` 子段（`p_vaddr+p_filesz` 非 4 字节对齐，`process.cc:196`）：dynamic llvm-ts 7 例 blocked，QEMU 可装载 ⇒ gem5 侧限制，**未分配 issue**（建议登记 + 另立 gem5 任务）。
- dynamic `popen/spawn/vfork/execle-env` 与 static 4 例同源（guest root 无 DADAO `/bin/sh`，exec 回退宿主 ELF、PT_INTERP `/lib64/…`），非 ISS-357。
- static `Prolangs-C/unix-smail`：输出逐字节相同、仅 exit 69≠0（`/bin/lmail`、`/bin/smail` 无 DADAO 版；`-d` 对照 exit 0）⇒ 环境缺口第 5 例。
- `math_test` B7 在现引擎复测 0 errors（两次独立运行）；按约束**不改写为 PASS**，快照沿用上一版 picolibc 段并标注待裁定。
- FS 首轮 16 并发出现 `vast/inst` 1 例非 guest 停机（shim 125）；8 并发复跑与单独重放（2/2）均 ILLI 248 ⇒ 并发偶发，非缺陷。
- 新向量 `tests/inst/fp/convert.yaml`（15 例）使 inst 总数 1014→1029。
**遗留问题**：① L1 `make check` rc=2 全为外因：首个红 `check-patch-tree`（in-flight chipyard 任务改共享源，9 问题）；`-k` 排除该门控后再现 `check-milestones-fresh`（本任务派单行仍在「待开始」，台账归主会话、本任务禁改）、`check-run-artifacts`（当时 17 项：16 条非法名 + 1 项三件套缺失；reviewer 轮已 PASS）、`check-temp-dirs`（5 个他人遗留目录），其余门控全绿。② picolibc B7 去留裁定。③ loader 对齐缺口立 issue（超出本任务书范围）。

## 审阅记录

### 第 1 轮 engineer 自审

范围：`se_tset_matrix.py`（全文件）、两个 README diff、`matrix-M11.md` 重生成链路、证据脚本；逐行核对后以证据脚本复验。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 cross_mode 键 `case-set` 与 `case_set` 不一致 → KeyError | ✅已修 | 统一为 `case_set` | 报告生成 rc=0 |
| F2 注入函数闭包读外层 `tracks`，改的副本不参与重算（假失败） | ✅已修 | 改为 `analyse_docs(docs)` 全流程重算 | `--self-test` 8/8 判出 |
| F3 `skipped` 用 `discovered-total` 对 embench（19<38）得负值 | ✅已修 | 优先用声明 `excluded`，否则 `max(0, discovered-total)` | 报告 embench skipped=0 |
| F4 7 例 `process.cc` BSS 对齐 blocked 无 owner（基线报 12 项失败） | ✅已修 | 新增 blocked 规则 + `new_findings` 条目 | BASELINE PASS |
| F5 static=fail / dynamic=blocked 同源 5 例被当成「verdict 差异」报错 | ✅已修 | `join_modes` 按 owner 判等价（`same_owner_diff`） | 报告中 5 例归 `same_owner_diff` |
| F6 证据脚本把 `*.EXIT` / `*.out` 写进运行期日志目录（`check-run-artifacts` 判非法名） | ✅已修 | 改 `-exit.txt`、strace 改 `.txt`，旧文件改名 | L1 日志已无本任务非法名 |
| F7 `--list` 用默认 scopes（含 embench/picolibc）而矩阵只跑 inst/arch → 覆盖检查误红 | ✅已修 | 从 `matrix.json` 的 `profiles`/`scopes` 派生 `--list` 参数 | `fs-matrix-coverage` PASS |
| F8 承接块把 counts 行与明细行塞进同一张表（列数不一） | ✅已修 | 拆成两张表 + B7 口径行 | 快照渲染核对 |
| F9 `grep -c` 计数与字面量 "yes" 比较（恒 FAIL） | ✅已修 | 期望值改为 INJECT 总行数 | 16 项 parity 检查全绿 |
| F10 承接段用字面量 `20` 选 counts 行（改数即失效，且属写死计数） | ✅已修 | 改按列数（13/8 个 `|`）区分 counts/明细行 | 重组快照与入库文件逐字节相同 |

判决：无未修 finding；状态可置「待验收」。边界核对：未改 `milestones*.md`、spec/contracts、gem5/QEMU 实现、用例与期望。

### 第 1 轮 reviewer 验收

判决：**Accepted**（reviewer 判定 engineer 达标；architect 仍需终审）。以下输出全部为 reviewer 亲自重跑所得，非转述。

**重跑记录**
- 一键证据 `FS_DIR=<运行期证据>/parity2` + 证据脚本全量 → `rc=1`、`summary: PASS=24 FAIL=2`。24 绿含：se 自检 8/8、`se-report-vs-baselines`、repro 两次生成一致、case-set 声明、fs-list / fs-matrix-coverage / engine-identity、compose、`snapshot-matches-generators expected=7c108c64… actual=7c108c64…`、注入 `rc=1` + `has no attribution entry` + 回绿 + 基线 md5 `66e1f68e…` 前后不变、`run_parity --self-test` 10/10、decode/inst/b6/b7、**L2 rc=0**、**L3 rc=0**；2 红 = L1（外因）+ `check-arch`（见下）。
- **计数独立重算**（reviewer 自写脚本读两份已入库基线）：static 589 行 → `qemu_pass 587 / gem5_pass 474 / both 474 / blocked_all 105 − timeout 97 = 8 / gem5_only_fail 9 / qemu_only_fail 0`；dynamic 592 行 → `590 / 451 / 451 / 136 − 93 = 43 / 4 / 0`，与报告 `totals` 逐项相等。`se_tset_matrix.py` grep `587|474|451|590|1029|1020|980` **0 命中**（无写死计数）。
- **归因完整性**：attribution 行数 `gem5_only_fail=13(9+4) / blocked=51(8+43) / timeout=190(97+93) / both_non_pass=2 / qemu_only_fail=0`，owner 全落在 `OWNERS` 词表；`build_attribution` fail-closed（未分类、blocked 无 capability、证据无 owner、`gem5_only_fail` 无登记项均 rc=1）⇒ **不存在未归因行**。
- **独立反例注入**：把入库快照 `vast/arch agree_pass 269→268` → 重跑同一脚本 `rc=1`、`FAIL snapshot-matches-generators … actual=78e75a74…`；`cp` + `md5sum -c` 还原 → `rc=0`、`summary: PASS=16 FAIL=0`、快照 md5 复归 `7c108c64…`。
- **矩阵**：`run_parity --list --profiles tiny,vast --scopes arch,inst` `rc=0` → 269/1029/269/1029；对入库 FS JSON 逐行重算 → `vast/arch` 269 AGREE_PASS、`tiny/inst` 1020+5+4、`vast/inst` 980+5+44、`tiny/arch` 269 N/A，与快照逐列相等。
- **B7 复测（reviewer 亲自跑，同 ELF/argv）**：`run_parity --profiles tiny --scopes picolibc` → `picolibc/math_test` QEMU PASS/0、**gem5 PASS/0**、`Tested 76404 functions, 0 errors detected`、`GEM5_EXIT_CODE=0`；同一轮 `run_parity rc=1` 报 `gem5 must stay BLOCKED (B7), got PASS (blocked masquerade)`，登记与现状的矛盾由门控如实暴露。
- **L1**：reviewer `make -k check` `rc=2`，失败恰 3 项：`check-patch-tree`（9 problem，chipyard 在途改共享源）、`check-milestones-fresh`（A1+R1：本任务行在「待开始」而册=「待验收」——本工作树 HEAD 比声明基线少 1 个台账提交，台账归主会话）、`check-temp-dirs`（5 个他人目录）；`check-run-artifacts` 本轮 **PASS**。
- **`check-arch` 偶发（如实记录，不掩盖）**：全量重跑中 `check-arch rc=2`（`start_busy_returns_busy` 得 `0x62`=EXIT_BUSY_SECOND，即 BUSY 窗口过期）；随后 2 次独立 `make check-arch` 均 `rc=0` 且该探针 PASS（1 红 / 2 绿）。失败时另一会话正在共享树跑 `build-mc`/`install-host`；本任务 diff 不含 arch/QEMU/gem5/用例 ⇒ 判并发时序外因，日志已留运行期证据目录。

**约束核验**：改动 7 项与完成区「修改文件」逐项一致（`git status` 前后快照逐行对账、7 个 md5 审查前后相等）；未动 `milestones*`/spec/contracts/用例与期望；完成区 18 行 ≤30、无运行期路径；状态 `待验收`。

**findings（文档级，不阻断，architect 收尾提交直接改）**：① 完成区「static 9（ISS-357 **5** + 环境缺口 **4**）」实为 **ISS-357 4 + 环境缺口 5**（与同段「unix-smail ⇒ 环境缺口第 5 例」自相矛盾；dynamic 4 全 ISS-357 正确）；② 完成区「`check-run-artifacts`（16 条日志名）」在其当时为 17 项（16 非法名 + 1 项三件套缺失），reviewer 本轮该门已 PASS；③ 新 refs JSON 沿用基线 evidence 文本中的具体运行期证据路径字样（L1 该门只扫 `.md` 故未红，基线本就含 12 处同类字样）。

**待裁定（非本任务可决，不作放行前提）**：B7 注销须走「缺陷关闭式重登记」——先定位 238→0 的根因并确认为真修复，再删 `PICOLIBC_KNOWN_BLOCKED`、把 picolibc 段纳入现场重生成、同步两份 README 与 `GEM5-015t` 口径；**不得**就地把 BLOCKED 改写成 PASS。loader `.bss` 7 例应立 issue 归 `components/gem5`（判据：`process.cc:196` `(seg.base & 3) != 0`，同一 ELF QEMU 可装载）。

#### 收尾（architect，2026-11-09 15:06）

- 判决 **Accepted**（reviewer 14:13 完成；完成通知未送达，主会话按盘上事实收口）。
- 计数与归因独立重算一致（static 587/474/474/8/97/9、dynamic 590/451/451/43/93/4；`se_tset_matrix.py` 无写死计数）；归因 fail-closed，无未归因行。
- 矩阵：`vast/arch` 269/269、`tiny/inst` 1020+5+4、`vast/inst` 980+5+44。
- **B7 复测**：reviewer 亲跑 `math_test` → QEMU/gem5 均 `0 errors`，`run_parity` 如实报 `blocked masquerade`。**处置按 reviewer 建议**：注销须走「缺陷关闭式重登记」（先定位 238→0 根因 → 再删 `PICOLIBC_KNOWN_BLOCKED` → picolibc 段现场重生成 → 同步 README/`GEM5-015t`），**不接受就地改写**；另立任务。
- `ISS-359` 已立（loader 非对齐 `.bss`，7 例）。
- 3 条 finding 已修（ISS-357 4+5、check-run-artifacts 17 项）；③ refs JSON 的运行期路径字样 L1 不扫 `.json`，保留但记录。
