# m18-chipyard-002: RTL 实现异步 escape 出口（cg5 rc8–rc11、cg9 新布局）

**模块**：chipyard
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入）、`m18-llvm-002`（汇编/编码）、`m18-testcases-004`（向量）；**须等 M16 当前 chipyard 批次释放写者窗口**（同 `components/chipyard`）
**可并行分片**：否
**预估**：4–6 h（标定：同档 chipyard-026 2–3 h；本任务含跨 cfx mask 读写与 escape 重写，取 2×）
**档位**：大改（RTL 异常进入/退出）
**状态**：已验证
**执行环境**：本地（chipyard `WumingTiny/Vast`）

**追加（m18-spec-009）**：异步进入须加 `当前模式 ≤ cg15 rc14` 上限；默认 supv 不打断 hypv。

## 背景

`m18-spec-007`/`ADR-0061 R3` 把出口改为 `cg5 rc8`–`rc11` + `escape cfxHA`，`cg9` 重排（`rc0`–`rc4`、`rc14`/`rc15`），`cg0`–`cg3` 的 switch/vector 改 `rc14`/`rc15`。RTL 仍是 R2：`switchMode`/`vector` 在 `rc8`/`rc10`、`cg5 rc0/1/3` 可写、无出口意图字段、`escape` 带偏移。

## 目标

1. **寄存器面**：`cg5 rc0`–`rc3` 只读（写 ⇒ `CFXREG`）；`rc4/rc5` cause id/info；删 `pending`；`rc8`–`rc11` 出口意图（进入时硬件复制，`rc11` 复位全 1）；`cg9` `rc0`–`rc4` 只读、`rc5` pending、`rc14` switch、`rc15` vector；`cg0`–`cg3` 的 switch→`rc14`、vector→`rc15`，旧 `rc8`/`rc10` ⇒ `CFXREG`。
2. **进入**：同步（含 `trap`）写目标 cfx `cg5 rc0`–`rc5` + `rc8`–`rc11`；异步写 `cg9 rc0`–`rc4` + hart `cg5 rc8`–`rc11`（不写 hart `cg5 rc0`–`rc3`）。
3. **`escape`**：`imms18` 必须 0（非 0 ⇒ `ILLI`）；`cfxha` = 当前 cfx（否则 `CFXESC`）；目标模式不得升权（`CFXESC`）；目标 cfx 未实现/无 monitor ⇒ `CFXESC`；跳 `rc10`；`rc11` 整字写目标模式 monitor `cg8 rc1`，与切换/跳转同一状态转换；`escape_num` +1。
4. **跨 cfx 读写**：进入时读“被打断模式 monitor 的 `cg8 rc1`”填 `rc11`；`escape` 时写目标 monitor 的 `cg8 rc1`——新增 mux/写口，须给时序与资源评估。
5. **生成物/断言**：受 opcodes 影响的 decode 断言重生成；`check-qemu-forms`/`check-legality-drift` 一致；`expected-divergences` 只增删必要项。
6. **不做**：不改 QEMU/gem5/IDL/LLVM/内核/spec。

## 验收（逐条贴真实 rc）

