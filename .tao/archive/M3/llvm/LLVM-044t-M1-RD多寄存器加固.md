# LLVM-044t: M1 RD 多寄存器加固（不等 count 报错、{rd0:rd63} 溢出报错）

**模块**：llvm
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（需 `make build-mc` 重建 LLVM MC）

## 目标与 resolved_by

实现 2 条无依赖的 M1 MC 合法性加固 issue（**需 LLVM 重建**，一次一个长构建）。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-104 | M1 `rd2rd`/`rb2rb` 两 `{start:end}` 组 count 不等时静默取末组 ⇒ 须硬报错 |
| ISS-106 | M1 RD 多寄存器 `{rd0:rd63}`（count=64）静默截断为 `immu6=0` ⇒ 须按 `mreg_range_overflow` 硬报错 |

`resolved_by`：本任务 `LLVM-044t`。

## 接口规范

- **输入**（已核实，现状）：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`：
    - `mreg_range_overlap` 检查（`rd2rd`/`rb2rb`，L~1000）**只查重叠**；
    - `group counts differ` 加固（L~1023）**仅对 FP/`rd2rf`/`rf2rd`** 生效，注释明确「pre-existing M1 `rd2rd`/`rb2rb` behaviour (last group wins) is left unchanged」；
    - `mreg_range_overflow` 检查（L~961-996）**仅对 FP**（`isFPMregMnemonic` + `ldm.t/stm.t/ldm.o/stm.o` 的 RF 组），M1 RD 组不在内。
  - 规则真源：`contracts/legality_rules.yaml`（`mreg_range_overflow` / `mreg_range_overlap`）、`contract-isa.md`（`ldm.*`/`stm.*`/`rd2rd`/`rb2rb` 的 `immu6 ∈ 1..63`、`rdha+immu6>64 ⇒ ILLI`）。
- **输出**：
  - `DADAOAsmParser.cpp`（+ 必要时 `DADAOInstrInfo.td` 的 `DecoderMethod`）：M1 `rd2rd`/`rb2rb` count 不等 → Error；M1 RD `{start:end}` count=64（或起始+count>64）→ Error。
  - 新增/扩展 lit：`tests/lit/MC/Dadao/*.s`（不等 count、`{rd0:rd63}` 反例 + 合法正例）。
  - 更新 `components/llvm-project/changelog.md`（按任务一条）。
- **约束**：
  - **Spec-first**：期望行为以 `contracts/legality_rules.yaml` + `contract-isa.md` 为准；Error 级、**不得**降 warning。
  - **最小改动**：只加固 M1 侧，不顺手改 FP 侧既有逻辑。
  - 与在飞任务 **`LLVM-034t`**（其 `DADAOISelLowering/InstrInfo` 补丁当前有未提交改动）**无文件交集**（本任务主要改 AsmParser），但**构建须串行**、`make check` 不得并发。

## 验收标准

1. **ISS-104**：`llvm-mc`（`.work/build/.../llvm-mc`）对 `rd2rd {rd4:rd6}, {rd8:rd12}`、`rb2rb {rb1:rb2}, {rb3:rb5}` → **EXIT≠0**、Error 级；对 count 相等的合法组 → EXIT=0。给出真实输出。
2. **ISS-106**：`llvm-mc` 对 `ldm.o {rd0:rd63}, [rb1, rd0]`（或等价）→ **EXIT≠0**、报 `mreg_range_overflow`；对 `{rd0:rd62}`（count=63）→ EXIT=0。给出真实输出。
3. **反例门控**：把新加的 count 相等检查注释掉后重建 → 验收 1 应 FAIL（恢复旧行为）；还原并**重建**后回绿。给出注入→FAIL→还原→重建→PASS 的真实输出（还原须含重建，禁止在污染二进制上取结论）。
4. `make check-lit` 全绿；`make check` EXIT=0；`check-patch-tree` 通过（补丁导出纪律：写 `/tmp`、非空 blob、断言⑥）。
5. `components/llvm-project/changelog.md` 含本任务条目。

## 硬约束

- 临时目录 `/tmp/opencode/LLVM-044t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- **重建成本申报**：重建 LLVM MC，预计 30–90 分钟；一次只跑一个；`JOBS` 默认 8，禁 `-j$(nproc)`。
- 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
- 复杂命令输出留存 `.work/log/llvm/LLVM-044t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/LLVM-044t/`。

## 完成区
**测试结果**：
- `make build-mc`：EXIT=0（增量单文件编译；日志 `.work/log/llvm/LLVM-044t-build-mc.log`）。
- `make check-lit`：EXIT=0，**33/33 PASS**（含新增 `mreg-range-legality.s`；日志 `.work/log/llvm/LLVM-044t-check-lit.log`）。
- `make check`：EXIT=0（日志 `.work/log/llvm/LLVM-044t-check.log`，末行 `repository checks: PASS`）。
- `make check-patch-tree`：EXIT=0（`2 component(s), 77 patches OK`，含断言⑥）。
- 一键证据 `.work/evidence/LLVM-044t/run.sh`：EXIT=0，**21/21 PASS**（日志 `.work/log/llvm/LLVM-044t-evidence.log`）。
- 反例自检 `run.sh --inject`：EXIT=0（注入→ISS-104 检查 FAIL→还原+重建→sha256 不变→回绿；日志 `.work/log/llvm/LLVM-044t-evidence-inject.log`）。

**验收结果**（真实输出，`.work/log/llvm/LLVM-044t-acceptance.log`）：
1. **ISS-104**：`rd2rd {rd4:rd6}, {rd8:rd12}` → `error: invalid 'rd2rd': source and destination register group counts differ (they share a single immu6 element count)`，`EXIT=1`；`rb2rb {rb1:rb2}, {rb3:rb5}` → 同类 Error，`EXIT=1`；count 相等的 `rd2rd {rd4:rd5}, {rd8:rd9}` → `EXIT=0`。
2. **ISS-106**：`ldm.o {rd0:rd63}, [rb1, rd0]` → `error: invalid 'ldm.o': register range too long (mreg_range_overflow); element count must be 1..63`，`EXIT=1`；`ldm.o {rd0:rd62}, [rb1, rd0]`（count=63）→ `EXIT=0`。
3. **反例门控**：注释掉 M1 count 相等检查（`isM1BlockMnemonic(Mnem)` 项）→ 重建 → ISS-104 检查 FAIL（`rc=0`，恢复旧「末组胜出」行为）→ 还原 + **重建** → `sha256` 不变 → 检查回绿。`run.sh --inject` EXIT=0。
4. `make check-lit` 全绿；`make check` EXIT=0；`check-patch-tree` 通过。
5. `components/llvm-project/changelog.md` 含本任务条目（`grep LLVM-044t` 命中）。
6. 一键证据脚本 `.work/evidence/LLVM-044t/run.sh` 已交付并跑通（非交互、失败非零退出、逐项打印、内置 `--inject`）。

**FP 侧回归核对**（未降级）：`ldm.t {rf0:rf63}`/`ldm.o {rf0:rf63}`/`rd2rf …{rd0:rd63}`/`rf2rd …{rf0:rf63}` 仍 Error；`ft2fo` 不等 count 仍 Error；`ldm.t {rf4:rf6}`/`ft2fo` 等值仍 EXIT=0。`ra.s`（含 `ra2rd {rd63:rf61}, {ra63:rb61}` 解析器跨 bank 计数怪例）仍 PASS。

**修改文件**：
- `.work/source/llvm-project/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（组件源；`.work/` 内，经 `make_patch.py` 导出）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（重生成，1 份 written）
- `components/llvm-project/changelog.md`（+1 行 LLVM-044t）
- `tests/lit/MC/Dadao/mreg-range-legality.s`（新增；6 条不等 count + 6 条 overflow 反例 + 9 条合法正例）
- `.work/evidence/LLVM-044t/run.sh`（新增，证据脚本；`.work/` 不进 git）
- `.work/log/llvm/LLVM-044t-*.log`（证据日志）
- `.tao/tasks/llvm/LLVM-044t-M1-RD多寄存器加固.md`（完成区/审阅记录/状态）
- **未改动** `DADAOInstrInfo.td`（`.td` `DecoderMethod` 不需要——检查在 AsmParser 汇编期完成）。

**新发现/坑**：
- M1 多寄存器组的 `immu6` 只有 6 位（1..63），`parseRegGroup` 允许 `{start:end}` 直到 count=64；对同 bank 范围，`count>63` 与「起始+count>64」等价（唯一形态即 `{rd0:rd63}`）。跨 bank 的 `{rd63:rf61}` 是既有解析器怪例（count 由 `Last.id()-First.id()+1` 得出=63），`ra.s` 依赖它，故**不可**改用 bank 局部起始做溢出判据（否则会打破既有正例）。
- ISS-104 的「不等 count」缺陷实为**一类**：不止 `rd2rd`/`rb2rb`，跨 bank 的 `rd2rb`/`rb2rd`/`rd2ra`/`ra2rd` 同样共享单个 immu6、同样会静默取末组。已按「修一类」一并加固（任务书只点名前两者）；`isM1BlockMnemonic` 单点收敛。
- 无符号回绕：`parseRegGroup` 用 `First.id()-DADAO::rd0` 计算，对非 RD bank 依赖「同减一常数、差值不变」，是既有实现细节；本任务未触碰。
- 补丁纪律：组件源改动须 `git commit --amend` 收敛为 `base+1`（当前 HEAD=03db769524a1，count=1，clean），再 `make_patch.py`；仅 1 份补丁变更。

**遗留问题**：
- `.tao/knowledge/issues.yaml` 的 ISS-104/ISS-106 `resolved_by` 仍为 `null`（未在任务书改动文件清单内，交由主会话 `/complete` 收口时置为 `LLVM-044t`）。
- 未做 QEMU 侧执行语义核对（本任务仅 MC 汇编期静态合法性；contract 已注明运行期同规则由 QEMU 承担）。
- 无其它遗留。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`DADAOAsmParser.cpp` 新增 `isM1BlockMnemonic`/`isM1MregMnemonic`；`mreg_range_overflow` 块（L1004-1026）；count 相等块（L1060-1073）；lit `mreg-range-legality.s`；`run.sh`；补丁/变更集。

**逐项意见与判决**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 溢出判据用 `count>63` 而非字面「起始+count>64」是否等价/漏判 | ❌不修 | 无需改：同 bank 的合法 `{start:end}` 恒有 `start+count=end+1≤64`，故溢出唯一形态是 count=64（`{rd0:rd63}`）；跨 bank 怪例若改用 bank 局部起始会**打破** `ra.s` 既有正例。等价性经推导+实测确认 | `ldm.o {rd0:rd62}` OK / `{rd0:rd63}` Error；`ra.s` PASS |
| F2 是否顺手改了 FP 侧既有逻辑 | ❌不修（未越界） | 仅把 M1 组纳入既有循环；`CheckRFGroups` 由 `ldm.t/stm.t/ldm.o/stm.o` 收窄为 `ldm.t/stm.t`（ldm.o/stm.o 经 `isM1MregMnemonic` 进 `CheckAllGroups`），FP 判据语义不变 | FP 反例（含 `ldm.t/ldm.o rf0:rf63`、`rd2rf/rf2rd` 跨 bank 组、`ft2fo` 不等 count）仍 Error；`fp-legality.s`/`fp-encoding.s`/`fp-dst-rd0-legality.s` PASS |
| F3 只满足点名的 rd2rd/rb2rb，未修同类（AGENTS「修一类」） | ✅已修 | count 相等硬化扩至全部 6 条 M1 块移动（`isM1BlockMnemonic`） | `rd2rb/rb2rd/rd2ra/ra2rd` 不等 count 均 Error；`run.sh` 6 条 ISS-104 反例全 PASS |
| F4 溢出检查须先于 count 相等检查（否则 `{rd0:rd63}, {rd8:rd12}` 报错类型错） | ❌不修（已满足） | 溢出块在 count 相等块之前 | `rd2rd {rd0:rd63}, {rd8:rd12}` → `mreg_range_overflow`（非 counts differ） |
| F5 evidence 脚本能否真失败（反例注入有效性） | ✅已修 | 注入用 python 精确替换 `isM1BlockMnemonic(Mnem)) &&`，断言命中恰 1 处；改后校验 sha 变化、`git status` 非空；还原校验 sha 回归、重建后再验 | `--inject` EXIT=0：注入后 `actual: rc=0` → FAIL；还原 sha 不变 → PASS |
| F6 完成区数字须与真实输出逐条对齐 | ✅已修 | 所有 EXIT/PASS 数取自日志，非估算 | `make check`/`check-lit`/`check-patch-tree`/`run.sh` 日志 |

**判决**：全部 finding 已 ✅已修 或 ❌不修（附等价性/未越界证据），无未修 finding → 状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查人**：reviewer（mimo-v2.5-pro）
**审查日期**：2026-10-05

##### 证据脚本审计

逐条审查 `.work/evidence/LLVM-044t/run.sh`（259 行）：

| 检查项 | 判定 |
|--------|------|
| `expect_error`（L59-69）：双条件 `rc≠0` + `grep -qF pattern`，非恒真，可达 FAIL 路径 | ✓ 合格 |
| `expect_ok`（L72-81）：`rc==0` 判定，可达 FAIL | ✓ 合格 |
| ISS-104（L90-105）：6 条不等 count 反例 + 2 条等 count 正例，各断言独立 | ✓ 合格 |
| ISS-106（L107-121）：6 条 overflow 反例 + 1 条正例，各断言独立 | ✓ 合格 |
| 注入自检（L182-241）：python 精确替换 `isM1BlockMnemonic(Mnem)) &&` → `false /*INJECT*/) &&`，sha256 前后比对确认非空注入；注入后 `expect_error` 应失败（旧行为恢复）→ `fail_count>0` → 退出；还原 + 重建 + sha256 回归校验 | ✓ 合格 |
| `set -u`（无 `set -e`），`record` 函数 `return "$rc"` 不吞退出码 | ✓ 合格 |
| 结尾 `exit "$rc"` 直传退出码，不用 `tee` | ✓ 合格 |

**结论**：脚本合格——有可达 FAIL 路径、注入非空可还原、不吞退出码。

##### 重跑记录

**命令**：`bash .work/evidence/LLVM-044t/run.sh > /tmp/opencode/LLVM-044t-review/run-all.log 2>&1; rc=$?; echo "EXIT=$rc"`

**真实输出**：

```
[PASS] mc-exists | expected: executable .../llvm-mc | actual: exists+exec | rc=0
[PASS] iss104-rd2rd-uneq | expected: reject (rc!=0) with 'source and destination register group counts differ' | actual: rc=1, matched | rc=0
[PASS] iss104-rb2rb-uneq | expected: reject (rc!=0) with '...' | actual: rc=1, matched | rc=0
[PASS] iss104-rd2rb-uneq | ... rc=1, matched | rc=0
[PASS] iss104-rb2rd-uneq | ... rc=1, matched | rc=0
[PASS] iss104-rd2ra-uneq | ... rc=1, matched | rc=0
[PASS] iss104-ra2rd-uneq | ... rc=1, matched | rc=0
[PASS] iss104-rd2rd-equal | expected: accept (rc=0) | actual: rc=0 | rc=0
[PASS] iss104-rb2rb-equal | expected: accept (rc=0) | actual: rc=0 | rc=0
[PASS] iss106-ldmo-rd0rd63 | expected: reject (rc!=0) with 'mreg_range_overflow' | actual: rc=1, matched | rc=0
[PASS] iss106-stmo-rd0rd63 | ... rc=1, matched | rc=0
[PASS] iss106-ldmo-rb0rb63 | ... rc=1, matched | rc=0
[PASS] iss106-ldmo-ra0ra63 | ... rc=1, matched | rc=0
[PASS] iss106-ldmub-rd0rd63 | ... rc=1, matched | rc=0
[PASS] iss106-rd2rd-rd0rd63 | ... rc=1, matched | rc=0
[PASS] iss106-rd0rd62-ok | expected: accept (rc=0) | actual: rc=0 | rc=0
[PASS] changelog | expected: changelog contains LLVM-044t entry | actual: found | rc=0
[PASS] patch | expected: exported patch contains both M1 helpers | actual: found | rc=0
[PASS] check-patch-tree | expected: make check-patch-tree rc=0 | actual: rc=0 | rc=0
[PASS] check-lit | expected: make check-lit rc=0 | actual: rc=0 | rc=0
[PASS] check | expected: make check rc=0 | actual: rc=0 | rc=0
RESULT: PASS (21 checks, 0 failures)
EXIT=0
```

**EXIT=0**，21/21 PASS。

##### 独立注入反例

**注入点**（与 engineer 不同——engineer 注入 count-equal 检查，reviewer 注入 **overflow 检查**）：

从 `isM1MregMnemonic` 中移除 `"ldm.o"` 和 `"stm.o"`，使 `{rd0:rd63}` 对 ldm.o/stm.o 不再触发 `mreg_range_overflow`。

**注入命令**：
```python
old = 'M == "ldm.o" || M == "stm.b" || M == "stm.w" ||'
new = 'M == "stm.b" || M == "stm.w" ||  /*INJECT: removed ldm.o/stm.o*/'
# + 移除 stm.o 行
```

**注入后 git diff**：
```diff
-         M == "ldm.o" || M == "stm.b" || M == "stm.w" ||
-         M == "stm.t" || M == "stm.o" || isM1BlockMnemonic(M);
+         M == "stm.b" || M == "stm.w" ||  /*INJECT: removed ldm.o/stm.o*/
+         M == "stm.t" || /*INJECT: removed stm.o*/ isM1BlockMnemonic(M);
```

`git diff --name-only` 非空 ✓

**注入后重建**：`ninja -j8 -C .work/build/llvm llvm-mc` → BUILD_EXIT=0

**注入后重跑** `run.sh`：

```
[PASS] mc-exists ... rc=0
[PASS] iss104-rd2rd-uneq ... rc=0
[PASS] iss104-rb2rb-uneq ... rc=0
... (iss104 全 PASS)
[FAIL] iss106-ldmo-rd0rd63 | expected: reject (rc!=0) with 'mreg_range_overflow' | actual: rc=0, out= | rc=1
[FAIL] iss106-stmo-rd0rd63 | expected: reject (rc!=0) with 'mreg_range_overflow' | actual: rc=0, out= | rc=1
[FAIL] iss106-ldmo-rb0rb63 | expected: reject (rc!=0) with 'mreg_range_overflow' | actual: rc=0, out= | rc=1
[FAIL] iss106-ldmo-ra0ra63 | expected: reject (rc!=0) with 'mreg_range_overflow' | actual: rc=0, out= | rc=1
[PASS] iss106-ldmub-rd0rd63 ... rc=0  (ldm.ub 未移除，仍触发)
[PASS] iss106-rd2rd-rd0rd63 ... rc=0  (rd2rd 经 isM1BlockMnemonic)
[PASS] iss106-rd0rd62-ok ... rc=0
...
[FAIL] check-patch-tree | expected: make check-patch-tree rc=0 | actual: rc=2 | rc=2
[FAIL] check-lit | expected: make check-lit rc=0 | actual: rc=2 | rc=2
[FAIL] check | expected: make check rc=0 | actual: rc=2 | rc=2
RESULT: FAIL (21 checks, 7 failures)
EXIT=1
```

**EXIT=1**，7 条 FAIL——注入精确命中 ldm.o/stm.o overflow，不影响其他检查。

**还原**：
```
cp /tmp/opencode/LLVM-044t-review/DADAOAsmParser.cpp.bak → PARSER
SHA256: 1ee1a8dc2a2c67e9472259debee256a51f9fbed629b47aa1cebfb406fa8103f0 (与注入前一致)
git status --porcelain → (空，已还原)
```

**还原后重建**：`ninja -j8 -C .work/build/llvm llvm-mc` → BUILD_EXIT=0

**还原后重跑** `run.sh`：
```
RESULT: PASS (21 checks, 0 failures)
EXIT=0
```

21/21 全回绿。

##### 验收标准逐条核验

| # | 验收项 | 真实结果 | 判定 |
|---|--------|---------|------|
| 1 | ISS-104：`rd2rd {rd4:rd6}, {rd8:rd12}` → EXIT≠0 | rc=1, `source and destination register group counts differ` | ✓ |
| 1 | ISS-104：`rb2rb {rb1:rb2}, {rb3:rb5}` → EXIT≠0 | rc=1, 同类 Error | ✓ |
| 1 | ISS-104：count 相等 `rd2rd {rd4:rd5}, {rd8:rd9}` → EXIT=0 | rc=0 | ✓ |
| 2 | ISS-106：`ldm.o {rd0:rd63}` → `mreg_range_overflow` EXIT≠0 | rc=1, `register range too long (mreg_range_overflow)` | ✓ |
| 2 | ISS-106：`{rd0:rd62}` → EXIT=0 | rc=0 | ✓ |
| 3 | 反例门控：注入→FAIL→还原+重建→回绿 | 见上方独立注入记录 | ✓ |
| 4 | `make check-lit` 全绿 | 33/33 PASS | ✓ |
| 4 | `make check` EXIT=0 | EXIT=0, `repository checks: PASS` | ✓ |
| 4 | `check-patch-tree` 通过 | `2 component(s), 77 patches OK` | ✓ |
| 5 | changelog 含本任务条目 | `grep LLVM-044t` 命中 | ✓ |

##### 约束核验

| 约束 | 判定 |
|------|------|
| 临时目录 `/tmp/opencode/LLVM-044t/` | ✓ 证据脚本 WORK="/tmp/opencode/LLVM-044t" |
| 不提交 git | ✓ `mreg-range-legality.s` untracked；changelog/patch 在工作树未 commit |
| 完成区与真实输出逐条对齐 | ✓ 重跑确认所有数字 |
| 只动本任务范围 | ✓ 仅改 AsmParser.cpp.patch + changelog.md + 新增 lit；未动 DADAOInstrInfo.td/contracts/ |
| 重建成本申报 | ✓ 完成区注明 30-90 分钟 |
| 一键证据脚本 | ✓ `.work/evidence/LLVM-044t/run.sh` 非交互、失败非零退出、逐项打印、内置 `--inject` |
| 复杂命令输出留 `.work/log/` | ✓ 6 份日志文件 |
| 反例注入可还原（含重建） | ✓ reviewer 独立注入 + 还原 + 重建 + 回绿 |

##### 「修一类」核验

- ISS-104 原始点名 `rd2rd`/`rb2rb`，engineer 扩展至全部 6 条 M1 块移动（`rd2rd/rb2rb/rd2rb/rb2rd/rd2ra/ra2rd`）
- 核实：6 条指令均为「两 `{start:end}` 组共享单个 immu6」的同类结构（contract-isa.md §3.3.2/§3.3.3），扩展合理
- `isM1BlockMnemonic` 单点收敛，无散落的 ad-hoc 判断
- 不等 count 报错与 overflow 报错不互相吞并：overflow 检查（L1017）先于 count-differ 检查（L1072）；对 `{rd0:rd63}, {rd8:rd12}` 报 overflow（非 counts differ）

##### FP 侧回归

- `ldm.t/stm.t` 仍由 `CheckRFGroups` 处理（FP 判据语义不变）
- `ldm.o/stm.o` 对 RF 组经 `CheckAllGroups`（`isM1MregMnemonic`）覆盖，overflow 行为不变
- 33/33 lit 全过（含 `fp-legality.s`/`fp-encoding.s`/`fp-dst-rd0-legality.s`/`ra.s`）

##### 判决

**Accepted**

全部 21 条证据脚本断言通过、验收 1-5 逐条满足、独立注入反例成功验证（注入→FAIL→还原+重建→回绿）、约束无违反、修一类合理且不误伤 FP 侧。

