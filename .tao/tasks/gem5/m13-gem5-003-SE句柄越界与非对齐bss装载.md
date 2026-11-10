# m13-gem5-003: gem5 SE 缺陷修复（`SYS_WRITE` 句柄越界、非对齐 `.bss` 装载）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-gem5-002`（同一组件单写者，须串行）
**可并行分片**：否（组件单写者）
**状态**：已验证

## 背景

M13 差分要覆盖 dynamic 链接的 `llvm-ts`/`libc-test`，但 gem5 SE 有两个已登记的缺陷（`issues.yaml`）：

- **`ISS-358`（P2）**：`BaseSemihosting::callWrite` 用 `handle > files.size()` 判越界（应为 `>=`）。未 `SYS_OPEN` 时 `handle=1` 会读 `files[1]` 越界，`m12-chipyard-004` 探针实测 **segfault**。
- **`ISS-359`（P2）**：`src/sim/process.cc:196` 的 `fatal_if((seg.base & 3) != 0, ...)` 在 `p_vaddr + p_filesz` 非 4 字节对齐时直接 fatal，`dynamic llvm-ts` **7 例**因此 blocked（QEMU 可正常装载），名单见 `refs/INTEG-059t-se-parity-summary.json` 的 `new_findings`。

两者都直接压缩 M13 的可比样本（7 例 blocked + `SYS_WRITE` 崩溃风险），且都是 gem5 实现缺口，不是 spec 语义问题。

## 目标

1. **`ISS-358`**：边界判断改 `handle >= files.size()`；未打开句柄的 `SYS_WRITE` 返回错误码（按 Arm Semihosting 约定）而不是越界读。**不得**改变已打开句柄的正常路径。
2. **`ISS-359`**：删 `fatal_if`，改为「按段对齐要求零填到下一个对齐边界」（先按 `p_align` 向下对齐映射起点，再零填到下一 4 字节/页边界，具体以 gem5 loader 现有语义为准）；保持已对齐段行为不变。
3. **7 例 dynamic 复测**：`ISS-359` 名单中的 7 例在 gem5 SE 上从 `blocked` 转为可装载并可跑（pass 或按 oracle 判 fail，但**不得**死于 loader）。
4. **回归**：既有 SE 用例（static/dynamic）零回归；`check-inst`/`check-inst-smoke`/`check-arch`/L2 全绿。
5. `SYS_WRITE` 句柄用例：未 `SYS_OPEN` 直接 `SYS_WRITE` ⇒ 无崩溃、返回错误；`SYS_OPEN` 后正常写。

## 非范围

- 不改 `ISS-357`（stdout/stderr 写序，属 SE 驱动层口径，另立 testcases 任务）
- 不改 Tiny `hypv`/`cg3`（`m13-gem5-002`）
- 不改 QEMU / chipyard / spec
- 不重跑 3600s 长尾（`m13-testcases-003`）

## 验收标准

1. `ISS-358`：新增/复用探针证明「未 `SYS_OPEN` 的 `SYS_WRITE` 不再 segfault」，且打开句柄的正常写不变
2. `ISS-359`：7 例名单逐例从 blocked 转可跑（给出每例前后状态），并说明零填语义
3. 现有 SE 用例零回归（static/dynamic 抽样 + `check-inst` 全量）
4. `build-gem5` / `install-host` / `check-patch-tree` / `check-source-state` / L1 / L2 rc=0（外部红逐条核实归属）
5. 补丁由 `make_patch.py gem5` 导出（非手改），`patches/` + `series` + `changelog.md` 同笔
6. 一键证据脚本（含可达 FAIL 注入：改回 `>` 与改回 `fatal_if` 应各 FAIL）
7. 完成区 ≤30 行、无运行期路径

## 说明

