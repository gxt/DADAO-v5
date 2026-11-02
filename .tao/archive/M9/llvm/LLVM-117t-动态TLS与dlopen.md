# LLVM-117t: 动态 TLS（`DTPMOD`/`DTPREL`/`TPREL`）+ `dlopen`（线程链 T5）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`LLVM-100t`（T4：静态 `__thread` + `rb3` TP；**必须已验证**）、`TESTCASES-052t`（T3：线程用例收口）、`QEMU-065t`（T2：qemu-user 线程语义）、`INFRA-085t`（`D2` 的登记源与 `lld` 两处 `Err` 现场）、`TESTCASES-047t`（动态档驱动/4 条 `excluded`）、`INFRA-093t`（`--json-out`/`--work-dir`）
**状态**：已验证

> **编号（现场取号，2026-10-19）**：`llvm` 现存最大 = `LLVM-116t` ⇒ 取 **`117`**（`grep -rn 'LLVM-117' .tao/` 0 命中）。
> **线程链位置（T5）**：串行链 **T1 `INFRA-095t` → T2 `QEMU-065t` → T3 `TESTCASES-052t` → T4 `LLVM-100t` → T5 本册**。
> **跨模块披露（用户已裁定 T1–T5 链，本册不拆册）**：本册核心 = `llvm` 面（`lld` 发射 10/11/12 + 编译期 TLS 访问模型）；同时**必须**触及 **`infra` 面**（`components/musl/**` 的 ldso/TLS 运行时，若现场证明必要）与 **`testcases` 面**（`tools/testcases/run_libc_test_user_suite.py` 的 per-case DSO helper 构建与 4 条 `excluded` 撤除）。三面改动**同一册**交付，完成区须逐项分面列明；**不改** `spec/`/`contracts/`/`.tao/contracts/**`。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（先读，勿重复查证）

