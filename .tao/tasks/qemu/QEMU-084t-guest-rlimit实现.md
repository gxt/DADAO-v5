# QEMU-084t: QEMU user-mode guest rlimit 实现（ISS-343）

**模块**：qemu
**项目里程碑**：M11（P3；2026-11-06 用户裁定插在 M11 终验之前做，见「用户裁定」）
**依赖**：`TESTCASES-099t`（已验证；诊断与最小探针）
**状态**：待开始

## 用户裁定（2026-11-06）

> 「A：M11 终验前做（推荐）」——即 `INTEG-057t` 合并后立刻派本任务，做完再统一跑 L2/L3/夜跑与 M11 `m` 册，终验只跑一遍。

原任务书把它标为「M11 后/P3」是 architect 的归类错误：P3 是优先级，不等于里程碑归属；按 2026-11-05 的 4A「小项现在清」它本就属于本轮。本任务因此纳入 M11 期：改的是 L3/夜跑直接依赖的 QEMU，先改后验可避免「绿报告对应旧二进制」。

## 执行环境
本地；只改 QEMU user-mode 的 guest rlimit 记账，不改 spec。

## 背景

`ISS-343`：QEMU user-mode 对 guest `RLIMIT_AS/DATA/STACK` 是 no-op：

- guest `setrlimit(RLIMIT_DATA,0)` 返回成功
- `getrlimit` 仍返回 `RLIM_INFINITY`
- guest `mmap`/`brk` 不受限
- 与原生 Linux 不一致

`TESTCASES-099t` 最小探针已证明；根因在 `linux-user` 的 `setrlimit/prlimit64` 与 `do_brk()`/`target_mmap()` 未按 guest rlimit 记账。

## 目标

1. 实现 guest `RLIMIT_AS`/`RLIMIT_DATA`/`RLIMIT_STACK` 的记账：
   - guest `mmap`/`brk` 超过限制 ⇒ `ENOMEM`；
   - `getrlimit` 返回 guest 设置值；
   - 不改变 `RLIMIT_NOFILE`/`RLIMIT_CORE` 等既有语义。
2. 用 `TESTCASES-099t` 的最小探针验证：`RLIMIT_DATA=0` 后 RW mmap/brk 失败。
3. 不改变 Node/Tiny 正常路径；跑 QEMU user/system 代表测试。

## 验收标准

1. 最小探针：guest `setrlimit(RLIMIT_DATA,0)` 后 `getrlimit=0`、RW `mmap`/`brk` = `ENOMEM`。
2. 不设置 rlimit 时行为不变；Node/Tiny 测试不退化。
3. `make build-qemu`/`install-host`/`check-source-state`/`check-patch-tree`、L1 rc=0。
4. 反例：恢复 no-op ⇒ 探针 FAIL；还原回绿。
5. 完成区 ≤30 行；状态 `待验收`。

## 范围 / 非范围

**在范围内**：`components/qemu/patches/linux-user/{syscall.c,mmap.c,elfload.c}`（按现场）、`components/qemu/changelog.md`、`tools/qemu/user_mode_smoke.py`（新增 guest rlimit 探针用例，见「探针落点」）、本任务书、`milestones.md`、`ISS-343` 关闭。

**不在范围**：spec/contracts、gem5、tests 期望、其它 QEMU 语义。

## 探针落点

回归探针**入库**，不留在运行期临时目录：加进 `tools/qemu/user_mode_smoke.py`（QEMU 测试驱动，QEMU-081t 先例），沿用其 `compile_program`/`link_static` 与独立 oracle 风格。

探针至少断言：

1. `setrlimit(RLIMIT_DATA, 0)` 成功后 `getrlimit(RLIMIT_DATA)` 的 `rlim_cur == 0`；
2. 该状态下一次 RW `mmap`（一页 64 KiB 以上）返回 `-ENOMEM`；
3. 同位探针在**未设置** rlimit 时 `mmap` 成功（防「一律失败」假绿）；
4. 同上对 `RLIMIT_AS` 各一组。

补充判据须来自独立 oracle（原生 Linux 行为/契约），不读 QEMU 内部日志。

## 已知坑（来自 `TESTCASES-099t` 诊断，避免重复踩）

- musl DADAO 端口的公共 `brk()` 恒返回 `-ENOMEM`（`src/linux/brk.c`），**不能**用它判断 rlimit 记账；
- 公共 `syscall(SYS_brk, …)` 在该端口经 `va_arg` 传参异常（另见诊断记录），探针勿用；
- `mallocng` 走 `__syscall` 不受上述影响，可用 `malloc` 复核；
- 64 KiB 页：探针按页大小 65536 计算，不要写 4096。

## 说明

- 这是 P3 能力缺口；2026-11-06 用户裁定 A 插入 M11 终验之前，故属于 M11 期。
- 若实现需要跨平台通用改动，先做 DADAO target 最小路径，再评估通用化。
- 不把 no-op 写成“已支持”。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
