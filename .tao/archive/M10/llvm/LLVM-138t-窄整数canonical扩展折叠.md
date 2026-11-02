# LLVM-138t: 窄整数 canonical extension 折叠

**模块**：llvm
**项目里程碑**：M10
**依赖**：LLVM-137t
**状态**：已验证

## 背景
窄整数（i8/i16/i32）指令可按符号/无符号方向把结果 canonical 扩展到 64 位。当生产者与显式 `sext`/`zext` 方向完全一致时，可直接选 `.st/.ut/.sw/.uw/...` 变体，省掉随后的 `ext.so/ext.uo`。PR 提供 39 组 pattern，但基线和 shift-amount 类型需要核实。

## 目标
1. 在 `DADAOCodeGen.td` 增补精确 pattern：i8/i16/i32 × add/sub/mul/udiv/urem/sdiv/srem × shl/srl/sra，仅方向一致组合；方向不匹配保留 `ext.so/ext.uo`。
2. 核实 shift pattern 的移位量类型（IR 中窄 shift 的 amount 与 value 同宽，PR 写成 `i64 GPRD` 需证明 legalize 后成立）；不成立则改为正确类型或删掉该组。
3. 保留 `sub 0, x`（narrow-neg）既有处理；不改变 LLVM-134t 的 ext 清理口径。
4. 负例：`zext(ashr)`、`sext(lshr)`、`ptrtoint`/`inttoptr`、nsw/nuw、i8/i16 边界、div/rem；每类至少一组。
5. QEMU 运行期 oracle：独立 Python 派生期望，覆盖 39 组代表 + 方向不匹配；不能只看 `CHECK-NOT: ext`。

## 验收
- 新增/重放 lit 全绿；完整 `check-lit` 不回归（现场统计）。
- QEMU 结果与独立 oracle 一致；方向不匹配仍保留 ext。
- `make check`/`check-patch-tree` rc=0；证据 `.work/evidence/<任务号>/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/LLVM-138t/`。

## 约束
- 只改窄整数 extension 折叠与测试；不碰 i64 移位/code model/tailjmp/指针 PHI。
- 不改 ABI/调用约定；不改 spec/contracts/QEMU。
- **不提交、不 push**；重建申报；全量/夜跑未授权时不跑。

## 完成区

**状态**：已验证

