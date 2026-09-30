# TESTCASES-019t: `st.*` 源为 0 号寄存器的向量修正与补正向用例

**模块**：testcases
**项目里程碑**：M1→M2
**依赖**：`SPEC-055t`（`ADR-0015` Accepted）、`QEMU-028t`（实现已修）
**状态**：待开始

## 问题

`tests/vectors/isa/mem-rd.yaml` / `mem-rb.yaml` 中把 **`st.*` 的源**为 0 号寄存器判为 **ILLI**（与 `ADR-0015` D2/D3 相反），且该错误规则被 validator 的 F10 守卫**固化**：

- `mem-rd.yaml`：多条 `st.b/w/t/o`（RD）用例 `word: '0x10003000'` 等，`expected_fault: ILLI`，`notes: rd0 as dest/src → ILLI (rd_dest_rd0 / store_src_rd0)`
- `mem-rb.yaml`：`st.o_rrii_rb` 用例 `word: '0x23003000'`，`expected_fault: ILLI`，`notes: rb0 as dest/src → ILLI (rb_dest_rb0 / rb_base_rb0_store)`
- `tools/testcases/validate_vectors.py` 的 **F10④**（`deferred.md` 登记）：只提取 `rdha` 判「dest/src 非 rd0」，**未区分 dest/src**（RB 变体完全未覆盖）

> 注：上述旧用例的 `hb = 0`（基址 = `rb0`）——修好后会变成「写当前指令地址所在处」的**野写**，故**不可**简单翻转期望值，须**重设用例**。

## 修改内容

1. **删除/改写**「`st` 源为 0 号寄存器 → ILLI」的用例（RD 与 RB 两族）
2. **保留**「`ld.*`/`ldm.*` 的**目的**为 0 号寄存器 → ILLI」用例（正确）
3. **补正向用例**（期望值由 `ADR-0015` + `SimRISC-01/06` 独立推导，**不得**取自实现）：
   - `st.b rd0, [rbN, 0]`（`rbN` 预置为 RAM 地址）→ 内存写入 **0**；`expected_state` 反映之
   - `st.o rb0, [rbN, 0]` → 内存写入**该 `st.o` 指令的地址**（须回读校验）
   - `ld.o rdX, [rb0, imm12]` → 按「当前指令地址 + imm」取数（PC 相对基址可用；预置内存内容已知）
4. **修 validator F10④**：按 `role` 区分 **dest / src**——仅**目的**为 0 号寄存器判 ILLI；**源**不得判 ILLI；并补齐 RB 变体（`rb_dest_rb0` 仅限 `ld.o-rb`/`ldm.o-rrri-rb` 的 `rbha` 与 `orrr/orri` 的 `rbhb`）
   - 修后**转严**：对「`st` 源为 0 号寄存器却被写成 ILLI」的向量**报错**
5. 覆盖率/清单同步（`inventory.md` 如受影响）

## 约束

- 期望值**独立推导**，禁止从 QEMU/LLVM 输出反填
- **不得**弱化既有断言；改动须逐条列出「旧 → 新 → 依据」
- 语义零变化（除本 ADR 明确变更者）

## 验收标准

1. 无「`st` 源为 0 号寄存器 → ILLI」的用例残留（给出 `grep` 证据）
2. 新增正向用例存在，且期望值可由 `ADR-0015` + spec 逐条复算（完成区贴推导）
3. validator F10④ 按 role 区分 dest/src；**注入反例**（把某正向用例改成 ILLI、或把 `ld` 目的的 ILLI 用例删掉）→ 检查**报错**；复原后无残留
4. `validate_vectors` 全绿（`make check` EXIT=0）；harness 在新 QEMU 上跑通新增用例
5. 数据级覆盖率不下降（给出新旧对比）

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
