# m14-infra-003: K0 收口门控 `make check-linux-k0`

**模块**：infra
**项目里程碑**：M14
**依赖**：`m14-linux-001`、`m14-linux-002`、`m14-spec-001`、`m14-spec-002`、`m14-infra-001`、`m14-infra-002`（K0 全批）
**可并行分片**：否（收口门控，需全批产物）
**预估**：4–5 h
**状态**：待开始

## 背景

K0 各任务各自有局部验收，但缺一个**跨产物**的收口门控：vmlinux 是否真按契约链接、initramfs 是否真可复现且含 `/init`、工具链矩阵与启动契约投影是否仍绿、补丁集是否可重建且幂等。本任务把这些收敛为 `make check-linux-k0`，并纳入 **L2**（`make check-modules`）。

本任务也是本批**唯一**允许再次改 `Makefile` 的任务：把 `check-linux-toolchain`、`check-linux-boot-contract` 接入 L1，把 `check-linux-k0` 接入 L2（目标名与 `_locked-*` 规则已由 `m14-linux-001` 声明）。

## 目标

1. `tools/linux/check_k0.py`（目标 `make check-linux-k0`）：读取契约投影与矩阵，逐项断言下列产物；**缺产物/未构建 ⇒ 明确 FAIL**（给 `make linux-*` 命令），不得 SKIP。
2. `Makefile` 接线：`check-linux-toolchain`、`check-linux-boot-contract` 进 L1 `_locked-check`；`check-linux-k0` 进 L2 `check-modules`；`check-linux-k0` 已是写者目标（会增量构建），锁状态复核。
3. `docs/Process-07 §1.1` 登记三条（两条 L1 + 一条 L2，判据可机械判）。
4. `--inject` 自检：对每类产物做临时副本注入，逐项 FAIL；还原后回绿。
5. 耗时测量：打印各项耗时；若增量耗时超 L2 预算（`docs/Process-07 §3`），完成区登记实测值并给建议（**不擅自改层**）。

## 断言清单（每条必须有可达 FAIL）

| # | 断言 | 期望来源（不写死第二份） |
|---|---|---|
| K1 | `vmlinux` 存在且可解析 | 构建目标 `make linux-vmlinux` |
| K2 | ELF64、大端、`e_machine = 0x0DA0`、`ET_EXEC` | `contract-linux-boot` / `contracts/linux-boot.yaml` |
| K3 | `e_entry = 0x0010_0000` | 同上（`kernel.entry`） |
| K4 | 仅允许的段类型；每个 `PT_LOAD` `p_vaddr == p_paddr`、`p_vaddr % 0x10000 == 0`、`p_align >= 0x10000`、区间 ⊆ `[kernel.base, initramfs.base)` | 同上 |
| K5 | 无段与 `[0, 0x2_0000)`、BootROM、hmon SRAM 重叠 | 同上（`reserved` 区） |
| K6 | `llvm-nm -u vmlinux` 为空 | 链接完整性 |
| K7 | initramfs 存在、`newc` 可解析、含 `.` + `init`（0755）+ `TRAILER!!!`、`init` 内容 sha = 构建 ELF | `make linux-initramfs` + `paths.linux_initramfs_manifest()` |
| K8 | initramfs 二次生成 sha256 相同（可复现） | 生成器两次运行（临时目录） |
| K9 | initramfs `size ≤ 32 MiB`；`init` ELF 为静态（无 `PT_INTERP`/`DT_NEEDED`） | 投影 + `contract-linux-boot` |
| K10 | `make check-linux-toolchain` 逻辑 rc=0（直接调 `tools/linux/check_toolchain.py`，避免递归 make） | `m14-infra-001` 矩阵 |
| K11 | `make check-linux-boot-contract` 逻辑 rc=0（直接调脚本） | `m14-spec-001` 投影 |
| K12 | `apply-series` 幂等：连续两次 rc=0，linux 源树 `HEAD` 前后相同、clean；直接对 linux 源树核 `git status --porcelain` 为空且 `rev-list --count <base>..HEAD` = 期望值（空/非空补丁集现场判定；不依赖全局 `check-source-state`，避免其它组件在途噪声）；两次运行**只作用于 linux**（`apply_series.py --component linux`） | `docs/Process-01` + `components/linux/series` + `paths.linux_source_dir()` |
| K13 | 补丁数/段数/条目数**现场统计**并与完成区一致（不写死） | 产物解析 |

## 接口规范

- **产物定位**：一律经 `tools/linux/paths.py`（`m14-linux-001`）从 `manifests/` 解析，**不得**在脚本/任务书写宿主绝对路径或具体 `.work/**`。
- **增量构建**：`check-linux-k0` 作为 make 目标可依赖 `linux-vmlinux`/`linux-initramfs`（或脚本内显式调用对应目标），保证从「已 fetch + 已 install-host」的树可自举；构建失败 ⇒ 门控 FAIL 且不再继续后续断言（fail-closed）。
- **超时**：内核构建/`apply-series` 设明确超时；`timeout` 的 `124` 判 FAIL（`AGENTS.md`「长任务」判据）。
- **输出**：逐项 `[PASS]/[FAIL] <id> <期望> <实际>`；末尾 `N/N 项通过`（现场统计）+ 总耗时；任一 FAIL ⇒ 非零退出。
- **注入模式**：`--inject` 在临时目录复制产物/投影/矩阵后篡改，断言「目标检查 FAIL ∧ 注入非空」，然后删除临时副本（不触碰真实产物）；若确需触碰真实文件，必须 `cp`+md5 还原。
- **L2 前置**：`docs/Process-09` 的 L2 只要求「已 provision 的树」；缺 `make fetch`/`make install-host`/`make build-musl` 前置时门控**明确 FAIL 并给出命令**（不 SKIP）。

