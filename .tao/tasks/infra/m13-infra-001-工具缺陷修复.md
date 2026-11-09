# m13-infra-001: 工具缺陷修复（gem5 首建 `ValueError`、里程碑核验器基线残留）

**模块**：infra
**项目里程碑**：M13
**依赖**：无
**可并行分片**：否（两个脚本，单写者）
**状态**：待开始

## 背景

两个已登记的工具缺陷（`issues.yaml`），都会在新机器/归档场景误伤：

- **`ISS-355`（P2）**：`tools/gem5/build_gem5.py` 在 `--build` 指向 `.work/build/gem5` 且该路径**不存在**时，先 `build_link.parent.mkdir(parents=True)` 再 `build_link.symlink_to((source/"build").relative_to(build_link.parent))`；`source/build` 不在 `build_link.parent` 之下 ⇒ `Path.relative_to` 抛 `ValueError`，首次 `make build-gem5` rc=2（`m12-gem5-001` 实测）。当前避让方式是先手工建目录，属绕行未修根因。
- **`ISS-356`（P3）**：`tools/infra/check_milestone_tasks.py` 两处基线残留：① `MBOOK_NAME_RE = ^[A-Z]+-\d{3}m-.*\.md$` 不命中新式 `mNN-<module>-*.md`，会按「无 m 册」跳过；② m 册标题自引自身文件名号可绕 vacuous 检查。

## 目标

1. **`ISS-355`**：符号链接目标计算改为可跨目录（如 `os.path.relpath`），删除/改写会抛 `ValueError` 的 `Path.relative_to`；**保持**「`build_link` 存在且非符号链接 ⇒ 打印 note 并跳过」的既有行为。
2. **`ISS-356`**：`MBOOK_NAME_RE` 扩展为同时命中 `mNN-<module>-*.md`（大小写与编号格式按仓库现况）；补 vacuous 检查的「标题自引自身文件名号」反例（须可 FAIL）。
3. 两处都补**先红后绿**证据：改前跑出当前错误行为，改后回绿。

## 非范围

- 不改 gem5/QEMU/chipyard 组件源码（本任务只改 `tools/`）
- 不改 spec / 契约 / 台账语义
- 不动 `check_milestones_fresh.py`（另一个检查器）

## 验收标准

1. `ISS-355` 复现：在 `--build` 目标不存在时调用，**改前** `ValueError`（记录 traceback），**改后** rc=0 且生成正确符号链接（目标可解析到 gem5 源树 `build/`）
2. `ISS-355` 回归：`build_link` 已存在但不是符号链接时仍打印 note 且不改动
3. `ISS-356` 复现：构造 `m99-xxx-001-标题.md` 形态的核验册，**改前**被「无 m 册」跳过，**改后**被识别；vacuous 检查对「标题自引文件名号」给出 FAIL（注入佐证）
4. 现有门控零回归：`check-tasks` / `check-milestones-fresh`（两本册）/ L1 / L2 rc=0（外部红逐条核实归属）
5. 一键证据脚本（含可达 FAIL 注入）
6. 完成区 ≤30 行、无运行期路径

## 说明

- 修复点以实际源码为准，任务书不写死行号。
- `ISS-355` 的 `ValueError` 由 `Path.relative_to` 抛出（不是显式 `raise`），勿被「文件里没有 `ValueError` 字样」误导。
- 构建验证不需要重编 gem5：只需覆盖 `build_gem5.py` 的链接建立路径（可用一次性临时目录作为 `--build` 目标）。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定时留问。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 用户裁定须原样写入任务书。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
