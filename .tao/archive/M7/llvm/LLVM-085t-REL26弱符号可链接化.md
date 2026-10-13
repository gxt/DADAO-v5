# LLVM-085t: REL26 未定义弱符号可链接化（`ISS-194`）

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-079t`/`080t`（`已验证`）；同改 `components/llvm-project/patches` ⇒ **串行**
**状态**：已验证

> 立项来源：用户 2026-10-12 裁定「**先在 M7 内做解锁件再归档**」；依据 `ISS-194`（blocked **26** 条）。

## 目的

`TESTCASES-042t` 发现：`lld` 不为**未定义弱函数**生成 veneer/弱桩 ⇒ 链接期报 **`R_DADAO_REL26 out of range`**（如 `test-iconv`），**26 条** picolibc test 因此 blocked。本任务让**未定义弱符号**在 DADAO 目标下**可链接**（弱桩/veneers/或按 `ADR-0019` 口径放宽该情形的重定位处理），并解锁这 26 条。

## 接口规范

- **输入**：`ISS-194`（`notes` 含复现与根因方向：LD 对未定义弱函数未生成 veneer/弱桩）；`ADR-0019`（DADAO 重定位类型口径，**`D8` 禁 `ABS32`** 等）；`.tao/knowledge/contract-elf.md`（ELF/reloc 合约）；`components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/**` 与 lld 侧 DADAO 目标（现场定位）。
- **输出**：
  1. **未定义弱符号可链接**（lld/MC 侧，范围 `components/llvm-project/patches/**`）：实现弱桩/veneer 或等价机制；**保持强符号与越界检查的严格性不变**（不得为通过而放宽全局检查）。
  2. **复现/回归用例**：最小 `weak` 用例 + `test-iconv` 类真实用例（`llvm-mc`/`lld` + QEMU 运行）。
  3. **重建**（增量 `build-mc` + `install-host`；申报耗时、`setsid` 规则同上）；**picolibc test 全量重跑**（`make check-picolibc-tests-full`，~7 min）⇒ before/after 四分类。
  4. `milestones.md` 流水更新 `LLVM-085t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**真源 = `ADR-0019`/`contract-elf`/spec**；**不得**放宽到"任何越界 REL26 都放过"；计数不写死。

## 验收标准

1. **可链接**：`ISS-194` 所述 `R_DADAO_REL26 out of range` 场景**消失**——最小弱符号用例 + `test-iconv` 类真实用例**链接并运行成功**（真实输出 + 退出码，**非抽样**：给 ≥3 个原 blocked 用例的 before/after）。
2. **严格性未放宽**：**强符号**越界/非法重定位仍**被拒**（给反例输出）；`ADR-0019 D8`（禁 `ABS32`）等既有口径不变（门控为准）。
3. **解锁量化**：`check-picolibc-tests-full` 重跑 ⇒ `pass` **上升**、`blocked` **下降**（before/after 数字 + 解锁用例清单）。
4. **门控**：`make check`、`check-lit`、`check-patch-tree`、`check-index-blobs`、`check-no-residue`、`check-picolibc-tests` 各 EXIT=0。
5. **反例可失败**：注入（构造**强**符号越界 ⇒ 应 FAIL 的断言；或恢复某用例）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
6. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）
1. 临时目录 `/tmp/opencode/LLVM-085t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥、`.work/source/llvm-project` = `base+N`、`series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/llvm-project/patches/**`、`tests/**`、`tools/llvm/**` 若需、任务书、`milestones.md` 行）；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时留问（如涉及 ABI/reloc 语义取舍 ⇒ 停下报告）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、**计数不写死**、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **长任务**：申报耗时；>10 min ⇒ `setsid nohup` + `XXX_EXIT`；`JOBS=8`、禁全核、一次一个；`124` 判 FAIL。
10. **计数不写死**。

## 完成区

**测试结果**：一键证据 `<证据目录>/run.sh` 基线 **rc=0**（16 项全绿）、`--inject` **rc=0**（I1：lit 期望注入→FAIL rc=1→`cp`+md5 还原命中回绿；I2：强符号探针改弱→链接成功⇒严格性检查 FAIL，证断言可达 FAIL）。门控：`make check` / `check-lit`(103/103) / `check-patch-tree` / `check-index-blobs` / `check-no-residue` / `check-picolibc-tests`(fast 20: pass16 fail0 excl2 blocked2) 全 rc=0；picolibc 全量四分类见验收③（`XXX_EXIT=0`）。计数均现场统计；`forms` 期望值由 `llvm-readobj` 现场派生（非写死）。
**修改文件**（仅本任务范围）：
- `components/llvm-project/patches/lld/ELF/Arch/DADAO.cpp.patch`：未定义弱符号的 PC 相对分支/call → 解析为本位（自循环）；REL26 的 `call-iiii`(0x74) 改写为 `jump-iiii`(0x70)
- `tests/e2e/weak_undef_e2e.c`、`tests/e2e/weak_hook_def.s`、`tests/e2e/weak_undef_forms.s`、`tests/e2e/weak_undef_strong.s`、`tests/e2e/lit/weak_undef.test`（均新建）
- `tests/e2e/lit/lit.cfg.py`（+`%not` / `%llvm_objdump` 替换）【**越界披露**：任务书范围写 `tests/**`、下发提示写 `tests/llvm/**`，本任务实际用到 `tests/e2e/**`】
- `.tao/knowledge/milestones.md`（`LLVM-085t` 行）；本任务书；证据/日志（非 git）：`<证据目录>/`、`<日志目录>/`

**用户裁定原话（2026-10-12；lessons §3.3 原样落盘）**：问「未定义弱函数 PC 相对 call 按哪一机制（A=ARM/AArch64 惯例 / D=链接器局部弱桩 / C=真 veneer 跳到 0 / 先只登记）」→ 答：**「学习risc-v，做成死循环；需要注意的是：call指令本身还有压RAS的行为，导致其它异常；所以，此处应改为jump指令，即jump [rb0, 0]」**
取得渠道：**engineer 直接提问用户**（据完成区自述）；**渠道注记待用户复核**

**验收结果**（与真实输出逐条对齐；计数均现场统计）：
1. **可链接**：before `ld.lld: error: ...(function _strerror_r: .text._strerror_r+0x80): relocation R_DADAO_REL26 out of range: -69269232553464 is not in [-8388608, 8388607]; references '_user_strerror'`（`test-iconv`）；after 最小弱用例与 `test-iconv` **rc=0**。27 条原 blocked：**22 pass + 4 self-skip(excluded) + 1 移因**（`test-double-free` → RASOF，故障 PC 定位 `__sigjmp_setsigs`，我另用「真 `ret` 桩」链接复现同样 RASOF ⇒ 与弱符号无关）。编码：`call [rb0, X]`→**`jump [rb0, 0]`**；`br.z`/`br.eq`→`[rb0, 0]`（`forms.o` 的 5 条 REL26/20/14 ⇒ 5 自循环）。
2. **严格性未放宽**：未定义**强**符号 ⇒ `undefined symbol: strong_fn`（rc=1）；已定义**远距**强符号（`--defsym strong_fn=0xFC0010000000`）⇒ `R_DADAO_REL26 out of range`（rc=1）；已定义弱符号 ⇒ 正常 `call [rb0, X]`（hook 值 9 到达调用者，guest rc=9，0 处 `jump [rb0,0]`）。`--noinhibit-exec` 下 LLD 本就把未定义符号降为 warning（该 flag 自身口径，未改）。
3. **解锁量化**：`check-picolibc-tests-full` **pass 152→174（+22）/ blocked 65→39（−26）/ excluded 18→22（+4）/ fail 0 / 回归 0**（before = 基线现场；逐条 transitions：blocked→pass 22、blocked→excluded 4）。解锁清单 = 22 pass（test-dprintf/fflush/fgetc/fgets-eof/fopen/fread-fwrite/freopen/grp/iconv/mktemp/posix-io/pwd/rand/rename/setvbuf/strerror/strerror_s/strerrorlen_s/tmpnam/ungetc-ftell/vfprintf-s/wchar）+ 4 self-skip（test-access/dirent/ftrunc/statvfs）。
4. **门控 / 反例**：门控见「测试结果」（各 EXIT=0）；反例见「测试结果」（I1/I2 各 FAIL→还原/回绿）。

**新发现/坑**：
- **口径**：DADAO 学 RISC-V（自循环）；**DADAO 的 `call` 会压 RegRAS**，而 callee 不存在 ⇒ 其 push 无人 pop（外层 `ret` 会弹出陈旧条目）⇒ 必须改写成 `jump`（用户裁定）。若该 call 真被执行 ⇒ **可见 hang**；本批 27 条全部由 `&sym == 0` 守卫、不执行。
- `isUndefWeak()` **不足**：LLD 把 **hidden** 未定义符号的 binding 降为 local（实测 hidden 未定义弱仍报越界）⇒ 按跨目标惯例改用 `isUndefined()`（ARM/AArch64/PPC/RISC-V 同，`InputSection.cpp` `R_PC`）；强符号仍由 LLD 的 undefined-symbol 检查拒绝。
- **非 DADAO 特有**：x86-64 把 `--image-base` 抬到 `0x100000000000` 时，weak `call foo` 同样报 `R_X86_64_PLT32 out of range`（实测）——是「相对分支 + 弱符号=0 + 映像远离 0」的通用组合。
- 各 ISA 惯例（真源 `lld/ELF/InputSection.cpp` `R_PC` 分支）：ARM/AArch64 分支→`P+4`、非分支→`P`；RISC-V/PPC→`P`；其余（含 DADAO 原状）→`sym->getVA()=0`。
- `test-double-free` 现 blocked 于 RASOF（`__sigjmp_setsigs`），与 `setjmp/longjmp` 桩同族（原「setjmp 1 条」→ **2 条**）。
**遗留问题**：
- **口径固化待办（超本任务文件范围 ⇒ 交 architect）**：`contract-elf.md §3.2` 与 `ADR-0019 §D6` 均无「未定义弱符号」条款；本任务按用户裁定落地（原话见上），建议随 `/complete` 立一条 ADR/contract 修订并回填 `ISS-194.resolved_by`。本任务**未改** `spec/`、`contracts/`、`issues.yaml`。
- `R_DADAO_REL12`（PC 相对**访存**）的未定义弱情形**未纳入**（本批无此情形 ⇒ 保持严格报错）；如需另议。
- 全量余 blocked 39 属其它已登记缺口（vfscanf 11 / `__muldc3` 6 / ISS-193(b) 5 / QEMU signal 6 5 / vfwscanf 3 / lgammaf_r 2 / (e) 2 / RASOF 1 / setjmp 1 / log10f·tgammaf·nearbyintf 各 1）。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查 `lld/ELF/Arch/DADAO.cpp` 的改动（1 处判定 + 1 处 call→jump 改写 + 2 条注释），并复验：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 判据 `isUndefWeak()` 漏 **hidden** 未定义弱（LLD 把其 binding 视为 local，`isWeak()` 变 false） | ✅已修 | 判定改 `rel.sym->isUndefined()`（对齐 LLD 跨目标 `R_PC` 惯例），并加注释说明；变量名 `weakBranch`→`undefBranch` | 修前 hidden 未定义弱 ⇒ `R_DADAO_REL26 out of range` rc=1；修后 rc=0 且编码 `jump [rb0, 0]`；`forms.s` 增 hidden 用例（5 reloc⇒5 自循环） |
| `call`→`jump` 改写是否误伤已定义弱 / 强符号 | ❌不修（结构隔离） | 改写仅在 `undefBranch && type==REL26` 分支内 | 已定义弱：`call [rb0, …]`×2、`jump [rb0,0]`×0、guest rc=9；未定义强 ⇒ `undefined symbol` rc=1；已定义远强 ⇒ 越界 rc=1 |
| 强符号越界是否被放宽 | ✅已修（保持原样） | 未改 `checkInt` 路径 | 证据脚本两条 must-fail 断言（`undefined symbol` / `R_DADAO_REL26 out of range`）现场通过 |
| 未定义弱落在非 `call/jump` 指令上 ⇒ 是否静默 | ✅已修（显式失败） | 增 opcode 校验：非 0x74/0x70 ⇒ `Err` | 代码级；未构造该输入的用例（防御性分支，本批 0 例） |
| `val = rel.addend`（丢弃原 `S+A−P`）是否静默丢信息 | ✅已修（依据 RISC-V `dest = P + A`） | — | MC 对 `call [rb0, sym]` 发 `r_addend=0`；`disp & 3` 对齐检查与 `checkInt` 仍生效（addend 非法时显式报错） |
| `isExec` 未参与 weak 分支（REL26 若落非 exec 段会改字节） | ⏸延后（不可达） | — | `R_DADAO_REL26` 由汇编器只发在指令上；本批 0 例，已记遗留 |
| 证据脚本计数是否写死 / 断言是否可达 FAIL | ✅已修 | `forms` 期望值改为由 `llvm-readobj` 现场派生；`record()` 捕获被检命令 rc | 基线 rc=0（16 项）；`--inject` rc=0：I1 md5 `fdf11d1b…` 还原命中、I2 严格性检查 MUST fail rc=1 |
| 新增 `%not`/`%llvm_objdump` 替换、使用 `tests/e2e/**` 是否越界 | ✅已披露 | — | 完成区越界披露条；`check-lit` 103/103 不回归 |
| 任务书「26 条」 vs 现场 27 条 | ✅已修 | 完成区按现场 27 记 | `ISS-194` notes（`LLVM-084t` 26→27）+ 本次现场 27 |

判决：finding 均 ✅已修 / ⏸已披露（不可达）/ ❌已核定（结构隔离），无未处置项 ⇒ 状态 `待验收`。**待用户/架构师追认事项**：口径固化（ADR/contract 修订）已列入遗留、交 `architect`。

#### 第 1 轮 reviewer 验收

**重跑记录**（workdir=仓库根；均为我的真实输出/退出码，禁 `|tee` 吞码）：

| # | 命令 | 真实结果 |
|---|---|---|
| 1 | `make check`/`check-lit`/`check-patch-tree`/`check-index-blobs`/`check-no-residue`/`check-picolibc-tests` | 各 rc=0（lit **103/103**；patch-tree 4 组件 123 patches OK；blobs 88 OK；fast 20: pass16/excl2/blocked2/fail0） |
| 2 | `make check-picolibc-tests-full`（setsid 后台，`FULL_EXIT=0`） | `total=235 pass=174 fail=0 excluded=22 blocked=39` ⇒ 与自述四数一致（我的统计）；与 before 报告（152/0/18/65）机械对账：blocked→pass 22、blocked→excluded 4、回归 0 |
| 3 | `<证据目录>/run.sh` 重跑 | rc=0，16 项 exp/act 逐条对齐 |
| 4 | 22 条解锁抽 **8** 条直跑 QEMU | test-iconv/dprintf/wchar/strerror/fopen/grp/vfprintf-s/rename 均 guest rc=0（无「仍 blocked 记 pass」；22 名单与 SHOULD_FAIL/EXCLUDED/UNSUPPORTED 三表零交集） |
| 5 | 4 条 blocked→excluded 直跑 QEMU | test-access/dirent/ftrunc/statvfs 各 **guest rc=77** + 首行 `fake …, skipping` ⇒ 用例自身 SKIP（Meson 口径），非 harness 静默跳过/隐藏失败 |
| 6 | test-double-free 直跑 | guest rc=138（0x8A RASOF）⇒ 移因机器故障，与弱符号无关（before 为 REL26 blocked） |
| 7 | 严格性三类（我自写源） | 未定义**强** ⇒ rc=1 `undefined symbol: strong_fn`；`--defsym strong_fn=0xFC0010000000` ⇒ rc=1 `R_DADAO_REL26 out of range`；已定义**弱** ⇒ 正常 `call [rb0,X]`、guest rc=9 |
| 8 | 自循环语义实证 | 未定义弱（含 hidden）⇒ 链接 rc=0、3 站点均 `jump [rb0, 0]`（字节 0x70）；无守卫执行 ⇒ guest hang（timeout rc=124，本位自循环非跳 0） |
| 9 | REL12 未纳入核 | `ld.o rd8,[rb0,weak_ld]`+`.weak` ⇒ rc=1 `R_DADAO_REL12 out of range` ⇒ 仍严格报错 |
| 10 | `<证据目录>/run.sh --inject` | rc=0：I1 lit 注入→rc=1 FAIL、还原 md5 `fdf11d1b…` 命中；I2 弱化探针 rc=0 ⇒ 严格性断言 FAIL rc=1（与完成区一致） |

**独立注入（不与 I1/I2 重复，反证核心判据）**：改被测产物 `<源树>/lld/ELF/Arch/DADAO.cpp` 的 `isUndefined()`→`isUndefWeak()`，`cp`+md5 备份 `713c6f68…` ⇒ 重建（`REBUILD_INJECT_EXIT=0`）⇒ 重跑**同一脚本** rc=**1 FAIL**（`forms: REL26/20/14 link`、`forms: one self-loop`、`lit weak_undef.test` 三项；hidden 用例复现 `R_DADAO_REL26 out of range`，与 ISS-194 原故障签名一致）⇒ `cp` 还原、md5 命中 `713c6f68…` ⇒ 重建（`REBUILD_RESTORE_EXIT=0`）⇒ 重跑 rc=0 回绿；`make check-source-state` rc=0（llvm-project base+1 clean）。**反向证明**：hidden 未定义弱确为 `isUndefWeak()` 漏判面、`isUndefined()` 判据不可回退。

**机制正确性**：① 触发面仅 `rel.sym->isUndefined() && type∈{REL26,REL20,REL14}`；call→jump 改写仅 `undefBranch && REL26`，非 call/jump 显式 `Err`；已定义弱/强走原路径（实测）。② RegRAS：`call_iiii_ra(0x74)` 压栈（`contracts/abi.yaml` RegRAS 事实）而自循环 callee 无人弹 ⇒ 改 `jump_iiii_rb(0x70)`（与 `contracts/opcodes.yaml` 一致）；真 call/ret 平衡由 guest rc=9 实测。③ 守卫不可达（grep 实证）：`strerror.c:351 if (&_user_strerror == NULL || …)`、`semihost/common/{open,write}.c (… && gettimeofday)`、`stdlib/arc4random.c if (arc4random_abort)` / `(arc4random_fork_detect && …)`。④ 上游同类判据可定位：`lld/ELF/InputSection.cpp` `R_PC` 分支 `r.sym->isUndefined()` + hidden 注释（ARM/AArch64/PPC/RISC-V 分派，RISC-V=本位自循环）。

**约束核验**：临时文件全在 `/tmp/opencode/LLVM-085t-review/` ✓；未 commit、实现未改（注入期唯一改动已 md5 还原）✓；rc 均直捕 ✓；计数现场统计（run.sh 期望值由 `llvm-readobj` 现场派生）✓；越界核：`contracts/`、`tests/vectors/`、`spec/` 无改动；`tests/e2e/**`+`lit.cfg.py`（`%not`/`%llvm_objdump`）已披露且恰当、lit 103/103 不回归；完成区「修改文件」与工作树逐条对账一致（并行任务的未跟踪任务书不属本任务）。验收前后 `git status` 与 9 个产物 md5 逐行一致。

**裁定记录（专项，只判完备性、不判真伪）**：议题/选项/原话/结论**齐备**（原话完整引用，含 A/D/C/先只登记四选项）；**取得渠道未写明**（有「问→答」结构与「用户裁定原话」标注，但未注明系「engineer 直接提问用户取得」还是「经主会话问答取得」）⇒ 记录完备性 finding（非阻断，见整改项①）。

**判决：Accepted（阻断项 0）**。非阻断整改项：① 裁定记录补一行「取得渠道」；② 口径固化（`ADR-0019`/`contract-elf` 无「未定义弱」条款）按遗留交 architect，随收尾立 ADR/contract 修订并回填 `ISS-194`；③ `R_DADAO_REL12` 未纳入（本批 0 例、实测仍严格）另议；④ `--noinhibit-exec` 下未定义强符号亦落自循环（该 flag 下 LLD 本把未定义降为 warning）建议口径固化时一并写明；⑤ 证据脚本加固建议：scope 检查未覆盖 untracked（已在脚本注释披露）、picolibc 子步骤未断言 harness 自身 rc/未先清旧 JSON（陈旧产物理论可假绿）。
