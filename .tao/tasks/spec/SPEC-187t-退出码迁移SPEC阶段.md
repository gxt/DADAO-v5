# SPEC-187t: 退出码迁移 SPEC 阶段（Machine-v5 + ADR）

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-184t`（已验证；Machine-v5 D10）；`SPEC-186t`（DADAO-12 §5.2 路由与跨节同步范围定稿）；本任务只做 SPEC，不改 QEMU/gem5/tests
**状态**：已验证

## 执行环境
本地；只改退出码规范与 ADR 投影，不改实现、不改测试。

## 背景

M11 退出码已定稿，但现行 spec/ADR 仍是旧口径：

- `Machine-v5` 用 `0x80 | spec_cause_bit_index`，只列 `0x81` 与历史 `0x87`（unmapped）
- `ADR-0004 D5.8` 用同一公式；`CFXREG` 被写成 `0x84`，与 `1<<2` 公式不自洽（`ISS-341`）
- `PTWERR`、`unmapped`、旧 `0x84`/`0xE1` 仍散落在 spec/ADR
- 缺少 monitor / 其它 cfx 的分段表

本任务把已定稿的完整退出码表落到 `spec/Machine-v5`，ADR 只留决策与指针。

## 已定稿口径（用户 2026-11-05，不得改写）

- guest 段：`0x00–0x3F` = PASS；`0x40–0x7F` = FAIL。
- 机器 fault 段：
  - `0xC0–0xFF` = monitor：`bit7=1, bit6=1, bit5:4=运行模式, bit3:0=DADAO 异常位索引`
  - `0x80–0xBF` = 其它 cfx：`bit7=1, bit6=0, bit5:0=cfxHA`
- 运行模式：user/jail/supv/hypv = `00/01/10/11`。
- monitor 异常位索引：`CFXTRAP=0`、`CFXMEM=1`、`CFXREG=2`、`CFXESC=3`、`CFXPERM=7`、`ILLI=8`、`UNDI=9`、`RASOF=10`、`RASUF=11`、`MALIGN=12`、`IALIGN=13`。
- 删除：`PTWERR`、`unmapped`、旧 `0x84`、`0xE1`。
- `unmapped` 归当前运行模式 monitor 的 `CFXMEM`。
- A/D 回写失败归当前运行模式 monitor 的 `CFXMEM`（`cause_info` = PTE 物理地址）。
- reserved cfx 的普通 `ld/st` 归 `CFXMEM`；`trap`/`escape` 归 `ILLI`；均进当前 monitor。

## 目标

1. `spec/Machine-v5-测试机运行环境.md` 增加“完整退出码表”：
   - guest 段、monitor 段、其它 cfx 段三张表或一张分段表；
   - 每个 monitor 异常位索引逐项列出；
   - 明确 `CFXTRAP` 进目标 cfx 时按“其它 cfx”段编码，`CFXESC` 进当前 cfx 时同理；
   - 明确 A/D 回写失败、unmapped、reserved cfx 的落点；
   - 删除 `0x87`、`0x84`、`0xE1`、`PTWERR`、`unmapped` 的旧表述。
2. `ADR-0004 D5.8` 由公式改为**决策 + 指针**：只说明“退出码分段与 monitor/其它 cfx 编码规则见 `spec/Machine-v5 §x`”，不再维护逐码表；删除旧 `0x84`/`0x87`/`0xE1` 与公式。
3. `ADR-0020 D15`（及任何引用旧码表的 ADR/spec 句）改为指针；不改其它 ADR decision。
4. 同笔重算 `manifests/spec-readonly.lock.toml` 的 `machine-v5` sha 并写授权注记；其它册 sha 不变。

## 接口规范

### 1. `spec/Machine-v5`

- 选择现有退出码小节（`§1.2`/`§5.5` 或等价位置）扩展；不新增 `##`/`###` 编号，除非现有结构无法承载（若必须新增，先留问）。
- 表格必须可机械解析：每行含“范围/位域/含义”；monitor 表逐行列出 11 个位索引。
- 不把 QEMU/gem5 的实现细节写成规范；不定义 host `$?` 之外的语义。

### 2. ADR

