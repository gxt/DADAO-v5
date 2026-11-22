# m16-gem5-020: gem5 cache 前置与接线（StaticInst flags + `--caches`）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-testcases-004`（盘点）已合入；`m16-gem5-019`（D21 差异）
**可并行分片**：否
**预估**：中（flags + 配置，不含 cfx5 命令）
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

`m16-gem5-019` 的 D21：`src/arch/dadao/inst.cc` 只置 `IsInteger/IsFloating/IsInvalid/IsNonSpeculative`，`opClass` 恒 `IntAluOp`，未置 `IsLoad/IsStore/IsAtomic`。后果：开 cache 后 gem5 认不出访存，cache 不工作。

裁定（`discussing.md`「M16 三方差分（Vast arch）批次裁定」）：gem5 用 Classic cache，`cache-model=on` 映射 `--caches`；cache 只服务 arch 功能覆盖，周期判据不进本轮。**本任务只做前置与接线，不实现 cfx5 命令**（下一任务）。

## 要做

1. **StaticInst flags**：在 `src/arch/dadao/inst.cc` 按解码结果设置 `IsLoad`/`IsStore`/`IsAtomic`（以及必要的 `opClass`：`MemReadOp`/`MemWriteOp`），来源用现有 decoder 的 mm/load/store 分类；不得引入第二套分类表。
2. **`--caches` 接线**：`configs/dadao/fs.py` 增加 L1 I/D cache 参数（大小/相联/行宽，默认与 RTL 一致：8 路 × 128 组 × 64 B），由 `cache-model=on` 或 shim 映射打开；`off` 路径（默认）不加 cache，行为与现在逐字节相同。
3. **`qemu_gem5_shim.py`**：把 `-machine ...,cache-model=on` 映射为 gem5 `--caches` + L1 参数；`off` 不加。
4. **不回归**：Atomic/Timing 现有测试（`run_inst_tiny` 01 册、`run_m5_e2e --profile vast`）在 `off` 下不变；`on` 下至少能启动并完成一个最小访存程序。

## 不做

- 不实现 cfx5 寄存器/命令（`m16-gem5-021`）；
- 不改 `src/cpu/simple/**`、不改 cache 组件；
- 不设周期阈值、不改周期表口径。

## 约束

- 独立 `git worktree`；**不提交 git**；组件改动按 `docs/Process-01` 导出补丁（`make_patch.py gem5` 幂等），显式 staging；
- 不改 `spec/`/契约；术语「寄存器组」；
- 不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. **flags 可达 FAIL**：去掉 `IsLoad/IsStore` 注入 ⇒ `cache-model=on` 下 cache 不命中（`system.cpu.dcache` 统计为 0 或程序失败）⇒ 红；`cp`+md5 还原后回绿；
2. `cache-model=off`：`run_inst_tiny` 01 册 38/38、`run_m5_e2e --profile vast` 10/10，与改前逐字节/逐例相同；
3. `cache-model=on`：最小访存程序跑通，`dcache` 有命中/缺失统计；与 `off` 的签名一致（功能不因 cache 改变）；
4. `check-gem5-decode`、`check-patch-tree`（gem5 段 0 problem）、`check-index-blobs` 记录 rc；
5. `--inject` 至少 2 路（去 flags / 去 `--caches` 映射）⇒ 各自红，还原回绿；
6. `make check-tasks` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
