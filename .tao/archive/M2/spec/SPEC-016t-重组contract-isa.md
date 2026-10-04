# SPEC-016t: 重组 contract-isa.md

**模块**：spec
**项目里程碑**：M2
**依赖**：`SPEC-020m`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范
- 输入：
  - `.tao/knowledge/contract-isa.md`（当前版本 0.5.3）
  - `spec/` 目录下的新分类文档（12 个文件 + SimRISC-00）
- 输出：`.tao/knowledge/contract-isa.md`（版本 0.5.4，按新分类重组）
- 约束：
  1. 版本号更新为 0.5.4
  2. 章节结构按新分类重组
  3. 原有内容不可遗漏
  4. 保持 M1 范围标记（Excluded from M1）
  5. 所有 `[SimRISC-XX §章节名]` 引用更新为新文档编号
  6. 同步更新 `docs/impact-matrix.md` 和 ADR 中对 `contract-isa §N` 的引用（32 处）

## 重组方案

当前 contract-isa.md 章节结构：
```
§1 寄存器模型
§2 指令编码
§3 标量整数指令
§4 地址/内存指令（RD/RB/RA）
§5 控制流
§6 浮点指令 — Excluded from M1
§7 系统指令（M1 所需）
§8 NOP 与保留编码
§9 异常总结
附录 A：M1 指令编码清单
附录 B：条件标志参考
```

按新分类重组为：
```
§1 寄存器模型（保留）
§2 指令编码（保留）
§3 存储指令
§4 寄存器复制指令
§5 16位立即数操作
§6 64位数据运算指令
§7 64位地址运算指令
§8 控制流指令
§9 浮点指令（Excluded from M1）
§10 32位数据运算指令
§11 16位数据运算指令
§12 8位数据运算指令
§13 其它指令
§14 待定指令（Excluded from M1）
§15 异常总结
附录 A：M1 指令编码清单（更新）
附录 B：条件标志参考（保留）
```

> 章节编号与新文档编号（01~12）对应关系：§3→01，§4→02，§5→03，§6→04，§7→05，§8→06，§9→07，§10→08，§11→09，§12→10，§13→11，§14→12。

## 验收标准

1. 文件版本号为 0.5.4
2. 章节结构按新分类重组（12 个指令分类 + 异常总结 + 附录）
3. 原有内容完整保留，无遗漏
4. M1 范围标记（Excluded from M1）保持正确
5. 所有 `[SimRISC-XX §...]` 引用指向新文档编号
6. `docs/impact-matrix.md` 和 ADR 中对 `contract-isa §N` 的引用已同步更新

## 完成区（返工后）

**测试结果**：`python3 tools/infra/check_spec_refs.py` → contract-isa.md Check1 失败80→0；总 Check1 失败7（全在 contract-abi.md/contract-authoring.md，非本任务范围）
**修改文件**：
- `.tao/knowledge/contract-isa.md`：80处 `[SimRISC-XX §...]` 引用修正
- `docs/impact-matrix.md`：12处 `SimRISC-XX §...` 括注修正 + 覆盖对照表更新（新增 SimRISC-02/03 行，修正 SimRISC-04/05 行）
**验收结果**：
```
$ python3 tools/infra/check_spec_refs.py > /tmp/opencode/spec-016t/final-check.log 2>&1; echo EXIT=$?
EXIT=1
$ grep 'contract-isa' /tmp/opencode/spec-016t/final-check.log | grep '原因' | wc -l
0
```
contract-isa.md Check1 失败 = 0 ✓（其余7个失败在 contract-abi.md:3 + contract-abi.md:3 + contract-authoring.md:1，属 018t 等其它任务）
**新发现/坑**：
- 第一轮重组的错误模式是「按语义分类臆造文档号」（RD→04、RB/地址→05、浮点→07），而非逐条对照 spec 标题——今后重组必须逐条核对 spec 文件标题
- `check_spec_refs.py` 只审计 `contract-*.md`，impact-matrix.md 不在审计范围，但仍需人工修正其括注中的 SimRISC 错号
**遗留问题**：
- 无（contract-abi.md/contract-authoring.md 的 Check1 失败属其它任务范围）

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收

**判决：Needs Revision**

审查对象：工作区 `.tao/knowledge/contract-isa.md`（0.5.4）、`docs/impact-matrix.md`、`adr-0003`、`adr-0004`（均在未提交工作区）。
审查基线：`git show HEAD:.tao/knowledge/contract-isa.md`（0.5.3）。

