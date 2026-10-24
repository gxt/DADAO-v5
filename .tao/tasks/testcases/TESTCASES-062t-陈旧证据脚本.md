# TESTCASES-062t: 陈旧证据脚本收口（`ISS-237`/`ISS-238`/`ISS-282③`）

**模块**：testcases
**项目里程碑**：M9（用户 2026-10-24 裁定「M9 内做」）
**依赖**：无
**状态**：已验证

## 立项来源

- `ISS-237`：`QEMU-061t` 的 `smoke_derive.py` L2 派生逻辑过时（`GATE_VECTORS` 已含 `aip-si.yaml`，再"追加"无增量）
- `ISS-238`：`SPEC-145t` 证据脚本因 `rela`→`aip` 改名后有 **14 项 stale 断言**
- `ISS-282③`：`llvm-ts-user-*` 命名遗留（`INFRA-093t` 验收第 3 项）

## 目标

1. 237：按现行 `GATE_VECTORS` 重写派生断言（"追加"改为"集合包含"），并给"改前恒真/改后可达 FAIL"的证据。
2. 238：14 项 stale 断言逐条改指/删除；保留语义断言。
3. 282③：把 `llvm-ts-user-*` 的豁免/命名按 `Process-08` 收口（或明确"保留 + 记录判据"，不进门控），使 `ISS-282` 可关。

## 验收

1. 各脚本真实重跑 rc=0；`ISS-238` 的 14 项 **0 残留**（grep 证据）。
2. **可达 FAIL ≥2**：① 237 把"集合包含"改回"追加" ⇒ 注入即失败；② 238 改坏一条断言 ⇒ 红。
3. `make check`(L1) rc=0；`check-run-artifacts` rc=0。
4. 证据 `.work/evidence/<任务ID>/run.sh`。

## 约束

- 不改 QEMU/LLVM 实现；不 commit/push；临时目录 `/tmp/opencode/TESTCASES-062t/`。

## 完成区

**测试结果**：`bash .work/evidence/TESTCASES-062t/run.sh` 34/34 PASS rc=0；`--inject` 49/49 PASS rc=0（含 4 组可达 FAIL）。`bash .work/evidence/SPEC-145t/run.sh` 73/73 PASS rc=0，`--inject` 95/95 PASS rc=0（5 例注入均先红后绿）。`python3 .work/evidence/QEMU-061t/smoke_derive.py` rc=0（4/4 组命中）。
**修改文件**：`tools/infra/check_run_artifacts.py`（删 `INFLIGHT_LEGACY` + `--legacy-status` + `legacy` 分支、docstring/A3 输出同步）；`docs/Process-08-…规范.md` §2 A3 一行；`.tao/knowledge/issues.yaml`（`ISS-237`/`ISS-238`/`ISS-282` 补收口注记）；`.tao/knowledge/milestones.md`（本册行）；本任务书。**gitignored 交付**：`.work/evidence/QEMU-061t/smoke_derive.py`（重写）、`.work/evidence/SPEC-145t/run.sh`（重写）、`.work/evidence/TESTCASES-062t/run.sh` + `legacy-before.{list,md5}`、`.work/tests/archive/ISS-282/`（26 件 + README）。
**验收结果**：① 237 判据 = 集合包含（两侧现场派生、键含源文件名前缀）：现行 4/4、rc=0；回退「追加」逻辑 ⇒ rc=1 + `missing` 行；对照证明成员判据（`aip-si.yaml in GATE_VECTORS`）在注入态仍 PASS = 恒真。② 238 14 个陈旧词 grep 命中合计 **0**（`rela.si`/`rela-si`/`PC 相对`/旧计数 `235`·`156`·`199`/`0x58`/`run_gate_rc_nonzero`/`已知红`/`授权原话`/旧任务书名/`git diff -- spec/`/`XFAIL`）；改坏一条断言 ⇒ rc=1。③ 282③ 26 个 `llvm-ts-user-*` 移入 `.work/tests/archive/ISS-282/`，md5 26/26 一致、`.work/log` 残留 **0**；门控对该形状新文件判红、旧版（含豁免）同一临时树 rc=0。④ `make check-run-artifacts` rc=0（A3 `1435 new / 0 illegal`）、`--self-test` 6/6 PASS、`make check`(L1) rc=0。
**新发现/坑**：① `.work/evidence/QEMU-061t/oracle_aip.py` 亦随 `op`→`opc` 字段改名 stale（`KeyError: 'op'`，L70）——同族但其不在本册 3 条范围，未修。② `INFLIGHT_LEGACY` 实际早已不生效（26 件均被 `.run-artifacts-baseline` 快照豁免，A3 打印 `legacy=0`）⇒ 删除代码对门控 rc 无影响，但命名卫生仍需搬迁。③ 证据脚本内 heredoc 被赋值捕获时若 python 失败会「0 行静默绿」⇒ 已加行数下限断言。
**遗留问题**：`oracle_aip.py` stale（交后续证据维护笔）；`.work/tests/archive/` 其余存量（398 文件级）未搬迁（`ISS-278` 边界，本册只搬 `llvm-ts-user-*`）；未 commit/push。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 SPEC 脚本 heredoc 失败 ⇒ 0 行断言静默绿 | ✅已修 | 第 1/5 节各加「断言行数 > 0」fail-closed 断言 | 默认/`--inject` 均 0 FAIL |
| F2 证据 I-3 用 `git show HEAD:`，提交后对照失效 | ✅已修 | 固定为任务基线 `879de8cd`（只读导出，不写工作树） | `--inject` I-3 两向均 PASS |
| F3 `--legacy-status` 删除后 rc 被管道 `tail` 吞 | ✅已修 | 证据脚本直接取 python rc（期望 2） | S4 期望=2 实际=2 |
| F4 新脚本是否残留旧词（自证命中） | ✅已修 | §0 自我陈旧词扫描 + 证据 S2 14 项 grep | 14 项命中合计 0 |
| F5 搬迁是否逐字节 | ✅已修 | 搬前 md5 快照入证据目录，逐件比对 | 26/26 identical |

