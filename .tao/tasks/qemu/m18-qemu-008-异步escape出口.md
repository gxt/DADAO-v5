# m18-qemu-008: QEMU 实现异步 escape 出口（cg5 rc8–rc11、cg9 新布局、escape cfxHA）

**模块**：qemu
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入：DADAO-12/22 0.8.0、ADR-0061 R3）
**可并行分片**：否（同 `components/qemu` 写者）
**预估**：3–5 h（标定：同档 qemu-006 捕获缓冲修订 2–3 h；本任务含 cg5/cg9 重排 + escape 重写 + 入口自动填，取 1.5–2×）
**档位**：大改（QEMU 异常进入/退出模型）
**状态**：已验证
**执行环境**：本地（`qemu-system-dadao`，Vast/Tiny）

## 背景

`m18-spec-007` 定稿并合入：`cg5` 分“入口记录（`rc0`–`rc3`，只读）+ 出口意图（`rc8`–`rc11`，进入时硬件复制、软件可写）”；`cg9` 重排为 `rc0`–`rc3` 同序记录、`rc4` 源集合、`rc5` pending、`rc14` switch、`rc15` vector；`escape` 改为 `escape cfxHA`（`imms18` 恒 0），按 `cg5 rc8`–`rc11` 返回并把 `rc11` 整字写入目标模式 monitor 的 `cg8 rc1`。

QEMU 现实现仍是 R2：`m->switch_run_mode`=`rc8`、`m->excp_vector`=`rc10`、`cg5 rc0/1/3` 可写、`cg5 rc5` 是死状态 pending、`escape` 有 `imms18` 偏移并检查 `cause_id != 0`、异步写 `cg9 rc0`–`rc6`。本任务把 QEMU 对齐到 0.8.0 规范。

## 目标

1. **`cg5`**：`rc0`–`rc3` 改 `HW/RO`（软件写 ⇒ `CFXREG`）；`rc4` cause id、`rc5` cause info；删除 `pending` 字段；`rc8`–`rc11` 为出口意图（RW，进入时硬件复制，`rc11` 复位全 1）；`rc6`/`rc7` 保持 reserved。
2. **`cg9`（`cfx_hart`）**：`rc0`–`rc3` 同序记录（`HW/RO`）；`rc4` 本次源集合（`HW/RO`）；`rc5` `async_src_pending`（`HW/RO`）；`rc14` `async_switch_run_mode`（RW，复位 2）；`rc15` `async_excp_vector`（RW，48 位、低 2 位写忽略）；`rc6`–`rc13` reserved ⇒ `CFXREG`。
3. **`cg0`–`cg3`**：`<mode>_switch_run_mode` 由 `rc8` → `rc14`、`<mode>_excp_vector` 由 `rc10` → `rc15`；原 `rc8`/`rc10` 访问 ⇒ `CFXREG`。
4. **同步进入（含 `trap` 进目标 cfx）**：写目标 cfx `cg5 rc0`–`rc3`（入口记录）+ `rc4`/`rc5`（cause）+ `rc8`–`rc11`（出口意图；`rc11` = 被打断模式的 `cg8 rc1` 当前字）。
5. **异步进入（`cfx_hart`）**：写 `cg9 rc0`–`rc4`（记录 + 源集合）与 **hart 自己的 `cg5 rc8`–`rc11`**（`rc11` = 被打断模式的 mask）；**不写** hart `cg5 rc0`–`rc3`。
6. **`escape cfxHA`**：`imms18` 必须 0（非 0 ⇒ `ILLI`）；`cfxha` 必须等于当前 cfx（否则 `CFXESC`）；目标模式（`rc8`）不得高于当前模式（否则 `CFXESC`）；目标 cfx 未实现或无对应 monitor（jail→jmon）⇒ `CFXESC`；跳转精确取 `rc10`；把 `rc11` **整字**写入目标模式 monitor 的 `cg8 rc1`（与切模式/切 cfx/跳转同一状态转换）；`escape_num` +1；**删除** `cause_id != 0` 的帧有效性检查；不设有效位。
7. 更新受影响的 QEMU 侧探针/单测（`tests/arch/**`、`tests/unit/qemu/**`、`tools/testcases/arch/**`）；`vast-arch-inventory.md` 与保留差异表按新口径标注。
8. **不做**：不删 `cfx_jmon`（`m18-qemu-007`）、不改内核/IDL/LLVM/gem5/RTL。

