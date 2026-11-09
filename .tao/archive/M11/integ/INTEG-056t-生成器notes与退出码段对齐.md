# INTEG-056t: 生成器 notes 与 §7.1 对齐（generator-sync 回绿）

**模块**：integ
**项目里程碑**：M11
**依赖**：`INTEG-055t`（已验证；退出码三段式迁移）
**状态**：已验证

## 执行环境
本地；只改生成器内的 notes 文本并重渲染，不改向量语义/期望值/判据。

## 现状

`INTEG-055t` 把 `tests/inst/base/ctrl-{jump,call,ret}.yaml` 的 notes 里旧退出码（`0x81`/`0x88`/`0x8A`/`0x8B`）删掉或改为「monitor」，但**手工改 yaml**、未同步生成器 `tools/testcases/generate_ctrl_jump_call_ret.py` 里的同名字符串。

L2 `make check-modules` 因此在 `check-generator-sync` 红：

```
FAIL: tests/inst/base/ctrl-jump.yaml 与重渲染结果不一致
FAIL: tests/inst/base/ctrl-call.yaml 与重渲染结果不一致
FAIL: tests/inst/base/ctrl-ret.yaml 与重渲染结果不一致
generate_ctrl_jump_call_ret --check: FAIL
```

## 目标

1. 以**已入库 yaml 为期望**，把生成器里对应的 notes 字符串改成同一文本（共 10 处，diff 见 `git show` 的 `INTEG-055t` 提交：`ctrl-jump` 2 处、`ctrl-call` 3 处、`ctrl-ret` 5 处）。
2. 重跑生成器渲染，确认三册 yaml **byte-identical**（无内容变化）。
3. 不改 `expected_fault`/`expected_state`/`expected_pc`/编码字/`spec_cite`/用例集。
4. 若发现 yaml 与生成器差异不止 notes（语义字段也被手工改），停止并报告，不得擅自改语义。

## 范围 / 非范围

**在范围内**：`tools/testcases/generate_ctrl_jump_call_ret.py`（仅 notes 字面量）、本任务书、`milestones.md`。

**不在范围内**：`tests/inst/base/*.yaml`（期望保持现入库内容不变）、`spec/**`、ADR、`contracts/**`、QEMU/gem5 源树与补丁。

## 验收标准

1. `python3 tools/testcases/generate_ctrl_jump_call_ret.py --check` rc=0（3 册 byte-identical）。
2. `git status --porcelain -uall` 不出现 `tests/inst/base/ctrl-*.yaml`（yaml 未变）。
3. `make check-modules JOBS=32` rc=0（或若仍有其它失败，逐条给出真实 rc 与归属，区分环境红）。
4. `make check`（L1）rc=0。
5. 反例：把生成器某条 notes 改回旧码（如 `0x81`）⇒ `--check` rc=1；`cp`+`md5sum -c` 还原回绿（禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 修复方向是**生成器对齐产物**，不是产物对齐生成器：yaml 里的 notes 已按 `Machine-v5 §7.1` 更新，生成器是滞后的一侧。
- 只动字面量文本；不得为了过门控而放宽 `--check` 判据。

## 完成区

