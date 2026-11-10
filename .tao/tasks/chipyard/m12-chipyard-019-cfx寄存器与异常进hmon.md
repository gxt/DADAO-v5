# m12-chipyard-019: `cfx_power` / `cfx3` 寄存器组 + 同步异常进 hmon

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-007`（BootROM 固件 + power 搬运 + 最小 hmon 已通）、`m12-chipyard-018`（双端口/骨架）
**可并行分片**：否（单核实现，单写者）
**状态**：待开始

## 用户裁定（2026-11-10）

- Tiny **恒 `hypv`**：异常进入强制 `hypv`；**`switch_run_mode` 写入被忽略、保存值保持 3、读回保存值**
- **`cg3` 仅 `hypv` 可访问**：其它模式访问 ⇒ `CFXREG`
- **`cg3 rc10`（`excp_vector`）**：初值 = 该 cfx 内部 SRAM 起始；写入**忽略低 2 位**（按 4 字节对齐落盘），不报错
- **同步异常直接进 hmon 向量**（不经 `trap` 指令）；`trap` 的 semihosting 判定只看 `immu18 ∈ 0x3FF00–0x3FFFF`
- **IALIGN：IP 停留非法地址**，`excp_cause_ip` = 该地址，触发指令的正常写回照常完成
- **R15 = B**（无嵌套上限）、**R16 = B**（无硬件 `halted` 兜底）
- **`escape`**：目标 cfx 恒为当前 cfx；偏移只 0 / +4

## 目标

1. **cfx 寄存器组**：`cfx_power`（cfx63）与 `cfx3 hmon` 的 cg0–cg8 必要寄存器（`excp_cause_id/ip/info`、`excp_vector`、四类同步 mask、`cfx_intr_mask`、`switch_run_mode`、`cg7` 空间块、`cg8 rc1` ⇒ `CFXREG`）。
2. **异常进入**：五类同步异常（`CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN`）写 `excp_cause_*` 并跳向量；`escape` 返回（0/+4）。
3. **`cg3` 权限**：非 `hypv` 访问 ⇒ `CFXREG`。
4. **`rc10` 语义**：初值 = hmon SRAM 起始；写入忽略低 2 位。
5. **Tiny 恒 `hypv`**：`switch_run_mode` 读回 3。

## 非范围

- BootROM 固件/power 搬运/hmon handler 主体（`007`）
- 双端口/取指缓冲（`018`）
- 访存指令语义（`008`）、FP（`011`–`015`）
- QEMU/gem5 侧对齐（M13 任务）

## 验收标准

1. 五类同步异常**各 ≥3 例**进 hmon 向量，`excp_cause_id`（one-hot）/`ip`/`info` 正确
2. **IALIGN 专门断言**：`ip` 停在非法地址、`cause_ip` = 非法地址、触发指令写回完成
3. `cg3` 在非 `hypv` 模式访问 ⇒ `CFXREG`（用例 + 反例）
4. `rc10` 写入未对齐值 ⇒ 落盘为对齐值（低 2 位清零），读回一致
5. `switch_run_mode` 写 0 后读回 3、运行模式仍 `hypv`
6. `escape` 的 0 与 +4 两路各有用例
7. 273 例零回归 + Tiny 44/44
8. Verilator 构建 rc=0（主控机）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
9. 一键证据脚本（含可达 FAIL 注入）
10. 完成区 ≤30 行、无运行期路径

## 说明

- 构建/调试在主控机；不占用 207/208。
- 组件单写者；补丁走 `make_patch` 导出。
- 与 `Machine-v5 §4.4` 的 `excp_cause` 表逐条对齐；发现冲突停下登记。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
