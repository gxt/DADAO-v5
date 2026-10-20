# LLVM-118t: picolibc 残余后端缺口现场重枚举 + `ISS-222` ①/③/④ 判定

**模块**：llvm
**项目里程碑**：M9
**依赖**：`INFRA-096t`（builtins/安装根新鲜度门控，`待验收`——本册要跑 picolibc 构建与测试，安装根不新鲜会假绿/假红）、`LLVM-117t`（动态 TLS，`待验收`）、`QEMU-064t`（新解码表，`待验收`）、`LLVM-119t`（同改 `components/llvm-project/**`，**必须串行**，见「约束」）
**状态**：待验收

> **编号（现场取号，2026-10-20）**：`llvm` 现存最大 = `LLVM-117t` ⇒ 取 **`118`**（编写前 `grep -rn 'LLVM-118' .tao/` 零命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实（先读，勿重复查证旧结论）

- **`ISS-193` 的旧口径（6 类 41 源）已过时，不得直接引用为现状**：`INFRA-066t` 的 41 源清单是 2026-10-12 的现场；此后 `LLVM-084t`/`086t`/`087t`/`088t`/`089t`/`115t` 逐类删表，现行 `components/picolibc/patches/meson.build.patch` 的 `_dadao_backend_blocked` **只剩 1 条**（`hash_page.c`，注释标 `ISS-193 (c)`）；最近一次构建日志 `.work/log/llvm/LLVM-115t-build-picolibc.log:98` 打印 `DADAO port scope: excluding 1 backend-blocked libc sources (ISS-193)`。**本册第一步 = 现场重枚举，不继承任何旧数**。
- **`ISS-222` 四类（`INFRA-082t` A2+A3 现场）**：
  - ① `%N`（`%0`/`%1`… 操作数引用）代入空串：现场 `rb2rd %0, rb3, 1` → `rb2rd , rb3, 1`；根因 = `DADAOAsmPrinter` 未覆写 `PrintAsmOperand`（`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOAsmPrinter.{h,cpp}.patch` 现场 `grep` 两者零命中 ⇒ 基类对未知操作数不打印）。
  - ② `"m"`/`"+m"` 内存操作数 ⇒ ISel `report_fatal_error` + core：**已单独立 `LLVM-119t`**，本册**不做**（勿重复修）。
  - ③ `rotl`/`rotr`/`bswap` 缺 ISel：patch 现场已见 `DADAOISelLowering.cpp.patch:434`（`ISD::BSWAP i64 → Expand`）、`:451`（`ROTL i64 → Legal`）、`:452`（`ROTR i64 → Custom`，`:1402-1419` 折 `ROTL`）；`DADAOCodeGen.td.patch:415-419` 有 `rol.o` 选择。**是否真的收口须用可复现命令重新证明**（不得凭注释断言）。
  - ④ `dynamic_stackalloc` 缺：patch 现场 `DADAOISelLowering.cpp.patch:352-353`（`STACKSAVE`/`STACKRESTORE`/`DYNAMIC_STACKALLOC → Expand`）。同上，须现场复核。
- **消费侧真值面**：picolibc 构建 = `tools/infra/build_picolibc.py`（`--jobs`；工具链戳记失效会整树重建）；全量枚举的编译数据库 = `.work/build/picolibc/compile_commands.json`（**只含未被过滤表排除的条目** ⇒ 见「枚举口径」）；门控 = `make build-picolibc`、`make check-picolibc-tests`（L2）、`make check-picolibc-tests-full`（opt-in，L3 规模）。
- **口径依据**：`LLVM-086t` 用户裁定 C「**只解锁，不立约定**」（用户 2026-10-12，逐字；`spec/Toolchain-01` 不因本册改动）；`AGENTS.md`「Spec-first」（期望值来自 `spec/` 与契约，不从实现反推）。

## 接口规范