- 两处改动分别属 `src/base/semihosting.cc`（或等价实现文件）与 `src/sim/process.cc`；以实际源码路径为准，任务书不写死行号。
- 组件单写者：与 `m13-gem5-002` 串行。
- 构建在主控机（`JOBS=8`），不占用 207/208。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定时留问。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 用户裁定须原样写入任务书。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`src/arch/generic/semihosting.cc`（6 处句柄边界 + `callClose` 空槽判定）、`src/arch/dadao/process.cc`（删对齐 fatal + 零填语义注释）、`components/gem5/changelog.md`、`tests/shared/bootrom/semihost_smoke.S`（注释纠偏）、证据 `run.sh` 与 `semihost_handles.{S,lds}`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 同文件 6 处 `handle > files.size()` 是同一越界（`callRead`/`ISTTY`/`SEEK`/`FLEN`/`CLOSE` 均可由 guest 触发），只改 `callWrite` 会留同类缺陷 | ✅已修（越界披露：同文件、同类判定，合法句柄行为不变） | 6 处统一 `>=`；`callClose` 补 `!files[handle]`（原缺，已关闭/占位句柄会解引用空槽） | 探针 14 条断言覆盖 5 个服务 + `handle == files.size()` 精确 off-by-one；回退 `>` ⇒ 探针不退出 0，还原 ⇒ 回绿 |
| 任务书字面「零填到下一个对齐边界」未新增填充代码 | ❌不修（附证据） | 只删 fatal，注释写明零填来源 | 零填由 loader 既有语义保证（`MemoryImage::write()` 对无文件数据子段按字节 `memsetBlob([base, base+size))`、页分配零初始化）。可观测证据：`Burg`/`spiff` 的 .bss 起点分别 `0x53de6`/`0x48dfa`（非对齐），两例 dynamic oracle 逐字节比对通过；其余 5 例该语义未单独观测（4 例超预算、`lemon` 撞既有页面故障缺口）。新增填充在本实现下不可证伪，属死代码（最简原则） |
| 探针初版用 `cmp.so rd, rd, rb` 汇编报错（`cmp` 只收 rd 操作数） | ✅已修 | 期望值先装 rd13 再比较 | `llvm-mc` rc=0；探针 14/14 |
| 探针沿用 `semihost_smoke.lds` 时 `.text` 溢出其 0x400 窗口 | ✅已修 | 专用 `semihost_handles.lds`（`.text ≤ 0x800`） | `ld.lld` rc=0；`llvm-readelf -l` 单 PT_LOAD FileSiz 0x848 |
| 运行期产物误落任务 worktree（`after/`、`red-*`、`sample/` 等） | ✅已修 | 移到任务临时目录；`run.sh` 的 RUN 路径同改并在仓库根做 CWD 校验 | `git status -uall` 只剩 4 改 + 1 新增 |
| `changelog.md` 条目初版插在 `m13-gem5-002` 之前 | ✅已修 | 移到其后（同日期，节内顺序） | `check-component-changelog` rc=0 |
| `semihost_smoke.S` 头注释仍称「gem5 会崩」 | ✅已修 | 改为三平台不可比的理由（无/未预置 `SYS_OPEN` 句柄；gem5 报 EBADF） | 重汇编产物与安装对象 `cmp` 逐字节相同（注释级改动） |
| `--full` 首跑被共享 gate lock（另一会话 `check-modules`）堵在 `build-gem5` | ✅已修 | `--skip-build` 复用已验证的修复后二进制 | `--inject` 首步 `A0 build-gem5` rc=0；B1–B6 依赖该二进制且全绿 |

