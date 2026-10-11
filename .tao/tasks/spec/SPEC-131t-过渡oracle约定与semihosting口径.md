# SPEC-131t: 过渡 oracle 约定 + semihosting `cfxha` 口径收口（规范/合约/锁）

**模块**：spec
**项目里程碑**：M7
**依赖**：无（同改 `spec/`/锁 ⇒ 与其它 `spec` 任务串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #7`）：**过渡 oracle 采用**——宿主机结果作参照 + **明确边界**（端序／`long double`=f64 vs 宿主 80-bit／`fenv`／UB／实现定义），**登记为「非判据真源」**（将来 `GOLDEN-*` 替换）。
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #9`）：semihosting 用 `trap cfx3, 0x30000`；**须核 M6 探针 `cfx_umon` 是否为 cfx3，不一致要登记**。
  - 实测事实（本 `k`）：`cfx_umon` = **cfxha 0**；`cfx3` = `hmon`（`spec/DADAO-12 §1`）；v5 `tests/scripts/codegen_crt0.s` 与 `tools/qemu/min_rom_probe_049t.py` 均用 `trap cfx_umon, 0x30000`；`contract-semihosting §1` 与 QEMU 实现（`trans_ctrl.c.inc`）均**只查 `immu18[17:16]`、与 `cfxha` 无关**。
  - 现行正文：`spec/Process-05-里程碑TDD规范.md §2`（L3「独立 oracle（host 侧按 IR/spec 语义派生）」）；`spec/Machine-01 §5.1`；`.tao/knowledge/contract-semihosting.md §1`；`.tao/knowledge/contract-see.md`。
- **输出**：
  1. **过渡 oracle 约定**：在 `spec/Process-05-里程碑TDD规范.md`（§2 或其下新增小节）写入「**过渡 oracle**」——宿主机结果**仅作参照**、**非判据真源**；边界清单（**端序** big-endian vs 宿主 / **`long double`** = f64（`sizeof=8`）vs 宿主 80-bit / **`fenv`**（v5 `machine/fenv.h` 退化为 `FE_TONEAREST`）/ **UB / 实现定义**）；标注将来由 `GOLDEN-*` 里程碑替换。
  2. **semihosting `cfxha` 口径**：`contract-semihosting §1` / `spec/Machine-01 §5.1` 明确「tag 判定与 `cfxha` 无关」的**现行口径**，并对 `cfx3` vs `cfx_umon`(cfx0) **不一致**给出**处置结论**（保留现状并注明为何与 `cfx3` 等效，**或**按用户裁定统一为 `cfx3`——**须用户裁定后**，`INTEG-033k §避坑`）。
  3. 相关 `spec/` 册 `sha256` 锁同步（`spec/*.md` 若纳入锁）。
- **约束**：
  - **Spec-first**：正文以 `spec/` 与 `contract-*` 为准；ADR 不承载正文（`Process-03`）。
  - **不改上游只读册**（`SimRISC-*`/`DADAO-*`）；本任务只改 v5 自定册/合约（`Machine-01`/`Process-05`/`contract-*`）。
  - **`cfxha` 口径改动须用户裁定**（`AGENTS.md`「最小安全设计」：需语义裁定才留问；不猜测、不自行改契约）。
  - **计数不写死**；只动任务范围，越界须披露。

## 验收标准

1. **过渡 oracle 正文**：`spec/Process-05 §2`（或新增小节）含「宿主机结果 = 参照、**非判据真源**」+ **四类边界**（端序/`long double`/`fenv`/UB-实现定义）+ `GOLDEN-*` 替换指针（`grep` 真实输出）。
2. **semihosting 口径**：`contract-semihosting §1` / `Machine-01 §5.1` 明确「tag 判定与 `cfxha` 无关」；**`cfx3` vs `cfx0` 不一致有明确处置**（或明确标注「待用户裁定」并保留现状）。
3. **锁同步**：`make check-spec-readonly`（或等价）EXIT=0；被改册 `sha256` 锁同步。
4. **门控**：`make check` EXIT=0；`check-spec-refs` 无新增违规。
5. **反例门控**：对新增/修改断言可注入反例 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿（若有可注入点）。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
