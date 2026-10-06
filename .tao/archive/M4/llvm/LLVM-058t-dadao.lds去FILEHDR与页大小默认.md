# LLVM-058t: `dadao.lds` 去 `FILEHDR PHDRS` + DADAO 页大小默认 64 KiB

**模块**：llvm
**项目里程碑**：M4
**依赖**：`SPEC-112t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（v5 自身知识，**执行依赖**）：
  - `SPEC-112t` 后版本 `.tao/adr/adr-0003-object-abi.md`（§D5 + `## 修订` rev. 2026-10-06）与 `.tao/knowledge/contract-elf.md §5/§6.1.2`（**期望值以此为准，不从实现反推**）。
  - 当前 `tests/scripts/dadao.lds`（`LLVM-056t` 产物，`text PT_LOAD FILEHDR PHDRS;`）。
  - `.work/source/llvm-project/lld/ELF/Arch/DADAO.cpp`（`LLVM-056t` 版，193 行）；**只读对照** `lld/ELF/Arch/PPC64.cpp:605`（`defaultMaxPageSize = 65536;`）、`lld/ELF/Target.h:144`（`unsigned defaultMaxPageSize = 4096;` 成员）、`lld/ELF/Driver.cpp:2376-2390`（`-z max-page-size` 以 `defaultMaxPageSize` 为默认值、显式值即覆写）。
  - `components/llvm-project/{series,patches/**,changelog.md}`；`spec/Process-01-组件补丁组织与构建编排.md`（补丁导出纪律）。
  - **对拍基准**（`LLVM-056t` 证据）：`.work/evidence/LLVM-056t/run.sh` + `inputs/*.s`（11 个）、`.work/log/llvm/LLVM-056t-*`（reloc `.text` 字节 = `4c200018482100004822ffff740000036b2000046e209003`；`data.elf` 的 `.data` = `0000ffff000000000000ffff000000100000ffff00000000`、`.rodata` = `0000ffff00000000`；RAM/ROM 溢出负例与边界恰好填满）。
  - **内存几何**（`ADR-0004 §D1`，自包含）：RAM 16 MiB `0xffff_0000_0000`–`0xffff_00ff_ffff`；ROM 64 KiB `0xffff_ffff_0000`–`0xffff_ffff_ffff`。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  1. `tests/scripts/dadao.lds`：`text PT_LOAD FILEHDR PHDRS;` → **`text PT_LOAD;`**（**唯一改动**；`MEMORY`/`ENTRY`/ 段序 / `ALIGN` / `ASSERT` / `data`/`rom` 两行 `PT_LOAD` 均**不变**）。
  2. `.work/source/llvm-project/lld/ELF/Arch/DADAO.cpp`：在 ctor（第 54–60 行 `DADAO(Ctx &ctx) : TargetInfo(ctx) { … }`）内**加一行** `defaultMaxPageSize = 0x10000;  // DADAO page = 64 KiB (DADAO-12 §2.2.1)`（照 `PPC64.cpp:605`）。**不动** `relocate()` / `getRelExpr()` / `calcEFlags()` / `relocateAlloc()` / `relocateInSection()` / 其它任何函数体与 `iRelSymbolicRel` 哨兵行。
  3. 重建 `lld`（`make build-lld` 或 `ninja -j8 -C .work/build/llvm lld`；**开始前申报重建，预计 5–20 min**）。
  4. 重导出补丁 + `series`（`Process-01`：`git -C .work/source/llvm-project commit --amend` 收敛 base+1 → `tools/infra/make_patch.py` → `make check-patch-tree`）；`components/llvm-project/changelog.md` 加一条 `LLVM-058t` 记录。
  5. 重跑并更新链接证据：**新建** `.work/evidence/LLVM-058t/run.sh`（本任务主证据，含反向证明）；**更新** `.work/evidence/LLVM-056t/run.sh` 中因本改动而过期的期望值（此前 §2 检查 `text PT_LOAD file offset` = `0x0`、§7 grep `FILEHDR PHDRS`），使 056t 脚本在当前代码库下仍全绿（或在其头部标注「§2/§7 期望已由 `LLVM-058t` 更新」）。在本任务「完成区」记录重跑结果；**不得**改写 `LLVM-056t` 任务书既有「完成区/审阅记录」（如需注记只追加）。
