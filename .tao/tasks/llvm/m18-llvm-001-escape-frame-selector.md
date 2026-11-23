# m18-llvm-001: escape frame selector 的 LLVM 汇编/反汇编支持

**模块**：llvm
**项目里程碑**：M18
**依赖**：`m18-spec-003`（`SimRISC-11`/Toolchain-01/contract-asm 的编码真源）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为编码/汇编器/反汇编器 + lit，取 1.5–2× 中位）
**档位**：中改（工具链编码）
**状态**：已验证
**执行环境**：本地（`build-mc`；lit）

## 背景

`m18-spec-002/003` 给 `escape` 增加 **frame selector bit1**：

- `imms18` bit1：0=cg5，1=cg9；
- 合法 `imms18 ∈ {0,1,2}`（cg5 偏移 0/+4、cg9 偏移 0），`3 ⇒ ILLI`；
- 汇编层 `imms20 ∈ {0,4,8}`（8=cg9 偏移 0）；
- `imms18[17:2]` SBZ。

LLVM 侧目前只接受/生成 `imms20 ∈ {0,4}`，需要同步，否则内核/探针无法汇编 `escape ..., 8`。

## 目标

1. **汇编器**：`escape cfxha, [excp_cause_ip, <imm>]` 接受 `imm ∈ {0,4,8}`；`8` 编码为 `imms18=2`（bit1=1、bit0=0）；拒绝其它值并给出诊断；`imms18[17:2]` 非零的诊断/编码规则与 spec 一致。
2. **反汇编器**：把 `imms18` bit1 解回 frame selector；输出可区分 cg5/cg9（助记符/注释/操作数形式由 spec-003 的汇编语法定，遵循 Toolchain-01）。
3. **测试**：`tests/unit/llvm/lit/MC/DADAO` 增 `escape` 的 0/4/8 正向、非法值负向、bit1 编解码往返；必要时 `check-codegen` 补一条最小程序。
4. **补丁/文档**：`components/llvm/patches/**` 经 `make_patch.py llvm` 重导；`components/llvm/changelog.md` 记录；不改 `spec/`/contracts。

## 验收（逐条贴真实 rc）

