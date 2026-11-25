# m16-testcases-023: 删除 ADWBFAIL 用例（页表必须在内存；`DIV-14`/`DIV-04` 收口）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-chipyard-018`（007 现状）、`m16-chipyard-022`（pmem）
**可并行分片**：否（共享 `tests/arch/ptw/`）
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-25 裁定）

1. **页表必须放在内存里，用的是内存的物理地址**（不能放 BootROM/只读镜像）。
2. **不构建 ADWBFAIL 的测试用例**。

据此，`arch-ptw-007` 的 `flush_adwbfail` 子项（槽 2/3）**在三个平台上都不成立**：QEMU/gem5 原来靠"页表放只读 BootROM"构造 A/D 回写失败，违反第 1 条；RTL 的 PA RAM 全可写，构造不出。`DIV-14`（RTL 不可观测）与 `DIV-04`（ADWBFAIL 不单列用例）随之收口。

## 要做

1. **删用例**：从 `tests/arch/ptw/` 的 `arch-ptw-007` 移除 `flush_adwbfail` 子项（`ptw_sig.S`/`ptw_carrier_tlb.py`/`ptw_sig` 生成器/`expected.yaml`/`rtl-coverage.yaml`），槽数由 4 降为 2（只留 `flush_ok`）；`expected.yaml`/`gen_*`/`--selfcheck` 双向一致。
2. **登记收口**：
   - 删除 `expected-divergences.yaml` 的 `DIV-14`；
   - `DIV-04` 改写为"ADWBFAIL 不做用例（用户裁定：页表必须在内存 + 不构建 ADWBFAIL 用例）"，状态 `closed`/`wont-fix`（按 schema 支持的方式）；
   - `ISS-515` 关闭（`wont-fix`，理由同上）；`tests/arch/README.md`/`vast-arch-inventory.md` 的未覆盖项同步。
3. **RTL `ptw_tlb.S` 的 `CASE_OR` 手工注入**：不再是"用例覆盖"来源；按新口径处置——**保留为实现的内部证据可、但不得在文档/完成区声称它覆盖 ADWBFAIL 用例**（若删除该注入段，需说明它对 `ptw_tlb` 其它检查点无影响）。
4. **不回归**：`arch-ptw-001/002/006` 其它 signature/guest 用例、`arch-ptw-013`（known-red 待 `m16-testcases-022`）、`014/015` gap；QEMU/gem5/RTL 逐槽。

## 不做

- 不改 spec/契约（第 1/2 条是用户裁定，已可由现有 §4.5/§2.2 解释）；
- 不改 RTL/spec 的 A/D 回写语义；
- 不新造 ADWBFAIL 用例。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 `tests/arch/ptw/**`、`tests/arch.yaml`、`tests/arch/modes.yaml`、`expected-divergences.yaml`、`tests/arch/README.md`、`vast-arch-inventory.md`、本任务书；
- 不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `arch-ptw-007` 只剩 `flush_ok` 两槽，三方（QEMU/gem5/RTL）逐槽一致；
2. `DIV-14` 已删、`DIV-04` 改写并关闭、`ISS-515` 关闭、文档无"ADWBFAIL 用例覆盖"表述；
3. **可达 FAIL ≥2**：注入"把 `flush_adwbfail` 加回" ⇒ `--selfcheck`/run_arch 红；注入"页表放只读镜像" ⇒ 判据红（或在文档登记为何不再允许）；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、`run_arch --self-test`、`check_issues` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
