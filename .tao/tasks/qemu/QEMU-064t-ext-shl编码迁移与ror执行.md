# QEMU-064t: `ext`/`shl` 编码迁移与 `ror` 执行（decodetree + `trans_*` + L3 语义向量）

**模块**：qemu
**项目里程碑**：M9
**依赖**：`SPEC-152t`（编码真源：四表 + `contracts/opcodes.yaml`）、`LLVM-116t`（后端面收口；本册以其为前置以保证最终 L1/L2/L3 全绿）、`ADR-0032`（`Accepted`；`D1`–`D6`）、`QEMU-004t`（decodetree 生成器/校验器先例）、`QEMU-061t`（`insn.decode` 计数从记录派生、禁写死的先例）、`QEMU-062t`/`QEMU-063t`（`trans_*` 拆分与 user-mode 后端）、`docs/Process-01`（补丁树）、`ISS-229`/`ISS-210`（构建单写者 + `install-host`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

- 来源 = `ADR-0032`（`D1`–`D6`）+ `SPEC-152t`（编码真源）；用户 2026-10-19 原话见 `ADR-0032 §Context`。
- **现状（主会话 2026-10-19 核）**：
  1. `components/qemu/patches/target/dadao/insn.decode.patch`：由 `tools/qemu/generate_decodetree.py` 从 `contracts/opcodes.yaml` 生成（新文件补丁，256 条 pattern 为当时计数，**计数从记录派生**，`QEMU-061t` 订正）。
  2. `insn_trans/trans_shift.c.inc.patch`：`trans_shl_uo_orrr_rd` / `trans_shl_uo_orri_rd` 等，`ha` 由 pattern 决定（当前 `shl.uo` orrr `0x14`、orri `0x1C`）；窄位宽 `trans_shl_ut/uw/ub_*` 已实现。
  3. `tools/qemu/check_qemu_trans.py --strict` 按 `id` 派生 `trans_*` 名（`shl.uo` → `trans_shl_uo_orrr_rd`）⇒ **改名会同时改函数名**；缺失即 L2 `check-interface` 红。
  4. `tools/qemu/min_rom_probe_005t.py`（诊断探针，非门控）硬编码 `shl_uo_orri(..., 0x1C, ...)`；`tools/qemu/check_005t_coverage.py` 的 id 清单含 `shl.uo_*`（非门控，但属引用面）。
  5. TCG 现成：`tcg_gen_rotr_i64`（`.work/source/qemu/include/tcg/tcg-op-common.h:227`）⇒ `ror` 无需新 helper。
  6. L3 `check-qemu-semantics` 跑 `tests/vectors/isa/reg-shift-extend.yaml` 全量语义；该文件由 `tools/testcases/generate_isa_vectors.py` 生成（当前只覆盖 `shl/shr/ext`，`SHIFT = {"shl","shr","ext"}`）。
- **证据指针**：`components/qemu/patches/target/dadao/{insn.decode.patch,insn_trans/trans_shift.c.inc.patch}`、`tools/qemu/{generate_decodetree.py,validate_decodetree.py,check_qemu_trans.py}`、`Makefile` 的 `check-qemu-semantics`。

## 目标

1. **解码面**：`insn.decode` 重生成 —— `ext` 迁 `ha 0x20/0x21`、`0x28/0x29`；`shl.o/t/w/b` 迁 `0x10/0x18`；`ror.o/t/w/b` 占 `0x11/0x19`；pattern 计数**从记录派生**（不写死）。
2. **执行面**：`trans_shl_uo_*` → `trans_shl_o_*` 改名；新增 `trans_ror_{o,t,w,b}_{orrr,orri}_rd`，语义 = 逻辑循环右移；窄位宽按位宽取模 + 高位写满（值语义）；`hb == 0` ⇒ ILLI；orri 越界 ⇒ ILLI。
3. **语义向量（独立 oracle）**：`tests/vectors/isa/reg-shift-extend.yaml` 增 `ror` 的 encoding/semantic/boundary/ILLI 用例（**期望值手算**，不从 QEMU/LLVM 反推）；`tools/testcases/generate_isa_vectors.py` 增 `ror` 语义函数，重生成。
4. **收口**：L1/L2/L3 全绿；补丁树/changelog/`series` 一致；`--inject` 可达 FAIL。

## 接口规范

