# m20-llvm-003: 允许 `.set` 定义的 Absolute 符号作指令立即数（ISS-430）

**模块**：llvm
**项目里程碑**：M20
**依赖**：`m20-llvm-001/002` 已合入；同改 `components/llvm-project`，须串行
**可并行分片**：否（单组件 AsmParser）
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（issues-left 分诊，2026-11-25）

`ISS-430`：`m14-llvm-005` 后，下面这种合法写法从「静默 0」变成报错：

```
.set VD, L1-L0
L0:
...
set.zw rb1, wp0, VD
L1:
```

`VD` 已由 `.set` 固化为 **Absolute** 符号（值可编码），但 AsmParser 仍按
「symbol difference ('A - B')」拒绝，诊断文案也不准确。禁止未解析的符号差是对的，
但不该连带拒绝已求值的 Absolute 符号。

## 目标

1. AsmParser 在指令立即数路径上对**已求值的 Absolute 符号**放行（`evaluateAsAbsolute`
   成功即可编码）；未解析的 `A - B`、未定义符号仍按原语义拒绝。
2. 诊断文案只在真的是未解析符号差时使用“symbol difference”；Absolute 符号失败时
   给出与值/宽度相关的诊断。
3. 新增 lit 正例/负例：`.set VD, L1-L0` + `set.zw ... VD` 编码正确；未定义/不可求值
   的符号差仍 rc≠0；不改变既有 `symdiff-imm-err.s` 中真正应拒绝的用例。

## 验收（逐条贴真实 rc）

1. 最小复现：修复前 `llvm-mc` rc≠0（记录原文）；修复后 rc=0，目标指令编码与手算
   （`VD` 的绝对值 + 字段布局）一致。
2. `symdiff-imm-err.s`/`symdiff-addr-err.s` 中未解析符号差的负例仍全部 rc≠0；
   新增正例通过。给出注入（把 Absolute 分支关掉 ⇒ 正例红；`cp`+md5 还原回绿）。
3. `make check-lit`、`check-instrinfo`、`check-patch-tree` 的 llvm 段 0 problem；
   `series` 数按实际（不得为过门控改数）。
4. 重建/安装按仓库纪律；记录 `llvm-mc` 安装根与构建树 md5 一致。证据落运行期证据
   目录内 `run.sh`；不写具体构建/临时路径。

## 约束

独立 `git worktree`（分支 = `m20-llvm-003`）；不提交 git；只改
`components/llvm-project/**`、对应 lit 与本任务书；不改 `spec/`、契约、`Makefile`。
当前 gem5 任务在独立源/构建树，LLVM 无活跃写者；不要碰 gem5。

## 完成区

