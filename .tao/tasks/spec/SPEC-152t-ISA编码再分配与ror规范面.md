# SPEC-152t: ISA 编码再分配与 `ror` 的规范面（`ext` 迁出 / `shl` 迁入并去 `u` / 新增 `ror`）

**模块**：spec
**项目里程碑**：M9
**依赖**：`ADR-0032`（**`Accepted`**，`D1`–`D6` 已于 2026-10-19 逐条确认；**开工前置 = `spec/` 改动授权原话落纸**）、`SPEC-141t`（`ror` 预研：候选 A 形态/收益/六环代价）、`SPEC-142t` / `SPEC-143t`（MISC-octa 子表补格 + 只读锁重算先例）、`SPEC-145t` / `SPEC-149t` / `SPEC-150t`（用户授权 + 只读册 `sha256` 同步先例）、`docs/Process-06`（`spec/` 目录保护）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实（**先读，勿重复查证；仍须现场复核**）

- **来源**：`ADR-0032`（`D1`–`D6`）+ 用户 2026-10-19 原话（**逐字**，渠道 = 经主会话问答；全文见该 ADR `§Context`）：
  - 「**修改ext的编码，ext.uo的opx改为100-000/101-000；ext.so的opx改为100-001/101-001**」
  - 「**把四个子表中的shl.ux的opx改为010-000/011-000…然后增加ror.ux指令，其opx为010-001/011-001…格式分别为orrr/orri，针对的都是rd寄存器**」
  - 「**可以去掉u；同理，shl有必要带后缀u吗？**」→「**确认立项**」
- **已核事实（主会话 2026-10-19；本册执行时逐条复核并留命令输出）**：
  1. 基表 `010-000/001` = `ext.uo/so`（orrr）、`011-000/001` = `ext.uo/so`（orri）；`010-100`/`011-100` = `shl.uo`；
  2. 三个宽度表（`SimRISC-08/09/10`）`010-000/001`、`011-000/001` **空**，`010-100`/`011-100` = `shl.u*`；
  3. 基表 `100-000/001`、`101-000/001` **全空** ⇒ `ext` 可整体迁入；
  4. `spec/` 内 `shl.s*` **0 命中**、`shr.s*` **8 命中** ⇒ `shl` 无算术变体；
  5. `shl.u*` 全仓引用面约 **170 处**（主会话核；本册现场重数，**不写死**）。

## 目标

在不改任何实现的前提下，把**编码真源**改到位并让**规范面门控全绿**：

1. **四张表**（基表 + `SimRISC-08/09/10`）：`ext` 迁 `100/101` 的 `000/001`；`shl` 迁 `010/011` 的 `000` 并去 `u`；`ror` 占 `010/011` 的 `001`（四宽度）。
2. **语义条文**：`SimRISC-04 §4.2` 与 `SimRISC-08/09/10 §4.2` 增补 `ror` 定义（逻辑循环右移、单向、无 `u/s`、窄位宽取模/越界 ILLI、目的 `rd0` ⇒ ILLI）。
3. **编码投影**：`contracts/opcodes.yaml` 重生成（新增 `scope: m9` 8 条；`check_scope.py` 白名单/计数同步）；`.tao/contracts/contract-isa.md` / `contract-asm-list.md` 同步。
4. **助记符改名落纸**：`spec/`、契约、生成器、语料/向量/生成 lit 的**机械改名**（语义不动）；引用面**逐条清单**留证据。
5. **只读锁**：仅对改动册重算 `sha256`，授权原话落本册。

## 接口规范

- **输入（真源）**：`ADR-0032` `D1`–`D6`（确认后）；`spec/SimRISC-00 §4.2` 四表、`SimRISC-04 §4.2`、`SimRISC-08/09/10 §4.2`；`tools/spec/generate_opcodes.py`；`tools/spec/check_scope.py`；`tools/llvm/gen_asm_list.py`；`tools/testcases/generate_isa_vectors.py`、`generate_lit_vectors.py`；`manifests/spec-readonly.lock.toml`。
- **输出**：
  1. `spec/SimRISC-00-指令系统设计.md`（四张表 + 表下例外/说明 + 附录变更记录）；
  2. `spec/SimRISC-04-64位数据运算.md`（`§4.2` 语义 + 逐条表 + 生成区 + 册头分类计数 + 附录）；
  3. `spec/SimRISC-08-32位数据运算.md` / `SimRISC-09-16位数据运算.md` / `SimRISC-10-8位数据运算.md`（表 + `§4.2` + 生成区 + 册头计数 + 附录）；
  4. `spec/Toolchain-01-汇编语言.md`（**现场核**：仅当出现 `shl.u*`/`ext` 编码示例时改；改则版本 `0.5.3 → 0.5.4` + 附录，不改则留 `grep` 证据）；
  5. `contracts/opcodes.yaml`（重生成）、`.tao/contracts/contract-isa.md`（`§2.8`/附录 A、`§6.4.1`、新增 `§6.4.5 ror`）、`.tao/contracts/contract-asm-list.md`（重生成）；
  6. `tools/spec/generate_opcodes.py`（`ha`/助记符/`scope: m9`）、`tools/spec/check_scope.py`（`ALLOWED_SCOPES` + 计数）、`tests/vectors/inventory.md`（id 机械改名）、`tests/vectors/isa/reg-shift-extend.yaml` 与 `tests/llvm/lit/MC/DADAO-gen/*`（重生成）；
  7. `manifests/spec-readonly.lock.toml`（改动册 `sha256` + 授权注记）；
  8. 本册完成区 + `.work/evidence/SPEC-152t/**`（default + `--inject`）+ 日志 `.work/log/spec/SPEC-152t/**`。