- **输入**：`contracts/opcodes.yaml`（`SPEC-152t` 后）；`spec/SimRISC-04 §4.2` + `08/09/10 §4.2`（`ror` 语义）；`tools/qemu/generate_decodetree.py`；现有 `trans_shift.c.inc.patch`；`.work/source/qemu/**`（**只读参照**，交付只走 `patches/**`）。
- **输出**：
  1. `components/qemu/patches/target/dadao/insn.decode.patch`（重生成/重导出）；
  2. `components/qemu/patches/target/dadao/insn_trans/trans_shift.c.inc.patch`（改名 + `ror` 实现）；
  3. 其它 ripple：`tools/qemu/min_rom_probe_005t.py`、`tools/qemu/check_005t_coverage.py`（诊断工具，非门控；只做机械改名/编码更新）；
  4. `tools/testcases/generate_isa_vectors.py`（`ror` 语义 + `SHIFT` 集合）+ 重生成的 `tests/vectors/isa/reg-shift-extend.yaml`；
  5. `components/qemu/changelog.md`（`## M9` 节，`docs/Process-01 §10` 体例）；
  6. `.work/evidence/QEMU-064t/**`（default + `--inject`）+ 日志 `.work/log/qemu/QEMU-064t/**`；
  7. 本册完成区。
- **约束**：
  - **不改** `spec/`、`contracts/**`、`.tao/contracts/**`、`components/llvm-project/**`；与 `SPEC-152t`/`LLVM-116t` 冲突 ⇒ 停并留问。
  - **不改** 期望值来迁就实现；**不得**以「抬超时/改分类/删向量」当通过。
  - 补丁**一文件一补丁** + `series` 同步；`insn.decode.patch` 用生成器输出重导出（**禁手改 hunk 头/pattern**）。
  - **计数不写死**：pattern 数、`trans_*` 数、向量数现场派生。
  - **独立 oracle**：`ror` 期望值用 Python 按定义（`(x >> k) | (x << (W-k))`，`k mod W`）手算；**不得**从 QEMU 运行结果回填。
  - **构建单写者**：`build-qemu` / `install-host` 不与其它 L2/L3 并发（`ISS-229`）；改 `insn.decode`/`trans_*` 后 **必跑 `install-host`**（`ISS-210`）。

## 做

### 阶段 0：现场复核

1. 核 `SPEC-152t`、`LLVM-116t` 均 `已验证`；`contracts/opcodes.yaml` 中 `shl.o/t/w/b`、`ror.o/t/w/b`、`ext.uo/so` 的 `id`/`ha`/`mask`/`value` 与 `ADR-0032` 一致（逐条打印）。
2. 记录基线：`python3 tools/qemu/validate_decodetree.py`、`python3 tools/qemu/check_qemu_trans.py --strict` 的 rc/计数（预期当前为旧编码的绿；改名后先红后绿）。

### 阶段 A：decodetree

1. 生成到临时目录：
   `python3 tools/qemu/generate_decodetree.py --out-decode /tmp/opencode/QEMU-064t/insn.decode --out-stubs /tmp/opencode/QEMU-064t/translate_stubs.c.inc`
2. 按 `docs/Process-01` 把生成结果落为 `insn.decode.patch`（新文件补丁；由 `git diff`/`diff -u` 生成，不手拼 hunk）。
3. `python3 tools/qemu/validate_decodetree.py` rc=0；pattern 数 = `opcodes.yaml` 记录数（现场派生；`ror` 新增 8 条）。

### 阶段 B：`trans_*` 实现

1. **改名**：`trans_shl_uo_orrr_rd` → `trans_shl_o_orrr_rd`，`trans_shl_uo_orri_rd` → `trans_shl_o_orri_rd`；`ut/uw/ub` 同理。
2. **`ror.o`**：
   - orrr：`shamt = rdhd & 0x3F`；`tcg_gen_rotr_i64(rdhb, rdhc, shamt)`；
   - orri：`immu6` 0..63 全有效；`tcg_gen_rotri_i64` 或 `tcg_gen_rotr_i64` + 常量；
   - `hb == 0` ⇒ `gen_exception_illegal`。
3. **`ror.t/w/b`**：源先掩到 `W` 位，`shamt = rdhd & (W-1)`（orrr）；orri 的 `immu6 > W-1` ⇒ ILLI；结果 `tcg_gen_rotr_i64` 后掩到 `W` 位（高位零，值语义）；`W = 32/16/8`（`N = W-1 = 31/15/7`）。
4. 诊断工具机械同步：`min_rom_probe_005t.py` 的 `shl_uo_orri` 名/编码（`0x1C` → `0x18`）与调用点；`check_005t_coverage.py` 的 id 清单（`shl.uo_*` → `shl.o_*`）。
5. `components/qemu/changelog.md` 增 `## M9` 条目。

### 阶段 C：语义向量（独立 oracle）