判决：全部 finding 已修或附证据不修；状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（本人执行，括号内为真实退出码）**：证据脚本 `--full` **29/29 `RESULT=PASS`（rc=0）**、`--inject` **29/29（rc=0**，注入态探针 SIGSEGV rc=139，`cp`+md5 还原至原值后回绿**）**；`install-host`(0)、`check-patch-tree`(0，9 集 330 补丁)、`check-source-state`(0，gem5 `base+1`、clean)、`check-index-blobs`(0，244 新文件补丁 OK)、`check-gem5-decode`(0，positive 264/264 + negative 388/388)、`check-inst-smoke`(0)、`check-arch`(0)、`check-unit`(0)、`check-modules` L2(0)、`check-inst`(0，Vast **980/985 含 5 deferred** + Tiny **44/44**，与完成区逐字一致)；L1 `make check` **rc=2**。
**L1 外部红归属（已亲核）**：唯一红 = `check-milestones-fresh` 的 R1「`m13-testcases-003` 有 worktree 但台账在『待开始』」。**同一条检查在主树 master 重跑 rc=0 PASS**；成因是本任务分支分叉点早于他任务的台账迁移（分支内该行仍在『待开始』、且缺 `m13-testcases-004` 行），**非本任务改动** ⇒ 满足验收标准 4「外部红逐条核实归属」。（完成区写「2 条外部」，我方现场为 1 条 VIOLATION + 1 条台账缺行，均外部。）
**独立注入（我方，非 engineer 自检）**：把 `src/arch/generic/semihosting.cc` 中 `callWrite` 的 `RetErrno(size, EBADF)` 改为 `retError(EBADF)`（改被测产物）⇒ 重跑**同一**证据脚本 `--fast` ⇒ **`RESULT=FAIL` rc=1**（B1 actual=65、B2 `GEM5_EXIT_CODE=65`、B3 payload=0）⇒ `cp` 还原 + md5 与原值相等 ⇒ 重建 ⇒ `--fast` **`RESULT=PASS` rc=0**。
**`lemon` 既有缺口复现（我方）**：把 `fatal_if((seg.base & 3)…)` 原样回退并重建后跑 **static `lemon`**，仍 `rc=-6`、`panic … Page table fault when accessing virtual address 0` + `GenericPageTableFault::invoke`，与**任务前基线**（证据集 `GEM5-025t`，2026-11-07、二进制编译于当日）**同签名**；且该静态 ELF 4 个 PT_LOAD 尾均 4 字节对齐（`unaligned tails = 0`）⇒ 修复前它本就能装载，故障与本修复无关。
**7 例前后（我方 run.json 逐例）**：**后** = Burg pass 4.9s / spiff pass 399.6s / lemon blocked 57.3s `rc=-6` / obsequi·sqlite3·bc·mafft blocked 600s timeout；**前**（回退 `fatal_if`）= 7 例全 `blocked` 且 reason 逐例含 `not 4-byte aligned`（基址 0x53de6 / 0x51de5 / 0x4d355 / 0x48dfa / 0xe9833 / 0x53fe5 / 0xadd21）。与完成区一致（完成区 394s / 56.5s 对我方 399.6s / 57.3s 为现场值波动，非判据）。
**文件与纪律**：`tests/shared/bootrom/semihost_smoke.S` 逐行 diff **仅 `@@` 注释**（非注释改动 0 行），我方重汇编 `.o`/`.elf` 与安装对象 `cmp` 全等、且与**改动前**源汇编产物 md5 相同；`series` 100 行 ↔ 100 补丁双射、`sort -c` 通过；补丁/`series`/changelog/`semihost_smoke.S` 审前审后 md5 逐一相等；`git status --porcelain -uall` 审前审后均**空**、HEAD 仍 `a211d01c`（未 commit、未 push、未动台账）；完成区 7 行（≤30）、无运行期路径；我方运行期产物只落任务临时目录，未落仓库。
**语义核验**：`files[0]` = `push_back(nullptr)` 占位 ⇒ 合法句柄 `[1, size)`，`handle == files.size()` 必须判越界，`>=` **精确**；`RetErrno(size, EBADF)`（SYS_WRITE/SYS_READ「全部未传/未取」）与 `retError(EBADF)`（标量服务 -1）合 Arm Semihosting 约定，`semiErrno` 由 DADAO 分发层写入 ⇒ `SYS_ERRNO=9`；`handle < size` 且非空的正常路径逐字未变；`SYS_WRITE` 句柄与 QEMU/chipyard 的对齐仍受 `ISS-358` 已登记事实约束（QEMU arm-compat 未预置 fd 0/1/2 ⇒ 三平台该服务本就不可直接比对），本次改动未新增分歧。零填**非新代码**：`src/base/loader/elf_object.cc` 对 `p_memsz > p_filesz` 建 `data == nullptr` 子段、`MemoryImage::writeSegment` 走 `memsetBlob` 按字节零填至 `p_memsz`，**已对齐段行为不变**；被删的 `fatal_if` 校验的是 `p_vaddr + p_filesz`（文件/未初始化分界，非段起点），非架构要求，**不掩盖真实错误**——溢出/栈侵入/入口对齐/入口覆盖四条 `fatal_if` 仍在，对象级对齐由链接器保证、真错位会在 guest 侧 MALIGN 可见，Burg/spiff 另有逐字节 oracle 佐证。
**判决：Needs Revision**（**仅 1 项**，证据脚本断言的可达 FAIL 路径）：
- `inject_loop()` 的 `ck "I8 ${id}: old fatal blocks it" blocked "$klass"` 对 **lemon / obsequi / sqlite3 / bc / mafft 共 5 例恒真**——修复态与注入态 `klass` 实测**同为 `blocked`**（我方比对两份 run.json：仅 Burg/spiff 可判别），两支写同一结果，这 5 条**无可达 FAIL 路径**，标签「old fatal blocks it」未被断言验证。
- **改法**：`json_cases` 一并输出 `reason`，I8 改为 `ck "I8 ${id}: old fatal blocks it" loader-kill "$(loader_verdict "$reason")"`（注入生效 ⇒ `loader-kill` PASS；注入失效 ⇒ `loader-clean` **FAIL**，7 例均可达）；改后**只需**重跑证据脚本 `--inject` 并贴新输出，其余 28 条断言我方逐条核过均有可达 FAIL 路径、**无需重验**。
- 非阻断备注：`issues.yaml` 中 `ISS-358`/`ISS-359` 仍 `open`、`resolved_by: null`，留 `/complete` 知识沉淀处置。

