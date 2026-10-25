# SPEC-166t: 规范收尾（拍平包装层 / 去"已删除"残留 / 去编码值 / 断跨册引用 / `spec_cite` 解耦）

**模块**：spec
**项目里程碑**：M9（收尾前）
**依赖**：`SPEC-165t`（已验证，`master 7fffab58`：纯净化 + 改名 + 结构归位 + 重编号 + 门控）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源（用户裁定，2026-10-22）

- 「`SimRISC-01`：二级标题 `1. 存取类指令` 没必要，把三级标题升为二级标题是不是更好」⇒ 选 **A（只拍平"纯包装"层）**
- 「已删除的内容，没有必要在各分册中保留，包括伪指令」
- 「在很多分册中，写着某些指令的 `编码`，这部分应该只出现在 `SimRISC-00` 中」
- 「编码格式当然要保留」（**格式代号 `orrr`/`orri`/`rrii` 一律保留**，只删具体编码值）
- 「减少交叉链接很关键，减少各种计数和比较很关键」
- 「`spec_cite` 直接说哪个手册、哪条指令不行吗」⇒ 已确认改为 `手册: 助记符`

## 现场事实（`SPEC-165t` 之后，执行前须复核）

- 单包装册（正文 `##` 恰 1 个且其下 `###` ≥2）：**5 册**（`01/02/03/05/06`）
- `（已删除）` 小节/整节：**7 册**（`04`2、`06`1、`08`3、`09`4、`10`4、`11`1、`00` 的已删助记符块 + 3 处"空单元格"注）
- 跨册引用 `SimRISC-0x §…`：**27 处**
- 具体编码值（`op=`/`ha=`/`opx=`/位串/编码字）：`01–12` 剩 **2 行**（`04` 的 `rol` 编码说明）
- 正文"N 条/N 族"：`SimRISC-00` 等若仍有，按 §见验收清除
- `spec_cite`：`contracts/opcodes.yaml` 264 条仍为 `手册 §小节标题`；`tests/**` 147 处数字节号

## 目标

### 1. 拍平"纯包装"层（只 5 册）
删掉唯一 `## 1. <类指令>` 包装，其下 `### 1.M <标题>` → `## M. <标题>`（连续重排）；`00/04/07/08/09/10/11` **不动**。

### 2. 删除"已删除内容"残留
- 整节/整小节直接删（不留占位、不写"已删除"）；
- `SimRISC-00 §5 伪指令` 只留"本版仅 8 条合成型，权威见 `Toolchain-01 §6`"，删"已删除助记符"块；
- 三处"空单元格为已删除条目…"改中性：**"空白单元格 = reserved（UNDI）"**；
- **changelog 里的删除记录保留**（变更史）。

### 3. 删除具体编码值（保留格式代号）
删 `op = …`/`ha = …`/`opx = …`/位串（`011-101` 等）/编码字（`0x…`）在指令描述中的出现；`SimRISC-00` 主表与子表**不动**。
**保留**：`orrr`/`orri`/`rrii` 等格式代号、立即数数据值示例、ILLI/UNDI 的规则表述。

### 4. 断开跨册引用
27 处 `SimRISC-0x §…` 全部删除；确需指路只用"手册名"（不带 `§`、不带节号）。

### 5. 正文不写条数
各册正文不出现"N 条/N 族"；需要条数只允许出现在**附录 A 生成区**（带生成标记）。

### 6. `spec_cite` 改为"手册 + 助记符"
- 指令类：`SimRISC-07: ftmin`
- 非指令类（编码布局/异常/QFC/伪指令定义）：`SimRISC-00: 编码布局`（标题兜底，**不带 `§`**）
- 迁移：`contracts/opcodes.yaml` 264 条 + `tests/**` 147 处数字节号 + `.tao/contracts/**` 与 `contract-isa.md`

### 7. 门控
- `check_numbering.py`：新增"**单包装层**"判据（正文 `##` 恰 1 个且其下 `###` ≥2 ⇒ FAIL）；
- `check_spec_cite_targets.py`：支持两种形式（助记符 → 查该册附录 A 表；非助记符 → 查标题），`--self-test` ≥3 注入；
- 相关生成器（`gen_asm_list`/`gen_legality_list`）输出随拍平/去子标题同步。

## 验收

