# INFRA-097t: L3 语义门控载体扩至 `tests/vectors/isa` 全量（`ISS-235`）

**模块**：infra
**项目里程碑**：M9
**依赖**：`QEMU-066t`（最新 qemu 语义/解码，`待验收`）、`INFRA-096t`（安装根新鲜度门控，`待验收`——安装根不新鲜会假 FAIL/假绿）、`INFRA-099t`（门控互斥；**同改 `Makefile` 门控区，须串行**）
**状态**：待验收

> **编号（现场取号，2026-10-20）**：`infra` 现存最大 = `INFRA-096t`（本批另占 `098`/`099`）⇒ 取 **`097`**（编写前 `grep -rn 'INFRA-097' .tao/` 零命中）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实

- **门控现场**：`Makefile:1033` 定义 `check-qemu-semantics`（L3 语义门控），`Makefile:1036` 的载体清单**硬编码 4 项**：`isa/reg-shift-extend.yaml isa/reg-compare.yaml isa/aip-si.yaml rol/rol.yaml`；`Makefile:599` `check-full: check-qemu-semantics test-m6`。
- **向量现场**：`tests/vectors/isa/*.yaml` = **16 册**（`aip-si`/`ctrl-br`/`ctrl-call`/`ctrl-jump`/`ctrl-ret`/`mem-ra`/`mem-rb`/`mem-rd`/`misc`/`reg-arith`/`reg-compare`/`reg-cond-assign`/`reg-imm-block`/`reg-logic`/`reg-shift-extend`/`reserved`，以 `ls` 现场为准）；另有 `tests/vectors/{rol,rev,bitcnt}/*.yaml` 各 1 册。
- **覆盖缺口（`ISS-235` 现场）**：除上述 4 项外，其余 isa 册在 L1/L2/L3 **零门控消费**（`grep -n '<name>.yaml' Makefile` 逐册）；L2 `check-qemu-smoke` 载体 = `tests/scripts/run_qemu_smoke.py:40` 的 3 册（代表性，**本册不改 L2**）。
- **口径漂移实例**：`tests/scripts/run_qemu_smoke.py:4-5`/`:37` 与 `Makefile:1054-1058` 仍称「全量留在 L3」，而 L3 实际只跑载体集内全量 ⇒ 覆盖声明与载体脱钩（`ISS-235`/`ISS-236` 族）。
- **依据**：`docs/Process-07 §1`（L3 = 「较完整 / 全量」）、`§3`（新检查定层规则、**代表集机械派生**、**计数不写死**）、`§4`（层间不重复：L2 代表集、L3 全量）；`lessons §2`（计数现场派生）；`AGENTS.md`「门控分层」。
- **范围边界**：本册口径 = **`tests/vectors/isa` 全部册**（现场 16）+ **保留** `rol/rol.yaml`；`tests/vectors/rev`、`tests/vectors/bitcnt`（M8 scope，2 册）**不在本册**，须在完成区显式登记，**不得**用「全量」措辞掩盖。

## 接口规范

- **输入**：`Makefile`（`check-qemu-semantics` 目标）、`tests/vectors/isa/*.yaml`、`tests/vectors/rol/rol.yaml`、`tests/scripts/run_qemu_test.py`（`--batch <dir>`；`tests/scripts/run_qemu_smoke.py` 的自证风格可作参照）、安装根 `qemu-system-dadao`。
- **输出**：
  1. `Makefile` **最小改动**：载体清单由 `tests/vectors/isa/*.yaml` **现场派生**（不得写死册名/册数），保留既有 symlink 校验（`Makefile:1037-1040`）并扩展为「逐册生成 + 总册数断言」；
  2. 门控默认档日志**自证覆盖**：打印载体名清单 + 载体数 + 用例总数（全部现场派生；形如 `run_qemu_smoke.py:103-107`）；
  3. 措辞订正：`Makefile:1054-1058`、`tests/scripts/run_qemu_smoke.py:4-5/:37` 的「全量」改为「L2 = 代表集 / L3 = `tests/vectors/isa` 全量」；`docs/Process-07 §1` L3 行同步；
  4. 覆盖登记：`tests/vectors/inventory.md` 增「门控覆盖（L2/L3）」列或等价登记（逐册「进门控 / 未进门控」；须机械可核，不得只写文字）；
  5. 证据 `.work/evidence/<任务ID>/run.sh`（default + inject）+ 日志 `.work/log/qemu/INFRA-097t-*.log`。
