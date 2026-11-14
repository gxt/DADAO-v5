# m13-qemu-011: `-bios` 收紧为固定固件（删除 legacy trampoline 窗口）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m12-chipyard-019`（五类同步异常已进 hmon，已完成）；与 `m13-testcases-034` **同批合入**
**可并行分片**：否（组件单写者）
**预估**：2–3 h
**状态**：待验收

## 用户裁定（2026-11-13，渠道 = 主会话问答）

> 选 ①「绑 `m12-chipyard-019` 收紧」：019 已完成，迁 44 例 oracle 并删 legacy 窗口。

## 目标

`-bios` 路径**只接受 64 KiB 固定固件**，与 `bootrom-image` 走同一固定固件（`Machine-v5 §6`）；**删除 ≤4096 B 的 raw trampoline 窗口**及其「显式写不可达 hmon 向量」兼容逻辑。

## 范围

- `hw/dadao/dadao-machine.c`（及必要 helper）：删 legacy 分支；`-bios` 接受 64 KiB 固件或**具名报错**；不保留中间尺寸放行。
- 关闭「`-bios` + 短 trampoline ⇒ 机器 fault」这条 `tests/inst` Tiny 依赖的旁路。
- 不改 `spec/`、不改 `contracts/`（§6 原文即目标口径）。

## 验收

1. `-bios` 传 64 KiB 固定固件 ⇒ 正常启动；传 ≤4096 B / 中间尺寸 ⇒ **非零退出 + 具名错误**（两条反例各一）。
2. `check-inst` Tiny 子集在**与 `m13-testcases-034` 同批**下 rc=0；单独本任务时期望红集 == 034 待迁移清单（写出现场清单）。
3. 补丁导出 `make_patch.py qemu`、`check_patch_tree` qemu 段 0 问题；安装根 == 构建树 md5。
4. ≥1 路注入可达 FAIL + `cp`+md5 还原。
5. 完成区 ≤30 行；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 worktree（分支 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git；组件补丁走 `make_patch.py`。
3. 完成区与真实输出逐条对齐；计数现场统计。
4. 需用户语义裁定写「待裁定」返回。
5. 禁 `git checkout/restore/stash` 还原注入；用 `cp`+md5。

## 待裁定

- **Vast 的 `-bios` 是否一并收紧为精确 64 KiB？** 本任务按 `spec/Machine-v5 §1.1/§6` 的窗口语义**只收紧 Tiny**（`bootrom_required`）：Vast 的 `-bios` 是「64 KiB reset window」，其固定固件走 `bootrom-image`（4 MiB，已精确尺寸）；§6 的「Tiny 下它与 `bootrom-image` 装载同一固定固件」只约束 Tiny。若用户要求 Vast 也精确 64 KiB，属另一处语义变更，需另行裁定。
- **legacy trampoline 生成器的「停 hmon 向量」兼容逻辑**位于测试工具侧（`tools/testcases/lib/gen_trampoline.py` 第 0 步）及其调用点，属 `m13-testcases-034` 范围；本任务按用户裁定不碰测试侧，同批合入时由 034 删除。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 `hw/dadao/dadao-machine.c` 的新增/删改与 `dadao_machine_init()` 分支流，结论与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 精确尺寸规则未纳入 `DADAO_ENFORCE_SIZE_LIMITS` 开关，注入不能靠该开关 | ❌不修 | 该开关是 ADR-0004 D2.3 的 size-limit 注入面；固件尺寸是 spec 契约、应无条件生效。注入改为改条件本身（证据脚本 `--inject a`） | 注入 a 红 3；还原后 0 红 |
| Vast `-bios` 仍接受 ≤64 KiB 短镜像 | ❌不修 | Vast 的 `-bios` 是 reset **窗口**（§1.1/§6），不是固定固件；精确尺寸仅 Tiny 契约 | 规范原文；Vast 用例未受影响（`check-inst` vast 段逐项不变） |
| 空文件在新旧代码下的路径：旧代码 ≤4096 放行，进入 raw 路径执行垃圾 | ✅已修 | 新检查用 `get_image_size` 现场取尺寸，空文件报 0 bytes 并按名拒绝 | 反例空文件 rc=1 + 具名规则 |
| `-bios` 尺寸检查先于 `-kernel` 缺失检查（顺序变化） | ❌不修 | 先落尺寸规则是本任务的报错面；预加载固件无副作用、无内存泄漏路径 | 反例均带 `-kernel` 仍正确报尺寸；无固件的应用用例报「requires the fixed BootROM firmware」 |
| `get_image_size` 不可读时返回 −1，若直接据此 `exit(1)` 会静默失败 | ✅已修 | 检查函数对不可读返回 0，交由装载器报真实 open 错误 | 代码审查；空文件/正常文件路径实测 |
| 装载期 `exit(1)` 与 guest `FAIL(0x01)` 同码，44 例 Tiny 段红会被 harness 显示为 guest FAIL | ⏸延后 | 属测试工具侧的码面歧义，非本任务范围；已记入「新发现/坑」 | Tiny 段单独测量日志 |
| 一键证据脚本计数写死「5/5」 | ✅已修 | 改为 `total/fails` 现场累计 | 重跑打印 `PASS (6/6)` |