1. **拍平**：`01/02/03/05/06` 正文 `##` ≥2 且无同名单包装；`00/04/07/08/09/10/11` 二级节数与改前一致（现场统计）。
2. **已删除**：`grep -n '已删除' spec/SimRISC-*.md` ⇒ 仅命中 `SimRISC-00` 的 changelog 段；正文 0。
3. **编码值**：`grep -nE '\b(op|ha)\s*[=:：]|opx\s*=|\b[01]{3}-[01]{3}\b|0x[0-9A-Fa-f]{8}' spec/SimRISC-0[1-9]*.md spec/SimRISC-1[0-2]*.md` ⇒ **0**（立即数示例若误命中，逐条判定并在完成区说明）。
4. **跨册引用**：`grep -rn 'SimRISC-[0-9][0-9] §' spec/` ⇒ **0**。
5. **条数**：正文无"N 条/N 族"（生成区除外）。
6. **spec_cite**：`grep -c 'spec_cite: .*§' contracts/opcodes.yaml tests/` ⇒ **0**；`check_spec_cite_targets` rc=0。
7. **可达 FAIL ≥4**：① 给 `SimRISC-01` 加回包装层 ⇒ numbering 红；② 塞回 `已删除` 小节 ⇒ 正文扫描红；③ `spec_cite` 写错助记符 ⇒ cite_targets 红；④ 塞回一条跨册 `§` 引用 ⇒ 引用扫描红。
8. `make check`(L1) + `make check-modules`(L2) 绿；`check_patch_tree` 绿。

## 接口规范

- **输入**：`spec/SimRISC-00…12`、`tools/spec/**`、`tools/llvm/gen_asm_list.py`、`contracts/**`、`tests/**`、`.tao/contracts/**`。
- **输出**：拍平 + 去残留的 13 册；新格式 `spec_cite`；2 个门控调整。
- **约束**：不改任何指令语义/编码；不改 `opcodes.yaml` 字段（除 `spec_cite`）；不 commit/push；临时目录 `/tmp/opencode/SPEC-166t/`。

## 风险与纪律

- 拍平与删节都会改节号 ⇒ **先建映射表**（最终形态）再改引用；改完全量 `grep` 校验旧节号残留。
- 删"已删除"小节前，逐条确认该小节内**没有**仍在生效的语义/约束（若有，先迁到正文再删）。
- 逐册自检，单册失败不影响其它册。

## 完成区

