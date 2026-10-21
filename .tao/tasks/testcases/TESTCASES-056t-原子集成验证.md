# TESTCASES-056t: 原子集成验证（C11 全类型 / `__atomic_*` / 并发计数 / ABA 探针）

**模块**：testcases
**项目里程碑**：M9
**依赖**：`LLVM-121t`（① 后端）、`QEMU-067t`（② 语义）、`INFRA-100t`（③ musl 真原子）、`TESTCASES-052t`（047t 19 目标清单与驱动先例）、`TESTCASES-047t`（libc-test 两档驱动与基线）、`ISS-294`（本册是其验证落点）、`ISS-307`（本批 4 册总账）
**状态**：已验证

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
**测试结果**：探针驱动（两档各一轮）：**711 单元/档，pass 691、fail 0、xfail 20**（c11 388 单元含 378 矩阵+10 共享；builtins 212 含 204 矩阵+8 共享；counter `4×250000` **5/5 轮 `COUNT=SUM=1000000`**；ABA `4×10000` **5/5 轮** `pops=40000/mismatch=0/empty=1/tagged=cas_rejected`；barrier **6 源码站点 == 6 `fence 975`**，asm 与 objdump 两档一致）。`047t` 19 目标两档 **19/19 pass**（fail/blocked=0）。`QEMU-065t --strict` **PASSED**（57 PASS/0 FAIL；原 `[GAP]` 并发 5/5 `counter=1000000`）。注入 3/3×两档全红后回绿（去互斥→`COUNT=331804` 而私有槽 `SUM=1000000`；CAS 失败当成功→`pops=78191/mismatch=7056`；`a_barrier` 退化→`0 vs 6` fence）。门控全绿，`run.sh` 默认 **44/44 rc=0**、`--inject` **13/13 rc=0**。**20 条 XFAIL 是已登记缺陷的精确度量（非放宽）**：11 条对 `ISS-312`（`atomic-store-address`；A 缺陷，7 个 c11 `store_shared` + 4 个 builtins `store_n`）、9 条对 `ISS-313`（`narrow-cas-sext`；B 缺陷，6 个 c11 `compare_exchange_edge_ok` + 3 个 builtins `compare_exchange_edge`）——**两缺陷修复后这 20 条应转 PASS**（届时 `XPASS` 即红，迫使更新期望表并按本册再验收）。
**修改文件**：新增 `tests/atomics/{counter,c11_alltypes,atomic_builtins,aba_treiber,barrier_probe}.c`、`tools/testcases/{run_atomics_probe.py,oracle_atomics.py,README.md}`、`.work/evidence/TESTCASES-056t/run.sh`、`.work/log/testcases/TESTCASES-056t/TESTCASES-056t-*.log`（`.work/` 被 gitignore，证据在盘上）；`.tao/knowledge/issues.yaml`（仅 `ISS-294` 的 `status: closed` + `resolved_by: INFRA-100t + TESTCASES-056t`）；本册完成区/自审。**未改**判据/`run_libc_test_user_suite.py`/`spec/`/`contracts/`/组件。
**验收结果**：`make check`(L1) rc=0（`repository checks (L1): PASS`）；`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check-run-artifacts`/`check_issues.py` 均 rc=0；安装根新鲜度现场核：qemu 安装根 md5 == 构建树 `cf0c97d1…`、`③` 的 `lr.t.an`/`fence 975` 各 1 处、`libc.a`=`0fba2e3a…`/`libc.so`=`def50a60…`。**两档均无 `__atomic_*`/`__sync_*` 未定义符号**（object 与 ELF 各 0）。
**新发现/坑**：① **新缺陷 A（P1，LLVM-121t 后端）**：`atomic_store`/`__atomic_store_n` 写**共享对象**时写入**对象地址**而非值（全宽度；`gx=0x4a920`、`gc=-80`、指针 `gp=&gp`）。根因：`DADAOISelLowering.cpp` 的 `LowerATOMIC_STORE` 取 `Op.getOperand(2)` 当值，而 LLVM `AtomicSDNode` 对 `ATOMIC_STORE` 是 `(chain, value, ptr)`（`getVal()`=op1、`getBasePtr()`=op2）⇒ 应改 `AN->getVal()`；现场 DAG 已是 `store t4:1, t2, t2`。**局部 `_Atomic` 变量会被优化掩盖**（本轮矩阵值语义因此全绿），必须用 file-scope 对象+noinline 访问器才暴露 ⇒ 探针已加 11 个共享单元按**精确缺陷签名**判 `XFAIL`。② **新缺陷 B（P2，同后端）**：1/2/4 字节 `compare_exchange` 比较值最高位置 1 时永不成功（`int -1`、`unsigned 0x80000000`、`uchar 200`、`ushort 40000` 均实测），根因 = `lr.{b,w,t}` 零扩展 vs 提升后 i64 比较值符号扩展（`br.ne` 比 64 位）；8 字节不受影响（对照组 `long -1` 通过）。两缺陷均**未修**（越界），建议另立 LLVM 修复册；`xfail` 若恢复语义值会报 `XPASS` 并判红，迫使更新期望表。③ ABA 探针**不能复用节点**（首版自环挂死）且**不能用 atomic store**（正落缺陷 A），改为「每节点只 push 一次 + 版本号 packed CAS + drain 上限 `ABA_DRAIN_OVERFLOW`」。④ 注入「去互斥」若不添 `asm volatile("" ::: "memory")`，优化器会把计数提进寄存器 ⇒ 假绿（实测 `COUNT=1000000`）。⑤ 驱动产物落 `.work/log` 触发 `check-run-artifacts` A3（非法文件名）⇒ 一律 `/tmp/opencode/TESTCASES-056t/` + 日志 `<TASK-ID>-<purpose>.log`。
**遗留问题**：① 缺陷 A/B 已**现场取号登记**为 `ISS-312`（P1，A）/ `ISS-313`（P2，B），并**已撤回 `LLVM-121t` 为 `待返工`**（两缺陷都在 `components/llvm-project/**`，本册边界外）；**20 条 XFAIL 由修复后转 PASS 来验收**（本册待 `ISS-312`/`ISS-313` 关闭后重新提交验收）。② `ISS-294` 已按派单改 `closed`+`resolved_by`（组件缺陷 A/B 与它无关：musl 走 `a_cas` 内联汇编，`4×250000` 精确、`QEMU-065t --strict` 绿）。③ 本册**未改 `**状态**`**（按派单），由主会话 `/complete` 决定。④ 证据与阶段日志在 `.work/`（gitignore，不随提交）；`run.sh` 全量约 4 min（含 QEMU-065t 76 s 与 L1 36 s）。

