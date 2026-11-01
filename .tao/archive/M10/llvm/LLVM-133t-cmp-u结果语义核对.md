# LLVM-133t: `cmp.{ut,uw,ub}` 结果语义核对与断言（ADR-0037）

**模块**：llvm
**项目里程碑**：M10
**依赖**：SPEC-173t（语义）、QEMU-074t（实现）
**状态**：已验证

## 执行环境
**执行环境**：本地（仅在需要改代码时重建）

## 接口规范

### 背景（ADR-0037）
- `DADAOCodeGen.td` 的 `DADAOCmpU` pattern 注释已写「result is still the i64 {-1,0,1} value consumed by `br.*`/`cs.*`」——即后端**已假设** -1 = 全 1。
- 新语义与之一致 ⇒ 预计**无需改代码**；本册做核对 + 断言，防未来回退。

### 输出
1. 核对 `cmp_ut/cmp_uw/cmp_ub` 的所有使用点（pattern、`DADAOCmpU` 降级、`br.n`/`cs.*` 选择）确实按 i64 -1/0/1 消费；若发现按零扩展假设的代码，修正并说明。
2. 新增/加强 lit（或等价脚本）断言：`cmp.ut` 后接有符号分支时选择 `br.n`（不是 `br.nz`/`br.eq` 等），并钉住 `cmp.ut` 指令选择。
3. 不改 ISA/编码；不改 QEMU/spec。

### 约束
- 若只需加测试，**不重建**；若改代码，按长任务规则由主会话重建。
- 断言须有可达 FAIL（注入错误选择或错误 pattern）。

## 验收标准
1. 核对结论（逐使用点，含文件/行）。
2. 新断言在 `check-lit` / L2 中通过；反例注入 ⇒ 红 ⇒ 还原 ⇒ 绿。
3. L1 / L2 绿。
4. 完成区贴真实输出与退出码。

## 完成区

**核对结论**（`DADAOCmpU` 及其结果的**全部**消费点；行号 = 组件源树 `llvm/lib/Target/DADAO/`；各点均按 i64 {-1,0,1} 读 bit63，与 ADR-0037 D1 一致 ⇒ **无需改代码**）：
1. **节点 / 产出**：`DADAOCodeGen.td:113`（SDNode，结果恒 i64）；`DADAOISelLowering.cpp:2369`（LowerBR_CC）、`:2712`（LowerCmpSelect ← LowerSETCC/LowerSELECT_CC）；`DADAOISelDAGToDAG.cpp:778`（指针 bank → `cmp.uo`）。
2. **指令选择**：`DADAOCodeGen.td:833/835`（i64 → cmp.uo / cmp.ui）、`:848/850/852`（i32/16/8 → cmp.ut/uw/ub）；`DADAOInstrInfo.td` 的 `cmp_{ut,uw,ub,uo,ui}` 只定编码，无结果语义假设。
3. **消费（判据 = bit63）**：`DADAOCodeGen.td:856-861`（br.n/nn/z/nz/p/np）、`:871-873`（cs.n/z/p）；`DADAOISelLowering.cpp:2484-2541`（窄：ULT→BRN、ULE→BRNP、UGT→BRP、UGE→BRNN）、`:2573-2596`（i64 同映射）、`:2726-2743`（SETCC/SELECT_CC：ULT→CS_N、ULE→CS_P、UGT→CS_P、UGE→CS_N）；ISA 判据 `contract-isa.md §8.4`（`br.n` = `rdha < 0`）、`§6.5`（`cs.n`/`cs.p`）。
4. **唯一零扩展假设**：`DADAOISelLowering.cpp:2533-2541`、`:2714-2721` 的 `SIGN_EXTEND_INREG`（窄无符号 cmp 后补 `ext.so`）。ADR-0037 后对 {-1,0,1} 是恒等变换 ⇒ **语义正确、生成码不变**；仅注释仍称 “zero-extended” 且多一条 `ext.so`（见遗留 1）。