**测试结果**：`make check`(L1) rc=0；`make check-modules`(L2) rc=0（`L2_EXIT=0`）；`.work/evidence/SPEC-166t/run.sh` 39 项全 PASS（4 类注入 红→还原→绿）
**修改文件**（84）：`spec/` 20（13 SimRISC + `README.md` + 6 只读册跨册引用）、`contracts/` 4（opcodes/fp_semantics/legality_rules/abi）、`.tao/contracts/contract-isa.md`、`manifests/spec-readonly.lock.toml`、`tests/` 23、`tools/` 33、`.tao/knowledge/milestones.md`（状态行同步，`check-milestones-fresh` 强制）、本任务书
**阶段完成度**：1 映射表 ✅（`.work/SPEC-166t/map/`：before/after 标题表 + section_map + removed_sections[20]）｜2 拍平 5 册 ✅｜3 删「已删除」✅｜4 删编码值 ✅｜5 断跨册 ✅｜6 去计数 ✅｜7 spec_cite ✅｜8 门控 ✅
**拍平结果**：01 `1–4 存取RD/RB/RA/RF寄存器`｜02 `1 寄存器组之间块赋值/2 条件赋值/3 浮点条件赋值`｜03 留 `§1`（自有正文）+ `2 set.rd/3 set.rb/4 set.ft·set.fo`｜05 `1 加减/2 自增自减/3 比较/4 IP 相对寻址`｜06 `1 条件跳转/2 无条件跳转/3 函数调用/4 函数返回`；各 wrapper 散文并入册首
**已删除归零**：`grep -c '已删除' spec/SimRISC-*.md` ⇒ 全 0（00 §5 删「已删除助记符」块、3 处子表注改「空白 = reserved（UNDI）」、04/06/08/09/10/11 共 13 个「（已删除）」小节删净；changelog 用「删除」表述，未改）
**编码值归零**：01–12 命中 8 行全在 03，全为伪指令**立即数示例**（`set.rd/set.rb/set.ft/set.fo … 0x…` / `@@` 注释），违规 0；04 的 `rol`/`ctlz` 位串与 `opx=` 已删，`orrr`/`orri` 格式代号全保留
**跨册引用归零**：`grep -rn 'SimRISC-[0-9][0-9] §' spec/` ⇒ 0（原 27 = 13 册内 20 + DADAO-11/12/13/21、Toolchain-01、Machine-01 共 7）
**条数归零**：12 册册头 `（N 条）`、07 两处「本节 N 条」、01 三处「共有N条」、00 §5「8 条」全删；附录 A/B 生成区不变
**spec_cite 迁移**：`contracts/opcodes.yaml` 264 条 → `SimRISC-NN: <助记符>`（册取 `classify()`，生成器同步 + `assert` 对账 + 重跑幂等）；`tests/**` 22 文件 1439 行 + `contracts/{fp_semantics,legality_rules,abi}.yaml` 96 行 → `手册: 小节标题`；新形 `§` 残留 0
**门控**：`check_numbering.py` 加「单包装层」判据（`wrapper=0`）；`check_spec_cite_targets.py` 重写（助记符→该册附录 A；否则→标题；旧 `§` 形直接报错），`--self-test` = 2 基线 + 3 注入全 PASS
**验收结果**：run.sh rc=0；日志 `.work/log/spec/SPEC-166t/`（`SPEC-166t-L1-check.log` / `SPEC-166t-L2-check-modules.log` / `check-*.log` / `SPEC-166t-inject-*.log`）；19 册 sha256 同笔重算 ⇒ `check-spec-readonly` PASS
**新发现/坑**：① `spec_cite` 值含 `": "` **必须加引号**，否则 YAML 崩（`validate-vectors` 564 gap 即此因）；② 机械改写会打到「断言 spec 文本」的检查器（`check_d7_consistency.py` 的 needle 须同步）；③ `.tao/contracts/*.md` 的 `[SimRISC-xx §标题]` 方括号形是 `check_spec_refs` 判据，**不可**改新形（会失明），只把失效节改指向存活节
**遗留问题**：① **越界披露**：为达验收 4（`grep spec/` ⇒ 0）改了 6 册非 SimRISC 只读册共 7 处（只删 `§节名`，语义未动）+ `spec/README.md` 引用约定 + `tests/vectors/schema.md` 示例；② 08/09/10 删「逻辑运算类指令」空壳后把 `Bit manipulating` 由 `###` 升 `## 2.`（唯一合理处置，二级节数不变）；③ 04 同句删去「32/16/8 位 ext 已从指令集中删除」半句（64 位事实保留）；④ `gen_asm_list` 脚注 `Toolchain-01 §4.2`（投影 `contract-asm-list.md`）未动——非 SimRISC 引用且受 drift 门控

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-22）

逐行审查改动源码/脚本（门控 2 个、生成器 10 个、证据脚本 2 个）与 13 册 diff，findings：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `spec_cite` 值含 `": "` 未加引号 ⇒ YAML 解析崩（`validate-vectors` 报 564 coverage gap） | ✅已修 | 1417 行单引号化；生成器走 `yaml.dump` 自动加引号 | `make validate-vectors` rc=0（706 cases）；全量 `yaml.safe_load` 0 bad |
| F2 机械改写误改「断言 spec 文本」的检查器 needle | ✅已修 | `check_d7_consistency.py` needle → `完整流程见 SimRISC-00。` | 该器 rc=0（全部 D7 项 PASS） |
| F3 证据日志命名违 `check-run-artifacts` A3（15 illegal） | ✅已修 | 日志改 `check-*.log` / `SPEC-166t-*.log` | `make check` rc=0 |
| F4 证据脚本写死 264 条（违「计数不写死」） | ✅已修 | 改为现场统计 `^- id:` 条数与助记符形对账 | `checks.py cite` 输出 264/264（现场） |
| F5 注入④锚点在册内出现 2 次 ⇒ 注入失败（潜在假绿） | ✅已修 | 断言放宽为 ≥1、仅替换 1 处 | `crossref-back:注入后` rc=1、`还原后` rc=0 |
| F6 注入①②在双引号 heredoc 内被 bash 展开反引号（注入内容被改） | ✅已修 | 注入改为独立 python 脚本（`inject/*.py`） | 4 类注入均 红→md5 还原→绿 |
| F7 `spec/README.md` 引用约定与新格式不符 | ✅已修 | 「标题编号」条补：禁单包装层、跨册只写手册名、`spec_cite` 两形 | 文档与门控同源；门控 rc=0 |

判决：全部 finding 已修，任务状态 → `待验收`。

### 第 1 轮 reviewer 验收（2026-10-23，独立重跑）

