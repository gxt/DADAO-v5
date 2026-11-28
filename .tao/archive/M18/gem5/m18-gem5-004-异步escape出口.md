# m18-gem5-004: gem5 实现异步 escape 出口（cg5 rc8–rc11、cg9 新布局）

**模块**：gem5
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入）、`m18-llvm-002`（汇编）、`m18-testcases-004`（向量）
**可并行分片**：否（同 `components/gem5`）
**预估**：3–4 h（标定：同档 gem5-001/002 2–3 h；本任务含布局 + escape + 入口，取 1.2–1.5×）
**档位**：大改（gem5 异常模型）
**状态**：已验证
**执行环境**：本地

## 背景

`m18-spec-007`/`ADR-0061 R3`：`cg5 rc0`–`rc3` 入口记录（只读）、`rc8`–`rc11` 出口意图；`cg9 rc0`–`rc4`/`rc14`/`rc15`；`escape cfxHA` 按 `rc8`–`rc11` 返回并整字写目标 monitor `cg8 rc1`。gem5 仍是 R2。

## 目标

1. 寄存器面：`cg5` 新布局（`rc0`–`rc3` 只读、`rc4/rc5`、`rc8`–`rc11`、`rc11` 复位全 1、删 pending）；`cg9` 新槽位；`cg0`–`cg3` switch/vector → `rc14`/`rc15`，旧 `rc8`/`rc10` ⇒ `CFXREG`。
2. 进入：同步写目标 cfx `cg5 rc0`–`rc5`+`rc8`–`rc11`；异步写 `cg9 rc0`–`rc4` + hart `cg5 rc8`–`rc11`。
3. `escape`：`imms18=0`（非 0 ⇒ `ILLI`）；`cfxha`=当前 cfx；不得升权；目标未实现/无 monitor ⇒ `CFXESC`；跳 `rc10`；`rc11` 整字写；`escape_num` +1。
4. 与 QEMU/RTL 同 ELF 签名一致；不一致登记 `expected-divergences.yaml`（含 `DIV-*` 增删）。
5. 不做：不改 QEMU/RTL/IDL/LLVM/内核/spec。

## 验收（逐条贴真实 rc）

