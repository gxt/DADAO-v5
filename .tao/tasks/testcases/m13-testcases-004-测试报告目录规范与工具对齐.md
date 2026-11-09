# m13-testcases-004: 测试报告目录规范与工具对齐

**模块**：testcases
**项目里程碑**：M13
**依赖**：无（报告目录已先行落地：`docs/TestReports/`）
**可并行分片**：否（跨 tools/docs 单写者）
**状态**：待开始

## 背景

用户 2026-11-10 裁定：

- **人读结论放 `docs/`，加子目录**；原始数据不入库；矩阵快照随结论同处（不污染 `tests/`）。
- 目录命名定为 **`docs/TestReports/`**，其下不再分 `parity` 等二级主题子目录，靠**文件名**区分；文件名须清晰整齐。
- 现存 `tests/parity/matrix-M11.md` **已迁入并改名** `docs/TestReports/M11-三平台一致矩阵.md`（凡例同步迁为 `…-凡例.md`），`tests/parity/` 已删除。
- 目录约束（命名 / 收什么不收什么 / 必备四项 / 禁止项）已写入 `docs/TestReports/README.md`；`docs/README.md` 已加索引。
- 现有 qemu/gem5 差分结论已落 `docs/TestReports/M13-三平台差分-qemu-gem5.md`。

**本任务只做「规范落地 + 工具/门控对齐」，不改上述结论内容。**

## 目标

1. **规范入册**：在 `docs/Process-09`（测试组织规范）新增「测试报告归属」一节，写清四类产物的落点（运行产物 / 原始数据 / 里程碑快照 / 人读结论）、命名规则、必备四项、禁止项；与 `docs/TestReports/README.md` 互为一致（不重复造第二套口径，Process-09 引 README 为准）。
2. **工具对齐**：`tools/testcases/parity/run_parity.py`、`se_tset_matrix.py`、`tools/testcases/night_run.py` 及 `tools/testcases/parity/README.md` 中默认输出路径 / 注释 / 示例改为 `docs/TestReports/<M>-…` 形态（**不改变算法与口径**）。
3. **门控**：新增 L1 检查 `check-test-reports`（`tools/infra/check_test_reports.py` + `Makefile` + `Process-07` 层归属登记），断言：
   - `docs/TestReports/` 下无运行期绝对路径（`/tmp/**`、`/home/**`、`.work/**` 具体路径）
   - 快照类文件首行含 `<!-- 现场生成，勿手改 -->`
   - 文件名符合 `<M>-<主题>[-<后缀>].md`（`<M>` = `M\d+`）
   - 每册头部含「生成时间 / 数据来源 / 机器指纹 / 复现命令」四项关键词
   - 检查器**必须可达 FAIL**（注入 4 类各一次，`cp`+md5 还原）
4. **引用一致性**：`git grep 'tests/parity'` 只剩白名单（归档册的历史叙述、`docs/README.md` 的来源说明），其余 0；`tests/parity/` 目录不存在。
5. **回归**：`check-tasks` / `check-knowledge-refs` / `check-run-artifacts` / L1 / L2 rc=0。

## 非范围

- 不改 `docs/TestReports/` 下两份报告的**结论与数据**（只允许修格式/链接错误，且须在完成区逐条列出）
- 不改生成器的选例/比对算法
- 不重跑长尾计时（`m13-testcases-003`）
- 不动 `.tao/archive/` 的正文（历史册路径已在迁移时机械更新，不再改写）

## 验收标准

1. `docs/Process-09` 有「测试报告归属」节，与 `docs/TestReports/README.md` 无矛盾（逐条对照表）
2. 三个工具脚本 + 其 README 的默认输出/示例指向新目录（`python3 tools/testcases/parity/run_parity.py --help` 可见）
3. `make check-test-reports` rc=0；4 类注入各可达 FAIL 并还原回绿
4. `git grep tests/parity` 仅白名单；`tests/parity` 不存在
5. L1 / L2 / `check-tasks` / `check-knowledge-refs` / `check-run-artifacts` rc=0（外部红逐条核实归属）
6. 一键证据脚本（运行期证据目录下的 `run.sh`）
7. 完成区 ≤30 行、无运行期路径

## 说明

- 门控复杂度按最小原则：先做 4 条静态断言，不引入格式化/渲染。
- `docs/TestReports/README.md` 与两份报告由 architect 先行落地；本任务以其为**输入**，不重写。
- 构建/门控在主控机；不占用 207/208。

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
