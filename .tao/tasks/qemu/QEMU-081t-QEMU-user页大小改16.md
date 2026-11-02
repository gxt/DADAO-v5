# QEMU-081t: QEMU user 页大小 12 → 16（64 KiB）

**模块**：qemu
**项目里程碑**：M11
**依赖**：无（下游：`GEM5-014t` 验收 5b 直接消费本任务；`QEMU-079t`/`QEMU-080t` 若开工，与 `target/dadao/cpu-param.h` 同文件，须串行并在本任务之后 rebase）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库根；组件源树 `.work/source/qemu` 现 HEAD=`f98216a`、base+1、`git status` 干净；实现落任务分支 `QEMU-081t`，不 merge、不 push）

## 用户裁定（2026-11-02，逐字）

- DADAO 页大小是 **16 位 / 64 KiB**；`contract-elf` 的 `p_align=0x10000` 一致。
- `qemu-dadao` 当前 `TARGET_PAGE_BITS=12`（4 KiB）是 **QEMU 的 bug**，不是基准，必须改为 16。
- `GEM5-014t` 已按 16 位/65536 修正，依赖本任务完成 QEMU 对照。

（同文见 `.tao/knowledge/discussing.md` 2026-11-02「Tiny/Node 澄清与页大小」。）

## 性质：QEMU 实现缺陷修正，不是规范变更

- 规范早已钉死 64 KiB：`spec/DADAO-12 §2.2.2`「`VA[15:00]` 页内偏移 16 位，即 64 KiB」、`§2.2.4`「普通页 64 KiB，8×8 KiB fragment」；`.tao/contracts/contract-elf.md §5.3` `p_align` 目标默认 `0x10000`；`.tao/knowledge/MEMORY.md` 反套用清单「页大小 64 KiB，不是 4 KiB」。
- `TARGET_PAGE_BITS=12` 是从 `DADAO-0628` QEMU 骨架（RISC-V 血统）继承的实现缺陷，**不是 v5 规范**。
- 因此：**不新增 ADR、不改 `spec/`、不改 `.tao/contracts/`、不改 `contracts/`**。若执行中发现规范本身有歧义，按「失败处置」留问，不自行改契约。

## 问题根源（2026-11-02 现场核对）

1. 唯一硬编码：`.work/source/qemu/target/dadao/cpu-param.h:22` `#define TARGET_PAGE_BITS 12`；补丁镜像 `components/qemu/patches/target/dadao/cpu-param.h.patch:28` 同。
2. 该宏经 `include/exec/target_page.h` 派生全部 `TARGET_PAGE_SIZE/MASK/ALIGN`，影响两面：
   - **linux-user**：`page_set_flags`/`page_find_range_empty` 粒度；ELF 装载 `ELF_PAGESTART/PAGEOFFSET`、`imgsrc_mmap`、`zero_bss`、`info->brk = TARGET_PAGE_ALIGN`；`target_mmap`（host 4 KiB < target ⇒ `mmap_h_lt_g`）；`do_brk`；`setup_arg_pages`（guard 页）/`copy_elf_strings`（页缓冲）；`AT_PAGESZ`（`linux-user/elfload.c:702`）；`getpagesize` 系统调用（`linux-user/syscall.c:13289`）；`AT_BASE`/`AT_PHDR` 页对齐；`target_mprotect`/`target_munmap` 对齐检查；`TARGET_ARCH_HAS_SIGTRAMP_PAGE` 的 trampoline 页。
   - **softmmu**：`helper.c:868` `tlb_set_page(..., TARGET_PAGE_SIZE)`；`cpu.c` `translate_for_debug` 的 `lg_page_size`（3 处）；`system/physmem.c` 的 subpage 容器（`subpage_init` 以 `TARGET_PAGE_SIZE` 承载 <1 页 MMIO）；`rom_add_elf_program` 的 `romsize`。
3. 其余 DADAO 补丁无第二处页大小硬编码：`grep -rn "TARGET_PAGE_BITS" components/qemu/patches` 仅 `cpu-param.h` 1 行定义 + `cpu.c` 3 处派生使用。仓库内另有 1 处 4 KiB 假设在测试驱动 `tools/qemu/user_mode_smoke.py:498`（`base % 4096`）。
4. 现有工具链产物已符合 64 KiB（现场 `llvm-readelf -l`）：静态 `functional_argv.elf`、动态同款、`.work/source/musl/lib/libc.so` 的**所有** `PT_LOAD` 均 `Align 0x10000` 且 `p_offset ≡ p_vaddr (mod 0x10000)`；`e_entry` 不必页对齐（例 `0x21f40`）。
5. 系统态各物理区均 64 KiB 对齐（现场常量）：RAM `0xFC00_0000_0000`/16 MiB、ROM `0xFFFF_FFFC_0000`/256 KiB、pmem/hmon/smon host SRAM `0x0100_0000_{0000,0100,0200}_0000`/各 64 KiB、RAM alias `0`/16 MiB；当前机器无 <64 KiB MMIO 设备（exit-port 已删，halt 走 semihosting）。

## 参考对照（只读；内容溯源，非执行依赖）

