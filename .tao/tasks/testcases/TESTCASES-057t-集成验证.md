# TESTCASES-057t: `clmul` 集成验证（GHASH / CRC-32C / `__int128` 对拍）

**模块**：testcases
**项目里程碑**：M9
**依赖**：`QEMU-068t`（执行语义 + 解除 `excluded`）、`LLVM-122t`（`llvm.clmul` / `llvm.dadao.clmul` / `__builtin_dadao_clmul`）
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
