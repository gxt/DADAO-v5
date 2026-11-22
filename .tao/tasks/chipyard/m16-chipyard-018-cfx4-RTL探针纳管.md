# m16-chipyard-018: cfx4 RTL PTW/TLB 探针纳管

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-testcases-010`（cfx4 case id/期望已落 `tests/arch/ptw`）
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

现有 RTL 的 cfx4 探针散在 `tools/chipyard/ptw/{vastptw,vastwalk}` 与 `tlb/vasttlb`，检查点与 QEMU 的 15 条不完全对应。`m16-testcases-010` 已把 QEMU 侧纳管；本任务把 RTL 侧接入同一 case id / expected，形成三方中的 RTL 一方。

## 要做

1. **迁入**：`tools/chipyard/ptw/**`、`tlb/vasttlb*` 的载体/生成器/check 脚本落 `tests/arch/ptw/`（RTL 后端），迁完删旧目录（按 `discussing` 落点）。
2. **对齐 case id**：RTL 探针的检查点映射到 `m16-testcases-010` 的 15 条 case；缺的补、多的登记为额外检查点。
3. **签名统一**：RTL 侧用 `tests/shared/signature.py` 与 `tests/shared/asm/signature.inc`（`__REC`→`SIGUPD` 已是同机制），host 侧不另写解析器。
4. **三方跑**：`run_arch.py --cfx 4 --platforms qemu,gem5,chipyard` 三方逐槽一致；不一致登记 `expected-divergences.yaml`。
5. **Tiny 不回归**：Tiny 无 PTW，既有代表例不变。

6. **HSU 覆盖**（用户 2026-11-22：HSU 纳入、J 不纳入）：RTL 侧 PTE 的 `H`/`S`/`U` 与 `R/W/X` 组合逐条对齐 QEMU/gem5；J 位不测，未覆盖项写入清单。

## 不做

- 不改 PTW/TLB 的实现语义（只纳管探针；实现缺口另立任务）；
- 不改 QEMU/gem5。

## 约束

- 独立 `git worktree`；**不提交 git**；RTL 探针集中 `tests/arch/ptw/`；
- 重建环境写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. RTL 探针逐条跑通，签名与 QEMU/gem5 逐槽一致（或登记差异）；
2. 15 条 case 的 RTL 在位情况现场统计（缺的写「缺」+ 原因）；
3. **可达 FAIL**：改一条 RTL 记录值 ⇒ 红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
