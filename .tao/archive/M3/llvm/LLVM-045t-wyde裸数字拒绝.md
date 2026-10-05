# LLVM-045t: wyde 位置仅接受 wp0–wp3（裸数字 0–3 须报错）

**模块**：llvm
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（需 `make build-mc` 重建 LLVM MC）

## 目标与 resolved_by

实现 1 条无依赖的 LLVM MC 解析收紧 issue（**需 LLVM 重建**）。用户 2026-10-04 已裁定。完成后应关闭：

| ISS | 改动点 |
| --- | --- |
| ISS-128 | `set.zw`/`set.ow`/`or.w`/`andn.w` 的 wyde 位置裸数字 0–3 被静默接受 ⇒ 只能写 `wp0`–`wp3`，裸数字须报错 |

`resolved_by`：本任务 `LLVM-045t`。

## 接口规范

- **输入**（已核实，现状）：
  - `components/llvm-project/patches/.../AsmParser/DADAOAsmParser.cpp.patch`：`parseWydePosToken()`（L400）正确解析 `wpN`；但 `parseOperand()`（L~650）对裸数字回退到 `parseImmediate()`，且 `DADAOInstrInfo.td.patch` 的 `DADAOWydePosAsmOperand`（L38-42）`PredicateMethod = isWydePosImm` 接受 `kImmediate && 0≤ImmVal≤3`。
  - 期望（用户裁定）：`set.zw rd1, 1, 0x1234` 等裸数字 0–3 须 **Error 级报错**；`set.zw rd1, wp1, 0x1234` 合法。裸 5/8 现状已正确报错。
  - 连带：`tests/e2e/smoke_add.s`、`smoke_arith.s`、`smoke_fp.s`（`smoke_jump.s` 若含实际指令）使用裸数字，须改 `wpN`；并修正其注释「wpN 被静默忽略、须用数值 0/1/2/3」（与事实相反）。`LLVM-035t:22` 旧表述**已在任务书中更正**（L27 已注明），本任务只需确认无其它残留。
- **输出**：
  - `DADAOAsmParser.cpp`（收紧 wydepos 匹配为仅接受 `parseWydePosToken` 产出的操作数）+ 必要时 `DADAOInstrInfo.td`；
  - `tests/e2e/smoke_add.s`/`smoke_arith.s`/`smoke_fp.s`（+`smoke_jump.s` 若有实际指令）改 `wpN` 并修正注释；
  - lit 正/反例（若有 MC lit 覆盖）；
  - `components/llvm-project/changelog.md` 补条目。
- **约束**：
  - **Spec-first**：以 `contract-isa.md` / `spec/Toolchain-01` 的 wyde 位置记法为真源；`ADR-0013 D9` 相关注释符（`;`）不受影响。
  - Error 级、不得降 warning。
  - 反汇编器打印 `wp0`–`wp3`（现状已正确）须回归「汇编↔反汇编往返」。
  - 与在飞 **`LLVM-034t`** 无文件交集（本任务改 AsmParser/e2e），但**构建串行**。

## 验收标准

1. `llvm-mc` 对 `set.zw rd1, 1, 0x1234`、`set.ow rd2, 0, 1`、`or.w rd3, 3, 0x1`、`andn.w rb4, 2, 0x1` → **EXIT≠0**、Error 级（裸数字被拒）。
2. `llvm-mc` 对 `set.zw rd1, wp1, 0x1234`、`or.w rd3, wp3, 0x1` 等 → EXIT=0，编码与修复前一致（wpN 语义不变）；反汇编回 `wpN`。
3. **反例门控**：恢复 `isWydePosImm` 接受裸数字（或 `parseImmediate` 兜底）后重建 → 验收 1 应 FAIL（旧“静默接受”行为）；还原并**重建** → 回绿。给出注入→FAIL→还原→重建→PASS 的真实输出（还原须含重建）。
4. `tests/e2e/*.s` 中所有**实际指令**不再使用裸数字 wyde 位置（`grep` 逐文件核对，注释中引用的说明文字须改为正确表述）；`make check-lit`、E2E smoke 全绿。
5. `make check` EXIT=0；`check-patch-tree` 通过。

## 硬约束

