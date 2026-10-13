# LLVM-050t: ELF writer → RELA + `e_flags=1` + `e_machine`→dadao + `getRelocType`（4 类）

**模块**：llvm
**项目里程碑**：M4
**依赖**：`SPEC-105t`、`SPEC-109t`、`INFRA-045t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-105t` 落地后的 `.tao/knowledge/contract-elf.md §1–§4`（`e_flags[7:0]=1` namespace、`SHT_RELA`、`R_DADAO_ABS48=0`/`REL26=1`/`REL20=2`/`REL14=3`/`NUM=4`、公式无 −4、`ABS48` 3 片）与 `.tao/adr/adr-0019-dadao-relocation-types.md`（Accepted）。
  - 现有 DADAO MC 层（实测）：`MCTargetDesc/DADAOELFObjectWriter.cpp`（`HasRelocationAddend_=false`、`getRelocType` 返回 0 桩、`needsRelocateWithSymbol` 返回 false）；`MCTargetDesc/DADAOFixupKinds.h`（仅 `DADAO_FK_PCRel_12/18/24`）；`MCTargetDesc/DADAOAsmBackend.cpp`（3 类 fixup + 同段 `evaluateFixup` 就地折叠 + `applyFixup` 掩码）；`MCTargetDesc/DADAOMCCodeEmitter.cpp`（`getMachineOpValue` 对符号表达式按 `getFixupKindForInstr` 发 PCRel fixup）；`MCTargetDesc/DADAOMCTargetDesc.cpp`（`DADAOTargetStreamer` 已设 `e_flags = 0x1`）；writer 已设 `EM_DADAO = 0x0DA0`。
  - `llvm/lib/MC/ELFObjectWriter.cpp`（`.o` 写出的通用路径；**不改共享层**，见约束）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  1. `DADAOELFObjectWriter`：`HasRelocationAddend_` 由 `false` 改 **`true`**（`SHT_RELA`）；实现 `getRelocType`（4 类映射：`DADAO_FK_ABS48→R_DADAO_ABS48`、`DADAO_FK_PCRel_24→R_DADAO_REL26`、`DADAO_FK_PCRel_18→R_DADAO_REL20`、`DADAO_FK_PCRel_12→R_DADAO_REL14`）；`needsRelocateWithSymbol` 对 `ABS48` 返回 `true`。
  2. `DADAOFixupKinds.h`：新增 `ABS48` fixup kind（按 `ADR-0019 D5` 逐指令挂载，linker 依指令内 `wyde-position` 判定片）；`AsmBackend::getFixupKindInfo` 补其信息。
  3. `llvm/include/llvm/BinaryFormat/ELF.h`（或 target 本地头）：新增 `R_DADAO_*` 枚举（值 0–4）与 `EM_DADAO`（若尚未有）。**不改**上游其它 machine 定义。
  4. `DADAOMCCodeEmitter`：对 `set.zw`/`or.w`/`andn.w`（rwii，地址构造）的符号表达式发出 `ABS48` fixup（`r_addend` 表达 `A`）；`REL*` 走既有 PCRel 路径。
  5. 导出的 `components/llvm-project/patches/**` 与 `series`；`check-patch-tree` 通过。
