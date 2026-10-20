# LLVM-100t: `__thread` 用户变量的编与链（clang `TLSSupported` + 后端 `GlobalTLSAddress` lowering）

**模块**：llvm
**项目里程碑**：M9
**依赖**：**M9 线程链串行前置** = `INFRA-095t`（T1：`__clone` + TP，运行判据必需）、`QEMU-065t`（T2：qemu-user 线程语义）、`TESTCASES-052t`（T3：19 条 thread 用例收口；本册在其后开工）；`INFRA-085t`（**登记源 + 消费方**：阶段 `D1` 的 ①③④ 已达成、② 「编译 `__thread` 用户变量」**BLOCKED 于 llvm 面** —— 完成区「D1-⑤ / D1-⑥②」+「遗留①」+「新发现/坑 ④」）；**契约真源** = `.tao/contracts/contract-dynlink.md §4.3`（类型 10/11/12/13 的公式与落点）+ `§7`（TLS 纳入 M8；TP 方向/偏置归 musl arch 宏）+ `§10②`（未支持类型遇即报错、不静默）、`.tao/contracts/contract-elf.md §2.2`（**静态类型表 0–5 + `ABS48`=6**，**无静态 TLS 类型**）+ `§6.1.2`（ELF 路径装载语义：头/程序头**不进** `PT_LOAD`）、`.tao/contracts/contract-abi.md §1.3`（`rb3` = `rbtp`（TP），M3 起保留不分配）；`ADR-0019 D10`/`D12`（类型集与编号，**冻结、不得增改**）、`ADR-0025 D5`（musl 硬依赖 TP ⇒ TLS 纳入 M8）、`ADR-0026 D2`/`D7②`（构建侧显式传 / 未支持类型遇即报错）；后端基线 = `LLVM-094t`（PIC/动态）、`LLVM-095t`（`PCREL_HI/LO`）、`LLVM-096t`（驱动/相对查找表/`stackrestore`）、`LLVM-097t`（`bswap`）、`LLVM-098t`、`LLVM-099t`（均已落地或已立）；纪律 = `ISS-229`（L2/L3 串行、禁并发）、`ISS-210`（改 `components/**`/`.td`/驱动 ⇒ **必单跑 `install-host`** 且禁「旧安装根自洽假绿」）、`docs/Process-01`（组件补丁树：一文件一补丁 + `series`）、`docs/Process-05`（L1/L2/L3）
**状态**：待验收

> **项目里程碑调整（2026-10-17，用户裁定）**：`M8` → **`M9`** —— 用户原话（**逐字**，渠道 = 经主会话问答）「**tls 可以推到 M9**」；`M8` 不要求 `dlopen`/模块级 TLS，`D2`（TLS 类动态重定位）亦已推迟 `M9+`。**范围 / 判据不变** ✗（本册其余内容照旧）。

> **口径（T4 接线，2026-10-19 修订）**：本册仍以 **能编 + 静态可核** 为主体判据，并**新增运行验证**（阶段 E，**仅静态档 3 例**）—— 依据 = M9 线程链 T4 硬指标「`ISS-246` 的 `functional/{tls_align,tls_init,tls_local_exec}` 转 `pass`」；**动态 DSO TLS / `dlopen` 不在本册**（T5 `LLVM-117t`）。`**状态**` 归主会话 `/complete`，本册**不自置**。

