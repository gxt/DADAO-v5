# m15-testcases-009: 「一例一镜像」术语清理 + `__PRINT` 零长硬化

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-007`（**已交付**：故障例链式合并，镜像 904→272）**必须先合入**（同改 `tests/inst/**` 与相关文档）
**可并行分片**：否（跨册文档统一改）
**预估**：1–1.5 h
**档位**：小改（纯文档/注释 + 一处宏硬化；复核 diff + 1 路注入 + 受影响门控 ≤15 min）
**状态**：已验证

## 背景（`m15-testcases-007` 交付时登记的残留）

`m15-testcases-007` 把故障例链式合并后（**904 → 272 镜像**），仓内仍有多处描述"**一例一镜像** / 两种镜像形态"，与现行为矛盾：

- **248 处 `.S` 注释**（分布在 **209 个文件**）仍写「一例一镜像」；
- `tests/inst/MIGRATION.md §2`、`tests/inst/inventory.md`、`docs/Process-07-门控分层规范.md` 仍按旧模型描述；
- 另有硬化项：`__PRINT` 是 do-while，**`len=0` 会死循环**（0 链例文件会撞到），`007` 已在收尾处用 `.if __NCHECK > 0` 兜住 —— 应把预判**收进宏本身**。

## 目标

1. **术语统一**：全部改为「**镜像 = 每 `.S` 一个**（链例 + 该文件的全部故障例顺序跑）」；`CASE_N=<pt>` 的**单例调试模式**仍保留，描述为「调试用单例模式」；
2. **`__PRINT` 硬化**：`len == 0` 时**直接返回**（不进入 do-while），并保留 `007` 收尾处的 `.if` 兜底（双保险）；加注释说明；
3. **文档三处同步**：`tests/inst/MIGRATION.md §2`、`tests/inst/inventory.md`、`docs/Process-07`（若有镜像计数，改成指向 `check-inst-asm` 现场值）；
4. 不改变任何用例、检查点、镜像数、退出码。

## 验收（真实 rc + 输出）

1. `grep -rc "一例一镜像" tests/inst docs` = **0**（历史归档 `.tao/archive/**` 不计；任务书本身的引用须显式排除并说明）；
2. `check-inst-asm` **272/272**（镜像数不变）、`check-case-ledger`、`check-tests-index`(472)、`check-inst-macro-scope`（含 S9）、`check-dirs`、`check-no-residue`；
3. **`__PRINT` 硬化可达 FAIL**：造一个 `len=0` 的宏调用（临时 `.S`，注入后必须**不死循环**且行为与 `.if` 兜底一致），`cp`+md5 还原；
4. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

只动 `tests/inst/**`（注释与 `__PRINT` 宏）、`tests/inst/MIGRATION.md`、`tests/inst/inventory.md`、`docs/Process-07-门控分层规范.md`、本任务书；**不动** `spec/`、`contracts/`、`components/**`、`tools/**`、测试期望；不提交 git；`cp`+md5 还原（禁 `git checkout/restore`）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-17）

**判决**：无未修 finding（小改：注释/文档 + 1 处宏硬化）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `.if \len > 0` 写在宏体内，须确认 MC 展开后能对 `(8 * __NCHECK)` 求值、且不改变既有镜像语义 | ✅已修 | `__PRINT` 循环体整体包进 `.if \len > 0`/`.endif`（汇编期求值，零长不产码） | 272 个 `.S` 全量编译并执行：`check-inst-asm` 272/272 |
| 收尾 `.if __NCHECK > 0` 可能被误判为多余而删除 | ✅已修（保留） | 未删；与宏内预判构成双保险，注释写明两层分工 | 证据脚本断言两处 `.if` 均在场 |
| 248 处替换可能误伤代码行 | ✅已修 | 仅替换 `@@` 注释；`git diff -U0 -- '*.S'` 非注释改动行 = 0 | 同上命令输出 0 |
| `inventory.md`/`Process-07` 仍按 `007` 前口径写「故障例逐个比 monitor 退出码」 | ✅已修 | 改为「镜像 = 每 `.S` 一个（链例 + 全部故障例顺序跑）；比结果字节流；故障例不符 ⇒ 退出码 ≠ 0；`-defsym` = 调试用单例模式」 | 通读 diff；`validate-vectors` PASS |
| `docs/Process-07` 无 inst 镜像计数 | ⏸延后（不适用） | 无计数可改；补「镜像数/检查点数现场派生，不写死」 | 该文件全文 `grep 272/904` 无命中 |
| 同文件仍写「每册目录内 `.lds`（无则 01 册默认）」，与 `m15-testcases-006` 统一布局不符 | ⏸延后 | 超本任务范围，未改；已记「新发现」 | — |
| `make check` 三红是否本任务引入 | ❌不修 | 改动全在 `tests/inst/**` + `docs/Process-07`；三红分别指向 linux 组件源超前补丁集、`m16-chipyard-001` 台账未移入进行中、`m14-linux-012` 旧日志命名 | 见完成区「遗留问题」 |

### 第 1 轮 reviewer 验收（2026-11-17）

**判决**：**Accepted**（小改档：diff + 2 路独立注入 + 受影响门控；结论全部基于本人重跑，未采信完成区数字）。

**重跑记录（rc 均本人自采，无 `| tee`）**
- `git rev-parse --show-toplevel` = 本 worktree；基线与收尾 `git status --porcelain -uall` **均空**、HEAD 始终 `f10b511a`（未新增提交）。
- `git diff --name-only 87472016..HEAD | wc -l` = **216**（209 `.S` + 1 `.inc` + 6 `.md`）；越界文件 = **0**（全部 ∈ `tests/inst/**` + `docs/Process-07-门控分层规范.md` + 本任务书；`spec/`、`contracts/`、`components/**`、`tools/**` 零改动）。
- `git diff -U0 -- '*.S'`：变更行 496（+248/−248），内容以 `@@` 起者 496，**非 `@@` 注释行 = 0**（`.S` 代码零改动）。
- `grep -ro "一例一镜像" tests/inst docs | wc -l` = **0**（`grep -rn` 无命中 rc=1）；本任务书 6 处引用在 `.tao/tasks/**`（扫描域外，完成区已显式说明排除）。
- `make check-inst-asm` rc=**0**：`272/272 镜像通过（272 个 id；链例 + 故障链 633 例）`、`jobs=62`（核数−2）。
- `check-case-ledger` rc=0（现场身份 5438 条）；`check-tests-index` rc=0（`inst=272/arch=11/unit=186/tset=3/total=472`）；`check-inst-macro-scope` rc=0（含 S9、三分层 + 死宏 0）；`check-dirs` rc=0；`check-no-residue` rc=0。
- 证据脚本审计 + 重跑：`bash .work/evidence/<任务ID>/run.sh` rc=**0**，**31/31 PASS**；断言均有可达 FAIL 路径、无恒真、rc 直采。

**注入清单（独立、任务书未列；`cp`+md5 还原，禁 checkout/restore/stash/show/reset）**
1. **硬化可达 FAIL**：`inst_test.inc` 宏内 `.if \len > 0` → `.if 1`（md5 `da047db9…`→`7f5cddc3…`、`git status` 命中该文件）+ 临时载体在链例主路径 `__PRINT TEST_BUF, 0` ⇒ `run_asm_suite` **rc=1**（`{'qemu': -2}` 超时、输出 8359680 B）；直接 `timeout 15 qemu …` ⇒ **rc=124**（7982551 B 死循环）。`cp` 还原 → md5 相等 → 重跑 **rc=0 / 80 B** 回绿。（首版插点落在 `__fc_13` 的 `__EXIT` 失败路径后不可达 ⇒ 误绿，改插 `__TEST_BEGIN` 后复验；现场留 `inj/{inject,inject2,restore}.out`）
2. **术语回潮**：`ld.o_rrii_ra.S` 的 `@@` 注释加回「一例一镜像」⇒ `grep -ro | wc -l` = **1**（判据可被违反）；`cp` 还原 → md5 相等 → **0**。

**`make -k check` 三红逐项归因（rc=2；仅 3 目标红，其余全 PASS）**
- `check-patch-tree`（15 problem）：断言全指 `arch/dadao/**`（linux 组件源超前补丁集）；本 diff 无组件路径 ⇒ **外因**。
- `check-milestones-fresh`（1 VIOLATION）：`m16-chipyard-001` 有 worktree 但 m16 台账在「待开始」（`git worktree list` 可见其在途）；本任务的 m14/m15 台账均 PASS ⇒ **外因**。
- `check-run-artifacts`（7 problem）：`.work/log/m14-linux-012/*`、`.work/log/gem5/restore-after-inject.log`、`.work/log/linux/archived-tmp/*`；本任务证据落 `.work/evidence/<任务ID>/`（不入 `.work/log/`）⇒ **外因**。
- 三红与本 diff 交集 = **0**（diff 路径域仅 `tests/` 214 + `docs/` 1 + `.tao/` 1）。

**遗留（非阻断）**：① 建议 `grep -r "一例一镜像" tests/inst docs` 进 L1 防回潮；② `docs/Process-07`「每册目录内 `.lds`」与 `m15-testcases-006` 布局不符（超本任务范围，engineer 已记「新发现」）。

## 完成区

**测试结果**：一键证据脚本 `.work/evidence/<任务ID>/run.sh` **31/31 PASS**（rc=0，含 1 路反例注入 → 还原回绿）；验收门控全 rc=0：`check-inst-asm` 272/272、`check-case-ledger`、`check-tests-index`（`total=472`）、`check-inst-macro-scope`（含 S9）、`check-dirs`、`check-no-residue`。
**修改文件**：`tests/inst/**/*.S` 209 个（仅 `@@` 注释，共 248 行）、`tests/inst/macros/inst_test.inc`、`tests/inst/MIGRATION.md` §2、`tests/inst/README.md`、`tests/inst/schema.md`、`tests/inst/inventory.md`、`docs/Process-07-门控分层规范.md`、本任务书。
**验收结果**（真实输出）：
- `grep -ro "一例一镜像" tests/inst docs | wc -l` = `0`（扫描域 = `tests/inst` + `docs`；`.tao/archive/**` 历史归档与 `.tao/tasks/**` 本任务书均不在扫描域，故天然排除）。
- `run_asm_suite: 272/272 镜像通过（272 个 id；链例 + 故障链 633 例）`；`check-tests-index`：`inst=272 / arch=11 / unit=186 / tset=3 / total=472`；`check-case-ledger`：`现场身份 5438 条（asm 4917 / lit 521）`。
- `__PRINT` 双保险：宏内 `.if \len > 0`（零长不产码）+ 收尾 `.if __NCHECK > 0`；临时载体显式 `__PRINT TEST_BUF, 0` 与 0 检查点对照组（走收尾兜底）均 rc=0、输出 0 B（行为一致）。
- 可达 FAIL：删掉宏内预判 ⇒ 同一载体 20 s 超时 rc=**124**（死循环）；`cp` 还原后 md5 与注入前一致（`da047db9…`），rc=0 回绿；注入后 `git diff --name-only` 命中该文件（非空注入）。
- 附加回归：`check-asm-list`、`check-asm-prose`、`validate-vectors`（`156/156 M1 identities`、`272 .S carriers`）全 rc=0。
**新发现/坑**：
- `docs/Process-07` 该行仍写「每册目录内 `.lds`（无则 01 册默认）」，与 `m15-testcases-006` 的统一链接布局不符 ⇒ 建议另立小任务（本任务只改镜像口径，未动此句）。
- `make check` 在本 worktree 3 红，均与本次 diff 零交集：`check-patch-tree`（linux 组件源超前仓库补丁集，m14-linux 在途）、`check-milestones-fresh`（`m16-chipyard-001` 有 worktree 但台账仍在待开始）、`check-run-artifacts`（`m14-linux-012` 等旧日志命名）。
- 可机械判的术语口径：`grep -r "一例一镜像" tests/inst docs` 建议进 L1 防回潮。
**遗留问题**：上述 `make check` 三红（共享在途状态，非本任务引入，未处置）；`docs/Process-07` 无 inst 镜像计数，故未加「指向现场值」的数字，改为口径描述 + 「镜像数现场派生，不写死」。
