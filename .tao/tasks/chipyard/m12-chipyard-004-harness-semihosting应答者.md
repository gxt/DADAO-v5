# m12-chipyard-004: harness 侧 semihosting 应答者（最小 5 服务）

**模块**：chipyard
**项目里程碑**：M12
**可并行分片**：否（单次 Verilator 构建 + 单次运行，不可拆）
**状态**：待开始
**依赖**：`m12-chipyard-003`（BootROM + loadmem 闭环）

## 背景与已定方案

- semihosting 是 FS/SE 共用、profile 无关的机制：guest 执行 `trap <any cfxha>, 0x3FF00+op`（判定只看 `immu18[17:8]`），由宿主完成 I/O 并把结果写回 `rd8`（`spec/Machine-v5 §5`）。
- **用户裁定**：应答者放 **harness 侧 C++**，与 QEMU `semihosting/arm-compat-semi.c`、gem5 `src/arch/dadao/semihosting.cc` 同层；**核内不实现宿主 I/O**。
- **M12 不考虑 fesvr/pk**；Tiny 阶段不涉及 syscall。

## 目标

1. **核内「抬到边界」**：命中 semihosting tag 时，把 `(op, 参数寄存器值/指针, 返回寄存器号)` 通过一个可观测通道（DPI 导出端口或预留 MMIO，二选一并写明理由）交给 harness；**核不做任何宿主调用**。
2. **harness 侧应答者**（C++，table-driven）：
   - 最小服务：`SYS_WRITEC(0x03)` / `SYS_WRITE0(0x04)` / `SYS_WRITE(0x05)` / `SYS_EXIT(0x18)` / `SYS_CLOCK(0x10)`
   - 语义严格按 `spec/Machine-v5 §5.3` 表；返回 `rd8`；`SYS_EXIT` 触发有界停机（不依赖 TestDriver 超时）
   - 未实现的服务号 ⇒ 明确报错（不静默当 0）
3. **三平台一致**：同一 ELF 在 QEMU `dadao-tiny`、gem5 FS Tiny、chipyard 的 stdout 与退出码一致（判据 = 与 qemu/gem5 一致，不用独立 oracle）。
4. 文档：`components/chipyard/README.md` 记录通道形态、服务集、未实现语义。

## 验收标准

1. `SYS_WRITE0` 输出在 harness stdout 逐字节正确（含中文/长字符串不截断）
2. `SYS_EXIT` 退出码映射到宿主退出码（按 `spec §7.1` 的 guest 段 `0x00–0x3F` = PASS）
3. `SYS_CLOCK` 返回单调递增、单位与 `spec` 一致
4. 未实现服务号（如 `SYS_OPEN`）⇒ 明确报错并给出服务号，不静默
5. 同一 ELF 三平台 stdout + 退出码一致
6. Verilator 构建 rc=0（`server207`）；`make apply-series` / `check-source-state` / `check-patch-tree` / L1 / L2 rc=0
7. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 非范围

- 完整 25 服务（后续任务按需补）
- fesvr/pk、TSI（不在 M12）
- 核内部指令实现（`005` 起）

## 说明

- 通道形态（DPI 端口 vs MMIO）会影响后续核实现，**必须在任务书完成区给出选择理由**；若发现与 `003` 的启动路径冲突，停下报告。
- 构建/运行在 `server207`；仓库修改在主控机。