1. `make verilog` + sim 构建 rc=0、`%Error`=0；sim md5 记录。
2. 向量（`m18-testcases-004`）在 Vast/Tiny 上可跑的条目通过；`rc11` 整字恢复、升权 `CFXESC`、非 0 `imms18` `ILLI`、未实现目标 `CFXESC`。
3. 与 QEMU 同 ELF 签名逐字节一致；不一致登记 `expected-divergences.yaml` 并说明。
4. **可达 FAIL ≥2 路**：`rc11` 增量写；恢复 `rc8` 当 switch；还原重建回绿。
5. 不回归：M16 cfx/cache 代表集、Tiny 基线；`check-patch-tree` chipyard 段 0 problem、`check-component-changelog` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/chipyard/patches/**`、`components/chipyard/changelog.md`、`tests/arch/**`、`tests/arch/expected-divergences.yaml`、本任务书。
3. 不改 QEMU/gem5/IDL/LLVM/内核/spec/契约/Makefile；不改版本号。
4. 组件补丁经 `make_patch.py chipyard` 重导；`cp`+md5 还原；还原后重建；等 M16 chipyard 写者窗口。

## 待裁定

无。

## 完成区

**测试结果**：运行期证据目录内 `run.sh --base` = **32/32 PASS, EXIT=0**；`run.sh --inject` = **15/15 PASS, EXIT=0**。Vast/Tiny `make verilog`+sim rc=0、`%Error`=0（Vast sim md5 `b9946093…`，注入后重建 `f0c67c01…`；Tiny `27c6b274…`；二进制不跨增量重建逐位复现，还原判据 = 源码 md5 + 载体回绿）。
**修改文件**：`components/chipyard/patches/generators/dadao-gewu/**/GewuFile.scala.patch`、`.../dadao-wuming/**/{WumingCore,WumingDecoder}.scala.patch`、`.../resources/dadao/bootrom/bootrom.{tiny,vast}.hex.patch`、`components/chipyard/changelog.md`；`tests/arch/{expected-divergences.yaml,hart/README.md,hart/check_hart_rtl.py,hart/check_escape_rtl.py,hart/escape_escalation.S}`；本任务书。
**验收结果**：
- 寄存器面/进入/出口按 0.8.0+R3：`cg5 rc0`–`rc3` 只读、`rc4/5` cause、`rc8`–`rc11` 出口意图；`cg9 rc0`–`rc5`/`rc14`/`rc15`；`cg0`–`cg3` `rc14`/`rc15`；旧 `rc8`/`rc10` ⇒ `CFXREG`。
- `arch-hart-002` smon/umon 各 **38 槽 PASS**（异步进入、`rc11` 整字、覆盖/屏蔽/pending、模式上限 0/2）。
- `arch-hart-001` hmon **0–64 槽 PASS**（槽 1/7 为登记的 `DIV-17`：RTL 以 cfx_power 交付）；65–123 因 0.8.0 载体未设 `rc14=3` 被 spec-009 上限挡住（**KNOWN-RED**）。
- `escape_escalation` 探针 PASS：`rc11` 整字、升权 `CFXESC`、未实现目标 `CFXESC`、`imms18≠0` `ILLI`。
- Tiny `01-load-store` **38/38**；`11-cfx` **4/5**（`escape_ciii` = `DIV-18`：Tiny 无 monitor `cg8 rc1`）。
- 注入 A（`rc11` 增量写）⇒ smon slot 11 红；注入 B（删升权判定）⇒ 探针 `SYS_EXIT 3`；均 `cp`+md5 还原、重建回绿、源码树干净。
- 门控：`check-patch-tree` chipyard 段 **0 problem**、`--source-state` OK（全仓 rc=1 来自 qemu/gem5/musl 既有漂移）；`check-component-changelog`/`check-knowledge-refs`/`check-tests-index`/`check-index-blobs`/`check-no-residue`/`run_arch --self-test` 全 rc=0。
**新发现/坑**：① 0.8.0 的 `cfx15.S` 异步段与 spec-009 上限不相容（体在 hypv、未写 `rc14=3`）⇒ H 模式必然停在 slot 65；0.8.1 载体随 chipyard-003。② 旧 `bootrom.{tiny,vast}.hex` 未随 R3 迁移：Tiny hmon 处理器仍写 `cg5 rc3`（新布局只读）⇒ 新 RTL 上 `CFXREG` 死循环；已从 R3 源重生成，且改 hex 后须删 `.classpath_cache/chipyard.jar`。③ RTL 固定 BootROM 以 cfx_power 交付测试体，QEMU/gem5 以 cfx_hmon 交付 ⇒ 首次 trap 的 prev/escape cfx 两槽差异（`DIV-17`）。④ `check_hart_rtl --selfcheck` 写死 89/40 已改为从 `expected.yaml` 现场派生。⑤ Verilator 二进制跨增量重建不逐位复现，注入还原判据用源码 md5 + 载体回绿。⑥ HEAD QEMU 已迁 0.8.1，跑 0.8.0 载体 rc=2；同 ELF 的 QEMU 侧证据以 `m18-qemu-008` 与本任务共享的 `m18-testcases-004` oracle 为准，未另建 0.8.0 QEMU。
**遗留问题**：① H 模式异步段/`esc_criteria` 在 0.8.0 载体上 KNOWN-RED（模式上限），待 `m18-chipyard-003`（cg15/cg16 + 0.8.1 载体）。② Tiny `escape_ciii` 的 `cg8 rc1` 缺口 = `DIV-18`。③ “无帧有效位（cause=0 也可 `escape`）”无 RTL 直接载体，仅 QEMU/inst 向量覆盖；代码已删除门控。④ `m18-testcases-005` 的 cg15/cg16 全项在 RTL 上 KNOWN-RED（本轮未做源接口）。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 `GewuFile`（读写集/入口记录/出口意图/异步进入/模式上限）、`WumingDecoder`（`imms18` SBZ）、`WumingCore`（escape 事件与 trace）及 BootROM 重生成。核对：`cg5 rc0`–`rc3` 不在写集；`rc8`–`rc11` 可写且 `rc11` 整字恢复；同步写目标 cfx 两层、异步只写 hart `rc8`–`rc11`；`escape` 四类判据在切换前判定；`rc14` 上限用 `runMode <= asyncSwitch`；旧 `rc8/rc10` 无译码（CFXREG）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check_hart_rtl --selfcheck` 写死 89/40 | ✅已修 | 改为读 `expected.yaml` 现场派生 | `--selfcheck` rc=0（证据 32/32） |
| F2 旧 BootROM hex 仍写 R2 `cg5 rc3`，新 RTL 上死循环 | ✅已修 | 从 R3 源重生成 tiny/vast hex | H/S/U 均越过 BootROM；`DIV-17` 收窄为 2 槽 |
| F3 0.8.0 H 载体异步段被 spec-009 上限挡住 | ✅记录 | 不伪装通过；证据断言 0–64 绿、65 起截断 | `run.sh` H prefix 断言 PASS |
| F4 Tiny `escape_ciii` 无 `cg8 rc1` | ✅登记 | `DIV-18` | Tiny 11-cfx 4/5 |
| F5 RTL 以 cfx_power 交付、QEMU/gem5 以 cfx_hmon 交付 | ✅登记 | `DIV-17` 两槽（1/7=63） | H prefix 逐槽断言 |
| F6 `escape` 仍要求 `cause_id != 0` | ✅已修 | 删除帧有效位门控 | S/U 38/38；代码审查 |
| F7 Verilator 二进制跨注入重建不逐位复现 | ✅记录 | 还原判据改源码 md5 + 载体回绿 | inject 15/15（源码 md5 复原、smon/探针回绿） |

