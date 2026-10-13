# LLVM-054t: 越界立即数诊断（禁静默环绕）

**模块**：llvm
**项目里程碑**：M4
**依赖**：`LLVM-051t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/knowledge/contract-asm.md` §2.4（立即数范围；地址立即数 `%4==0` 校验）、§9（诊断：未知助记符/越界寄存器/立即数越界等须报错）、§11（**缺陷**：越界立即数**静默环绕**；实例 `add.si rd8, 131072` → 编码为 −131072；`cmp.ui …, 4096` → 0）；`.tao/adr/adr-0013-assembly-syntax.md` D3（装配器 `%4` + 范围校验，非 4 倍数或越界 ⇒ 报错）。
  - `.tao/knowledge/contract-asm-list.md` 的「立即数范围速查」（各立即数字段位宽/取值范围）；`contracts/opcodes.yaml`（字段位宽）。
  - 现有 AsmParser（`AsmParser/DADAOAsmParser.cpp`）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  - AsmParser 对**每个**立即数字段做**范围校验**：越界 MUST **报错**（`Error`，非零退出），**MUST NOT** 静默按位截断/环绕；地址类立即数同时校验 `%4==0`。
  - 诊断文本 SHOULD 含位置（文件:行:列）与「期望范围」提示（`contract-asm §9`）。
  - 覆盖所有受影响指令族（`add.si`/`cmp.ui` 等 riii；分支/call/jump 的 `imms14/20/26`；访存 `imms12`；`ret imms18`；`orri immu6`；`rwii immu16` 等，按 `contract-asm-list.md` 速查逐一核对）。
- **约束**：
  - **不静默环绕**：越界一律报错；**合法边界值**（如 `imms18` 的 −131072/131071、`imms14` 的 −8192/8188、`add.si` 的合法 18 位范围）必须**接受**（不得误杀）。
  - `%4==0` 仅对**地址类**（跳转/分支目标与 escape/访存？按 `contract-asm §2.4`/§3.2：跳转/分支目标偏移与 escape 偏移单位为字节且须 `%4==0`）适用；勿误加到非地址立即数（`ret imms18` 值非地址、`orri immu6` 非地址）。
  - **reloc/fixup 坑预防（5 条，同 `LLVM-050t`）**：符号/可重定位操作数不得被范围校验误判（不可在汇编期求值者交链接期）。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建/串行/临时目录/留证纪律同 `LLVM-050t`；`ninja -j8`；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-054t/`；**不提交 git**。

## 验收标准

1. 构建 EXIT=0。
2. **越界报错（反例）**：`add.si rd8, 131072`、`cmp.ui rd8, rd9, 4096` 等（`contract-asm §11` 实例）→ `llvm-mc` 报告越界错误、非零退出；逐例给出真实 stderr 输出。
3. **边界接受**：各字段的**最小/最大合法值**（含负边界）→ `llvm-mc` EXIT=0 且编码正确（逐条 oracle 核对）。
4. **对齐**：地址类非 4 倍数（如 `jump [rb0, 6]`）→ 报错；`ret` 非地址 立即数**不**受 `%4` 约束。
5. **无静默环绕**：任选 ≥3 个字段注入越界值，均报错（不再出现「编码成 −x / 0」的静默环绕）。
6. **lit 向量**：`tests/llvm/lit/MC/DADAO/` 新增反例用例（`%not` + `expected-error` 或等价）；`make check-lit` EXIT=0 不回归；`make check` EXIT=0；`make test-codegen` 不回归。
7. 一键证据脚本 `.work/evidence/LLVM-054t/run.sh`（含 `--inject`：把某字段范围校验改宽/删掉 → 该用例由报错变接受 → 期望 FAIL → 还原+重建 → 回绿）；完成区贴真实输出。

## 完成区

**测试结果**：通过 **21/21** 项检查（一键证据 `.work/evidence/LLVM-054t/run.sh` 正常模式 `RESULT: PASS (normal, 0 failures)` EXIT=0：14 项 reject/accept 断言 + 独立 oracle 边界 23/23 + lit + 5 项仓库门控）；反例注入 `--inject` `RESULT: PASS (inject, 0 failures)` EXIT=0（禁范围校验 → `add.si rd8, 131072` 由「报错」变「接受并静默环绕为 -131072」（检测到）→ 还原+重建 → 回绿）。`make check` EXIT=0（lit 50/50）；`make check-lit` 50/50；`make test-codegen` 15/15；`check-patch-tree` 2 components/85 patches OK；`check-source-state` llvm-project `HEAD=6078d79fd1cd count=1 clean=True`。失败原因：无。

**修改文件**：
- 组件源码（`.work/source/llvm-project`，已 amend 收敛为 base+1，`HEAD=6078d79fd`）：
  - `llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（**唯一改动**，+125/−3 行）：新增 `checkImmediateRanges()` 及 `ImmFieldKind`/`ImmFieldRange` 辅助；`Match_Success` 分支在发射前调用；3 处地址范围报错文本补上期望范围。