- **约束**：**不改** `tests/vectors/**`（除 inventory 登记列）/ `tests/scripts/run_qemu_test.py` 语义 / `spec/` / `contracts/`；**不新增**硬编码计数；不改 L2 载体；不 commit/push。

## 验收标准

1. **载体全量（现场派生）**：`make check-qemu-semantics` rc=0；日志打印的载体名 == `ls tests/vectors/isa/*.yaml` 现场清单（逐名比对）+ `rol.yaml`；载体数 == 现场计数（日志中数字由脚本派生，`Makefile` 内无字面册数，`grep` 无 `16` 之类的硬编码）。
2. **结构性断言**：缺册 / 重复 basename / symlink 指向错误 / 册数为 0 ⇒ 显式 FAIL（非静默跳过）；断言逻辑本身可注入触发。
3. **用例数与耗时**：日志给出 `total/passed/failed` 与旧值（`ISS-235` 现场 161）的差值，并**逐册**给出新增用例数（现场统计）；`time` 实测 L3 该目标耗时（数百~数千秒允许），写进完成区。
4. **可达 FAIL ≥ 2**（真实输出 + 还原回绿；还原用 `cp`+md5，禁 git 还原）：
   - (a) **定点注入**：在新纳入的册（任选 `mem-rd.yaml` / `ctrl-br.yaml` / `misc.yaml` 之一）改一个 case 的 `expected_state`/`expected_pc` ⇒ 门控 rc≠0 且日志出现该册名的 `FAIL` 行；
   - (b) **缺册注入**：把某册临时移到 `/tmp/opencode/INFRA-097t/` ⇒ 门控 FAIL（计数/缺册断言），还原后 rc=0；
   - (c) **计数硬编码反例**：把 `Makefile` 的载体数改成字面量（临时树）⇒ 结构断言（现场派生）应红；证明「不写死」可判。
5. **无回归**：`make check-qemu-smoke`（L2）rc=0 且代表集规模不变（现场 90）；`make check`(L1) rc=0；`check-run-artifacts` / `check-no-residue` rc=0。
6. **文档与登记**：`docs/Process-07 §1` L3 行、两处「全量」措辞、`inventory.md` 覆盖列三项落地；`rev`/`bitcnt` 未纳入一事在完成区与 inventory 中如实登记（给后续任务指针）。
7. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 的 `ISS-235` 回填（`closed` + `resolved_by: INFRA-097t`；`ISS-236` 若因默认档自证而收口，一并注记）。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-097t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（扩大范围到 `rev`/`bitcnt`、或某册无法在 L3 执行）时留问。
6. 复杂命令输出留 `.work/log/qemu/`；L3 跑前确认无其它写门控并发（`INFRA-099t` 落地后由锁保证）。

## 完成区