1. 构建与单测 rc=0；`m18-testcases-004` 向量在 gem5 上可跑条目通过。
2. 同 ELF 与 QEMU 签名一致；`expected-divergences` 更新且 `check-*` rc=0。
3. 可达 FAIL ≥2 路（`rc11` 增量写；升权不判），`cp`+md5 还原回绿。
4. 不回归：既有 gem5 cfx/缓存代表集；`check-patch-tree` gem5 段 0 problem；`check-component-changelog` rc=0。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/gem5/patches/**`、`components/gem5/changelog.md`、`tests/arch/**`、`tests/arch/expected-divergences.yaml`、本任务书。
3. 不改其它实现/spec/契约/Makefile；不改版本号；`cp`+md5 还原；等 gem5 写者窗口。

## 待裁定

无。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` → **PASS=42 FAIL=0，exit 0**。含 `build-gem5` PASS；`check-gem5-decode` 263/263 + 391/391 + 28/28 + 2/2（failures 0）；B6 执行 harness 30/30（failures 0，`imms18 ≠ 0 ⇒ ILLI` 全例）；用 `f6f87ff2`（m18-testcases-004，spec 0.8.0）向量树 + 同源重建的 step5 BootROM 在 gem5 上跑 `arch-hart-001` 124 槽、`arch-hart-002` 38 槽×2、`arch-pmem-001` 48 槽、`arch-pmem-002` 10 槽×2 全 PASS（`run.json` verdict 全 PASS）；cfx4/PTW 14 例非回归 PASS；cfx5 寄存器面 `arch-cache-001/002` PASS（003/004 见遗留⑤）；`check-patch-tree` gem5 段 0 problem、`check-component-changelog`/`check-knowledge-refs`/`check-tests-index` rc=0；两路注入先红后还原重建回绿。另单跑 `run_arch --self-test` PASS、`check-tasks` rc=0。
**修改文件**：`components/gem5/patches/**`（11 份：`node_cfx.{cc,hh}`、`tiny_cfx.{cc,hh}`、`exec/b6.{cc,hh}`、`exec/b6_test.cc`、`inst.cc`、`isa.cc`、`decode/decode_table.inc`、`decode/decode_assertions.inc`）、`components/gem5/decode-assertions.tsv`（`gen_decode_table.py` 生成物，与补丁同批、非手改，`check-gem5-decode` 必需）、`components/gem5/changelog.md`、`tests/arch/expected-divergences.yaml`、`tests/arch/hart/README.md`、`tests/arch/pmem/README.md`、`tests/arch/vast-arch-inventory.md`、本任务书；未改 spec/契约/QEMU/RTL/IDL/LLVM/内核/Makefile。
**验收结果**：① 寄存器面：`cg5 rc0`–`rc3` HW/RO（写⇒`CFXREG`）、`rc4/rc5` 原因、`rc8`–`rc11` 出口意图、`rc11` 复位全 1、删 pending；`cg9 rc0`–`rc5` HW/RO、`rc6`–`rc13`⇒`CFXREG`、`rc14`/`rc15` RW；`cg0`–`cg3` switch/vector→`rc14`/`rc15`、旧 `rc8`/`rc10`⇒`CFXREG`。② 进入：同步写目标 `cg5 rc0`–`rc5`+`rc8`–`rc11`；异步只写 `cg9 rc0`–`rc4`+hart `cg5 rc8`–`rc11`（hart `rc0`–`rc3` 不动）。③ `escape cfxHA`：`imms18≠0`⇒`ILLI`（Node 直调分支已删，统一走 B6）、`cfxha`≠当前/升权/目标未实现/无 monitor⇒`CFXESC`、跳 `rc10`、`rc11` 整字写目标 monitor `cg8 rc1`、`escape_num`+1、无帧有效位。④ 注入：A `rc11` 改 `|=` ⇒ `slot 74 escape rc11 whole word … expected 0x0123456789abcdef actual 0xffffffffffffffff`；B 删升权判定 ⇒ supv→hypv 自环、`模拟器超时（10s）`；两路均 `cp`+md5（原 `5779348d…`）还原、重建后 124 槽回绿。
**新发现/坑**：① 共享 `.dadao/tests/bootrom/step5/bootrom_step5.bin`（md5 `fd12e63c…`）的电源阶段仍是 **R2**（反汇编 `cfx2rc cfx_hmon cg3 rc10/rc8`），在 R3 gem5 上首个 `CFXREG` 把 PC 送到未重定位的默认 hmon 向量、二次 `CFXMEM` 停机；证据改为从同一 0.8.0 树重建（md5 `5ff4418e…`），未覆盖共享安装根。② Node 的 `escape` 曾被 `inst.cc` 直调绕过 B6 并吞掉 `imms18`（`imms18=3/4` 变 `CFXESC` 而非 `ILLI`）；删直调、统一 `runB6 → executeEscape → escapeFrom` 后修复。③ 共享 QEMU 源/二进制仍是 R2（`target/dadao/cpu.c` 无 `escape_run_mode`/`rc8` 记号），同 ELF 对照不可做，已登记 `DIV-16`。④ 证据的注入检测最初只 grep `run_arch` 输出，槽名在驱动 `run.log`，已改为两处都查。⑤ `tools/gem5/check_b6.py` 的 `EXPECTED_LEGALITY` 仍是 spec-007 前口径（基线红，见遗留③）。
**遗留问题**：KNOWN-RED（逐条登记、本轮不改）：① `m18-gem5-005` 源接口 `cg15`/`cg16` + `cg15 rc3` 掩码（`DIV-16` temporary）；② RTL（`m18-chipyard-002/003`）、IDL（`m18-idl-003/004`）、内核（`m18-linux-026`）的 R3/源接口迁移；③ `tools/gem5/check_b6.py` 需把 `EXPECTED_LEGALITY["escape_ciii_cfx"]` 改为 `("imms18 == 0", _CFX)` 并删 `_SBZ_ESCAPE`/`_ESCAPE_CG9`（两行），否则该非门控 harness 报 contract 漂移；④ `tests/unit/gem5/tiny_hmon/tiny_hmon.S` 仍用旧 `escape …, [off]` 语法（`m18-llvm-002` 后不可汇编），归该探针迁移面；⑤ `tests/arch` 的 cache/time/env 等 full 级载体仍按 R2 读故障现场（如 `cache/cache.body.S` 的 `REC_CAUSE` 把 `cg5 rc2`/`rc4` 当 cause/info），与 R2 `expected.yaml`/oracle 配对，R3 下错位——实测 `arch-cache-001/002` PASS、`arch-cache-003/004` 红，归 `m18-testcases-005` 的载体迁移，统一测试前不判。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`node_cfx.{hh,cc}`（寄存器面/进入/异步捕获/escape）、`tiny_cfx.{hh,cc}`（同步 cg5 + cg3 rc14/15 + escape）、`exec/b6.{cc,hh}` 与 `b6_test.cc`、`inst.cc`（去 Node escape 直调）、`isa.cc`（dump）、`decode_*` 重生成、`changelog`、`tests/arch` 三份文档 + `expected-divergences.yaml`、证据脚本。
**逐行要点**：`cg5` 入口记录在 step 5 采样 `entryMode`/`cfxCode` 后才切模式，`rc8`–`rc11` 由 `rc0`–`rc3` 复制；`prevIntrMask` 取入口模式 monitor 的 `cg8 rc1`，无 monitor 行 fail-safe 全 1。`cg9` 写 `rc0`–`rc5` 忽略不报异常、`rc6`–`rc13` ⇒ `CFXREG`；异步进入只写 hart `rc8`–`rc11`。`escape` 四类拒绝全部先于任何状态切换，`rc11` 整字写目标 monitor、`escape_num` 记在被退出的 cfx。Tiny 只有 hypv（`rc14` 写忽略、`rc15` 低 2 位忽略），目标模式无 monitor 自然 `CFXESC`。b6 的 `executeEscape` 只接受 `imms18=0`；`b6_test` 的旧 cg5 +4 / cg9 帧例全部改 `ILLI`。未改函数对外签名（`escapeFrom(cfxha, byteOffset)` 保留，b6 恒传 0）。
**防造假**：注入均 `cp` 备份 + md5 前后对账（原 `5779348d…`）、注入后 `git -C .work/source/gem5 status` 非空、还原后为空；`run.sh` 无 `tee` 吞码；计数现场统计（42 项）不写死。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `imms18=3/4` 变 `CFXESC`（Node 直调吞掉 imms18） | ✅已修 | 删 `inst.cc` 的 `escape_ciii_cfx` 直调，走 B6 | arch-hart-001 124/124；注入 A/B 均红 |
| F2 共享 step5 BootROM 是 R2，R3 gem5 首条 `cfx2rc cg3 rc15` 即 `CFXREG`→`CFXMEM` | ✅已修 | 证据从 0.8.0 树重建私有 BootROM 并 `--bootrom` | `step5: PASS`；6 个 case 全 PASS |
| F3 注入检测只 grep `run_arch` 输出 | ✅已修 | 同时 grep 驱动 `run.log` | 两路“detected”PASS |
| F4 `run_case` 用 `local case=$1 … $case`（`set -u` 下未定义） | ✅已修 | 改名 `case_id` 并分行 | 脚本 42/42 |
| F5 `check_b6.py` `EXPECTED_LEGALITY` 旧口径 | ⏸延后 | 不在允许文件集；harness 本体 30/30 通过 | 遗留③ |
| F6 `check-patch-tree` 总 rc=2 | ❌不修 | 8 problem 全在 qemu(6)/musl(2)，gem5 段 0 problem | 实测日志 |
| F7 共享 QEMU 非 R3，同 ELF 对照不可做 | ⏸延后 | 登记 `DIV-16` + 遗留① | QEMU 90s 超时、无 R3 记号 |

残留：遗留①–⑤；所有可在本任务内修的 finding 已修，状态对账为「待验收」。

### 第 1 轮 reviewer 验收

**重跑记录（均本人执行，仓库根）**
1. 运行期证据目录内 `run.sh` 第 1 次：`PASS=42 FAIL=0`、尾行 `m18-gem5-004 evidence: PASS`；两路注入各自 `detected`（`slot 74 escape rc11 whole word … actual 0xffffffffffffffff`；`模拟器超时（10s）`）+ `restored md5=5779348d…` + `back to green`。第 2 次同脚本 **rc=0**（`RUN2_RC=0`，`PASS=42 FAIL=0`）。向量现场计数（`run.json` `signature_count`）：arch-hart-001 **124**、arch-hart-002 **38×2**、arch-pmem-001 **48**、arch-pmem-002 **10×2**、cfx4/PTW **14**、arch-cache-001/002 **21/12**，verdict 全 PASS；`vector md5 207606c9…` 两次相同。
2. **自设注入 C**（`escape` 忽略 `imms18`）：`exec/b6.cc` `if (imms18 != 0)` → `if (false)`（`cp` 备份，md5 `d6e9caa8…`→`cb47ca5b…`）→ `make build-gem5 rc=0` → arch-hart-001 **rc=1**，4 红＝slot 56/57（`escape imms18=3` cause/info）、slot 59/60（`imms18=4`）；`cp` 还原 md5 `d6e9caa8…` 相等、源树干净、重建 `rc=0` → 复跑 **rc=0**、124 槽 PASS。
3. `make -s check-gem5-decode` **rc=0**；`make -s check-tasks` **rc=0**；`check_decode` `positive 263/263, negative 391/391, legality 28/28, legacy 2/2, failures 0`；B6 harness `B6 coverage 30/30, failures 0`；`check-patch-tree` 8 problem 全在 qemu(6)/musl(2)，`gem5: 106 patch(es)` **0 problem**（total rc=2，基线）。
4. `make -k check` **rc=2**，红目标恰 6 且与本提交 18 文件无交集：`check-patch-tree`(qemu/musl 共享源树)、`check-musl-freshness`(toolchain/builtins stamp)、`check-milestones-fresh`(9 VIOLATION 全 m16-*)、`check-run-artifacts`(659 非法名，22 条 `.EXIT`，属本任务仅 1 条)、`check-interface`(LLVM lit 294≠309)、`check-temp-dirs`(他任务陈旧临时目录 + 文件系统 88.3%) ⇒ 6 项基线红，非本提交。
5. `python3 tools/gem5/check_b6.py` **rc=1**：`escape_ciii_cfx: legality ('imms18 == 0', …) != ('imms18[17:2] == 0', 'imms18 != 3', …)`；它读 `contracts/opcodes.yaml`（父提交已为 `imms18 == 0`）⇒ 基线红；已由 master `4c7fb95e` 归 `m18-gem5-005`（允许改 `tools/gem5/check_b6.py`、并关闭 `DIV-16`）。
6. `arch-cache-003/004` 本人复跑 **rc=1**（16/15 槽，槽 1 起字段错位 `0x4` vs `0x10105c`）＝ R2 载体读 R3 `cg5`，与遗留⑤自述一致；迁移面已归 `m18-testcases-005`（其目标 1 含 `tests/arch/**`）。

**代码核验（读补丁与已应用源）**：`cg5 rc0–rc5` 写返 `nullptr ⇒ CFXREG`、`rc8–rc11` RW、`escapeIntrMask = ~0ULL`（复位全 1）、`pending` 字段已删；`cg9 rc0–rc5` 写忽略不报异常、`rc6–rc13` 读写 false ⇒ `CFXREG`、`rc14/rc15` RW 复位 2；`cg0–cg3` 的 switch/vector 落 `rc14/rc15`、旧 `rc8/rc10` ⇒ `CFXREG`；同步进入写目标 `rc0–rc5`+`rc8–rc11`，异步只写 `cg9 rc0–rc4` + hart `cg5 rc8–rc11`（不动 `rc0–rc3`）；`executeEscape` 只认 `imms18==0`（`b6_test` 非零全 ILLI）、`inst.cc` 直调分支已删；`nodeEscape` 顺序＝保留 cfx⇒ILLI、`cfxha`≠当前/升权/目标未实现/无 monitor⇒`CFXESC`（全部先于状态切换）、`rc11` 整字写**目标** monitor `cg8 rc1`、`escape_num`+1、跳 `rc10`。与 `spec/DADAO-12 §3.6/§4.7/§5.1/§5.3` 逐条一致。

**约束核验**：18 文件与完成区声明逐条相符；无 spec/契约/Makefile/QEMU/RTL/LLVM/内核改动；分支未 push；状态 `待验收`；验收前后快照对账＝工作树干净、4 个关键产物 md5 不变，唯一新增改动是本审阅记录；证据脚本未用 `tee` 吞码、计数现场派生、两路注入与本路注入均 `cp`+md5 可还原。

**finding（文档级，不阻断，交 architect 收尾改）**：F1 `expected-divergences.yaml` 的 `DIV-16.impact` 写「spec/QEMU/**RTL** 已是 0.8.1-rc」不实——`m18-chipyard-002/003` 均「待开始」，RTL 仍 R2/0.8.0；同一提交的 `DIV-11.impact` 却写「RTL 仍按 R2 的 escape 编码」，两句自相矛盾，请删去该句中的 RTL。

**判决：Accepted**（验收命令块在本人两次重跑下全绿、注入三路可达 FAIL 且还原回绿、约束无违反；F1 为文档级小错，按规程记 finding 不返工）
