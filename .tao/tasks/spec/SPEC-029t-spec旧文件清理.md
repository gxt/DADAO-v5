# SPEC-029t: spec/ 旧文件清理与 SimRISC-10 补交

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：无
**状态**：已验证

## 问题描述

审核发现 commit 提交状态与实际不符：

1. **旧文件未删除**：SPEC-014t 声称「旧 01~04 已删除」，但 HEAD 中仍存在：
   - `spec/SimRISC-01-数据类指令.md`（0.5.3 原件）
   - `spec/SimRISC-02-地址类指令.md`
   - `spec/SimRISC-03-浮点类指令.md`
   - `spec/SimRISC-04-系统类指令.md`
   - `spec/SimRISC-01-存储.md`（改名后的旧名，`55e2c19` 未用 `git mv`）
   - `spec/SimRISC-07-浮点.md`（旧名）

2. **SimRISC-10 从未提交**：`spec/SimRISC-10-8位数据运算.md` 一直为 untracked

## 修改内容

### 1. 删除旧文件（确认工作树已是删除状态）

工作树当前状态（`git status --short spec/`）：
```
 D spec/SimRISC-01-存储.md
 D spec/SimRISC-01-数据类指令.md
 D spec/SimRISC-02-地址类指令.md
 D spec/SimRISC-03-浮点类指令.md
 D spec/SimRISC-04-系统类指令.md
 D spec/SimRISC-07-浮点.md
?? spec/SimRISC-10-8位数据运算.md
```

### 2. 提交 SimRISC-10

`spec/SimRISC-10-8位数据运算.md` 加入 git。

### 3. 提交状态修复

将所有变更 `git add` 并提交，使 HEAD 与工作树一致。

## 约束

- 只处理上述 git 提交状态，不改动文件内容
- 提交前确认 `spec/SimRISC-0.5.3/` 归档目录未受影响
- 确认最终 `spec/SimRISC-*.md`（非 0.5.3）只有 00~12 共 13 个文件

## 验收标准

1. `git ls-files spec/SimRISC-*.md | grep -v 0.5.3` 恰好 13 个（00~12）
2. 旧文件 `SimRISC-01-数据类指令.md` 等 4 个原始 0.5.3 文件已删除
3. `spec/SimRISC-10-8位数据运算.md` 已入库
4. `spec/SimRISC-0.5.3/` 归档目录完整（5 个文件）
5. `git status --short spec/` 干净

## 完成区

**测试结果**：全部 5 条验收标准通过

**修改文件**：
- 删除：`spec/SimRISC-01-存储.md`、`spec/SimRISC-01-数据类指令.md`、`spec/SimRISC-02-地址类指令.md`、`spec/SimRISC-03-浮点类指令.md`、`spec/SimRISC-04-系统类指令.md`、`spec/SimRISC-07-浮点.md`
- 新增：`spec/SimRISC-10-8位数据运算.md`

**验收结果**：
```
$ git ls-files spec/SimRISC-*.md | grep -v 0.5.3 | wc -l
13

$ git ls-files spec/SimRISC-*.md | grep -v 0.5.3 | sort
spec/SimRISC-00-指令系统设计.md
spec/SimRISC-01-取数存数.md
spec/SimRISC-02-寄存器复制.md
spec/SimRISC-03-16位立即数操作.md
spec/SimRISC-04-64位数据运算.md
spec/SimRISC-05-64位地址运算.md
spec/SimRISC-06-控制流.md
spec/SimRISC-07-浮点运算.md
spec/SimRISC-08-32位数据运算.md
spec/SimRISC-09-16位数据运算.md
spec/SimRISC-10-8位数据运算.md
spec/SimRISC-11-其它.md
spec/SimRISC-12-待定.md

$ git ls-files spec/SimRISC-0.5.3/
spec/SimRISC-0.5.3/SimRISC-00-指令系统设计.md
spec/SimRISC-0.5.3/SimRISC-01-数据类指令.md
spec/SimRISC-0.5.3/SimRISC-02-地址类指令.md
spec/SimRISC-0.5.3/SimRISC-03-浮点类指令.md
spec/SimRISC-0.5.3/SimRISC-04-系统类指令.md

$ git status --short spec/
（空，工作树干净）

$ git log --oneline -1
0abb9c0 spec: 清理旧文件并补交 SimRISC-10
```

**新发现/坑**：无

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：本次为纯 git 状态修复（删除旧跟踪 + 新增 SimRISC-10），无代码逻辑改动。

