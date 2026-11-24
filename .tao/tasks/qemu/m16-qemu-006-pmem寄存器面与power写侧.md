# m16-qemu-006: QEMU cfx_pmem 寄存器面 + cfx_power_ctrl 写侧

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-chipyard-022` 已合入（RTL 面基准）；`m16-spec-003` 的一致性裁定（若涉及 DMA 语义）
**可并行分片**：否（同改 `components/qemu`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

- `ISS-533`：QEMU 的 `cfx_pmem` 只实现 `cg15`（+`cg7`），`cg8/cg12/cg13/cg14` 走 `CFXREG`；RTL 按 `DADAO-12 §4.9` 全实现 ⇒ cfx32 寄存器面不能三方逐槽比，`DIV-06` 的 `close_when` 不足。
- `ISS-525`：`cfx_power_ctrl`（`cg8 rc1`，WO）写侧三个实现都未实现（写 0 报 `CFXREG`），与"WO、写被接受、读 ⇒ `CFXREG`"不符。

## 要做

1. **`cfx_pmem` 寄存器面**（按 `§4.9`）：`cg8 rc0 pmem_exist`（RO）；`cg12/13/14 rc0–63` start/size/attr（RW）；保留 rc ⇒ `CFXREG`；与 RTL 的取值口径一致（测试机约定 64 区域）。
2. **`cfx_power_ctrl` 写侧**：写被接受（不产生异常）、读 ⇒ `CFXREG`；若 spec 定义了副作用，按 spec 落。
3. **探针/三方**：`tests/arch/pmem/` 与 `tests/arch/power/` 的 QEMU 侧期望同步；核 `DIV-06`/`DIV-13` 的 `close_when` 是否可收窄（不擅自删除）。
4. **不回归**：`check-patch-tree` qemu 段 0 problem、`make_patch.py qemu` 幂等、cfx5/cfx15 代表集。

## 不做

- 不改 RTL/gem5/spec（对齐任务另立）；
- 不改 `cfx_pmem` 的 DMA 语义（ISS-531 已由 spec 任务定义，若要求 fence/invalidate，只在探针里按新口径）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `cg8/12/13/14` 读写、保留 rc ⇒ `CFXREG`；`pmem_exist` RO；
2. `cfx_power_ctrl` 写被接受（不报错）、读 ⇒ `CFXREG`；
3. **可达 FAIL ≥2**：注入"cg12 读回 `CFXREG`"、"power_ctrl 写仍报 CFXREG" ⇒ 红；`cp`+md5 还原并重建回绿；
4. `check-patch-tree` qemu 段 0 problem、`check-component-changelog`、`check-knowledge-refs` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
