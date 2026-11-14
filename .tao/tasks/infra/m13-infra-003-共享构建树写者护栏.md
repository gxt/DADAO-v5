# m13-infra-003: 共享构建树/安装根的写者护栏（`ISS-373`）

**模块**：infra
**项目里程碑**：M13
**依赖**：无
**可并行分片**：否（改共享门控与构建脚本）
**预估**：5–7 h
**状态**：待开始

## 背景（`ISS-373`，P1；2026-11-14 再次复现 3 次）

多个任务并行时共用 `.work/build/**`、`.work/source/**` 与 `.dadao/cross-toolchain/**`（安装根）：

- `m16-gem5-008` 重建 `gem5.opt` 期间，`m13-testcases-024`/`035`/`chipyard-001` 的复核读到**0 字节/半截/被替换**的 `gem5.opt` ⇒ 假红；还原/重试后才判明是环境；
- 反之也会**假绿**：读到的二进制若与提交不一致，跑批通过不能证明当前源码正确（`m16-gem5-008` 自己就要求"钉住完成版 md5"）。
- 现有 `gate.lock`（`docs/Process-07 §2`）只串行化**同一 make 树内的门控目标**；它**不阻止**并行会话的 `build-*`/`install-host` 写同一树，也**不告诉读方**"这个二进制正在被替换"。

## 目标

1. **写者身份 + 时段可见**：`build-*`/`install-host`/`install-cfx-aliases` 等写目标在开始时把 `{target, pid, host, start, duration, git-head}` 写入共享状态文件（如 `.dadao/writers/<component>.json`），结束时清除；异常退出由下次启动检测并清理 stale 记录。
2. **读方 fail-closed**：
   - `run_asm_suite.py`、`tools/testcases/**`、`tools/gem5/**`、`tools/qemu/**`、`tools/linux/**` 的**证据/跑批**入口，在启动与结束各记录一次所用二进制的 md5；**结束 md5 ≠ 启动 md5 ⇒ FAIL（"二进制在跑批期间被替换"）**，而不是静默用新二进制。
   - 若启动时该组件有活跃写者记录 ⇒ 默认**拒绝启动**并提示等待；`--allow-concurrent` 显式覆盖（记录到日志）。
3. **门控**：新增 `make check-writer-guards`（L1），用临时树自测：① 写者记录存在时读入口拒绝；② 跑批期间替换二进制 ⇒ FAIL；③ stale 记录可清理；④ 正常路径不误伤（≥1 路注入 + 还原）。

## 验收

1. 上面 4 类自测全绿（每类都有真实"注入 → FAIL → 还原 → 回绿"）。
2. 在**两个并发会话**下实测：会话 A 跑 `build-gem5`，会话 B 启动跑批 ⇒ B 被拒（或明确告警并记录）；A 结束后 B 正常启动。
3. 不改变现有 `gate.lock` 语义（嵌套放行仍成立）；`make check`/`check-modules` 全绿。
4. 文档：`docs/Process-07` 增一节「共享构建树/安装根的写者护栏」，写清状态文件位置、stale 判定、`--allow-concurrent` 的使用边界。
5. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**不要跑 `install-host`**（本任务只加护栏，不需要装）；`build-*` 仅在自测临时树里用最小目标。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `tools/infra/**`、`tools/testcases/inst/run_asm_suite.py`、`docs/Process-07`、`Makefile`（仅新增门控目标与该目标进 L1 的接线）；**不改** `spec/`、`contracts/`、组件源码。
5. 大文件落 `/tmp/opencode/m13-infra-003/` 并测完即删。

## 待裁定

（实现中写）

## 审阅记录

（待填）