**测试结果**：`generate_ctrl_jump_call_ret.py --check` rc=0（3 册 byte-identical）；独立重渲染 `cmp` 3/3 相同；解析后逐用例逐字段比对 3 册差异字段 = NONE；`make check`（L1）rc=0；`make check-modules JOBS=32` rc=2，唯一红点为 `check-generator-sync`（本任务 3 册全 OK，红点来自范围外 3 个生成器漂移（`ctrl_br`/`mem_vectors`/`misc`），见遗留问题）。
**修改文件**：`tools/testcases/generate_ctrl_jump_call_ret.py`（仅 4 处 notes 字面量）、本任务书、`.tao/knowledge/milestones.md`；另交付未入库运行期证据脚本。
**验收结果**：
- 生成器实际只差 4 处（任务书写的「10 处」是 055t 全部 notes 改动数，其中 6 处该提交已同步，余 4 处）：jump-iiii boundary →「CFXMEM（当前运行模式 monitor，spec/Machine-v5 §7.1）」；call-iiii RASOF 去「(0xFA)」；ret D4b RASUF 与 D4a RASUF 各去「(0xFB)」。
- 未改 `expected_fault`/`expected_state`/`expected_pc`/`encoding.word`/`spec_cite`/用例集：结构比对 3 册 `差异字段=NONE`。
- 反例：`sed` 注入 `CFXMEM (0x81)`（2 行，`git diff --name-only` 非空）⇒ `--check` rc=1（jump/call 两册 FAIL、ret 仍 OK）⇒ `cp` 备份 + `md5sum -c` 还原 ⇒ rc=0 回绿。
- `git status --porcelain -uall` 仅 1 个 `M`（生成器），无 `tests/inst/base/ctrl-*.yaml`。
- 证据脚本：默认（快检 + 注入自检）PASS；`RUN_L1=1` 下 `make check` rc=0 PASS；`RUN_L2=1` 断言「3 册 OK=3 + 已知范围外 FAIL=1 + 未知 FAIL=0」PASS。文档改动后复跑 `make check` rc=0（含 `check-milestones-fresh`）。
**新发现/坑**：① `check-generator-sync` 的红行是 `FAIL: <path> …`（带冒号），按 `^FAIL ` 解析会得到 0 条而假绿（本任务证据脚本首版踩到，已改为 `^FAIL[: ]` 并区分「已知范围外」与「未知」）。② 055t 只同步了部分生成器：ctrl-br（10 处）、mem-ra/rb/rd（monitor 措辞 + 换行）、misc（纯换行）仍漂移；逐字段比对显示 mem/ctrl-br 差异字段仅 `notes`、misc 为 `NONE`，**无语义漂移**。③ `check-milestones-fresh`：非 `已验证` 行的「完成时间」只能是 `YYYY-MM-DD HH:MM（登记）`，写「（实现）」等注即红（本任务已踩并修正）。
**遗留问题**：`make check-modules` rc=2 的全部原因均在本任务范围外（本任务未触碰对应生成器与 yaml，属 055t 同类残留，需独立任务）：`generate_ctrl_br --check` FAIL（L2 中该册是首个红点，故 make 未继续到 mem/isa/misc/bitcnt）；单独实测 `generate_mem_vectors --check` rc=1（mem-ra/rb/rd mismatch）、`generate_misc --check` rc=1（仅换行）、`generate_isa_vectors`/`generate_bitcnt_vectors` rc=0。

## 审阅记录

### 第 1 轮 engineer 自审

范围：`tools/testcases/generate_ctrl_jump_call_ret.py` 的 4 处 notes 字面量 + 证据脚本。逐行对照已入库 yaml 的 notes 文本；核对字符串拼接后与 yaml 完全一致（含全角括号、`；/;` 标点、`§` 与空格）；确认未触碰任何 `_case(...)` 的语义实参。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| jump-iiii boundary 若自拟措辞，会与 ctrl-br 已入库文案不一致（同一语义两种写法） | ✅已修 | 采用与 ctrl-br yaml 相同的「CFXMEM（当前运行模式 monitor，spec/Machine-v5 §7.1）」 | `cmp` 逐字节相同 |
| 证据脚本用 `^FAIL ` 匹配不到 `FAIL:` 行 ⇒ 「已知范围外 FAIL=0」恒真（假绿） | ✅已修 | 改用 `^FAIL[: ]`，并拆分 `other_fail`/`unknowable` 两个计数 | `RUN_L2=1` 实跑：3 册 OK=3、已知范围外 FAIL=1、未知 FAIL=0 |
| `--check` 只比字节，不能证明语义字段未变 | ✅已补 | 证据脚本新增「解析结构逐字段比对」步骤，差异字段非空即红 | 3 册 `差异字段=NONE`；该步骤可达 FAIL（注入 0x81 时 jump/call 的 notes 字段即不同） |

### 第 1 轮 reviewer 验收

