# m16-testcases-008: `unit` 允许 `system` 并登记 Tiny hmon

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-006`（Tiny hmon 已迁 `tests/unit/gem5/`）已合入
**可并行分片**：否（共享 `tests/unit.yaml`/索引校验器）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（用户 2026-11-22 裁定）

Tiny hmon 从 `tests/arch/` 迁到 **`tests/unit/gem5/`**（选 A）。`unit` scope 的 `platforms` 目前只允许 `host`/`toolchain`，导致该测试无法登记进 `tests/unit.yaml`，迁出后没有 L1/L2 覆盖。本任务放开 `unit` 的 `system` 平台并登记。

## 要做

1. **平台放开**：`tools/testcases/check_tests_index.py` 的 `SCOPE_PLATFORMS["unit"]` 增加 `"system"`；同步脚本内注释与 `--self-test` 用例。
2. **登记**：`tests/unit.yaml` 增加 `unit-gem5-hmon-001`：
   - `file: unit/gem5/check_tiny_hmon.py`；
   - `platforms: [system]`；
   - `level: full`（依赖 gem5 构建，不进 L2 `check-unit`）；
   - `requires: [gem5-fs]`（或现有合法依赖名，现场核 `check_tests_index` 允许集）。
3. **文件类型**：索引校验原本按 `.s`/`.ll` 等；允许 `unit` 的 `.py` 驱动（与 `arch` 的 driver 型一致），只校验文件存在、字段合法。
4. **文档**：`tests/unit/README.md`（或 `tests/unit/gem5/README.md`）写明 Tiny hmon 的运行方式、依赖 gem5 FS、不进 L2；`tests/arch/README.md` 已由 006 改，不再重复。
5. **门控**：`check-unit` 不因新增条目改变（level=full 不进 L2）；`check-unit-full` 是否纳入该测试由现有 full 规则决定；若 full 会跑 gem5，必须在任务书完成区说明耗时与前置。

## 不做

- 不改 Tiny hmon 测试本身；
- 不改 gem5 源码；
- 不改 arch 的 `machine: vast` 规则。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集限 `tests/unit.yaml`、`tools/testcases/check_tests_index.py`、`tests/unit/**/README.md`、本任务书；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-tests-index` rc=0；现场统计 `unit` 条数 = yaml 条数，`unit-gem5-hmon-001` 被识别；
2. 注入 3 路：① `platforms: [system]` 之外的非法值 ⇒ FAIL；② `file` 不存在 ⇒ FAIL；③ 重复 id ⇒ FAIL；`cp`+md5 还原后回绿；
3. `check-unit` rc=0 且**不因新条目多跑 gem5**（日志/成员数可比）；
4. `check_tests_index.py --self-test` rc=0；
5. `make check-tasks`、`check-knowledge-refs` 记录 rc。

## 完成区

**测试结果**：运行期证据脚本 `run.sh` → `summary: checks=34 fails=0` / `RESULT: PASS` rc=0。`check-tests-index` rc=0（unit=187 == yaml=187，现场派生）；注入 3 路（非法 platform / file 不存在 / 重复 id）均 rc=1，`cp`+md5 还原后 rc=0；`--self-test` rc=0（含新增 unit system 基线与非法 platform 注入两例）；`check-tasks`/`check-knowledge-refs` rc=0。`check-unit` **rc=2（已知基线红）**：check-lit 180 项 PASS 后停止于 test-codegen，19/19 以 `SHT_RELA present` 结构失败；HEAD 干净树同一驱动 19 条 FAIL **逐行 diff 为空**，非本任务引入（详见遗留）。`check-unit-full` 干跑无新用例，**不会跑 gem5**（= check-unit + check-lit-full，均不读 `tests/unit.yaml`），故无 gem5 耗时/前置需要纳入 L3。