- 临时目录 `/tmp/opencode/LLVM-045t/`；禁止在仓库内留临时文件。
- 不提交 git（提交须用户确认）。
- 完成区结论须与真实命令输出逐条对齐；失败即停、禁止自动重试。
- 只动本任务范围文件，越界须披露。
- **重建成本申报**：重建 LLVM MC，预计 30–90 分钟；一次只跑一个；`JOBS` 默认 8。
- 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
- 复杂命令输出留存 `.work/log/llvm/LLVM-045t-<命令名>.log`。
- 交付一键证据脚本：非交互、任一检查失败非零退出、逐项打印「检查名/期望/实际/退出码」、内置反例注入自检；落 `.work/evidence/LLVM-045t/`。

## 完成区

**测试结果**：通过 **19/19**（一键证据 `.work/evidence/LLVM-045t/run.sh` 全 PASS，`EXIT=0`）；`run.sh --inject` 自检 PASS（放宽 `isWydePosImm` 接受 `kImmediate` → 重建 → 4 条 bare-rejected 全 FAIL → `git checkout` 还原 + 重建 → 回绿，`EXIT=0`）。`make check` `EXIT=0`（lit `32/32` = MC `28` + E2E `4`）；`make check-patch-tree` `EXIT=0`（77 patches OK）；`make check-source-state` OK。oracle `122/122`；`check_lit_bytes` `110 patterns OK`。

**修改文件**：

- 组件源码（`.work/source/llvm-project`，收敛为 base+1 commit `fa4799318`；base=`6dfe1677ab8dffbc6ec13d53a1e0215d75147689`）：
  - `llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（+21/−5：新增 `kWydePos` kind + `createWydePos` 工厂；`isWydePosImm` 收紧为仅 `Kind == kWydePos`；`print` 补 case；`parseWydePosToken` 改用 `createWydePos`。**未改** `DADAOInstrInfo.td`——`PredicateMethod=isWydePosImm` 保留，收紧点在 predicate 实现）
- DADAO-v5 仓库：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（`make_patch.py llvm-project` 从真实源导出：`1 written, 44 unchanged`；未手改）
  - `components/llvm-project/changelog.md`（`Process-01 §162` 按任务一条追加）
  - `tests/e2e/smoke_add.s` / `smoke_arith.s` / `smoke_fp.s` / `smoke_jump.s`（裸数字 wyde → `wpN`；修正「wpN 被静默忽略、须用数值」的错误注释）
  - `tests/lit/MC/Dadao/wpn_operand.s`（删除「裸数字 0–3 回归」块；表头表述更正）
  - `tests/lit/MC/Dadao/wpn_err_bare_num.s`（**新增**：4 条 rwii 助记符裸数字均 Error 的反例）
  - `tests/lit/MC/Dadao/rwii.s`（表头示例注释 `set.zw rd8, 0, ...` → `wp0`）
  - 本任务书
- 非易失证据（gitignored）：`.work/evidence/LLVM-045t/run.sh`；日志 `.work/log/llvm/LLVM-045t-*.log`；临时 `/tmp/opencode/LLVM-045t/`。

**验收结果**（真实命令 + 真实输出 + 退出码；`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"` 制式，无 `tee`）：

1. **构建**（验收 1）：`make build-mc` → `EXIT=0`（增量 8 步：重编 `DADAOAsmParser.cpp.o` → 重链 `llvm-mc/llvm-objdump/llvm-readobj/llc`；log `.work/log/llvm/LLVM-045t-build-mc.log`）。
2. **裸数字被拒**（验收 1，Error 级）：`set.zw rd1, 1, 0x1234` / `set.ow rd2, 0, 1` / `or.w rd3, 3, 0x1` / `andn.w rb4, 2, 0x1` → 均 `EXIT=1` + `error: invalid operand for instruction`。边界：`wp4`（`invalid wyde-position…`）、`4`、`-1`、`WP1`、`foo` 均 `EXIT=1`。
3. **wpN 合法且编码不变**（验收 2，修复前后逐字节一致）：
   ```
   set.zw rd1, wp1, 0x1234  → [0x4c,0x05,0x12,0x34]   EXIT=0
   set.ow rd2, wp0, 1       → [0x4d,0x08,0x00,0x01]   EXIT=0
   or.w   rd3, wp3, 0x1     → [0x48,0x0f,0x00,0x01]   EXIT=0
   andn.w rb4, wp2, 0x1     → [0x4b,0x12,0x00,0x01]   EXIT=0
   ```
   （修复前对同名 `wpN` 输入实测为同一组字节。）
