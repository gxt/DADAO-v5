# INFRA-100t: musl 真原子（`a_cas` / `a_cas_p` / `a_barrier` 落 `lr/sc`+`fence`）

**模块**：infra
**项目里程碑**：M9
**依赖**：`QEMU-067t`（②；`lr/sc`/`fence` 执行语义）、`LLVM-121t`（①；clang 须能产出 `lr/sc`/`fence` 且不落 libcall）、`INFRA-095t`（musl `__clone` + TP；`src/thread/dadao/*.s` 与 `REPLACED_OBJS` 先例）、`ISS-294`（假原子根因，本册为其实现落点）、`ISS-307`（本批 4 册总账）
**状态**：已验证

## 执行环境
**执行环境**：本地

> **编号（现场取号，2026-10-21）**：`infra` 模块现有最大 = `INFRA-099t` ⇒ 取 **`100`**；`find .tao -name 'INFRA-100*'` = 0 命中。
> **本批位置**：串行链 ① `LLVM-121t` → ② `QEMU-067t` → **③ 本册** → ④ `TESTCASES-056t`；四册同改共享安装根，**禁止并行**。
> **本批边界**：只动 `components/musl/**`；**不改** `spec/` / `contracts/**` / `components/llvm-project/**` / `components/qemu/**` / `tools/testcases/**`。

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 现状（2026-10-21 核）

`components/musl/patches/arch/dadao/atomic_arch.h.patch`（new-file，70 行）现为**单线程假原子**，原文要点（**执行前请逐行复核**）：

1. **文件头**（`.patch:8`）明写 `DADAO atomic primitives -- SINGLE-THREADED, NOT REAL ATOMICS.`，并在 `:8-51` 论证「ISA 的 `lr/sc`/`fence` 是 `scope: excluded` ⇒ 无法表达真 RMW / 硬件屏障」，末尾给「多线程可达后必须替换」的重访触发（指向 `INFRA-082t` 任务书）。
2. **`a_cas`**（`.patch:53-60`）= **普通 load / compare / store** 三步（`int old = *p; if (old == t) *p = s; return old;`）⇒ 多线程下**丢更新**（`ISS-294` 实测：`3×2000` → `5999/5992/5999`；`4×250000` → 15/15 轮 `rc=124`）。
3. **`a_cas_p`**（`.patch:62-69`）= 同形假原子，操作 `void *` 值。
4. **`a_barrier`**（`.patch:71-76`）= `__asm__ __volatile__ ("" : : : "memory")`——**纯编译器屏障**，不发射硬件 `fence`。

### 现场约束（**决定实现形态，务必先读**）

1. **只需 3 个函数**：musl 的 `src/internal/atomic.h` 对 `a_swap`/`a_fetch_add`/`a_fetch_and`/`a_fetch_or`/`a_and`/`a_or`/`a_inc`/`a_dec`/`a_store`/`a_spin`（默认 `a_barrier`）/`a_and_64`/`a_or_64` 均给出**基于 `a_cas` 的通用回退** ⇒ arch 侧只要 `a_cas`/`a_cas_p`/`a_barrier` 三条真原子，其余自动正确（`a_ll`/`a_sc` 可选，不必提供）。
2. **clang 的 DADAO 内联汇编不能替换 `%N`**：模板里写 `%0` 会被打印成**空串**（`INFRA-082t`/`pthread_arch.h` 文件头已记录该限制）。⇒ 必须用「`register <T> x __asm__("rdN")` 绑定物理寄存器 + 模板里**字面**写寄存器名」的既有惯用法（先例：`arch/dadao/pthread_arch.h` 的 `__get_tp()`、`arch/dadao/syscall_arch.h:444-480`）。**禁止**在任何新 asm 模板里用 `%N`。
3. **asm 文件会被自动构建**：musl `Makefile:21-27` 的 `ARCH_GLOBS = $(addsuffix /$(ARCH)/*.[csS],$(SRC_DIRS))`、`SRC_DIRS` 含 `src/*` ⇒ 新增 `src/<dir>/dadao/*.s` 自动进 `ARCH_OBJS`（先例：`INFRA-095t` 的 `src/thread/dadao/clone.s`，经 `REPLACED_OBJS` 替换通用实现）。
4. **指令可用性前置**：`lr.t/sc.t`、`lr.o/sc.o`、`fence` 的汇编支持来自 ①（`LLVM-121t` 的 `.td` + MC），执行语义来自 ②（`QEMU-067t`）。本册开工前两者须 `已验证`。
5. **构建目标**：`make build-musl`（`libc.a` + crt）与 `make build-musl-shared`（PIC `libc.so` + 动态 smoke）**均以 `install-host` 为前提**（`Makefile:573-591`）；`make check-musl-freshness` 校验归档与安装根同源。

