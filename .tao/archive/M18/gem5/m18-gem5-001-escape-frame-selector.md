# m18-gem5-001: gem5 escape frame selector 语义与断言

**模块**：gem5
**项目里程碑**：M18
**依赖**：`m18-spec-003`（escape 编码真源）、`m18-idl-001`（参考语义/向量）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为 b6 escape 语义 + 断言 + 生成断言，取 1.5–2× 中位）
**档位**：中改（功能模型编码语义）
**状态**：已验证
**执行环境**：本地（gem5 SE/FS 现有构建流程）

## 关联（2026-11-24，来自 M17）

- `tests/inst/11-cfx/escape_ciii_cfx.S` 的 `__c13`（`imms18=2` ⇒ 期望 `CFXESC`）在 gem5 上仍按旧编码（`imms18 >> 1 != 0 ⇒ ILLI`）返回 `rc=13`；新旧 gem5 二进制实测相同 ⇒ 既有能力缺口，非 `m17-gem5-001` 回归（证据见该任务书「新发现/坑」④）。本任务收口前须覆盖该例，否则 M17 全四方无法达到 274/274。

## 背景

`m18-spec-003` 已把 `escape` 改为 `imms18` bit1 帧选择（0=cg5，1=cg9；合法 `{0,1,2}`，`3 ⇒ ILLI`；cg9 仅偏移 0；`imms20 ∈ {0,4,8}`）。gem5 侧仍按旧编码：

- `components/gem5/patches/src/arch/dadao/exec/b6.cc` 注释/实现只认 0/+4 与 `imms18[17:1]` SBZ；
- `b6_test.cc` 的 escape SBZ/帧测试未覆盖 bit1/cg9；
- `decode/decode_assertions.inc` 由 opcodes 生成，需随 `contracts/opcodes.yaml` 重生成；
- `tools/gem5/check_b6.py` 的 `EXPECTED_LEGALITY` 已由 spec-003 更新，gem5 模型必须与之对齐。

## 目标

1. `b6.cc`/`b6.hh`：escape 解析 `imms18` bit1；cg5 偏移 0/+4；cg9 仅 0；`imms18=3` 或 `[17:2] != 0` ⇒ ILLI；cg9 帧判据/返回（`cfx_hart cg9 rc3 != 0`、`prev_run_mode/prev_cfx_code/cause_ip`、saved global mask）按 `DADAO-12 §5.3`。
2. `b6_test.cc`：增 `imms18=2`（cg9 路径）、`imms18=3`/`[17:2]` 非零的 ILLI；保留原 cg5 0/4 用例。
3. **重生成** `decode/decode_assertions.inc`（用仓库生成器），确保 `check-qemu-forms`/legality 相关门控与 `contracts/opcodes.yaml` 一致。
4. `tools/gem5/check_b6.py` 的 `EXPECTED_LEGALITY` 与新模型一致（0 error）；若 gem5 构建成本高，至少跑静态 checker + 受影响的 b6 单测。

## 验收（逐条贴真实 rc）