**修改文件**：`tools/testcases/check_tests_index.py`（`SCOPE_PLATFORMS["unit"]` + `system`；docstring/注释；self-test +2 例）；`tests/unit.yaml`（+`unit-gem5-hmon-001`，`kind: driver`/`platforms: [system]`/`level: full`/`requires: [gem5-fs]`；头注释）；新增 `tests/unit/gem5/README.md`；本任务书。运行期证据脚本与日志在证据目录，不入库。

**验收结果**：`make check-tests-index` → `结果: PASS（473 条…）`；`check_tests_index --self-test` → `self-test: PASS`（36 例，含 `case9 干净基线·unit system .py 驱动 rc=0`、`case10 注入·unit platform 非法 rc=1`）；注入真实 rc 红/绿：platform 1/0、file 1/0、dup-id 1/0，三次还原 md5 均 `75ea3e35…` 一致；`check-unit` rc=2、基线驱动 rc=1、`codegen.diff` 空、FAIL 19 == `expected.yaml` programs 19；编译工具链 md5（llc/llvm-mc/llvm-objcopy）在跑批与基线期间均 `4977e92a…,ad34d612…,16dd959a…` 未变；补充 `check-case-ledger`（5692 条）与 `check-dirs` 均 rc=0。

**新发现/坑**：① `check-unit` 当前在共享安装根上红：test-codegen 的 raw single-TU 组装产物出现 `SHT_RELA`（`call [rb0, main]` 等），19/19 失败；HEAD 干净树逐行相同 ⇒ 基线红，与本任务无关（另案 issue）。② 证据脚本放在运行期证据目录（worktree 内为软链到主工作树）时，`git -C` 会解析到**主工作树**，导致跑错树（首轮误跑出 472 条）；已改为按当前工作目录取 toplevel + 校验 `unit-gem5-hmon-001` 存在。③ 并行会话（`m16-testcases-007`）反复 `install-host` 会刷新 qemu 二进制；判定失败集只依赖 llc/llvm-mc/llvm-objcopy，脚本对其做前后 md5 对账，qemu 单列说明。④ `check_tests_index` 对 `requires` **无白名单**（任意非空去重字符串），故 `gem5-fs` 合法性与 night/arch suite 命名一致；若后续要收紧需另立规则。

**遗留问题**：① `check-unit` 基线红（above），本任务「check-unit rc=0」验收项由「错误集与基线逐行相同」替代，待独立 issue/任务处置。② `docs/Process-09` §1 表仍写 unit = host/toolchain，本任务变更集不含该文件，未改；建议后续同步为 host/toolchain/system。③ 未跑真实 gem5 用例（环境依赖 gem5 构建，任务明确不进 L2/L3；登记与静态校验已覆盖）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| README 写了具体运行期路径（gem5 构建目录） | ✅已修 | 改为「默认构建落点」措辞 | README 运行期路径关键词扫描无命中（rc=1） |
| 证据脚本经运行期软链目录解析 REPO 到主工作树，首轮误测 472 条 | ✅已修 | `REPO=${REPO:-$(git rev-parse --show-toplevel)}` + 校验新条目存在 | run4 首行 `repo=…/m16-testcases-008`，unit=187 |
| 当前 FAIL 集取自 make 的 `tail -20`，少 3 行（16≠19） | ✅已修 | 复制完整驱动日志（运行期日志目录） | `current.fail`/`baseline.fail` 均 19 行，diff rc=0 |
| 工具链 md5 稳定性把 qemu 纳入，遇并行 install-host 刷新即误红 | ✅已修 | 只对 llc/llvm-mc/llvm-objcopy 对账；qemu 由驱动 ReadGuard 覆盖 | run4 `编译工具链 md5 稳定` PASS |
| 新平台/`.py` 驱动缺反向锁，删掉放开会静默回退 | ✅已修 | self-test 增 unit system 基线 + 非法 platform 注入 | self-test case9 rc=0 / case10 rc=1 |
| `check-unit` 基线红（19/19 SHT_RELA） | ⏸延后 | 不改测试/工具链（非本任务范围） | 干净树 19 条 FAIL 与当前逐行相同；`codegen.diff` 空 |

