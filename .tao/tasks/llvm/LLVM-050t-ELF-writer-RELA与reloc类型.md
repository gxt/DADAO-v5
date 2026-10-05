# LLVM-050t: ELF writer → RELA + `e_flags=1` + `e_machine`→dadao + `getRelocType`（4 类）

**模块**：llvm
**项目里程碑**：M4
**依赖**：`SPEC-105t`、`SPEC-109t`、`INFRA-045t`
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
