# TESTCASES-075t: tset 迁移（libc-test/llvm-ts/embench）

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-071t
**状态**：已验证

## 目标（P5）
1. 驱动：`tools/testcases/{run_libc_test_user_suite.py,run_llvm_ts_user.py,run_embench_user_suite.py}` → `tools/testcases/tset/<suite>/`；套件独有 glue → `tests/tset/<suite>/`（共享才进 `shared`）。
2. 新门控 `check-tset-<suite>-smoke`（L2）；旧目标保留别名；`ansibench` 不纳入。
3. 更新 `tests/tset.yaml`、Makefile/文档；`check-run-artifacts` 目录名仍按 Process-08。

## 验收
- 三套 smoke 绿；旧入口等价；`make check`/`check-modules` 绿；无期望/驱动语义改动。

## 约束
- 只改本任务范围内的 `tests/`、`tools/testcases/`、`Makefile`、索引/`case-ledger`、`milestones.md`；不改 spec/qemu/LLVM 语义。
- **旧路径/旧门控在本任务内保留**（薄 wrapper/别名）；删除旧入口只在 `TESTCASES-076t` 做。
- 不改测试期望、不放宽断言；只做“搬家 + 接线 + 兼容层”。
- 只跑 smoke/定向；全量 `check-full`/夜跑留到 `TESTCASES-076t` 或任务空档。
- 临时目录 `/tmp/opencode/<任务号>/`；不提交。

## 完成区

**状态**：已验证

### 修改文件
- 驱动：`tools/testcases/tset/{libc-test,llvm-ts,embench}/run_*.py`（+ libc/llvm `run_smoke.py`）；旧扁平路径留薄 wrapper。
- glue：`tests/tset/embench/{embench_runtime.c,embench_user_boardsupport.c,embench_include/}`（`tests/scripts/` 留符号链接）。
- 接线：`Makefile`、`tools/infra/check_run_artifacts.py`、`tools/integ/run_embench_e2e.py`、`tests/tset.yaml`、`tests/tset/*/README.md`。
- 文档/台账：`docs/Process-08/09`、`tests/README.md`、`tests/INVENTORY.md`、`tests/scripts/README.md`、`components/embench-iot/README.md`、`milestones.md`。
- 证据：`.work/evidence/TESTCASES-075t/run.sh`（未入库）。

### 验收命令与结果
- `make check` rc=0；`check-tests-index` rc=0（240 条，现场）；`check-case-ledger` rc=0（1958 条；`--write` 后 md5 `22103f04…` 不变）。
- `make check-tset-libc-smoke` rc=0（5 类 / 5 代表）；`make check-tset-llvm-smoke` rc=0（3 树 / 3 代表）；`make check-tset-embench-smoke` rc=0（38/38 pass）。
- 语义对账：三份驱动 vs `HEAD` 仅 `REPO_ROOT`（embench 另 shim 路径/注释）之差；旧 wrapper == 新路径 2 例逐例 `klass/exit` 全等；embench 迁移前 38/38 == 迁移后 38/38。
- `test-m6` 的 Embench E2E 复用新 glue：`run_embench_e2e.py --opt O0` rc=0（19/19）。
- `.work/evidence/TESTCASES-075t/run.sh`：13 项 PASS（含注入 A/B → 红 → `cp`+md5 还原 → 绿）。

### 新发现/坑
- 旧扁平 wrapper 与实现同名：smoke 脚本的 `sys.path` 必须把实现目录排在 `tools/testcases` 之前，否则 import 命中 wrapper 并以驱动 argparse 退出。
- `make` recipe 失败返回 2（非 1）：证据脚本「应红」判据须 `rc!=0`，不能写死 1。
- L2 三个 tset 目标不加 `install-host/build-musl` 前置（每次 gate 重入会重复重建 builtins），改显式 guard；L2 由 `check-unit` 先建。

