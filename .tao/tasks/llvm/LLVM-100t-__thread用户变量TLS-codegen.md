# LLVM-100t: `__thread` 用户变量的编与链（clang `TLSSupported` + 后端 `GlobalTLSAddress` lowering）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`INFRA-085t`（**登记源 + 消费方**：阶段 `D1` 的 ①③④ 已达成、② 「编译 `__thread` 用户变量」**BLOCKED 于 llvm 面** —— 完成区「D1-⑤ / D1-⑥②」+「遗留①」+「新发现/坑 ④」）；**契约真源** = `.tao/contracts/contract-dynlink.md §4.3`（类型 10/11/12/13 的公式与落点）+ `§7`（TLS 纳入 M8；TP 方向/偏置归 musl arch 宏）+ `§10②`（未支持类型遇即报错、不静默）、`.tao/contracts/contract-elf.md §2.2`（**静态类型表 0–5 + `ABS48`=6**，**无静态 TLS 类型**）+ `§6.1.2`（ELF 路径装载语义：头/程序头**不进** `PT_LOAD`）、`.tao/contracts/contract-abi.md §1.3`（`rb3` = `rbtp`（TP），M3 起保留不分配）；`ADR-0019 D10`/`D12`（类型集与编号，**冻结、不得增改**）、`ADR-0025 D5`（musl 硬依赖 TP ⇒ TLS 纳入 M8）、`ADR-0026 D2`/`D7②`（构建侧显式传 / 未支持类型遇即报错）；后端基线 = `LLVM-094t`（PIC/动态）、`LLVM-095t`（`PCREL_HI/LO`）、`LLVM-096t`（驱动/相对查找表/`stackrestore`）、`LLVM-097t`（`bswap`）、`LLVM-098t`、`LLVM-099t`（均已落地或已立）；纪律 = `ISS-229`（L2/L3 串行、禁并发）、`ISS-210`（改 `components/**`/`.td`/驱动 ⇒ **必单跑 `install-host`** 且禁「旧安装根自洽假绿」）、`docs/Process-01`（组件补丁树：一文件一补丁 + `series`）、`docs/Process-05`（L1/L2/L3）
**状态**：待开始

> **项目里程碑调整（2026-10-17，用户裁定）**：`M8` → **`M9`** —— 用户原话（**逐字**，渠道 = 经主会话问答）「**tls 可以推到 M9**」；`M8` 不要求 `dlopen`/模块级 TLS，`D2`（TLS 类动态重定位）亦已推迟 `M9+`。**范围 / 判据不变** ✗（本册其余内容照旧）。

> **口径**：本册判据 = **能编 + 静态可核**（**不跑**：运行归 `P3`/`QEMU-062t`）。`**状态**` 归主会话 `/complete`，本册**不自置**。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（**先读，勿重复查证**）

- 来源 = `INFRA-085t` 完成区（`2026-10-17`，阶段 `B1 + D1`）的「D1-⑤」「D1-⑥②」「新发现/坑 ④」「遗留①」+ 第 6 轮 engineer 自审 `F10`/`F11`；architect 立项 2026-10-17（主会话派单）。
- **现场事实（`INFRA-085t` 实测，证据不入库但本机留档）**：
  1. **clang 面**：`clang --target=dadao-unknown-elf -O1 -c thread_local.c` ⇒ **rc=1** + `error: thread-local storage is not supported for the current target`；根因 = `components/llvm-project/patches/clang/lib/Basic/Targets/DADAO.h` 的 `DADAOTargetInfo` 构造里 **`TLSSupported = false`**（注释「Freestanding: no TLS」）。
  2. **后端面**：绕过 Sema 直接喂 IR（`.work/evidence/INFRA-085t/b1d1/tls.ll`，`@tv = thread_local global i32 7`）给 `llc -filetype=obj` ⇒ **rc≠0** + `Cannot select: … GlobalTLSAddress`；`llvm/lib/Target/DADAO/**` **零** TLS 代码（`LowerOperation` 无 `ISD::GlobalTLSAddress` 分支、`DADAOISelDAGToDAG::Select` 只处理 `ISD::GlobalAddress`）。
  3. **已就位（不要重做）**：MC/汇编器**已**接受 `.tdata,"awT"`/`.tbss` 并产出 `SHF_TLS` + `STT_TLS`（`tls_seed.s`，`INFRA-085t` D1.3/D1.6 实测 `PT_TLS` p_filesz=8/p_memsz=16/p_align=8）；lld <u>无 scripted `PHDRS` 时</u>**自动**生成 `PT_TLS`；musl 侧 TP 宏已定值（`arch/dadao/pthread_arch.h`：`TLS_ABOVE_TP`、`GAP_ABOVE_TP 0`、`TP_OFFSET 0`、`DTP_OFFSET 0`；`reloc.h`：`TPOFF_K 0` + 类型 10/11/12/13 映射）。
  4. **安全网（现状、不得回退）**：`lld/ELF/Arch/DADAO.cpp` 对 `TLS_DTPMOD`/`DTPREL`/`TPREL`/`TLSDESC` **两处显式 `Err`**（`getRelExpr` + `relocate`，`INFRA-085t` D1.12 实测 2 sites）；`libc.so` 重定位直方图 `{6:33, 7:6, 8:2626}`、TLS 类 **0 命中**（D1.11/D1.11b）。
