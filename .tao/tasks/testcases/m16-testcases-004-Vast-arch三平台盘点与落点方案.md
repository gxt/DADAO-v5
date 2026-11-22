# m16-testcases-004: Vast arch 三平台盘点与落点方案

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（只读；与 `m16-testcases-005` 可并行）
**可并行分片**：是（9 个 cfx 可分片）
**预估**：中（只读盘点 + 文档，不设硬时限）
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22 裁定）

M16 的三方差分收敛为 **Vast arch scope**，裁定见 `.tao/knowledge/discussing.md`「M16 三方差分（Vast arch）批次裁定」：

- 只测 Kaiwu-Vast，不含 Tiny、不含 linux-user；cfx = 0/2/3/4/5/15/32/34/63；
- 三方（QEMU/gem5/RTL）签名逐槽一致，期望值独立派生自 `spec/`/`contract`，用户是 oracle；
- 仿真不进常规门控；
- 用例/脚本/数据集中 `tests/arch/`，签名机制集中 `tests/shared/`；
- 不预先造通用启动链，按 cfx 选最小载体。

本任务只做**盘点与方案**，不改组件代码、不改规范正文、不跑仿真。

## 要做

### 1. 三平台 cfx 盘点矩阵

对以下 9 个 cfx，逐项列 QEMU / gem5 / RTL 三侧状态：

`cfx0 umon`、`cfx2 smon`、`cfx3 hmon`、`cfx4 ptw`、`cfx5 cache`、`cfx15 hart`、`cfx32 pmem`、`cfx34 time`、`cfx63 power`。

每个 cfx 至少覆盖五面：**寄存器面 / 命令与副作用 / 异常与子原因 / 现有测试载体 / 现有门控**。每一格必须给证据：

- 有实现：`path:line`（组件源码树或补丁树，按 `docs/Process-01` 口径）；
- 没有：写「缺」并给判定依据（例如全树 grep 0 命中、或契约存在但实现无对应行）；
- 载体：写清是「QEMU bootrom 探针 / RTL ELF+loadmem / gem5 FS / 无」；
- 门控：写清在 `check-arch`、`check-arch-smoke`、手工脚本、无 中的哪一种。

矩阵落 `tests/arch/data/vast-arch-inventory.md`（新文件）。**27 格（9 cfx × 3 平台）必须全覆盖**，不许留空。

### 2. `tests/arch` 落点方案

落 `tests/arch/PLAN.md`（新文件），至少包含：

- 目录结构：`tests/arch/<cfx>/`（用例、`.lds`、生成器、`check_*.py`、`expected.yaml`）、`tests/arch/run_arch.py`、`tests/arch/common/`、`tests/arch/data/`；
- `run_arch.py` 的接口：`--cfx <0|2|3|4|5|15|32|34|63>`、`--platforms qemu,gem5,chipyard`、`--cache-model on|off`（arch 固定 on）、`--self-test`；
- `tests/arch.yaml` 字段方案：`machine: vast`（固定）、载体类型（`asm` / `driver`）、`platforms: [system]`；
- 迁移清单：`tools/chipyard/{ptw,tlb,dcache,icache,excp}/**`、`tools/testcases/arch/min_rom_probe_tlb.py`、`tests/arch/hmon/`（Tiny，移出 arch）的去向；
- 与 `m16-testcases-005` 的接口：签名脚本落 `tests/shared/signature.py`，arch 通过 `tests/arch/common/` 薄壳调用。

### 3. Process-09 修订草案

在 `tests/arch/PLAN.md` 内给逐条替换文本（**不改正文**）：

- §3 scope→目录映射：arch 专用脚本/数据随 `tests/arch/`；
- §5 根级清单：支持驱动型 case 与 `machine` 字段；
- §6 落点：scope 专用脚本随 scope，`tools/` 只放跨 scope 共享；
- §7 目录结构：`tests/arch/` 增加 `run_arch.py`/`common/`/`data/`，`tools/testcases/arch/` 标待迁。

每条写「原文位置 → 新文」，便于后续任务直接落地。

### 4. Tiny hmon 迁出方案

现有 `tests/arch.yaml` 的 `arch-hmon-001`（`tests/arch/hmon/tiny_hmon.S`，gem5 Tiny FS）与 arch 只 vast 冲突。给出迁移落点（建议 `tests/unit/gem5/`）与需要同步改的文件（`arch.yaml`、`tests/arch/README.md`、`checks`/门控引用），只给方案，不执行。

## 不做

- 不改 QEMU/gem5/chipyard 源码或补丁；
- 不改 `docs/Process-09` 正文、不改 `tests/arch.yaml`；
- 不建 `run_arch.py` 实现、不写新用例、不跑仿真/不重建。

## 约束

- 独立 `git worktree`；**不提交 git**；只写 `tests/arch/PLAN.md` 与 `tests/arch/data/vast-arch-inventory.md`（外加运行期证据目录）；
- 不写运行期路径（`.work/**`、家目录、临时目录）到入库文件；
- 术语用「寄存器组」「核芯功能扩展」；
- 每条结论可回溯到真实 `path:line` 或现场 grep 输出，禁止凭记忆。

## 验证

运行期证据目录内的 `run.sh`，至少检查：

1. 矩阵 9 cfx × 3 平台 = 27 格全部有值（缺也要写「缺」），现场统计并与文中声明对账；
2. 矩阵内所有 `path:line` 落在文件行数内；
3. `tests/arch/PLAN.md` 的四节（目录/接口/迁移/Process-09 草案）齐全，Process-09 每条有「原文 → 新文」；
4. 不改代码：变更集 ⊆ {本任务书, `tests/arch/PLAN.md`, `tests/arch/data/vast-arch-inventory.md`} ∪ `.tao/**`；
5. `--inject` 至少 2 路（删一格矩阵 / 伪造一条引用）⇒ FAIL，`cp`+md5 还原后回绿；
6. `make check-knowledge-refs` 与 `make check-tasks` 只读跑，记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