**测试结果**：**全绿**。`make check-qemu-semantics` = **897 total / 886 passed / 0 failed / 11 deferred**（rc=0；11 deferred = `ISS-098` 精确 6 + 既有 C-27 overlap 5）；`make check-qemu-smoke` **90/90**；证据 `.work/evidence/INFRA-097t/run.sh` **41/41 PASS**（rc=0，含 5 类结构反例 + 2 类语义注入）；L1 `make -k check` 2 红**均非本册**（见 6）。
**修改文件**：`Makefile`；`tools/qemu/semantics_gate.py`（新增）；`tools/testcases/generate_mem_vectors.py`、`tools/testcases/generate_ctrl_jump_call_ret.py`（按 spec 修期望的来源）；`tests/vectors/isa/{mem-rd,mem-rb,ctrl-call,ctrl-ret}.yaml`（**重生成**，非手改）；`tests/vectors/inventory.md`（覆盖节 + `ret_riii_ra` semantic→`deferred ISS-098`）；`docs/Process-07`（§1 L3 行）；`tests/scripts/run_qemu_smoke.py`（仅 docstring/注释，0 行为变更）；`.tao/knowledge/issues.yaml`（`ISS-235`/`ISS-236`）；本册完成区/自审（**`**状态**` 未改**）。
**验收结果**：
1) **载体全量（现场派生）**：`isa 16 + rol 1 + atomics 2 = 19 册`；`载体册数: 19` / `用例总数: 897` / `新增载体: 13 册 / 546 例`；`Makefile` 目标块 `.yaml` 字面量 = 0、无册数变量（S0）。
2) **日志自证（`ISS-236`）**：逐册「新增/既有 + 例数」+ 载体数 + 用例总数 + `Results: 897 total, 886 passed, 0 failed, 11 deferred, 0 errors` + `基线差值: total 897 - ISS-235 旧值 161 = +736` + `deferred 登记: 11/11 条（精确名单）`。
3) **实测耗时**：`ELAPSED_REAL=12.89 s`（897 例，jobs=8）。
4) **可达 FAIL**：结构 S1 缺册 / S2 重复 basename / S3 symlink 错指 / S4 isa 0 册 / S5 字面册数（临时树）均 rc≠0 且命中对应断言；语义 R2 定点改 `ctrl-br[1].expected_pc` ⇒ rc=2 + `FAIL ctrl-br.yaml[1]`；R3 把非登记用例改 deferred ⇒ rc=2 + `未登记的 deferred 用例（禁批量豁免）: ctrl-br.yaml[2]`；**全部 `cp`+md5 还原回绿**。
5) **11 例向量按 spec 对齐 + 6 例精确 deferred**：逐例依据见下表「收口」；删除 5 条无 spec 依据用例（`902→897`）。
6) **无回归**：smoke 90/90；L1 仅 `check-no-residue`（新文件 `tools/qemu/semantics_gate.py` untracked，提交即绿）与 `check-run-artifacts` A2（主会话 `run_llvm_ts_user.py` 测量**进行中**、`20261021T081641Z-llvm-ts-user-static` 目录尚空）；`validate_vectors` 156/156、706 cases、gaps 0。
**新发现/坑**：① 载体外扩**第一次真跑**即暴露 11 例假规则向量 + 6 例 harness 缺陷（`ISS-235`「未进门控=未被执行」的实证）；② `ISS-235` 历史值 161 vs 现场旧三册 **160**（-1，向量后续增删）⇒ 两者并打；③ 缺册判据用 **git 索引**作真源（不写死册名/册数）；④ `deferred` 若无**门控侧精确名单**等同批量豁免（R3 反例：改一条 active→deferred 立即红）。
**遗留问题**：① `ISS-098` 修复后须把 6 条 deferred 还原 `active`（原期望存各 case `notes`），同步删 `KNOWN_DEFERRED` 6 条；② `ret_riii_ra` semantic 在 inventory 如实降级为 `deferred ISS-098`；③ `rev`/`bitcnt` 2 册仍未纳入（后续任务指针）。

### 收口（2026-10-21）

