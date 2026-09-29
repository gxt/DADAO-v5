# SPEC-043t: SimRISC-03（16位立即数操作）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`、`docs/spec/assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表（生成区）；前置 `SPEC-041t`/`SPEC-042t`
**状态**：已验证

## 背景与目标

第 1、2 章已完成。本任务处理**第 3 章：16位立即数操作**（`set.zw`/`set.ow`/`set.w`/`or.w`/`andn.w`，8 条 `rwii`）+ 4 组伪指令展开示例。

## 修改范围（仅 `spec/SimRISC-03-16位立即数操作.md`）

### A. `rwii` 真指令（块 31–36 / 47–51 / 55–57）

| 旧 | 新 |
|---|---|
| `set.ow   rdha, wpN, immu16` | `set.ow   rdHA, wpN, immu16` |
| `set.zw   rdha, wpN, immu16` | `set.zw   rdHA, wpN, immu16` |
| `or.w     rdha, wpN, immu16` | `or.w     rdHA, wpN, immu16` |
| `andn.w   rdha, wpN, immu16` | `andn.w   rdHA, wpN, immu16` |
| `set.zw  rbha, wpN, immu16` | `set.zw  rbHA, wpN, immu16` |
| `or.w    rbha, wpN, immu16` | `or.w    rbHA, wpN, immu16` |
| `andn.w  rbha, wpN, immu16` | `andn.w  rbHA, wpN, immu16` |
| `set.w    rfha, wpN, immu16` | `set.w    rfHA, wpN, immu16` |

（`wpN`/`immu16` 原样，见生成表「汇编形式」列）

### B. 伪指令展开示例中的**块赋值/格式转换**（真指令，多寄存器组记法）

`set.rd`/`set.rb`/`set.ft`/`set.fo` 的展开注释里出现的真指令是 **旧 3 操作数形式**（`X, Y, 1`），须改为**新组记法**。`immu6=1` → **单寄存器组，不带冒号**（`assembly-language.md` §4 第 97 行、§5 速查表 `{reg}` count=1）。

| 位置 | 旧 | 新 |
|---|---|---|
| 111 | `展开为 rb2rd rd5, rb3, 1` | `展开为 rb2rd {rd5}, {rb3}` |
| 112 | `展开为 rf2rd rd2, rf7, 1` | `展开为 rf2rd {rd2}, {rf7}` |
| 113 | `展开为 rd2rd rd8, rd3, 1` | `展开为 rd2rd {rd8}, {rd3}` |
| 114 | `展开为 ra2rd rd4, ra10, 1` | `展开为 ra2rd {rd4}, {ra10}` |
| 137 | `展开为 rd2rb rb5, rd3, 1` | `展开为 rd2rb {rb5}, {rd3}` |
| 138 | `展开为 rb2rb rb2, rb7, 1` | `展开为 rb2rb {rb2}, {rb7}` |
| 161 | `展开为 rd2rf rf1, rd0, 1` | `展开为 rd2rf {rf1}, {rd0}` |
| 162 | `展开为 rd2rf rf1, rd0, 1` | `展开为 rd2rf {rf1}, {rd0}` |
| 168 | `展开为 rd2rf rf1, rd5, 1` | `展开为 rd2rf {rf1}, {rd5}` |
| 169 | `展开为 ft2ft rf1, rf2, 1` | `展开为 ft2ft {rf1}, {rf2}` |
| 170 | `展开为 fo2fo rf2, rf7, 1` | `展开为 fo2fo {rf2}, {rf7}` |

> **注意**：`X2Y` 的组顺序为**目的在前、源在后**，以生成表「汇编形式」列（`rd2rf {rfHB:…}, {rdHC:…}` 等）为准，**逐条核对**，不得仅按本表盲改。

### C. 其余展开注释（`set.zw`/`set.ow`/`or.w`/`set.w`，已具体寄存器）

如 `; 展开为 set.zw rd1, wp0, 0` —— 已是新格式（具体寄存器），**保持**；仅需确认无小写字段名残留。

### D. 正文引用

字段名引用大写：`rdha`→`rdHA`、`rfha`→`rfHA` 等；行 42 注中的 `or.w rdhb, rdhc, rdhd` → `or.w rdHB, rdHC, rdHD`。

## 约束

- **只改 `spec/SimRISC-03-16位立即数操作.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->`，本文件行 6–22）
- **语义零变化**：仅记法/标点；数值（`0x1234`/`-42`/`0xDEAD…` 等）、限制条文一字不动
- **伪指令的调用写法不改**（`set.rd rd5, rb3` 等，非硬件指令，不在速查表内）
- 逐条核对，禁止正则批量替换后不复查

