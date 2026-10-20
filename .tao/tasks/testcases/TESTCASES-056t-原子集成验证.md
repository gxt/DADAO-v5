# TESTCASES-056t: 原子集成验证（C11 全类型 / `__atomic_*` / 并发计数 / ABA 探针）

**模块**：testcases
**项目里程碑**：M9
**依赖**：`LLVM-121t`（① 后端）、`QEMU-067t`（② 语义）、`INFRA-100t`（③ musl 真原子）、`TESTCASES-052t`（047t 19 目标清单与驱动先例）、`TESTCASES-047t`（libc-test 两档驱动与基线）、`ISS-294`（本册是其验证落点）、`ISS-307`（本批 4 册总账）
**状态**：待开始

## 执行环境
**执行环境**：本地

> **编号（现场取号，2026-10-21）**：`testcases` 模块现有最大 = `TESTCASES-055t` ⇒ 取 **`056`**；`find .tao -name 'TESTCASES-056*'` = 0 命中。
> **本批位置**：串行链 ① → ② → ③ → **④ 本册（最后）**；本册不改组件、只做**验证/证据**，但**同用共享安装根** ⇒ 仍不得与 ①②③ 并行。
> **本册边界**：**只加**驱动/探针；**不改**既有判据（`tools/testcases/run_libc_test_user_suite.py` 的分类/`GAP_SIGNATURES`/`attribute_port_gaps` 一律不动 ✗）；不改 `spec/`/`contracts/**`/`components/**`。

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

1. **被验缺口**：`ISS-294` = musl `a_cas` 假原子 ⇒ 多线程互斥丢更新（实测：`3×2000` → `5999/5992/5999`；`4×250000` → 15/15 轮 `rc=124`）。裁定 = **(A) ISA 增原子原语，LR/SC-only**；实现落 **③ `INFRA-100t`**，验证落 **本册**。
2. **上游能力已就绪（前置，须逐条复核）**：`ISS-252`（线程 19 目标两档 19/19，`TESTCASES-052t`）、`ISS-296`–`ISS-299`（PI futex / robust / 取消 / 驱动降级 四缺口全修）、`ISS-295`（`__clone` TP 条件化）。
3. **驱动能力（现状，现场核）**：`tools/testcases/run_libc_test_user_suite.py` 支持 `--link-mode {static,dynamic}`、`--filter <regex>`、必填 `--json-out`、`--work-dir`（`INFRA-093t` 运行产物规矩）；`--filter` 可用于只跑 19 目标；`tools/testcases/report_thread_cases.py` 可派生线程用例视图；证据脚本惯例见 `.work/evidence/TESTCASES-052t/run.sh`。
4. **19 条线程目标清单**：见 `TESTCASES-052t` 册内（现场派生，**不在此复制、禁写死**）；静态档另有 `regression/pthread_create-oom` 属 `ISS-257` flake、**不计入** 19。
5. **既有并发缺口的原始现场**：`.work/log/qemu/QEMU-065t-atomicity-probe.log`（1×200000 精确、3×2000 起丢更新；4×250000 5/5 超时）+ `QEMU-065t` 证据脚本的 `[GAP]`/`--strict` 口径（修好后探针应自然转 `[PASS]`，见 `ISS-294` 收尾裁定段）。
6. **工具链门控**：`tools/testcases/check_lit_gen.py`、`run_artifacts.py` 为既有产物/证据守卫；新增驱动需自带 `--inject` 反例自测（`Process-08` 证据脚本口径）。

## 目标

1. **两档**（静态 + 动态）跑完下列全部族，逐条 PASS、逐例可比：
   - **047t 线程 19 目标**：19/19 `pass`，两档不回归；
   - **并发计数**：`N` 线程 × `M` 次互斥自增，计数**精确 = `N×M`**（`N/M` 现场从探针参数读，禁常量）；
   - **C11 `<stdatomic.h>` 全类型**：`_Atomic int / long / char / short / void*`（+ `_Atomic size_t`）× `relaxed/acquire/release/acq_rel/seq_cst` × `load/store/exchange/fetch_add/fetch_sub/fetch_or/fetch_and/fetch_xor/compare_exchange_strong/weak`；
   - **`__atomic_*` 家族**（GCC 内建）：`__atomic_load_n/store_n/exchange_n/fetch_add/fetch_sub/fetch_and/fetch_or/fetch_xor/compare_exchange_n` × `{1,2,4,8}` 字节 × `{__ATOMIC_RELAXED,ACQUIRE,RELEASE,ACQ_REL,SEQ_CST}`；
   - **ABA 探针**（Treiber 栈 + 版本号）：验证 `sc` 失败语义/重试正确性（不丢节点、不重复弹出、栈长归零）。
2. **`a_barrier` 断言**：`a_barrier()` 站点在生成代码里**确有 `fence`**（结构断言，非「跑得快就算」）。
3. **关闭 `ISS-294`**（验证落点 = 本册；`resolved_by` 由 `/complete` 落，`status` 变更不在本册内做）。
4. 证据可审计：一键脚本 `run.sh` + `--inject` 反例，JSON 产物落 `.work/`，脚本**能被反向注入判红**。