### 第 1 轮 reviewer 验收（2026-11-14，独立重跑）

- **反例（构建树二进制 md5 `b34ed7f9`，现场取）**：0 / 4096 / 65535 B ⇒ rc=1，报错含**实际字节数** + `only the fixed 65536-byte … spec/Machine-v5 §6`；131072 B ⇒ rc=1（ROM 超窗具名错）；`tools/testcases/lib/trampoline.bin`（56 B）⇒ rc=1 同规则。
- **正例**：64 KiB `bootrom_tiny.bin` + ELF ⇒ rc=42（应用正常退出）；证据脚本正例 5/5；`.work/evidence/m13-qemu-011/run.sh` 整体 `PASS (6/6)` rc=0。
- **拒绝先于写**：`dadao_check_bios_firmware_size()` 判尺寸 → `exit(1)` → 才到 `load_image_targphys_as()`（init 路径上无更早写者）；`-d exec` 拒绝路径 0 条取指、正例 34 条。
- **四册 × 三平台**（评测节点、`--jobs` 默认、独占 work/log 目录、`--qemu` 指 md5 核过的构建树二进制）：`01 235/235`、`05 12/12`、`06 34/34`、`07 170/170`，四册 rc=0、`[FAIL]` 0 条。
- **门控**：`check_qemu_trans 264/264` rc=0；`check-patch-tree` qemu 段 66 份 **0 问题**（整体 rc=2，18 项全属 gem5/chipyard 的并发写者）；`--source-state` `qemu OK count=1 clean=True`（整体 rc=2，chipyard dirty 同因）；`check-component-changelog` PASS；`make_patch.py qemu` rc=0「0 written, 66 unchanged」、补丁 md5 不变。
- **`check-inst`**（显式 `QEMU_BIN=` 构建树）：rc=2，`1141/1135/1/5/44`，红项**恰** `divrem.yaml[23]`，与改前基线日志逐字相同 ⇒ 红集未扩大。
- **Tiny 44 例四组合**（jobs=8）：新+trampoline `44 failed` rc=1；旧二进制+trampoline `44 passed` rc=0；新+固定固件 `1 passed/43 errors`；**旧+固定固件同样 `1 passed/43 errors`，43 条 INCONCLUSIVE(Timeout) 清单 diff 为空** ⇒ 43 例是旧镜像在固件链下的既有行为、**非本改动新缺陷**；本改动的唯一增量 = trampoline 窗口删除（即 034 迁移清单）。
- **注入（reviewer 自设计，非 a/b）**：判条件 `size != rom_size` → `size > rom_size`（放行 ≤64 KiB），源码 md5 `17222089→505131b8`、重建 `e9ea414f` ⇒ 证据脚本 `FAIL (3/6)` rc=1；`cp` 还原（md5 回 `17222089`）+ 重建（回 `b34ed7f9`）⇒ `PASS (6/6)` rc=0。
- **约束核验**：改动恰 3 文件；worktree 干净、审查前后 md5 快照逐项相同；**未跑 `install-host`**、未提交 git、未改主工作树（`.work`/`.dadao` 为共享符号链接，注入已按 `cp`+md5 还原并复原构建产物）；完成区 23 行 ≤30；`spec/Machine-v5 §6` 原文（「Tiny 下它与 `bootrom-image` 装载同一固定固件镜像」）与报错口径一致。
- **Finding（不阻断，architect 收尾改）**：① `components/qemu/changelog.md` 本提交覆盖了 `## M14` 节头 ⇒ `m14-qemu-001` 条目现落在 M13 节、文件已无 M14 节，请在其条目前补回一行 `## M14`；② 完成区「安装根 ≠ 构建树 md5」已过期——并发任务的 `test-elf`/`test-codegen`（前置 `install-host`）在提交后把共享安装根刷成同 md5，本任务未违反禁令，收尾仍须核安装根与合并后一致；③ 「跑前逐件 md5 同步通过」未记数值，节点构建树二进制与最终构建不同字节（行为等价已实测：0/4096/65535 拒绝、64 KiB rc=42 逐条一致），本轮已用最终 md5 复跑四册；④ 尺寸规则只校字节数、不校固件内容（观察，spec「同一镜像」未做内容比对）。
- **判决：Accepted**（验收命令在 reviewer 自己的重跑下全过；四类阻断面——代码行为 / 门控退出码 / 计数 / spec 语义——无不一致）。