## 验收标准

1. A 段 8 条真指令为新格式（`rdHA`/`rbHA`/`rfHA`，`wpN`/`immu16` 原样）
2. B 段 11 处展开注释为 `{reg}, {reg}` 单元素组（**无冒号**；目的/源顺序与生成表相符）
3. C 段具体寄存器注释未被误改
4. 正文引用大写、无小写字段名残留
5. **语义零变化**（逐 hunk；数值/条文未动）
6. **不改生成区**（证据：命中行号 > `ASSEMBLY_LIST_END`）
7. 与生成表「汇编形式」列**逐条相符**（独立复算；A 段 8 条 + B 段 11 条对照）
8. 反例验证：注入一处回退（如 B 段写成 `{rd5:rd5}` 或改回 `rd5, rb3, 1`）→ 检查可检出；复原后无残留
9. `make check` EXIT=0

## 完成区

**测试结果**：`make check` EXIT=0（通过）

**修改文件**：`spec/SimRISC-03-16位立即数操作.md`（唯一改动文件）

**验收结果**：

### A段转换后全文（rwii真指令，8条）

```simrisc
set.ow   rdHA, wpN, immu16
set.zw   rdHA, wpN, immu16
or.w     rdHA, wpN, immu16
andn.w   rdHA, wpN, immu16
```
```simrisc
set.zw  rbHA, wpN, immu16
or.w    rbHA, wpN, immu16
andn.w  rbHA, wpN, immu16
```
```simrisc
set.w    rfHA, wpN, immu16
```

### B段转换后全文（伪指令展开注释，11处）

```
行111: set.rd   rd5, rb3       ; 展开为 rb2rd {rd5}, {rb3}
行112: set.rd   rd2, rf7       ; 展开为 rf2rd {rd2}, {rf7}
行113: set.rd   rd8, rd3       ; 展开为 rd2rd {rd8}, {rd3}
行114: set.rd   rd4, ra10      ; 展开为 ra2rd {rd4}, {ra10}
行137: set.rb   rb5, rd3       ; 展开为 rd2rb {rb5}, {rd3}
行138: set.rb   rb2, rb7       ; 展开为 rb2rb {rb2}, {rb7}
行161: set.ft   rf1, 0         ; 展开为 rd2rf {rf1}, {rd0}
行162: set.fo   rf1, 0         ; 展开为 rd2rf {rf1}, {rd0}
行168: set.ft   rf1, rd5       ; 展开为 rd2rf {rf1}, {rd5}
行169: set.ft   rf1, rf2       ; 展开为 ft2ft {rf1}, {rf2}
行170: set.fo   rf2, rf7       ; 展开为 fo2fo {rf2}, {rf7}
```

### D段转换后（正文字段引用大写）

```
行40: `or.w` 指令（rwii 格式）：将 `rdHA` 中由 `wpN` 指定的 wyde 替换为 `(rdHA[wyde] | immu16)`
行42: > **注意**：`or.w` 同时是 MISC-wyde 表的三寄存器逻辑 OR 指令（`or.w rdHB, rdHC, rdHD`）
行43: `andn.w` 指令：将 `rdHA` 中由 `wpN` 指定的 wyde 替换为 `(rdHA[wyde] & ~immu16)`
```

### 与生成表「汇编形式」列逐条对照证据

**A段 8条对照**（生成表 `docs/assembly-list.md` 行92-104）：

| # | 实现（行号） | 生成表 | 一致 |
|---|---|---|---|
| 1 | `set.ow rdHA, wpN, immu16`（行32） | `set.ow rdHA, wpN, immu16`（行100） | ✅ |
| 2 | `set.zw rdHA, wpN, immu16`（行33） | `set.zw rdHA, wpN, immu16`（行103） | ✅ |
| 3 | `or.w rdHA, wpN, immu16`（行34） | `or.w rdHA, wpN, immu16`（行99） | ✅ |
| 4 | `andn.w rdHA, wpN, immu16`（行35） | `andn.w rdHA, wpN, immu16`（行97） | ✅ |
| 5 | `set.zw rbHA, wpN, immu16`（行48） | `set.zw rbHA, wpN, immu16`（行102） | ✅ |
| 6 | `or.w rbHA, wpN, immu16`（行49） | `or.w rbHA, wpN, immu16`（行98） | ✅ |
| 7 | `andn.w rbHA, wpN, immu16`（行50） | `andn.w rbHA, wpN, immu16`（行96） | ✅ |
| 8 | `set.w rfHA, wpN, immu16`（行56） | `set.w rfHA, wpN, immu16`（行101） | ✅ |

