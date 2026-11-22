# m16-testcases-010: cfx4 PTW/TLB 用例纳管与 QEMU/gem5 跑通

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-006`（`run_arch.py` 骨架）已合入
**可并行分片**：是（15 条可分片，但共享 `tests/arch/ptw/expected.yaml`）
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

现有 cfx4 的 15 条 TLB/PTW 探针载体在 `tools/testcases/arch/min_rom_probe_tlb.py`（QEMU bootrom），不在 `tests/arch.yaml`。按 004 的落点方案，把它们迁入 `tests/arch/ptw/`，由 `run_arch.py --cfx 4` 驱动，先跑 QEMU + gem5（shim），RTL 侧由 `m16-chipyard-018`。

## 要做

1. **迁入**：15 条 case 的载体/期望/生成器落到 `tests/arch/ptw/`；`expected.yaml` 保留现有判据来源（`contract-tlb`/`contract-see`/`spec/DADAO-12`）。
2. **索引**：`tests/arch.yaml` 登记 15 条（`kind: driver`，`machine: vast`，`platforms: [system]`）。
3. **驱动**：`run_arch.py --cfx 4 --platforms qemu,gem5` 能逐条跑并取签名；gem5 经 `qemu_gem5_shim.py`（`-machine kaiwu-vast`）。
4. **三方预留**：RTL 后端未接时显式 fail-closed（不静默），由 `m16-chipyard-018` 接。
5. **覆盖**：每条 case 的检查点映射到 `contract-tlb` 条款，回填 `tests/arch/data/vast-arch-inventory.md` 的 cfx4 行。

## 不做

- 不新增语义用例（先迁现有 15 条）；
- 不改 QEMU/gem5/RTL 实现；
- 不接 RTL 后端（下一件）。

## 约束

- 独立 `git worktree`；**不提交 git**；用例/驱动/期望集中 `tests/arch/ptw/`；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 15 条在 QEMU 上逐条 rc=0 且签名与现有期望一致；
2. 15 条在 gem5（shim）上逐条跑；与 QEMU 签名一致，或逐条登记差异（原因+用户裁定状态）；
3. `check-tests-index` 现场统计 `arch` 条数 = yaml 条数；注入「删一条」⇒ 红；
4. **可达 FAIL**：改一条期望槽 ⇒ 红；`cp`+md5 还原回绿；
5. `check-tasks`、`check-knowledge-refs` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
