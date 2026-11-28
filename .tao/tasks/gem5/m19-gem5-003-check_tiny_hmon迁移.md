# m19-gem5-003: `check_tiny_hmon` 迁移到 Tiny 新几何与 hmon 数据区

**模块**：gem5
**项目里程碑**：M19
**依赖**：`m19-gem5-002`、`m19-testcases-002`、`m19-testcases-003`、`m19-testcases-005`
**可并行分片**：否
**预估**：2–4 h
**档位**：小改
**状态**：待验收

## 背景

`tests/unit/gem5/check_tiny_hmon.py` 及其资产（`tiny_hmon.S`、`expected.yaml`、`tiny_hmon_layout.inc`）仍按旧 Tiny 几何与被测固件约定写：

- 旧 64 KiB BootROM、8 MiB SRAM、入口 `0x10100`、表偏移 `0xE000`、`0x30001` 表头；
- hmon 数据槽 `0xD8/0xE0/0xE8/0xF0/0xF8`（spec 新数据区为 `0x0C00–0x0CFF`）。

`m19-gem5-002` 已把 gem5 Tiny profile 迁到新几何；`m19-testcases-002` 已改 `tiny_hmon.lds`；`m19-testcases-003` 已改 BootROM 构建器（表 `0x1F00`）；`m19-testcases-005` 定义 hmon 数据区子偏移。本任务把该 harness 与资产迁齐，使 `make check-tiny-hmon` 在新几何下真实跑通。

## 目标

1. `check_tiny_hmon.py`：BootROM 大小/表偏移/表头、SRAM 大小、入口 `0x2000`、DUMP `0x800`、image_window 128 KiB 全部按 profile/构建器现场取值，删除硬编码旧值。
2. hmon 数据区按 `m19-testcases-005` 定稿的 `0x0C00–0x0CFF` 子偏移；`tiny_hmon_layout.inc` / `expected.yaml` / `tiny_hmon.S` 与之逐项一致。
3. `tiny_hmon.S` 的 `escape` 语法漂移（LLVM 下无法汇编）如仍存在，按现行语法修好，或在本任务内明确记为依赖项（不得静默跳过）。
4. 运行：`make check-tiny-hmon`（或等价）在 gem5 新 profile 下 rc=0；`power → hmon → 应用` 与 CFXESC 帧两条路径都覆盖。

## 验收（逐条贴真实 rc）