1. gem5 构建（既有流程）rc=0；`b6` 相关单测 `imms18=0/1/2/3` + `[17:2]` 非零用例通过；`imms18=2` 真走 cg9。
2. `tools/gem5/check_b6.py` 静态 0 error；`check-qemu-forms`/`check-legality-drift`/`check-spec-codeblocks` rc=0。
3. **可达 FAIL ≥2 路**：① 仍按旧 `[17:1]` SBZ ⇒ 新单测红；② cg9 帧不恢复 mask ⇒ 测试红；`cp`+md5 还原后回绿（源码还原后重建）。
4. 不回归：既有 gem5 代表集/`check-gem5-decode`（如适用）rc=0；`check-patch-tree` gem5 段与基线逐行相同（musl 10 基线除外）；`check-component-changelog` rc=0。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/gem5/patches/src/arch/dadao/exec/b6*`、`components/gem5/patches/src/arch/dadao/decode/decode_assertions.inc`（生成物）、`components/gem5/changelog.md`、`tools/gem5/check_b6.py`（仅期望）、本任务书。
3. 不改 QEMU/RTL/LLVM/内核/spec/contracts；不改版本号；术语「bank = 寄存器组」。
4. 组件补丁经 `make_patch.py gem5` 重导；生成断言用仓库生成器；还原 `cp`+md5；还原后重建。
5. 若 gem5 模型语义与 spec 冲突，按 spec 改模型并写「待裁定」，不得反向改 spec。

## 待裁定

1. **cg9 返回口径（spec 已改，任务目标 1 仍是旧口径）**：目标 1 写的「cg9 帧判据 `rc3 != 0`、返回 `prev_run_mode/prev_cfx_code/cause_ip`、恢复 saved global mask」来自 ADR-0060 旧模型；`ADR-0061 R2` / `m18-spec-005`（已验证）已改为「`cg9` 是异步捕获缓冲、**不是返回帧**；`imms18[1] = 1` 编码合法但执行恒按所选帧无效 ⇒ 当前 cfx `CFXESC`，不改变 cfx/运行模式/`cg9`」。按硬约束 5「模型与 spec 冲突按 spec 改」实现后者。请架构师确认：① 是否需在 `ADR-0061`/`DADAO-12 §5.3` 补 R2 注记（`m18-spec-005` 的 N1 finding）；② `m18-idl-002` 任务书仍写「`escape imms18=2` 按 `src_frame != 0` 有效、返回清 `src_frame`」，与该 spec 口径冲突，需按 R2 改写或另立裁定。
2. **CFXESC 交付路由（超出本任务允许文件集，需续任务）**：cg5 的帧/目标错误由 `tinyEscape`/`nodeEscape` 在 hook 内直接 raise（hook 返回 true），不走 `inst.cc` 的 `Fault::CfxEsc` fallback；cg9 现在返回 `Fault::CfxEsc`，会走该 fallback，而 fallback 用 `machineFaultAt(..., target=-1)` ⇒ Tiny 进 hmon、Node 进当前运行模式 monitor（`inst.cc.patch` 注释自述 “still enters the current monitor”），与 `DADAO-12 §5.1/§5.3`「进入**当前 cfx**」不符。修法在 `components/gem5/patches/src/arch/dadao/inst.cc.patch`（`CfxEsc` fallback 改为进当前 cfx），但 `inst.cc` 不在硬约束 2 的允许集，本任务未改。请裁定是否扩范围或另立任务；本任务交付的 b6 核心语义（返回 `CfxEsc`、不改变状态、不调 hook）已由单测覆盖。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` **41/41 PASS（rc=0）**；`run.sh --inject` **31/31 PASS（rc=0）**（含基线复跑）。b6 harness compile rc=0、`[FAIL]` 0：30/30 coverage，`imms18 = 0/1/2/3` 与 `[17:2]` 非零、`cfx15/cfx32` 的 cg9 用例逐条 PASS。`check-gem5-decode` rc=0（positive 263/263、negative 391/391、legality 28/28、failures 0）；静态 `check-qemu-forms`/`check-legality-drift`/`check-spec-codeblocks`/`check-component-changelog`/`check-patch-tree`/`check-no-residue` 全 rc=0；`make build-gem5 JOBS=32` rc=0（实测重编 `decode.cc`/`b6.cc` 并链接 `gem5.opt`）。`make check` rc=2，唯一失败 `check-isa-coverage`（缺 `llvm-mc`，环境/基线，m18-spec-003 同因）。
**修改文件**：`components/gem5/patches/src/arch/dadao/exec/b6.cc.patch`、`b6.hh.patch`、`b6_test.cc.patch`、`decode/decode_assertions.inc.patch`、`decode/decode_table.inc.patch`（生成物连带，越界披露）、`components/gem5/decode-assertions.tsv`（生成物连带，越界披露）、`components/gem5/changelog.md`、本任务书。`tools/gem5/check_b6.py` 复核后无需改动（`EXPECTED_LEGALITY` 已含 `imms18[17:2] == 0` + `imms18 != 3`，`contract_rule_errors()` 0 error）。补丁全部由源树修改后 `make_patch.py gem5` 重导出（106 份、仅 5 份变化），未手改补丁文件。
**验收结果**：语义按 `DADAO-12 §5.1/§5.3/§5.4`：`imms18[17:2]` 非零 / `imms18 = 3` / reserved cfx ⇒ ILLI（均先于目标/帧判定与状态切换）；`imms18[1] = 0` 走 cg5，偏移 `(imms18 & 1) << 2`；`imms18[1] = 1` 走 cg9，cg9 非返回帧 ⇒ 恒 `CFXESC`、不调 `escapeFrom`、不改 cfx/模式/`cg9`（cfx15 与 cfx32 同）。可达 FAIL 3 路（`cp`+md5 还原，md5 `fb9793cb…` 前后一致、还原后 harness 回绿、源树 `git status` 空）：A 旧 `[17:1]` SBZ ⇒ `escape cfx15 imms18=2 (cg9 frame) -> CfxEsc` 红；B 去掉 cg9 `CFXESC` 分支 ⇒ 同点红；C 去掉 `imms18 = 3` ⇒ `escape imms18=3 … Illegal` 红。生成物 `gen_decode_table.py --check` rc=0（263 rows）：escape legality 变更连带 `decode_table.inc`（legality 数组长度 2→3）与 `decode-assertions.tsv`（legality 列），负例两文件逐字节不变。
**新发现/坑**：① 任务目标 1 的 cg9 返回口径属 ADR-0060 旧模型，与本任务采用的新 spec 冲突，已按硬约束 5 取 spec（见待裁定 1）；② `gen_decode_table.py` 一次写 4 个输出，escape legality 条数变化必改 `decode_table.inc`，无法只重生成 assertions；③ 本 worktree 从共享源树拷贝 `build/` 后 scons 增量有效（路径变化未触发全量重编），显著缩短构建；④ 证据脚本初版把 coverage 标记数写死为 1（实际 3 处），已改为 `check_min` 下限断言（实测修复）；⑤ cg9 返回 `Fault::CfxEsc` 会走 `inst.cc` 既有 fallback，该 fallback 进当前运行模式 monitor 而非当前 cfx（见待裁定 2）。
**遗留问题**：① `check-wuming-cycles` rc=2（`contracts/wuming-cycles.yaml` 与 doc 不一致，基线红，非本任务；m17-gem5-001 遗留①的另一半）；② gem5 代表集 `run_inst_tiny --platforms gem5` 未跑（需本 worktree `install-host` 工具链，不在任务允许范围）；③ 待裁定 1 的跨模块 R2 同步（IDL/QEMU 侧）；④ 待裁定 2 的 CFXESC 交付路由（`inst.cc` 不在允许文件集，未改）。

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**（逐行）：`exec/b6.cc::executeEscape`、`exec/b6.hh` 的 hook 注释、`exec/b6_test.cc::checkTrapEscape` 全部 escape 用例、重生成的 `decode/{decode_assertions,decode_table}.inc` 中 escape 行、`decode-assertions.tsv` escape 行、`components/gem5/changelog.md`、证据脚本。

