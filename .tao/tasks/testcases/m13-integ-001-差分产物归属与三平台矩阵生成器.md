# m13-integ-001: 差分产物归属与三平台矩阵生成器

**模块**：testcases
**项目里程碑**：M13
**依赖**：无（用户 2026-11-10 裁定放宽：本任务只做产物归属／schema／生成器，chipyard 列按 `N/A`，由 `integ-002/003` 在 M12 核完成后填列）
**可并行分片**：按套件 / 按指令族（实现标「待定」，派单前按节点实况定）
**状态**：待开始

## 背景

M13 要做 qemu/gem5/chipyard 三平台差分。当前产物散落：`docs/TestReports/M11-三平台一致矩阵.md`、`.tao/knowledge/refs/*-parity-summary.*`、`tools/testcases/parity/*.py`、各基线 JSON；矩阵内含运行期绝对路径，fresh clone 不可复现。

## 目标

1. **归属梳理**（用户 2026-11-09 记入 discussing 的待办）：明确四类产物的边界——原始基线 JSON（数据）、逐例报告（派生）、矩阵快照（展示）、生成器（代码），各自放哪、谁生成、是否入库。
2. **矩阵 schema**：三平台（qemu/gem5/chipyard）统一的 per-case 行格式（case id / 三平台 status / exit / 归因 owner）；chipyard 列在核未就绪时记 `N/A` 而非伪值。
3. **去掉运行期路径**：矩阵只写「机器指纹」（CPU 型号、源码 tree hash、编译器版本、二进制 md5 作诊断），不写 `/tmp/...` 绝对路径。
4. **生成器**：`tools/testcases/parity/` 增加三平台汇总入口（复用现有 `run_parity.py` / `se_tset_matrix.py` 的归因与 fail-closed 逻辑）。

## 验收标准

1. 四类产物的边界与位置写入 `docs/Process-09`（或等价文档），并给出「谁生成、是否入库」表
2. 矩阵 schema 有三平台列；chipyard 未就绪时 `N/A` 有明确依据
3. `grep -rn '/tmp/opencode' docs/TestReports/ .tao/knowledge/refs/` 为 0（矩阵与报告无运行期绝对路径）
4. 生成器可在 fresh clone 上从已入库 JSON 重建矩阵（不需运行期目录）
5. `make check` / `check-knowledge-refs` / L2 rc=0
6. 一键证据脚本（含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

不改 chipyard 核、不改 gem5/QEMU 实现、不跑长尾计时（`m13-testcases-00x`）

## 说明

- M13 的**差分执行**依赖 M12 核实现（chipyard 可用）；本任务是**骨架**，可在核未就绪时先做（chipyard 列 `N/A`，用户 2026-11-10 裁定）。
- 报告落点与命名以 `docs/Process-09 §15` + `docs/TestReports/README.md` 为准（不另立口径）。
- 差分产物归属以 `m13-integ-001` 的结论为准。

## 硬约束

1. 临时目录 `/tmp/opencode/m13-integ-001/`；禁仓库内临时文件。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存运行期日志目录；命令在 worktree 根内、相对路径。
6. 单任务单机；节点操作后 `make sync-node-repo`。
7. 不要删除其它任务的临时目录。

