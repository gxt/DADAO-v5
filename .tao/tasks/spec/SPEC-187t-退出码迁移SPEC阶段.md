# SPEC-187t: 退出码迁移 SPEC 阶段（Machine-v5 + ADR）

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-184t`（已验证；Machine-v5 D10）；`SPEC-186t`（DADAO-12 §5.2 路由与跨节同步范围定稿）；本任务只做 SPEC，不改 QEMU/gem5/tests
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
