# m17-testcases-008: `escape_ciii_cfx` 按平台能力条件化（Tiny 验证 CFXREG + DIV 逐槽声明）

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-chipyard-002`（根因，已验证）、`m17-idl-026`（four-way 认 DIV `slots`，已验证）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-27 裁定 1）

根因（`m17-chipyard-002`）：Tiny RTL 无 `cfx_hmon` 的 `cg4`（`commonRows` 缺项）与 `cg15 rc3`（`asyncModel` 门控），用例无条件访问 ⇒ **CFXREG**（pc `0xffffff010160` / `0xffffff010164`），未武装进 `.faultpad` 以点号 0 退出 ⇒ rc=0 + 空签名。

用户裁定：**不造假常量、不跳过**。Tiny 缺这两个寄存器是**被验证的行为**：

- 受控触发访问，断言 `cause_id = 0x4`（CFXREG）、`cause_info = 该指令编码`；
- Tiny 的期望值写进 `tests/arch/expected-divergences.yaml` 的 `DIV-18` **逐槽声明**（`slots`: `case` + 0 基 `slot` + `chipyard`）；`idl_four_way.py` 已支持（`m17-idl-026`）；
- IDL/QEMU/gem5/Vast 路径保持现有真实检查逐条不变。

已实测：Tiny 的 `escape` 指令本身可用（硬件写 `cg15 rc3` 在 Tiny 为空操作、不报错）。

## 要做

1. **能力探测**（用例开头、武装故障例之前）：受控判断 `cfx_hmon` 是否有 `cg4`/`cg15 rc3`（沿既有 hmon handler + `__PREP_ESC` 落点机制），CFXREG 不当致命错误；
2. **有能力平台**（IDL/QEMU/gem5/Vast）：现有检查逐条不变；
3. **Tiny**：对 `cg4 rc5`、`cg15 rc3` 的每处访问，在受控 handler 下真实触发并把实测 `cause_id`（`0x4`）与 `cause_info`（指令字）写入对应签名槽——期望值从 spec 独立派生（CFXREG = `1<<2`；`cause_info` = 编码），不抄其它平台输出；
4. **`DIV-18`**：补 `cg4`；加 `slots` 逐槽声明（`case: escape_ciii_cfx` / 0 基槽号 / `chipyard` 期望值）；`close_when` 与 impact 文本同步（写明「Tiny 期望 CFXREG + 槽值由本条目声明」）；
5. 订正 `.S` 头 GAP 注释（现与代码矛盾）；
6. 其它检查（落点、`cg5` 帧、rc8–rc11、返回值）在 Tiny 仍真实执行。

## 不做

- 不改 RTL/QEMU/gem5/IDL 语义；不改 `idl_four_way.py`（`m17-idl-026` 已做）；
- 不改 `expected.tsv` 槽数；不放宽 IDL/QEMU/gem5 的真实检查；
- 不写常量槽（P0/P1/P2/1 之类）。

## 约束

- 独立 `git worktree`；不提交 git；只动 `tests/inst/11-cfx/escape_ciii_cfx.S`、`tests/arch/expected-divergences.yaml`（`DIV-18`）、必要的生成物（`tests/data/inst-signature/{expected.tsv,inputs.sha256}`，不得改槽数）、`components/chipyard/README.md`（如 GAP 说明需同步）+ 本任务书；完成区 ≤30 行；`**状态**` 改 `待验收`。

## 验证

1. `make check-idl-full` **274/274**（chipyard 签名非空；其余三方逐字节一致；`DIV-18.slots` 生效并输出标注）；
2. **可达 FAIL ①**：把 `DIV-18` 声明值改错 ⇒ 该例必红（`m17-idl-026` 的「值需更新」路径）；还原回绿；
3. **可达 FAIL ②**：Tiny 侧改错探测落点/期望 ⇒ 红；还原回绿；
4. **可达 FAIL ③**：有能力平台（QEMU/gem5）改错 `cg15 rc3` 值 ⇒ 必红（证明未放宽）；还原回绿；
5. Tiny 槽值的 **spec 推导**写明（CFXREG 位号、`cause_info` = 指令字编码）；
6. `make check-idl` 274/274；`check-knowledge-refs` rc=0；`git status -uall` 仅允许文件 + 任务书。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