1. `tools/testcases/generate_isa_vectors.py`：
   - `SHIFT` 增 `ror`；
   - 新增 `_ror_result(src, amount, N)`：`src &= (1<<(N+1))-1; k = amount % (N+1); return ((src >> k) | (src << ((N+1)-k))) & mask`（`k=0` 直接返回 `src`）；
   - `gen_shift_orrr_semantic` / `gen_shift_orri_semantic` / boundary 函数增 `bm == "ror"` 分支；
   - **边界用例**：orrr 取 `amount = 0/1/W-1/2`；orri 取 `0/1/W-2`，并加 `W`（越界）⇒ `expected_fault = ILLI`；
   - `dst rd0` ⇒ ILLI（每宽度至少 1 例）。
2. 重生成 `tests/vectors/isa/reg-shift-extend.yaml`；`python3 tools/testcases/validate_vectors.py` rc=0。
3. **独立复核**：另写一次性 Python（`/tmp/opencode/QEMU-064t/oracle.py`）按定义重算全部 `ror` 期望值，与 YAML 逐条比对；结果落 `.work/log/qemu/QEMU-064t/**`（**不得**调用 QEMU/LLVM）。

### 阶段 D：构建与门控

1. `make build-qemu`（增量；改 `.c.inc` 约秒级）→ `make install-host`（申报耗时；`JOBS=8`）。
2. 逐项跑：
   - `python3 tools/qemu/validate_decodetree.py`
   - `python3 tools/qemu/check_qemu_trans.py --strict`
   - `make check-interface`
   - `make check-qemu-smoke`（L2）
   - `make check-qemu-semantics`（L3）
   - `make check`（L1）
   - `make check-modules`（L2）
   - `make check-full`（L3，含 `check-lit-full`；申报耗时，长任务按 `AGENTS.md` 落 `XXX_EXIT=$rc`）
   - `make check-patch-tree`、`make check-component-changelog`
3. `--inject`（至少 1 条）：把 `trans_ror_o_orrr_rd` 的 `tcg_gen_rotr_i64` 改成 `tcg_gen_rotl_i64`（或把掩码 `0x3F` 改 `0x1F`）⇒ `check-qemu-semantics` 必须在 `ror` 用例上 FAIL；`cp` 备份 + `md5` 对账还原后回绿。

## 验收标准

1. **前置**：`SPEC-152t`、`LLVM-116t` 均 `已验证`；`ADR-0032` = `Accepted`。
2. **decodetree**：`validate_decodetree.py` rc=0；每条 `opcodes.yaml` 记录有对应 pattern/`trans_*`；`ext`/`shl`/`ror` 的 `mask`/`value` 与 `SPEC-152t` 逐条一致；pattern 数 = 记录数（现场派生，含新增 8 条 `ror`）。
3. **`trans_*`**：`check_qemu_trans.py --strict` rc=0；`trans_shl_o_*` 与 `trans_ror_*` 全部在场；无旧名 `trans_shl_uo_*` 残留（活补丁树 grep 0 命中）。
4. **语义**：L3 `check-qemu-semantics` 对 `reg-shift-extend.yaml` 全量 PASS；`ror` 用例覆盖：
   - `ror.o` 量 `0/1/31/32/63`；
   - `ror.t/w/b` 量 `0/1/W` 与 orri `W` 越界 ILLI；
   - `dst rd0` ⇒ ILLI（每宽度至少 1 例）；
   - 期望值与独立 oracle 逐条一致（日志留证）。
5. **门控全绿**：`make check` rc=0（L1）、`make check-modules` rc=0（L2）、`make check-full` rc=0（L3）；`check-qemu-trans --strict` / `check-interface` / `check-patch-tree` / `check-component-changelog` rc=0。
6. **可达 FAIL**：`--inject`（旋转方向或掩码）后 `check-qemu-semantics` 非零，且 FAIL 落在 `ror` 用例；还原后 `md5` 一致、门控回绿；三段输出齐全。
7. **无回归**：`shl/shr/ext` 原有语义用例全绿；`check-qemu-smoke` 代表集全绿；`qemu-dadao`/`qemu-system-dadao` 安装根来自本次构建（`sha256`/时间戳 + `--version`）。
8. **补丁纪律**：`insn.decode.patch` 由生成器输出重导出；`trans_shift.c.inc.patch` 一文件一补丁；`series` 不变；`changelog.md` 有 `## M9` 条目。
9. **计数不写死**：完成区给出「pattern 数 / `trans_*` 数 / 向量条数」的现场统计命令与数值，不使用硬编码期望。

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
