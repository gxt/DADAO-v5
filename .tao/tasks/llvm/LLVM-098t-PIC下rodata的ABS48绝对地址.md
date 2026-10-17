# LLVM-098t: `-fPIC` 下 `.rodata` 仍发 `ABS48` 绝对地址（`P2` 阶段 A1 的新阻塞；**根因未知 ⇒ 第一步诊断**）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`INFRA-085t`（**登记源 + 消费方**：阶段 A1 出口判据 `make build-musl-shared`）、`LLVM-096t`（前一轮 4 项：驱动 `-shared` 转发 / PIC 相对查找表 opt-out / PIC 跳转表进 `.data.rel.ro` / VLA）、`LLVM-097t`（`i64 = bswap` ⇒ 本轮 `install-host` 已含）、`ADR-0019 D10`（重定位类型集**冻结**）/`ADR-0026`（动态链接行为）、`ISS-229`（禁并发）、`ISS-210`（改 `components/**` ⇒ 单跑 `install-host`）、`docs/Process-01`（组件补丁树）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（**先读**）

- **来源** = `INFRA-085t` 阶段 A1 复跑（2026-10-17）：本轮 `install-host` **PASS**（主会话现场；新工具链已含 `bswap`〔`LLVM-097t`〕与 `LLVM-096t` 四项），但 `make build-musl-shared (JOBS=8)` ⇒ **`MUSL_SHARED_EXIT=2`**（日志 `.work/log/infra/P2-A1-rebuild.log`，83,913 B）。
- **现场签名（architect 只读取证，逐字）**：

  ```text
  ld.lld: error: relocation R_DADAO_ABS48 cannot be used against symbol '.L0 '; recompile with -fPIC
  >>> defined in obj/src/math/atan2f.lo
  >>> referenced by atan2f.c
  >>>               obj/src/math/atan2f.lo:(.rodata.atan2f+0x0)
  ```

  末段：`ld.lld: error: too many errors emitted, stopping now (use --error-limit=0 to see all errors)` ⇒ `clang: error: ld.lld command failed with exit code 1` ⇒ `make[1]: *** [Makefile:162: lib/libc.so] Error 1` ⇒ `make: *** [Makefile:497: build-musl-shared] Error 1` ⇒ `MUSL_SHARED_EXIT=2`（log L148）。
- **量（现场实测）**：签名行 `grep -c` = **20**（lld 默认 `--error-limit` 截断，**不是**全部）；涉及 **12** 个对象、**20** 条重定位，偏移 = `+0x0` / `+0x8` / `+0x10`，符号一律 `.L0`（lld 打印带尾随空格；**同一对象内定义**）。
- **已知例子（对象 / 函数 / 节）**：`src/locale/langinfo.c`（`.rodata.__nl_langinfo_l`）/ `src/math/atan2f.c`（`.rodata.atan2f`）/ `src/math/atan2.c` / `src/math/cos.c` / `src/math/sin.c` / `src/math/sincos.c` / `src/math/cosf.c` / `src/math/jn.c` / `src/math/lgamma_r.c` / `src/math/lgammaf_r.c` / `src/ctype/iswctype.c` / `src/locale/iconv.c`。
- **前序处置（**不要**据此预设根因）**：`LLVM-096t` 已把 **PIC 跳转表**送 `.data.rel.ro`（41×`RELATIVE`）、并给 **relative lookup table** 加 TTI opt-out（`ISS-240`）；`ISS-241` 曾以**同一文案**登记（`-shared` 拒 `.rodata` 内局部 `ABS48`）。⇒ 本条属**第三类现场**（同文案、重跑仍现），**机制未定** ✗。**本册禁止**在诊断前把根因写成「跳转表」/「相对查找表」/「常量节放置」中的任一种。
- **参考仓库检索（只读，内容溯源、非执行必需）**：`.cache/refs/DADAO-0628` 对 `-fPIC` / `ABS48` / `data.rel.ro` / `shouldBuildRelLookupTables` **0 命中**（其动态链接置于内核之后、未做用户态 PIC 库）⇒ **无做法可借**；本项目差异 = 无内核 + musl `ldso` + 自定重定位类型集（`ADR-0025`/`ADR-0019 D10`）。

