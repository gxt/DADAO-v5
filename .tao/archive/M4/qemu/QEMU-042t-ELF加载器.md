# QEMU-042t: QEMU ELF 加载器（`Ehdr`/`Phdr`/装载/`e_entry`）

**模块**：qemu
**项目里程碑**：M4
**依赖**：`SPEC-107t`、`SPEC-109t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-107t` 调整后的 `.tao/adr/adr-0004-test-machine.md`（ELF 加载约定：解析 `Ehdr`/`Phdr`、按 `VA=PA` 装载 LOAD 段、跳 `e_entry`；**保留 raw-bin 双镜像路径**）与 `.tao/knowledge/contract-elf.md §5/§6`。
  - 现有 `.work/source/qemu/hw/dadao/dadao-machine.c`（实测：只 `load_image_targphys_as` 把 `-bios` 载入 ROM `0xffff_ffff_0000`、`-kernel` 载入 RAM `0xffff_0000_0000`，**不解析 ELF、不读 `e_entry`**；启动经 ROM trampoline）。
  - `ADR-0004` D1（内存映射）、D2.3（双镜像协议）、D3（exit port）、D5.6（区域×访问矩阵）、D5.8（fault 退出码）。
- **输出**（组件源码改在 `.work/source/qemu`；导出补丁）：
  1. `hw/dadao/` 的 ELF 加载器：识别并解析 `Elf64_Ehdr`/`Elf64_Phdr`（大端）；校验 `EI_CLASS=ELFCLASS64`、`EI_DATA=ELFDATA2MSB`、`e_machine=EM_DADAO(0x0DA0)`、`e_flags[7:0]=1`（`contract-elf §1`）；按 `VA=PA` 将 **PT_LOAD** 段装入映射区域（RAM/ROM，按段 `p_vaddr`/`p_memsz`，`p_filesz` 数据 + `.bss` 零填充）；启动 PC = **`e_entry`**（或按 `SPEC-107t` 修订约定）。
  2. **raw-bin 兼容**：既有 `-bios`+`-kernel`(flat) 路径**不回归**（M3 `make test-codegen` 依赖）；区分方式按 `SPEC-107t` 修订约定（建议按 ELF magic `0x7F 'E' 'L' 'F'` 自动判别）。
  3. **负例（畸形 ELF 显式拒绝）**：magic/class/dataEncoding/machine/flags/`e_type` 不符、`Phdr` 越界、`p_filesz > p_memsz`、装载越出映射区域等 → **启动加载阶段报错并非零退出**，**不得**静默截断/部分加载/继续执行（对齐 `ADR-0004` D2.3「工具/加载错误」层，与 guest fault 分层）。
  4. **加载期 over-size 守卫（本任务新增）**：装载前对**尺寸**做显式上界检查——① **ROM blob > 64 KiB**（`ADR-0004` D1：ROM `0xffff_ffff_0000`–`0xffff_ffff_ffff`）；② **镜像（含 `.bss` 的 `p_memsz`）超出 RAM 16 MiB**（`0xffff_0000_0000`–`0xffff_00ff_ffff`）；③ 装载区间越出映射区域 ⇒ **显式报错、非零退出**（信息含实际尺寸与区域上限），**MUST NOT** 静默截断/部分加载。（呼应 `LLVM-056t` 的 `MEMORY`/`ASSERT` 链接期守卫：链接期拦不住的手工/异常 ELF 由加载期兜底。）
  5. 探针/证据：`tools/qemu/min_rom_probe_042t.py`（或 `.work/evidence/QEMU-042t/`）——ELF 正常装载+`e_entry` 生效、raw-bin 兼容、≥3 类畸形 ELF 拒绝、**≥2 类 over-size 拒绝**；含反例注入自检。
