# m19-qemu-001: QEMU Tiny 新几何与装载（8K ROM / 8K hmon / 256K SRAM）

**模块**：qemu
**项目里程碑**：M19
**依赖**：`m19-spec-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待验收

## 背景

QEMU 的 `kaiwu-tiny` 仍按 64 KiB BootROM / 8 MiB SRAM / 64 KiB hmon 建模。Tiny 新硬件几何（`m19-spec-002`）为：ROM 8 KiB、SRAM 256 KiB、hmon 8 KiB、entry `MAIN_SRAM_BASE+0x2000`、raw 基址 `0x2000`、DUMP 0x800（pt_regs）、SIGNATURE 0x1000、EXIT 0x30、MAILBOX 0x20、STACK 0x39000–0x3F000、MemRAS 0x3F000–0x40000。

## 目标

1. `-M kaiwu-tiny`：bootrom 8 KiB、RAM 256 KiB、hmon 8 KiB；reset PC 仍 `0xFFFF_FFFF_0000`。
2. `bootrom-image` / legacy `-bios`：镜像恰好 8 KiB；QEMU 原样装入，不按应用 `e_entry` 改写。
3. `-kernel`（raw/ELF）：只接受 `0x2000` 起的 SRAM 段；raw 基址 `0x2000`、`e_entry=0x2000`；禁止 PT_LOAD 到 header/BootROM/hmon。
4. 头区：`VERSION=0x0000`、`MAILBOX=0x0020`、`EXIT_BLOCK=0x0030`；按新地址建模。
5. DUMP：`DUMP_BASE=0x0800`、`DUMP_SIZE=0x800`，四组 `rd/rb/ra/rf` 顺序与 `pt_regs` 一致；`rd[0]=status`、`rb[0]=ip`。
6. 更新 QEMU 侧探针/驱动中的旧地址；不改 gem5/chipyard。

## 验收（逐条贴真实 rc）

1. QEMU 跑通 `power → hmon → 应用`；`tests/inst` 代表例与旧基线语义一致（地址类期望按新几何更新）。
2. 镜像/入口校验：错误 `bootrom` 大小、`e_entry≠0x2000`、PT_LOAD 越界均显式失败，不静默。
3. DUMP 0x800：按 `pt_regs` 偏移读回四组；`rd0/status`、`rb0/ip` 正确。
4. **可达 FAIL ≥2 路**：① 把 RAM 改回 8 MiB ⇒ 尺寸/边界用例红；② 把 entry 改回 0x10100 ⇒ 装载校验红。
5. `make check-qemu-semantics` / `check-interface` 真实 rc（基线红逐行对照）。

## 约束

独立 `git worktree`；**不提交 git**；只动 QEMU 组件/补丁与 QEMU 侧工具；不改 gem5/chipyard；不接板；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：证据脚本 `run.sh` **66/66 通过，rc=0**（含 2 路注入反例均转红后 cp+md5 还原回绿）。
**修改文件**：`components/qemu/patches/{hw/dadao/dadao-machine.c,target/dadao/{cpu.c,cpu.h,helper.c}}.patch`、`components/qemu/{README.md,changelog.md}`、`tools/qemu/smoke-kaiwu-tiny.sh`、本任务书。
**验收结果**（逐条真实 rc）：
1. 几何：`-M help` 含「8 KiB BootROM + 256 KiB SRAM + 8 KiB hmon SRAM」；`info mtree` rc=0，`dadao-ram=0x40000`/`dadao-rom=0x2000`/`dadao-hmon-sram=0x2000`；RAM 末字节 `OK`、末+1 `NOACCESS`。装载链 3 路（bootrom-image+ELF / bootrom-image+raw / `-bios`+ELF）`power→hmon→app` 均 rc=0。`tests/inst` 代表例**本任务未跑**（缺 8 KiB 固件与 entry 迁移），**由 `m19-testcases-002/003` 兑现**，不作为本任务已验项。
2. 镜像/入口：bootrom 8193/65536/4096 全 rc=1 且具名；`e_entry=0x10100` rc=1（报 `0xffffff002000`）；PT_LOAD 头区/BootROM/hmon/窗口外 rc=1 具名；raw 131073 B rc=1。`tools/qemu/smoke-kaiwu-tiny.sh` rc=0（7/7）。
3. DUMP 0x800：dump rc=0；rd0=0、rd8/rb8/ra8/rf16 标记逐项相等、`rb0 == nm(rb_ip)`；guard 与 1-past-RAM 的 cause_ip（= 故障指令）+ cause_info（= 故障地址）逐项相等；SIGNATURE、EXIT_BLOCK reason/code 相等。
4. 可达 FAIL：① Tiny profile 的 `ram_size` 注入 8 MiB ⇒ 0xffffff040000=`OK`、RAM 边界例 app rc≠0（红），cp+md5 还原后 `NOACCESS`、rc=0；② `DADAO_TINY_KERNEL_ENTRY` 注入 0x10100 ⇒ 合法 ELF rc=1（红），还原后 rc=0。
5. 门控：`check-patch-tree` rc=0（464 patches OK、qemu source-state clean base+1）；`check-component-changelog` rc=0；`make check-interface`/`check-qemu-forms` rc=2，错误行与基线 `m19-spec-002` **逐字相同**（实际为 `machine_profile.ProfileError: profile 'tiny': sp 0xffffff7eff00 outside RAM [0xffffff000000, 0xffffff03ffff]`，属 `tests/ee-tiny/runtime.yaml` 未迁，依赖 `m19-testcases-002`）；`check-qemu-semantics` 已退役（`TESTCASES-076t`，见 Makefile 注释）；等价门控 `check-inst-asm` 实测 rc=2（`TINY_BOOTROM … not found`，依赖 `m19-testcases-002/003` 的 entry/固件）。
**新发现/坑**：
- `ld.o`/`st.o` 立即数为 **signed 12-bit**、hmon 只有 `rd63` 一个 scratch ⇒ spec §6.2 的 hmon data 区 `0x0C00` 无法用 rb0 相对单指令访问；证据固件沿用 0xD8 槽，最终布局须由 `m19-testcases-003` 定案。
- 主仓 `.work/source/qemu` 曾被 `m18-qemu-007` 的未导出改动污染（与补丁集不一致）；本任务改为「base 重放补丁集 → 叠加本任务 delta → 导出」，避免回滚他人改动。
- worktree 的 `.dadao/cross-toolchain` 是指向共享安装根的只读软链；本任务未跑 `install-host`（会写共享根）。
**遗留问题**：`check-interface`/`check-qemu-forms` 红 = 依赖 `m19-testcases-002`（基线同红）；`check-inst-asm` 未跑 = 依赖 `m19-testcases-002/003`；hmon data 布局由 `m19-testcases-003` 定案。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| header 区判据以 `kernel_base` 为界，需确认真实拒绝而非落入泛化消息 | ✅已修 | `dadao-machine.c` 增具名 header 拒绝分支 | `neg_header.elf` rc=1 且消息含 `main-SRAM header area` |
| `DADAO_MAX_MAPPED_REGIONS=3` 与 window+rom+mon 组合是否会溢出 | ✅不修 | 两 profile 的 `rom/mon_elf_segments` 均为 false，n≤2；代码上限 3 | `check-patch-tree` + 编译通过 |
| guard_lo 只在 TLB 路径建模，monitor `xp` 仍可读 | ✅不修（记录） | — | guest 路径已验证 CFXMEM；`xp` 读的是物理内存视图，不属 guest 语义（坑已记） |
| 注入 A 直接改 `DADAO_TINY_RAM_SIZE` 触发 `_Static_assert` 编译失败，不是运行时红 | ✅已修 | 改注入 Tiny profile 的 `.ram_size` | 注入后 xp=`OK`、app rc≠0；还原后 `NOACCESS`、rc=0 |
| 证据固件 rc7 补丁硬编码文件偏移，app.S 变更后失效 | ✅已修 | 从 `llvm-objdump` 现场取 `set.zw rd8` 地址 | `guest exit 7 reaches the host` rc=7 |
| 导出补丁误带 `m18-qemu-007` 的文本回滚（trans_ctrl/cpu.h） | ✅已修 | 恢复补丁集→base 重放→叠加 delta→重导出 | `git diff m19-spec-002 -- components/qemu` 仅 4 补丁 + README/changelog；`deliberately not implemented` 仍在 |
| 证据 app 只覆盖访存/分支，缺代表性算术 | ✅已修 | 加 `add.o` + store/load 回读两组断言（失败码 5） | 证据 66/66 通过（app 只有在算术/回读全对时才 rc=0） |

### 第 1 轮 reviewer 验收（2026-11-27）

**重跑记录（命令均在仓库根执行；证据脚本 = 运行期证据目录内的 `run.sh`；真实输出/退出码如下）**：
- 首跑 `run.sh`：`== summary: 66 passed, 0 failed ==`、`EXIT=0`；两路自带注入均转红（`injected: ... (red)` 期望值命中）且 `restore A/B md5` expected=actual 相等。
- 独立注入（非脚本自带）：Tiny profile `ram_guard_size` 置 0（改被测产物 `cpu.c`）→ 重跑同一 `run.sh` ⇒ `summary: 64 passed, 2 failed`、`EXIT=1`，红点 = `restored: boot chain green rc expected=0 actual=1`（app 退出码 1 = guard 存储未触发 CFXMEM）；`cp` 还原 + md5 对账 `cpu.c: OK` → `make build-qemu` rc=0 → 重跑 ⇒ 66/66、`EXIT=0` 回绿。
- `tools/qemu/smoke-kaiwu-tiny.sh`：`=== summary: 7 passed, 0 failed ===`、`SMOKE_EXIT=0`。

**要点/约束逐条核验**：
1. 几何：`-M help` 描述串命中；mtree `ram=0x40000`/`rom=0x2000`/`hmon=0x2000`；`0xffffff03fff8=OK`、`0xffffff040000=NOACCESS`；bootrom 镜像实测 **8192 B**，8193/65536/4096 具名拒绝、8192 通过；`e_entry=0x10100`、PT_LOAD 落头区/BootROM/hmon/窗口外、raw 131073 B 均 rc=1 且消息具名；DUMP 0x800 / SIGNATURE 0x1000 / EXIT 0x30 按现场偏移读回（`check_dump.py`：0x0800/0x0A00/0x0C40/0x0E40/0x1000/0x0030），`rb0 == nm(rb_ip)`、guard/1-past-RAM 的 cause_ip+cause_info 逐项相等。
2. 门控：`check-patch-tree` rc=0（464 patches OK、qemu 段无 problem）；`check-source-state` rc=0（qemu `count=1 clean=True`）；`check-component-changelog` rc=0 PASS；`check-interface`、`check-qemu-forms` 均 rc=2，与基线树（自基线 commit 归档执行同命令）输出归一化路径前缀后 `diff` **为空（逐行相同）**；`check-inst-asm` rc=2（`tiny/bootrom_tiny.bin not found`）与完成区一致；`check-qemu-semantics` 无规则（已退役）。
3. changelog/README 已同步新几何；`components/qemu`、`tools/qemu` 无旧地址（`0xffffff010100`/8 MiB/64 KiB ROM）残留。变更集仅 8 文件（4 补丁 + README/changelog + smoke + 本任务书），未碰 gem5/chipyard；验收前后 `git status --porcelain -uall` 均 **0 行**、`cpu.h`/`cpu.c` md5 还原相等。
4. hmon data `0x0C00` 与 rb0 signed-12-bit 的冲突在「新发现/坑 + 遗留问题」**如实披露为未定项**（证据固件沿用 0xD8 槽、布局待 `m19-testcases-003` 定案），未写成已定；monitor `xp` 可读 guard 一事已在自审披露（guest 路径 CFXMEM 已验）。

**发现（文档级，不阻断，交 architect 收尾改）**：① 完成区 ProfileError 引文为缩写，实际为 `profile 'tiny': sp 0xffffff7eff00 outside RAM [0xffffff000000, 0xffffff03ffff]`；② 完成区把 `check-qemu-semantics` 退役归因 `m13-testcases-043`，Makefile 注释写 `TESTCASES-076t`；③ 验收 1 的 `tests/inst` 代表例本任务未跑（依赖 `m19-testcases-002/003`，已在遗留问题披露）。

**判决：Accepted** —— 验收命令在我自己的重跑下全部通过（66/66、smoke 7/7、门控 rc 与基线逐行对照一致），独立注入可红、cp+md5 还原后回绿，硬约束（只动 QEMU 侧、不提交 git、完成区不写运行期路径）无违反。