- **`D2` 的真缺口**：`INFRA-085t` 阶段 `D1` 明确把「TLS 类动态重定位**发射**（`TLS_DTPMOD`=10 / `DTPREL`=11 / `TPREL`=12）」推迟到 `M9+`，触发条件 = **引入 `dlopen`**（完成区「待确认项 ⑦ / 不做项 7」）；用户 2026-10-17 裁定「`ISS-260:1`」= M8 维持排除、随 `M9` 收编。
- **lld 现状 = 两处显式 `Err`**：`components/llvm-project/patches/lld/ELF/Arch/DADAO.cpp.patch` 的 `getRelExpr`（约 `:313-322`）与 `relocate`（约 `:549-558`）对 `R_DADAO_TLSDESC`(13) / `TLS_DTPMOD`(10) / `TLS_DTPREL`(11) / `TLS_TPREL`(12) 报错；`COPY`(9) 亦按 `contract-dynlink §10②` 不发射。T4 后 `libc.so` 的重定位直方图仍应 **TLS 类 0 命中**（本册必须改变的是「TLS 程序/DSO」的产物，而非 `libc.so` 本身）。
- **契约公式（独立 oracle 真源）**：`contract-dynlink §4.3` 表 — `10` = `DTPMOD` = **定义该符号的模块** `tls_id`（加载器分配、**≥1**、8 字节槽）；`11` = `DTPREL` = **`DTPOFF(sym) + A`（补码）**；`12` = `TPREL` = **`TPOFF(sym) + A`（补码，可负）**；`13` = `TLSDESC` **不发射**。编号冻结 = `ADR-0019 D10`/`D12`（`NUM`=16；`14/15` = 静态配对）；`§10②` = 未支持类型遇即报错、不静默；`§7` = TLS 纳入、TP 方向/偏置归 musl arch 宏。
- **musl 运行时已就位（先核，不重复实现）**：`arch/dadao/reloc.h` 已把 `REL_DTPMOD`/`REL_DTPOFF`/`REL_TPOFF`/`REL_TLSDESC` 映射到 10/11/12/13，`TPOFF_K=0`；`arch/dadao/pthread_arch.h` = `TLS_ABOVE_TP`、`GAP_ABOVE_TP=0`、`TP_OFFSET=0`、`DTP_OFFSET=0`；`src/thread/__tls_get_addr.c` 与 `ldso/dynlink.c` 的 DTV/TLS 分配走 musl 通用路径。**若**现场证明 DADAO 的 `TP_ADJ`/DTV 布局需要 arch 补丁，才改 musl（infra 面，最小化并披露）。
- **驱动现状（testcases 面）**：`tools/testcases/run_libc_test_user_suite.py` 的 `STRUCTURAL_EXCLUSIONS`（静态档）与 `DYNAMIC_EXCLUSION_REASONS`（动态档）把 4 条列为 `excluded`：`functional/dlopen.c`、`functional/tls_align_dlopen.c`、`functional/tls_init_dlopen.c`、`regression/tls_get_new-dtv.c`；`EXTRA_CASE_SOURCES` 只覆盖 `functional/tls_align` 的 DSO 对象，**不构建 per-case `.so`**；`functional/tls_align` 动态档需要 `tls_align_dso.so`（现由排除表外的方式未构建）。非 TLS DSO 探针（`dlopen_dso.so` + `dlsym`）实测 exit 0 ⇒ 装载能力在位，缺的是 **DSO 构建 + TLS 重定位发射**。
- **4 条用例的 `.mk` 依赖（现场）**：`dlopen.mk` → `dlopen_dso.so`（`-rdynamic`）；`tls_align.mk` → `tls_align_dso.so`（动态）/ `.o`（静态）；`tls_init_dlopen.mk` → `tls_init_dso.so`；`tls_get_new-dtv.mk` → `tls_get_new-dtv_dso.so` + `-Wl,-rpath='$ORIGIN'`。
- **前置运行面**：T2 已保证 `clone`/TP/futex/信号；T4 已保证 `__thread` 编出 + 静态运行；T5 在此之上跑**动态档**。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/lld/ELF/Arch/DADAO.cpp.patch`、`lld/ELF/Relocations.cpp`/`Arch/DADAO.h` 相关现状（只读源 `.work/source/llvm-project/**`，可 `git diff`）；
  - `components/musl/patches/**`（只读现状；若需改，按 `docs/Process-01` 一文件一补丁 + `series` + `changelog.md`）；
  - `tools/testcases/run_libc_test_user_suite.py`（只读现状；本册可改其 DSO 构建/排除表）；
  - `contract-dynlink §4.3`/`§7`/`§10②`、`contract-elf §2.2`、`ADR-0019 D10`/`D12`、`ADR-0025 D2`（`M9` 收编）、`ADR-0026 D2`（构建侧显式 `-dynamic-linker`）。
- **输出**：
  1. **lld**：10/11/12 的 `getRelExpr` + `relocate` 实现（8 字节槽、大端写、补码偏移；`DTPMOD` 的模块 id 语义按 `§4.3`）；**保留** `TLSDESC`(13)/`COPY`(9) 的显式报错；静态/local-exec 链路（T4）**不回归**。
  2. **musl（仅当必要）**：DTV/TLS 运行时最小补丁（若通用 `dynlink.c` 已够 ⇒ **0 改动**，完成区须给出「为何 0 改动」的现场证据）。
  3. **驱动（testcases 面）**：按各 `.mk` 构建 per-case DSO helper（`-fPIC -shared`；`dlopen` 主程序 `-rdynamic`；`rpath=$ORIGIN`）；**动态档**撤除 4 条 `excluded`（静态档保持 `dlopen` 无 loader 的排除）；`functional/tls_align` 动态档链接 `.so`。
  4. `.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项 rc、含 `--inject`）+ 日志 `.work/log/llvm/LLVM-117t-*.log`；
  5. 本册完成区（≤30 行，**分 llvm/infra/testcases 三面**）+ 审阅记录。
- **约束（硬）**：
  - **类型号/公式冻结**：不得新增/改号（`ADR-0019 D10`/`D12`）；不得把 `TLSDESC`/`COPY` 放开；
  - **不改** `spec/`、`contracts/`、`.tao/contracts/**`、`.cache/refs/**`；**不改** 语料（`libc-test` patchless）与期望值；
  - 改 `components/llvm-project/**` ⇒ **必单跑 `make install-host`**（先申报耗时；`JOBS=8`、禁全核；不并发 L2/L3 —— `ISS-229`/`ISS-210`）；改 musl ⇒ `make build-musl-shared` 并复跑静态不回归；
  - 期望值独立：`DTPMOD`/`DTPREL`/`TPREL` 的数值由**手算 + 合约表**给出，不从 `lld`/`llvm-readobj` 反推；DSO 的 TLS 偏移由源码布局/链接脚本手算；
  - 4 条用例若失败，按**首错**分类；不得用「扩 `excluded`」或「改 `known-fail`」掩盖；失败现场保留。

## 做

### 阶段 0：前置与基线

- 核 T1–T4 已验证；安装根新鲜（`clang --version`、`ld.lld --version`、时间戳）。
- 基线（期望失败/排除）：动态档跑 4 条 filter ⇒ 现为 `excluded`（或链接期 `TLS_*` 报错）；记录现场。`functional/tls_align` 动态档 ⇒ 当前链接失败（缺 `.so` 或 10/11/12 被拒）。
- 用 `llvm-readobj -r` 对一个最小 `-fPIC -shared` TLS DSO（`__thread int tv=7; int *f(){return &tv;}`）记录现状错误串（`TLS dynamic relocation ... has no dynamic expression` / 两处 `Err` 之一）。

### 阶段 A：lld 发射 10/11/12

- **A1 `getRelExpr`**：为 `R_DADAO_TLS_DTPMOD`/`DTPREL`/`TPREL` 返回正确的动态表达式（DTPMOD = 模块基址类；DTPREL/TPREL = 符号 TLS 偏移类）；保留 `TLSDESC`/`COPY` 的 `Err`。
- **A2 `relocate`**：写 8 字节、**大端**（`write64be`/等价），`DTPREL = DTPOFF(sym)+A`、`TPREL = TPOFF(sym)+A`（补码）；`DTPMOD` = 定义模块的 `tls_id`（主程序/DSO 场景分别核对；DSO 的模块 id 由 ldso 在加载时分配，链接期槽值/重定位语义按 `§4.3`）。
- **A3 静态/local-exec 不回归**：T4 的静态 3 例 + `_Thread_local` 探针复跑；静态 ELF 的 TLS 访问**不得**新出现 10/11/12（仍走 T4 选定载体）；`libc.so` 重定位直方图仍为 `{6,7,8}`（TLS 类 0）除非 musl 自身新增 TLS DSO（不应发生）。
- **A4 链接期失败面**：未定义 TLS 符号、`TLSDESC`、`TP` 越界 ⇒ 显式 `Err`（`§10②`）；贴真实错误串。

### 阶段 B：musl 运行时（先判后改）

- 用 A1/A2 产物链一个最小 `libtls.so` + 主程序 `dlopen`/`dlsym`，在 `qemu-dadao` 跑：期望 `tv` 初值正确、`&tv` 在 DSO 的 TLS 块内、两线程各自独立。
- 若失败：定位是 **DTV 分配/`__tls_get_addr`/`TP_ADJ`/`DTP_OFFSET`** 哪一环；只有确认通用 `dynlink.c` 不适用时才改 musl（最小补丁 + `changelog.md`）；若需改 `arch/dadao/pthread_arch.h` 的 TLS 宏 ⇒ **先核对契约 `§7` 是否允许**（现为 `TLS_ABOVE_TP`/`GAP=0`/`TP_OFFSET=0`/`DTP_OFFSET=0`），改宏即改 ABI 口径 ⇒ **停下报告**（须用户裁定）。
- 验收：**DSO 级 TLS** 与 **主程序级 TLS** 并存时互不覆盖；`dlopen` 后新 DTV 槽（`tls_get_new-dtv`）正确。

### 阶段 C：驱动 DSO helper + 撤除动态档排除

- 在 `tools/testcases/run_libc_test_user_suite.py` 按 `.mk` 建 per-case DSO：
  - `functional/dlopen.c` → `dlopen_dso.so`（主程序 `-rdynamic`）；
  - `functional/tls_align.c`（动态）→ `tls_align_dso.so`；
  - `functional/tls_align_dlopen.c` → `tls_align_dso.so`；
  - `functional/tls_init_dlopen.c` → `tls_init_dso.so`；
  - `regression/tls_get_new-dtv.c` → `tls_get_new-dtv_dso.so` + `-Wl,-rpath='$ORIGIN'`。
- **只撤动态档** 4 条 `excluded`；静态档 `dlopen`/`*_dlopen`/`tls_get_new-dtv` 仍按「无动态装载器」排除（`tls_align` 静态档已由 T4 走 `.o`）。
- DSO 命名/路径与上游 `t_pathrel`/`$ORIGIN` 约定一致；构建失败时**不得**退回 `excluded` 掩盖，按首错定位。

### 阶段 D：4 条用例 + 动态档回归

- 目标 filter：`^functional/(dlopen|tls_align|tls_align_dlopen|tls_init_dlopen)$|^regression/tls_get_new-dtv$`，动态档；期望 **5/5**（4 条原 `excluded` + `tls_align` 动态）`pass`。若某条有据不可达 ⇒ 按首错**分类**（`blocked`/`known-fail` 须有合约/上游依据），并在完成区分条说明；**不得**静默扩排除。
- 全量动态档（不带 filter）逐例对账 T3 基线：除目标 5 条外 **0 条 `pass→non-pass`**；`excluded` 数从 30 → 26（仅撤 4 条）；`known-fail` 仍 4（TLS 3 已由 T4 转 pass？——以 T3/T4 实际为准：T4 后 `known-fail` 应从 4 → 1（仅 `strptime`），本册须按最末一轮现场基线对账，**不写死**）。
- 静态档复跑（至少 4 条 filter + `tls_align`）确认未被驱动改动破坏。

### 阶段 E：证据、issue、门控

- `.work/evidence/<任务ID>/run.sh`，**≥2 条可达 FAIL**：
  1. 注入「把 `relocate` 的 10/11/12 改回 `Err`」（临时副本）⇒ DSO 链接/运行 FAIL；`cp`+md5 还原 ⇒ 回绿；
  2. 注入「DTPREL 不做补码/写成小端」⇒ 手算偏移对账 FAIL（或 `tv` 值错）；还原 ⇒ 回绿；
  3. 可选：把 DSO helper 构建移除 ⇒ 目标用例回到 `excluded`/链接失败 ⇒ 断言 FAIL。
- `ISS-260` 关闭（`resolved_by: LLVM-117t`）；`ISS-246` 若 T4 已关则追加交叉引用，未关则一并收口（以 T4 状态为准）。
- 门控各留 rc：`make check`（L1）、`check-patch-tree`、`check-component-changelog`、`check-source-state`、`check-instrinfo`（若改 `.td`）、`check-isa-coverage`、`check-no-residue`、`check-tasks`、`check-issues`；任务收尾 `make check-modules`（L2，串行）。

## 验收标准

1. **lld 发射正确**：最小 `-fPIC -shared` TLS DSO 的 `llvm-readobj -r` 出现 `R_DADAO_TLS_DTPMOD`/`DTPREL`（或 `TPREL`，按访问模型）且**不再报错**；`TLSDESC`/`COPY` 注入例仍显式 `Err`（非静默）。公式与 `contract-dynlink §4.3` 逐条一致，并用**手算**的 `DTPOFF`/`TPOFF` 对账（独立 oracle）。
2. **TLS 值语义**：`dlopen` 的 DSO 中 `__thread` 变量初值正确、地址落在其 TLS 块、两线程互不串值；`tls_get_new-dtv` 的 `dlopen` 后新 DTV 槽正确；主程序与 DSO 的 TLS 并存不覆盖。
3. **4 条 `ISS-260` 用例**：`functional/dlopen`、`functional/tls_align_dlopen`、`functional/tls_init_dlopen`、`regression/tls_get_new-dtv` 动态档 **`pass`**（或逐条有据分类，依据须为合约/上游 `.mk`，不得自定义）；`functional/tls_align` 动态档同时 `pass`。
4. **无回归**：T3 基线逐例对账 — 目标外 0 条 `pass→non-pass`；`excluded` 仅少 4 条（30→26）；静态档复跑不回归；`libc.so` 的 TLS 类重定位仍 0（除非有据的新 DSO）；`check-isa-coverage` 不受影响。
5. **`ISS-260` 关闭**：`issues.yaml` `resolved_by: LLVM-117t`；`check_issues.py` rc=0；`ISS-246` 状态与 T4 一致。
6. **可达 FAIL ≥2**：证据脚本两条注入「FAIL → `cp`+md5 还原 → 回绿」；禁恒真、禁 `git checkout/restore/stash`。
7. **前置 `install-host`**：改 `components/llvm-project/**` 后单跑 `install-host`（申报耗时、`JOBS=8`），贴 `ld.lld --version` + 时间戳；改 musl 后 `build-musl-shared` + 静态不回归。
8. **边界与分面**：`spec/`/`contracts/`/`.tao/contracts/**`/语料/期望值 0 改动；llvm/infra/testcases 三面改动逐项列明；不提交 git、不 push；完成区 ≤30 行并与真实输出逐条对齐。

## 不做项（显式）

1. **新增/改重定位类型编号** ✗（`ADR-0019 D10`/`D12` 冻结；`NUM`=16）。
2. **`TLSDESC`(13) / `COPY`(9) 发射** ✗（`§4.3`/`§10②`；遇即报错）。
3. **`-static-pie` / `rcrt1.o` 的 `_DYNAMIC` 绝对地址** ✗（`ISS-245`，独立项）。
4. **静态档 `dlopen`** ✗（无动态装载器，结构性排除保持）。
5. **`spec/` / 契约 / 用户裁定外的 ABI 宏** ✗（改 TP 方向/偏置须用户裁定 + ADR）。
6. **`ISS-257`/`255` 的 `RLIMIT_AS` 虚拟化、宿主信号族** ✗（qemu 独立项）。
7. **里程碑 / L3 判定** ✗（归主会话 / `/complete`）。

## 完成区

**测试结果**：① 动态档目标 5 例（`functional/{dlopen,tls_align,tls_align_dlopen,tls_init_dlopen}` + `regression/tls_get_new-dtv`）**5/5 pass**，`excluded` **30 → 26**；② 全量动态档 341 例 **pass 338 / fail 0 / known-fail 1（`strptime`=ISS-251）/ blocked 2**（`musl/pleval` 既有动态档链接缺口、`regression/flockfile-list`=ISS-255）；与 2026-10-19 基线逐例对账 **0 条 pass→非 pass**、**26 条非 pass→pass**；③ `047t` 10 例（3 TLS + 7 线程）**两档 10/10**（3 例 TLS 动态档 blocked→pass）；④ `make check-lit` **118/118**、`check_lit_gen` **64/64**、`make check`（L1）**rc=0**、证据脚本 **PASS（46 checks，含 2 处可达 FAIL）**。
**修改文件**：`components/llvm-project/**`（14 补丁改 + 新增 `patches/lld/ELF/InputSection.cpp.patch`；`series` 82→83、`check-patch-tree` 184→185）+ `changelog.md`；`tools/testcases/run_libc_test_user_suite.py`；`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（补丁行号位移后 `gen_isa_coverage.py` 重派生）；`.tao/knowledge/issues.yaml`（`ISS-246`/`ISS-260` → `closed`）。**`components/musl/**` 0 改动**。
**验收结果**：① 发射：`dso.o` `.rela.got` = `0x0 R_DADAO_TLS_DTPMOD tv` / `0x8 R_DADAO_TLS_DTPREL tv` / `0x10 R_DADAO_ABS48 .Lgot.0`，`.rela.text` 有 `R_DADAO_PCREL_HI .got 0x10` + `R_DADAO_REL26 __tls_get_addr`；② 消费：`libtv.so` `.rela.dyn` = `0x20400 R_DADAO_TLS_DTPMOD tv` / `0x20408 R_DADAO_TLS_DTPREL tv` / `0x20410 R_DADAO_RELATIVE - 0x20400`；非抢占符号（DSO 内 `static __thread`）= `R_DADAO_TLS_DTPMOD - 0x0` / `- 0x4`（无符号、addend=手算 DTPOFF），运行 `stv=5 sum=6` exit 0；③ 运行（独立 oracle）：`RESULT OK dso=0x7fb8dc7789d0 t1=0x7fb8dc53ebcc t2=0x7fb8dc4dabcc main=11`（DSO 初值 7→99 可写、两线程各自独立、与主程序块不重叠、主程序 `__thread`=11 不被覆盖）；initial-exec：`x=21 y=22 xoff=0 yoff=4` exit 0（`.rela.dyn` 仅 `R_DADAO_TLS_TPREL itv`）；静态档产物仍 **0 条** 10/11/12；④ 门控 rc=0：`check-patch-tree`/`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-musl-freshness`/`check-builtins-freshness`/`check-issues`/`check-run-artifacts`/`check-instrinfo`/`check-isa-coverage`/`make check`。
**新发现/坑**：① **`__tls_get_addr` 的参/返回值必须是 pointer IR 类型**——`LowerCallTo` 的 `isPointer` 由 IR 类型（`ArgTy->isPointerTy()`）设置，用 `i64` 会让 `CCIfPtr` 不命中 ⇒ 参数落 `rd16`、返回值取 `rd8`（运行期读到垃圾指针、qemu 崩）；RISC-V 模板用 `IntegerType` 是因为它没有 bank 区分。② lld 的**输入侧 TLS 槽**不能走泛型 `processAux`：`R_TPREL` 不在 `isRelExpr()` 里 ⇒ `isStaticLinkTimeConstant` 对 shared 也返回 true（会把 DSO 的 TPOFF 静默定死）；必须像 RISCV/X86_64 那样覆写 `scanSection`。③ `getTlsTpOffset` 的 `switch (emachine)` 对 `EM_DADAO` 是 `llvm_unreachable`（`ADR-0029` 时无人走），链接期常量 TPREL 一用就打到 —— 需补 Variant 1 无 gap 分支。④ shared 里**非抢占** TLS 符号不能发带符号动态项（local STT_TLS 不在 `.dynsym`），须走 `addAddendOnlyRelocIfNonPreemptible`（符号置零 + addend= DTPOFF，musl 用 `def.dso` 自身补齐）。⑤ DSO 的 TLS 槽若由编译器自造，必须把「对地址」再放一个普通 ABS48 指针槽（`PCREL_LOAD` 只能取槽内容，取不到「对地址」）。
**遗留问题**：① 按派单**未跑** `install-host`/`build-qemu`/L2/L3（运行期用构建树 `clang`/`ld.lld` + 安装根 `qemu-dadao`）⇒ 安装根工具链仍是 T4 版本，`make check-lit`/`check-isa-coverage` 走安装根 `llvm-mc`/`llc`（本册未新增 lit 用例）；`check-builtins-freshness` 需 `make build-builtins` 并把同一归档 `cp` 到构建树资源目录与安装根两处消费点（T4 同法，非 `install-host`），`check-musl-freshness` 需 `make build-musl-shared`（已做，rc=0）。② `-static-pie`/`rcrt1.o` 的 `_DYNAMIC`（`ISS-245`）与 `TLSDESC`(13)/`COPY`(9) 仍显式报错（本册不做）。③ `local-dynamic` 模型显式报错（clang 默认不产生、语料无需求）。④ 收集到的共享 DSO 若被 `dlopen` 且用 initial-exec，musl 会在加载期报 `initial-exec TLS resolves to dynamic definition`（标准限制，本册未改）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`components/llvm-project/**` 的全部改动（14 文件 + `InputSection.cpp`）、`tools/testcases/run_libc_test_user_suite.py` 的 helper 构建/排除表/运行 CWD。逐行看过 `scanTLSSlot`/`relocateInSection`/`LowerGlobalTLSAddress`/ISel 两分支/AsmPrinter 槽生成/驱动三张表。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| ① `__tls_get_addr` 用 `i64` 声明 ⇒ `CCIfPtr` 不命中，参数进 `rd16`、返回值取 `rd8`（运行期垃圾指针） | ✅已修 | `LowerGlobalTLSAddress` GD 分支：`CallTy = PointerType::get(...)`（参 + 返回均是） | 修前 `t1` 探针 `ld.st rd4,[rb4,0]` 前读 `rd8` ⇒ qemu 崩；修后反汇编 `aip.si rb16,…` + 返回 `rb8`，`t1`/`main`/DSO 探针 exit 0 |
| ② 输入侧 TLS 槽走泛型 `processAux` 会被当链接期常量（`R_TPREL` 不在 `isRelExpr()`）⇒ shared 静默错值 | ✅已修 | 新增 `DADAO::scanSection` 覆写（RISCV/X86_64 同形）：10/11/12 只许可写非可执行槽 + `STT_TLS`，静态/动态按 `shared`/`isPreemptible` 分流 | DSO `.rela.dyn` 出现 DTPMOD/DTPREL；DSO 内 `static __thread` 走无符号 addend 记录且运行 5/6 正确 |
| ③ shared 下非抢占 TLS 符号不能用带符号动态项（local STT_TLS 不入 `.dynsym`） | ✅已修 | `scanTLSSlot` 非抢占分支用 `addAddendOnlyRelocIfNonPreemptible(type, …, symbolicRel)` | 3b 探针：`R_DADAO_TLS_DTPMOD - 0x0` / `- 0x4`，`stv=5 sum=6` exit 0 |
| ④ `getTlsTpOffset` 无 `EM_DADAO` 分支 ⇒ 链接期常量 TPREL 命中 `llvm_unreachable` | ✅已修 | `InputSection.cpp` 增 `EM_DADAO` = Variant 1 无 gap（与 musl `(image)&(align-1)` 同式） | IE 非 PIC 例 `xoff=0/yoff=4` exit 0；DSO IE `.rela.dyn` 仅 `TLS_TPREL itv` |
| ⑤ GD 的 `tls_index` 对地址无法用现有 2 指令对直接取（`ld.o` 取内容，非地址） | ✅已修 | AsmPrinter 为每 GV 额外发一个「持对地址」的普通 ABS48 指针槽，`PCREL_LOAD` 只取指针 | `dso.o` `.rela.got` 第三槽 `R_DADAO_ABS48 .Lgot.0`；`.so` 里该槽为 `RELATIVE`（addend=对地址） |
| ⑥ `rb2rd` 的块计数 0 非法（`copyPhysReg` 用 1） | ✅已修 | ISel IE 分支以 `getTargetConstant(1)` 建 `rb2rd` | 反汇编 `rb2rd {rd4}, {rb4}`（无多余操作数），IE/DSO 两例运行 pass |
| ⑦ `DADAOELFObjectWriter`：`FK_Data_8` + PCREL specifier 落 `default:` ⇒ 静默 ABS48 | ❌不修 | — | 不可达：`parseDDDirective` 对数据指令的非 TLS specifier 显式报错、`DADAOMCCodeEmitter` 对指令上的 TLS specifier 显式报错；AsmPrinter 只产 TLS spec。加分支无收益 |
| ⑧ 每个 TU 各自发 GD 对 ⇒ 跨 TU 重复 `.rela.dyn` 记录（lld 合成 GOT 会去重） | ❌不修 | — | 语义正确（每条独立可解），代价仅几字节；与既有「编译器自管 `.got`」口径一致（ABS48 GOT 槽同形） |
| ⑨ 驱动加 helper 构建/CWD 可能改变其它用例判决 | ✅已核 | helper 仅在 `mode == "dynamic"` 且 `cid ∈ HELPER_DSOS` 时构建；CWD 只对带 helper 的用例设置 | 全量动态档逐例对账：**0 条 pass→非 pass**；静态档 `excluded` 仍 30、10 例 10/10 |
| ⑩ 补丁行号位移使 `llvm-isa-backend-matrix` 过期 | ✅已修 | `gen_isa_coverage.py` 由真源重派生 | `gen_isa_coverage.py --check` PASS；`make check-isa-coverage` rc=0 |
| ⑪ 证据脚本自身「假绿」风险（注入未生效/恒真断言） | ✅已核 | inject A 改为在 `scanTLSSlot` 入口注入（原注入点在 DSO 场景不可达，实测被本项抓到）；两处注入均断言「非零 rc + 注入诊断在首错」 | 首轮 inject A 实测 `actual=0`（未红）⇒ 定位并改正；终轮 46/46 PASS，注入→红→`cp`+md5 还原→回绿 |

**判决**：8 条已修 + 2 条有据不修 + 1 条已核；无未修 finding ⇒ 状态置 `待验收`。

#### 第 1 轮 reviewer 验收（2026-10-20，独立复核）
- **重跑记录**：`run.sh` default rc=0（46/46 PASS）；`run.sh --inject` rc=0（13/13 PASS）。关键数字逐条对账：
  - 发射：`dso.o` `.rela.got` = `0:R_DADAO_TLS_DTPMOD:tv;8:R_DADAO_TLS_DTPREL:tv;10:R_DADAO_ABS48:.Lgot.0` ✓
  - 消费：`libtv.so` `.rela.dyn` 有 DTPMOD/DTPREL/RELATIVE ✓
  - 运行：probe RESULT OK ✓（DSO 初值 7→99、两线程各自独立、main TLS=11 不被覆盖）
  - 非抢占 DSO：`stv=5 sum=6` ✓（符号零 addend 记录）
  - initial-exec：`x=21 y=22 xoff=0 yoff=4` ✓
  - local-exec 无动态 TLS 重定位 ✓
  - 目标 5 例动态 5/5 pass（dlopen/tls_align/tls_align_dlopen/tls_init_dlopen/tls_get_new-dtv）✓
  - 047t 10 例两档 10/10 ✓、3 TLS 例两档均 3/3 pass ✓
  - 注入 A（scanTLSSlot 加 Err）：DSO 链接 FAIL → 诊断含 INJECTED → 还原回绿 ✓
  - 注入 B（addend 1→0）：probe FAIL（Bus error）→ 还原回绿 RESULT OK ✓
- **独立注入**：改 `DADAO.cpp` relocate DTPREL/TPREL 写零 ⇒ `run.sh --inject` rc=1（2 FAIL：probe segfault）；还原 md5 对账 YES + 回绿（13/13 PASS, rc=0）。
- **musl 零改动**：`git log faa472f^..292c54a -- components/musl` = **0 commits** ✓。
- **musl runtime 实测**：安装根 clang 编 TLS ✓、安装根 lld 链 DSO 产生 2 条 TLS 重定位 ✓。
- **三模型分派**：local-exec（T4）✓、initial-exec（`%tls_tprel` 12）✓、global-dynamic（`%tls_dtpmod`+`%tls_dtprel`+`__tls_get_addr`）✓、local-dynamic **显式报错** ✓。
- **`getTlsTpOffset` EM_DADAO**：`InputSection.cpp.patch` Variant 1 no gap ✓。
- `make check`(L1)：PASS ✓。
- `git status --porcelain`：空 ✓。

**判定：Accepted**。T5 核心交付全部达标；musl 零改动有据；两处 engineer 注入 + 独立注入均红→还原→绿；无未通过的约束。