**审查内容**：
1. 暂存区排除了 `docs/README.md`（属 SPEC-030t），仅包含 spec/ 变更 ✅
2. 6 个旧文件删除 + 1 个新文件新增，与任务书要求一致 ✅
3. 提交后 `git status --short spec/` 干净 ✅
4. `spec/SimRISC-0.5.3/` 归档目录未受影响（5 个文件） ✅
5. `git ls-files spec/SimRISC-*.md | grep -v 0.5.3` 恰好 13 个（00~12） ✅

**判决**：无 finding，通过。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑全部验收命令（未读完成区转述）；对验收断言做反例证伪；核对 commit 内容与仓库门控。

**重跑记录（真实输出）**

1) 验收标准 1 — `spec/SimRISC-*.md`（非 0.5.3）计数与清单：
```
$ git -c core.quotePath=false ls-files 'spec/SimRISC-*.md' | grep -v 0.5.3 | wc -l
13
$ git -c core.quotePath=false ls-files 'spec/SimRISC-*.md' | grep -v 0.5.3 | sort
spec/SimRISC-00-指令系统设计.md
spec/SimRISC-01-取数存数.md
spec/SimRISC-02-寄存器复制.md
spec/SimRISC-03-16位立即数操作.md
spec/SimRISC-04-64位数据运算.md
spec/SimRISC-05-64位地址运算.md
spec/SimRISC-06-控制流.md
spec/SimRISC-07-浮点运算.md
spec/SimRISC-08-32位数据运算.md
spec/SimRISC-09-16位数据运算.md
spec/SimRISC-10-8位数据运算.md
spec/SimRISC-11-其它.md
spec/SimRISC-12-待定.md
```
→ 恰好 13 个（00~12），命名与 SimRISC-00 分类一致。

2) 验收标准 2 — 旧文件已从 HEAD 删除（`git cat-file -e HEAD:<path>`）：
```
spec/SimRISC-01-数据类指令.md -> not in HEAD
spec/SimRISC-02-地址类指令.md -> not in HEAD
spec/SimRISC-03-浮点类指令.md -> not in HEAD
spec/SimRISC-04-系统类指令.md -> not in HEAD
spec/SimRISC-01-存储.md       -> not in HEAD
spec/SimRISC-07-浮点.md       -> not in HEAD
```
→ 6 个旧文件（4 个 0.5.3 原件 + 2 个旧名）均不在 HEAD。

3) 验收标准 3 — SimRISC-10 已入库且内容完整：
```
$ git ls-files 'spec/SimRISC-10-8位数据运算.md'
spec/SimRISC-10-8位数据运算.md
```
内容 126 行，含 26 条 8 位指令书写形式（add/sub/cmp/mul/div/rem ×{ub,sb}=12；and/or/xor/xnor=4；shl.ub、shr.ub、shr.sb、ext.ub、ext.sb 各 orrr+orri=10），与 `contracts/opcodes.yaml` 中 `op: '0x43'`（MISC-byte）的 **26 条编码条目**逐一对应（21 条 orrr + 5 条 orri）。
```
$ python3 -c "import yaml;d=yaml.safe_load(open('contracts/opcodes.yaml'));print(len([x for x in d if x.get('op')=='0x43']))"
26
```
另与 `docs/assembly-list.md`「8位数据运算（26 条）」的 26 行、`adr-0012` 计数表「10 | 8位数据运算 | 26」一致。

4) 验收标准 4 — 归档目录完整：
```
$ git ls-files spec/SimRISC-0.5.3/
spec/SimRISC-0.5.3/SimRISC-00-指令系统设计.md
spec/SimRISC-0.5.3/SimRISC-01-数据类指令.md
spec/SimRISC-0.5.3/SimRISC-02-地址类指令.md
spec/SimRISC-0.5.3/SimRISC-03-浮点类指令.md
spec/SimRISC-0.5.3/SimRISC-04-系统类指令.md
```
→ 5 个（00~04）。

5) 验收标准 5 — 工作树干净：
```
$ git status --short spec/
（空）
```