## 接口规范

**输入**（只读）：
- 安装根工具链（`clang`/`lld`/`llvm-nm`/`llvm-objdump`，`INSTALL_ROOT` 由 `Makefile` 给出）+ `.work/build/qemu/qemu-dadao`（或安装根 `qemu-dadao`，**二选一须在证据里写明并核对 md5 一致**）。
- `tools/testcases/run_libc_test_user_suite.py`（047t 驱动，**只调用不改**）、`tests/libc-test/**`（manifest 锁定语料）、`TESTCASES-052t` 的 19 目标清单。
- musl 头文件与库（③ 之后）、`__atomic_*` 由 ① 之后的后端直接展开（**不链 libatomic**）。

**输出**（交付物）：
1. `tests/atomics/`（探针源码，**入库**）：`counter.c`、`c11_alltypes.c`、`atomic_builtins.c`、`aba_treiber.c`、`barrier_probe.c`（每份文件头写清用途/期望/oracle 口径）。
2. `tools/testcases/run_atomics_probe.py`（新驱动）：`--link-mode {static,dynamic}`、`--json-out`（必填）、`--work-dir`、`--jobs`、`--inject`（反例自测）；**不接管** 047t 判据。
3. `tools/testcases/oracle_atomics.py`（独立 oracle，**纯 Python**：C11 语义模型 + Treiber 不变量 + `N×M` 派生；**不 import 任何组件产物**）。
4. `docs/` 或 `tools/testcases/README` 中一段「如何跑」的指针（若既有 README 已有章节 ⇒ 追加，不新建文件）。
5. `.work/evidence/TESTCASES-056t/**`（含 `run.sh`，默认 + `--inject`）+ `.work/log/testcases/TESTCASES-056t/**`；本册完成区。

**约束**：
- **不改** `run_libc_test_user_suite.py` 的分类/签名/降级逻辑；不改 `tests/vectors/**`；不改 `components/**`。
- **独立 oracle**：期望值一律由 `oracle_atomics.py` 按语义手算/按不变量派生，**不得**从实现运行结果回填；**不得**用同一份 C 逻辑既产生期望又产生观测。
- **计数现场派生**：`N/M`、用例数、`fence` 出现次数全部从参数/产物读，禁写死。
- **每条断言须有可达 FAIL**：至少 2 条真实注入并回绿（见下）；恒真断言（如「两支写同一结果」）一律不接受。
- 探针**不得用 `__atomic_*` 去验证 `__atomic_*` 的正确性**（族①要用「顺序/单线程 + 独立 oracle」判）；并发族用**不变量/精确计数**判。

## 设计要点（**不预设唯一实现**）

### A. 并发计数（`counter.c`）

- 形态：`N` 线程 × `M` 次 `pthread_mutex_lock/unlock` 保护共享 `long` 自增；参数由 `argv` 给（默认 `4 × 250000`）。
- 判据：`count == N*M`（**精确**），且各线程自报次数之和 == `N*M`（第二重独立校验）；`timeout` 用 `run_artifacts` 口径（`124` 判 FAIL，不得当「慢」放过）。
- 关闭对象：`ISS-294` 的原始现场（`4×250000` 15/15 `rc=124`）⇒ 修复后须**每轮精确**。

### B. C11 全类型（`c11_alltypes.c`）

- 类型矩阵：`_Atomic char/short/int/long/void*`（+ `_Atomic unsigned` 变体）；每类型覆盖 `load/store/exchange/fetch_{add,sub,or,and,xor}/compare_exchange_strong/weak` × 5 种 ordering。
- 单线程值语义用**独立 oracle**（Python 手算每个 op 的返回值/最终值），多线程只对「不变量」断言（如计数器最终值 = 成功 `increment` 次数）。

### C. `__atomic_*` 家族（`atomic_builtins.c`）

- `{1,2,4,8}` 字节 × 9 个内建 × 5 种 ordering；**链接期**同时断言 `llvm-nm -u` 无 `__atomic_*`（证明走的是 ① 的 lr/sc 展开而非库）。
- 子字宽（1/2 字节）**必须**加「同字相邻字段不变」断言（与 ① 的掩码合成对应）。

### D. ABA 探针（`aba_treiber.c`）

- Treiber 栈（`_Atomic(void*) head`）+ 每节点 `version`；`N` 线程 × `M` push/pop 混合；判据 = **不变量**：① 所有 push 的节点恰好被弹出一次（无丢/无重）；② 终态栈空；③ 无环/无野指针（弹出节点内容校验）。
- 该探针**必须**能在「`sc` 失败不清保留 / 失败当成功」的实现下红（② 的可达 FAIL 与本册呼应）。

### E. `a_barrier` 结构断言（`barrier_probe.c`）

