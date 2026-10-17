# TESTCASES-050t: 驱动与口径收尾（include 路径 / 超时抬升 / 静态 builtins / `siod` 排除）

**模块**：testcases
**项目里程碑**：M8
**依赖**：`TESTCASES-048t`（A 类 222 两档真值 `193/2/0/27/0`；本册承接其 `blocked 27` 中的「缺头 3 / 超时 6 / `siod`」与口径面）、`TESTCASES-047t`（静态档 `tgmath` blocked 的现场）、`INFRA-088t`（driver 默认接 compiler-rt，本册只补测试驱动侧）、`ISS-267`（缺头/方言登记源）、`ISS-265`（参考可移植性，**不在本册处置**）、`ISS-248`（`blocked>0 ⇒ rc=1`）、`ADR-0025`（M8 范围）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 问题根源

四项**驱动/口径**收尾（不是被测程序或后端缺陷；**不改语料、不改期望值**）：

### ① include 路径缺失（3 例 `blocked`）

- 现场：`048t` 的「缺头 3」= `MultiSource/Applications/office-ispell`（`sgtty.h`）、`MultiSource/Benchmarks/Prolangs-C/archie-client`（`copyright.h`）、`SingleSource/Benchmarks/Polybench/utilities/template-for-new-benchmark`（`polybench.h`）。
- 事实：
  - `archie-client` 的 `copyright.h` **就在单元目录内**，上游用 `target_include_directories(archie PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})` 提供；
  - Polybench 模板的 `polybench.h` **同目录**，且 `Polybench/utilities/` **无 `CMakeLists.txt`**（上游从不构建它，本仓按「`.c` 含 `main`」口径纳入）⇒ 没有任何 `-I` 来源。
- 根因方向（本笔实读，待诊断确认）：`tools/testcases/run_llvm_ts_user.py` 的 `include_directories`/`target_include_directories` 分支（约 `:841-855`）**把参数原样记入** `config.include_dirs`，未走同文件已有的 CMake 变量展开函数 `expand_cmake_arg()`（`:641`；`set`/`list` 分支已用）⇒ 编译行出现字面量 `-I ${CMAKE_CURRENT_SOURCE_DIR}`；无 `CMakeLists.txt` 的单元则**没有任何单元目录 `-I`**。
- 处置：`include_directories` 系参数先 `expand_cmake_arg`（`variables["CMAKE_CURRENT_SOURCE_DIR"] = [unit_dir]`，`curated_sources()` 已如此设置）；并对**每个单元**默认追加 `-I<unit_dir>`（CMake `CMAKE_CURRENT_SOURCE_DIR` 语义，等价上游默认包含路径）。
- `office-ispell` 的 `sgtty.h` 是 **BSD 专有头**（musl 不提供、上游亦不随语料提供）⇒ 不属「路径缺失」：按 ④ 同口径 `excluded` + 逐条 reason（**不补假头**）；若判断应补头 ⇒ **留问**（改语料/加垫片属超出本册范围）。

### ② 超时抬升（5 例「真慢」，1 例不属本册）

- 现场（`048t`，`--timeout 300`）：`blocked` 中「300 s timeout 6」= `lemon`、`lua`、`SimpleMOC`、`unix-smail`、`mafft`、`nbench`。
- 事实：其中 5 例是**真慢**（`lua`/`mafft`/`nbench`/`SimpleMOC`/`lemon`），需要**实测**后按例抬到 **900–1800 s**；`unix-smail` 是**卡死**（只打 `resolve 'ALL' = 'ALL' @ '' (LOCAL)` 后停住）⇒ 归 `QEMU-063t`，**不得**用抬超时掩盖。
- 处置：驱动加**逐例超时表**（`cid → seconds`，默认仍 `DEFAULT_TIMEOUT`）；值必须来自**本机实测**（记录每例真实耗时），不得凭感觉填；改后须证明该例**真跑完**（guest 退出码判定），而非再次 `124`。

### ③ `functional/tgmath` 静态档缺 builtins

- 现场：`047t` 静态档 `functional/tgmath` `blocked`，`undefined symbol: __muldc3`（complex multiply helper）；链接行**无** compiler-rt builtins archive（`tools/testcases/run_libc_test_user_suite.py` 的 `CASE_NOTES` 已记「本册链接行无该库；加 `.work/build/compiler-rt-builtins/lib/linux/libclang_rt.builtins-dadao.a` 实测 exit=0」）。
- 对照：`llvm-test-suite` 驱动已用 `clang -print-libgcc-file-name` 取同一 archive 并与 `libc.a` 同 `--start-group`（`INFRA-088t` 后 driver 默认真实路径）。
- 处置：libc-test 驱动**静态档**链接行补同款 archive（`clang -target dadao-unknown-elf -print-libgcc-file-name` ⇒ 存在性断言 ⇒ 与 `libc.a` 同 `--start-group`）；动态档不动（`libc.so` 内已解析，现 `pass`）。

### ④ `siod` 排除（不改语料）

