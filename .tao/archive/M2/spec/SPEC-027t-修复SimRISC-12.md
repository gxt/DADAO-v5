# SPEC-027t: 修复 SimRISC-12 待定文档

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 问题描述

commit `7f1af95`（删除 ftmadd/fomadd）创建了 `spec/SimRISC-12-待定.md`，存在以下缺陷：

1. **头部条数与内容矛盾**：头部写「（14 条）— cfxld/cfxst/fence/lr_\*/sc_\*/rela.si/f\*madd」，但同一 commit 已删除 ftmadd/fomadd，应为 12 条，且移除 `f*madd`
2. **rela.si 描述正文丢失**：只有代码块 `rela.si rbha, imms18`，原 0.5.3 的语义描述（左移12位 / 4KB对齐 / 高16位保持 / 512MB范围）**全部丢失**
3. **循环引用**：SimRISC-06 说「详见 SimRISC-12」，SimRISC-12 说「详见 SimRISC-06」
4. **缺文件末尾换行**

## 修改内容

### 1. 修正头部（spec/SimRISC-12-待定.md 第4行）

```
> **分类：待定 [deferred]**（12 条）— cfxld/cfxst/fence/lr_*/sc_*/rela.si
```

### 2. 补回 rela.si 描述正文

从 `spec/SimRISC-0.5.3/SimRISC-02-地址类指令.md` 的 §PC相对寻址 完整迁回，内容如下（逐字）：

```
PC相对寻址指令需要两个源操作数，一个目的操作数；其中一个源操作数为RB0寄存器，即PC值。
操作数类型是 `riii` ，立即数为18位有符号数，虽然有位数限制，但是具有很好的便利性。
由于立即数采用补码的编码方式，无需区分加减操作。
具体指令如下：

```simrisc
rela.si    rbha, imms18
```

注意，采用这种操作数类型的加法指令，无法判断是否溢出。
由于imms18为有符号数，该加法指令也隐含实现了减法指令。

rela.si指令根据PC的偏移地址计算目标地址。
rela.si指令将一个18位有符号立即数左移12位，得到一个30位的有符号数，接着将PC地址的低12位清零，得到PC所在4KB对齐基地址；
然后将该基地址加上30位的有符号数，就得到了目标地址，最后将目标地址写入rbha寄存器，**rbha 的高 16 位保持不变**。

通常的使用场景是先通过rela.si获取一个基地址，然后再通过存取类指令或跳转类指令的偏移地址获取具体变量的地址。
采用rela.si指令可以处理偏移地址在512MB以内的PC相对寻址问题，对于更大范围的PC相对寻址，仍然需要采用显式的rb0参与寻址。
```

### 3. 修正循环引用

- `spec/SimRISC-12-待定.md` 第65行「rela.si 指令详见 SimRISC-06（控制流）。」**删除**（描述已在本文档）
- `spec/SimRISC-06-控制流.md` 第117行注释保留（指向 SimRISC-12 正确）

### 4. 补文件末尾换行

## 约束

- 逐条精确替换，**禁止正则批量替换**
- 不改动文件其他内容

## 验收标准

1. SimRISC-12 头部为「（12 条）」且无 `f*madd`
2. rela.si 完整描述正文存在（含「左移12位」「4KB对齐基地址」「rbha 的高 16 位保持不变」「512MB」）
3. SimRISC-12 无「详见 SimRISC-06」的循环引用
4. 文件末尾有换行

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收

**审查对象**：`spec/SimRISC-12-待定.md`（worktree 未提交改动，`git diff` 单文件 16+/3-）
**独立 oracle**：`spec/SimRISC-0.5.3/SimRISC-02-地址类指令.md` §PC相对寻址（L173–190）

##### 1. 头部修正（验收标准 1）