> **M9 线程链 T4（用户 2026-10-19/20 裁定「添加 thread 相关支持，注意：rb3 应该被用起来」）**：串行链 **T1 `INFRA-095t` → T2 `QEMU-065t` → T3 `TESTCASES-052t` → T4 本册 → T5 `LLVM-117t`**。本册 = **静态 `__thread` 的 codegen + 静态档运行**；`rb3` 由 T1 的 `__clone`/`__set_thread_area` 真正承担 TP，本册的 `GlobalTLSAddress` 必须**显式读 `rb3`**（不得用任何其它寄存器/常量替代）。
>
> **T4 新增现场（2026-10-19，接到本册时必须先核）**：
> - `arch/dadao/crt_arch.h` 已改为 `_start` 从 **`rb1` 读装载器交付的初始栈**（`QEMU-062t` 落地）⇒ `AT_PHDR`/`AT_PHNUM`/`AT_PHENT` 可达、`static_init_tls` 能找到 `PT_TLS`；**原「静态 auxv 注入未做」的阻塞已消失**（「待确认项 ①」据此更新）。
> - 用户态链接按 `ISS-247` 裁定 = **lld 默认基址（最低 `PT_LOAD=0x10000`）**，**禁** `-T tests/scripts/dadao.lds`（该脚本显式 `PHDRS`，会吞 `PT_TLS`）。
> - 驱动 `tools/testcases/run_libc_test_user_suite.py` 的 `functional/tls_align` 在**静态档**通过 `EXTRA_CASE_SOURCES` 把 `functional/tls_align_dso.c` 编成**普通对象**（`.mk`: `tls_align-static.LDLIBS := tls_align_dso.o`）⇒ **local-exec**，正是本册范围；动态档同名用例链接 `.so`（需 10/11/12 发射）= **T5**。
> - ISA 链 `SPEC-152t`/`LLVM-116t`/`QEMU-064t` 已完成 ⇒ 工具链以当前安装根为准（`install-host` 新鲜）。

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
  - 用 `tests/scripts/dadao.lds`（**显式 `PHDRS`**）链接 TLS 对象 ⇒ 现状**响亮报错**（`has an STT_TLS symbol but doesn't have a PT_TLS segment`，`INFRA-085t` D1.9）⇒ **如实记录、本册不改 lds**（用户态禁 `-T dadao.lds`，`ISS-247`）。
- **不做**：静态 `__thread` 程序的**运行**在阶段 C 不做 —— 运行验证统一放 **阶段 E（T4 接线新增）**；阶段 C 只判「能链 + `PT_TLS` + 无 10/11/12 动态项」。

### 阶段 D：证据与门控

- `.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项 rc、含 `--inject`）+ 日志 `.work/log/llvm/<任务ID>/`；`--inject` 每条断言须有**可达 FAIL**路径，还原用 **`cp` 备份 + md5 对账**（**禁** `git checkout`/`restore`/`stash`）。
- 门控各留**自身**真实 rc（**禁** `cmd | tee` 吞码）：`make check`(L1)、`check-patch-tree`、`check-index-blobs`、`check-instrinfo`（若改 `.td`）、`check-source-state`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-knowledge-dir`、`check-component-changelog`、`python3 tools/infra/check_issues.py`；**L2（`make check-modules`）任务收尾跑**（串行、禁与 L3 并发）。

### 阶段 E：运行验证（**T4 接线新增**；静态档 3 例 + `_Thread_local` 探针）

- **前置**：阶段 A–D 的 codegen 已落地 + `make install-host` 新鲜（贴时间戳/`clang --version`）；T1/T2/T3 已验证（`__clone`/qemu 线程/19 条 047t 用例）。
- **E1 三例（静态档）**：用 T3 的驱动、`--link-mode static`、精确 filter：
  ```
  python3 tools/testcases/run_libc_test_user_suite.py --link-mode static \
    --filter '^functional/(tls_align|tls_init|tls_local_exec)$' \
    --work-dir /tmp/opencode/LLVM-100t/tls-static \
    --json-out /tmp/opencode/LLVM-100t/tls-static.json
  ```
  期望 **3/3 `pass`**、`fail=0`、exit 0：
  - `functional/tls_align`：TLS 块对齐（含 `tls_align_dso.o` 普通对象，local-exec）；
  - `functional/tls_init`：`.tdata` 初值在**静态启动**时被 `static_init_tls` 从 `PT_TLS` 复制/清零；
  - `functional/tls_local_exec`：local-exec 取址 = `TP + TPOFF`，多线程各自独立（本册至少单线程；多线程由 T1/T2 保证）。
