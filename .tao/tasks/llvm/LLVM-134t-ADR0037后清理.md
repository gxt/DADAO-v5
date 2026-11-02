# LLVM-134t: ADR-0037 后清理（冗余 `ext.so` + ABS48 显示偏移）

**模块**：llvm
**项目里程碑**：M10
**依赖**：LLVM-133t（语义核对）、LLVM-132t（fixup 大端修正）
**状态**：已验证

## 执行环境
**执行环境**：本地（LLVM 增量重建由主会话执行）

## 接口规范

### 背景（实测）
1. `DADAOISelLowering.cpp` 两处在窄无符号比较后做 `SIGN_EXTEND_INREG`：
   - `LowerBR_CC`（≈2541–2547）：为 `br.n/np/p/nn` 规范化 {-1,0,1}；
   - `LowerCmpSelect`（≈2721–2726）：为 `cs.*`/`setcc` 同款。
   ADR-0037 后 `cmp.ut/uw/ub` 的 -1 **已是 64 位全 1** ⇒ 该扩展是恒等变换，只多发射一条 `ext.so`（注释仍是旧口径）。
2. `DADAOAsmBackend::getFixupKindInfo` 的 `DADAO_FK_ABS48` 仍 `{0, 16, 0}`；按 LLVM-132t 的大端规则（`offset = 32 − size`）应为 **16**。它只影响 `--show-encoding` 的位标记（整字节标记，不触发断言），不影响编码/链接。

### 输出
1. 删除上述两处 `SIGN_EXTEND_INREG`，同步过时注释；确认窄无符号分支/条件赋值语义不变（`cmp.u*` 已全 1）。
2. `DADAO_FK_ABS48` 的 `TargetOffset` `0 → 16`。
3. 补 lit：
   - i32/i16/i8 无符号比较 + `br.n`/`cs.n` 的汇编**不含** `ext.so`；
   - `set.zw/or.w/andn.w`（带符号）`--show-encoding` 的 A 标记落在正确位。
4. 不改 QEMU/spec/契约；不改 `applyFixup`。
5. **DWARF64 默认的 `cc1as`/`llvm-mc` 路径**（LLVM-130t 遗留）：目前 `clang -c x.s`（cc1as）与 `llvm-mc` 不继承 DADAO 的默认 DWARF64，也不报 `-gdwarf32`。需改共享 `clang/lib/Driver/ToolChains/Clang.cpp`（`-gdwarf64` 注入与 `-gdwarf32` 拒绝的 target 门控），与本次重建同批；完成区须单列共享文件理由。

### 约束
- 若删除 `ext.so` 暴露其它路径依赖（例如某处仍需窄位规范化），停下报告，不硬删。

## 验收标准
1. `llc -O2`：窄无符号比较用于分支/选择时无 `ext.so`（贴指令计数，修复前有、修复后 0）。
2. `llvm-mc --show-encoding` 的 ABS48 三指令标记与预期一致。
3. `make install-host` 后 L1 / L2 绿；新增 lit PASS。
4. 反例注入（恢复 `SIGN_EXTEND_INREG` 或 `0` 偏移）⇒ 断言红 ⇒ 还原 ⇒ 绿。
5. 完成区贴真实输出与退出码。

