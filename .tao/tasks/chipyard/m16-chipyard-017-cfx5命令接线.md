# m16-chipyard-017: RTL cfx5 命令接线

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-016`（cfx5 寄存器面）
**可并行分片**：否
**预估**：3–5 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

`m16-chipyard-016` 已让 cfx5 寄存器可访问；本任务把 `cache_ctrl` 命令接到 `WumingCache` 的 D/I 阵列（现有 cmd 口在 `m16-chipyard-009/010` 中接空）。

## 要做

1. **命令解码**：按 `m16-spec-001` 的 `[1:0]` 操作、`[3:2]` 范围、`[15:14]` 选择，`cache_addr_start`/`cache_addr_size` 按 56 位 PA。
2. **D 侧**：clean（写回保留）、invalidate（丢弃脏行）、flush（写回+删除）；范围 all/单行/区间；使能位为 0 不维护；不可缓存/MMIO 无效果不报异常。
3. **I 侧**：clean no-op；invalidate/flush 使 I-Cache 行失效；I 无 dirty。
4. **per-hart**：命令只作用本 hart（单 hart 下无跨核问题）。
5. **Tiny**：Tiny 无 cfx5，行为不变。

## 不做

- 不改 `WumingCache` 的填充/替换算法（只加命令通路）；
- 不改 cfx5 寄存器位域（016）；
- 不写三方用例（`m16-testcases-009`）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出（`components/chipyard/patches/**` + `series`），`make_patch.py chipyard` 幂等；
- 重建环境（JDK/conda/`RISCV`）写进证据脚本；不把环境问题当代码失败；
- 术语「寄存器组」；不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. RTL 探针：D 脏行 invalidate 后内存旧值（DMA/直连读可见）、clean 后新值、flush 后行失效；I 侧改写代码后 invalidate 生效；
2. 范围/使能/异常逐条；Tiny 代表例不回归；
3. **可达 FAIL**：注入「invalidate 先写回」⇒ 红；注入「I 侧不失效」⇒ 红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
