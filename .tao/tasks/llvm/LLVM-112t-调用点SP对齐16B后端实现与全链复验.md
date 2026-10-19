# LLVM-112t: 调用点 `SP` 对齐 16 B 的后端实现与全链复验（`StackAlignment=Align(16)`）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`SPEC-151t`（规范/契约面，**同批**；本册实现前其 16 B 口径须已落地或同批落地）、`ADR-0018 C9 D3`（**architect 已于 2026-10-19 就地修订**；用户原话见下）、`ADR-0031 D7`（16 B 栈值对齐；SP 16 B ⇒ 绝对 `%16==0` 无条件成立）、`LLVM-111t`（16 B 相对取整已落；本册在其上把**基址**钉成 16 B）、`LLVM-110t`（FP=`rb2`、`rb63` 普通 callee-saved 的现行帧布局；本册不得回退）
**状态**：待验收

## 用户授权（原话逐字；渠道 = 经主会话问答，2026-10-19）

> 「**同意，调用点SP对齐改成16B**」

- 裁定口径：**`call` 执行时 `sp % 16 == 0`**（由 8 B 改为 16 B）；栈参数仍按 **8 B 槽**；16 B 值仍按 16 B 对齐。
- 本册 = 该裁定的**实现 + 全链复验**面；规范/契约/`abi.yaml`/只读锁归 `SPEC-151t`。

## 问题根源

