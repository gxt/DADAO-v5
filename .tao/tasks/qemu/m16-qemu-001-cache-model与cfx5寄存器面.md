# m16-qemu-001: `cache-model` 属性与 cfx5 寄存器面

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-testcases-004`（盘点）、`m16-testcases-006`（arch 骨架）已合入
**可并行分片**：否
**预估**：中（属性 + 寄存器面，不含影子数据通路）
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

用户 2026-11-22 裁定（`discussing.md`「M16 三方差分（Vast arch）批次裁定」）：

- QEMU 增加 `-machine kaiwu-vast,cache-model=off|on`，**默认 off**；off 保持现有直通（Linux/K0/inst 不变），on 只给 arch 测试。
- 完整影子写回 D-Cache 是后续任务；本任务先落**属性 + cfx5 寄存器面**，为影子通路与命令接线留稳定接口。
- `cache-model=off` 时 cfx5 口径：`cache_exist` 读 0，cfx5 命令/寄存器访问按 `CFXREG`（保留）处理。

## 要做

1. **`cache-model` 属性**：`hw/dadao/dadao-machine.c` 增加 QOM property，取值 `off|on`，默认 `off`；非法值启动报错（非零退出）。`on` 时记录到 machine 状态，供后续任务使用。
2. **cfx5 寄存器面**：
   - `off`：`cache_exist` 读 0；`cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size` 等 cfx5 寄存器按 `CFXREG` 处理（与现有"未实现 cfx"路径一致）。
   - `on`：`cache_exist` = `0b11`（I/D）；`cache_enable`、`cache_ctrl`、`cache_addr_start`、`cache_addr_size` 可读写，保留位/非法编码按契约（`m16-spec-001`）报 `CFXREG`；命令暂不产生数据效果（留给影子 D-Cache 任务），但必须返回确定值、不 panic。
3. **契约对齐**：寄存器号/位域从 `m16-spec-001`（`spec/Kaiwu §3.2`、`.tao/contracts/contract-cache.md` 若存在）现场解析，不手写魔数；若契约缺失，先登记缺口再实现，不自行定义。
4. **不回归**：`off` 下现有 QEMU 测试（`check-arch-smoke`、K0 冒烟、`run_inst_tiny` 代表例）行为不变。

## 不做

- 不实现影子 D-Cache 数据通路（下件任务）；
- 不实现 cfx5 命令对 I/D cache 的实际维护效果（下件任务）；
- 不改 `spec/`/契约正文；不改 RTL/gem5。

## 约束

- 独立 `git worktree`；**不提交 git**；组件改动按 `docs/Process-01` 导出补丁（`components/qemu/patches/**`）；
- 不改 `src/cpu/simple/**`；术语「寄存器组」；不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `off` 默认：cfx5 寄存器访问报 `CFXREG`、`cache_exist=0`；现有 `check-arch-smoke` 与一条 K0/inst 代表例 rc=0，与改前一致；
2. `on`：`cache_exist=0b11`；四个寄存器可读写且回读一致；非法编码报 `CFXREG`；
3. `cache-model=bogus`：启动非零退出并给出可读错误；
4. **可达 FAIL**：注入「off 下 cfx5 可访问」⇒ 判据红；注入「on 下 `cache_exist` 只置 I」⇒ 红；`cp`+md5 还原后回绿；
5. `check-patch-tree`（qemu 段 0 problem）、`check-index-blobs`、`make check-tasks` 记录 rc；
6. `--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