- **E2 `_Thread_local` 探针（独立 oracle）**：自写 `tls_probe.c`（随本册自包含）：`_Thread_local int a = 0x12345678; _Thread_local int b;` + 两个线程分别写/读；期望：主线程 `a` 初值 = **`0x12345678`**（手写常量）、线程内 `&a` 与 `__get_tp()` 的差 = **手算 TPOFF**（`.tdata` 偏移 0 / `.tbss` 偏移 8，按 `readelf`/自写 ELF 解析核对）、两线程互不串值。**独立 oracle = 源码常量 + 手算偏移**，不从 clang/LLVM 内部读取。
- **E3 大端**：`.tdata` 文件字节 = **大端**（`0x12345678` ⇒ `12 34 56 78`）；`.tbss` 不占文件；TLS 访问立即数按大端解释。至少 1 个非对齐友好值（如 `0x0102030405060708`）使端序错可见。
- **可达 FAIL**：① 注入 `TLSSupported=false`（临时副本）⇒ E1/E2 编译失败；② 把 `GlobalTLSAddress` 的 TP 改成 `rb4`/常量 0（临时副本）⇒ E2 地址差 FAIL 或段错；③ 改 `.tdata` 初值/偏移的手算期望 ⇒ E2 对账 FAIL。三者均 `cp`+md5 还原回绿。
- **不做**：动态档 `tls_align`（`.so` 链接）/`tls_*_dlopen`/`tls_get_new-dtv` ⇒ **T5 `LLVM-117t`**；`-fPIC` 下的 general-dynamic/initial-exec 仍不在本册。

## 验收标准

1. **`__thread` 变量源码 `-O0` 与 `-O2` 编译 rc=0**（`thread_local.c`：`__thread int tv = 7; __thread int tz;` + 读写函数；**`-fPIC` 不在本判据内**，见验收 6）。
2. **产物重定位/访问序列正确（按阶段 0 落纸的判定为准）**：① 若判为 (甲)/(乙-静态) ⇒ `readelf -r`（或自写 ELF64-BE 解析，**shipped 脚本不得依赖 `readelf`**：`ADR-0016 D11` 最小安装集无 binutils）看到**该载体类型正确落点**、**无** `TLS_DTPMOD|DTPREL|TPREL`(10/11/12)/`TLSDESC`(13)；② 若判为「走动态」⇒ **必须**先经用户裁定（`D2`），本册**不得**自行实现。**两种情形均须**给「类型号/公式取自 `contract-dynlink §4.3` 或 `contract-elf §2.2`」的**独立**期望值来源（非读实现反推）。
3. **大端 oracle**：`.tdata` 初值字节序、TLS 偏移、访问序列的立即数**独立手算**逐项对账（`ELFDATA2MSB`）；至少 1 个「非 0、非对齐友好」的初值/偏移使端序错误可见（达到 FAIL 路径）。
4. **可达 FAIL**：`.work/evidence/<任务ID>/run.sh` 可跑通（非交互、逐项打印期望/实际/rc、任一失败非零退出）；**每条断言有可达 FAIL 路径**（`--inject` ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），**禁恒真断言**、**禁** `git checkout/restore/stash` 还原、**计数不写死**。
5. **前置申报 `install-host`**：改 `components/**` ⇒ 单跑一次 `make install-host`（**开工前申报预计耗时**；参照 `LLVM-097t` ≈5–10 min 增量、`LLVM-091t` 全量 `build-mc` ≈72 min 的上界，按实际改动申报；`JOBS=8`、**禁全核**、**不并发**）；改 MC/`.td`/驱动 ⇒ 跑运行期判据**前**安装根必须新鲜（`ISS-210`），并留「安装根时间戳 / `clang --version` 版本串」证据。
6. **不回归**：① 静态档与非 PIC 产物**逐字节**对照（crt1.o / musl_smoke.elf 一类基线，差异须逐条归因）；② `libc.so` 与动态可执行（`INFRA-085t` B1 产物）**同形不变**；③ `-fPIC` 下 `__thread` 的现状（若仍败）**如实记录**为已知限制，**不得**为了让 `-fPIC` 过而打开动态 TLS 发射；④ 无 `spec/`/`contracts/`/`.tao/contracts/**` 改动（若判需改 ⇒ **留问**）。
7. **构建纪律与串行**：`ISS-229`（L2/L3 禁并发）、`ISS-210`（安装根新鲜）；组件源按 `docs/Process-01 §6.3/§6.4` 收敛（`.work/source` 可 `git diff`），补丁由 `check-patch-tree` 机械校验。
8. **运行验证（T4 新增，限静态档）**：阶段 E 的 `functional/{tls_align,tls_init,tls_local_exec}` **3/3 `pass`**（`--link-mode static`、显式 `--json-out`/`--work-dir`）+ `_Thread_local` 探针（初值 = 手写常量、偏移 = 手算、两线程互不串值）；**动态档 DSO TLS / `dlopen` 不在本册**（T5）；完成区必须区分「静态运行通过」与「动态未做」。
9. **完成区与真实输出逐条对齐**（≤30 行）；`milestones.md` 流水行由收尾笔更新。