判决：所有可修 finding 已修；状态对账为「待验收」。

### 第 1 轮 reviewer 验收

**重跑记录（审查者独立执行，不采信完成区转述）**
- `git diff 1407b926..1adad422` = 12 文件，与完成区「修改文件」逐项对上；无 QEMU/gem5/IDL/LLVM/内核/spec/契约/Makefile 改动；未 push（`origin/master..HEAD` 仅本地 WIP）；状态 `待验收`；完成区 15 行 ≤30。
- 源码语义逐行（`GewuFile`/`WumingDecoder`/`WumingCore` patch）：`cg5 rc0–rc3` 不在写集（写 ⇒ `CFXREG`）、`rc4/rc5`=cause id/info、`pending` 已删、`rc8–rc11` 出口意图且 `rc11` 复位全 1；`cg9 rc0–rc5`/`rc14`/`rc15`（`rc6–13` 无译码 ⇒ `CFXREG`）；`cg0–cg3` switch/vector 走 `rc14/rc15`、旧 `rc8/rc10` 全仓无译码；同步进入写 `rc0–rc5`+`rc8–rc11`、异步进入只写 `cg9 rc0–rc4` + hart `cg5 rc8–rc11`（不碰 `rc0–rc3`）；`escape` 六判据齐（`imms18≠0⇒ILLI`、`ha==curCfx`、`curImplemented`、目标 cfx、目标 monitor、`escapeTargetMode<=runMode`）+ 跳 `rc10` + `rc11` 整字写目标 monitor + `escapeNum+1`；上限 `runMode <= cg9 rc14` 进 `intr.valid`。
- `git diff 1adad422..c37b2868` 对照：003 未回退上述任一条；`cg9→cg15`、`cg8 rc1→cg15 rc3` 属 `m18-spec-008` 迁移，出口意图/上限/六判据原样。
- 自带证据（读记录）：运行期证据目录 `run-base.EXIT=0` + `summary: 32/32`；`run-inject.EXIT=0` + `summary: 15/15`（注入 A `rc11` 增量写 ⇒ smon 红、注入 B 删升权 ⇒ 探针 `SYS_EXIT 3`；`cp`+md5 还原重建回绿）。
- 行为证据（我重跑 003 运行期证据目录内 `run.sh --base` = 32/32、EXIT=0；共享源树已是 003 状态，按约定不重放 002）：`arch-hart-002` smon/umon 各 38 槽 PASS、`arch-hart-001` 124 槽仅 `DIV-17`(1/7)=63、`arch-pmem-001` 48 槽、`arch-pmem-002` 10×2；我另跑 Tiny `01-load-store` 38/38、`11-cfx` 4/5（`escape_ciii` = `DIV-18`）；cache 代表集 RTL `arch-cache-001/002/003` PASS、`004` 登记 GAP（`run_arch` rc=0）。
- 采信（未亲跑）：0.8.0 QEMU 同 ELF 腿以共享 oracle（`m18-qemu-008`/`m18-testcases-004`）为准，本任务未建 0.8.0 QEMU（完成区已披露）。

**finding（不阻断）** F1 交接记录只在批次册（`ed5a42a3`）与 M16 台账 033 行，本任务书/030 台账行未写 ⇒ 文档级，交 architect 收尾补。F2 `run.sh` 的 `check-patch-tree chipyard problems` 在工具零输出时恒过（同脚本 `source-state` 兜底）⇒ 建议补 rc 断言。

**判决**：Accepted
