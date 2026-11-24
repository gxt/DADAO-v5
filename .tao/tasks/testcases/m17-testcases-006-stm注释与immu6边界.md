# m17-testcases-006: `stm` 注释订正 + `immu6=63` 边界用例

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-idl-020`（同改 `tests/inst` 共享文件与期望数据，须串行）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-24 复核发现）

复核 `stm.b` / `stm.o` 系列时发现两处缺陷：

1. **注释错误**：8 个 `stm.*.S` 的第 5 行都写「`X0` 作源合法（读出 0/当前指令地址）」。该说法只对 `rd0`（读出 0）与 `rb0`（读出当前指令地址）成立；对 **`ra0`**（读出 `{RACNT, MRPTR}`，`SimRISC-00 §2.4`）与 **`rf0`**（读出 FCSR：`[33:32]` 舍入、`[4:0]` 标志、只读 qNaN 位，复位 `0x7FF8_0000_7FC0_0000`，`SimRISC-00 §2.3.1`）不成立。
2. **缺 `immu6=63` 边界**：`ldm` 系列已有「`immu6=63`（最大合法个数）整组」用例，`stm.b` 与 `stm.o`（ra/rb/rd/rf）尚未覆盖。

## 要做

1. 逐文件订正第 5 行注释，按寄存器写准：
   - `rd0` ⇒ 读出 **0**；`rb0` ⇒ 读出**当前指令地址**；
   - `rf0` ⇒ 读出 **FCSR**（`[33:32]`/`[4:0]`/只读 qNaN 位；复位 `0x7FF800007FC00000`）；
   - `ra0` ⇒ 读出 **`{RACNT, MRPTR}`**（`[63:54]` SBZ、`[53:48]` RACNT、`[47:0]` MRPTR）。
   覆盖文件：`stm.b_rrri_rd`、`stm.o_rrri_{ra,rb,rd,rf}`、`stm.t_rrri_{rd,rf}`、`stm.w_rrri_rd`（共 8 个）。
2. 给 `stm.b_rrri_rd` 与 `stm.o_rrri_{ra,rb,rd,rf}` 各加 **1 个 `immu6=63` 链例**：
   - 源组用 `MUNI`（64 个同值 8 字节单元）经 `ldm.o {X1:X63}` 装入（ra/rf 变体用对应 bank 的 `ldm.o`）；
   - 目标 `MSTORE`（64 × 8 B = 512 B；`stm.o` 的 63 × 8 B = 504 B 恰好放得下）；
   - 检查首/中/尾 3 个数据单元 + 最后一个元素；`stm.b` 按 63 字节检查首/中/尾。
3. 点号续排（旧点号不变），重新生成 `tests/data/inst-signature/{expected.tsv,inputs.sha256}`（`make inst-signature-data`），同步 `tests/case-ledger.tsv` / `tests/inst.yaml`（计数变化按 `check-case-ledger`/`check-tests-index` 口径）。
4. 不改既有用例的 `.text` 与点号；不改 `.idl`/执行器/其它册。

## 不做

- 不改 `ldm` 系列；不改 `stm` 语义；不新增镜像（仍 272，例数/槽数增加）。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 完成区 ≤30 行、不写运行期路径；计数现场派生。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-inst-asm` rc=0（272/272，QEMU）；`make check-idl` rc=0（272/272，槽数现场统计）；
2. `grep` 断言 8 个文件的第 5 行**不再出现**「读出 0/当前指令地址」对 ra0/rf0 的误述；`ra0`/`rf0` 行含 `RACNT`/`FCSR`；
3. 新增 `immu6=63` 例在每个文件内可达（链例点号递增、`__CHECK_*` 期望与 `MUNI` 值一致）；
4. **可达 FAIL ≥2 路**：① 把某 63 例的最后一个期望槽改错 ⇒ 该例红；② 把 `immu6` 从 63 改成 62 而检查点不变 ⇒ 红；`cp`+md5 还原后回绿；
5. `check-case-ledger`/`check-tests-index`/`check-manifests-guard` rc=0。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