## 不做项（显式）

1. **`D2`（TLS 类动态重定位**发射**：`TLS_DTPMOD`=10/`DTPREL`=11/`TPREL`=12）** ✗ —— 已 **推迟 `M9+`**（2026-10-17 主会话决定、待用户追认；依据 = `D1` 已够 `M8`、`D2` 仅 `dlopen` 的模块级 TLS 需要；触发条件 = 引入 `dlopen`）。本册**只做 local-exec**。
2. **`TLSDESC`(13) / `COPY`(9) 发射** ✗（`§4.3` 明标「不发射」，lld 忍即报错）。
3. **lds / 静态启动 auxv 注入** ✗：`tests/scripts/dadao.lds`·`dadao-dyn.lds` 的 `PHDRS`、`contract-elf §6.1.2` 装载语义 —— **本册不改**；初始栈/auxv 已由 `QEMU-062t` 的 `crt_arch.h`（读 `rb1`）与 qemu-user 注入解决（「待确认项 ①」已消解）。
4. **`infra`/musl 面** ✗：`tools/infra/build_musl.py`、`Makefile`、`components/musl/**`、`arch/dadao/{reloc.h,pthread_arch.h,__set_thread_area.s}`（现状已就位，本册**不改**）。
5. **`spec/`、`contracts/`、`.tao/contracts/**`、重定位编号** ✗（`ADR-0019 D10`/`D12` 冻结；改须用户裁定 + ADR）。
6. **动态档 / `dlopen` 的运行验证** ✗：本册只跑**静态档 3 例**；`functional/tls_align` 动态档（`.so`）、`tls_{align,init}_dlopen`、`tls_get_new-dtv` 归 **T5 `LLVM-117t`**。
7. **`-fPIC` 的 TLS 访问模型（initial-exec / GOT-TLS）实现** ✗（= `D2` 面）；如 `-fPIC` 下 `__thread` 仍败 ⇒ 记录已知限制、不扩范围。
8. **`L3` 与里程碑判定** ✗（归主会话 / `/complete`）。

## 待确认项

| # | 项 | 我的默认（**待用户确认**） | 备选 / 影响 |
|---|---|---|---|
| ① | **静态 `__thread` 的启动 auxv 注入载体**（`INFRA-085t`「遗留②」原文三选项） | **已消解（2026-10-19 现场）**：`QEMU-062t` 已把 `arch/dadao/crt_arch.h` 的 `_start` 改为从 **`rb1` 读装载器交付的初始栈**（`rb2rb {rb16},{rb1}`），`AT_PHDR/AT_PHNUM/AT_PHENT/AT_BASE/AT_ENTRY` 由 qemu-user `create_elf_tables()` 注入 ⇒ **不再需要** (a) 扩 lds / (b) crt 合成 phdr / (c) 其它；本册**不改** `dadao.lds`、不改 `contract-elf §6.1.2`。若现场仍读不到 auxv，**停下报告**（归 qemu/装载面），不得在本册扩 lds。 | 影响：已无阻断；遗留 (a) 方案作废（保留为历史记录） |
| ② | **阶段 0 若判出「必须新静态 TLS 类型 / 必须由 lld 动态发射 10/11/12」** | **停下留问**（**不自行扩类型、不改契约**）：`ADR-0019 D10` 冻结 ⇒ 新类型须用户裁定 + ADR；动态发射即 `D2`（`M9+`，另有触发条件） | 影响：本册范围/排期；若走 `D2` ⇒ 与 `dlopen` 排期绑定 |
| ③ | **`-fPIC` 下 `__thread`（initial-exec / GOT-TLS）的归属** | **不在本册**（= `D2`/`M9+`）；本册若遇 `-fPIC` 失败 ⇒ **如实记录**为已知限制（影响 `libc-test` TLS 用例与部分程序，**不阻塞 `P3`**） | 若要求本册一并覆盖 ⇒ 范围扩到 GOT-TLS + 10/11/12 发射（与 `D2` 冲突，须重排） |

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-20）