4. **往返**（验收 2）：`llvm-mc -filetype=obj` → `llvm-objdump -d` 反汇编回 `set.zw rd1, wp1, 0x1234` / `set.w rf5, wp3, 0x7` / `or.w rd3, wp3, 0x1`；`-filetype=asm` 亦回 `wpN`（6/6 匹配，`EXIT=0`）。
5. **反例门控**（验收 3，真实输出 `.work/log/llvm/LLVM-045t-inject.log`）：
   ```
   $ .work/evidence/LLVM-045t/run.sh --inject; echo "EXIT=$?"
   inject: relaxing isWydePosImm to also accept kImmediate (old bare-digit behaviour)
   inject: dirty: llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
   inject: rebuild EXIT=0
   [FAIL] bare-rejected-set.zw | actual: rc=0, no-error (accepted!) | rc=1
   [FAIL] bare-rejected-set.ow | actual: rc=0, no-error (accepted!) | rc=1
   [FAIL] bare-rejected-or.w   | actual: rc=0, no-error (accepted!) | rc=1
   [FAIL] bare-rejected-andn.w | actual: rc=0, no-error (accepted!) | rc=1
   inject: got expected bare-rejected FAIL (4/4)
   inject: restore sha256 unchanged (15a02ddd…36ddc4)
   [PASS] bare-rejected-… (×4)
   inject: PASS (injection FAILed bare-rejected; restore sha256 unchanged; green again)
   EXIT=0
   ```
   注入非空（`git diff --name-only` 非空）；还原用 `git checkout` 且 sha256 一致、`git status` 空、**重建**后回绿。
6. **e2e 无裸数字 + lit/E2E**（验收 4）：`grep` 逐文件核对 `tests/e2e/*.s` 0 命中；`llvm-lit tests/lit/MC/Dadao` → `Passed: 28`（基线 27，+1 `wpn_err_bare_num.s`）；`tests/lit/E2E` → `Passed: 4`；`check_lit_bytes.py` → `110 patterns OK`（去掉 4 条裸数字 OBJ 行，114→110，脚本独立计数一致）；oracle `122 passed, 0 failed`，`Cross-check OK: 122 >= 110`。
7. **`make check`**（验收 5）：`EXIT=0`（log `.work/log/llvm/LLVM-045t-check.log`：lit `32/32`，`repository checks: PASS`）。
8. **补丁**（验收 5）：`make check-patch-tree` → `2 component(s), 77 patches OK`，`EXIT=0`；`make check-source-state` → `llvm-project: OK HEAD=fa4799318a57 count=1 clean=True`。
9. **一键证据**（验收 6）：`.work/evidence/LLVM-045t/run.sh` → `RESULT: PASS (19 checks, 0 failures)`，`EXIT=0`（非交互、任一失败非零退出、逐项 `[PASS]/[FAIL] 检查名 | 期望 | 实际 | rc`、内置 `--inject`、结尾 `exit "$rc"` 无 `tee`）。
10. **未越界**：`git status --short --untracked-files=all` 仅列 8 个改动文件 + 1 个新增 lit + 本任务书；无 `*_tmp*`/`*.orig`/`*.rej`；`.work/source/llvm-project` 干净（`clean=True`）。

**新发现/坑**：

