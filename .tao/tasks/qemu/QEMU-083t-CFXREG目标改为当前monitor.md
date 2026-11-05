# QEMU-083t: CFXREG 异常目标改为当前 monitor

**模块**：qemu
**项目里程碑**：M11
**依赖**：`SPEC-186t`（DADAO-12 §5.2 定稿：`CFXREG` 统一进当前运行模式 monitor）；本任务只改 QEMU 实现
**状态**：待开始

## 执行环境
本地；只改 QEMU `cfx2rd`/`cfx2rc` 的非法寄存器组合异常目标，不改 spec/测试期望。

## 问题根源

`ISS-342`（open）：QEMU `helper_cfx2rd`/`helper_cfx2rc` 对「rc ≥ scratch_regs_num / 不存在的寄存器组合」调用 `cfx_raise(..., cfxha /*被访问的 cfx*/, ...)`，而不是当前运行模式 monitor。Node 启动链把 `cfx_umon` 的 hypv 向量设为 profile ENTRY，于是这类 fault 会回到测试本体开头（自环，`-d cpu` 恒 PC=ENTRY；`m5_perm_badcombo_cfxreg` 修复前 timeout）。

用户已裁定：**`CFXREG` 统一进当前运行模式 monitor，不进入被访问的 cfx**。

## 目标

1. 在 QEMU 的 `cfx2rd`/`cfx2rc` 非法寄存器组合路径，把异常目标从 `cfxha` 改为**当前运行模式 monitor**（`inner_run_mode` 对应的 `umon/jmon/smon/hmon`），与 `SPEC-186t` 的 §5.2 一致。
2. 不改变合法寄存器组合的正常读写；不改变其它异常（`CFXPERM`/`CFXMEM`/`ILLI`/`CFXESC`）的目标。
3. 源树 base+1 干净；按 `docs/Process-01` 重导出补丁；不改其它组件。
4. 用既有 `tests/arch/umon/m5_perm_badcombo_cfxreg.s` 验证不再自环；测试资产中“body 先自装 umon hypv 向量为 escape stub”的规避可保留，但不得依赖它才能通过。

## 接口规范

- 定位 `components/qemu/patches/target/dadao/helper.c.patch` 中 `helper_cfx2rd`/`helper_cfx2rc` 的非法组合分支；改 `cfx_raise` 的 cfx 参数为当前 monitor。
- 若存在其它“非法寄存器组合”路径（如 `cg/rc` 越界、只读寄存器写），只在语义确实是 `CFXREG` 时同改；逐处给出理由。
- 不改 `CPUState`/`DADAOCPU` 结构、不改寄存器布局、不改异常优先级。
- 重导出补丁，`make apply-series` + `check-source-state` 通过。

## 范围 / 非范围

**在范围内**：`components/qemu/patches/target/dadao/helper.c.patch`（必要时同文件其它 `cfx_raise` 调用）、`components/qemu/changelog.md`、本任务书、`milestones.md`、`ISS-342` 关闭。

**不在范围内**：`spec/**`、`.tao/contracts/**`、`contracts/**`、`components/gem5/**`、`tests/**` 期望值、退出码表、`DADAO-12 §5.2` 正文。

## 验收标准

1. **目标正确**：非法 `cfx2rd`/`cfx2rc` 组合 ⇒ `CFXREG` 进入当前运行模式 monitor；用 QEMU trace/寄存器断言证明目标 cfx 不是被访问 cfx。
2. **合法路径不变**：合法 `cfx2rd`/`cfx2rc` 读写仍正常；既有 inst/arch 不退化。
3. **复现用例**：`m5_perm_badcombo_cfxreg` 在 Node profile 下不再自环/timeout；退出/观察值符合任务书预期。
4. **构建**：`make build-qemu`、`make install-host` rc=0；`check-source-state`/`check-patch-tree` rc=0。
5. **回归**：`make check-arch`、`make check-inst`、`make check`（L1）rc=0；Node 965/970 量级不退化。
6. **反例可达 FAIL**：把目标改回 `cfxha` ⇒ 复现用例 FAIL；`cp`+`md5sum -c` 还原后回绿。
7. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务是 `ISS-342` 的实现侧；`SPEC-186t` 只负责 §5.2 正文。若 `SPEC-186t` 最终把 `CFXREG` 目标写成别的口径，本任务以其为准并留问，不自行改语义。
- 测试资产里的 umon 向量规避是既有 workaround；本任务不改测试资产，但验收要证明实现修复后不依赖它。

## 未决（下发前需确认）

1. `SPEC-186t` 的 `CFXREG` 目标句定稿（当前用户口径：当前 monitor）。
2. 测试资产是否保留 workaround；默认保留，不改 `tests/**`。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
