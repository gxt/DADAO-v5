# m14-linux-005: K1 收口门控 `check-linux-k1`（Vast 端到端）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-003`、`m14-linux-004`
**可并行分片**：否
**预估**：2–3 h
**状态**：待开始

## 用户裁定（2026-11-14，原话）

> 「smon的时候应该就开启了PTBR，能进入start_kernel，开启时钟之前打印信息退出，我觉得K1就算完成」

⇒ K1 的判据 = **Vast 上跑完 `power → hmon → smon → 内核 → start_kernel → （自建表/写 PTBR）→ 打印 → 开时钟前 `SYS_EXIT(0)`**，不作为 K1 判据的部分（init/syscall/中断）不纳入。

## 背景

K0 已有 `make check-linux-k0`（119 项、10 路注入、入 L2，`m14-infra-003`）。K1 需要同规格的收口门控，否则 K0/K1 的边界无法机械判定。

## 范围

1. 新增 `tools/linux/check_k1.py` + `make check-linux-k1`，纳入 **L2**（`_locked-check-modules`），`docs/Process-07` 组合表与 `Makefile` help 同步；
2. 检查项（现场派生，不写死计数）：
   - **端到端**：`bootrom-image`（Vast 固定固件）+ `-kernel <vmlinux>` → guest `rc=0`；
   - **阶段顺序**：`power` → `hmon` → `smon` → 内核入口 → `start_kernel` 标记 → 退出，**顺序正确且各出现 1 次**（用 semihosting 输出/探针记录，不用 `-d` 逐指令日志）；
   - **boot info**：15 字段里至少 `magic/version/size/kernel_base/entry/hart_id` 与构建参数一致；
   - **PTBR**：打印并校验「内核自建表」生效（PTBR 值与 PTE 索引 4096），且切换后仍有输出；
   - **退出点**：`SYS_EXIT(0)` 出现在**任何时钟/中断开启之前**（以输出顺序或探针记录判定）；
   - **反向断言**：不得出现 `panic/CFXMEM` 等异常路径痕迹（若出现 ⇒ FAIL 并列出）。
3. **可达 FAIL 注入 ≥4 路**（`cp`+md5 还原）：① 破坏 boot info magic；② 把 PTBR 指向未映射基址；③ 把退出码改成 1；④ 删 `start_kernel` 标记 ⇒ 各自命中对应断言；
4. 与 `check-linux-k0` 不重复：K0 查"能否交接"，K1 查"内核跑起来并退出"。

## 验收（逐条贴真实 rc）

1. `make check-linux-k1` **rc=0**；检查项计数现场打印；
2. 4 路注入逐条「注入→红→还原→绿」，还原后 md5 与注入前一致；
3. `make check-linux-k0` 仍 rc=0（K0 不回归）；`make check-modules` **不跑**（共享安装根）——按模块单独跑 `check-linux-k1`；
4. `docs/Process-07` 的 L2 组成表含新目标；`Makefile` help 有对应行；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；禁 `install-host`/`check-modules`；`build-linux` 用 `JOBS=32`；禁边构建边测试。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `tools/linux/**`、`Makefile`（目标 + L2 接线）、`docs/Process-07`、任务书；**不改** `spec/`、`contracts/`、`components/**`。
5. 只在 `qemu-system vast` 上验收；Vast 固件/镜像用共享产物，不重建 QEMU。

## 待裁定

（实现中写）

## 审阅记录

（待填）