### 第 1 轮 reviewer 验收

**重跑记录**（reviewer 独立执行，不采信完成区）：仓库根执行运行期证据目录内的 `run.sh`

- `summary: checks=34 fails=0` / `RESULT: PASS`，脚本退出码 `RC=0`
- `make check-tests-index` rc=0 → `结果: PASS（473 条…）`；`unit=187 == yaml=187`（现场派生）
- 注入 3 路（非法 platform / file 不存在 / 重复 id）均 `rc=1`，`cp`+md5 还原后均 `rc=0`，三次还原 md5 与起点 `75ea3e35…` 一致
- `--self-test` rc=0，`case9 干净基线·unit system .py 驱动`、`case10 注入·unit platform 非法` 均 PASS（共 36 例）
- `check-unit` **rc=2**：`check-lit` 180 PASS / 0 FAIL 后停在 `test-codegen`，`Results: 0/19 passed, 19 failed`、`make: *** [check-unit] Error 2`；干跑与日志中 hmon 命中均为 0
- `check-unit-full` 干跑 hmon 命中 0、无 `tests/unit.yaml` 引用；成员来源 = Makefile `_locked-check-unit-full: check-unit check-lit-full`（check-lit / codegen / elf / ir-lli / picolibc / lit-full），仓内无第二处读 `tests/*.yaml`
- `check-tasks` rc=0（报告型提示①不阻断）、`check-knowledge-refs` rc=0（0 悬空）；抽查 `check-case-ledger` rc=0（现场 5692 条）、`check-dirs` rc=0

**基线红判据：成立**。`current.fail`/`baseline.fail` 各 19 行，reviewer 自跑 `diff` rc=0、`codegen.diff` 0 字节；make 输出可见的 16 条 FAIL 行全部含于 `current.fail`（`comm -23` 计 0），19 条全为 `SHT_RELA present`；两轮 `llc/llvm-mc/llvm-objcopy` md5 `4977e92a…/ad34d612…/16dd959a…` 前后一致；基线树 = `git archive HEAD`（94bab42d，不含本次未提交改动）。⇒ **KNOWN-RED**，非本任务引入；**建议 issue**（收尾入 issue 台账）：`check-unit/test-codegen` raw single-TU 组装 19/19 `SHT_RELA present`，P2、scope testcases/llvm，独立于本任务处置。

**独立注入（reviewer 自做，未用 `git checkout/restore/stash`）**：① `tests/unit.yaml` 改非法 platform → `rc=1`，报 `VIOLATION … scope unit 允许 ['host','toolchain','system']`；`cp` 还原 md5 `75ea3e35…` 相等 → `rc=0`。② 回退 `SCOPE_PLATFORMS["unit"]` → `--self-test` `rc=1`（case9 FAIL）→ `cp`+md5 还原 → `rc=0`（证明 self-test 有可达 FAIL 路径）。

**约束核验**：变更集 = 本任务书 / `tests/unit.yaml` / `tools/testcases/check_tests_index.py` / 新增 `tests/unit/gem5/README.md`，与任务书限定一致；README 运行期路径关键词扫描 rc=1；四文件 md5 与开工快照一致、`git status` 逐行相同（4 行）；无「银行」术语；未提交 git。

**finding（不阻断）**：`docs/Process-09 §1` 表仍写 unit 平台 `host / toolchain`，与本次放开不一致。判定**不必在本任务同步**：任务书变更集明确不含该文件、无门控/退出码/断言依赖该表、`§7` 未把 unit 平台写成规范项；按「文档级小错」记 finding，请 architect 收尾补一行 `host / toolchain / system`（或另立小任务）。

**判决：Accepted**（任务书「`check-unit` rc=0」一项按 AGENTS §4 基线红判据以「错误集逐行相同」替代，见上；待架构师终审）。

