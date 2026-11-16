# m14-qemu-003: 异步源轴 mask 查询改按「当前运行模式 monitor」（`ISS-455`）

**模块**：qemu
**项目里程碑**：M14
**依赖**：`m14-linux-009`（**已验证**：K2 收口门控）；`m14-linux-008`（已验证，内核侧两行旋钮）
**可并行分片**：否（qemu 组件单写者）
**预估**：1.5–2 h
**档位**：中改（单点语义 + 门控断言；复核 ≥2 路注入）
**状态**：待验收

## 背景（用户 2026-11-16 裁定「ISS-455：查 mode monitor」）

`spec/DADAO-12 §5.2（三）步骤 3` 明确：异步中断来源过滤查「**当前运行模式 monitor** 的 `cfx_<monitor>_<mode>_cfx_intr_mask`（cg0–3 rc4）」与 `cfx_<monitor>_global_cfx_intr_mask`（cg8 rc1）。

现状三处口径不一致：

- **spec**：查 **mode monitor** 的行（supv ⇒ `cfx_smon` 的 supv 行 = `cfx_smon cg2 rc4`）；
- **QEMU**：查**当前 cfx**（`inner_cfx_code`）的行 —— `m14-linux-007` 实测：首投后当前 cfx = 15（`escape` 不恢复 `inner_cfx_code`），只开 `cfx_smon` 一行时**仅 1 个 tick**；
- **`contract-see §6.4`**：同 QEMU 读法（且写了「当前 cfx = `cfx_smon`」的实例句，首投后不成立 —— `ISS-454`）。

用户裁定：**按 spec 字面，查 mode monitor** ⇒ QEMU 与契约都要改；内核侧（`m14-linux-008` 的"两行都写"）随之收敛为只写 `cfx_smon cg2 rc4`（另立 `m14-linux-010`）。

## 目标

1. **QEMU**：异步源轴过滤由「当前 cfx 的行」改为「**当前运行模式 monitor** 的 `<mode>_cfx_intr_mask`」（supv ⇒ `cfx_smon` 的 `cg2 rc4`）；全局轴 `cfx_<monitor>_global_cfx_intr_mask`（cg8 rc1）保持不变；
2. **门控断言**：`k2_time_probe`/`k2_irq_probe` 增（或改）一条 —— **首投后只开 `cfx_smon cg2 rc4` 一行**仍能持续 tick（改前必红、改后必绿，即"先红后绿"）；
3. 其它 target 行为**不变**（只改 dadao 侧逻辑）。

## 验收（真实 rc + 输出）