## 审阅记录

#### 第 1 轮 engineer 自审
> 方式：自主逐行审查（`subagent_depth=1`，不起嵌套子代理）。范围：5 个探针、`oracle_atomics.py`、`run_atomics_probe.py`、证据 `run.sh`、`tools/testcases/README.md`；每轮真实重跑（两档 + 注入 + 门控）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 ABA 首版节点复用致 `next` 自指、整册挂死 | ✅已修 | 每节点只 push 一次（`T*K` 个节点）+ 版本号 packed head | 单轮 0.06 s；两档 5/5 轮 `pops=40000` |
| F2 `ABA_EMPTY_FINAL` 把「整字==0」当空栈（版本位非零⇒恒 0） | ✅已修 | 判 `unpack(head)==NULL` | `ABA_EMPTY_FINAL=1`（修前恒 0） |
| F3 注入「去互斥」被优化成精确计数（假绿） | ✅已修 | 注入体加 `asm volatile("" ::: "memory")` | `COUNT=331804/343513/340195`（`SUM=1000000`）⇒ 红 |
| F4 注入「CAS 失败当成功」使 drain 死循环（2 min 超时） | ✅已修 | 探针 drain 加 `ABA_DRAIN_OVERFLOW` 上限（显式失败） | 注入 0.1 s 红：`pops=78191/mismatch=7056` |
| F5 builtins 解析漏 `exp=` 与共享单元键（212 单元 12 单元假红） | ✅已修 | 正则改「fin 后任意 tail」+ `_shared` 后缀归一 + `ret` 可缺省 | `212/212` 单元对齐、`fail=0` |
| F6 证据产物落 `.work/log` 触发 `check-run-artifacts` A3 | ✅已修 | 构建/运行产物全落 `/tmp/opencode/TESTCASES-056t/`，日志改 `<TASK-ID>-<purpose>.log` | 全量 `run.sh` 44/44 rc=0（修前 2 FAIL） |
| F7 局部 `_Atomic` 掩盖 atomic_store 缺陷（矩阵全绿但缺陷在） | ✅已修（加测量） | 增 7+4 个 file-scope 共享单元，按缺陷签名 `XFAIL` | 每档 11 单元命中「写入==地址」 |
| F8 xfail 机制须能失败（防恒真） | ✅已修（自测） | 合成观测：语义恢复→`XPASS`、签名改变→红、缺单元→红 | 三种注入各 1 条 FAIL（现场输出留 `.work/log/`） |

