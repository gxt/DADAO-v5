# m13-integ-004: riscv-tests 移植与差分

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-integ-001`
**可并行分片**：按套件 / 按指令族（实现标「待定」，派单前按节点实况定）
**状态**：已验证

> **范围调整（2026-11-10，architect 按 `integ-001` 先例）**：chipyard 核未就绪（`008`–`017` 未做）⇒ 本任务先做**移植 + qemu/gem5 两平台差分**，chipyard 列记 `N/A`（依据：`m12-chipyard-015` 未开始）；三平台填列由 `m13-integ-002/003` 或后续补齐。

## 背景

用户 2026-11-08：riscv-tests 的移植与调整放 M13。M12 只用 inst/tset 中已被 qemu/gem5 验证的子集。

## 目标

1. **移植**：riscv-tests 的裸机测试框架适配 DADAO（启动、退出、签名区、`tohost` 等价物）。
2. **子集选择**：按 DADAO 支持的非 cfx 指令族筛选可移植用例，逐条记录「移植 / 不适用 / 需改」。
3. **三平台差分**：移植后的用例在 qemu / gem5 FS / chipyard 上比对。

## 验收标准

1. 移植清单（可用/不适用/需改）逐条列名并可追溯
2. 移植后的用例三平台一致或差异逐条归因
3. 报告落 `.tao/knowledge/refs/m13-004-riscv-tests.{json,md}`
4. 门控同前
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 非范围

改引擎实现、改 spec/contracts

## 说明

- M13 主体任务**依赖 M12 的核实现完成**（chipyard 可用）；在此之前只做 `m13-testcases-001`–`003` 的长尾计时。
- 差分产物归属以 `m13-integ-001` 的结论为准。

## 硬约束

1. 临时目录 `/tmp/opencode/m13-integ-004/`；禁仓库内临时文件。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存运行期日志目录；命令在 worktree 根内、相对路径。
6. 单任务单机；节点操作后 `make sync-node-repo`。
7. 不要删除其它任务的临时目录。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查：`extract.py`（分类/表达式/独立 oracle 交叉校验/`--check`）、`gen.py`（DADAO 映射/签名区/退出码/注入）、
`run_riscv_tests.py`（两引擎命令/判定/清理/指纹）、`verify_cases.py`（独立模型/结构）、框架宏、报告与证据脚本。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| 1 | guest 注入时宿主 oracle 也被改坏，无法区分「guest 自检失败」与「宿主判据失败」 | ✅已修 | `gen.render` 的 `expected_sig` 改从原始 case 取，注入只改 guest 常量 | guest 注入：`signature_ok=True`、`exit=66`；host 注入：`exit=0`、`signature_ok=False` |
| 2 | `gen.emit` 有未用形参 `index`，load_rd 又做一次冗余 tab 处理 | ✅已修 | 删形参；直接拼接已带 tab 的行 | `py_compile` + 全量差分 35/35 |
| 3 | `run_riscv_tests.py` gem5 版本取成 usage、`GEM5_CONFIG` 死常量、注入运行不清理工作目录 | ✅已修 | 从 gem5 启动横幅正则取版本；删死常量；`--keep` 之外一律清理 | JSON `gem5=25.1.0.1`；注入后目录自动清理 |
| 4 | `verify_cases.py` 未拒绝「磁盘上多余、清单未声明」的 case 文件 | ✅已修 | 增加 declared/on_disk 集合对账 | 正常 PASS；`--inject` rc=1 |
| 5 | 报告误称 L2 已跑 | ✅已修 | 改为 BLOCKED（`check-arch-smoke→install-host` 触发全量 LLVM 构建），并列外部红项 | `check-test-reports` PASS |
| 6 | 证据脚本 TMP 落在仓库根、期望失败被当成失败、报告路径正则过宽 | ✅已修 | TMP 移到忽略目录；`report` 支持 want=1；正则对齐门控 | 证据 15/15 PASS；`git status` 无残留 |
| 7 | 报告缺首行快照 marker | ✅已修 | 首行 `<!-- 现场生成，勿手改 -->` + 数值来源说明 | `check-test-reports: PASS (5 report(s), 3 snapshot(s))` |

判决：未修 finding = 0；任务转 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-11，全部本人实跑，worktree 根 + 相对路径）

**判决：Accepted**（5 条非阻断 finding 见末尾，交 architect 收尾处置）。退出码均取命令自身（`cmd; echo $?`），原始输出留 `.work/log/testcases/m13-integ-004-reviewer/`。

**重跑记录**
1. 证据脚本 `bash .work/evidence/m13-integ-004/run.sh` ⇒ **rc=0**、`PASS (14 passed, 0 failed)`；内含 `run_riscv_tests: PASS (35/35)`、`count total_cases: expected=474 actual=474`、`check-test-reports: PASS (5 report(s), 3 snapshot(s))`、`check-tests-index`/`check-no-residue`/`check-generator-sync`/`py_compile` 全 rc=0；`extract_check` 因本机无上游检出为 `[SKIP]`（工程侧 `evidence.log` 为 `PASS (15 passed…)` + `extract: PASS (114/114/35)`，完成区 15/15 有据）。
2. 本人另跑 `run_riscv_tests.py --only rv64ui/add|rv64um/mulh|rv64ui/srlw --keep` ⇒ 3 例 rc=0，qemu/gem5 console `cmp` **字节全等**（md5 `bd2feacd…`/`afb0c192…`/`cc75543d…`）；行数 15/6/24 与 `cases/*.yaml` 的 expected 逐行相等，且与我**独立另写**的 RISC-V 模型（sext32 / `>>64` / 截断除）逐行相等。
3. **独立注入（改被测产物）**：`cases/rv64ui/add.yaml` expected `…000a→…000b` ⇒ **同一 run.sh rc=1**（`verify_cases`/`differential`/`restore_green`/`json_counts` 4 项 FAIL，`passed_files expected=35 actual=34`）；`cp` 还原 + md5 仍 `2bbcb95019d3d1ad002fc38124aec89b` ⇒ 同脚本 **rc=0**（14 passed），`git status --porcelain -uall` **0 行**。另：单改产物后 `verify_cases` rc=1、`run_riscv_tests` rc=1（qemu rc=68=`0x40|4`），还原后均 rc=0。
4. L1 本人重跑：`make check` ⇒ **rc=2**；单独 `make check-knowledge-refs` ⇒ rc=2（唯一违规 = 他任务 `m13-testcases-008-208接跑B组差集.md:17`）、`make check-temp-dirs` ⇒ rc=2（5 项全为他任务目录）、`check-patch-tree` ⇒ 21 项全在 `components/{qemu,gem5,chipyard}` 共享树 ⇒ **3 红确为外部项**，与本任务 50 文件改动无交集。
5. L2 实证：`check-modules.log` 有 `_locked-check-arch-smoke: install-host build-bootrom` → `ninja -j8 -C .work/build/llvm` `[1/3573]…[1717/3573]` 后 `Terminated`；`check.log:447` `SKIP (no build-tree clang at .work/build/llvm/bin/clang)` ⇒ 根因 = 任务 worktree 缺 `.work/build`、`build-mc` 从零配置；现 `.work/` 仅 `evidence`/`log` + `source` 符号链接，构建树已清、未占共享安装根。
6. oracle 溯源（禁实现当期望）：`curl` 取上游 pinned commit `0494f954` 的 7 个文件 sha256 ⇒ **7/7 与 `upstream-index.yaml` 相等**；`rv64um/mulh.S`、`rv64ui/srlw.S` 宏逐条对上（testnum 与期望值全等，且恰排除 `SRC*_EQ_DEST/BYPASS/ZEROSRC/ZERODEST`）；`verify_cases.py` 不 import `extract/gen`、以独立语义模型复算 474 条。

**约束核验**：清单 114 = 移植 35（rv64ui 28 + rv64um 7）+ 需改 57 + 不适用 22（18 `amo*` + 4 `rv64si`），与报告 §3、`refs/*.json` 一致，逐行有 reason、port 均有 DADAO 映射、非 port 无 cases；按 `SimRISC-04` 核对 `mul.{so,uo} {rdHA=高64, rdHB=低64}`、除零/`INT_MIN÷-1` 定值表、`srlw/sllw/sraw` 的 W 位结果符号扩展 ⇒ gen 映射正确（`mulh/mulhu` 双目的换序、`ext.so 31` 皆对）；`SimRISC-12` 原子仅 `lr/sc`、全仓无 `amo*` ⇒ `na` 成立、`lrsc→rewrite` 自洽；退出码 `0` / `0x40|(n&0x3F)` ⊂ `Machine-v5 §7.1` guest FAIL 段 `0x40–0x7F`，与 `ADR-0020 D8` 一致（注入实测 rc=66/68），参数块 `0x20026`=`ADP_Stopped_ApplicationExit`（`set.zw` 清其余 48 位，`SimRISC-03`）；签名区 `ENTRY=0xFFFFFF010100`（spec §6）+`0x4000+8×24=0xFFFFFF0141C0` ∈ SRAM `0xFFFF_FF00_0000`+8 MiB，镜像 blob `0x2030`（img 8496 B）⇒ 代码<0x2000、STR/TBL/BUF/签名不重叠，`EXIT_BLOCK=0xFFFFFF7E0000` 亦在 SRAM；报告首行 marker + 册头四要素齐、无运行期路径，`docs/README.md:38`、`tests/README.md:71` 索引在位（`check-tests-index` rc=0）；完成区 5 行、无运行期路径；`git show --stat` 50 文件 = 完成区声明 49 + 任务书，无 Makefile/contracts/spec/`tests/{inst,unit,tset}` 改动，HEAD = architect WIP（engineer 未 commit）。

**非阻断 finding**：① 完成区「15/15（20 项）」在 fresh-clone 下实为 14 + `[SKIP]`，建议注明依赖已清理的上游检出；② 报告 §2/`tests/riscv-tests/README.md`/`dadao_test.inc` 称「BootROM 设置 SP 后跳入」，spec §6 为「crt 在入口设置 SP」且本镜像无 crt（测试不建栈、两引擎 rc=0，无行为影响），改措辞；③ `dadao_test.inc` 头注释列 6 个 `--defsym` 常量，实际只注入 `ENTRY`/`EXIT_BLOCK`（其余为 `gen.py` 内偏移）；④ inventory `auipc` 理由里「`aip.si` 以 4 KiB 为单位」与 auipc 同粒度、非差异点（真差异是结果落 RB bank、无 `lui/auipc` 组合）；⑤ `check.log`/`check-modules.log`/`run.log`/`evidence.log` 落 worktree 根（`*.log` 被 ignore、`check-no-residue` 不报），未入运行期日志目录，收尾随 worktree 删除或移 `.work/log/testcases/`；⑥ `/tmp/opencode/m13-integ-004-{g,h}.json`（guest/host 注入的 JSON，00:23）落在任务临时目录**之外**，与硬约束 1 不符，收尾删除（reviewer 未代删，保留现场）。

## 完成区

**测试结果**：证据脚本 15/15 断言 PASS（20 项输出含计数断言）；qemu/gem5 差分 35/35 文件 `AGREE_PASS`、474/474 例签名一致、`DIFF=0`；独立 oracle 复算 474 例全中；guest/host 两类注入均 rc=1、还原后 rc=0；`check-test-reports`/`check-tests-index`/`check-no-residue`/`check-generator-sync`/`py_compile`/`extract --check` 全 rc=0。L1 全量 `make check` rc=2：3 红均 master 同红外部项（`check-patch-tree` 共享源码树未合入改动、`check-knowledge-refs` 他任务任务书具体运行期路径、`check-temp-dirs` 他任务超龄目录）。L2 `check-modules` BLOCKED：`check-arch-smoke→install-host` 在本 worktree 触发全量 LLVM 构建，20 min 未完成；已清本地构建树（未占共享安装根）。
**修改文件**：`tests/riscv-tests/{README.md,upstream-index.yaml,inventory.yaml,framework/dadao_test.inc,cases/rv64ui/*.yaml(28),cases/rv64um/*.yaml(7)}`；`tools/testcases/riscv_tests/{extract.py,gen.py,verify_cases.py,run_riscv_tests.py,README.md}`；`docs/TestReports/M13-riscv-tests移植与差分.md`；`.tao/knowledge/refs/m13-004-riscv-tests.{json,md}`；`docs/README.md`（索引 1 行）；`tests/README.md`（目录地图 1 行）。
**验收结果**：清单 114 = 移植 35 + 需改 57 + 不适用 22（逐条名见 `inventory.yaml` 与报告 §3）；chipyard 列 `N/A`（`m12-chipyard-008/009/010/011–015` 均待开始）；报告落 `docs/TestReports/M13-riscv-tests移植与差分.md`（首行 marker、册头四要素），原始逐例 JSON 不入库（Process-09 §15）。
**新发现/坑**：上游 `BYPASS`/`SRC*_EQ_DEST`/`ZERODEST` 是 RISC-V 微架构/`x0` 别名测试，不属 ISA 可见值；`rd0` 作目的在 DADAO 是 ILLI，不能机械移植。gem5 Tiny 要求 BootROM 恰为 64 KiB（短 trampoline 会 fatal），本驱动按 profile 补齐。签名区 + semihosting 控制台可在两引擎逐字节对账，比只看退出码更可归因。
**遗留问题**：L2 本 worktree 未能跑完（见测试结果）；`rv64um` 的 `mulw/divw/divuw/remw/remuw/mulhsu` 与 FP、原子仍为「需改」，需后续任务按契约派生；chipyard 列待核就绪后补齐。

#### 收尾（architect，2026-11-11 03:07）

- reviewer **Accepted**：清单三分 114 = 35 + 57 + 22 逐条成立（`amo*` 无对应、`lrsc` 需改自洽）；`35/35 AGREE_PASS`、`474/474` 签名一致，reviewer 另写独立模型复算 3 例全中。
- **oracle 独立**：期望来自上游 pinned commit `0494f954` 的宏常量（7/7 sha256 与 `upstream-index.yaml` 相等），`verify_cases.py` 不 import `extract/gen`，未拿引擎输出当期望。
- 注入：翻 `add.yaml` expected ⇒ 同一脚本 4 项 FAIL（qemu rc=68=`0x40|4`）⇒ 还原回绿。
- **L2 BLOCKED 已核实根因**：任务 worktree 缺 `.work/build` ⇒ `install-host → build-mc` 从零配置 LLVM（3573 目标）；本任务未触碰 L2 载体。替代验证：合并后在主工作树跑 `make check-modules`（判 up-to-date）。
- 非阻断（转 `ISS-376`）：fresh-clone 下 14+SKIP（依赖上游检出）；「BootROM 设 SP」措辞与 §6（crt 设）不符；`dadao_test.inc` 注释 6 个 `--defsym` 实只 2 个；`auipc` 理由措辞；4 个 log 落 worktree 根未入运行期目录；2 个 `/tmp/opencode/m13-integ-004-*.json` 越界（收尾已删）。