- `DADAO-0628` `components/qemu/patches/0001-...-skeleton.patch` 写 `TARGET_PAGE_BITS 12`，而同系列 `0029` 又写 `cfx_tlb_addr_size = 65536`（自相矛盾）⇒ **不复用**；v5 以 `spec/DADAO-12 §2.2.2` 为唯一依据取 16。[内容溯源，非执行依赖]
- v5 自身无 `cfx_tlb_addr_size` 字段（PTW/TLB 按 ADR-0041 自建），不受该 0628 取值影响。
- 除上述两条外，本任务不从 0628 吸收任何代码/常量/地址，也不复制其补丁。

## 接口规范

### 输入

- QEMU 组件源树 `.work/source/qemu`（base+1 单提交、干净）与补丁集 `components/qemu/patches/**`。
- 现有工具链产物：`.dadao/cross-toolchain/bin/{clang,ld.lld,qemu-dadao,qemu-system-dadao}`、`.work/source/musl/lib/{crt1.o,libc.a,libc.so}`。
- 已核事实：所有工具链产出 ELF 的 `PT_LOAD` 为 `p_align=0x10000` 且偏移/地址同余。

### 输出

1. `.work/source/qemu/target/dadao/cpu-param.h`：`TARGET_PAGE_BITS 16`（`TARGET_VIRT_ADDR_SPACE_BITS` 保持 48，不动）。
2. `components/qemu/patches/target/dadao/cpu-param.h.patch`：由 `python3 tools/infra/make_patch.py qemu` 重导出（**禁手工编辑**）；源树收敛为 base+1 单提交。
3. 重建并安装的 `qemu-dadao` 与 `qemu-system-dadao`（安装根与 build 树逐字节一致）。
4. `tools/qemu/user_mode_smoke.py`：页对齐断言改 64 KiB，并新增 guest 页大小断言（见 D 节）。
5. `components/qemu/changelog.md` 的 M11 条目。
6. 证据脚本 + 日志 + 本任务书完成区（状态 `待验收`）。

### 约束

