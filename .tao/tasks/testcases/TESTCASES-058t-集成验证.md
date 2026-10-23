# TESTCASES-058t: `fma` 集成验证（单次舍入对拍 / 点积与 GEMM / Horner 零拷贝）

**模块**：testcases
**项目里程碑**：M9（FP 完备性）
**依赖**：`SPEC-158t`、`LLVM-123t`、`QEMU-070t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么要单独验"单次舍入"

- `fma` 与 `mul+add` **不等价**：前者只舍入一次。若实现或选择退化为两条，**普通用例多数仍对**，只有特定输入暴露 ⇒ 必须有**针对性反例**，否则等于没测。
- 期望值须**独立**：用 Python `fractions.Fraction`（精确有理数）+ 一次 IEEE 舍入算出，**不得**从 QEMU/LLVM 结果反推（`AGENTS.md`「Independent oracle」）。

### 现场事实（2026-10-21 核，执行前须复核）

- 集成范式：`tools/testcases/run_atomics_probe.py` + `oracle_atomics.py`（probe + 独立 oracle + 两档）；本册照此结构。
- 目标上 `double`/`float` 已完整（`fo`/`ft`）；`unsigned __int128` 可用。
- 四操作数语义 ⇒ **所有形态零拷贝**（`acc += a*b`、`fma(a,b,c)`、Horner 均 1 条、无 `rf2rf`）；`LLVM-123t` 已在 lit 断言，本册做端到端复核。
- `check-testcases-suites`（L2 fast）耗时预算须现场测后定层（`Process-07 §3`）。

## 目标

1. **指令级**：单次舍入反例 + 特殊值 + 四种舍入模式，与独立 oracle 逐例相等；
2. **算法级**：点积 / 小型 GEMM（double）结果与 oracle 在**给定误差界**内一致；Horner 多项式与 oracle 相等；
3. 代码形态断言：循环累加编译结果 **1 条 `fofma`**（可选，若 `llc` 可用则做）；
4. 用例能失败（≥2 条真实注入），耗时可控（定层有实测依据）。

## 接口规范

- **输入**：`tests/` 新增 C 用例 + `tools/testcases/` probe/oracle；`Makefile`（如需新目标或纳入 `check-testcases-suites`）。
- **输出**：`tools/testcases/run_fma_probe.py`（编译 → QEMU → 比对，两档 `-O0`/`-O2`）、`tools/testcases/oracle_fma.py`（`fractions` 精确 + 一次舍入；含自检）、C 用例（`fma_edges.c`、`fma_dot.c`、`fma_horner.c`）、证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改 `spec/`/`contracts/`；不引入外部库（OpenSSL/zlib）；不改判定语义；不 commit/push。

## 设计要点（**不预设唯一实现**）

### A. 单次舍入反例（核心）

- 构造：取 `a = 1 + 2^-23`（单）/`1 + 2^-52`（双），`b = a`，`c = -1`：
  - 精确 `a×b + c = 2^-22 + 2^-46`（单）⇒ 一次舍入与两次舍入结果**不同**；
- 至少 **4 组**这类反例（单/双各 2 组），每组的两个候选结果（fma / mul+add）必须**互相不同**——用例先自检这一点，否则该例无效。

### B. 特殊值与模式

- `±0`、`±Inf`、qNaN、sNaN、次正规；
- 四种舍入模式（`rf0[33:32]`：RN/RZ/RP/RM）各 ≥1 例，选会被模式影响的值；
- `sNaN` 输入 ⇒ NV 置位且结果为 qNaN（用 `rf0` 读标志验证，若 C 层无接口则用内联汇编读取）。

### C. 算法级

- **点积**：长度 16/64/256 的随机向量（种子固定），与 oracle 的**逐步 fma**（同样单次舍入）逐位相等；
- **小型 GEMM**：4×4 × 4×4（double），与 oracle 相等；
- **Horner**：5/9 次多项式，与 oracle 相等；
- 误差界：算法级若用不同求和顺序，须给**明确误差界**（相对 ≤ k·u），不得写"近似相等"这类不可判断言。

### D. 定层

- 先单跑测总耗时；≤ fast 预算 ⇒ 纳入 `check-testcases-suites`（L2）；否则单列按需目标并在完成区写明实测值（`Process-07 §3`）。

## 验收标准

1. 指令级（含 4 组单次舍入反例）+ 特殊值 + 四模式全绿，**两档优化级**。
2. 点积 / GEMM / Horner 全绿（误差界明写）。
3. 计数现场派生；失败/跳过分列，禁静默跳过。
4. **可达 FAIL ≥ 2**：① 把实现退化为 `fomul`+`foadd`（临时）⇒ 单次舍入反例红；② 翻转 oracle 的一个期望位 ⇒ 红。
5. `make check-modules`（L2）rc=0（若纳入）或 L1 + 单目标 rc=0（若不纳入）。
6. 证据脚本一键复跑、真实 rc 落盘（禁 `cmd | tee` 吞码）。
7. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（atom probe 结构、两档口径、`rf0` 读取方式、fast 预算）。
2. 写 oracle（`fractions` + 一次舍入）+ 自检（fma 与 mul+add 必须不同）。
3. 指令级 → 特殊值/模式 → 点积/GEMM/Horner。
4. 两档跑 + 耗时测 + 定层 + 反例注入。
5. L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 临时把 C 侧 `fma()` 换成 `a*b+c` ⇒ 反例红；还原 ⇒ 绿。
- 改 oracle 一组期望（`cp` 备份 + md5）⇒ 红；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不做性能基准（只做正确性 + 代码形态断言）；
- 不做 `fmsub`/`fnmadd` 用例（指令未立）；不做 libm 精度对比（`fma` 只保证单次舍入）。
- 不引入外部数学库。

## 完成区

**测试结果**：`.work/evidence/TESTCASES-058t/run.sh`：oracle 自检 **32/32**；probe **O0 626/626**、**O2 626/626**（观测 72 条、算法记录 25 条，两档计数现场派生一致）；注入模式 **634/634**（4 类注入全红 + 复原回绿）；`check-fma-probe` / `validate-vectors` / `check_qemu_trans --strict`（**266/266**）各 rc=0。

**修改文件**：
- 新增 `tools/testcases/oracle_fma.py`（Fraction 精确 + 一次舍入，`--selftest` 32/32）、`tools/testcases/run_fma_probe.py`（两档 + 注入）、`tests/fma/{fma_common.h,fma_edges.c,fma_dot.c,fma_horner.c}`；证据 `.work/evidence/TESTCASES-058t/run.sh`（`.work/` 不入库）
- 修改 `Makefile`（新增 `check-fma-probe`：L2 `check-modules` + 门控锁 + help）
- 覆盖披露：新增 C 用例 **3**（edges/dot/horner；72 观测 + 25 算法记录）、oracle/driver **2**、L2 目标 **1**；**删除 0**、修改既有用例 **0**

**验收结果**：
- 单次舍入判别 6 例（单/双各 3）：ft `(1+2⁻²³)(1−2⁻²³)−1` 融合 **0xA8800000** / 两步 **0x0**；fo `(1+2⁻⁵²)(1−2⁻⁵²)−1` 融合 **0xB970000000000000** / **0x0**；ft 平方 0x28800000/0x0、fo 平方 0x3970000000000000/0x0；ft/fo both 0x34000001/0x34000000、0xBCDFFFFFFFFFFFFFFC/0xBCE0000000000000
- 形态：C `fma`/`fmaf`、`acc += a*b`（LLVM 收缩）、Horner（5/9 双、5 单）、点积 16/64/256（两种写法、逐步哈希）、GEMM 4×4；**值与 rf0[4:0] 双断言**（NV/NX/OF/UF；四舍入方向各 ≥1 例）
- 无 libcall：3 个对象 `llvm-nm -u` 无 fma/fmaf/fmal、链接镜像无该符号、`objdump -dr` 无 `R_* fma` 重定位（9 项全空）
- 指令选择（O0/O2）：`sel_fma` 恰 1 `fofma` + 1 `ftfma`、0 `fomul/foadd/rf2rf`；`dot_fma_run`/`dot_contract_run`/`gemm4`/`horner_d`/`horner_f` 均 ≥1 融合且 0 两步；`sel_two_step` 含 `fomul`+`foadd`（计数正控）
- 注入（可达 FAIL，均复原）：① oracle 期望改两步值 ⇒ 6/6 红；② sNaN NV 改 0 ⇒ 4/4 红；③ C `fma`→`a*b+c` ⇒ 6/6 红；④ `llvm.fma`→`fmul`+`fadd`（IR 层降级＝lowering 退化）⇒ `sel_fma` 0 融合、判别 6/6 红
- 门控：`make check`（L1）**rc=0**；`make check-modules`（L2，含 check-fma-probe）**rc=0**；实测 ≈0.6 s/档 ⇒ 定层 **L2**

**新发现/坑**：① `-fno-builtin`（沿用其它 probe）会把 C `fma` 打回 musl libcall（O0 实测 `call [rb0,0]`、镜像出现 musl `fma`）⇒ 本册必须去掉该 flag；② -O2 常量折叠 `fma()`（flags 读 0）⇒ 操作数须不透明化；③ 循环后的 `rf2rd` 会被上提到循环前 ⇒ post 读须依赖结果；④ 长点积融合/两步**末值可能相同**（末 ulp 吞掉差异）⇒ 算法级用逐步哈希而非仅末值

**遗留问题**：无（未改 ISA/QEMU/LLVM；`fmsub`/性能基准按任务边界不做）

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 engineer 自审（2026-10-23，自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `-fno-builtin`（照抄其它 probe）使 C `fma` 在 -O0 退化为 musl libcall（`call [rb0,0]`、镜像含 musl `fma`） | ✅已修 | `run_fma_probe.compile_flags` 去掉该 flag 并注释原因 | O0/O2 `sel_fma` = 1 fofma + 1 ftfma；9 项 libcall 断言空 |
| F2 -O2 常量折叠 `fma(const,…)` ⇒ 无指令、flags 读 0（假红） | ✅已修 | `fma_hide`（空 asm 不透明化）用于 `fma_c`/`fma_two_step`/`fma_contract`/`sel_*` | O2 `cpath/c_disc_ft` 值 + NX 正确；626/626 |
| F3 循环后的 `rf2rd` 被上提到循环前 ⇒ 读到 0 标志 | ✅已修 | `fma_rd_rf0_dep(dep)`（结果作输入依赖）+ 各 rf0 助手加 `memory` clobber | dot/horner flags 断言两档全绿 |
| F4 初版判别例 `ft_square`/`fo_sub` 实际不判别（融合=两步） | ✅已修 | 换为 `c=-(1+2⁻²²)`/`-(1+2⁻⁵¹)` 与 `both` 例（oracle 自检"必须不同"把关） | selftest 6/6 判别例 `fused!=two-step` |
| F5 `_ratio_bits` 丢符号；`horner_expect` 用 fo 位型生成 ft 数据 | ✅已修 | 有符号 Fraction 编码；`gen_bits(..., fmt)` 传格式 | dot/horner `data stream` 哈希两档绿 |
| F6 libcall 扫描正则误中自身符号（`sel_fma`/`dot_fma_run`） | ✅已修 | 改为 `nm` 末列精确名 + 新增 `objdump -dr` 重定位断言 | 9 项 libcall 断言 actual=[] |
| F7 `judge_init`/`judge_restore` 返回 list 未逐条登记；cpath 组不打印 step 却在两步组内 | ✅已修 | 逐条登记；`TWO_STEP_GROUPS` 去 cpath | 626/626 两档 |
| F8 注入 `_mutate` 在 src==dst 时 md5 比较失真；C 侧锚点引用后置函数 ⇒ 编译红 | ✅已修 | 先取 md5 再写；注入体改为内联两步表达式 | 注入 634/634；源 md5 未变 |
| F9 IR 注入正则只匹配 `tail call`，-O0 无 tail ⇒ 重写 0 次 | ✅已修 | `(?:tail )?call` | O0/O2 各重写 4/6 处并红 |
| F10 GEMM 未断言 flags（任务要求四形态走 flags） | ✅已修 | 探针输出 pre/post；oracle 累积 16×4 步 flags | gemm flags 断言两档绿 |
| F11 验收项③要求"注入到 lowering"；本册用 IR 层降级（等价 ISel 输入） | ❌不修（附理由） | 任务硬约束"不改 LLVM 实现"+ 全量重建成本；降级后实测 `sel_fma` 0 fofma/0 ftfma、1 fomul/1 foadd，判别 6/6 红 | 注入证据见完成区④ |

判决：F1–F10 全部修复，F11 为方法选择（已披露并有等价证据）；无未修缺陷。状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-23，独立重跑）

**重跑记录（本人命令 + 真实输出/退出码）**
- oracle 自检：`python3 tools/testcases/oracle_fma.py --selftest` → rc=0，`total=32 pass=32 fail=0`
- 两档 probe：`run_fma_probe.py --opt O0/O2` → 各 rc=0，`total=626 pass=626 fail=0 observations=72 algorithm=25`（两档计数现场派生一致，与完成区一致）
- 门控：`check_qemu_trans --strict` rc=0（`266/266 insns have trans impl; orphan 0`）；`make validate-vectors` rc=0；`make check`(L1) rc=0；`make check-fma-probe` rc=0；`make check-modules`(L2，含 check-fma-probe) rc=0（8m40s）
- 证据脚本 `.work/evidence/TESTCASES-058t/run.sh --no-gates` 本人重跑 rc=0（其内 4 类注入两档全红签名 6/6、4/4、6/6、6/6）

**独立核验**
- 手推 2 组（IEEE + spec §2.5，不经 oracle）：ft `(1+2⁻²³)(1−2⁻²³)−1` 精确积 `1−2⁻⁴⁶`、和 `−2⁻⁴⁶` 精确可表示 ⇒ **0xA8800000**，两步（积先舍入为 1）⇒ **0x0**；fo `(1+2⁻⁵²)(1−2⁻⁵²)−1` ⇒ **0xB970000000000000** / 两步 **0x0** —— 与用例期望、实测输出逐位一致
- oracle 独立性：`oracle_fma.py` 仅用 `fractions.Fraction` 精确算术 + 单次整数舍入，无 softfloat/宿主 `fma`/ctypes/子进程调用（selftest 的宿主对照是 `struct.pack` 转换，非 fma）
- libcall（本人 `nm -u` + `objdump -dr`，3 对象×两档×3 项）：无 `fma/fmaf/fmal` 未定义符号、镜像无该符号、无 `R_* fma` 重定位；`sel_fma` O0/O2 各恰 1 `fofma`+1 `ftfma`、0 `fomul/foadd/rf2rf`；`sel_two_step` 1 `fomul`+1 `foadd`（正控成立）
- 覆盖披露属实：`git diff --name-status 99cd4068~1..99cd4068 -- tests/` = 4 A（3 C 用例 + 1 头）、**删除 0、修改既有 0**；tools/ 2 A；Makefile 仅增 `check-fma-probe`（PHONY/门控锁/help/L2 挂接）；`-- components/ spec/ contracts/` diff 为空（未改实现）
- 注入 3 次（`cp` 备份 + md5 还原，还原后 md5 与注入前一致、重跑回绿 626/626）：① oracle 期望改两步值（源级）⇒ rc=1、disc **6/6 红**；② sNaN NV 期望改 0 ⇒ rc=1、special flags **4/4 红**（实测 guest NV=0x01）；③ `fma_common.h` C `fma`→volatile `a*b+c` ⇒ O0/O2 各 rc=1、disc 值 **6/6 红**（实测值=两步值）

**约束核验**：不改 spec/contracts ✓；无外部库 ✓；注入不污染仓库（工作树快照 + md5 对账全 OK、`git status` 干净）✓；脚本无吞码（`rc=$?` 直取）✓。

**判决：Accepted**（期望值与 spec 相符、oracle 无循环论证、libcall 已消除、注入全红、覆盖未删、门控全绿）；无阻断项。