- **证据指针**：`.work/evidence/INFRA-085t/b1d1/{run.sh, probe_b1d1.py, thread_local.c, tls.ll, tls_seed.s}`；日志 `.work/log/infra/INFRA-085t-B1D1/{probe-default.log, probe-inject.log, build-shared.log}`（`probe-default.log` 末段 `D1.13`/`D1.14` = **BLOCKED** 记录，**不冒充绿灯**）。
- **参考来源说明**：本册自包含，不需外部仓库内容；如引用 `DADAO-0628` 只作「**内容溯源，非执行必需**」（只读 `.cache/refs/**`、不复制代码、不作执行依赖）。

## 目标

让 **`__thread` 用户变量**（C 层）在本 target 上**可编、可静态核**，即补齐 `INFRA-085t` 阶段 `D1②` 的 `llvm` 面缺口：

1. **clang 面**：`TLSSupported = true`（同源撤掉「freestanding ⇒ 无 TLS」的口径；TLS 已由 `ADR-0025 D5`/`contract-dynlink §7` 纳入 M8）；
2. **后端面**：`ISD::GlobalTLSAddress` 有 lowering —— 取址 = **TP(`rb3`) + TPOFF**，**大端**、`TP_OFFSET=0`/`GAP_ABOVE_TP=0`/`TLS_ABOVE_TP`（即 `TPOFF(sym) == DTPOFF(sym)`，无附加常数）；
3. **重定位面**：**先判**「local-exec（非 PIC/静态档）是否**无需** `R_DADAO_TLS_DTPMOD|DTPREL|TPREL`（10/11/12）动态发射」——若无需 ⇒ **本册不含 `D2`**（`D2` 已推迟 `M9+`，见「不做项 2」）；若判出**必须**新类型/改契约 ⇒ **停下留问**（见「待确认项 ②」），**不自行扩张**。

## 接口规范

- **输入**：现场复现（「做」阶段 0/A/B 的命令 + 期望/现状签名）；类型号与公式真源 = `contract-dynlink.md §4.3`（期望值**从合约表解析**，**不读实现反推**）+ `contract-elf.md §2.2`；TP 口径 = `contract-abi.md §1.3` + musl `arch/dadao/{pthread_arch.h,reloc.h}`（**只读**）；**只读**：`.work/source/llvm-project/**`（组件源检出，`check-source-state` 可 `git diff`）、`.dadao/cross-toolchain/**`（工具链 + sysroot）、`manifests/components.lock.toml`。
- **输出**：
  1. **组件补丁**：`components/llvm-project/patches/**`（**一文件一补丁**、镜像上游仓内路径，`docs/Process-01`）+ `series` 同步 + `components/llvm-project/changelog.md`（`Process-01 §10` 体例）；
  2. **证据**：`.work/evidence/<任务ID>/run.sh`（开工即落 `LLVM-100t`；一键、非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」、含 `--inject` 可达 FAIL）+ 原始输出落 `.work/log/llvm/<任务ID>/`；
  3. 本册完成区（≤30 行）+ 审阅记录；`milestones.md` 行由主会话/architect 收尾笔维护。
