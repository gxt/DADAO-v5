# QEMU-028t: `st.*` 源为 0 号寄存器被误判 ILLI 的修复

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：`SPEC-055t`（`ADR-0015` Accepted；合约澄清）
**状态**：待开始

## 问题

QEMU 的 4 个翻译函数把 `st.*` 的**源**字段 `ha` 当成**目的**，误判 ILLI：

```c
static bool trans_st_b_rrii_rd(...)  { if (a->ha == 0) { gen_exception_illegal(ctx); return true; } ... }
static bool trans_st_w_rrii_rd(...)  { if (a->ha == 0) { ... } }
static bool trans_st_t_rrii_rd(...)  { if (a->ha == 0) { ... } }
static bool trans_st_o_rrii_rd(...)  { if (a->ha == 0) { ... } }
static bool trans_st_o_rrii_rb(...)  { if (a->ha == 0) { ... } }   ← 源为 rb0
```

`stm.*` 的 RRRI 变体同理（须逐条核查）。

按 `ADR-0015` D2/D3：`st.*`/`stm.*` 的**源**为 `rd0`（读出 0）或 `rb0`（读出**当前指令的地址**）**均合法**，**不得**触发 ILLI。

## 修改内容

1. 删除上述 `st.*`/`stm.*` 翻译函数中 `a->ha == 0 → ILLI` 的检查（**源**侧）
2. **保留** `ld.*`/`ldm.*` 的 `ha == 0 → ILLI`（那是**目的**侧，合法约束）
3. **保留** `orrr/orri` 的 `hb == 0 → ILLI`（目的侧）
4. **保留** `ra` 变体的现状（`ra0` 合法）
5. **同类全排查**：把「检查了 `ha`/`hb` 且该字段是**源**」的函数全部找出并修正；在完成区给出「保留/删除」逐条清单

## 验收标准

1. `st.b/w/t/o`（RD）源为 `rd0`、`st.o`（RB）源为 `rb0` 均**不再 ILLI**；写入值分别为 **0** 与**当前指令地址**
2. `ld.*`/`ldm.*` 目的为 0 号寄存器**仍** ILLI；`orrr/orri` 目的为 rb0 **仍** ILLI（**不得**误删）
3. **探针证据（最小 ROM / harness）**：
   - `st.o rb0, [rbN, 0]` 后从内存读回的值 = **该条 `st.o` 指令的地址**（非下一条）
   - `st.b rd0, [rbN, 0]` 写入 0
   - `ld.o rdX, [rb0, imm]` 能按「当前指令地址 + 偏移」取数（PC 相对基址可用）
   - 分支偏移/极性**逐条**核对（不得抽样），并给出「仅令该断言比较值错 → FAIL」的真实输出
4. 补丁集按 `docs/spec/component-patching.md`（一文件一补丁）；`make build-qemu` PASS；`make check` EXIT=0（含 `check_qemu_trans` 的 `254/254` 或相应计数）
5. 反例验证：把某条 `st` 的检查加回 → 可检出；**注入须可复原且须重建**（给出 `git status`/`git diff` 与重建证据）
6. 不改 `docs/m1-retrospective.md`

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