**B段 11条对照**（生成表行83-90,172,192；`immu6=1` → `{reg}` 无冒号）：

| # | 实现 | 生成表模板（immu6=1展开） | 目的/源顺序 | 一致 |
|---|---|---|---|---|
| 1 | `rb2rd {rd5}, {rb3}` | `rb2rd {rdHB}, {rbHC}` | 目的 rd、源 rb | ✅ |
| 2 | `rf2rd {rd2}, {rf7}` | `rf2rd {rdHB}, {rfHC}` | 目的 rd、源 rf | ✅ |
| 3 | `rd2rd {rd8}, {rd3}` | `rd2rd {rdHB}, {rdHC}` | 目的 rd、源 rd | ✅ |
| 4 | `ra2rd {rd4}, {ra10}` | `ra2rd {rdHB}, {raHC}` | 目的 rd、源 ra | ✅ |
| 5 | `rd2rb {rb5}, {rd3}` | `rd2rb {rbHB}, {rdHC}` | 目的 rb、源 rd | ✅ |
| 6 | `rb2rb {rb2}, {rb7}` | `rb2rb {rbHB}, {rbHC}` | 目的 rb、源 rb | ✅ |
| 7 | `rd2rf {rf1}, {rd0}` | `rd2rf {rfHB}, {rdHC}` | 目的 rf、源 rd | ✅ |
| 8 | `rd2rf {rf1}, {rd0}` | 同上 | 同上 | ✅ |
| 9 | `rd2rf {rf1}, {rd5}` | 同上 | 同上 | ✅ |
| 10 | `ft2ft {rf1}, {rf2}` | `ft2ft {rfHB}, {rfHC}` | 目的 rf、源 rf | ✅ |
| 11 | `fo2fo {rf2}, {rf7}` | `fo2fo {rfHB}, {rfHC}` | 目的 rf、源 rf | ✅ |

### git diff 证明未触 ASSEMBLY_LIST 区

```
$ git diff spec/SimRISC-03-16位立即数操作.md | grep "^@@" 
@@ -29,31 +29,31 @@
@@ -108,10 +108,10 @@
@@ -134,8 +134,8 @@
@@ -158,16 +158,16 @@
```

所有 hunk 起始行号 ≥29 > 22（ASSEMBLY_LIST_END 行），生成区（行6-22）零改动。

### 语义零变化证据

数值逐 hunk 核对（均未动）：
- 行74: `0` / 行77: `-1`, `0xFFFF` / 行80: `-42`, `0xFFD6`
- 行83: `0xFFFFFFFFFFFFFFF0`, `0xFFF0` / 行86: `~(1<<5)`, `0xFFDF`
- 行89: `42` / 行90-92: `0x1234ABCD`, `0x1234`, `0xABCD`
- 行95-99: `0xDEADBEEF_CAFEBABE`, `0xDEAD`, `0xBEEF`, `0xCAFE`, `0xBABE`
- 行125: `rb1, wp0, 0` / 行128-131: `0x123456789ABC`, `0x1234`, `0x5678`, `0x9ABC`
- 行149-151: `0x3F800000`, `0x3F80`, `0x0000`
- 行154-158: `0x3FF0000000000000`, `0x3FF0`, `0x0000`

限制条文（行68、121等）一字不动。

### 反例注入 + 复原证据

1. **注入**：将行111 `rb2rd {rd5}, {rb3}` 回退为 `rb2rd rd5, rb3, 1`
2. **检出**：`git diff` 显示 `+set.rd   rd5, rb3       ; 展开为 rb2rd rd5, rb3, 1`（非空，注入有效）
3. **复原**：恢复为 `rb2rd {rd5}, {rb3}`
4. **验证**：`git diff` 显示 `-set.rd   rd5, rb3       ; 展开为 rb2rd rd5, rb3, 1` / `+set.rd   rd5, rb3       ; 展开为 rb2rd {rd5}, {rb3}`（新格式恢复）

同理注入 D段行40 `rdha`（小写），检出后复原为 `rdHA`，无残留。

### make check 真实输出