## 完成区
**测试结果**：静态自检全绿：`run.sh --with-l1` **24 passed / 0 failed**（rc=0）、`run.sh --inject` **39 passed / 0 failed**（rc=0）。运行期**未重建**（任务约束），旧安装根上 `run.sh --runtime` = **24 passed / 12 failed**（预期红：cc1as/llvm-mc 默认 DWARF64、ABS48 标记、`ext.so` 计数 6、4 lit FAIL）；这些红同时就是运行期断言的**可达 FAIL 实证**。
**修改文件**：`components/llvm-project/patches/clang/lib/Driver/ToolChains/Clang.cpp.patch`（新增补丁）；`…/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`；`…/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp.patch`；`…/patches/llvm/tools/llvm-mc/llvm-mc.cpp.patch`；`components/llvm-project/{series,changelog.md}`；`tests/llvm/lit/CodeGen/DADAO/{cmp-u-branch.ll,narrow-int.ll}`；`tests/llvm/lit/MC/DADAO/{show-encoding-fixup-bigendian.s,lit.cfg.py,dwarf64-default.s(新)}`；`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（行号派生重生成）；`.tao/knowledge/milestones.md`（状态行）。证据：`.work/evidence/LLVM-134t/`（`run.sh`/`check_static.py`/`mk_syntax_cmds.py`/`baseline/`）。
**共享文件理由**：`addClangTargetOptions`（`DADAO.cpp`）**只喂 cc1**（LLVM-130t 已证），cc1as 不经该钩子 ⇒ `-gdwarf64` 注入与 `-gdwarf32` 拒绝的唯一落点是共享 `ClangAs::ConstructJob`（`clang/lib/Driver/ToolChains/Clang.cpp`）；改动包在 `if (Triple.getArch() == llvm::Triple::dadao)` 内，其它 target 零影响。`llvm-mc` 无 driver 层，其默认格式只能在 `llvm-mc.cpp` 的 `setDwarfFormat` 处做同款 DADAO 门控（`-g` + `Triple::dadao`），其它 target 不变。
**验收结果**：
- `make apply-series` rc=0 → `llvm-project already applied (base+1, matches patches)`。
- `-fsyntax-only` 4 TU（真实 compile_commands 命令）：`Clang.cpp` / `DADAOAsmBackend.cpp` / `DADAOISelLowering.cpp` / `llvm-mc.cpp` 全 **rc=0 bytes=0**。
- `make check-patch-tree` rc=0 → `5 component(s), 202 patches OK`。
- `make check`（L1）rc=0 → `repository checks (L1): PASS`（含 `check-isa-coverage` 重生成后）。
- `bash .work/evidence/LLVM-134t/run.sh --with-l1` rc=0 → `RESULT: 24 passed, 0 failed`；`run.sh --inject` rc=0 → `RESULT: 39 passed, 0 failed`（日志 `.work/log/llvm/LLVM-134t-*.log`）。
- 旧安装根反例（未重建，故为预期红）：`run.sh --runtime` rc=1 → `RESULT: 24 passed, 12 failed`；4 个目标 lit 全 FAIL（`CHECK-NOT: ext.so` 命中、ABS48 标记、cc1as 失败）。
- 反例：`run.sh --inject` 7 类注入（恢复 `SIGN_EXTEND_INREG`、ABS48 `16→0`、clang `-gdwarf64→-gdwarf32`、llvm-mc `dadao→x86_64`、删 lit `CHECK-NOT`、回退 ABS48 标记、坏 TU）逐条**目标断言转红**，`cp`+md5 还原后 md5 全等、静态集回绿。
**重建后验收清单**（主会话 `make install-host` 后执行）：
1. `bash .work/evidence/LLVM-134t/run.sh --runtime` → 期望 **0 failed**（含 4 个目标 lit PASS、`ext.so`=0、6 条 ABS48 标记、cc1as/llvm-mc CU `format=DWARF64 addr_size=0x08`、`-gdwarf32` rc=1、obj md5 仍 `98f1a6a5…`）。
2. `make check`（L1）/`make check-modules`（L2）绿；`make check-width-sizes` 绿。
3. 若 `ext.so` 仍非 0 ⇒ 另有窄位规范化依赖，按任务约束**停下报告**（未硬删）。
**新发现/坑**：① 删两处扩展使 `DADAOISelLowering.cpp.patch` 行号下移，`gen_isa_coverage` 派生的 `buildmi/isel-cpp` 证据行号须重生成（否则 L1 `check-isa-coverage` 红）——任务书未列该同步面。② `llvm-mc` 无 `-dwarf32` 选项（只有 `-dwarf64`），"拒绝 `-gdwarf32`"只对 clang 驱动成立；llvm-mc 传 `-gdwarf32` 本就 unknown-arg rc=1。③ 证据脚本的 lit 反查只能数 `CHECK` 指令行，注释里出现 `ext.so` 会假红。
**遗留问题**：运行期验收（含 L2 / lit 全量）需主会话重建后跑，本笔**未跑构建**；`changelog.md` 与 `llvm-isa-backend-matrix.*` 属门控/流程要求的同步面，任务书未逐项列出，已在此声明。

## 审阅记录

#### 第 1 轮 engineer 自审

**方式**：自主逐行审查（`subagent_depth=1`）；对照 ADR-0037 D1、`contract-isa.md §10.2/§11.2/§12.2`、`MCAsmStreamer.cpp:81-134`（`Index = offset*8 + TargetOffset + J`）与 `DiagnosticDriverKinds.td:17`（错误级别）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `-gdwarf32` 在 `renderDwarfFormat` 之后才报错，若诊断非 Error 会带 32 位跑下去 | ✅已确认 | —（`err_drv_unsupported_opt_for_target` = **Error**） | `grep DiagnosticDriverKinds.td:17` 为 `Error<`；预重建 `-gdwarf32` rc=1（旧行为是汇编器报错，非本诊断） |
| F2 cc1as 注入应只在真正要调试信息时（`-g0` 不注入），但 `-gdwarf32` 无论 `-g` 都拒绝（与 C 路径一致） | ✅已确认 | `else if (WantDebug)` + 独立 `-gdwarf32` 分支 | `-g0`/`-g` 分支人工复核；`lit-dwarf64-suite` 静态锁 |
| F3 只删扩展是否留下未用变量/告警 (`CmpVT`/`IntVT`) | ✅已确认 | —（两变量仍在阈值判断中使用） | 4 TU `-fsyntax-only`（`-Wall -Wextra`）rc=0、日志 0 B |
| F4 `llvm-mc` 默认仅对 `-g` 生效，且显式 `-dwarf64` 仍走原路径 | ✅已确认 | `Dwarf64 = MCOptions.Dwarf64 \|\| (dadao && GenDwarfForAssembly)` | `--inject` 把 `dadao→x86_64` 后断言红 |
| F5 ABS48 期望标记按 `TargetOffset=16` 推导（字节 2-3），而非抄实现 | ✅已确认 | lit 6 条期望由 `Index` 公式 + 修复前编码字节推导 | `run.sh --runtime` 预重建该 6 条全红（旧标记在字节 0-1） |
| F6 证据脚本可能「恒真」：空命令文件、注释命中计数 | ✅已修 | `mk_syntax_cmds.py` 校验 4 条命令；空文件显式 FAIL；lit 计数只看 `CHECK` 行 | `--inject` 的坏 TU → rc=1 bytes=320；`lit-narrow-int` 首轮实红后改判据 |
| F7 任务书未列的同步面（changelog / coverage 矩阵 / milestones） | ✅已处置 | 重新生成矩阵、补 changelog 条目、状态行同步 | L1 首轮因行号红 → 重生成 → 全绿 |

**判决**：finding 全部处置完毕（无延后/不修），状态置 `待验收`。
#### 第 1 轮 reviewer 验收

**方式**：独立重跑 + 手工抽查 + 独立反例注入（`cp`+md5，临时树/备份还原，全程未用 `git checkout`）；判决只依据本人终端输出与退出码。日志：`.work/log/llvm/LLVM-134t-reviewer-{L1,L2}.log`，反例现场 `/tmp/opencode/LLVM-134t-review/`。

**重跑记录**（均 rc=0，逐项本人执行）：
- `run.sh --runtime` → **36 passed / 0 failed**（静态 23 + 运行期 13；含 cc1as/llvm-mc CU `format=DWARF64 addr_size=0x08`、`-gdwarf32` rc=1、6 条 ABS48 低 16 位标记、obj md5 `98f1a6a5…`=基线、4 目标 lit PASS）。
- `run.sh --inject` → **39 passed / 0 failed**（7 类注入逐条转红 + cp/md5 还原全等 + 坏 TU rc=1 bytes=320 + 还原后静态回绿）。
- `make check`（L1）→ `repository checks (L1): PASS`，**L1_EXIT=0**（含 `check-width-sizes: PASS`）。
- `make check-modules`（L2）→ **Passed: 153 (100.00%)**，`module checks (L2): PASS`，**L2_EXIT=0**（4 目标 lit 全 PASS）。

**手工抽查**：① `llc -O2` i32/i16/i8 `ult`+`br.n`/`cs.n`（`cmp.ut/uw/ub` 真实生成）→ **ext.so=0**（基线 6）；② `set.zw/or.w/andn.w --show-encoding` 标记 `[0x4c,0x20,A,A]` 等，A 落字节 2-3（低 16 位）；③ `clang -c x.s -g` 与 `llvm-mc -g` CU DWARF64/0x08，`-gdwarf32` rc=1 带 driver 诊断；④ x86_64 对照 `-gdwarf32/-gdwarf64/-###` 行为不变（共享文件零影响）；⑤ obj md5 == 基线（ABS48 改动仅显示层，`applyFixup` 不读 `getFixupKindInfo`，已核函数体）。

