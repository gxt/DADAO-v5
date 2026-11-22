# m16-chipyard-019: RTL cfx0/2 寄存器面与权限（A）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-017`（cfx5 命令接线）合入
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定：先 A 再做 B）

004 盘点：RTL 的 `WumingCfxHa` 只有 hmon/power/ptw，**cfx0 umon 与 cfx2 smon 全缺**——无寄存器行、`cfx2rd`/`cfx2rc` 访问直接 `CFXREG`；同步异常还固定进 hmon（`WumingParams.scala.patch:154` 的 `monitor = 0`）。

本任务只做 **A：寄存器面 + 权限**；U/S 模式进入路由由 `m16-chipyard-020`（B）另做。

## 要做

1. **cfx 序列**：`WumingParams.scala` 的 `WumingCfxHa`（Vast）加入 cfx0、cfx2；Tiny 不加（Tiny 不跑 Linux，保持现状）。
2. **寄存器行**：`GewuFile` 为 cfx0/cfx2 提供 cg/rc 行（模式行、id/version/计数、异常帧、scratch、全局中断掩码等，按 `DADAO-12 §3` 与 `contract-see` 的 cfx 寄存器表）；保留 rc 仍 `CFXREG`。
3. **权限**：`cfx2rd`/`cfx2rc` 访问 cfx0/2 时走通用两轴掩码；未实现的寄存器/保留位按 CACHE 类同法报 `CFXREG`。
4. **探针**：RTL 探针读 cfx0/2 寄存器、写读回、保留 rc ⇒ `CFXREG`；只测寄存器面，不测 U/S 模式进入。
5. **不回归**：Tiny 的 cfx 序列不变；cfx3/4/5/63 现有行为不变。

## 不做

- 不补 U/S 模式进入路由（`monitor` 仍固定 hmon）——留给 `m16-chipyard-020`；
- 不改 `WumingCore` 的异常进入主控制流；
- 不改 QEMU/gem5。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境（JDK/conda/`RISCV`）写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. RTL 探针：cfx0/2 的寄存器读写、保留 rc ⇒ `CFXREG`；Vast 上 `cfx2rd`/`cfx2rc` 不再一律 `CFXREG`；
2. Tiny 的 cfx 序列不变、代表例不回归；cfx3/4/5/63 现有探针不回归；
3. **可达 FAIL**：注入「Vast 去掉 cfx0」⇒ 探针 `CFXREG`、红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