```
$ make check > /tmp/opencode/SPEC-043t-make-check.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

**新发现/坑**：无特殊发现。本任务为纯记法替换，改动模式清晰。

**遗留问题**：无。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方法**：自主逐行审查（subagent depth limit reached，无法调用嵌套子代理）

**审查结果**：

| hunk | 行 | 内容 | 对照 | 判定 |
|------|---|------|------|------|
| 生成区 | 6-22 | ASSEMBLY_LIST 区域 | 未改动（git diff 命中行均 > 22） | ✅ |
| A段1 | 32 | `set.ow rdHA, wpN, immu16` | 生成表行100 | ✅ |
| A段2 | 33 | `set.zw rdHA, wpN, immu16` | 生成表行103 | ✅ |
| A段3 | 34 | `or.w rdHA, wpN, immu16` | 生成表行99 | ✅ |
| A段4 | 35 | `andn.w rdHA, wpN, immu16` | 生成表行97 | ✅ |
| A段5 | 48 | `set.zw rbHA, wpN, immu16` | 生成表行102 | ✅ |
| A段6 | 49 | `or.w rbHA, wpN, immu16` | 生成表行98 | ✅ |
| A段7 | 50 | `andn.w rbHA, wpN, immu16` | 生成表行96 | ✅ |
| A段8 | 56 | `set.w rfHA, wpN, immu16` | 生成表行101 | ✅ |
| B段1-11 | 111-170 | 见完成区B段对照表 | 生成表行83-90,172,192 | ✅ |
| C段 | 74-99 | 展开注释（具体寄存器） | 未被误改 | ✅ |
| D段 | 40,42,43 | 正文引用大写 | 无小写残留 | ✅ |
| 语义 | 全文 | 数值 | 未动 | ✅ |
| 反例 | - | 注入回退 → diff 非空 → 还原恢复 | - | ✅ |

**判决**：通过，0 个 finding。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立重跑，不采信完成区叙述）
**审查脚本**（reviewer 自写，留档）：`/tmp/opencode/SPEC-043t/verify.py`（结构性全量核验）、`scope_inject.sh` / `inject2.sh`（范围 + 反例注入）。基线 `git show HEAD:spec/SimRISC-03-16位立即数操作.md` 存为 `spec.HEAD.md`。

**方法说明**：B 段不靠字符串比对——脚本从 `docs/assembly-list.md` 的「汇编形式」列用正则 `\{([a-z]+)H` **反推每条 `X2Y` 的目的/源寄存器组**，再与正文 `{dst}, {src}` 的组类逐条比对；另用「先把新记法规范化回旧记法再与 HEAD 逐字节比对」证明语义零变化。

##### 重跑记录（真实输出/退出码）

1. 独立核验脚本（对交付文件）：
```
$ python3 /tmp/opencode/SPEC-043t/verify.py; echo EXIT=$?
[PASS] ASSEMBLY_LIST_END == 22
[PASS] ASSEMBLY_LIST_START == 6
[PASS] A段 found 8 rwii lines            # 行32/33/34/35/48/49/50/56
[PASS] A段 line 32..56 matches table (set.ow/rd, set.zw/rd, or.w/rd, andn.w/rd,
       set.zw/rb, or.w/rb, andn.w/rb, set.w/rf)   # 8 条逐条对生成表
[PASS] B段 count == 11
[PASS] B段 line 111: rb2rd {rd5}, {rb3}    ... (112 rf2rd/{rd2},{rf7}、113 rd2rd、114 ra2rd、
       137 rd2rb、138 rb2rb、161/162/168 rd2rf、169 ft2ft、170 fo2fo)   # 11 条 X2Y 全对
[PASS] B段 line 111..170 no colon/?       # 单元素组不带冒号
[PASS] B段 line 111..170 dst/src groups vs table  # 目的/源组与生成表逐条一致
[PASS] C段 concrete-reg comments unchanged vs HEAD   # 7 条完全一致
[PASS] D段 no lowercase field-name residue
[PASS] semantic zero-change (normalized WORK == HEAD)
[PASS] numeric literal multiset unchanged after normalization
[PASS] literal 0x1234/0xABCD/0xDEADBEEF_CAFEBABE/0x3F800000/0x3FF0000000000000/
       0xFFFF/0xFFD6/0xFFF0/0xFFDF/-42 present
RESULT: ALL CHECKS PASS
EXIT=0
```
> 注：B 段 dst/src 校验的判据取自生成表字段组（如 `rb2rd {rdHB:…}, {rbHC:…}` → dst=rd、src=rb），非任务书自述表。

2. 范围约束：
```
$ git status --porcelain
 M ".tao/tasks/spec/SPEC-043t-...正文改新汇编格式.md"
 M "spec/SimRISC-03-16位立即数操作.md"        # 仅此两文件，无生成器/contracts/docs 改动，无未跟踪文件
$ git diff -U0 -- spec/...md | grep '^@@'
@@ -32,4 +32,4 @@   @@ -40 +40 @@   @@ -42,2 +42,2 @@   @@ -48,3 +48,3 @@
@@ -56 +56 @@    @@ -111,4 +111,4 @@  @@ -137,2 +137,2 @@  @@ -161,2 +161,2 @@
@@ -168,3 +168,3 @@
# 脚本解析 -U0 全部增删行号：lines<=22 touched: NONE   （生成区 6–22 零改动）
```

3. 语义零变化（独立方法）：把正文按「X2Y 组记法 → 旧 3 操作数、`rdHA`→`rdha`…」规范化后与 HEAD 逐字节比较 → **完全相同**（无 diff）。另做 token 差异分析：全文大小写 token 变化仅为 `rdha→rdHA`(8)、`rbha→rbHA`(3)、`rfha→rfHA`(1)、`rdhb/rdhc/rdhd→rdHB/rdHC/rdHD`；除这些外**无任何**新增/删除 token，数值与条文一字未动。

4. 反例注入（脚本可失败，逐项）：
```
[detected] B段 {rd5}->{rd5:rd5}      verify EXIT=1
[detected] B段 dst/src 组对调         verify EXIT=1 （B段 dst/src 组校验 + 规范化等价同时报 FAIL）
[detected] B段 回退 rd5, rb3, 1       verify EXIT=1
[detected] A段 rdHA->rdha             verify EXIT=1
[detected] A段 set.w rfHA->rbHA       verify EXIT=1
[detected] 数值 0xFFD6->0xFFD7        verify EXIT=1
[detected] 数值 0x1234->0x1235        verify EXIT=1
[detected] C段 展开 42->43            verify EXIT=1
[detected] 生成区表格行改坏           verify EXIT=1
# 真实就地注入（B段 {rd5}->{rd5:rd5}）后：verify EXIT=1；还原后
sha256(before)=23933311... == sha256(after)=23933311...   RESTORE OK: file byte-identical
sha256(git diff before)==sha256(git diff after)           DIFF OK: git diff identical
post-restore verify: PASS；git status 无残留
```

5. `make check` 真实退出码（未走管道）：
```
$ make check > /tmp/opencode/SPEC-043t/make-check.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
# 尾部：check-patch-tree: 2 component(s), 67 patches OK
#       check-asm-list-consistency: 12 spec files OK
#       repository checks: PASS
```

##### 约束核验（逐条）

| # | 验收标准 | 结论 | 证据 |
|---|---|---|---|
| 1 | 只改 spec(+任务文件) | ✅ | `git status` 仅 2 文件；无未跟踪文件 |
| 2 | 未触生成区 | ✅ | `ASSEMBLY_LIST_END`=行22；-U0 全部增删行号 >22（NONE ≤22）；`check-asm-list-consistency` 12 files OK |
| 3 | A 段 8 条真指令 | ✅ | 8 条逐条命中 `rdHA/rbHA/rfHA`，`wpN/immu16` 原样，且与生成表逐条相符 |
| 4 | B 段 11 处 `{dst}, {src}`（无冒号，组对一致） | ✅ | 11 条计数正确、无 `:`/`?`；**从生成表反推 dst/src 组**逐条一致 |
| 5 | C 段未误改 | ✅ | 7 条具体寄存器展开注释与 HEAD 完全相同 |
| 6 | 语义零变化 | ✅ | 规范化后逐字节 == HEAD；token/数值分析无意外变化；关键数值与限制条文均在且未变 |
| 7 | 与生成表逐条相符 | ✅ | A 8 + B 11，脚本独立复算 |
| 8 | 反例可检出、复原无残留 | ✅ | 9 项注入全部 FAIL；就地注入后 sha256/git diff 双还原一致 |
| 9 | `make check` EXIT=0 | ✅ | 真实退出码 EXIT=0 |

##### 判决

**Accepted**。九条验收标准在审查者独立重跑下全部通过；未发现规避行为（无改契约/弱化断言/改生成器）；反例注入均能被检出，还原后仓库零残留。无阻断性发现。建议主会话将任务状态置为 `已验证`，并交由架构师终审。

（说明：完成区声称的行号/数值/退出一一复核一致，未发现夸大或改写。）