```
$ sed -n '4p' "spec/SimRISC-12-待定.md"
> **分类：待定 [deferred]**（12 条）— cfxld/cfxst/fence/lr_*/sc_*/rela.si

$ grep -n 'f\*madd\|ftmadd\|fomadd' "spec/SimRISC-12-待定.md"
（无匹配，EXIT=1）
```

✅ 通过：条数为「（12 条）」，`/f*madd` 已移除。条数与指令数自洽（fence1 + cfxld1 + cfxst1 + lr_*4 + sc_*4 + rela.si1 = 12）。

##### 2. rela.si 描述正文逐句比对（验收标准 2，核心）

用 octav 抽取 oracle L173–190 与 SimRISC-12 L61–78 逐行 diff：

```
$ sed -n '173,190p' "spec/SimRISC-0.5.3/SimRISC-02-地址类指令.md" > /tmp/opencode/SPEC-027t/oracle.txt
$ sed -n '61,78p'  "spec/SimRISC-12-待定.md"                     > /tmp/opencode/SPEC-027t/actual.txt
$ diff /tmp/opencode/SPEC-027t/oracle.txt /tmp/opencode/SPEC-027t/actual.txt
DIFF_EXIT=0
```

✅ 通过：**逐字节零差异**，原文全部 18 行（含代码块 `rela.si    rbha, imms18`）无遗漏、无改写。

关键语义确认（均在正文中）：左移12位 ✅、PC 低12位清零得 4KB 对齐基地址 ✅、`**rbha 的高 16 位保持不变**` ✅、512MB 范围 ✅。

##### 3. 循环引用（验收标准 3）

```
$ grep -n "SimRISC-06" "spec/SimRISC-12-待定.md"
（无任何匹配，EXIT=1）

$ grep -n "详见 SimRISC-12" "spec/SimRISC-06-控制流.md"
117:> **注**：rela.si 属于待定分类（deferred），详见 SimRISC-12。
```

✅ 通过：SimRISC-12 已无对 SimRISC-06 的引用（含「详见 SimRISC-06」）；SimRISC-06 指向 SimRISC-12 的注保留。

##### 4. 文件末尾换行（验收标准 4）

```
$ python3 -c "d=open('spec/SimRISC-12-待定.md','rb').read(); print(d.endswith(b'\n'))"
True
```
`git diff` 亦显示 `\ No newline at end of file` 标记随本次改动消失。

✅ 通过。

##### 5. 约束核验（逐条）

- **只改 SimRISC-12**：`git diff --stat` 该文件 1 file changed, 16 insertions(+), 3 deletions(-)；三处 hunk 均为头部、rela 段、末尾换行，未触碰其他内容。✅
- **不改动文件其他内容**：diff 无其他行变动。✅
- **精确替换（禁正则批量）**：结果与 oracle 逐字节一致，无正则误伤痕迹（如全角/半角、空格差异）。✅

##### 6. 反例验证（检查方法能失败）

- 删掉「然后将该基地址加上30位的有符号数…」整句 → `diff` 输出 `15d14`，`REVERSE_DIFF_EXIT=1`（检测到遗漏）。✅
- 头部改回「（14 条）…/f*madd」→ `grep 'f\*madd'` EXIT=0（命中）。✅
- 追加回「rela.si 指令详见 SimRISC-06（控制流）。」→ `grep "详见 SimRISC-06"` EXIT=0（命中）。✅
- 去掉末尾换行 → `ends_with(b'\n')=False`（检测到）。✅

四种检查方法均对注入反例报 FAIL，非恒真。

##### 判决：**Accepted**

四条验收标准在我的独立重跑下全部通过，硬约束无违反，核心 rela.si 正文与 oracle 逐字节一致。

**流程观察（非验收标准，供主会话处置）**：任务文件的「完成区」仍为空、状态行仍为「状态：待开始」，engineer 未回填自审记录（该任务文件最后提交为 `979404f`，未含本轮产出记录）。请主会话在将状态置为 `已验证` 前补记完成区/状态与提交。