- **约束**：
  - **不改** `components/**`、任何实现代码、`tests/scripts/**`；**不改** 既有 `scope: m1` 语义（`shl` 改名**只改名字**）。
  - **`ror` 的 `scope` = `m9`**（新增指令，非 M1 身份；`check_scope.py` 扩展白名单）。总数 = 235 + 8 = **243**（现场派生，不写死；本册验收按「`m1` 156 / `fp` 60 / `excluded` 11 / `m3` 1 / `m8` 7 / `m9` 8」逐项核）。
  - **计数不写死**：引用面、表格条数、opcodes 总数一律现场统计。
  - **期望值独立**：`ror` 语义条文按定义手写（逻辑循环右移），不从 QEMU/LLVM 反推。
  - **`spec/` 只读**：仅在本册取得的授权范围内改动；其它册 `sha256` 不变。
  - **不动旧助记符别名**（`ADR-0032 D3` 被否项）。

## 做（顺序 = `ADR-0032 D5`）

### 阶段 0：开工前置

1. 核 `ADR-0032` 已转 `Accepted` 且 `D1`–`D6` 逐条确认；**用户对 `spec/` 的授权原话逐字落本册**（`docs/Process-06`）。未满足 ⇒ **停**，不写 `spec/`。
2. 现场复核 `§立项来源` 的 5 条事实，命令与输出留 `.work/log/spec/SPEC-152t/**`。

### 阶段 A：表格（先 `ext` 迁出 → 再 `shl` 迁入 → 再 `ror` 占位）

1. `SimRISC-00` 基表（`MISC-octa`）：
   - `100-000` = `ext.uo`（orrr）、`100-001` = `ext.so`（orrr）；`101-000` = `ext.uo`（orri）、`101-001` = `ext.so`（orri）；
   - `010-000` = `shl.o`（orrr）、`010-001` = `ror.o`（orrr）；`011-000` = `shl.o`（orri）、`011-001` = `ror.o`（orri）；
   - 其余（`shr.uo/so`、`ctpop`/`ctlz`/`cttz`、`cmp` 等）**格位不变**。
2. `SimRISC-08/09/10`：`010-000` = `shl.t/w/b`（orrr）、`010-001` = `ror.t/w/b`（orrr）；`011-000`/`011-001` 同名 orri；`shr.*`、`add.*` 等**格位不变**。
3. 表下说明：`shl` 去 `u` 的命名规则（`ADR-0032 D3`）；`ror` 的单向/无 `u/s`（`D4`）；若有「例外」注记（如 `ctpop`）保持不动。

### 阶段 B：语义条文

1. `SimRISC-04 §4.2`：把 `shl.u` 改 `shl`（含公式块与逐条表）；新增 `ror` 语义块与逐条表：
   - `ror.o: rdHB[63:0] = ror64(rdHC[63:0], amount)`；`amount` = `rdHD[5:0]`（orrr）或 `immu6`（orri，`0..63`）；
   - 窄变体：`ror.t/w/b` 的 `amount` = 源低位 `log2(W)` 位；orri 的 `immu6` 有效 `0..W-1`，越界 ⇒ ILLI；
   - 目的 `rd0` ⇒ ILLI；结果写满（`SPEC-069t` 值语义）。
2. `SimRISC-08/09/10 §4.2`：同步 `shl` 改名与 `ror` 条文（各自位宽 `W=64/32/16/8`；上位界 `N=W-1`）。
3. 生成区（`<!-- ASSEMBLY_LIST_START -->` …）由 `tools/llvm/gen_asm_list.py` 重生成，**不手改**。

### 阶段 C：生成器与投影

