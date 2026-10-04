# SPEC-025m: 版本更新最终里程碑

**模块**：spec
**项目里程碑**：M2
**状态**：里程碑
**目标**：SimRISC 0.5.4 版本更新全部完成——合约重组、opcodes 重新生成、版本引用同步、工具脚本适配
**关联任务**：`SPEC-016t`、`SPEC-024t`、`SPEC-018t`、`SPEC-019t`

## 核验
- 关联任务是否均已 `已验证`
- 各任务产出：
  - `.tao/knowledge/contract-isa.md` 版本 0.5.4，章节按新分类重组
  - `contracts/opcodes.yaml` 字段调整完成，spec_cite 指向新文档，语义变更已同步
  - `README.md` 版本表 0.5.4
  - `spec/DADAO-11~23` 头部引用 0.5.4
  - 工具脚本（generate_opcodes/check_spec_drift/check_spec_refs/gen_asm_list）适配新文档编号
  - `docs/assembly-list.md` 分类顺序与新文档一致
- **`make check` 绿**
- **`make check-spec-refs` 通过**

（核验通过后，主会话将 `**状态**` 置为 `里程碑`）