### 遗留
- 未整跑 `make check-modules`（任务限 smoke/定向；L2 新成员已逐个跑绿）。
- `tests/scripts/` 共享件（crt0/lds/运行时）与 `e2e` 收口留 `TESTCASES-076t`。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 旧扁平 wrapper 与实现同名，smoke import 命中 wrapper（argparse rc=2） | ✅已修 | `run_smoke.py` 的 `sys.path` 顺序（HERE 最后插入） | `--list` rc=0；三条 smoke 全绿 |
| smoke 类别断言与选择同源，近乎恒真 | ✅已修 | 类别改由源码路径独立派生 + 校验 id 与类别/树一致 | `--list` 结构断言 PASS；`libc=5/5`、`llvm=3/3` |
| `REPO_ROOT` 层级（嵌套两层后需 4 个 `..`） | ✅已修 | 三驱动 + 两 smoke | 对账 diff 仅路径行；门控全绿 |
| 证据脚本注入 B 期望 rc 写死 1 | ✅已修 | 改判 `rc!=0` | 证据 13/13 PASS |
| Makefile 兼容别名是否为空目标 | ✅不修 | `check-{libc-test,llvm-ts,embench}-smoke` 仅依赖新目标（旧目标本不存在） | `make -n` 不适用；实际调用走新目标 |

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲自执行，均在仓库根相对路径）**：
- `make check` RC=0；`make check-tests-index` RC=0（现场 240 条：inst=40/arch=10/unit=187/tset=3）；`make check-case-ledger` RC=0（1958 条）；`--write` 前后 md5 均 `22103f0467eeeedb354a8d92a05562fb`，byte-identical。
- 三条 smoke：`check-tset-libc-smoke` RC=0（5 类/5 代表，现场统计）；`check-tset-llvm-smoke` RC=0（3 树/3 代表）；`check-tset-embench-smoke` RC=0（38/38 pass）。
- 旧别名 `check-libc-test-smoke`/`check-llvm-ts-smoke`/`check-embench-smoke` 各 RC=0（依赖式别名，Makefile:854-856）。
- `bash .work/evidence/TESTCASES-075t/run.sh` RC=0：13/13 PASS（脚本审阅通过：注入 A/B 各有可达 FAIL 路径、判据为 `rc!=0` 不写死、还原用 `cp`+md5 对账）。
- `make check-modules` RC=0（L2；三条 tset smoke 在成员表 Makefile:919）。

**语义不变核验**：三份驱动 vs `HEAD^` diff 仅 `REPO_ROOT` 层数（+2 注释里的 sister driver 路径、embench `DEFAULT_SHIM`/文档 shim 路径），无逻辑改动；旧扁平路径为薄 wrapper（runpy 转发，`sys.path` 前插实现目录）；`tests/scripts/` 三个 embench 件为符号链接 → `tests/tset/embench/`，目标存在。

**独立反例（reviewer 注入，非复用 engineer）**：改 `tools/testcases/tset/embench/run_embench_user_suite.py` 的 `DEFAULT_SHIM` → 不存在路径 ⇒ `check-tset-embench-smoke` RC=2（FAIL：`hosted board shim not found`）；`cp` 备份还原 + md5 前后一致 ⇒ 回绿 RC=0。全程未用 git checkout/restore/stash。

**约束核验**：① `ansibench` 全树 grep 无命中（未纳入）✓；② `check-run-artifacts` 目录名规则 `RUN_DIR_RE`（`^\d{8}T\d{6}Z-`）未变，实跑产物目录 `20261026T221821Z-embench-user-static` 合规 ✓；③ 无测试期望/断言放宽（驱动 diff 已逐行核）✓；④ 范围外披露仅 `components/embench-iot/README.md` 路径文案 + `tests/scripts` 符号链接——必要且未改语义 ✓；⑤ 工作树干净（`git status --porcelain -uall` 0 行，与审前快照一致），无残留 ✓。

**判决：Accepted**。剩余风险：`tests/scripts/` 共享件与 e2e 收口、旧入口删除留 `TESTCASES-076t`（任务书已声明，不阻断）。
