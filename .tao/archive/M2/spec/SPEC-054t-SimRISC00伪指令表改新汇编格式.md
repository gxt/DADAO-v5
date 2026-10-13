# SPEC-054t: SimRISC-00 伪指令表改为新汇编格式

**模块**：spec
**项目里程碑**：M2
**依赖**：`ADR-0013`（含 D8）、`assembly-language.md` v1.1、生成表；前置 `SPEC-041t`…`053t`
**状态**：已验证

## 背景

全库终检发现 `spec/SimRISC-00-指令系统设计.md` §伪指令 表格（约 L378–395）仍为**旧小写字段级**写法（该文件无 ` ```simrisc ` 块、无生成区，故前序章节转换未覆盖）。本任务收尾。

## 修改范围（仅 `spec/SimRISC-00-指令系统设计.md`）

### §伪指令表（L384–395 等）

| 旧 | 新（以生成表为准） |
|---|---|
| `not.b rdhb, rdhc` / `not.w` / `not.t` / `not.o` | `not.b rdHB, rdHC` 等 |
| `xnor.b rdhb, rdhc, rd0` / `xnor.w` / `xnor.t` / `xnor.o` | `xnor.b rdHB, rdHC, rd0` 等（平铺；`rd0` 为具体寄存器）|
| `neg.b rdhb, rdhc` / `neg.w` / `neg.t` / `neg.o` | `neg.b rdHB, rdHC` 等 |
| `sub.sb rdhb, rd0, rdhc` / `sub.sw` / `sub.st` | `sub.sb rdHB, rd0, rdHC` 等（**`orrr` 平铺**）|
| `sub.so rd0, rdhb, rd0, rdhc`（`neg.o` 展开） | `sub.so {rd0, rdHB}, rd0, rdHC`（**双目的**，与 `SPEC-044t` 第 4 章同款）|

**保持**：`nop` / `swym 0`、`return` / `ret rd0, 0`（具体示例）；`set.rd rdxx, imm64` 等伪指令签名（`rdxx`/`rbxx`/`rfxx` 为伪指令形参）。

### 其它

全文扫描确认无其它旧式**寄存器字段引用**（`rdhb`/`rbhb`/`cg`/`rc` 小写等）；如发现一并转换并说明。

## 约束

- **只改 `spec/SimRISC-00-指令系统设计.md`**；不改生成器 / `contracts/` / `docs/`
- **语义零变化**：位宽/数值/条文一字不动
- 具体寄存器/编号（`rd0`）保持
- 命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. 伪指令表内所有**真指令**写法为新格式；`neg.o` 展开为**双目的** `sub.so {rd0, rdHB}, rd0, rdHC`
2. `swym 0`/`ret rd0, 0`/`set.rd rdxx, imm64` 等**未被误改**
3. 全文重扫**零残留**小写字段引用（`\b(r[bdr]h[a-z]|cg[a-z]{2}|rc[a-z]{2})\b` 为空）
4. **语义零变化**（逐 hunk）
5. 与生成表「汇编形式」列（`not`/`neg` 相关）逐条相符
6. 反例验证：注入一处回退（如 `neg.o` 展开写回 4 操作数、或 `not.b` 小写）→ 检查可检出；复原后无残留
7. `make check` EXIT=0

## 完成区

**测试结果**：通过 6/6（验收标准 1–7 全部满足）

**修改文件**：`spec/SimRISC-00-指令系统设计.md`（唯一改动文件）

**改动对照**（L384–391，共 8 行）：

| 行 | 旧 | 新 |
|----|-----|-----|
| 384 | `not.b rdhb, rdhc` / `xnor.b rdhb, rdhc, rd0` | `not.b rdHB, rdHC` / `xnor.b rdHB, rdHC, rd0` |
| 385 | `not.w rdhb, rdhc` / `xnor.w rdhb, rdhc, rd0` | `not.w rdHB, rdHC` / `xnor.w rdHB, rdHC, rd0` |
| 386 | `not.t rdhb, rdhc` / `xnor.t rdhb, rdhc, rd0` | `not.t rdHB, rdHC` / `xnor.t rdHB, rdHC, rd0` |
| 387 | `not.o rdhb, rdhc` / `xnor.o rdhb, rdhc, rd0` | `not.o rdHB, rdHC` / `xnor.o rdHB, rdHC, rd0` |
| 388 | `neg.b rdhb, rdhc` / `sub.sb rdhb, rd0, rdhc` | `neg.b rdHB, rdHC` / `sub.sb rdHB, rd0, rdHC` |
| 389 | `neg.w rdhb, rdhc` / `sub.sw rdhb, rd0, rdhc` | `neg.w rdHB, rdHC` / `sub.sw rdHB, rd0, rdHC` |
| 390 | `neg.t rdhb, rdhc` / `sub.st rdhb, rd0, rdhc` | `neg.t rdHB, rdHC` / `sub.st rdHB, rd0, rdHC` |
| 391 | `neg.o rdhb, rdhc` / `sub.so rd0, rdhb, rd0, rdhc` | `neg.o rdHB, rdHC` / `sub.so {rd0, rdHB}, rd0, rdHC` |

**未改动行**：L382 `swym 0`、L383 `ret rd0, 0`、L392–399 `set.rd rdxx`/`set.rb rbxx`/`set.ft rfxx`/`set.fo rfxx` 等伪指令签名——全部保持原样。

**验收结果**：
1. ✅ 伪指令表 L384–391 全部转换为新格式；`neg.o` 展开为双目的 `sub.so {rd0, rdHB}, rd0, rdHC`（与 SimRISC-04 L169 一致）
2. ✅ `swym 0`/`ret rd0, 0`/`set.rd rdxx, imm64` 等未被误改
3. ✅ 全文零残留：`grep -nE '\b(r[bdr]h[a-z]|cg[a-z]{2}|rc[a-z]{2})\b'` → EXIT=1（无匹配）
4. ✅ 语义零变化：diff 仅显示大小写变更 + `neg.o` 展开花括号，位宽/数值/条文一字不动
5. ✅ 与 SimRISC-04 生成表「汇编形式」列逐条相符
6. ✅ 反例验证：注入 L384 `not.b rdhb, rdhc` 回退 → grep 检出 L384；还原后零残留（EXIT=1）
7. ✅ `make check` EXIT=0（真实输出：`/tmp/opencode/spec-054t-check.log`）

**新发现/坑**：无

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`spec/SimRISC-00-指令系统设计.md` L384–391（8 行伪指令表）

**逐行核验**：

| 行 | 伪指令 | 语法列 | 展开形式列 | 判定 |
|----|--------|--------|-----------|------|
| 384 | `not.b` | `rdHB, rdHC` ✓ | `xnor.b rdHB, rdHC, rd0` ✓ | ✅ |
| 385 | `not.w` | `rdHB, rdHC` ✓ | `xnor.w rdHB, rdHC, rd0` ✓ | ✅ |
| 386 | `not.t` | `rdHB, rdHC` ✓ | `xnor.t rdHB, rdHC, rd0` ✓ | ✅ |
| 387 | `not.o` | `rdHB, rdHC` ✓ | `xnor.o rdHB, rdHC, rd0` ✓ | ✅ |
| 388 | `neg.b` | `rdHB, rdHC` ✓ | `sub.sb rdHB, rd0, rdHC` ✓（orrr 平铺） | ✅ |
| 389 | `neg.w` | `rdHB, rdHC` ✓ | `sub.sw rdHB, rd0, rdHC` ✓（orrr 平铺） | ✅ |
| 390 | `neg.t` | `rdHB, rdHC` ✓ | `sub.st rdHB, rd0, rdHC` ✓（orrr 平铺） | ✅ |
| 391 | `neg.o` | `rdHB, rdHC` ✓ | `sub.so {rd0, rdHB}, rd0, rdHC` ✓（双目的，与 SimRISC-04 L169 一致） | ✅ |

**未改动行核验**：L382 `swym 0`、L383 `ret rd0, 0`、L392–399 `set.*` 伪指令签名——全部保持原样，无误改 ✓

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 无 | — | — | — |

**判决**：全部 finding 已修（0 条），可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查对象**：`spec/SimRISC-00-指令系统设计.md`（唯一被改 spec 文件）+ 本任务文件
**审查方式**：全部结论基于我自己的命令重跑，不采信完成区转述。

**一、改动范围核验（约束 1）**

```
$ git status --short
 M ".tao/tasks/spec/SPEC-054t-...md"
 M "spec/SimRISC-00-指令系统设计.md"