**测试结果**：新增 lit 8 例全 PASS；`narrow-int.ll` 仍 PASS；L1 `make check` rc=0；L2 `make check-lit` rc=0（151/151）；证据脚本 23 checks / 0 failed。
**修改文件**：`tests/llvm/lit/CodeGen/DADAO/cmp-u-branch.ll`（新增）；`tests/llvm/lit/CodeGen/DADAO/narrow-int.ll`（仅注释）；`tests/…` 之外：`.tao/knowledge/milestones.md`（仅 `LLVM-133t` 行状态 `待开始`→`待验收`，L1 `check-milestones-fresh` 强制表↔任务书一致）；`.work/evidence/LLVM-133t/`（`run.sh` + `mutate_text.py`，证据，未跟踪）。
**验收结果**：
- `make -s check` → 尾行 `repository checks (L1): PASS`，rc=0
- `make -s check-lit` → `Passed: 151 (100.00%)`，rc=0（日志含 `PASS: DADAO-CodeGen :: cmp-u-branch.ll`；序号随并行完成顺序波动，不作判据）
- `.work/evidence/LLVM-133t/run.sh` → `LLVM-133t evidence: PASS (23 checks, 0 failed)`，rc=0：10 项注入（cmp.ut→cmp.st、br.n→br.nz、br.nn→br.nz、cmp.uw→cmp.ut、cmp.ub→cmp.uw、cmp.uo→cmp.ut、cs.n→cs.z、插入杂散 cmp.uo、插入杂散 br.n、IR 改有符号比较）全部“预期红”；仓库文件往返注入 md5 对账一致、还原后 lit 回绿。
**新发现/坑**：① FileCheck 子串匹配：`br.n` 会命中 `br.nn` 前缀 ⇒ 区分极性须写 `br.n {rd`。② `CHECK-NOT` 只覆盖相邻两条正检查之间：极性 NOT 放在 `br.nn` 之后会漏掉 cmp 与 br 之间插入的错误分支（本次注入自检首轮即漏检）。③ “只加测试”任务若真改 .td/.cpp 做注入需重建 ⇒ 改为在 llc 输出副本注入 + 把 IR 改成有符号比较（等价“错 pattern”），既可达 FAIL 又不动编译输入。
**遗留问题**：1) 后端两处 `SIGN_EXTEND_INREG` 在 ADR-0037 后冗余（多一条 `ext.so`）、注释（`DADAOISelLowering.cpp:2533-2537`、`:2714-2717`）仍称 .u* 零扩展 ⇒ 建议后续小任务删冗余并改注释，需改 .cpp + 重建 llc（本任务约束“不重建”，未做；新 lit 有意不断言 `ext.so`，删除后仍绿）。2) `docs/DDLN/README.md` 开工前即有未提交改动（非本任务），未触碰。3) 未做真·后端源码注入（需重建）；注入覆盖面见上。

## 审阅记录

#### 第 1 轮 engineer 自审

**逐行审查范围**：`tests/llvm/lit/CodeGen/DADAO/cmp-u-branch.ll`（新增 8 例）、`tests/llvm/lit/CodeGen/DADAO/narrow-int.ll`（注释）、`.work/evidence/LLVM-133t/{run.sh,mutate_text.py}`。后端源码**未改**，仅做只读核对（结论见完成区 1–4）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `run.sh` 中 `local name=$1 … out="…$name…"` 同一 `local` 语句内引用未赋值变量，`set -u` 下 `unbound variable`，脚本在首个注入处崩 | ✅已修 | 拆成两条 `local`（先赋值、再拼路径） | 重跑 `run.sh` → `PASS (23 checks, 0 failed)` rc=0 |
| F2 往返注入用 IR 块作用域定位 `; CHECK:` 行 ⇒ 命中失败（CHECK 注释在 `define` 之前，不在块内），注入“未生效” | ✅已修 | `mutate_text.py` 增 `--occurrence N`（全文件第 N 次命中，绕过块作用域）；往返注入改用它 | `roundtrip-inject:red` PASS + `roundtrip-restore` md5 一致 |
| F3 `narrow-int.ll` 新注释把比较小节写成 `§10.4.1/§11.4.1/§12.4.1`（实为**移位**小节） | ✅已修 | 改为 `§10.2/§11.2/§12.2`（`contract-isa.md` 比较小节，已核行 953/1030/1107） | 脚本 `lit-narrow-int` PASS；`contract-isa.md` grep 核对 |
| F4 `ult32_brnn` 的极性 `CHECK-NOT: br.n {` 放在 `br.nn` 正检查**之后** ⇒ 恒真（注入在 cmp 与 br 之间插 `br.n` 时未红） | ✅已修 | 把该 NOT 移到 `CHECK: cmp.ut` 与 `CHECK: br.nn` 之间（附注释说明理由） | 注入 `stray-brn` → `CHECK-NOT: excluded string found` rc=1（首次修复前为“恒真漏检”） |
| F5 头注释称零扩展“使 `cmp.ut`+`br.n` 走错边”过度归因：后端本有 `ext.so` 补偿，生成码一直正确 | ✅已修 | 改述为“旧口径会走错边 ⇒ 后端以 `ext.so` 补偿；ADR-0037 后该补偿为恒等操作，指令序列不变” | 对比改前/改后 llc 输出（仅 `.file` 行不同）+ 人工复核 |
| F6 防造假 / 可达 FAIL 自查 | ✅已确认 | — | 每条 PASS 均取**命令自身** rc（`; rc=$?`，无 `tee` 吞码）；9 类注入逐条“预期红”，`repo-md5-unchanged` 证明注入全程未污染仓库 |

