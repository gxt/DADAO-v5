# TESTCASES-057t: `clmul` 集成验证（GHASH / CRC-32C / `__int128` 对拍）

**模块**：testcases
**项目里程碑**：M9
**依赖**：`QEMU-068t`（执行语义 + 解除 `excluded`）、`LLVM-122t`（`llvm.clmul` / `llvm.dadao.clmul` / `__builtin_dadao_clmul`）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 为什么是这三类用例

- `ADR-0035 D1` 的立项判据 = **目标应用域能力需求 + 软硬件代价比**（语料频次**不作**否决依据）；目标域明说「以后肯定要支持加解密和网络」。
- `clmul` 是 **GHASH（GCM 认证）**、**CRC（Barrett 约减）**、**Reed-Solomon** 的公共原语 ⇒ 集成验证须覆盖「真实算法能跑通」，而不只是「单条指令结果对」。

### 现场事实（2026-10-21 核，执行前须复核）

- 指令级 oracle 必须**独立**：**不得**从 QEMU/LLVM 生成期望值（`AGENTS.md`「Independent oracle」）。
- 现有集成范式：`tools/testcases/run_atomics_probe.py` + `oracle_atomics.py`（原子链，711 例，两档）⇒ **本册照同一结构**（probe + 独立 oracle + 两档）。
- 目标上 `unsigned __int128` 已完整支持（`mul.uo` 双目的 + `UMUL_LOHI_PSEUDO`）⇒ GHASH 的 128 位状态无需软件拼接即可表达。
- `check-testcases-suites`（L2，fast）与 `--stage full` 的耗时预算见 `Makefile`；新用例是否进 fast **须现场测耗时后裁定**（不写死假设）。

## ✅ 已裁定（2026-10-21）

- 可达路径 = 通用 `llvm.clmul` + 私有 `llvm.dadao.clmul` + `__builtin_dadao_clmul`（用户原话，见 `LLVM-122t`）⇒ 集成用例**以 `__builtin_dadao_clmul` 为主路径**，并各留 ≥1 例走通用 `llvm.clmul`（IR 级）。
- 本册**不**引入 OpenSSL / zlib 等外部库（工具链与依赖面不受控）。

## 目标

1. **指令级**：`clmul` 边界与随机对拍（独立 oracle）；
2. **算法级**：GHASH（GF(2^128) 乘）端到端正确；CRC-32C（Castagnoli）用 `clmul` 实现并与独立参考对拍；
3. 用例**能失败**（≥2 条真实注入），且耗时可控（进 L2 与否有实测依据）。

## 接口规范

- **输入**：`tests/` 下新增 C 用例 + 驱动器；`tools/testcases/`（probe + oracle）；`Makefile`（如需新目标或纳入 `check-testcases-suites`）。
- **输出**：
  1. `tools/testcases/run_clmul_probe.py`（编译 → QEMU 运行 → 与 oracle 比对；两档优化级，口径照原子链）；
  2. `tools/testcases/oracle_clmul.py`（**独立**实现：carry-less 乘、GHASH、CRC-32C；附自检恒等式）；
  3. C 用例：`clmul_edges.c`、`clmul_ghash.c`、`clmul_crc32c.c`（命名可调，须自描述）；
  4. 证据 `.work/evidence/<任务ID>/run.sh`；日志 `.work/log/testcases/`。
- **约束**：不改 `spec/`/`contracts/`；不改门控判定语义；不 commit/push；用例计数**现场派生**。

## 设计要点（**不预设唯一实现**）

### A. 指令级对拍（`clmul_edges.c`）

- 输入：`0`、`1`、`1<<63`、`1<<0`、全 1、`(1<<63)*(1<<63)`（进位到最高位）、随机 ≥ 64 组（种子写死以便复现）。
- 三个出口都比：低半、高半、`__int128` 合成值。
- oracle 自检（先证明参考本身对）：`a*1 == a`、`(1<<k)*(1<<m) == 1<<(k+m)`、交换律、结合律各抽 ≥3 组。

### B. GHASH（`clmul_ghash.c`）

- 实现 GF(2^128) 乘（GCM 的 `X·H`，反射位序约定须**明写**在用例注释里：GCM 的 bit 序与 `clmul` 的 bit 序差一个 `rev`，**这是最易错点**）。
- 交叉验证链：① Python 位串行参考；② 用 **NIST GCM 标准 KAT**（值逐字抄自标准文档并在注释标注来源章节）验①；③ 再用①验 C 实现。
  - **禁止**把 KAT 当作"唯一真值"绕过 oracle（KAT 只用于证明参考实现正确）。
- 至少覆盖：单块（16 B）、两块（链式累加）、全零 H、H = 全 1。

### C. CRC-32C（`clmul_crc32c.c`）