1. **区分「语法记号 vs 裸立即数」必须用独立的 `MCParsedAsmOperand::Kind`**：matcher 的 predicate 只能看到已解析的操作数；`parseWydePosToken` 与 `parseImmediate` 原都造 `kImmediate`，故 `isWydePosImm` 无法区分。新增 `kWydePos` kind 是最小且语义明确的收敛点（无需改 `.td`）。
2. **`.td` 的 `SuperClasses=[DADAOImmAsmOperand]` 不参与 imm/wyde 类匹配**：生成 matcher 仅在 **token/register** 类上用 `isSubclass`（`validateOperandClass` 的 L956/L1251），每个 formal 由各自 predicate 校验（L1676）；因此子类 predicate（`isWydePosImm`）与父类（`isImm`）语义分叉**不引起交叉匹配**（已核生成 `.inc`）。
3. **收紧的副作用（正确方向）**：`wpN` 过去还能被当作**通用立即数**误用（如 `add.si rd1, wp1` 会被当 imm=1）；现在一律拒绝。全库核查 `tests/`/`tools/`/`spec/`/`contracts/` 无一处依赖该误用（`wpN` 仅出现在 rwii wyde 位置或 Python 变量名/direct-encoder）。属预期收紧，建议沉淀。
4. **e2e/注释与事实相反**：`smoke_*.s` 原注释称「wpN 被静默忽略、须用数值」——实为**反了**（`wpN` 一直被正确编码，裸数字被静默接受）。按 ISS-128 已更正。
5. **`check_lit_bytes` 计数是动态自洽的**：删除旧的「裸数字回归」OBJ 行使 114→110，脚本按现存 `; OBJ:` 行独立计数仍一致（非固定阈值），故不受影响。
6. **`wpN` 语义真源**：`spec/Toolchain-01 §汇编格式表`（`rwii | 助记符 dst, wpN, immu16`）、`spec/SimRISC-03`（`set.zw rdHA, wpN, immu16` 等）——与本次收紧一致。
7. **反例注入惯用法**：把 `isWydePosImm` 的 `if (Kind != kWydePos)` 放宽为 `… && Kind != kImmediate` 即复现旧「静默接受」行为；修复用 `git checkout`（源码已 base+1 提交）可精确还原，配 `ninja llvm-mc` 重建即可闭环（还原含重建）。

**遗留问题**：无功能遗留。`tools/llvm/validate_instrinfo.py`/`DADAOInstrInfo.td` 头部计数注释的陈旧问题**非本次引入**，归 `LLVM-046t`（不改，越界）。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查（改动仅 `DADAOAsmParser.cpp` + 测试/补丁/changelog）：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1：新增 `kWydePos` 后 `print()` 等 `switch(Kind)` 是否遗漏分支 | ✅已修（实现时已补） | `print()` 增 `case kWydePos`；分解 `switch` 有 `default` 故无需改 | `make build-mc EXIT=0`（无 `-Wswitch` 告警）；lit 28/28 |
| F2：`isWydePosImm` 改为只认 `kWydePos` 后，裸数字路径是否真的不匹配 | ✅已修 | predicate `if (Kind != kWydePos) return false;` | 4 条裸数字 `EXIT=1` + `error:`；`--inject` 放宽后可复现接受→FAIL |
| F3：wyde 操作数改 kind 后 `addImmOperands` 转换是否仍输出正确 imm | ✅已修（无需改 `addImmOperands`） | `addImmOperands` 用 `ImmVal`（`kWydePos` 已设） | 5 条 `wpN` 编码逐字节匹配修复前值；往返 `wpN` |
| F4：`wpN` 不能再当通用立即数——是否破坏既有用例 | ✅不修（正确收紧） | 无（语义边界） | oracle 122/122、lit 28/28、全库 grep 无该误用 |
| F5：`.td` 子类 predicate 与父类 `isImm` 分叉是否引起交叉匹配 | ✅不修（已核无风险） | 无 | 生成 `DADAOGenAsmMatcher.inc` L956/1251 仅在 token/reg 用 `isSubclass`，L1676 按 formal predicate 校验 |
| F6：`tests/e2e` 注释原为反向错误表述 | ✅已修 | 4 文件 NOTE 更正为「须 `wpN`，裸数字 Error」 | grep 0 裸数字；E2E 4/4 |
| F7：`check_lit_bytes` 固定计数可能失配 | ✅已修（动态自洽） | `wpn_operand.s` 去 4 条 OBJ 行 | `check_lit_bytes: 110 patterns OK`、`N == 独立计数`；oracle cross-check `122>=110` |
| F8：changelog 追加引入尾部空行 | ✅已修 | 去尾部多余空行 | `git diff --stat` = `1 insertion` |
| F9：补丁是否真实导出、可应用 | ✅已修 | `make_patch.py`（未手改） | `check-patch-tree 77 patches OK`、`check-source-state clean=True` |