$ git diff --name-only
（同上两文件）
```

`git diff` 显示 spec 文件仅有 **L384–391 共 8 行** 变更，L382/L383/L392–399 及全文其余部分未动。约束 1 守住。任务文件变更属完成区/审阅记录填写，符合预期。

**二、8 行逐条比对（验收 1、5）**

| 行 | 语法列（现状） | 展开列（现状） | 权威来源 | 判定 |
|----|------|------|------|------|
| 384 | `not.b rdHB, rdHC` | `xnor.b rdHB, rdHC, rd0` | SimRISC-10 L140 | ✅ |
| 385 | `not.w rdHB, rdHC` | `xnor.w rdHB, rdHC, rd0` | SimRISC-09 L140 | ✅ |
| 386 | `not.t rdHB, rdHC` | `xnor.t rdHB, rdHC, rd0` | SimRISC-08 L140 | ✅ |
| 387 | `not.o rdHB, rdHC` | `xnor.o rdHB, rdHC, rd0` | SimRISC-04 L159 | ✅ |
| 388 | `neg.b rdHB, rdHC` | `sub.sb rdHB, rd0, rdHC` | SimRISC-10 L92 | ✅ |
| 389 | `neg.w rdHB, rdHC` | `sub.sw rdHB, rd0, rdHC` | SimRISC-09 L92 | ✅ |
| 390 | `neg.t rdHB, rdHC` | `sub.st rdHB, rd0, rdHC` | SimRISC-08 L92 | ✅ |
| 391 | `neg.o rdHB, rdHC` | `sub.so {rd0, rdHB}, rd0, rdHC` | SimRISC-04 L169 | ✅ |

`neg.o` 展开为**双目的**，与生成表字段位序一致：
`spec/SimRISC-04 L38: | sub.so | rrrr | rd | sub.so {rdHA, rdHB}, rdHC, rdHD | ...`
→ 目的对在首位，后跟两源：`{rd0, rdHB}, rd0, rdHC` ✅。验收 1、5 满足。

**三、未误改行核验（验收 2）**

L382 `nop`/`swym 0`、L383 `return`/`ret rd0, 0`、L392–399 `set.rd rdxx, imm64`/`set.rb rbxx`/`set.ft rfxx`/`set.fo rfxx` 全部与 `git show HEAD` 逐字节一致（diff 中未出现）。✅

**四、全 spec 零残留（验收 3）**

自建脚本（`/tmp/opencode/spec-054t-review/scan.py`，剥除 `<!-- ASSEMBLY_LIST_START/END -->` 生成区，排除 `SimRISC-0.5.3`，正则 `\b(r[bdr]h[a-z]|cg[a-z]{2}|rc[a-z]{2})\b`）：

```
$ python3 /tmp/opencode/spec-054t-review/scan.py /home/ubuntu/DADAO-v5/spec
TOTAL_MATCHES=0   EXIT=0
```

对照（含生成区、全 SimRISC 数字文件）：

```
$ grep -nE '\b(r[bdr]h[a-z]|cg[a-z]{2}|rc[a-z]{2})\b' spec/SimRISC-[0-9]*.md
grep EXIT=1   # 无匹配
```

零残留。✅

**五、语义零变化（验收 4）**

脚本对 HEAD 版与现状版逐行比对，仅做「字段名大小写还原（`rdHB`→`rdhb`）+ 双目的花括号展平（`{rd0, rdHB}`→`rd0, rdHB`）」归一后：

```
Unexplained sem-diffs = 0 | lines: 400 400
```

即 8 行变更的**操作数顺序、位宽、说明文字**与旧版完全等价，唯一差异是寄存器字段大小写与 `neg.o` 的 4 平铺操作数↔双目的规范写法。语义零变化。✅

**六、反例注入（验收 6，注入在 /tmp 副本，未触碰真实仓库）**

| 注入 | 内容 | 我的脚本输出 | 结果 |
|------|------|------|------|
| A | `neg.o` 展开写回 4 操作数 `sub.so rd0, rdhb, rd0, rdhc` | `SimRISC-00-...:391: rdhb/rdhc ...` `TOTAL_MATCHES=2` `Exited with code 1` | ✅ FAIL 可检出 |
| B | `not.b` 语法列改回 `not.b rdhb, rdhc`（`diff` 确认非空） | `SimRISC-00-...:384: rdhb/rdhc ...` `TOTAL_MATCHES=2` `Exited with code 1` | ✅ FAIL 可检出 |
| C | 追加 `cgab`/`rcxz`（验证正则另两分支非空） | `SimRISC-12-待定.md:125: cgab/rcxz ...` `TOTAL_MATCHES=2` `Exited with code 1` | ✅ FAIL 可检出 |

三次注入后清理 `/tmp` 副本，复核仓库：

```
$ git status --short
 M ".tao/tasks/spec/SPEC-054t-...md"
 M "spec/SimRISC-00-指令系统设计.md"   # 与审查开始前一致，无残留
