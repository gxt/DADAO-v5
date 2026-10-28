# LLVM-136t: PR 基线 rebase 与清理（LLVM-130–133 优化前置）

**模块**：llvm
**项目里程碑**：M10
**依赖**：当前 master（含 LLVM-130t–135t 已验收成果）
**状态**：待开始

## 背景（自包含）
外部 PR：`https://github.com/gxt/DADAO-v5/compare/master...xkw9:DADAO-v5:pr/llvm-130-133`
（commit `3d77f7bb`，15 文件）声称汇集 LLVM-130～133 的后端优化，但分支基线过旧，**整体重生成 component patch** 时回退了 master 已有功能：

- `DADAOTargetMachine.cpp` 删除 `selectCodeModel()`，改成 `CM.value_or(CodeModel::Small)` ⇒ `-mcmodel=medium/kernel/tiny` 不再报错（回退 LLVM-131t）；
- `DADAOISelDAGToDAG.cpp` 删除 `ISD::ExternalSymbol` 的 large code model 物化 ⇒ large 间接 libcall 退化（回退 LLVM-131t）；
- `DADAOCodeGen.td` 的 `tailjmp_rrii` 从 `GPRBTC` 改回 `GPRB` ⇒ 重新引入 epilogue clobber 风险（回退 LLVM-131t）；
- 任务号冲突：现有 `LLVM-130t–133t` 已分别用于 64 位缺省/DWARF64、代码模型、fixup 大端、cmp.u 语义；PR 把新优化标成 131/132/133 是错误占用。
- PR 报 lit `151/151`，当前 master 基线为 `154/154`；`lit.cfg.py` 还把 `LLVM_TOOLS_DIR` 提到 site config 之前，绕开安装根（ISS-300 风险）。

## 目标
1. **Rebase/合并到当前 master**（不直接 merge PR 原始提交），重新生成 `components/llvm-project/patches/**`；确保 patch 是从当前源码增量导出，**diff 只含新增功能，不得回退**：
   - `selectCodeModel` 保留；
   - `ExternalSymbol` large 物化保留；
   - `tailjmp_rrii` 保持 `GPRBTC`；
   - LLVM-134t/135t 的 ext 清理/cfx 别名不回归。
2. **任务号重排**：新优化改用 `LLVM-136t–139t`（136 前置、137 i64 移位、138 窄扩展、139 指针 PHI）；docs/test 注释/报告同步，不再写 130–133。
3. **`lit.cfg.py` 工具链口径**：默认恢复安装根/site config 优先；若保留 `LLVM_TOOLS_DIR` override，必须显式 opt-in + 工具链版本/哈希校验，不能静默绕过 `make install-host`。
4. **基线对齐**：矩阵用 `gen_isa_coverage.py` 现场重生成并 `--check`；`make install-host`；当前 lit 基线核对（master 154/154）。
5. 本任务**只做 rebase/清理/基线**，不实现 137–139 的优化；三者的补丁在新基线上另册。

## 验收
- `git diff` 相对 master：无 `selectCodeModel`/`ExternalSymbol`/`tailjmp GPRBTC` 回退；无 LLVM-134/135 回退。
- `make check-patch-tree` rc=0（patch 数与 series 一致、非空 blob）；`make install-host` rc=0。
- `make check` rc=0；`make check-lit` 当前基线全绿（现场统计，不写死 151/154）。
- `gen_isa_coverage.py --check` / 矩阵一致性 rc=0。
- 证据 `.work/evidence/<任务号>/run.sh`（含注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/LLVM-136t/`。

## 约束
- 不直接 `git merge`/`cherry-pick` PR 原始提交；以 rebase/重生成方式接入。
- 不改 spec/contracts/QEMU/前端语义；不新增与 137–139 无关的优化。
- 组件补丁按 `docs/Process-01`（一文件一补丁 + series + `check-patch-tree`）。
- **不提交、不 push**；长构建/长测试申报耗时；全量/夜跑未授权时不跑。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