### 第 2 轮 engineer 返工（第 1 轮 reviewer finding：I8 恒真）

审查范围：仅证据脚本的 `inject_loop()`（被测代码、B 组 6 条断言、C/G 组均未改；组件源保持 `base+1`、clean）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `ck "I8 ${id}: old fatal blocks it" blocked "$klass"` 对 lemon/obsequi/sqlite3/bc/mafft 恒真：这 5 例在修复态（60 s 预算 ⇒ timeout）与注入态（loader fatal）的 `klass` 同为 `blocked`，两支写同一结果，标签「old fatal blocks it」未被断言验证 | ✅已修 | I8 改为按 `reason` 判别：`ck "I8 ${id} [klass=$klass]: old fatal blocks it" loader-kill "$(loader_verdict "$reason")"`（`reason` 含 `not 4-byte aligned`/`seg.base & 3` ⇒ `loader-kill`，否则 `loader-clean`）；`json_cases` 本已输出 `reason`，未动 | ① `--inject` 重跑 **29/29 PASS（rc=0）**，7 例逐条 `expected=loader-kill actual=loader-kill`（注入态 reason 分别含基址 `0x53de6`/`0x51de5`/`0x4d355`/`0x48dfa`/`0xe9833`/`0x53fe5`/`0xadd21`）；② **负控**：同一断言对**修复态** `after/run.json` 跑 ⇒ **7/7 FAIL**（`actual=loader-clean`）、`RESULT=FAIL` rc=1 ⇒ 7 例均有可达 FAIL 路径 |

判决：finding 已修并在「注入态 PASS / 修复态 FAIL」两侧现场验证；状态保持 `待验收`。

### 第 2 轮 reviewer 验收