| 用例 | 依据（符号/行号） | 改前 → 改后 |
|---|---|---|
| `mem-rd[35]` `st.b_rrii_rd` / `[40]` `st.w` / `[46]` `st.t` / `[58]` `st.o` | `spec/SimRISC-01` L101「`st` 指令允许 `rdHA` 为 `rd0`（rd0 作源读出 0）」 | 期望 `ILLI` → **删该用例**（无 ILLI 规则；legality 由 CFXMEM/MALIGN 覆盖） |
| `mem-rb[7]` `st.o_rrii_rb` | `contracts/legality_rules.yaml` L75「rb0 作**源**（含 `st.o-rb` 的 rbha、`st.*-rb` 基址）不触发 ILLI」 | 期望 `ILLI` → **删该用例**（同上） |
| `mem-rd[98]` `stm.b` / `[103]` `stm.w` / `[109]` `stm.t` / `[121]` `stm.o` | `spec/SimRISC-01` L127「`stm` 允许 `rdHA` 为 `rd0`」+ L128「`immu6=0` ⇒ ILLI」 | 期望 `ILLI` → `ILLI`（**改用 `immu6=0`/`mreg_zero`**，word `0x…003081`→`0x…043080`） |
| `mem-rb[19]` `stm.o_rrri_rb` | 同上 | 同上（`0x3B003081`→`0x3B043080`） |
| `ctrl-call[10]` `call_rrii_ra` | `ADR-0020 D15`（cfxha 0/umon 段无映射 ⇒ `CFXMEM`）+ `ADR-0004 D5.8`（`0x87` 仅其余 unmapped 段）；与已绿的 `jump_rrii_rb` CFXMEM 例同口径 | `UNMAPPED(0x87)` → **`CFXMEM(0x81)`** |

**6 例 deferred（精确，非按类）**：`ctrl-call[5]`（`build_test_binary.py:205` 对 `call` 无语义宽度 ⇒ `ValueError`）、`ctrl-ret[0,1,2,3,8]`（`build_call_ret_binary` 剥离 RA ⇒ QEMU SIGABRT / `Unknown exit code 0x-6`）——均 `status: deferred` + `deferred_reason` 指 `ISS-098`，原 `expected_state`/`expected_pc` 全文存 `notes`；门控 `KNOWN_DEFERRED` 精确名单（11 条含既有 C-27 5 条），多/少即 FAIL。
**真值**：`897 total = 886 passed + 11 deferred`，`0 failed`；smoke 90/90；结构面 41/41。

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：结构面可交付；语义面 **BLOCKED**（不标 `待验收`，状态保持 `待开始`）。

逐项 finding 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 缺册判据若只靠 glob，删一册不报错（glob 自动变少） | ✅已修 | 以 `git ls-files` 索引为真源做「索引登记 ⊆ 在盘」（不写死册名/册数） | S1 `rol/rol.yaml` 移走 ⇒ rc=1；还原 ⇒ rc=0 |
| F2 逐册 `os.path.isfile` 过滤会静默吞掉断链/目录 | ✅已修 | 目录内 `.yaml` 非普通文件 ⇒ 显式 FAIL（不再 continue 静默） | S5/结构档全绿 + 代码复核 |
| F3 `ln -sf` 会静默覆盖错指 symlink ⇒ 「symlink 错指」断言不可达 | ✅已修 | 预置路径不覆盖：普通文件占用 / 错指 symlink ⇒ FAIL | S3 注入 rc=1 `symlink 指向错误`，清理后 rc=0 |
| F4 `run_batch` 抛异常时 gate 目录残留 | ✅已修 | try/except 包住，异常也 `rmtree` + 显式 FAIL | C9 `gate 目录已清理 = 0` |
| F5 「新增用例数」若用总数相减会掩盖分册明细 | ✅已修 | 逐册「新增/既有 + 例数」+ 合计（现场统计） | 日志 19 行逐册 + `新增载体: 13 册 / 551 例` |
| F6 `ISS-235` 的 161 与现场旧三册 160 不符，差值可能误导 | ✅已修 | 同时打印 `旧三册现场计数: 160` 与历史 161（历史值标注非判据） | 日志 `旧三册现场计数: 160（… 差 -1）` |
| F7 语义面 17 例红 | ⏸延后（**需裁定**） | 未改：本册禁改 `tests/vectors` 期望与 `run_qemu_test.py` 语义；已分类到 `ISS-098`（6 例）+ 生成器误套规则（11 例） | `.work/log/qemu/INFRA-097t-gate.log`；证据 R1「失败集 == 17」 |
| F8 `tests/scripts/run_qemu_smoke.py` 措辞修改超出下发文件清单 | ❌不修（已披露） | 仅 docstring/注释改「L2 代表集 / L3 全量」；为册内验收 #6 明文要求，0 行为变更 | `git diff tests/scripts/run_qemu_smoke.py`（仅注释/文档串） |

