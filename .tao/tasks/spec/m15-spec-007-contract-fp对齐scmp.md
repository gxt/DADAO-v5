# m15-spec-007: `contract-fp.md` 与 spec 对齐（scmp 无序结果）

**模块**：spec
**项目里程碑**：M15
**依赖**：`a6f11e23`（spec 已改：signaling compare 无序结果 = canonical quiet NaN，版本号不变）
**可并行分片**：否（单文件）
**预估**：0.5–1 h
**档位**：小改
**状态**：待验收

## 背景

`m15-qemu-001` 执行时发现：`.tao/contracts/contract-fp.md` **第 26/88 行仍写「Signaling Compare 返回 sNaN」**，与 `a6f11e23` 之后的 `spec/SimRISC-07 §4` 冲突，且**没有任何门控覆盖这一条**。

## 要做

1. 改 `.tao/contracts/contract-fp.md` 第 26/88 行：signaling compare 的无序结果 → **canonical quiet NaN**（与 `spec/SimRISC-07 §4` 逐字一致），并补一句「quiet 与 signaling 的差别只在 `NV`」；
2. 若该文件有版本号/变更记录，按 `docs/Process-02` 处理——**但版本号升级须用户认可**：只加内容条目、版本号保持，等用户裁定；
3. 全文件搜 `sNaN`：凡「无序结果」语境的一律改；「sNaN 作输入置 NV」的语境**保留**。

## 验收

1. `grep -n "sNaN" .tao/contracts/contract-fp.md` 逐条给出处置（改/留 + 理由）；
2. `check-contract-relocs`、`check-spec-refs`、`check-knowledge-refs` rc=0；
3. 与 spec 的对应句**逐字比对**（给 diff）。

## 完成区

**测试结果**：证据脚本（运行期证据目录内的 `run.sh`）rc=0 —— 主检查 8 项全绿，5 路反例注入（行 88 回退 sNaN / 行 26「不适用」回填 / 行 88 删逐字句 / 版本升号 / 伪造 spec 引节）均「注入⇒判红⇒cp+md5 还原⇒回绿」。`make check-contract-relocs` rc=0、`make check-spec-refs` rc=0（1332 引用、失败 0）、`make check-knowledge-refs` rc=0（具体 `.work/**` 0、悬空 0）；附带 `check-fp-contract`/`check-contracts-pending`/`check-dirs` 均 rc=0。

**修改文件**：`.tao/contracts/contract-fp.md`（仅 2 行：§1 第 26 行、§8 第 88 行；标题/版本头 `0.5.6` 未动，该文件无变更记录小节 ⇒ 无条目可加）。

**验收结果**：
1. `grep -n "sNaN"` 共 11 行逐条处置：**改 1 行** = 88（「Signaling Compare 返回 sNaN」→「四种比较一律返回 canonical quiet NaN」+ NV 差别句）；**改+留同行** = 26（改：删「比较的 quiet 无序结果」限定、删「不适用」里的 signaling compare 项、补 NV 差别句；留：「sNaN 作输入仍按各节规则置 NV」）；**留 9 行**，均为「sNaN 作输入/无序源操作数置 NV」或位型语境 —— 38（fo2ft 算术输入置 NV）、89（signaling compare 任一操作数为 sNaN 或 qNaN 即置 NV）、90（quiet compare 仅含 sNaN 置 NV）、91（qNaN/sNaN 按整型解读为正数；spec §4 同位型句未改）、168（roundint sNaN 作输入）、183/184/185（minmax 单 NaN 同论 / 双 NaN 组合 / sNaN 作输入置 NV）、197（fma sNaN⇒置 NV、返回 qNaN）。
2. 三个门控 rc=0（输出见上）。
3. 与 spec `§4` 逐字比对：spec 句 =「**四种比较一律返回 canonical quiet NaN**（符号位 0、payload 全零，见 §异常与标志）；quiet 与 signaling 的差别只体现在 `NV` 标志（signaling 无序即置 `NV`，quiet 仅 sNaN 置 `NV`）」；contract 同行同上，**唯一 diff = 句末句号**（contract 体例统一「。」结句后接引用标记，`grep -c '。\['`=123/123）；去句末句号后逐字相等 = True。两处 diff 均为 `-...+...` 单行，改动仅 2 insertions/2 deletions。

**新发现/坑**：① **门控缺口**：`check-fp-contract` 只校验投影完备性（id/族/spec_cite/legality），不校验 compare 无序结果的 NaN 取值 ⇒ 本次修正是靠证据脚本 C1 的「spec 句逐字在场」断言兜住，仍建议后续加机械门控。② 证据脚本首版 C4 白名单用字面量子串，漏「作为算术输入」「**sNaN** 同论」两种加粗/长词形态 ⇒ 误报 2 处，改正则后 11 行全部归类通过（计数现场统计，未写死行号）。③ 注入期间被检检查的判红会污染总失败数 ⇒ 引入 `QUIET` 标志只在反例窗口内不计。

**遗留问题**：机械门控缺口（见「新发现/坑」①）未在本任务内补 —— 任务书「要做」只列 contract-fp.md，未列 `tools/spec/`，按最小修改未越界；建议另立小任务给 `check-fp-contract` 增一条「contract §8 含 spec §4 逐字句」断言（可复用本脚本 C1 的提取逻辑）。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 `.tao/contracts/contract-fp.md` 两处改动与证据脚本：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| §8「见 §异常与标志」在 contract 内无同名小节，可能歧义 | ❌不修 | — | 该措辞为 spec §4 原句逐字（验收要求），行尾 `[SimRISC-07 §异常与标志]` 已指明册/节；改写成 contract 内小节约破坏逐字一致 |
| §1 新增 NV 差别句与 §8 NV 两条重复 | ❌不修 | — | §1 是全局口径（供 oracle 单点消费），§8 是 compare 族细则；spec 同样在「全册适用」与 §4 各写一次 |
| 行 91 仍提 sNaN，会否误导「结果可为 sNaN」 | ❌不修 | — | 该句讲 NaN **位型**按整型为正数（spec §4 同句未改），非结果取值；行 88 已明定四种比较结果一律 canonical qNaN |
| 版本号未升是否漏处理 | ✅已修 | 无正文改动，核对确认 | `grep '版本：0.5.6'` 命中、标题 `0.5.6` 命中；证据脚本 C5 断言 |
| 证据脚本每条断言是否有可达 FAIL 路径 | ✅已修 | 5 路注入（含 md5「空注入」防护） | 注入输出逐条 `注入后判红 rc=1` + `还原后回绿 rc=0` + md5 对账一致 |
| 是否有越界改动 | ✅已修 | 无 | `git status -uall` 仅 `M .tao/contracts/contract-fp.md`；`git diff --stat` = 2 insertions/2 deletions |