**重跑（本人执行，括号内为真实退出码）**：证据脚本 `--full --skip-build` **28/28 `RESULT=PASS`（rc=0）**；`--inject` **29/29（rc=0**，注入态探针仍 SIGSEGV rc=139，`cp`+md5 还原至 `d6c49e33…`/`9424d180…` 后回绿**）**；`check-patch-tree`(0，9 集 330 补丁)、`check-source-state`(0，gem5 `HEAD=304f55f933c3 count=1 clean=True`)；L1 `make check` **rc=2**，唯一红仍是 `check-milestones-fresh` R1 指向 `m13-testcases-003`，**主树同条检查 rc=0 PASS** ⇒ 外部，与第 1 轮同。两态 `run.json` 均由我方本轮重跑生成。
**① 恒真是否真消除（双侧现场）**：抽出脚本**自身**的 `ck`/`json_cases`/`loader_verdict` 逐条跑 I8 —— **注入态 7/7 `expected=loader-kill actual=loader-kill`，0 failed**；**修复态（`klass` pass/blocked 混合）同一断言 7/7 `actual=loader-clean` ⇒ `RESULT=FAIL`、rc=1**。上一轮不可判别的 5 例（lemon/obsequi/sqlite3/bc/mafft）两态 `klass` 仍同为 `blocked`，但 `reason` 不同 ⇒ **7 例每条都有可达 FAIL**。
**② 判据硬度与假 PASS 风险**：匹配串仅 `not 4-byte aligned` 与 `seg.base & 3`；我方修复态 `run.json` **命中 0 次**（7 条 reason 为 byte-exact matched / `rc=-6` / `timeout after 600s`）⇒ 负控真实变红，**无假 PASS**；反向若串变窄会判 `loader-clean` 而**响亮 FAIL**，不静默。注入态 7 例 reason 内基址与第 1 轮原值**逐一对上**：`Burg 0x53de6`、`lemon 0x51de5`、`obsequi 0x4d355`、`spiff 0x48dfa`、`sqlite3 0xe9833`、`bc 0x53fe5`、`mafft 0xadd21`。（非阻断观察：`entry point … is not 4-byte aligned` 与本串同尾；但 `validateElf` 中段对齐 fatal 先于入口对齐 fatal，且 7 个 ELF 的 PT_LOAD 尾均非 4 字节对齐（C 组 `at-least-1` 逐例 PASS），段 fatal 必先触发，该重叠不可达。）
**③ 改动范围（严格证明）**：把当前证据脚本的 I8 块反向还原为旧 4 行后 md5 = `55aa7fb2…`，与我第 1 轮记录的脚本 md5 **完全相同**、行数回到 336 ⇒ **除 I8 块外一字未动**（`json_cases` 本已输出 `reason`、`loader_verdict` 未改；B/C/G 各组断言逐行同第 1 轮）；被测代码与补丁/`series`/changelog/`semihost_smoke.S` 的 md5 与第 1 轮**逐一相等**，gem5 源 `304f55f` clean。
**纪律**：`git status --porcelain -uall` 审前审后均**空**、快照逐行相同；HEAD 仍 `2db81a66`（我未 commit/push、未动台账）；完成区 7 行（≤30）、各轮审阅记录 ≤40 行、无运行期路径；我方运行期产物只落任务审阅目录，未落仓库。
**判决：Accepted** —— 第 1 轮唯一阻断已修，并经「注入态 PASS / 修复态 FAIL」双侧现场验证；两缺陷真修且不掩盖错误、7 例前后状态如实、门控唯一外部红已确证归属。非阻断备注沿用第 1 轮：`issues.yaml` 的 `ISS-358`/`ISS-359` 仍 `open`、`resolved_by: null`，留 `/complete` 知识沉淀处置。

## 完成区