## 目标

`-fPIC` 编译产物**不得**把 `ABS48`（绝对 48 位）写进 `.rodata`（或**任何**会进只读段的位置）⇒ 使 `make build-musl-shared` **rc=0**，从而解 `INFRA-085t` 阶段 A1 的出口判据。

**第一步 = 诊断（强制、先于任何修法）**：定位该常量在 **IR / DAG / MC** 三层分别是什么路径 —— `ConstantPool`（`BlockAddress` / `GlobalAddress` / 浮点常量合并）/ `ConstantExpr` / pass 改写的表 / 节放置（`.rodata` vs `.data.rel.ro`）；给**最小复现**（单文件 `-fPIC -S`）。诊断结论写成「**构造类别 → 证据（`file:line`/IR/DAG/MC）→ 建议落点**」表，**先落完成区**再动修法。

## 接口规范

- **输入**：本册「立项来源」的现场签名与日志；`.work/source/musl/**`（消费侧复现源，**只读**，交付不改）；`.work/build/llvm` 与安装根（当前工具链，已含 `LLVM-096t`/`LLVM-097t`）；`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（现状）；口径真源 = `ADR-0019 D10`（类型集：`ABS48`=6、动态 `7`–`13`、`PCREL_HI/LO`=14/15、`NUM`=16）/`ADR-0026`（仅 GNU hash、eager `BIND_NOW`、GOT 3 条、越界 5 条）/`.tao/contracts/contract-elf.md §2.2`、`§3`、`.tao/contracts/contract-dynlink.md`（PIC/GOT/`RELATIVE` 口径）。
- **输出**：
  1. **诊断报告**（本册完成区，≤30 行；长输出留 `.work/log/llvm/`）+ **最小复现源**（放 `.work/evidence/`，随证据脚本保留）；
  2. **组件补丁**（`components/llvm-project/patches/**`，**一文件一补丁**；若新增文件则 `series` 同步 + `changelog.md` 一条，`docs/Process-01 §10` 体例；`check-patch-tree` 机械校验）；
  3. **证据**：`.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项打印「检查名 + 期望/实际 + rc」、任一失败非零退出、含 `--inject`）+ 原始输出落 `.work/log/llvm/<任务ID>/`；
  4. 本册完成区 + `milestones.md` 流水行（收尾归 `/complete`）。
- **约束**：**最小改动**；**不得**改 `spec/`、`contracts/`、`.tao/contracts/**`、musl 源/锁条目；**不得**新增/改重定位类型编号（`ADR-0019 D10` 冻结；若诊断结论**必须**新增类型/改契约 ⇒ **停下报告**，归用户语义裁定 ✗）；组件源**一律 git 基线**（只经 `patches/**` 交付、base+1 单 commit；**不得**直接改 `.work/source/**` 作为交付）；期望值**独立**、**不从 LLVM/lld 的通过与否反推**。

## 做

### ① 诊断（**必做，且先于修法**）

```sh
# workdir = 仓库根；<TC> = 安装根 cross-toolchain/bin（或用 .work/build/llvm/bin，同一二进制来源）
M=.work/source/musl
INC="-I$M/arch/dadao -I$M/arch/generic -I$M/obj/src/internal -I$M/src/include \
     -I$M/src/internal -I$M/obj/include -I$M/include"
<TC>/clang --target=dadao-unknown-elf -ffreestanding -nostdinc $INC \
  -fno-stack-protector -fPIC -fno-unwind-tables -fno-asynchronous-unwind-tables \
  -ffunction-sections -fdata-sections -w -O2 -S -o /tmp/opencode/LLVM-098t/atan2f.s \
  $M/src/math/atan2f.c
<TC>/llvm-readobj --relocations /tmp/opencode/LLVM-098t/atan2f.o   # 逐条核：类型 6（ABS48）、符号、所属节
```

- **逐层取证**（三条都要，**写出证据再下结论**）：
  1. **IR**：`-emit-llvm -S`（`-fPIC`）看该常量的初始化子是什么 —— `blockaddress(@fn, %bb)` / `@global` / 浮点常量 / pass 生成的表；`-O0` 与 `-O2` 对比（判断是否某 pass 生成）；
  2. **DAG/MC**：`-S` 产物里该 `.rodata.<fn>` 槽位的指令/数据形态（`.dd.o64`/`.quad`/…）；必要时 `-print-after-all`/`-debug-only`（只读诊断工具可用，**不改构建输入**）；
  3. **节放置**：`llvm-readobj -S` 核该节标志（是否 `SHF_WRITE`）与名字（`.rodata.<fn>` vs `.data.rel.ro.*`）；**同源非 `-fPIC` 对照**（走 `.dd.o64` 绝对 8 字节项）——对照用于证明「PIC 与绝对项的分叉点在哪一层」。
- **最小复现**：从上述对象中**至少 2 个**（建议 `atan2f.c` + `iswctype.c`，覆盖数学表与 ctype 表）裁出**单函数 + 单常量表 + 一次取址**的最小源；要求：`-fPIC -O2 -S` 仍出现同一签名（`.rodata` 内 `ABS48` 打本对象标签），裁不掉就在完成区说明哪一步不可裁（**不得**用「整文件」糊过诊断）。
- **与 `ISS-241` 的去重判定（必写）**：若诊断为「与 `ISS-241` 同机制」⇒ 在本册完成区写明依据，并**择一收口**（本册承接 / 回 `ISS-241`），**不得双开**；若不同 ⇒ 在新 issue 处回填一句判定（不动历史正文）。

### ② 修法（**由 ① 的结论决定，禁止预设**）

候选（**择一或组合，须在完成区写理由 + 与契约逐条对齐**）：

- **(a) CodeGen：PIC 下把含指针常量的节置 `.data.rel.ro`**（可写可重定位；链接期 `RELATIVE`）—— 与各 arch 惯例一致，**不新增类型**；
- **(b) CodeGen：PIC 下该常量取址走 GOT 间接**（`GOT` 3 条形态 / `aip.si` + `ld.o`，`ADR-0026 D5`）—— 只在「常量本身不必是绝对地址」时成立；
- **(c) LLD：把局部 `ABS48` 降级 `R_DADAO_RELATIVE` 并把目标节置可写** —— **须先判**是否违背 `ADR-0019 D10`/`contract-elf §3`（`ABS48` 语义 = 绝对 48 位、`RELATIVE` = 装载期基址加），**不得**借机扩类型集；
- **(d) ① 诊断得到的其它最小落点**（须写明为何是它）。

**纪律**：只改**必须**改的一处路径；若发现修法会波及静态档语义 ⇒ 立即停下回到验收 ③（静态不回归是硬要求）；若撞到**另一类**生产侧缺口 ⇒ 保留现场、登记 issue、继续推进（**不掩盖**）；若因此 `rc=0` 不可达 ⇒ 完成区「遗留问题」如实写、交主会话，**不得伪绿**。

**构建/安装**：改 `components/**` ⇒ **单跑一次** `install-host`（**申报预计耗时 ≈5–10 min**，参照 `LLVM-091t`/`QEMU-061t` 实测；`JOBS=8`、**禁**全核、**禁**与任何 `build-*`/L2/L3 并发 —— `ISS-229`；安装根必须新鲜 —— `ISS-210`）。

### ③ 验收（五条，逐条留真实输出与自身 rc）

1. **最小复现无 `ABS48` 打只读段**：`-fPIC -O2` 产物 `llvm-readobj --relocations` **逐条**核 —— `.rodata*`（及一切 `SHF_WRITE=0` 且非 `.data.rel.ro*` 的节）内 **0** 条 `R_DADAO_ABS48`（类型 6）；允许形态 = GOT 间接 / PC 相对（`PCREL_HI`/`LO`）/ 可写可重定位节内的 `RELATIVE`。**修前基线**：同一复现**确有一条** `ABS48`（证明断言非恒真）。
2. **主判据**：`make build-musl-shared` **rc=0**（日志中 `recompile with -fPIC` **0** 处、`ABS48 cannot be used` **0** 处、`error:` **0** 处）；产出 `lib/libc.so` 为 **`ET_DYN`** + `readelf -d` 有 `SONAME[libc.so]`、**仅** `GNU_HASH`、**无** `HASH`/`RELR`/`VERSYM`/`VERNEED`；并对 `lib/libc.so` 全量 `llvm-readobj --relocations` 抽查无 `.rodata` 内 `ABS48`。
3. **静态不回归（硬要求）**：`make build-musl` **rc=0**；静态 4 项事实逐条复现（`ELF64` / `ELFDATA2MSB` / `ET_EXEC` / 无 `PT_INTERP`）；`libc.a` / `crt1.o` / 静态 ELF 的 `sha256`：**本册补丁前/后**双跑对照，差异**逐条归因**（预期仅 `.comment` 内组件 commit hash ⇒ **剥离 `.comment` 后逐字节相同**）；与 `INFRA-082t`/`INFRA-085t` 记录值的差异须**全部**命中已登记口径（`.comment` + `ISS-206` 号表），**不得**出现未归因差异。
4. **可达 FAIL**：`--inject` ≥2 条并给出「注入 → FAIL → `cp` 备份 + md5 还原 → 回绿」真实输出 —— (i) 还原/禁用修复（或把修复条件改回）⇒ 验收 1 的 `ABS48` 断言 **FAIL**；(ii) oracle 侧把期望节名/类型号改错 ⇒ **FAIL**。**禁恒真**、禁「两支写同一结果」；**禁** `git checkout`/`restore`/`stash` 还原（会清未提交改动）。
5. **独立 oracle**：以独立脚本从 `llvm-readobj` 原始输出 / ELF 字节判定「**重定位类型 + 目标节属性**」是否合 `ADR-0019 D10`/`ADR-0026`（`.rodata` 只允许 PC 相对或 GOT 间接；`ABS48` 仅允许落可写可重定位节），期望值**独立**写（不调用 LLVM/lld 判定结论）；含**大端**敏感例（`ELFDATA2MSB` 下重定位字段逐字节核 + 至少 1 个常量表项的值级核验）。

## 不做项（显式）

1. **`D2`（TLS 类动态重定位发射）** ✗（另行裁定）。
2. **`INFRA-079t`（compiler-rt builtins）** ✗。
3. **`ISS-243`（i32 窄返回 canonical 化）** ✗（独立缺陷，不并入本册）。
4. **`INFRA-085t` 的 `B1`/`C1`/`D1`**（动态可执行 / `ldso` 真接入 / TLS 动态）✗ —— 本册只解 **A1** 的 `.rodata` 阻塞。
5. **运行验证 / `qemu-user` / 三套测试集**（`P3`/`P4`）✗ —— 判据 = **能编 + 静态可核**。
6. **改 `spec/`、`contracts/`、`.tao/contracts/**`、musl 源/锁条目、重定位类型集** ✗。
7. **`L2`/`L3` 与里程碑判定** ✗（归主会话 / `/complete`）。

## 验收标准

1. **诊断**：① 的「构造类别 → 证据 → 建议落点」表齐全（IR/DAG/MC 三层 + 节放置 + 非 PIC 对照）+ 最小复现（≥2 源）真实输出；**根因未定的写法视为未完成**。
2. 验收 1 + 2（最小复现无 `ABS48` 打只读段；`make build-musl-shared` rc=0）为主判据。
3. 验收 3 静态不回归（4 项事实 + `sha256` 逐条归因，0 未归因差异）。
4. 验收 4 可达 FAIL（≥2 注入，含还原回绿）+ 验收 5 独立 oracle（类型/目标节，独立期望值，含大端例）。
5. 构建纪律：改 `components/**` ⇒ 单跑 `install-host`（申报耗时、`JOBS=8`、不并发、`ISS-210`）；`check-patch-tree` / `check-index-blobs` / `check-source-state` / `check-no-residue` / `check-tasks` / `check-knowledge-refs` / `check-component-changelog` / `check_issues` 各留**自身**真实 rc=0（禁 `cmd | tee` 吞码）；`make check`(L1) rc=0。
6. 完成区与真实输出逐条对齐（≤30 行）；`milestones.md` 流水行更新（收尾归 `/complete`）。

## 完成区
**测试结果**：`.work/evidence/LLVM-098t/run.sh` 三模式全绿：default **33 PASS/0 FAIL/2 SKIP**、`--inject ii` **38 PASS/0 FAIL**、`--inject i` **43 PASS/0 FAIL**；门控 **11/11 rc=0**（含 `make check` L1）。
**修改文件**：**产品源码 0 改动、导出 0 补丁**（`components/**` 无变化；`check-patch-tree` 仍 **151**）。新增（`.work/`，不入 git）：`evidence/LLVM-098t/{run.sh, oracle_abs48.py, repro/{jt_math,jt_ctype,const_table}.c, static/musl_smoke.c, stale/{math_atan2f,ctype_iswctype}.lo + README.md}`、`log/llvm/LLVM-098t/*`。
**验收结果**：
- **① 诊断（强制首步；IR/DAG/MC 三层 + 节放置 + 非 PIC 对照；原件 `log/llvm/LLVM-098t/diag-ir-dag-mc.txt`）**：IR = `switch` 指令、`blockaddress` **0 处**（`-O0` 无表、`-O1/-O2/-O3/-Os` 才有 ⇒ 非前端常量、非 pass 生成的表）；DAG = `br_jt JumpTable:i64<0>` → `DADAOISD::BR_JT` → `PCREL_LOAD TargetJumpTable`（`DADAOISelLowering.cpp:293` 强制 `EK_BlockAddress`）；MC = `.LJTI0_0: .dd.o64 .LBB…` → `FK_Data_8` → `R_DADAO_ABS48`（`DADAOELFObjectWriter.cpp:73`）；**节放置分叉点** = `DADAOTargetObjectFile.cpp::getSectionForJumpTable`（PIC ⇒ `.data.rel.ro`，非 PIC ⇒ `.rodata`）。最小复现 2 源（`-fPIC -O2 -S/-c`，命令见 `run.sh` S2/S3）：`repro/jt_math.c`（裁自 `src/math/cos.c` 的 `switch (n&3)`）、`repro/jt_ctype.c`（裁自 `src/ctype/iswctype.c` 的 dense switch）。
- **① 根因**：现场 12 个 `.lo` 是**陈旧对象**（mtime `08:04` < LLVM-096t 提交 `09:56` / 安装 `10:19`；musl `Makefile` 不以编译器二进制为依赖 ⇒ `make` 复用旧对象）⇒ `.rodata` 类缺陷**已由 LLVM-096t 修好**，本册**无需改编译器**（故 0 补丁）。证据：clean rebuild 后 **1338 个 `.lo` 中 1337 个只读段 ABS48 = 0**，同一 12 源全部落 `.data.rel.ro.<fn>`；陈旧 12 对象实际是 **119 处**（非 lld 截断显示的 20）。
- **①** 2 源 + 真实 4 源（`atan2f/cos/iswctype/langinfo`）`-fPIC -O2` ⇒ 只读段 ABS48 = **0**；`-fno-pic` 对照 ⇒ **4 处 `.rodata`**（修前形态，证明断言非恒真）。
- **② 等价验证（**非**最终验收）**：clean rebuild（build-tree clang，`make clean && make -j8`）**rc=2**；`--error-limit=0` 全量 **22 条** = 6×ABS48（全在 `ldso/dlstart.lo` 的 `.text`，musl 内联 asm）+ 16×undefined；**`.rodata` 目标 0 条**。⇒ 主判据 rc=0 **未达**，4 类原因均非本册缺陷（见遗留）；**最终以主会话 `install-host` 后复跑为准**。
- **③ 静态不回归**：smoke 链接 rc=0 + 4 项事实（ELF64 / `ELFDATA2MSB` / `ET_EXEC` / 无 `PT_INTERP`）+ 无 `DT_NEEDED`；与 INFRA-082t 基线**同尺寸 75336**、差异**全部**在 `.comment`（151 B）。`libc.a`/`crt1.o` sha256 与 085t 基线不同（归因 `.comment` + ISS-206，属 085t 已登记口径；旧归档已被本轮 clean rebuild 原位覆盖，无法再逐成员对照 ⇒ 以 ELF 字节级 elfdiff 为准）。
- **④ 可达 FAIL ≥2**：(i) 关掉 PIC 重定向 + `ninja llc` ⇒ 4 条 ABS48 进 `.rodata`、lld 报原文 `recompile with -fPIC`；`cp`+md5 还原、`ninja llc` 后与安装根 llc **逐字节相同**、回绿。(ii) oracle 期望类型 `6→7`、`SHF_WRITE 0x1→0x0` 两处改错均 **FAIL**，改回后绿。**未用** `git checkout/restore/stash`。
- **⑤ 独立 oracle**（`oracle_abs48.py`）：自写 ELF64/`ELFDATA2MSB` 字节解析（`r_info` 低位=类型/高位=符号、`SHF_WRITE` 判目标节、`SHT_RELA` entsize 硬校验），期望值独立取 `ADR-0019 D10`（ABS48=6）+ `contract-dynlink §4.3`；大端**值级**核验 `.rodata+0x0 == 40 49 0f db`（pi = `0x40490FDB`）。
- **门控（各自真实 rc）**：`check-instrinfo` / `check_lit_gen` / `check-patch-tree`(151) / `check-index-blobs` / `check-source-state` / `check-no-residue` / `check-tasks` / `check-knowledge-refs` / `check-component-changelog` / `check_issues` / `make check`(L1) 全 **0**。
**新发现/坑**：
- 「`recompile with -fPIC`」会**掩盖陈旧对象**：换工具链后 musl `.lo` 不会自动重建（`make` 不跟踪 `CC`）⇒ 必须 clean。这是 `ISS-241`/`ISS-244`「同文案反复出现」的真实成因。
- lld 默认 `--error-limit` 截断：现场「20 处」实为 **119 处**（12 对象，原件见 `evidence/LLVM-098t/stale`）。
- 只看现场对象会误判「LLVM 仍缺修复」；须全量 rebuild 后复算（本轮 `2670` 对象扫描：陈旧 10199 处 → 新构建 6 处）。
- `ISS-241` 与 `ISS-244` **同机制**（catopen 现场即跳转表；其 `.lo` 现为 `.data.rel.ro.catopen`）⇒ 建议一并按 LLVM-096t 收口、不双开。
**遗留问题**：
- **②主判据未达（如实，不伪绿）**，4 类均非 LLVM 代码生成：(a) 6×ABS48 = musl 内联 asm（`arch/dadao/crt_arch.h:69` `set.rb rb17,_DYNAMIC`；`arch/dadao/reloc.h:109` `set.rd rd8,__dls2`，后者自注「P2 需改 PC 相对/GOT」）⇒ 归 musl（A1 正在改 `components/musl/**`，本册**未碰**）；(b) 14×undefined = **过期 `arch/dadao/arch.mak` 排除表**（13 源现 11 源可编，仅 `rotl` 2 源 `Cannot select`）⇒ 刷表 + backend `rotl`（另一册）；(c) `__muldc3`/`__mulsc3` = compiler-rt（`INFRA-079t`，不做项）；(d) `__vdsosym` = VDSO 缺失（musl 面）。
- 新发现**未登记 issue**：`.tao/knowledge/issues.yaml` 含 A1 未提交改动，按派单**不碰**；请主会话登记（建议：musl `dlstart` 绝对地址 / `arch.mak` 排除表过期 / `rotl` backend 缺口），并按上条把 `ISS-241`+`ISS-244` 一并收口。
- 任务 `**状态**` 按要求**未改**（仍 `待开始`），归主会话裁定。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

**判决**：本册**无产品代码改动**（0 补丁）⇒ 自审范围 = 证据脚本 / oracle / 诊断结论与真实输出的逐条一致性。`subagent_depth=1`，故为自主逐行审查。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `SHT_RELA` 的 `sh_entsize==0` 时 oracle 会解析 0 条 ⇒ 可能「恒真绿」 | ✅已修 | oracle 加硬校验（entsize≠24 直接退出，不产出「0 violations」） | default 全绿；S11(ii) 仍能红 |
| F2 S7 全树扫描只有「0 violations」，缺「确实看到 ABS48」的非空性 | ✅已修 | 现场统计 `writable` 计数并断言 `> 0`（不写死阈值） | 实际 2709 |
| F3 `--inject ii` 若只把类型号 6→7，配 `--expect-nonwritable 0` 会**空绿** | ✅已修 | 该注入改用 `--min-writable 4 --require-section`（构造未被识别 ⇒ 红） | `S11(ii) wrong type number goes red` |
| F4 静态 ELF 与基线差 8 B：源文件名进 `.strtab`（`static_smoke.c` vs `musl_smoke.c`） | ✅已修 | 复现源改名 `static/musl_smoke.c`（与 `build_musl.PROG_C` 同基名） | elfdiff rc=0（同尺寸 75336，仅 `.comment`） |
| F5 S6 `langinfo.c` 缺 `bits/syscall.h` ⇒ 该源未真正验证（脚本却可能绿） | ✅已修 | S0 按 musl 规则现场生成 `bits/{alltypes,syscall}.h`；S6 任一源失败即红 | S6 rc=0（4/4 源） |
| F6 S7 `\|.text\|` 只匹配 `.text`，漏 `.text._dlstart_c`（6→3 误判） | ✅已修 | 改 `\|\.text` 前缀匹配 | 6/3/3/6 |
| F7 `--inject i` 中断会把组件检出留在注入态 | ✅已修 | `trap 'cp $BAK $CPP' EXIT INT TERM`，还原后 `trap -` | 还原 md5 一致 + llc 与安装根逐字节相同 |
| F8 `make lib/libc.so` 若意外成功，`allerr_rc` 未初始化（`set -u` 直接崩） | ✅已修 | 初始化 + 「XFAIL 已解」提示分支 | 三模式全绿 |
| F9 S10 属 **XFAIL**，是否掩盖失败？ | ❌不掩盖 | 期望集合逐项钉死（22 条 / 6 ABS48 / 16 undefined 逐字），任何漂移即红；输出标注「最终验收归 `/complete`」 | S10 五条断言原件 |
| F10 未改编译器 ⇒ 无「修」，是否伪绿？ | ❌不伪绿 | 结论由 clean rebuild 全量重扫（1337/1338 个 `.lo` 为 0）+ `-fno-pic` 对照 + 两处注入支撑；②主判据**如实标未达**并给 4 类归因 | 完成区「遗留问题」+ `evidence-*.log` |

**未修 finding**：无（F9/F10 为判定项，非缺陷）。**状态**：按派单未改任务 `**状态**`（仍 `待开始`），交主会话裁定。

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
