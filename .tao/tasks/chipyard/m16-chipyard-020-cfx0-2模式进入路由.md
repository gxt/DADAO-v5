# m16-chipyard-020: RTL cfx0/2 模式进入路由（B）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-019`（A：cfx0/2 寄存器面与权限）合入
**可并行分片**：否
**预估**：6–8 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定：先 A 再做 B）

`m16-chipyard-019` 只补了 cfx0/2 的寄存器面与权限。RTL 的同步异常仍**固定进 hmon**（`WumingParams.scala.patch:154` 的 `monitor = 0`），没有“U-mode → cfx0”“S-mode → cfx2”的路由，也没有 user/supv 模式下的 `switch_run_mode`、异常帧与向量。本任务补这条主控制流。

## 要做

1. **模式进入路由**：按 `DADAO-12 §5.2` 与 `contract-see`：
   - U-mode 同步异常 → cfx0 umon；
   - S-mode 同步异常 → cfx2 smon；
   - H-mode 仍 → cfx3 hmon（现有）。
2. **`switch_run_mode`**：从 user/supv 陷入时按 `<mode>_switch_run_mode` 切换运行模式；与 `trap`/`escape` 的目标 cfx 组合对齐。
3. **异常帧**：`inner_run_mode`、`inner_excp_cause_*`、`inner_excp_ip`、`prev_cfx` 等按 `§5.2` 保存/恢复；`escape` 恢复语义与 QEMU/gem5 一致。
4. **异步中断**：单 hart 的 timer/pmem 中断按当前模式进入对应 monitor（与 M16 的中断源范围一致；不含 UART/IPI/多核）。
5. **用例**：U-mode/S-mode 同步异常进入、帧字段、`switch_run_mode`、`trap`/`escape` 三方（QEMU/gem5/RTL）签名一致。

6. **HSU（运行模式）**（用户 2026-11-22：HSU 纳入、J 不纳入）：U/S/H 三种模式的进入与权限检查；J-mode 不测，写入未覆盖项。

7. **三方用例（B）**：cfx0/2 的 case 定义/期望只写一份；RTL 探针与 QEMU/gem5 后端复用同一 case（非必要不为每个平台写三份载体），由 `check-arch-vast` 按需跑三方。

**H/S/U 三模式**（用户 2026-11-22）：本任务本身就是把 U/S 路由做稳；验收必须覆盖 `hmon`/`smon`/`umon` 三种模式下的异常进入、`switch_run_mode`、异常帧，不能只验 hypv/hmon。

**两轴 `cfxreg` 强制判定**（承接 019 遗留①）：019 只落存储面与 `readOk/writeOk` 行判；本任务必须补上 `CFXPERM` 强制——U/S 下访问 cfx0/2 时按目标 cfx 的 `<mode>_cfxreg` 掩码 + `cg3 rc12` deleg 判权；未写 deleg/未开放掩码 ⇒ `CFXPERM|NCFXPERM`。与 `m16-testcases-017` 的 env 掩码准备配合，不能留成两任务互指的空档。

## 不做

- 不改 cfx0/2 的寄存器行/权限（019）；
- 不改 cfx3/4/5 的既有语义；
- 不加多核/IPI/UART/J-mode。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 改 `WumingCore` 主控制流，必须逐步验证；重建每次约 30 分钟，证据脚本记录耗时与环境；
- 术语「寄存器组」；不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. U-mode 同步异常进入 cfx0、S-mode 进入 cfx2、H-mode 仍进 cfx3；帧字段（cause/info/ip/prev_cfx/run_mode）逐项；
2. `switch_run_mode` 与 `trap`/`escape` 组合；异常返回后状态正确；
3. 单 hart timer/pmem 中断进入对应 monitor；
4. 三方同一 ELF 签名逐槽一致；不一致登记 `expected-divergences.yaml`；
5. **可达 FAIL**：注入「U-mode 仍进 hmon」⇒ 用例红；注入「switch_run_mode 不生效」⇒ 红；`cp`+md5 还原并强制重建后回绿；
6. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
