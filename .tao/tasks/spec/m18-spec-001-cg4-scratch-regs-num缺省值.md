# m18-spec-001: cg4 scratch_regs_num 缺省值（cfx0/1/2/3/15=2，其它非 reserved=0）

**模块**：spec
**项目里程碑**：M18
**依赖**：无（与 `ADR-0060`/0.9.0-rc 同批；QEMU/RTL/gem5 实现各自串行）
**可并行分片**：是（spec/contract、QEMU、RTL、gem5 四块）；执行受各组件写者串行约束
**预估**：3–5 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务跨 spec/契约 + 三实现默认值，取 2–3× 中位）
**档位**：中改（寄存器默认值 + 三实现）
**状态**：待开始
**执行环境**：本地（spec + QEMU/gem5；chipyard RTL 构建按节点/本地既有流程）

## 背景

`spec/DADAO-12 §3.5/§3.7` 当前把 `cg4 rc6 scratch_regs_num` 定义为「硬件实现至少 2 个、最多 64 个」，QEMU/gem5 对所有 cfx 都给 4，chipyard `GewuCfxParams.scratchRegs` 默认 4。用户 2026-11-23 要求改为：

- `cfx0/1/2/3/15` 缺省 **2**（四个 monitor + hart；实际上 cg6 只在这些 cfx 被内核用）；
- 其它**非 reserved** cfx 缺省 **0**（不提供暂存寄存器，访问 cg6 即 `CFXREG`）；
- `0` 成为合法值；非 0 仍是 2..64。

## 目标

1. **spec**：`§3.5` 的 `scratch_regs_num` 行与 `§3.7` 的「每个核芯功能扩展都有暂存寄存器」改为「数量由 cfxha 决定；0 表示无暂存寄存器；cfx0/1/2/3/15 缺省 2，其它非 reserved 缺省 0；非 0 范围 2..64」；`rc >= N` 或 `N=0` 访问 cg6 ⇒ `CFXREG`。
2. **contract**：`contract-see §3`/`contract-syscall §8` 里「scratch_regs_num ≥ 2」的绝对表述改为「仅在 cfx0/1/2/3/15 保证 ≥2；其它 cfx 可为 0」；`contract-cfx-aliases` 仅字段表，不需要改。
3. **QEMU**：`cfx_reg_ptr`/初始化按 cfxha 给默认：0/1/2/3/15=2，其它已实现非 reserved（4/5/32/34/63 等）0；cg6 访问 `rc >= N` 或 N=0 ⇒ `CFXREG`。
4. **chipyard RTL**：`GewuCfxParams.scratchRegs` 默认按 cfx 设定；cfx0/2（及将来 cfx1/3）2，cfx3/63 等未用 0；cfx15 若未实现则不影响。
5. **gem5**：`tiny_cfx.cc`/`node_cfx.cc` 初始化按 cfx 设定；cg6 访问规则同上。
6. **测试/期望**：`tests/arch/umon/check_cfx02_regs.py`、`m5_perm_badcombo_cfxreg.s`、`cfx02_regs.S`、`tests/inst/11-cfx` 等把「scratch_regs_num=4」改为按 cfx 期望（0/2），并加「cfx4/5/32/34 的 cg6 访问 ⇒ CFXREG」的用例。

## 验收（逐条贴真实 rc）

1. spec/contract 改后 `check-spec-refs`/`check-spec-drift`/`check-spec-purity`/`check-spec-changelog`/`check-contracts-*` rc=0；`grep` 无「每个 cfx 至少 2 个」类旧表述。
2. QEMU：cfx0/2/15 `cg4 rc6=2`；cfx4/5/32/34/63 `=0`；cfx0 的 `cg6 rc0/rc1` 可读写，`rc2` ⇒ `CFXREG`；cfx4/5 的任意 cg6 ⇒ `CFXREG`。探针覆盖。
3. gem5 同 QEMU 口径；chipyard `check-arch` 代表集或对应 cfx 探针同口径。
4. **可达 FAIL ≥2 路**：① 把 cfx4 的 scratch_regs_num 改回 2 ⇒ 新负向用例红；② 把 cfx0 改成 0 ⇒ `cg6 rc0/1` 读写红；`cp`+md5 还原后回绿。
5. 不回归：`check-inst-asm`、`check-arch-smoke`、`check-qemu-forms`、`check-patch-tree` 各组件段 0 problem；`make check` 与基线逐行相同。
6. 三实现口径一致（QEMU/gem5/chipyard 探针期望同一表）；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 改动范围：`spec/DADAO-12-SEE-…`、`spec/.manifests.toml`、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-syscall.md`、`components/qemu/patches/**`、`components/chipyard/patches/**`、`components/gem5/patches/**`、`tests/arch/**`、`tests/inst/**`、各组件 changelog、本任务书。
3. 不改 `Makefile`、内核、busybox；不改版本号（随 0.9.0-rc 批次，由主会话统一）；术语「bank = 寄存器组」。
4. 组件补丁经各自 `make_patch.py` 重导；源码还原 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
5. 与 `ADR-0060`（hart-first/cg9）同属 0.9.0-rc 批次，但不改 cg9/异步投递逻辑；若 QEMU/RTL/gem5 的 hart-first 任务先改同一文件，先合入者为准，后做者 rebase。

## 待裁定

- **cfx4（`cfx_ptw`）是否也置 0**：当前 `dadao_switch_mm()` 的 `contract-tlb TLB-30` 步骤 ④ 会读写 `cfx_ptw cg6 rc0/rc1`；若 cfx4 缺省 0，这两次访问会 `CFXREG`、启动即失败。两个选择：
  - A：cfx4 也缺省 2（作为例外）；
  - B：保持 cfx4=0，并删除 `dadao_switch_mm()` 的 cfx_ptw cg6 读写、同步改 `contract-tlb TLB-30`（该注释称步骤 ④ 当前只是“可组合性”，未被 ①–③ 使用）。
  未定前不派实现。

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
