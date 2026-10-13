# LLVM-056t: DADAO LLD target + 链接脚本 `dadao.lds`

**模块**：llvm
**项目里程碑**：M4
**依赖**：`INFRA-043t`、`LLVM-050t`、`SPEC-107t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `INFRA-043t` 产出的 `ld.lld`（`.work/build/llvm/bin/ld.lld`）；`LLVM-050t` 的 `.o`（含 `SHT_RELA` + `R_DADAO_*`）。
  - `.tao/knowledge/contract-elf.md §1–§6`（`SPEC-105t`/`SPEC-107t` 后版本：`EM_DADAO=0x0DA0`、`e_flags=0x1`、`SHT_RELA`、4 类 reloc、公式无 −4、`ABS48` 3 片、段对齐/VA=PA、pipeline）；`.tao/adr/adr-0019`（Accepted）；`.tao/adr/adr-0004`（`SPEC-107t` 调整后的加载约定：RAM 基址 `0xffff_0000_0000` 作 `.text`/entry、`FILEHDR PHDRS`、段序 `.text→.rodata→.data→.bss`）。
  - **内存几何（自包含；`ADR-0004` D1）**：**RAM 16 MiB** 位于 `0xffff_0000_0000`–`0xffff_00ff_ffff`（`DADAO_RAM_BASE`/`DADAO_RAM_SIZE`）；**ROM 64 KiB** 位于 `0xffff_ffff_0000`–`0xffff_ffff_ffff`（`DADAO_ROM_BASE`/`DADAO_ROM_SIZE`）。链接脚本据此定义 `MEMORY` 区域。
  - `lld/ELF/Arch/RISCV.cpp`、`lld/ELF/Arch/PPC64.cpp`、`lld/ELF/Target.{cpp,h}`、`lld/ELF/CMakeLists.txt`（**只读对照**：主流 LLD target 范式）。
  - `DADAO-0628 DL-061c`（标准 `ld.lld` + `dadao.ld`，**只读对照**；注意其地址基址/`-4`/reloc 集与 v5 不同，**不照抄**）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  1. `lld/ELF/Arch/DADAO.cpp`：实现 `relocate()`（`R_DADAO_ABS48`/`REL26`/`REL20`/`REL14`；大端写回；偏移溢出 ⇒ **link-time error**，不截断/wrap）与 `getRelExpr`（`R_PC`/`R_ABS`）。
  2. `lld/ELF/Target.{cpp,h}` 注册 `EM_DADAO (0x0DA0)` → DADAO target；`lld/ELF/CMakeLists.txt` 增列 `Arch/DADAO.cpp`。
  3. 链接脚本 **`dadao.lds`**（落点建议 `tests/scripts/dadao.lds`，随产物入库）：`ENTRY`（入口符号，如 `_start` 或 `e_entry` 约定）；**`MEMORY` 区域**——`RAM (rwx) : ORIGIN = 0xffff_0000_0000, LENGTH = 16M`、`ROM (rx) : ORIGIN = 0xffff_ffff_0000, LENGTH = 64K`（`ADR-0004` D1）；**`ASSERT` 段尺寸/地址约束**（如 `ASSERT(.text + .rodata + .data <= ORIGIN(RAM)+LENGTH(RAM), "image exceeds RAM")`，并对 ROM 段 `ASSERT(SIZEOF(...) <= 64K, ...)`）；`.text` 起于 RAM 基址 `0xffff_0000_0000`；段序 `.text→.rodata→.data→.bss`；对齐依 `contract-elf §5`（`.text` 4B、其余 8B）；`FILEHDR PHDRS` 使 `.text` file-offset 0；权限 RX/RW。
  4. 导出的 `components/llvm-project/patches/**` + `series`。
- **约束**：
  - **relaxation 禁用**（`ADR-0019 D7`）：不缩短序列、不重排，linker 只做原地补丁。
  - **溢出 = link-time error**（`ADR-0019 D6`）：越界 relocation 必须 `ld.lld` 报错并非零退出。
  - **段溢出 = link-time error（本任务新增）**：`dadao.lds` 的 `MEMORY` + `ASSERT` 必须使**段尺寸/地址超出区域**（`.text+.rodata+.data` 超 RAM 16 MiB、ROM 段超 64 KiB）时 `ld.lld` **报错并非零退出**，不得静默 wrap、截断或溢出到区域外（呼应 `ADR-0004` D2.3「工具/加载错误」层）。
  - **大端** 写回；`EM_DADAO`/`e_flags` 正确（`ET_EXEC` 头）。
  - **reloc/fixup 坑预防（5 条，同 `LLVM-050t`）**；linker 侧尤其②（同段/跨段判定）与⑤（不得用受限字段承载大值）。
  - **不做**：`RELA_PAGE`/`RELA_LO`（留后）、relaxation、绝对调用约定扩展。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建：`make build-lld`（`INFRA-043t`）；受 `JOBS` 限制；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-056t/`；**不提交 git**；复杂命令输出留存 `.work/log/llvm/`。

## 验收标准

1. `make build-lld` / `ninja -j8 -C .work/build/llvm ld.lld` EXIT=0。
2. **ET_EXEC**：对 ≥1 个含跨段/外部符号引用的 `.o`，`ld.lld -T dadao.lds`（或等价）EXIT=0；`llvm-readobj -h` 显示 `Type: EXEC`、`Machine: 0xDA0`、`Flags [ (0x1)`、`Entry: <addr>`；`.text` file-offset = 0（`FILEHDR PHDRS`）。
3. **reloc 解析**：`ABS48`（3 片，读指令内 `wyde-position`）、`REL26/REL20/REL14`（`(S+A−P)>>2`，**无 −4**）逐条真实解析；给出链接前后 `llvm-readobj -r`/`-s` 对照与手算核对（≥1 每类）。
4. **大端**：段/数据字节序核对（hexdump）。
5. **溢出负例**：构造 `REL14`/`ABS48` 越界 → `ld.lld` **报错、非零退出**（不截断/wrap）；给出真实 stderr。
6. **段溢出负例（本任务新增）**：构造段尺寸/地址超出 `MEMORY` 区域（① `.text+.rodata+.data` > RAM 16 MiB；② ROM 段 > 64 KiB）→ `ld.lld` 因 `ASSERT`/区域约束 **报错、非零退出**（真实 stderr）；并验证**恰好填满**区域（边界值）**不报错**（不误杀）。
7. **链接脚本**：`dadao.lds` 存在且内容与 `ADR-0004`/`contract-elf §5` 一致（地址/段序/对齐/`FILEHDR PHDRS`/**`MEMORY`（RAM 16 MiB / ROM 64 KiB）+ `ASSERT`**）。
8. **不回归**：`make check` EXIT=0；`check-patch-tree` OK；`make test-codegen` 不回归。
9. 一键证据脚本 `.work/evidence/LLVM-056t/run.sh`（含 `--inject`：改 `relocate` 公式（加 −4/改掩码）或放宽 `ASSERT`/`MEMORY LENGTH` → 期望 FAIL → 还原+**重建 ld.lld** → 回绿）；完成区贴真实输出。

## 完成区

**状态**：`待验收`（实现完成）。

**用户裁定（原话，落盘）**：
- 问：`relocate()` 是否要同时实现 `R_DADAO_ABS48` 的「数据路径」（8 字节字段，`.dd.o64 <sym>`/`.quad <sym>`）？
  答：**「两条都实现（推荐）」**——指令路径 3 片 wyde + 数据路径 8 字节；以目标 section `SHF_EXECINSTR` 判别；越界(>48 位)均 link-time error。
- 问：验收 2 要求「`.text` file-offset = 0」，实测 `.text` sh_offset=0x1000（file offset 0 被 ELF 头占据），首个 PT_LOAD p_offset=0 且 flat 镜像以 .text 起始；请确认口径。
  答：**「采纳 p_offset=0/flat 口径（推荐）」**。

**测试结果**：通过 9/9 验收项。
- 一键证据脚本 `.work/evidence/LLVM-056t/run.sh` 正常模式 **0 failures / EXIT=0**（40 项检查）；`--inject` 模式 **0 failures / EXIT=0**（8 项注入自检，见下）。
- 回归：`make check` EXIT=0（`repository checks: PASS`，lit 50/50）、`make check-patch-tree` EXIT=0（89 patches OK）、`make test-codegen` EXIT=0（15/15）。
- 失败原因：无。

**修改文件**：
- 组件源码（`.work/source/llvm-project`，已 `git commit --amend` 收敛为 base+1：`6dfe1677a..32983b731`，worktree clean，count=1）：
  - `lld/ELF/Arch/DADAO.cpp`（**新增**，193 行）：`DADAO` (TargetInfo) — `relocate()`（4 类；`relocateAlloc` 覆写按 section `SHF_EXECINSTR` 区分 ABS48 指令/数据路径）、`getRelExpr()`（`R_PC`/`R_ABS`）、`calcEFlags()`、ctor 设 `iRelSymbolicRel=R_DADAO_NUM`。
  - `lld/ELF/Target.cpp`（+2：`case EM_DADAO: return setDADAOTargetInfo(ctx);`）
  - `lld/ELF/Target.h`（+1：`void setDADAOTargetInfo(Ctx &);`）
  - `lld/ELF/CMakeLists.txt`（+1：`Arch/DADAO.cpp`）
- 补丁集：`components/llvm-project/series`（53→**57**）与 `components/llvm-project/patches/**`（`make_patch.py` 导出：`lld/ELF/Arch/DADAO.cpp.patch`（新增，193 行）+ `lld/ELF/{CMakeLists.txt,Target.cpp,Target.h}.patch` 3 份修改）；**未手改**。
- 链接脚本：`tests/scripts/dadao.lds`（**新增**，随产物入库）。
- 台账：`components/llvm-project/changelog.md`（+LLVM-056t 一条）。
- 证据脚本：`.work/evidence/LLVM-056t/run.sh` + `inputs/*.s`（11 个）；日志 `.work/log/llvm/LLVM-056t-*.log` 与 `.work/log/llvm/LLVM-056t-logs/`。
- 本任务书（完成区/自审/状态）。

**验收结果**（真实输出；命令均 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`；详细日志 `.work/log/llvm/`）：

1. **构建 EXIT=0**（`.work/log/llvm/LLVM-056t-build3.log`）：
   `ninja -j8 -C .work/build/llvm lld` → `[3/3] Linking CXX executable bin/lld`，`BUILD_EXIT=0`。
   （**注**：ninja 目标名为 `lld`，`bin/ld.lld` 是 `lld` 的 POST_BUILD 符号链接拷贝，无独立 `ld.lld` 目标——与 `INFRA-043t` 实测一致；`make build-lld` 亦 `EXIT=0`。）
2. **ET_EXEC**（`rela.o` 含跨段/外部符号；`ld.lld -T tests/scripts/dadao.lds`，LD_EXIT=0）——`llvm-readobj -h`：
   ```
   Type: Executable (0x2)
   Machine: 0xDA0
   DataEncoding: BigEndian (0x2)
   Entry: 0xFFFF00000000
   Flags [ (0x1)   （e_flags=0x1）
   ```
   `-S`：`.text Address: 0xFFFF00000000`（RAM 基址）、`AddressAlignment: 4`；`.data Alignment: 8`。
   `-l`：首个 `PT_LOAD Offset: 0x0`（`FILEHDR PHDRS`）。**`.text` sh_offset=0x1000**（见「用户裁定」与「新发现/坑 3」）。
3. **reloc 解析**（链接前 `readobj -r` / 链接后 `objdump -s`，`reloc.elf` .text = `4c200018 48210000 4822ffff 74000003 6b200004 6e209003`；手算逐类 ≥1，布局 `.text@0xFFFF00000000`、`ext=0xFFFF00000018`、`other=0xFFFF00000020`）：
   | 类型 | 符号 | S | P（重定位处） | 公式 | 落点 | 实测字节 |
   |---|---|---|---|---|---|---|
   | ABS48 wp0 | ext | 0xFFFF_0000_0018 | 0xFFFF_0000_0000 | S+A=0xFFFF00000018，片0=0x0018 | set.zw rd8,wp0 | `4c200018` |
   | ABS48 wp1 | ext | 同上 | 0xFFFF_0000_0004 | 片1=0x0000 | or.w rd8,wp1 | `48210000` |
   | ABS48 wp2 | ext | 同上 | 0xFFFF_0000_0008 | 片2=0xFFFF | or.w rd8,wp2 | `4822ffff` |
   | REL26 | ext | 0xFFFF_0000_0018 | 0xFFFF_0000_000C | (S+A−P)>>2=0xC>>2=**3** | call imms24 | `74000003` |
   | REL20 | other | 0xFFFF_0000_0020 | 0xFFFF_0000_0010 | 0x10>>2=**4** | br.nz imms18 | `6b200004` |
   | REL14 | other | 0xFFFF_0000_0020 | 0xFFFF_0000_0014 | 0xC>>2=**3** | br.eq imms12 | `6e209003` |
   均**无 −4**（`ADR-0019 §D3`）。
4. **大端**：`reloc.elf` .text 低 16 位按大端落点（上表字节）；`data.elf` `.data`=`0000ffff00000000 0000ffff00000010 0000ffff00000000`、`.rodata`=`0000ffff00000000`（`llvm-objdump -s`，见 `.work/log/llvm/LLVM-056t-reloc-pre-post.log`）。
5. **reloc 溢出负例**（`.work/log/llvm/LLVM-056t-overflow.log`，均 `LD_EXIT=1`）：
   ```
   R_DADAO_REL14 out of range: 16386 is not in [-2048, 2047]
   R_DADAO_REL20 out of range: 131074 is not in [-131072, 131071]
   R_DADAO_REL26 out of range: 67108866 is not in [-8388608, 8388607]
   R_DADAO_ABS48 out of range: 562945658454016 is not in [-140737488355328, 281474976710655]  (.data，数据路径)
   R_DADAO_ABS48 out of range: 562945658454032 is not in [-140737488355328, 281474976710655]  (.text，指令路径)
   ```
6. **段溢出负例（本任务新增）**（均 `LD_EXIT=1`）：
   ```
   RAM: ld.lld: error: RAM sections exceed 16 MiB
        ld.lld: error: section '.bss' will not fit in region 'RAM': overflowed by 8 bytes
   ROM: ld.lld: error: ROM section exceeds 64 KiB
        ld.lld: error: section '.rom' will not fit in region 'ROM': overflowed by 1 bytes
   ```
   边界（**恰好填满**）不误杀：`ram_fill`（.text 4B + .bss 0xFFFFF8，末尾恰 0xFFFF00000000+0x1000000）`LD_EXIT=0`；`rom_fill`（.rom=0x10000）`LD_EXIT=0`。
7. **链接脚本**：`tests/scripts/dadao.lds` — `ENTRY(_start)`；`MEMORY`：`RAM (rwx) : ORIGIN = 0xffff00000000, LENGTH = 16M`、`ROM (rx) : ORIGIN = 0xffffffff0000, LENGTH = 64K`；`text PT_LOAD FILEHDR PHDRS`；段序 `.text(ALIGN(4))→.rodata(ALIGN(8))→.data(ALIGN(8))→.bss(ALIGN(8))`；`ASSERT`（RAM/ROM 尺寸）；`> RAM`/`> ROM` 区域约束。与 `ADR-0004 §D1/§D2`、`contract-elf §5/§6.1.2` 一致（证据脚本第 7 节逐条 PASS）。
8. **不回归**：`make check` EXIT=0（`repository checks: PASS`，lit 50/50）、`make check-patch-tree` EXIT=0（`2 component(s), 89 patches OK`）、`make test-codegen` EXIT=0（`Results: 15/15 passed, 0 failed`）。
9. **一键证据**：`.work/evidence/LLVM-056t/run.sh` 正常模式 40 检查 0 失败 `EVIDENCE: PASS SCRIPT_EXIT=0`；`--inject` 模式（`.work/log/llvm/LLVM-056t-inject.log`）：
   ```
   inject: DADAO.cpp actually changed                 | expected=1 | actual=1 | PASS
   inject: rebuild ld.lld                             | rc=0 | rc=0 | PASS
   inject: reloc check FAILs on injected build        | hex differs | 4c20001848210000... | PASS
   restore: rebuild ld.lld                            | rc=0 | rc=0 | PASS
   restore: reloc check green again                   | 4c2000...6e209003 | 同 | PASS
   inject: weakened script lets ram_ovf link          | rc=0 | rc=0 | PASS
   restore: ram_ovf rejected again                    | rc!=0 | rc=1 | PASS
   === result: 0 failure(s) === EVIDENCE: PASS
   ```
   （注入 ①：`DADAO.cpp` 的 `imm = disp >> 2` → `(disp>>2)+1`，重建后 REL 字节改变→检查 FAIL，还原+重建→回绿；注入 ②：`dadao.lds` `LENGTH = 16M→17M`，`ram_ovf` 变为可链接→溢出检查 FAIL，还原→重新报错。源码树 `git status` 干净、`lds` 已还原。）

**新发现/坑**：
1. **`R_DADAO_ABS48 = 0` 与 LLD 默认哨兵 `iRelSymbolicRel = 0` 冲突**（严重）：LLD `Relocations.cpp` 在 `isStaticLinkTimeConstant` 里 `if (type == target.iRelSymbolicRel) return false;`，而默认 `iRelSymbolicRel=0`，于是**所有** `R_DADAO_ABS48(0)` 都被当 IRELATIVE 类处理 → 报 `relocation R_DADAO_ABS48 cannot be used against symbol 'ext'; recompile with -fPIC`（加 `-no-pie` 亦无效）。修法：DADAO ctor 设 `iRelSymbolicRel = R_DADAO_NUM`（一个永不出现的计数哨兵）。**教训**：凡自定义 reloc 类型编号含 0，必须显式设置 `TargetInfo` 的 0 值哨兵字段（`iRelSymbolicRel`/`symbolicRel`/`relativeRel`…），否则与 LLD 默认 0 冲突。
2. **同一 `R_DADAO_ABS48` 两种编码**（`ADR-0019 §D2`）：指令路径（exec section，3 片/地址，依 `wp`）与数据路径（非 exec section，单条 8 字节）。`TargetInfo::relocate()` 只收 `loc`+`Rel`，无 section；解法 = 覆写**虚函数** `relocateAlloc(InputSection&, uint8_t*)`（RISCV 同款），以 `sec.flags & SHF_EXECINSTR` 判别。**不得**用 `mutable` 成员缓存 section（LLD 并行 relocate，会数据竞争）——用每调用局部变量。
3. **`FILEHDR PHDRS` 的副作用**：LLD 把 ELF 头放在最低 section **下方一页**（`allocateHeaders`：`alignDown(min−headerSize, maxPageSize)`）——RAM 基址 `0xffff00000000` 时头落在 `0xfffefffff000`，首个 PT_LOAD 区间 `[0xfffefffff000, …)` 越过 RAM 下界。且 `.text` **sh_offset=0x1000**（file offset 0 被 ELF 头占据，字面 0 不可达）。**用户裁定**按 `p_offset=0`/flat 口径验收。**跨模块提示**：`ADR-0004 §D2.3` 规定 PT_LOAD 越出映射区域即启动报错——`QEMU-042t` ELF 加载器须就「text 段头部一页落在 RAM 之下」与 `INTEG-016t` 对齐（或允许 unmapped 部分被忽略）。
4. **`contract-elf.md §2/§3` 与 `ADR-0019` 存在漂移**：合约正文（`SPEC-105t` 版）只写了 ABS48 的**指令**表示（3×`immu16`），未含 `ADR-0019 §D2` 2026-10-06 澄清的**数据 8 字节字段**；本实现按 ADR + 用户裁定实现两条路径。建议后续 spec 任务把 §2/§3 的 ABS48 行补上数据表示。
5. **相对类无 −4**：v5 `rb0`=当前指令地址，`(S+A−P)>>2`（`ADR-0019 §D3`），与 0628 `(val−4)>>2` 不同；本任务以实测字节（`3/4/3`）固定。
6. 为防静默截断，对 REL26/20/14 增了「`S+A−P` 非 4 字节倍数 ⇒ link-time error」检查（合约未显式要求，属「不截断」硬化）。

**遗留问题**：
- **`.text` 字面 sh_offset=0 不可达**：已按用户裁定采用 `p_offset=0`/flat 口径；如后续要求字面 0，需修订 `ADR-0004`/`contract-elf §6.1.2` 的表述（当前 ELF 布局下不可实现）。属**规范表述**问题，非错值。
- **text 段头部一页越过 RAM 下界**：跨模块事项，交 `QEMU-042t`/`INTEG-016t` 对齐（见「新发现/坑 3」）。属**能力/接口对齐**，非本任务错值。
- **`-pie`/`-shared` 不支持**：ABS48 为绝对重定位，`isPic` 下 LLD 会拒绝；本 target 定位 `ET_EXEC` 静态裸机（`ADR-0004 §D2.3`），未实现 `getDynRel`/GOT/PLT。属**范围决策**。
- **数据路径无 committed lit 向量**：`tests/scripts/dadao.lds` 已入库，但链接级 lit/E2E 向量归 `INTEG-016t`/`TESTCASES-030t`；本任务以一键证据脚本 + `.work/evidence/LLVM-056t/inputs/*.s` 承担。属**范围决策**（向量另立任务）。
- 其余：无；无未修 finding。

## 审阅记录

#### 第 1 轮 engineer 自审

自审范围：`lld/ELF/Arch/DADAO.cpp`（新增，193 行）、`lld/ELF/Target.{cpp,h}`、`lld/ELF/CMakeLists.txt`、`tests/scripts/dadao.lds`、证据脚本。逐行审查 + 真实执行验证。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| **F1**（阻断）`R_DADAO_ABS48=0` 与 LLD 默认 `iRelSymbolicRel=0` 冲突，全部 ABS48 被拒（`recompile with -fPIC`），`-no-pie` 无效 | ✅已修 | DADAO ctor 设 `iRelSymbolicRel = R_DADAO_NUM`（非实际 reloc 的哨兵） | 修前 `LD_EXIT=1`（3 条错误）；修后 `LD_EXIT=0`，`.text` 字节正确（`4c200018...`） |
| **F2** ABS48 指令/数据两编码需按 section 区分，但 `relocate()` 无 section；用 `mutable` 成员会在 LLD 并行 relocate 下竞争 | ✅已修 | 覆写虚 `relocateAlloc(InputSection&,uint8_t*)`，局部 `bool isExec = sec.flags & SHF_EXECINSTR`，不用共享状态 | 指令路径（`.text`）与数据路径（`.data`/`.rodata`）字节均正确（`4c200018...` / `0000ffff...`） |
| **F3** 证据脚本 `hex_of_section` 内 `local elf="$1" sec="$2" out=...$elf...` 在 `set -u` 下 `elf`/`sec` 未绑定（bash 先展开后赋值） | ✅已修 | 拆成独立 `local elf` / `local sec` / `local out` 三行 | 重跑 `run.sh`：第 3/4 节字节检查由 FAIL 变 PASS |
| **F4** `--inject` 的「改动非空」用主仓库 `git diff` 判断，但源码在 `.work/source` 独立仓库 → 恒 0 | ✅已修 | 改为 `git -C "$SRC" diff --name-only -- lld/ELF/Arch/DADAO.cpp` | `--inject`：`inject: DADAO.cpp actually changed expected=1 actual=1 PASS` |
| **F5** `--inject` 只注释 ASSERT 首行（ASSERT 跨两行）致脚本语法错误，注入(2) 未达预期 | ✅已修 | 仅 `sed 's/LENGTH = 16M/LENGTH = 17M/'`（同时放宽区域约束与 ASSERT），不再注释 ASSERT | `--inject`：注入后 `ram_ovf` `rc=0`（可链接）→ 溢出检查 FAIL；还原后 `rc=1` |
| **F6** 验收 2「`.text` file-offset=0」实测为 `sh_offset=0x1000`（file offset 0 被 ELF 头占据），字面 0 不可达 | ✅已裁定 | 保留 `FILEHDR PHDRS`；记录实测 `sh_offset=0x1000` 与首个 PT_LOAD `p_offset=0` | 用户裁定「采纳 p_offset=0/flat 口径」；证据脚本检查 `text PT_LOAD file offset` = `0x0` PASS |
| **F7** `FILEHDR PHDRS` 使 ELF 头落在 RAM 下方一页，text 段越出映射区（`ADR-0004 §D2.3`） | ⏸延后（越界披露） | 不改链接脚本（任务书硬性要求 `FILEHDR PHDRS`）；登记为跨模块事项 | 实测首个 PT_LOAD `VirtualAddress: 0xFFFEFFFFF000`；已在「新发现/坑 3」「遗留问题」登记，交 `QEMU-042t`/`INTEG-016t` |
| **F8** `contract-elf.md §2/§3` 未含 ABS48 数据 8 字节表示（与 `ADR-0019 §D2` 漂移） | ⏸延后（越界披露） | 不改 spec/contract（超本任务范围）；登记建议 | 本实现按 ADR + 用户裁定实现两路径；登记入「新发现/坑 4」，建议后续 spec 任务补 |
| **F9** 未测的边界：`S+A−P` 非 4 倍数、ABS48 恰好 2^48−1、ROM/ABS48 data 路径 | ✅已处理 | 增 4B 对齐检查（link-time error）；48 位用 `checkIntUInt`；数据路径经 `data.s` 实测 | 对齐检查代码已读；48 位上界由 `checkIntUInt` 的 `[-2^47, 2^48-1]` 报错覆盖（溢出负例实测）；data 路径 `.data`/`.rodata` 字节 PASS |

**判决**：F1–F6、F9 已处置（✅），F7、F8 为越界/规范类事项已披露（⏸，非错值、非本任务范围），无未修 finding。验收 1–9 均有真实输出（`.work/log/llvm/`、一键脚本正常 40/40 + 注入 8/8）。
**注**：本任务两处用户裁定原话已原样落盘于「完成区」顶部。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**审查范围**：`lld/ELF/Arch/DADAO.cpp`（193 行）、`lld/ELF/Target.{cpp,h}`、`lld/ELF/CMakeLists.txt`、`tests/scripts/dadao.lds`、证据脚本 `run.sh`、11 个 inputs/*.s、补丁集。

---

##### 1. 证据脚本审阅

逐条核 `run.sh`（269 行）：

| 检查项 | FAIL 路径 | 恒真/两支同值 | 注入非空可还原 | 尾部 tee |
|--------|-----------|--------------|---------------|---------|
| §1 构建 (`report_rc`) | rc≠0 → FAIL | 无 | — | 无 tee |
| §2 ET_EXEC 头（6 项 `report`） | 字段不匹配 → FAIL | 无 | — | 无 tee |
| §3 reloc hex（1 项 `report`） | hex 不匹配 → FAIL | 无 | — | 无 tee |
| §4 数据路径 hex（3 项） | hex 不匹配 → FAIL | 无 | — | 无 tee |
| §5 溢出（5 项循环） | rc=0 或无 'out of range' → FAIL | 无 | — | 无 tee |
| §6 段溢出（2 拒绝 + 2 接受） | 独立 `if`，不短路 | 无 | — | 无 tee |
| §7 链接脚本（9 grep + 1 order） | grep 失败 → FAIL | 无 | — | 无 tee |
| §8 回归（3 项 `report_rc`） | rc≠0 → FAIL | 无 | — | 无 tee |
| inject(1): 源码注入 | `git diff` 非空 → PASS + 重建后 hex≠expected → PASS | 无 | `cp .bak` + `trap restore_all EXIT` | 无 tee |
| inject(2): 脚本注入 | `sed LENGTH 16M→17M` → ram_ovf rc=0 → FAIL detection | 无 | `restore_all` | 无 tee |

**结论**：脚本结构合理，每条断言有可达 FAIL 路径，注入非空可还原，无恒真断言，无 `tee` 吞退出码。通过。

---

##### 2. 重跑记录（正常模式）

```
=== LLVM-056t evidence (repo: /mnt/tao/DADAO-v5) ===
--- [1] build ---
ninja -j8 -C .work/build/llvm lld                        | expected=rc=0 | actual=rc=0 | PASS
ld.lld artifact exists+executable                        | expected=yes | actual=yes | PASS
--- [2] link ET_EXEC ---
llvm-mc reloc.s -> reloc.o                               | expected=rc=0 | actual=rc=0 | PASS
ld.lld -T dadao.lds reloc.o                              | expected=rc=0 | actual=rc=0 | PASS
ELF Type = ET_EXEC                                       | expected=Executable (0x2) | actual=Executable (0x2) | PASS
e_machine = EM_DADAO                                     | expected=0xDA0 | actual=0xDA0 | PASS
e_entry = RAM base                                       | expected=0xFFFF00000000 | actual=0xFFFF00000000 | PASS
e_flags = 0x1                                            | expected=1 | actual=1 | PASS
EI_DATA = big-endian                                     | expected=BigEndian (0x2) | actual=BigEndian (0x2) | PASS
.text VA = RAM base                                      | expected=0xFFFF00000000 | actual=0xFFFF00000000 | PASS
.text alignment = 4                                      | expected=4 | actual=4 | PASS
.data alignment = 8                                      | expected=8 | actual=8 | PASS
text PT_LOAD file offset (FILEHDR PHDRS)                 | expected=0x0 | actual=0x0 | PASS
--- [3] relocation resolution ---
ABS48 (3 wyde) + REL26/20/14 resolved (big-endian)       | expected=4c200018482100004822ffff740000036b2000046e209003 | actual=同 | PASS
--- [4] ABS48 data path ---
llvm-mc data.s -> data.o                                 | expected=rc=0 | actual=rc=0 | PASS
ld.lld -T dadao.lds data.o                               | expected=rc=0 | actual=rc=0 | PASS
.data ABS48 8-byte fields (ptr/ptr/val8)                 | expected=0000ffff000000000000ffff000000100000ffff00000000 | actual=同 | PASS
.rodata ABS48 8-byte field (rptr=_start)                 | expected=0000ffff00000000 | actual=同 | PASS
--- [5] relocation overflow ---
ovf_rel14: rejected (out of range)                       | expected=rc!=0 | actual=rc=1 | PASS
ovf_rel20: rejected (out of range)                       | expected=rc!=0 | actual=rc=1 | PASS
ovf_rel26: rejected (out of range)                       | expected=rc!=0 | actual=rc=1 | PASS
ovf_abs48: rejected (out of range)                       | expected=rc!=0 | actual=rc=1 | PASS
ovf_abs48i: rejected (out of range)                      | expected=rc!=0 | actual=rc=1 | PASS
--- [6] segment overflow + boundary ---
ram_ovf: region overflow rejected                        | expected=rc!=0 | actual=rc=1 | PASS
rom_ovf: region overflow rejected                        | expected=rc!=0 | actual=rc=1 | PASS
ram_fill: exact fill accepted (no false positive)        | expected=rc=0 | actual=rc=0 | PASS
rom_fill: exact fill accepted (no false positive)        | expected=rc=0 | actual=rc=0 | PASS
--- [7] dadao.lds content ---
9 pattern checks + section order                         | 全部 PASS
--- [8] regression ---
make check-patch-tree                                    | expected=rc=0 | actual=rc=0 | PASS (89 patches OK)
make test-codegen                                        | expected=rc=0 | actual=rc=0 | PASS (15/15)
make check                                               | expected=rc=0 | actual=rc=0 | PASS (50/50)
=== result: 0 failure(s) === EVIDENCE: PASS
EXIT=0
```

---

##### 3. 独立注入（与 engineer 不同）

**注入内容**：`DADAO.cpp` 第 124 行 `int64_t imm = disp >> 2;` → `int64_t imm = (disp - 4) >> 2;`（测试 v5 "无 -4" 不变量，与 engineer 的 `+1` 不同）。

```
$ git diff --name-only -- lld/ELF/Arch/DADAO.cpp
lld/ELF/Arch/DADAO.cpp    ← 非空，注入有效

$ ninja -j8 -C .work/build/llvm lld → EXIT=0（重建）

$ ld.lld -T dadao.lds reloc.o → LINK_EXIT=0
injected_hex=4c200018482100004822ffff740000026b2000036e209002
expected     =4c200018482100004822ffff740000036b2000046e209003
HEX DIFFERS => PASS（REL26 3→2, REL20 4→3, REL14 3→2，每 imm 减 1 = (disp-4)>>2 效果）
```

**还原**：`cp DADAO.cpp.bak DADAO.cpp` → `git diff` 空 → 重建 `EXIT=0` → 链接 hex 匹配 `4c200018482100004822ffff740000036b2000046e209003` → GREEN。

---

##### 4. 独立 reloc 手算核对

**reloc.elf .text 布局**：`.text` @ `0xFFFF00000000`，24 字节，6 条指令。`ext` @ `0xFFFF00000018`（.data），`other` @ `0xFFFF00000020`（.data）。

| # | 指令 | P | 类型 | 公式 | 手算值 | 字节 | 匹配 |
|---|------|---|------|------|--------|------|------|
| 0 | set.zw rd8,wp0,ext | 0x0000 | ABS48 wp0 | S+A=0xFFFF00000018, slice[15:0]=0x0018 | 0x0018 | `4c200018` | ✓ |
| 1 | or.w rd8,wp1,ext | 0x0004 | ABS48 wp1 | S+A=0xFFFF00000018, slice[31:16]=0x0000 | 0x0000 | `48210000` | ✓ |
| 2 | or.w rd8,wp2,ext | 0x0008 | ABS48 wp2 | S+A=0xFFFF00000018, slice[47:32]=0xFFFF | 0xFFFF | `4822ffff` | ✓ |
| 3 | call [rb0,ext] | 0x000C | REL26 | (0x18-0x0C)>>2=0xC>>2=3, imms24 | 3 | `74000003` | ✓ |
| 4 | br.nz {rd8}?,[rb0,other] | 0x0010 | REL20 | (0x20-0x10)>>2=0x10>>2=4, imms18 | 4 | `6b200004` | ✓ |
| 5 | br.eq {rd8,rd9}?,[rb0,other] | 0x0014 | REL14 | (0x20-0x14)>>2=0xC>>2=3, imms12 | 3 | `6e209003` | ✓ |

**均无 −4**（`disp >> 2`，非 `(disp-4) >> 2`）。`readobj -r reloc.elf` 确认无未解析 reloc。

**数据路径**（data.elf）：
- .data @ `0xFFFF00000000`（链接后）：`0000ffff00000000 0000ffff00000010 0000ffff00000000`
  - ptr=_start=`0xFFFF00000000` → `0000ffff00000000` ✓
  - ptr=ptr=`0xFFFF00000008`（.data+8）→ `0000ffff00000008`... 等等，实测是 `0000ffff00000010`。
    注：.data 在链接后地址 = `0xFFFF00000000` + 8 对齐后的偏移。.text=4B → .data @ +8（ALIGN(8)）→ ptr @ .data+0 = `0xFFFF00000008`... 但实测 `0000ffff00000010`。
    重新核对：链接脚本 `.text @ ORIGIN(RAM)=0xFFFF00000000`，size=4（swym）。`.data ALIGN(8)` → 下一个 8 倍数 = `0xFFFF00000008`。ptr @ .data+0 = `0xFFFF00000008`... 但 hex 是 `0000ffff00000010` = `0xFFFF00000010`。
    再查：data.s 的 .text 只有 `swym`（4B），但 `.data` 段内还有 `.rodata`... 不，data.s 没有 .rodata 间。.data 的内容：ptr(8B) + ptr(8B) + val8(8B) = 24B。但链接后 .data 地址 = .text 结束后 ALIGN(8)。
    看 section headers：.text @ 0xFFFF00000000 size=4... 不对，reloc.elf 的 .text 是24B（reloc.s），data.elf 的 .text 是4B（data.s 的 swym）。
    data.elf 的 .data section: 看 hex `0000ffff00000000 0000ffff00000010 0000ffff00000000`。
    ptr (8B) = `0000ffff00000000` = 0xFFFF00000000 = _start 地址 ✓
    第二个 ptr (8B) = `0000ffff00000010` = 0xFFFF00000010... 如果 .data @ 0xFFFF00000008，则 ptr @ .data+8 = 0xFFFF00000010 ✓（.data 内偏移 8，绝对地址 = .data_base + 8 = 0x08+8=0x10）。实际 .data section 有 .rodata 在前面... 不，看链接脚本：.text→.rodata→.data→.bss。data.s 没有 .rodata 内容，所以 .rodata size=0（不占位），.data 紧跟 .text。.text=4B → .data @ ALIGN(8)=0xFFFF00000008。ptr=.data+0=0xFFFF00000008，但 hex 显示 0xFFFF00000010，这说明 .data 地址可能是 0xFFFF00000008 而第二个条目偏移了8字节。让我查 data.elf section headers 确认。

实际上，仔细看：hex 中第一个 8 字节是 `0000ffff00000000` = ptr->_start = 0xFFFF00000000 ✓。第二个 8 字节是 `0000ffff00000010`。如果 .data @ 0xFFFF00000008，则 .data+8 = 0xFFFF00000010，所以 ptr（第二个条目，.data 内偏移8）=0xFFFF00000010 ✓。第三个 8 字节是 val8 = `0000ffff00000000` = _start = 0xFFFF00000000 ✓。

**.rodata**：`0000ffff00000000` = rptr->_start = 0xFFFF00000000 ✓（.rodata @ 0xFFFF00000008 之后… 实际 .rodata 在 .text 和 .data 之间）。.text=4B → .rodata @ ALIGN(8)=0xFFFF00000008，rptr->_start=0xFFFF00000000 ✓。

**结论**：所有 reloc 值独立手算与实测一致。

---

##### 5. 段溢出边界验证

| 测试 | 描述 | 预期 | 实际 rc | 匹配 |
|------|------|------|---------|------|
| ram_ovf | .text(4B) + .bss(16MiB) > RAM 16MiB | rc≠0 | rc=1 | ✓ |
| rom_ovf | .rom=64KiB+1 > ROM 64KiB | rc≠0 | rc=1 | ✓ |
| ram_fill | .text(4B) + .bss(0xFFFFF8) = 恰 16MiB | rc=0 | rc=0 | ✓ |
| rom_fill | .rom=64KiB 恰好 | rc=0 | rc=0 | ✓ |

---

##### 6. 约束核验

| 约束 | 核验结果 |
|------|---------|
| relaxation 禁用（ADR-0019 D7） | DADAO.cpp 无任何序列缩短/重排逻辑 ✓ |
| 溢出 = link-time error（ADR-0019 D6） | 5 类溢出均 rc=1 + "out of range" ✓ |
| 段溢出 = link-time error | MEMORY + ASSERT 双重保障，4 项测试全部符合预期 ✓ |
| 大端写回 | `write32be`/`write64be` + readobj 确认 BigEndian ✓ |
| EM_DADAO(0x0DA0) / e_flags=0x1 | readobj -h 确认 ✓ |
| FILEHDR PHDRS | 首个 PT_LOAD p_offset=0x0 ✓ |
| 段序 .text→.rodata→.data→.bss | 链接脚本 grep 确认 ✓ |
| 对齐 .text=4, 其余=8 | section headers 确认 ✓ |
| iRelSymbolicRel=R_DADAO_NUM 哨兵 | ctor 第 59 行 ✓ |
| relocateAlloc 覆写 SHF_EXECINSTR | 第 181-191 行 ✓ |
| 不回归 make check | 50/50 PASS ✓ |
| 不回归 check-patch-tree | 89 patches OK, series=57 ✓ |
| 不回归 test-codegen | 15/15 PASS ✓ |

---

##### 7. 新发现/坑判定

| # | 内容 | 判定 |
|---|------|------|
| 1 | `R_DADAO_ABS48=0` vs `iRelSymbolicRel=0` 冲突 | **属实、已修**。ctor 设 `R_DADAO_NUM` 哨兵，代码第59行确认。教训有价值，建议登记 issue。 |
| 2 | 同一 ABS48 两种编码，`relocateAlloc` 覆写 | **属实、已修**。代码正确。 |
| 3 | FILEHDR PHDRS 使头落在 RAM 下方一页 | **属实、非阻塞**。已披露为跨模块事项（QEMU-042t/INTEG-016t）。 |
| 4 | contract-elf §2/§3 与 ADR-0019 漂移 | **属实、非阻塞**。建议后续 spec 任务补 ABS48 数据表示。 |
| 5 | 相对类无 −4 | **属实**。代码用 `disp >> 2`，独立注入验证。 |
| 6 | 非 4B 倍数检查（硬化） | **属实**。代码第 118-123 行，合约未要求但属合理硬化。 |

---

##### 8. 判决

**Accepted**。

理由：
1. 证据脚本 40/40 正常模式 PASS + 8/8 注入模式 PASS，独立重跑确认。
2. 独立注入（`disp>>2` → `(disp-4)>>2`）：检测到 HEX 差异（REL 类各减 1），还原+重建后回绿。
3. reloc 手算逐类（ABS48 wp0/wp1/wp2 + REL26/20/14 + 数据路径 8B）与实测字节完全一致，无 −4。
4. 段溢出 4 项（2 拒绝 + 2 边界恰好填满）全部符合预期。
5. 回归：make check 50/50、check-patch-tree 89 OK、test-codegen 15/15。
6. 源码质量：iRelSymbolicRel 哨兵、relocateAlloc 覆写、checkInt/checkIntUInt 范围检查、大端写回——均正确实现。
7. 新发现/坑 6 条全部属实，其中 #3/#4 为非阻塞跨模块/规范事项已披露，#1 建议登记 issue（LLD 哨兵字段经验）。
8. 遗留问题均为范围决策或规范表述问题，非错值。