- **约束**：
  - **不改 guest 执行语义**（decode/trans 不动）；不动 `target/dadao/**` 指令翻译。
  - **加载错误与 guest fault 分层**：加载阶段错误走 QEMU 非零退出（非 `ADR-0004` D5.8 的 guest 码通道）。
  - **over-size 守卫（本任务新增）**：装载前校验 **ROM blob ≤ 64 KiB**、**镜像（含 `.bss` 的 `p_memsz`）≤ RAM 16 MiB**；超限 ⇒ 显式报错 + 非零退出，不得静默截断/部分加载/继续执行。上界取 `ADR-0004` D1 的 `DADAO_ROM_SIZE`/`DADAO_RAM_SIZE`（与 `LLVM-056t` 的 `MEMORY`/`ASSERT` 链接期守卫互为兜底）。
  - **补丁纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/qemu` 工作树；导出补丁写 `/tmp`、非空 blob；`make check-patch-tree`（含断言⑥）通过；不手改补丁。
  - 构建：`make build-qemu`（**5–20 分钟**，开始前写明预计耗时；`JOBS` 限制）；失败即停、不自动重试。
  - 临时目录 `/tmp/opencode/QEMU-042t/`；**不提交 git**；复杂命令输出留存 `.work/log/qemu/`。

## 验收标准

1. 构建 `make build-qemu` EXIT=0。
2. **ELF 装载**：一个 `EM_DADAO` ELF（`LLVM-056t` 产出或手工构造的等价最小 ELF）→ `qemu-system-dadao` **按 `e_entry` 进入**、执行到 exit port、`$?` 等于期望 guest 码（真实命令+输出）。
3. **段装载**：`.data`/`.rodata` 初值按 VA=PA 正确就位、`.bss` 零填充（探针读出校验，含非零数据）。
4. **raw-bin 兼容**：既有 `-bios trampoline.bin -kernel flat.bin` 路径 EXIT 与 `e_entry` 前行为一致（用一个 M3 用例复跑）。
5. **负例**：≥3 类畸形 ELF（错 magic / 错 `e_machine` / 错 `EI_DATA` / `p_filesz > p_memsz` 等）→ QEMU **非零退出**、错误信息明确；给出真实输出。
6. **over-size 负例（本任务新增）**：≥2 类尺寸超限——ROM blob > 64 KiB、镜像（含 `.bss`）> RAM 16 MiB——→ QEMU **非零退出**、错误信息含实际尺寸与区域上限；并验证**恰好填满**（边界值）**不报错**（不误杀）；给出真实输出。
7. **不回归**：`make check`/`make check-qemu-semantics` EXIT=0；`make test-codegen`（M3 15/15）EXIT=0（说明走 raw-bin 兼容路径）。
8. 一键证据脚本 `.work/evidence/QEMU-042t/run.sh`（含 `--inject`：把 `e_entry` 装载改为 RAM 基址 / 关掉某校验 / 放宽 over-size 上界 → 期望 FAIL → 还原+**重建** → 回绿；结尾无 `tee`）。
9. `<源注释/section 扫描>`：`git status` 仅本任务应有改动。

## 完成区

**测试结果**：

| 命令 | 退出码 | 结论 |
|------|--------|------|
| `make build-qemu` | EXIT=0 | 0 warning（`.work/log/qemu/QEMU-042t-build.log`） |
| `python3 tools/qemu/min_rom_probe_042t.py`（22 项） | EXIT=0 | 22/22 PASS（`.work/log/qemu/QEMU-042t-evidence.log`） |
| `make check` | EXIT=0 | 含 `check-qemu-semantics: PASS`、`check-interface` 全绿、`check-patch-tree` 89 patches OK（`.work/log/qemu/QEMU-042t-check.log`） |
| `make test-codegen` | EXIT=0 | `Results: 15/15 passed, 0 failed`（raw-bin 兼容路径，`.work/log/qemu/QEMU-042t-test-codegen.log`） |
| `run.sh --inject all` | EXIT=0 | 4/4 注入「检出→还原+重建→回绿」，末行 `source restored to HEAD (git diff empty)`（`.work/log/qemu/QEMU-042t-inject.log`） |
| `make check-patch-tree` / `make check-source-state` | EXIT=0 | qemu HEAD=62a659e4，count=1，clean=True |

失败项：**无**。

**修改文件**：

组件源（`.work/source/qemu`，`commit --amend` 收敛为 base+1，worktree clean）：
- `hw/dadao/dadao-machine.c` —— 新增 ELF 加载（路径 A：解析大端 `Elf64_Ehdr`/`Phdr`、头字段校验、按 `p_offset`/`p_vaddr`/`p_filesz`/`p_memsz` VA=PA 装载 `PT_LOAD`、`.bss` 零填充、`cpu_set_pc(CPU(cpu), e_entry)`）；raw-bin 路径（B）保留并加装载期尺寸守卫。

导出/入库：
- `components/qemu/patches/hw/dadao/dadao-machine.c.patch`（596 行，非空 hunk；`check-patch-tree` 断言⑥/⑨ 过）
- `components/qemu/series`（内容不变，幂等跳过）
- `tools/qemu/min_rom_probe_042t.py`（新增，22 项探针，自包含、可 `--only`）

证据（`.work/`，不入库）：`.work/evidence/QEMU-042t/run.sh`（一键 + `--inject`）、`.work/log/qemu/QEMU-042t-*.log`。

**验收结果**（真实输出节选，完整见上述日志）：

- 验收 2/3（ELF 按 `e_entry` 进入 + 段装载）：
  `qemu-system-dadao -M dadao-m1 -nographic -kernel /tmp/opencode/QEMU-042t/pos_data.elf` → `EXIT=0`；该 ELF `e_entry=RAM_base+0x100`，RAM base 处放 `fence`（ILLI `0x88`）毒饵，故只有真正取 `e_entry` 才能到达 exit port 写 0；探针 `elf_data_bss` 校验 `.rodata`/`.data`（非零初值）VA=PA 就位、`.bss` 尾部 16 B 读回为 0。
- 验收 2（`e_entry` 注入反例）：`--inject entry`（`cpu_set_pc(..., e_entry)`→`DADAO_RAM_BASE`）→ 进入 base 毒饵 → `exit=136 (0x88)`，探针 FAIL；还原+重建后回绿。
- 验收 5（畸形 ELF 负例，≥3 类，实测 11 类）：
  ```
  EI_CLASS:      dadao-m1: malformed ELF '...': EI_CLASS=1, expected ELFCLASS64 (2)        EXIT=1
  EI_DATA:       ... EI_DATA=1, expected ELFDATA2MSB (2)                                    EXIT=1
  e_machine:     ... e_machine=0x1234, expected EM_DADAO (0x0da0)                            EXIT=1
  e_flags ver:   ... e_flags version=2, expected 1                                           EXIT=1
  e_flags res:   ... e_flags=0x00000101 has reserved bits [31:8] set                        EXIT=1
  e_type:        ... e_type=0x0001, expected ET_EXEC (0x0002)                                EXIT=1
  Phdr 越界:     ... program header table out of file bounds (...)                           EXIT=1
  filesz>memsz:  ... PT_LOAD[1] p_filesz (0x38) > p_memsz (0x30)                             EXIT=1
  段越界:        ... PT_LOAD[1] ... outside the mapped regions (RAM ... ROM ...)             EXIT=1
  ELF magic 截断: ... file is 16 bytes, smaller than Elf64_Ehdr (64 bytes)                   EXIT=1
  错 magic 无 -bios: ... not an ELF (bad magic); -bios rom.bin is required for the raw-bin path EXIT=1
  ```
- 验收 6（over-size 负例 + 恰好填满不误杀）：
  ```
  ROM blob 65537 B:  dadao-m1: ROM image '...' is 65537 bytes, exceeds the ROM region size limit of 65536 bytes  EXIT=1
  RAM image 16777217B: dadao-m1: RAM image '...' is 16777217 bytes, exceeds the RAM region size limit of 16777216 bytes EXIT=1
  ELF 段 p_memsz > RAM: ... outside the mapped regions (RAM ... size 0x1000000, ROM ... ) EXIT=1
  恰好填满不报错: ELF p_memsz=16 MiB EXIT=0；ELF ROM 段 p_memsz=64 KiB EXIT=0；raw ROM=64 KiB EXIT=0；raw RAM=16 MiB EXIT=0
  ```
- 验收 4/7（raw-bin 不回归）：探针 `rawbin_compat`（`-bios tramp.bin -kernel flat_ok.bin`）EXIT=0；`make test-codegen` 15/15；`make check-qemu-semantics` PASS。

**新发现/坑**：

1. **`p_offset ≠ 0` 与 `p_filesz==0` 的 `p_offset` 未定义**：按 `LLVM-058t` 新布局首个 `PT_LOAD` 的 `p_offset=0x10000`，加载器用 `p_offset`/`p_vaddr` 通用处理（探针专门用非零 `p_offset` 验证）；另 ELF 规范允许 `p_filesz==0` 的段其 `p_offset` 未定义，故文件范围越界检查仅在 `p_filesz>0` 时执行（否则会误杀合法 `.bss`-only 段）。探针 `elf_bss_only_offset` 固化此边界。
2. **错 magic 的双路径语义**：路径选择由 kernel 前 4 字节 magic 决定（`SPEC-107t`），因此「magic 错」的文件在定义上属 raw-bin 路径；当无 `-bios` 时报 `bad magic; -bios rom.bin is required`（装载层非零退出）。有 `-bios` 时按 raw-bin 正常装载（非畸形 ELF）——这是 magic 判别器的必然语义，非缺陷。
3. **`check-interface` 的既有文本依赖**：`tools/integ/check_interface_alignment.py` 的 `dual_image_bios_kernel` 用**字面子串**匹配 patch（`bios rom.bin is required` / `kernel test.bin is required`）。重写报错信息时必须保留该措辞，否则 `make check` 失败（已修正；属既有门控约束，非本次新增）。
4. **exit-port 的 `Blocked re-entrant IO` stderr 警告**：exit-port handler 内 `cpu_loop_exit()` 触发，**改动前即存在**（raw-bin M3 路径同样出现），仅 stderr、不影响 `$?`；本次未改动该 handler。
5. **`e_entry` 生效需显式设 PC**：路径 A 不用 `-bios`，而 CPU 复位 PC=`rb0`=ROM 基址；必须在装载后 `cpu_set_pc(CPU(cpu), e_entry)`。注入 `entry`（改回 RAM 基址）即被探针检出（exit 0x88）。
6. **注入方式**：`oversize` 注入（关掉显式尺寸守卫）后，`load_image_targphys_as` 仍会以通用信息拒绝（非零退出），故该负例的**检出判据为「stderr 含实际尺寸与上限」**（正对应验收 6 的措辞要求），而非仅退出码。

**遗留问题**：

- **EI_OSABI 未校验**：任务 §输出 明确列出校验项为 `EI_CLASS`/`EI_DATA`/`e_machine`/`e_flags[7:0]`；`contract-elf §1.1` 另列 `EI_OSABI=0`，本次未纳入（避免对 LLD 产物的过严拒绝）。若后续要求全量校验 §1，另立任务补 `EI_OSABI`。
- **重叠 `PT_LOAD` 未做显式重叠检查**：真实 `dadao.lds` 产出非重叠段；本次按**最小修改**未加入重叠拒绝（任务负例未要求）。如后续认为需要，可另立任务。
- `e_entry` 未做装载期映射/对齐校验（按 spec，越界/未对齐由 guest 层 fault `0x87`/`0x8D` 处理，属 ADR-0004 D4/D5 分层）；本次遵循分层，未在加载期加检。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查范围：`.work/source/qemu/hw/dadao/dadao-machine.c`（本次唯一改动源）+ `tools/qemu/min_rom_probe_042t.py` + `.work/evidence/QEMU-042t/run.sh`。

**审查意见（逐行）**：

- **逻辑正确性**
  - 大端访问器 `dadao_elf_rd16/32/64` 不依赖 host 端序与 C 结构体 padding；用 `sizeof(Elf64_Ehdr/Phdr)` 仅作尺寸断言（64/56），字段按显式偏移读取。
  - `dadao_region_contains` 用 `memsz <= size - (vaddr - base)`（先判 `vaddr>=base`、`vaddr-base>size`），无 uint64 溢出；ROM 上界 `2^48` 不需计算 `base+size`。
  - Phdr 表越界判据 `e_phoff > len || e_phnum > (len - e_phoff)/e_phentsize` 用除法避免乘法溢出；先校验 `e_phentsize==56` 排除除零。
  - 逐段：`p_filesz>p_memsz`、文件范围（仅 `p_filesz>0`）、区域包含、`p_filesz` 数据写入、`p_memsz-p_filesz` 零填充，均显式失败而非截断。
  - `p_memsz==0` 段跳过（合法空段）；`p_filesz==0` 段仍按 `p_memsz` 零填充。
  - `cpu_set_pc(CPU(cpu), e_entry)` 同时更新 `env.pc`/`env.rb[0]`；实测 entry≠RAM base 时确按 `e_entry` 执行（base 毒饵未触发）。
  - 路径选择：仅读前 4 字节 magic；非 ELF 走 raw-bin，且 raw-bin 才要求 `-bios`（ELF 路径允许省略，符合 ADR-0004 D2.3 路径 A）。
- **设计/惯用法**：改动集中在 `hw/dadao/`，未触碰 `target/dadao/**`（decode/trans 不动）；raw-bin 旧行为除新增尺寸守卫与措辞外不变；`DADAO_ENFORCE_SIZE_LIMITS` 开关仅为注入服务，默认 1。
- **防造假**：所有命令输出经 `cmd > log 2>&1; rc=$?` 留证（无 `tee`）；探针任一 check 失败即非零退出；注入 4 模式各含「注入→重建→检出 FAIL→还原→重建→回绿」真实记录，且末尾 `git diff` 为空。

**finding 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `error_report` 中 `PRIx64` 与 `DADAO_RAM_BASE/ROM_BASE`（ULL 后缀）类型不匹配（`-Wformat`） | ✅已修 | 对二者加 `(uint64_t)` 强转 | `make build-qemu` EXIT=0 且 `grep -c warning:` = 0 |
| 2 | `check-interface::dual_image_bios_kernel` FAIL：门控按字面子串匹配 patch，改写报错措辞后丢失 `bios rom.bin is required`/`kernel test.bin is required` | ✅已修 | 缺 `-kernel` → `-kernel test.bin is required`；raw 缺 `-bios` → 含 `-bios rom.bin is required` | `check_interface_alignment.py` EXIT=0；`make check` EXIT=0 |
| 3 | 探针 `neg_bad_flags_res` 用 `e_flags=0x100`（version=0），命中 version 分支而非 reserved 分支（测试自身 bug） | ✅已修 | 改 `0x101`（version=1 + reserved bit8） | 探针 22/22 PASS |
| 4 | `run.sh --inject all` 只执行首个 mode：QEMU `-nographic` 读取并消费了 process-substitution 的 stdin | ✅已修 | 用 `mapfile` 先读入模式列表；探针 `subprocess.run(..., stdin=DEVNULL)` | `--inject all` 4/4 检出，末行 `restored to HEAD` |
| 5 | 归类路径用 `g_file_get_contents` 整文件读入，大 raw kernel 无谓占内存 | ✅已修 | 新增 `dadao_kernel_is_elf()` 只读 4 B magic；仅 ELF 路径再读全文件 | 探针 22/22 PASS；build 0 warning |
| 6 | `p_filesz==0` 的段其 `p_offset` 按 ELF 规范未定义，文件范围检查会误杀合法 `.bss`-only 段 | ✅已修 | 文件范围检查加 `p_filesz>0` 前置；新增探针 `elf_bss_only_offset` | `elf_bss_only_offset` PASS；探针 22/22 |

**判决**：全部 finding ✅已修，无 `⏸延后`/`❌不修`。改动源自审通过，状态置 **待验收**，交主会话 `/complete` 由 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

审查者：reviewer 子代理，独立验证。

**一、探针/证据脚本审计**

审核 `tools/qemu/min_rom_probe_042t.py`（22项）和 `.work/evidence/QEMU-042t/run.sh`（4注入模式）：

1. **`br_nz(18, 3)` 分支正确性**：`code_data_checks` 中，PASS 路径 `set_zw_rd(16,0,0)` + `st_o_rd(16,16,0)` 写 EXIT=0 → `cpu_loop_exit` 阻断后续 FAIL store；FAIL 路径 `br_nz` 跳至 `set_zw_rd(16,0,1)` + `st_o_rd(16,16,0)` 写 EXIT=1。两支结果不同，非恒真 ✓
2. **注入4模式均有独立 FAIL 路径**：
   - `entry`: `e_entry`→`RAM_BASE` → fence 毒饵触发 ILLI(0x88) → exit=136 ≠ 0 → FAIL ✓
   - `validate`: `e_machine` 校验 `if(0&&...)` → 错 machine 被放过 → 后续段装载可能成功但探针 `neg_bad_machine` 期望 EXIT=1 → FAIL ✓
   - `oversize`: `DADAO_ENFORCE_SIZE_LIMITS=0` → 关闭显式守卫 → `load_image_targphys_as` 仍拒绝 → stderr 含实际尺寸 → FAIL ✓
   - `offset`: `p_offset` 强制为0 → 读 ELF 头部而非偏移0x10000处数据 → data check XOR != 0 → EXIT=1 → FAIL ✓
3. **还原含重建**：每个注入后 `cp $BACKUP $SRC` + `make build-qemu`，非仅源码还原 ✓
4. **无 `tee`**：探针为 Python `subprocess.run(capture_output=True)`；`run.sh` 末尾 `exit "$overall"`，无管道吞退出码 ✓
5. **cmp 防空注入**：`run.sh` 每次注入后 `cmp -s $SRC $BACKUP` 检测 sed 是否命中 ✓

**二、独立重跑记录**

| 命令 | 退出码 | 真实输出 |
|------|--------|---------|
| `python3 tools/qemu/min_rom_probe_042t.py` | EXIT=0 | 22/22 PASS，RESULT: PASS |
| `make check` | EXIT=0 | check-patch-tree 89 patches OK; check-qemu-semantics 149/149 PASS; 80/80 interface checks PASS |
| `make test-codegen` | EXIT=0 | Results: 15/15 passed, 0 failed |
| `make check-patch-tree` | EXIT=0 | 2 component(s), 89 patches OK |
| `make check-source-state` | EXIT=0 | qemu: OK HEAD=62a659e48d9a count=1 clean=True |

**三、独立注入验证（`entry` 模式）**

```
# 1. 注入
$ sed -i 's|cpu_set_pc(CPU(cpu), e_entry);|cpu_set_pc(CPU(cpu), DADAO_RAM_BASE); /* REVIEWER INJECT */|' .work/source/qemu/hw/dadao/dadao-machine.c
$ git -C .work/source/qemu diff --name-only
hw/dadao/dadao-machine.c
  → 改动1行：cpu_set_pc(..., e_entry) → cpu_set_pc(..., DADAO_RAM_BASE)

