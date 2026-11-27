# m17-testcases-006: `stm` 注释订正 + `immu6=63` 边界用例

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-idl-020`（同改 `tests/inst` 共享文件与期望数据，须串行）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

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

**测试结果**：新增 5 例单镜像 QEMU 全绿；证据脚本（运行期 `run.sh`）ALL PASS：`make check-inst-asm` 272/272 rc=0、`make check-idl` 272/272（parties=idl,qemu）rc=0；`check-case-ledger`/`check-tests-index`/`check-manifests-guard` rc=0；2 路注入 ⇒ 均红、`cp`+md5 还原后回绿。
**修改文件**：`tests/inst/01-load-store/` 的 `stm.b_rrri_rd`、`stm.o_rrri_{ra,rb,rd,rf}`、`stm.t_rrri_{rd,rf}`、`stm.w_rrri_rd`（8 个 `.S`）；`tests/data/inst-signature/{expected.tsv,inputs.sha256}`；`tests/case-ledger.tsv`（`tests/inst.yaml` 无计数，不变）。
**验收结果**：链例点号 1..N 内续排、旧链例槽号不变：`stm.b` 18→21、`o_ra` 14→18、`o_rb` 23→27、`o_rd` 26→30、`o_rf` 14→18（`t/w` 不变）；故障例点号为满足「1..N 连续」门控顺延（如 `stm.b` 19-24→22-27）。槽数 4537→4556（+19）；镜像仍 272。
**新发现/坑**：① RB 组 `immu6=63` 装入 `{rb1:rb63}` 会覆盖签名写指针 `rb30`（元素 29）及 `rb29/rb27` ⇒ 新例先 `rb2rd` 暂存 `rb30`、存后 `rd2rb` 恢复（否则 `__REC` 写坏地址 → CFXMEM，hmon 重入）。② `ldm` 禁重叠 ⇒ RB 组装入/存储基址都只能用 `rb0`，两处地址用 `.org` 钉住 + 字面常量偏移（`MUNI−0x2388`、`MSTORE−0x2390`）。③ `MSTORE+0x038` 已被本文件点号 3 写脏（`A0..AF`）⇒ `stm.b` 新例先用 `st.o` 重植末字节 `0xA7`，不依赖前序用例。
**遗留问题**：无

## 审阅记录 → 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| RB 组装入 `{rb1:rb63}` 覆盖签名指针 `rb30` | ✅已修 | 装入前 `rb2rd rd18←rb30`、存储后 `rd2rb rb30←rd18` | `stm.o_rrri_rb` 27 槽 QEMU PASS |
| RB 组装入不能用 `rb3` 作基址（`ldm` 禁重叠 ILLI） | ✅已修 | 装入/存储都改 `rb0` + `.org` 钉址字面偏移 | 同上，且 `validate-vectors`/点号连续性 PASS |
| `stm.b` 尾单元期望依赖点号 3 的写脏状态（`0xAF`） | ✅已修 | 新例先 `st.o` 重植 `0xC0DE0000000000A7`（在 `ldm` 之前，避免覆盖源组元素） | `stm.b_rrri_rd` 21 槽 QEMU PASS；expected 末槽 `0x…78A7` |

## 审阅记录 → 第 1 轮 reviewer 复核

**审阅文件**：8 个 `stm.*.S`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`、`tests/case-ledger.tsv`、`tests/inst/macros/inst_test.inc`、运行期证据目录内的 `run.sh`、本任务书。

**重跑记录（全部本人执行，真实输出/rc）**
- 仓库根执行运行期证据目录内的 `run.sh` ⇒ `ALL PASS`，rc=0（63 s；含工程 2 路注入红→md5 还原→回绿与 L2/L1 门控）
- `make check-inst-asm` ⇒ rc=0，`272/272 镜像通过（272 id；链例 + 故障链 632 例）`
- `make check-idl` ⇒ rc=0，`272/272 例四方一致（parties=idl,qemu；主清单 272 / pending 0 / 现场派生 272）`
- `make check-case-ledger` ⇒ rc=0（现场 5718 条）；`make check-tests-index` ⇒ rc=0（492 条）；`make check-manifests-guard` ⇒ rc=0
- `make inst-signature-data` 重生成 ⇒ rc=0，`272 镜像 / 4556 槽`，两份数据文件 md5 前后相同（非手改）

**独立注入 3 路（均不复用工程 2 路；`cp` 备份 + md5 还原）**
- ① `stm.o_rrri_ra` 中槽 0x0F8 期望 `…6978→…6979` ⇒ `[FAIL] stm.o_rrri_ra 检查点 18 rc=16`；还原 md5 相等 ⇒ 回绿 rc=0
- ② `stm.b_rrri_rd` 植入值 `A7→A6`（钉第 64 字节）⇒ `[FAIL] stm.b_rrri_rd 检查点 21 rc=21`；还原 md5 相等 ⇒ 回绿 rc=0
- ③ `stm.o_rrri_rd` 源组 `MUNI→MDUMP` ⇒ `[FAIL] stm.o_rrri_rd 检查点 30 rc=27`；还原 md5 相等 ⇒ 回绿 rc=0

**约束核验**
1. 注释：第 5 行 `rd0`=读出 0（b/o_rd/t_rd/w_rd）、`rb0`=当前指令地址、`rf0`=FCSR 含 `[33:32]`/`[4:0]`/只读 qNaN 与复位值、`ra0`=`{RACNT,MRPTR}` 含三字段；`grep` 中「读出 0/当前指令地址」未命中 ra0/rf0 行 ✓
2. immu6=63：5 文件各 1 例，`ldm.o {X1:X63}` 自 `MUNI` 装入、`stm.*` 落 `MSTORE`；o_* 检查 0x000/0x0F8/0x1F0（首/中/尾）+ 0x1F8（第 64 元素未写）；`stm.b` 检查 0x000/0x020/0x038（63 字节）并以植入 `A7` 钉住第 64 字节未写（大端，`spec/DADAO-21-ABI`）✓
3. 点号：与 HEAD 逐条比对——旧链例点号全同、故障例宏名相同且整体顺延（`b` +3、`o_*` +4）、8 文件均 1..N 连续无重号；槽数 4537→4556（+19）现场派生 ✓
4. 期望独立：抽 `ra15`=`MUNI` 字面量 `0x0F1E2D3C4B5A6978`、`ra18`=模式 `A0+i`（i=63 ⇒ `…DF`）手算一致；来源为 `.S` 内联常量，非 QEMU 实测反推 ✓
5. 门控：上列 5 条命令本人重跑全 rc=0 ✓
7. 越界：`git status -uall` 12 行 = 完成区 11 文件 + 任务书自身；`tests/inst.yaml`、`idl/`、`tools/` 零改动；既有 `.text` 仅第 5 行注释与末尾新增块，删除行仅故障例点号顺延（第 3 项 1..N 连续所要求）✓

**判决：Accepted**（非阻断备注：`run.sh` 第 2 节只数 `X1:X63` 行、不断言源=`MUNI`/目标=`MSTORE`，已由本次人工核验与注入③补足）
