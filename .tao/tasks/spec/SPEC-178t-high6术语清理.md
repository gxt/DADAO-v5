# SPEC-178t: 术语清理：移除 `high6` 简写

**模块**：spec
**项目里程碑**：M10
**依赖**：当前 master
**状态**：待开始

## 背景

`high6` 是讨论中形成的简写，不是正式术语。规范、ADR、contracts、索引和任务书中仍有使用，容易与 `cfxha`、`addr[47:42]` 混淆。用户已授权修改 spec。

## 目标

1. 将所有**活跃文档**中的 `high6` 改为正式表述：
   - `high6 = 0` → `addr[47:42] = 0`；
   - `high6 = 1..63` → `addr[47:42] = 1..63`；
   - `high6 != 0` → `addr[47:42] != 0`；
   - 首次出现可写“地址高 6 位（`addr[47:42]`）”，后文统一用 `addr[47:42]`。
2. 覆盖范围：`spec/**/*.md`、`.tao/adr/**/*.md`、`.tao/contracts/**/*.md`、`.tao/tasks/**/*.md`、`docs/**/*.md`、`contracts/**`、`components/*/changelog.md`、`tests/**/*.md`。
3. **不改**：
   - `.tao/archive/**`、`.work/**`、`.dadao/**`、`.cache/**` 等历史/生成物；
   - 代码、测试脚本中的注释（除非该文件本身是文档）；
   - 任何语义、编号、接口、测试期望。
4. spec 版本/changelog/sha 按 `docs/Process-06` 规则处理；纯术语变更不得改变语义。

## 验收

- 活跃文档 `grep -RIn 'high6'` 命中为 0（排除归档/生成物/代码脚本）。
- `make check` rc=0；`check-spec-readonly`、`check-spec-changelog`、`check-knowledge-refs` rc=0。
- 不改 spec 语义；不动 QEMU/LLVM/测试期望。
- 证据 `.work/evidence/<任务号>/run.sh`：注入一个 `high6` 残留→FAIL→删除→PASS；用 `cp`+md5 还原，禁止 checkout/restore。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 同步；临时目录 `/tmp/opencode/SPEC-178t/`。

## 约束

- 只做术语替换；不讨论/不修改 fence 定义。
- 不提交、不 push；不跑 full/夜跑。
- 每处替换保持原句可读；不能机械替换成 `addr[47:42]=0` 后语义含糊。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