## 验收（逐条贴真实 rc）

1. 单元探针（新增/改造）：`cg5` 写入 `rc0`–`rc3` ⇒ `CFXREG`；`rc8`–`rc11` 读写正常；`rc11` 复位全 1；`cg9` 新槽位读写/保留槽 `CFXREG`；`cg0`–`cg3` 的 `rc14`/`rc15` 生效、`rc8`/`rc10` ⇒ `CFXREG`。
2. 进入探针：同步 `trap` 后目标 cfx 的 `cg5 rc0`–`rc5`/`rc8`–`rc11` 正确；异步进入后 `cg9 rc0`–`rc4` 与 hart `cg5 rc8`–`rc11` 正确、hart `cg5 rc0`–`rc3` 保持不变。
3. `escape` 探针：正常返回（mode/cfx/ip/mask 四者都对）；`rc11` 整字写目标 monitor；`imms18 != 0` ⇒ `ILLI`；错误 cfxha / 升权 / 未实现目标 ⇒ `CFXESC`；`escape_num` +1。
4. **可达 FAIL ≥2 路**：① 把 `rc11` 改成增量写 ⇒ 探针红；② 恢复 `cause_id != 0` 检查或把 `rc8` 当 switch ⇒ 探针红；`cp`+md5 还原并重建回绿。
5. 不回归：M16 cfx5/cache 代表集、Tiny 基线（Tiny 无 hart/umon 的路径按既有规则）；`check-patch-tree` qemu 段 0 problem；`check-component-changelog`、`check-knowledge-refs`、`check-qemu-forms` rc=0。
6. **KNOWN-RED 披露**：Linux 侧（K2/K5/K6、IDL 四方比对、LLVM 向量）在实现任务跟进前会红——逐条列出并归因，**不得改内核/IDL/LLVM/tests 去凑绿**。
7. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/qemu/patches/**`、`components/qemu/changelog.md`、`tests/arch/**`、`tests/unit/qemu/**`、`tools/testcases/arch/**`、`tests/arch/vast-arch-inventory.md`、本任务书。
3. 不改 `spec/`、`.tao/contracts/`、`Makefile`、内核/musl/busybox/gem5/RTL/LLVM/IDL；不改版本号。
4. 组件补丁经 `make_patch.py qemu` 重导；还原 `cp`+md5；还原后重建；术语「bank = 寄存器组」。
5. 顺序：先实现进入/布局，再实现 `escape` 与 `rc11` 原子写；每步用探针验证。

## 待裁定

无。

## 完成区

**测试结果**：自研 QEMU 单测 `tools/testcases/arch/min_rom_probe_m18qemu008.py` **21 例 / 150 断言全 PASS**（`--self-test`：150/150 断言均有可达 FAIL）。证据脚本（运行期证据目录内 `run.sh`）**29/29 PASS**，含 2 路注入：① `rc11` 改增量写 ⇒ `escape_rc11_restore` 红；② 恢复 `cause_id != 0` 检查 ⇒ `async_entry` 红；均 `cp`+md5 还原、重建后 21/21 回绿。静态门控（脚本内）`check-patch-tree`/`check-qemu-forms`/`check-component-changelog`/`check-knowledge-refs`/`check-tests-index`/`check-dirs`/`check-no-residue`/`check-spec-refs`/`compileall` 全 rc=0；`make_patch qemu` 重导 0 改动。

**修改文件**：`components/qemu/patches/target/dadao/{cpu.h,cpu.c,helper.c}.patch`（`make_patch.py qemu` 重导，3 份改）、`components/qemu/changelog.md`、`tools/testcases/arch/node_probe_prelude.py`（hypv 向量 rc10→rc15）、`tools/testcases/arch/min_rom_probe_m18qemu008.py`（新增）、`tools/testcases/arch/README.md`、`tests/arch/vast-arch-inventory.md`、本任务书。

**验收结果**：`make build-qemu` → `build-qemu: PASS`（softmmu + linux-user 双目标）；探针输出 `summary: 21 case(s), 0 failure(s)`；证据脚本 `summary: checks=29 failures=0` / `m18-qemu-008 evidence: PASS`（退出码 0）。

**新发现/坑**：① 共享 llvm-mc 已升到 `escape cfxHA`（`m18-llvm-002` 落共享根），旧 `escape X, [excp_cause_ip, n]` 直接**汇编报错**——所有旧向量在 ② 之前既红于槽位也红于语法；本探针用 word 编码不受影响。② `cfx_hmon` 的 `cg5` 在 prelude 的 power→hmon trap 后已非复位态，复位断言须用从未进入的 cfx。③ `cp -p` 还原后 mtime 早于目标文件 ⇒ ninja 跳过重建（注入"回绿"假绿风险），还原后必须 `touch`。④ 共享安装根正被别的会话 `make install-host`（`ninja -j32` PID 3611947）：Tiny `run_codegen_e2e` 因此被 writer-guard 判「二进制被替换」；本任务全程未跑 `install-*`、未覆盖共享 QEMU。⑤ `-d cpu` 的 `MODE`/`CFXCODE` 是十进制，`PREVM` 行的 `PEND` 已换 `PIM` 并新增 `ESCOM/ESCIC/ESCIP/ESCIM` 行。

**遗留问题**：KNOWN-RED（等 `m18-testcases-004` 向量改写）：`check-arch-smoke`/`check-arch`/`check-arch-self-test` 与 `tests/arch` 载体（`common/env-{hmon,smon,umon}/env.S`、`hart/cfx15.S`+`check_*`、`pmem/pmem*.S`+`check_*`、`umon/{mode_entry,cfx02_regs,m5_trap_escape,m5_perm_mask_cfxperm}.S`、`cache/time/ptw` 载体）及 legacy 探针（`min_rom_probe_{044t,045t,046t,integ040t,integ044t,integ048t,integ049t,integ050t,integ051t,async_094t}.py`）；`tests/shared/asm/perm_hypv.inc` 与 `tests/ee-vast/{hmon,smon,power,hmon_k0,smon_k0}_vast.S` 在允许路径外，同需 ②/内核任务。gem5/RTL/IDL/LLVM/Linux（K2/K5/K6、`check-idl` 四方、`check-cfx-vectors`、`check-cfx-alias-install`）按实现链后续任务，本分支未改。Tiny codegen baseline 本轮因共享工具链被并发替换无法归属（writer-guard），待安装根空闲后重跑。`check-arch-self-test` 红 = 本工作树未构建 LLVM（缺 `llvm-mc`，`make install-host`）；借用共享工具链时另可见旧向量的 `escape` 语法错（后者归 ②）。`check-temp-dirs` 实测红 6 项（5 项为其它会话 >2 h 的 `/tmp/opencode` 目录 + 磁盘 85%），非本任务产生。"目标模式无 monitor ⇒ `CFXESC`" 分支当前不可达（jmon 仍实现），由 `m18-qemu-007` 删 jmon 后覆盖。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`target/dadao/{cpu.h,cpu.c,helper.c}` 三份补丁（`make_patch.py qemu` 重导）、新探针 + prelude 一行、changelog、inventory、README。

**逐行要点**：
- `cfx_reg_ptr`：`cg0`–`cg2` = rc0–3/14/15，`cg3` 加 rc12；`cg5` rc0–3/4/5 只读、rc8–11 RW；`cg9` 走 `dadao_hart_async_reg_read/write`（rc0–5 写忽略、rc14/15 RW、rc6–13 ⇒ `CFXREG`）。与 `§3.1`–`§3.6`/`§4.7` 表逐行对照。
- `cfx_enter`：先采样 prev_cfx/prev_mask（monitor = 进入前模式），再切模式；写目标 cfx `rc0`–`rc5` + `rc8`–`rc11`；`rc11 = 进入前模式 monitor 的 cg8 rc1` 整字（无 monitor 行时 fail-safe 全 1）。
- `dadao_async_enter`：只写 `cg9 rc0`–`rc4` 与 hart 自己 `cg5 rc8`–`rc11`；`cg9 rc5` 只做 pending 扣除；`rc11` 同源同值。
- `helper_cfx_escape`：`imms18 != 0` ⇒ `ILLI`；reserved ⇒ `ILLI`；`cfxha != inner || ci < 0` ⇒ `CFXESC`；目标模式升权 / 目标 cfx 未实现 / 目标模式无 monitor ⇒ `CFXESC`，全部在任何状态切换之前；随后切 mode/cfx、`escape_num++`、`rc11` 整字写目标 monitor、跳 `rc10`（48 位、4 B 对齐）；删除 `cause_id != 0` 检查。
- `cfx2rc` 写侧：`rc15` 低 2 位忽略（不再误判 `cg5 rc15`，该 rc 不存在）；Tiny 的「switch 写忽略」从 rc8 改 rc14；`cg5 rc8/9/10/11` 分别 2/6/48/64 位落盘。
- 用户态构建：`escape` 在 decode 层即 `ILLI`，helper 不在 user 路径；两处 `dadao_async_kick` 调用均在 `#ifndef CONFIG_USER_ONLY` 内，`make build-qemu`（softmmu+linux-user 双目标）链接通过。

**探针**：word 编码，不依赖汇编器；`--self-test` 逐断言变异验证可达 FAIL；每个 case 单独 QEMU 进程，最后一次 `-d cpu` 块取观测。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `cfx_hmon cg5` 在 prelude 的 power→hmon trap 后已有帧，不能拿它断言"复位值" | ✅已修 | 复位值改读从未进入的 `cfx_umon` | `cg5_reset_rw` PASS |
| F2 `cg5 rc10`/`cg9 rc15` 期望未按字段宽度（48 位/低 2 位）派生 | ✅已修 | 期望值按 `& 0x0000FFFFFFFFFFFF & ~3` 现场派生 | 两例 PASS |
| F3 `cg0`–`cg2` 的 rc14/rc15 迁移未覆盖 | ✅已修 | 新增 `mode_slots_cg0`（写/读 + rc8/rc10 ⇒ `CFXREG`） | 19/19 PASS，自审 134/134 |
| F4 注入还原用 `cp -p` 保留旧 mtime ⇒ ninja 跳过重建（假绿） | ✅已修 | 还原后 `touch`，并在证据脚本里以「重建 rc + 回绿」双判 | 注入回绿轮 PASS |
| F5 "目标模式无 monitor" 分支在当前 QEMU 不可达（jmon 仍实现） | ⏸延后 | 代码分支已实现；`m18-qemu-007` 删 jmon 后由同一 `mci < 0` 分支覆盖 | 遗留登记 |
| F6 `-d cpu` 的 `MODE`/`CFXCODE` 是十进制、`PEND` 已换成 `PIM` | ✅已修 | 探针改十进制解析；旧 `PEND` 解析的 legacy 探针列 KNOWN-RED | 观测值正确 |
| F7 `tests/arch` 旧向量 / legacy 探针未改写 | ⏸延后 | 架构师 2026-11-26 明确「期望向量等 `m18-testcases-004`」；本任务只交付自研 QEMU 单测 | 完成区 KNOWN-RED 清单 |
| F8 未跑 cfx5/cache 代表集与 Tiny codegen | ⏸延后 | 前者同 F7；后者被 writer-guard 判红（共享 `llc`/`objcopy` 在跑批中被 install-host 替换） | 日志与 PID 已记录 |
| F9 注入②表现为「guest 超时」而非断言失败（CFXESC 落 cfx_hart 的 supv 向量 0 后死循环） | ❌不修 | 探针未给 cfx_hart 装 supv 向量；注入目的是「探针必须红」，`runlimit` 上限 + rc=1 已判红 | 证据日志 `inject detected by async_entry rc=1` |

**判决**：所有可修 finding 已修；F5/F7/F8 延后、F9 不修，均已在表格与「遗留问题」登记。状态对账 = **待验收**。

### 第 2 轮 engineer 自审

**针对 reviewer F-R1（阻断）**：
- 重写为 `_mode_slots_case(cg)`，**`cg0`/`cg1`/`cg2`/`cg3` 各一个 case**（`mode_slots_cg0/1/2/3`），删除原两个都传 `CG3` 的 case。
- 每个 case 断言：`rc14` 复位值 = `DADAO-12 §3.x` 的「初始值」列、写入另一 2 位值后读回、恢复；`rc15` 写入后读回（低 2 位规则只在 spec 明写「低 2 位」的行断言——§3.4 hypv 断言掩码，§3.1–§3.3 未写该句 ⇒ 写对齐值断言恒等，不声称实现独有的掩码）；`rc8`/`rc10` 访问 ⇒ `CFXREG` 且 `cause_info` 按 `cfx2rd` 编码现场构造。
- 槽位（switch/vector）、复位值、保留洞（8/10 ∈ reserved）全部在导入期从 spec 表解析（`mode_facts()`），不是写死 rc14/rc15；解析不到即 `OracleError` 退出 2。
- 文档改实：README「21 例 / 150 断言」、inventory「21 例 / 150 断言（cg0–cg3 四行各自）」、changelog「21 例 / 150 断言」。

**F-R2/F-R3（文档）**：完成区 `check-temp-dirs` 改为实测「6 项（5 项他人 >2 h 目录 + 磁盘 85%）」；`check-arch-self-test` 归因改为「本工作树未构建 LLVM、缺 `llvm-mc`」，旧向量语法错单列为 ② 的范围。

**F-R4**：按 reviewer 判决不动（注入②以 guest 超时收红，已在 F9 披露）。

**复验**（本人终端实跑）：探针 `summary: 21 case(s), 0 failure(s)`；`--self-test: PASS`（21 case 逐项 150/150 可达 FAIL）；证据脚本 `checks=29 failures=0` + `PASS`；`build-qemu` rc=0；`check-patch-tree` rc=0（qemu 段 0 problem，补丁集未变）；两路注入仍红并 `cp`+md5 还原后 21/21 回绿。状态保持 **待验收**。

### 第 1 轮 reviewer 验收

**重跑（本人执行，命令+真实 rc）**：运行期证据目录内 `run.sh` → `summary: checks=29 failures=0` + `m18-qemu-008 evidence: PASS`，退出码 0；两路注入各自报红（`escape_rc11_restore`、`async_entry`）并 `cp`+md5 还原、重建后 `19/19` 回绿。探针 → `summary: 19 case(s), 0 failure(s)` rc=0；`--self-test` → `self-test: PASS`，19 case 断言逐项相加 = **134/134**（15+3+3+3+3+5+3+8+8+11+5+5+16+5+5+5+5+20+6）。**独立注入第 3 路**（`escape` 把 `rc11` 写到当前 cfx 而非目标模式 monitor）→ `escape_rc11_restore` rc=1（`rd31 expected 0x8000 actual 0xffffffffffff7fff`）；`cp`+md5 还原（与注入前逐字节一致）→ 重建 rc=0 → `19/19` 回绿、`git status` 空。门控独立重跑：`check-patch-tree` rc=0（qemu 69 patch；11 patch set / 463 patches OK）、`check-qemu-forms`/`check-component-changelog`/`check-knowledge-refs`/`check-tests-index`/`check-dirs`/`check-no-residue`/`check-spec-refs` rc=0、`build-qemu` rc=0（PASS，softmmu+linux-user）。`make check` rc=2 → 红于 `check-isa-coverage`（缺 `llvm-mc`：本工作树未构建 LLVM，`a9b88db0` 的 9 文件不含 llvm/spec/Makefile ⇒ 与本任务无因果）；`check-arch-smoke`/`test-codegen` rc=2 同因（缺 LLVM 源 + 共享安装根被他人 `install-host` 占用）；`check-arch-self-test` rc=2，2 项 FAIL 均为「缺 `llvm-mc`」；`check-temp-dirs` rc=2 = 6 项（5 项他人 >2 h 临时目录 + 磁盘 85%），非本任务产生。

**KNOWN-RED 核实**：legacy 探针 `min_rom_probe_async_094t.py`、`min_rom_probe_integ051t.py` 实跑超时（红）；静态核实 `tests/arch/hart/cfx15.S`、`tests/ee-vast/hmon_vast.S` 等仍用旧 `escape …, [excp_cause_ip, n]` 语法（汇编器已改 `escape cfxHA`）。完成区已逐条登记 `tests/arch` 载体、legacy 探针、`tests/shared/asm/perm_hypv.inc`、`tests/ee-vast/*` 并指向 `m18-testcases-004`/内核任务；本提交 9 文件未改任何测试清单、`Makefile`、`expected-divergences.yaml` ⇒ **无静默跳过**。`tests/arch` 载体的**执行侧红我未独立复跑**（本工作树缺工具链，补装需 `install-host`，硬约束禁止覆盖共享安装根）——此项为采信，其余全部为本人输出。

**约束核验**：9 文件与「修改文件」逐条一致；无 `spec/`、`.tao/contracts/`、`Makefile`、其它组件；提交内无 `.dadao` 安装物；`git branch -r --contains a9b88db0` 为空（未 push）；状态 `待验收`；注入前后工作树快照一致（`git status` 空、12 个目标文件 md5 全等）。寄存器面/进入写入集合/escape 逐条对照 `spec/DADAO-12 §3.6/§4.7/§5.1–§5.4` 与补丁：`cg5 rc0–rc3` 写⇒`CFXREG`、`rc11` 复位全 1、`cg9 rc0–rc5` 写忽略（spec 明写「写忽略」）、`rc14` 复位 2、`rc15` 低 2 位忽略、`rc6–rc13`⇒`CFXREG`；同步写目标 `cg5 rc0–rc5`+`rc8–rc11`（`rc11`=被打断模式 monitor `cg8 rc1`）、异步只写 `cg9 rc0–rc4`+hart `cg5 rc8–rc11`（`rc0–rc3` 不变）；`escape` 四类 `CFXESC`/`ILLI` 全在状态切换前、`rc11` 整字写目标 monitor、`cause_id` 检查已删、`escape_num`+1。`node_probe_prelude.py` 向量 `rc10`→`rc15` **必要且正确**（`rc10` 已 `CFXREG`，不改则 power→hmon 无向量）。

**finding（阻断）**：F-R1 覆盖缺口——验收 1 要求 `cg0`–`cg3` 的 `rc14`/`rc15` 生效与 `rc8`/`rc10`⇒`CFXREG`，但 `case_mode_slots` 与 `case_mode_slots_cg0` **两个 case 都传 `CG3`**（前者 hmon、后者 umon），`CG0`/`CG1` 全程无断言、`CG2` 仅作 `rc15` 功能写入；而 `mode_slots_cg0` 的 docstring 写「cg0-cg2 share the same branch」、README/changelog/inventory 声称覆盖 `cg0`–`cg3`。实现分支本人已人工核对正确（`cfx_reg_ptr` 的 `cg<=2` 与 `cg==3` 同走 `cfx_mode_reg`），但该验收项无探针证明且命名/文档让覆盖看似已达成。修法：该 case 改传 `CG0`（建议 `CG0`+`CG2`）断言 `rc14`/`rc15` 生效、`rc8`/`rc10`⇒`CFXREG`（期望按 `mode[cg]` 行现场派生），并修正 changelog/inventory 的「18 例」（实为 19 例）。

**非阻断 finding**：F-R2 完成区 `check-temp-dirs` 记「192 项」，实跑 6 项；F-R3 完成区把 `check-arch-self-test` 归因「等 `m18-testcases-004`」，实跑 2 项 FAIL 均为「缺 `llvm-mc`」；F-R4 注入②红的形式是 guest 超时而非断言失配（engineer F9 已披露，认可不修）。

**判决**：Needs Revision（仅 F-R1 一项阻断；F-R2–R4 记录不阻断）。上述输出全部为本人终端实跑，未采信完成区转述。

### 第 2 轮 reviewer 验收

**F-R1 闭环（本人读码 + 重跑）**：`min_rom_probe_m18qemu008.py` 现有 `mode_slots_cg0/1/2/3` **四行各一 case**（`_mode_slots_case(cg)` 参数化，各 8 断言）：`rc14` 复位值 = spec `init` → 写 `other=(init+1)&3` → 读回 → 恢复 `init`；`rc15` 写/读（低 2 位规则仅在 §3.4 声明时断言掩码，否则写已对齐值断言精确 RW）；`rc8`/`rc10` ⇒ `CFXREG`（`rd20/rd21`、`rd26/rd27` 指令字逐字段比对）+ `rd25=2`。期望**现场派生**：`mode_facts()` 正则解析 `spec/DADAO-12 §3.1–§3.4` 各 cg 表，失败即抛 `OracleError`（表缺失 / switch reset 非数字 / switch·vector·reset 行不完整 / `rc8`、`rc10` 不在 reserved 集合），`MODE_FACTS = mode_facts()` 在 import 期求值 ⇒ 解析失败即整探针不可运行。

**重跑（本人执行，真实 rc）**：探针 → `summary: 21 case(s), 0 failure(s)` rc=0；`--self-test` → `self-test: PASS`，21 case 断言现场相加 = **150/150**（`mode_slots_cg0..cg3` 各 8/8，其余与上轮同）；运行期证据目录内 `run.sh` → `summary: checks=29 failures=0` + `m18-qemu-008 evidence: PASS` 退出码 0，其中两路注入各自报红（`escape_rc11_restore` rc=1、`async_entry` rc=1）并 `cp`+md5 还原、重建后 `21/21` 回绿；`make build-qemu` rc=0（`build-qemu: PASS`）。脚本内 8 个 `check-*` + `check-spec-refs` + `compileall` + `make_patch qemu` 重导 0 改动，全 rc=0。

**自设注入（本轮新角度）**：把 `mode_facts()` 的 `f["switch"] = rc` 改成 `rc + 1`（spec 派生槽位被污染）⇒ `mode_slots_cg0`/`cg1`/`cg2`/`cg3` **四 case 全红**，`summary: 21 case(s), 4 failure(s)` rc=1，证明断言确实依赖现场派生值而非写死；`cp`+md5 还原（与注入前逐字节一致）⇒ `21 case(s), 0 failure(s)` rc=0。

**文档一致**：README / `vast-arch-inventory.md` / `changelog.md` 均已改「**21 例 / 150 断言**」并写明「四行各自」与「现场取自 `DADAO-12 §3.1–§3.4`」；完成区 `check-temp-dirs` 已改「实测红 6 项（5 项他人 >2 h 目录 + 磁盘 85%）」、`check-arch-self-test` 归因已改「本工作树未构建 LLVM、缺 `llvm-mc`」（旧向量语法错单列为 ② 范围），F-R2/F-R3 处置在审阅记录中有行可查。

**范围**：`d7b57a51` 恰 **5 文件**（本任务书、`components/qemu/changelog.md`、`tests/arch/vast-arch-inventory.md`、`tools/testcases/arch/README.md`、`min_rom_probe_m18qemu008.py`），无 `.patch`、`spec/`、`.tao/contracts/`、`Makefile`、其它组件；`28c78c60` 是 merge master，其相对第一父带入的 19 文件全部来自 master 侧提交（`3087ce2e`/`310d5972`/`dcbf6385`/`f012ca03`），非本任务改动；`git branch -r --contains d7b57a51` 输出为空（**未 push**）；状态 `待验收`；注入前后 `git status` 空、探针与 `DADAO-12` md5 全等。

**判决**：**Accepted**（F-R1 已闭环，F-R2/F-R3 已按上轮 finding 修正，F-R4 维持披露）。以上均为本人终端实跑输出。