1. `make build-mc` rc=0；`llvm-mc` 手测 `escape ..., 0/4/8` 编码与 `llvm-objdump` 反汇编往返正确；非法值（1/2/3/5/6/7…）报错。
2. 新增 lit 用例全绿；`make check-lit`（或 `check-lit-full`）rc=0；`check-unit` 与基线逐行相同。
3. **可达 FAIL ≥1 路**：回退编码（只允许 0/4）⇒ 新增 `8` 用例红；`cp`+md5 还原后回绿。
4. `check-patch-tree` llvm 段 0 problem；`check-component-changelog` rc=0；`make check` 与基线逐行相同。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/llvm/patches/**`、`components/llvm/changelog.md`、`tests/unit/llvm/**`、本任务书。不改 `spec/`、`.tao/contracts/`、`Makefile`、QEMU/RTL/gem5/内核。
3. 组件补丁经 `make_patch.py llvm` 重导；不改版本号；术语「bank = 寄存器组」。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
5. 期望值以 `SimRISC-11`/`Toolchain-01`/`contract-asm` 为准，不从现有实现反推。

## 待裁定

无（若 spec-003 的汇编语法/操作数形式有歧义，停下写「待裁定」）。

## 完成区

**测试结果**：证据脚本 26/26 rc=0；`--inject` 6/6 rc=0（回退只允许 0/4 ⇒ `8` 汇编 rc=1、`cfx2-escape-frame.s` lit rc=1；`cp`+md5 `cdec6b5c…` 一致 → 重建回绿）。`make check-lit` 182/182 rc=0（基线 180/180，+2 新例）。`check-case-ledger` PASS（+9 行）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/{AsmParser/DADAOAsmParser.cpp,MCTargetDesc/DADAOMCInstPrinter.cpp}.patch`（0/4 → 0/4/8 + 诊断；printer 仅注释说明 bit1）；`components/llvm-project/changelog.md`（M18 条）；`tests/unit/llvm/lit/MC/DADAO/cfx2-escape-frame.s`（新，11 向量）；`cfx2-escape-frame-err.s`（新，12 反例）；`cfx2-trap-escape{,-err}.s`（`8` 转正向、诊断串）；`validate_cfx_vectors.py`（合法集 `{0,4,8}`）；`tests/case-ledger.tsv`（**越界**：门控要求的生成物，+9 行）；证据 = 运行期证据目录 `run.sh`。
**验收结果**：`make build-mc` rc=0。手测 cfx_hart/cfx_smon 的 0/4/8 ⇒ `7e3c0000/01/02`、`7e080000/01/02`，`llvm-objdump` 回显 `[excp_cause_ip, 0/4/8]`；1/2/3/5/6/7/12/16/-4/524288 全 rc=1 且诊断含 `must be 0, 4 or 8`；`obj→asm→obj` 字节相同。`check-patch-tree` llvm-project 段 **0 problem**（整体 rc=1 仅因并行会话的 musl/chipyard/gem5/linux 源树漂移 25 problem，基线同）。
**新发现/坑**：①反汇编零代码改动：printer 的 `imms18 << 2` 天然把 cg5 印 0/4、cg9 印 8（Toolchain-01 §5 规范长形），只需补注释；②`cfxha=5` 的标量名是 `cfx_cache`（首轮 lit 因写 `cfx5` 红）——反汇编名字取自 `contracts/cfx-aliases.txt`，写向量前必查；③每条 `@@ OBJ:` 都是 case-ledger 身份行，新增 lit 必须 `check_case_ledger.py --write`（生成物，不手写）；④`check-unit` 基线红：`test-codegen` 0/19（`raw single-TU object is not fully resolved: SHT_RELA present`），与本任务无关。
**遗留问题**：`make -k check` 余 6 个**基线红**（均非本任务改动）：`check-patch-tree`（25 foreign）、`check-component-changelog`（chipyard 节序 M16,13,14,16）、`check-musl-freshness`、`check-milestones-fresh`（R1：m18-llvm-001/m18-idl-001 台账仍在「待开始」+ spec-003 次序；须主会话改台账）、`check-run-artifacts`（582 foreign log 名）、`check-temp-dirs`（5 个 foreign 陈旧目录）。`check-codegen` 最小程序**不适用**：escape 无 CodeGen/IR 路径（`Pattern = []`，ciii 仅 MC 层），未加。

## 审阅记录

### 第 1 轮 engineer 自审

**逐行审查**（改动源 = `.work/source/llvm-project` 提交 `983529614` 的 2 文件）：
- 校验式 `Bytes != 0 && Bytes != 4 && Bytes != 8`：顺序正确（常量/表达式判定在前，`%4` 不再放行 12/16）；`-4` 与 `524288` 均被他分支拒绝，实测 rc=1。
- `imms18` 上界：汇编层只可能得到 {0,1,2}，`3` 与 `[17:2]≠0` 不可生成 ⇒ 与 SimRISC-11 §3 的 ILLI 编码不冲突；未在汇编器加 `cfxha==15` 判据（那是运行期 CFXESC，MC 层只管语法，符合 Toolchain-01）。
- printer：仅注释，输出路径未变（`imms18 << 2`）；`7e3c0002 → 8` 回读验证。
- 测试：oracle（独立派生自 `contracts/opcodes.yaml`）32 条 0 错误；负向 12 条全可达 FAIL；无恒真断言。
- 证据脚本：默认/注入两模式各条目有独立失败路径；注入后 `git diff --name-only` 非空（1 文件）；还原用 `cp`+md5 对账（`cdec6b5c…` 前后一致），未用 `git checkout/restore/stash`。

**finding 与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 新 lit 文件使 `check-case-ledger` 红（9 行缺失） | ✅已修 | `python3 tools/infra/check_case_ledger.py --write`（生成物 `tests/case-ledger.tsv`，+9 行；越界已披露） | `check-case-ledger` PASS |
| F2 证据脚本 `local name=$1 asm=$2 exp=$3` 两实参触发 `set -u` unbound | ✅已修 | 去掉未用 `name=$1`，改 `local asm=$1 exp=$2` | 重跑 default 26/26 rc=0 |
| F3 注入模式打印 `expected=rc!=0 / actual=rc=0` 易误读为假绿 | ✅已修 | 改为「mutation caught」分支显式 `ok/bad` + 原始 rc | `--inject` 6/6 rc=0（`actual=rc=1`） |
| F4 首轮向量误写 `escape cfx5`（反汇编名 `cfx_cache`） | ✅已修 | 改用 `escape cfx_cache` | MC lit 89/89 rc=0 |

**判决**：无未修 finding；状态 → `待验收`。


### 第 1 轮 reviewer 验收

**重跑记录**（任务 worktree 根、相对路径，全部为本人终端输出；证据脚本 = 运行期证据目录内 `run.sh`）：
- 手测 `llvm-mc -show-encoding`：`escape cfx_hart/smon,[excp_cause_ip,0/4/8]` ⇒ `7e3c0000/01/02`、`7e080000/01/02`（imms18 ∈ {0,1,2}）；`llvm-objdump` 回显 `[excp_cause_ip,0/4/8]`，cg5/cg9 可区分；`obj→asm→obj` `cmp` rc=0（两对象 md5 同 `fd5bc468…`）。
- 拒绝：1/2/3/5/6/7/12/16/-4/524288 全 rc=1 且含 `must be 0, 4 or 8`；`sym` rc=1 `must be a constant`；`[rb0,8]` rc=1 `base must be 'excp_cause_ip'`。
- `run.sh`：**26 passed / 0 failed，rc=0**；`run.sh --inject`：**6 passed / 0 failed，rc=0**（回退只允许 0/4 ⇒ 8 被拒、正向 lit rc=1；还原后源文件 md5 `cdec6b5c…` 前后一致、源树 0 残留、重建回绿）。
- `make build-mc` rc=0；`make check-lit` **182/182 rc=0**（新增 `cfx2-escape-frame{,-err}.s` 均在列）；`check-case-ledger` PASS（现场 5701 条，+9）；复跑 `check_case_ledger.py --write` 后 tsv md5 **不变** ⇒ ledger 确为工具重算、非手写。
- `check_patch_tree.py`：llvm-project 段 **0 assertion**（整体 24 problem 全 foreign：gem5/chipyard/linux/musl；基线 28，含本任务修复的 4 条 llvm）。
- `make -k check` rc=2，与基线 rc=2 同；结论行 diff 仅 3 类（llvm 4 条消失、28→24、ledger 5692→5701），`check-*: PASS/FAIL` 集合逐项相同，无新增红。
- `make test-codegen` 0/19（与完成区所述基线红一致）；`escape_ciii` 定义 `Pattern = []` ⇒ CodeGen 不适用成立。`make_patch.py llvm-project`：**0 written, 99 unchanged** rc=0。
- **reviewer 自设注入**（清编码 bit1：`Bytes >> 2` → `(Bytes >> 2) & 1`）⇒ 同一 `run.sh` **rc=1、5 FAIL**（encode/disasm/lit/patch-tree 段）；`cp`+md5 还原 + 重建 ⇒ **26/26 回绿**、`llvm-mc` md5 与注入前一致。（坑：`cp -p` 保留 mtime 会令 `build-mc` 不重建 ⇒ 还原后必须 `touch` 并核二进制 md5。）

**约束核验**：`git diff --name-status master...HEAD` = 10 路径，与完成区逐条一致；无 `spec/`、`.tao/contracts/`、`Makefile`、QEMU/RTL/gem5/内核改动；补丁经 `make_patch.py` 重导（0 written/99 unchanged）；还原只用 `cp`+md5（无 checkout/restore/stash）；期望值派生自 `SimRISC-11`/`Toolchain-01`/契约，oracle 独立于 llvm-mc（32 条 0 错误、合法集 `{0,4,8}`）；完成区 9 行 ≤30；状态 `待验收`；本任务 worktree 前后 `git status` 快照逐行相同、0 残留。

**findings（均非阻断，交 architect 收尾处置）**：
- R1 验收 3 的「`cfx2-trap-escape{,-err}.s` 的 8 正向」只达成一半：`-err.s` 已删 8 负向、诊断串改 `0, 4 or 8`，但 `cfx2-trap-escape.s` 无 8 正向行（仅 0/4）；8 正向全由新增 `cfx2-escape-frame.s` 承担。是否补一行由 architect 定。
- R2 完成区「基线 180/180」与实测不符：基线 lit 在当前共享构建下 179/180 rc=2（`cfx2-trap-escape-err.s` 因 8 转正向而红）。
- R3 完成区「check-patch-tree 25 problem」本人实测 24（基线 28），foreign 计数时变/笔误。
- R4 证据脚本 ROOT 取自调用 cwd（运行期目录为指向主仓的符号链接）：以绝对路径在主仓执行会因新 lit 不在 master 而红，须在任务 worktree 以相对路径执行。
- R5 审查期间主仓工作树出现并行会话 14 行改动（chipyard m16-chipyard-021），与本任务无关，已披露。

**判决：Accepted**（验收命令块在本人重跑下全部通过、硬约束无违反；engineer 完成区数字叙述见 R1–R3）。