**语义核对**：判定次序 = SBZ(`[17:2]`) → `imms18 = 3` → reserved cfx → 帧，与 `DADAO-12 §5.3` 步骤 0 及 IDL `_op_escape` 逐条一致；`imms18 = 2` 合法但 cg9 非返回帧 ⇒ `CFXESC`（`§5.1/§5.4`），不进入 `escapeFrom`（hook 只服务 cg5，`b6.hh` 已注明）；cg5 偏移 `(imms18 & 1) << 2` 只可能 0/4；任何 fault 路径无寄存器/内存/控制转移副作用（测试逐条断言 `escapeCalls == 0`、`writes.empty()`、`!controlTransfer`）。生成物与 `contracts/opcodes.yaml` 一致（`check-legality-drift`/`check-gem5-decode` 复核），未手改生成物。补丁 `make_patch.py` 重导出、`check-patch-tree` 0 problem，源树 E1 成立（base+1、clean）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务目标 1 的 cg9 返回口径与 `m18-spec-005`/ADR-0061 R2 冲突 | ✅已修 | 按硬约束 5 取 spec：cg9 ⇒ `CFXESC`，不实现 rc3/prev/mask 返回；写入待裁定 1 | `run.sh` 41/41；spec 条文逐条对照 §5.1/§5.4 |
| F2 原测试把 `imms18 = 2` 当 ILLI（旧 `[17:1]` SBZ） | ✅已修 | `b6_test.cc` 改为 cg5 0/1、cg9 2（cfx15/32）、`3` 与 `[17:2]` 非零 ILLI | harness 逐条 PASS；注入 A 点名该用例 |
| F3 只重生成 assertions 不可行（`decode_table.inc` 存 legality 长度） | ✅已修 | 用仓库生成器重生成 4 个输出；`decode_table.inc`/`decode-assertions.tsv` 变化作为生成物连带披露 | `gen_decode_table --check` rc=0；负例两文件无 diff |
| F4 证据脚本把 coverage 标记数写死 1（实际 3） | ✅已修 | 新增 `check_min`，标记/OK 行改下限断言；结果行按失败数输出 PASS/FAIL | `run.sh` 41/41、`--inject` 31/31，rc=0 |
| F5 `check_b6.py` 期望值是否需改 | ❌不修 | `m18-spec-003` 已对齐 `imms18[17:2] == 0` + `imms18 != 3` | `contract_rule_errors(live_b6_entries())` 0 error；harness `[FAIL]` 0 |
| F6 cg9 跳过 `escapeFrom` 后 `Fault::CfxEsc` 的交付路由 | ⏸延后 | b6 核心语义已正确（返回 `CfxEsc`、无状态改变）；`inst.cc` 的 fallback 进当前 monitor 而非当前 cfx，`inst.cc` 不在允许文件集，登记待裁定 2/遗留④ | `inst.cc.patch` 的 `CfxEsc` 分支注释与 `fs_machine.cc::MachineFault::invoke` 逐行核对；b6 单测覆盖核心返回值 |