- **约束**：
  - **只改上述 2 个实现点**（`dadao.lds` 1 行 + `DADAO.cpp` 1 行）；**不改** `DADAO.cpp` 其它函数；**不改** reloc 语义 / `e_flags` / `EM_DADAO` / 段序 / `ASSERT` / `MEMORY` / `ENTRY`。
  - **硬约束——中性/不约束完整 linker**（用户本轮原话，务必贯彻）：
    - 本任务是「**M4 路径级脚本 + 可覆写目标默认值**」的落地，**LLD 的 `FILEHDR PHDRS` 能力原样保留**；**不得**把 `defaultMaxPageSize = 0x10000` 描述为「DADAO 页大小永不改变」的不变式（它是**默认值**，`-z max-page-size` 可覆写）。
    - `p_offset` **不要求**为 0、**不禁止**为 0；不得把「首段 `p_offset = 0x10000`」写成算法不变式（它是当前布局的**实测**结果）。
    - 只约束 M4 路径级脚本 + 目标默认值，**不得**影响后续完整 linker 实现；**不得**新增任何 linker 层的硬编码约束。
  - **补丁纪律（`spec/Process-01`）**：不手改补丁；`make_patch.py` 导出前校验 E1（worktree 干净 + HEAD = base+1）；导出后 `make check-patch-tree`（9 断言）须过。`series` 路径不变（`lld/ELF/Arch/DADAO.cpp.patch` 已存在 ⇒ 仍 57 项）。
  - 构建受 `JOBS`（默认 8）限制；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-058t/`；**不提交 git**；复杂命令完整输出留存 `.work/log/llvm/`。

### 硬约束清单（下发/执行必带）

1. **只动任务书范围**：`tests/scripts/dadao.lds` + `.work/source/.../DADAO.cpp` ctor 一行 + 补丁/changelog/证据；越界须披露。
2. **不提交 git**（主仓库与组件源树均不提交；组件源树仅按 `Process-01` `commit --amend` 收敛 base+1）。
3. **完成区与真实输出逐条对齐**：命令一律 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，**禁** `cmd | tee log; echo $?`（管道后 `$?` 是 `tee` 的，恒 0；需要同时看终端与落盘时用 `cmd > log 2>&1; rc=$?; cat log; echo "EXIT=$rc"` 或 `${PIPESTATUS[0]}`）。
4. **失败即停、禁自动重试**（含换参数/换等价命令/改码后重跑）；保留失败现场并报用户。
5. **临时目录** `/tmp/opencode/LLVM-058t/`；不得污染仓库。
6. **补丁导出纪律**（`Process-01`）：见上约束。
7. **一键证据脚本** `.work/evidence/LLVM-058t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入→预期 FAIL→还原（含重建）→回绿**（见验收 12）；结尾**不得用 `tee` 吞退出码**。
8. **重建成本申报**：每次重建前在回复写「重建 `lld`，预计 N 分钟」；多例注入合并到一轮重建，不零散重跑。

## 验收标准

> 每条须**真实输出 + 退出码**；详细日志落 `.work/log/llvm/`；证据脚本 `.work/evidence/LLVM-058t/`。

