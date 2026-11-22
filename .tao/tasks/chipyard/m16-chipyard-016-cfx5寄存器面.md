# m16-chipyard-016: RTL cfx5 寄存器面

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-testcases-004`（盘点：RTL cfx5 只有阵列、无命令面）已合入
**可并行分片**：否
**预估**：3–4 h（GewuFile 寄存器行 + 参数 + 探针）
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

用户 2026-11-22 裁定：cfx 范围含 **cfx5 cache**；三个平台都要支持，缺啥补啥；每个 cfx 一件小任务。

现状：`WumingCfxHa` 只有 `hmon`/`power`/`ptw`，RTL 的 Vast 实现掩码里没有 cfx5；`WumingCache` 已有 D/I 阵列（`m16-chipyard-009/010`），但 cfx5 的寄存器/命令口未接线。`m16-spec-001` 已定义 `cfx_cache`（cfx5）寄存器与命令语义。

本任务只做**寄存器面**：让 `cfx2rd`/`cfx2rc` 能访问 cfx5 的 `cache_exist`/`cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size`，命令暂不驱动阵列（命令接线是下一件）。

## 要做

1. **参数/序列**：`generators/dadao-wuming/.../WumingParams.scala` 的 `WumingCfxHa`（Vast）加入 cfx5；Tiny 不加（Tiny 无 cache）。
2. **寄存器行**：`generators/dadao-gewu/.../GewuFile.scala` 增加 cfx5 的 cg/rc 行，位域/读写属性按 `m16-spec-001` 与 `spec/Kaiwu §3.2` 现场解析（不手写魔数）；`cache_exist` 读 `0b11`（I/D），`cache_enable` 可读写，`cache_ctrl`/`cache_addr_start`/`cache_addr_size` 可读写、保留位按契约报 `CFXREG`。
3. **核分派**：`WumingCore` 的 `cfx2rd`/`cfx2rc` 路径能到达 cfx5；未实现命令编码按契约返回确定值/异常，不 panic、不静默。
4. **探针**：新增 RTL 探针（`tests/arch/cache/` 落点，按 `m16-testcases-006` 的骨架）读回 `cache_exist=0b11`、写读四个寄存器、非法编码 ⇒ `CFXREG`；只做寄存器面，不测阵列数据。
5. **Tiny 不回归**：Tiny 无 cfx5，`WumingTinyConfig` 的 cfx 序列与行为不变。

## 不做

- 不接线 `cache_ctrl` 命令到 D/I 阵列（下件任务）；
- 不改 `WumingCache` 阵列/Cache 逻辑；
- 不改 spec/契约；不改 QEMU/gem5。

## 约束

- 独立 `git worktree`；**不提交 git**；组件改动按 `docs/Process-01` 导出补丁（`components/chipyard/patches/**` + `series`），`make_patch.py chipyard` 幂等；
- 术语「寄存器组」；不写运行期路径；Tiny 的 elaboration 不得改变（对比 FIRRTL/探针）。

## 验证

运行期证据目录内的 `run.sh`：

1. Vast elab + 探针：`cache_exist=0b11`，四个寄存器写读回一致；非法编码 ⇒ `CFXREG`（`contract-see §6.1`）；
2. Tiny：cfx5 不在实现序列，访问 ⇒ `CFXREG`；Tiny 既有代表例（`tests/inst` 01 册或 `semihost_smoke`）不回归；
3. **可达 FAIL**：注入「Vast 的 `WumingCfxHa` 去掉 cfx5」⇒ 探针 `CFXREG`、红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`make check-tasks` 记录 rc；
5. `--inject` ≥2 路；
6. 注明重建耗时与所用环境（JDK/conda/`RISCV`），不把环境问题当代码失败。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