- **输入**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（后端）、`components/picolibc/patches/meson.build.patch`（过滤表）、`.work/source/picolibc`（组件源）、`.work/build/picolibc`（构建树）、安装根 `.dadao/cross-toolchain/**`、`tools/infra/build_picolibc.py`、`tools/testcases/picolibc_tests.py`。
- **输出**：
  1. **现场枚举报告 + TSV**：对**全集**逐条重编（见「枚举口径」），逐源记录 `rc` / 首条错误签名 / 归类；TSV 落 `.work/log/llvm/`（计数现场派生，不写死）；
  2. **逐类「做/不做 + 依据」表**（写进完成区，≤30 行；长证据留日志）：每类给「失败签名 / 代表源（现场计数）/ 根因指针 / 决策 / 依据」；「不做」必须给可核依据 + 登记落点（过滤表注释 / issue 注记 / `components/picolibc/README.md` 已知边界），不得只写「不做」；
  3. **实现的项**：后端补丁（`components/llvm-project/patches/**`，一文件一补丁 + `series` 同步）+ lit 用例 + 运行时探针（独立 oracle）；`%N` 若做，须能被 `lit` 与运行时同时证明；
  4. 证据脚本 `.work/evidence/<任务ID>/run.sh`（一键、逐项 rc、default + inject，注入用 `cp`+md5 还原）+ 日志 `.work/log/llvm/LLVM-118t-*.log`。
- **约束**：**不改** `spec/` / `contracts/`（机器数据）/ `.tao/contracts/**` / `tests/vectors/**`；**不新增**过滤表条目（只许删/保持，且逐条给依据）；**不改** `LLVM-119t` 范围（`"m"` 约束）；改 `components/llvm-project/**` 后 **必须** `make install-host`（由主会话或按派单执行）再用门控/测试验证；**不跑** `git commit`/`push`；`git checkout/restore/stash` 禁用。

## 枚举口径（本节即「全量」定义，可复现、非抽样）

1. 用**当前安装根工具链**重建 picolibc（`make build-picolibc`）确保 `compile_commands.json` 与现状一致；
2. **全集** = 上游 meson 源清单（含被过滤表排除的源）。取法二选一，须在册内写明所用方法与依据：
   - (a) 在**临时副本**（`/tmp/opencode/LLVM-118t/picolibc-src`）里把 `_dadao_backend_blocked` 置空后重新配置，读其 `compile_commands.json`；或
   - (b) 从 `.work/source/picolibc` 的 meson `src_*` 变量/`meson introspect --targets` 派生全集，再与 `compile_commands.json` 做差集补齐；
3. 对全集**每一条**编译项重编（`-fsyntax-only` 不足以暴露后端崩溃 ⇒ 必须真实 `-c` 到 `/tmp` 输出），逐条记录 rc 与**首条**错误签名；
4. 归类按**错误签名**归并（不按旧 (a)–(f) 硬套）；旧 6 类 41 源仅作「差异对照」，差异须写归因（哪一册/哪条改动使其转移或消失）。
5. 计数一律现场派生（条目数 / non-OK 数 / 类数 / 每类源数），任务书与日志**不得**写死数字。

## 验收标准

1. **枚举完整性**：报告给出全集条目数、non-OK 数、类数，均为现场派生；提供「全集条目」与「重编条目」的计数等式（防漏项）；抽样不可接受。
2. **逐类判定**：每类「做/不做 + 依据」齐全；「做」的类已实现且证据链完整；「不做」的类有可核依据 + 登记落点（过滤表注释逐条对应 issue 号 / README 已知边界）。
3. **`ISS-222` ①/③/④ 逐项现场结论**：
   - ③④：用可复现命令（`clang -c` 探针 + `llc` 检查 + 源文件编译）证明「已收口/仍缺」，并在 issue 注记回填；**不得**只引用 patch 注释；
   - ①：若做 ⇒ lit + 运行时探针（`%0`/`%1` 代入后汇编文本与手写期望逐字相等；运行时值 = 手算常量）；若不做 ⇒ 必须变为**显式诊断**（`clang -c` rc=1 + 诊断含「operand reference unsupported」类信息），**禁止**继续静默打印空串。