- 参数必须写死并断言：poly `0x1EDC6F41`（反射 `0x82F63B78`）、init `0xFFFFFFFF`、refin/refout = true、xorout `0xFFFFFFFF`。
- 参考 = Python **位串行**实现（非表驱动、非 clmul），长度 0/1/15/16/17/64/1000 B。
- 与 clmul 版结果逐例相等；**同时**断言 `"123456789"` 的 CRC-32C = `0xE3069283`（标准 check 值，用于钉住参数）。

### D. 耗时与定层

- 先单跑测总耗时；若 ≤ fast 预算 ⇒ 纳入 `check-testcases-suites`（L2）；否则单列按需目标（不进 L1/L2），并在完成区写明实测值与依据（`Process-07 §3`）。

## 验收标准

1. 指令级、GHASH、CRC-32C 三组全绿，**两档优化级**（`-O0`/`-O2`，口径照原子链）。
2. 计数现场派生（不写死用例数）；失败/跳过分列，禁静默跳过。
3. **可达 FAIL ≥ 2**（真实注入 → 红 → 还原 → 绿）：(a) 翻转 oracle 的一个期望位 ⇒ 红；(b) 把 C 侧 `clmul` 换成普通 `*`（或去掉 `rev`）⇒ GHASH/CRC 红。
4. `make check-modules`（L2）rc=0（若纳入）或 L1 + 单目标 rc=0（若不纳入）。
5. 证据脚本可一键复跑（`.work/evidence/<任务ID>/run.sh`），真实 rc 落盘（禁 `cmd | tee` 吞码）。
6. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（`run_atomics_probe.py` 结构、两档口径、fast 预算、QEMU 运行参数）。
2. 写 oracle（含自检恒等式）→ 先让 oracle 自证绿。
3. 指令级用例 → 绿；再 GHASH → 再 CRC-32C。
4. 两档跑 + 耗时测 → 定层 + 注入反例。
5. L2/L1 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 改一个期望值位（`cp` 备份 + md5）⇒ 对拍红；还原 ⇒ 绿。
- C 侧把 `__builtin_dadao_clmul` 换成 `*` ⇒ GHASH/CRC 全红（证明用例确实依赖该指令语义，而非"恒真"）。

## 已知边界（**披露，不自行扩面**）

- 不做 AES/SHA 轮指令用例（无该类指令；若将来立项另册）。
- 不做 IEEE CRC-32（`crc32`/zlib 多项式）——本册只做 CRC-32C（`crc32c` 语义），IEEE 路径需 `clmul` 不同参数（若要做，加一条用例，不算扩面）。
- 不做性能基准（只做正确性；性能另册）。
- 不引入外部库（OpenSSL/zlib）。

## 完成区