- 断言：`clang -S`（或 `llvm-objdump -d`）里 `a_barrier()` 调用点对应位置**含 `fence`**（计数 > 0，值按 ③ 选定：`0x00C3` 或 `0x03CF`）；**独立 oracle** = 源码里 `a_barrier()` 的出现次数（宏展开后静态可数）。
- 运行侧：`store(data); a_barrier(); store(flag)` + 读侧对应序列，`N` 轮不出现「flag 可见而 data 未定」的观测（**弱一致宿主上可能不敏感** ⇒ **不作硬判据**，只作附加观测，且必须写清「不敏感≠等价」）。

## 验收标准

1. **047t 19 目标两档 19/19**：`run_libc_test_user_suite.py --link-mode {static,dynamic} --filter <19 目标正则> --json-out ...` 逐例 `pass`；其余用例状态**逐例不变**（与 `TESTCASES-052t` 基线对比，禁抽样）。
2. **并发计数**：两档各 ≥5 轮，每轮 `count == N*M`（`N/M` 从参数读），无 `124`。
3. **C11 全类型 + `__atomic_*`**：逐条 PASS，逐条带 oracle 依据；`--atomic` 家族链接期 `__atomic_*` 未定义符号 = 0。
4. **ABA 探针**：不变量 ①②③ 全部成立，两档各 ≥5 轮。
5. **`a_barrier` 结构断言**：`fence` 计数 == 源码 `a_barrier()` 站点数（现场派生），两档均成立。
6. **`QEMU-065t` 并发项转 `[PASS]`**：重跑该册证据脚本（`--strict`）⇒ 原 `[GAP]` 项转 `[PASS]`，`--strict` 绿（**不回填**该册历史记录，只在本册留证据指针）。
7. **证据脚本自证**：`run.sh`（默认 + `--inject`）均 rc=0；`--inject` 至少覆盖下面 2 条可达 FAIL。
8. **门控**：`make check`（L1）绿；本册不改组件 ⇒ 无需重建，但**安装根须为 ①②③ 之后的新鲜产物**（md5/戳记核对并留证）。

## 做（阶段）

- **阶段 0 现场复核**：核 ①②③ 均 `已验证`；核 19 目标清单现状（两档 19/19）；核 `fence` 在安装根 `clang -S` 产物中的助记符形态；记录基线（`ISS-294` 的 `4×250000` 现场数字）。
- **阶段 A 探针与 oracle**：`tests/atomics/*.c` + `oracle_atomics.py`（先写 oracle，再写驱动；oracle 与观测**分文件、无共享实现**）。
- **阶段 B 驱动**：`run_atomics_probe.py`（`--inject` 自测；JSON 产物；`--jobs` 并发）；两档跑通。
- **阶段 C 回归与收口**：047t 19 目标两档 + `QEMU-065t` 证据脚本 `--strict` + `make check`（L1）→ 证据脚本 `--inject` → 完成区（含 `ISS-294` 关闭建议）。

## 可达 FAIL（**≥2，须真实注入并回绿**）

1. **假原子注入**：把探针用的 `a_cas` 替换为「load/compare/store」等价实现（或把 ③ 的 arch 版本临时退回，**用临时树注入**，禁 `git restore/checkout`）⇒ 并发计数**丢更新**（≠ `N×M`）或 `124` ⇒ 红；还原后回绿。
2. **并发规模派生**：断言若把 `N×M` 写成常量 `1000000`，把参数改成 `4×2500` 时**仍应判红**（说明期望值必须现场派生）；实现为真原子时判据应随参数变绿 —— 该条以 `--inject` 的「常量期望」反例自测证明。
3. **去掉 `a_barrier` 断言**：把结构断言改成「恒真」（如只 `grep` 文件存在）⇒ 注入「`a_barrier` 退化为空 asm」的变体后**不红** ⇒ 说明断言失效，必须改回可 FAIL 形态。
4. **`sc` 失败当成功**（用 ② 的注入手法，或探针侧篡改成功位判据）⇒ ABA 探针的不变量 ①（丢/重节点）**红**。

## 已知边界（**披露**）

- **并发类判据的可重复性**：qemu-user 多宿主线程下的内存序观测**可能不稳定** ⇒ 运行期顺序类观测**不作硬判据**（硬判据 = 精确计数/不变量/结构断言），任何「偶发红」须登记 `issues.yaml` 而**不得**放宽断言。
- **`scope: excluded` 的 re-scope 不在本批**：本册只验证组件行为，规范面仍标未实现（见 ①②③ 的「已知边界」）；`ISS-294` 的关闭以「行为已验证」为准，规范面收口由另行授权的 spec 册负责。
- 动态档 `-fPIC` 口径沿用 `TESTCASES-049t`；`pleval` 等既有 `blocked` 项**不动**。
- 本册**不**新增门控挂载（不并入 `make check`/`check-full`）；是否升级为门控由用户在收尾时裁定（`ADR-0033 D5` 同类先例）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
