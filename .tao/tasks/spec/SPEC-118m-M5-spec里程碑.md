# SPEC-118m: M5 spec 里程碑

**模块**：spec
**项目里程碑**：M5
**状态**：待开始
**目标**：规范层支持 M5——① **ADR 决策落地**：`ADR-0020`（SEE/HEE 与 semihosting，D1–D14）新建、`ADR-0004` 修订（新 bootrom 与加载模型，R1–R3，含 **R3「RAM 基址是否随 bootrom 调整」判定/记录**）、`ADR-0016` 范围判定（S1）——**每个 decision 逐条经用户确认**；② **SEE/HEE + semihosting 规范正文入 `spec/`** + 投影（`contract-sbi.md`/`contract-see.md`/`contract-semihosting.md`）+ `spec/README` 投影表；③ **re-scope**：`trap`/`escape`/`cfx2rc`/`cfx2rd` 由 `excluded`→已实现（`contracts/*` + 投影 + `check_scope` 计数 155/11/227；`SimRISC-12` 保持 deferred）；④ **大小写敏感修订**（`Toolchain-01 §2.1` + `contract-asm §2.1` 撤销「不敏感」；`ISS-157` 以「条款撤销」结案）；⑤ **`Process-05 §6` 落点规则补正**（`.dadao/tests/` 口径）。
**关联任务**：`SPEC-113t`、`SPEC-114t`、`SPEC-115t`、`SPEC-116t`、`SPEC-117t`（5 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`.tao/adr/adr-0020-see-semihosting.md`（`Accepted`）、`adr-0004` 修订、`adr-0016` 范围判定；`spec/DADAO-12`（+`DADAO-13/21/22` 相关）semihosting 正文；投影 `contract-sbi.md`/`contract-see.md`/`contract-semihosting.md`；`contracts/opcodes.yaml` 4 条 re-scope；`check_scope.py` 计数
- 用户逐条确认记录：`ADR-0020` D1–D14、`ADR-0004` R1–R3、`ADR-0016` S1 **逐条**已确认（完成区原话/摘要）；无「未确认即 `Accepted`」
- **R3 归属**：判定结论 + 「仅判定/记录、实现另立任务」已登记
- `python3 tools/spec/check_scope.py` EXIT=0（`m1=155`/`excluded=11`/`total=227`）；`make check` EXIT=0（`check-spec-refs`/`check-legality-drift`/`check-asm-*` 绿）
- `ISS-157` 以「条款撤销」`closed`；`ISS-110` 部分收口登记
- `spec/README.md` 投影表 `DADAO-12/13/22/23` 行更新（`deferred`→实际落点）
- `make check-no-residue` 干净

## 核验记录（主会话）

（核验命令、输出与退出码；结论）
