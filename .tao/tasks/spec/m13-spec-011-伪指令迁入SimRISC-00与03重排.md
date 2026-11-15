# m13-spec-011: 伪指令迁入 `SimRISC-00 §5`；`SimRISC-03` 按 rd/rb/rf 拆三章；`set.ft` 写宽对照

**模块**：spec
**项目里程碑**：M13
**依赖**：`m13-spec-010`（已合 `cb8ca30d`，`rf2rf` 已入 `SimRISC-02`）
**可并行分片**：否（spec 结构重排，牵动全仓引用）
**预估**：3–4 h
**档位**：大改（结构重排 + 锁 + 全仓引用；≥4 路注入 + 独立重算）
**状态**：待开始

## 用户裁定（2026-11-15，原话）

> 「同意A，两个补充也可以。SimRISC-03 中的伪指令应该移动到 SimRISC-00的第5章，SimRISC-03的第一章，按rd/rb/rf分开三章；此外，在tests/inst/00 目录下，新增这7种伪指令的专门的汇编测试」

（本任务只做**spec 侧**两件；`tests/inst` 的载体另立任务。A 的第二条补充「lit 对照用例」在 llvm 面，另立任务。）

## 任务

1. **迁入 `SimRISC-00 §5 伪指令`**：把 `SimRISC-03` 现有的 `## 2. set.rd`、`## 3. set.rb`、`## 4. set.ft / set.fo` **正文整体迁到** `SimRISC-00 §5`（保持内容不变，只搬 + 调整交叉引用），使 §5 从"一行指针"变成**规范正文**；`SimRISC-03` 侧删除这三章并在册首/相关处留指针「伪指令见 `SimRISC-00 §5`」。
2. **`SimRISC-03` 第一章按 rd/rb/rf 拆三章**：现 `## 1. 立即数常数赋值` 拆为 **rd 组 / rb 组 / rf 组** 三章（原顺序保持：rd → rb → rf），后续章节与附录随之顺延编号；**内容不改**（仅拆章、补章首一句导语）。
3. **A 的补充之一（写宽对照表）**：在 `SimRISC-00 §5`（`set.ft` 段）增加一张两行对照表：`set.ft rf, imm32` ⇒ **只写低 32、高 32 不动**；`set.ft rf, rf` ⇒ **整 64 位**（并注明后者是 `m13-spec-010` 删 `ft2ft` 后的语义，属可观察变化）。
4. **全仓引用同步**：`grep -rn "SimRISC-03"`（现 257 处）里凡指向"章号/小节"的引用，按新编号更新；`.tao/contracts/*`、`contracts/*`、`docs/DDLN/*`、`docs/Process-*` 同步；`SimRISC-00 §5` 的旧指针句删改。
5. **锁与门控**：`manifests/spec-readonly.lock.toml` 同笔重算改动册 sha256；changelog 各册补条目（版本号按现有规则）。

## 验收（逐条贴真实 rc/现场值）

1. 结构：`SimRISC-00 §5` 含四类伪指令正文（`set.rd`/`set.rb`/`set.ft`/`set.fo`，含立即数/寄存器两形式与展开示例）；`SimRISC-03` 不再有伪指令章、且第 1–3 章分别是 rd/rb/rf 组；
2. **写宽对照表**在位（`set.ft` imm 窄 / reg 整 64 位）；
3. 全仓引用：`grep -rn "SimRISC-03 §"` 无失效章号（`check-spec-cite-targets`/`check-spec-refs`/`check-rule-refs` rc=0，贴改动前后引用计数）；
4. 门控：`check-spec-readonly`（锁重算）、`check-spec-changelog`、`check-spec-purity`、`check-spec-refs`、`check-spec-cite-targets`、`check-spec-numbering`、`check-rule-refs`、`check-asm-list`、`check-asm-prose`、`check-isa-coverage`、`check-knowledge-refs` 全 rc=0；
5. **≥4 路可达 FAIL 注入**（`cp`+md5 还原）：① 把 `SimRISC-03` 某章号引用改错 ⇒ cite-targets 红；② 删写宽对照表一行 ⇒ 你自设的断言红；③ 锁不重算 ⇒ `check-spec-readonly` 红；④ 伪指令章残留旧编号 ⇒ `check-spec-numbering` 红；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **不改语义**（除写宽对照表这一处用户已裁定的补充）：不动 `rf2rf` 定义/限制、不动其它指令语义；
- 只改 `spec/**`、`.tao/contracts/**`、`contracts/**`、`docs/**`、`manifests/spec-readonly.lock.toml`、本任务书；**不改** `tests/**`、`components/**`、`tools/**`；
- 禁 `install-host`/`check-modules`/`build-*`；不 sync/reset 节点；不提交 git；注入还原 `cp`+md5。

## 待裁定

（实现中写）

## 审阅记录

（待填）