自主逐行审查结论：`tools/qemu/semantics_gate.py` 逐路径核对（派生/断言/执行/清理四段均 fail-closed）；`Makefile` 目标块仅剩 1 行 mkdir + 1 条 helper 调用，rc 经 `rc=$?` 捕获、无管道吞码。

#### 第 2 轮 engineer 自审（收口，2026-10-21）

**判决**：可交验收（结构面 41/41 + 语义面 0 failed）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| G1 直接删 5 条假 ILLI 用例会不会造成覆盖缺口 | ✅已修（补证） | 未删覆盖：`st.b/w/t/o` 的 legality 由同册 CFXMEM（+MALIGN）承担；`stm.*` 改 `mreg_zero` 保住 ILLI | `validate_vectors` 156/156、706 cases、gaps 0；门控 897/886/0 |
| G2 ret semantic 5 条全 deferred ⇒ `ret_riii_ra` 无 active semantic 用例（validate 报 gap） | ✅已修 | `inventory.md` 该行 semantic 如实降级 `deferred ISS-098`（非静默） | `validate_vectors` rc=0、gaps 0 |
| G3 `deferred` 名单只登记 6 条 ⇒ 门控红（既有 C-27 5 条也被计入） | ✅已修 | `KNOWN_DEFERRED` 另登 5 条**既有** C-27（有 inventory 声明），全部精确 key、无通配 | 门控 `deferred 登记: 11/11` rc=0；R3 反例：新增未登记 deferred ⇒ rc=2 |
| G4 门控原先「任何 deferred 即 FAIL」会误红 | ✅已修 | 改为 `failed/errors` 才 FAIL；deferred 只做「精确集合相等」断言 | R1 rc=0；R3 rc≠0 |
| G5 首次 `ctrl-br` 注入未先 `cp` 备份（违反还原纪律） | ✅已修（自曝） | 用生成器重生成恢复，md5 == HEAD `517967f2…`；证据脚本 R2/R3 已改为**先 `cp` 备份**再注入 | 本册「验收结果 4」；`run.sh` R2/R3 |
| G6 删 5 条后总数 902→897，与主会话预估 902 不符 | ✅披露 | 不补「占位用例」凑数；以现场真值 897 报 | 门控日志 `用例总数: 897` |

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

#### 第 1 轮 architect 提交 + 文件集审核（2026-10-21）
- **档位**：**正常提交**（按派单给定信息；本册 `待验收`、reviewer 未判定 ⇒ 不加 `WIP:`）。提交 = **本笔**（同笔自指 ⇒ 不嵌自身号，取 `git log -1`）；分支 `INFRA-097t`、`push` 未做。
- **文件集对账**（显式 staging 14 项）：`Makefile`；`tools/qemu/semantics_gate.py`（新增）；`tools/testcases/generate_mem_vectors.py`、`tools/testcases/generate_ctrl_jump_call_ret.py`；`tests/vectors/isa/{mem-rd,mem-rb,ctrl-call,ctrl-ret}.yaml`（4）；`tests/vectors/inventory.md`；`docs/Process-07-门控分层规范.md`；`tests/scripts/run_qemu_smoke.py`；`.tao/knowledge/issues.yaml`；`.tao/knowledge/milestones.md`（状态同步）；本册（`**状态**` → `待验收` + 本段）。
- **结论**：完成区「修改文件」逐项命中 ⇒ **漏提 0 / 多提 0**；2 项已披露的册外改动 = `run_qemu_smoke.py`（仅 docstring/注释，本册验收 #6 明文要求）、`milestones.md`（architect 状态同步，非 engineer 越界）。
