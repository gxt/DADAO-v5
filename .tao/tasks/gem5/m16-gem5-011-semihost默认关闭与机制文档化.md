# m16-gem5-011: semihosting 默认关闭（与 ARM/RISC-V 一致）+ 调用机制与安全边界文档化

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-007`（semihosting 开关，已验证）、`m16-chipyard-001`（已收尾）
**可并行分片**：否（`components/gem5` 单写者）
**预估**：1–1.5 h
**档位**：小改（一处默认值 + 两份文档；复核 diff + 1 路注入 + 受影响门控）
**状态**：待开始

## 背景（用户 2026-11-17 裁定）

> 用户：「默认关闭没问题，关键是怎么调用宿主机功能」——即采「接受 `--semihost` 开关 + **默认 `off`**、显式开启」，与 gem5 上游 ARM（`--semi-enable`）/ RISC-V（`--semihosting`）一致。

现状：

- `configs/dadao/se_timing.py`：`--semihost` 默认 **`off`**（与上游一致）。
- `configs/dadao/fs.py`：默认 **`on`**（不一致，需统一为 `off`）。
- 调用方（`tools/gem5/compare_chipyard.py`、`tools/testcases/parity/qemu_gem5_shim.py`）均**显式**传 `--semihost on` ⇒ 改默认值无回归。
- `components/gem5/README.md` / `changelog.md` 未写「触发机制 + 服务表 + 宿主边界」。

## 目标

1. **默认值统一**：把 `fs.py` 的 `--semihost` 默认 `on` → **`off`**。按 `docs/Process-01` 的组件流程：改**源树** `configs/dadao/fs.py`（`.work/source/gem5`）→ `python3 tools/gem5/make_patch.py gem5` 重导补丁 → 确认 `make_patch` 幂等。
2. **文档化调用机制**（写进 `components/gem5/README.md` 与 `changelog.md` 的对应条目，不新建文件）：
   - **触发**：guest 执行 `trap <任意 cfxha>, 0x3FFxx`（`immu18[17:8] == 0x3FF`）；gem5 在 cfx/向量处理**之前**短路，QEMU 同口径；`--semihost off` 或无 responder 时该 trap 行为不变。
   - **传参**：服务号 `rd16`、参数块指针 `rb16`、标量返回 `rd8`、64 位**大端**（`contract-semihosting §2`）。
   - **服务表**：`BaseSemihosting` 的 24 个 generic 服务 + `SYS_SYNCCACHE`（0x19）；适配器只提供 `State/Result`（寄存器/大端/`TranslatingPortProxy`）。
   - **宿主边界**：console → 宿主 stdout（`--console-out`）；文件 → `files_root_dir`；时间 → 宿主时钟；`SYS_SYSTEM` 默认 `deny`（`--semihost-system native` 才允许）。
   - **默认关**：`se_timing.py`/`fs.py` 均 `off`，需显式 `--semihost on`。
3. 不改 C++、不重建 `gem5.opt`（仅 Python 配置与文档）。

## 验收（逐条贴真实 rc）

1. `grep -n '"--semihost"' .work/source/gem5/configs/dadao/fs.py` 默认值 = `off`；`se_timing.py` 仍 `off`。
2. `make_patch gem5` 幂等（二次 `0 written`）；`check-patch-tree` gem5 段 **0 problem**；`--source-state` gem5 OK；`check-component-changelog` rc=0。
3. `check-gem5-decode` rc=0。
4. **1 路注入**（`cp`+md5 还原）：把 `fs.py` 默认改回 `on` ⇒ 验收 1 的断言必须红。
5. README/changelog 的机制段五项齐全（触发/传参/服务表/宿主边界/默认关），逐项可 `grep` 命中。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. **不改任何版本号**（版本号升级须用户认可，见 `AGENTS.md` 核心原则）。
3. 只动：`components/gem5/patches/configs/dadao/fs.py.patch`（重导产物）、`components/gem5/README.md`、`components/gem5/changelog.md`、源树 `configs/dadao/fs.py`、本任务书。
4. 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore/stash/show`、禁 `reset --hard`）。

## 待裁定

（无）

## 审阅记录

（待填）