- 不改 `tests/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`gem5/**`、`components/{llvm-project,musl,picolibc,embench-iot,gem5}/**`、`Makefile`、`manifests/**`、`tools/testcases/**`。
- `tools/qemu/user_mode_smoke.py` 是 **QEMU 测试驱动**（非 `tests/**` 向量/期望值），属用户点名的「QEMU 测试驱动」审计面；只改页对齐/页大小断言，不改被测程序语义与既有期望输出。
- 只改 `cpu-param.h` 一处宏；审计中若确认 QEMU 源码另有 4 KiB 假设，**必须先给出现场与依据**再改，并在完成区逐条列出；不得顺手改无关代码。
- 测试资产（如 `p_align<0x10000` 的 ELF、按 4 KiB 写死的用例）若必须改 ⇒ 登记 BLOCKED 并另立任务，本任务不改。
- 还原纪律：任何注入/临时改动一律 `cp` 备份 + `md5sum -c` 还原；**禁** `git checkout`/`restore`/`stash`/`show <commit>:<path>`。
- 临时目录 `/tmp/opencode/QEMU-081t/`；仓库内不留临时/探针文件。

## 实施与审计清单

### A. 宏与补丁（唯一源码改动点）

1. 改前自检：`make check-source-state` ⇒ `qemu: OK HEAD=… count=1 clean=True`，记下旧 HEAD。
2. 改 `.work/source/qemu/target/dadao/cpu-param.h` 的 `12` → `16`（其余字符逐字不变）。
3. 收敛为 base+1：`git -C .work/source/qemu add target/dadao/cpu-param.h`；`git -C .work/source/qemu commit --amend --no-edit`（保留 `dadao: qemu patch series` 提交信息）；复跑 `make check-source-state` 为 OK。
4. 重导出：`python3 tools/infra/make_patch.py qemu`；期望仅 `cpu-param.h.patch` 被重写（`1 written, N unchanged`）。
5. 记录 `git -C .work/source/qemu diff <旧HEAD>..<新HEAD> --stat`：应为 `target/dadao/cpu-param.h | 2 +-`（1 行）；若审计要求追加改动，逐条列出理由。

### B. linux-user 影响面审计（逐项给「核对/实测」结论，不猜）

1. `AT_PAGESZ` 与 `getpagesize`：由 `TARGET_PAGE_SIZE` 派生 ⇒ 期望 65536；以 guest 探针实测（见验收 3）。
2. ELF 装载页粒度：`ELF_PAGESTART/PAGEOFFSET`、`imgsrc_mmap`（`vaddr_ps`/`p_offset-vaddr_po`）、`zero_bss`、`info->brk = TARGET_PAGE_ALIGN(range.hi+load_bias)`；判据 = 验收 3/4 的静态+动态装载与运行，且 `llvm-readelf -l` 复核 `p_align=0x10000`、同余。
3. `target_mmap`：host 4 KiB < target 64 KiB ⇒ `mmap_h_lt_g`；判据 = 匿名映射返回地址 `%65536==0`、`offset=4096` 返回 `EINVAL`（64 KiB 页语义）、`MAP_FIXED` 装载成功。
4. `do_brk`：`new_brk/old_brk` 均按 64 KiB 取整；判据 = 首个 `brk(0)` `%65536==0`，`brk(cur+1)` 后写 `ROUND_UP(cur+1,65536)-8` 成功（整页已映射；4 KiB 构建在此必然失败）。
5. 栈：`setup_arg_pages` guard 页 = 64 KiB、`STACK_LOWER_LIMIT = 32*TARGET_PAGE_SIZE`（2 MiB）、`copy_elf_strings` 64 KiB 页缓冲；判据 = 长 argv/env（合计 >100 KiB，跨页）长度/内容正确。
6. 信号 trampoline：`TARGET_ARCH_HAS_SIGTRAMP_PAGE` 分配的页变为 64 KiB；判据 = 一次 raise/catch 往返（信号 trampoline 可执行、`rt_sigreturn` 正常）。
7. 对齐/边界：`target_mprotect`/`target_munmap` 对非 64 KiB 对齐地址返回 `EINVAL`；`munmap(addr,1)` 长度上取整；判据 = 验收 3 的对应断言。
8. `probe_guest_base`：`align = MAX(SHMLBA, TARGET_PAGE_SIZE)` = 64 KiB；identity map 下 NULL 页 `[0,64K)` 与镜像 `[0x10000,…)` 相邻；判据 = 静态/动态 smoke 均能启动（必要时记录实际 `guest_base`）。

### C. softmmu 影响面审计（同一宏，系统态）

1. `tlb_set_page(..., TARGET_PAGE_SIZE)`：RAM/ROM/SRAM 基址+大小均 64 KiB 对齐；hmon/smon 映射的 `address`/`paddr` 低 16 位一致（host base 均为 64 KiB 对齐）。判据 = `check-inst-smoke`/`check-inst`/`check-arch-smoke` 全绿；不改代码。
2. subpage 机制：<64 KiB MMIO 由 `subpage_init` 以 64 KiB 容器承载；当前机器无此类设备。若 `check-arch-smoke` 暴露新设备跨越 64 KiB 页边界，记录并停下问（不在本任务新增设备适配）。
3. `translate_for_debug` 的 `lg_page_size=16`：semihosting 调试读写按 64 KiB 步进；判据 = `check-arch-smoke` 的 semihosting 用例。
4. 系统态 ELF/rom：`rom_add_elf_program` 的 `romsize` 取 `p_memsz`（不按页取整），段间不重叠判据仍按 `p_paddr` 区间；`-bios` 256 KiB、`-kernel` 载荷不受页大小影响。判据 = `check-inst` 全量通过。

### D. 测试驱动（QEMU 侧）

1. `tools/qemu/user_mode_smoke.py:498`：`base % 4096` → `base % 65536`。
2. 同文件新增断言：动态 `AT_BASE % 65536 == 0`；静态与动态各输出一次 `getauxval(AT_PAGESZ)`/`sysconf(_SC_PAGESIZE)` 期望 65536（可从被测程序源码派生，不得读 QEMU 日志反推）。
3. 不改 `HELLO_C` 等被测程序语义/既有期望输出；不改 `run_qemu_test.py`/`semantics_gate.py`（系统态，无页大小常量）。

### E. 不改清单

`tests/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`gem5/**`、`components/{llvm-project,musl,picolibc,embench-iot,gem5}/**`、`Makefile`、`manifests/**`、`tools/testcases/**`；`.tao/knowledge/discussing.md` 只由主会话修改。

## 验收标准

1. **宏与补丁**：
   - `grep -n "TARGET_PAGE_BITS" .work/source/qemu/target/dadao/cpu-param.h` ⇒ 仅 `#define TARGET_PAGE_BITS 16`；`grep -n "TARGET_PAGE_BITS" components/qemu/patches/target/dadao/cpu-param.h.patch` 同。
   - `make check-patch-tree` rc=0；`make check-source-state` rc=0（`qemu: OK HEAD=… count=1 clean=True`）。
   - `git -C .work/source/qemu diff <旧HEAD>..<新HEAD> --stat` 只含 `target/dadao/cpu-param.h`（+ 审计确认必须改的行，逐条给理由）。
2. **构建/安装**：`make build-qemu JOBS=8` rc=0；`make install-host` rc=0（若 rc=75 属 gate.lock 占用 ⇒ 等待重跑，不作通过）；`md5sum .work/build/qemu/qemu-dadao .dadao/cross-toolchain/bin/qemu-dadao` 两哈希一致，`qemu-system-dadao` 同。
3. **guest 可见页大小（用户态独立探针）**：静态 musl 程序（配方同 `tools/qemu/user_mode_smoke.py::compile_program/link_static`）逐项输出：
   - `syscall(SYS_getpagesize)` = **65536**；
   - `sysconf(_SC_PAGESIZE)` = **65536**；
   - `getauxval(AT_PAGESZ)` = **65536**；
   - `mmap(NULL,1,…)` 返回地址 `% 65536 == 0`；
   - 首个 `brk(0)` `% 65536 == 0`；`brk(cur+1)` 后写 `ROUND_UP(cur+1,65536)-8` 成功；
   - `mmap(fd, offset=4096)` ⇒ `-1/EINVAL`；`munmap(addr+4096,4096)` ⇒ `-1/EINVAL`；`munmap(addr,1)` ⇒ `0`；
   - 长 argv/env（>100 KiB，跨 64 KiB 页）长度/内容正确；
   - `qemu-dadao -strace` 中出现 `getpagesize() = 65536`。
   宿主 `getconf PAGESIZE` 是主机页（4 KiB），**不得**用作证据。
4. **静态/动态 smoke**：`python3 tools/qemu/user_mode_smoke.py --qemu .dadao/cross-toolchain/bin/qemu-dadao --work /tmp/opencode/QEMU-081t/smoke` rc=0；动态行 `AT_BASE % 65536 == 0`，`AT_PAGESZ` 断言通过。
5. **系统态回归**：`make check-inst-smoke` rc=0；`make check-inst` rc=0（全量 inst，用户点名的旧 `check-qemu-semantics`；属 L3 单目标，仅此一项）；`make check-arch-smoke` rc=0。
6. **L2 收尾**：`make check-modules` rc=0（含 `check-inst-smoke`/`check-arch-smoke`/`check-unit`/3 个 tset user-mode smoke）。任一红项须给出归因：若属测试资产按 4 KiB 写死 ⇒ 逐例登记 BLOCKED + 另立任务（保留现场）；若属 QEMU 实现 ⇒ 本任务修；既有红项附基线证据。**不得掩盖、不得为凑绿改范围外文件**。
7. **旧 4 KiB 残留扫描**：
   - `grep -rn "TARGET_PAGE_BITS 12" components/qemu/patches .work/source/qemu/target/dadao` ⇒ 0 行（rc=1）。
   - `grep -rn "4096\|0x1000" components/qemu/patches/{target/dadao,linux-user/dadao,hw/dadao} .work/source/qemu/{target/dadao,linux-user/dadao,hw/dadao} tools/qemu` ⇒ 命中逐条列出并分类；**与页大小相关者必须为 0**（`tools/qemu/user_mode_smoke.py` 的 `% 4096` 必须消失）。
   - `grep -rn "TARGET_PAGE_BITS" components/qemu/patches` ⇒ 仅 `cpu-param.h` 定义（16）+ `cpu.c` 3 处派生；无第二个定义。
8. **反例可达 FAIL（cp + md5，禁 git 还原）**：
   - 静态：把 `tools/qemu/user_mode_smoke.py` 的 `% 65536` 临时改回 `% 4096` ⇒ 证据脚本的源扫描断言 FAIL；`cp` 还原 + `md5sum -c` 后回绿。
   - 运行时：把 `cpu-param.h` 改回 12 → `make build-qemu JOBS=8` + `make install-host` ⇒ 探针 `getpagesize=4096`（或 `brk` 页尾写失败），证据脚本 FAIL；还原 16、重建、重装 ⇒ 回绿。两次构建各记 rc 与耗时。
9. **体例/台账**：`components/qemu/changelog.md` 在 `## M11` 下追加 `- **2026-11-02 \`QEMU-081t\`**` + `  - 摘要：…` + `  - 执行者：engineer`；`make check-component-changelog` rc=0；`make check-milestones-fresh` rc=0；`make check-tasks` rc=0；完成区 ≤30 行；状态 `待验收`。
10. **证据与诚实**：`.work/evidence/<任务ID>/run.sh` 一条命令重跑 1–9（逐条取命令自身 rc，禁 `| tee` 吞码），落 `run.EXIT`；日志按 `check-run-artifacts` A3 命名规则落 `.work/log/qemu/`；L1 `make check` 开工前记基线、收尾复跑，红项逐条给归因；**不跑整套 L3（`check-full`）与夜跑**（`check-inst` 单目标按验收 5 执行）；失败保留现场并按「失败处置」推进。

## 文件范围

- 允许：`.work/source/qemu/target/dadao/cpu-param.h`（组件工作树，非 v5 跟踪）、`components/qemu/patches/target/dadao/cpu-param.h.patch`、`components/qemu/changelog.md`、`tools/qemu/user_mode_smoke.py`、本任务书、`.tao/knowledge/milestones.md`、`.work/evidence/<任务ID>/`、`.work/log/qemu/`、`/tmp/opencode/QEMU-081t/`。
- 禁止：其余一切（尤其 `tests/`、`spec/`、`contracts/`、`.tao/contracts/`、`.tao/adr/`、`.tao/knowledge/discussing.md`、其它组件、`Makefile`、`manifests/`、`components/qemu/series`）。

## 下发前预检（5 项，现场核）

1. **任务书内部一致**：宏一处、补丁一份、验收 1–10 与文件范围一一对应；编号 `QEMU-081` 未被占用（`.tao/tasks/qemu/` 最大 `QEMU-078t`，`archive/**` 无 081）。
2. **验证前置可用**：`.work/source/qemu` 在位、`clean=True count=1`；`tools/infra/make_patch.py` 可跑；`make build-qemu`/`install-host` 目标存在；安装根已有两二进制（11-02 08:26）；clang/ld.lld/musl 产物在位；`tools/qemu/user_mode_smoke.py` 可跑。
3. **验收逐条可跑性**：1/7/8/9/10 现在可跑；2–6 需先构建/安装（预计增量 5–20 min，视头文件依赖面）；不跑整套 L3（`check-full`）/夜跑，`check-inst` 单目标按验收 5。
4. **与 `contracts/`、工具链产物一致**：零改动；已核三例 ELF 的 `p_align=0x10000` 且偏移/地址同余。
5. **拟改文件 × `spec/` 清单**：全部不在 `spec/` ⇒ **无命中、无 BLOCKED**；`tools/qemu/user_mode_smoke.py` 非 `tests/**`，属测试驱动。

## 风险

- **R1 手编补丁**（禁止）⇒ 必须走 `make_patch.py`；导出后红则按 `docs/Process-01 §6.4` 收敛后重导。
- **R2 源树变脏**：改完未提交即跑 `--source-state` 必红 ⇒ 先收敛再自检。
- **R3 构建耗时/失败**：`cpu-param.h` 依赖面大，重编可能接近全量；`install-host` 若被无关前置阻断，保留现场、报告，不手拷二进制（ISS-300）。
- **R4 同文件并行**：`QEMU-079t`/`080t` 若开工，`cpu-param.h` 串行；合并顺序以本任务为先。
- **R5 测试资产 4K 假设**：L2 tset 若因用例写死 4 KiB 失败 ⇒ 逐例 BLOCKED + 另立任务，不改资产。
- **R6 系统态隐藏页假设**：若 `check-inst`/`check-arch-smoke` 暴露 <64 KiB 区域/跨页 MMIO ⇒ 记录并停下问，不擅自扩范围。
- **R7 基线红**：L1/L2 开工前的既有红须记录，收尾不得新增。
- **R8 相邻但不同的问题**：`TARGET_VIRT_ADDR_SPACE_BITS=48` 与 DADAO 规范 VA 42 位的差异不属本任务（保持现值）；若探针/ELF 装载暴露它，登记 issue 并另立任务，不在本任务改。

## 完成区

**测试结果**：`.work/evidence/QEMU-081t/run.sh` **rc=0（34/34）**；`run.sh --inject` **rc=0（8/8）**；探针 **27/27**；user smoke **55/55**；`check-inst-smoke`/`check-inst`/`check-arch-smoke`/`check-modules` 全 rc=0。耗时：首次 `build-qemu JOBS=8` 164 s、`install-host` 83 s；注入 12 位重建 32 s/装 441 s、还原 16 位重建 11 s/装 60 s（均 rc=0，含 gate.lock 排队）；full run 549 s（首轮 1917 s，含排队）。
**修改文件**：`components/qemu/patches/target/dadao/cpu-param.h.patch`（12→16，`make_patch.py` 重导出，1 written/62 unchanged）；`tools/qemu/user_mode_smoke.py`（`% 4096`→`% PAGE_SIZE`、新增静态/动态页大小断言、`link_static` 补 compiler-rt builtins）；`components/qemu/changelog.md`（M11 条目）；`.tao/knowledge/milestones.md`；本任务书。组件工作树 `.work/source/qemu/target/dadao/cpu-param.h`（非 v5 跟踪，base+1 clean）；证据 `.work/evidence/QEMU-081t/**`、日志 `.work/log/qemu/QEMU-081t-*.log`。
**验收结果**：
1. 宏/补丁：源与补丁各恰 1 行 `TARGET_PAGE_BITS 16`、0 行 12；`check-source-state` rc=0（HEAD=base+1 clean）；pre-change blob 比对=「仅 12→16 一行」且 `git diff <旧HEAD>..<新HEAD> --stat` = `cpu-param.h | 2 +-`；`check-patch-tree` 全量仅 gem5 红（外部），qemu 作用域（同一 checker 代码）63 patches rc=0。
2. 构建/安装：`build-qemu JOBS=8`、`install-host` rc=0；`qemu-dadao`/`qemu-system-dadao` 的 build 树与安装根 md5 逐一致（`fd0ee3d1…` / `47729506…`）。
3. 静态探针：`getpagesize`/`sysconf(_SC_PAGESIZE)`/`getauxval(AT_PAGESZ)`=**65536**；`mmap(NULL,1)` 64 KiB 对齐；`sbrk(0)`=0x50000（64 KiB 对齐）+ `brk(cur+1)` 后页尾 8 B 写成功；`mmap(offset=4096)`⇒`-1/EINVAL`；`munmap(addr+4096,4096)`⇒`-1/EINVAL`；`munmap(addr,1)`⇒0；argv 120000 B + env 40000 B（跨页）长度/校验和/首末字节全对；SIGUSR1 raise/catch 往返（sigtramp 64 KiB）；`guest_base=0x0` 且 `%65536==0`。**两条 N/A（需裁定）**：本 ABI 无 getpagesize 系统调用，`syscall(SYS_getpagesize)` 与 `-strace getpagesize() = 65536` 不可表达（已机械断言 syscall.tbl/musl syscall.h.in 均无该项）。
4. 静态+动态 smoke：`user_mode_smoke.py` rc=0（55/55），`AT_BASE % 65536 == 0`，静态/动态三条页大小查询均 65536。
5. 系统态：`check-inst-smoke`、`check-inst`（全量 inst）、`check-arch-smoke` 全 rc=0。
6. L2：`check-modules` rc=0。
7. 残留：`TARGET_PAGE_BITS 12` 0 行；页大小相关 `\b(4096|0x1000)\b` 0 处；`TARGET_PAGE_BITS` = 1 定义 + 3 派生使用。
8. 注入（cp+md5，禁 git 还原）：静态 `% 4096` ⇒ 残留扫描 FAIL（打印 `user_mode_smoke.py:571`）⇒ 还原回绿；运行时 12 位 ⇒ 探针 rc=1（`getpagesize=4096`、`sysconf=4096`、`AT_PAGESZ=4096`、`mmap_align=40960`、`brk_align=61440`）⇒ 还原 16 位 ⇒ 27/27 回绿；`cpu-param.h` md5 `a37946f7…`、补丁 md5 `2115509c…` 与注入前备份逐字节相同。
9. 台账：changelog `## M11` 追加条目；`check-component-changelog`/`check-milestones-fresh`/`check-tasks` rc=0；状态 `待验收`。
10. 证据/诚实：`run.sh` 一条命令覆盖 1–9，逐条捕命令自身 rc（无 `tee`）；L1 开工基线 rc=2（26 项全为 gem5）、收尾复跑 rc=2（27 项全为 gem5，GEM5-014t 仍在改共享源，无本任务新增红）；未跑 `check-full`/夜跑。
**新发现/坑**：(a) 页大小只能用 `AT_PAGESZ` 观察——DADAO ABI 取 asm-generic，无 getpagesize（QEMU 的 `TARGET_NR_getpagesize` 分支被 `#ifdef` 掉）；(b) musl 端口 `brk()/sbrk(inc)` 是 `-ENOMEM` 桩，堆须用裸 `brk`(nr 214) 验；(c) musl 重建后 libc.a 的 printf 引 binary128 助手，`link_static` 原配方缺 compiler-rt builtins ⇒ 含 printf 的被测程序一律链不上（基线红、非本任务引入），已按 `run_clmul_probe.py` 同款 `--start-group libc.a builtins --end-group` 修正（不改被测程序语义/期望输出）；(d) `.work` 是主工作树软链，证据脚本 `Path(__file__).resolve()` 会导错到主树 `tools/qemu`，改用 `git rev-parse --show-toplevel`；(e) `physical_memory_set_dirty_lebitmap` 的 `hpratio=host/target` 在 4 KiB host 下为 0，但仅 KVM/MSHV/VFIO 调用，TCG 不经过，记录不改。
**遗留问题**：① **BLOCKED（验收手段，待裁定）** 验收 3 的 `syscall(SYS_getpagesize)`/`-strace getpagesize()` 两项不可达（证据见「新发现 a」），已用 `AT_PAGESZ` 等价三路覆盖，是否改写该验收条目由主会话/用户裁定。② 外部红：`make check-patch-tree` 全量因 **gem5** 断言⑥⑨ 红（GEM5-014t 在改共享 `.work/source/gem5`；开工基线同红、非本任务引入），qemu 作用域复核 rc=0，待其合入后自愈。③ 观察（禁改范围）：`tests/shared/runtime/dadao_user_dyn_probe.c:54` 的 `AT_BASE % 4096` 仍在（弱断言，64 KiB 下仍成立，属测试资产）。
**收尾记录（2026-11-03 04:20，architect）**：reviewer 第 1 轮 **Accepted**；收尾只改「状态→已验证 + 本节两行 + milestones 流水状态/时间」，既有正文与审阅记录原文未改；不提请 merge/push（由主会话 `/complete` 后 `merge --squash`）。
**收尾遗留（reviewer findings ①–⑤，原文见第 1 轮 reviewer 验收，不改其文字）**：① 完成区 `user_mode_smoke.py:571` 现场实为 572（笔误，不影响结论）；② 注入态 `mmap_align=40960` 是当时值、reviewer 实测 28672（运行时变化，`brk_align=61440` 一致）；③ `run.sh` 对 `check-source-state` 未做外部归因分类，共享树并发改脏时整轮红（第 1 轮实证）⇒ 是否补分类待裁定；④ 验收 3 的 `syscall(SYS_getpagesize)`/`-strace getpagesize()` 两项 BLOCKED，改判据待裁定；⑤ `--inject` 的 `--amend` 使 qemu HEAD `f98216a→37b8590→c90144f`、二进制 md5 `fd0ee3d1…→c6f0689a…`（build==install 判据仍成立、源树仍 base+1 干净）。

## 审阅记录

#### 第 1 轮 engineer 自审

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1. 证据脚本 diffstat 断言用 `git diff HEAD~1 HEAD`，而 `HEAD~1` 是 upstream base（base+1 流程下无「变更前提交」） | ✅已修 | 改为「pre-change blob（`cpu-param.h.pre`）逐字符比对 + `git diff <旧HEAD>..<新HEAD>`」双证 | 全量 run：`current cpu-param.h == pre-change blob + the single 12 -> 16 edit`、`old-HEAD..new-HEAD diff stats only cpu-param.h (2 +-)` 均 PASS |
| 2. 证据/探针脚本用 `Path(__file__).resolve().parents[3]`：`.work` 是主工作树软链 ⇒ 解析到主树，导入**主树未改版** `tools/qemu/user_mode_smoke.py`（症状：builtins 缺失、`% 4096` 假差异） | ✅已修 | 两脚本改用 `git rev-parse --show-toplevel`；`run.sh` 先 `cd` 到本 worktree 根 | 探针在改后 27/27，smoke 55/55 |
| 3. 验收 3 的 `syscall(SYS_getpagesize)` 在本 ABI 不存在（编译失败：`use of undeclared identifier`） | ✅已修 + 登记 BLOCKED | 改 `getpagesize()`/`sysconf(_SC_PAGESIZE)`（musl 两者均取 `libc.page_size`←`AT_PAGESZ`）；脚本内加「syscall.tbl / musl syscall.h.in 均无 getpagesize」机械断言 | `probe getpagesize/sysconf/at_pagesz=65536`；`DADAO syscall table has no getpagesize` PASS；遗留问题 ① |
| 4. musl 端口 `brk()`/`sbrk(inc)` 是 `-ENOMEM` 桩 ⇒ 首版 `brk(0)` 取值错（打印 65535、`brk_failed=1`） | ✅已修 | 用 `sbrk(0)` 读当前 break、裸 `brk`（nr 214，asm-generic）扩展堆 | `brk_addr=0x50000`、`brk_align=0`、`brk_tail_write=1` |
| 5. 探针输出解析把 `a=1 b=2` 整行当值 ⇒ 多条断言假 FAIL | ✅已修 | 按空白切 token 再 `split("=",1)`；`want()` 统一 `str(expected)` 比较 | `munmap_*`/`argv_*`/`env_*`/`signal_got` 全 PASS |
| 6. 首次 full 试跑 rc=2（`syntax error near unexpected token '('`）：**运行中编辑了 run.sh**，bash 按字节偏移续读 | ✅已确认（非逻辑缺陷） | 最终跑前冻结脚本；后续 run 全部在脚本稳定后启动 | 改后 `bash -n` + 全量 run rc=0（34/34） |
| 7. 早期自建 `.work/log/qemu/QEMU-081t-*.EXIT` 不符 `check-run-artifacts` A3 命名（只允许 `.log/.json/.txt`） | ✅已修 | 删 `.EXIT` 文件，内容汇总进 `.work/evidence/QEMU-081t/builds.txt` | `ls .work/log/qemu/QEMU-081t-*` 仅 `.log`；A3 规则逐条核对 |
| 8. 范围披露：`link_static` 补 compiler-rt builtins 超出「只改页对齐断言」 | ✅已修（必要） | 按 `tools/testcases/run_clmul_probe.py` 同款 `--start-group libc.a builtins --end-group`；未改被测程序语义/既有期望输出 | 修复前 `ld.lld: undefined symbol __eqtf2`；修复后 smoke 55/55（基线红，非本任务引入） |
| 9. 记录不改项：`physical_memory_set_dirty_lebitmap` 的 `hpratio=host/target`（4 KiB host ⇒ 0） | ❌不修（记录） | 仅 KVM/MSHV/VFIO 调用，TCG（qemu-system-dadao 唯一加速器）不经过 | `grep` 调用点只有 `accel/{kvm,mshv}` 与 `hw/vfio` |
| 10. 记录不改项：`tests/shared/runtime/dadao_user_dyn_probe.c:54` 的 `AT_BASE % 4096` | ❌不修（禁改范围） | 测试资产不在本任务范围；64 KiB 对齐是其更强条件，断言仍成立 | 全量 run 里该文件未参与；已登记遗留 ③ |

判决：finding 1–8 已修并复验，9–10 为记录项（无缺陷），无未修 finding ⇒ 状态置 `待验收`。

#### 第 1 轮 reviewer 验收

重跑记录（全部由 reviewer 在本 worktree 亲自执行，rc 取命令自身，非采信完成区）：
- `run.sh` 第 1 轮 **33/34 rc=1**：唯一 FAIL `make check-source-state rc=2`，日志 `qemu: OK HEAD=37b8590 count=1 clean=True` / `gem5: FAIL … M src/arch/dadao/process.cc`（GEM5-014t 并发改共享 `.work/source/gem5`）⇒ 环境并发、非本交付物；随即直跑 `make check-source-state` **rc=0**。已记为重跑第 1 次（未掩盖根因）。
- `run.sh` 第 2 轮、以及注入还原后的第 3 轮均 **34/34 rc=0**：`check-source-state 0`、`check-patch-tree rc=2`（26 problem **全 gem5**，非 gem5 行 grep rc=1）、qemu 作用域 `1 component, 63 patches OK rc=0`、`build-qemu 0`/`install-host 0`、build 树==安装根 md5 逐一致、探针 **27/27**、smoke **55/55**（`AT_BASE % 65536=0`、静态/动态 `getpagesize/sysconf/AT_PAGESZ=65536`）、`check-inst-smoke 0`（90/90）、`check-inst 0`（1007/1012，5 deferred 已登记）、`check-arch-smoke 0`（10/10 + 25 svc）、`check-modules 0`、残留扫描与 changelog/milestones/tasks 三门控全 0。
- `run.sh --inject` **8/8 rc=0**：静态注入命中 `tools/qemu/user_mode_smoke.py:572` 并被残留扫描抓出；12 位重建重装后探针 **rc=1**（`getpagesize/sysconf/at_pagesz=4096`、`brk_align=61440`）；还原 16 位重建重装后探针 rc=0；两文件 `md5sum -c` OK。
- **reviewer 独立反例（与 engineer 两次注入不同）**：只改补丁镜像 `cpu-param.h.patch` `16→12`、源树保持 16 ⇒ 全量 `run.sh` **31/34 rc=1**（FAIL×3：`scan_macro`、qemu 作用域 `check-patch-tree rc=1` 断言⑥⑨、`TARGET_PAGE_BITS 12 still present`）；`cp` + `md5sum -c` 还原为 `2115509c…`（与备份逐字节一致）⇒ 回绿 **34/34 rc=0**。全程未用 `git checkout/restore/stash`。
- 另直跑：`make check`(L1) **rc=2**、26 problem 全 gem5、无其它 FAIL（同 engineer 基线 26 / 收尾 27 全 gem5）；`check-inst-smoke` **rc=0**、`check-arch-smoke` **rc=0**、`check-inst` **rc=0**、`check-modules` **rc=0**；`check_run_artifacts.py --self-test` rc=0。

约束核验：
- 宏/补丁：源与补丁各恰 1 行 `TARGET_PAGE_BITS 16`、0 行 12；补丁 `+` 正文与 `cpu-param.h` 25 行逐行相等；`f98216a..HEAD --stat` 仅 `cpu-param.h | 2 +-`；pre-change blob 与旧 HEAD blob md5 同（`c801ad0c…`）；源树 base+1、`git status` 干净。
- 残留：`grep -E '\b(4096|0x1000)\b'` 在 patches/源树三目录 + `tools/qemu` **0 命中**；smoke 已无 `% 4096`（改 `% PAGE_SIZE`，`PAGE_SIZE=1<<16` 独立于 QEMU 推导）。
- `getpagesize` 不可达且非静默跳过：`linux-user/dadao/syscall.tbl`、musl `arch/dadao/bits/syscall.h.in`、host `asm-generic/unistd.h` 均无该号，build 树无 `TARGET_NR_getpagesize`，QEMU `syscall.c:13289` 分支被 `#ifdef` 掉；musl `getpagesize()/sysconf(_SC_PAGESIZE)` 均取 `libc.page_size ← aux[AT_PAGESZ]`，另有 `AT_PAGESZ`/mmap 对齐/brk 对齐/EINVAL 等纯 QEMU 行为断言 ⇒ 验收 3 两小条确属 BLOCKED（已登记待裁定）。
- `link_static` 补 builtins **必要**：reviewer 实测 `be/errno_rd8/enosys_rd8/ioctl_mask/pagesz/probe` 不带 builtins 全部 `undefined symbol: __eqtf2`，带 builtins rc=0 且同用例两版 ELF 字节相同 ⇒ 不改被测程序语义/期望输出；musl 产物 mtime 11-02 09:41（开工前）⇒ 属基线红。
- 范围/体例：`git status` 仅完成区声明的 5 个文件，未碰 `tests/ spec/ contracts/ .tao/contracts/ gem5/ Makefile manifests`；reviewer 未写主工作树（期间主会话自行新增 QEMU-079t/080t 与 milestones 改动，非本任务产物）；完成区 17 行（≤30）、自审段 18 行（≤40）；`.work/log/qemu/QEMU-081t-*` 全为 `.log`，仓库无 `*_tmp*`/`.orig`/`.rej`/备份残留。

判决：**Accepted**。finding（交 architect 收尾处置，不改本判决）：① 完成区 `user_mode_smoke.py:571` 现场实为 **572**；② 完成区注入 `mmap_align=40960`，reviewer 实测 **28672**（运行时变化，`brk_align=61440` 一致）；③ `run.sh` 对 `check-source-state` 未做外部归因分类（`check-patch-tree` 有）⇒ 共享树被并发改脏时整轮红（第 1 轮实证），是否补分类待裁定；④ 验收 3 的 `syscall(SYS_getpagesize)`/`-strace getpagesize() = 65536` 须裁定改写；⑤ `--inject` 的 `--amend` 循环使 qemu HEAD `f98216a→37b8590→c90144f`、二进制 md5 变为 `c6f0689a…`（完成区 `fd0ee3d1…` 为当时值），判据 build==install 仍成立、源树仍 base+1 干净。