**测试结果**：两档各 **627 PASS / 0 FAIL**（O0 compile 0.24 s / run 0.06 s；O2 compile 0.61 s / run 0.08 s）；`--inject` 档 641 PASS（9 类注入全红 + 源未变 + 复原回绿）；oracle 自证 **51/51**（GF(2) 恒等式 + GCM 规范附录 B 的 H/X_i/GHASH + CRC-32C 四组发布向量）。全部期望值由 oracle 现场派生、计数现场统计（无写死）。
**修改文件**：新增 `tests/clmul/{clmul_edges.c,clmul_ghash.c,clmul_crc32c.c,clmul_ir.ll}`、`tools/testcases/{oracle_clmul.py,run_clmul_probe.py}`、`.work/evidence/TESTCASES-057t/run.sh`（`.work/` 不入库）；改 `Makefile`（新增 `check-clmul-probe`：L2 `check-modules` + 门控锁 + help）、`.tao/knowledge/milestones.md`（流水行状态 `待开始`→`待验收` + 一句改动，L1 `check-milestones-fresh` 要求）；本册。**覆盖披露**：新增用例文件 **4**（3 个 C 探针 + 1 个 IR 包裹 → 84 个 clmul 单元、9 个 GHASH 向量、17 个 CRC 向量）、新增工具 **2**、证据脚本 **1**、L2 目标 **1**；修改既有用例 **0**、删除 **0**。
**验收结果**：
- 两档全绿 `PASS (O0): total=627 pass=627 fail=0` / `PASS (O2): total=627 pass=627 fail=0`；分组 oracle 51 / edges 431 / ghash 63 / crc 58 / asm 9 / build 8 / run 3（两档计数现场派生一致）。
- 指令级：84 单元 × 3 出口（通用 `llvm.clmul` 低半、`llvm.dadao.clmul.hi` 高半、`__builtin_dadao_clmul` 的 i128）+ 84 个 `{lo,hi}` pair；含 `0/1/(1<<63)²⇒hi=1<<62/全1/1<<k×1<<m`、64 个 splitmix64 随机单元（种子 0xC1A50577）。
- GHASH 与 NIST 一致（GCM 规范 App.B tc2）：`C1·H = 5e2ec746917062882c85b0685353deb7`、`GHASH(H,A,C) = f38cbb1ad69223dcc3457ae5b6b0f885`；tc3（4 块）/tc4（AAD 20 B + C 60 B）的 X1…X6 与发布值逐项相等；另含 H=0、H=全1、单块、两块链、AAD+半块。
- CRC-32C：`crc32c("123456789") = e3069283`；`32×0x00 → 8a9136aa`、`32×0xff → 62a8ab43`、`00..1f → 46dd794e`、反向 `→ 113fdb5c`（发布向量）；长度 0/1/7/8/9/15/16/17/63/64/65/1000 与位串行参考逐例相等。
- 可达 FAIL（两档同值，均真实注入）：① GHASH 期望翻 1 位 ⇒ **9/63 红**；② CRC 换 IEEE 多项式 ⇒ **21/58 红**；③ clmul 高低半互换 ⇒ **316/424 红**；④ clmul 换普通乘 ⇒ **338/424 红**；⑤ `rev` 记作恒等 ⇒ **4/7 红**；⑥ C 侧 `clmul`→`*`：GHASH **14/63**、CRC **16/58** 红且对象 `clmul.o` 归零（结构性断言可达 FAIL）；⑦ 探针副本注入高低半互换 ⇒ driver **rc=1**（159 FAIL），删副本后 rc=0。
- 门控：`make check-clmul-probe` **PASS(O0+O2)**；`validate-vectors` OK（706 cases）；`check_qemu_trans --strict` **266/266**；`make check`(L1) rc=0；`make check-modules`(L2，含 check-clmul-probe) rc=0；证据 `.work/evidence/TESTCASES-057t/run.sh` **19/19 PASS**（rc 落盘 `run.rc`=0；全程 `; rc=$?` 不吞码）。实测 ≈0.7 s/档 ⇒ 定层 **L2**。
**新发现/坑**：① GCM 位序桥（`rev128` + 自然多项式序）是唯一易错点，oracle 用「位串行 vs rev+clmul」双形式互证并以发布 X1 钉住；② u128 内用 `0x87 << i` 折叠高位会在 x^255 处**静默丢 7 位**（实测 X1 首字节 `2e` vs `5e`）⇒ 须两段折叠；③ Barrett 商 66 位，用 `clmul` 低 64 位截断会丢 bit64/65（实测 8 B/32 B 末位错）⇒ 须保留 u128 再移位；④ `-O0` 下静态 kernel 只有 out-of-line wrapper 含 1 条 `clmul.o`（4 处调用）⇒ 结构性断言只取下界，另用「GHASH 对象 `mul.uo`==0」钉住未被展开成 64 位乘。
**遗留问题**：`milestones.md` 的 `已验证` + 完成时间留给 `/complete`（工程师只按 L1 门控要求同步到 `待验收`）；其余无（未改 ISA/QEMU/LLVM；性能基准按边界不做）。

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

### 第 1 轮 engineer 自审（2026-10-24，自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `barrett32` 用 `clmul_lo` 取 66 位商积 ⇒ 丢 bit64/65（8 B/32 B 末位错：`40795c73` vs `40795c72`） | ✅已修 | `clmul_wide` + u128 右移 33 得商 | `crc_eight_ramp=40795c72`、`ff32=62a8ab43`、`seqr32=113fdb5c` 与位串行参考相等 |
| F2 GHASH 用 `0x87<<i` 折叠 x^(128+i) 在 i>120 时溢出 u128（X1 首字节 `2e` vs 发布 `5e`） | ✅已修 | `gf128_reduce`：一次折叠 + 7 位 `spill` 二次折叠 | `C1·H=5e2ec746…`、tc1–tc4 GHASH/链全等于发布值 |
| F3 探针数据生成按首字母分派：`string` 落入 `seqr` 分支 ⇒ `crc32c("123456789")` 错 | ✅已修 | 按 `kind[1]`（`t`=string / `e`=seq）分派 | `crc_check123456789 = e3069283` |
| F4 oracle 把 CRC 长度与 CHAIN 下标按十六进制解析（`15`→21） | ✅已修 | 两者改 `int(x)` 十进制 | 长度断言与 17 例 CRC 全绿 |
| F5 `_ck()` 位置参数误用（`ok` 落到 `detail`）⇒ 覆盖类断言 TypeError | ✅已修 | `_ck(..., ok=None)` 关键字，覆盖类断言显式传 `ok=` | 两档 627/627 无异常 |
| F6 边界表含 `1<<64`（超出 64 位操作数） | ✅已修 | 改为 `bit_62_63`（`1<<62 × 1<<63`） | `edges: boundary cells present` 0 missing |
| F7 探针表里的操作数写错时 oracle 会"按错的值算期望"而仍绿 | ✅已修 | 新增 `edges: boundary operands match the oracle table`（逐 label 比对 a,b） | 新断言绿；注入高低半互换时该组同时红 |
| F8 `ASM_OBJ` 初版要求 ghash 对象 `clmul.o ≥ 4`（把指令数当调用数）⇒ -O0 假红（实测 1） | ✅已修 | 取下界 1，另加 `mul.uo ≤ 0`（GHASH 无普通乘，展开成 64 位乘即红） | O0 `clmul.o=1 mul.uo=0`、O2 `12/0`；C 侧注入后 `clmul.o=0` |

