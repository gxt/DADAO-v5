# m17-testcases-002: `ldm.*` 注释订正 + `rf0` 目的用例 + `immu6=63` 边界补齐

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-testcases-001`（签名区数据派生与 `check-inst-sig`；本任务改 `.S` 后须重生成）
**可并行分片**：否
**预估**：2–3 h
**档位**：小改
**状态**：待开始

## 背景（用户 2026-11-20 观察，三条均已现场核实）

1. **注释有误**：`tests/inst/01-load-store/ldm.t_rrri_rf.S:5` 写「`rf0` 作目的合法（**按 FCSR 写掩码**）」——`.t` 只写目的低 32 位，`rf0` 在该写入窗口内**只有 `[4:0]` 可写**（`[33:32]` 舍入模式与只读 qNaN/SBZ 保持原值，见 `spec/SimRISC-01 §4` 写入宽度注）。同句在 `ldm.o_rrri_rf.S:5` 对 `.o` 成立，**不要改**。
2. **缺 `rf0` 作目的的用例**：`ldm.o` 有 `ldm.o {rf0:rf1}, [rb3, rd19]`（`ldm.o_rrri_rf.S:67`），`ldm.t` 全文件 `rf0` 只在第 5 行注释里。
3. **`immu6=63` 边界只在 `ldm.ub`**：`ldm.ub_rrri_rd.S:50-58` 有最大合法个数整组装入 + 回写；`ldm.ut`/`ldm.uw` 没有。

## 目标

1. 订正 `ldm.t_rrri_rf.S:5` 的注释为「只写低 32 位；`rf0` 内仅 `[4:0]` 可写，其余位保持」；
2. `ldm.t` 补一例 **`rf0` 作目的**：装入后断言 `rf0[63:32]` 与 `rf0[31:5]` 保持原值、`rf0[4:0]` = 写入值的低 5 位（目的范围可取 `{rf0:rf1}`，起点 0 不被判 ILLI）；
3. `ldm.ut` / `ldm.uw` 各补一例 **`immu6=63`**：`{rd1:rd63}` 整组装入 + 回读（索引用 `rd0`，理由同 `ldm.ub` 该例注释：用 `rd19` 会落进传送范围 ⇒ ILLI）。

## 验收（逐条贴真实 rc）

1. **注释修正不改指令流**：该镜像 `.text` md5 与改前相同；全仓 `grep "按 FCSR 写掩码"` 只剩 `ldm.o_rrri_rf.S`（`.o` 的正确表述）；
2. **`rf0` 用例逐位**：`rf0[63:32]` 不变、`[31:5]` 不变、`[4:0]` = 低 5 位（三条断言各自可达 FAIL）；
3. **`immu6=63` 逐字节**：`ldm.ut`/`ldm.uw` 各 63 元素装入后回读与源数据逐字节相等；
4. **三平台**：qemu / gem5 / chipyard 同一 ELF 的签名流逐字节相等（chipyard 若被其它任务占用 ⇒ 记 BLOCKED + 替代证据，不得并发构建）；
5. **签名数据同步**：`tests/data/inst-signature/expected.tsv` 与 `inputs.sha256` 重生成，`make check-inst-sig` 绿（新增用例的槽全部纳入）；
6. **可达 FAIL ≥2 路**（`cp`+md5）：① 把 `rf0` 断言里的 `[4:0]` 期望改错 ⇒ 红；② 把 `immu6=63` 的数量改 62 ⇒ 回读红；
7. 门控：`check-inst-asm` **272/272**、`check-case-ledger`（`--write` 重生成）、`check-tests-index`、`check-inst-macro-scope`、`check-knowledge-refs` 真实 rc。

## 完成区必须写

**需重测周期的镜像清单**：本任务改动指令流的镜像（`ldm.t`、`ldm.ut`、`ldm.uw`）——它们的「实测总拍数」记录作废；按指令类的周期表不受影响（只依赖同族样本）。

## 约束

独立 `git worktree`；不提交 git；**只改这三个文件 + 必要的数据重生成**（最小原则，不顺带改其它 `ldm.*`/`ld.*`）；不改 `spec/` 与契约；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