1. **构建**：`make build-lld`（或 `ninja -j8 -C .work/build/llvm lld`）**EXIT=0**（贴真实输出；说明 `bin/ld.lld` 为 `lld` 目标的符号链接拷贝，无独立 `ld.lld` 目标）。
2. **`dadao.lds`**：改为 `text PT_LOAD;`；`grep -n 'FILEHDR' tests/scripts/dadao.lds` **无输出**（EXIT=1）；其余内容与 `LLVM-056t` 版**逐行一致**（给出 `diff` 或对拍输出，仅该行变化）。
3. **`DADAO.cpp`**：ctor 含 `defaultMaxPageSize = 0x10000;`；`git -C .work/source/llvm-project diff -- lld/ELF/Arch/DADAO.cpp`（相对 056t 的 base+1 版本）**仅新增该 1 行**；`relocate`/`getRelExpr`/`calcEFlags`/`relocateAlloc`/`relocateInSection` 函数体 diff **为空**。
4. **链接与 ELF 布局**（`llvm-mc` 复用 `LLVM-056t` 的 `inputs/reloc.s` → `reloc.o`；`ld.lld -T tests/scripts/dadao.lds reloc.o`，`LD_EXIT=0`）——`llvm-readobj -h/-l/-S`：
   - **无 `PT_LOAD` 越界**：所有 `PT_LOAD` 的装载区间 `[p_vaddr, p_vaddr+p_memsz)` 均落在映射区（RAM/ROM）内；**不出现** `0xFFFEFFFFF000`；首段 `p_vaddr = 0xFFFF00000000`。
   - **`e_entry = 0xFFFF00000000`**。
   - **`p_align = 0x10000`（65536）**（全部 `PT_LOAD`）。
   - **首段 `p_offset = 0x10000`** 且 **`p_offset ≡ p_vaddr (mod p_align)`**（`0x10000 mod 0x10000 = 0 = 0xFFFF00000000 mod 0x10000`）。**注**：`p_offset` 为**实测值**，不作为算法不变式。
   - `.text` VA = `0xFFFF00000000`；`.data` 段 VA **与 056t 记录一致**（不变）。
5. **reloc 期望值逐条不变（与 `LLVM-056t` 记录对拍）**：
   - `reloc.elf` `.text` 字节 = `4c200018482100004822ffff740000036b2000046e209003`（**逐字节相同**）；`readobj -r` 无未解析 reloc。
   - `data.elf` `.data` = `0000ffff000000000000ffff000000100000ffff00000000`、`.rodata` = `0000ffff00000000`（逐字节相同）。
6. **反向证明 ①——LLD `FILEHDR PHDRS` 能力未削弱**：把 `FILEHDR PHDRS` **临时加回**脚本副本（或在 `/tmp/opencode/LLVM-058t/` 下建带 `FILEHDR` 的副本）→ `ld.lld` 链接**成功 EXIT=0**（`PT_LOAD`/`p_offset` 可不同）；随后**删除副本**（不污染 `tests/scripts/`），主脚本回绿。给真实输出。
7. **反向证明 ②——`-z max-page-size` 仍可覆写**：`ld.lld -z max-page-size=4096 -T ... reloc.o` → `p_align = 0x1000`（还原到 4096）、链接 EXIT=0、reloc 字节仍相同；还原为默认链接后 `p_align = 0x10000`。给真实输出（可选附 `-z max-page-size=0x20000`）。
8. **reloc 溢出负例仍成立**：`REL14`/`REL20`/`REL26`/`ABS48`（指令路径与数据路径）越界 ⇒ `LD_EXIT≠0` + `out of range`（5 条，同 056t）。
9. **段溢出负例仍成立**：`ram_ovf`（`.text+.rodata+.data+.bss` > RAM 16 MiB）、`rom_ovf`（`.rom` > 64 KiB）⇒ `LD_EXIT≠0` + 区域报错；**边界恰好填满**（`ram_fill`、`rom_fill`）⇒ `LD_EXIT=0`（不误杀）。
10. **不回归**：`make check` EXIT=0；`make check-patch-tree` EXIT=0（`series` 57 项、断言全过）；`make test-codegen` EXIT=0；`make check-lit` EXIT=0（若环境已 build-mc）。
11. **补丁与台账**：`components/llvm-project/patches/lld/ELF/Arch/DADAO.cpp.patch` 已更新为含新行的版本（非空 hunk）；`series` 含该路径不变；`components/llvm-project/changelog.md` 含 `LLVM-058t` 条目（写明：去 `FILEHDR PHDRS` + `defaultMaxPageSize = 0x10000`；`p_align` 默认 64 KiB 可覆写）。
12. **一键证据脚本**：`.work/evidence/LLVM-058t/run.sh` 正常模式 **全绿 / EXIT=0**；`--inject` 模式**内置注入→FAIL→还原（含重建）→回绿**，至少覆盖：
    - (a) **脚本级注入（不改编译输入，优先）**：把 `dadao.lds` 的 `text PT_LOAD;` 改回 `text PT_LOAD FILEHDR PHDRS;` → 首段越界检查 **FAIL**；还原 → 回绿（无需重建）。
    - (b) **源码级注入（一次重建批量做）**：把 `defaultMaxPageSize = 0x10000` 改为 `0x1000` → 重建 `lld` → `p_align` 检查 **FAIL**；还原源码 + **重建** → 回绿。
    - 注入有效性：注入后 `git -C .work/source/llvm-project diff --name-only`（或 `dadao.lds`）**非空**；还原后 `git diff` 空、工作区干净。