- 现场：`MultiSource/Applications/siod`（`048t` 编译/方言 7 之一）上游用 BSD `struct dirent` 字段 **`d_namlen`**；musl 的 `struct dirent` **无该字段**（`d_reclen` 等语义不同）。
- 处置：驱动 `excluded` 清单加该例 + **逐条 reason**（引用上游源码用法 + musl 头现场），不进入 `blocked`/`fail`；**不改语料**、不加兼容宏。
- 同批「编译/C 方言 7」中的其余 6 例（Burg、gawk、make、p2c、OptimizerEval、cdecl）**保持 `blocked`**（现代 clang `-Wimplicit-int` 挡下；未授权全局压 `-Wno-`）——本册**不改**其分类。

## 接口规范

- **输入**：
  - `tools/testcases/run_llvm_ts_user.py`（include 跟踪 / 超时 / `excluded` 口径）
  - `tools/testcases/run_libc_test_user_suite.py`（静态链接行 / `CASE_NOTES`）
  - 语料：`.work/source/llvm-test-suite/**`、`.work/source/libc-test/**`（`patchless`，**只读**）
  - 产物：`.dadao/cross-toolchain/`（安装根）、`.work/build/compiler-rt-builtins/lib/linux/libclang_rt.builtins-dadao.a`
- **输出**：
  - 两个驱动的最小改动（`expand_cmake_arg` 复用 + 默认 `-I<unit_dir>`；逐例超时表；静态 builtins；`excluded` 条目）
  - 两套复跑 JSON/日志：`048t`（两档）+ `047t`（静态档；动态档可选）
  - 证据：`.work/evidence/<任务号>/run.sh`（default + `--inject`）
  - 本任务书完成区 + `milestones.md` 行 + `ISS-267` 处置注
- **约束**：只改两个驱动 + 本任务书（+ 台账）；**不改**语料/期望值/`known-fail` 依据表准入；**不动** `spec/`、`.tao/contracts/`、`contracts/`、`components/**`；跑测期间**不并发**其它测试集（`ISS-229`）。

## 验收标准

1. **① include**：`archie-client`、Polybench 模板两例的编译行含**解析后**的单元目录 `-I`（日志/JSON 留证；不得出现字面 `${…}`）；两例修后按现场判定（`pass` 或**有据** `blocked`——`archie-client` 若因 musl 无 `re_comp` 等仍不通，必须如实记 `blocked` + 新 reason，**不得**造 stub）。`office-ispell` 按 `excluded` + reason 落纸。
2. **② 超时**：逐例超时表**只含** `lua`/`mafft`/`nbench`/`SimpleMOC`/`lemon`（值 900–1800，附本机实测耗时：每例「修前 300 s 截断时的已耗时 / 修后完整耗时」）；改后 5 例**真跑完**（`pass`/`fail`/`known-fail` 由 oracle 判定，不得再是 `124`）；`unix-smail` **不在**超时表内。
3. **③ tgmath**：`--filter 'functional/tgmath'` 静态档 `pass`（guest exit 0）；链接行含 builtins archive（逐字留证）。
4. **④ siod**：`excluded` 计数与 reason 落纸（同批其它 6 个方言例分类不变）。
5. **两套复跑（逐例记账，禁止只报总数）**：`048t` 两档 `blocked 27 → 现场派生值`（变化只允许本节列出的例；`fail 2`/`known-fail 0` 不变）、`047t` 静态档 `blocked 25 → 现场派生值`（只允许 `tgmath` 转 `pass`）；`total == discovered − excluded`、`closure_ok`/`classification_ok` 由脚本断言；**无回归**（逐例 JSON diff）。
6. **可达 FAIL（≥3）**：① 去掉 `-I<unit_dir>` ⇒ 两例重回缺头；② 清空超时表 ⇒ 5 例重回 `124`；③ 去掉 builtins ⇒ `tgmath` 重回 `__muldc3`；④ 删 `siod` 的 excluded ⇒ 该项审计 FAIL。`--inject` 真跑触发后 `cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）。
7. **门控（各留自身 rc）**：`make check`(L1)、`check-tasks`、`check-knowledge-refs`、`check-no-residue`、`python3 tools/infra/check_issues.py`。
8. **不写死计数**：所有预期值由基线 JSON + 转移集**运行期派生**；证据脚本任一失败非零退出。

## 不做

- **不改**语料（含 `siod`/`office-ispell` 源码与头文件）、**不改**期望值、**不改** `known-fail` 准入（`ISS-246`/`ISS-251`/`ADR-0030` 之外不新增）。
- **不**用抬超时处理 `unix-smail`（`QEMU-063t`）；**不**做 `ISS-265`（2 例参考可移植性，待裁）、`ISS-253`（`wchar_t`）、`ISS-254`（`INFRA-089t`）、线程/TLS（`M9`）。
- **不**动 `components/**`（不重建工具链）、`spec/`、`.tao/contracts/`、`contracts/`。
- **不**跑 B 类 1890 单元（`048t` 范围外）。

## 硬约束

1. 临时目录 `/tmp/opencode/TESTCASES-050t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕被检命令自身退出码（禁 `cmd | tee` 吞码）；长日志落 `.work/log/testcases/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（如 `archie-client` 需 `re_comp` 兼容层、`office-ispell` 需补 BSD 头）时留问。
6. 用户裁定须把**原话**写入本任务书。
7. 测试串行：同改共享文件（`tests/vectors/`、`Makefile`、`contracts/`）的任务不得与本册并行。

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
（审查者独立验证的重跑记录、约束核验、判决）