# 2. 重建（预计5-20 min）
$ make build-qemu
  → EXIT=0

# 3. 探针检出
$ python3 tools/qemu/min_rom_probe_042t.py --only elf_data_bss
  → [FAIL] elf_data_bss  expected: ELF entry=e_entry, .rodata/.data placed, .bss zero -> exit=136 (expected 0)
  → RESULT: FAIL, EXIT=1
  → exit=136 = 0x88 = ILLI（RAM base 处 fence 毒饵触发）

# 4. 还原 + 重建
$ cp backup .work/source/qemu/hw/dadao/dadao-machine.c
$ make build-qemu → EXIT=0

# 5. 回绿
$ python3 tools/qemu/min_rom_probe_042t.py --only elf_data_bss
  → [PASS] elf_data_bss -> exit=0
  → RESULT: PASS, EXIT=0

# 6. 还原确认
$ git -C .work/source/qemu diff --quiet -- hw/dadao/dadao-machine.c
  → CLEAN（无差异）
```

**四、独立负例/边界验证（直接调用 qemu-system-dadao）**

| 测试 | 命令 | EXIT | stderr 摘要 |
|------|------|------|------------|
| EI_CLASS=1 | `$QEMU -M dadao-m1 -nographic -kernel bad_class.elf` | 1 | EI_CLASS=1, expected ELFCLASS64 (2) |
| e_machine=0x1234 | `$QEMU -M dadao-m1 -nographic -kernel bad_machine.elf` | 1 | e_machine=0x1234, expected EM_DADAO (0x0da0) |
| 截断 16B | `$QEMU -M dadao-m1 -nographic -kernel truncated.elf` | 1 | file is 16 bytes, smaller than Elf64_Ehdr (64 bytes) |
| 非 ELF 无 -bios | `$QEMU -M dadao-m1 -nographic -kernel not_elf.bin` | 1 | bad magic; -bios rom.bin is required |
| ROM 超限 65537B | `$QEMU -M dadao-m1 -bios rom_oversize.bin -kernel min.bin` | 1 | ROM image ... is 65537 bytes, exceeds ... limit of 65536 bytes |

**五、e_entry 生效证据**

注入 `entry`（`e_entry` → `DADAO_RAM_BASE`）后 exit=136 (0x88 ILLI)，而正常时 exit=0。RAM base 处放置 fence（ILLI `0x88`）毒饵，证明加载器确实按 `e_entry` 设 PC 而非 RAM base。

**六、段装载证据**

探针 `elf_data_bss` 的 `DATA_CHECKS` 校验：
- `.rodata` 偏移0: `0xDEADBEEFCAFEBABE`，偏移8: `0x0123456789ABCDEF`
- `.data` 偏移16: `0x1122334455667788`，偏移24: `0x99AABBCCDDEEFF00`
- `.bss` 偏移32/40: 0（零填充）
全部 XOR=0 → PASS → exit=0。

**七、非零 p_offset 证据**

探针 `elf_bss_only_offset` 构造 `p_filesz==0` 且 `p_offset=0x100000`（越出文件范围）的段，加载器因 `p_filesz==0` 跳过文件范围检查 → 不误杀 → exit=0。确认加载器不假设 `p_offset=0`。

**八、约束核验**

| 约束 | 状态 | 证据 |
|------|------|------|
| 不改 guest 执行语义（decode/trans 不动） | ✅ | `git -C .work/source/qemu diff --stat HEAD -- target/` 为空 |
| 加载错误与 guest fault 分层 | ✅ | 负例 EXIT=1（QEMU 进程退出），非 exit port 通道 |
| ROM ≤64 KiB / RAM ≤16 MiB 守卫 | ✅ | ROM 65537B → EXIT=1 含尺寸；RAM 16777217B → EXIT=1 含尺寸 |
| 恰好填满不误杀 | ✅ | 探针 elf_fill_ram_exact / elf_fill_rom_exact / rawbin_rom_exact / rawbin_ram_exact 全 PASS |
| 补丁纪律（check-patch-tree 89） | ✅ | check-patch-tree EXIT=0, 89 patches OK |
| 不手改补丁 | ✅ | source 与 patch 一致（patch 为 new-file diff） |
| make build-qemu EXIT=0 | ✅ | 独立重建 EXIT=0 |
| make check / check-qemu-semantics EXIT=0 | ✅ | 独立重跑 EXIT=0 |
| make test-codegen 15/15 | ✅ | 独立重跑 15/15 PASS |
| target/dadao/** 未改 | ✅ | `git diff --stat HEAD -- target/` 为空 |
| git status 仅本任务改动 | ✅ | worktree clean at HEAD 62a659e |

**九、遗留问题判定**

| 遗留 | 阻塞性 | 判定 |
|------|--------|------|
| EI_OSABI 未校验 | 非阻塞 | 任务 §输出 仅要求 EI_CLASS/EI_DATA/e_machine/e_flags；contract-elf §1.1 另列 EI_OSABI=0，避免对 LLD 产物过严拒绝。可另立任务补。 |
| 重叠 PT_LOAD 未显式拒绝 | 非阻塞 | 真实 dadao.lds 产出非重叠段；按最小修改未加入。可另立任务。 |
| e_entry 未做加载期映射/对齐校验 | 非阻塞 | 按 ADR-0004 D4/D5 分层，越界/未对齐由 guest 层 fault 处理。 |

三项遗留均为非阻塞，不影响本任务交付。

**判决：Accepted**

全部验收标准独立验证通过。探针22/22 PASS，`make check`/`test-codegen`/`check-patch-tree`/`check-source-state` 全绿，独立注入（entry 模式）完整循环通过（注入→重建→检出 FAIL→还原→重建→回绿），独立负例5类验证通过，e_entry 生效证据确凿，段装载/bss 零填充/非零 p_offset/over-size 守卫均已验证。遗留3项均为非阻塞。