6) commit `0abb9c0` 内容：
```
$ git -c core.quotePath=false show --name-status --format='%H%n%s' 0abb9c0
0abb9c08708a4ecf2ccdacd054ea6efbcf1ca0b0
spec: 清理旧文件并补交 SimRISC-10
D	spec/SimRISC-01-存储.md
D	spec/SimRISC-01-数据类指令.md
D	spec/SimRISC-02-地址类指令.md
D	spec/SimRISC-03-浮点类指令.md
D	spec/SimRISC-04-系统类指令.md
D	spec/SimRISC-07-浮点.md
A	spec/SimRISC-10-8位数据运算.md
```
→ 7 项变更全部位于 `spec/`，6 删 1 增，与任务书一致；无 `docs/` 等其它模块文件混入。
```
$ git -c core.quotePath=false show --name-only --format='' 0abb9c0 | grep -v '^spec/' | grep -vc '^$'   # 非 spec 文件数
0
$ git show --name-only --format='' 0abb9c0 | grep -c 'docs/README.md'   # 误纳检查
0
```
→ **未误纳** `docs/README.md`（该文件的工作树改动属 SPEC-030t，仍在未暂存状态）。

**约束核验（逐条）**

| 约束 | 结果 |
|------|------|
| 只处理 git 提交状态，不改动文件内容 | ✅ commit 仅含名称级 D/A，无内容修改；`git show --stat` 为纯删除+新增整文件 |
| 提交前确认 `spec/SimRISC-0.5.3/` 未受影响 | ✅ 归档 5 文件完整，且不在 0abb9c0 变更内 |
| 最终非 0.5.3 的 `spec/SimRISC-*.md` 恰 13 个（00~12） | ✅ 实测 13 |
| 未误纳 `docs/README.md` 等其它模块文件 | ✅ 0abb9c0 非 spec 文件数 = 0 |
| `git status --short spec/` 干净 | ✅ 空 |

**反例验证（证伪检查方法）**

- 计数检查可失败：注入一个伪 tracked 文件到临时 index 后，同一命令返回 **14**（>`spec/SimRISC-99-测试.md`）；对 pre-fix HEAD~1 运行同一命令返回 **18**（含 01-存储/01-数据类/02-地址/03-浮点/04-系统/07-浮点 等旧文件、缺 SimRISC-10）。→ 该断言非恒真。
- 旧文件删除检查可失败：同一 `git cat-file -e` 命令对 HEAD~1 的 `SimRISC-01-数据类指令.md`/`SimRISC-01-存储.md`/`SimRISC-07-浮点.md` 均返回 **PRESENT**。
- commit 污染检查可失败：把「非 spec 文件数=0」的过滤施加于触碰 docs 的提交（如 `f95c2c9`）会列出 `docs/README.md`/`docs/assembly-list.md`/`tools/llvm/gen_asm_list.py` 等，证明检查能检测误纳。
- 归档检查：`spec/SimRISC-0.5.3/` 实测 5 个，非 0.5.3 计数 13，二者互不串扰。

**门控回归（独立重跑）**

- `make check-spec-drift` → **EXIT=0**（PASS，3 合约 0 错误）
- `make validate-vectors` → **EXIT=0**（178/178，747 cases，覆盖率缺口 0）
- `make check-patch-tree` → **EXIT=0**（67 patches OK）
- `make check-spec-refs`（standalone，非 `make check` 成员）→ **EXIT=2**（59 violations: 7 Check1 + 52 Check2）。与 HEAD~1 对比：HEAD~1 为 **74 violations（22 Check1）**，本任务删除旧文件+补交 SimRISC-10 后 **Check1 由 22 降至 7**（contract-isa.md 原先失败的 15 条 `[SimRISC-10 §…]` 引用因文件入库而全部解析成功）。剩余 7 条 Check1（`contract-abi.md`/`contract-authoring.md` 对 DADAO/SimRISC-0X/SimRISC-02 的引用）**均为 pre-fix 已存在**，本任务**未引入任何新失败**。

**输出真实性**：engineer 完成区引用的 13/清单/归档 5 文件/`git status` 空/`git log -1 = 0abb9c0` 与我的独立重跑**逐条一致**，无重写或美化。

**判决**：**Accepted**

- 5 条验收标准在独立重跑下全部通过；约束逐条守住；commit 内容干净无污染。
- 说明：本任务为纯 git 状态修复，`check-spec-refs` 的剩余失败为 pre-fix 既有问题且该目标不属 `make check`，不构成返工理由。

**非阻断观察（供架构师定夺，非本任务范围）**：`contracts/opcodes.yaml` 中 26 条 8 位指令（`op: '0x43'`）的 `spec_cite` 仍写 `SimRISC-04 §加减操作/§乘除操作/…`，而 `contract-isa.md §12` 同类条目引用的是 `SimRISC-10 §…`。该不一致**属于 pre-fix 既有状态**（0abb9c0 未触及 opcodes.yaml），且本任务约束明令「不改动文件内容」，故不在本任务内修复；建议后续任务对齐 opcodes.yaml 的 `spec_cite` 指向。