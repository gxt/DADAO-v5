# LLVM-140t: McCat 18-imp `L_canny.c` -O2 SIGABRT（SelectionDAG RUW 类型不匹配）

**模块**：llvm
**项目里程碑**：M10
**依赖**：LLVM-139t（当前后端基线）
**状态**：已验证

## 背景

夜跑 `2026-10-29-12` 的 `tset:llvm-ts` static/dynamic 两档都在同一用例失败：

- 用例：`MultiSource/Benchmarks/McCat/18-imp`
- 文件：`L_canny.c`
- 编译：`-O2`
- 现象：clang 在函数 `dfilter` 的指令选择阶段 SIGABRT（rc=134）
- 断言：`SelectionDAG::ReplaceAllUsesWith` 的
  `Cannot use this version of ReplaceAllUsesWith!`
- 结果：`213 pass / 0 fail / 1 blocked / 8 excluded`；夜跑整体 rc=2，报告 `2026-10-29-12` 不能作为 M10 证据。

已确认可复现，不是超时/OOM/flaky。复现命令见下；崩溃输出已留 `.work/log/llvm/LLVM-140t/LLVM-140t-clang-crash.log`。

## 目标

1. **最小化并定位**
   - 用 `dfilter`/`L_canny.c` 生成可重复的 reduced case（优先 `llvm-reduce` 或裁剪 IR）；
   - 确定是 DADAO `DAGToDAGISel`/pattern/自定义 lowering 的哪一步触发，记录调用栈或 MIR/DAG 证据；
   - 检查是否与 LLVM-137/138/139 的后端改动相关；如相关，指出具体文件/条件。
2. **最小修复**
   - 只改 DADAO 后端必要代码/补丁；不关闭断言、不吞异常、不把用例标 known-fail/blocked 了事；
   - 不改变全局 ABI、寄存器类、code model、i64 语义；不碰 QEMU/spec。
3. **回归测试**
   - 新增 lit/CodeGen 回归（优先 reduced `.ll`，覆盖 `ReplaceAllUsesWith` 类型不匹配路径）；
   - 精确复现命令编译 rc=0；
   - `run_llvm_ts_user.py --only 'McCat/18-imp' --link-mode static|dynamic` 两档 rc=0；
   - 相关 LLVM-137/138/139 向量与 `check-lit` 不回归。
4. **重跑最终夜跑（主会话）**
   - engineer 只交定向验证；修复合入后由主会话重跑 `make check-night`（长任务，主会话 `setsid nohup`，报告目录用新的本地 `YYYY-MM-DD-HH`）。

## 精确复现

```bash
.dadao/cross-toolchain/bin/clang -target dadao-unknown-elf -nostdinc \
  -I .work/source/musl/arch/dadao -I .work/source/musl/arch/generic \
  -I .work/source/musl/obj/include -I .work/source/musl/include \
  -I .work/source/llvm-test-suite/MultiSource/Benchmarks/McCat/18-imp \
  -O2 -DNDEBUG -w -DSMALL_PROBLEM_SIZE -Wno-implicit-int \
  -c .work/source/llvm-test-suite/MultiSource/Benchmarks/McCat/18-imp/L_canny.c \
  -o /tmp/opencode/LLVM-140t/L_canny.o
```

期望修复后 rc=0；当前 rc=134。崩溃 reproducer 可由上述命令重生成；原始副本在 `/tmp/opencode/LLVM-140t/`（临时目录，不作持久证据）。

## 验收

