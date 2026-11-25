# m16-gem5-025: gem5 cfx_pmem 寄存器面 + cfx_power_ctrl 写侧

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-qemu-006` 合入（同口径）；`m16-chipyard-022`（RTL 面基准）
**可并行分片**：否（同改 `components/gem5`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

与 `m16-qemu-006` 同源：`ISS-533`（gem5 的 `cfx_pmem` 只实现 `cg15`（+`cg7`），`cg8/12/13/14` ⇒ `CFXREG`）与 `ISS-525`（`cfx_power_ctrl` WO 写侧未实现）。

## 要做

1. **`cfx_pmem` 寄存器面**（按 `§4.9`）：`pmem_exist`（RO）、`cg12/13/14 rc0–63`（RW）、保留 rc ⇒ `CFXREG`；取值口径与 QEMU/RTL 一致。
2. **`cfx_power_ctrl` 写侧**：写被接受（不产生异常）、读 ⇒ `CFXREG`。
3. **探针/三方**：`tests/arch/pmem/`、`tests/arch/power/` 的 gem5 侧期望同步；核 `DIV-06`/`DIV-13` 的 `close_when` 收窄。
4. **不回归**：cfx5/cfx15/time 代表集、gem5 自身回归（`check-patch-tree` gem5 段 0 problem）。

5. **`cg9 rc6` 对齐 spec-006（`DIV-18` gem5 部分）**：`cfx_hart cg9 rc6` 改为 RW、复位 2、**异步进入取该值**（当前 gem5 写忽略、恒 2）；`arch-hart-001` 的 rc6 断言与 QEMU/RTL 同场景。
6. **Tiny 的旧掩码面（`ISS-m16-009`）**：`cg0–cg3 rc4` 与 trap/escape 保存恢复掩码在 gem5 Tiny 上仍在（QEMU/RTL/Node 已统一 `CFXREG`）；按 `tests/unit/gem5/tiny_hmon` 的依赖决定「改 Tiny 行为 + 改该测试」还是登记 Tiny 差异，二者择一并写明。

## 不做

- 不改 RTL/QEMU/spec；
- 不改 DMA 语义（按 `m16-spec-003`）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `cg8/12/13/14` 读写、保留 rc ⇒ `CFXREG`；`pmem_exist` RO；
2. `cfx_power_ctrl` 写被接受、读 ⇒ `CFXREG`；
3. **可达 FAIL ≥2**：注入"cg12 读回 `CFXREG`"、"power_ctrl 写报错" ⇒ 红；`cp`+md5 还原并重建回绿；
4. `check-patch-tree` gem5 段 0 problem、`check-component-changelog`、`check-knowledge-refs` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