**测试结果**：ISS-358 探针 **14/14**（gem5 FS tiny：rc=0、guest exit 0、`SYS_OPEN(":tt")` 后 64 B 有效写）＋`semihost_write.elf`（裸 handle 1）由 rc=139 转 rc=0 / exit 0 / console 1136 B。ISS-359 七例（前 = 注入旧 `fatal_if`，均 0.37–0.41 s blocked；未对齐基址 Burg `0x53de6`、lemon `0x51de5`、obsequi `0x4d355`、spiff `0x48dfa`、sqlite3 `0xe9833`、bc `0x53fe5`、mafft `0xadd21`）：后 Burg **pass**、spiff **pass**（394 s，oracle 接受 exit=1）、lemon 可装载并运行 56.5 s 后撞既有页面故障缺口（`GenericPageTableFault`，static 轮同签名）、obsequi/sqlite3/bc/mafft 可装载但 600 s 预算内未完成（timeout，非 loader）。static/dynamic 各 4 例抽样 pass；`check-inst` Vast 980/985（5 deferred）+ Tiny 44/44。
**修改文件**：`components/gem5/patches/src/arch/generic/semihosting.cc.patch`（新增）、`components/gem5/patches/src/arch/dadao/process.cc.patch`、`components/gem5/series`、`components/gem5/changelog.md`、`tests/shared/bootrom/semihost_smoke.S`（注释）；另本任务书。组件源 `dadao: gem5 patch series`（base+1、clean；`make_patch.py gem5` 导出 2 written / 98 unchanged）；证据脚本与探针在运行期证据目录。
**验收结果**：红①`callWrite(handle=1)` 的 gdb 栈 `#1 … src/arch/generic/semihosting.cc:272` SIGSEGV、rc=139；红②`Burg` blocked，`segment '5(uninitialized)' base 0x53de6 is not 4-byte aligned`（0.37 s）。绿：`build-gem5` / `install-host` / `check-patch-tree`（9 集 330 补丁）/ `check-source-state`（gem5 `base+1`、clean）/ `check-inst`（980/985+44/44）/ `check-inst-smoke` / `check-unit` / `check-arch`（14/14）/ `check-gem5-decode` / L2 全 rc=0；L1 首跑 rc=0，收尾复跑仅 `check-milestones-fresh` 红（2 条**外部**：`m13-testcases-003` 台账仍在「待开始」、`m13-testcases-004` 未入表 ⇒ 他任务 worktree 与台账不一致；`check-temp-dirs`/`check-run-artifacts` 一度因他任务陈旧临时目录与 in-flight run 目录变红，清理/收口后复跑 rc=0）；证据脚本 `--full` **28/28**、`--inject` **29/29**（均返工后重跑，rc=0；`>` 回退 ⇒ 探针不退出 0；`fatal_if` 回退 ⇒ 七例逐条 `loader-kill`；同一 I8 断言对修复态 `run.json` 负控 ⇒ **7/7 FAIL rc=1**，故 7 例均有可达 FAIL；`cp`+md5 还原后回绿）。
**新发现/坑**：① 句柄越界是**同文件 6 处**同一模式（不止 `callWrite`），`callClose` 还缺空槽判定；② 零填不需新代码：`MemoryImage::write()` 按字节 memset 无 data 子段、页零初始化，错的只是「段基址必须 4 字节对齐」这条校验；③ `spiff` dynamic 的 oracle 接受 `exit=1`（与 static 轮同类）；④ 七例中 4 例是**时间**上限（qemu 12–1103 s，gem5 慢 3–300×），非装载问题。
**遗留问题**：① `lemon` dynamic 仍 blocked，根因是 guest 未映射访问 ⇒ gem5 `GenericPageTableFault` abort（SE 不向 guest 投 SIGSEGV）；static 基线同签名，属既有缺口，建议另立任务；② 4 例长尾属 `m13-testcases-003` 预算议题；③ gem5 FS semihosting 句柄语义目前仅由运行期探针覆盖，仓库内无常驻用例（可选后续任务）。

#### 收尾（architect，2026-11-10 11:27）

- 第 2 轮 **Accepted**：I8 改为 `reason` 判别后，**两侧现场实证**——注入态 7/7 `loader-kill` PASS、修复态 7/7 `loader-clean` FAIL；上一轮不可判别的 5 例（`lemon`/`obsequi`/`sqlite3`/`bc`/`mafft`）`klass` 仍同为 `blocked` 但 `reason` 可判 ⇒ 恒真消除。
- 改动范围严格限于 I8：反向还原后脚本 md5 与第 1 轮完全相同（336 行），被测代码/补丁/`semihost_smoke.S` md5 逐一相等。
- 两缺陷真修：`callWrite` 边界 `>=`（`handle==files.size()` 精确）、`.bss` 非对齐改零填（`fatal_if` 校验的是 `p_vaddr+p_filesz` 分界，非架构要求；溢出/栈侵入/入口对齐/入口覆盖四条 fatal 仍在）。
- 7 例前后如实：`Burg`/`spiff` pass；`lemon` 可装载后 `GenericPageTableFault`（转 `m13-gem5-004`）；其余 4 例 600 s 预算内未完成（属长尾）。
- 关闭 `ISS-358`/`ISS-359`（`resolved_by: m13-gem5-003`）。