范围：本轮全部改动（clang `Targets/DADAO.h`、`Driver/ToolChains/DADAO.cpp`；llvm `DADAOISelLowering.{h,cpp}`、`DADAOISelDAGToDAG.cpp`、`DADAOCodeGen.td`、`DADAOInstrInfo.cpp`；证据脚本 3 件；派生矩阵）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `INTRINSIC_WO_CHAIN` 置 `Custom` 用 `MVT::i64` 不生效（legalizer 以 `MVT::Other` 查 intrinsic action）⇒ `__builtin_thread_pointer` 仍 `Cannot select` | ✅已修 | 动作键改 `MVT::Other`，注释写明查表口径 | 探针汇编出现 `rb2rd {rd17}, {rb3}`；`PASS main.builtin_tp` |
| F2 驱动注释引用了不存在的诊断原文（`"PIC TLS is not supported"`） | ✅已修 | 改为「rejects it with an explicit diagnostic」 | 负控诊断实测 = `requires the local-exec TLS model`（证据 9c） |
| F3 `TargetLoweringBase::TM` 为 private，lowering 内直接 `TM.getRelocationModel()` 不成立 | ✅已修 | 改用 public `getTargetMachine().getRelocationModel()` | 重编译通过 + `-fPIC` 负控拒绝 |
| F4 证据脚本注入 9b 在「替换未生效」时可能假绿 | ✅已修 | 注入后校验 md5 变化 + 重建 rc + 探针 rc/FAIL 行 | `--inject` 19/19 全绿（先红后回绿） |
| F5 探针两线程各自 `printf` ⇒ stdout 行交错（实测 `expect=0xPASS 65` 拼接），日志不可解析 | ✅已修 | worker 只记观测值/地址，main `join` 后统一打印 | `probe.out` 逐行完整、`PROBE OK` |
| F6 `make check` 红：`check-isa-coverage` 派生矩阵随本次 ISel 改动失效 | ✅已修 | `gen_isa_coverage.py` 重派生 `tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（isel-cpp 20→21） | `gen_isa_coverage --check` PASS；`make check` rc=0 |
| F7 环境：`make build-builtins` stage 到 `<build>/lib/...`，门控读 `<build>/lib/clang/23/lib/...`（`Makefile:415` 与 `383/384` 派生不一致） | ✅已修（绕过 + 登记） | 按 install-host 同一目的路径手工 `cp` 两份（构建树资源目录 + 安装根）后 `build-musl-shared` 刷新戳记 | `check-builtins-freshness`/`check-musl-freshness` rc=0；坑记入完成区 |

判决：全部 finding 已修/已绕过，无未修项 ⇒ 可标「待验收」（`**状态**` 按派单不由 engineer 改）。

## 完成区

**测试结果**：证据脚本 **54/54** rc=0（`--inject` **19/19** rc=0）；L1 `make check` rc=0；`047t` 10 例静态 **10/10 pass**、动态 **7 pass + 3 TLS blocked**（无 pass→非 pass）；`046t` `crc32 -O2` pass；`check-lit` **118/118**。
**修改文件**：`components/llvm-project/patches/` 下 7 份（`clang/lib/Basic/Targets/DADAO.h`、`clang/lib/Driver/ToolChains/DADAO.cpp`、`llvm/lib/Target/DADAO/{DADAOISelLowering.h,DADAOISelLowering.cpp,DADAOISelDAGToDAG.cpp,DADAOCodeGen.td,DADAOInstrInfo.cpp}`，`series` 仍 82）+ `components/llvm-project/changelog.md`；`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（门控派生重生成）；`.tao/knowledge/issues.yaml`（ISS-246 notes 分解）；证据 `.work/evidence/LLVM-100t/{run.sh,tls_probe.c,tls_checks.py}`。组件源 HEAD = base+1、工作树干净。
**验收结果**：① `thread_local.c` `-O0`/`-O2` rc=0/0，`-S` = `set.zw rd4, wp0, tv` + `or.w rd4, wp1/wp2, tv` + `add.o rb4, rb3, rd4`，`.tdata,"awT"` / `.tbss,"awT"` 就位；ET_REL 仅 6×`R_DADAO_ABS48`（tv/tz），**0 条** 10/11/12/13。② 探针（独立 oracle，手算 0/8/16）：`main.a.init=0x12345678`、`main.wide.tpoff=0x8`、`main.b.tpoff=0x10`、`main.wide.plus2=0xa`、`main.builtin_tp` 与 `rb3` 一致；两线程 TP 不同（`0x…afd0` vs `0x…6fd0`）、各自 `a/wide/b` 回读正确、main 块不被改；`PROBE OK` exit 0。③ ELF：`PT_TLS` p_filesz=16/p_memsz=24/p_align=8；`.tdata` 字节 = `12345678 00000000 0102030405060708`（大端）；`st_value(a/wide/b)=0/8/16`、均 `STT_TLS`。④ `libc-test` 静态 `functional/{tls_align,tls_init,tls_local_exec}` **3/3 pass**；动态同 3 例 **blocked**，诊断 `requires the local-exec TLS model … dynamic TLS … not supported`（T5 面，未静默）。
**新发现/坑**：① 阶段 0 选 **(甲)**：ABS48 的 `S` 对 `STT_TLS` 符号 = TLS 块内偏移（lld `getSymVA` 对 TLS 返回 `va − PT_TLS.firstSection`），在 `TLS_ABOVE_TP`/`GAP_ABOVE_TP 0`/`TP_OFFSET 0` 下 = `TPOFF` ⇒ 零新类型；② `build-builtins` 的 build-tree staging 路径与 `check-builtins-freshness` 读取路径不一致（`Makefile:415` vs `383/384`）；③ builtins 归档跨构建非字节确定（`c96e…`→`fb1b…`），每次重建 clang 都要 builtins + `build-musl-shared` 重链；④ `__builtin_thread_pointer` 的 action 必须键 `MVT::Other`（`LegalizeDAG` 查表口径）；⑤ 每访问 4 条指令（3 片 ABS48 + `add.o`），未做 `ABS12` 折叠（±2 KiB，留作优化）。
**遗留问题**：① 动态 TLS（`-fPIC`/`-ftls-model=global-dynamic|initial-exec`）按设计**显式拒绝**，动态档 3 例 `blocked` ⇒ 归 T5 `LLVM-117t`；② 按派单未跑 `install-host`/L2/L3（运行期判据用构建树 `clang`/`ld.lld`）；③ `ISS-246` `status` 保持 `open`（notes 已记静态/动态分解）。