**独立反例**（不可由 engineer 自检替代）：
- A（运行期断言可红）：`narrow-u.ll` 追加 `sext i32→i64`（md5 `ebfed331→515a2c4b`）⇒ llc 出 1 条 ext.so ⇒ `run.sh --runtime` **FAIL `llc: ext.so count`，rc=1，35 passed/1 failed**；cp 还原 md5==`ebfed331` ⇒ 重跑 **36/0 rc=0**。
- B（lit 断言可红）：`show-encoding-fixup-bigendian.s` 期望改回旧标记（md5 `74e2dfaf→d5153818`）⇒ `llvm-lit` **Failed 1/1 rc=1**；cp 还原 md5 全等 ⇒ **PASS rc=0**。

**约束核验**：两处 `SIGN_EXTEND_INREG` 确删（源码+补丁 grep=0，余 1 处为说明注释；contract-isa.md §10.2 SPEC-069t 确认 `.u*` 的 -1 已 64 位全 1，删除为恒等变换，cmp.u*→br.n/cs.n 无中间变换）；ABS48 `{"DADAO_FK_ABS48",16,16,0}`；本任务 diff 未触 `applyFixup`；`Clang.cpp`/`llvm-mc.cpp` 改动均包在 `Triple::dadao` 门控（诊断级别 `Error<`，x86_64 对照实证）；未改 QEMU/spec/契约；lit 断言用 `rd{{[0-9]+}}` 非常量，CHECK-NOT/标记双向（want 有+old 无）可达 FAIL（A/B 反例实证）；完成区「修改文件」与 `git diff HEAD~1 HEAD --name-only`（15 文件）逐一对上；工作区快照前后 0 行 + 交付物 md5 全等，无越界、用户改动未触。

**注**：完成区「24 passed」= `--with-l1` 口径（静态 23+L1 1），本人跑 `--runtime` 为 36=静态 23+运行期 13，口径一致无数值矛盾；pre-rebuild 12 failed 为历史记录，采信（本人以 A/B 反例独立证明可达 FAIL）。

**判决：Accepted**（验收命令块本人重跑全绿、约束无违反；`ext.so` 归零未暴露其它路径依赖——L2 153/153 全绿即证）。