## ✅ 已裁定（2026-10-21，用户「甲」）

**裁定原话**：「甲」= **按数据宽度对齐**：`.b`=1 / `.w`=2 / `.t`=4 / `.o`=8 字节自然对齐；不满足 ⇒ **MALIGN**。

> **标签对照（勿混）**：用户裁定编号「甲」= 按数据宽度对齐（即本册旧文「乙」项）；旧文「甲」（全族 8 B）作废。`ADR-0034 D6` 已就地修订、`spec/SimRISC-11 §4.2` 已订正。

**对本册的具体影响**：

- `a_cas`（32 位，`int` 4 B 对象）**用 `lr.t.an` + `sc.t.ar` 直接作用于 `addr`**；**不需要**为锁字做 8 B 填充，也**不需要** `lr.o/sc.o` 掩码合成（旧「甲」形态作废）。
- 前提 = 4 B 对齐（C 的 `int` 对象天然满足）；`a_cas_p` 仍 `lr.o.an`/`sc.o.ar`（8 B 自然对齐，不变）。

## 目标

1. `a_cas`（32 位）改为**真**原子（`lr/sc` 环；形态按上节裁定）。
2. `a_cas_p`（64 位指针）改为真原子：`lr.o.an`+`sc.o.ar` 环，**指针（`rd` bank 值）→ 地址（`rb` bank）用 `rd2rb`**，返回原值（`rd` bank）。
3. `a_barrier` 改为硬件 `fence`（full barrier：`PRED_R|PRED_W|SUCC_R|SUCC_W`，即 `immu18 = 0x00C3`，见 `SimRISC-11 §4.1` 例）。
4. **删掉**文件头「SINGLE-THREADED, NOT REAL ATOMICS」整块与「多线程可达后必须替换」的过期论证；改成「真原子 + 依赖 `lr/sc`/`fence` + 保留粒度/对齐前提」的真实描述（**不得**只删不写）。
5. `build-musl` / `build-musl-shared` / `check-musl-freshness` 绿；`4×250000` 互斥计数**精确** = `1,000,000`；`TESTCASES-047t` 19 目标用例**不回退**。

## 接口规范

**输入**（只读）：
- `components/musl/patches/arch/dadao/atomic_arch.h.patch`（现状）、`src/internal/atomic.h`（通用回退契约：**只要 3 个原语**）、`arch/dadao/pthread_arch.h`（`register ... __asm__("rdN")` 惯用法先例）、`arch/dadao/syscall_arch.h`（多寄存器绑定先例）。
- `SimRISC-11 §4.1/§4.2`（`fence` 立即数常量与 `lr/sc` 语义）、`contract-asm`（`rd2rb`/`rb2rd` 记法）、`contract-abi §1.3`（`rd`/`rb` bank 职责）。
- `Makefile` 的 `build-musl` / `build-musl-shared` / `install-host` / `check-musl-freshness`。

**输出**（交付物）：
1. `components/musl/patches/arch/dadao/atomic_arch.h.patch`：重写 `a_cas`/`a_cas_p`/`a_barrier` + 文件头改写（new-file 补丁：index blob 须重算）。
2. 需要时的 asm 辅助文件：`components/musl/patches/src/.../dadao/*.s`（若选「`lr/sc` 环放 `.s`、header 只做声明」的形态；`Makefile` 的 `ARCH_GLOBS` 自动纳入）+ `series` 同步。
3. `components/musl/changelog.md`（`## M9` 节）+ `series`（`check-patch-tree` 断言）。
4. 探针源码（**不入库**，放 `.work/evidence/INFRA-100t/**` 或 `/tmp/opencode/INFRA-100t/**`）：4 线程 × 250000 互斥计数、`pthread_mutex/cond/sem` 压力、`a_cas`/`a_cas_p` 单线程值对照。
5. `.work/evidence/INFRA-100t/**`（含 `run.sh` 与 `--inject`）+ `.work/log/infra/INFRA-100t/**`；本册完成区。