4. **过滤表**：条目数 ≤ 现状 1；每删一条须证明「该源可编 + 其符号在 `libc.a` 可用」（`llvm-nm`/`llvm-readobj`；若安装根缺工具，按 `INFRA-098t` 现状用构建树工具并披露）；若保留，注释须写清「不做」依据与 issue 指针。
5. **无回归**：`make check-picolibc-tests-full`（opt-in）**pass 数 ≥ 现场基线、fail = 0、blocked 不增**（基线现场取，逐项列出新增解锁）；`make check-picolibc-tests`（L2）rc=0；`check-instrinfo` / `check-isa-coverage` / `check-patch-tree` / `check-lit` rc=0。
6. **可达 FAIL ≥ 2**（每条须真实输出 + 还原后回绿）：
   - (a) **修前现场**：至少一条真实失败签名（如 `Cannot select` / 后端 fatal error）在改前复现、改后消失；
   - (b) **注入回退**：在**临时树**把补丁回退（或改坏 lowering）⇒ lit/探针转红；
   - (c) **错误值注入**：把探针期望值改错（如谓词真值表、`bswap` 结果）⇒ 探针 rc≠0；还原后 rc=0。
7. **完成区**（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 的 `ISS-193`/`ISS-222` 按实况回填（`closed` 仅在对应面全清时；否则注记剩余面）。
8. **不跑** `git commit`/`push`；越界改动须披露。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-118t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（新增约束字母 / 改 `spec/` / 接受新边界）时留问。
6. 复杂命令输出留 `.work/log/llvm/`；长构建按 `AGENTS.md` 申报耗时、`JOBS=8`、禁全核。

## 完成区

