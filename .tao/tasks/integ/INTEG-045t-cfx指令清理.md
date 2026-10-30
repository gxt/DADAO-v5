# INTEG-045t: cfx 指令清理（reserved 规则/删除 cfxld-cfxst/fence 宏）

**模块**：integ
**项目里程碑**：M10
**依赖**：INTEG-041t（fence ciii）、INTEG-044t（权限）
**状态**：待开始

## 背景

1. `encode_cfx_reserved` 目前只挂 `fence`，应覆盖所有带 `cfxha` 的核芯功能扩展指令；根因是 `contracts/legality_rules.yaml` 的 spec_cite/description 和 `opcodes.yaml` 的 rule_refs 只挂 fence，生成器按 rule_refs 输出。
2. 用户决定删除 `cfxld/cfxst`；SimRISC-11 仍有一整节/汇编表/decode ILLI，SimRISC-00 编码表仍有 `crii` 和两格。
3. SimRISC-11 缺 fence 12 个宏名表；`7–14` reserved 也应统一为 `6–14`。

## 目标

1. **reserved 规则**
   - `legality_rules.yaml`：`encode_cfx_reserved` 描述改为“所有带 cfxha 的核芯功能扩展指令”；spec_cite 改 SimRISC-11；
   - `opcodes.yaml`：`trap/escape/cfx2rd/cfx2rc/fence` 都挂 `encode_cfx_reserved`；
   - 生成器/附录重新生成；补测试覆盖各 cfx 指令的 reserved→ILLI。
2. **删除 cfxld/cfxst**
   - SimRISC-11：删除该节、汇编速查行、`crii`、decode ILLI；更新分类/说明；
   - SimRISC-00：删除 `crii` 格式定义、编码表两格、历史引用；
   - `contracts/opcodes.yaml`：删除 `cfxld_crii_cfx`/`cfxst_crii_cfx`；
   - LLVM MC/汇编器/别名/矩阵/统计/测试同步；不再保留 `crii`。
3. **fence 宏表**
   - SimRISC-11 增 12 个宏：`PRED_CR/CW/CI/CO/MR/MW`、`SUCC_CR/CW/CI/CO/MR/MW`；
   - 值与 LLVM AsmParser 一致（1<<6..1<<11 / 1<<0..1<<5）；
   - `|` 组合，整体作为 immu18；`hb`/保留位 SBZ。
4. **版本/锁/索引/合同** 同步；不改 fence 编码语义。

## 验收

- `make check`、`check-modules`、`check-arch-smoke`、`check-arch`、`check-lit`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state`、`check-isa-coverage` 全 rc=0。
- 证据 `.work/evidence/<任务号>/run.sh` 注入→FAIL→cp+md5 还原→PASS。
- 不删除 QEMU-047t 已删探针之外的内容；不改权限模型/启动链。
- 完成区 ≤30 行；任务书/里程碑 `待验收`；临时 `/tmp/opencode/INTEG-045t/`。

## 约束

- 只做本任务；不提交、不 push；不跑 full/夜跑；重建先申报。
- `encode_cfx_reserved` 必须由源规则/生成器修，不能手改生成附录。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
