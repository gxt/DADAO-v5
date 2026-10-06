# LLVM-058t: `dadao.lds` 去 `FILEHDR PHDRS` + DADAO 页大小默认 64 KiB

**模块**：llvm
**项目里程碑**：M4
**依赖**：`SPEC-112t`
**状态**：待开始

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

**测试结果**：（真实输出/退出码；引用 `.work/evidence/LLVM-058t/` 与 `.work/log/llvm/`；重建耗时）

**修改文件**：（`tests/scripts/dadao.lds`、组件源树 `lld/ELF/Arch/DADAO.cpp`、补丁集、`components/llvm-project/changelog.md`、证据脚本、本任务书）

**验收结果**：（逐条对应「验收标准」1–13，附真实命令输出/退出码；**禁**转述/估算）

**新发现/坑**：

**遗留问题**：（含跨模块：新布局 `p_align = 64 KiB` / 首段 `p_offset = 0x10000` 对 `QEMU-042t`/`INTEG-016t` 的输入影响）

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

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
