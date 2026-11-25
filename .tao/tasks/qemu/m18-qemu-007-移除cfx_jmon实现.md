# m18-qemu-007: QEMU system 移除 `cfx_jmon`（cfx1）实现

**模块**：qemu
**项目里程碑**：M18
**依赖**：`m18-spec-007`（定义异步 escape）+ 内核改用异步 escape 的任务（待立）；本任务**不得**在其之前合入，否则 K2/K6 立刻红
**可并行分片**：否（同 `components/qemu` 写者）
**预估**：2–3 h（标定：同档 QEMU 单点寄存器/cfx 面任务取 2–3 h；含探针与 profile 断言调整）
**档位**：中改（QEMU cfx 集合）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景（用户 2026-11-25 裁定）

`cfx_jmon`（cfxha 1）在 spec 里只有一句「处理 jail 模式下的同步异常」，**没有设计**（无 cg/rc 面定义、无 jailed 模式语义、无 SBI 入口实现），RTL 也未实现（`WumingParams` 的 cfx 表无 cfx1）。QEMU system 却把它放进 `DADAO_CFX_IMPL_VAST`（`1<<1`）、登记进 `dadao_cfxha_map`、并在 `helper.c` 的 cg7 空间表里给 `umon/jmon/ptw` 记 16 个空块 —— 这是**超出设计范围的实现**，会诱使软件把 jmon 当可用 monitor（`m18-linux-024` 的内核返程帧就是这么用的）。

用户裁定：**QEMU system 不应实现 cfx_jmon**；内核的返程帧另选（见另一任务）。

## 目标

1. 从 QEMU system 的已实现 cfx 集合中移除 cfx1：`DADAO_CFX_IMPL_VAST` 去掉 `1<<1`；`dadao_cfxha_map`/`DADAO_NUM_CFX` 与 `helper.c` 的 cg7 空间表同步；Tiny 本就不含 cfx1，保持。
2. 语义：移除后按 profile 既有规则处理 —— 未实现 cfx 的 `trap` ⇒ `CFXREG`（Vast）或 `ILLI`（Tiny 的 `unimpl_cfx_trap_illi`），**不得**静默零值或落到别的 monitor；寄存器访问同规则。
3. 清理引用：QEMU 源码/注释里「jmon 已实现」「umon/jmon/ptw 16 blocks」等表述；`tests/arch` 里若有依赖 jmon 存在的断言（README 已声明 cfx1 不在 arch 范围），改为「cfx1 未实现 ⇒ CFXREG」。
4. 与 RTL/gem5 口径对齐：RTL 无 cfx1；gem5 的 J 模式映射若要保留，仅作注释/未实现，不得因此认为 cfx1 可用。

## 验收（逐条贴真实 rc）

1. QEMU 补丁按 `docs/Process-01` 重导；`check-patch-tree` qemu 段 0 problem；`make build-qemu`/`install-qemu` rc=0。
2. 探针：`trap cfx1, 0` ⇒ `CFXREG`（Vast）；读/写 cfx1 的 cg/rc ⇒ `CFXREG`；`trap cfx0/2/3` 行为不变（umon/smon/hmon 仍有 cg5）。
3. **可达 FAIL ≥2 路**：① 把 `1<<1` 加回 ⇒ 上述 `CFXREG` 断言红；② 只删掩码不删 `cfxha_map` ⇒ 数组下标/CFXREG 判定红；`cp`+md5 还原并重建回绿。
4. 不回归：`check-qemu-forms`、`check-cfx-alias-install`（若涉及）、`check-qemu` 代表集、Tiny 基线；`check-component-changelog` rc=0。
5. 联动：与内核切换任务同批验收时，`check-linux-k2`/`k6` 必须绿（见依赖；若内核尚未切换，本任务只做 QEMU 侧证据并标 BLOCKED，不宣称收口）。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/qemu/patches/target/dadao/**`、`components/qemu/changelog.md`、`tests/arch/**`（仅 cfx1 相关断言）、本任务书；不改 spec/契约/Makefile/内核/RTL/gem5。
3. 不改版本号；术语「bank = 寄存器组」；还原 `cp`+md5。
4. **顺序**：必须在内核不再 `trap cfx_jmon` 之后合入；违反会让 K2/K6 立刻 `CFXREG` 红。
5. 清理 QEMU 共享源树时按 `docs/Process-01` 全量重放，避免留下旧 cfx1 代码。

## 待裁定

1. 用户在 2026-11-25 裁定「定义异步 escape」，本任务等待 `m18-spec-007` 与内核换帧任务落地；不采用 hmon/hart cg5/kmon 方案。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