**约束**：
- **改 musl 后必须 `make build-musl` + `build-musl-shared` + `make install-host`**（安装根 `libc.a`/`libc.so` 新鲜度；`ISS-210`/`ISS-301` 类假绿）；长构建由**主会话**执行。
- **不改** `src/internal/atomic.h`（通用回退即可）；**不加** `a_ll`/`a_sc`（非必需）。
- 探针/期望值**独立 oracle**：期望计数 = `线程数 × 每线程次数`（乘法手算），**不得**从程序自身中间量回填。
- **不得**以「降并发数/抬超时/跳过用例/改 `047t` 分类」当通过。
- 不得引入 `__atomic_*` 内建（会依赖 ①，但本册要证明的是**指令级**原语；用内建会把失败归因掩盖到后端）。

## 设计要点（**不预设唯一实现**，但须覆盖）

### A. `a_cas`（32 位）

两种形态（**择一并记录**）：

1. **内联 asm 环**（首选，性能）：用 `register` 绑定固定物理寄存器（如地址 `rd9`/`rd10`、值 `rd11`/`rd12`），模板中**字面**写指令；循环用模板内局部标签（`.L...`），失败即重试（或返回后由 C 侧重试）。
2. **`.s` 辅助函数 + header 包装**：`src/<dir>/dadao/atomic_cas.s` 导出 `__dadao_a_cas(volatile int *, int, int)`，`atomic_arch.h` 里 `static inline int a_cas(...) { return __dadao_a_cas(p,t,s); }`（多一次调用开销，但实现与调度风险最低）。

- 顺序：`lr.<w>.an` + `sc.<w>.ar`（获取/释放兼具，对应 musl 的锁/发布语义）。
- **已裁定口径（按数据宽度）**：`lr.t`/`sc.t` 直接作用于 `addr`（4 B 对齐即合法；不做 8 B 字掩码合成）—— 见「✅ 已裁定（2026-10-21，用户「甲」）」。
- 返回值语义 = musl 契约：`old`（未写入时的观测值）；比较成功则写入并返回 `old == t`。

### B. `a_cas_p`（64 位指针）

- 入参是 `void *`（`rd` bank 值）⇒ 地址操作数需 `rd2rb`（`contract-asm §4.2`，`immu6` = 复制个数）；
- `lr.o.an` + `sc.o.ar` 环；8 B 自然对齐（`void *` 对象本身满足，仍需记录前提）；
- 返回 `void *`（`rd` bank）：`sc` 的 `rdHB` 只是成功位，**原值**取自 `lr` 的 `rdHC`；如用 `rb` 中转须 `rb2rd` 回 `rd`。
- **不要求**对「未对齐 8 B 的指针槽」做掩码合成（musl 的 `a_cas_p` 目标总是指针大小的对齐槽）——该前提写进文件头注释。

### C. `a_barrier`

```
__asm__ __volatile__("fence <imm>" : : : "memory");
```
`imm = PRED_R|PRED_W|SUCC_R|SUCC_W = 0x00C3`（full barrier；`SimRISC-11 §4.1` 的示例值，编码 `0x778000C3`）。**保留** `"memory"` clobber（编译器侧仍需）。若用户/实现需要更强（含 I/O），可用 `0x03CF`（`pred/succ` 全类型）——须在完成区记录所选值。

### D. 文件头改写（**不是删了就算**）

新头注释须写清：① 真原子，依赖 `lr/sc`（`ADR-0034` 编码，`QEMU-067t` 语义）与 `fence`；② 保留粒度 = 精确 8 B（宿主 CAS 实现所致）与 spurious-failure 可重试；③ 对齐前提（按数据宽度：`a_cas` 的 `.t` 需 4 B、`a_cas_p` 的 `.o` 需 8 B 自然对齐）；④ `a_cas_p` 的 `rd`/`rb` bank 转换说明；⑤ 已知上限（如 ABA 等价写入检不出）。

## 验收标准