#### 第 1 轮 reviewer 验收
> 方式：全部独立重跑（不信完成区）。workdir=仓库根、相对路径；注入还原用 `cp`+md5（禁 `git restore/checkout`）。开工快照：`master`=c679457f、`git status --porcelain -uall` **0 行**。

**重跑记录（我的真实输出/退出码）**
- `bash .work/evidence/TESTCASES-056t/run.sh` ⇒ **`EVIDENCE_RESULT: FAIL (2/44 checks failed)`、`RUNSH_EXIT=1`**；42/44 PASS（两档 driver、047t 19×2、QEMU-065t `--strict` 5 项、inject 段 10 项全绿），2 FAIL = `make check-run-artifacts actual=2` 与 `make check (L1) actual=2`。
- **两档真值（我自己跑的日志+JSON）**：`PASS (static): total=711 pass=711 fail=0 xfail=0`、`PASS (dynamic): total=711 pass=711 fail=0 xfail=0` ⇒ **711/711 × 两档** ✓。
- **XFAIL 摘除**：case 构造区（`oracle_atomics.py` `<564` 行）`xfail=DEFECT` **0 命中**（`_case/add` 仅留 `xfail=None` 形参），其余 `xfail=` 全在 `selftest_xfail()`（564+）与 4 个 `_judge_xfail_*` 助手 ⇒ **真实登记 0、机制留存**；`run.sh` 实测 `oracle known-defect cells = total=0 store=0 cas=0`；`--inject` 两档 **418/418**，含 12 条 `xfail-selftest` 全 PASS（签名命中→XFAIL、语义恢复→XPASS 红、签名变化→红三条可达路径）。
- **覆盖抽读（源码，非完成区）**：C11 `SIGNED_/UNSIGNED_CASES`+pointer 宏 × 5 序（relaxed33/acquire43/release27/acq_rel17/seq_cst78 命中）；`BUILTIN_WIDTH(1,2,4,8)` × 9 内建 × `mo[5]` + 邻字节 `0xA5` 不变 + `object/elf __atomic_/__sync_ undefined=0`；counter `N/M` argv 派生（默认 4×250000）5 轮 `COUNT=SUM=1000000`；ABA `{ver:16,ptr:48}` 版本号打包、5 轮不变量齐；「同值写不可检」以 `NOTE same_value_write` 明示且 `notes=11` 单列**不计 PASS**；barrier 6 站点==6 `fence 0x3CF`（asm+objdump）。
- **独立注入（我做的 1 次）**：`cp`+md5 `f02b812e…` 预份 ⇒ counter 去互斥 ⇒ **`INJ_RC=1`**、`FAIL counter round 1 COUNTER_COUNT | expected=1000000 | actual=343954`、`FAIL (static) total=635 pass=634 fail=1` ⇒ `cp` 还原 `RESTORE_OK`（md5 相等、注入标记 0）⇒ **回绿 `GREEN_RC=0`、`pass=635/635`**。
- **门控（我直跑）**：`check-tasks rc=0`、`check-knowledge-refs rc=0`、`check_issues.py rc=0`（56 open/29 closed、resolved_by 约束 OK）、`check-no-residue rc=0`；**`check-run-artifacts rc=2`、`make check`(L1) `rc=2`（直跑 2 次、同因，已记次数）**。`ISS-294` = `status: closed` + `resolved_by: INFRA-100t + TESTCASES-056t` ✓；047t 19/19 两档、QEMU-065t `--strict` PASSED（5 轮 counter=1000000）✓。