## 范围（改哪些文件）

- `tools/linux/check_k0.py`（新建；含 `--inject`）
- `tools/infra/apply_series.py`（新增 `--component <name>` 过滤，可重复；**默认行为不变**，供 K12 只作用于 linux，避免门控写入其它组件）
- `Makefile`（仅成员表：L1 `_locked-check` 追加 `check-linux-toolchain`、`check-linux-boot-contract`；L2 `check-modules` 追加 `check-linux-k0`；必要时补 `_locked-*` 规则，但目标声明归 `m14-linux-001`）
- `docs/Process-07-门控分层规范.md`（§1.1 三行登记：两条 L1 + 一条 L2）
- 本任务书

**不改**：`tools/linux/{make_vmlinux,make_initramfs,check_toolchain,check_boot_contract}.py` 的判据（只调用）；`components/`；`spec/`；`contracts/`；`manifests/`（除只读解析）。

## 验收标准

1. `make check-linux-k0` rc=0，逐项 K1–K13 全 PASS，`N/N` 现场统计；在**干净克隆 + 前置完成**的树可复现（完成区写明前置命令序列）。
2. 缺产物路径：临时移走 `vmlinux`（`cp` 备份后 `mv`）⇒ rc≠0 且点名 `make linux-vmlinux`；还原 ⇒ rc=0（可达 FAIL，不 SKIP）。
3. `--inject` 覆盖至少四类：① vmlinux 副本改 `e_entry`；② initramfs 副本删 `init`；③ 矩阵副本改一行 `declared`；④ 源树临时弄脏/多一 commit ⇒ 各自 FAIL；还原后回绿（贴真实输出）。
4. `make check-modules`（L2）rc=0 且**包含** `check-linux-k0`（输出可见）；`make check`（L1）rc=0 且**包含** `check-linux-toolchain` 与 `check-linux-boot-contract`（`grep`/输出取证）。外部红逐条归属（非本任务产物）。
5. `apply-series` 幂等断言可失败：在临时克隆/临时树制造「第二次运行新增 commit」的反例 ⇒ K12 FAIL；真实源树不动（或用 Process-01 §7 恢复并 md5 对账）。`apply_series.py --component linux` 只处理 linux；**不带** `--component` 时行为与派单前一致（输出/组件遍历顺序不变，可对照基线）。
6. 耗时：打印各类耗时（构建/解析/apply-series）；若 L2 增量 > `docs/Process-07 §3` 预算，完成区写实测与建议（不改层）。
7. `docs/Process-07 §1.1` 两行登记与 `Makefile` 实际层归属一致（L1/L2），判据列可机械判；`make check-milestone` 不因本任务新增项变红（除本任务 `待验收` 的预期项）。
8. 一键证据脚本（含注入）；完成区 ≤30 行、无运行期路径。

## 说明

- **不要重复判据**：K3/K4/K5/K9 的期望值从 `contracts/linux-boot.yaml` 派生；K10/K11 调用既有检查器，不在本脚本复制其逻辑（避免两套真源漂移）。
- **L2 成本**：K0 vmlinux 是最小骨架，增量构建应在秒级；首次全量构建可能数分钟。以实测为准；若超预算，按 `Process-07 §3` 由主会话决定分层，不在本任务擅自下移。
- **`check-linux-k0` 会写构建树** ⇒ 已在 `GATE_LOCKED_TARGETS`；`make check-modules` 嵌套调用时依赖 gate lock 的嵌套放行（`docs/Process-07 §2`），实测确认不自锁。
- 参考实现只读：`.cache/refs/DADAO-0628` 的 K3 收口 runner 可对照「fail-closed/无 SKIP」写法（**内容溯源，非执行必需**），不复制。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数/耗时写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/授权原话不得编造；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出/构建日志留存运行期日志目录（`docs/Process-08`）。
10. 证据脚本基线钉**派单前 commit 常量**或现场 md5，不得取 `HEAD`。
11. 被检命令的退出码必须直接捕获（禁 `cmd | tee` 吞码）。

## 用户授权

**用户授权（2026-11-13，渠道 = 主会话问答；选项「授权这三处（推荐）」）**：用户同意本批任务修改 `spec/Machine-v5`（含只读锁）、`docs/Process-01`、`docs/Process-07` 三处；本任务按授权执行，其余 `spec/` 与 `docs/Process-*` 改动仍需逐次授权。

本任务范围：`docs/Process-07` 的 L1/L2 成员表登记。

## 待裁定

（需用户语义裁定的事项写这里：问题 + 选项 + 建议 + 自决的临时处置；返回主会话。）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审（待填）

### 第 1 轮 reviewer 验收（待填）