判决：F1–F8 全部修复并复验；无未修缺陷，无降级/跳过项。状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-24，独立重跑）

- **重跑（本人执行）**：`./.work/evidence/TESTCASES-057t/run.sh` → `EVIDENCE_RC=0`、`run.rc=0`、`PASS (19 checks)`；其中 `check-clmul-probe`(O0+O2)、`validate-vectors`(706 cases)、`check_qemu_trans --strict`(266/266)、`make check`(L1)、`make check-modules`(L2) 的 rc 均由脚本直取为 0。另单跑 `make check-clmul-probe` → `MAKE_CLMUL_RC=0`。
- **计数现场统计（不采信 627）**：O0/O2 均 `total=627 pass=627 fail=0`；分组 oracle=51、edges=431、ghash=63、crc=58、asm=9、build=8、run=3、objdump=1、探针组×3=1（合计 627，两档一致）。分项：clmul 单元 84（20 边界 + 64 splitmix64 随机）×3 出口 + 84 pair + rev 6 + 覆盖 4 = 431；GHASH 9 向量 = 63；CRC 17 向量 = 58；oracle 自证 51（恒等式 + 双形式 + 发布向量）。
- **标准向量独立核对**：本人另写 `/tmp/opencode/TESTCASES-057t-review/indep_check.py`（**与 oracle 不同的算法形态**：GHASH 用自然序 Horner + 128 位反转，CRC 用 MSB-first 反射等价形；不 import 仓库 oracle、不碰 QEMU/LLVM）→ **20/20 PASS, rc=0**：tc2 `C1·H=5e2ec746917062882c85b0685353deb7`、`GHASH(H,A,C)=f38cbb1ad69223dcc3457ae5b6b0f885`；tc3 X1–X4 + GHASH、tc4 X1–X6 + GHASH；`crc32c("123456789")=e3069283`、`32×0x00=8a9136aa`、`32×0xff=62a8ab43`、`00..1f=46dd794e`、`1f..00=113fdb5c` —— 与用例表、探针实测输出逐位相等。
- **oracle 独立性**：`oracle_clmul.py` 零 import、无 subprocess/QEMU/LLVM 调用；`clmul()` 是 GF(2) 位移异或**定义**；CRC 为位串行（非表、非 clmul）。三个探针只观察（打印输入/中间值），期望值全部由 oracle 现场派生；KAT 只用于钉参考，不作唯一真值。
- **注入 3 次（均在 `/tmp` 临时树，仓库文件零改动，md5 前后一致）**：① GHASH 期望翻 1 位 → driver rc=**1**、2 FAIL（`f38c…884` vs 实测 `…885`）；② CRC 多项式换 IEEE `0xEDB88320` → rc=**1**、26 FAIL（check 值变 `cbf43926`）；③ C 探针 EDGE 高低半互换 → rc=**1**、159 FAIL。未注入树复跑 `PASS (O2): total=627 pass=627 fail=0` rc=0（回绿）。engineer 侧 9 类注入签名本人重跑全红：9/63、21/58、316/424、338/424、4/7、14/63、16/58、structural 0×2。
- **覆盖披露核验**：`git diff --name-status d15d1906~1..d15d1906 -- tests/` = 4 `A`、0 M、0 D；工具 2 `A`；与完成区声明一致。
- **约束**：`git diff -- components/ spec/ contracts/` 空（rc=0，未改实现/规范/契约）；Makefile 仅新增 `check-clmul-probe`（+ 门控锁 + help + L2 接线），未改既有门控判定语义；`.work/` 不入库。
- **证据脚本审读**：无 `| tee`（仅注释提及）、`step()` 以 `rc=$?` 直取、`run.rc` 落盘；各断言有可达 FAIL（注入签名含 `red>0` 且 `total>0` 双守卫、探针源 md5 基线、两档计数比对）；计数全部现场派生，无写死。
- **快照对账**：验收前/后 `git status --porcelain -uall` 均 0 行且一致；7 个目标文件 `md5sum -c` 全 OK（`run.sh` 与审读副本逐字节相同）。
- **判决：Accepted** —— 标准向量正确、oracle 无循环、注入全红且可回绿、覆盖未删、门控全绿；无阻断项，无降级/跳过项。
