# m18-spec-001: cg4 scratch_regs_num 缺省值（每个非 reserved cfx = 2）

**模块**：spec
**项目里程碑**：M18
**依赖**：无（与 `ADR-0060`/0.9.0-rc 同批；QEMU/RTL/gem5 实现各自串行）
**可并行分片**：是（spec/contract、QEMU、RTL、gem5 四块）；执行受各组件写者串行约束
**预估**：2–4 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为默认值 + 三实现，取 2–3× 中位）
**档位**：中改（寄存器默认值 + 三实现）
**状态**：待开始
**执行环境**：本地（spec + QEMU/gem5；chipyard RTL 构建按节点/本地既有流程）
**放行（用户 2026-11-25）**：契约语义变更已认可（每个非 reserved cfx 由 4 改 2）；**一次全做**（spec/契约 + QEMU + gem5 + RTL），但**等 M16 chipyard 批次释放 RTL 写者窗口后**再派单；版本号不动。

## 背景

`spec/DADAO-12 §3.5/§3.7` 规定 `cg4 rc6 scratch_regs_num`「至少 2 个、最多 64 个」；QEMU/gem5 对所有 cfx 都给 **4**，chipyard `GewuCfxParams.scratchRegs` 默认 **4**。

用户 2026-11-23 最终裁定：**每个非 reserved cfx 的缺省值 = 2**（此前讨论过 0，已按本次裁定覆盖）。reserved cfx 不实现该寄存器（访问仍 `CFXREG`），不参与缺省值。

## 目标

1. **spec**：`§3.5` 的 `scratch_regs_num` 行与 `§3.7` 明确「非 reserved cfx 的缺省值 = 2；范围 2..64」；`rc >= 2` 访问 cg6 ⇒ `CFXREG`。
2. **contract**：`contract-see §3`/`contract-syscall §8` 的「`scratch_regs_num ≥ 2`」保持，补一句「测试机缺省 2」；`contract-cfx-aliases` 不需要改。
3. **QEMU**：`r->scratch_regs_num` 由 4 改 **2**（所有已实现非 reserved cfx）；cg6 访问 `rc >= 2` ⇒ `CFXREG`。
4. **chipyard RTL**：`GewuCfxParams.scratchRegs` 默认 4 → **2**（cfx0/2 及所有 `commonRows` cfx）；`cfx3/63` 等已实现的非 reserved cfx 同样 2。
5. **gem5**：`tiny_cfx.cc`/`node_cfx.cc` 初始化 4 → **2**；cg6 访问规则同上。
6. **测试/期望**：`tests/arch/umon/check_cfx02_regs.py`、`m5_perm_badcombo_cfxreg.s`、`cfx02_regs.S`、`tests/inst/11-cfx` 等把「scratch_regs_num=4 / rc2..3 可读写」改为 2 / rc2 起 `CFXREG`；三平台口径一致。

## 验收（逐条贴真实 rc）

1. spec/contract 改后 `check-spec-refs`/`check-spec-drift`/`check-spec-purity`/`check-spec-changelog`/`check-contracts-*` rc=0；活文档无「scratch_regs_num=4」类旧值。
2. QEMU：cfx0/2/4/5/15/32/34/63 的 `cg4 rc6=2`；`cg6 rc0/rc1` 可读写，`rc2` ⇒ `CFXREG`；reserved cfx 仍 `CFXREG`。
3. gem5 同 QEMU 口径；chipyard `check-arch`/cfx 探针同口径。
4. **可达 FAIL ≥2 路**：① 把某 cfx 的 scratch_regs_num 改回 4 ⇒ 新负向用例红；② 把 cfx0 改成 0 ⇒ `cg6 rc0/1` 读写红；`cp`+md5 还原后回绿。
5. 不回归：`check-inst-asm`、`check-arch-smoke`、`check-qemu-forms`、`check-patch-tree` 各组件段 0 problem；`make check` 与基线逐行相同。
6. 三实现口径一致；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 改动范围：`spec/DADAO-12-SEE-…`、`spec/.manifests.toml`、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-syscall.md`、`components/qemu/patches/**`、`components/chipyard/patches/**`、`components/gem5/patches/**`、`tests/arch/**`、`tests/inst/**`、各组件 changelog、本任务书。
3. 不改 `Makefile`、内核、busybox；不改版本号（随 0.9.0-rc 批次，由主会话统一）；术语「bank = 寄存器组」。
4. 组件补丁经各自 `make_patch.py` 重导；源码还原 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
5. 与 `ADR-0060`（hart-first/cg9）同属 0.9.0-rc 批次，但不改 cg9/异步投递逻辑；若 QEMU/RTL/gem5 的 hart-first 任务先改同一文件，先合入者为准，后做者 rebase。

## 待裁定

无。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
