# INFRA-123t: DDLN TT 草稿工作流退役

**模块**：infra
**项目里程碑**：M11
**依赖**：无（`docs/DDLN` 规则与草稿清理）
**状态**：待开始

## 执行环境
本地；改 DDLN 规则与索引，删除 gitignored TT 草稿。**不做 TT 备份**（用户明确授权）。

## 用户裁定（2026-11-05，原话）

> 「现在主会话已经固定在master分支上了，lecnote单独一个会话已无意义，是不是完全做一次同步之后，删除TT-*」
> 「可以；无需备份TT」

## 现场（2026-11-05）

`docs/DDLN`：

- `DD-*`：81 册
- `TT-*`：81 册
- 一一对应，无单边文件
- 76 对完全相同
- 5 对不一致，且 **DD 全部更新、TT 落后**：
  - `A002`：DD 11 种格式；TT 12 种（含已撤销 `crii`）
  - `A011`：DD 新 `fence cfxha`；TT 旧 `fm/pred/succ`
  - `C001`：DD 三段作用域（含 per-task）；TT 两段
  - `E003`：DD 11 格式类；TT 写 `crii` 未启用
  - `F003`：DD 含 per-task；TT 仅 per-hart/per-system

这些 DD 更新来自任务代理直接编辑 DD（如 `INTEG-041t` 任务书明确记录“本次直接改了 DD，建议收尾时同步 TT”），TT 未同步。

## 目标

1. **确认 DD 为唯一真源**：不执行 TT→DD 同步（会回退 5 册）；5 处不一致以 DD 为准。
2. 删除全部 `TT-*`（81 份）；**不备份**。
3. 改 DDLN 规则，去掉 TT 草稿工作流：
   - `docs/DDLN/AGENTS.md`：删除“TT 草稿/DD 定稿/TT→DD 同步/DD 不直接改”等规则；改为“DD 是唯一真源，直接编辑 DD；不再有 TT”。
   - `docs/DDLN/.gitignore`：删除 `TT-*` 忽略规则（不再有 TT）；若保留需写明“已退役”。
   - `.tao/knowledge/MEMORY.md`：删除“草稿 TT-* 由 .gitignore 忽略”表述。
   - `docs/DDLN/README.md`/其它活文件若有 TT 说明，同步更新。
4. 更新索引/规则后跑 L1 与 `check-knowledge-refs`；不改任何 DD 技术内容（除规则文件）。

## 接口规范

- 只改 `docs/DDLN/AGENTS.md`、`docs/DDLN/.gitignore`、`docs/DDLN/README.md`（若引用 TT）、`.tao/knowledge/MEMORY.md`、本任务书、`milestones.md`。
- 不改 81 册 `DD-*` 内容；不把 TT 内容复制进 DD。
- 删除 `TT-*` 由 architect 在主工作树执行（TT 是 gitignored，任务 worktree 不可见）；子代理只做审计与规则修改。
- 删除后验证：`find docs/DDLN -name 'TT-*' | wc -l` = 0；`DD-*` = 81。
- 不新增/改写 DDLN 写作规则其它条目。

## 范围 / 非范围

**在范围内**：`docs/DDLN/AGENTS.md`、`docs/DDLN/.gitignore`、`docs/DDLN/README.md`（若引用 TT）、`.tao/knowledge/MEMORY.md`、本任务书、`milestones.md`；主工作树 `docs/DDLN/**/TT-*.md` 删除。

**不在范围内**：81 册 `DD-*` 内容、`spec/**`、ADR、contracts、QEMU/gem5/tests、其它知识库。

## 验收标准

1. **DD/TT 审计**：81 对；5 处差异均为 DD 更新；无 TT-only。
2. **TT 删除**：主工作树 `find docs/DDLN -name 'TT-*'` = 0；`DD-*` 仍 81；无备份（用户授权）。
3. **规则退役**：`docs/DDLN/AGENTS.md` 不再出现“TT 草稿 / TT→DD / DD 不直接改”规则；明确“DD 唯一真源、直接编辑”。
4. **索引/知识库**：`.gitignore` 不再忽略 TT（或注明退役）；`MEMORY.md`/DDLN README 不再把 TT 当草稿。
5. **门控**：`check-knowledge-refs`、`check-milestones-fresh`、`make check`（L1）rc=0。
6. **反例可达 FAIL**：在规则文件写回“TT 草稿”或主树新建一个 TT 测试文件 ⇒ 断言 FAIL；删除/还原后回绿（TT 测试文件在仓库外或临时路径）。
7. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 用户明确“无需备份 TT”，删除不可恢复；执行前必须完成 81 对审计与 5 处 DD 为准的确认。
- 这是工作流退役，不是内容改写；DD 技术内容零改动。
- 若删除后发现某册内容只存在于 TT、DD 缺失，立即停止并报告；本次审计无 TT-only。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