- **约束**：**最小改动**、只碰任务范围；**不得**改 `spec/`、`contracts/`、`.tao/contracts/**`（**须用户事先授权**）、`.cache/refs/**`；**不得**新增/改重定位类型编号（`ADR-0019 D10`/`D12` **冻结**；`NUM` = `16`）；**不得**打开 10/11/12 的**动态发射**（= `D2`，`M9+`）；组件源一律 **git 基线**（只经 `patches/**` 交付，**不得**把 `.work/source/**` 直改当交付）；**计数不写死**（现场派生）；期望值**独立**（合约/手算，不从 LLVM 读取器反推）。

## 做

> 复现统一在 **workdir（= 仓库根）** 内、相对路径；`<TC>` = 安装根 `cross-toolchain/bin`（`ADR-0016`，路径经 `manifests/` 定位、**不硬编码**）；`<TMP>` = `/tmp/opencode/LLVM-100t/`。**改 `components/**` ⇒ 单跑一次 `make install-host`**（**申报耗时**、`JOBS=8`、**禁全核**、**不与其他 L2/L3 并发** —— `ISS-229`/`ISS-210`）；改了 `.td`/MC/驱动 ⇒ **安装根必须新鲜**后才能跑运行期判据。

### 阶段 0（**先判性质，后动代码**）：local-exec 的 TPOFF **载体**

- **为什么要判**：`contract-elf.md §2.2` 的**静态**类型只有 `0`–`5` 与 `ABS48`=6、`14/15`；`10/11/12` 是**动态/TLS** 类型（`contract-dynlink §4.3` 的落点 = 8 字节槽，由 ldso 运行期填）。而 local-exec 的 TLS 取址需要在**链接期**把 `TPOFF(sym)` 塞进**指令/数据字段**。
- **候选（**不预设**，逐条给判据与后果）**：
  - **(甲) `ABS48`(6) 链接期解析在 `STT_TLS` 符号上**：ELF 里 `STT_TLS` 符号的 `st_value` = **TLS 块内偏移**；本 target `TLS_ABOVE_TP` + `GAP_ABOVE_TP=0` + `TP_OFFSET=0` ⇒ **`TPOFF(sym)` 数值上等于该偏移** ⇒ `ABS48` 的 `S+A` 直接可用。**代价**：`ABS48` 语义（`§2.2` = 绝对地址 / 无符号 48 位）被**复用**到 TP 相对偏移 ⇒ **须在册内写明理由**；**不得**据此改类型表。
  - **(乙) `TLS_TPREL`(12) 由 lld **静态**解析（local symbol 不入 `.rela.dyn`）**：**现状不允许** —— lld 两处显式 `Err`、且 `§4.3`/`§10②` 把它定义为**动态**类型；要走此路 ⇒ **等于提前打开 `D2`**（`M9+`）或**改契约语义** ⇒ **停、留问**。
  - **(丙) 新增静态 TLS 类型**：**禁止**（`ADR-0019 D10` 冻结；须用户裁定 + ADR）⇒ **停、留问**。
- **产出（写进完成区，逐条带证据）**：选定载体 + 选定理由（合约条款号/公式）+ **独立手算**一个 `__thread` 变量的 `TPOFF` 并核对产物字段；若判出必须 (乙)/(丙) ⇒ **停止实现、留问**（不得先做后补）。
- **可达 FAIL**：断言「产物里该访问站点**不**含类型 10/11/12/13」—— 现状（未实现）不适用；实现后由 `--inject` 把载体改回 (乙) 形态 ⇒ FAIL ⇒ `cp` + md5 还原 ⇒ 回绿。

### 阶段 A：clang `TLSSupported`

