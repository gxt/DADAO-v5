# SPEC-152t: ISA 编码再分配与 `ror` 的规范面（`ext` 迁出 / `shl` 迁入并去 `u` / 新增 `ror`）

**模块**：spec
**项目里程碑**：M9
**依赖**：`ADR-0032`（**`Accepted`**，`D1`–`D6` 已于 2026-10-19 逐条确认；**开工前置 = `spec/` 改动授权原话落纸**）、`SPEC-141t`（`ror` 预研：候选 A 形态/收益/六环代价）、`SPEC-142t` / `SPEC-143t`（MISC-octa 子表补格 + 只读锁重算先例）、`SPEC-145t` / `SPEC-149t` / `SPEC-150t`（用户授权 + 只读册 `sha256` 同步先例）、`docs/Process-06`（`spec/` 目录保护）
**状态**：待验收

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

## 用户授权（`spec/` 改动，逐字）

> 渠道 = 经主会话问答；原话逐字取自 `ADR-0032 §Context`（该 ADR 已于 2026-10-19 转 `Accepted`，`D1`–`D6` 逐条确认原话「**没异议**」；本册由 architect 于 2026-10-19 下发执行）。
>
> - 「**增加两件事情：第一件事：修改ext的编码，ext.uo的opx改为100-000/101-000；ext.so的opx改为100-001/101-001；核实是否可行，然后我说第二件事**」
> - 「**是的，腾出编码**」
> - 「**第二件事：把四个子表中的shl.ux的opx改为010-000/011-000，即刚才ext.uo腾出来的位置；然后增加ror.ux指令，其opx为010-001/011-001，即刚才ext.so腾出来的位置；ror指令的格式分别为orrr/orri，针对的都是rd寄存器**」
> - 「**ror不区分有符号数还是无符号数，是否有必要在后缀里带u**」→「**可以去掉u；同理，shl有必要带后缀u吗？**」→「**确认立项**」
>
> 授权范围 = 上述编码迁移/改名/新增 `ror` 及由此必需的规范面机械同步（含只读锁重算）；不含其它 `spec/` 语义改动。

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
**测试结果**：必绿 20/20 PASS；预期红 3/3 确认（`check-instrinfo` / `check-isa-coverage` / `check-interface` 均 rc=2，原因 = `.td` / QEMU `trans_*` 未改，归 `LLVM-116t` / `QEMU-064t`）；`run.sh` default rc=0、`--inject` rc=0。
**修改文件**：`spec/`（SimRISC-00/04/08/09/10、DADAO-11、DADAO-22）；`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`；`.tao/contracts/contract-isa.md`、`.tao/contracts/contract-asm-list.md`；`manifests/spec-readonly.lock.toml`；`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`tools/spec/gen_legality_list.py`；`tools/llvm/gen_asm_list.py`；`tools/testcases/generate_isa_vectors.py`、`tools/testcases/validate_mc_vectors.py`（注释）；`tests/vectors/inventory.md`、`tests/vectors/isa/reg-shift-extend.yaml`；`tests/llvm/lit/MC/DADAO-gen/gen-orrr.s`、`gen-orri.s`；本册。
**验收结果**：
- 四表逐格（80 格断言 `check_tables.py` rc=0）：octa `010-000` ext.uo→shl.o、`010-001` ext.so→ror.o、`010-100` shl.uo→空；`011-000/001/100` 同；`100-000/001` 空→ext.uo/ext.so、`101-000/001` 空→ext.uo/ext.so。tetra `010/011-000` 空→shl.t、`010/011-001` 空→ror.t、`010/011-100` shl.ut→空；wyde/byte 分别同构（w/b）。
- `opcodes.yaml` 235→243（现场派生：m1 156 / fp 60 / excluded 11 / m3 1 / m8 7 / m9 8）；`validate-encoding` rc=0；`check-scope` rc=0。
- `spec/` 内 `shl.u[otwb]` **0 命中**；全仓实现/生成物残留 54 处（文件+行数见 `.work/log/spec/SPEC-152t/SPEC-152t-shl-u-residual.log`，归后两册）；历史记录（`.tao/archive`/`.tao/adr`/任务书）不改。
- 证据：`.work/evidence/SPEC-152t/run.sh`（default 20 项必绿 + 3 项预期红；`--inject` 两条：opcodes `ha 0x10` 撞格 ⇒ `validate-encoding` 红；表格写回 `shl.uo` ⇒ `check_tables` 红；`cp`+md5 还原后双绿）。
- **`L1` 预期红**：至 `LLVM-116t`/`QEMU-064t` 收口（`check-instrinfo`/`check-isa-coverage`/`check-interface`，如实记录、不为转绿改实现）。
**新发现/坑**：① `check-spec-codeblocks` 额外命中 `DADAO-11`/`DADAO-22` 的汇编示例（6 处 `shl.uo`），必须机械改名并计入只读锁；② 任务书事实 4「`shr.s*` 8 命中」实指 `SimRISC-00` 表内 8 格，全 `spec/` 现为 59 命中（含正文/生成区）；③ `check-instrinfo` 不检查 `scope: m9`（`ror` 无 `.td` 定义也不报）⇒ 覆盖盲点，须 `LLVM-116t` 补。
**遗留问题**：① 预期红三项按跨册归属处理（见上）；② 未改 `tests/llvm/lit/MC/DADAO/imm-range.s`、`CodeGen/DADAO/br-jt.ll`、`tools/llvm/llvm-isa-backend-matrix.*`、QEMU 探针/补丁（归后两册）；③ architect 下发的任务消息未附独立 `spec/` 授权句，本册按 `ADR-0032 §Context` 逐字引录；若审查要求更严格，请主会话补用户原话。

### 返工（2026-10-20）

**测试结果**：`run.sh` default **rc=0**（25 项必绿，含 `check-instrinfo`/`check-isa-coverage`/`check-interface` 已改必绿断言）；`run.sh --inject` **rc=0**（2 组独立注入，各「红 → `cp`+md5 还原 → 绿」）；`make check`（L1）**rc=0**。
**修改文件**：新增 `tools/spec/check_tables.py`（校验器**入 git**）；重写 `.work/evidence/SPEC-152t/run.sh`；`.work/evidence/SPEC-152t/check_tables.py` 改**薄壳**（`.work` 不入 git）；本册。**未触碰** `spec/`、`contracts/`、`.tao/contracts/`，未 commit/push。
**验收结果**：
- **期望网格现场派生**：`contracts/opcodes.yaml` 每条记录 `(op, ha)` → `(子表, ha[5:3] 行, ha[2:0] 列)`，格内容 = 记录 `id`；再与 `SimRISC-00` 四表文本**双向**比对（缺格 / 多格 / 内容不符 均红）。现跑：**4 表 101 条记录 / 256 格，0 格不符**（记录数/格数/非空数均现场统计打印，代码内**无字面网格**）。
- `--self-test`（临时树 `/tmp/opencode/SPEC-152t-rework/`）：baseline rc=0；改 `opcodes.yaml` 一格 ⇒ rc=1；改 `spec` 表一格 ⇒ rc=1；删 `spec` 一格 ⇒ rc=1。
- `.work` 那份**改薄壳**（`runpy` 调仓库内真源）而非删除：本册正文与历史日志仍引用该路径，删除会使 `check-knowledge-refs` 悬空（实测 rc=2）；薄壳无任何逻辑，避免"两份实现漂移"。
- 3 项「预期红」按现场改**必绿**（后端已由 `LLVM-116t`/`QEMU-064t` 收口），另增 `check-run-artifacts` 自检；日志统一 `SPEC-152t-evidence-*.log` / `SPEC-152t-inject-*.log`（`docs/Process-08` A3）。
**新发现/坑**：① 证据工具放 `.work/` 被 `.gitignore` 忽略、无法版本控制 ⇒ 校验器必须落 `tools/spec/`，`.work` 只留薄壳；② 删除被任务书/日志引用的 `.work` 路径会破 `check-knowledge-refs`（悬空即红）；③ `run.sh` 日志名不匹配 `<TASK-ID>-*` 会被 A3 判红并级联破 L1。
**遗留问题**：无（真源与四表内容零改动；三项后端门控已转绿，`git status -uall` 仅 `?? tools/spec/check_tables.py`）。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 生成器窄位宽 `orri` 初版只给 shl/ror 加 `immu6 <= N`，把 `shr.*` 原约束丢了 | ✅已修 | `generate_opcodes.py` 四个 `orri` 统一保留 `immu6 <= nbits` | `spec/SimRISC-08` `encode_sbz` 由误降的 2 条恢复为 4 条（shl/ror/shr.ut/shr.st）；`check-legality-drift` rc=0 |
| F2 spec 附录写了 `ADR-0032`/`SPEC-152t`，`check-spec-changelog` 红 16 项 | ✅已修 | 5 册附录改为纯语义描述（不写任务/ADR 号） | `check-spec-changelog` PASS；`run.sh` 记录 |
| F3 改 `shl.uo` 后 `check-spec-codeblocks` 命中 `DADAO-11`/`DADAO-22` 示例 | ✅已修 | 6 处机械改名 `shl.uo `→`shl.o  `；两册 `sha256` 同步 | `check-spec-codeblocks` PASS（647 行）；`check-spec-readonly` 21 册 OK |
| F4 契约 §6.4.5 写「三种操作数均为 rd 银行」，orrr 实为 4 个字段 | ✅已修 | 改为「操作数寄存器均为 `rd` 银行」 | `check-spec-refs`/`check-spec-drift` rc=0 |
| F5 任务消息限定的文件集不含生成器/契约/向量，但验收门控必需 | ✅已修（披露） | 改动面扩到 `tools/spec/*`、`contract-asm-list`、`contract-isa`、`tests/vectors/*`、gen lit；均在任务书阶段 C 授权面内 | 完成区「修改文件」逐项；`git status` 无 `components/**`/`tests/scripts/**`/`tests/e2e/**` |
| F6 注入脚本的还原不得用 `git checkout` | ✅已修 | `run.sh --inject` 用 `cp` 备份 + md5 前后对账 | `--inject` 输出「md5 对账：两个文件均已还原」；还原后 `validate-encoding`/`check_tables` 回绿 |

**自审判决**：无未修 finding；实现与 `ADR-0032 D1`–`D6` 逐条对齐；未改任何实现（`components/**`、QEMU/LLVM 代码）。任务保持 `待开始`（按 architect 下发要求不改 `**状态**`）。

#### 第 1 轮 reviewer 验收（2026-10-20）

**复核项与真实输出**：
- ADR-0032 = Accepted ✓（line 3）、D4 修订为 `rol` ✓（§修订段）
- opcodes.yaml：**243** 条（m1=156/fp=60/excluded=11/m3=1/m8=7/m9=8）✓，`rol` **8** 条 / `ror` **0** 条 ✓
- 四表独立重算（ADR-0032 D4 修订版期望 `rol.*`）：**80 格 0 不符** ✓；ext 迁 `100/101-000/001`、shl 迁 `010/011-000`、rol 占 `010/011-001` ✓
- `make check`（L1）rc=**0** ✓（含 `check-instrinfo` 0 errors、`check-isa-coverage` PASS、`check-scope` PASS）
- 独立注入：`opcodes.yaml` 中 `rol.o_orrr_rd` scope m9→m1 ⇒ `check-scope` rc=**1**（m1=157,m9=7）；`cp`+md5 还原后 rc=**0** ✓

**不符/问题**：
1. **证据脚本 `check_tables.py` EXPECTED 仍写 `ror.*`**（8 处），与 ADR-0032 D4 修订后的 `rol` 真源不一致 ⇒ `check_tables.py` rc=1（8 格不符），`run.sh default` 必红。
2. **`run.sh` 标注 `check-instrinfo`/`check-isa-coverage`/`check-interface` 为「预期红」**——但 `LLVM-116t`/`QEMU-064t` 已落地且 `install-host` 已更新，三项现全绿 ⇒ `run.sh default` 报 4 FAIL（3 项「预期红项意外转绿」+ table-cells），rc=**1**。
3. **`run.sh` 日志命名违反 A3**：写入 `evidence-*.log` / `inject-*.log`（不匹配 `<TASK-ID>-*`），触发 `check-run-artifacts` 红并级联破坏 L1。
4. 完成区声称「run.sh default rc=0、80 格断言 0 不符、预期红 3/3」均与当前现场不符。

**判定**：**Needs Revision**——① 更新 `check_tables.py` EXPECTED 为 `rol.*`；② 移除 `run.sh` 的 3 条「预期红」断言（LLVM/QEMU 已收口）或改为条件跳过；③ 修正 `run.sh` 日志命名前缀为 `SPEC-152t-<name>`。

#### architect 提交留痕（2026-10-19）
档位：**正常提交**（无 `WIP:` 前缀，按父会话明确指令）。**如实披露**：本笔提交时「第 1 轮 reviewer 验收」为**空**、`**状态**` = `待验收` ⇒ 严格按角色规则应为 `WIP:`；本笔依主会话指令执行，若后续判 `Needs Revision`，返工提交仍落本分支并随 squash 收口。开工分支 `SPEC-152t` 实现提交 `7560453`，squash 落 `master`（单提交；**未 push**）。
文件集 **24 项**对账：`spec/` 7 册 + `contracts/opcodes.yaml`、`contracts/legality_rules.yaml` + `.tao/contracts/` 2 册 + `manifests/spec-readonly.lock.toml` + `tools/spec` 3 器 + `tools/llvm/gen_asm_list.py` + `tools/testcases` 2 器 + `tests/vectors` 2 册 + gen lit 2 册 + 本册 = 完成区「修改文件」逐条一致；**architect 账面 1 项**（`.tao/knowledge/milestones.md`，状态行/流水行同步）= 已披露的**多提**（台账范围）。`INTEG-036m`（归档 `M8`）无本任务号 ⇒ 无需改。**无漏提 / 无越界**。
秒级门控：`run.sh` default rc=0（20 必绿 + 3 预期红均 rc=2）、`check-milestones-fresh` rc=0（5 行 PASS）；**`L1` 预期红至 `LLVM-116t`/`QEMU-064t` 收口**。

#### 返工要求（architect，2026-10-20；主会话依据 reviewer `Needs Revision` 指派）
1. `.work/evidence/SPEC-152t/check_tables.py` 的 `EXPECTED` **必须从真源现场派生**（`contracts/opcodes.yaml` + `spec/SimRISC-0x` 四表），**禁**再把 `ror.*` 等字面写死（同一病根第二次：`validate_instrinfo --self-test` 已因此返工）。
2. `run.sh` 中 3 项「预期红」（`check-instrinfo`/`check-isa-coverage`/`check-interface`）**已转绿** ⇒ 改为必绿断言（或按现场条件跳过），**预期与实际一致**，不许留假红。
3. `run.sh` 日志命名须符合 `docs/Process-08`（`<任务号>-<用途>.log`）；`evidence-*.log`/`inject-*.log` 会触发 `check-run-artifacts` 红并级联破 L1（A3）。

#### architect 收尾（文件集审核，2026-10-20，分支 `ISA-chain-complete`）
- 状态：`待验收` → **`待返工`**（reviewer `Needs Revision`；审阅记录未改写，返工要求段见文末）。
- 文件集：本册 = 提交 `b6d691a`（`WIP:` 前缀；含 reviewer 已写未提交的验收段 + 本册返工要求段）；`milestones.md` 该册行/清单/进度行 = `23da6b7`。**无漏提 / 无多提 / 无越界**。
- 门控：`make check`（L1）rc=**0**。
- 提示（给返工 engineer）：本册真源/四表内容已被 reviewer 复核 **80 格 0 不符**，返工**只碰证据脚本**（`check_tables.py` / `run.sh`），**不得**改 `spec/`/`contracts/`。

#### 第 2 轮 engineer 自审（返工，2026-10-20）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| G1 `--self-test` baseline 用 `expect_zero=0/1` 判真值，四例判定全反（baseline 报 FAIL） | ✅已修 | 用例改传 `True`/`False` | `--self-test` 4/4 PASS、rc=0 |
| G2 直接删除 `.work/evidence/SPEC-152t/check_tables.py` ⇒ 本册正文引用悬空，`check-knowledge-refs` rc=2 | ✅已修 | 改为 `runpy` 薄壳（逻辑全在 `tools/spec/check_tables.py`） | `make check-knowledge-refs` rc=0；薄壳跑默认/`--self-test` 均 rc=0 |
| G3 `run.sh` 两组注入耦合在同一路径、日志名 `evidence-*`/`inject-*` 不合 A3 | ✅已修 | 拆两组独立注入（各自备份/还原/md5 对账）；日志前缀 `SPEC-152t-` | `--inject` rc=0；`check-run-artifacts` rc=0 |
| G4 完成区旧「预期红 3/3」与现场不符（后端已收口转绿） | ✅已修 | 三项改必绿断言，另纳 `check-run-artifacts` | `run.sh` default 25/25 PASS、rc=0 |

**自审判决**：无未修 finding；未改 `spec/`/`contracts/`；未 commit/push；`**状态**` 保持 `待返工`（由 architect 置回 `待验收`）。

#### architect 提交留痕（2026-10-20，返工）
档位：**正常提交**（返工完成退回验收，无 `WIP:`）`8bb7008`。文件集 **3 项**：`tools/spec/check_tables.py`（新增，完成区已声明）+ 本册（已声明）+ `.tao/knowledge/milestones.md`（architect 状态同步，任务书未声明 = 已披露的**台账范围**）。`.work/evidence/**` 属忽略区未入 git；**无漏提 / 无越界**。
门控：`check_tables.py` default rc=**0**（4 表 101 记录 / 256 格 / 0 不符）、`--self-test` rc=**0**（4/4）；`make check`（L1）rc=**0**（首次 rc=2 = 台账「一句改动」123 字符 > 120，缩短后转绿）。**未 push**。
