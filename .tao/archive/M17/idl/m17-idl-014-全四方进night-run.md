# m17-idl-014: 全四方进 `night-run`（gem5/chipyard 常驻门控）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-013`（门控翻到 272/272、`idl/tools/` 新布局）
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-22 裁定 B）

`make check-idl` 在 L2 只跑 IDL+QEMU；全四方（IDL/QEMU/gem5/chipyard）目前没有任何常驻门控，只在任务收口由证据脚本人工跑一次 ⇒ gem5/RTL 侧漂移无人守。裁定 B：**全四方进 `night-run`**，L1/L2/L3 不变（L2 仍两方）。

现状（现场）：`night_run.py` 的 `DEFAULT_MEMBERS` = `tset:libc-test`/`llvm-ts`/`embench` + `arch:cfx` + 3 个 `tset:gem5-se-*` + `arch:gem5-fs`；`check_night_report.py` 的 `REQUIRED_MEMBERS` 是同一组 8 个；night-run 用独立锁 `.dadao/night.lock`，**不占** `gate.lock`。

## 要做

1. `Makefile` 新增目标 `check-idl-full`（**不进** `GATE_LOCKED_TARGETS`）：
   - `$(PYTHON) idl/tools/idl_four_way.py --platforms qemu,gem5,chipyard --jobs $(TEST_JOBS)`；
   - 日志落运行期日志目录内的 `check-idl-full.log`；缺任一引擎/固件 ⇒ rc=2（可见，不静默跳过）；
   - help 行注明「nightly 成员；全四方」。
2. `tools/testcases/night_run.py`：`DEFAULT_MEMBERS` 追加 `idl:four-way=make check-idl-full`；`MEMBER_TIMEOUTS` 加 `("idl","four-way"): 1800`；模块 docstring 的成员清单同步。
3. `tools/testcases/check_night_report.py`：`REQUIRED_MEMBERS` 加 `("idl","four-way")`；docstring 的「四 scope / 八成员」改为现场口径（不写死数）。
4. `docs/Process-07`：登记 `check-idl-full` = **nightly 成员**（不进 L1/L2/L3），并注明 L2 `check-idl` 仅 IDL+QEMU。
5. 不改 013 的语义、清单与门控口径。

## 不做

