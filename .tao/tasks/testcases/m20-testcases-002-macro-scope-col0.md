# m20-testcases-002: `check-inst-macro-scope` 与扫描器接受列 0 断言行（ISS-461）

**模块**：testcases
**项目里程碑**：M20
**依赖**：无
**可并行分片**：否（两个扫描器 + 一个自检）
**预估**：1 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（M20 分诊，2026-11-25）

`ISS-461` 记录 `check-inst-macro-scope` 的 S8（已整例宏化的 `.S` 正文不得再有裸
`__CHECK_*`）只用行首 `\t` 作为识别边界；`llvm-mc` 实测接受列 0 的宏调用/指令，
因此列 0 的裸断言行可以绕过 S8 与用例扫描器。当前仓库列 0 断言行数为 0，
属**潜在漏检**，不是现存红。

现场复核：

- `BARE_CHECK_RE` 对 `__CHECK_RD 1, rd5, 0x0`（列 0）不匹配；
- `run_inst_tiny.CHAIN_CASE_RE` 对列 0 的 `TEST_LD ...` 不匹配；
- `check_inst_macro_scope.py --selfcheck` 当前 PASS，但自检只用 Tab 缩进样例。

## 目标

1. S8 与用例扫描器统一为「允许缩进或列 0」，不放松其它判据。
2. 自检新增一条列 0 裸断言注入：注入即 FAIL，还原即 PASS。
3. 新增一条列 0 的链例/宏调用扫描断言，证明 `run_inst_tiny` 现场计数不因列 0
   而漏例；不得改动 `.S` 向量本身。

## 验收（逐条贴真实 rc）

1. `python3 tools/testcases/check_inst_macro_scope.py --selfcheck`：新注入路径
   真实 FAIL、还原后 PASS；原有 12 类注入全部保持 PASS。
2. `python3 tools/testcases/check_inst_macro_scope.py`：基线 rc=0（当前列 0
   违规数为 0，修复不应引入新红）。
3. `run_inst_tiny.scan_source` 在临时副本上对列 0 的 `TEST_*` 行现场计数，
   与 Tab 缩进副本一致；给出两份输出的对照。
4. `check-inst-asm`、`check-tests-index` 真 rc；`check-patch-tree` 总 rc 受在途
   任务影响时按「本任务未触碰组件补丁」披露。
5. **可达 FAIL**：把列 0 支持改回 `^\t` ⇒ 新自检注入回红；`cp` + md5 还原后回绿。

## 约束

独立 `git worktree`（分支 = `m20-testcases-002`）；不提交 git；只改
`tools/testcases/check_inst_macro_scope.py`、`tests/ee-tiny/run_inst_tiny.py`
与本任务书；不改 `.S` 用例、`components/**`、`spec/`、契约、`Makefile`。
证据落在「运行期证据目录内的 `run.sh`」，不写具体构建/临时路径。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