#### 第 1 轮 architect 提交审核（2026-10-20）

- **档位**：`待验收`（engineer 返回、reviewer 判决前）⇒ **正常提交**（按派单「提交 `LLVM-100t/T4`」）。**提交号 `0ecb976`**（内容提交；本注为随后一笔留痕，落地 `master` 时与内容一并 `merge --squash`）；落 `LLVM-100t` 分支；**未 push**。
- **状态/台账改动（architect 现场）**：本册 `**状态**` `待开始 → 待验收`（engineer 按派单不自置）；`milestones.md` 两处同步（流水行状态 + 一句改动，现 **90** 字符 ≤120；清单行）。
- **文件集对账**（`git diff --cached --name-only`，**显式 staging 13 项**、禁 `git add -A`）：
  - 与完成区「修改文件」逐条相符：`components/llvm-project/patches/**` **7** 份、`components/llvm-project/changelog.md`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`、`.tao/knowledge/issues.yaml`、本册。
  - **多提 1 项**：`.tao/knowledge/milestones.md`（architect 职责内，见上）。
  - `issues.yaml` 内含 **architect 侧新增 `ISS-301`**（`P2` / `open` / `scope: [infra]`）：`build-builtins` 的 re-stage 目标（`Makefile:415` ⇒ `.work/build/llvm/lib/dadao-unknown-unknown-elf/...`）与门控/`install-host` 读取目标（`383/384` ⇒ `.../lib/clang/23/lib/...`）**不一致**，本轮靠手工 `cp` 兜底；另「归档跨构建非字节确定」（`c96e…`→`fb1b…`，现盘 `cb77…`）待查清。**该坑已在本册 `F7` + 完成区「新发现/坑 ②③」写明**（已核）。
  - **漏提 / 越界**：无（`spec/`、`contracts/`、`tools/` 其它、`tests/` 零改动）。**注意**：完成区列出的 `.work/evidence/LLVM-100t/{run.sh,tls_probe.c,tls_checks.py}` 为**非跟踪**产物（`.gitignore:2` = `.work/`），不入库（证据留本机）。
- **核验（现场复跑）**：`check-patch-tree` **5 组件 / 184 patches OK** rc=0（与 changelog「series 仍 82、184 不变」一致）；`check_issues.py` rc=0（**56 open / 17 closed**，`resolved_by` 约束 OK）；`check_milestones_fresh.py` rc=0（11 行、状态一致/覆盖/≤120/倒序/格式）；`check-builtins-freshness` rc=0（三副本同 sha `cb77…`，即本轮 `cp` 兜底生效）；**`make check`（L1）rc=0，34.7 s**（日志 `/tmp/opencode/LLVM-100t/make-check-architect.log`）。
- **披露（已核、不改写）**：① `ISS-246` 保持 `open`（静态已由本册收口、动态归 `LLVM-117t`）；② 本轮**未** `install-host`/L2/L3（按派单禁）；③ `ISS-301` 为本轮新登记，修法未做。

#### 第 1 轮 reviewer 验收（2026-10-20）

**重跑记录**（全部在 master=f3ac4b4、工作树干净下执行）：
- `run.sh` default：rc=1（11 红）。**核心断言全绿**：A 编译 O0/O2/S rc=0、asm add.o rb3、obj reloc 仅 ABS48 无 10-13、E2 探针 PROBE OK（a.init=0x12345678、wide.tpoff=0x8、b.tpoff=0x10、builtin_tp rb3、两线程 TP 不同）、E3 ELF PT_TLS 16/24/8 + tdata BE image 正确、E1 静态 3/3 pass、047t 静态 10/10、046t crc32 pass。**11 红均为外部状态变化**：(a) T5 落地后 `-fPIC`/`-ftls-model=global-dynamic` 不再被拒绝（9c 负控 4 红）+ 动态档 TLS 3 例 blocked→pass（T5 节 3 红 + 047t 动态 2 红）；(b) `check-lit` 121 例中 inline-asm-m 系列 3 红 = 安装根 llc 崩溃（rc=134 断言），**实测归因**：`77153a2 LLVM-119t`（inline-asm-m 崩溃修复）晚于安装根 llc mtime（04:27 vs 提交 07:54），build-tree llc 08:27 含修复且 rc=0 ⇒ 安装根滞后，非本册回归。
- `run.sh --inject`：rc=1（4 红 = 同源 9c 负控 + lit.installroot）。注入自身 9a/9b 全绿（inject→FAIL→cp+md5 还原→回绿）。
- 独立注入：改 `tls_checks.py` 的 `b.value` 期望 16→24 ⇒ `FAIL exe.sym.b.value expect=24 actual=16`；还原 md5 对账 YES + 回绿（全 PASS, rc=0）。
- `make check`(L1)：rc=0。
- `git status --porcelain`：空（工作树干净）。
- `git log --oneline faa472f^..292c54a -- components/musl`：**0 commits**（musl 零改动 ✓）。

**约束核验**：① TLSSupported=true ✓；② 非 PIC 默认 local-exec ✓；③ TLS_OFFSET 3 片 ABS48 + add.o rb,rb3,rd ✓；④ `llvm.thread.pointer` ⇒ rb3 ✓；⑤ 探针 0/8/16 ✓；⑥ 两线程互不串 ✓；⑦ `.tdata`/`.tbss` SHF_TLS+STT_TLS ✓；⑧ 100t 范围无 10/11/12/13 ✓；⑨ 静态 047t 3/3 pass ✓；⑩ 动态 3 例 blocked（设计如此，已由 117t 收口）。

**判定：Accepted**。T4 核心交付全部达标；run.sh 11 红均为 T5 落地 + 安装根滞后所致（外部状态变化，非本册缺陷）；独立注入红→还原→绿通过。证据脚本需随 T5 集成更新期望值（非阻塞，归主会话收尾）。

