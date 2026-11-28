# m18-qemu-007: QEMU system 移除 `cfx_jmon`（cfx1）实现

**模块**：qemu
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入）+ `m18-linux-026`（内核迁移异步 escape，去 jmon）；本任务**不得**在其之前合入，否则 K2/K6 立刻红
**可并行分片**：否（同 `components/qemu` 写者）
**预估**：2–3 h（标定：同档 QEMU 单点寄存器/cfx 面任务取 2–3 h；含探针与 profile 断言调整）
**档位**：中改（QEMU cfx 集合）
**状态**：已验证
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景（用户 2026-11-25 裁定）

`cfx_jmon`（cfxha 1）在 spec 里只有一句「处理 jail 模式下的同步异常」，**没有设计**（无 cg/rc 面定义、无 jailed 模式语义、无 SBI 入口实现），RTL 也未实现（`WumingParams` 的 cfx 表无 cfx1）。QEMU system 却把它放进 `DADAO_CFX_IMPL_VAST`（`1<<1`）、登记进 `dadao_cfxha_map`、并在 `helper.c` 的 cg7 空间表里给 `umon/jmon/ptw` 记 16 个空块 —— 这是**超出设计范围的实现**，会诱使软件把 jmon 当可用 monitor（`m18-linux-024` 的内核返程帧就是这么用的）。

用户裁定：**QEMU system 不应实现 cfx_jmon**；内核的返程帧另选（见另一任务）。

## 目标

1. 从 QEMU system 的已实现 cfx 集合中移除 cfx1：`DADAO_CFX_IMPL_VAST` 去掉 `1<<1`；`dadao_cfxha_map`/`DADAO_NUM_CFX` 与 `helper.c` 的 cg7 空间表同步；Tiny 本就不含 cfx1，保持。
2. 语义：移除后按 profile 既有规则处理 —— 未实现 cfx 的 `trap` ⇒ `CFXREG`（Vast）或 `ILLI`（Tiny 的 `unimpl_cfx_trap_illi`），**不得**静默零值或落到别的 monitor；寄存器访问同规则。
3. 清理引用：QEMU 源码/注释里「jmon 已实现」「umon/jmon/ptw 16 blocks」等表述；`tests/arch` 里若有依赖 jmon 存在的断言（README 已声明 cfx1 不在 arch 范围），改为「cfx1 未实现 ⇒ CFXREG」。
4. 与 RTL/gem5 口径对齐：RTL 无 cfx1；gem5 的 J 模式映射若要保留，仅作注释/未实现，不得因此认为 cfx1 可用。

## 验收（逐条贴真实 rc）

