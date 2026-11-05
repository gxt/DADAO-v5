# SPEC-185t: spec 非 spec 引用清理

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-184t`/`SPEC-186t`/`SPEC-188t`/`SPEC-189t`/`SPEC-190t`/`SPEC-187t`（均已完成；spec 正文已定稿）
**状态**：待开始

## 执行环境
本地；只删 `spec/` 内对非 `spec/` 目录的引用标记，不改任何规范语义。

## 背景

用户裁定（2026-11-05）：

> 「清理 spec 目录下的各文件的交叉引用，尤其是对非 spec 目录的文件的引用，全部清理掉。」
> 边界选 **A**：只删非 spec 引用，保留 spec 内部互引。
> 引用处理选 **A1**：只删引用标记，保留句子；不内联 ADR/契约内容。

现场统计（2026-11-05）：

- `Machine-v5-测试机运行环境.md`：`ADR-*` 65 处
- `Toolchain-01-汇编语言.md`：`ADR-*` 9、`contract-*` 14、`.tao/contracts` 6、`.tao/knowledge` 2、`contracts/` 12、`tools/` 3
- `spec/README.md`：`ADR-*` 3、`contract-*` 30、`.tao/contracts` 3、`docs/` 12、`contracts/` 17、`manifests/` 1、`tests/` 6、`tools/` 12
- 其它 19 册主要只有 spec 内部互引（`SimRISC-*`/`DADAO-*`/`Machine-v5`/`Toolchain-*`）

## 目标

1. 删除 `spec/*.md` 中对 **非 spec 目录** 的引用：
   - `ADR-*`
   - `contract-*` / `contracts/*`
   - `.tao/contracts/*` / `.tao/knowledge/*`
   - `docs/*`
   - `tests/*`
   - `tools/*`
   - `manifests/*`
   - `0628`
   - 外部 URL（`http://`/`https://`）
2. 保留 **spec 内部互引**：`SimRISC-*`、`DADAO-*`、`Machine-v5`、`Toolchain-*`、`spec/*.md`。
3. `spec/README.md` 只保留 spec 册索引：
   - 全部分册清单
   - Tiny/Node 投影
   - 推荐阅读顺序
   - 删除 contracts/tests/tools/manifests/docs 等非 spec 投影行；若某节整体是非 spec 内容，删除该节。
4. 同笔重算 `manifests/spec-readonly.lock.toml` 中所有被改 spec 册的 sha；未改册不变。

## A1 规则（只删标记）

- 优先只删引用 token，例如：
  - `……建立首张页表。[ADR-0043 D10]` → `……建立首张页表。`
  - `见 contract-isa §3` → 删除引用；若整句仅为指针，删除该句（不新增语义）
- 不把 ADR/contract 的规则内联进 spec；不新增数值/编码/异常语义。
- 若删除后句子语法不完整（只剩“见/参见”），允许最小删除“见/参见”短语；逐处记录。
- 不改变任何“应当/必须/不得”的规范强度。

## 范围 / 非范围

**在范围内**：`spec/*.md`（22 册）、`spec/README.md`、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`。

**不在范围内**：`.tao/**`、`contracts/**`、`docs/**`、`components/**`、`tests/**`、`tools/**`、`Makefile`、ADR、门控脚本。

## 验收标准

1. **非 spec 引用清零**：`ADR-`、`contract-`、`.tao/`、`contracts/`、`docs/`、`tests/`、`tools/`、`manifests/`、`0628`、`http(s)://` 在 `spec/*.md` 活正文 0 命中（历史段/变更记录是否保留由现场判定并披露；默认历史段也不得保留非 spec 路径引用）。
2. **spec 互引保留**：`SimRISC-*`/`DADAO-*`/`Machine-v5`/`Toolchain-*`/`spec/` 引用仍在（数量不减少；README 索引仍指向 spec 册）。
3. **语义零改动**：`git diff` 只能删除引用 token / 指针句 / README 非 spec 行；不得新增或改写规范句。脚本对“删除引用后正文”做归一化比对，差异仅为被删 token/空行。
4. **README**：只索引 spec 册；profile/阅读顺序存在；contracts/tests/tools/manifests/docs 投影 0 命中。
5. **锁**：所有被改册 sha 与 `sha256sum` 逐字相等；未改册不变。
6. **门控**：`check-spec-readonly`/`check-spec-refs`/`check-spec-drift`/`check-spec-changelog`/`check-spec-numbering`/`check-spec-purity`/`check-spec-cite-targets`/`check-spec-codeblocks`、`check-milestones-fresh`、`make check`（L1）rc=0。
7. **反例可达 FAIL**：写回一处 `[ADR-xxxx]` 或 `contract-isa §x` ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原后回绿。
8. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是“去引用”，不是“去内容”：句子保留，规则不搬。
- 若某处删除引用后无法判断语义，保留现场并留问，不自行补写。
- 与其它 spec 任务串行改锁；当前 186t/188t/189t/190t/187t 均已合入，可直接执行。
- 原 `SPEC-185t`（spec 自包含 + README 索引迁移）是主会话误拟，已由本任务书取代；本任务不新增册头、不重写索引结构。

## 未决（下发前确认）

1. 历史段/变更记录中的旧 ADR/contract 引用是否也删；默认删（保持“spec 内无非 spec 引用”）。
2. `spec/README.md` 中纯非 spec 的投影表是否整节删除；默认删除。
3. `Toolchain-01` 中若引用是句子主干（如“见 contract-isa 的编码表”），是否允许最小删除“见…表”短语；默认允许并逐处记录。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