- 上述精确命令 rc=0；生成对象非空。
- `run_llvm_ts_user.py --only 'McCat/18-imp'` static/dynamic rc=0。
- 新增回归测试全绿；`make check-lit`、`make check`、`check-patch-tree`、`check-source-state` rc=0。
- 证据 `.work/evidence/<任务号>/run.sh`：注入→FAIL→`cp`+md5 还原→PASS。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/LLVM-140t/`。
- 不跑完整夜跑（主会话负责）；不跑 `check-full`（未授权）。

## 约束

- 只改 LLVM 后端/补丁/测试/文档；不改 spec/QEMU/contracts。
- 不提交、不 push；`make build-llvm`/`make install-host` 等重建先申报耗时。
- 失败保留完整现场（命令、输出、退出码、日志）；不得以排除用例或放宽断言代替修复。

## 完成区

**状态**：已验证

### 修改文件
- `components/.../DADAOISelDAGToDAG.cpp.patch`（`make_patch.py` 增量导出：`ext` 节点按 `Node->getValueType(0)` 定型）
- `.work/source/llvm-project`（base+1 单 commit、干净）
- `tests/unit/llvm/lit/CodeGen/DADAO/m10-narrow-neg-ext-narrow.ll`（新：6 窄结果扩展 + i64 对照）
- `tests/unit/llvm/codegen/m10-narrow-neg-ext-narrow.ll`（新运行期向量，14 例）+ `expected.yaml` + `validate_codegen_vectors.py` oracle 分支
- `tests/unit/llvm/ir-lli/manifest.yaml`（两新 `.ll` 归类）；`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`（重生成，仅行号位移）；`milestones.md`

### 测试结果
证据 27/27；精确命令 rc=0（10056 B）；llvm-ts `McCat/18-imp` static/dynamic 各 1/1 PASS（byte-exact）；`check-lit` 159 passed/0 failed（现场统计，基线 158+1）；`run_codegen_e2e` 19/19；`check-unit`/`check`/`check-patch-tree`（205 patch）/`check-source-state` rc=0；`-O0/-O1/-O2/-O3/-Os` 五档与 `-verify-machineinstrs` 全 rc=0

### 验收命令与结果
- `bash .work/evidence/LLVM-140t/run.sh` → `evidence: 27 passed, 0 failed` rc=0；I1（lit `sub.sw`→`sub.uw`）/I2（向量期望 −1→−2）/I3（源码还原修复行）注入→FAIL、`cp`+md5 还原→PASS
- 构建：`build-mc JOBS=8` rc=0（5m03）、`install-host` rc=0（2m10）、`build-musl-shared` rc=0（刷新 freshness stamp）；安装根 llc == 构建树 llc（md5 `c095be40…`）
- 根因现场：`.work/log/llvm/LLVM-140t/LLVM-140t-{rootcause.txt,clang-crash.log,isel-debug-prefix.log,reduced-ir.txt}`；崩溃点 `t18: i32 = sign_extend t17`，`t17: i16 = sub Constant:i16<0>, t15`（`ReplaceNode`@SelectionDAGISel.h:412）

### 新发现/坑
- 根因 = LLVM-138t 的 extend 根 narrow-neg 特例硬编码 `MVT::i64`；窄结果（`sext i16->i32`）时 RAUW 类型不等 ⇒ 断言；与 137/139 无关
- 常量比较会被 InstCombine 折叠掉整个 narrow-neg；运行期向量须比较 volatile 载入的期望值才能保住 DAG 形状
- 换工具链后 `check-musl-freshness` 必红（stamp 绑定 clang/ld.lld 哈希）⇒ 须 `make build-musl-shared`
- 新增 `*.ll` 必须登记 `ir-lli/manifest.yaml` 结构闭包，否则 `check-unit` 红
- `tests/unit.yaml` 未收录 M10 lit（137/138/139 起既有缺口），本册沿用；`check-tests-index` 不判未收录

### 遗留
- 未跑 `check-full`/夜跑（主会话负责）；未提交、未 push（提交权归 architect）
- `tests/unit.yaml` 的 4 个 M10 lit 索引缺口未补（非本册引入），建议 architect 统一处理

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：ISel 修复行与注释、lit/运行期向量、oracle、manifest/矩阵/文档、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 只改结果类型是否够（`ext` 指令 def 为 GPRD/64 位寄存器类） | ✅已确认 | 与既有 Pat `(i32 (sext (i16 GPRD)))` 同形，不再改 | lit/运行期向量在 -O0..-O3 + `-verify-machineinstrs` 全 rc=0 |
| 窄结果是否只 i32（i8→i16 亦会触发） | ✅已补覆盖 | lit 加 `sext_neg8_i16`；向量加 i8→i16 两例 | `check-lit` 159/159；e2e 19/19 |
| 运行期向量被 IR 折叠而空转 | ✅已修 | 期望值改 volatile 载入，DAG 保住 `sub i16`+`sext i32` | `.dadao/tests/codegen-e2e/*.prog.s` 含 `sub.sw rd0`+`ext.so`；I2 注入可致非零 |
| 向量未登记 ir-lli 结构闭包 | ✅已修 | manifest 两处登记 | `check-unit` PASS；`diff_ir_lli` 101=20+81、0 unclassified |
| 矩阵/补丁行号漂移 | ✅已修 | `gen_isa_coverage.py` 重生成 | `make check` rc=0（check-isa-coverage 绿） |
| 其他 Select 分支是否有同类硬编码 | ✅已排查 | 仅常量/移位分支，已按节点类型定型 | 全 `ReplaceNode` 调用点逐条核对（420–929 行） |
| `check-full`/夜跑 | ⏸延后 | 主会话负责 | 已在遗留声明 |

**判决**：finding 全部处置（6 项已修/确认、1 项延后并披露）⇒ 可标 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-29）

**重跑记录（reviewer 亲自执行，均在 workdir 内、未用管道吞码）**：
- 精确复现命令：rc=0，对象 10056 B（注入反例前/后各跑一次，最终态 rc=0）
- `run_llvm_ts_user.py --only 'McCat/18-imp'`：static rc=0（total=1 pass=1 fail=0 blocked=0，byte-exact）；dynamic 同为 1/1 PASS rc=0
- `make check` rc=0（repository checks L1: PASS）；`make check-lit` rc=0（现场统计 Discovered 159 / Passed 159，与完成区一致）；`make test-codegen` rc=0（19/19，含新向量 PASS）；`make check-unit` rc=0（ir-lli structural on-disk=101 include=20 exclude=81 unclassified=0，与完成区一致）；`make check-patch-tree` rc=0（205 patch OK）；`make check-source-state` rc=0（llvm-project HEAD=dfc5bb228b17 count=1 clean=True）
- `bash .work/evidence/LLVM-140t/run.sh` 重跑：**27 passed, 0 failed，rc=0**；脚本逐条审过：每条断言有可达 FAIL 路径、无恒真、I1/I2/I3 用 `cp`+md5 还原、无 `cmd|tee` 吞码、计数现场统计

**根因与修复真实性（独立注入，非采信完成区）**：
- 注入 `Node->getValueType(0)`→`MVT::i64` 回组件源（`cp` 备份 md5 fd080851…），`ninja llc` 重建后：新 lit 测试与原始 `L_canny.ll` 均 **rc=134**，断言原文 = `Cannot use this version of ReplaceAllUsesWith!`，栈内 `DADAO DAG->DAG Instruction Selection on @sext_neg16_i32 / @dfilter` —— 崩溃真实复现，修复行 load-bearing
- `cp`+md5 还原（相等）→ 重建后 build llc 与安装根 llc md5 同为 `c095be40…`，两测试 rc=0 回绿。坑：`cp -p` 保留旧 mtime 会让 ninja 判 no-work，须 touch 后重建（reviewer 实测）
- 补丁 diff 核对：改动确为 1 行类型化 + 注释；`-O0/-O1/-O2/-O3/-Os` 及 `-mllvm -verify-machineinstrs` 现场各 rc=0

**约束核验**：改动仅 LLVM 后端补丁/测试/矩阵/台账/任务书（git status 快照前后逐行 diff=0），无 QEMU/spec/contracts；断言开启（assertions=ON，注入可崩即证）；无 known-fail/排除用例（新用例均入 lit+e2e 实跑；manifest 两条为 host-lli 通道结构性归类，沿用 137/138/139 既有约定）；矩阵 diff 全部为 `patch:NNN` 行号位移、0 处其它改动；未跑 check-full/夜跑；未提交。

**findings（均不阻断）**：① 完成区「安装根 llc==构建树 llc（md5 `c102feea…`）」——等式成立（reviewer 两次实测相等），但哈希前缀与现场 `c095be40…` 不符，属过时/笔误，建议收尾时改；② 完成区「-O0..-O3/-Os 四档」实为五档，措辞笔误。

**判决：Accepted**（验收命令全绿、根因独立复现、注入→FAIL→还原→回绿闭环、约束无违反；可提交）。
