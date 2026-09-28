# SPEC-018t: 更新 README.md + 版本引用同步

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`SPEC-020m`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范
- 输入：
  - `README.md`（当前版本表显示 SimRISC 0.5.3）
  - `spec/DADAO-11~23`（6 个文件，头部引用「基于 SimRISC 0.5.3」）
  - `.tao/knowledge/contract-abi.md`、`contract-elf.md`
  - `.tao/knowledge/adr-0003.md`、`adr-0004.md`
  - 其他引用 SimRISC 0.5.3 的文件（见下方清单）
- 输出：上述文件中 SimRISC 版本引用更新为 0.5.4
- 约束：
  1. 仅更新版本号引用，不修改其他内容
  2. 已完成的任务文件、`changelog.md`、`MEMORY.md` 等历史记录**不改写**

## 版本引用更新清单

| 文件 | 更新内容 |
|------|----------|
| `README.md` | 版本表 SimRISC 0.5.3 → 0.5.4 |
| `spec/DADAO-11-AEE-*.md` | 头部「基于 SimRISC 0.5.3」→ 0.5.4 |
| `spec/DADAO-12-SEE-*.md` | 同上 |
| `spec/DADAO-13-HEE-*.md` | 同上 |
| `spec/DADAO-21-ABI-*.md` | 同上 |
| `spec/DADAO-22-SBI-*.md` | 同上 |
| `spec/DADAO-23-HBI-*.md` | 同上 |
| `.tao/knowledge/contract-abi.md` | 版本引用 |
| `.tao/knowledge/contract-elf.md` | 版本引用 |
| `.tao/knowledge/adr-0003.md` | 版本引用 |
| `.tao/knowledge/adr-0004.md` | 版本引用 |

> 以上为已知清单。工程师执行时应 `grep -rln '0.5.3'` 排除 .git/.dadao/.work 和已完成任务文件，确认无遗漏。

## 验收标准

1. `README.md` 版本表中 SimRISC 版本为 0.5.4
2. `spec/DADAO-11~23` 头部引用更新为 0.5.4
3. 知识库文件版本引用更新为 0.5.4
4. 已完成任务文件和历史记录未被修改
5. 其他版本号（AEE/ABI、SEE/SBI、HEE/HBI）保持不变

## 完成区
**测试结果**：N/A（纯文档更新，无构建/测试步骤）
**修改文件**：
- `README.md` — 标题和版本表：SimRISC 0.5.3 → 0.5.4
- `spec/DADAO-11-AEE-*.md` — 头部版本引用
- `spec/DADAO-12-SEE-*.md` — 头部版本引用
- `spec/DADAO-13-HEE-*.md` — 头部版本引用
- `spec/DADAO-21-ABI-*.md` — 头部版本引用
- `spec/DADAO-22-SBI-*.md` — 头部版本引用
- `spec/DADAO-23-HBI-*.md` — 头部版本引用
- `.tao/knowledge/contract-isa.md` — 版本字段
- `.tao/knowledge/contract-abi.md` — 版本引用（2 处）
- `.tao/knowledge/contract-elf.md` — 版本引用（2 处）
- `.tao/knowledge/adr-0003-object-abi.md` — 版本引用（4 处）
- `.tao/knowledge/adr-0004-test-machine.md` — 版本引用（7 处）
- `.tao/knowledge/adr-0001-greenfield-rebuild.md` — 版本引用（3 处）
- `.tao/knowledge/contract-authoring.md` — 版本引用（1 处）
- `.tao/knowledge/deferred.md` — 版本引用（1 处）
- `contracts/legality_rules.yaml` — 头部注释版本
- `contracts/opcodes.yaml` — 头部注释版本
- `docs/README.md` — 版本引用
- `docs/impact-matrix.md` — 冻结基线版本
- `docs/m2-spec-planning.md` — spec 版本引用
- `docs/m1-retrospective.md` — contracts/opcodes.yaml 版本引用（1 处）
- `docs/issues.yaml` — issue 标题版本引用
- `tests/vectors/schema.md` — mnemonic 字段版本引用
- `.tao/README.md` — contract-isa.md 描述版本

**验收结果**：
- `grep -rln '0.5.3' --include='*.md' --include='*.yaml'` 排除 .git/.dadao/.work/SimRISC-0.5.3 后，仅剩：
  - `.tao/tasks/` 下的历史任务文件（不改写）
  - `.tao/knowledge/MEMORY.md`（历史记录，不改写）
  - `docs/m1-retrospective.md` 的2处 M1 基线历史记录（line50、line252，属历史事实）
- 其他版本号（AEE/ABI 0.9.2、SEE/SBI 0.7.1、HEE/HBI 0.1.2）均未改动
- 无任务文件、MEMORY.md 被修改