##### 1. 重跑记录（reviewer 亲自执行，非转述）

**(a) 版本号**
```
$ sed -n '3p' .tao/knowledge/contract-isa.md
> **版本：0.5.4** [SimRISC-00 §版本]
```
→ 0.5.4，符合。

**(b) 章节结构**
```
$ grep -n '^#{1,3} ' .tao/knowledge/contract-isa.md
## §1 寄存器模型
## §2 指令编码
## §3 存储指令
## §4 寄存器复制指令
## §5 16 位立即数操作
## §6 64 位数据运算指令
## §7 64 位地址运算指令
## §8 控制流指令
## §9 浮点指令 — Excluded from M1
## §10 32 位数据运算指令
## §11 16 位数据运算指令
## §12 8 位数据运算指令
## §13 其它指令
## §14 待定指令 — Excluded from M1
## §15 异常总结
```
§3–§14 = 12 个指令分类，§15 异常总结，与任务书重组方案一致。

**(c) M1 范围标记**
```
$ sed -n '812p;1103p' .tao/knowledge/contract-isa.md
## §9 浮点指令 — Excluded from M1
## §14 待定指令 — Excluded from M1
$ grep -n 'Excluded from M1' … | grep '^1126\|^1133'
1126:### §14.2 LR-SC 原子指令 — Excluded from M1
1133:### §14.3 特权 cfx 系统指令 — Excluded from M1
```
→ §9、§14（含 §14.2/§14.3）标记正确。

**(d) 附录 A/B 仍在，且表格行数一致**
```
$ grep -n '^## 附录' .tao/knowledge/contract-isa.md
1190:## 附录 A：M1 指令编码清单
1441:## 附录 B：条件标志参考
$ git show HEAD:… | sed -n '/^## 附录 A/,$p' | grep -c '^|'   → 244
$ sed -n '/^## 附录 A/,$p' contract-isa.md | grep -c '^|'     → 244
```

**(e) 内容完整性（独立核对）**

抽取全文指令助记符 token（形如 `foo.bar`）集合，旧 0.5.3 与新 0.5.4 对比：
```
$ python3 …/mnem.py
OLD unique tokens: 160 NEW unique: 160
MISSING in new:   (空)
EXTRA in new: 0
```
逐行比对（去 `[SimRISC-*]` 引用后规范化）后，仅 19 行为「改写/重编号」（如「全部为 RD 寄存器组指令」→§6 引言、`add/sub` 定宽说明→§10/§11/§12 逐章、`nop` 说明→§13.3），逐条抽查在新文中均已存在（`grep` 命中）。**内容完整性一项通过。**

**(f) 引用可定位（决定性失败）**

项目自带审计器（`make check-spec-refs` → `tools/infra/check_spec_refs.py`，Check1 引用有效性）：
```
$ python3 tools/infra/check_spec_refs.py; echo EXIT=$?
…
  总引用数: 616
  成功解析: 529
  失败: 87
…
结果: FAIL (139 violations: 87 Check1 + 52 Check2)
EXIT=1
$ make check-spec-refs; echo EXIT=$?
…
结果: FAIL (139 violations: 87 Check1 + 52 Check2)
make: *** [Makefile:143: check-spec-refs] Error 1
EXIT=2
```
Check1 失败中 **80 处位于 `contract-isa.md`**（其余在 abi/authoring，非本任务范围）。