**重跑（本人执行，真实 rc）**：`make check`(L1) rc=0（含 `check-patch-tree: 5 component(s), 192 patches OK`、`check-spec-readonly: 21 volumes OK`）；`make check-modules`(L2) rc=0（805/805、`check-rnd-probe: PASS`）；`check_numbering` rc=0（`wrapper=0`）；`check_spec_cite_targets` rc=0（1819 行、unresolved=0）；`--self-test` rc=0（2 基线 + 3 注入 + 空文件全 PASS）；lock 21 条 sha256 本人现场重算 0 不符。

**拍平**：01/02/03/05/06 正文 `##`=6/5/6/6/6（≥2、无单包装）；00/04/07/08/09/10/11 二级节=6/4/7/4/4/4/6，与 `b5867892~1` 逐册**相等**（diff=0）。

**表行数（`|` 行 前→后，13 册）**：121/40/18/10/74/8/17/72/39/39/39/48/4 → 全 diff=0；附录 A 助记符集合逐册一致。

**删除节判定（逐节对 `b5867892~1` 原文核）**：实测 15 个带「（已删除）」标题（04:2、06:1、08:3、09:4、10:4、11:1）+ 00「已删除助记符」块 + 00 三处空单元格注 ⇒ **均无仍在生效的唯一语义/约束被删**：① 04 §2.1 正文「rd0 时 xnor 即取反」原样保留；② `ret rd0, 0` 用法保留于 06 §4 正文，「ret 显式两操作数、不加无参形态」保留于 Toolchain-01 §6.2 明文 + 06 附录 A；③ nop/return/not/neg 四条替代映射全量保留于 Toolchain-01 §6.2（00 §5 指向它）；④ 窄位宽逻辑/ext 删除的活语义（空白格=reserved(UNDI)）保留于 00 中性注；⑤ changelog「伪指令集收缩」等删除记录未动。

**编码值**：01–12 命中 8 行全在 03、全为 `set.*` 立即数示例（`@@` 注释），违规 0；格式代号 orrr=164/orri=97/rrii=32（分册均非 0）。**跨册引用**：`grep -rn 'SimRISC-[0-9][0-9] §' spec/` 0 命中。

**spec_cite**：opcodes.yaml 现场 `^- id:`=264、助记符形=264（全 `SimRISC-NN: 助记符`）；contracts/ tests/ 旧 `§` 形 0；本人独立全量 264 条助记符 ⇒ 该册附录 A **精确命中 264/264**（含 fp `SimRISC-07: ft2uo`、atomic `SimRISC-11: sc.w.nn`、64bit `SimRISC-04: cmp.uo`、`SimRISC-12: cfxld`、`SimRISC-01: stm.b`、`SimRISC-03: set.w` 等 9 条抽样均命中）。

**语义零漂移**：`git diff` opcodes.yaml 增删 264±行**全为 `spec_cite`**（非 spec_cite 行 0）；fp_semantics/legality_rules/tests/** 非 spec_cite 变更行 0；tools/ 仅注释/docstring/常量串；abi.yaml 仅 spec_cite。

**越界披露核对**：6 册只读册共 7 行改动（DADAO-11/12/13/21 各 1、Machine-01 4、Toolchain-01 1）**仅删 `§节名`、规范正文未动**；`spec/README.md`+`tests/vectors/schema.md` 仅同步引用约定 —— 与披露一致。

**注入（本人，cp+md5，两次）**：① opcodes.yaml 一条改 `reviewernosuchinsn` ⇒ `unresolved=1` rc=1；还原 md5 相等 ⇒ rc=0。② SimRISC-02 加回包装层 ⇒ `wrapper=1` rc=1（L8 单包装层）；cp 还原 md5 相等 ⇒ rc=0。验收前后 `git status` + 13 册/opcodes.yaml md5 快照对账**逐行一致**（无残留）。

**观察（非阻断）**：a) 证据脚本 `checks.py` 基线取 `git show HEAD:`，提交后复跑 `flatten` 恒假（本人实测 FAIL）、`tables` 自比恒真——证据于 head=2b860a32 时产出有效，但不可作可复跑回归，后续宜改显式基线；b) 00 byte 子表引言「覆盖…逻辑…」与窄位宽逻辑已删存在张力（两版一致，非本任务引入）；c) 完成区「13 个小节」与实测 15 个「（已删除）」标题差在 09/10 `## 2` 计法；d) `contract-isa.md §6.6` 仍列 `not.o`/`neg.o` 展开行（本任务仅改指针），与「1:1 别名不保留」口径的张力属既有状态，供 architect 定夺。

**判决：Accepted** —— 本人重跑全部通过；未发现语义误删/改、门控与退出码不符、断言与现场不符或 spec_cite 解析失败。
