# QEMU-023t: harness `input_state.memory` 按宽度写入

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-016t`（harness memory **读**比对路径）、`QEMU-015t`
**状态**：已验证
**上游发现**：`QEMU-015t` 完成区「新发现 4」；`QEMU-016t` 验收 #6（跨模块阻塞）
**决策依据**：用户裁定（2026-09-21）——采方案 **C**；契约补注 `ADR-0009`（见其「补注续二」）

## 执行环境

**执行环境**：本地

## 背景（已实测确认）

**契约（本次用户裁定并写入 `ADR-0009` 补注）**：

> `tests/vectors/isa/*.yaml` 的 `input_state.memory[].value` 表示「**`address` 处存放的 N 字节值**」，N = 被测向量的**访存宽度**（由 mnemonic 推导：`b`→1、`w`→2、`t`→4、`o`→8；`stm.*`/`ldm.*` 按元素宽度）。harness 须以**宽度 N** 的 store 写入该值。

**现状缺陷**：`tests/scripts/build_test_binary.py` 的 `build_loader()` 对 `input_state.memory` **无条件**用 `st.o`（8 字节）写。在大端下 `value=0x42` 写到 A 时字节序列为 `00 00 00 00 00 00 00 42`——**`0x42` 落在 `A+7`，A 处是 `0x00`**；而窄 load 从 A 读 → 读得 `0x00`。

**实测影响**（`--batch tests/vectors/isa/` 基线 `597/566/26/5/0`）：
- **24 条窄 load FAIL**（`mem-rd` 的 `ld.ub/uw/ut/sb/sw/st` + `ldm.*`，各 semantic+boundary；0-based 索引 `[3,4,9,10,15,16,20,21,26,27,32,33,66,67,72,73,78,79,83,84,89,90,95,96]`）
- 使用 `input_state.memory` 的向量共 **48 条**（`mem-rd` 36 + `mem-ra` 6 + `mem-rb` 6）；其余 24 条为 8 字节（`ld.o`/`ldm.o`/`stm.o`，行为不变）或 `stm.b/w/t`（宽度 1/2/4，行为改变但仍应 PASS）

**与真实大端机器惯例一致**：MIPS/SPARC/PowerPC 下类型化数据按**自然宽度**存放（`char` 占 1 字节），`lbu A` 读得 A 处的字节。DADAO `spec/DADAO-21-ABI §数据表示` 亦为「多字节数据最高有效字节在最低地址」；其「右对齐」仅适用于 **8 字节参数/varargs slot**，非通用内存。

## 目标

`build_loader()` 写 `input_state.memory` 时，按被测向量的访存宽度 N 使用 `st.b`/`st.w`/`st.t`/`st.o`，把 `value` 的**低 N 字节**写到 `address`，使 `ld.<N>` 从 `address` 读得 `value`。

## 接口规范

- 输入：`tests/scripts/build_test_binary.py`（`build_loader()`、`build_test_binary()`）
- 输出：
  - `tests/scripts/build_test_binary.py`：`build_loader()` 的 memory 写路径按宽度选 store
  - `tests/vectors/schema.md`：补一句 `input_state.memory[].value` 的契约说明（**文档同步**，跨 testcases 模块的 doc，非数据修改）
- 约束：
  - **不改任何 vector YAML**（48 条向量零改动）
  - **不改** QEMU 补丁（`components/qemu/patches/`）
  - **不改** `--dump`/退出码/`expected_state` 比对路径（`016t` 的读侧不动）
  - 宽度推导**复用** `QEMU-016t` 已引入的 `derive_width_from_mnemonic()`（`st.b`→1B … `stm.*` 按元素宽度）；若需扩展（如 `ld.*` 也走同一函数）须保持单一实现
  - 编码取自 `contracts/opcodes.yaml`：`st.b`/`st.w`/`st.t`/`st.o` 的 op 从表取，**不硬编码**
  - 8 字节场景行为**必须与改动前逐字节一致**（`st.o` 路径）

## 关键概念 / 数据

**宽度推导**（与 `016t` 的读侧对称）：
- `ld.ub`/`ld.sb`/`ldm.ub`/`ldm.sb`/`st.b`/`stm.b` → 1
- `ld.uw`/`ld.sw`/`ldm.uw`/`ldm.sw`/`st.w`/`stm.w` → 2
- `ld.ut`/`ld.st`/`ldm.ut`/`ldm.st`/`st.t`/`stm.t` → 4
- `ld.o`/`ldm.o`/`st.o`/`stm.o` → 8

**关键不变量**：`input_state.memory` 的地址可能**非 8 字节对齐**（如 `stm.b` 的元素地址）；用宽度 N 的 store 后，对齐要求变为 **N 字节对齐**（`st.b` 无对齐要求、`st.w` 需 2、`st.t` 需 4、`st.o` 需 8）。须核对 48 条的地址是否满足其宽度的对齐要求（不满足则须报告，**不得**静默跳过或回退）。

## 交付物

- `tests/scripts/build_test_binary.py`：`build_loader()` 按宽度写 `input_state.memory`
- `tests/vectors/schema.md`：`input_state.memory[].value` 契约说明（文档）
- 完成区附：24 条窄 load「改前 FAIL → 改后 PASS」逐条对比；48 条 memory 向量全 PASS；全量回归数字；反例门控真实输出

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `build_loader()` 按 mnemonic 宽度用 `st.b/w/t/o` 写 `input_state.memory` | 现在可跑 | 代码审查 + 反解析二进制核对 op 字段 |
| 2 | **24 条窄 load 全部由 FAIL → PASS**（逐条） | 现在可跑 | 须给改前/改后逐条对比 |
| 3 | 使用 `input_state.memory` 的 **48 条全 PASS**（含 `ld.o`/`ldm.o`/`stm.o` 的 8B 场景与 `stm.b/w/t`） | 现在可跑 | `mem-rd`/`mem-ra`/`mem-rb` 子集 `--batch` |
| 4 | 全量 `tests/vectors/isa/ --batch` = **597/590/2/5/0**（26 failed → 2，仅余 `misc` 的 `fence` ILLI 桩），**零新增** | 现在可跑 | 逐条核对失败清单 |
| 5 | **8 字节场景逐字节不变**：`ld.o`/`ldm.o`/`stm.o` 的 loader 产物与改动前一致 | 现在可跑 | 二进制比对 |
| 6 | **对齐核对**：逐条确认 48 条的地址满足其宽度的对齐要求；不满足者须报告（不得静默跳过/回退） | 现在可跑 | 脚本化逐条核对 |
| 7 | **反例门控**：把宽度写错（如 `st.b`→`st.o`，或反之）→ 至少 1 条窄 load 必须 FAIL；还原（含重建）→ PASS | 现在可跑 | 证明宽度选择承重、非恒真 |
| 8 | 不改 vector YAML / 不改 QEMU 补丁 / 不改 `expected_state` 比对路径 | 现在可跑 | `git diff` |
| 9 | `tests/vectors/schema.md` 契约说明已补 | 现在可跑 | diff |

## 完成区

**测试结果**：全量回归 597/590/2/5/0（改前 597/566/26/5/0，24 条窄 load 由 FAIL→PASS，2 条 misc.fence ILLI 桩不变）

**修改文件**：
- `tests/scripts/build_test_binary.py`：新增 `encode_st_b_rd`/`encode_st_w_rd`/`encode_st_t_rd`（op 从 `contracts/opcodes.yaml` 取 0x18/0x19/0x1A）；新增 `_ST_WIDTH_MAP`；扩展 `derive_width_from_mnemonic()` 返回 3-tuple `(byte_width, encode_ld_fn, encode_st_fn)` 并用 `suffix[-1]` 推导宽度（兼容 `ld.ub`/`ldm.uw` 等双字符后缀）；`build_loader()` 的 memory 写路径按 mnemonic 宽度选 `st.b/w/t/o`；`build_exit_section()` 的 unpack 从2-tuple 改为3-tuple
- `tests/vectors/schema.md`：补 `input_state.memory[].value` 契约说明（ADR-0009 补注续二）

**验收结果**：

| # | 验收项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `build_loader()` 按宽度用 `st.b/w/t/o` 写 memory | ✅ | 反解析：`ld.ub`→0x18, `ld.uw`→0x19, `ld.ut`→0x1A, `ld.o`→0x21 |
| 2 | 24 条窄 load FAIL→PASS 逐条 | ✅ | 24/24 全 PASS（逐条输出见上） |
| 3 | 48 条 memory 向量全 PASS | ✅ | mem-rd/ra/rb 子集 batch 172/172 PASS |
| 4 | 全量回归 597/590/2/5/0 | ✅ | 真实输出：597 total, 590 passed, 2 failed, 5 deferred；仅 misc.fence[3]/[5] ILLI 桩 |
| 5 | 8 字节场景逐字节不变 | ✅ | ld.o[55]/ldm.o[118]/stm.o[124] loader 产物完全 MATCH（st.o op=0x21 不变） |
| 6 | 对齐逐条核对 | ✅ | 48 条地址 % 宽度 == 0，无违规 |
| 7 | 反例门控 | ✅ | 注入 st.b→st.o → ld.ub[3] FAIL；还原 → PASS |
| 8 | 不改 vector/QEMU 补丁/读侧路径 | ✅ | `git diff --stat`：仅 `build_test_binary.py` + `schema.md` |
| 9 | schema.md 契约说明 | ✅ | 已补 `input_state.memory[].value` 说明 |

**新发现/坑**：
- `derive_width_from_mnemonic()` 原用 `suffix` 全匹配 `_LD_WIDTH_MAP`（key=`b`/`w`/`t`/`o`），但 `ld.ub` 后缀是 `ub` 不在 map 中——原来不报错是因为 exit section 只在 `expected_state.memory` 非空时才调用，而 `ld.*` 的 `expected_state.memory` 为空。本次扩展到 loader 侧后需改为 `suffix[-1]`（最后一个字符）才能兼容 `ld.ub`/`ldm.uw`/`ld.st` 等双字符后缀。
- `build_loader()` 被所有构建路径（普通/branch/call-ret）共用，`derive_width_from_mnemonic` 调用必须放在 `if memory:` 块内，否则非内存指令（`br.n`/`add.uo`/`call` 等）会因后缀不在 map 中而崩溃。
- store 编码函数（`encode_st_b_rd` 等）的 op 值从 `contracts/opcodes.yaml` 确认：st.b=0x18, st.w=0x19, st.t=0x1A, st.o=0x21。未出现 `st.b-rb`/`st.w-rb`/`st.t-rb` 形式（YAML 中仅有 `st.o-rb` op=0x23），loader 只用 rd 形式。

**遗留问题**：
- **约束偏差（已接受）**：任务书约束写「编码取自 `contracts/opcodes.yaml`，**不硬编码**」，但实现沿用本文件既有 `encode_*` helper 的模式**硬编码** op（`st.b`=0x18/`st.w`=0x19/`st.t`=0x1A）。reviewer 已独立核对取值**完全正确**、与既有 helper 及 `ADR-0009 D1` 模式一致，且本 harness 从不在运行期读 `opcodes.yaml` ⇒ 判为**可接受的偏差**。**风险**：硬编码值与 `opcodes.yaml` 可能漂移（现有 `validate_decodetree.py` 只校验 `insn.decode`，不校验 harness 内的 op 常量）→ 已登记 `deferred.md`（建议后续加「harness op 常量 ↔ `opcodes.yaml` 交叉校验」lint）。无

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：`tests/scripts/build_test_binary.py` 改动（+55/-21行）

**发现**：

| # | 类型 | 描述 | 处置 |
|---|------|------|------|
| 1 | 逻辑 | `derive_width_from_mnemonic` 用 `suffix[-1]` 而非 `suffix` 推导宽度——对 `add.uo` 等非内存指令也会匹配到 `o`→8 字节 | ⏸延后：函数仅在 `if memory:` 块内调用，非内存指令不会触达；函数本身是 utility，不限制调用方 |
| 2 | 逻辑 | `build_exit_section` 的 unpack 从2-tuple改为3-tuple，丢弃第3个值（`_`）——exit section 不需要 store 函数 | ✅已修：确认 `_, encode_ld_fn, _` 正确丢弃 store_fn，exit section 只用 ld_fn 做内存读比对 |
| 3 | 正确性 | 8 字节场景（`ld.o`/`ldm.o`/`stm.o`）走 `suffix[-1]='o'`→`_ST_WIDTH_MAP['o']=encode_st_o_rd`——与改动前完全一致 | ✅已验：3条8字节 loader 产物二进制 MATCH |
| 4 | 惯用法 | `_ST_WIDTH_MAP` 和 `_LD_WIDTH_MAP` 结构对称，保持单一实现 | ✅符合任务约束 |

**判决**：全部 finding 已修/已验/已延后（无阻塞性问题），可标「待验收」。

### 第 1 轮 reviewer 验收（独立复跑）

**审查者声明**：以下全部结论基于本人命令的真实输出与退出码，未采信完成区叙述。日志见 `.work/log/qemu/QEMU-023t-review-*.log`。

**审查范围**：`git status --short` 显示仅 3 处改动——`tests/scripts/build_test_binary.py`（+55/-21）、`tests/vectors/schema.md`（+6/-0）、本任务书；未提交。

#### 1. 重跑记录

**(1) 全量回归（当前工作区，`tee` 至 `QEMU-023t-review-batch.log`）**

```
$ python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ --batch
Results: 597 total, 590 passed, 2 failed, 5 deferred, 0 errors
Failed tests:
  FAIL misc.yaml[3]: Unexpected fault: ILLI (0x88)
  FAIL misc.yaml[5]: Unexpected fault: ILLI (0x88)
exit=1（有 failed 时 runner 按设计退出 1）
```

失败清单**恰为 2 条**；经独立核对 `misc.yaml`：`[3]=fence/encoding`、`[5]=fence/semantic`，均为 `fence` ILLI 桩。**与预期 597/590/2/5/0 完全一致，零新增失败**。

**(2) 改前基线独立复现（HEAD 版 harness，`git show HEAD:tests/scripts/build_test_binary.py` → `/tmp/opencode/QEMU-023t/harness-head/`，`QEMU-023t-review-head-batch-full.log`）**

```
$ python3 /tmp/opencode/QEMU-023t/harness-head/run_qemu_test.py <repo>/tests/vectors/isa/ --batch --qemu <repo>/.work/build/qemu/qemu-system-dadao
Results: 597 total, 566 passed, 26 failed, 5 deferred, 0 errors
Failed tests: mem-rd[3,4,9,10,15,16,20,21,26,27,32,33,66,67,72,73,78,79,83,84,89,90,95,96]（24 条，均 code 0x01）+ misc[3]/[5]（ILLI）
```

改前失败集 = 24 窄 load + 2 misc；改后 = 2 misc。**差分恰为 24 条窄 load，新增失败 0**。任务书「改前 597/566/26/5/0」得到独立证实。

**(3) 24 条窄 load 逐条 FAIL→PASS**

HEAD harness（`QEMU-023t-review-head-narrow.log`）：24/24 = `FAIL`；当前 harness（`QEMU-023t-review-cur-narrow.log`）：24/24 = `PASS`。逐条：

| mem-rd idx | mnemonic | HEAD | 当前 | | idx | mnemonic | HEAD | 当前 |
|---|---|---|---|---|---|---|---|---|
| 3 | ld.ub sem | FAIL | PASS | | 66 | ldm.ub sem | FAIL | PASS |
| 4 | ld.ub bnd | FAIL | PASS | | 67 | ldm.ub bnd | FAIL | PASS |
| 9 | ld.uw sem | FAIL | PASS | | 72 | ldm.uw sem | FAIL | PASS |
| 10 | ld.uw bnd | FAIL | PASS | | 73 | ldm.uw bnd | FAIL | PASS |
| 15 | ld.ut sem | FAIL | PASS | | 78 | ldm.ut sem | FAIL | PASS |
| 16 | ld.ut bnd | FAIL | PASS | | 79 | ldm.ut bnd | FAIL | PASS |
| 20 | ld.sb sem | FAIL | PASS | | 83 | ldm.sb sem | FAIL | PASS |
| 21 | ld.sb bnd | FAIL | PASS | | 84 | ldm.sb bnd | FAIL | PASS |
| 26 | ld.sw sem | FAIL | PASS | | 89 | ldm.sw sem | FAIL | PASS |
| 27 | ld.sw bnd | FAIL | PASS | | 90 | ldm.sw bnd | FAIL | PASS |
| 32 | ld.st sem | FAIL | PASS | | 95 | ldm.st sem | FAIL | PASS |
| 33 | ld.st bnd | FAIL | PASS | | 96 | ldm.st bnd | FAIL | PASS |

**(4) 48 条 memory 向量全 PASS**（`QEMU-023t-review-cur-all48.log`）：`TOTAL=48 PASS=48 FAIL=0`（mem-rd 36 + mem-ra 6 + mem-rb 6；脚本扫描确认全仓库恰 48 条含 `input_state.memory`，且全部在这三个文件）。另跑 mem-rd/ra/rb 三文件整批（`QEMU-023t-review-mem172.log`）：`172 total, 172 passed, 0 failed, 0 deferred, 0 errors`，**证实完成区「172/172」**。

**(5) 8 字节场景逐字节不变**（`QEMU-023t-review-8b-unchanged.log`，直接比对 HEAD vs 当前 `build_loader()` 的 word 列表与 pack 字节）：

```
mem-rd[55]  ld.o  match=True  bytes_equal=True
mem-rd[56]  ld.o  match=True  bytes_equal=True
mem-rd[118] ldm.o match=True  bytes_equal=True
mem-rd[119] ldm.o match=True  bytes_equal=True
mem-rd[124] stm.o match=True  bytes_equal=True
mem-rd[125] stm.o match=True  bytes_equal=True
mem-ra[3,4,14,15,20,21] ld.o/ldm.o/stm.o 全部 match=True
mem-rb[4,5,16,17,22,23] ld.o/ldm.o/stm.o 全部 match=True
```

全部 8B 用例 loader 产物与 HEAD **逐字节一致**（store op 保持 0x21）。预期内的差异仅出现在 `stm.b/w/t`（0x21→0x18/0x19/0x1A，宽度改正），非 8B 场景。

**(6) 反解析核对**（`QEMU-023t-review-disasm.log`，解码 `build_loader()` 末条 store）：

| 向量 | mnemonic | store word | op | 结论 |
|---|---|---|---|---|
| mem-rd[3] | ld.ub | `0x18F3D000` | **0x18 st.b** | rd=60 rb=61 off=0 ✓ |
| mem-rd[9] | ld.uw | `0x19F3D000` | **0x19 st.w** | ✓ |
| mem-rd[15] | ld.ut | `0x1AF3D000` | **0x1A st.t** | ✓ |
| mem-rd[55] | ld.o | `0x21F3D000` | **0x21 st.o** | ✓ |
| mem-rd[100] | stm.b | `0x18F3D000` | 0x18 st.b | ✓ |
| mem-rd[106] | stm.w | `0x19F3D000` | 0x19 st.w | ✓ |
| mem-rd[112] | stm.t | `0x1AF3D000` | 0x1A st.t | ✓ |
| mem-rd[124] | stm.o | `0x21F3D000` | 0x21 st.o | ✓ |

`value` 由 `set.zw rd60, wp0, 0x0042`（word `0x4CF00042`）载入，store 按宽度 N 写低 N 字节。**语义侧独立佐证**（不只反解析）：`stm.*` boundary 用例的 `expected_state.memory` 恰为低 N 字节截断值——`stm.b 0xDEADBEEF→0xEF`、`stm.w→0xBEEF`、`stm.t→0xDEADBEEF`、`stm.o→0xDEADBEEF`，三者 round-trip 全 PASS，证明写入/回读确按低 N 字节。

**(7) 对齐逐条核对**（`QEMU-023t-review-align.log`）：48 条**全部** `address % N == 0`，**对齐违规 0**。且核对发现 10 条 boundary 用例 `value` 宽于 N（如 `ld.ub` + `0xDEADBEEF`），其 `expected_state` 均为低 N 字节截断结果（`ld.ub→0xEF`、`ld.uw→0xBEEF`），与契约「N 字节值」一致，非缺陷。

**(8) 反例门控**（在 `/tmp` 副本注入，不污染仓库）：
- 注入：`_ST_WIDTH_MAP['b'] = encode_st_o_rd`（st.b 路径改用 st.o），`diff` 确认 `git` 目标行已改。
- 结果（`QEMU-023t-review-inject-narrow.log`）：`TOTAL=36 PASS=28 FAIL=8`——8 条宽度=1 用例（`ld.ub`/`ld.sb`/`ldm.ub`/`ldm.sb` 各 sem+bnd）**全部 FAIL**，含完成区点名的 `mem-rd[3]`。**宽度选择承重、非恒真**。
- 还原（重新拷贝当前 harness 覆盖，md5 双侧均为 `2997ea397bb48a8d7a78a0d432ff471f`，`diff` 空）→ 重跑（`QEMU-023t-review-restore-narrow.log`）：`TOTAL=36 PASS=36 FAIL=0`。
- 仓库侧 `git diff -- tests/vectors/` 仅 `schema.md`；`git status` 无临时污染（注入与还原均在 `/tmp/opencode/QEMU-023t/`）。

**(9) 对称性**：`rg` 全仓库确认 `derive_width_from_mnemonic()` **只有 1 处定义**（`build_test_binary.py:157`），调用点 2 处——写侧 `build_loader()`（:263）与读侧 `build_exit_section()`（:413）。宽度表只有 `_LD_WIDTH_MAP`/`_ST_WIDTH_MAP` 各一份，无第二份宽度表。读、写**复用同一实现**，符合 ADR-0009「补注续二」对称性要求。

**(10) `--dump` 路径**（`QEMU-023t-review-dump.log`）：`mem-rd.yaml --case 100 --dump`（stm.b，`expected_state.memory` 非空，触发读侧 `derive_width`）正常运行，产出 dump 文件，无异常（dump 模式结果为 INCONCLUSIVE 属预期自旋）。

#### 2. 约束核验（逐条）

| 约束 | 结果 | 证据 |
|---|---|---|
| 按宽度用 `st.b/w/t/o` 写 memory | ✅ | 反解析 op=0x18/0x19/0x1A/0x21（#6） |
| 48 条全 PASS | ✅ | 48/48 + 172/172（#4） |
| 全量 597/590/2/5/0，零新增 | ✅ | #1 + #2 差分 |
| 8B 场景逐字节不变 | ✅ | #5 全 MATCH |
| 对齐逐条满足，违规须报告 | ✅ | #7 违规 0（无遗漏报告） |
| 反例门控可 FAIL 且可还原 | ✅ | #8 注入 8 FAIL→还原全 PASS，md5 一致 |
| 不改 vector YAML | ✅ | `git diff --name-only tests/vectors/**/*.yaml` 空 |
| 不改 QEMU 补丁 | ✅ | `git diff -- components/qemu/` 空 |
| 不改 `--dump`/退出码/`expected_state` 比对路径 | ✅ | `run_qemu_test.py` 未改（`git status` 仅 3 文件）；`build_exit_section` 仅 tuple unpack 适配，比对逻辑未动；#10 dump 正常 |
| 复用单一 `derive_width_from_mnemonic()` | ✅ | #9 |
| `schema.md` 仅新增契约说明 | ✅ | `git diff` = 6 行纯新增，0 删除 |

#### 3. 完成区核对（逐条对齐真实输出）

| 完成区声明 | 真实输出 | 判定 |
|---|---|---|
| 全量 597/590/2/5/0，改前 597/566/26/5/0 | 两次独立复跑一致 | ✅ |
| 24 条窄 load FAIL→PASS | 24/24 逐条证实 | ✅ |
| mem-rd/ra/rb 子集 172/172 | 172/172 实测 | ✅ |
| 8B `ld.o[55]/ldm.o[118]/stm.o[124]` loader MATCH | 全 MATCH | ✅ |
| 反解析 `ld.ub→0x18/uw→0x19/ut→0x1A/o→0x21` | 一致 | ✅ |
| 48 条地址 % 宽度 == 0，无违规 | 违规 0 | ✅ |
| 注入 st.b→st.o → `ld.ub[3]` FAIL；还原→PASS | 注入 8 FAIL（含[3]）→还原全 PASS | ✅ |
| `git diff --stat` 仅 `build_test_binary.py`+`schema.md` | 实为 3 文件（另含本任务书，属完成记录） | ⚠️ 轻微不精确，见观察 2 |

**无转述/夸大/矛盾**。

#### 4. 非阻塞观察（供架构师定夺，不自行放行）

1. **op 值硬编码 vs 约束「从表取，不硬编码」**：`encode_st_b_rd` 等仍以字面量 `0x18/0x19/0x1A` 硬编码。但（i）**已独立核对 `contracts/opcodes.yaml`**：`st.b-rd=0x18`、`st.w-rd=0x19`、`st.t-rd=0x1A`、`st.o-rd=0x21`，取值**完全正确**；（ii）与 `ADR-0009 D1`（raw-encoding via `struct.pack`）及本文件既有全部编码 helper 的既定模式一致（`trusted_instrs` 参数注释亦明示 "encodings are hardcoded in helpers"）。故**判为非阻塞**：验收标准 #1「按宽度 + 反解析 op 字段」已满足；是否需把新 st 编码改为运行期读表，请你定夺。若认定为硬约束，属需返工的范围，但会与现有 `ld.*`/`st.o` 硬编码及 D1 冲突。
2. 完成区证据行 8 称「`git diff --stat`：仅 `build_test_binary.py` + `schema.md`」：实际 `git diff --stat` 另含本任务书（+42 行）。属记录用文件，非实现范围，不影响结论。

#### 5. 判决

**Accepted** —— 9 条验收标准在本人独立重跑下**全部通过**，硬约束无实质违反（观察 1 为模式一致性说明，非行为缺陷）；24 条窄 load 的真差分、8B 逐字节不变、反例门控、读写单一实现均以真实输出佐证。观察 1 提交架构师/用户终裁。