**测试结果**：`make check-lit` 186/186 PASS（rc=0，含新增 2 条）；DADAO MC lit 93/93（rc=0）；`make check-instrinfo` 0 errors（rc=0）；证据脚本默认模式 `fails=0 skips=0`（rc=0）、`--inject` 模式 `fails=0 skips=1`（rc=0，check-lit 按设计跳过）。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp.patch`（重导出，源码 +26/−1 行，`series` 99 不变）；`components/llvm-project/changelog.md`（M20 一条）；`tests/unit/llvm/lit/MC/DADAO/set-abs-sym-ok.s`（新增）；`tests/unit/llvm/lit/MC/DADAO/set-abs-sym-err.s`（新增）；本任务书。
**验收结果**：
1. 复现与修复：任务书给的 `.set VD, L1-L0` + `set.zw rb1, wp0, VD` 在修复前已是 rc=0、编码 `0x4`（`m14-llvm-006` 已修 ABS48 路径，pre-fix 快照实测同此）；残留缺口在 PC 相对操作数——pre-fix 对 `.set VD` 作 `jump`/`br.z`/`ld.o [rb0,]` 操作数 rc=1 且 3 次报 “its value is a symbol difference”。修复后 rc=0，与同值字面量的 `.text` 逐字节相同（36 字节：`set.zw`=4e 04 00 08、ABS12=22 10 20 08、REL12=22 14 00 08、`jump`=70 00 00 02、`br.z`=72 04 00 02、负值=70 ff ff fe、带常量 equate=72 04 00 03），无 `R_DADAO` 重定位；`clang -c` 同结果。
2. 负例保持：`symdiff-imm-err.s`/`symdiff-addr-err.s` 仍 2/2 rc≠0 且含 symbol difference；新增负例 4/4：未定义 equate、跨段 equate 仍报 symbol difference（点名 `'UVD'`/`'XD'`），写出 `A - B` 仍拒，越界 equate 改为 `branch/jump target out of range for a 18-bit PC-relative immediate`（值/宽度诊断）。注入：还原两处改动 ⇒ `git diff` 非空、正例 lit rc=1 且汇编 rc=1（5 处 symbol difference）、负例 lit rc=1 且无 range 诊断；`cp`+md5 还原（md5 `18c52d49…` 相等、source clean）→ 重建后 llvm-mc md5 回 `93ee53c1…` → lit rc=0。
3. 门控：`check-patch-tree` llvm 段 99 patches、0 problem（整库 rc=1 = 24 条 gem5/musl 他任务漂移，llvm 0 条）；`--source-state` llvm OK（HEAD=178ca700a、count=1、clean）。
4. 重建/安装：`make install-host` rc=0；安装根与构建树 llvm-mc md5 同为 `93ee53c15b7cc0aa66ef2078583fa614`、llvm-objdump 同为 `90d9b3b8af7e39b1cbedb246f7973a7e`。证据：运行期证据目录内 `run.sh`（默认 / `--inject`）。
**新发现/坑**：
1. ISS-430 原文已由 `m14-llvm-006` 覆盖：ABS48 立即数路径用 `isa<MCSymbolRefExpr>` 放行 equate。残留同类缺陷在 `DADAOAsmBackend::evaluateFixup` 的 PC 相对判据：只看折后 `!AddSym`，无法区分「写出 `A - B`」与「单符号 equate」，故 jump/br/REL12 误报；本次补上同一判据（折后绝对常量按写出的值编码、不减 IP）。
2. `check_lit_bytes.py` 在本任务前即红：N=279 vs 独立计数 289，10 条 `@@ OBJ:` 行不被严格模式匹配（`ra.s` 2 条、`rf-group-range.s` 8 条，属 m20-llvm-001/002 的 `.dd.t32`/组范围行）。本任务新增 10 条全部匹配（279→289、289→299），缺口 10 不变，未在范围内修。
3. 写出二元式仍走旧判据：`jump [rb0, VD+4]` 仍报 symbol difference（与 `parseImmediate` 的 `isa<MCSymbolRefExpr>` 口径一致）；等价的 `.set VO, (L1-L0)+4` 单符号写法可编码。
**遗留问题**：① `check_lit_bytes.py` 的 10 条历史未匹配 OBJ 行（建议另立小任务扩展解析面或把非指令行移出扫描）；② `check-patch-tree` 整库 rc=1 为 gem5/musl 他任务 KNOWN-RED；③ 未跑 L2 `check-modules`（任务验收未要求）。

## 审阅记录

#### 第 1 轮 engineer 自审

**结论**：改动集中在 `DADAOAsmBackend::evaluateFixup`（1 处判据 + 1 个折后值分支）；所有 finding 已处置，状态可置「待验收」。

逐行审查要点（无 finding）：`IsEquatedValue` 仅在 `!Target.getAddSym()` 时参与判定，`Target.getSubSym()`（跨段/未解析）无条件先拒；地址 equate（`.set ADDR, L1`）不折、保留 AddSym，走原重定位/就地路径；折后 `!Add && !Sub` 分支只在 PC 相对类（PCRel_12/18/24、REL12）可达（ABS48/ABS12 在此前已返回），`Value = Target.getConstant()` 不减 IP，与数值字面量编码一致；`hasFinalLayout` 门不变。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `--inject` 首版用非 verbose lit 输出匹配诊断子串，lit 不打印 stderr ⇒ 假红（hits=0） | ✅已修 | lit 改 `-v`，并另跑一次汇编器直接断言 rc/子串 | `--inject` 二轮 `fails=0`：`inject_positive_lit_red` lit_rc=1/asm_rc=1/hits=5 |
| F2 折后值分支若 `hasFinalLayout` 为假时误吞「写出差」 | ✅已修（口径） | 分支内再判 `isa<MCSymbolRefExpr>`，否则 `nullopt` 交回默认路径 | 写入差负例 4/4 仍拒；`symdiff-addr-err.s` rc≠0 |
| F3 `jump [rb0, VD+4]`（写出二元式）仍按 symbol difference 拒绝 | ⏸保留（口径一致） | 不改；与 `parseImmediate` 的「单符号 vs 写出差」口径一致 | 记入「新发现 3」；等价的单符号 equate 已验证可编码 |
| F4 `check_lit_bytes.py` 基线即红 | ⏸延后（范围外） | 不改 | 基线 279/289 与现状 287/297 缺口同为 10，逐行未匹配集不变（10 条均在 m20-llvm-001/002 的 lit 内） |
| F5 预置 pre-fix 快照不可由干净检出复得 | ✅已做 | `--inject` 重建注入态时顺带留快照；缺快照时显式 SKIP 并打印原因 | 默认模式两次均 `skips=0`（快照已在） |
| F6 任务书原复现（`set.zw`）不能复现 rc≠0 | ✅已核（如实记录） | 不改代码；完成区写明 m14-llvm-006 已修，残留缺口在 PC 相对路径并给出 pre-fix 实测 | 完成区验收 1、新发现 1 |


#### 第 1 轮 reviewer 验收

**判决：Accepted**（5 条非阻断 finding 见末，交 architect 收尾处置）。

**重跑记录**（worktree 根、相对路径；证据 = 仓库根执行运行期证据目录内 `run.sh`）：
1. `bash 运行期证据目录内 run.sh` → rc=0，`SUMMARY: fails=0 skips=0` / `RESULT: PASS`，16 项全 rc=0：安装根==构建树 md5（llvm-mc `93ee53c1…`、llvm-objdump `90d9b3b8…`）、`issue_repro` rc=0 enc=0x4、pre-fix 快照对 ok.s rc=1 且 7 处 symbol difference、equate==字面量 `.text` 逐字节相同且 0 R_DADAO、负例 4/4、symdiff 2/2、DADAO MC lit 93/93（new=2）、`=== Result: 0 errors ===`、`check-patch-tree: llvm-project: 99 patch(es)` 且 llvm assertion 0、`make check-lit` 186/186。
2. 独立重跑：`make check-lit` rc=0 `Passed: 186 (100.00%)`；`make check-instrinfo` rc=0；`python3 tools/infra/check_patch_tree.py` llvm 段 0 problem（整库 rc=1 = 他任务 gem5/musl 漂移，与本任务无关）；`check-component-changelog`/`check-tests-index`/`check-dirs`/`check-no-residue`/`check-writer-guards`/`check-knowledge-refs` 全 rc=0。
3. 正例：`set-abs-sym-ok.s` rc=0，10 条 OBJ 字节逐条经 `contracts/opcodes.yaml` mask/value 独立校验 10/10 唯一命中；与同值字面量 `.text` 48B md5 相同、`llvm-readobj -r` 0 重定位、`clang -c` 同结果。
4. 负例：`set-abs-sym-err.s` rc=1，4 条诊断逐条命中（'UVD'/'XD' symbol difference、越界 `18-bit PC-relative immediate`、写出 `A - B` 拒）；`symdiff-imm-err.s`/`symdiff-addr-err.s` 各 rc=1；pre-fix 快照对越界 equate 误报 symbol difference、修后为值/宽度诊断 ⇒ 目标2 达成。
5. 判据一致性：`evaluateFixup` 的 `isa<MCSymbolRefExpr>(Fixup.getValue())` 与 `parseImmediate` 的 `!isa<MCSymbolRefExpr>(Expr)` 同口径；未放宽真 `A - B`——写出 `L1-L0` 在 jump/br/set.zw/ld.o[rb0,] 全 rc=1、`VD + 4` rc=1、跨段/未定义 equate rc=1（均与 pre-fix 相同）；地址/全局/弱/未定义 equate 与 pre-fix 逐字节 + 重定位数全 SAME。

**独立注入**（`cp` 备份 + md5 对账，全程未用 git checkout/restore）：equate 放行判据改恒 false → `make build-mc-lite` rc=0 → 正例 lit rc=1（1/1 Failed）、直接汇编 rc=1 且 7 处 symbol difference；负例 lit rc=1 且越界诊断退化为 symbol difference（range 命中 0）⇒ 可达 FAIL 成立 → `cp` 还原 + md5 相等（源树 clean）→ 重建 rc=0 → llvm-mc md5 回 `93ee53c1…` → 两 lit 回绿 → `run.sh` `fails=0`。另重跑 `run.sh --inject` → rc=0 `fails=0 skips=1`。

**约束核验**：分支 `m20-llvm-003` 未提交（`git log master..HEAD` 空）；变更集 5 项与完成区「修改文件」逐项一致（changelog、AsmBackend 补丁、两新 lit、本任务书），无越界、未碰 gem5、未改 spec/契约/Makefile；`series` 99 现场统计；新增内容「银行」0 处；**任务书订正已写清**（完成区验收1 + 新发现1：set.zw 复现 pre-fix 即 rc=0/enc `0x4`，残留缺口在 PC 相对操作数 —— 与我用 pre-fix 快照实测一致）。

**Finding（均非阻断，交 architect 收尾）**：F1 背景/目标段仍写旧前提，订正仅在完成区 ⇒ 补一行注记；F2 完成区「36 字节」与实测不符（ok.s `.text`=48B、`run.sh` 对照=44B；其仅列 7 编码+2 swym=36），「逐字节相同」本身成立 ⇒ 改数；F3 `check_lit_bytes` `N (289) != independent count (299)` 为基线红（HEAD 279≠289、未匹配 10 条逐行相同、本任务新增 10 条全匹配），遗留①未落 issue 号 ⇒ 补登记；F4 主仓 `check-patch-tree` llvm 段现 2 条 assertion = 未合入中间态（共享源树已含新补丁、主仓补丁仍旧，合入即消；主仓本就 gem5/musl 基线红）；F5 `check-temp-dirs` rc=1（他任务 5 个陈旧临时目录 + `/tmp` 占用 92.5%，mtime 均早于本任务；本任务运行期临时目录约 50 个手工探测残留待收尾清理）。