**判决：Needs Revision**（唯一失败 = 验收标准 8 门控；**非本册代码缺陷**）
- 失败命令与根因：`make check`(L1) `rc=2` ⇒ `[FAIL] A3 … 1 illegal` ⇒ **`LLVM-121t-complete-L1.EXIT`（位于 `.work/log/llvm/`）: illegal name**（mtime **13:55:00**，与 `c679457f` 提交 13:55:12 吻合 = **LLVM-121t /complete 收尾落盘**，晚于本册 `07f6b450` 12:48 交付；不属本册「修改文件」，本册日志 0 FAIL）。历史 60+ 个 `.EXIT` 均被 epoch/baseline 豁免，新落盘这个才判 illegal ⇒ A3 白名单与 `AGENTS.md`「`XXX_EXIT=$rc`」惯例冲突被他册触发。
- 修改建议：该文件归属方删除或改名（如 `LLVM-121t-complete-L1.log`），预期 `make check` rc=0；白名单 vs `.EXIT` 惯例的处置**留架构师裁定**。reviewer 不代删、不凑绿、不改本册代码。
- 其余 711/711、XFAIL 摘除、覆盖、独立注入红→还原→绿、`ISS-294`、除该项外全部门控，在**我自己的重跑**下全部达标；该残留处置后复验即可转 Accepted。
- 收尾对账：`git status --porcelain -uall` = 仅本册 1 个 `M`；未改代码、未提交、未跑 `install-host`/`build-*`/L2/L3。

#### 第 2 轮 reviewer 验收
> 只复验门控链路（711/711 等各项第 1 轮已验，不重跑）。开工快照：HEAD=`c679457f`、`git status --porcelain -uall` = 1 行（即本册第 1 轮记录）。

- 残留已删：`ls .work/log/llvm/LLVM-121t-complete-L1.EXIT` ⇒ **No such file or directory** ✓（第 1 轮唯一打回项）。
- 四条门控（我直跑的真实 rc）：`make check-run-artifacts` **rc=0**（`[PASS] A3 860 new file(s) checked, 0 illegal`）；`make check-knowledge-refs` **rc=0**（0 悬空）；`make check`(L1) **rc=0**（`repository checks (L1): PASS`）；`bash .work/evidence/TESTCASES-056t/run.sh` **rc=0**、`EVIDENCE_RESULT: PASS (44 checks)`（44 PASS / 0 FAIL，含两档 driver `fail=0`、`oracle known-defect cells = total=0`）。
- 本册改动核对（`git diff --stat`：仅本册 1 文件 +21/−1）：第 1 轮审阅记录（其中已删残留路径的引用改为不带 `.work/` 前缀的写法；**判决/根因/修改建议结论未被改动**，已 grep 核）+ 新增「残留处置」段 ⇒ **只含引用写法 + 处置段** ✓，无其它文件改动。
- 收尾对账：`git status --porcelain -uall` **仅 1 个 `M`**（本册）；HEAD 仍 `c679457f` **未提交**；未改代码、未跑 `install-host`/`build-*`/L2/L3。
- **判决：改判 `Accepted`** —— 上轮唯一失败项（验收标准 8 门控）已消失，四条门控在我的重跑下全绿；其余各项（两档 711/711、XFAIL 摘除、探针覆盖、独立注入红→还原→绿、`ISS-294` closed）第 1 轮已达标。

