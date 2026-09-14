# SPEC-011m: M1 spec 里程碑

**模块**：spec
**项目里程碑**：M1
**状态**：待开始
**目标**：DADAO-v5 的 M1 规格基线完成——SimRISC 0.5.3 的 ISA 合约/编码表之上，ABI 合约、Object ABI ADR、Test Machine ADR、ELF 合约、合法性规则、QFC 覆盖校验均已创建并 Accepted，规格冻结动作（impact matrix + README 冻结状态）完成，spec 基线冻结
**关联任务**：`SPEC-002t`~`SPEC-010t`

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出的文件是否都存在：`.tao/knowledge/{contract-isa,contract-abi,contract-elf}.md`、`.tao/knowledge/adr-0003-object-abi.md`、`.tao/knowledge/adr-0004-test-machine.md`、`contracts/{opcodes,abi,legality_rules}.yaml`、`docs/impact-matrix.md`
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）
