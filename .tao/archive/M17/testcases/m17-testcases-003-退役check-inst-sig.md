# m17-testcases-003: 退役 `check-inst-sig`（`check-idl` 为超集）

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-idl-013`（`check-idl` 覆盖 272 例后才退役）
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-22 裁定 A）

`check-inst-sig`（L2，QEMU 单平台，272 镜像逐槽 vs `tests/data/inst-signature/expected.tsv`）与 `check-idl`（L2，013 后 272 例，对每一方都比同一份 `expected.tsv` 再四方互比）**在同一层重复判同一件事**。`Process-07 §4` 要求「一个检查只在一层」。裁定 A = 退役 `check-inst-sig`。

保留：`expected.tsv` 派生（`make inst-signature-data`）、`tests/shared/signature.py`、`.S` 内联期望——它们都是 `check-idl` 的输入。

## 要做

1. `Makefile`：
   - 从 `_locked-check-modules`（L2 列表）删除 `check-inst-sig`；从 `GATE_LOCKED_TARGETS` 删除；
   - 删除 `_locked-check-inst-sig` 目标与 `INST_SIG_LOG`（确认无其它使用者）；
   - 删除 help 里的 `make check-inst-sig` 行 / PHONY 项；
   - **保留** `inst-signature-data`（它调 `check_inst_sig.py --write`）。
2. `tools/testcases/inst/check_inst_sig.py`：保留脚本与 `--write`（生成 `expected.tsv`、`inputs.sha256`）；usage/docstring 改为「期望值生成器；执行门控已退役，槽级判据在 `check-idl`」，避免误导。
3. `docs/Process-07`：
   - L2 表行删除 `check-inst-sig`，写明「签名区槽级判据已并入 `check-idl`（`m17-testcases-003`）」；
   - §7 表删除该行（或标「已退役」并指向 `check-idl`）。
4. `tools/testcases/README.md` 与 `tests/data/inst-signature/README.md` 中指向 `make check-inst-sig` 的 operational 说法改为「生成用 `make inst-signature-data`；执行判据见 `check-idl`」。
5. 不改 `expected.tsv`、`signature.py`、`tests/inst` 载体、`check-idl` 本身。

## 不做

- 不删 `check_inst_sig.py`（`--write` 仍是 `expected.tsv` 的唯一生成入口）；
- 不改历史任务书 / `.tao/archive/**`。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动 `Makefile`、`tools/testcases/inst/check_inst_sig.py`（docstring/usage）、`docs/Process-07`、`tools/testcases/README.md`、`tests/data/inst-signature/README.md`、本任务书；
- 完成区 ≤30 行、不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl` rc=0（272/272）；`make check-inst-asm` rc=0（未被影响）；
2. **L2 成员断言（现场派生）**：`_locked-check-modules` 的前置列表里不含 `check-inst-sig`（从 Makefile 文本现场解析，不写死）；`GATE_LOCKED_TARGETS` 同样不含；
3. `python3 tools/testcases/inst/check_inst_sig.py --help` 可运行；`make inst-signature-data` 目标仍在（**不执行 `--write`**，避免重写期望；只断言目标存在且脚本可解析）；
4. **可达 FAIL 2 路**：① 把 `check-inst-sig` 加回 `_locked-check-modules` 前置 ⇒ 成员断言红；② 在 `docs/Process-07` 的 L2 行加回该名 ⇒ 文档一致性断言（grep 口径）红；均 `cp`+md5 还原后回绿；
5. `check-manifests-guard`/`check-dirs` rc=0。

## 完成区

**测试结果**：证据脚本 `run.sh` **PASS=16 / FAIL=0，rc=0**（`make check-idl` 272/272、`make check-inst-asm` 272/272、`check-manifests-guard`/`check-dirs` PASS、2 路注入红→`cp`+md5 还原→绿）。
**修改文件**：`Makefile`、`tools/testcases/inst/check_inst_sig.py`（docstring/`--write` help）、`docs/Process-07-门控分层规范.md`（L2 行 + §7 删行）、`tools/testcases/README.md`、`tests/data/inst-signature/README.md`、本任务书（未提交 git；`expected.tsv`/`signature.py`/`tests/inst`/`check-idl` 未动）。
**验收结果**：
- L2 成员现场解析：`_locked-check-modules` = `check-inst-asm check-idl check-arch-smoke check-unit …`（无 `check-inst-sig`）；`GATE_LOCKED_TARGETS` 同；`.PHONY`/help 无；`_locked-check-inst-sig` 目标与 `INST_SIG_LOG` 已删；`inst-signature-data` 仍在且 recipe = `check_inst_sig.py --write`。
- `check-idl` 输出 `check_four_way: 272/272 例四方一致（parties=idl,qemu；主清单 272 / pending 0 / 现场派生 272）`，rc=0；`check-inst-asm` `272/272 镜像通过`，rc=0；`check_inst_sig.py --help` rc=0（含「生成器」）。
- 注入① 加回 L2 前置 ⇒ `AssertionError: _locked-check-modules still lists check-inst-sig`（md5 a73966e5→5f621e47）；注入② 加回 L2 文档行 ⇒ `Process-07 L2 row still lists check-inst-sig as member`（md5 d635eead→c3a8d94b）；均 `cp`+md5 还原回绿。
- **未用** `make -n check-modules`（会真跑 L2）；未执行 `--write`。
**新发现/坑**：`.tao/knowledge/nodes.md` L157/161/195 仍写「现行门控 `check-inst-sig`」，属知识库、按规则留给主会话 `/complete` 更新；`tests/inst/macros/inst_test.inc:177` 注释仍提 `make check-inst-sig` 诊断——改它会使 `inputs.sha256` 漂移，且任务禁改 `.S` 载体，故未动。
**遗留问题**：上述两处文案待后续任务/`/complete` 同步；无功能遗留。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `inst_test.inc`/`nodes.md` 仍提旧门控 | ⏸延后 | 未改（超出任务书文件集；改 `.inc` 会改 `inputs.sha256`） | 已在「新发现/坑」登记 |
| 数据 README 的「门控」措辞残留（relation/unwritten/诊断） | ✅已修 | 改为「比对/`check-idl` 报/旧诊断路径（非门控）」 | static 断言绿；重跑 `run.sh` PASS=16 |
| run.sh 首版 block 解析用 `=` 未匹配 target 的 `:`（假红） | ✅已修 | `^name\s*[:=]` | 注入前后 GREEN/RED 与预期一致 |
| 文档断言把「已退役」提及误判为仍在宣称 | ✅已修 | 仅禁「含 `make check-inst-sig` 且不含『退役』」的行 | 注入②仍可达 RED |
### 第 1 轮 reviewer 复核

| # | 核项 | 结果 |
|---|---|---|
| 1 | 重跑运行期证据目录内 `run.sh` | rc=0，`SUMMARY: PASS=16 FAIL=0`（`check_four_way: 272/272` make rc=0、`run_asm_suite: 272/272 镜像通过` rc=0、guard/dirs PASS、2 路注入红→还原→绿） |
| 2 | `--help` 独立重跑 | rc=0，docstring 首行即「生成器」，并写明「执行判据已并入 L2 check-idl」 |
| 3 | Makefile 现场解析（未用 `make -n`） | `_locked-check-modules` = `check-inst-asm check-idl check-arch-smoke …`（无 `check-inst-sig`）；`GATE_LOCKED_TARGETS`、`.PHONY`、help 均无；`_locked-check-inst-sig`/`INST_SIG_LOG` 0 处；`inst-signature-data` recipe = `check_inst_sig.py --write` |
| 4 | 保留物 vs HEAD | `expected.tsv`/`inputs.sha256`/`signature.py`/`tests/inst/**` 零 diff；`check_inst_sig.py` 16 行改动全在 docstring + `--write` help |
| 5 | 文档 | Process-07 L2 行含「签名区槽级判据已并入…原 check-inst-sig 退役」，§7 无该行；两份 README operational 已改；仓内剩余提及=Makefile/文档「已退役」注释 + 脚本日志前缀 + `nodes.md` L157/161/195 + `inst_test.inc:177` + 台账/任务书 |
| 6 | reviewer 独立注入 2 路（不复用工程路） | ① `.PHONY` 加回 `check-inst-sig` ⇒ 静态断言红，run.sh rc=1（PASS=13/FAIL=3）；② `inst-signature-data` recipe 改成 `echo` ⇒ 断言 `recipe lost --write` 红，rc=1；均 `cp`+md5 还原（a73966e5 回位）后 rc=0 PASS=16 |
| 7 | 越界对账 | 前后两次 `git status --porcelain -uall` 快照逐行相同，= 完成区 6 文件；无 untracked；`check-knowledge-refs` rc=0 |
| 8 | 遗留 | `nodes.md` L157/161/195 旧门控名属知识库、任务书禁改 ⇒ 主会话 `/complete` 范畴；`inst_test.inc:177` 改动会使 `inputs.sha256` 漂移（已核实该文件在其内）且属禁改载体 ⇒ 未动合理 |

finding：F1 `nodes.md` 三行仍写「现行门控 `check-inst-sig`」（文档级，留 `/complete`）；F2 `inst_test.inc:177` 注释残留（同上，改则动 `inputs.sha256`）。均不阻断。

**判决：Accepted**（重跑 rc=0 / PASS=16，272/272 两项独立成立，2 路独立注入可达 FAIL 且还原回绿，约束无违反）

