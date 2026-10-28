# LLVM-137t: i64 常量移位立即数选择

**模块**：llvm
**项目里程碑**：M10
**依赖**：LLVM-136t（干净基线）
**状态**：已验证

## 背景
当前 i64 的 `shl`/`lshr`/`ashr` 常量移位会先物化移位量、再走寄存器移位；ISA 已有 `shl.o`/`shr.uo`/`shr.so` 立即数形态（`immu6`）。PR（commit `3d77f7bb`）的 64 位常量化部分可作为输入，但必须在 136t 的干净基线上重放，不得夹带 code model/tailjmp 回退。

## 目标
1. 在 `DADAOISelDAGToDAG.cpp` 的常量移位选择中支持 `MVT::i64`，`0 <= shamt < 64` 时选 `shl_o_orri`/`shr_uo_orri`/`shr_so_orri`；`shamt == 0` 保持规范 copy 语义；变量移位保留寄存器形态。
2. 不改变 poison 语义；不为 `shamt >= 64` 构造立即数；不影响窄整数移位（137 只改 i64 分支）。
3. 新增/重放 lit：0、1、31、32、63、变量移位；补 `shamt >= 64` 负例（若 IR 合法可构造）与窄移位回归。
4. QEMU 运行期 oracle：用独立 Python 按 u64 截断/有符号右移派生期望，跑至少 0/1/31/32/63 + 变量；不仅看汇编。

## 验收
- 新增 lit 全绿；完整 `check-lit` 不回归（现场统计）。
- QEMU 运行期结果与独立 oracle 一致；变量移位/窄整数回归不变。
- `make check` rc=0；`check-patch-tree` rc=0；证据 `.work/evidence/<任务号>/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/LLVM-137t/`。

## 约束
- 只改 i64 常量移位选择与对应测试/补丁；不碰 code model、tailjmp、窄 extension、指针 PHI。
- 不改 spec/contracts/ABI；不改 QEMU。
- **不提交、不 push**；重建申报；全量/夜跑未授权时不跑。

## 完成区

**状态**：已验证

