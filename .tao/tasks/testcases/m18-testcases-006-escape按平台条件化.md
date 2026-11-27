# m18-testcases-006: `escape_ciii_cfx` 按平台能力条件化（Tiny 跳过 `cg4`/`cg15 rc3`）

**模块**：testcases
**项目里程碑**：M18
**依赖**：`m17-chipyard-002`（根因定位，已验证）、`m18-testcases-004/005`（本用例迁移）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-27 裁定 A）

M17 四方唯一红 `escape_ciii_cfx` 的根因（`m17-chipyard-002`）：Tiny RTL 无 `cfx_hmon` 的 `cg4`（`commonRows` 缺项）与 `cg15 rc3`（被 `asyncModel = gp.hart.isDefined` 门控），测试却无条件：

- `.S:82` `cfx2rc cfx_hmon, cg15, rc3, rd5`（写 async mask）⇒ **CFXREG**（cause `0x4`，pc `0xffffff010160`）；
- `.S:84` / `:125` / `:149` `cfx2rd cfx_hmon, cg4, rc5`（escape_num）⇒ 同样 **CFXREG**（pc `0xffffff010164`）。

首个异常发生在测试武装任何故障例之前 ⇒ `.faultpad` 的 `__pad_fail` 以点号 0 退出（**rc=0 + 空签名**）。

用户裁定 **A**：Tiny 保持 M16 寄存器面不变（`DIV-18` 口径），由**测试载体按平台能力条件化**；Tiny 上这两项不校验、槽位填常量，其余检查照旧真实执行。

## 要做

1. **能力探测**：在用例开头（武装故障例前）用受控方式判断 `cfx_hmon` 是否有 `cg4` / `cg15 rc3`——例如以 hmon handler 捕获 CFXREG 的探针（沿用例既有 `__PREP_ESC` + 落点机制），或等价可靠的探测；**不得**把 CFXREG 当致命错误；
2. **条件化**：
   - 有能力（IDL/QEMU/gem5/Vast）：现有检查**逐条不变**；
   - Tiny：跳过对 `cg4 rc5`、`cg15 rc3` 的直接访问；对应签名槽写入**与其它平台相同的常量**（由 `spec/DADAO-12 §3.5/§5.1/§5.3` 独立派生，不从 QEMU 抄），其余检查（落点、cause、rc8–rc11、帧记录）照旧真实执行；
3. 订正 `.S` 头 GAP 注释（现称「escape_num 不计入链例」与代码矛盾）与 `tests/arch/expected-divergences.yaml` 的 `DIV-18` 文本（补 `cg4`，写明测试载体条件化方式）；
4. 若探测发现 Tiny 连 `escape` 本身都因缺 `cg15 rc3` 而失败（硬件写路径），**停止并回报**（说明 A 不可行、需改判 B），不要硬凑常量。

## 不做

- 不改 RTL/QEMU/gem5/IDL 语义；不改其它用例；不改 expected.tsv 的槽数；
- 不放宽 IDL/QEMU/gem5 三方的真实检查。

## 约束

- 独立 `git worktree`；不提交 git；只动 `tests/inst/11-cfx/escape_ciii_cfx.S`、`tests/arch/expected-divergences.yaml`、必要时 `tests/data/inst-signature/expected.tsv`（不得改槽数）、`components/chipyard/README.md`（如 GAP 说明需同步）+ 本任务书；完成区 ≤30 行。

## 验证

1. `make check-idl-full` **274/274**（chipyard 签名非空、四方逐字节一致）；
2. Tiny 上仍真实执行其余检查：注入（如把 `case3` 落点改错）⇒ 必红；`cp`+md5 还原回绿；
3. 有能力的平台未放宽：注入（如把 QEMU 侧 `cg15 rc3` 值改错）⇒ 必红——用 `run_inst_tiny --platforms qemu,gem5` 的差分或等效证据；
4. 常量**独立派生**证据（spec 段落 + 推导过程），不得抄 QEMU/其它平台输出；
5. `grep -c 'escape_num'` 注释与代码一致；`DIV-18` 文本含 `cg4`；
6. `git status -uall` 仅允许文件 + 任务书。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