**判决**：范围内无未修 finding；F6 属允许文件集外的适配层路由，记待裁定 2/遗留④；所有证据为现场真实 rc/md5，状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（本人执行，仓库根）**：运行期证据目录内 `run.sh` ⇒ `RESULT: PASS (checks=41, failures=0)` rc=0；同脚本 `--inject` ⇒ `PASS (checks=31, failures=0)` rc=0（共 3 次重跑）。门控逐条 rc=0：`check-gem5-decode`（`summary: positive 263/263, negative 391/391, legality 28/28, failures 0`）、`check-qemu-forms`、`check-legality-drift`、`check-spec-codeblocks`、`check-component-changelog`、`check-patch-tree`（`gem5: 106 patch(es)`、`11 patch set(s), 463 patches OK`、0 problem）、`check-no-residue`。
**生成物**：重跑仓库生成器（不带 `--check`）后 4 个输出 md5 逐个 `OK`（rc=0）⇒ 确为生成器产物；escape 连带仅 `kLegality85`/`kAssertLegality85` 改为 `imms18[17:2] == 0` + `imms18 != 3`（长度 2→3）与 blob index；负例两文件与 HEAD 逐字节相同（`2e181bf7…`）。
**补丁零手改**：5 份变化补丁逐字节 == 源树 `git diff base..HEAD`（5/5 IDENTICAL）；`make_patch.py gem5 --dry-run` 列 106 份，与 `patches/` 实有清单 diff 0 行。
**构建**：`make build-gem5 JOBS=32` rc=0；本人注入后强制重建的关键行 `[CXX] src/arch/dadao/exec/b6.cc -> DADAO/arch/dadao/exec/b6.o`、`[LINK] -> DADAO/gem5.opt`、`build-gem5: PASS`；还原后再建 rc=0（内容哈希口径 ⇒ 二进制与源一致）。
**独立注入（未列项）**：把 `executeEscape` 的 `byteOffset … << 2` 改 `<< 3` ⇒ 同一 `run.sh --inject` 报 **FAIL rc=1（7 项）**，含 `escape imms18=1: byte offset 4` 红与 `source tree clean after restore` 检出残留；`cp` 还原 md5 `fb9793cb…` 相等、源树 `git status` 空，重跑回 `PASS (checks=31)` rc=0。
**快照对账**：验收前后 `git status --porcelain -uall` 逐行相同（8 行），4 个目标文件 md5 与注入前一致；改动文件与完成区「修改文件」逐行一致（`decode_table.inc.patch`、`decode-assertions.tsv` 为已披露生成器连带）。
**语义（从 spec 原文复述后对照）**：`DADAO-12 §5.3` 步骤 0 = `[17:2]!=0`→ILLI、`imms18=3`→ILLI、reserved→ILLI、目标/帧错→**当前 cfx** `CFXESC`（先于任何状态切换）；`§5.1` 与 `SimRISC-11 §2` 合法集 `{0,1,2}`、`imms18[1]` 帧选择、`imms18=2` 恒 `CFXESC`、cg5 偏移 `(imms18 & 1) << 2`。`executeEscape()` 次序逐条相符；cg9 分支不调 `escapeFrom`、无状态写（测试断言 `escapeCalls==0 && writes.empty() && !controlTransfer && memReads==0`）。
**R2 口径**：`ADR-0060` D4 的 `async_cause_id`/`prev_*`/`saved_global_intr_mask` 返回模型确属旧模型；`ADR-0061 R2 D3/D9` + `m18-spec-005`（已验证）为捕获缓冲、`imms18=2` 不返回。`b6.cc` 无 rc3/prev/saved 逻辑 ⇒ 取 R2，engineer 陈述属实。
**待裁定①属实**：`Fault::CfxEsc` → `machineFaultAt(…, target=-1)`：Tiny `target<0 ⇒ TinyCfxhaHmon`、Node `target = runMode`（`fs_machine.cc`），均进**当前运行模式 monitor**，与 `DADAO-12 §5.1/§5.3`「escape 帧/目标错误 → 当前核芯功能扩展、不属于 monitor 路由」不符；cg5 走 hook 直接 raise（`target=cfxCode`）正确，仅 cg9/无帧路径错 ⇒ 建议另立任务，修点 `inst.cc.patch`（按 `inner_cfx_code` 定 target / 用 `machineFaultToCfx`）。
**待裁定②属实**：`m18-idl-002`（待开始）目标 1/2 仍写「`escape imms18=2` 按 `src_frame != 0` 有效、返回清 `src_frame`」「帧由 escape 结束」，与 `m18-spec-005` R2 冲突，派单前须改写。
**基线红**：`check-isa-coverage`（缺 `llvm-mc`）与 `check-wuming-cycles`（`contracts/wuming-cycles.yaml` 与现解析不一致）在 `git archive HEAD` 建的基线树重跑，输出与当前树 `diff` **0 行**、rc 同为 2 ⇒ 基线即红。
**发现（不阻断）**：`SimRISC-11 §3.1` IDL 生成块仍为 R1（cg9 有效帧 → `cfx_escape_enter`），与 `DADAO-12` R2 正文不一致——`m18-spec-005` 已记 `ISS-530` 并指 `m18-idl-002`，`idl/` 不在本任务允许集。
**判决：Accepted**
