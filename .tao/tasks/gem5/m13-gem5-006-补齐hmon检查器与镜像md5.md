# m13-gem5-006: 补齐 gem5 hmon 检查器缺失文件 + 镜像 md5 常量

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-gem5-005`（装载契约，已合入）、`m12-chipyard-019`（hmon 段 56→120 B，已合入）
**可并行分片**：否（组件单写者）
**状态**：待开始

## 背景

`m13-gem5-005` 的完成区声明新增/修改了 4 个文件，但它们**从未进入任何 commit、磁盘上也不存在**（`m12-chipyard-019` 的 reviewer 实测：`git log --all` 无、磁盘无、合入 commit `611f9920` 的 `--stat` 不含）。

后果：`tools/gem5/check_tiny_hmon.py` 现在运行 `exit=2`（引用了不存在的 include），gem5 侧 hmon 门控失效。

同时 `m12-chipyard-019` 把 hmon 段从 **56 B 扩到 120 B**，BootROM 镜像 md5 由 `777b6bc9…` 变为 `33bfe14af0e47d9e6f9c2d4a34fc5ae0`；`m13-gem5-005` 的证据脚本里硬编码了旧值。

## 目标

1. **补齐 4 个文件**（按 `m13-gem5-005` 的设计重新导出，不得凭空造）：
   - `tests/arch/hmon/tiny_hmon_handler.S`
   - `tests/arch/hmon/tiny_hmon_handler.lds`
   - `tests/arch/hmon/tiny_hmon_layout.inc`
   - `tools/gem5/check_tiny_hmon.py`（使其与 `tests/arch/hmon/tiny_hmon.S` 的 include 匹配、可运行）
2. **更新镜像常量**：证据脚本与 checker 中的 `777b6bc9…` → `33bfe14a…`；若代码里有 `56 B`/`size=56` 之类的期望，改为 120 B（以实测为准，不写死猜测值）。
3. **保持 `tests/arch/hmon/expected.yaml`**：`m12-chipyard-019` 已把 `shared_bootrom_md5` 更新为新值 **且等于实测**，不要回退。
4. **可运行**：`python3 tools/gem5/check_tiny_hmon.py` rc=0，断言条数与记录数一致（现场统计）。

## 非范围

- 不改 gem5 引擎实现（`m13-gem5-005` 已定）
- 不改 chipyard/QEMU
- 不改 spec/契约

## 验收标准

1. 4 个文件存在且被 git 跟踪（`git ls-files` 可查），内容与 `tiny_hmon.S` 的 include/符号一致
2. `python3 tools/gem5/check_tiny_hmon.py` rc=0，输出记录数与断言数现场统计
3. `grep -rn '777b6bc9' tools/ tests/` 为 0（或仅历史注释，须说明）
4. `make check-modules` / `check-inst` / `check-unit` 零回归（外部红逐条核实）
5. 一键证据脚本（含可达 FAIL 注入：例如把镜像 md5 改回旧值 ⇒ 应 FAIL）
6. 完成区 ≤30 行、无运行期路径；**「修改文件」清单须与 `git show --stat` 逐项对账**

## 说明

- 必须在独立 `git worktree` 内作业（`ISS-368`）；不占用 207/208。
- 组件单写者；补丁走 `make_patch`。
- 若无法重建 `tiny_hmon_handler.S`（设计细节丢失），**停下报告**，由主会话决定回滚 `m13-gem5-005` 的相应部分。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；**「修改文件」必须与 `git status`/`git show --stat` 对账**。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