- **约束**：
  - **不改共享 MC 层**（`lib/MC/**`）：复用 target 级 hook（`MCAsmBackend::evaluateFixup`/`getFixupKindInfo`/`MCObjectWriter`）与 `getRelocType`，避免影响其它 ELF backend（`LLVM-041t` 先例）。
  - **RELA 语义**：`r_addend` 显式携带 `A`；`ABS48` 的 `value = S + A`；`REL*` 的 `field = (S + A − P) >> 2`（**无 −4**）。
  - **reloc/fixup 坑预防（M4 硬约束，源自 `DADAO-0628` 实录）**：① fixup **必须尊重 `IsResolved`**（禁写预链接原始值）；② same-section「快速路径」不可靠则**删掉、退回真重定位**（跨 section/未定义符号必须发 reloc，参考 `ML-003e`：`isUndefined()` 不是「是否需重定位」的正确判据，正确判据是「目标符号是否与 fixup 同 section」）；③ **`rb0`（= 当前 PC）禁作基址/零**；④ 跳转表/间接跳转目标标签**必须显式发射**；⑤ 大常量**不得折入**受限立即数/relocation 字段（先材料化，参考 `ML-030a`）。
  - **本任务不做**：全局数据 lower（`LLVM-055t`）、伪指令（`051t`）、LLD（`056t`）。
  - **补丁纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/llvm-project` 工作树进行，**不得**手改 `components/**/patches/**`；`commit --amend` 收敛 base+1 → `tools/infra/make_patch.py` 导出裸 `git diff`；`make check-patch-tree`（断言⑥⑨）通过。
  - 构建用 `ninja -j8 -C .work/build/llvm llc llvm-mc llvm-objcopy llvm-readobj`；受 `JOBS` 限制、**禁 `-j$(nproc)`**；失败即停、不自动重试。
  - 临时目录 `/tmp/opencode/LLVM-050t/`；**不提交 git**；复杂命令输出留存 `.work/log/llvm/LLVM-050t-*.log`。

## 验收标准

1. 构建 EXIT=0；产物（`llvm-mc`/`llc`/`llvm-readobj`）更新。
2. **RELA**：对一个含**跨 section/未定义符号**的 `.s`，`llvm-mc -triple=dadao -filetype=obj` → `llvm-readobj -h`/`--sections` 显示存在 **`SHT_RELA`**（`.rela.*`）节，`llvm-readobj -r` 列出对应 `R_DADAO_REL26/REL20/REL14/ABS48`；无 REL（`SHT_REL`）记录。
3. **编号/映射**：四类 fixup 到编号的映射与 `contract-elf §2` 逐条一致（`ABS48=0`/`REL26=1`/`REL20=2`/`REL14=3`），给出真实 `llvm-readobj -r` 输出。
4. **`e_machine`/`e_flags`**：`llvm-readobj -h` 显示 `Machine: 0xDA0`、`Flags [ (0x1)`（`e_flags[7:0]=1`）——回归确认既有实现未被破坏。
5. **`r_addend`**：`llvm-readobj -r --expand-relocs` 显示 RELA 的 `Addend` 字段非零且等于 `A`（构造一个 `+A` 用例）。
6. **lit 向量**：新增/扩展 `tests/llvm/lit/MC/DADAO/`（或 patch 内 `llvm/test/MC/DADAO/`）用例，断言 RELA 类型/编号/`readobj` 字段；`make check-lit` EXIT=0 且不回归。
7. **不回归**：`make test-codegen`（M3 15/15）EXIT=0；`make check` EXIT=0；`check-patch-tree` OK；`check-source-state` clean。
8. 一键证据脚本 `.work/evidence/LLVM-050t/run.sh`（非交互、失败非零、逐项打印、`--inject`：改 `getRelocType` 映射错 → 期望 FAIL → 还原+**重建** → 回绿；结尾无 `tee`）；完成区贴真实输出与退出码。

## 完成区

**测试结果**：通过 12/12（一键证据 `.work/evidence/LLVM-050t/run.sh` 正常模式 12 项全 PASS，EXIT=0）+ 反例注入 2/2（`--inject`：注入 FAIL → 还原+重建回绿，EXIT=0）。`make check` EXIT=0；`make test-codegen` 15/15；`make check-lit` 36/36；`check-patch-tree` 83 patches OK；`check-source-state` llvm-project clean+count=1。失败原因：无。

**修改文件**：
- 组件源码（`.work/source/llvm-project`，已 amend 收敛为 base+1：
  `6dfe1677a..884f88cb7`）：
  - `llvm/lib/Target/DADAO/MCTargetDesc/DADAOELFObjectWriter.cpp`（`HasRelocationAddend_`→true；`getRelocType` 4 类映射；`needsRelocateWithSymbol` ABS48→true；改引用 `ELF::EM_DADAO`）
  - `llvm/lib/Target/DADAO/MCTargetDesc/DADAOFixupKinds.h`（+`DADAO_FK_ABS48`，`LastTargetFixupKind=ABS48`）
  - `llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCCodeEmitter.cpp`（rwii 地址构造 `set.zw`/`or.w`/`andn.w`（rd/rb 变体）符号表达式发 `ABS48` fixup，PCRel=false）
  - `llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp`（`getFixupKindInfo` 补 ABS48；`applyFixup` 未解析 fixup 经 `maybeAddReloc` 发真重定位，尊重 `IsResolved`）
  - `llvm/include/llvm/BinaryFormat/ELF.h`（+`EM_DADAO=0x0DA0`；include `ELFRelocs/DADAO.def`）
  - `llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def`（**新增**：`R_DADAO_ABS48=0`/`REL26=1`/`REL20=2`/`REL14=3`/`NUM=4`）
  - `llvm/lib/Object/ELF.cpp`（`getELFRelocationTypeName` 增 `EM_DADAO` case，使 `llvm-readobj -r` 显示 `R_DADAO_*` 名称）
- 补丁集：`components/llvm-project/series`（48→51）与 `components/llvm-project/patches/**`（新 `ELFRelocs/DADAO.def.patch`；改 ELF.h / Object/ELF.cpp / writer / emitter / backend / fixupkinds 补丁）
- 台账：`components/llvm-project/changelog.md`（+LLVM-050t 一条）
- 测试向量：`tests/llvm/lit/MC/DADAO/rela.s`、`tests/llvm/lit/MC/DADAO/rela-addend.s`（新增）
- 证据脚本：`.work/evidence/LLVM-050t/run.sh`（新增）；日志 `.work/log/llvm/LLVM-050t-*.log`

**验收结果**（真实输出，日志 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`）：

1. **构建 EXIT=0**（`.work/log/llvm/LLVM-050t-build.log` / `-build2.log`）：
   `ninja -j8 -C .work/build/llvm llc llvm-mc llvm-objcopy llvm-readobj` → `EXIT=0`；产物更新。
2. **RELA**（`llvm-readobj --sections`，跨 section 用例 `rela.s`）：存在 `.rela.text` / `Type: SHT_RELA (0x4)`；**无** `SHT_REL (0x9)`。
3. **编号/映射**（`llvm-readobj -r rela.o`）：
   ```
   0x0  R_DADAO_ABS48 ext  0x0
   0x4  R_DADAO_ABS48 ext  0x0
   0x8  R_DADAO_ABS48 ext  0x0
   0xC  R_DADAO_REL26 ext  0x0
   0x10 R_DADAO_REL20 other 0x0
   0x14 R_DADAO_REL14 other 0x0
   ```
   与 `contract-elf §2.2`（ABS48=0/REL26=1/REL20=2/REL14=3）逐条一致。
4. **`e_machine`/`e_flags`**（`-h`）：`Machine: 0xDA0`；`Flags [ (0x1)`。
5. **`r_addend`**（`-r --expand-relocs rela_addend.o`）：`R_DADAO_ABS48` Addend `0x15`/`0x16`（=21/22）、`R_DADAO_REL26` Addend `0x4`、`R_DADAO_REL20` Addend `0x8`、`R_DADAO_REL14` Addend `0xC`（=12），即 `A`。
6. **lit**：`.work/build/llvm/bin/llvm-lit tests/llvm/lit/MC/DADAO/rela.s tests/llvm/lit/MC/DADAO/rela-addend.s` → `Passed: 2 (100.00%)`；`make check-lit` → `Passed: 36 (100.00%)` EXIT=0（新增 2 例，无回归）。
7. **不回归**：`make test-codegen` → `Results: 15/15 passed, 0 failed`（`.work/log/llvm/LLVM-050t-test-codegen.log`）；`make check` → `repository checks: PASS` EXIT=0（`.work/log/llvm/LLVM-050t-make-check.log`）；`make check-patch-tree` → `83 patches OK`；`make check-source-state` → `llvm-project: OK HEAD=884f88cb7c5b count=1 clean=True`。
8. **一键证据**：`.work/evidence/LLVM-050t/run.sh` → `RESULT: PASS (12 checks, 0 failures)` EXIT=0；`run.sh --inject` → 注入（writer `getRelocType` 的 `ABS48→REL14`）后 `inject-mapping` FAIL，`git checkout` 还原 + `ninja` 重建后 `restore-mapping` 回绿，`RESULT: PASS` EXIT=0。

**新发现/坑**：
- **`llvm-readobj -r` 对自定义 machine 默认打 `Unknown (N)`**：要让 `-r` 列出 `R_DADAO_*` 名称（验收 2/3 要求），必须走 `llvm/BinaryFormat/ELFRelocs/<T>.def` + `Object/ELF.cpp::getELFRelocationTypeName` 注册；仅在 writer/ELF.h 定义枚举名不够。已在 ELF.h 以 `.def` 形式接入（非直接写枚举）。
- **`applyFixup` 是占位量（reloc）落地的关键挂钩**：`MCAssembler::evaluateFixup` 只调 target 的 `applyFixup`，不会自动 `recordRelocation`；未解析 fixup 必须在 `applyFixup` 内显式 `maybeAddReloc`（参照 Lanai），否则永远不产生重定位。
- **判据用「同 section」而非 `isUndefined()`**：`DADAOAsmBackend::evaluateFixup` 对「目标符号与 fixup 同 section」返回 resolved（含 STB_GLOBAL 函数），跨 section/未定义返回 `nullopt`，交由共享 writer 判 `isSymbolRefDifferenceFullyResolvedImpl`→false→发 reloc。实测同 section 全局 `call main` 仍就地解析（M3 E2E 不回归），跨 section/未定义发 RELA。
- **`ABS48` 永不就地解析**：`evaluateFixup` 的 PCRel 范围检查（`<= PCRel_24`）天然排除排在其后的 `ABS48`；`applyFixup` 对 `IsResolved=false` 先发 reloc 再 return，`IsResolved=true` 且 ABS48 时直接 return（不写占位）。
- **`needsRelocateWithSymbol` 对 ABS48 返回 true**：防止共享 writer 把已定义局部符号改写成 `STT_SECTION`（实测局部同/跨 section 符号在 ABS48 中保留原名）。
- **`set.ow` 未纳入 ABS48 集**：任务书/ADR-0019 明列地址构造为 `set.zw`/`or.w`/`andn.w`；`set.ow`（其余位置 1）属常量材料化首选，非地址构造，故未纳入（见遗留问题）。

**遗留问题**：
- `set.ow` 的符号表达式未映射 `ABS48`（按任务书/ADR 明列范围排除）；若将来需要 `set.ow <sym>` 绝对常量 reloc，须扩展 `isAddressConstructionInstr`。属**能力缺口**（非错值）。
- 全局数据 lower / `.quad <sym>` 的 `ABS64` 类 reloc 未实现（`getRelocType` 对 `FK_Data_*` 走 `llvm_unreachable`）——归 `LLVM-055t`，本任务范围外。
- 本任务不实现 LLD `relocate`（归 `LLVM-056t`）；本任务只保证 `.o` 侧 RELA/类型/编号/addend 正确。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：对改动源码逐行审查（`DADAOELFObjectWriter.cpp` / `DADAOFixupKinds.h` / `DADAOMCCodeEmitter.cpp` / `DADAOAsmBackend.cpp` / `ELF.h` / `ELFRelocs/DADAO.def` / `Object/ELF.cpp`）+ 证据脚本逐条核 FAIL 路径。判决：**通过**（无未修 finding；均已在下方表格处置）。

**逐行审查要点**：
- `getRelocType`：4 个 fixup kind 的映射与 `contract-elf §2.2` 一一对应；`default: llvm_unreachable` 与上游 Lanai 同构（不支持即失败，不静默返回 0——修复了原桩「任何重定位都返回 0=R_DADAO_ABS48」的静默错值）。
- `needsRelocateWithSymbol`：仅 ABS48→true；REL*→false 允许 writer 用 section symbol 表达局部跨段符号（实测 addend/符号正确）。
- `getMachineOpValue`：`isReg`/`isImm` 分支不变；仅 expr 分支新增 rwii 判定 → `ABS48`(PCRel=false)；其余 expr 仍走既有 PCRel 路径（branch/call/jump）。`wp` 操作数为 imm，不受影响。
- `applyFixup`：范围检查扩到 `ABS48`；`!IsResolved` → `maybeAddReloc` 后 return（尊重 `IsResolved`，不写预链接原始值）；ABS48 即使 resolved 也不就地写；PCRel 掩码/位移逻辑未动。
- `getFixupKindInfo`：数组新增第 4 项、索引范围同步到 `ABS48`；否则 applyFixup 里 `getFixupKindInfo(ABS48)` 越界（虽当前无人调用，仍修正）。
- 共享层：**未碰 `lib/MC/**`**；`lib/Object/ELF.cpp` 仅新增 `EM_DADAO` case（名称显示），不改其它 backend 行为；`ELF.h` 新增 `EM_DADAO` 与 `ELFRelocs/DADAO.def` include（additive）。
- 证据脚本：每项 claim 有可达 FAIL 路径（`rel_lines` 精确 `diff`、`grep -q` 退出码、lit/test-codegen/make check 退出码）；`--inject` 校验 `git diff --name-only` 非空（防空注入）、`trap` 复原+重建、还原后断言 worktree 干净；结尾无 `tee`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `applyFixup` 原对未解析 fixup 直接 return，导致 M4 永远不产生重定位 | ✅已修 | 未解析 fixup 先 `maybeAddReloc` 再 return | `run.sh` rela-section/mapping PASS；跨 section/未定义 `readobj -r` 有 4 类 reloc |
| F2 `getRelocType` 桩返回 0（=ABS48），任何 fixup 都静默落 ABS48 | ✅已修 | 实现 4 类映射；未知 kind `llvm_unreachable` | 注入 ABS48→REL14 后 mapping `diff rc=1`（可失败）；四类映射逐条一致 |
| F3 `getFixupKindInfo` 范围停于 `PCRel_24`，ABS48 会越界/走基类 | ✅已修 | 数组+索引范围扩到 `ABS48`（TargetSize=16） | 构建 EXIT=0；映射 PASS |
| F4 `llvm-readobj -r` 打 `Unknown (N)`，不满足验收 2/3「列出 R_DADAO_*」 | ✅已修 | 新增 `ELFRelocs/DADAO.def` + `Object/ELF.cpp` 注册（任务书「或 target 本地头」范围外的必要附加，已披露） | `readobj -r` 显示 `R_DADAO_ABS48/REL26/REL20/REL14` |
| F5 `set.ow` 符号表达式未映射 ABS48 | ❌不修 | 无改动 | 证据：任务书输出 #4 与 `ADR-0019 §D2` 均**明列**地址构造为 `set.zw`/`or.w`/`andn.w`；`contract-isa §4` 中 `set.ow`（其余 48 位置 **1**）是常量材料化首选、非地址构造。范围外，非缺陷（能力缺口登记于遗留问题） |
| F6 全局数据/`.quad <sym>` 无 ABS64 类 reloc | ❌不修 | 无改动 | 证据：任务书「本任务不做：全局数据 lower（`LLVM-055t`）」；`getRelocType` 对 `FK_Data_*` 显式 `llvm_unreachable`（不静默成功）。归 `LLVM-055t` |

**自验命令退出码**：`run.sh`（正常/`--inject`）EXIT=0；`make check` EXIT=0；`make test-codegen` EXIT=0；`make check-lit` EXIT=0；`check-patch-tree` EXIT=0；`check-source-state` EXIT=0。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-06
**审查范围**：证据脚本审核 + 重跑 + 独立注入 + 独立 readobj 复核 + 约束核验

---

##### 1. 证据脚本审核

逐条核 `run.sh`（206 行）：
- **FAIL 路径**：`check()` 函数对 `rc≠0` 打 `[FAIL]` 并递增 `FAILS`；最终 `$FAILS -eq 0` 才 `exit 0`，否则 `exit 1`。**非恒真**。✅
- **注入非空可还原**：`sed -i` 改 `return ELF::R_DADAO_ABS48` → `return ELF::R_DADAO_REL14`；`git diff --name-only` 校验非空（防空注入）；`trap 'git checkout + rebuild' EXIT` 保证还原。✅
- **结尾无 `tee`**：全脚本无 `tee`；输出直接 `echo`/`printf`。✅
- **inject-mapping 逻辑**：注入后 `check_mapping` 期望 `diff rc≠0`（映射错），`$([ "$inj_rc" -ne 0 ] && echo 0 || echo 1)` 正确反转。✅
- **restore-mapping 逻辑**：还原后 `check_mapping` 期望 `diff rc=0`（回绿）。✅
- **check 函数非恒真**：每项传入不同 `name`/`expected`/`actual`/`rc`，断言各异。✅

**脚本判定**：合格，可作为验收证据。

---

##### 2. 重跑记录

**正常模式**（`run.sh`）：

```
$ bash .work/evidence/LLVM-050t/run.sh > /tmp/opencode/LLVM-050t-review/run.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

输出：
```
[PASS] mc-exists | expected: executable | actual: exists=yes | rc=0
[PASS] readobj-exists | expected: executable | actual: exists=yes | rc=0
[PASS] assemble-rela | expected: EXIT=0 | actual: rc=0 | rc=0
[PASS] rela-section | expected: SHT_RELA present, SHT_REL absent | actual: rela_rc=0 rel_rc=1 | rc=0
[PASS] elf-header | expected: Machine 0xDA0, Flags 0x1 | actual: mach_rc=0 flags_rc=0 | rc=0
[PASS] reloc-mapping | expected: ABS48=0 REL26=1 REL20=2 REL14=3 | actual: diff rc=0 | rc=0
[PASS] rela-addend | expected: Addends 0x15 0x16 0x4 0x8 0xC present | actual: missing=0 | rc=0
[PASS] lit-new | expected: Passed: 2 (100.00%) | actual: Passed: 2 (100.00%) | rc=0
[PASS] test-codegen | expected: 15/15 passed; test-codegen: PASS | actual: Results: 15/15 passed, 0 failed | rc=0
[PASS] make-check | expected: repository checks: PASS | actual: repository checks: PASS | rc=0
[PASS] check-patch-tree | expected: patches OK | actual: patches OK | rc=0
[PASS] check-source-state | expected: llvm-project: OK count=1 clean=True | actual: llvm-project: OK HEAD=884f88cb7c5b count=1 clean=True | rc=0
RESULT: PASS (12 checks, 0 failures)
```

**注入模式**（`run.sh --inject`）：

```
$ bash .work/evidence/LLVM-050t/run.sh --inject > /tmp/opencode/LLVM-050t-review/inject.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

输出：
```
inject: breaking getRelocType (ABS48 -> REL14) in llvm/lib/Target/DADAO/MCTargetDesc/DADAOELFObjectWriter.cpp
inject: git diff --name-only => llvm/lib/Target/DADAO/MCTargetDesc/DADAOELFObjectWriter.cpp
inject: rebuilding llvm-mc/llvm-readobj ...
[PASS] inject-mapping | expected: mismatch (ABS48 wrongly REL14) | actual: diff rc=1 | rc=0
inject: restoring source and rebuilding ...
[PASS] restore-mapping | expected: mapping green | actual: diff rc=0 | rc=0
inject: PASS (injection FAILed mapping; restore clean; green again)
```

---

##### 3. 独立注入（与 engineer 不同的方式）

**注入目标**：`HasRelocationAddend_` 由 `true` 改回 `false`（使输出变为 `SHT_REL` 而非 `SHT_RELA`）。
**与 engineer 的注入不同**：engineer 改 `getRelocType` 映射，reviewer 改 `HasRelocationAddend_`。

**注入前**（正常状态）：
```
$ llvm-readobj --sections verify.o | grep -E 'SHT_RELA|SHT_REL'
    Name: .rela.text (1)
    Type: SHT_RELA (0x4)
```

**注入后**（`HasRelocationAddend_=false`）：
```
$ sed -i 's/HasRelocationAddend_=\*\/true/HasRelocationAddend_=*\/false/' DADAOELFObjectWriter.cpp
$ git diff --name-only
llvm/lib/Target/DADAO/MCTargetDesc/DADAOELFObjectWriter.cpp
$ ninja -j8 -C .work/build/llvm llvm-mc llvm-readobj > rebuild.log 2>&1; echo "REBUILD_EXIT=$?"
REBUILD_EXIT=0
$ llvm-mc --triple=dadao-unknown-elf -filetype=obj rela.s -o indep.o
$ llvm-readobj --sections indep.o | grep -E 'SHT_REL|\.rel'
    Name: .rel.text (1)
    Type: SHT_REL (0x9)
```

注入后变为 `SHT_REL`，`rela-section` 断言 FAIL（期望 SHT_RELA 存在且 SHT_REL 不存在）。**注入有效**。

**还原 + 重建**：
```
$ cp writer.cpp.bak DADAOELFObjectWriter.cpp
$ git diff --name-only
(empty — worktree clean)
$ ninja -j8 -C .work/build/llvm llvm-mc llvm-readobj > restore-rebuild.log 2>&1; echo "RESTORE_REBUILD_EXIT=$?"
RESTORE_REBUILD_EXIT=0
$ llvm-readobj --sections indep-restore.o | grep -E 'SHT_RELA|SHT_REL'
    Name: .rela.text (1)
    Type: SHT_RELA (0x4)
```

还原后回绿（`SHT_RELA`）。**注入→FAIL→还原+重建→回绿** 完整闭环。

---

##### 4. 独立 readobj 复核

**（a）跨 section 用例 `.s` → `llvm-mc --filetype=obj` → SHT_RELA / 无 SHT_REL**：

```
$ llvm-readobj --sections verify.o
    Name: .rela.text (1)
    Type: SHT_RELA (0x4)
```
无 `SHT_REL (0x9)`。✅

**（b）`-r`/`--expand-relocs` 列出 R_DADAO_* 类型**：

```
$ llvm-readobj -r --expand-relocs verify.o
  Section (3) .rela.text {
    Relocation { Offset: 0x0  Type: R_DADAO_ABS48 (0) Symbol: ext   Addend: 0x0 }
    Relocation { Offset: 0x4  Type: R_DADAO_ABS48 (0) Symbol: ext   Addend: 0x0 }
    Relocation { Offset: 0x8  Type: R_DADAO_ABS48 (0) Symbol: ext   Addend: 0x0 }
    Relocation { Offset: 0xC  Type: R_DADAO_REL26 (1) Symbol: ext   Addend: 0x0 }
    Relocation { Offset: 0x10 Type: R_DADAO_REL20 (2) Symbol: other Addend: 0x0 }
    Relocation { Offset: 0x14 Type: R_DADAO_REL14 (3) Symbol: other Addend: 0x0 }
  }
```

编号：`ABS48=0` / `REL26=1` / `REL20=2` / `REL14=3`，与 `contract-elf §2.2` 逐条一致。✅

**（c）`e_machine`/`e_flags`**：

```
$ llvm-readobj -h verify.o
  Machine: 0xDA0
  Flags [ (0x1)
    0x1
  ]
```
`e_machine=0x0DA0`、`e_flags` 含 `0x1`。✅

**（d）`r_addend` = `A`**（`rela-addend.s` 用例）：

```
$ llvm-readobj -r --expand-relocs verify-addend.o
  Relocation { Type: R_DADAO_ABS48 (0) Addend: 0x15 }  ; ext+21 → A=21
  Relocation { Type: R_DADAO_ABS48 (0) Addend: 0x16 }  ; ext+22 → A=22
  Relocation { Type: R_DADAO_REL26 (1) Addend: 0x4 }   ; ext+4  → A=4
  Relocation { Type: R_DADAO_REL20 (2) Addend: 0x8 }   ; other+8 → A=8
  Relocation { Type: R_DADAO_REL14 (3) Addend: 0xC }   ; other+12 → A=12
```
`r_addend` 值与源码 `+A` 逐一对应。✅

**（e）reloc/fixup 坑预防5条**：

| # | 坑 | 核验 | 结果 |
|---|---|---|---|
| ① | fixup 必须尊重 `IsResolved` | `applyFixup` 第129行：`if (!IsResolved) { maybeAddReloc(...); return; }`——未解析 fixup 先发 reloc 再 return，不写预链接原始值 | ✅ |
| ② | same-section 判据=「同 section」（非 `isUndefined()`） | `evaluateFixup` 第104行：`if (&Add->getSection() != F.getParent()) return nullopt;`——判据为「目标符号是否与 fixup 同 section」，第18行注释明确说明 | ✅ |
| ③ | `rb0` 禁作基址/零 | emitter 中 `rb0` 仅出现在操作数编码注释（寄存器编号范围），无 `rb0` 误用为基址 | ✅ |
| ④ | 跳转表标签必须显式发射 | MCCodeEmitter 不处理跳转表（codegen 层职责）；跳转表在 ISel 阶段处理，不在此层 | ✅ |
| ⑤ | 大常量不得折入 | `getRelocType` 对未知 kind → `llvm_unreachable`（不静默返回）；`applyFixup` 对 ABS48 即使 resolved 也直接 return（不写占位值） | ✅ |

---

##### 5. 约束核验

| 约束 | 核验 | 结果 |
|---|---|---|
| 不改共享 MC 层（`lib/MC/**`） | `git diff --name-only HEAD~1 \| grep 'lib/MC/'` → 无匹配 | ✅ |
| 不改 `ADR-*`/`contracts/**` | `git diff --name-only HEAD~1 \| grep -E 'ADR\|contracts'` → 无匹配 | ✅ |
| 不碰 `docs/DDLN/**` | `git status --short -- docs/DDLN/` → 无输出 | ✅ |
| 不改证据脚本/产物 | reviewer 仅重跑 `run.sh`，未修改 `.work/evidence/` 或 `.work/source/` | ✅ |
| 临时目录 `/tmp/opencode/LLVM-050t-review/` | reviewer 所有产物在此目录 | ✅ |
| 不提交 git | 无 `git commit` 操作 | ✅ |
| `make check` EXIT=0 | 重跑 EXIT=0，`repository checks: PASS`，36/36 | ✅ |
| `make test-codegen` 15/15 | 重跑 EXIT=0，`Results: 15/15 passed, 0 failed` | ✅ |
| `make check-lit` 36/36 | 重跑 EXIT=0，`Passed: 36 (100.00%)` | ✅ |
| `check-patch-tree` OK | 重跑 EXIT=0，`83 patches OK` | ✅ |
| `check-source-state` clean | 重跑 EXIT=0，`llvm-project: OK HEAD=884f88cb7c5b count=1 clean=True` | ✅ |

---

##### 6. 披露判定

**超出字面清单的附加改动**：

| 附加 | 必要性 | 判定 |
|---|---|---|
| `Object/ELF.cpp`（`getELFRelocationTypeName` 注册 `EM_DADAO`） | **必要**：不加此注册，`llvm-readobj -r` 对自定义 machine 打 `Unknown (N)`，验收 2/3「列出 R_DADAO_*」无法满足 | ✅ 合理 |
| `ELFRelocs/DADAO.def`（新增文件） | **必要**：ELF.h 的 `.def` include 机制要求此文件存在；定义重定位类型枚举值 | ✅ 合理 |
| `ELF.h`（`EM_DADAO` + `ELFRelocs/DADAO.def` include） | **必要**：writer 引用 `ELF::EM_DADAO`、`ELF::R_DADAO_*`，ELF.h 是标准注入点 | ✅ 合理 |

**遗留问题**：

| 遗留 | 阻塞性 | 判定 |
|---|---|---|
| `set.ow` 未映射 ABS48 | 非阻塞：任务书/ADR-0019 明列地址构造为 `set.zw`/`or.w`/`andn.w`；`set.ow` 属常量材料化，非地址构造（能力缺口，已登记） | ✅ 非阻塞 |
| `.quad` → `LLVM-055t` | 非阻塞：任务书明确「本任务不做：全局数据 lower（LLVM-055t）」 | ✅ 非阻塞 |
| LLD → `LLVM-056t` | 非阻塞：任务书明确「本任务不做：LLD（056t）」 | ✅ 非阻塞 |

---

##### 7. 判决

**Accepted**

**理由**：
1. 证据脚本合格（FAIL 路径可达、注入非空可还原、结尾无 `tee`、非恒真）
2. 正常模式 12/12 PASS，EXIT=0
3. 注入模式 2/2 PASS（`inject-mapping` FAIL + `restore-mapping` 回绿），EXIT=0
4. 独立注入（`HasRelocationAddend_ false`）→ 断言 FAIL → 还原+重建 → 回绿，完整闭环
5. 独立 readobj 复核：SHT_RELA 存在/无 SHT_REL、编号 0/1/2/3 与 contract-elf §2.2 一致、`e_machine=0xDA0`、`e_flags=0x1`、`r_addend=A` 正确
6. 5 条坑预防全部守住
7. 不改共享 MC 层、不改 ADR/contracts、不碰 docs/DDLN
8. 附加改动（Object/ELF.cpp、DADAO.def）必要合理
9. 遗留问题均非阻塞，归后续任务