```

约束「反例注入须在 /tmp 副本」守住，复原干净。✅

**七、make check（验收 7）**

```
$ make check > /tmp/opencode/spec-054t-review/make-check.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
...（tail）
check-asm-list-consistency: 12 spec files OK
check_issues: 64 open, 10 closed (0 blocking M1-gate: 0)
repository checks: PASS
```

真实退出码 0（未经管道，直接 `$?`）。✅

**约束逐条核对**

| 约束 | 结果 |
|------|------|
| 只改 `spec/SimRISC-00-指令系统设计.md`（+任务文件） | ✅ |
| 不改生成器/`contracts/`/`docs/` | ✅（diff 无涉及） |
| 语义零变化（位宽/数值/条文） | ✅（归一后逐行相等） |
| 具体寄存器/编号 `rd0` 保持 | ✅ |
| 命令缺失即停 | ✅（未出现，未安装任何东西） |

**说明**：验收 5 所述「与生成表汇编形式列相符」——`not`/`neg` 展开出现在各 SimRISC-0X 的伪指令定义小节（L92/L140/L159/L169，非 ASSEMBLY_LIST 生成区）；我逐条对照这 4 处真值，全部一致。

**判决**：**Accepted**

全部 7 条验收标准在我独立重跑下通过，约束无违反，反例注入均被检出且仓库复原干净。工程师产出达标，供主会话终审。