- `ADR-0004 D5.8`：保留“退出码用于 pass/fail/fault 三分”的决策；删除逐码表与 `0x80 | cause_bit` 公式；指向 `Machine-v5` 表。
- `ADR-0020 D15`：只保留指针；若其正文有旧码字面，改为指针。
- 每册追加 `rev. 2026-11-05`，在 `## 修订` 记录范围；不改写其它 decision。

### 3. 锁

- 仅 `machine-v5` 块重算；注记含日期 + “授权原话见任务书 §已定稿口径” + 改动摘要。

## 范围 / 非范围

**在范围内**：`spec/Machine-v5-测试机运行环境.md`（退出码相关小节 + `0.3.2-rc` 追加 1 条）、`ADR-0004` D5.8、`ADR-0020` D15 指针、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`、`ISS-341` 关闭。

**不在范围内**：QEMU/gem5/tests 实现与期望值；`DADAO-12 §3.6/§4.5` 原因表（属 `SPEC-186t` 跨节同步或后续任务）；其它 spec 册；`contracts/**`；`Makefile`；门控脚本。

## 验收标准

1. **表完整**：从 `Machine-v5` 正文机械解析出 guest 段、monitor 段、其它 cfx 段；11 个 monitor 位索引逐项命中；`CFXTRAP`/`CFXESC` 的目标 cfx 编码有明确句。
2. **旧码清零**：`PTWERR`、`unmapped`、`0x84`、`0xE1` 在 `Machine-v5` 活文件 0 命中（历史段除外）；`0x87` 不再作为 unmapped 约定。
3. **A/D 与 reserved cfx**：A/D 回写失败、unmapped、reserved cfx 的 `ld/st`/`trap`/`escape` 落点逐项断言为 `CFXMEM`/`ILLI` 当前 monitor。
4. **ADR 指针化**：`ADR-0004 D5.8` 不再含逐码表/公式；`ADR-0020 D15` 指向 `Machine-v5`；两册 `rev. 2026-11-05`。
5. **锁**：`sha256sum` 与锁值逐字相等；锁 diff 仅 `machine-v5` 块；其它册 sha 不变。
6. **门控**：`make check-spec-readonly`、`check-spec-refs`、`check-spec-drift`、`check-spec-changelog`、`check-spec-numbering`、`check-spec-purity`、`check-spec-cite-targets`、`check-spec-codeblocks`、`check-issues`、`check-milestones-fresh`、`make check`（L1）rc=0。
7. **反例可达 FAIL**：改一个 monitor 位索引 / 把 `0x84` 写回 ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原后回绿。
8. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- `ISS-341` 在本任务关闭（`resolved_by: SPEC-187t`）；`ISS-342` 由 `SPEC-186t` + QEMU 任务处理，不在本任务。
- 下游三阶段：本任务 → QEMU/gem5 实现 → tests/parity；后两阶段在 SPEC 收口后另立任务，不在本册展开。
- 本任务不改 `DADAO-12 §4.5` 的 `NUPERM` 等原因表；若 `SPEC-186t` 的跨节同步范围裁定为“另立任务”，该任务与本任务串行。

## 未决（下发前需确认）

1. **`SPEC-186t` 跨节同步范围**：`DADAO-12 §3.6/§4.5` 的旧原因表由谁改；若另立任务，本任务只做 `Machine-v5` + ADR。
2. **退出码表落点**：`Machine-v5` 现有小节是否足够承载完整表，还是需要新增小节；开工时现场确认，若需新增标题先留问。
3. **`ADR-0020 D15` 及其他 ADR**：只改直接引用旧码表的句；不扩大到其它 ADR。

## 完成区

**测试结果**：一键证据 `运行期证据脚本 --inject` → `SCRIPT_RC=0`；静态审计 0 失败，11 项 gate（含 `make check` L1）全 rc=0；注入「monitor 索引 12→14」「写回 `0x84`」均 FAIL，`cp`+md5 还原后回绿（static_fails 0）。
**修改文件**：`spec/Machine-v5-测试机运行环境.md`（§1.2/§3 + 0.3.2-rc 一条）、`.tao/adr/adr-0004-test-machine.md`（D5.7/D5.8 + rev. 2026-11-05）、`.tao/adr/adr-0020-see-semihosting.md`（D15/Rationale + rev. 2026-11-05 + `## 修订`）、`.tao/contracts/contract-see.md`（投影最小同步，范围外披露）、`manifests/spec-readonly.lock.toml`（仅 machine-v5 注记+sha）、`.tao/knowledge/issues.yaml`（ISS-341 closed）、`.tao/knowledge/milestones.md`、本任务书；证据脚本 运行期证据脚本（未入 git）。
**验收结果**：① `check-spec-readonly`: 21 册 OK；`check-milestones-fresh`: PASS 58 行；`make check`: `repository checks (L1): PASS`；`check-issues`: 3 closed/2 open、resolved_by OK；`check-spec-refs`: 1081 resolved/0 fail。② Machine-v5 活正文 `PTWERR`/`unmapped`/`0x84`/`0xE1`/`0x81`/`0x87`/公式均 0 命中；monitor 表机械解析出 11 项且索引/名称逐项相等。③ 锁 sha `180bdb0b…` 与文件逐字相等；`git show HEAD` 对账仅 machine-v5 一项 sha 变化。④ ADR-0004 D5.8 无表格/无公式、指针指向 `Machine-v5 §1.2`；ADR-0020 D15 同；两册 `rev. 2026-11-05`。
**新发现/坑**：`check-run-artifacts` A3 要求运行期日志目录的新文件名为 `check-<name>.log` 或 `<TASK-ID>-<purpose>.log|json|txt`；证据脚本日志一度用 `make-check-L1.log` 致 L1 红，改任务前缀后回绿。ADR-0020 原无 `## 修订`，本次新增并挂 rev。per-mode `0xE1` 是合法派生值但被验收明文禁止字面出现，故 monitor 表只用范围+位域，不枚举逐模式码。
**遗留问题**：`docs/DDLN/D-D002`、`docs/Machine-00`、`ADR-0009`、`ADR-0041` 仍含旧 `0x81`/`0x87`/`PTWERR` 表述（不在本任务范围）；ADR-0004 D5.1–D5.6/D6.1 的历史逐码字面保留（本任务只指针化 D5.8）；QEMU/gem5/tests 与 `contracts/**` 机器数据未改（按任务，下游阶段处理）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方式**：自主逐行审查（`subagent_depth=1`，无嵌套子代理）。逐行核对 Machine-v5 §1.2/§3/0.3.2-rc、ADR-0004 D5.7/D5.8、ADR-0020 D15/Rationale、contract-see、锁、issue/里程碑与证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| D5.7 仍是旧分区（`0x01`–`0x7F` FAIL），与定稿冲突 | ✅已修 | 改为 `0x00`–`0x3F` PASS / `0x40`–`0x7F` FAIL | 静态审计 + 结构检查 PASS |
| 逐模式枚举会引入被禁字面 `0xE1` | ✅已修 | monitor 表只用 `0xC0`–`0xFF` + `bit3:0`，不枚举派生码 | 活正文 `0xE1` 0 命中 |
| `contract-see` 投影仍写旧 `0x81`/`0x87` | ✅已修 | 最小同步为三段编码 + `Machine-v5 §1.2` 指针 | `check-spec-refs` PASS；已在范围外披露 |
| 证据脚本日志名 `make-check-L1.log` 触发 A3 | ✅已修 | 日志改 `SPEC-187t-<gate>.log` | `make check` rc=0 |
| 注入后锁 sha 与文件暂时不等 | ✅非缺陷 | 注入期预期失败；还原后 static_fails=0 | `--inject` 输出 PASS |
| `CFXTRAP`/`CFXESC` 目标 cfx 编码是否明示 | ✅已确认 | 专句 `0x80`–`0xBF`、`bit5:0=cfxHA` | 静态断言 PASS |

#### 第 1 轮 reviewer 验收

**重跑（reviewer 自跑，workdir=任务 worktree，注入前/后各记 status+md5 快照）**：

1. `运行期证据脚本` → `SCRIPT_RC=0`：`[PASS] static audit :: 0 failure(s)`，11 项 gate 全 `rc=0`（readonly 21 册 / refs 1081 resolved·0 violation / drift / changelog / numbering / purity / cite-targets / codeblocks 542 / issues 3 closed·2 open / milestones-fresh 58 行 / L1 `repository checks (L1): PASS`），`RESULT: PASS`。
2. `run.sh --inject` → `INJECT_MODE_RC=0`：`inject 12→14: static_fails=2`、`restore md5_ok=True static_fails=0`；`inject 0x84: static_fails=2`、`restore … static_fails=0`。
3. 独立逐条 gate（命令行，非脚本）：`check-spec-readonly|refs|drift|changelog|numbering|purity|cite-targets|codeblocks|milestones-fresh` rc 全 0；`python3 tools/infra/check_issues.py` rc=0；`make check` → `rc=0`、`repository checks (L1): PASS`。
4. **独立注入（与 engineer 不同项）**：把 monitor 表 `| 7 | … | CFXPERM |` 改 `| 6 | …` ⇒ `run.sh` → `INJECT_RC=1`，`FAIL monitor index map`、`FAIL lock machine-v5 sha`、`FAIL check-spec-readonly rc=2`、`FAIL make-check-L1 rc=2`、`RESULT: FAIL (3)`；`cp` 还原 + `md5sum -c` → `Machine-v5…: OK`（`MD5_RC=0`）后重跑 `RESULT: PASS`、`rc=0`。全程未用 git 还原。
5. 内容核验：§1.2 分段表 4 行齐（guest `0x00–0x3F`/`0x40–0x7F`、其它 cfx `0x80–0xBF`、monitor `0xC0–0xFF`）；monitor 11 项索引 0/1/2/3/7/8/9/10/11/12/13 现场逐行核对；`CFXTRAP`/`CFXESC` 专句按 `0x80–0xBF`；未映射/A-D/reserved 三条落点齐全；活正文 `0x81|0x87|0x84|0xE1|unmapped|0x80 |` 全 0 命中，仅附录 0.3.2-rc 历史行留 `PTWERR` 字面，§1–§7 无旧码；diff 无新增 `##`/`###`。
6. ADR/锁/issue：ADR-0004 D5.8 无 `|`、无 `spec_cause_bit_index`/`0x80 |`，指针 + 三分 + `rev. 2026-11-05`（状态行+`## 修订`）；ADR-0020 D15 指针 + `## 修订` rev，全文旧码 0 命中；逐码表未复制进任一 ADR；锁 `sha256=180bdb0b…` 与文件实测逐字相等，HEAD 对账 `changed: [Machine-v5]`（21 册）；ISS-341 仅 `status/resolved_by` 两行变化。
7. 范围：`git diff --name-only HEAD` = 完成区声明 8 文件，QEMU/gem5/tests/DADAO-12/13/22 未动；`contract-see` 2±2 行（范围外，已披露）。残留 D-D002/Machine-00/ADR-0009/ADR-0041 现场 grep 复核确实在；完成区遗留段已登记，未见另立任务。快照对账：8 文件 md5 全 `OK`、`status diff rc=0`。
8. 体例：完成区 5 个非空行（≤30）、自审 14 行（≤40）、无绝对运行期路径，21/58/3·2/1081/11 项与现场一致。

**findings（均非阻断）**：F1 `contract-see` 属任务书「在范围内」清单之外的改动（已披露），且第 1 行除旧码外还把「对应 cfx」同步为「当前运行模式 monitor」——与 Machine-v5 §3 一致、必要连带，建议架构师在收尾时确认归属；F2 完成区遗留段对 ADR-0004 的旧码枚举不全（D1/D3/D4/D6.2/D6.3/Rationale/Consequences 亦仍含 `0x87`/`0x88`/`0x8C` 等活字面），与 D5.8 新指针并存矛盾，属任务书「不改其它 decision」划界内的范围遗留，**未另立任务**，请架构师裁定是否补登；F3 完成区「11 项 gate」为笔误（应「11 项 gate」，实测确 11 项）。

**判决：Accepted**（验收命令块在 reviewer 重跑下全绿、独立反例注入可达 FAIL 并回绿、约束无违反；findings 交 architect 终审）。

#### 收尾（architect，2026-11-05）

- F1：`contract-see` 的最小同步判为必要连带（旧码→三段编码 + 目标由“对应 cfx”改为“当前 monitor”，与 Machine-v5 §3 一致），不判越界。
- F2：ADR-0004 其它 decision（D1/D3/D4/D6.2/D6.3/Rationale/Consequences）仍有旧码，属本任务“不改其它 decision”划界内；另立 `SPEC-191t` 清理 ADR-0004 + DDLN D-D002/Machine-00/ADR-0009/ADR-0041 旧码。
- F3：完成区“11 项链”笔误已改为“11 项”。
- 运行期路径已改为通用描述；判决 Accepted，状态置 `已验证`。