1. `tools/spec/generate_opcodes.py`：
   - `build_misc_octa`：`ext` orrr `ha 0x20/0x21`、orri `ha 0x28/0x29`；`shl` orrr `ha 0x10`、orri `ha 0x18`；`ror` orrr `ha 0x11`、orri `ha 0x19`；
   - `build_misc_fixed_width`：`shl.*` orrr `0x10`、orri `0x18`；新增 `ror.*` orrr `0x11`、orri `0x19`（`immu6 <= nbits`）；
   - 新增记录 `scope="m9"`；docstring/计数注释同步。
2. `tools/spec/check_scope.py`：`ALLOWED_SCOPES` 增 `m9`；计数（`EXPECTED_*`）与 `docstring` 同步；**保留可达 FAIL**（删一条 `m9` 记录 ⇒ 计数不符）。
3. 重生成（顺序固定）：
   - `python3 tools/spec/generate_opcodes.py`
   - `python3 tools/llvm/gen_asm_list.py`
   - `python3 tools/testcases/generate_lit_vectors.py`
   - `python3 tools/testcases/generate_isa_vectors.py`
4. `tests/vectors/inventory.md`：`shl.u*` 的 8 个 id 机械改名（`shl.o/t/w/b`），**不加** `ror`（`scope: m9` 非 M1 身份）。

### 阶段 D：只读锁与证据

1. `manifests/spec-readonly.lock.toml`：仅对实际改动册重算 `sha256`，文件头追加「2026-10-19（`SPEC-152t`，用户授权原话…）」注记。
2. `.work/evidence/SPEC-152t/**`：default 跑全部门控；`--inject` 至少 1 条可达 FAIL（建议：把 `ror.o` orrr 的 `ha` 改成 `0x10` ⇒ 与 `shl.o` 冲突，`validate-encoding`/`check-scope` 必须红；`cp` 备份 + `md5` 对账还原）。
3. `.work/log/spec/SPEC-152t/**` 落原始日志（命名 `SPEC-152t-*.log`）。

## 验收标准

1. **前置**：`ADR-0032` = `Accepted` 且 `D1`–`D6` 逐条确认；本册含用户 `spec/` 授权**原话**；未满足则本册不得报 `待验收`。
2. **四表逐格**：基表 8 个目标格位（`010-000/001`、`011-000/001`、`100-000/001`、`101-000/001`）与三宽度表的 `010-000/001`、`011-000/001` 与 `ADR-0032` 完全一致；无重复格、无 `ext`/`shl` 残留旧格；`shr`/`cmp`/`ctpop` 等格位不变。逐格证据落盘。
3. **助记符改名**：活树（排除 `.git`/`.cache`/`.work`/`.tao/archive`/`.dadao`）`shl.u[otwb]` **0 命中**；`shl.s*` 仍 **0**；`shr.s*` 仍 **8**（现场重数，不符须解释）。
4. **`ror` 语义**：`SimRISC-04 §4.2` 与三宽度册条文含：单向、无 `u/s`、`orrr`/`orri`、`rd` 银行、`0..W-1`（orri 越界 ILLI）、`dst_rd0` ILLI、窄位宽寄存器量取模；与 `ADR-0032 D4` 逐条对齐。
5. **门控（本册范围）**：
   - `make validate-encoding` rc=0；
   - `make check-scope` rc=0（`m9` = 8、总数现场派生 = 243）；
   - `make check-rule-refs`、`make check-legality-invariants` rc=0；
   - `make check-asm-list`、`make check-asm-list-drift`、`make check-spec-codeblocks`、`make check-spec-refs`、`make check-spec-drift`、`make check-spec-numbering`、`make check-spec-changelog` rc=0；
   - `make check-spec-readonly` rc=0；
   - `make validate-vectors` rc=0；
   - `python3 tools/testcases/check_lit_gen.py` rc=0。
   - **跨册预期红（不得冒充绿）**：`make check-instrinfo`、`make check-isa-coverage`、`make check-interface` 在 `LLVM-116t`/`QEMU-064t` 落地前为红，须在本册完成区**如实列出**并注明归属；不得为转绿而改实现。
6. **可达 FAIL**：`--inject` 注入（`ha` 冲突）后至少 `validate-encoding`/`check-scope` 之一非零；还原后 `md5` 一致且门控回绿；给出注入前/后/还原三段真实输出。
7. **只读锁**：`manifests/spec-readonly.lock.toml` 中**仅**改动册 `sha256` 变化（逐册 diff 留证）；授权注记含日期/任务号/原话。
8. **零实现改动**：`git status --porcelain -uall` 的证据须证明未触碰 `components/**`、`tests/scripts/**`、`tests/e2e/**`；越界即披露。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