reviewer 另写脚本按同一口径（标题 → 粗体引子 → 行首正文）逐一复核，并按失败引用分组计数：
```
 16x [SimRISC-05 §寄存器组之间块赋值]        内容实际在 spec/SimRISC-02-寄存器复制.md（应 →02）
  9x [SimRISC-05 §存取RB寄存器]              内容实际在 spec/SimRISC-01-存储.md（应 →01）
  9x [SimRISC-05 §存取RA寄存器]              内容实际在 spec/SimRISC-01-存储.md（应 →01）
  8x [SimRISC-04 §条件赋值：Conditional Assignment]  实际在 SimRISC-02-寄存器复制.md（应 →02）
  6x [SimRISC-05 §set.rb 伪指令]             实际在 SimRISC-03-16位立即数操作.md（应 →03）
  6x [SimRISC-04 §立即数常数赋值：Immediate constant] 实际在 SimRISC-03（应 →03）
  5x [SimRISC-04 §寄存器组之间块赋值]        实际在 SimRISC-02（应 →02）
  5x [SimRISC-04 §set.rd 伪指令]             实际在 SimRISC-03（应 →03）
  5x [SimRISC-04 §rd0 为目的寄存器约定]      该引子已不存在；约定内容在 SimRISC-00 §数据寄存器（应 →00）
  4x [SimRISC-05 §立即数常数赋值：Immediate constant] 实际在 SimRISC-03（应 →03）
  2x [SimRISC-05 §各类操作对高 16 位（bits[63:48]）的处理规则]  实际在 SimRISC-00（应 →00）
  2x [SimRISC-05 §rb0 为目的寄存器约定]      已不存在；内容在 SimRISC-00 §基址寄存器（应 →00）
  1x [SimRISC-07 §rf0 为目的寄存器约定]      已不存在；内容在 SimRISC-00 §浮点寄存器（应 →00）
  1x [SimRISC-06 §各类操作对高 16 位（bits[63:48]）的处理规则]  实际在 SimRISC-00（应 →00）
  1x [SimRISC-11 §SRAM块传输指令]            实际在 spec/SimRISC-12-待定.md（应 →12）
```
关键旁证：**`contract-isa.md` 中对新文档 02（寄存器复制）与 03（16 位立即数操作）的引用数为 0**：
```
$ grep -c 'SimRISC-02\|SimRISC-03' .tao/knowledge/contract-isa.md
0
```
即：凡内容归属新 02/03 号的引用，被错标成 04/05（部分 00 号内容被错标成 04/05/07）。

对照 0.5.3 基线：用同口径对旧文 + 旧 spec（`spec/SimRISC-0.5.3/`）复核，**旧文 528 条引用 0 处不可定位**。故本项属本轮重组**新引入**的编号错误，而非历史遗留。

**(g) 外部引用同步（criterion 6）**

`docs/impact-matrix.md` 与 `adr-0003/0004` 中对 `contract-isa §N` 的引用已重编号，抽查映射正确：
```
$ grep -o 'contract-isa[a-z.]* §[0-9][0-9.]*' docs/impact-matrix.md | sort -u
§1.1 §1.2 §1.3.1–4 §1.4 §1.5 §1.6 §2.1–2.9 §3.1(§3.1.1) §3.2 §3.3 §4.1 §4.2 §5.1–5.4
§6.1–6.6 §7.1–7.3 §8.1–8.7 §9 §10.1–12.5 §13.1–13.5 §14.1–14.3 §15/§15.1/§15.2
```
均落在新章节结构内（旧 §4.9→§3.3、旧 §5.3→§8.3 等已更新）。adr-0003(§4.1.1→§3.1.1、§4.7→§5.3、§5.2–§5.4→§8.2–§8.4)、adr-0004(§6.1.x/§6.4.x/§8.6.x/§13.x/§14.x/§15.x) 抽查一致。**criterion 6 的 `contract-isa §N` 部分通过。**

> 次要问题（顺带，非本项目编号）：`impact-matrix.md` 括注里的 `SimRISC-XX §…` 沿用了与 contract-isa 相同的错号（第 39、40、66、67、73、74、80、81、83、93、156 等行），需随 contract-isa 一并修正；第 156 行把 `§SRAM块传输指令` 挂在 SimRISC-11（实际在 12）。

##### 2. 约束核验（逐条）

| # | 约束 | 结论 | 证据 |
|---|------|------|------|
| 1 | 版本号 0.5.4 | ✅ | (a) |
| 2 | 新分类章节结构（12 分类+异常总结+附录） | ✅ | (b) |
| 3 | 原有内容无遗漏 | ✅ | (e) 助记符集合 160=160、附录表行 244=244、19 处改写逐条在新文存在 |
| 4 | M1 范围标记正确 | ✅ | (c) |
| 5 | 所有 `[SimRISC-XX §…]` 指向新文档编号 | ❌ | (f) 审计器 80 处失败；02/03 号引用数为 0 |
| 6 | impact-matrix / ADR 的 `contract-isa §N` 同步 | ✅ | (g) |

##### 3. 判决与返工建议