1. **后端基址只有 8 B**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOFrameLowering.h`（工作副本 `…/DADAOFrameLowering.h:34`）构造 `TargetFrameLowering(StackGrowsDown, /*StackAlignment=*/Align(8), 0)`。`determineFrameLayout` 用 `std::max(getStackAlign(), MFI.getMaxAlign())` 取整帧大小 ⇒ 帧大小只保证 8 B 倍数，`call` 时 `sp` 可能为 `8 (mod 16)`。
2. **`D7` 的无条件性缺口**：`LLVM-111t` 已把 `reassignDADAOArgLocs` 的 16 B 栈值偏移 `alignTo(StackOff, 16)`、caller `CALLSEQ` 在 `HasStack16` 时取整到 16；但若**基址** `sp` 本身是 `8 (mod 16)`，绝对地址仍可能 `%16==8`。其完成区坑 ① 已如实披露（探针只能用 16 B 对齐局部变量钉住基址）。SP 改 16 B 后，`D7` 的 `p0 % 16 == 0` **无条件成立**，探针不再需要「钉基址」技巧。
3. **FP 函数的调用点风险**：SP-only 函数的出参区在 prologue 随帧大小取整（16 B 后自动对齐）；**FP 函数**（`hasFP`）在调用点用 `ADJCALLSTACKDOWN/UP` 调整 `NumBytes`。现 `LowerCall` 只在 `HasStack16` 时 `alignTo(ArgStackSize, 16)`，**8 B-only 且栈实参个数为奇数**时 `NumBytes` 为 8 的奇数倍 ⇒ 调用点 `sp` 落 `8 (mod 16)`。必须由探针证伪或修正（修正面 = `LowerCall` 的 caller 侧 `NumBytes`，callee 的 `ArgStackSize`/`VarArgStackOffset` 仍保持精确，`LLVM-111t` F3 结论不变）。
4. **手写汇编/入口面**：`crt1`（musl `crt/crt1.c` + `arch/dadao/crt_arch.h`）、`setjmp`/`longjmp`/`sigsetjmp`、`syscall_cp.s`、`__set_thread_area.s`、picolibc `setjmp.S`/`semihost-dadao.S`、musl `ldso` 入口、`reloc.h` 内联汇编 —— 是否有按 8 B 推 `sp`/帧偏移的假设，须逐文件核对。已知现场（供执行时复核，**不替代实测**）：`qemu-user` 初始 SP 由 `setup_arg_pages()` 给 16 B 对齐（`crt_arch.h` 注释）、信号帧 `sp &= ~0xf`；上述汇编多数**不改 `rb1`**，`setjmp` 帧 `rb2` 槽在 1288、`sigsetjmp` 跨 `call` 用 1296 暂存 `rb32`（均 8 B 槽偏移，不要求 16 B 起点）。
5. **连带面必须全量复跑**：`Align(16)` 改变**所有**函数的帧大小/偏移（8 B 基线允许变化），因此 lit、三套大型测试、`build-musl*`、`build-picolibc` 都必须重跑；**不得**只跑新增探针。

## 判据（写死）

- **对齐不变量**：任一 `call` 执行时 `sp % 16 == 0`；callee 入口 `rbsp % 16 == 0`。覆盖：叶子/非叶子、SP-only/FP（`-fno-omit-frame-pointer`）、有/无栈实参、奇数个 8 B 栈实参、变参、VLA/`alloca`、`setjmp`/`longjmp`/`sigsetjmp` 之后、静态/动态入口。
- **16 B 值**：栈上 16 B 值（f128 / 2 块 RD 组）绝对地址 `%16==0` **无条件**（不再依赖探针钉基址）；高半在低地址、`ldm.o`/`stm.o` 直通语义不变（`ADR-0031 D6/D7`）。
- **语义不变**：8 B 值（标量/指针/HFA/HPA/`>16 B` 聚合）的**运行结果**不变；汇编布局允许变化（帧大小、偏移、指令数），但所有探针的**手算期望值**与三套测试的 pass/fail 归类必须逐项一致（既有 `known-fail`/`blocked` 的归属不得因本册而漂移；新增失败必须逐条归因）。
- **覆盖集合不变**：`f128` 与 `Count==2 && Bank==0` 的 RD 组仍按 `alignTo(…,16)`；HFA/HPA/≥3 块、8 B 标量仍按原规则。
- **补丁树**：只改既有 patch 的终态；编辑在 `.work/source/llvm-project` 进行，用 `python3 tools/infra/make_patch.py llvm-project` 导出（**禁**手工编辑 `.patch`，`Process-01 §6.1.1`）；`series` 条目数与 `check-patch-tree` 计数不变。

## 改动清单

### A. 后端：`DADAOFrameLowering.h` / `.cpp`

- `.h` 构造：`/*StackAlignment=*/Align(8)` → **`Align(16)`**。
- `.cpp`：
  - 注释「8-byte aligned at calls (contract-abi.md §2.2)」→ 16 B；「Re-derive … with an 8-byte local area」处说明 saved-FP 槽仍为 8 B、总帧大小按 16 B 取整。
  - `determineFrameLayout`：确认 `StackAlign = std::max(getStackAlign(), MFI.getMaxAlign())` 与 `MFI.setStackSize(alignTo(StackSize, StackAlign))` 在 16 B 下正确；saved-FP 槽（`FPSaveSlotOffset = -8`）与对象偏移不变。
  - 若 `emitPrologue`/`emitEpilogue`/大帧寻址有硬编码「8」的对齐假设，逐一核对并更新注释/实现（**最小改动**）。
- `.td` / `DADAOInstrInfo` 无需改；`DataLayout`（`S128`）不变。

### B. 调用点 `NumBytes`（仅当探针 P5 红）

- `DADAOISelLowering.cpp::LowerCall`：现 `const uint64_t NumBytes = HasStack16 ? alignTo(ArgStackSize, 16) : ArgStackSize;`。
- 若 FP + 奇数 8 B 栈实参探针显示 `sp % 16 != 0` ⇒ 改为 **无条件** `alignTo(ArgStackSize, 16)`（caller 侧），`CALLSEQ_START/END` 用同一值；**callee 侧** `ArgStackSize`（= `VarArgStackOffset`）**保持精确、不取整**（`LLVM-111t` F3）。
- 若探针全绿（说明框架层已自动补位）⇒ **不改**，在完成区贴探针证据与理由。
- 只动 `LowerCall` 的栈区大小计算；不动 `reassignDADAOArgLocs` 的每值取整、bank 游标、寄存器分配。

### C. 手写汇编 / 入口核对（逐文件，**优先不改**）

逐文件核对「是否改 `rb1` / 是否按 8 B 推帧偏移 / 是否要求 16 B 起点」并留 `grep`/行号证据：

- `components/musl/patches/arch/dadao/crt_arch.h`（`_start`/`_dlstart`：`rb2rb {rb16},{rb1}`，不改 SP）
- `components/musl/patches/src/setjmp/dadao/setjmp.S`、`longjmp.S`、`src/signal/dadao/sigsetjmp.s`
- `components/musl/patches/src/thread/dadao/syscall_cp.s`、`__set_thread_area.s`
- `components/musl/patches/arch/dadao/reloc.h`（内联汇编 `sp -> rb1`）
- `components/picolibc/patches/libc/machine/dadao/setjmp.S`、`libos/semihost/machine/dadao/semihost-dadao.S`
- musl `crt/crt1.c`、`ldso/dlstart.c`（上游；核对不调整 SP）
- `components/qemu/patches/linux-user/dadao/*`：初始 SP 16 B 对齐（`setup_arg_pages`）、信号帧 `sp &= ~0xf`、`clone` 的 `newsp` 对齐 —— **只核对、不改**；若发现 qemu 侧只给 8 B，须停下报告（跨模块）。

**判据**：上述文件若无人改 `rb1` 且所有 `stm.o`/`ldm.o` 偏移为 8 B 倍数，则**零改动**，完成区逐文件写「核对不改 + 证据」。若确需改（例如入口把 SP 向下取整到 8），按组件补丁流程改 `.work/source/<component>` 并用 `make_patch.py` 重导出，完成区披露。

### D. 证据与探针（新增，不入产品代码）

- `.work/evidence/LLVM-112t/*`（`default` / `--inject`，执行时新建）+ 探针源码（`P1.c`…）+ 基线快照。
- 运行日志 `.work/log/llvm/LLVM-112t-*.log`；门控日志 `check-<name>.log`。
- 探针入口 SP 捕获：4 行汇编 `capture_sp(unsigned long *p)` —— 入口 `st.o rb1, [rb16, 0]`，`ret rd8, 0`；C 侧在每个待测调用点 `capture_sp(&sp)`，断言 `sp % 16 == 0`。**该 stub 用汇编写**，避免编译器把取 `rb1` 优化掉。

## 探针（必做；独立 oracle；手算期望值）

1. **P1 `p0 % 16 == 0`（f128 变参，无钉基址）**：复刻 `LLVM-111t` P1（16 int + 16 double 命名参数占满，变参 `int`/`long double`/`int`），**删掉**用于钉基址的 16 B `volatile` 局部；断言 `p0%16==0`、`p1==p0+16`、`p2==p0+32`、`ld==` 手算常量。改前（旧安装根）应 FAIL/`%16==8`，改后 PASS。
2. **P2 `rbsp % 16 == 0` at `call`**：至少 6 个调用点 —— ① 叶子；② 非叶子无栈实参；③ **奇数个 8 B 栈实参**；④ SP-only；⑤ `-fno-omit-frame-pointer`（FP）；⑥ 递归/间接调用。每个调用点 `capture_sp` 断言 `%16==0`；`③+⑤` 即 **P5**（`NumBytes` 风险点）。
3. **P3 VLA / `alloca`**：`alloca(8/24/40)` 与 VLA（运行时长度 1/3/5）之后调用 `capture_sp` ⇒ `%16==0`；`hasStackRealignment` 路径（如需要显式 `-mstackrealign`/超对齐类型）至少 1 例。
4. **P4 `setjmp`/`longjmp`/`sigsetjmp`**：`setjmp` → `longjmp` 后 `capture_sp` ⇒ `%16==0`；`sigsetjmp(env,1)`/`siglongjmp` 同；验证 `rb2`/`rb63` 恢复与 SP 恢复同时成立。
5. **P6 入口**：静态 `_start` → `main` 内首次 `capture_sp` ⇒ `%16==0`；动态（`ldso`）同程序 ⇒ `%16==0`。
6. **P7 8 B 基线语义**：只用 8 B 值（20 `int` + 17 `double` + 16 pointer + 变参）—— 改前/改后 **stdout、exit、`va_arg` 读值**逐项相同；**汇编允许不同**（帧大小/偏移可变），在完成区贴 `diff` 摘要（不得要求逐字节相同）。
7. **P8 16 B 值绝对对齐**：`struct S16`/`S12` 与 f128 在 8 B 栈参数之后的绝对地址 `%16==0`（不钉基址）；后续 8 B 参数值正确；12 B 例的「多耗 1 槽」已知后果如实记录。

**可达 FAIL（至少 3 处，`cp` 备份 + md5）**：

- 注入 ①：把 `Align(16)` 改回 `Align(8)`（临时树或源文件备份）⇒ P1/P2/P5 至少一处 FAIL；
- 注入 ②：把 P2 期望 `%16` 改成 `%8`（或断言取反）⇒ FAIL；
- 注入 ③：篡改 P7 基线输出一个字节 ⇒ `cmp`/值断言 FAIL。
- 每处还原后 md5 回原值、`default` 回绿；**禁** `git checkout/restore/stash`（用 `cp` 备份或临时树）。

## 回归 / 门控（全链）

- **构建**：`ninja -C .work/build/llvm clang llc` → rc=0；`make install-host JOBS=8` **单跑**（`ISS-210`；不得与其它 install/构建并发；若检测到并发 install 在跑，等待或报告，不抢跑）。
- **L1/L2/L3**：`make check`（L1）、`make check-modules`（L2）、`make check-full`（L3）全 rc=0。
- **lit**：`make check-lit` + `make check-lit-full`（含 `LLVM-111t` 新增 `m8-varargs-stack-align.ll`；不得回归）。
- **三套大型测试（全量两档，静态→动态）**：
  - `TESTCASES-046t`：embench-iot 全量（38/38）两档；
  - `TESTCASES-047t`：libc-test 全量两档（现行 excluded 30 口径不变；`pass/fail/known-fail/blocked` 逐项与改前对照，任何转移逐条归因）；
  - `TESTCASES-048t`：**A 类 222 全量两档**（B 类 1890 未接入驱动，本册不扩；若主会话要求再扩，另立/申报）。逐例判据与改前一致。
  - 驱动调用按 `INFRA-093t`：`--json-out` 必填、`--work-dir` 独立目录；**不得**用 `cmd | tee` 吞退出码；运行期 `timeout`（`124` = FAIL）。
- **构建面**：`make build-musl`、`make build-musl-shared`、`make build-picolibc` —— 逐项（目标/命令/rc/产物大小）落册。
  - `build-picolibc` **已知既有缺口**：`strtold.c` 的 `i128→f128` `uint_to_fp` 缺 `__floatuntitf`（`ISS-283`，改前亦失败）。本册须在改前留基线；若失败项与基线**逐项相同** ⇒ 记「非本册引入」并附 `ISS-283` 指针；若新增失败 ⇒ 必须修或停下报告。**不得**用排除/放宽掩盖。
- **补丁/源树门控**：`check-patch-tree`（计数不变）、`check-source-state`（clean+base+1）、`check-isa-coverage`（一行为同长度替换；若 `isel-cpp` 行号漂移则重跑 `gen_isa_coverage.py`）。
- **台账门控**：`check-tasks`、`check-knowledge-refs`、`check-no-residue`、`check-milestones-fresh`、`python3 tools/infra/check_issues.py`。
- 全部 rc=0；输出留 `.work/log/llvm/LLVM-112t-*.log`；**复杂命令先落盘再分块看**。

## 执行环境

**执行环境**：本地

## 接口规范

- **输入**：`SPEC-151t` 落地后的 16 B 规范/契约 + 用户裁定原话 + `ADR-0018 C9 D3` + `ADR-0031 D7` + `LLVM-111t` 现实现。
- **输出**：`DADAOFrameLowering.h/.cpp` 终态改动（必要时 `DADAOISelLowering.cpp` 的 `NumBytes`）；重新导出的 patch；`.work/evidence/LLVM-112t/*`；探针源码/日志；三套测试 `run.json` 指针；完成区。
- **约束**：
  - 临时目录仅 `/tmp/opencode/LLVM-112t/`；证据与日志留非易失位置。
  - 只动本册列出的文件；越界须披露。
  - 不提交 git（提交权归 architect）；不改 `**状态**`；不改 `spec/` / 契约 / ADR（归 `SPEC-151t` / architect）。
  - 失败保留现场并继续推进；有据重试须记录次数；只在需用户语义裁定时留问。
  - `install-host` 单跑；长构建/长测试按 `AGENTS.md` 长任务纪律（`setsid nohup`、落 `EXIT` 标记、申报预计耗时）。

## 验收标准

1. `Align(16)` 落地（或等价机制），且 `determineFrameLayout` 的 saved-FP 槽/对象偏移正确；`Align(16)` 为**唯一**必要的帧对齐开关（如需 `NumBytes` 修正，附 P5 证据）。
2. `call` 时 `sp % 16 == 0` 在 P1–P6 全部成立（含 FP + 奇数 8 B 栈实参、VLA、setjmp 后、静态/动态入口）；P1 **不再**依赖 16 B 局部钉基址。
3. P7 8 B 基线**语义**逐项不变（stdout/exit/值）；P8 16 B 绝对地址无条件 `%16==0`；12 B 同 16 B 起的已知后果如实记录。
4. `--inject` ≥3 处真实 FAIL、还原后回绿（md5 对账）；证据脚本 `default` 全 PASS。
5. `install-host` 单跑完成；`make check` / L2 / L3 / `check-lit` / `check-lit-full` 全 rc=0；`check-patch-tree` 计数不变、`check-source-state` clean+base+1。
6. `046t` 全量两档、`047t` 全量两档、`048t` A 类 222 两档逐项与改前对照；`build-musl`/`build-musl-shared` rc=0；`build-picolibc` 逐项、`ISS-283` 既有缺口按基线判定非回归。
7. 手写汇编/入口逐文件核对表（文件 → 是否改 `rb1` → 证据），零改或最小改均须披露。
8. 完成区贴真实命令/退出码/关键输出（不转述）；用户授权原话原样写入。

## 完成区
**测试结果**：探针 **8/8 PASS**（P1 f128 变参、P2agg S16/S12、Pva va_start 游标、Pcallsp 八类调用点、Pcallsp-fp/P5、Pvla alloca/VLA、Psetjmp、Pframe 帧取整；静态+动态入口；全部不再钉 16 B 基址）。P7 8 B-only 语义：stdout 与改前基线逐字节相同、exit 0（汇编仅帧大小差异，24 行 diff）。**lit 114/114**、`check-lit-full` 12/12；**046t static 38/38**（19 bench × O0/O2）；**047t static 10/10、dynamic 10/10**（含 5 个 `long double`）。`build-musl` rc=0（8 s）、`build-musl-shared` rc=0（5 s）、`check-musl-freshness` PASS——**但二者用安装根旧 clang**，未验新编译器产物（见遗留）。
**修改文件**：
- `components/llvm-project/patches/llvm/lib/Target/DADAO/{DADAOFrameLowering.h,DADAOFrameLowering.cpp,DADAOISelLowering.cpp}.patch`（3 份改；`series` 仍 82）
- `components/llvm-project/changelog.md`（本册条目）
- `tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（`gen_isa_coverage.py` 重派生：行号漂移 + 删除死参数）
- `.work/evidence/LLVM-112t/{run.sh,src/*,baseline/*}`（新增）
- `.work/source/llvm-project`（3 源文件 amend 进本地 `dadao: llvm-project patch series`；E1 = base+1、worktree clean）
**验收结果**：`ninja -C .work/build/llvm clang llc` rc=0（首轮 257 s、NumBytes 改动后 235 s、去死参后增量 ~4 min）；`check-patch-tree` **rc=0，181 patches OK**；`check-source-state` rc=0；`check-instrinfo`/`check-index-blobs`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-issues`/`check-isa-coverage`/`check-milestones-fresh`/`make check`(L1) 全 rc=0。证据脚本 `run.sh` **rc=0**；`--inject` rc=0（4 处 tamper 真实 FAIL→还原回绿）；`--inject-align8` rc=0（真回滚 `Align(8)`→重建→Pframe `sp%16==8` FAIL→还原→重建→绿）；`--inject-numbytes` rc=0（`NumBytes=ArgStackSize`→重建→P5 FAIL→还原→绿）。
**新发现/坑**：① 探针 asm 的 `ret rd8, 0` 会把 rd8 **置 0**（`ret rdHA, imms18` 是赋值形态），必须用 `ret rd0, 0` 保留返回值，否则栈实参读取恒为 0。② 仅删掉锚点后 P1 在旧编译器下**偶然通过**（帧大小恰好 16 倍数）——`Align(8)` 的真失败面须用 Pframe（单个 8 B 对象 + `-fomit-frame-pointer`）；本次 `align8` 回滚中 Pcallsp 仍绿、Pframe 才红。③ FP + 奇数个 8 B 栈实参是 `NumBytes` 的真实缺口（回滚实验 P5 红）；SP-only 帧由 `Align(16)` 自动覆盖。④ 本目标默认 `-O2` 仍生成 FP（未 `-fomit-frame-pointer`）。⑤ build-tree 的资源目录 builtins 陈旧（缺 `__eqtf2` 等），用 build-tree clang 跑套件需 shim 只把 `-print-libgcc-file-name` 指回安装根。⑥ lit E2E 的 qemu 解析要求 `LLVM_TOOLS_DIR` 指向扁平 symlink 目录（`tools_dir/../qemu`）。
**遗留问题**：① `install-host` 后须复验：`build-musl`/`build-musl-shared` 用**新** clang 重建 + `check-musl-freshness`；046/047 **全量**两档、048t A 类 222、L2/L3、全量 lit。② 048t 未跑（本册派单未含）。③ 本笔**未** `install-host`/L2/L3，**未** commit/push 主仓，**未**改 `**状态**`。

**安装根 + 全量复跑（2026-10-19 15:56）**：`install-host` rc=0（14:21 起）、`build-musl-shared` rc=0、`check-musl-freshness` PASS；全量复跑 `046t` **38/38 + 38/38**、`047t` **309/0/4/24 + 312/0/4/21**、`048t` **201/3/0/16/2**（两档一致，`lencod` 转 pass），结果落 `.work/tests/authoritative/`（主会话现场，本行不替代 L2/L3；L2/L3 由主会话另跑）。


## 审阅记录

#### 第 1 轮 engineer 自审
逐行审查 `DADAOFrameLowering.h/.cpp`、`DADAOISelLowering.cpp::LowerCall`/`reassignDADAOArgLocs` 及探针源码/证据脚本，findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 探针 callee 用 `ret rd8, 0`，而 `ret rdHA, imms18` 是**赋值**形态 ⇒ rd8 被清 0，栈实参断言假红 | ✅已修 | `callees.S` 改 `ret rd0, 0`（保留 rd8） | Pcallsp odd/even 值断言回绿（`bad=0`） |
| 去掉 16 B 锚点后，P1 在旧（`Align(8)`）编译器下**偶然**通过（帧大小恰为 16 倍数）⇒ 无法证明核心改动 | ✅已修 | 新增 `Pframe.c`（单个 8 B 对象 + `-fomit-frame-pointer`）并纳入默认/回滚模式 | `--inject-align8`：Pframe `sp1/sp2=…c8` FAIL，还原后 PASS |
| `--inject-align8` 的 sed 替换漏写前导 `/`，把源行改坏 ⇒ 重建 rc=1、探针用旧二进制假绿 | ✅已修 | 替换串补 `\/\*`；并保留“重建 rc≠0 即 FAIL”的断言 | 重跑 `--inject-align8`：两次重建 rc=0、探针先 FAIL 后 PASS |
| `HasStack16` 在 `NumBytes` 无条件取整后成为死出参/死变量（维护陷阱） | ✅已修 | 删除模板参数与 `Stack16` 跟踪；两处调用点同步 | `ninja` rc=0；`check-patch-tree` 181 OK；默认证据脚本全绿 |
| 探针 `first_bad` 在 `bad` 已被值检查置位时不记录 SP 失败（诊断误导） | ✅已修 | `first_bad` 改 NULL 初始化 + `!first_bad` 判定 | 回滚日志正确打印 `first_bad=8-byte-object-frame` |
| `NumBytes` 无条件取整会改变 SP-only 帧大小（最多 +8 B，ABI 布局允许变化） | ❌不修（设计内） | — | P7 8 B-only 语义逐字节不变、046/047 pass/fail 不变；布局变化已披露 |
| 大帧 `emitAddImm` 分块可产生非 16 倍数的**中间** SP；只有最终值需 16 B | ❌不修（无中间调用） | — | 规范只约束 `call` 执行时；分块序列内无 `call` |

自审判定：所有 finding 已处置，实现/探针/证据脚本与完成区真值一致；`**状态**` 按派单由主会话维护（本次未改）。


#### 第 1 轮 reviewer 验收
（待执行）

#### 提交留痕（architect，2026-10-19）
- **档位**：正常档（按主会话指定提交信息；同 `LLVM-111t` 5efb7ca 先例；`**状态**` = `待验收`，reviewer 第 1 轮尚未执行）。分支 `LLVM-112t` 提交 `0c7f43f`，squash 落 `master` 为 `3f13c13`；分支已删；**未 push**。
- **文件集**（显式 staging **8** 项，禁 `git add -A`）：3 份补丁 + `components/llvm-project/changelog.md` + `tools/llvm/llvm-isa-backend-matrix.{md,tsv}` + 本册（= 完成区「修改文件」所列内容文件）+ `.tao/knowledge/milestones.md`（状态行同步，`check-milestones-fresh` 强制；**对账补充项，已披露**）。`.work/evidence/LLVM-112t/` 由 `.gitignore` 排除、不入库。**无漏提 / 无多提 / 无越界**。
- **状态改动**：本册 `待开始 → 待验收`；`milestones.md` LLVM-112t 行同步 `待验收`；完成区追加「安装根 + 全量复跑（2026-10-19 15:56）」一行，既有内容未改。
- **门控真实 rc**：`check-patch-tree`=0（181）、`check-instrinfo`=0、`check_lit_gen.py`=0（64/64）、`check-isa-coverage`=0、`check-index-blobs`=0、`check-source-state`=0、`check-no-residue`=0、`check-tasks`=0、`check-knowledge-refs`=0、`check-component-changelog`=0、`check-musl-freshness`=0、`check-milestones-fresh`=0、`check_issues.py`=0（78 open / 29 closed）。
- **`make check`(L1) = 红（1 项）**：`check-run-artifacts` A2 `.work/tests/authoritative/latest is missing`（主会话 15:56 权威跑把 `embench-*/libc-*/llvmts-*` 平铺写进 `authoritative/`，未建 `Process-08` 规定的 `<TS>-<套件>-<档>/` 目录与 `latest` 指针；`.work/` 被 gitignore、与本笔内容无关）。距红 60 s 重试 **1 次**仍红；其余 209 项 PASS。未伪造 `latest` 掩盖。