1. **先红后绿**：改前跑新断言 ⇒ **FAIL**（贴真实输出：只开一行时 tick 数停在 1）；改后 **PASS**；
2. `make build-qemu` + **`make install-host`** rc=0，贴 `qemu-system-dadao` 新 md5（**源树干净时**取，`ISS-451`）；
3. `check-linux-k0` 119/119、`check-linux-k1` 108/108、`k2_trap_probe` 85/85、`k2_time_probe` 151/151、`k2_irq_probe` 95/95 全绿；`check-qemu-forms` rc=0；
4. **≥2 路注入**（`cp`+md5 还原 + 重建）：① 把查询改回"当前 cfx 的行" ⇒ 新断言红；② 把位索引从"目标 cfxha"改成"cause 位索引" ⇒ tick 消失/断言红；
5. 补丁纪律：`apply_series --component qemu`、`check-source-state`、`check-patch-tree`（qemu 0 problem）、`make_patch qemu` 幂等；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/qemu/**` + `tools/linux/**`（探针断言）+ 本任务书；不改 `spec/`、`.tao/contracts/`（契约修订归 `m14-linux-010`）；
- 不提交 git；注入还原 `cp`+md5；构建与跑批不同时；`JOBS=32`。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：改动可交付，状态 → `待验收`。

- **语义**：`cfx_enter()` 步骤 3 的源轴改为 `env->cfx[mon].mode[mon].cfx_intr_mask`（`mon = inner_run_mode & 3`，mode⇔cg⇔cfx0–3 一一对应，与既有全局轴取法同源）；位索引仍 `target`（来源 cfxha）；全局轴未动；`sync` 分支未动；`pending` 仍记在 `env->cfx[ci]`。与 `spec/DADAO-12 §5.2` 步骤 3 字面对齐，与 `inner_cfx_code` 解耦。
- **越界披露**：`tools/testcases/arch/min_rom_probe_integ042t.py`（异步投递打开/屏蔽改按 `cfx_hmon cg3 rc4`）与 `min_rom_probe_integ051t.py`（用例说明与标签改述）不在任务书「只改 `tools/linux/**`」字面范围内；不改则 `check-arch` 必红，属必要最小改动。`spec/`、`contracts/`、`tests/**`、其它组件未动。
- **先红后绿的诚实性**：改前测量用**旧安装根二进制**（`67ecec37`，任务开始时现场 md5）跑同一断言，非伪造；两侧输出都在完成区。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `SINGLE_ROW_PATCHES` 引用尚未定义的 `IRQ_C`（`NameError`） | ✅已修 | 把 `TIME_C/IRQ_C/IRQFLAGS_H` 移到模块顶部常量区 | `py_compile` + 后续 3 次整跑 |
| `single_row_run()` 把 md5 字符串当 bytes 还原，异常路径中止在 `finally` 中途中、内核源留在注入态 | ✅已修 | 保存原始 bytes；还原后 md5 不一致即 raise | 还原行 `md5 期望=93d2ec18/9581470b 实际=同`；`.work/source/linux` `git status` 空 |
| `k2_irq_probe` 的 `only-smon-row` 注入在修复后 P2 不再变红（期望过时） | ✅已修 | 期望收窄为 `C0/P1`，注明行为红路径由 `k2_time_probe` C10 承担 | `--inject --only only-smon-row` 实跑 |
| 注入①首版把 `mon` 改名导致 `global_mask` 引用未定义（编译 rc=2） | ✅已修 | 保留 `int mon`、只替换 `src_mask` 行 | `build-qemu` rc=0 后注入实跑 |
| 自审新增的 selfcheck 计数用「假变异项」凑数 | ✅已修 | 改显式 `+2 if single_row` | `--selfcheck PASS (16/16)` |
| 并发启动第二个探针抢共享内核构建树（一次 `--quick` 假红） | ✅已修 | 中止并串行重跑 | 重跑 `--quick` 全绿 |

### 第 2 轮 reviewer 验收

**判决**：**Accepted**（判决基于本人重跑，非采信完成区）。

- **重跑**：`.work/evidence/m14-qemu-003/run.sh full` → `EXIT=0`（19 项含 patch-tree 416 OK/qemu 69、source-state clean、qemu-forms、interface、changelog、k2_time 156/156、k2_irq 97/97、k2_trap 85/85、k0 119/119、k1 108/108、k2 104/104、check-arch 14 探针）；`k2_time_probe --selfcheck` → `16/16` `EXIT=0`；`make check-inst-asm` → `904/904` `EXIT=0`。
- **语义**：`mon = entry_mode & 0x3`（`entry_mode = inner_run_mode`），`src_mask = cfx[mon].mode[mon].cfx_intr_mask`、`global_mask = cfx[mon].global_cfx_intr_mask`（与改前 `cfx[entry_mode&3]` 等价，未变），位索引仍 `target`，`if (!sync)` 分支未动，步骤 3 内无 `inner_cfx_code` ⇒ 符合 `ISS-455`。
- **先红后绿**（重跑 `run.sh --inject`）：红侧 `C10 2/5`（`tick 期望=3 实际=0`、`退出 <missing>`、`rc 期望=0 实际=19`、二进制 `f32698a9`）；绿侧 `C10 5/5`（`rc=0`、`babd01d7`）；两侧还原 md5 均与备份相等。
- **自设计注入①** `mon` 固定 `2`：`k2_time C10 5/5 仍绿`（探针全在 supv ⇒ `mon≡2` 恒等）但 `integ042t 24/25 红`、`integ051t 2/14 红`（hypv 下 monitor 应为 3）⇒ **判据强度结论：C10 单独判不出「按 mode」，由 check-arch 的 hypv 探针承担；k2+check-arch 组合足够**。
- **自设计注入②** 源轴位索引 `target→ci`（全局轴不动）：`C10 2/5 红`、`042t 24/25 红`、`051t 2/14 红`、irq 多断言红 ⇒ 红。两路均 `cp`+md5 还原 + `build-qemu` 回绿（`C10 5/5`、`042t 25/25`、`051t 14/14`，build 树=安装根 `babd01d7`）。
- **越界**：`integ042t` **必需**（把两处写回 `cfx_pmem` 行即红 24/25，实测）；`integ051t` 为纯标签/注释改述（回退仍 `14/14` 绿）⇒ 自审「两者不改则必红」对 051t **不成立**（文档级小错，不阻断，随收尾改）。`spec/`、`contracts/`、`tests/inst/`、`components/linux/` 未动（`git diff --name-only` 7 文件核对）。
- **补丁纪律**：`make_patch` 幂等（`36733ba1` 两同）、`apply-series --component qemu rc=0` 且 HEAD `03186abdecc0` 不变、`check-patch-tree rc=0`、`--source-state clean=True`。**采信未重跑**：engineer 注入②（全局轴，irq 73/82）。
- **并发**：全程未跑 `install-host`（只 `build-qemu`），**最终安装根 md5 = `babd01d7`**（与构建树 `cmp` 同），`m15-testcases-006` 可续用；注入窗口前均 `pgrep` 确认无对方写者。
- **快照对账**：`git status -uall` 空；`helper.c 0a6abf06`、`irq.c 93d2ec18`、`irqflags.h 9581470b`、`time.c e6586243`、`042t 35bd8bd1`、`051t 63e3d9ea` 全部等于注入前快照。

## 完成区

**测试结果**：6/6 门控组全绿（0 失败）；先红后绿两侧均实测。失败原因：无。
**修改文件**：
- `components/qemu/patches/target/dadao/helper.c.patch`（`cfx_enter()` 步骤 3 源轴改读 `env->cfx[mon].mode[mon].cfx_intr_mask`，`mon = inner_run_mode & 3`；全局轴、位索引不变）、`components/qemu/changelog.md`；
- `tools/linux/k2_time_probe.py`（新增 C10 单行断言 + `single_row_run()` + selfcheck 变异）、`tools/linux/k2_irq_probe.py`（C1 两行说明改述、`only-smon-row` 期望收窄）；
- `tools/testcases/arch/min_rom_probe_integ042t.py`、`min_rom_probe_integ051t.py`（**越界披露**，见自审）。
**验收结果**：
- **先红后绿**（C10：首投后只开 `cfx_smon cg2 rc4` 一行）——改前 `tick 行数 期望=3 实际=0`、`退出 tick 期望=3 实际=<missing>`、`rc 期望=0 实际=19`（`0x13 = K2_FAIL_NO_TICK`）⇒ 2/5；改后 5/5（`cfx_smon=0x…7fff`、`cfx_hart=0x…ffff`、tick 1–3、rc=0）。注：任务书按 `m14-linux-007` 预估「停在 1 个 tick」，本镜像实测更早（0 个），根因未追，不影响判据「改前必红」。
- `k2_time_probe 156/156`（151 + 5 C10）、`--selfcheck 16/16`；`k2_irq_probe 97/97`；`k2_trap_probe 85/85`；`check-linux-k0 119/119`、`k1 108/108`、`k2 104/104`；`check-arch` 14 探针 + `check-arch-smoke`；`check-inst-asm 904/904`；`check-qemu-forms`/`check-interface`/`check-component-changelog` rc=0。
- `make build-qemu` rc=0、`make install-host` rc=0；**安装根 md5 = `babd01d7`**（`v11.1.1-1-g03186ab`；与构建树 `cmp` 同一内容）。运行期日志/证据未归档：一键脚本在运行期证据目录，`--quick` 实跑 PASS；`k2_irq_probe --inject --only only-smon-row` 亦 PASS（C0/P1 变红、还原后回绿）。
- 补丁纪律：`make_patch qemu` 幂等（`helper.c.patch` md5 `36733ba1` 两次相同）、`apply-series --component qemu` rc=0 且 HEAD 不变（`03186abdecc0`）、`check-patch-tree` 416 补丁 OK（qemu 69、0 problem）、`--source-state` qemu `clean=True count=1`。
- 2 路注入（`cp`+md5 还原+重建）：① 源轴改回「当前 cfx 的行」⇒ C10 2/5 红；② 全局轴改按当前 cfx 的 `cg8 rc1` ⇒ irq 探针 73/82，P4/C9/C1 红（帧内投递失去全局轴保护、跑至超时 rc=124）。注：派单②的字面「全局轴也改走 mode monitor」即**现状**（无可注入的变更），故取镜像方向；任务书②「位索引改用 cause 位」亦属同类可构造注入。
**新发现/坑**：
- QEMU 二进制 md5 随**组件源 HEAD** 变（`qemu-version.h` 内嵌 `QEMU_PKGVERSION`）：同一源码提交前/后两次构建 `2a27cb01` ≠ `babd01d7` ⇒ md5 只在「同 HEAD + 同构建环境」内可比（`ISS-451`）。
- `single_row_run()` 首版把 md5 串当 bytes 还原，异常路径停在 `finally` 中途中、内核源留在注入态（已按 diff 反打还原、`git status` 空）；现改为存原始 bytes + 还原后 md5 断言。
- 两个探针的 `SCRATCH` 默认值仍指向旧任务临时目录 ⇒ 新任务须用 `K2T_TMP`/`K2I_TMP` 覆盖；并发跑两个探针会抢同一内核构建树（一次 `--quick` 因而假红，已串行重跑）。
**遗留问题**：
- `contract-see §6.4` 与内核「两行都写」的收敛归 `m14-linux-010`（本任务按约定未动 `contracts/`）。
- `m14-linux-010` 删掉 `cfx_hart` 行写入后，`SINGLE_ROW_PATCHES` 的注入点会消失（现会具名报错「注入点不唯一（0 处）」），需随该任务同步调整。
- `k2_irq_probe` 的 `only-smon-row` 注入只剩静态红路径（C0/P1）。