判决：**全部 finding 已处置，无未修项**；状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**审阅时间**：2026-10-05
**证据脚本**：`.work/evidence/LLVM-045t/run.sh`（317 行）
**日志**：`/tmp/opencode/LLVM-045t-review/`

---

##### 1. 证据脚本审查

脚本结构合理，逐条核验：

| # | 检查项 | FAIL 路径 | 判定 |
|---|--------|-----------|------|
| 1 | mc-exists | `! -x "$MC"` → rc=1 | ✅ 可达 |
| 2–5 | bare-rejected-{set.zw,set.ow,or.w,andn.w} | `rc==0` 或无 `error:` → rc=1 | ✅ 可达（两条件任一即可触发） |
| 6–10 | wp-enc-{set.zw,set.ow,or.w,andn.w,set.w} | `rc!=0` 或不含 `want` → rc=1 | ✅ 可达 |
| 11 | roundtrip | `ok!=6` 或 `odrc/asrc!=0` → rc=1 | ✅ 可达 |
| 12 | e2e-no-bare | `hits` 非空 → rc=1 | ✅ 可达 |
| 13 | lit-mc | `rc!=0` 或不含 `Passed: 28` → rc=1 | ✅ 可达 |
| 14 | lit-e2e | `rc!=0` 或不含 `Passed: 4` → rc=1 | ✅ 可达 |
| 15 | lit-bytes | `rc!=0` 或不含 `patterns OK` → rc=1 | ✅ 可达 |
| 16 | oracle | `rc!=0` 或不含 `122 passed, 0 failed` → rc=1 | ✅ 可达 |
| 17 | patch-def | 缺 `createWydePos` 或 `Kind != kWydePos` → rc=1 | ✅ 可达 |
| 18–19 | check-patch-tree / check-source-state | `make` 退出非零 → rc=非零 | ✅ 可达 |

- 结尾 `exit "$rc"`（L317），无 `tee` 吞退出码 ✅
- `--inject` 模式：注入→重建→验证 FAIL→还原→重建→验证 PASS，流程完整 ✅
- 注入非空（sha256 前后不同、`git diff --name-only` 非空）✅

**脚本判定：合格**（每条断言有可达 FAIL 路径、无恒真、注入可还原、结尾不吞退出码）。

---

##### 2. 重跑证据脚本

```bash
cd /mnt/tao/DADAO-v5 && .work/evidence/LLVM-045t/run.sh > /tmp/opencode/LLVM-045t-review/run.log 2>&1; echo "EXIT=$?"
```

逐项结果（共 19 项）：

| # | 检查名 | 期望 | 实际 | rc |
|---|--------|------|------|----|
| 1 | mc-exists | executable 存在 | exists+exec | 0 |
| 2 | bare-rejected-set.zw | EXIT!=0 + error: | rc=1, error: invalid operand for instruction | 0 |
| 3 | bare-rejected-set.ow | EXIT!=0 + error: | rc=1, error: invalid operand for instruction | 0 |
| 4 | bare-rejected-or.w | EXIT!=0 + error: | rc=1, error: invalid operand for instruction | 0 |
| 5 | bare-rejected-andn.w | EXIT!=0 + error: | rc=1, error: invalid operand for instruction | 0 |
| 6 | wp-enc-set.zw | rc=0, encoding: [0x4c,0x05,0x12,0x34] | match=yes | 0 |
| 7 | wp-enc-set.ow | rc=0, encoding: [0x4d,0x08,0x00,0x01] | match=yes | 0 |
| 8 | wp-enc-or.w | rc=0, encoding: [0x48,0x0f,0x00,0x01] | match=yes | 0 |
| 9 | wp-enc-andn.w | rc=0, encoding: [0x4b,0x12,0x00,0x01] | match=yes | 0 |
| 10 | wp-enc-set.w | rc=0, encoding: [0x4f,0x17,0x00,0x07] | match=yes | 0 |
| 11 | roundtrip | objdump+asm both print wpN (6/6) | match=yes | 0 |
| 12 | e2e-no-bare | 0 bare numeric wyde | 0 hits | 0 |
| 13 | lit-mc | 28/28 MC PASS | Passed: 28 (100.00%) | 0 |
| 14 | lit-e2e | 4/4 E2E PASS | Passed: 4 (100.00%) | 0 |
| 15 | lit-bytes | rc=0, patterns OK | 110 patterns OK | 0 |
| 16 | oracle | 122 passed, 0 failed | ok | 0 |
| 17 | patch-def | kWydePos + createWydePos | ok | 0 |
| 18 | check-patch-tree | make rc=0 | rc=0 | 0 |
| 19 | check-source-state | make rc=0 | rc=0 | 0 |