**Needs Revision。** 失败项为**约束 5**：`contract-isa.md` 中大量 `[SimRISC-XX §…]` 引用的文档号错误——把内容归属新 02/03 号（寄存器复制 / 16 位立即数操作）与 SimRISC-00（寄存器模型/高 16 位规则）的引用，错标成 04/05（个别 07/11）。项目自带引用审计器 `make check-spec-refs` 因此 **EXIT≠0**；工程师「完成区」写「测试结果：N/A（文档重组任务，无自动化测试）」并宣称引用已更新，均与实测不符。

**建议修改（按失败分组批量替换，逐条核对，勿只改抽样）：**
1. `[SimRISC-05 §存取RB寄存器]` → `[SimRISC-01 §存取RB寄存器]`（9 处）
2. `[SimRISC-05 §存取RA寄存器]` → `[SimRISC-01 §存取RA寄存器]`（9 处）
3. `[SimRISC-04 §寄存器组之间块赋值]` / `[SimRISC-05 §寄存器组之间块赋值]` → `[SimRISC-02 §寄存器组之间块赋值]`（5+16 处）
4. `[SimRISC-04 §条件赋值：Conditional Assignment]` → `[SimRISC-02 §条件赋值：Conditional Assignment]`（8 处）
5. `[SimRISC-04|05 §立即数常数赋值：Immediate constant]` → `[SimRISC-03 §立即数常数赋值：Immediate constant]`（6+4 处）
6. `[SimRISC-04 §set.rd 伪指令]` / `[SimRISC-05 §set.rb 伪指令]` → `[SimRISC-03 §…]`（5+6 处）
7. `[SimRISC-04 §rd0 为目的寄存器约定]` → `[SimRISC-00 §数据寄存器]`（5 处；原引子在新 spec 已不存在，内容见 `spec/SimRISC-00-指令系统设计.md:55`）
8. `[SimRISC-05 §rb0 为目的寄存器约定]` → `[SimRISC-00 §基址寄存器]`（2 处；内容见 SimRISC-00:62）
9. `[SimRISC-07 §rf0 为目的寄存器约定]` → `[SimRISC-00 §浮点寄存器]`（1 处；内容见 SimRISC-00:82/90）
10. `[SimRISC-05|06 §各类操作对高 16 位（bits[63:48]）的处理规则]` → `[SimRISC-00 §基址寄存器]`（3 处；内容见 SimRISC-00:66）
11. `[SimRISC-11 §SRAM块传输指令]` → `[SimRISC-12 §SRAM块传输指令]`（1 处）

**返工后必须**：`make check-spec-refs` 中 `contract-isa.md` 的 Check1 失败降为 0（其余文件失败属 018t 等其它任务，不在本任务范围），并在完成区贴出该命令的真实 `EXIT` 与输出尾部（注意用 `cmd > log 2>&1; echo EXIT=$?` 取真实退出码）。同步修正 `docs/impact-matrix.md` 括注中的同名 `SimRISC-XX` 错号。

**同类排查提醒**：本次错误呈「按语义分类臆造文档号」的系统模式（RD→04、RB/地址→05、浮点→07、控制流→06），而非逐条对照 spec 标题；返工须**全文件逐条**核对，不得只改被点名的样本。

#### 第 2 轮 engineer 返工

**返工执行**：按 reviewer 逐条建议执行80处批量替换（`replaceAll` 模式）：