**判决**：finding 全部处置完毕（无延后 / 不修），状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**（reviewer 独立执行，日志 `.work/log/llvm/LLVM-133t-reviewer-{l1,l2-lit,evidence}.log`）：
- `make -s check` → 尾行 `repository checks (L1): PASS`，rc=0。
- `make -s check-lit` → `Passed: 151 (100.00%)`，rc=0；含 `PASS: DADAO-CodeGen :: cmp-u-branch.ll`（我方显示 41 of 151，完成区写 57 of 151——lit 并行完成序号，非门控判据，见 finding L）。
- `bash .work/evidence/LLVM-133t/run.sh` → `PASS (23 checks, 0 failed)`，rc=0，与完成区逐项一致。
- 手工抽查（独立最小 IR `/tmp/opencode/LLVM-133t-review/spot.ll`，llc rc=0）：ult i32→`cmp.ut`+`br.n`；i16→`cmp.uw`+`br.n`；i8→`cmp.ub`+`br.n`；slt i32→`cmp.st`+`br.n`。

**脚本审核**：`run.sh` 每条注入先验「生效且非空」（`cmp -s` 守卫），rc 均取被检命令自身（无 `tee` 吞码）；10 项注入逐条有可达 FAIL 路径（9 asm 变异 + IR 有符号化），往返注入为真实仓库文件 cp+md5 还原（trap 兜底）。23 checks 计数与现场吻合。

**独立反例**（禁 git checkout/restore，全部 cp+md5）：
1. 仓库测试文件首条 `CHECK: br.n`→`br.nz` ⇒ lit FAIL rc=1（`:37 CHECK expected string not found`）⇒ cp 还原 ⇒ md5=7c904660…（与注入前一致）⇒ lit PASS rc=0。
2. CHECK-NOT 约束力（独立于 run.sh）：llc 输出副本在 `ult32_brnn` 的 `br.nn` 前插杂散 `br.n` ⇒ FileCheck rc=1 `:57 CHECK-NOT: excluded string found`；在 `ult32_brn` 的 `br.n` 前插杂散 `cmp.uo` ⇒ rc=1 `:36 CHECK-NOT excluded`。非恒真。
3. IR 首条 `icmp ult i32`→`slt`（/tmp 副本）⇒ llc+FileCheck rc=1 `:32 CHECK expected string not found`。

**约束核验**：① 零代码改动属实——`git diff master` 不含 `components/llvm-project/**`（grep 计数 0），组件源树 `.work/source/llvm-project` `git status` 干净；与核对结论（消费点按 i64 -1/0/1 读 bit63）一致。② 使用点行号抽核通过：`DADAOCodeGen.td:113/833-835/848-852/856-861/871-873`、`DADAOISelLowering.cpp:2533-2541`（SIGN_EXTEND_INREG，注释仍称 zero-extends ⇒ 遗留 1 属实）、`:2726-2743`（ULT→CS_N/UGE→CS_N、ULE/UGT→CS_P）、`contract-isa.md:830`（`br.n` = rdha<0）。③ `narrow-int.ll` diff 仅两处注释，CHECK 行未动。④ `milestones.md` 仅 LLVM-133t 一行 待开始→待验收。⑤ `docs/DDLN/README.md`（用户改动）验收前后 md5=dea6daa2… 未触碰。

**快照对账**：验收前后 `git status --porcelain -uall` 逐行 diff rc=0；5 个目标文件 md5 前后全等（rc=0）；完成区「修改文件」声明与实际 diff 一致（任务书本身由 architect 的 WIP 提交带入，非 engineer 越界）。

**finding**：L（非阻塞，文档级）——完成区引用的 lit 输出行号 `(57 of 151)` 与我方重跑 `(41 of 151)` 不同，系 lit 并行完成序号波动；`Passed: 151` 与 PASS 事实一致，交 architect 收尾时顺手改。

**判决**：**Accepted**（验收命令块全绿、反例可达 FAIL 且还原回绿、约束零违反、快照对账干净）。
