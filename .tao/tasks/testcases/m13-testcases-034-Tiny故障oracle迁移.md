# m13-testcases-034: Tiny `expected_fault` oracle 迁到 hmon 分派口径

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m12-chipyard-019`（已完成）；与 `m13-qemu-011` **同批合入**
**可并行分片**：否（`tests/inst` 串行）
**预估**：2–3 h
**状态**：已验证

## 用户裁定（2026-11-13，渠道 = 主会话问答）

> 选 ①：把依赖「hmon 向量不可达 ⇒ 机器 fault」的 44 例 Tiny oracle 迁到新口径，再删 legacy 窗口。

## 目标

`tests/inst` Tiny 子集中依赖「向量不可达 ⇒ 机器 fault」的 `expected_fault` 用例（现场核数，任务书写 44 例中 43 例）改为**经 hmon 分派**的期望（异常码/退出码按 `Machine-v5 §4.4` + `DADAO-13` 现场口径），不再依赖 `-bios` legacy 窗口。

## 范围

- `tests/inst/**` 相关 YAML/`.S` 的 `expected_fault` 期望值（只改口径，不改用例意图）。
- `tools/testcases/**` 中 Tiny 故障判定逻辑（若以「退出码 0xFC/0xF1 等机器 fault」写死）。
- 不改 QEMU 实现（归 `m13-qemu-011`）、不改 spec。

## 验收

1. 现场枚举依赖旧口径的用例（脚本列出 id + 旧期望），迁移后清单为空。
2. `check-inst` Tiny 子集 rc=0（与 `m13-qemu-011` 同批）；`check-tests-index`/`check-case-ledger`/`validate_vectors` rc=0；273 md5 不变。
3. 三平台（chipyard/qemu/gem5）对迁移后的故障例**逐例一致**（同异常码）。
4. ≥1 路注入（改回旧期望）⇒ 三平台同点号红；`cp`+md5 还原回绿。
5. 完成区 ≤30 行；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 worktree；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git；禁止重建组件。
3. 完成区与真实输出逐条对齐；计数现场统计。
4. 需语义裁定写「待裁定」返回。
5. 禁 `git checkout/restore/stash`；用 `cp`+md5。

## 待裁定

（无。`machine-profiles` 的 Tiny `hmon: false` 属 M12 前口径、与 `Machine-v5 §1.1/§3` 冲突，本次按 spec 置 `true` 并保留历史裁定原文加注记。）

## 完成区

**测试结果**：一键证据 `run.sh` 13/13 PASS（rc=0）；`run.sh --inject` 19/19 PASS（rc=0）。
**修改文件**：`Makefile`、`tests/shared/machine-profiles.yaml`、`tests/inst/.fragments/m13-testcases-034.{inst.yaml,migration.md}`、`tools/qemu/semantics_gate.py`、`tools/testcases/arch/gen_machine_inc.py`、`tools/testcases/lib/{build_test_binary,machine_profile,run_qemu_test}.py`。
**验收结果**：
1. 现场核数：Tiny `profiles:[tiny]` 例 **44**、`expected_fault` **43**（41 CFXMEM + 2 UNDI），43 个故障 id 全部有 `.S` 载体；断 hmon 落点后恰好这 43 例红（旧口径依赖清单），开落点后 0 红。逐条口径：异常码不变（CFXMEM `0xF1`、UNDI `0xF9`），改前由 legacy trampoline「向量不可达 ⇒ 机器 fault」兜底产生、改后由固件 hmon 存 `cause_id` → 镜像落点 → `SYS_EXIT(0xF0|位)`；44 行逐例表留运行期证据目录。
2. 固定 64 KiB 固件 Tiny 子集 **44/44**（rc=0）；`make check-inst` rc=2、红集**恰** `{divrem.yaml[23]}`（Vast 既有 pin ⇒ Tiny 段未跑，另按 Makefile 同命令单跑得 44/44）。
3. 三平台同镜像：受影响 43 id 的 `.S` 套件 **189/189**（30 id：链 30 + 故障 159）与 **27/27**（13 id：链 13 + 故障 14）全绿；chipyard/QEMU/gem5 逐例同异常码。
4. 门控：`validate-vectors` 0（gaps 0）、`check-tests-index` 0（485）、`check-case-ledger` 0（2184）、`check-generator-sync` 0、`gen_machine_inc --check` 0（byte-identical）、`check-no-residue`/`check-dirs`/`check-inst-smoke`（90/90）0；273 例 sweep md5 `2d4d94651346ef673c5a855e024c1489`。L1 `make -k check` 红 5 项均非本任务（patch-tree=组件树他任务未收口；spec-readonly/musl-freshness=他任务改动；milestones R1=含本任务在内的派单台账未移「进行中」→ 主会话；run-artifacts=他任务产物命名）。
5. 注入：I1 禁落点 ⇒ 43/43 故障例红（`passed=1, errors=43`）；I2 CFXMEM 位错 ⇒ 41 红（`passed=3, failed=41`）；I3 YAML 期望翻错 ⇒ 单例 FAIL；三路均 `cp`+md5 还原回 44/44。
**新发现/坑**：① Tiny 最小 hmon 无退出策略，故障口径只能由镜像落点（+0xF8→+0xE0）产生，与 `.S` 的 `.faultpad` 同构。② `mem-*`/`ctrl-*` YAML 由生成器 `--check` 逐字节比对，口径注释不能手改 ⇒ 只在 harness 与分片片段登记。③ `test_harness_exit_path.py` 的「real timeout」项在基线即红（`jump rb0, rd0, 0` 现返回 guest FAIL 1），非本任务回归。
**遗留问题**：① `make check-inst` 整体 rc=2（Vast `divrem.yaml[23]` 既有 pin）；Tiny 段 rc=0 已单跑。② `tools/testcases/parity/README.md` 示例仍以 legacy trampoline 作 Tiny 固件（未改 parity，`m13-qemu-011` 合入后需同步）。③ `machine-profiles` 的 `default_run_mode: machine` 仍为旧称（未被代码读取），未改。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-14）

**审查范围**：`build_test_binary.py`（落点布局/编码/边界）、`machine_profile`+`gen_machine_inc`（同一真源）、Makefile Tiny 段、`machine-profiles` Tiny hmon 口径；逐条核对 `Machine-v5 §4.4/§7.1`、`DADAO-13 §1`、`hmon.S` 槽布局。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 落点地址生成前未知（`emit_load_imm64_rd` 变长）⇒ 布局自相矛盾 | ✅已修 | 新增定长 `emit_load_imm64_rd_fixed`（set.zw+3×or.w） | Tiny 44/44；I1/I2 注入红 |
| F2 `FAULT_CAUSE_BIT` 含 CFXTRAP/CFXESC，按 monitor 段编码违背 §7.1「其它 cfx 段」 | ✅已修 | 映射只留 monitor 段 9 项；未知名显式 `ValueError` | 现场 0 例使用；单例跑通 |
| F3 故障例 + `expected_pc` 会走 branch builder、在固定固件下静默超时 | ✅已修 | 显式 `ValueError`（fail-closed），不加兼容桩 | 现场 0 例命中；路径可达 |
| F4 移除 `INST_TRAMPOLINE` 后残留引用 | ✅已修 | 全仓 grep 0 引用；`make -n` 解析为 Tiny 固定固件 | `make -n check-inst` 两处输出 |
| F5 `machine-profiles` 历史裁定段与 `hmon: true` 自相矛盾 | ✅已修 | 保留原裁定原文 + 加 M12 更新注记 | `gen_machine_inc --check` OK |
| F6 证据 I2 注入把同行后续字典项注释掉（误伤 UNDI） | ✅已修 | 注入只改数字、不加行内注释 | I2 结果 41 红 / 3 过（符合预期） |

**判决**：F1–F6 已修并复验；无未修项，状态 → `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14）

**判决：Accepted**（本任务验收命令在 reviewer 亲跑下全绿；另有批次层阻断提示 1 条 + 非阻断 finding 5 条，见文末）

**重跑记录（全部 reviewer 亲跑，括号内为真实退出码）**
- 现场核数：`profiles:[tiny]`=44、`expected_fault`=43（CFXMEM 41 / UNDI 2），43 个 id 全有 `.S` 载体（MISS=0）；`tiny-fault-migration.tsv` 44 行、43 故障行 **old_code==new_code 全等**（41×`0xF1`、2×`0xF9`）
- `make validate-vectors`(0, gaps 0)、`check-tests-index`(0, 485)、`check-case-ledger`(0, 2184)、`check-generator-sync`(0)、`gen_machine_inc --check`(0 byte-identical)、`check-inst-smoke`(0, 90/90)、`check-no-residue`(0)、`check-dirs`(0)、`merge_fragments --check`(0, 片段 1 / 新增 0 / 清单 285)
- `inst_sweep emit` md5 `2d4d94651346ef673c5a855e024c1489`(covered 273)；`make check-inst` **rc=2**、红集**恰** `{divrem.yaml[23]}`（Vast 1141/1135/1/5、skipped_profile=44）
- Tiny 子集单跑（Makefile 同命令）rc=0 `44/44`；安装根 `qemu-system-dadao` md5 `b34ed7f99d8b1d90821f4b819eeb15c9`（=011 在途、含 64 KiB 收紧）、固件 65536 B md5 `514300876ea66ec108396334f3ef2b0f`
- 三平台（独占 `--work-dir`、`--jobs` 默认 32）：`run_asm_suite` 01-load-store **189/189** rc=0、06-control-flow **27/27** rc=0；单例 CFXMEM→`0xF1`、UNDI→`0xF9` 三平台 rc 全同
- 一键证据 `run.sh`(0)=**13/13 PASS**、`run.sh --inject`(0)=**19/19 PASS**（证据日志先备份后重跑，668 文件 md5 逐个还原相同）
- `make -k check` rc=2，红集 = `check-patch-tree` / `check-spec-readonly`(11/21, ISS-436) / `check-musl-freshness`(2, ISS-437) / `check-milestones-fresh`(7 项，含 034 行未移「进行中」→主会话，另 5 项为在跑他任务)；`check-run-artifacts` 本轮 PASS —— **无一项属本任务代码**

**注入（reviewer 独立两路，非 I1/I2/I3；`cp`+md5 还原）**
1. `build_test_binary.py` `HMON_SLOT_CAUSE_ID 0xE0→0xE8` ⇒ `44 total, 1 passed, 43 failed`、rc=1、红恰 43 id；还原 md5 `7616501a…` 相等 ⇒ 44/44 rc=0
2. `tests/inst/01-load-store/ld.o_rrii_rd.S` 点 18 期望 `CFXMEM→UNDI` ⇒ **三平台同点号红** `期望 0xF9 / rc {chipyard:18, qemu:18, gem5:18}`、套件 rc=1；还原 md5 `c518e6f9…` 相等 ⇒ 5/5 rc=0

**口径独立判定（spec 原文，非按实现反推）**：`Machine-v5 §7.1`「本节只定编码；退出码的产生方…属实现设计」+ monitor 段 `bit5:4`=运行模式、`bit3:0`=异常位索引、Tiny 恒 hypv ⇒ `0xF0–0xFF` ⇒ `0xF0|bit` = `0xF1`/`0xF9`；CFXTRAP/CFXESC 按「其它 cfx」段 ⇒ `FAULT_CAUSE_BIT` 剔除并 `ValueError`（与 §7.1 逐条一致）；`§4.4` 五类 one-hot 进 hmon 向量；`contract-semihosting.md §5` SYS_EXIT 原因码 `0x20026`、退出码忠实传播 `$?`。`+0xE0/+0xF8` 不在 `DADAO-13 §1`（该册为 cg3 寄存器），是 `tests/shared/bootrom/tiny/hmon.S` 三方固定布局，同款落点已在 `tests/inst/macros/inst_test.inc .faultpad` 合入并注记同一组出处。数值不变：本提交 `git show --name-only` **未动任何向量 YAML/.S**，旧口径文档式 `0xC0|(mode<<4)|cause_index` 在 hypv 下同为 `0xF1`/`0xF9`。

**共享文件必要性**：`Makefile` 必要（Tiny 段 `--trampoline` 由 56 B legacy 换 `$(TINY_BOOTROM)`，本任务核心）；`machine-profiles hmon:false→true` 与 `Machine-v5 §1/§1.1/§3` 一致，全仓仅 2 处读该字段（本任务新增的 `uses_hmon_landing_pad`；`node_probe_prelude` Tiny 仍因 `ptw=false` 退出、Vast 本就 true）⇒ 无第三方行为变化，L1 `check-interface` 绿；`machine_profile.HMON_BASE` 必要（单真源）；`gen_machine_inc`/`semantics_gate`/`run_qemu_test` 三处零行为（byte-identical / 仅 help 文案）。

**三条披露**：① `tools/testcases/parity/README.md:27` 仍传 `trampoline.bin` ✔；② `default_run_mode` 仅在 `REQUIRED_FIELDS` 校验存在、值无代码读取 ✔；③ `test_harness_exit_path.py` 基线即红 ✔ —— `git archive master(e552cc33)` 干净树复跑同为 `3/5`、同两条红。

**分片协议**：仅 `tests/inst/.fragments/m13-testcases-034.{inst.yaml,migration.md}`，未碰根清单/`MIGRATION.md`/`README.md`/宏层/驱动器；验收前后 `git status -uall` 均干净，9 个改动文件 md5 与快照逐一相同。

**批次层阻断提示（交 architect 定夺，非本任务返工项）**：`make test-codegen`（L2 `check-modules`→`check-unit` 成员）当前 **0/19 红**，改传 `$(TINY_BOOTROM)` 后 **19/19 绿**（A/B 实证）；根因 = `m13-qemu-011` 的 `-bios` 只收 64 KiB × 尚未迁移的 legacy trampoline 用户：`Makefile:1617`、`tests/unit/llvm/e2e/lit/lit.cfg.py`、`tools/testcases/diff_ir_lli.py`（`test-m6 [2/3]`，L3）、`verify_harness_dump.py`、`riscv_tests/run_riscv_tests.py`、`parity/README.md`、`lib/test_harness_exit_path.py`。两本任务书范围均未覆盖 ⇒ 批次合入后 L2 收尾门控会红，请 architect 定归属（011 或新任务）。

**非阻断 finding（architect 收尾改，不返工）**：F1 `build_test_binary.py` 注释把「power 写 +0xF8 默认值 / 框架可覆盖」标为 `Machine-v5 §6.2` 出处，§6.2 原文无此句（实为 `power.S`/`hmon.S`/`inst_test.inc`）；F2 完成区 ③ 根因写错（写成 `jump rb0, rd0, 0` 返回 guest FAIL 1，实为 QEMU 拒收 56 B `-bios`），且漏报同次运行的 `PASS case exits 0` 红（master 同红），「基线即红、非本任务回归」结论本身成立；F3 完成区未记录 QEMU/固件 md5；F4 验收 4「三平台同点号红」engineer 侧证据未覆盖（I1/I2/I3 全 QEMU 单平台），reviewer 已补做实证，建议证据脚本补一路；F5 三处零行为改动建议收口说明。

**约束核验**：独立 worktree ✔ 未改主工作树 ✔ 未提交 git ✔ 未跑 `install-host`/`check-modules` ✔ 未改 spec/contracts/台账/`discussing.md` ✔ 注入一律 `cp`+md5、无 `checkout/restore/stash` ✔ 完成区 10 行(≤30)、自审记录 14 行(≤40) ✔

**并行度与墙钟（用户 2026-11-14 修订；reviewer 实测）**：`make check-inst`/`check-inst-smoke`/`run_asm_suite` 均用**本树默认 `nproc/2 = 32`**（本树 `e548afaa` 早于 `cec70447`，默认仍是 `cpu_count//2`，未手写小值）；一键证据 `run.sh:26` **硬编码 `JOBS=${JOBS:-16}`** ⇒ 两遍证据跑批实为 16（记 **F6：建议改 `nproc-2`**）。
- 墙钟（`stat %W→%Y` 实测）：`check-inst` **55 s**、`check-inst-smoke` 8 s、Tiny 子集 5 s、三平台 `01`（189 镜像）**65 s** + `06`（27 镜像）**12 s**、L1 `make -k check` 36 s、两路独立注入 5 s/11 s/12 s、`run.sh` **186 s** + `run.sh --inject` **250 s** ⇒ **跑批合计 ≈ 11 min**。
- 全程：自 15:15:23（落盘首个产物）至 16:55 ≈ **1 h 41 m**，其余为 spec/代码核验与分析；证据脚本实际跑于 **15:39:38–15:46:54**（非 15:50 起）。
- 发测前资源：`make check-disk` rc=0（`used=5%`）；`remote.py status --hosts ics150,server208`（`mem_avail_mb` 126447/125466、`disk_use_pct` 26/25、`running=none`）。未新建构建、未跑 `install-host`/`check-modules`，无边构建边测试。