13. **状态**：完成后 `**状态**` 置 `待验收`；提交前经 `/complete` 收尾。

## 完成区

**测试结果**：一键证据脚本 `.work/evidence/LLVM-058t/run.sh` **正常模式 0 failure / EXIT=0**、`--inject` 模式 **0 failure / EXIT=0**（真实输出：`.work/log/llvm/LLVM-058t-evidence-run.log`、`LLVM-058t-evidence-inject.log`）。重建耗时：`make build-lld` 为增量——cmake 复用已有配置（日志 `Configuring done (8.1s)` + `Generating done (4.2s)`），ninja 仅 3 步（编译 `DADAO.cpp.o` + 归档 `liblldELF.a` + 链接 `bin/lld`）；`--inject` 另含两次增量重建（源码注入 + 还原）。回归门控：`make check`/`make check-patch-tree`/`make test-codegen`/`make check-lit` 全 EXIT=0。

**修改文件**：
- `tests/scripts/dadao.lds`（首段 `text PT_LOAD FILEHDR PHDRS;` → `text PT_LOAD;` + 头部注释同步，见审阅记录 F1/用户裁定）
- `.work/source/llvm-project/lld/ELF/Arch/DADAO.cpp`（ctor **+1 行** `defaultMaxPageSize = 0x10000;`；组件源树经 `commit --amend` 收敛 base+1，**未提交**）
- `components/llvm-project/patches/lld/ELF/Arch/DADAO.cpp.patch`（由 `make_patch.py` 重导出，`+1,193`→`+1,194`；`series` 内容不变仍 57 项）
- `components/llvm-project/changelog.md`（追加 `LLVM-058t` 一条）
- `.work/evidence/LLVM-056t/run.sh`（§2 首段 file offset `0x0`→`0x10000`、§7 `text PT_LOAD FILEHDR PHDRS`→`text PT_LOAD`；头部加注由 `LLVM-058t` 更新）
- `.work/evidence/LLVM-058t/run.sh`（新建）+ `DADAO.056t.cpp`（056t 基线快照）
- 本任务书（完成区/自审/状态）

**验收结果**（逐条对应「验收标准」1–13；完整日志 `.work/log/llvm/LLVM-058t-acceptance.log` 与 `LLVM-058t-*.log`）：