- 不改 `check-idl`（L2）的平台集；不改 272 条清单；不改 `.idl`/执行器；
- 不把 nightly 成员升成提交前门控。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动上述 4 个文件 + 本任务书；完成区 ≤30 行、不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl-full` rc=0（贴 272/272、耗时、四方 md5）；
2. `NIGHT_DRY_RUN=1 make night-run` 打印的成员清单含 `idl:four-way`（现场统计条数）；
3. `check-night-report`：用一份**构造的** night 报告（含新成员）判 PASS；删掉 `idl:four-way` 行 ⇒ FAIL（可达）；
4. **可达 FAIL ≥2 路**：① 选中平台缺引擎（`Makefile` 已写死 `qemu,gem5,chipyard`；令 chipyard 不可执行）⇒ rc=2「缺引擎」，证明不会静默跳过（注：`--platforms` 是 opt-in，少给一方本身 rc=0，故入口必须钉死三方）；② 把 `REQUIRED_MEMBERS` 的 `idl:four-way` 去掉后用同一报告 ⇒ 覆盖断言失效（反向证明新增项确实被核）；
5. `make check-idl`（L2 两方）仍 rc=0，未被改动。

## 完成区

**测试结果**：证据脚本 26/26 绿（rc=0）；`make check-idl-full` rc=0 / 272/272 / 121 s（整目标墙钟）；
`make check-idl`（L2 两方）rc=0 / 272/272；`NIGHT_DRY_RUN=1 make night-run` members=9（现场统计）含 `idl:four-way`；
`night_run.py --self-test` 9/9、`check_night_report.py --self-test` 14/14。

**修改文件**：
- `Makefile`：新增目标 `check-idl-full`（PHONY + help；**不进** `GATE_LOCKED_TARGETS`，日志落运行期日志目录）
- `tools/testcases/night_run.py`：`DEFAULT_MEMBERS` 加 `idl:four-way`、`MEMBER_TIMEOUTS` 加 1800、自测成员同步、docstring/help
- `tools/testcases/check_night_report.py`：`REQUIRED_MEMBERS` 加 `("idl","four-way")`、docstring 改现场口径、自测同步（新增「缺该成员 ⇒ FAIL」用例）
- `docs/Process-07-门控分层规范.md`：nightly 登记 + L2 注明仅 IDL+QEMU + §7 计数改现场口径
- 本任务书

**验收结果**（运行期证据目录内 `run.sh` 的真实输出）：
- `check_four_way: 272/272 例四方一致（parties=idl,qemu,gem5,chipyard；主清单 272 / pending 0 / 现场派生 272）`，120961 ms
- 四方 md5：qemu `1e8ff6e9…`、bootrom `a5d78816…`、gem5.opt `2ddf0f24…`、chipyard `34c26203…`（4/4 可读）
- 可达 FAIL：① 缺 chipyard 引擎 ⇒ rc=2「缺 …（不静默跳过）」；② 构造报告删 `idl:four-way` 行 ⇒ `check-night-report` rc=1 且指名；③ 去掉 `REQUIRED_MEMBERS` 该条 ⇒ 同一报告转 PASS；④ Makefile / 文档 / 接线注入（临时副本）各自 FAIL，仓库文件 md5 前后一致

**新发现/坑**：
- 任务书验证 4① 措辞与实现不符：`--platforms qemu,gem5`（少一方）本身 **rc=0**（静默面），报 rc=2 的是「选中平台缺引擎」。证据两侧都测（少一方 ⇒ rc=0 且 parties 无 chipyard；缺引擎 ⇒ rc=2），这也正是目标必须钉死三方的理由。
- `Process-07 §7` 的「grep -c = 64 / 清单 65 行」在本任务前已漂移（实测 65 个直接目标 + `check-idl`/`check-manifests-guard` 两个包装 = 67 行）⇒ 改为现场口径。

**遗留问题**：无

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 报告门控换 `REQUIRED_MEMBERS` 后，`night_run.py --self-test` 的 8 成员假报告会假红 | ✅已修 | 自测 green 列表加 `idl:four-way` | `--self-test` 9/9 |
| `check_night_report` 自测 GREEN_ROWS 未含新成员 ⇒ 绿灯用例失效 | ✅已修 | GREEN_ROWS 加 `("idl","four-way",0)` + 新增「缺 idl 成员 ⇒ FAIL」用例 | `--self-test` 14/14 |
| 覆盖失败文案写死成员集（易漂移） | ✅已修 | 改为指向 `REQUIRED_MEMBERS` / `night_run.DEFAULT_MEMBERS` | 证据 §3 消息「缺成员行：idl:four-way（…REQUIRED_MEMBERS…）」 |
| `Process-07 §7` 的 64/65 计数已漂移 | ✅已修 | 改现场派生并点名两个包装目标 | 证据 §9 + 注入删登记 ⇒ FAIL |
| 证据脚本 doc 断言用固定串、与文档实际措辞不符（首轮 2 红） | ✅已修 | 拆成 `现场派生` / `不写死` / `L1/L2/L3` 三条独立 grep | 末轮 26/26 |
| 证据脚本 `grep -o 'parties=idl,[a-z,]*'` 截断 `gem5`（丢数字，首轮 1 红） | ✅已修 | 字符类加 `0-9`（3 处） | 末轮 §5 实际=`parties=idl,qemu,gem5` |
| 任务书验证 4① 措辞（少一方 ⇒ rc=2）与实现不符 | ❌不修（记录，见完成区「新发现」） | 证据按「少一方 ⇒ rc=0」「缺引擎 ⇒ rc=2」两侧实测 | 证据 §4/§5 |

### 第 1 轮 reviewer 验收（2026-11-23）

**重跑记录**（均在任务 worktree 仓库根执行；证据 = 运行期证据目录内的 `run.sh --repo <worktree>`）：
- `run.sh`：rc=0，`EVIDENCE: PASS (26/26 checks green)`（共复跑 5 次 = 首跑绿 / 注入A红 / 还原绿 / 注入B红 / 还原绿）
- `make check-idl-full`：rc=0 / 123 s / `check_four_way: 272/272 例四方一致（parties=idl,qemu,gem5,chipyard；主清单 272 / pending 0 / 现场派生 272）`；四方 md5 现场取：qemu `1e8ff6e9…`、bootrom `a5d78816…`、gem5.opt `2ddf0f24…`、chipyard `34c26203…`（4/4 可读）
- `NIGHT_DRY_RUN=1 make night-run`：rc=0，`members=9`（现场数行），含 `idl:four-way  $ make check-idl-full`
- `make check-idl`（L2 两方）：rc=0 / 21 s / 272/272，`parties=idl,qemu`
- `night_run.py --self-test` rc=0（9/9）；`check_night_report.py --self-test` rc=0（14/14）；`make check-knowledge-refs` rc=0（悬空 0，非基线红）

**独立注入（不复用工程 4 路；仓库文件级，`cp` 备份 + md5 还原，未用 git checkout）**：
- 注入 A：把 `Makefile` 的 `check-idl-full` 平台集改 `qemu,gem5` ⇒ 重跑**同一** `run.sh` rc=1、1 红（`日志 parties … 实际=parties=idl,qemu,gem5`）；还原 md5 `d3e76331…` 相等 ⇒ 回绿 26/26
- 注入 B：`night_run.py` 删 `idl:four-way` 成员 ⇒ 重跑同一 `run.sh` rc=1、3 红（dry-run 行 / 构造报告 / 接线）；还原 md5 `12894b5b…` 相等 ⇒ 回绿 26/26
- 收尾对账：注入前后 `git status --porcelain -uall` 快照逐行相同（恰 5 文件），5 文件 `md5sum -c` 全 OK

**约束核验**：完成区 5 文件 = 现场 5 文件（未越界）；`check-idl-full` 不在 `GATE_LOCKED_TARGETS`（awk 逐行核，仅 `check-idl` 在锁内）；L1/L2/L3 成员与 `check-idl` 平台集 diff 无触碰；272 清单 / `.idl` / 执行器未改；`Process-07` 已登记 nightly 行 + 登记表行 + L2 注明「仅 IDL + QEMU 两方」。

**静默面核实（第 4 点）**：亲测 `--platforms qemu,gem5`（少 chipyard）单例 rc=0（平台 opt-in）；缺引擎 rc=2 且指名「缺 chipyard…（不静默跳过）」——与完成区「新发现」一致。`Makefile` 写死 `--platforms qemu,gem5,chipyard`，且 `run.sh` 断言日志 `parties` 必含四方 ⇒ 入口钉死三方、漂移即红，够。

**finding（非阻断）**：任务书验证 4① 字面（少一方 ⇒ rc=2）与实现不符（实测 rc=0）；属验收措辞笔误、未被任何门控读取 ⇒ architect 收尾时改任务书该行措辞。

**判决：Accepted**