- **现状（读源码）**：`components/llvm-project/patches/clang/lib/Basic/Targets/DADAO.h` 构造里 `TLSSupported = false`（注释「Freestanding: no TLS, no thread-local storage support」）。
- **做**：改为 `true`（并**同源**订正该注释：TLS 已纳入 M8，见 `contract-dynlink §7`/`ADR-0025 D5`）；核对是否需同步 `MaxTLSAlign`/`getDataLayout` 的 TLS 相关项（**只做最小必要**，顺带改动须在完成区披露）。
- **复现（现状 rc=1）**：样例源**随本册自包含**（不必依赖别册 `.work/**`）——开工时按下面内容落 `<TMP>/thread_local.c`：
  ```c
  __thread int tv = 7;
  __thread int tz;

  int bump(void)
  {
      tv++;
      tz = tv + 1;
      return tv + tz;
  }
  ```
  ```
  <TC>/clang --target=dadao-unknown-elf -O1 -c <TMP>/thread_local.c -o <TMP>/thread_local.o
  ```
- **期望**：`-O0` 与 `-O2` **均 rc=0**；`-S` 文本可读且可 `llvm-mc` 往返（**大端**、`.tdata`/`.tbss` 就位）。
- **可达 FAIL**：`-O0`/`-O2` 任一 rc≠0（**现状即 FAIL**，天然可达）；对照断言 = `TLSSupported=false` 的注入副本仍报原错（证断言非恒真）。

### 阶段 B：后端 `GlobalTLSAddress` lowering（TP = `rb3`、大端）

- **现状（读源码）**：`DADAOISelLowering.cpp` 的 `LowerOperation` **无** `ISD::GlobalTLSAddress` 分支；`DADAOISelDAGToDAG.cpp` 的 `Select` 只接 `ISD::GlobalAddress`（含 PIC 的 `aip.si`/`ld.o` 通路）⇒ TLS 取址落到无 pattern 的 ISel（`Cannot select`）。
- **做（形态由实现定，判据看产物）**：`setOperationAction(ISD::GlobalTLSAddress, MVT::i64, Custom)` + `LowerOperation` 分支（照 AArch64/Hexagon 同款），**或**在 `DADAOISelDAGToDAG::Select` 里按 `GlobalAddress` 同法接（择一，册内说明）。**语义**：地址 = `TP + TPOFF`；`TP` = **`rb3`**（`contract-abi §1.3`；该寄存器在 `DADAORegisterInfo.cpp` 已 `Reserved`，只能显式读写、不得分配给虚拟寄存器）；`TPOFF` 的承载 = 阶段 0 选定的载体；**大端**逐字节核对（`.tdata` 初值、偏移）。
- **不做**：`initial-exec`/`global-dynamic`（GOT-TLS / `TLSDESC` / `DTPMOD`）= `D2` 面 ⇒ 若 `-fPIC` 下 `__thread` 仍不可编，**如实记录为已知限制**（不冒充完成）。
- **期望**：`__thread int tv = 7; __thread int tz;` 的 `tv++`/`tz = tv+1` 生成「读 TP + 加偏移」序列，偏移在 ET_REL 里是**重定位**而非写死常数；`.tdata` 8 字节 + `.tbss` 8 字节、`SHF_TLS`/`STT_TLS` 就位。
- **可达 FAIL**：把 lowering 分支回退成「无 pattern」⇒ `Cannot select` 复现 ⇒ FAIL；`cp` + md5 还原 ⇒ 回绿。

### 阶段 C：链接面（**仅在阶段 0 判为 (甲)/(乙-静态) 时**）

- **判据**：非 PIC 静态档 `__thread` 程序**能链**（或**有据**说明为何不能链）：
  - 用 **lld 默认布局**（无 scripted `PHDRS`）链接 ⇒ 期望 `PT_TLS` + 取址偏移**链接期解析**、**无** `TLS_DTPMOD|DTPREL|TPREL`(10/11/12) 动态项；
  - 用 `tests/scripts/dadao.lds`（**显式 `PHDRS`**）链接 TLS 对象 ⇒ 现状**响亮报错**（`has an STT_TLS symbol but doesn't have a PT_TLS segment`，`INFRA-085t` D1.9）⇒ **如实记录、本册不改 lds**（改 lds / 静态 auxv 归「待确认项 ①」，见下）。