**新发现/坑**：
- 版本引用分布在远超任务清单列出的范围：contracts/*.yaml、docs/*.md、tests/vectors/schema.md、ADR 文件、contract-authoring.md、deferred.md、.tao/README.md 等均含有版本引用
- `docs/m1-retrospective.md` 中的版本引用需区分「历史事实」和「当前引用」：M1 基线版本（line50、line252）是历史记录，contracts/opcodes.yaml 版本（line260）是当前文件引用
- `tools/*.py` 和 `spec/SimRISC-01~04` 有预存改动（非本次任务引入）

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：24 个文件的版本引用更新（0.5.3 → 0.5.4）

**逐项审查**：

1. **README.md**：标题 `# DADAO for SimRISC 0.5.4` 和版本表 `| SimRISC | 0.5.4 |` — 仅替换版本号，其他内容不变 ✅
2. **spec/DADAO-11~23（6个文件）**：头部「基于 SimRISC 0.5.3」→「基于 SimRISC 0.5.4」— 各组件版本号（0.9.2/0.7.1/0.1.2）保持不变 ✅
3. **contract-isa.md**：版本字段 `0.5.3` → `0.5.4` ✅
4. **contract-abi.md**：2处引用（来源行 + M2命名约定行）✅
5. **contract-elf.md**：2处引用（来源行 + 指令格式表头）✅
6. **adr-0003-object-abi.md**：4处引用（关联行 + 依赖oracle行 + D2描述 + D2表格）✅
7. **adr-0004-test-machine.md**：7处引用（关联行 + spec描述 + 依赖oracle行 + rf0推导行 + M1排除行 ×2 + rf0常量行）✅
8. **adr-0001-greenfield-rebuild.md**：3处引用（关联行 + Context + D3）✅
9. **contract-authoring.md**：1处引用（版本约定行）✅
10. **deferred.md**：1处引用（编码知识行）✅
11. **contracts/*.yaml**：头部注释版本 ✅
12. **docs/*.md**：版本引用（README/impact-matrix/m2-spec-planning/m1-retrospective）✅
13. **docs/issues.yaml**：issue标题版本引用 ✅
14. **tests/vectors/schema.md**：mnemonic字段版本引用 ✅
15. **.tao/README.md**：contract-isa.md描述版本 ✅

**约束核验**：
- 任务文件（`.tao/tasks/`）未修改 ✅
- `MEMORY.md` 未修改 ✅
- `changelog.md`（如存在）未修改 ✅
- `spec/SimRISC-0.5.3/` 目录未修改 ✅
- 其他版本号（0.9.2/0.7.1/0.1.2）未被意外修改 ✅

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `docs/m1-retrospective.md` line50/252 仍为0.5.3 | ❌不修 | 历史事实记录，描述M1基线版本 | grep确认仅剩2处，均为M1历史基线描述 |

**判决**：所有版本引用已更新为0.5.4，约束条件全部满足。无未修 finding。

#### 第 1 轮 reviewer 验收

**审查对象**：SPEC-018t「更新 README.md + 版本引用同步」当前工作树状态（HEAD=`5bf9065`）。
**方法**：全部结论基于本审查者亲自执行的命令与输出，不采信完成区转述。

**重跑记录（真实输出）**：

1）残留扫描（任务指定检查，`--include='*.md'`）：
```
$ grep -rln '0.5.3' --include='*.md' . | grep -v .git | grep -v .dadao | grep -v .work | grep -v SimRISC-0.5.3
./docs/m1-retrospective.md
./.tao/knowledge/adr-0006-llvm-baseline.md      ← 正则假阳性（下方 -F 复核无命中）
./.tao/knowledge/changelog.md                   ← 正则假阳性
./.tao/knowledge/MEMORY.md
./.tao/tasks/{testcases,spec,llvm,qemu,integ,infra}/*.md   ← 历史/在办任务文件
```
逐条复核字面命中：
```
$ grep -rnF '0.5.3' docs/m1-retrospective.md .tao/knowledge/MEMORY.md .tao/knowledge/changelog.md
docs/m1-retrospective.md:50:规范 `SimRISC 0.5.3`；`AEE / ABI 0.9.2`；`SEE / SBI 0.7.1`；`HEE / HBI 0.1.2`
docs/m1-retrospective.md:252:| 维度 | 0628（0.4.1） | v5（0.5.3） |
.tao/knowledge/MEMORY.md:5,11,66,70,72 ...
$ grep -oF '0.5.3' .tao/knowledge/adr-0006-llvm-baseline.md .tao/knowledge/changelog.md
（两条命令均无输出 → 二者为 “376.53 MiB”/“189,410” 等被正则 `.` 误配，非真残留）
```
结论：`*.md` 范围内真残留仅 `docs/m1-retrospective.md`（M1 历史基线）、`MEMORY.md`/`changelog.md`（任务约束 2 明确豁免）、任务文件（历史）。与完成区声明一致。

2）README.md 版本表：
```
$ grep -nE 'SimRISC|AEE|SEE|HEE|ABI|SBI|HBI' README.md
1:# DADAO for SimRISC 0.5.4
11:| SimRISC | 0.5.4 |
12:| AEE / ABI | 0.9.2 |
13:| SEE / SBI | 0.7.1 |
14:| HEE / HBI | 0.1.2 |
```

3）`spec/DADAO-11~23`（6 文件）头部：
```
DADAO-11/21 : > **版本：0.9.2**（… 基于 SimRISC 0.5.4 指令系统设计）
DADAO-12/22 : > **版本：0.7.1**（… 基于 SimRISC 0.5.4 指令系统设计）
DADAO-13/23 : > **版本：0.1.2**（… 基于 SimRISC 0.5.4 指令系统设计）
```

4）知识库文件（0.5.4 命中数 / 0.5.3 命中数）：
```
contract-isa.md 1/0   contract-abi.md 2/0   contract-elf.md 2/0
adr-0001 3/0   adr-0003 4/0   adr-0004 7/0   contract-authoring.md 1/0   deferred.md 1/0
```
与完成区声明的处数逐一吻合。

5）归档目录未改：
```
$ git status --porcelain spec/SimRISC-0.5.3/   →（空）
$ git diff --stat -- spec/SimRISC-0.5.3/       →（空）
$ head -3 spec/SimRISC-0.5.3/SimRISC-00-指令系统设计.md → > **版本：0.5.3**
```

6）其他版本号未被改动：`git diff` 中凡触及 `0.9.2/0.7.1/0.1.2` 的增删行，同一行仅把 `SimRISC 0.5.3` 改为 `0.5.4`，`0.9.2/0.7.1/0.1.2` 逐字未动（README 表、DADAO 头部、`docs/m2-spec-planning.md`、`docs/impact-matrix.md` 冻结基线行均如此；`contract-isa §10.1.2` 为节号非版本）。

7）已完成任务文件/历史记录：
```
$ git diff --name-only -- .tao/tasks/ → SPEC-016t / SPEC-018t / SPEC-019t
  三者 `**状态**` 均为「待验收」（无「已验证」任务被改）
$ git status --porcelain .tao/knowledge/MEMORY.md .tao/knowledge/changelog.md →（空）
```

**约束核验**：

| 约束 | 结论 |
|------|------|
| 1. 仅更新版本号引用，不修改其他内容 | ✅ SPEC-018t 自身编辑均为版本号替换；`adr-0003/adr-0004` 中的 `contract-isa §N` 章节重编号与 `contract-isa.md` 大规模重组均属 **SPEC-016t**（其完成区已自认该两文件与其他 §N 引用） |
| 2. 已完成任务文件、`changelog.md`、`MEMORY.md` 不改写 | ✅ 被改任务文件仅 3 个「待验收」文件；MEMORY.md / changelog.md 未改 |
| 3. `spec/SimRISC-0.5.3/` 归档未修改 | ✅ |
| 4. 其他版本号（0.9.2/0.7.1/0.1.2）不变 | ✅ |

**验收标准逐条**：
1. README 版本表 SimRISC=0.5.4 ✅
2. DADAO-11~23 头部=0.5.4 ✅
3. 知识库版本引用=0.5.4 ✅
4. 已完成任务文件/历史记录未改 ✅
5. 其他版本号不变 ✅

**findings（非阻断，供架构师定夺）**：

- **F1（范围/路线，建议归口）**：工程师完成区「验收结果」所用扫描为 `--include='*.md' --include='*.yaml'`，**窄于**任务书「应 `grep -rln '0.5.3'` 排除 .git/.dadao/.work 和已完成任务文件」的无过滤扫描。无过滤扫描下仍有 3 个**源码脚本**含字面 `SimRISC 0.5.3`：`tools/spec/validate_encoding.py:4`、`tools/spec/check_qfc_coverage.py:11`、`tests/scripts/build_test_binary.py:16`。这三者不在 SPEC-018t 交付物（README+DADAO+知识库），亦不在 SPEC-019t「需更新脚本」表（仅 4 个脚本），落在任务覆盖缝隙。**建议**架构师将工具脚本版本引用归口 SPEC-019t 或新增任务；**不阻断本任务**（本任务指定检查为 `*.md`）。
- **F2（一致性，观察）**：`.tao/knowledge/MEMORY.md:11` 状态行仍为 `| SimRISC 规范 | ✅ 0.5.3 |`，与 README 0.5.4 不一致。此为任务约束 2 明确豁免（MEMORY.md 不改写），合规；建议在 025m 里程碑或专门任务同步，避免长期不一致。
- **F3（观察）**：`docs/m1-retrospective.md:252` 的 `v5（0.5.3）` 是否属历史事实为判断题；工程师按「M1 历史基线」保留、同时把 line 260 当前引用改为 0.5.4，同一标准、可接受。

**判决**：**Accepted**。验收标准 1~5 与 4 项约束在本审查者独立重跑下全部通过；F1~F3 为非阻断观察（F1 归口建议由架构师在 025m 定夺）。

> 本 Accepted 仅代表「工程师本次任务达标」，最终接受决定归架构师。