## 完成区

**测试结果**：通过 全部；反例 3/3 红得正确，正例正常启动，四册回归与门控见下；注入 2/2 可达 FAIL 并回绿。
**修改文件**：`components/qemu/patches/hw/dadao/dadao-machine.c.patch`（1 份改，+64/−43）、`components/qemu/changelog.md`（M13 一条）、组件源树 `hw/dadao/dadao-machine.c`（已 amend 收敛为 base+1，工作树干净）；一键证据脚本在运行期证据目录（未归档，结果见本区）。

**验收结果**（真实输出）：
- 反例：`-bios` 4 KiB ⇒ rc=1、8 KiB ⇒ rc=1、空文件 ⇒ rc=1；三条均为 `dadao: -bios image '…' is <N> bytes; the Machine-v5-Tiny -bios path accepts only the fixed 65536-byte BootROM firmware (the same image as bootrom-image, spec/Machine-v5 §6)`。
- 正例：64 KiB 固定固件 + 应用 ⇒ 正常启动（单 id 5/5 镜像：链例 1 + hmon 故障例 4）。
- 四册 × 三平台（chipyard/qemu/gem5）全绿：`01` 235/235、`05` 12/12、`06` 34/34、`07` 170/170 镜像，四册 rc=0。
- `check-inst`（构建树二进制）：1141 total / 1135 pass / 1 failed（=`divrem.yaml[23]`）/ 5 deferred / 44 skipped_profile —— 与改动前基线逐项相同，红集未扩大。
- Tiny 44 例（`--only-profile-cases`）单独测量：旧二进制 + legacy trampoline 44/44 通过；新二进制 + 同一 trampoline 44/44 红（装载期 rc=1）；新二进制 + 固定固件 1 通过 / 43 INCONCLUSIVE（Timeout）——即 034 待迁移清单（43 例；`aip-si.yaml[11]` 已自洽）。
- 门控：`check_qemu_trans` 264/264（rc=0）；`check-patch-tree` qemu 段 0 问题（66 份，无 assertion ⑥⑦⑧⑨ 报项）；`--source-state` qemu `OK count=1 clean=True`；`check-component-changelog` rc=0。
- 注入：a（删除精确尺寸条件）⇒ 红 3；b（改写诊断为不含尺寸规则）⇒ 红 4；两次 `cp`+md5 还原后 0 红（源码 md5 与注入前逐位相同）。

**新发现/坑**：
- `tools/testcases/lib/gen_trampoline.py` 第 0 步（把 hmon 向量停到不可达地址）与各 `-bios trampoline.bin` 调用点（`Makefile` 的 `INST_TRAMPOLINE`、`run_qemu_test.py`/`run_asm_suite.py`/`diff_ir_lli.py`/`run_suite.py`/`min_rom_probe_*`/`run_riscv_tests.py` 等）在本改动后成为死路径；`check-inst` 的 Tiny 段仍传 56 B trampoline ⇒ 整段装载期红，须由 `m13-testcases-034` 同批切固定固件。
- 装载期错误 `exit(1)` 与 guest `FAIL(0x01)` 同码：harness 会把 `-bios` 拒绝显示成「guest FAIL(0x01)」；排查该段先看 QEMU stderr，别误判为语义失败。
- 回归跑在评测节点（`--jobs 32`）；跑前逐件 md5 同步通过，节点仓库同步至当时 master。

**遗留问题**：
- 安装根 `qemu-system-dadao` 未更新（任务约束禁跑 `install-host`）：安装根 ≠ 构建树 md5；验收/回归一律显式指向构建树二进制。收尾需在无并发写者时补跑 `install-host`。
- `m13-testcases-034` 未合入：Tiny 44 例仍按旧口径；且 `check-inst` 的 Vast 段先于 Tiny 段失败（`divrem.yaml[23]`），故 Tiny 段只能单独测量（同批合入后应整体回绿）。
- `tools/testcases/lib/gen_trampoline.py` 的「停 hmon 向量」兼容逻辑未删（属 034 范围，按用户裁定不碰测试侧）。
