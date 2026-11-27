# m16-qemu-006: QEMU cfx_pmem 寄存器面 + cfx_power_ctrl 写侧

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-chipyard-022` 已合入（RTL 面基准）；`m16-spec-003` 的一致性裁定（若涉及 DMA 语义）
**可并行分片**：否（同改 `components/qemu`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

- `ISS-533`：QEMU 的 `cfx_pmem` 只实现 `cg15`（+`cg7`），`cg8/cg12/cg13/cg14` 走 `CFXREG`；RTL 按 `DADAO-12 §4.9` 全实现 ⇒ cfx32 寄存器面不能三方逐槽比，`DIV-06` 的 `close_when` 不足。
- `ISS-525`：`cfx_power_ctrl`（`cg8 rc1`，WO）写侧三个实现都未实现（写 0 报 `CFXREG`），与"WO、写被接受、读 ⇒ `CFXREG`"不符。

## 要做

1. **`cfx_pmem` 寄存器面**（按 `§4.9`）：`cg8 rc0 pmem_exist`（RO）；`cg12/13/14 rc0–63` start/size/attr（RW）；保留 rc ⇒ `CFXREG`；与 RTL 的取值口径一致（测试机约定 64 区域）。
2. **`cfx_power_ctrl` 写侧**：写被接受（不产生异常）、读 ⇒ `CFXREG`；若 spec 定义了副作用，按 spec 落。
3. **`cfx_hart cg9 rc6` 写忽略（ISS-m16-003 / DIV-18 的 QEMU 部分）**：`async_switch_run_mode` 写被接受但**不生效**（读回恒 2，投递时固定 supv），与 RTL「写接受、忽略」一致；spec 的「写忽略」明文由 M18 的 spec 任务补，本任务只改实现。

3. **探针/三方**：`tests/arch/pmem/` 与 `tests/arch/power/` 的 QEMU 侧期望同步；核 `DIV-06`/`DIV-13` 的 `close_when` 是否可收窄（不擅自删除）。
4. **不回归**：`check-patch-tree` qemu 段 0 problem、`make_patch.py qemu` 幂等、cfx5/cfx15 代表集。

## 不做

- 不改 RTL/gem5/spec（对齐任务另立）；
- 不改 `cfx_pmem` 的 DMA 语义（ISS-531 已由 spec 任务定义，若要求 fence/invalidate，只在探针里按新口径）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `cg8/12/13/14` 读写、保留 rc ⇒ `CFXREG`；`pmem_exist` RO；
2. `cfx_power_ctrl` 写被接受（不报错）、读 ⇒ `CFXREG`；
3. **可达 FAIL ≥2**：注入"cg12 读回 `CFXREG`"、"power_ctrl 写仍报 CFXREG" ⇒ 红；`cp`+md5 还原并重建回绿；
4. `check-patch-tree` qemu 段 0 problem、`check-component-changelog`、`check-knowledge-refs` 记录 rc。

## 完成区

**测试结果**：通过 45/45（运行期证据目录 `run.sh`，EXIT=0）；4 个注入均可达 FAIL（3 路 Vast + 1 路 kaiwu-tiny），`cp`+md5 还原后重建回绿。
**修改文件**：`components/qemu/{changelog.md,patches/target/dadao/{cpu.c,cpu.h,helper.c}.patch}`；`tests/arch/{README.md,expected-divergences.yaml,pmem/{README.md,expected.yaml,pmem_dma.S},power/power_vast.py}`。
**验收结果**：`build-qemu` PASS；Vast 探针 23/23 槽（pmem_exist=全1、cg12/13/14 64 位往返、保留 rc⇒CFXREG、power 写 0 接受/读⇒CFXREG、rc6 写后仍读 2）；kaiwu-tiny 探针写 `cfx_power_ctrl` ⇒ `CFXREG`（guest exit 0）；`make_patch.py qemu` 两次 md5 不变；`check-patch-tree` 463 patches OK（qemu 69）；`check-component-changelog`/`check-knowledge-refs` rc=0；`run_arch --self-test` PASS；`arch-cache-001`/`arch-hart-001`/`arch-time-001`/`arch-pmem-001` 均 PASS；最终 Vast+Tiny 探针 PASS。
**新发现/坑**：分支跟踪树缺 `tests/arch/common/runlimit.py`（主检出中有未跟踪副本，arch 驱动 import 它）；`run.sh` 仅从主检出临时复制并在退出时删除，未入库。worktree 无 `.dadao`，`run.sh` 临时链接主检出的 `cross-toolchain`/`tests`（gitignored）。
**遗留问题**：gem5 侧 `cg8/12/13/14` 与 power 写侧仍未实现（`ISS-m16-*` 的 gem5 部分），`DIV-06` 的 `close_when` 已收窄为 gem5、未删除；`DIV-18` 文本已刷新但 `close_when` 的「spec 明文 + `arch-hart-001` 写 0 断言」未达成，条目保留；`rc6`「写忽略」spec 明文按任务约定留 M18。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `pmem_exist` 用 `>=64` 判分支仍含 `1<<64` 移位表达式 | ✅已修 | 改为 `==64` 常量分支 | 重新编译 `build-qemu: PASS`，探针槽 0 读全 1 |
| power 写侧 bit0/1/2 副作用：spec 只写关机/硬/软复位，QEMU 只有一种 guest reset | ✅已修（按 spec 落） | bit0 `qemu_system_shutdown_request`；bit1/2 `qemu_system_reset_request`；bit=0 无动作 | 探针写 0 被接受（哨兵槽 13 正确）；读仍 CFXREG |
| 删除 `DadaoHartAsync.switch_run_mode` 后是否残留引用 | ✅已修 | 全仓 grep 仅余 cg3/cg8 同名寄存器；cg9 读/写/入口均改固定 `DADAO_MODE_SUPV` | 重新编译通过；`arch-hart-001` PASS（异步投递仍 supv） |
| 注入前源码已含本任务改动，`git diff` 非空不能证明注入 | ✅已修 | 先本地 commit 到 base+1（源码干净），注入后再查 md5 变化 + `git diff --name-only` 非空 | run.sh 输出 `md5_diff=1 git=target/dadao/helper.c`；还原后 md5 逐字节相同 |
| `make_patch.py` 幂等是否被“时间戳刷新”假绿 | ✅已修 | 连续两次导出后对全部 patch + series 做 md5 快照比较 | `cmp rc=0` 两次（36/36 中） |
| 探针期望是否从实现反推 | ✅已修 | 期望值现场解析 `DADAO-12 §4.7/§4.9/§4.12`、`tests/arch/pmem` 的 64 区域约定、`contracts/opcodes.yaml` | run_probe 23/23；注入后对应槽 FAIL |

### 第 1 轮 reviewer 验收（2026-11-25）

**重跑记录**（仓库根执行运行期证据目录内的 `run.sh`，全部为 reviewer 本人输出）：
1. 全量首跑：`== 36/36 checks passed ==`、`EXIT=0`；`build-qemu`、`probe[baseline/final] PASS 23/23 slots`、3 路注入各 `FAIL → cp+md5 还原（4f5e44a0… 逐字节相同）→ 重建回绿`、`make_patch.py qemu` 幂等 `cmp rc=0`×2、`check-patch-tree` `rc=0`（`qemu: 69 patch(es)`、`11 patch set(s), 463 patches OK`）、`check-component-changelog`/`check-knowledge-refs`/`run_arch --self-test`/`arch-{cache,hart,time,pmem}-001` 均 `rc=0`。
2. reviewer 独立注入（改「`pmem_exist` 读回 0」，非 engineer 三路）：同一脚本 `EXIT=1`、`FAIL probe[baseline] slot 0: got 0x0000000000000000, want 0xffffffffffffffff`；注入期间 `make_patch.py qemu` 因源树脏拒绝导出（E1/E3）、`check-patch-tree` 随之 `rc=1`，补丁 md5 与注入前逐个相同 ⇒ 注入未混进补丁；`cp`+md5 还原（源树回到 base+1、`git status` 干净）后重跑 `36/36 EXIT=0`。
3. `runlimit.py`：`git ls-files | grep runlimit` 无输出；`git status --porcelain -uall` 前后均恰为 11 个改动文件、无未跟踪残留；master（`a3fc0e79`）含该文件、本分支基线（`01fc74a7`）不含 ⇒ `run.sh` 临时复制 + 退出删除只是运行期技巧，其内容未进本分支提交（`master..HEAD` 空、零提交）。
4. 补丁/源树：运行期 qemu 源码树为单个本地 commit 且 `git status` 干净，`make_patch` 连续两次全部 patch + series md5 不变 ⇒ 补丁与 base+1 一致；`make_patch` 幂等是真比对（非时间戳）。

**语义核验**（本人读 `spec/DADAO-12 §4.7/§4.9/§4.12`、`spec/Kaiwu §3`、RTL 探针 `pmem.S`/`check_pmem.py`、探针 `run_probe.py`/`probe.S`/`inject.py`）：`§4.9` `pmem_exist` RO=全 1（64 区域测试机约定与 RTL 同）、`cg12/13/14 rc0–63` 64 位 RW、其余 cg8 rc ⇒ `CFXREG`，与 RTL 逐项同口径；`§4.12` bit0 关机 / bit1 硬复位 / bit2 软复位 → QEMU shutdown / guest reset（硬软同映射）、写 0 无动作、读 ⇒ `CFXREG`；`§4.7` rc6 读恒 2、写接受不生效、`dadao_async_enter()` 固定 supv，`DadaoHartAsync.switch_run_mode` 存储已删（grep 仅余 cg0–cg3 的 rc8 与 profile 同名字段，无残留引用）；23 槽期望现场由 spec + pmem README + `opcodes.yaml` 派生，非从实现反推；`DIV-06` `close_when` 收窄为 gem5 属实（`DIV-13` 已由 `m16-chipyard-027` 删除，本任务无可收窄项）。

**阻断 finding**：`spec/Kaiwu §3` 明写 `cfx_power_ctrl`（`cg8 rc1`）**Kaiwu-Tiny 未实现 ⇒ 访问 `CFXREG`（显式失败，不设静默成功的桩）**；新增写侧分支只判 `cg==8 && POWER && rc==1`，无 profile 门控。实测（kaiwu-tiny + 固件，llvm-mc/ld.lld 链接 ELF）：写 power_ctrl 的程序 `exit=0`（写被接受），对照写 Tiny 未实现 cfx 寄存器的程序 `timeout rc=124`（`CFXREG` 路径挂起）⇒ 本任务把 Tiny 从 `CFXREG` 改成「接受且可触发关机/复位」，违反 spec（改动前走 `cfx_reg_ptr` 返回 NULL ⇒ `CFXREG`）。**改法**：加 profile 开关（vast 实现 / tiny 不实现），flag 为假时落回通用路径 ⇒ `CFXREG`，并在 `run.sh` 增 kaiwu-tiny 可达 FAIL 槽。

**非阻断 findings**：① `tests/arch/README.md` 未覆盖项 1 仍写「QEMU/gem5/RTL 都没有该寄存器、三方一致 = `CFXREG`」（`power_vast.py` 已同步、README 未同步）；② `DIV-18` 的 impact/reason 仍称「QEMU 写 0 生效、读回 0」已过时——`close_when` 的「spec 明文 + `arch-hart-001` 写 0 断言」两项未达成 ⇒ 条目应保留、文本需刷新；③ `ISS-525`/`ISS-533` 标题仍称 QEMU 未实现（issues 归主会话收尾）；④ 电源 `bit0/1/2` 副作用本身无「执行后可观测」判据（`README` 未覆盖项 2 已登记，非本任务缺口）。

**约束核验**：独立 worktree、DADAO 仓零提交 ✅；补丁按 `docs/Process-01` 导出且 `check-patch-tree` 0 problem ✅；任务书与本记录无运行期路径、无「银行」用词 ✅；改动范围仅 `components/qemu` + `tests/arch` + 本任务书，未动 RTL/gem5/spec ✅；探针/证据脚本各断言均有可达 FAIL（三路注入 + reviewer 独立注入均实测红）✅。

**判决**：**Needs Revision** —— 阻断项为上「阻断 finding」（Kaiwu-Tiny `power_ctrl` 写侧须 `CFXREG`，需 profile 门控 + 可达 FAIL 槽）；其余验收命令在我本人重跑下全绿，注入→FAIL→还原→回绿链路真实。

### 第 2 轮 reviewer 验收（2026-11-25）

**重跑**（仓库根执行运行期证据目录内的 `run.sh`，均本人执行）：全量 `== 45/45 checks passed ==`、`EXIT=0`；`probe[baseline/final] PASS 23/23`、`tiny[baseline/final] PASS cfx_power_ctrl => CFXREG`、4 路注入（`pmem-cg12-read`/`power-write-cfxreg`/`rc6-write-effective`/`tiny-power-write-accepted`）各 `FAIL → cp+md5 还原（d0545ebe… 逐字节相同）→ 重建回绿`、`make_patch.py qemu` 幂等 `cmp rc=0`×2、`check-patch-tree` `rc=0`（qemu 69 patches、11 set/463 OK）、`check-component-changelog`/`check-knowledge-refs`/`run_arch --self-test`/`arch-{cache,hart,time,pmem}-001` 全 `rc=0`；三项门控另在脚本外本人直跑：`check-component-changelog` rc=0、`check-knowledge-refs` rc=0（写入本记录后复跑）。
**基线 KNOWN-RED（非本任务）**：脚本外直跑 `run_arch --self-test` ⇒ `FAIL（8 项）`，根因为分支基线（`01fc74a7`，早于 master hotfix `a3fc0e79`）无 `tests/arch/common/runlimit.py`，8 个驱动 `--selfcheck` 报 `ImportError`（`git cat-file -e HEAD:…` 证实 HEAD 即无、工作树未删除任何文件）；`run.sh` 的运行期临时副本使其在脚本内 `rc=0`（完成区已披露该 shim），合并 master 后自愈——请 architect 合并后直跑复核。
**profile 门控**：`DadaoProfile.power_ctrl`（vast=true / tiny=false）仅在 `cfx2rc` 的 power 写分支被判（grep 单点），flag 为假 ⇒ 落回 `cfx_reg_ptr` ⇒ `CFXREG`（无静默桩）。独立复测：第 1 轮的 Tiny repro（写后 exit 0）现 `rc=124`（CFXREG 挂起；修复前 `rc=0`），对照 Tiny 未实现 cfx 写同为 `rc=124`。
**Vast 副作用实测**：写 bit0 后自旋 ⇒ QEMU `rc=0`（关机生效）；写 bit1/bit2 加 `-no-reboot` ⇒ `rc=0`（复位请求生效）；写 0 对照加 `-no-reboot` ⇒ `rc=124`（无动作）；Vast 探针槽 13 写 0 被接受、槽 14 读 ⇒ `CFXREG` 不变。
**reviewer 独立注入**（改运行期 qemu 源码树 `cpu.c` 的 tiny `power_ctrl=false→true`，非 engineer 的 helper.c 四路）：同一脚本 `EXIT=1`、`FAIL tiny[baseline] … qemu rc=1`，`make_patch`/`check-patch-tree` 因源树脏 `rc=1` 且**补丁 md5 逐个未变**（未污染）；`cp`+md5 还原（`8b9bf863…` 相同、源树干净）⇒ 重跑 `45/45 EXIT=0`。
**补丁/源树**：qemu 源码树单个本地 commit、`git status` 干净（base+1）；幂等导出后 11 个目标文件 md5 与审前快照逐一相同。
**文档**：`tests/arch/README.md` 未覆盖项 1 已改为「QEMU Vast 接受写 / Tiny 仍 `CFXREG`、gem5/RTL 未实现」，与实测一致；`DIV-18` impact/reason 已刷新为 QEMU 现状（写接受忽略、读恒 2、投递固定 supv），`close_when` 保留合理——`cfx15.S` 仍只读 rc6（写 0 断言未补）、spec `§4.7` 无「写忽略」明文（留 M18），两条件均未达成；其引用的 `ISS-m16-003` 在 master 的 `issues-m16.yaml` 中存在（本分支基线仍是旧 `issues.yaml`，合并后即对齐，非死引用）。
**遗留/其他 finding**（不阻断）：`ISS-525`/`ISS-533`（master 侧 `ISS-m16-*`）标题仍写「三个实现都未实现 / QEMU 只实现 cg15」，请 architect 收尾刷新；gem5 面、`DIV-06` 收窄为 gem5、rc6 spec 明文留 M18 三项遗留判定维持。
**快照对账**：审前/审后 `git status --porcelain -uall` 均恰为 11 个改动文件、零未跟踪（`runlimit.py` 无残留）；目标文件 md5 除本记录所在任务书外全部相同；`master..HEAD` 空、未提交 git。
**判决**：**Accepted** —— 第 1 轮阻断项（Kaiwu-Tiny `power_ctrl` 须 `CFXREG`）已按 profile 门控修复并带可达 FAIL 槽，其余验收命令在我本人重跑下全绿；本结论为「工程师达标」证据，仍待 architect 终审。

### 第 2 轮 engineer 自审（返工）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 阻断：Tiny 写 `cfx_power_ctrl` 被接受（应 `CFXREG`） | ✅已修 | `DadaoProfile` 增 `power_ctrl`（Vast true / Tiny false）；`cfx2rc` 写分支加 `DADAO_PROFILE(env)->power_ctrl` 门控，假值落回通用路径 | kaiwu-tiny 探针 `PASS cfx_power_ctrl => CFXREG`；注入去门控后 `qemu rc=1`（写被接受）可达 FAIL |
| 缺 kaiwu-tiny 可达 FAIL 槽 | ✅已修 | 新增 `tiny_probe.{S,lds}` + `run_tiny_probe.py`；`run.sh` 增 baseline/final 与独立 `inject_tiny_case` | `tiny[baseline/final] PASS`；`tiny[...-fail] FAIL`→还原 md5 相同→`tiny[...-green] PASS` |
| `tests/arch/README.md` 未覆盖项 1 口径过时 | ✅已修 | 改为 QEMU Vast 已实现、Tiny 按 `spec/Kaiwu §3` 仍 `CFXREG`；gem5/RTL 未实现 | 文本与 `power_vast.py` 一致；`check-knowledge-refs` rc=0 |
| `DIV-18` 文本仍称 QEMU 写 0 生效 | ✅已修（条目保留） | 刷新 impact/reason/user_ruling：QEMU 已固定 rc6；缺口转为 `arch-hart-001` 未覆盖写 0 断言；`close_when` 未删 | YAML 解析通过；`run_arch --self-test` PASS |
| 电源副作用无「执行后可观测」判据 | ✅不修 | 属测试面缺口，已在 README 未覆盖项 2 登记；本任务只落实现 | `README` 未覆盖项 2 保留 |
| 源码改动后补丁是否同步 | ✅已修 | 源码收敛为 base+1 单提交后重导出；连续两次 `make_patch` 全量 patch+series md5 不变 | run.sh `make_patch qemu idempotent` `cmp rc=0`×2；`check-patch-tree` rc=0 |