**RESULT: PASS (19 checks, 0 failures)，EXIT=0**

---

##### 3. 独立注入反例（不复用 engineer 的自检）

**注入点**：`DADAOAsmParser.cpp` L263 `isWydePosImm()` 的 `Kind != kWydePos`
**注入方式**：改为 `Kind != kWydePos && Kind != kImmediate`（复现旧「裸数字静默接受」行为）
**注入前 sha256**：`15a02ddd29c883134a3b00700daa6ad9d4c73ef1ef11a0b4ac46e190e836ddc4`

**Step 1 — 注入 + 验证非空**：
```bash
$ git -C .work/source/llvm-project diff --name-only
llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp    # 非空 ✅
$ sha256sum $ASM  # AFTER ≠ BEFORE ✅
```

**Step 2 — 重建 llvm-mc**（增量 ninja，约 30 秒）：
```bash
$ ninja -j8 -C .work/build/llvm llvm-mc  # BUILD_EXIT=0
```

**Step 3 — 裸数字被静默接受（FAIL）**：
```
set.zw rd1, 1, 0x1234  → RC=0（被接受！应为 RC=1）
set.ow rd2, 0, 1       → RC=0（被接受！应为 RC=1）
or.w   rd3, 3, 0x1     → RC=0（被接受！应为 RC=1）
andn.w rb4, 2, 0x1     → RC=0（被接受！应为 RC=1）
```
→ **注入确认有效**：裸数字不再被拒，旧行为复现。

**Step 4 — 还原 + 重建**：
```bash
$ git -C .work/source/llvm-project checkout -- llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
$ sha256sum $ASM  # RESTORED=15a02ddd...36ddc4（与 BEFORE 一致）✅
$ git -C .work/source/llvm-project diff --quiet && echo "CLEAN"  # CLEAN ✅
$ ninja -j8 -C .work/build/llvm llvm-mc  # REBUILD_EXIT=0
```

**Step 5 — 回绿验证**：
```
set.zw rd1, 1, 0x1234  → RC=1 + error: invalid operand for instruction ✅
set.ow rd2, 0, 1       → RC=1 + error: invalid operand for instruction ✅
or.w   rd3, 3, 0x1     → RC=1 + error: invalid operand for instruction ✅
andn.w rb4, 2, 0x1     → RC=1 + error: invalid operand for instruction ✅
```
→ **回绿成功**。

---

##### 4. 独立复核验收 1–5

| 验收项 | 结果 |
|--------|------|
| 验收 1：裸数字 0–3 → EXIT≠0 + error: | ✅ 4/4 均 `rc=1` + `error: invalid operand for instruction` |
| 验收 2：wpN 编码不变 | ✅ `set.zw→[0x4c,0x05,0x12,0x34]` / `set.ow→[0x4d,0x08,0x00,0x01]` / `or.w→[0x48,0x0f,0x00,0x01]` / `andn.w→[0x4b,0x12,0x00,0x01]` / `set.w→[0x4f,0x17,0x00,0x07]` |
| 验收 2：往返 objdump/asm | ✅ 6/6 匹配（`set.zw rd1, wp1, 0x1234` / `set.w rf5, wp3, 0x7` / `or.w rd3, wp3, 0x1`） |
| 验收 3：反例门控 | ✅ 独立注入→FAIL→还原+重建→回绿（见上 §3） |
| 验收 4：e2e 无裸数字 | ⚠️ **发现**：`smoke_fp.s:34` 注释 `set.zw rdN, 1, immu16` 仍有裸数字 `1`，应改为 `wp1`（详见 §5） |
| 验收 4：lit MC 28/28 | ✅ `Passed: 28 (100.00%)` |
| 验收 4：E2E 4/4 | ✅ `Passed: 4 (100.00%)` |
| 验收 4：oracle 122 | ✅ `122 passed, 0 failed` |
| 验收 4：check_lit_bytes 110 | ✅ `110 patterns OK` |
| 验收 5：make check 32/32 | ✅ `Passed: 32 (100.00%)`，EXIT=0 |
| 验收 5：check-patch-tree 77 | ✅ `77 patches OK`，EXIT=0 |

