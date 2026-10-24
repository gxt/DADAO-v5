# INFRA-103t: 陈旧引用/文案收口 + 两个工具缺陷

**模块**：infra
**项目里程碑**：M9（收尾前）
**依赖**：`SPEC-167t`（册名已稳定）、`SPEC-170t`（schema `opc`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源

收口以下已登记的缺陷/陈旧项（全部为"文档/工具与现状不一致"，非新功能）：

| issue | 一句话 |
|---|---|
| `ISS-160` | `contract-isa` 投影层仍列已删伪指令；`impact-matrix` 悬空；`check_spec_codeblocks` 的 `PSEUDO_INSTRUCTIONS` 陈旧 |
| `ISS-208` | `ADR-0012 D9.5` 与 `check_scope.py` 注释写 `227→228`，与现场不符 |
| `ISS-308` | `0x77000000` 字面残留（该编码已归 `OPC-MISC` 并迁 `op 0x47`） |
| `ISS-311` | `components/musl/README.md`「原子」段过期（仍称无可用原子、`__clone` 返回 `-ENOSYS`） |
| `ISS-318` | FP 异常措辞缺口：`UF` 未写"tiny 且 inexact"、tininess 检测点未声明、标志 sticky 未明示 |
| `ISS-090` | `components/qemu/changelog.md` 缺任务级记录（自 2026-09-23 起） |
| `ISS-300` | `install-host` 之外的二进制替换属例外手法，应写进纪律/文档 |
| `ISS-329` | `contract-isa.md §6.6` 仍列已删伪指令 `not.o`/`neg.o` |

**另两个工具缺陷**（本册一并修，来自 `LLVM-126t`/`SPEC-158t` 披露）：
- `tools/llvm/gen_asm_list.py --embed-spec` **非幂等**（会改 12 册）；
- `tools/llvm/gen_isa_coverage.py` 生成的 `frem_proof()` 对 `.work/source` 用 `git grep`（未跟踪目录）⇒ **死断言**。

## 目标

1. 逐条修正上表 8 项（以**现场事实**为准；每条给出"改前是什么、现在该是什么"的依据）。
2. `gen_asm_list --embed-spec` 改为幂等（二次运行零 diff）。
3. `frem_proof()` 改为对**已跟踪的补丁源**取证（或删除该死断言并说明）。
4. 顺带核实一条**待查项**（不立 issue）：QEMU `fosclb` 溢出是否置 `OF`/`UF` —— 用 2 个用例现场判定，**只出结论，不改语义**；若确认缺标志，登记新 issue 不在此修。

## 验收

1. 8 条 issue 各有"改前/改后"现场证据（grep 或门控输出），并在完成区写清每条的依据。
2. `gen_asm_list --embed-spec` 二次运行 `git status` 零变化。
3. `frem_proof` 不再是死断言（注入：把 `FREM` 错接 `forem` ⇒ 该证明必须红）。
4. `fosclb` 判定结论（置/不置 OF/UF）与依据。
5. 受影响门控：`check-spec-refs`、`check_spec_codeblocks`、`check_scope`、`check-asm-list`、`check-asm-list-drift`、`check_qemu_trans --strict`（266/266）、`check-instrinfo`、`check-contracts-dir`；`make check`(L1) 一次 rc=0。
6. **可达 FAIL ≥2**：① `contract-isa` 塞回 `not.o` ⇒ 契约门控红；② 把 `frem_proof` 改回死断言 ⇒ 注入 `FREM`→`forem` 时不再红（说明死断言）。
7. 证据 `.work/evidence/<任务ID>/run.sh`。

## 接口规范

- **输入**：`.tao/contracts/**`、`components/*/README.md`、`components/qemu/changelog.md`、`tools/llvm/gen_asm_list.py`、`tools/llvm/gen_isa_coverage.py`、`docs/**`、`spec/**`（只读，除 `ISS-318` 的措辞）。
- **输出**：文档/工具修正 + 结论。
- **约束**：不改指令语义/编码；`ISS-318` 只改措辞不改规则；不 commit/push；临时目录 `/tmp/opencode/INFRA-103t/`。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
