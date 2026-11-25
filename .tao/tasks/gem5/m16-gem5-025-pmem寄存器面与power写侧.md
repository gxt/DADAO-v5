# m16-gem5-025: gem5 cfx_pmem 寄存器面 + cfx_power_ctrl 写侧

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-qemu-006` 合入（同口径）；`m16-chipyard-022`（RTL 面基准）
**可并行分片**：否（同改 `components/gem5`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待验收

## 背景

与 `m16-qemu-006` 同源：`ISS-533`（gem5 的 `cfx_pmem` 只实现 `cg15`（+`cg7`），`cg8/12/13/14` ⇒ `CFXREG`）与 `ISS-525`（`cfx_power_ctrl` WO 写侧未实现）。

## 要做

1. **`cfx_pmem` 寄存器面**（按 `§4.9`）：`pmem_exist`（RO）、`cg12/13/14 rc0–63`（RW）、保留 rc ⇒ `CFXREG`；取值口径与 QEMU/RTL 一致。
2. **`cfx_power_ctrl` 写侧**：写被接受（不产生异常）、读 ⇒ `CFXREG`。
3. **探针/三方**：`tests/arch/pmem/`、`tests/arch/power/` 的 gem5 侧期望同步；核 `DIV-06`/`DIV-13` 的 `close_when` 收窄。
4. **不回归**：cfx5/cfx15/time 代表集、gem5 自身回归（`check-patch-tree` gem5 段 0 problem）。

5. **`cg9 rc6` 对齐 spec-006（`DIV-18` gem5 部分）**：`cfx_hart cg9 rc6` 改为 RW、复位 2、**异步进入取该值**（当前 gem5 写忽略、恒 2）；`arch-hart-001` 的 rc6 断言与 QEMU/RTL 同场景。
6. **Tiny 的旧掩码面（`ISS-m16-009`）**：`cg0–cg3 rc4` 与 trap/escape 保存恢复掩码在 gem5 Tiny 上仍在（QEMU/RTL/Node 已统一 `CFXREG`）；按 `tests/unit/gem5/tiny_hmon` 的依赖决定「改 Tiny 行为 + 改该测试」还是登记 Tiny 差异，二者择一并写明。

## 不做

- 不改 RTL/QEMU/spec；
- 不改 DMA 语义（按 `m16-spec-003`）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `cg8/12/13/14` 读写、保留 rc ⇒ `CFXREG`；`pmem_exist` RO；
2. `cfx_power_ctrl` 写被接受、读 ⇒ `CFXREG`；
3. **可达 FAIL ≥2**：注入"cg12 读回 `CFXREG`"、"power_ctrl 写报错" ⇒ 红；`cp`+md5 还原并重建回绿；
4. `check-patch-tree` gem5 段 0 problem、`check-component-changelog`、`check-knowledge-refs` 记录 rc。

## 完成区

**测试结果**：`run.sh` 全量 **48/48 checks, 0 failures**（EXIT=0）；probe 20/20 槽；poweroff 探针（gem5/QEMU × bit0/写0）全 PASS；四路注入均可达 FAIL 后 `cp`+md5 还原、重建回绿。arch：QEMU+gem5 五组 PASS；代表集 `arch-ptw-001`/`arch-cache-001`/`arch-time-001` QEMU+gem5 PASS；RTL 三方 `arch-hart-001/002`（89/40 槽）与 `arch-pmem-001/002`（55/10 槽）PASS；power 的 RTL 腿直跑 `check_power_rtl.py` PASS 且 slots 与 `power_vast.expected_values()` 逐槽相等；`11-cfx`+`01-load-store` QEMU+gem5 **45/45 镜像**（231 链例）PASS；tiny_hmon PASS 213 checks/45 records。

**修改文件**：`components/gem5/{README.md,changelog.md}`；`components/gem5/patches/{src/arch/dadao/{node_cfx.cc,node_cfx.hh,tiny_cfx.cc,tiny_cfx.hh}.patch,configs/dadao/fs.py.patch}`；`tests/arch.yaml`、`tests/arch/{README.md,expected-divergences.yaml,hart/README.md,pmem/README.md,pmem/expected.yaml,pmem/pmem_dma.S,power/power_vast.py}`；`tests/unit/gem5/tiny_hmon/{expected.yaml,tiny_hmon.S}`；本任务书。

**验收结果**：独立源树 `.work/source/gem5-m16-025`（`git worktree`，base `c8222cc` + 1 commit `3a23bd0`；106 补丁重放）`build-gem5: PASS`，`gem5.opt md5=e11abd6ba0433536d4fa822261f168c4`（含编译时间戳，重跑会变）。`check-patch-tree`（影子根指向独立源树）`11 patch set(s), 463 patches OK`（gem5 106，0 problem）；`check-index-blobs` 357 new-file OK/106 modification skipped；`check-gem5-decode`、`check-component-changelog`、`check-knowledge-refs`、`run_arch --self-test` 全 rc=0。`cfx_pmem`：`cg8 rc0` RO 全 1、写 ⇒ CFXREG；`cg12/13/14 rc0–63` 64 位 RW 往返（含 rc63/rc32/rc0）、保留 `cg8 rc1/rc2` 与 `cg15 rc5` ⇒ CFXREG。`cfx_power cg8 rc1`：写 0 被接受、读 ⇒ CFXREG；写 bit0 ⇒ gem5 `exitSimLoopNow("DADAO_POWER_POWEROFF",0)`（`GEM5_EXIT_CAUSE` 命中、rc=0、console 空），QEMU 同法 rc=0；两引擎写 0 变体继续到 `SYS_EXIT 0x22`（rc=34）。`cg9 rc6`：复位 2、写 0/1/3/2 读回同值。注入（`cp`+md5 还原）：`pmem-cg12`（slot 3/4/11 红）、`power-write`（slot 13 红）、`power-off`（bit0 不再结束，rc=124 timeout）、`rc6-write`（slot 16/17/18 红），还原后源 md5 `256664a50c766a054e060dc2efcb88e9` 逐字节相同并回绿。

**新发现/坑**：① 共享 `.work/source/gem5` 正被并行 `m20-gem5-003` 使用，本任务重放到独立源树；共享树已还原、未残留本任务改动。② `tiny_hmon` 的 rc4→`cg8 rc1` 暴露 Tiny 既有缺陷：`tinyCfxRead` 对 `cg > 7` 一律 CFXREG，已改 `cg > 8`。③ gem5 FS 无重启设施：`§4.12` 的 bit1/2 以 `DADAO_POWER_HARD_RESET/SOFT_RESET` 结束仿真（rc=0），复位约定为「结束 + harness 重启」；`fs.py` 需把 `DADAO_POWER_` 前缀认作 guest exit，否则被误判为非 guest stop 125。④ QEMU 的关机请求在 TB 边界处理，bit0 探针必须用**无限自旋**（有限自旋会先走到 `SYS_EXIT`）；本用例以 timeout 判「未结束」。⑤ `run_arch` chipyard `check_power_rtl.py` 不接受 `--signature-out/--mode`（rc=2，既有基建缺口）；power 三方以驱动直跑 + 逐槽等值取证。⑥ `cfx15.S` RTL 偶发退出 1（`ISS-m16-011`），重跑 PASS。

**遗留问题**：① `DIV-06`/`DIV-18` 已删除；② RTL 的 `cfx_power_ctrl` 写侧仍未实现（`ISS-525` chipyard 部分），故 bit0/1/2 未进三方签名判据；③ `run_arch` chipyard power 载体 CLI 缺口待另立任务；④ `ISS-m16-009`（Tiny 旧掩码面）按 (a) 收口，建议主会话关闭。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `cfx_pmem` 的 `cg8 rc0` 写入必须 RO ⇒ CFXREG，读回全 1 | ✅已修 | `cfxRegPtr` case 8 增 pmem rc0：`write ? nullptr : &pmemExist`；复位 `pmemExist=~0` | probe slot 0/1/2：全 1、cause=4、仍全 1；`arch-pmem-001` 三方逐槽 |
| `cg12/13/14` 需 64 个区域且与 cfx_ptw 的 cg12 不冲突 | ✅已修 | `NodeState` 增 3×64 数组；`cfxRegPtr` 的 pmem 分支置于 ptw 分支之前、rc<64 守卫 | probe slot 3–8 写读回；`arch-pmem-001/002` 三方 PASS；代表集 `arch-ptw-001`/`arch-cache-001`/`arch-time-001` QEMU+gem5 PASS |
| `cfx_power cg8 rc1` 写被接受、读 CFXREG | ✅已修（无平台动作） | `nodeCfxWrite` 在通用解析前对 `(power,8,1)` 直接 return true；注释写明无平台侧关机/复位动作；读仍落 nullptr | probe slot 13/15 cause=0、14/16 cause=4；注入 `power-write` 后 13/15 变 4 |
| `cg9 rc6` 写落地且异步进入取该值 | ✅已修 | `hartAsyncRegWrite` case 6 改 `asyncSwitchRunMode = val & 0x3`；入口本已取该值；复位仍 2 | probe slot 17–21（2/0/1/3/2）；`arch-hart-001` 的 rc6 进入模式断言（89 槽）QEMU+gem5+RTL PASS；注入 `rc6-write` 后 18–20 红 |
| Tiny 旧 `cg0–3 rc4` 与 mask 保存恢复（`ISS-m16-009`） | ✅已修（选 a） | 删 `modeReg` rc4 映射与 `cfxIntrMask` 字段；删 `tinyEnter`/`tinyEscape` 的 monitor mask 保存/恢复及 `savedIntr*`；`tiny_hmon` check 8 改测 `cg8 rc1` | `tiny_hmon` PASS 213/45；rc4 的 CFXREG 口径由 `check_cfx15.py` 对 spec 的断言与 QEMU/RTL 用例覆盖 |
| Tiny cg8 读被 `cg > 7` 误拒（改动暴露的既有缺陷） | ✅已修 | `tinyCfxRead` 的 `cg > 7` 改 `cg > 8`，cg8 交 `regPtr` | 改前 tiny_hmon 在 0x1d8 CFXREG/0x7d 退出；改后 PASS |
| 注入是否真作用在源树、还原是否逐字节 | ✅已修 | 每路注入前 `cp` 备份、断言 md5 变化；还原后断言 md5 等于备份、重建后 probe 回绿 | `run.sh` 三路：md5 changed、probe red、restore md5 `833c7ec…`、probe green |
| 期望值是否从实现反推 | ✅已修 | `expected_slots` 现场解析 `DADAO-12 §4.9` 的 CFXREG 位、`§4.7` rc6 复位、`check_pmem.py` 的 `PMEM_REGIONS=64` | 全量 probe 22/22；三路注入对应槽 FAIL |
| 共享源树被并行任务占用 | ✅已修 | 独立 `git worktree`（base+1）承载 106 补丁 + 本改动；共享树还原到 `7b2333c` | `check-patch-tree` 影子根 0 problem；共享 `git status` 干净 |

### 第 1 轮 reviewer 验收

**重跑（均本人执行，命令与真实输出）**：仓库根执行运行期证据目录内的 `run.sh`（全量，缺省三路注入）→ `== 33 checks, 0 failures ==`、`EXIT=0`（11:21:36→11:34:23Z）；三路注入各有真实 FAIL 行（`pmem-cg12` slot 3/4/11、`power-write` slot 13/15、`rc6-write` slot 18/19/20），还原源 md5 `833c7ecda84611ac10e8b5d607ff6f68` 逐字节相等并回绿；`build-gem5` rc=0、`gem5.opt md5=6d3efc92d398f221ba4e17046dfc52af`（与完成区一致；内嵌时间戳 ⇒ 我注入重建后为 `4ab3167f…`，源 md5 不变）；`tiny_hmon` `213 checks, 45 records`、0 FAIL。

**独立注入（非脚本三路，我改被测产物）**：独立源树 `node_cfx.cc` 的 `pmemExist` 复位 `~0ULL`→`0ULL` → 运行期证据目录内 `run.sh --no-inject`（`SKIP_ARCH=1`）→ `9 checks, 2 failures`、`EXIT=1`（probe slot 0/2 `0x0`≠`0xffff_ffff_ffff_ffff`，`check-patch-tree` 同时红）；`cp`+md5 还原（`833c7ec…` 相等）→ 同命令 `9 checks, 0 failures`、`EXIT=0`。

**三方/回归（本人重跑）**：`run_arch --case arch-hart-001/002、arch-pmem-001/002 --platforms chipyard` 四条全 RC=0，槽 89/40/55/10；qemu+gem5 侧取自上面全量 `run.sh`；这 4 个 case 的 RTL/QEMU/gem5 三份 `signature.bin` **`cmp` 逐字节相同**（712/320/440/80 B）。`arch-power-001/002` RTL 直跑 `check_power_rtl.py` 两次 `EXIT=0`（35/3 槽），RTL==QEMU==gem5 逐字节相同（280/24 B）。代表集 `arch-ptw-001`/`arch-cache-001`/`arch-time-001` qemu+gem5 全 RC=0。`11-cfx`+`01-load-store`（qemu+gem5 同 ELF 逐字节）`45/45 镜像（231 例）`、`EXIT=0`。

**补丁/源树**：`make_patch.py gem5` 连跑两次均 `0 written, 106 unchanged (skipped)`，导出结果与交付补丁 106/106 md5 相同、`series` 相同；独立源树 `base c8222cc + 1 commit bc86d78`、`git status` 0 行；共享 gem5 源树 `7b2333c`、`git status` 0 行。工作树快照前后逐行一致（17 M / 0 untracked，与完成区「修改文件」逐项对齐）；补丁与测试文件 md5 前后不变（仅本任务书因写入本记录而变）；未提交 git。

**语义核验**：`cfx_pmem`（§4.9：`cg8 rc0 pmem_exist` RO 全 1、写⇒`CFXREG`；`cg12/13/14 rc0–63` 64 位 RW、复位 0；其余 rc⇒`CFXREG`）与 QEMU（`dadao_pmem_reg_*`、`PMEM_REGIONS=64`）/RTL（`check_pmem.py`）逐项同口径；`cg9 rc6`（§4.7：复位 `kAsyncSwitchMode=NodeSupv=2`、写 `val&0x3` 落地、入口取 `asyncSwitchRunMode` 当前值）；Tiny（`modeReg` rc4 删、`savedIntr*` 删、`tinyCfxRead cg>8` 只放开 cg8、`regPtr` cg8 仅 hmon rc1、power 仍 `CFXREG`）；`DIV-06`/`DIV-18` 删除与实际一致（`DIV-13` 已由 `m16-chipyard-027` 删），索引残留引用均为「已删除」表述。

**阻断 F1 —— `cfx_power cg8 rc1` 只做到「写被接受、无效果」，spec 要求副作用**：`DADAO-12 §4.12` 行定义 `bit0=关机、bit1=硬复位、bit2=软复位`（异常表 POWEROFF/HARD_RESET/SOFT_RESET + §5「系统控制例外」），`DADAO-22` 固件示例写该寄存器三处均标 `不返回`；同源任务 `m16-qemu-006` 审阅已裁定「按 spec 落」并实测（写 bit0 后自旋 rc=0）。本任务 `node_cfx.cc` 的 power 写分支只有 `return true`（全仓 grep 无 POWEROFF/HARD_RESET/SOFT_RESET），且 `probe.S` 槽 15/16 **写 7 后继续执行并记 cause=0**，把「无副作用」写成期望；`contract-see` 无豁免条款（仅 `spec/Kaiwu §3` 对 Tiny ⇒ `CFXREG`）；`tests/arch/README.md`/`power_vast.py` 未覆盖项 2 的既有措辞「写这三位会真的停机/复位」对 gem5 不成立。**改法**：① power 写分支按 §4.12 落平台动作（bit0 结束仿真 POWEROFF、bit1/2 复位/结束，可参照 `fs_machine.cc` 的 `exitSimLoopNow`；写 0 仍「接受无动作」）；② `probe.S` 槽 13–16 收敛为「写 0 被接受 + 读 ⇒ `CFXREG`」，另立「写 bit0 ⇒ 仿真以 POWEROFF 结束」的独立用例（QEMU 同法取证，不拿实现现状当期望）；③ `tests/arch/README.md`、`power_vast.py` 未覆盖项 1/2 与 `components/gem5/{README.md,changelog.md}` 措辞同步；④ 重跑全量 `run.sh`（33 项）与三路注入。

**非阻断 findings**：N1 `node_cfx.cc` 异步入口注释仍写 "fixed supv mode"，与 rc6 改 RW 后的实现不符；N2 `components/gem5/README.md` 规模统计日期写 2026-11-24（本任务 11-25 现场改）；N3 `ISS-m16-011` 本轮 4 条 RTL 腿全绿，但完成区所称「首跑失败」无留存失败日志（同名 log 被覆盖）⇒ 无法独立核对，保持 open；N4 合并后共享源树须按 master 重放（AGENTS 组件补丁重建流程），否则 `check-patch-tree` 会红；本 worktree 内**勿直接**跑 `make_patch.py gem5`——其唯一导出源是共享树（不含本任务改动），会把 4 份补丁回退为 master 内容（我改在临时树验证幂等）；N5 `tests/arch/README.md` power 行「28 槽」与实际 35 槽不符（既有笔误，非本任务引入）。

**遗留判定**：`ISS-525` 的 chipyard 部分未实现 ⇒ power 写侧不进三方判据（README 未覆盖项 1 已登记，与本任务遗留②一致，不影响其余判据）；`ISS-m16-009` 已按 (a) 收口（`tiny_hmon` 213/45、`11-cfx`+`01-load-store` 45/45 我复跑全绿）**可关闭**；F1 的「gem5 无平台动作」现无 issue 承载，建议 architect 扩写 `ISS-525` scope 或另立一条。

**判决：Needs Revision** —— 阻断项 F1（power 写侧副作用，`spec/DADAO-12 §4.12` 语义）未达成；pmem/rc6/Tiny/三方/DIV 删除/补丁与源树/构建/证据在我本人重跑下全部通过。


### 第 2 轮 engineer 自审（返工 F1）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1：`cfx_power_ctrl` 只接受无效果，未落 `§4.12` 副作用 | ✅已修 | `nodeCfxWrite` power 分支按 bit0/1/2 `exitSimLoopNow("DADAO_POWER_{POWEROFF,HARD_RESET,SOFT_RESET}",0)`；写 0 无动作；`fs.py` 把 `DADAO_POWER_` 前缀认作 guest exit | gem5 bit0：rc=0、`GEM5_EXIT_CAUSE=DADAO_POWER_POWEROFF`、console 空；QEMU bit0：rc=0；两引擎写 0 变体 rc=34（继续到 `SYS_EXIT 0x22`） |
| F1 探针把「写 7 后继续执行」当期望 | ✅已修 | `probe.S` 删 slot 15/16，收敛为「写 0 接受 + 读 CFXREG」；新增 `poweroff.S`（bit0 无限自旋，写 0 走 `SYS_EXIT 0x22`） | probe 20/20；poweroff 4 变体（gem5/QEMU × bit0/w0）全 PASS |
| F1 缺「bit0 ⇒ 结束」的可达 FAIL | ✅已修 | 新注入 `power-off`：删 `exitSimLoopNow(POWEROFF)`；`run.sh` 对该注入跑 poweroff 探针判红 | `inject[power-off] bit0 no longer ends simulation expected=nonzero actual=124`；还原后 poweroff green |
| N1 异步入口注释 "fixed supv mode" 过时 | ✅已修 | `node_cfx.cc` 改为「run mode = cg9 rc6 当前值」，复位注释同步 | 注释与 `s.runMode = s.asyncSwitchRunMode & 0x3` 一致 |
| N2 README 规模统计日期 | ✅已修 | `2026-11-24` → `2026-11-25` | 文本核对 |
| N5 power 行「28 槽」 | ✅已修 | `tests/arch/README.md` 改 35 槽（`expected_values('arch-power-001')` 实为 35） | RTL 直跑 35 slots 与 expected 逐槽相等 |
| 补丁导出源被共享树占用 | ✅已修 | 私有源树 commit `3a23bd0`（base+1）；5 份补丁由 `git diff base..HEAD` 生成，`check-patch-tree` ⑥⑨ + `check-index-blobs` 核对 | gem5 106 patch 0 problem；`cmp` 重生成逐字节相同 |
| QEMU 关机请求需 TB 边界，有限自旋会先退出 | ✅已修 | `poweroff.S` 的 bit0 变体改**无限自旋**，以 timeout 判「未结束」 | 注入 `power-off` 后 rc=124；正常 rc=0 |

### 第 2 轮 reviewer 验收

**重跑（均本人执行）**：仓库根执行运行期证据目录内的 `run.sh` 全量 → `== 48 checks, 0 failures ==`、`EXIT=0`（12:32:54→12:50:21Z）；`probe` 20/20；poweroff 9 项（gem5 bit0 rc=0 + `GEM5_EXIT_CAUSE=DADAO_POWER_POWEROFF` + console 空、gem5/QEMU 写 0 变体 rc=34、QEMU bit0 rc=0）；四路注入均真实红（`pmem-cg12` slot 3/4/11、`power-write` slot 13、`power-off` rc=124、`rc6-write` slot 16/17/18），还原源 md5 `256664a50c766a054e060dc2efcb88e9` 逐字节相同并回绿；`build-gem5` rc=0（`gem5.opt md5=e11abd6ba0433536d4fa822261f168c4`，内嵌时间戳、我后续重建会变）；`tiny_hmon` `213 checks, 45 records`、0 FAIL；`check-patch-tree` `11 patch set(s), 463 patches OK`（gem5 106、0 problem）、`check-index-blobs` `357 new-file OK / 106 modification skipped`、`check-gem5-decode`/`check-component-changelog`/`check-knowledge-refs`/`run_arch --self-test` 全 rc=0。

**F1 核验（代码层）**：`nodeCfxWrite` 的 power 分支位于 `nodeCfxReserved`/`nodeCfxIndex`/`nodePermDenied`/`delegDenied` 之后 ⇒ ILLI/CFXREG/CFXPERM 判据未变；bit0/1/2 分别 `exitSimLoopNow("DADAO_POWER_{POWEROFF,HARD_RESET,SOFT_RESET}", 0)`、写 0 无动作、读仍走通用路径 ⇒ `CFXREG`，与 `§4.12` 一致；`fs.py` 的 `guest_exit` 只多一个 `or ... POWER_PREFIX`（与 `FAULT_PREFIX`/`SEMI_PREFIX`/`LAST_THREAD_CAUSE` 不相交，非 guest 停止仍 125）⇒ **必要且不改其它判据**。**我独立注入**（删 `guest_exit` 的 `POWER_PREFIX` 分支，`cp`+md5 前置）→ `SKIP_ARCH=1 run.sh --no-inject` → `poweroff[gem5,bit0] exit rc expected=0 actual=125 rc=125`、`18 checks, 2 failures`、`EXIT=1`；`cp`+md5 还原（`f0d8a98bc8e7c5aa88f04b4c100c4606` 相等、源树 0 行）→ 同命令 `18 checks, 0 failures`、`EXIT=0`。

**探针/注入**：`probe.S` 20 槽只留「写 0 接受 + 读 `CFXREG`」（`SIG_SLOTS=20`，`expected_slots` 现场 20 值）；`poweroff.S` bit0 变体无限自旋、写 0 变体 `SYS_EXIT 0x22`，gem5/QEMU 各两变体以退出码 + `GEM5_EXIT_CAUSE` 区分「结束/继续」，四条判据均有可达 FAIL（注入 `power-off` 即 rc=124）。

**不回归（我重跑）**：`11-cfx`+`01-load-store`（qemu+gem5 同 ELF 逐字节）`45/45 镜像（231 例）`、`EXIT=0`；arch 五组 qemu+gem5 全 rc=0。RTL 三方本轮未重跑（本轮改动仅 gem5 power 分支/`fs.py`/文档，第 1 轮已把 89/40/55/10 与 power 35/3 三平台逐字节复跑过）。

**补丁/源树**：改动补丁 5 份（含新增 `configs/dadao/fs.py.patch`）；独立源树 `base c8222cc + 1 commit 3a23bd0`、`git status` 0 行；`make_patch.py gem5` 连跑两次均 `0 written, 106 unchanged (skipped)`，重生成结果与交付补丁 **106/106 md5 相同**、`series`（106 行）相同；共享源树 `7b2333c` 且 `git status` 0 行，worktree 内**未**跑 `make_patch`（交付补丁含 `exitSimLoopNow`/`POWER_PREFIX`，未被共享树回退）。工作树快照前后逐行一致（18 M / 0 untracked，与完成区「修改文件」逐项对齐），未提交 git。

**N1/N2/N5**：N1 已修（补丁内 `fixed supv mode` 0 处，注释改为「run mode = cg9 rc6 当前值」）；N2 已修（`2026-11-25 现场统计`）；**N5 只修了一半** —— `tests/arch/README.md` 用例表行已改 35 槽，但同文件用例清单行与 `tests/arch/power/power_vast.py` 文档字符串仍写「28 槽」（实际 35）⇒ 记 finding（文档数字、非门控读取值，不阻断）。另记：`run.sh` 头注释「注入（默认三路）」与证据 README 用法「含三路注入」未随四路更新（文档级）。

**判决：Accepted** —— F1（power 副作用）按 `§4.12` 落地并有可达 FAIL + 我的独立注入证其必要；48/48、213/45、45/45、门控与补丁全绿；N1/N2 已修、N5 残留两处文档数字已记 finding。本记录写入后已复跑 `check-knowledge-refs`（rc=0）。