---

##### 5. 复核：越界 / 细节

| 项目 | 判定 |
|------|------|
| `tests/e2e/*.s` 实际指令无裸数字 | ✅ grep 确认 0 命中（实际指令行） |
| **`smoke_fp.s:34` 注释** | ⚠️ `set.zw rdN, 1, immu16` 仍有裸数字 `1`，任务要求「注释中引用的说明文字须改为正确表述」，应改为 `wp1`。**遗漏** |
| `DADAOInstrInfo.td` 未改 | ✅ 收紧点在 predicate 实现（`isWydePosImm`），`.td` 的 `PredicateMethod=isWydePosImm` 保留不变，正确 |
| changelog 追加 | ✅ 一条追加，内容准确，不越界 |
| 改动范围 | ✅ 8 个改动文件 + 1 个新增 lit + 任务书；无 `*_tmp*`/`*.orig`/`*.rej` |
| 构建纪律 | ✅ `JOBS=8`、增量 ninja、耗时约 30 秒（远低于上限） |
| `wpn_operand.s` 去掉裸数字回归块 | ✅ 4 行 `set.zw rb1, N, 0xffff` 删除，表头注释更正 |

---

##### 6. 判决

**Needs Revision**

理由：`tests/e2e/smoke_fp.s` 第 34 行注释 `set.zw rdN, 1, immu16` 仍含裸数字 `1`，违反任务验收 4 的硬性要求「注释中引用的说明文字须改为正确表述」。

**具体修改建议**：
- `tests/e2e/smoke_fp.s` 第 34 行：`set.zw rdN, 1, immu16` → `set.zw rdN, wp1, immu16`

其余所有功能验证均通过（裸数字拒绝、wpN 编码不变、往返、反例门控、lit/E2E/oracle 全绿、make check 32/32、check-patch-tree 77）。注释修正后无需重建，直接重跑 `run.sh` 确认 e2e-no-bare 即可。

---

#### 第 2 轮 reviewer 复核（改判）

**触发**：engineer 修复 `smoke_fp.s:34` 注释 + 「修一类」扫描。

##### 1. 修复落盘核验

`tests/e2e/smoke_fp.s` 第 34 行（`sed -n '32,36p'`）：
```
;   set.zw rdN, wp1, immu16 sets wyde #1 = register bits[31:16]; bits[15:0]
```
已改为 `wp1` ✅。

##### 2. 重跑 `run.sh`

```bash
cd /mnt/tao/DADAO-v5 && .work/evidence/LLVM-045t/run.sh > /tmp/opencode/LLVM-045t-rereview/run.log 2>&1; echo "EXIT=$?"
# EXIT=0
```

19/19 PASS，EXIT=0。逐项与第 1 轮一致（bare-rejected 4/4、wp-enc 5/5、roundtrip 6/6、e2e-no-bare 0 hits、lit-mc 28/28、lit-e2e 4/4、lit-bytes 110 OK、oracle 122/122、patch-def OK、check-patch-tree OK、check-source-state OK）。

##### 3. 独立「修一类」确认

自行 `grep -rn` 扫描 `tests/e2e/*.s`：

```bash
grep -rEn '(set\.zw|set\.ow|set\.w|or\.w|andn\.w)[[:space:]]+[a-z0-9]+,[[:space:]]*[0-3],[[:space:]]' tests/e2e/
# HITS=1（grep 退出码=1，即 0 命中）✅

grep -rn 'set\.zw.*[[:space:]][0-3],' tests/e2e/
# COMMENT_HITS=1（grep 退出码=1，即 0 命中）✅
```

`e2e/*.s` 实际指令与注释均无裸数字 wyde ✅。