1. `make build-gem5` rc=0；`make check-tiny-hmon` rc=0。
2. 镜像恰 8192 B；表项 `offset=0x800`、`size ≤ 0x0C00`；入口/DUMP/签名/EXIT 地址与 spec 一致。
3. hmon 数据槽读回：cause_id / cause_ip / cause_info / 返回地址 / 保存的 scratch 原值。
4. **可达 FAIL ≥2 路**：① 表偏移写回 `0xE000` ⇒ 红；② hmon 数据槽写回 `0xD8` ⇒ 红；均 `cp`+md5 还原回绿。
5. `check-tests-index` / `check-patch-tree`（gem5 段）真实 rc；基线红逐行对照。
6. 不改 QEMU/chipyard/testcases 固件；版本号未升。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/unit/gem5/**` 与必要索引；不接板；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：`make build-gem5` rc=0（增量链接，见「新发现/坑」）；`make check-tiny-hmon` rc=0（`check_tiny_hmon: PASS (250 checks, 50 records)`）；`make check-tests-index` rc=0（503 条）；`make check-patch-tree` rc=2 = **基线红**：gem5 段 19 行与主仓逐字相同（diff rc=0）；总 problem 数 88 vs 主仓 98，差 10 条 chipyard ⑥/⑨（主仓已合入 chipyard 003/004，源树 HEAD/status 未变）；运行期证据 `run.sh` **16/16 checks，rc=0**。

**修改文件**：`tests/unit/gem5/check_tiny_hmon.py`、`tiny_hmon/{tiny_hmon.S,tiny_hmon.lds,tiny_hmon_layout.inc,expected.yaml,README.md}`、`Makefile`（新增 `check-tiny-hmon` 目标，recipe `_locked-check-tiny-hmon`，列入 `GATE_LOCKED_TARGETS` 由 gate.lock 串行化；必要索引）。

**验收结果**：
1. 镜像恰 8192 B；表头 `DBOT/1/1/0x30001`、表偏移 `0x1F00`；hmon 表项 `type=1 flags=0x3 offset=0x800 size=0x540`；hmon code `0x53c`、段长 8 对齐 `0x540`、低于数据页 `0xC00`。
2. 入口/固定符号：`ENTRY=0xffffff002000`、`EXIT_BLOCK=0xffffff000030`、`DUMP_BASE=0xffffff000800`、`BOOTROM_BASE=0xffffffff0000`；geometry 14 项与 `fs.py --dump-geometry` 逐项相等（ROM 0x2000 / SRAM 0x40000 / hmon 0x2000 / image_window 0x20000 / DUMP 0x800）。
3. 路径①：guest exit `0x21`、console `hmon-ok`、record 0 为 power→hmon 的 CFXTRAP 现场。路径②：record 34 CFXESC `cause_id=0x8`、`cause_info=0x7efc0000`、`prev_cfx=0x3f`；record 35 monitor 未写（仍为 record 33 的 CFXTRAP，`+0x18=land_esc`）。
4. hmon 数据槽读回（`0xC00` 页）：cause_id/cause_ip/cause_info/return 及 `+0x20/+0x28` 保存的 rd63=`0x5a5a…`、rb63=`0x0badf00d…`；两寄存器返回后仍为原值（check 44–47）。
5. 可达 FAIL：表偏移注入 `0xE000` ⇒ `[FAIL] shared table inside image: expected=0xe000+0x30 <= 0x2000 actual=outside` + header FAIL，rc=1；旧槽注入 `0xE0/0xE8/0xF0/0xF8` ⇒ `[FAIL] hmon SRAM data slots (last fault): actual=('0x0','0x0','0x0','0x0')`，rc=1；均 `cp`+md5 还原（`d2f053f7…`）后回绿。
6. 未改 `components/gem5`、QEMU/chipyard/testcases 固件；版本号未升；`git status` 仅上述 7 文件。

**新发现/坑**：① lld 默认给 ELF 头生成 64 KiB 页对齐的 header `PT_LOAD`，落在 `0xffffff000000`（ENTRY 之下）会被新 loader 正确拒绝——链接脚本须显式 `PHDRS` 只留 app 段；② `escape` 已是 R3 语法（仅 `cfxHA`，`imms18=0`，返回点取 `cg5 rc10`），旧 `[excp_cause_ip,4]` 无法汇编；CFXESC 处理须先写 `rc10 = excp_cause_ip+4`；③ 现行 `cg5` 为 rc4/rc5 原因字段、`cg3` 为 rc14/rc15 向量/切换；④ 同目录 `tiny_hmon_min.S` 仍用旧槽（QEMU probe 资产，不在本任务范围，未改）；⑤ 为验收 #1 运行 `make build-gem5` 触发一次增量链接，`gem5.opt` md5 `341f…→0289…`，源树 HEAD/status 未变、geometry 仍为新值。

**遗留问题**：`tiny_hmon_min.S` + `tools/testcases/arch/min_rom_probe_integ007t.py` 的旧槽/旧几何迁移需另立任务（属 QEMU/testcases 范围）；`check-patch-tree` 的 gem5 段红为共享源树本地提交与补丁集漂移（gem5 段 19 行与主仓逐字相同；总 problem 数随主仓 chipyard 补丁集变动，当前 88 vs 98），非本任务引入。
**待裁定**：共享 `.work/source/gem5` 在并行会话窗口内被要求「只读不重编」，而验收 #1 要求 `make build-gem5`——本任务执行了一次增量链接；若批次要求完全禁跑该目标，请主会话在独占窗口复核后删除该条证据。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 7 文件 diff 与证据脚本，findings：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 链接脚本无 PHDRS ⇒ lld 生成 header `PT_LOAD` 落 `0xffffff000000`，loader 以「below entry」拒绝 | ✅已修 | `tiny_hmon.lds` 声明单一 `app PT_LOAD`，四段均 `:app` | 运行期镜像断言 PASS：唯一 PT_LOAD `[0xffffff002000,…)`；driver 读 `loads==1` |
| `escape` 旧第二操作数无法汇编 | ✅已修 | `escape cfx7` / `escape cfx_power`；`esc_land` 先写 `cg5 rc10=ip+4` | `llvm-mc` rc=0；CFXESC 记录 34/35 PASS |
| `record_esc_frame` 仍按旧 cg5 布局读 rc2/rc3/rc4 | ✅已修 | 改读 rc4 cause_id / rc2 ip / rc5 info / rc1 prev_cfx | record 34 四项 PASS |
| `cg3 rc8/rc10` 已迁 rc14/rc15 | ✅已修 | 向量写/读 rc15，switch_run_mode rc14 | check 3/4/36/39/40/41/42 PASS |
| hmon 槽仍 0xE0… / base 未加 0xC00 | ✅已修 | `rb22=HMON_BASE+HMON_DATA`，槽用 `HMON_SLOT_*`；check 脚本 `HMON_DATA_BASE+off` | 槽读回及注入旧槽翻红均 PASS |
| 「保存的 scratch 原值」无覆盖 | ✅已修 | 新增 sentinel + CFXMEM + 槽/寄存器回读 check 44–47 | 50 records 全 PASS |
| 几何仍硬编码（64 KiB/8 MiB/0xE000/0x30001） | ✅已修 | 全部改 `bld.*` / `prof.*`；新增 14 项 `fs.py --dump-geometry` 对照 | geometry 14/14 PASS |
| 负例 PT_LOAD 改写后段过大，命中「outside window」而非目标段 | ✅已修 | `patch_elf(..., mem_size=4)` | `targets the BootROM` / `targets the hmon SRAM` 两条 PASS |
| `make check-tiny-hmon` 目标不存在 | ✅已修 | Makefile 新增目标（不依赖重建，缺输入 rc=2） | `make check-tiny-hmon` rc=0 |

### 第 1 轮 reviewer 验收

**重跑（我本人在任务 worktree 根执行；rc 取被检命令自身退出码）**
- `make build-gem5` ⇒ rc=0，`scons: build/DADAO/gem5.opt is up to date`、`build-gem5: PASS`；`gem5.opt` md5 `028921ce…` 未变。
- `make check-tiny-hmon` ⇒ rc=0，`check_tiny_hmon: PASS (250 checks, 50 records)`，`[FAIL]` 0 条；`gem5 guest exit 0x21`、console `hmon-ok`、`GEM5_EXIT_CAUSE=semi:ADP_Stopped_ApplicationExit`；record 34 CFXESC `0x8 / 0x7efc0000 / prev 0x3f`、record 35 `monitor_unchanged`；geometry 14/14；镜像 8192 B、表头 `(DBOT,1,1,0x30001)`@`0x1F00`、表项 `type=1 flags=0x3 offset=0x800 size=0x540`、`ENTRY=0xffffff002000 / DUMP=0xffffff000800 / EXIT=0xffffff000030 / BOOTROM=0xffffffff0000`；`0xC00` 页四槽读回 + check 44–47（rd63/rb63 哨兵保存与恢复）全 PASS。
- `make check-tests-index` ⇒ rc=0（`PASS（503 条）`）；`make check-patch-tree` ⇒ rc=2（worktree `88 problem(s)`，gem5 段 19 行）。
- 运行期证据目录内的 `run.sh`，参数 `REPO=<本任务 worktree 根>` ⇒ `evidence: PASS (16 checks)` rc=0；两路注入分别 `FAIL (4/250)`（`[FAIL] shared table inside image: expected=0xe000+0x30 <= 0x2000 actual=outside`）与 `FAIL (1/250)`（`[FAIL] hmon SRAM data slots (last fault): actual=('0x0','0x0','0x0','0x0')`），`cp`+md5 还原 `d2f053f7…` 后回绿。
- `make check-knowledge-refs` ⇒ rc=0（写入本记录后已重跑）。

**独立注入（reviewer 自做，非 run.sh 已用两路）**：`tiny_hmon_layout.inc` 的 `HMON_SLOT_CAUSE_ID 0x00→0xE0`（注入前 md5 `80b626f6…`）⇒ `[FAIL] record count: expected=50 actual=0`、`make` rc=2（脚本 rc=1）；`cp` 还原 + md5 相等 ⇒ 再跑 `PASS (250 checks, 50 records)` rc=0，`git status --porcelain -uall` 空。

**约束核验**：`git diff --name-only` 仅 8 件（`tests/unit/gem5/**` 6 + `Makefile` + 本任务书），与完成区一致，未动 QEMU/chipyard/testcases 固件、版本号未升 ✓；Makefile 只增不改（`.PHONY` 追加、help 追加、新目标块，既有目标体 0 改动）✓；披露属实（证据目录内冻结 `gem5.opt` md5 `341ffd5e…` = 披露旧值、现行 `028921ce…` = 披露新值；源树 HEAD `c8c7f22`(11-27)、status 空）✓；`tiny_hmon_min.S` + `min_rom_probe_integ007t.py` 归 `m19-testcases-006`（其约束已点名该 py）✓；完成区 18 行、自审 15 行未超限 ✓。

**判决：Needs Revision**（1 条阻断 + 1 条文档级）
1. **阻断**：`check-tiny-hmon` 的 `--work-dir` 落 `$(TEST_ARTIFACTS_DIR)/tiny-hmon`（各 worktree 解析到同一主仓 `.dadao/tests`），却未列入 `GATE_LOCKED_TARGETS`。Makefile 自身注释写明「写 … SDK 产物目录 `$(TEST_ARTIFACTS_DIR)` 的目标全部串行化」；我脚本化扫全 Makefile，其余写该目录的目标（`build-bootrom`/`test-codegen`/`test-elf`/`check-unit*`/`check-arch*`/`test-m6`）全部已锁，本目标是唯一例外，其注释只给「不在 L1–L3」而无锁的豁免理由（对照 `check-wuming-cycles` 明写 "Read-only … stays outside"）⇒ 漏加；跨 worktree 并发会互相 `rmtree` 同一工作目录。**最小返工**：recipe 改名 `_locked-check-tiny-hmon` + `check-tiny-hmon` 加入 `GATE_LOCKED_TARGETS`（`check-writer-guards` S2a 只查 `build-*`/`install-*`，不因此转红），改后重跑 `make check-tiny-hmon` 与运行期证据 `run.sh`。
2. **文档级（随改一并修，不另开轮）**：完成区「88 problem 与主仓同命令逐行相同」在复核时点不成立——worktree **88** vs 主仓 **98**，差恰为 10 条 chipyard ⑥/⑨（主仓 `534f6b491`(09:10:24)、`7184e1b6e`(09:21:55) 改了 chipyard 补丁集，源树 HEAD 仍 11-27、status 空）；验收 #5 指定的 **gem5 段 19 行逐字相同成立**。建议措辞改为「gem5 段与主仓逐字相同；总 problem 数随主仓 chipyard 补丁集变动」。

**采信/未重跑**：无——上述命令均为我本人执行。

**返工处置（engineer，2026-11-28）**
1. 阻断 ✅已修：Makefile recipe 改为 `_locked-check-tiny-hmon`，`check-tiny-hmon` 加入 `GATE_LOCKED_TARGETS`（按既有 gate-locked 宏串行化，不新增 writer 条目）；`make check-tiny-hmon` rc=0（`PASS (250 checks, 50 records)`），运行期 `run.sh` 16/16 rc=0。
2. 文档 ✅已修：完成区「测试结果」「遗留问题」改为「gem5 段 19 行与主仓逐字相同（diff rc=0）；总 problem 88 vs 主仓 98，差值为 chipyard 段（主仓已合入 003/004）」。

### 第 2 轮 reviewer 验收

**重跑（我本人执行；rc 取被检命令自身退出码）**
- `make check-tiny-hmon` ⇒ rc=0，`check_tiny_hmon: PASS (250 checks, 50 records)`、`[FAIL]` 0 条；并发锁测试中的两次独立跑各 `250/0`、`record count 50/50`，证明共享工作目录未被互相 `rmtree`。
- `make check-writer-guards` ⇒ rc=0，`check-writer-guards: 27/27 PASS`（含 S2a `uncovered=0`、S2b `not-gate-locked=0`、S2c `unknown=0`）⇒ 新增锁未误伤 writer 表。
- 运行期证据目录内的 `run.sh`，参数 `REPO=<本任务 worktree 根>` ⇒ `evidence: PASS (16 checks)` rc=0；两路注入仍真红（`rc=1`），`cp`+md5 还原 `d2f053f7…` 与第 1 轮注入前值一致。

**并发锁（真实构造，非推断）**
- 进程 P1 `make check-tiny-hmon` `09:40:22.592 → 09:40:37.799` rc=0；同目标进程 B 于 `09:40:34.946` 起，日志首行 `gate-lock: WAIT … held by pid=2969960 … target=check-tiny-hmon, cmd=… _locked-check-tiny-hmon; waits up to 3600s`，随后 `gate-lock: ACQUIRED … after 2.6s` ⇒ **第二个进程等第一个结束才拿锁**，两跑窗口不重叠且均 PASS。
- `GATE_LOCK_FAILFAST=1` 探针 ⇒ `gate-lock: BUSY … target=check-tiny-hmon … refused immediately (rc=75)` + `make: *** [Makefile:198: check-tiny-hmon] Error 75` ⇒ 公共目标确由 `gate-locked-rule`（Makefile:198）生成并进锁；锁为主仓共享 `.dadao/gate.lock`（worktree 经 `.dadao` 软链同一文件 ⇒ 跨 worktree 串行）。

**Makefile 核验**：`git diff 7646279b c44f6772d -- Makefile` 仅 2 处——`GATE_LOCKED_TARGETS` 行追加 `check-tiny-hmon`、recipe 行 `check-tiny-hmon:` → `_locked-check-tiny-hmon:`（附 2 行注释）；**既有目标体改动 0 行**（全部删除行即此两行）；`WRITER_TARGET_COMPONENTS` 0 改动；`.PHONY` 含 `check-tiny-hmon`，`$(addprefix _locked-,$(GATE_LOCKED_TARGETS))` 覆盖新 recipe；两次跑均无 `overriding recipe` 告警。

**文档/状态**：完成区「测试结果」「遗留问题」已按第 1 轮建议改为「gem5 段 19 行与主仓逐字相同（diff rc=0）；总 problem 88 vs 主仓 98，差 10 条 chipyard」✓；`**状态**：待验收` ✓；第 1 轮 reviewer 记录与我写入原文**逐行相同**（仅其后追加 engineer「返工处置」段，未改写）✓。

**判决：Accepted** —— 两处返工均按最小返工点落地，全部验收命令在我自己的重跑下通过，锁行为有真实 `WAIT → ACQUIRED` / `BUSY rc=75` 证据。非阻断遗留：① 完成区「88 vs 98」是主仓移动靶（我复跑时主仓已到 `102`、chipyard `14` 条，worktree 仍 `88`，**gem5 段 19 行 diff rc=0 仍成立**，建议措辞只锚定 gem5 段）；② `tiny_hmon_min.S` + `min_rom_probe_integ007t.py` 仍归 `m19-testcases-006`；③ worktree 88 条为组件级既有基线红，与本任务无关。

**采信/未重跑**：无——上述命令均为我本人执行。