1. **构建** `JOBS=8 make build-lld` EXIT=**0**；`bin/ld.lld -> lld`（`lld` 目标的 POST_BUILD 符号链接拷贝，无独立 `ld.lld` 目标）。真实尾部：`[1/3] Building CXX object …/Arch/DADAO.cpp.o`、`[3/3] Linking CXX executable bin/lld`、`build-lld: PASS`（`.work/log/llvm/LLVM-058t-build-lld.log`）。
2. **`dadao.lds`** `grep -n 'FILEHDR'` 无输出 **EXIT=1**；`text PT_LOAD;`（三条 `PT_LOAD` 均去 `FILEHDR`）。`git diff`：功能行仅 `text PT_LOAD FILEHDR PHDRS;`→`text PT_LOAD;`；此外按用户裁定同步了第 12–14 行注释（原述 `FILEHDR PHDRS` 已失真）——详见 F1 与用户原话。`MEMORY`/`ENTRY`/段序/`ALIGN`/`ASSERT`/`data`:`rom` 行**逐行不变**。
3. **`DADAO.cpp`** ctor 含 `defaultMaxPageSize = 0x10000;`。以 056t 提交版（`.work/evidence/LLVM-058t/DADAO.056t.cpp`，193 行）对拍：`diff` = `59a60 > defaultMaxPageSize = 0x10000;  // DADAO page = 64 KiB (DADAO-12 §2.2.2)`，**added=1 / removed=0**；`relocate()`/`getRelExpr()`/`calcEFlags()`/`relocateAlloc()`/`relocateInSection()` 函数体 diff **为空**。
4. **链接与布局**（`llvm-mc` 056t `reloc.s`→`reloc.o`；`ld.lld -T dadao.lds reloc.o` **LD_EXIT=0**）：无 `PT_LOAD` 越界（自定义 bounds 检查：2 个 PT_LOAD 全落 RAM/ROM）；`e_entry=0xFFFF00000000`；首段 `p_vaddr=0xFFFF00000000`；全部 `p_align=0x10000`；首段 `p_offset=0x10000`（**实测**）且 `p_offset ≡ p_vaddr (mod p_align)`（`0x10000 ≡ 0xFFFF00000000 mod 0x10000`）；`.text` VA=`0xFFFF00000000`；**不出现** `0xFFFEFFFFF000`。
5. **reloc 字节逐条不变**：`reloc.elf .text = 4c200018482100004822ffff740000036b2000046e209003`（逐字节相同）；`llvm-readobj -r` 无未解析 reloc；`data.elf .data = 0000ffff000000000000ffff000000100000ffff00000000`、`.rodata = 0000ffff00000000`（均与 056t 相同）。
6. **反向证明 ①（能力未削弱）**：`/tmp` 下的脚本副本临时加回 `text PT_LOAD FILEHDR PHDRS;` → `ld.lld` **EXIT=0**（首段 `Offset=0x0`、`vaddr=0xFFFEFFFF0000`）；用后已删（`tests/scripts/` 未污染，主脚本回绿）。
7. **反向证明 ②（`-z max-page-size` 可覆写）**：`-z max-page-size=4096` → `p_align=0x1000`（EXIT=0）；`-z max-page-size=0x20000` → `p_align=0x20000`；默认链接回 `0x10000`。
8. **reloc 溢出负例仍成立**：`ovf_rel14/20/26`、`ovf_abs48`、`ovf_abs48i` 均 **rc=1 + `out of range`**（5/5）。
9. **段溢出负例仍成立**：`ram_ovf` rc=1（`RAM sections exceed 16 MiB`）、`rom_ovf` rc=1（`ROM section exceeds 64 KiB`）；`ram_fill`/`rom_fill` rc=0（恰好填满不误杀）。
10. **不回归**：`make check` EXIT=0（`repository checks: PASS`，lit 50/50）、`make check-patch-tree` EXIT=0（`2 component(s), 89 patches OK`）、`make test-codegen` EXIT=0（`Results: 15/15 passed`）、`make check-lit` EXIT=0（50/50）。
11. **补丁与台账**：`DADAO.cpp.patch` 重导出为 `@@ -0,0 +1,194 @@`（含新行、非空 hunk）；`series` 含 `lld/ELF/Arch/DADAO.cpp.patch`（57 项）；`changelog.md` 含 `LLVM-058t` 条目（去 `FILEHDR PHDRS` + `defaultMaxPageSize = 0x10000` / `p_align` 默认 64 KiB 可覆写）。
12. **一键证据脚本** `.work/evidence/LLVM-058t/run.sh`：正常模式 **全绿/EXIT=0**；`--inject`：`(a)` 脚本级加回 `FILEHDR PHDRS` → bounds 检查 FAIL（`OUT-OF-BOUNDS PT_LOAD: vaddr=0xfffeffff0000`）→ 还原回绿（无重建）；`(b)` 源码级 `0x10000`→`0x1000` → **重建** → `p_align=0x1000,`（FAIL）→ 还原源码（`git status` 空）+ **重建** → `p_align=0x10000,` 回绿。注入有效性：注入后 `git -C .work/source/llvm-project diff --name-only` 非空；还原后工作区干净。
13. **状态**：已置 `待验收`。