### 修改文件
- `components/.../DADAOISelDAGToDAG.cpp.patch`（`make_patch.py` 增量导出；diff 仅 shift hunk）
- `.work/source/llvm-project/.../DADAOISelDAGToDAG.cpp`（源树，base+1 单 commit、干净）
- `tests/unit/llvm/lit/CodeGen/DADAO/m10-i64-shift.ll`（新：0/1/31/32/63、变量、窄回归、>=64 负例）
- `tests/unit/llvm/codegen/m10-i64-shift.ll` + `expected.yaml`（新运行期向量）
- `tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（`gen_isa_coverage.py` 重生成：isel-cpp 56→59、yes 191→193）
- `.tao/knowledge/milestones.md`（状态行）

### 测试结果
通过 14/14（证据脚本）；`make check-lit` **155 passed / 0 failed**（基线 154 + 本册 1，现场统计）；`run_codegen_e2e.py` 16/16（含新向量）；独立 QEMU oracle 18/18（0/1/31/32/63 × shl/lshr/ashr + 变量 n=37）；`make check` rc=0；`check-patch-tree` rc=0（204 patches）。

### 验收命令与结果
- `bash .work/evidence/LLVM-137t/run.sh` → `evidence: 14 passed, 0 failed` rc=0；含 I1/I3 注入→FAIL、`cp`+md5 还原→PASS（I2/I4）
- 构建：`make build-mc JOBS=8` rc=0（实测约 6 min）；`make install-host` rc=0（实测约 5 min）；`make build-musl-shared JOBS=8` rc=0（工具链 build-id 变更后刷新 L1 stamp）
- 补丁增量：`git diff components` 仅 1 文件，无 `SIGN_EXTEND`/`ExternalSymbol`/`selectCodeModel`/`GPRBTC` 行
- 安装根 llc == 构建树 llc（md5 `9274c80b...`）；`m10-i64-shift.ll` 反汇编核对 `shl.o/shr.uo/shr.so` 与 `rd2rd`

### 新发现/坑
- i64 常量移位 `shamt>=64` 在 IR 合法但为 poison，SelectionDAG 在 ISel 前折成 undef ⇒ 负例只能钉「不发射 immu6>=64」；`Sh >= W` 守卫为防御层，正常管线不可直接触达
- `make install-host` 改变工具链 build-id ⇒ `check-musl-freshness` 变红，须 `make build-musl-shared JOBS=8` 刷新（否则 `make check` 非零）
- 矩阵 isel-cpp 计数随补丁行号/新引用机械变化，必须 `gen_isa_coverage.py` 重生成，不得手改

### 遗留
- 未跑 `check-full`/夜跑（未授权）；`shamt>=64` 无 IR 可达的直接单测（受 poison 折叠限制）
- 未提交、未 push（提交权归 architect）

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：`DADAOISelDAGToDAG.cpp` 常量移位分支（419–466）、`m10-i64-shift.ll`（lit + runtime）、`expected.yaml` 新条目、`run.sh`/`oracle.py`、矩阵重生成 diff、任务/里程碑行。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| i64 分支三元链顺序可能误落窄 opcode | ✅已修（实现时按 IsO 优先书写） | `IsO ? shl_o_orri : IsT ? ... : IsW ? ...` 三处 | lit 反汇编见 `shl.o/shr.uo/shr.so`；窄 i32/i16/i8 仍 `shl.t/w/b` |
| `shamt>=64` 负例可能恒绿 | ✅已确认边界 | 负例只断言不发射 `immu6>=64`；该路径被 poison 折叠，`Sh >= W` 为防御层 | `llc` 对 64 位移输出无 orri、无 `set.zw`；局限写入完成区 |
| 运行期向量可能被常量折叠绕过 | ✅已修 | 用 `alloca` + `volatile` 载入 a/b/n | `run_codegen_e2e` 16/16；独立 oracle 18/18 |
| 证据中 `grep -c` 无匹配 rc=1 可能误判 | ✅已确认 | 只取输出数字、不依赖 grep rc | evidence 14/14 rc=0 |
| `make install-host` 后 musl freshness 变红 | ✅已处置 | `make build-musl-shared JOBS=8` 刷新 stamp | `make check` rc=0（L1 PASS） |
| 矩阵行号/计数随补丁漂移 | ✅已处置 | `gen_isa_coverage.py` 重生成 md/tsv | `check-isa-coverage` 绿 |

**判决**：无未修 finding ⇒ 可标 `待验收`。

### 第 1 轮 reviewer 验收

**分析文件**：`DADAOISelDAGToDAG.cpp.patch`（+源树 cpp 与补丁逐字节比对 md5 一致）、lit/codegen 两册、`expected.yaml`、`oracle.py`、`run.sh`、矩阵 tsv、milestones 行、`git show ce50c278` 全部 8 文件。

**重跑（reviewer 亲自执行）**：
- `bash .work/evidence/LLVM-137t/run.sh` ×3：初跑 **13 passed/1 failed**（唯一红 C2，见 finding）；独立注入轮 **6 passed/8 failed**；还原回绿轮 **13 passed/1 failed**（与初跑逐行一致）
- C5 `make check-lit` rc=0、**passed=155 / failed=0**（现场统计）；C8 `make check` rc=0；C9 `check-patch-tree` rc=0；C6 QEMU oracle **18/18**；C7 `run_codegen_e2e` **16/16**；C10 安装根 llc md5 `9274c80b...` 一致

**独立反例注入**（改被测产物，非脚本自带 I1–I4；`cp`+md5 备份于 `/tmp/opencode/LLVM-137t-review/`）：patch `VT != MVT::i64`→`i99`；lit `shl.o …32`→`shl.t`；codegen 期望常量 `…0000`→`…0001` ⇒ C1/C4/C5/C7/C8 及 I2/I4 全 FAIL；`cp` 还原后 md5 与审前一致（`5c8616ff`/`e82adee0`/`3042c170`）、回绿。未用 git checkout/restore/stash。

**语义核验**（reviewer 自跑 llc 看真实汇编）：`shl0/lshr0/ashr0`→`rd2rd` copy；1/31/32/63→`shl.o/shr.uo/shr.so` 立即数；变量→`… rd16, rd17` 寄存器形态；窄 i32/i16/i8→`shl.t/w/b` 回归不变；`shl64/lshr64/ashr64` 函数体仅 `ret`（poison 折叠，无越界 immu6）。另用 Python 全量重算 IR 内 15 个期望常量（u64 截断/有符号右移）：0 mismatch。

**约束逐条**：components diff 仅 1 文件（`git show --name-only` 独立核验）；grep `SIGN_EXTEND|ExternalSymbol(删除)|selectCodeModel|GPRBTC|tailjmp` exit=1 无命中，`ExternalSymbol` 分支保留；未改 spec/contracts/QEMU；工作树 `git status -uall` 0 行、无残留；临时目录合规；未跑 check-full/夜跑。

**finding（非阻塞，architect 收尾改）**：`run.sh` C2/C3 用工作树 `git diff` 判"components 仅 1 文件"，ce50c278 提交后工作树干净 ⇒ 提交后重跑 C2 必红（files=0）。判据本身 reviewer 已用 `git show ce50c278 -- components/` 独立核验成立。建议改 `git diff ce50c278~1..ce50c278 --name-only -- components` 或 `git show --name-only ce50c278`。

**判决**：**Accepted**（验收命令在 reviewer 重跑下通过、约束无违反；C2 为证据脚本时序适配缺陷，非交付物缺陷，已记 finding）。

### architect 收尾（2026-10-28）
- reviewer Accepted；唯一 finding：证据 C2/C3 用工作树 git diff，提交后必红；已改锚 `ce50c278~1..ce50c278`，重跑 14/14 PASS。
