# m16-chipyard-027: RTL 缺面补齐（power common face + cfx5 S/U 可达）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-testcases-009` 复核结论（`DIV-16` 是否成立）；`m16-chipyard-023` 已合入
**可并行分片**：否（同改 `components/chipyard`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

- `ISS-524`：RTL 的 `cfx_power` 未开 common face（`cg4`/`cg6` 读出 `CFXREG`），而 `DADAO-12 §3.5/§3.7` 要求每个非 reserved cfx 都实现（QEMU/gem5 合规范）。
- `DIV-16`（`m16-testcases-009` 登记，待复核确认）：RTL 的 `cfx5` 只有 `cg8` 面，`cg0–cg3`（含 `user/supv_cfxreg`、`cg3 rc12`）不存在 ⇒ cfx5 的 S/U 访问在 RTL 不可达，`rtl-coverage.yaml` 记四条 mode gap。

## 要做

1. **`cfx_power` common face**：按 `commonRows` 打开 `cg4`（计数）与 `cg6`（scratch，≥2 个）；`cfx_id = 63`；不改变 `cg7`（BootROM 空间描述）与 `cg8 rc1`（power ctrl）语义。
2. **`cfx5` 的模式面**：按 `§3.1–§3.4` 给 cfx5 打开 `cg0–cg3`（至少 `user/supv_cfxreg` 与 `cg3 rc12`），使其 S/U 访问可达；**不放宽** `cfx5` 的维护命令语义。顺带修 **ISS-534**：维护端口把 `cache_addr_start` 截到 48 位（`CACHE-18` 要求 56 位不截断），补一条 ≥48 位向量。
3. **探针**：
   - `tests/arch/power/` 的 `arch-power-001` 把 `cg4/cg6` 纳入比较面（删 `DIV-13`）；
   - `tests/arch/cache/` 的 `arch-cache-001/002` 加 smon/umon 的 RTL 承载（删/收窄 `DIV-16` 的 mode gap）。
4. **不回归**：Tiny 无 cfx5/cfx_power 的 common face 变化；cfx0/2 两轴判权、cfx15/32/34、cfx5 的 H 模式用例、Tiny `11-cfx`/`01-load-store`。

## 不做

- 不改 `cfx_power_ctrl` 写侧（ISS-525，另立 qemu/gem5/RTL 分件）；
- 不改 QEMU/gem5/spec；
- 不支持多 hart。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出、`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `cfx_power` 的 `cg4`/`cg6` 读写符合 `§3.5/§3.7`（`cfx_id=63`、scratch 可读写），`arch-power-001` 槽位全绿、`DIV-13` 删除；
2. `cfx5` 的 `cg0–cg3` 在 S/U 可达（`arch-cache-001/002` 的 smon/umon RTL 段跑通），`DIV-16` 收窄或删除；
3. **可达 FAIL ≥2**：注入"关掉 power common face"、"关掉 cfx5 的 supv 行" ⇒ 红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、index-blobs/tests-index/tasks/component-changelog/no-residue、`run_arch.py --self-test` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