1. **并发计数（硬指标）**：4 线程 × 250000 次互斥自增，`pthread_mutex` + 共享 `int`，静态档与动态档各 ≥5 轮 ⇒ 计数**每轮精确 = 1,000,000**（独立 oracle = 乘法），无超时（`rc=124` 计 FAIL）。
2. **单线程值对照**（独立 oracle）：`a_cas`/`a_cas_p` 的「命中/不命中」两路返回值与内存副作用，按 musl 契约手算断言（不经 `__atomic_*`）。
3. **同步原语压力**：`pthread_mutex` / `pthread_cond`（signal+broadcast）/ `sem_t` 各 2 线程 × 10^5 次，值/顺序断言精确。
4. **不回退**：`TESTCASES-047t` 的 **19 条**线程目标用例（清单见 `TESTCASES-052t` 册内）静态/动态两档仍 **19/19 pass**（`--filter` + `--json-out`，逐例比对，禁抽样）。
5. **构建与门控**：`make install-host`（主会话）→ `make build-musl` + `make build-musl-shared` 均 rc=0 → `make check-musl-freshness` PASS → `make check`（L1）绿。
6. **头部声明核对**：`grep -c 'SINGLE-THREADED\|NOT REAL ATOMICS'` = **0**；`grep` 到 `fence` 与 `lr.`/`sc.` 指令助记符在实现中。

## 做（阶段）

- **阶段 0 现场复核**：打印 `atomic_arch.h.patch` 的三段实现与头部；确认 ①/② 均 `已验证`；记录基线（`4×250000` 现状 = `ISS-294` 实测，`047t` 19/19 现状）。
- **阶段 A `a_barrier`**：`fence` 落地 + 探针（编译器屏障 → 硬件屏障可观测的部分由 ② 的 fence 向量覆盖）。
- **阶段 B `a_cas`**：按裁定形态实现 + 单线程值对照 → 并发计数 → 压力。
- **阶段 C `a_cas_p`**：`rd2rb` 转换 + `lr.o/sc.o` 环 + 单线程值对照（含「指针值相等/不等」两路）。
- **阶段 D 收口**：重建 musl（`build-musl`/`build-musl-shared`，主会话）+ `check-musl-freshness` + `047t` 19 目标两档 + `make check`（L1）+ 证据脚本 `--inject` 反例 → 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

1. 把 `a_cas` 退回「普通 load/compare/store」⇒ 并发计数**丢更新**（≠ 1,000,000）或 hang ⇒ **红**（同时复现 `ISS-294` 现场）。
2. `a_cas_p` 漏 `rd2rb`（直接把 `rd` 值当地址用）⇒ 指针 CAS 值错/崩溃 ⇒ 单线程值对照与压力项 **红**。
3. `a_barrier` 退回 `"" ::: "memory"`（无 `fence`）⇒ ①能力断言红（`grep` 不到 `fence`）且并发压力**在弱内存一致宿主上可出现乱序**（若该轮不红须显式说明，不得把「不红」当「等价」）。
4. `sc` 环里把「失败重试」写成「失败即返回旧值」⇒ 并发计数**偏小** ⇒ 红。

## 已知边界（**披露**）

- **保留粒度 = 精确 8 B**（② 的宿主 CAS 实现）⇒ 规范允许；`a_cas` 的宿主 CAS 落在含该 int 的 8 B 字上（保留状态以 8 B 字为单位）⇒ **同一 8 B 字内的两个 int 会互相干扰**（一个 CAS 成功会使另一个 CAS 的保留失效 = spurious failure ⇒ 只影响性能，不影响正确性）。**须写进文件头**。
- **ABA 等价写入**（另一 hart 写成相同值）本实现检不出（② 同源限制）——写入文件头的「已知上限」。
- `spec/` 与 `contracts/**` **不改**（`scope: excluded` 的 re-scope 不在本批，见 ①/② 的「已知边界」）。
- `a_ll`/`a_sc` 不提供（musl 通用回退足够）；若 `047t` 出现需要它们的用例 ⇒ **停下报告**，不得默默加。