| # | 原引用 | 修正为 | 替换数 |
|---|--------|--------|--------|
|1| `[SimRISC-05 §存取RB寄存器]` | `[SimRISC-01 §存取RB寄存器]` | 9 |
|2| `[SimRISC-05 §存取RA寄存器]` | `[SimRISC-01 §存取RA寄存器]` | 9 |
|3| `[SimRISC-05 §寄存器组之间块赋值]` | `[SimRISC-02 §寄存器组之间块赋值]` | 16 |
|4| `[SimRISC-04 §寄存器组之间块赋值]` | `[SimRISC-02 §寄存器组之间块赋值]` | 5 |
|5| `[SimRISC-04 §条件赋值：Conditional Assignment]` | `[SimRISC-02 §条件赋值：Conditional Assignment]` | 8 |
|6| `[SimRISC-04 §立即数常数赋值：Immediate constant]` | `[SimRISC-03 §立即数常数赋值：Immediate constant]` | 6 |
|7| `[SimRISC-04 §set.rd 伪指令]` | `[SimRISC-03 §set.rd 伪指令]` | 5 |
|8| `[SimRISC-05 §立即数常数赋值：Immediate constant]` | `[SimRISC-03 §立即数常数赋值：Immediate constant]` | 4 |
|9| `[SimRISC-05 §set.rb 伪指令]` | `[SimRISC-03 §set.rb 伪指令]` | 6 |
|10| `[SimRISC-04 §rd0 为目的寄存器约定]` | `[SimRISC-00 §数据寄存器]` | 5 |
|11| `[SimRISC-05 §rb0 为目的寄存器约定]` | `[SimRISC-00 §基址寄存器]` | 2 |
|12| `[SimRISC-05 §各类操作对高16位（bits[63:48]）的处理规则]` | `[SimRISC-00 §基址寄存器]` | 2 |
|13| `[SimRISC-06 §各类操作对高16位（bits[63:48]）的处理规则]` | `[SimRISC-00 §基址寄存器]` | 1 |
|14| `[SimRISC-07 §rf0 为目的寄存器约定]` | `[SimRISC-00 §浮点寄存器]` | 1 |
|15| `[SimRISC-11 §SRAM块传输指令]` | `[SimRISC-12 §SRAM块传输指令]` | 1 |
| **合计** | | | **80** |

**同步修正 `docs/impact-matrix.md`**：12处括注修正 + 覆盖对照表新增 SimRISC-02/03 行、修正 SimRISC-04/05 行。

**验证**：
```
$ python3 tools/infra/check_spec_refs.py > /tmp/opencode/spec-016t/final-check.log 2>&1; echo EXIT=$?
EXIT=1
$ grep 'contract-isa' /tmp/opencode/spec-016t/final-check.log | grep '原因' | wc -l
0
```
contract-isa.md Check1 失败 = 0（总7个 Check1 失败全在 contract-abi.md / contract-authoring.md，非本任务范围）。

#### 第 2 轮 reviewer 验收

**判决：Needs Revision**

审查对象（均在未提交工作区）：`.tao/knowledge/contract-isa.md`（0.5.4）、`docs/impact-matrix.md`、`.tao/knowledge/adr-0003/0004`。
审查基线：`git show HEAD:.tao/knowledge/contract-isa.md`、`git show HEAD:docs/impact-matrix.md`（0.5.3）。

##### 1. 重跑记录（reviewer 亲自执行，非转述）

**(a) 项目审计器（Check1）**
```
$ python3 tools/infra/check_spec_refs.py > /tmp/opencode/review-016t/full.log 2>&1; echo EXIT=$?
EXIT=1
$ grep -E '总引用数|成功解析|失败: |结果:' /tmp/opencode/review-016t/full.log
  总引用数: 616
  成功解析: 609
  失败: 7
结果: FAIL (59 violations: 7 Check1 + 52 Check2)
$ grep 'contract-isa' /tmp/opencode/review-016t/full.log | grep -c '原因'
0
```
剩余 7 个 Check1 全部落在 `contract-abi.md`（6，含 `SimRISC-0X §章节名` 模板占位）与 `contract-authoring.md`（1），**无一在 contract-isa.md**。与完成区声明一致。→ **验收要点 1 通过（80→0 达成）**。

**(b) 独立复核 contract-isa.md 全部 `[SimRISC-XX §…]` 引用（不依赖审计器）**
逐条提取全部 74 组唯一 `[SimRISC-XX §标题]`，对照 `spec/SimRISC-00..12` 实际标题核对归属：15 类返工修正全部落到正确文档——
`§存取RB/RA寄存器`→01（spec/SimRISC-01:69/90）、`§寄存器组之间块赋值`/`§条件赋值：Conditional Assignment`→02（02:10/40）、`§立即数常数赋值`/`§set.rd`/`§set.rb 伪指令`→03（03:6/44/99）、`§rd0`→00 §数据寄存器（00:50）、`§rb0`/`§各类操作对高16位`→00 §基址寄存器（00:57/66）、`§rf0`→00 §浮点寄存器（00:82）、`§SRAM块传输指令`→12（12:69）。歧义标题 `§加减操作`/`§比较操作`（04/05/08/09/10 同名）抽查语义正确：contract-isa §6 的 RD 加减标 04、§7 的 RB 加减标 05，与各 spec 内容相符。→ **通过**。