### 修改文件
- `components/.../{DADAOCodeGen.td,DADAOISelDAGToDAG.cpp}.patch`（`make_patch.py` 增量导出：39 条 Pat + extend 根部 narrow `sub 0,x` 特例）
- `.work/source/llvm-project/...`（base+1 单 commit、干净；两份源文件已入上述补丁）
- `tests/unit/llvm/lit/CodeGen/DADAO/m10-narrow-extend.ll`（新：39 正例 + 方向/nsw/nuw/i8-i16 边界/ptrtoint/负例）
- `tests/unit/llvm/codegen/m10-narrow-extend.ll` + `expected.yaml`（新运行期向量，16 组边界组合）
- `tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（`gen_isa_coverage.py` 重生成：isel-cpp 59→64、pat 254→293、yes 193→202）
- `.tao/knowledge/milestones.md`（状态行）

### 测试结果
通过 15/15（证据脚本）；`make check-lit` **156 passed / 0 failed**（基线 155 + 本册 1，现场统计）；`run_codegen_e2e` 17/17（含新向量）；独立 QEMU oracle **84/84**（39 组合 × 2 值对 + 6 方向不匹配/非目标生产者）；`make check` rc=0；`check-patch-tree` rc=0；`check-isa-coverage` rc=0。

### 验收命令与结果
- `bash .work/evidence/LLVM-138t/run.sh` → `evidence: 15 passed, 0 failed` rc=0；含 I1/I3 注入→FAIL、`cp`+md5 还原→PASS（I2/I4）
- 构建：`make build-mc JOBS=8` rc=0（约 8 min）；`make install-host` rc=0；`make build-musl-shared JOBS=8` rc=0（刷新 freshness stamp）
- 安装根 llc == 构建树 llc（md5 `bce992b3...`）；反汇编核对 `add.ut/sub.uw/mul.ub/shl.b/shr.st` 与 `ext` 缺失，方向不匹配仍 `ext.so/ext.uo`
- shift 量类型核实：目标指针 64 位 ⇒ `getShiftAmountTy`=i64（`narrow-int.ll` 既有注释同口径），39 组中 9 条 shift 的 `(i64 GPRD:$b)` 成立；运行期 9 组变量移位 84/84 通过
- 补丁增量：`git diff components` 仅 2 文件，无 `GPRBTC/tailjmp/ExternalSymbol/selectCodeModel/CM.value_or`

### 新发现/坑
- `sub i16 %a, -32768` 被 LLVM 规范化为 `add.uw`（窄常量减法改加法），lit 边界负例须用寄存器操作数；边界语义由运行期向量承担
- 39 条 Pat 使 9 个此前无引用的 `.u*` 窄指令进入「ISel 用得上」，矩阵 yes/pat/isel-cpp 计数必须现场重生成，不得手写
- `sub 0,x` 在 zext 下也走 `sub.s*+ext.uo`（两指令）而非 `sub.u*`，是既有 neg 口径的有意保留

### 遗留
- 未跑 `check-full`/夜跑（未授权）；未提交、未 push（提交权归 architect）

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：39 条 Pat、ISel extend 分支、两份新测试、oracle/run.sh、矩阵 diff、任务/里程碑行。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| shift 组照抄 PR 的 `i64 GPRD` 可能不成立 | ✅已核实成立 | 不改；补注释与证据 | `narrow-int.ll` 既有 i32 变量移位用 i64 量；oracle 9 组 shift 全过 |
| 边界负例 `sub i16 %a,-32768` 实为 `add.uw` | ✅已修 | 改双寄存器 `zext_sub16_edge` | lit `sub.uw` CHECK 通过；边界值转运行期向量 |
| oracle 生成 IR 用 `srl/sra` 导致 llc 报错 | ✅已修 | `IR_OP` 映射 `lshr/ashr`；运行期向量重生成 | oracle 84/84；e2e 17/17 |
| oracle 缺 `and` 语义（负例） | ✅已修 | `narrow()` 增 `and` | 84/84 |
| ISel 特例会否打乱 m6-not-neg | ✅已确认 | 特例仅截 narrow `sub 0,x` | `m6-not-neg.ll`/`narrow-int.ll`/`abi-narrow-extend.ll` FileCheck rc=0 |
| 39 Pat 是否误碰 134t ext 清理 | ✅已确认 | 未改 cmp/ext 选择口径 | `cmp-u-branch.ll` 含于 156/156 |
| `make check` C8 首跑红（milestone 登记注） | ✅已修 | 待验收行恢复登记时间+注 | `check_milestones_fresh` PASS；证据 15/15 |

**判决**：无未修 finding ⇒ 可标 `待验收`。

### 第 1 轮 reviewer 验收

**审前快照**：`git status -uall` 0 行；lit/codegen/两补丁/matrix md5 记录。
**diff 核验**：`git show --stat 534f3546` = 9 文件，与完成区声明逐一对齐；components 仅 `DADAOCodeGen.td.patch`（+46 行：39 Pat + 注释）+ `DADAOISelDAGToDAG.cpp.patch`（+34 行：extend 根 narrow `sub 0,x` 特例）；grep `GPRBTC|tailjmp|ExternalSymbol|selectCodeModel|CM.value_or` 全 diff 无命中；`^-` 行仅补丁头（无删除=无 137/139 回退）。

**重跑（`bash .work/evidence/LLVM-138t/run.sh`，我方原始输出）**：
```
C1..C11 全 PASS；C5 make check-lit passed=156 failed=0 rc=0（现场统计）
C6 oracle: 84/84 passed；C7 run_codegen_e2e 17/17（m10-narrow-extend PASS）
C8 make check rc=0；C9 check-patch-tree rc=0；C11 check-isa-coverage rc=0
C10 构建树 llc == 安装根 llc（md5 bce992b3...）
I1 注入错 lit 期望 → rc=1；I2 cp+md5 还原 → md5 equal、rc=0
I3 注入运行期常量 → rc=1（case FAIL）；I4 还原 → md5 equal、rc=0
evidence: 15 passed, 0 failed；RUNSH_EXIT=0
```

**独立反例（reviewer 自做，注入点不同于 engineer）**：
- lit：`sed '32s/add.ut/add.st/'`（zext 期望错方向）→ `llvm-lit -q` rc=1 Failed 1/1；`cp -p` 还原 → md5 equal、rc=0。
- oracle：`oracle.py --inject`（翻转首期望值）→ `oracle: 83/84` rc=1，FAIL 可达。

**独立重算**：自写脚本解析 `m10-narrow-extend.ll` 16 组，按 LLVM IR 语义独立推导期望常量 → `16/16 constants match` rc=0。

**约束核验**：spec/contracts/QEMU 0 改动（C3）；未提交/push；临时物仅 `/tmp/opencode/LLVM-138t/`；审后 `git status -uall` 0 行、目标文件 md5 与审前一致。语义：39 组方向一致折叠、方向不匹配保留 `ext.so/ext.uo`、narrow-neg 保留 `sub.s*+ext.*`、nsw/nuw/i8-i16 边界/div-rem/ptrtoint 均有 lit 用例且被 156/156 覆盖；shift 量 i64 由 lit 寄存器形式 + 运行期 9 组变量移位实证。

**非阻断 finding**（记录，供 architect 收尾酌处）：run.sh C1 的 39/9 为写死交付物结构断言（可达 FAIL，成立）；C2 在树干净时退回检查 `git show HEAD`，提交后重跑仍有效但耦合 HEAD。

**判决：Accepted**——验收命令在我方重跑下全绿，独立反例注入→FAIL→还原→回绿成立，约束无违反。

### architect 收尾（2026-10-28）
- reviewer Accepted；唯一 finding：证据 C2 耦合 HEAD，已改锚 `534f3546~1..534f3546`，重跑 15/15。