## 完成区
**测试结果**：`build-musl` rc=0（12.2 s，10/10 ELF 检查）、`build-musl-shared` rc=0（13.5 s）、`check-musl-freshness` PASS。核心硬指标（独立 oracle = 乘法手算 `4×250000`）：**静态 5/5 轮、动态 5/5 轮 `COUNT=1000000`**，全部 rc=0。直接 `a_cas` 自旋锁 4×250000：静态 3/3、动态 3/3 均 `COUNT=1000000`（另单独记录 `SPINS` 静态 106195、动态 161011）。`sync_stress` 两档：mutex `200000`、cond `consumed=100000/order_errors=0`、sem `100000/final value=0`。`047t` 19 例：静态 **19/19 pass**、动态 **19/19 pass**（`--filter` + 必填 `--json-out`；`fail=0`、`blocked=0`）。`cas_values` 两档 34 项单线程契约全 PASS（含 `-1`/`INT_MIN`、offset-4 的 int、`0xdeadbeefcafebabe` 宽指针）。证据脚本 `run.sh --all`：**164/164 checks、`EVIDENCE_RESULT: PASS`、rc=0**。
**修改文件**：`components/musl/patches/arch/dadao/atomic_arch.h.patch`（new-file 重写 70→138 行，index blob `640f910`→`478acd9`）；`components/musl/changelog.md`（M9 条目）；`series` **24 不变**（无新增补丁）；组件工作树 `.work/source/musl/arch/dadao/atomic_arch.h`（E1：base+1 且干净，HEAD 见 `git -C .work/source/musl log`）；`.work/evidence/INFRA-100t/{run.sh,inject.py,cas_values.c,spin_count.c,mt_count.c,sync_stress.c}`；本册完成区/自审。
**验收结果**：`check-patch-tree` rc=0（**5 components / 185 patches OK**；同一文件重写 ⇒ 计数 185 不变）；`check-index-blobs`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-musl-freshness`/`check_issues.py` 均 rc=0；`make check`（L1）rc=0（"repository checks (L1): PASS"）。头部声明核对：`grep -c 'SINGLE-THREADED\|NOT REAL ATOMICS'` = **0**；`fence 975`/`lr.t.an`/`sc.t.ar`/`lr.o.an`/`sc.o.ar`/`ext.uo …,31` 各 1 处；无 `a_ll`/`a_sc` 定义；代码无 `__atomic_*`/`__sync_*`（唯一命中是注释里"不使用"的说明）。**注入 4 处（≥2 要求，全部真红→`cp`+md5 还原→回绿）**：① `a_cas` 退回普通 load/store ⇒ 自旋计数 `COUNT=436431`（rc=1）；② `sc` 失败不重试 ⇒ `COUNT=704421`（rc=1）；③ `a_cas_p` 落 32 位 `.t` ⇒ 宽指针 `0xdeadbeef…` 截成 `0xdeadbeef`（7 条 FAIL，rc=1）；④ `a_cas_p` 基址改 RD bank（丢 `rd2rb`）⇒ 汇编期 `invalid operand`（build rc=2，4 条诊断）。
**新发现/坑**：① `lr.t` **零扩展** 32 位，而 `contract-abi §4.2` 要求 caller 对 `int` 实参**符号扩展**；两套约定混用会让"符号扩展的比较值 vs 零扩展的 `lr.t`"永不相等并静默丢写 ⇒ 比较前统一 `ext.uo {rd11},{rd11},31`。**实测当前后端把 `int` 实参实例化为零扩展**（`set.zw`+`or.w` = `0x00000000FFFFFFFF`，非 canonical 有符号），故该指令是**防御项**而非修复项（删掉它 4 处注入/probe 仍全绿，已实测）；但后端与 `contract-abi §4.2` 的这一偏差值得单独登记（疑为 LLVM 侧 ABI 缺口，非本册范围）。② LLVM 全屏障 = **`fence 975` = `0x3CF`**（pred=succ=R|W|I|O），非任务书 §C 举例的 `0x00C3`；取 975 与后端 `getDADAOFenceImm` 一致，已写进文件头。③ 注入脚本首版写 `ld.ut rd,[rb]` 被汇编拒绝（ld/st 的地址形如 `[rb, imm]`），改 `[rb9, 0]`。④ `components/musl/README.md`「原子」段仍写"机器没有可用原子"——**本册未改**（不在交付清单），属文档漂移，建议后续同步。⑤ 保留粒度 8 B：同 8 B 字内两个 int 互致 spurious failure，实测 `SPINS` 非零但计数精确（仅重试，不丢更新）。
**遗留问题**：无（`install-host` 按分工由主会话执行；README 漂移见「新发现」④）。

## 审阅记录

#### 第 1 轮 engineer 自审
> 方式：自主逐行审查（全局 `subagent_depth=1`，engineer 不能起嵌套子代理）。范围：新增 `atomic_arch.h` 全文、导出补丁、`inject.py`/`run.sh`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 比较寄存器 `t` 的 64 位表示可能与 `lr.t` 的零扩展不一致（契约 §4.2 允许/要求符号扩展） | ✅已修（防御） | `a_cas` 比较前加 `ext.uo {rd11},{rd11},31`（`"+r"(want)` 允许写回），文件头据实说明"当前后端已零扩展 ⇒ 本指令是防御" | `cas_values` 的 `-1`/`-2`/`INT_MIN`/`load-fed` 两档全 PASS；**反例实测**：删该指令后 4 处 probe 仍绿（后端零扩展）⇒ 不谎称它是 load-bearing，改登记后端与契约 §4.2 的偏差 |
| F7 后端把 `int` 实参实例化为零扩展（`set.zw`+`or.w`），与 `contract-abi §4.2`「caller 按符号性扩展为 canonical 64 位」不符 | ⏸延后（越界） | 无改动（不在本册边界：`components/llvm-project/**` 禁改） | `clang -O2 -S` 现场：`ext(&x, -1, 5)` → `set.zw rd16, wp0, 0xffff` + `or.w rd16, wp1, 0xffff` = `0x00000000FFFFFFFF`；已写入「新发现」①，交主会话决定是否立 issue/任务 |
| F2 任务书 §C 的 `0x00C3` 与后端全屏障不一致 | ✅已修（按后端/规范取 975） | `fence 975`，文件头写明 `0x3CF` 与 `atomics-fence.ll` 一致 | `llvm-mc -show-encoding` = `[0x77,0x80,0x03,0xcf]`；`grep -c 'fence 975" : : :'`=1 |
| F3 证据脚本 `grep -c 'fence 975'` 把注释算进去（=2） | ✅已修 | 改为匹配 `fence 975" : : :` | `run.sh` 该项 PASS（164/164） |
| F4 注入脚本对 `br.nz` 的全局唯一性假设不成立（两处 lr/sc 环）且 `ld.ut rd,[rb]` 语法非法 | ✅已修 | `inject.py` 改为按 `#define a_cas` / `a_cas_p` / `a_barrier` 分块替换；地址写 `[rb9, 0]`；每处替换断言"恰好 1 次" | 4 个注入模式均"applied"且 `git diff --name-only` 非空；`cas_plain` 编过并跑出 `COUNT=436431`（终跑） |
| F5 内联汇编是否声明了全部被写寄存器（未声明 clobber 会踩 live 值） | ✅不修（已正确） | 无改动 | 模板只触碰 `rd10/rd11/rd12/rd13/rb9`，全部为操作数（`=r`/`+r`/`r`）；`-O2` 反汇编确认输入被搬到指定物理寄存器，且 4 线程压测 5/5 精确 |
| F6 `components/musl/README.md` 的「无真原子」表述过期 | ⏸延后（越界） | 无改动（任务交付清单不含 README） | 已写入「新发现」④，交主会话决定是否另立文档任务 |

#### 第 1 轮 reviewer 验收
> 方式：独立重跑（`run.sh --all` reviewer 执行 1 次）+ 三原语汇编抽验 + 独立注入 1 次 + 门控重跑；判决全部基于我方命令输出，不采信完成区转述。快照对账：验收前 `git status --porcelain -uall` = 空、补丁 md5 `f3c2b3d0…`；验收后 = 空（仅本记录）、musl 工作树 `git diff` 空、`atomic_arch.h` md5 回 `e1e38a2d…`（注入均 `cp`+md5 还原 ✓）。

**重跑记录（真实输出/退出码）**：`bash .work/evidence/INFRA-100t/run.sh --all` ⇒ **164/164 passed、`EVIDENCE_RESULT: PASS`、rc=0**（与完成区 164/164 一致）。`mt_count` 4×250000（oracle = `$((4*250000))` + 源码 `NTHREADS*NITER`）：静态 5/5、动态 5/5 全 `COUNT=1000000` rc=0；`spin_count` 回绿 3+3 轮均 1000000；`sync_stress` 两档 mutex 200000 / cond 100000（order_errors=0）/ sem 100000（final 0）。`047t` 我方重跑（json 现场读）：static/dynamic 均 `total=19 pass=19 fail=0 blocked=0` ⇒ 两档 19/19 ✓。注入 4 例（我方重跑逐例真红→`cp`+md5→回绿）：`cas_plain` 红 `COUNT=431238` rc=1；`cas_no_retry` 红 `COUNT=712053` rc=1；`cas_p_width` 红 7 FAIL 行（计数器 8，见披露）；`cas_p_bank` 汇编期 rc=2（4 条诊断）；每例 restore md5 相等、`git diff` 空、重建 rc=0、回绿。
**独立注入（reviewer 自选，异于 engineer 4 例）**：`a_cas` 删 `br.ne`（CAS 退化为无条件写）⇒ `make build-musl` rc=0、spin 探针 **rc=139 段错误（红）** ⇒ `cp` 还原 md5 `e1e38a2d…` 相等、`git -C .work/source/musl diff` 空 ⇒ 重建后 `COUNT=1000000` rc=0（回绿）。副作用处置：静态重建清构建树 `libc.so` 致 `check-musl-freshness` 红 1 次（rc=2），补跑 `build-musl-shared` rc=0 后 PASS——musl 静/动态配置切换的固有行为，非本册缺陷（run.sh 末尾跑 shared 即为此）。
**门控（我方重跑）**：`check-patch-tree` rc=0（5 components/185 patches OK）、`check-musl-freshness` rc=0 PASS、`make check`（L1）rc=0（"repository checks (L1): PASS"）。证据脚本审核：每条断言有可达 FAIL 路径、无恒真/两支同果、注入断言"恰 1 处"防静默空转、退出码直取未被管道吞 ⇒ **脚本合格**。
**三原语自验（我方 `clang -O2 -S` 抽汇编）**：`a_cas` = `ext.uo rd11,31` → `lr.t.an rd10,[rb9]` → `br.ne{rd10,rd11}→2f` → `sc.t.ar rd13,rd12,[rb9]` → `br.nz{rd13}→1b` 重试环 ✓、返回 `rd10`=旧值（musl 契约）✓；`a_cas_p` = `lr.o.an`/`sc.o.ar` 8 B ✓，指针基址 `rb2rb rb9←rb16`（**指针走 rb**）、值侧 `rb2rd`、返回 `rd2rb rb8←rd10` ✓；`a_barrier` = `fence 975`（`llvm-mc` 编码 `[0x77,0x80,0x03,0xcf]`=`0x3CF` 全类型 = 任务书 §C 的 `0x03CF` 档）+ `"memory"` clobber ✓。**文件头**：补丁与应用侧 `grep -c 'SINGLE-THREADED\|NOT REAL ATOMICS'` 均 **0**；84 行真原子描述头（语义/对齐/8 B 粒度/ABA/bank/防御项）在场 ⇒ 非只删不写 ✓；无 `a_ll`/`a_sc`、无 `__atomic_*`/`__sync_*` 代码 ✓；补丁与 `.work/source/musl` 应用文件逐行一致 ✓。
**ISS-310 复核（我方独立现场）**：`ext(x,-1,5)` → 汇编 `set.zw rd17,wp0,0xffff`+`or.w rd17,wp1,0xffff` = `0x00000000FFFFFFFF`（零扩展）；IR `declare @ext(i32 noundef,…)` **无 `signext`**（返回路径有 `signext i32`）；`contract-abi.md §4.2` 原文要求窄参数「保持符号位不变」「按类型符号性扩展为 canonical 64 位」且由 caller 完成 ⇒ **真缺陷（契约偏差），ISS-310 登记正确、应保持 open**；P2 合理（无实测错值，`a_cas` 的 `ext.uo` 使其不依赖本项）。
**约束逐条**：不改 `spec/`/`contracts/**`/llvm/qemu（WIP 提交文件清单核过）✓；未降并发/跳用例/改 047t 分类 ✓；独立 oracle = 乘法手算 ✓；模板无 `%N` ✓。**披露（不阻断）**：`cas_p_width` 红时 FAIL 行 7 vs 计数器 8，完成区写「7 条」略低估，红向与结论无碍。**判决：Accepted**。未改任何代码、未提交 git。

#### 提交（architect）
- 档位：**正常提交**（reviewer 判决 Accepted）⇒ `INFRA-100t 验收收尾（reviewer Accepted；ISS-310 经复核确认为真缺陷）`；`--cached` 对账 = 本册 + `milestones.md` + `issues.yaml` + `lessons.md`，与收尾范围一致（无漏提 / 多提 / 越界）；**未 `push`**。