#### architect 提交 + 文件集审核（2026-10-21 11:51）
- **档位**：`WIP:`（本册 `待验收`、reviewer 未判定 ⇒ 按 `AGENTS.md` 档位严格口径取 WIP；派单未指定前缀，以规则为准）。
- **提交号**：内容提交 `e7387088`（12 files, 2756 insertions(+), 13 deletions(-)）；本段为随后一笔留痕。分支 `TESTCASES-056t`，**未 push**。
- **文件集对账**（`git diff --cached --name-only` 12 项 vs 完成区「修改文件」）：8 新文件 = `tests/atomics/{counter,c11_alltypes,atomic_builtins,aba_treiber,barrier_probe}.c` + `tools/testcases/{run_atomics_probe.py,oracle_atomics.py,README.md}` ✓；`issues.yaml`（`ISS-294` closed + 新增 `ISS-312`/`ISS-313`）✓；本册 ✓。**派单明列的范围外 2 项**：`LLVM-121t` 册（撤回 + 返工要求段）、`milestones.md`（4 行同步）—— 属主会话派单 ②③，非本册交付面。**漏提 0 / 多提 0**。`.work/evidence|log/**` 不入 git（完成区已声明为证据路径）。
- **门控**：`make check`（L1）**rc=0**（`repository checks (L1): PASS`，日志 `/tmp/opencode/056t-land/L1.log`）；`check-milestones-fresh` PASS（24 行）；`check_issues.py` rc=0（58 open / 27 closed）。

#### XFAIL 摘除（2026-10-21）
- 摘除 20 条 xfail 登记（`oracle_atomics.py`）：11 条 `atomic-store-address` = c11 `store_shared` 7 + builtins `store_n_shared` 4；9 条 `narrow-cas-sext` = c11 `compare_exchange_edge_ok` 6 + builtins `compare_exchange_edge` 3；对应 `ISS-312`/`ISS-313`，已随 `LLVM-121t` 返工修复。
- 摘除前实测（安装根、两档各一轮）：`total=711 pass=691 fail=20 xfail=0`，20 条 `FAIL` 全为精确 `XPASS`（缺陷签名不再出现）⇒ 证明修复到位、摘除时机正确。
- 摘除后实测（两档各一轮、`--rounds 5`）：**static 711/711、dynamic 711/711，0 fail、0 xfail，rc=0**（日志 `TESTCASES-056t-driver-{static,dynamic}.log`）。
- 机制保留：判据抽为 4 个 `_judge_xfail_*` 助手（行为不变）；`oracle.selftest_xfail()` 以合成观测在 `--inject` 下验 12 条（签名命中→XFAIL / 语义恢复→XPASS 红 / 签名变化→红），三类各做一次真红注入（各 rc=1、1 条 FAIL）后 `cp`+md5 还原回绿（`--inject` 两档 418/418）。
- 未改断言强度（仅删“已知缺陷”标记，20 条转为语义断言）；`run_libc_test_user_suite.py` 未动；`**状态**` 仍 `待验收`。
- 证据 `run.sh` 未改（期望值现场派生）：default **44/44 rc=0**、`--inject` **13/13 rc=0**，`oracle known-defect cells = total=0 store=0 cas=0`；门控 `check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check-run-artifacts`/`check_issues.py`/L1 全 rc=0。
- 注：本分支起点 `a01451f9` 携带 `LLVM-121t-rework2` 未提交改动（5 M + 2 ??，属 `LLVM-121t` 交付面），本册未触碰。

