# SPEC-021t: 语义变更：st 类指令允许 0 号寄存器

**模块**：spec
**项目里程碑**：M2
**依赖**：`SPEC-014t`
**状态**：已验证

## 问题描述

0.5.3 中，st 类指令的 `rdha`/`rbha` 为 0 号寄存器时触发 ILLI 异常。0.5.4 改为允许——st 类指令的寄存器操作数都是读（没有写），所以 rd/rb/ra/rf 都允许为 0 号寄存器。

## 已确认方案（用户 2026-09-27）

- **所有 st 类指令**（`st.b`/`st.w`/`st.t`/`st.o` 的 rd/rb/ra/rf 形式 + `st.t-rf`）均允许 `rdha`/`rbha` 为 0 号寄存器
- **stm 类指令**（`stm.b`/`stm.w`/`stm.t`/`stm.o` 的 rd/rb/ra/rf 形式）也允许起始寄存器为 0 号
- stm 的范围限制（`rdha + immu6 > 64` 触发 ILLI）仍适用
- **ld 类指令约束不变**（约束已明确，无需修改）

## 受影响的指令

| 指令 | 变更 |
|------|------|
| `st.b rdHA, [rbHB, imms12]` | rdha != rd0 约束删除 |
| `st.w rdHA, [rbHB, imms12]` | 同上 |
| `st.t rdHA, [rbHB, imms12]` (rd/rf) | 同上 |
| `st.o rdHA, [rbHB, imms12]` (rd/rb/ra/rf) | rdha/rbha/raha != 0 约束删除 |
| `stm.b {rdHA:...}, [rbHB, rdHC]` | rdha != rd0 约束删除 |
| `stm.w {rdHA:...}, [rbHB, rdHC]` | 同上 |
| `stm.t {rdHA:...}, [rbHB, rdHC]` (rd/rf) | 同上 |
| `stm.o {rdHA:...}, [rbHB, rdHC]` (rd/rb/ra/rf) | rdha/rbha/raha != 0 约束删除 |

## 涉及文件

- `spec/SimRISC-01-存储.md`：删除 st/stm 的 `!= 0` 约束
- `.tao/knowledge/contract-isa.md`（由 SPEC-016t 处理，本任务只改 spec）

## 验收标准

1. `spec/SimRISC-01-存储.md` 中 st/stm 指令的 `!= 0` 约束已删除
2. stm 的范围限制（`rdha + immu6 > 64`）仍保留
3. ld 类指令约束未变
4. 其他内容未改动

## 完成区
**测试结果**：N/A（纯规范文档修改，无代码变更）
**修改文件**：`spec/SimRISC-01-存储.md`
**验收结果**：
- 存取RD（单st）：`rdha` 为 `rd0` 的 ILLI 限制已改为仅适用于 ld，st 允许 rd0 ✅
- 存取RD（stm）：`rdha` 为 `rd0` 的 ILLI 限制已改为仅适用于 ldm，stm 允许 rd0 ✅
- 存取RB：`rbha` 为 `rb0` 的 ILLI 限制已改为仅适用于 ld.o/ldm.o，st.o/stm.o 允许 rb0 ✅
- 存取RA：ra0 本就不触发异常（line 105），无需修改 ✅
- 存取RF：本无 rf0 限制，无需修改 ✅
- stm 范围限制（`rdha + immu6 > 64`）保留 ✅
- ld/ldm 约束未变 ✅
- 其他内容（对齐、immu6=0、寄存器重叠说明）未变 ✅
**新发现/坑**：无
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`spec/SimRISC-01-存储.md` 的 3 处修改

**逐行审查结论**：
1. Line 36 修改：原文对 ld/st 共用一句限制，改为 ld 限制 + st 允许，语义正确 ✅
2. Line 62 修改：原文对 ldm/stm 共用一句限制，改为 ldm 限制 + stm 允许，语义正确 ✅
3. Line 84 修改：原文对 ld.o/st.o/ldm.o/stm.o 共用一句限制，改为 ld 限制 + st 允许，语义正确 ✅
4. 未修改行检查：ra0 约束（line 105）本就不触发异常，无需改动 ✅；RF 无 rf0 约束 ✅；范围限制保留 ✅；对齐要求保留 ✅

**判决**：所有 finding 已修，可标「待验收」

#### 第 1 轮 reviewer 验收

**审查基线**：HEAD = `1be6384`（SPEC-014t，本任务依赖）。工作区 `spec/SimRISC-01-存储.md` 相对 HEAD 的差异即本任务产出。

**审查的文件**：
- `spec/SimRISC-01-存储.md`（产出）
- `spec/SimRISC-0.5.3/SimRISC-01-数据类指令.md`（0.5.3 存档，用于确认改动方向）
- `.tao/tasks/spec/SPEC-024t-opcodes字段调整.md`（下游一致性，见「观察」）

**重跑记录（独立执行，非采信完成区）**：

```
$ git diff -U0 -- "spec/SimRISC-01-存储.md"
@@ -36 +36 @@
-限制：`rdha` 为 `rd0` 时触发 ILLI 异常。（rd0 通用约定见 SimRISC-00）
+限制：`ld` 指令的 `rdha` 为 `rd0` 时触发 ILLI 异常。（rd0 通用约定见 SimRISC-00）`st` 指令允许 `rdha` 为 `rd0`（rd0 作为源寄存器读出 0）。
@@ -62 +62 @@
-- `rdha` 为 `rd0` 时触发 ILLI 异常
+- `ldm` 指令的 `rdha` 为 `rd0` 时触发 ILLI 异常；`stm` 指令允许 `rdha` 为 `rd0`（rd0 作为源寄存器读出 0）
@@ -84 +84 @@
-- `rbha` 为 `rb0` 时触发 ILLI 异常（rb0 通用约定见 SimRISC-00）
+- `ld.o`/`ldm.o` 指令的 `rbha` 为 `rb0` 时触发 ILLI 异常（rb0 通用约定见 SimRISC-00）；`st.o`/`stm.o` 指令允许 `rbha` 为 `rb0`（rb0 作为源寄存器读出 0）

$ git diff --stat -- "spec/SimRISC-01-存储.md"
 1 file changed, 3 insertions(+), 3 deletions(-)
```