- 补丁集：`components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（`make_patch.py` 重导出，1 written/52 unchanged；`series` 仍 **53**）。
- 台账：`components/llvm-project/changelog.md`（+LLVM-054t 一条）。
- 测试向量：`tests/llvm/lit/MC/DADAO/imm-range.s`（新增）。
- 证据脚本：`.work/evidence/LLVM-054t/run.sh`、`.work/evidence/LLVM-054t/boundary_oracle.py`（新增）；日志 `.work/log/llvm/LLVM-054t-*.log`。

**验收结果**（真实输出，`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`）：

1. **构建 EXIT=0**（`.work/log/llvm/LLVM-054t-build.log` / `-build2.log`）：
   `ninja -j8 -C .work/build/llvm llvm-mc llvm-objdump llvm-readobj llc` → `EXIT=0`。
2. **越界报错（反例，`contract-asm §11` 实例）** —— 真实 stderr：
   ```
   add.si rd8, 131072          → error: immediate out of range for 'add.si': 131072 is outside the imms18 (signed 18-bit) range [-131072, 131071]   (EXIT=1)
   cmp.ui rd8, rd9, 4096       → error: immediate out of range for 'cmp.ui': 4096 is outside the immu12 (unsigned 12-bit) range [0, 4095]          (EXIT=1)
   ```
   （另逐条验证 `add.si -131073`、`cmp.si 2048/-2049`、`cmp.ui -1`、`ld.ub [rb2,2048/-2049]`、`ret 131072`、`shl.uo 64/-1`、`set.zw 65536/-1`、`fence/swym 262144/-1` 均 EXIT=1。）
3. **边界接受 + 独立 oracle 编码核对**：`boundary-oracle: 23/23 passed`（复用仓库独立 oracle `tools/llvm/test_encoding_oracle.py` 的 `encode_*`，非从 llvm-mc 反推）：
   ```
   add.si rd8, 131071 = 5921ffff   add.si rd8, -131072 = 59220000
   cmp.ui rd8, rd9, 4095 = 5c209fff  cmp.ui … 0 = 5c209000
   cmp.si rd8, rd9, -2048 = 5d209800 cmp.si … 2047 = 5d2097ff
   ld.ub rd8, [rb2, -2048] = 10202800 ld.ub … 2047 = 102027ff
   ret rd8, -131072 = 76220000     ret rd8, 131071 = 7621ffff
   shl.uo rd8, rd0, 63 = 4070803f  ext.uo rd8, rd0, 0 = 40608000
   set.zw rd8, wp0, 65535 = 4c20ffff  swym 0 = 77880000  swym 262143 = 778bffff
   br.n {rd8}?, [rb0, 524284] = 6821ffff  … -524288 = 68220000
   br.eq {rd8, rd0}?, [rb0, 8188] = 6e2007ff  … -8192 = 6e200800
   jump [rb0, 33554428] = 707fffff  jump [rb0, -33554432] = 70800000  jump [rb3, rd0, 8188] = 710c07ff
   ret rd8, 6 = 76200006
   ```
4. **对齐**：`jump [rb0, 6]` → `error: jump/call offset must be a multiple of 4 bytes`（EXIT=1）；`br.eq {rd8, rd0}?, [rb0, 6]` → `error: branch/jump offset must be a multiple of 4 bytes`（EXIT=1）；`ret rd8, 6` → **EXIT=0**（非地址，不受 `%4`）。
5. **无静默环绕**：≥3 字段（`imms18`/`immu12`/`imms12`/`immu6`/`immu16`/`immu18`）注入越界值均报错；`--inject` 展示禁用校验后 `add.si rd8, 131072` 被接受并静默环绕为 `add.si rd8, -131072`（即修复前缺陷），还原后回绿。
6. **lit**：`imm-range.s` → `Passed: 1 (100.00%)`；`make check-lit` → `Passed: 50 (100.00%)` EXIT=0；`make check` → `repository checks: PASS` EXIT=0；`make test-codegen` → `Results: 15/15 passed, 0 failed`。
7. **一键证据**：`.work/evidence/LLVM-054t/run.sh` → `RESULT: PASS (normal, 0 failures)` EXIT=0；`run.sh --inject` → `inject-nonempty`(diff 非空) / `inject-breaks-reject`(接受环绕) / `restore-clean`/`restore-build`/`restore-green` 全 PASS，`RESULT: PASS (inject, 0 failures)` EXIT=0。

**新发现/坑**：
- **设计选择（为何在 AsmParser 而非 matcher 谓词）**：所有立即数共用单一 `DADAOImmAsmOperand`（`PredicateMethod=isImm`，无范围）；改成 per-field 谓词须改 auto-generated `DADAOInstrInfo.td`（由 `tools/llvm/generate_instrinfo.py` 生成），会引入生成器/漂移面。改为在 `matchAndEmitInstruction` 匹配成功后按指令 `TSFlags[3:0]`（`DADAO::FormatKind`）判定唯一立即数字段，最小面，且可给出「字段名 + 范围」诊断。
- **字段→FormatKind 判定**：`rrri`/`orri`→`immu6`；`rrii`（`cmp.ui`→`immu12`，`ld.*`/`st.*`/`cmp.si`→`imms12`，`jump`/`call`/`br.*`→地址跳过）；`riii`（`br.*`→地址跳过，否则 `imms18`）；`iiii`→地址跳过；`rwii`→`immu16`；`oiii`→`immu18`。地址类由既有路径先校验 `%4==0`+字节范围（`imms14/20/26`），故此处跳过，避免对已 `>>2` 的编码值二次误判。
- **`contract-asm §11` 缺陷行需更新**：越界立即数静默环绕现已修复，建议 `/complete` 把该行改为「已修复（LLVM-054t）」并核对 `issues.yaml` 对应条目（`§12.4` 缺口登记）。
- **地址类报错位置指向 `[`**（`parseAddressExpr`/`parseBranchAddress` 用 `StartLoc`），非数字本身——既有行为，本任务未改（诊断仍含位置）。

**遗留问题**：
- **（既有、非本任务引入）** `ld.st rd2, [rb1, x_offset]`（访存符号偏移）经 emitter 落 `R_DADAO_REL20`（`getFixupKindForInstr` 默认分支走 `PCRel_18`），语义上 PC 相对于数据偏移可疑。本任务只保证符号/可重定位操作数**不被范围校验误判**（已按 `ImmExpr` 跳过，reloc/fixup 坑①），未触碰 emitter；建议另立任务。
- `escape`/`trap`/`cfxld`/`cfxst` 等 `ciii`/`crii`（`scope: excluded`/`deferred`，本就不在 `.td` 中）不适用本任务立即数族，未覆盖（非缺陷）。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：自主逐行审查改动源码（`DADAOAsmParser.cpp` 的 `checkImmediateRanges`/`getImmediateFieldKind`/`getImmediateFieldRange` + `Match_Success` 调用点 + 3 处地址消息）、证据脚本（`run.sh`/`boundary_oracle.py`）及新增 lit。判决：**通过**（无未修 finding；见下表）。

**逐行审查要点**：
- **字段判定完备性**：遍历 `.td` 全部带立即数的 def 核验——`rrri`(count)/`orri`(immu6)/`rrii`(ld/st/cmp.si/cmp.ui)/`riii`(add.si/ret)/`rwii`(immu16)/`oiii`(immu18) 全覆盖；`iiii` 与 address 类跳过（已在前置路径校验）。`immu24` 仅 `iiii`（address）故无需单列。
- **`Flat.back()` 假设**：所有 DADAO 格式立即数均在 asm 操作数末位（含块移动 append 的 count）。块 count 由 `{start:end}` 推出且 ≤63（`mreg_range_overflow` 先行拦截），亦落在 `immu6`。
- **符号操作数**：`ImmExpr != nullptr` 直接跳过（reloc/fixup 坑①）；实测 `ld.st rd2, [rb1, x_offset]` EXIT=0 且发 reloc。
- **伪指令**：`set.rd/set.rb/set.ft/set.fo` 在 `matchAndEmitInstruction` 顶部即展开返回，其 imm64 不经本校验（正确；展开出的 `set.zw`/`or.w` 等经递归匹配再校验，且切片已 `&0xFFFF`）。
- **地址类**：`%4==0` 仍仅地址路径；`ret`/`add.si` 非地址不受约束（实测 `ret rd8, 6` EXIT=0）。3 处地址报错补期望范围，未改判定逻辑（阈值 `-8388608..8388607`/`-131072..131071`/`-2048..2047` 分别对应 imms26/20/14）。
- **伪指令/`-multiple-to-single` 回归**：递归发射的立即数（wyde 切片、元素宽度 W=1..8、负 restore）均在范围内；`make test-codegen` 15/15、`make check-lit` 50/50 无回归。
- **证据脚本**：`check()` 非恒真（按 rc 分支 FAIL 并计数）；reject/accept/边界/oracle/门控各项均有可达 FAIL 路径；`--inject` 校验 `git diff` 非空（防空注入）、`trap` 还原、还原后 `status --porcelain` 断言干净、重建回绿；结尾无 `tee`，各 `rc` 均在命令后立即捕获（已修 `$?` 被命令替换吞掉的写法）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 证据脚本 `make ...; check ... "$(grep ...)" $?` 中 `$?` 取到 grep 而非 make 的退出码（会把失败记成通过） | ✅已修 | 改为 `make ...; rc=$?; check ... "$rc"`（5 处） | 重跑正常模式：`make-check`/`check-patch-tree` 等 `rc=0` 且 actual 为真实结论行 |
| F2 lit `imm-range.s` 注释文本含 `` `OK:` `` 被 FileCheck 当指令 → 校验失败 | ✅已修 | 注释改为不含冒号的「OK directives」 | `llvm-lit imm-range.s` → `Passed: 1 (100.00%)` |
| F3 新增辅助多包了一层冗余匿名命名空间 | ✅已修 | 去掉内层 `namespace {`/`}` | 构建 EXIT=0；行为不变 |
| F4 地址范围报错原缺期望范围（`contract-asm §9` SHOULD） | ✅已修 | 3 处消息补 `expected [..] (imms14/20/26, %4==0)` | `br.n …524288` → `error: branch byte offset out of range: expected [-524288, 524284] (imms20, %4==0)` |
| F5 `ld.st …, [rb1, sym]` 的 reloc 类型为 `REL20`（PC 相对） | ❌不修 | 无改动 | 证据：`getFixupKindForInstr` 默认分支走 `PCRel_18`（`DADAOMCCodeEmitter.cpp`），**本任务未触碰 emitter**，属既有能力缺口；本任务仅保证符号操作数不被范围校验误判（已跳过、EXIT=0）。登记于「遗留问题」，建议另立任务 |

**自验命令退出码**：`run.sh`（normal/inject）EXIT=0；`make check` EXIT=0；`make check-lit` EXIT=0；`make test-codegen` EXIT=0；`check-patch-tree` EXIT=0；`check-source-state` EXIT=0；`check-no-residue` EXIT=0。

#### 第 1 轮 reviewer 验收

**审查范围**：独立重跑 `run.sh`（normal + inject）、独立注入反例（`rwii/immu16`）、手动验证边界编码≥3条、符号/对齐/门控、证据脚本审计。

##### 一、证据脚本审计

逐行审查 `.work/evidence/LLVM-054t/run.sh`：

| 检查项 | 结论 |
|---|---|
| `check()` 函数 | 非恒真——按 `$4`（rc）分支 PASS/FAIL，FAIL 计数。✓ |
| `expect_reject` | 调用 `asm_line` 后检查返回值：成功（rc=0）→ FAIL（不该接受），失败（rc≠0）→ PASS。✓ |
| `expect_accept` | 调用 `asm_line` 后检查返回值：成功（rc=0）→ PASS，失败（rc≠0）→ FAIL。✓ |
| `--inject` 模式 | ①`sed` 改 `SImm18→None`（riii 格式）；② `git diff --name-only` 验非空（防空注入）；③ 重建；④ 验 `add.si rd8, 131072` 由拒绝变接受（含 objdump 确认环绕）；⑤ `restore_source` + 重建；⑥ `status --porcelain` 验 clean；⑦ 验恢复后仍拒绝。✓ |
| `trap 'restore_source' EXIT` | inject 模式下异常退出也能还原源码。✓ |
| 结尾 | `FAILS==0` → `exit 0`，否则 `exit 1`；无 `tee` 吞退出码。✓ |
| `$?` 捕获 | 5 处 `make ...; rc=$?` 模式（已修 F1），不再用 `make ...; check ... "$?"`。✓ |
| 恒真/两支同结果 | 无——reject 路径 rc=0→FAIL、rc≠0→PASS；accept 路径反转。✓ |

结论：**脚本合格**。

##### 二、重跑记录

**Normal 模式**（`run.sh`）：

```
$ bash .work/evidence/LLVM-054t/run.sh > normal.log 2>&1; echo "EXIT=$?"
EXIT=0
```

输出摘要（`/tmp/opencode/LLVM-054t-review/normal.log`）：
```
[PASS] mc-exists | rc=0
[PASS] reject-add.si-131072 | error: immediate out of range for 'add.si': 131072 is outside the imms18 (signed 18-bit) range [-131072, 131071] | rc=0
[PASS] reject-cmp.ui-4096 | error: immediate out of range for 'cmp.ui': 4096 is outside the immu12 (unsigned 12-bit) range [0, 4095] | rc=0
[PASS] reject-add.si-minus | -131073 | rc=0
[PASS] reject-cmp.si-2048 | rc=0
[PASS] reject-cmp.ui-minus | -1 | rc=0
[PASS] reject-ld.ub-2048 | rc=0
[PASS] reject-ret-131072 | rc=0
[PASS] reject-immu6-64 | rc=0
[PASS] reject-immu16-65536 | rc=0
[PASS] reject-immu18-262144 | rc=0
[PASS] reject-jump-align | jump/call offset must be a multiple of 4 bytes | rc=0
[PASS] reject-br.align | branch/jump offset must be a multiple of 4 bytes | rc=0
[PASS] accept-ret-nonaddr | rc=0
[PASS] boundary-oracle | 23/23 passed | rc=0
  (23/23 boundary encodings all PASS — 逐条见下方独立核验)
[PASS] lit-imm-range | Passed: 1 (100.00%) | rc=0
[PASS] make-check-lit | Passed: 50 (100.00%) | rc=0
[PASS] make-check | repository checks: PASS | rc=0
[PASS] make-test-codegen | Results: 15/15 passed, 0 failed | rc=0
[PASS] check-patch-tree | 2 component(s), 85 patches OK | rc=0
[PASS] check-source-state | llvm-project: OK HEAD=6078d79fd1cd count=1 clean=True | rc=0
RESULT: PASS (normal, 0 failures)
```

**Inject 模式**（`run.sh --inject`）：

```
$ bash .work/evidence/LLVM-054t/run.sh --inject > inject.log 2>&1; echo "EXIT=$?"
EXIT=0
```

输出：
```
[PASS] inject-nonempty | llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp | rc=0
[PASS] inject-build | rc=0
[PASS] inject-breaks-reject | 0: 59 22 00 00 add.si rd8, -131072 | rc=0
[PASS] restore-clean | dirty=0 | rc=0
[PASS] restore-build | rc=0
[PASS] restore-green | error: immediate out of range for 'add.si': 131072 ... | rc=0
RESULT: PASS (inject, 0 failures)
```

##### 三、独立注入反例（与 engineer 不同）

**注入目标**：`rwii` 格式的 `immu16` 范围校验（`set.zw`）——engineer 注入的是 `riii/SImm18`（`add.si`）。

**注入命令**：
```bash
sed -i 's|return ImmFieldKind::UImm16;|return ImmFieldKind::None; // INJECTED rwii disabled|' \
  .work/source/llvm-project/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
```

**diff 验证**：`git diff --name-only` → `llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（非空 ✓）

**重建**：`ninja -j8 -C .work/build/llvm llvm-mc` → EXIT=0

**注入效果**：
```bash
$ printf 'set.zw rd8, wp0, 65536\n' | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o t.o -
EXIT=0  # 正常应 EXIT=1（越界）
$ llvm-objdump -d t.o
  0: 4c 20 00 00  set.zw rd8, wp0, 0x0   # 65536 & 0xFFFF = 0，静默环绕
```
**注入确认**：越界值 `65536` 被接受并静默环绕为 `0`——范围校验已被禁用。

**还原**：
```bash
$ git -C .work/source/llvm-project checkout -- llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
$ git -C .work/source/llvm-project status --porcelain
(empty — clean ✓)
$ ninja -j8 -C .work/build/llvm llvm-mc   # EXIT=0
```

**还原后验证**：
```bash
$ printf 'set.zw rd8, wp0, 65536\n' | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o t.o -
EXIT=1
stderr: error: immediate out of range for 'set.zw': 65536 is outside the immu16 (unsigned 16-bit) range [0, 65535]
```
**回绿确认** ✓

##### 四、独立复核（手动验证）

**4.1 越界报错**（手动，非脚本）：
| 指令 | 期望 | 真实 stderr | EXIT |
|---|---|---|---|
| `add.si rd8, 131072` | 报错 imms18 | `error: immediate out of range for 'add.si': 131072 is outside the imms18 (signed 18-bit) range [-131072, 131071]` | 1 |
| `cmp.ui rd8, rd9, 4096` | 报错 immu12 | `error: immediate out of range for 'cmp.ui': 4096 is outside the immu12 (unsigned 12-bit) range [0, 4095]` | 1 |

**4.2 边界接受 + 独立编码核验**（≥3 条，手动 `llvm-objdump` 比对 oracle）：

| 指令 | 期望编码 (oracle) | 真实编码 (objdump) | 匹配 |
|---|---|---|---|
| `add.si rd8, 131071` | 5921ffff | `59 21 ff ff` | ✓ |
| `cmp.ui rd8, rd9, 4095` | 5c209fff | `5c 20 9f ff` | ✓ |
| `cmp.si rd8, rd9, -2048` | 5d209800 | `5d 20 98 00` | ✓ |

**4.3 对齐**（手动）：
| 指令 | 期望 | 真实 | EXIT |
|---|---|---|---|
| `jump [rb0, 6]` | 报错 %4 | `error: jump/call offset must be a multiple of 4 bytes` | 1 |
| `ret rd8, 6` | 接受（非地址） | （无错误） | 0 |

**4.4 无静默环绕**：≥6 字段（`imms18`/`immu12`/`imms12`/`immu6`/`immu16`/`immu18`）越界均报错（normal 模式 14 项 reject 全 PASS）。

**4.5 符号不被误判**（手动）：
```bash
$ echo 'add.si rd8, external_sym' | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null
EXIT=0  # 符号操作数不被范围校验误杀 ✓
```

**4.6 门控**（独立重跑）：
| 门控 | 期望 | 真实 | EXIT |
|---|---|---|---|
| `make check-lit` | 50/50 | `Passed: 50 (100.00%)` | 0 |
| `make check` | PASS | `repository checks: PASS` | 0 |
| `make test-codegen` | 15/15 | `Results: 15/15 passed, 0 failed` | 0 |
| `check-patch-tree` | OK | `2 component(s), 85 patches OK` | 0 |
| `check-source-state` | clean | `llvm-project: OK HEAD=6078d79fd1cd count=1 clean=True` | 0 |

##### 五、约束核验

| 约束 | 结论 |
|---|---|
| 不静默环绕 | ✓ 越界一律报错（14 项 reject 全 PASS） |
| 合法边界值不误杀 | ✓ 23 项 boundary oracle 全 PASS + 手动 3 条编码核验 |
| `%4==0` 仅地址类 | ✓ `jump [rb0, 6]` 报错、`ret rd8, 6` 接受 |
| 符号/可重定位不被误判 | ✓ `add.si rd8, external_sym` EXIT=0 |
| 不改 lib/MC | ✓ 仅改 `AsmParser/DADAOAsmParser.cpp` |
| 补丁纪律 | ✓ `check-patch-tree` 2 components/85 patches OK |
| 临时目录 | ✓ `/tmp/opencode/LLVM-054t/` |
| 不提交 git | ✓ `check-source-state` clean=True |
| 一键证据脚本 | ✓ `run.sh` normal/inject 均 EXIT=0 |
| 反例注入可失败 | ✓ engineer 注入(SImm18) + reviewer 注入(UImm16) 均检测到环绕 |

##### 六、披露判定

- **`changelog.md`**：惯例加条，内容与改动一致。✓
- **F5 遗留（`ld.st …, [rb1, sym]` reloc REL20）**：`getFixupKindForInstr` 默认分支返回 `PCRel_18` 存在于 `DADAOMCCodeEmitter.cpp`，该文件**未被本任务修改**（属于整个 DADAO 后端初始引入的能力缺口）。本任务仅保证符号操作数不被范围校验误判（已按 `ImmExpr` 跳过），未触碰 emitter。**判定：既有问题，非本任务引入，登记为遗留合理，建议另立任务。** ✓

##### 七、源码审查要点

- `getImmediateFieldKind`：`rrri`(1)/`orri`(7)→UImm6；`rrii`(2) 按助记符分 UImm12/SImm12/None；`riii`(3) 按助记符分 None/SImm18；`iiii`(4)→None；`rwii`(5)→UImm16；`oiii`(8)→UImm18。与 `contract-asm-list.md` 速查一致。✓
- 范围常量：SImm12[-2048,2047]、UImm12[0,4095]、SImm18[-131072,131071]、UImm18[0,262143]、UImm16[0,65535]、UImm6[0,63]——均正确。✓
- `checkImmediateRanges` 在 `Match_Success` 分支、`emitInstruction` 之前调用——拦截时机正确。✓
- 符号操作数：`Op->getImmExpr()` 非空则跳过——reloc/fixup 坑①。✓
- 3 处地址报错文本补期望范围（imms14/20/26）——`contract-asm §9` SHOULD。✓

##### 判决

**Accepted**

所有验收命令在独立重跑下通过；独立注入反例（`rwii/UImm16`，与 engineer 的 `riii/SImm18` 不同）确认脚本能检测注入→FAIL→还原→回绿；边界编码独立核验≥3条与 oracle 一致；符号/对齐/门控全通过；F5 遗留判定为既有问题非本任务引入。