其余文件 grep 命中：

| 文件 | 命中 | 判定 |
|------|------|------|
| `tests/lit/MC/Dadao/wpn_err_bare_num.s` | 4 条（裸数字反例） | 有意反例，正确 |
| `tools/qemu/min_rom_probe_031t.py` | 4 条（QEMU 探针注释） | 不同模块（QEMU），**正确越界** |
| `DADAOInstrInfo.td:31` | 1 条（`.td` 注释 `also accepts wp0-wp3`） | `.td` 注释措辞略有误导（暗示裸数字是主语法），但收紧点在 AsmParser predicate，**不属本任务**。建议另立小任务清理 `.td` 注释，不阻塞本任务 |

##### 4. 改判

**Accepted**

理由：
- 第 1 轮唯一问题（`smoke_fp.s:34` 注释裸数字）已修复 ✅
- 「修一类」扫描确认 e2e 无遗漏；两处越界文件 engineer 判定正确 ✅
- 19/19 PASS，EXIT=0（未动源码，无需重建）✅
- 第 1 轮独立注入反例仍有效（注入→FAIL→还原+重建→回绿，证据在第 1 轮记录中）✅

`LLVM-045t` 可进入 `/complete` 收尾。

---

#### 第 1 轮 engineer 返工（reviewer Needs Revision 修复）

**根因**：`tests/e2e/smoke_fp.s` 第 34 行注释遗漏裸数字修正——`set.zw rdN, 1, immu16` 仍含裸数字 `1`。

**修复**：`tests/e2e/smoke_fp.s:34`：`set.zw rdN, 1, immu16` → `set.zw rdN, wp1, immu16`（其余文字不变）。**未动源码**，故无需重建、无需重导出补丁（`check-patch-tree`/`check-source-state` 不受影响）。

**修一类扫描**（精确正则 `(set\.zw|set\.ow|set\.w|or\.w|andn\.w)\s+op1,\s*[0-3],\s*`，覆盖 `tests/` + `tools/` + changelog + 本任务书；`grep -rn` 复核）——真实残留仅 1 处（已修），其余为**有意反例/引用**或**越界文件**：

| 命中 | 判定 |
|------|------|
| `tests/e2e/smoke_fp.s:34`（`set.zw rdN, 1, immu16`） | ✅ 已修为 `wp1` |
| `tests/e2e/**` 实际指令 | ✅ 0 命中（均为 `wpN`） |
| `tests/lit/MC/Dadao/wpn_err_bare_num.s:5,10,15,20`（`set.zw rb1, 1, …` 等） | ✅ **有意反例**（本任务新增，须裸数字被拒）；`:8,13,18,23` 为其 `CHECK` 回显 |
| 本任务书 §验收 1 / reviewer 记录 §4/§5（`set.zw rd1, 1, 0x1234` 等） | ✅ 引用裸数字作为「应被拒」的输入/证据，非缺陷 |
| `tools/qemu/min_rom_probe_031t.py:103,126,171,172`（注释 `set.zw rd62, 0, 0`） | ⚠️ 越界文件（非本任务范围），且为 direct-encoder 的机器字说明；**未改**并在此披露 |
| `DADAOInstrInfo.td:31` 注释「2-bit value 0-3, also accepts wp0-wp3」 | ⚠️ 措辞已略陈旧（现仅 `wpN` 合法），但属源码、改动会触发重建+补丁重导出，**未改**并披露 |

**重跑**（`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`）：
```
$ .work/evidence/LLVM-045t/run.sh > .work/log/llvm/LLVM-045t-run-after-fix.log 2>&1; rc=$?; echo "EXIT=$rc"
RESULT: PASS (19 checks, 0 failures)
EXIT=0
```
回绿（含 `e2e-no-bare` 检查 PASS）；`git status` 与修复前一致（新增 0 文件、仅 `smoke_fp.s` 多一处注释行改动）。

**遗留**：`tools/qemu/min_rom_probe_031t.py` 注释与 `DADAOInstrInfo.td:31` 措辞为**披露的越界项**，如需更正当另立任务（本任务硬约束限定 `.work/source/llvm-project`（若需）+ `tests/`，且预测不改源码）。