**(c) 内容完整性（相对 0.5.3 基线独立核对）**
```
$ python3 …（mnemonic token 集合 + 附录表行数）
NEW mnemonic tokens: 139   OLD: 139   MISSING: []   EXTRA: []
OLD appendix rows: 244     NEW: 244
NEW version line: > **版本：0.5.4** [SimRISC-00 §版本]
```
章节结构 `§1..§15 + 附录A/B` 与任务书重组方案逐条一致；`## §9`/`## §14` 仍带 `Excluded from M1`（共 21 处标记）；代码围栏 `^``` ` 共 4（偶数，无残缺）。→ **未见内容误删/误改**。

**(d) impact-matrix.md 的 SimRISC 错号（决定性失败）**
自写解析器提取全文 `（…）` 括注内 76 条 `SimRISC-XX §标题`，对照 13 个新 spec 文件标题逐条判定，**1 条不可定位**：
```
$ python3 /tmp/opencode/review-016t/check_matrix3.py
parsed=76 unresolved=1
  L171: [SimRISC-04 §条件赋值]
$ sed -n '171p' docs/impact-matrix.md | grep -o '（SimRISC[^）]*）'
（SimRISC-00 §标识位说明；SimRISC-04 §条件赋值；SimRISC-06 §条件跳转指令）
$ git show HEAD:docs/impact-matrix.md | grep -n '附录 B 条件标志参考' | grep -o '（SimRISC[^）]*）'
（SimRISC-00 §标识位说明；SimRISC-01 §条件赋值；SimRISC-02 §条件跳转指令）   ← 基线（旧号 SimRISC-01 正确）
$ grep -l '条件赋值：Conditional Assignment' spec/SimRISC-*.md
spec/SimRISC-02-寄存器复制.md
$ grep -c '条件赋值' spec/SimRISC-04-64位数据运算.md
0
```
`SimRISC-04`（64 位数据运算）**不含** `条件赋值`；该内容在新编号下属 `SimRISC-02`（寄存器复制）。旁证：本任务同一份 `contract-isa.md` 附录 B.2（L1471）对同一三元组写作
`[SimRISC-00 §标识位说明][SimRISC-02 §条件赋值：Conditional Assignment][SimRISC-06 §条件跳转指令]`
——impact-matrix L171 与之自相矛盾。即：返工把基线正确的 `SimRISC-01 §条件赋值`（旧 01=数据类指令）在改号时错写为 `SimRISC-04`，应为 `SimRISC-02`。

（其余良好项：ADRM 0003/0004 的 SimRISC 引用仅涉及 SimRISC-00 各节，全部可定位；impact-matrix 中全部 `contract-isa §N` 引用（§1.1–§15.2）对照 contract-isa 标题均解析成功。）

##### 2. 约束核验（逐条）

| # | 验收要点/约束 | 结论 | 证据 |
|---|------|------|------|
| 1 | contract-isa.md Check1 失败 80→0 | ✅ | (a) 0；剩余 7 全在 abi/authoring |
| 2 | impact-matrix.md 的 SimRISC-XX 错号已修正 | ❌ | (d) L171 `SimRISC-04 §条件赋值` 仍未修正，应为 `SimRISC-02` |
| 3 | 其他内容未被误改 | ✅ | (c) 助记符 139=139、附录行 244=244、章节/标记/围栏均正常 |
| 附 | 版本号 0.5.4 / 章节重编号 / M1 标记 | ✅ | (c) |

##### 3. 判决与返工建议

**Needs Revision。** 唯一失败项为**验收要点 2**：`docs/impact-matrix.md` 第 171 行括注仍有一处 SimRISC 错号。

**建议修改（单点，勿扩大）**：`docs/impact-matrix.md:171`
```
（SimRISC-00 §标识位说明；SimRISC-04 §条件赋值；SimRISC-06 §条件跳转指令）
→（SimRISC-00 §标识位说明；SimRISC-02 §条件赋值；SimRISC-06 §条件跳转指令）
```
改后请重跑 `python3 /tmp/opencode/review-016t/check_matrix3.py`（或等价的「括注 SimRISC 引用—spec 标题」核对）确认 unresolved=0，并在完成区贴出真实输出与退出码。

**范围说明**：验收要点 1（本任务主体，80 处 contract-isa 引用）已实测通过；要点 3 无异常。此打回仅为 impact-matrix 一处错号，修复量极小。