**新发现/坑**：
1. **任务书 §输出 2 的引用笔误**：`DADAO-12 §2.2.1` 实为「超页的地址转换」（512 MiB），普通页 64 KiB 在 **§2.2.2**（`SPEC-112t` 已记录同笔误）。`DADAO.cpp` 注释采用正确的 `DADAO-12 §2.2.2`。
2. **`llvm-readobj -l` 字段进制不统一**：`Offset`/`VirtualAddress`/`PhysicalAddress` 为**十六进制**，而 `FileSize`/`MemSize`/`Alignment` 为**十进制**——证据脚本初版按 `0x…` 解析 `MemSize`/`Alignment` 导致误报（已修为按前缀自适应解析）。
3. **`readobj -r` 空表**：`DADAO` 可链接 ELF 的 `.rela.*` 已在链接期就地全部解析，`-r` 输出空 `Relocations [ ]`（脚本据此断言未解析 reloc=0）。
4. **056t 证据脚本过期期望已同步**：`FILEHDR PHDRS` 移除后 056t §2/§7 期望过时，已更新并加注；056t 脚本重跑全绿。
5. **变更后 `DADAO.cpp` 与 056t 的对拍基线**：主仓库未提交 058t，故从主仓库 `HEAD` 的 056t 补丁重建 056t 文件快照存于证据目录（提交后仍可复现）。

**遗留问题**：
- **跨模块影响（需后续任务核实）**：`dadao.lds` 默认 `p_align=64 KiB` 使首段 `p_offset` 由 `0x0` 变为**实测 `0x10000`**（ELF 头/程序头表仍在文件中，`ProgramHeaderOffset=0x40`）。段 VA=PA 未变，故 guest 内存装载区间不变；但 **`QEMU-042t`（ELF 加载器）/`INTEG-016t` 若对 `p_offset` 或 `p_align` 有断言/假设，其输入期望值需相应核实**。本任务不改 QEMU，留待其任务覆盖。
- 无其它未完成项。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`tests/scripts/dadao.lds`、`lld/ELF/Arch/DADAO.cpp`（ctor +1 行）、重导出补丁/`series`、`changelog.md`、`.work/evidence/{LLVM-056t,LLVM-058t}/run.sh`。逐行核对：功能行改动、未触函数体、补丁非手改、证据脚本 FAIL 路径可达性、注入可复原性。判决：**无未修 finding，可标「待验收」**（下表 6 项均 ✅已修）。

**用户裁定（原话落盘；子会话问答对父会话不可见，在此登记）**：
- 提问：`dadao.lds` 第 12–14 行注释描述 `FILEHDR PHDRS`（去 `FILEHDR` 后已失真），与验收 2「`grep FILEHDR` 无输出」和「仅该行变化」冲突，如何处置？
- **用户裁定（原样）**：选「**更新注释块(推荐)**」——「改第33行为 `text PT_LOAD;`，同时改写第12-14行注释：去掉 `FILEHDR` 描述，改为说明『首段自 `.text` 起、`p_offset` 为链接器实测(当前 0x10000)，非算法不变式』。验收2『仅该行变化』按『功能性仅该行(注释随事实同步)』理解，`grep FILEHDR` 仍为 EXIT=1。」

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `dadao.lds` 注释提及 `FILEHDR PHDRS`，若保留则验收 2 `grep FILEHDR` 命中、且注释失真 | ✅已修（用户裁定） | 改写第 12–14 行注释为「头部只留在文件、首段自 `.text` 起、file offset 为实测非不变式」；`text PT_LOAD FILEHDR PHDRS;`→`text PT_LOAD;` | `grep -n FILEHDR tests/scripts/dadao.lds` EXIT=1；`git diff` 仅该注释块 + 功能行；证据脚本 §2 PASS |
| F2 `DADAO.cpp` 首次编辑误加 4 行注释块，违反「仅新增 1 行」 | ✅已修 | 收敛为单行内联注释 `defaultMaxPageSize = 0x10000;  // DADAO page = 64 KiB (DADAO-12 §2.2.2)` | 与 056t 快照 `diff` = `59a60`，added=1/removed=0；`git diff --numstat` = `1 0` |
| F3 证据脚本按 `0x…` 解析 `llvm-readobj -l` 的 `MemSize`/`Alignment`，而二者实为**十进制** → bounds/p_align 误报 FAIL | ✅已修 | `pt_load_bounds` 用自适应进制 `num()`；`all_aligns` 输出 `printf '0x%x'` | 正常模式重跑 5 个原 FAIL 项全部 PASS，0 failure/EXIT=0 |
| F4 `--inject` 末条 `restore(b): p_align green again` 的 expected 漏尾逗号（actual 为 `0x10000,`）→ 恒 FAIL | ✅已修 | expected 改 `0x10000,`（同 normal 模式口径） | `--inject` 重跑 0 failure/EXIT=0（`actual=0x10000,`） |
| F5 证据脚本 §3 依赖主仓库 `HEAD` 的 056t 补丁（058t 提交后 `HEAD` 变为 058t，检查失效） | ✅已修 | 新增 056t 文件快照 `.work/evidence/LLVM-058t/DADAO.056t.cpp`，脚本优先用快照、缺失再回退 `HEAD` | 快照 193 行；重跑 §3 四项 PASS |
| F6 任务书 `DADAO-12 §2.2.1` 为超页（512 MiB），普通页 64 KiB 实为 `§2.2.2` | ✅已修 | 代码注释采用 `DADAO-12 §2.2.2`（与 `contract-elf §5.3` 一致） | `grep '§2.2.2'` 命中；完成区「新发现/坑」① 披露 |