1. QEMU 补丁按 `docs/Process-01` 重导；`check-patch-tree` qemu 段 0 problem；`make build-qemu`/`install-qemu` rc=0。
2. 探针：`trap cfx1, 0` ⇒ `CFXREG`（Vast）；读/写 cfx1 的 cg/rc ⇒ `CFXREG`；`trap cfx0/2/3` 行为不变（umon/smon/hmon 仍有 cg5）。
3. **可达 FAIL ≥2 路**：① 把 `1<<1` 加回 ⇒ 上述 `CFXREG` 断言红；② 只删掩码不删 `cfxha_map` ⇒ 数组下标/CFXREG 判定红；`cp`+md5 还原并重建回绿。
4. 不回归：`check-qemu-forms`、`check-cfx-alias-install`（若涉及）、`check-qemu` 代表集、Tiny 基线；`check-component-changelog` rc=0。
5. 联动：与内核切换任务同批验收时，`check-linux-k2`/`k6` 必须绿（见依赖；若内核尚未切换，本任务只做 QEMU 侧证据并标 BLOCKED，不宣称收口）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/qemu/patches/target/dadao/**`、`components/qemu/changelog.md`、`tests/arch/**`（仅 cfx1 相关断言）、本任务书；不改 spec/契约/Makefile/内核/RTL/gem5。
3. 不改版本号；术语「bank = 寄存器组」；还原 `cp`+md5。
4. **顺序**：必须在内核不再 `trap cfx_jmon` 之后合入；违反会让 K2/K6 立刻 `CFXREG` 红。
5. 清理 QEMU 共享源树时按 `docs/Process-01` 全量重放，避免留下旧 cfx1 代码。

## 待裁定

1. 用户在 2026-11-25 裁定「定义异步 escape」，本任务等待 `m18-spec-007` 与内核换帧任务落地；不采用 hmon/hart cg5/kmon 方案。

## 完成区

**测试结果**：证据脚本 26/26 PASS（`build-qemu`、11 条静态不变量、7 例 runtime 探针、`min_rom_probe_m18qemu009` 20/20（新增 `cfx1_unimplemented` 例，`--self-test` PASS）、6 个 L1 门控、2 路注入各 4 步）。runtime 探针 7 例：`trap cfx1`/`cfx2rd cfx1 cg0,cg8`/`cfx2rc cfx1 cg5` ⇒ `CFXREG`（cause_info = 指令字、进入当前 hmon）；`trap cfx0/2/3` ⇒ `CFXTRAP` 且进入对应 monitor；dump 行集 = `{0,2,3,4,5,15,32,34,63}`。
**修改文件**：`components/qemu/patches/target/dadao/{cpu.c,cpu.h,helper.c,insn_trans/trans_ctrl.c.inc}.patch`（4 份改）、`components/qemu/changelog.md`、`tools/testcases/arch/{README.md,min_rom_probe_m18qemu009.py}`、`tests/arch/{README.md,vast-arch-inventory.md,pmem/{pmem.S,pmem_dma.S}}`、本任务书。未动 spec/契约/Makefile/其它组件。
**验收结果**：`make build-qemu JOBS=32` rc=0；`check-qemu-forms`/`check-patch-tree`（qemu 69 patches OK）/`check-component-changelog`/`check-tests-index`/`check-knowledge-refs`/`check-decodetree-repro` 全 rc=0；`make_patch.py qemu` 4 written / 65 unchanged，`check-patch-tree --source-state` qemu `HEAD=519347c count=1 clean=True`。注入①完整回退（`1<<1`+map+`NUM_CFX`）⇒ `trap cfx1` 探针 rc=1（超时：进入无向量的 jmon）；注入②仅回退 map（掩码保持清除）⇒ dump 多出 CFX01 行、探针 rc=1；两路均 `cp`+md5 对账还原（cpu.c `0e6840ec…`、cpu.h `08991e61…`、helper.c `a26c2f99…`）、重建后 7/7 回绿。证据脚本见运行期证据目录内 `run.sh`（含 `static_checks.py`/`inject.py`/`probe.py`）。
**新发现/坑**：① `cfx_idx()` 同时看 `cfx_impl_mask` 与 `dadao_cfxha_map`，只删掩码仍 `CFXREG`（map 缺行），故注入①必须完整回退三者；② `cp -p` 还原后 mtime 旧于目标文件，`make` 不重编（用无 `-p` 的 `cp`+`touch`）；③ 本机仍允许经 `switch_run_mode` 进入 jail，移除 jmon 后 jail 下的同步异常/`CFXREG` 会走 `cfx_enter` 的 `ci<0 ⇒ entered=false`（pc+4，静默）；RTL 无 jail、内核不跑 jail，属既有模型缺口，已登记遗留；④ spec 未改：`spec/Kaiwu §3` 仍写 Vast 实现 cfx1、`contracts/cfx-aliases.txt` 仍有 `cfx_jmon_*`（ISA 别名，由 spec 侧另行处置）。
**遗留问题**：① **合入时序**：本任务实现/验收已完成，但**必须等 `m18-linux-026` Accepted 后合入**——内核 026 之前仍 `trap cfx_jmon`，且 K1/K2 boot 链固件 `tests/ee-vast/hmon_k0_vast.S` 仍有 `OPEN_SUPV_REGS cfx_jmon`、`tests/unit/linux/amb_window_probe.py` 仍 `escape cfx_jmon`，提前合入会立刻 `CFXREG` 红；本任务未跑 K1/K2/K6（BLOCKED，按验收 5 只做 QEMU 侧证据、不宣称收口；该固件/探针不在本任务允许改动范围，属 `m18-linux-026` 同批迁移面）。② jail 模式无 monitor 的静默路径（见坑③）需 spec/裁定。③ `check-arch-smoke`/`check-cfx-alias-install` 需安装根与 llvm-mc，本环境缺 `llvm-mc` ⇒ `check-arch-self-test` 基线红（`check_hart`/`check_pmem_dma` 报缺工具链，与本 diff 无关）；ISA/别名未变，`check-cfx-alias-install` 不涉及。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 `cpu.c` 掩码、`cpu.h`（`DADAO_NUM_CFX`/数组注释）、`helper.c`（map/`cfx_idx`/`cfx_enter`/`cfx_raise`/cg7/escape）、`trans_ctrl.c.inc` 注释与导出补丁；核对 `env->cfx[]` 的全部使用点（`ci`/`mon`/`mci` 均经 `cfx_idx`，无「下标 == cfxha」假设）；核对 `trap`/`cfx2rd`/`cfx2rc` 的 `ci < 0 ⇒ CFXREG` 路径与 `escape` 的 `mci < 0 ⇒ CFXESC`；核对 Tiny（掩码未动、map 仍含 3/63，两 target 均编译通过）；核对 4 份补丁与源树一致、`check-patch-tree --source-state` 干净。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 只删掩码不删 map 时 `cfx_idx` 仍 -1，注入①原描述不可达 | ✅已修 | 注入①改为完整回退 mask+map+`NUM_CFX`（真实「cfx1 已实现」态）；注入②保留「仅回退 map」 | inj1 probe rc=1；inj2 dump `[0,1,2,…]` probe rc=1 |
| F2 `cp -p` 还原后 mtime 旧于对象文件，重建不生效导致假红 | ✅已修 | `restore()` 改无 `-p` 的 `cp`+`touch`；启动时 touch 四个源文件 | 还原后 probe 7/7 绿、md5 相等 |
| F3 m18qemu009 期望 `cause_info` 漏写 `rc<<6` | ✅已修 | 改为 `(CG15<<12)|(3<<6)|39` | 20/20 PASS；`--self-test` PASS |
| F4 jail 模式无 monitor：`cfx_enter` `ci<0` 走 pc+4（静默） | ⏸延后 | 不在本任务范围（RTL 无 jail、内核不跑 jail） | 完成区遗留②登记 |
| F5 `spec/Kaiwu`/别名表仍写 cfx1 实现/存在 | ⏸延后 | 本任务禁改 spec/契约 | 完成区坑④/遗留登记 |

判决：代码与测试 finding 全部闭环；F4/F5 为越界项已登记。状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（本人执行，真实 rc）**：仓库根执行运行期证据目录内 `run.sh` ⇒ `checks: PASS=26 FAIL=0`、rc=0（`build-qemu rc=0`；static 11 项 PASS；runtime probe `7 case(s), 0 failure(s)`——trap/读/写 cfx1 ⇒ CFXREG 且进当前 hmon、trap cfx0/2/3 ⇒ CFXTRAP 进对应 monitor；009 探针 `20 case(s), 0 failure(s)`；forms/patch-tree 463 OK/changelog/tests-index 503/knowledge-refs/decodetree 全 rc=0）。
**注入**：脚本内两路重跑——①完整回退 mask+map+NUM ⇒ `inj1 probe rc=1`；②仅回退 map ⇒ `cfx_rows expected [0,2,3,4,5,15,32,34,63] actual [0,1,2,…]`、rc=1；两路 `cp`+md5 还原（cpu.c `0e6840ec…`、cpu.h `08991e61…`、helper.c `a26c2f99…`）重建回绿 rc=0。**自设注入③**（trap helper `ci<0` 分支 `CFXREG→CFXTRAP`）⇒ `FAIL rd20: expected 4 actual 1`、**rc=1**；`cp`+md5 还原（`a26c2f99…`）重建 rc=0、probe `7 case(s), 0 failure(s)` rc=0。
**探针**：009 `--self-test` **rc=0**（20/20 例逐断言「reachable FAIL」）；008 `--case escape_unimpl_cfx` rc=0（escape 目标未实现 ⇒ CFXESC 分支实跑绿）；断言数现场统计 = **164**（`sum(len(checks))`，008 同口径 150，HEAD 版 157）。`cfx1_unimplemented` 覆盖 trap+读+写（rd25=3）。
**门控**：`make check` **rc=2**，唯一失败 `check-isa-coverage: 找不到 llvm-mc`（`command -v llvm-mc` rc=1、构建树 llvm-mc 不存在；`resolve_llvm_mc` 在读仓库内容前即 SystemExit ⇒ 基线同错同停点，其前 64 条 PASS/0 FAIL）；`check-arch-self-test` rc=2，`check_hart`/`check_pmem_dma` 均 `FAIL 缺 llvm-mc`（本人单跑证实，与本 diff 无关）。`check-source-state`：`qemu: OK HEAD=519347c118c3 count=1 clean=True`；注入后复跑 `check-patch-tree` rc=0。
**实现核验**（源树+补丁双侧）：VAST 掩码无 `1<<1`；`DADAO_NUM_CFX 9`；map `{0,2,3,4,5,15,32,34,63}`；cg7/escape/trans_ctrl 注释已同步（无 `umon/jmon/…` 实现表述）；trap `ci<0 ⇒ CFXREG` 目标=当前模式 monitor；寄存器访问同规则；escape `cfx_idx(target)<0 ⇒ CFXESC`（rc9=cfx1 同路径）；trap cfx0/2/3 走实现路径，3 例绿。
**范围/时序**：实盘 12 文件（qemu 补丁 4+changelog、tests/arch 4、tools/testcases/arch 2、本任务书）；无 spec/契约/Makefile/其它组件；分支无提交（**实现待审，需 architect 提交**）、远端无该分支（未 push）、状态 `待验收` ✓。任务书已写明「合入等 `m18-linux-026` Accepted」（依赖行+遗留①）；残留依赖已由 **026 分支**清理（其工作树实测：`hmon_k0_vast.S` 删 `OPEN_SUPV_REGS cfx_jmon`、`amb_window_probe.py` 与 linux 补丁无 `cfx_jmon`/`DADAO_CFX_JMON`）⇒ 属合入阻塞，非本任务缺陷。采信未重跑：`make_patch.py qemu 4/65`、K1/K2/K6（BLOCKED，本任务只做 QEMU 侧）。
**findings（文档级，不阻断）**：① 两处文档写「20 例 / **163** 断言」实为 **164**（`tools/testcases/arch/README.md`、`tests/arch/vast-arch-inventory.md`）⇒ architect 收尾改 164；② 完成区「修改文件」漏列 `tests/arch/vast-arch-inventory.md`、`tools/testcases/arch/README.md`（12 vs 10），且硬约束 2 正向清单未列 `tools/testcases/arch/**`（探针改动，验收 2/3 所需）⇒ staging 补列。
**判决：Accepted**（合入待 `m18-linux-026` Accepted；两条 findings 由 architect 收尾修正）