```
$ bash /tmp/opencode/SPEC-021t/check_st_rd0.sh "spec/SimRISC-01-存储.md"; echo "EXIT=$?"
PASS: RD单段: ld rdha=rd0 触发 ILLI
PASS: RD单段: st 允许 rdha=rd0
PASS: RD多段: ldm rdha=rd0 触发 ILLI
PASS: RD多段: stm 允许 rdha=rd0
PASS: RB段: ld.o/ldm.o rbha=rb0 触发 ILLI
PASS: RB段: st.o/stm.o 允许 rbha=rb0
PASS: stm 范围限制 rdha+immu6>64 保留
PASS: stm immu6=0 限制保留
PASS: A5 所有 rdha=rd0 ILLI 表述均已限定为 ld/ldm
PASS: A5 所有 rbha=rb0 ILLI 表述均已限定为 ld.o/ldm.o
----
EXIT=0
```

**约束核验（逐条）**：

1. ✅ **验收 1 — st/stm 的 `!= 0` 约束已删除或改为仅适用于 ld/ldm**：line 36 改为 `ld` 触发 ILLI + `st` 允许 rd0；line 62 改为 `ldm` 触发 ILLI + `stm` 允许 rd0；line 84 改为 `ld.o`/`ldm.o` 触发 ILLI + `st.o`/`stm.o` 允许 rb0。全文仅剩此 3 处 `rd0`/`rb0` 寄存器零约束（line 105 的 `ra0` 为「不触发异常」，line 133 的 `rf0` 是目的寄存器注释，均非 st 约束）。
2. ✅ **验收 2 — stm 范围限制保留**：line 64 `- \`rdha + immu6 > 64\`（超出 rd63）时触发 ILLI 异常，不环绕、不截断` 原样存在；line 63 `immu6 = 0` 限制亦在。
3. ✅ **验收 3 — ld/ldm 约束未变**：3 处改动均为「在原共享约束上追加 st/stm 允许子句并限定 ld/ldm」，ld/ldm 的 ILLI 语义与原文一致；`-U0` diff 显示除这 3 行外无其他改动。
4. ✅ **验收 4 — 其他内容未改动**：`git diff --stat` = 3 insertions / 3 deletions，`-U0` 仅 3 个 hunk，均落在约束行；未触碰指令表、对齐说明、示例（如 line 58 的 `stm.b rd16, rb2, rd0, 8`）、版本号等。
5. ✅ **任务书「已确认方案」逐条对应**：st.b/w/t/o（rd 形式）+ st.t-rf 由 line 36 覆盖；stm 由 line 62 覆盖；RB 形式 st.o/stm.o 由 line 84 覆盖；RA（line 105 不触发异常）、RF（无 rf0 约束）本无需改动，与完成区一致。
6. ✅ **改动方向与 0.5.3 存档一致**：`spec/SimRISC-0.5.3/SimRISC-01-数据类指令.md` line 37/63 确为共享约束「`rdha` 为 `rd0` 时触发 ILLI」，本任务正是放宽该约束，方向正确。

**反例验证（自建检查器，确认可失败）**：将 4 个反例注入 `/tmp/opencode/SPEC-021t/`（未污染仓库）并重跑，均正确报 FAIL：

```
===== ce1（还原 line36 为共享约束，st 不再允许） =====
FAIL: RD单段: st 允许 rdha=rd0 / FAIL: A5 未限定为 ld/ldm        EXIT=1
===== ce2（删除 stm 范围限制行） =====
FAIL: stm 范围限制 rdha+immu6>64 保留                          EXIT=1
===== ce3（还原 line62 为共享约束） =====
FAIL: RD多段: ldm/stm / FAIL: A5 未限定                          EXIT=1
===== ce4（还原 line84 为共享约束） =====
FAIL: RB段: ld.o/ldm.o / FAIL: A5 未限定 rbha                    EXIT=1
```

即该检查器非「只报 PASS」，删约束/留错约束/丢范围限制均能被检出。

**观察（非本任务失败项，供架构师）**：`contracts/opcodes.yaml`（st 各条仍含 `rdha != rd0`）与 `contracts/legality_rules.yaml`（`store_src_rd0`、`rb_base_rb0_store`）仍为 0.5.3 语义，与本 spec 变更不一致。核对任务书：本任务「涉及文件」仅列 `spec/SimRISC-01-存储.md`，并注明 contract-isa.md 归 SPEC-016t；`contracts/opcodes.yaml` 的同步已由 **SPEC-024t**（验收标准 3「st 零寄存器 legality 放宽」）承接（当前 `待开始`）。故属**跨任务待办**而非本任务缺陷，不构成打回理由，但 SPEC-024t 完成前 spec 与机器可读合约存在暂时不一致，提请架构师关注。

**判决**：**Accepted**。4 条验收标准在本人独立重跑下全部通过，改动范围与任务书约束（仅改 spec、只放宽 st/stm 零寄存器约束、保留 stm 范围限制）一致，反例验证证明检查有效。建议主会话将状态置为 `已验证`。终审与跨任务一致性由架构师定夺。