- **不做**：静态 `__thread` 程序**运行**（crt 的 auxv 注入未做、`AT_PHDR` 语义受 `contract-elf §6.1.2` 约束）⇒ **跑归 `P3`**。

### 阶段 D：证据与门控

- `.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项 rc、含 `--inject`）+ 日志 `.work/log/llvm/<任务ID>/`；`--inject` 每条断言须有**可达 FAIL**路径，还原用 **`cp` 备份 + md5 对账**（**禁** `git checkout`/`restore`/`stash`）。
- 门控各留**自身**真实 rc（**禁** `cmd | tee` 吞码）：`make check`(L1)、`check-patch-tree`、`check-index-blobs`、`check-instrinfo`（若改 `.td`）、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-knowledge-dir`、`check-component-changelog`、`python3 tools/infra/check_issues.py`；**L2（`make check-modules`）任务收尾跑**（串行、禁与 L3 并发）。

## 验收标准

1. **`__thread` 变量源码 `-O0` 与 `-O2` 编译 rc=0**（`thread_local.c`：`__thread int tv = 7; __thread int tz;` + 读写函数；**`-fPIC` 不在本判据内**，见验收 6）。
2. **产物重定位/访问序列正确（按阶段 0 落纸的判定为准）**：① 若判为 (甲)/(乙-静态) ⇒ `readelf -r`（或自写 ELF64-BE 解析，**shipped 脚本不得依赖 `readelf`**：`ADR-0016 D11` 最小安装集无 binutils）看到**该载体类型正确落点**、**无** `TLS_DTPMOD|DTPREL|TPREL`(10/11/12)/`TLSDESC`(13)；② 若判为「走动态」⇒ **必须**先经用户裁定（`D2`），本册**不得**自行实现。**两种情形均须**给「类型号/公式取自 `contract-dynlink §4.3` 或 `contract-elf §2.2`」的**独立**期望值来源（非读实现反推）。
3. **大端 oracle**：`.tdata` 初值字节序、TLS 偏移、访问序列的立即数**独立手算**逐项对账（`ELFDATA2MSB`）；至少 1 个「非 0、非对齐友好」的初值/偏移使端序错误可见（达到 FAIL 路径）。
4. **可达 FAIL**：`.work/evidence/<任务ID>/run.sh` 可跑通（非交互、逐项打印期望/实际/rc、任一失败非零退出）；**每条断言有可达 FAIL 路径**（`--inject` ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），**禁恒真断言**、**禁** `git checkout/restore/stash` 还原、**计数不写死**。
5. **前置申报 `install-host`**：改 `components/**` ⇒ 单跑一次 `make install-host`（**开工前申报预计耗时**；参照 `LLVM-097t` ≈5–10 min 增量、`LLVM-091t` 全量 `build-mc` ≈72 min 的上界，按实际改动申报；`JOBS=8`、**禁全核**、**不并发**）；改 MC/`.td`/驱动 ⇒ 跑运行期判据**前**安装根必须新鲜（`ISS-210`），并留「安装根时间戳 / `clang --version` 版本串」证据。
6. **不回归**：① 静态档与非 PIC 产物**逐字节**对照（crt1.o / musl_smoke.elf 一类基线，差异须逐条归因）；② `libc.so` 与动态可执行（`INFRA-085t` B1 产物）**同形不变**；③ `-fPIC` 下 `__thread` 的现状（若仍败）**如实记录**为已知限制，**不得**为了让 `-fPIC` 过而打开动态 TLS 发射；④ 无 `spec/`/`contracts/`/`.tao/contracts/**` 改动（若判需改 ⇒ **留问**）。
7. **构建纪律与串行**：`ISS-229`（L2/L3 禁并发）、`ISS-210`（安装根新鲜）；组件源按 `docs/Process-01 §6.3/§6.4` 收敛（`.work/source` 可 `git diff`），补丁由 `check-patch-tree` 机械校验。
8. **不做运行验证（显式声明）**：无 `qemu-user`（`P3`/`QEMU-062t`）⇒ 完成区**不得**出现「运行通过 / E2E 通过」叙述；判据一律 = **能编 + 静态可核**。
9. **完成区与真实输出逐条对齐**（≤30 行）；`milestones.md` 流水行由收尾笔更新。