**测试结果**：证据脚本 `.work/evidence/LLVM-118t/run.sh` default **25/25 rc=0**、`--inject` **9/9 rc=0**（3 处可达 FAIL：改错 lit 期望 / 改错运行期 oracle / 归档删 `hash_page.c.o`，均红→绿；`cp`+md5 对账仓库零改动）。L1 `make check` rc=0；`check-lit` **121/121**；`check_lit_gen` / `check-instrinfo` / `check-patch-tree`(**185**) / `check-index-blobs` / `check-source-state` / `check-no-residue` / `check-tasks` / `check-knowledge-refs` / `check-component-changelog` / `check-issues` / `check-isa-coverage` 全 rc=0。picolibc 定点 `--only` **7/7 pass**（`test-malloc`/`test-memset_s`/`hsearchtest`/`test-strtod`/`test-setjmp`/`test-pow`/`test-memcpy_s`）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOAsmPrinter.{h,cpp}.patch`、`components/picolibc/patches/meson.build.patch`、`components/{llvm-project,picolibc}/changelog.md`、`components/picolibc/README.md`（「当前移植范围」段更新为过滤表 0 条）、`.tao/knowledge/{issues.yaml,milestones.md}`、本册。**越界披露**：新增 `tests/llvm/lit/CodeGen/DADAO/inline-asm-operands.ll`（任务书验收 3 要求 lit；派单文件集未列）。
**验收结果**：
① **现场重枚举（全量、非抽样）**：全集 **1120** 条（等式：现行构建 1119 + 过滤 1 = 1120；改后 1120 = 1120 + 0），逐条真实 `-c` ⇒ **non_ok = 0**（TSV：`.work/log/llvm/LLVM-118t-enum-tsv.txt`）。旧「6 类 41 源」**全部消失**，逐类归因：**(a)** `LLVM-084t`、**(e)** `LLVM-086t`、**(b)** `LLVM-087t`+`LLVM-089t`、**(d)** `LLVM-088t`、**(c)** `LLVM-097t`、**(f)** `LLVM-115t`（本册现场复证，未继承旧数）。
② **逐类判定**：`ISS-222` ① ⇒ **做**（唯一仍「空串+误导诊断」项，代价 1 个覆写；`LLVM-086t` 裁定 C 只约束约束字母，不禁止打印）；③ rotl/rotr/bswap ⇒ **不做（已收口）**；④ `dynamic_stackalloc` ⇒ **不做（已收口）**；`ISS-193` (c) `hash_page.c` ⇒ **做（删表）**；其余 5 类 ⇒ **不做（已由前册收口，本册 0 失败复证）**。
③ `%N` 真值：修前安装根 `llc` **rc=1** + `invalid operand in inline asm` + `add.si , 5`；修后 rc=0 → `add.si rd32, 5` / `swym 3` / `add.si rd34, 7`+`add.si rd35, 9` / `set.zw rd5, wp0, g`；运行期 `pn 105 32 17 10` exit 0；lit 新例**旧 llc 红 / 新 llc 绿**。
④ ③④ 真值：`llc -O2` `ROTL`=1 条 `rol.o`、`ROTR`=`sub.so`+`rol.o`、`i64 bswap`=`Expand`（无 `Cannot select`）、`dynalloc`=Expand；运行期 `rot 23456789abcdef01 ef0123456789abcd efcdab8967452301 4950 5050` exit 0。bswap **未**改 `rev.o`：`Legal` 会命中 i32 bswap 的 `PromoteIntRes`（`LLVM-097t` 结论）⇒ 收益 27→1 条不抵回归风险。
⑤ picolibc：`build-picolibc` rc=0；过滤 **1 → 0**；`libc.a` 2,028,044 → **2,041,338 B**；`llvm-nm` 11/11 符号 `T`；`dbm_open` 探针改前链接失败 9 条 `undefined symbol`、改后链接+运行 rc=0。
⑥ 补丁：llvm **2 份改** + picolibc **1 份改**；`series` 83/14 **不变**；`check-patch-tree` **185** rc=0；组件树 E1/E3 收敛（`--source-state` OK）。
**新发现/坑**：① 改组件 commit ⇒ clang `.comment` 版本串变 ⇒ `build-builtins` 必须重跑（237 s），且 `atomic-install` 未刷新 build-tree/安装根副本 ⇒ 手工 `cp` 同一归档两处（sha256 `5512be72…`）+ `build-musl{,-shared}` 刷新戳记（12 s）；② overlay 下 E2E lit 把 qemu 解析为 `<llvm>/qemu` ⇒ 建**未跟踪**软链 `.work/build/llvm/qemu -> ../qemu` 后 `check-lit` 才 121/121；③ 重枚举命令**必须** `PATH=<install-root>/bin` 前置，否则 triple 全红（假红）。
**遗留问题**：① **既有缺陷（非本册引入）**：`test-printf`/`test-printf-int` 的 `%p` 用例（277/278）失败；A/B 对照（同一 `.o` × 删 `hash_page.c.o` 的归档）**逐字节同输出** ⇒ 与本册无关，建议主会话登记 issue。② 按派单**未跑** `install-host` / L2 / L3（含 `check-picolibc-tests(-full)`）；`check-lit` 走 `LLVM_TOOLS_DIR` overlay，故裸 `make check-lit` 在新 lit 例上预期红，`install-host` 后回绿。③ `ISS-223`（musl 13 源排除表）本册未动，需另册回删。

## 审阅记录

#### 第 1 轮 engineer 自审

**代码级审查（`DADAOAsmPrinter::PrintAsmOperand`）**：先交基类处理 `c`/`n`/`s`/`a`（`return false` 即已印）；带任何其它修饰符一律 `return true`（不猜、不吞）；`MO_Register` 要求物理寄存器（post-RA），否则 `return true` 交调用方诊断；`MO_Immediate` 十进制、`MO_GlobalAddress` 复用 `PrintSymbolOperand`（含 offset）、`MO_BlockAddress` 复用 `GetBlockAddressSymbol`；`default` 仍 `return true`。与 `LLVM-119t` 的 `PrintAsmMemoryOperand`（`[rb, off]`、修饰符非空即拒）同一口径，未新增约束字母、未改 ISA/ABI。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `%N` 探针首版把立即数写成 `%1`（实为 tie 输入 `%0` 的寄存器），误判「仍印错」 | ✅已修 | 探针改 `%2` 指向 `"i"(12)` | `add.si rd33, 12`；运行期 32 ✓ |
| F2 旋转探针首版用移位 idiom（clang 未识别）+ VLA/alloca 被 DCE 删除 ⇒ 未覆盖 `ROTL/ROTR/DYNAMIC_STACKALLOC` | ✅已修 | 改 `__builtin_rotateleft64/rotateright64` + volatile 读写强制保留分配 | 汇编含 `rol.o` / `sub.so` / `rd2rb {rb1}` |
| F3 旋转探针 oracle 算术错（`100+…+1` 写成 4950，实为 5050） | ✅已修 | 期望值改 5050 | 程序先 exit 1（证明比较非恒真），改后 exit 0 |
| F4 证据脚本 `need()` 用 `-x` 检查 `.a` ⇒ 误报 missing | ✅已修 | 加 `need_file()`（`-f`） | 脚本 header 段通过 |
| F5 `build_run` 未合并 qemu stderr（semihosting 输出走 stderr）⇒ stdout 捕获为空 | ✅已修 | qemu 行 `2>&1` | C7.1/C9.1 stdout 逐字相等 |
| F6 `check-run-artifacts` 拒 `.tsv` 扩展名 | ✅已修 | 改名 `LLVM-118t-enum-tsv.txt` + 同步 issue 引用 | L1 rc=0 |
| F7 新增 `tests/llvm/lit/...` 超出派单文件集 | ✅已披露 | 不撤销（验收 3 明令要求 lit） | 完成区「修改文件」+ 回报 |
| F8 overlay 下 `make check-lit` 的 9 例 E2E rc=127（qemu 路径解析） | ✅已修（本地） | 未跟踪软链 `.work/build/llvm/qemu -> ../qemu` | `check-lit` 121/121 rc=0 |

**判决**：全部 finding 已处置，无未修项 ⇒ 状态置 `待验收`（`check-milestones-fresh` A1 要求表行与册一致，`milestones.md` 同步）。


#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

#### 第 1 轮 architect 提交 + 文件集审核（2026-10-20）
- **档位**：按派单正常提交；**`reviewer` 尚未审**（本轮「第 1 轮 reviewer 验收」仍为占位）⇒ 与本规则「非 Accepted 用 `WIP:`」**不一致**，按派单执行并如实披露。
- **开工核对**：`git branch --show-current` = `LLVM-118t`；`git status --porcelain -uall` = 9 M + 1 ??（与本册完成区「修改文件」+ 越界披露逐条对得上）。未跟踪软链 `.work/build/llvm/qemu -> ../qemu` 落在忽略区、**不入库**、**保留**（后续 E2E lit 用）。
- **提交**：`81cf486`（分支 `LLVM-118t`，**未 push**）；`git diff --cached --name-only` = **10 文件**（2 份 `DADAOAsmPrinter` 补丁 + `meson.build.patch` + 2 份 `changelog.md` + picolibc `README.md` + `issues.yaml` + `milestones.md` + 本册 + 新增 `inline-asm-operands.ll`）；漏提 0 / 多提 0 / 越界 1（新 lit，完成区已披露）；`series` 83/14 未动。
- **门控（architect 复跑）**：`check-patch-tree` rc=0（5 组件 / **185** patch OK）；`check_issues` rc=0（53 open / 23 closed，含本次新登记）；`check-tasks` / `check-knowledge-refs` / `check-milestones-fresh` / `check-component-changelog` / `check-no-residue` 均 rc=0；L1 `make check` rc=0（`.work/log/llvm/LLVM-118t-architect-L1.log`，末行 `repository checks (L1): PASS`）。
- **状态核对**：本册 `**状态**：待验收` == `milestones.md` 流水行 `待验收`（`check-milestones-fresh` A1 口径）✓。
- **新登记**：`ISS-304`（`P2` / `scope: [testcases]`）= picolibc `test-printf`/`test-printf-int` 的 `%p`（serial 277/278，期望 `0x39`、实得 `0x8`/`0x3`）失败；A/B 删 `hash_page.c.o` 输出逐字节相同 ⇒ 与本册无关；**只建条目、不下结论**（期望值 / 格式实现 / 上游与否待后续册判）。
- **遗留处置**：完成区「遗留 ①」已由 `ISS-304` 覆盖；「遗留 ②」按派单未跑 `install-host` / L2 / L3（假绿风险已知，裸 `make check-lit` 在新 lit 例上预期红）；「遗留 ③」`ISS-223` 另册回删，本册未动。