**判决：Accepted**（验收命令在我自己的重跑下全部达标；范围外红点归属经独立复核正确）。本轮我只改本审阅记录。**快照对账**：审前/审后 `git status --porcelain -uall` 均 3 行（`milestones.md`、本任务书、生成器）、0 未跟踪；生成器注入前 md5 `a055e95ebb6aae0b5870e016c67e2222`，注入→还原后 `md5sum -c` `OK`，`diff` 快照 `SNAPSHOT_IDENTICAL=1`、`status` `STATUS_IDENTICAL=1`；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`。

**重跑记录（我的输出/退出码）**：
- `python3 tools/testcases/generate_ctrl_jump_call_ret.py --check` → **rc=0**（`OK:` ×3 + `PASS（3 册 byte-identical）`）。
- `make check`（L1）→ **rc=0**（尾行 `repository checks (L1): PASS`；日志 `^FAIL[: ]` 0 条）。
- `make check-generator-sync` → **rc=2**（`make: *** [Makefile:1666: check-generator-sync] Error 1`）：本任务 3 册 `OK` ×3、`generate_ctrl_jump_call_ret --check: PASS`，首红 `FAIL: …/ctrl-br.yaml 与重渲染结果不一致`。make 首红即停 ⇒ 我另逐个独立复跑：`generate_mem_vectors --check` **rc=1**（mem-rd/rb/ra mismatch）、`generate_misc --check` **rc=1**、`generate_isa_vectors` **rc=0**、`generate_bitcnt_vectors` **rc=0** —— 与 `INTEG-057t` 任务书「现状」四行逐条吻合，红点归属 `INTEG-057t` 正确（本任务不要求全绿）。
- `make check-modules JOBS=32` → **rc=2**，全日志 `^FAIL[: ]` 仅 `ctrl-br.yaml 与重渲染结果不一致` + `check-generator-sync Error 1`，我方 3 册 `OK` ×3（与完成区所述 rc=2、唯一红点一致）。
- 运行期证据脚本：逐条审断言（1/2/3/4/5 与 `RUN_L1`/`RUN_L2` 分支均有可达 FAIL 路径；步骤 5 断言 `inj>=1 && rc=1` 在 sed 模式失配时即红，非恒真）→ 我重跑 **rc=0**（`INTEG-056t evidence: PASS（fails=0）`，含 3 册 `差异字段=NONE`）。
- 范围：`git diff --name-only` = 本任务书 / `milestones.md` / 生成器 3 行；`git diff -- tests/inst/base/` 空；`git status -uall` 无 `tests/inst/base/ctrl-*.yaml`、无 `??`。

**独立比对（不采信完成区）**：把 `git show HEAD:` 版与当前版生成器各放进一个**仓库外的运行期临时树**渲染（不写工作树；运行期临时目录，用后即弃），PyYAML 逐册逐用例逐字段比对：**HEAD 渲染 vs 已入库 yaml 仅 `notes` 差 4 处**（`jump_iiii_rb` / `call_iiii_ra` / `ret_riii_ra` ×2），`expected_fault`/`expected_state`/`expected_pc`/`encoding.word`/`spec_cite`/`input_state`/`class`/`status`/`profiles`/`mnemonic`/`deferred_reason`、注释 header、用例 id 序列（6/11/10）**全等**；**当前渲染 vs 已入库 yaml `cmp` 3/3 rc=0**。生成器 diff 4 行全落在 `_case(...)` 的 `notes` 形参位（`spec_cite` 之后、`profiles=` 之前），`_check_yaml` 未被改动（`--check` 判据未放宽）；生成器与三册产物中旧码 `0x81/0x88/0x8A/0x8B/0xFA/0xFB` 残留 0 处。

**独立注入（`cp`+`md5sum -c`，未用 git 还原）**：把 jump boundary note 的 `CFXMEM（当前运行模式 monitor，` 改回 `CFXMEM (0x81), `（正则断言恰 1 处）⇒ `--check` **rc=1**（jump FAIL、call/ret 仍 OK）⇒ `cp` 还原 + `md5sum -c` → `…: OK` ⇒ `--check` **rc=0** 回绿，`git status` 与审前逐行相同。

**约束核验**：只改 notes 字面量 ✅ / yaml 零改动 ✅ / `--check` 判据未放宽 ✅ / 未触 QEMU、gem5、`spec/`、`contracts/`、其它生成器 ✅ / 完成区 13 行 ≤30 且无家目录·绝对·临时·构建树路径 ✅ / 状态 `待验收` ✅ / 反例用 `cp`+md5 还原（禁 git 还原）✅。

**非阻断 finding（文档级，交 architect 收尾）**：① 完成区「红点来自范围外 **4 个生成器**漂移」与本文件遗留问题自相矛盾——实为 **3 个**（`generate_ctrl_br`/`generate_mem_vectors`/`generate_misc`，mem 一个生成器出 3 册），`milestones.md` 亦写 3；② 完成区「055t 共 10 处、其中 6 处已同步」的拆分我无法复现：`f625dde8` 对这三册 yaml 的 `-` 行旧码我数到 **9** 处（jump 2/call 2/ret 5）、被改 `notes:` 行 **5** 条，而 HEAD 上余 4 处不一致（此数与我比对一致）；③ 任务书目标 1 写「共 10 处」而实际需改 4 处，engineer 已在完成区披露，建议立册时校正计数。三项均不涉代码行为/门控退出码/断言计数。

#### 收尾（architect，2026-11-06）

- finding 1「4 个生成器」已按 reviewer 实测更正为 3 个（`ctrl_br`/`mem_vectors`/`misc`）。
- finding 2/3：任务书目标里「10 处」为 055t 全部 notes 改动数，本任务实际 4 处；保留工程师披露，不再改计数口径。
- 剩余三个生成器由 `INTEG-057t` 收口。
- 判决 Accepted，状态置 `已验证`。
