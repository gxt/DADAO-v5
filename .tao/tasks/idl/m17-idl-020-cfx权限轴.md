# m17-idl-020: cfx 权限轴——`cfxreg`/`cfxexe` + 拒绝路径载体（B）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-013`（272 例四方基线）
**可并行分片**：否（改 `idl_exec.py` 与 `tests/inst`）
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景（用户 2026-11-23 裁 B）

cfx 评估结论：主路径完整，但权限轴只有 `cfxtrap` 在 IDL 里实现；`cfxreg`/`cfxexe` 未实现、`cfxmem` 未建模，且**没有任何「掩码拒绝 ⇒ CFXPERM」载体**。裁 B：补 `cfxreg`/`cfxexe`，并加 2 个拒绝路径载体进四方（272 → 274）。`cfxmem` 单列，不在本任务。

## 要做

1. `idl/tools/idl_exec.py`：
   - `cfx2rd`/`cfx2rc`：查**目标 cfx** 的当前模式 `cg3[CG3_REG]` 掩码（位索引 = 源 cfx = 当前 `cfx_code`；自身位忽略）⇒ 命中即 `CfxPerm`；`cause_info = 触发指令地址`（`DADAO-12 §4.1`）；
   - 直接跳转/取指进入其它 cfx（`cfxexe`）：按目标 cfx 的 `cg3[CG3_EXE]` + 源 cfx 位判定；`cfx2*`/`trap` 已有 `cfxtrap` 的路由保持一致；
   - 复位掩码与 `DADAO-13 §1` 一致（已有 cg3 初值，不得擅改）。
2. 新增 2 个载体（`tests/inst/11-cfx/`，命名与现有风格一致）：
   - `cfxreg` 拒绝：在 `cfx_power(63)` 里把 `cfx_hmon` 的 hypv `cfxreg` 掩码的 bit63 置 1，再 `cfx2rd cfx_hmon` ⇒ **CFXPERM** + `[39] NCFXPERM` + `cause_info = 指令地址`；
   - `cfxtrap` 拒绝：把 `cfx_hmon` 的 hypv `cfxtrap` bit63 置 1，再 `trap cfx_hmon` ⇒ **CFXPERM**（`cfx2*` 路径已实现，作对照）。
   - 两例都要有可达 FAIL（不触发/错 cause/cause_info 错 ⇒ 该例红）。
3. 同步测试数据与索引：`make inst-signature-data`（`expected.tsv`/`inputs.sha256` 从 `.S` 派生）、`tests/case-ledger.tsv`、`tests/inst.yaml`（按 `check-case-ledger`/`check-tests-index` 口径）；主清单 `idl/data/idl_exec_cases.toml` 272 → 274。
4. `idl/README.md`/`idl/docs/four-way.md` 的 cfx 说明补权限轴。

## 不做

- **`cfxmem`**（cfx SRAM/MMIO 地址窗口）不建模，单列；
- 不改 QEMU/gem5/chipyard/RTL；**若四方出现平台分叉**（尤其 `ISS-469` QEMU `cause_info`），保留现场、逐条归因、写「待裁定」并继续推进其余部分，**不在本任务改组件补丁**；
- 不改 `cfxtrap` 已有语义、不改 `fence`/`escape`。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 计数现场派生；完成区 ≤30 行、不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl` rc=0（**274/274**，IDL+QEMU）；全四方 274/274（或逐条列平台分叉与归因）；
2. 两个新载体在 IDL 上确实产生 `CFXPERM`（cause one-hot `1<<7`、子原因 `[39]`、`cause_info` = 指令地址）；
3. **可达 FAIL ≥3 路**：① 去掉 `cfxreg` 掩码检查 ⇒ 该例红；② `cause_info` 写成指令编码 ⇒ 该例红；③ 掩码位索引写反（自己/源） ⇒ 该例红；均 `cp`+md5 还原后回绿；
4. `check-idl-parse`/`check-idl-sync`/`check-case-ledger`/`check-tests-index`/`check-manifests-guard` rc=0；槽数/例数现场派生；
5. `idl/tools/idl_check_anchor.py --update` 后 `check-idl-exec-anchor` rc=0（`.idl` 未改、应无变化，确认即可）。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