### 第 1 轮 reviewer 验收（2026-10-24）

**判决：Accepted**（独立重跑 + 独立注入，非采信工程师叙述）

**重跑记录（reviewer 本人）**：`bash .work/evidence/TESTCASES-062t/run.sh` ⇒ **34/34 PASS rc=0**（含 `make check` L1 rc=0、`check-run-artifacts` rc=0、`--self-test` 6/6）；`--inject` ⇒ **49/49 PASS rc=0**；`smoke_derive.py` rc=0（4/4 组命中）；`SPEC-145t/run.sh` ⇒ **73/73 PASS rc=0**；A3 = `1435 new / 0 illegal / 5939 exempt`（5965−26=5939 ✓）。

**必核项**：① 237 判据源码 = 集合包含（两侧现场派生、键带文件名前缀）✓；**独立注入**（cp+md5）回退「追加」⇒ rc=1 + 4 组 MISSING，还原 md5 一致、rc=0；成员判据（`aip-si.yaml in GATE_VECTORS`）在注入态仍 PASS ⇒ 恒真属实。② 238：reviewer 逐项 grep 14 陈旧词**合计 0**；语义断言留存（29 条 check：validate_encoding / qfc / spec 正文等）；**独立注入**改坏 §4 标题断言 ⇒ rc=1+1 FAIL、还原回绿。③ 282③：archive 26 件+README、md5 26/26 逐字节一致、`.work/log` 残留 0；`INFLIGHT_LEGACY`/`--legacy-status` 源码 0 命中（argparse rc=2）；`Process-08 §2 A3` 已同步（diff 核过）。④ 覆盖：commit 仅 5 文件，`tests/`、`Makefile` 0 改动 ⇒ 用例 0 增 0 删、L1 项不变。⑤ 残留扫描 +1 独立注入：真文件追加 `rela.si` ⇒ run.sh rc=1（S2-03 命中），还原 md5 一致、34/34 回绿。⑥ `issues.yaml`：237/238/282 均 `closed` + `resolved_by: TESTCASES-062t` ✓。

**快照对账**：注入前后 `git status --porcelain -uall` 均 0 行；`.inject-*` 残留 0；两被改文件 md5 还原后与备份逐一对等（adb73174… / d02f3911…）。**无阻断项**（无断言放宽/stale 残留/文件被删/门控红）。