## 不做项（显式）

1. **`D2`（TLS 类动态重定位**发射**：`TLS_DTPMOD`=10/`DTPREL`=11/`TPREL`=12）** ✗ —— 已 **推迟 `M9+`**（2026-10-17 主会话决定、待用户追认；依据 = `D1` 已够 `M8`、`D2` 仅 `dlopen` 的模块级 TLS 需要；触发条件 = 引入 `dlopen`）。本册**只做 local-exec**。
2. **`TLSDESC`(13) / `COPY`(9) 发射** ✗（`§4.3` 明标「不发射」，lld 忍即报错）。
3. **lds / 静态启动 auxv** ✗：`tests/scripts/dadao.lds`·`dadao-dyn.lds` 的 `PHDRS`、`crt` 的 `AT_PHDR/AT_PHNUM/AT_PHENT` 注入、`contract-elf §6.1.2` 的装载语义 —— 一律归「待确认项 ①」（**须用户裁定**，且改契约**须授权**）。
4. **`infra`/musl 面** ✗：`tools/infra/build_musl.py`、`Makefile`、`components/musl/**`、`arch/dadao/{reloc.h,pthread_arch.h,__set_thread_area.s}`（现状已就位，本册**不改**）。
5. **`spec/`、`contracts/`、`.tao/contracts/**`、重定位编号** ✗（`ADR-0019 D10`/`D12` 冻结；改须用户裁定 + ADR）。
6. **运行验证 / `qemu-user` / 三套测试集** ✗（`P3`/`P4`）。
7. **`-fPIC` 的 TLS 访问模型（initial-exec / GOT-TLS）实现** ✗（= `D2` 面）；如 `-fPIC` 下 `__thread` 仍败 ⇒ 记录已知限制、不扩范围。
8. **`L3` 与里程碑判定** ✗（归主会话 / `/complete`）。

## 待确认项

| # | 项 | 我的默认（**待用户确认**） | 备选 / 影响 |
|---|---|---|---|
| ① | **静态 `__thread` 的启动 auxv 注入载体**（`INFRA-085t`「遗留②」原文三选项） | **不替用户定**（**主会话倾向 (b)**）。原文：**(a)** 扩 lds（`tls PT_TLS` + `.tdata/.tbss` + 把 ELF 头/phdr 放进可装载段 ⇒ **须授权改 `contract-elf §6.1.2`**）｜**(b)** crt 在 `.data` 合成 phdr 表（需 lds `PROVIDE` TLS 边界符号）｜**(c)** 其它。**现注**：**现在裁没有落点** —— 本册判据止于「能编 + 静态可核」，auxv 注入要等「TLS 程序的 lds 方案」落地才有执行面 ⇒ **随本册实施时一并裁**（届时按现场选定，且 (a) 必须先取得改 `contract-elf §6.1.2` 的**用户授权**） | 影响：静态 `__thread` 程序**能否运行**（`P3` 前置）；不改契约 ⇒ (a) 不可行 |
| ② | **阶段 0 若判出「必须新静态 TLS 类型 / 必须由 lld 动态发射 10/11/12」** | **停下留问**（**不自行扩类型、不改契约**）：`ADR-0019 D10` 冻结 ⇒ 新类型须用户裁定 + ADR；动态发射即 `D2`（`M9+`，另有触发条件） | 影响：本册范围/排期；若走 `D2` ⇒ 与 `dlopen` 排期绑定 |
| ③ | **`-fPIC` 下 `__thread`（initial-exec / GOT-TLS）的归属** | **不在本册**（= `D2`/`M9+`）；本册若遇 `-fPIC` 失败 ⇒ **如实记录**为已知限制（影响 `libc-test` TLS 用例与部分程序，**不阻塞 `P3`**） | 若要求本册一并覆盖 ⇒ 范围扩到 GOT-TLS + 10/11/12 发射（与 `D2` 冲突，须重排） |