**对账**：6 项 finding 全部 ✅已修；正常 `run.sh` 0 failure/EXIT=0、`--inject` 0 failure/EXIT=0、`make check`/`test-codegen`/`check-lit`/`check-patch-tree` 全绿 ⇒ 状态置「待验收」。


#### 第 1 轮 reviewer 验收（下发前预检）

**审查结论**：与 `SPEC-112t` 同轮审查，判决 **Accepted**（可直接下发）。详细逐项结论见 `SPEC-112t` 审阅记录「第 1 轮 reviewer 验收」。

**本任务专项确认**：
- 依赖 `SPEC-112t`（spec-first）正确且足够 ✓
- 「只改 2 行」（`dadao.lds` 1行 + `DADAO.cpp` 1行）与验收 2/3 一致 ✓
- `DADAO.cpp` 当前 193 行、ctor 内无 `defaultMaxPageSize`（待新增）✓
- `PPC64.cpp:605` `defaultMaxPageSize = 65536` 可作对照 ✓
- `Target.h:144` 默认值 4096 可作对照 ✓
- `components/llvm-project/series` 57 项含 `lld/ELF/Arch/DADAO.cpp.patch` ✓
- 验收 6/7 反向证明保证 `FILEHDR PHDRS` 能力保留 + `-z max-page-size` 可覆写 ✓
- `make build-lld`/`make check-patch-tree`/`make check`/`make test-codegen`/`make check-lit` 目标均存在于 Makefile ✓

#### 第 2 轮 reviewer 验收（实施后独立重跑）

**审查结论**：判决 **Accepted**。

**一、证据脚本审计**

`run.sh` 审计通过：
- FAIL 路径：`report`/`report_rc`/`expect_diff` 均有 FAIL → `FAILS++` → 退出码非零 ✓
- 注入可还原：(a) 脚本级 `cp` backup/restore + `trap restore_files EXIT`；(b) 源码级 backup + 重建 + 还原 + 重建 ✓
- 无 `tee` 吞退出码：所有检查命令用 `cmd > log 2>&1; rc=$?` ✓
- 无恒真断言：`report` 和 `expect_diff` 均有双向 FAIL 路径 ✓

**二、重跑记录**

正常模式：
```
=== result: 0 failure(s) ===
EVIDENCE: PASS
EXIT=0
```
52 项检查全 PASS（build/llds content/DADAO.cpp diff/link+header/PT_LOAD layout/reloc bytes/reverse proof①②/overflow negatives/region boundary/patch+changelog/regression gates）。