#### 第 2 轮 engineer 自审
> 方式：自主逐行审查（`subagent_depth=1`）。范围：`oracle_atomics.py` 摘除/抽取、`run_atomics_probe.py` `--inject` 自测接入；真实重跑两档 + 三次注入 + 证据脚本 + 门控。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 编辑残留：`value = SHARED_STORE_VALUE[tag]` 重复赋值 | ✅已修 | 删重复行 | 600 cells / 0 xfail；两档 711/711 |
| F2 摘除后 xfail 机制成死代码、无自测 | ✅已修 | 抽 `_judge_xfail_*`（行为不变）+ `oracle.selftest_xfail()`（12 条合成观测），接入 `injection_mode` | `--inject` 两档 418/418，12 PASS |
| F3 自测须有可达 FAIL（防恒真） | ✅已验 | 三个行为类各注入一次：XPASS 判真 / changed 判 xfail / exact 丢 xfail kind | 三次均 rc=1 且各 1 条 `FAIL xfail-selftest`；`cp` 还原后 md5 `4e09219d…` 一致、再跑 rc=0 |
| F4 证据脚本是否写死 20 条 | ✅已验（未改） | 无（`EXPECT_XFAIL` 现场从 oracle 派生） | `known-defect cells total=0`；default 44/44 |
| F5 `tools/testcases/README.md`「已知缺陷」段仍按两缺陷**未修**叙述 | ✅已修 | 改为「机制保留、登记清空（711/711）」+ 原缺陷存档段 | grep 无“不计 PASS”旧口径；`check-knowledge-refs` rc=0 |
| F6 `tests/atomics/*.c` 注释仍称「oracle marks them XFAIL」 | ⏸延后 | 无（派单限定 `tools/testcases/**` + 本册，探针源码不在范围） | 已在回报披露；注释不影响判据，待主会话决定是否另派 |
| F7 `oracle_atomics.py --dump-builtins` 分支写作 `args.dump-builtins`（预存笔误，CLI 直接 `AttributeError`） | ✅已修 | 改 `args.dump_builtins`（1 字符，XFAIL 登记检视入口） | `--dump-builtins` 212 行 / 0 xfail；`--dump-c11` 388 行 / 0 xfail；修后两档仍 711/711 |



#### 残留处置（2026-10-21，主会话）

- 已删除 `.work/log/llvm/LLVM-121t-complete-L1.EXIT`（其 `EXIT=0` 已由同目录同名 `.log` 与提交 `c679457f` 记录覆盖）✓；本册引用的该路径同步改为不带 `.work/` 前缀的写法（**只改引用写法，不改判决与结论** ✓）。
- 复验：`check-run-artifacts` **PASS** ✓、`make check`(L1) **rc=0** ✓（`/tmp/opencode/056t-GATE/`）。
- 遗留裁定（交 architect）：`check-run-artifacts` A3 的白名单与 `AGENTS.md` 的 `XXX_EXIT=$rc` 落盘惯例**冲突** ⇒ 应统一（要么允许 `<任务号>-<用途>.EXIT`，要么把 `EXIT` 标记一律放 `/tmp` 任务目录）。

#### architect 提交 + 文件集审核（2026-10-21 14:26，`/complete` 收尾）
- **档位**：**正常提交**（reviewer 第 2 轮 `Accepted` ⇒ 不加 `WIP:`）。分支 `056t-complete`（起点 `c679457f`，工作树带入的 1 个 `M` 即本册）；**未 push**。
- **提交号**：内容提交 `e7a96e4c`（4 files, +41/−8）；本段为随后一笔留痕。
- **文件集对账**（`git diff --cached --name-only` 4 项 vs 派单清单）：本册（`**状态**` 待验收→已验证 + 两轮审阅段/残留处置段，未改既有内容）✓；`milestones.md`（流水行置 `已验证` 并移至表首 + 原子链 4 册现状）✓；`issues.yaml`（`ISS-307` `closed` + `resolved_by` + ④ 段；`ISS-294` 前笔已 closed）✓；`lessons.md`（新增 §2.43）✓ —— **漏提 0 / 多提 0 / 越界 0**。
- **门控**：`make check`（L1）**rc=0**（`repository checks (L1): PASS`；含 `check-milestones-fresh` 24 行 PASS / `check-knowledge-refs` 0 悬空 / `check-run-artifacts` 860 文件 0 illegal / `check_issues` 55 open·30 closed、`resolved_by` 约束 OK）；日志 `/tmp/opencode/056t-complete/L1.log`。未跑 `install-host`/`build-*`/L2/L3。
