# m16-chipyard-031: RTL `cfx_power_ctrl` 写侧（写接受 + §4.12 副作用）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-027`（power common face）、`m16-qemu-006`/`m16-gem5-025`（同口径）
**可并行分片**：否（`components/chipyard` / `tests/arch/power`）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（`ISS-525` 的 RTL 部分）

`DADAO-12 §4.12`：`cfx_power_ctrl`（`cg8 rc1`）为 **WO**——写被接受，`bit0` 关机（POWEROFF）、`bit1` 硬复位（HARD_RESET）、`bit2` 软复位（SOFT_RESET）；读 ⇒ `CFXREG`。QEMU（`m16-qemu-006`：`exitSimLoopNow` 等）与 gem5（`m16-gem5-025`：`DADAO_POWER_*` guest exit）已实现；**RTL 仍无写分支，写 0 报 `CFXREG`**（`m16-testcases-016` 诊断项）。

## 要做

1. **写侧**：`cfx_power cg8 rc1` 写被接受（不报异常/`CFXREG`）；`bit0/1/2` 按 `§4.12` 落动作——按测试机约定：**结束仿真**（Verilator `$finish`/harness 退出）并由 harness 决定是否重启；`bit1/2` 若无法区分，写明"复位 = 结束 + harness 重启"（与 gem5 同口径）；写 0 无动作；其余位忽略。
2. **读侧**：保持 `CFXREG`。
3. **探针**：`tests/arch/power/` 的 RTL 面（`check_power_rtl.py`）加"写 0 被接受 + 读 `CFXREG`"与"写 bit0 ⇒ 仿真结束"两例（与 QEMU/gem5 的 `poweroff.S` 同场景）；`arch-power-001` 若因此可纳入写侧判据，按三方逐槽。
4. **登记**：`ISS-525` 收窄/关闭（RTL 补齐后）；`tests/arch/README.md` 未覆盖项同步。
5. **不回归**：`arch-power-001/002`、cfx15/pmem/time/cache/ptw 代表集、Tiny。

## 不做

- 不改 spec/契约；
- 不做真实板级断电（仿真内结束即可）；
- 不做 `cfx_power` 的其它寄存器。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出、`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. 写 0/bit0 行为（接受/结束仿真）与读 `CFXREG`；`arch-power-001` 三方（QEMU/gem5/RTL，写侧若纳入）逐槽；
2. **可达 FAIL ≥2**：注入"写仍报 CFXREG"、"bit0 不结束仿真" ⇒ 红；`cp`+md5 还原并重建回绿；
3. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、`check-component-changelog`/`check-tests-index`/`check-tasks`/`run_arch --self-test` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