`--inject` 模式：
```
=== result: 0 failure(s) ===
EVIDENCE: PASS
EXIT=0
```
注入(a)脚本级加回 FILEHDR PHDRS → bounds 检查 `rc=1`（`OUT-OF-BOUNDS PT_LOAD: vaddr=0xfffeffff0000`）→ 还原回绿 ✓
注入(b)源码级 `0x10000→0x1000` → 重建 → `p_align=0x1000,`（FAIL）→ 还原+重建 → `p_align=0x10000,` 回绿 ✓

**三、独立注入（与 engineer 不同的值）**

注入：`defaultMaxPageSize = 0x10000` → `0x8000`
- `git diff --name-only` = `lld/ELF/Arch/DADAO.cpp`（非空 ✓）
- 增量重建 `lld` EXIT=0
- `p_align = 32768 = 0x8000` ≠ 期望 `0x10000` → **FAIL** ✓
- 还原源码：`git status --porcelain` 空 ✓
- 重建 `lld` EXIT=0
- `p_align = 65536 = 0x10000` → **回绿** ✓

**四、约束核验**

| 约束 | 结果 |
|------|------|
| 只改 2 行（`dadao.lds` 功能行1行 + 注释同步 + `DADAO.cpp` 1行） | ✓ `diff` 仅 `text PT_LOAD FILEHDR PHDRS;`→`text PT_LOAD;` + 注释块 + `DADAO.cpp` +1行 |
| `DADAO.cpp` 函数体 diff 为空 | ✓ `diff` = `59a60 > defaultMaxPageSize...`，added=1/removed=0 |
| `e_entry = 0xFFFF00000000` | ✓ |
| 全部 `p_align = 0x10000` | ✓ |
| 首段 `p_offset = 0x10000` 且 `≡ p_vaddr (mod p_align)` | ✓ |
| 无 PT_LOAD 越界 | ✓ |
| `.text` VA = `0xFFFF00000000` | ✓ |
| reloc 字节逐条不变 | ✓ `.text`=`4c200018482100004822ffff740000036b2000046e209003`；`.data`=`0000ffff000000000000ffff000000100000ffff00000000`；`.rodata`=`0000ffff00000000` |
| `readobj -r` 无未解析 reloc | ✓ count=0 |
| 反向证明① FILEHDR 能力保留 | ✓ 脚本副本加回 FILEHDR → EXIT=0 |
| 反向证明② `-z max-page-size` 可覆写 | ✓ `4096→p_align=0x1000`；`0x20000→p_align=0x20000` |
| reloc 溢出负例（5 条）仍报错 | ✓ `rc=1 + out of range` |
| 段溢出 + 恰好填满不误杀 | ✓ `ram_ovf`/`rom_ovf` rc=1；`ram_fill`/`rom_fill` rc=0 |
| `make check` EXIT=0 | ✓ 50/50 |
| `make check-patch-tree` EXIT=0 | ✓ 89 patches OK |
| `make test-codegen` EXIT=0 | ✓ 15/15 |
| `make check-lit` EXIT=0 | ✓ 50/50 |
| 中性：`dadao.lds` 注释不含不变式措辞 | ✓ 写「file offset is a linker file-layout artifact (currently 0x10000), not an invariant」 |
| 中性：`DADAO.cpp` 注释不含不变式措辞 | ✓ 仅「DADAO page = 64 KiB」（可覆写） |
| 补丁含新行、series 57 项 | ✓ |
| changelog 含 LLVM-058t 条目 | ✓ |
| 056t 证据脚本过期期望已更新（仅 §2 offset + §7 pattern） | ✓ 头部加注 `LLVM-058t` 更新 |
| 056t 任务书未被改写 | ✓ `git diff` 空 |
| 056t 脚本重跑 EXIT=0 | ✓ |

**五、遗留判定**

- **`QEMU-042t` / `INTEG-016t` 断言核实**：`p_offset` 由 `0x0` 变为 `0x10000`，若这两个任务对 `p_offset` 或 `p_align` 有断言需相应更新。**非阻塞**，留待其任务覆盖。建议在 MEMORY 中登记为待核实项。
- **`DADAO-12 §2.2.1`→`§2.2.2` 笔误**：代码注释已采用正确引用。✓
- 无其它遗留。
