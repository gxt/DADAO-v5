# M10 回顾（cfx 五步 + 两轴权限 + 时间/中断 + 工具链与测试收口）

> 作者：architect（2026-11-01）｜ 依据：`.tao/knowledge/milestones.md` 任务流水、`INTEG-052m`、`issues-closed.md`、夜跑/L3 报告。

## 1. 达成判据与结果

1. **本期 `t` 册全部 `已验证`**（70 册，含收尾补丁 `INFRA-114t`），核验册 `INTEG-052m` 置 `里程碑`。
2. **夜跑 `make check-night` 4/4 PASS**：`libc-test` / `llvm-ts` / `embench` / `arch cfx` 四行 `rc=0`（报告 `.dadao/tests/night/2026-11-01-08/`）。
3. **L3 全量**戳 `20261031T170934Z` 8 行 `rc=0`；L1 `make check`、L2 `make check-modules` 均 `rc=0`。
4. **open issue 0**：M10 期 17 条关闭项冻结进 `issues-closed.md`；活台账 `0 open / 0 closed`。
5. **收尾门控**`make check-milestone` rc=0（`INFRA-114t` 修 `check-sync-nonmaskable` 的 `PMEM_DMA` 白名单后回绿）。

## 2. 主线（按能力面）

- **CFX 五步**：地址空间/PTBR/PTW（`INTEG-038t`, ADR-0039）→ PTE 页表步进（039, ADR-0040）→ TLB/G/A-D/PTWERR（040, ADR-0041，34 例探针）→ `cfx_pmem` 64 KiB SRAM + SRAM↔PA DMA（042/043, ADR-0042，23/25 例）→ 启动链 power→hmon→smon（046, ADR-0043）。每步自带 ADR + 探针，后一步只在前一步契约上增量。
- **权限**：两轴权限模型（`INTEG-044t`, ADR-0045）+ `cfx_*_cg_reg_deleg` 强制检查（048）+ `cg7` 空间描述只读表（049）+ reserved cfx 清理（045/089）。
- **时间与中断**：`cfx_time` + 单 hart `cfx_hart`（050）→ **统一异步中断仲裁**（051）：pending 归**目标 cfx** 的 `cg5 rc5`、按 cfxha 升序单层投递、mask 只挡投递不丢事件、解除后补投，14 例探针；DMA 侧 SBI 契约（047）单列。
- **工具链**：64 位缺省 + DWARF64（130）、代码模型 default/large（131）、fixup 大端修正（132）、cfx 别名运行时表（135 → 141 format=2 + stride 数组）、PHI GPRB（139）、窄整数 canonical 折叠（138）、i64 常量移位（137）、McCat SIGABRT（140）；基础设施侧代码跨度门控（106）、PIC `libc.a`/`-static-pie`（108）、0.5.3 PROVENANCE（107）、归档门控下移（109）、semihosting 旧口径清理（110）、`check-knowledge-dir` 回 L1（112）、同步不可屏蔽白名单补 `PMEM_DMA`（114）。
- **测试**：框架调研（067）→ inst/arch/unit/tset 四 scope 迁移（071–075）与收口（076）→ llvm-ts 零 known-fail（077–081）→ L3 去 tset smoke + 报告机检（082/083）→ 残留/生成器/期望值收尾（084–089）。测试从「脚本集合」变为「索引 + 门控 + 报告」三件套。
- **规范**：`cmp.u*` 的 -1 改 64 位全 1（173）、六册自洽性与 C1–C11 裁定落实（174/175，发布 0.9.3/0.7.2/0.1.3）、semihosting 判定迁 `0x3FF00–0x3FFFF`（176, ADR-0038）、删 SBI 保留值 `0x3FFFF`（177）、术语与 BootROM 口径（178/179）、`escape` 偏移只允许 0/+4（180）。

## 3. 经验

- **能力面顺序先行**：五步各带 ADR + 探针、后一步只在前一步契约上增量（038→039→040→042/043→046）；「pending 归目标 cfx、仲裁只做选择」的裁定（051）避免了「聚合位图 vs 既有掩码一真源」的双写。
- **门控分层是省时手段**：归档/里程碑类检查移到 `check-milestone`（109）、内容标识类回 L1（112），使 L1 保持「日常可常态绿」；反之白名单缺口（114）会让整链停在半途，须当场补齐而非放宽断言。
- **工具链改动的连带面**：MC/`.td` 改动必须补 `make install-host`（否则门控读旧安装根自洽假绿）；别名表改为运行时数据（135/141）后，数据更新不再要求重建 LLVM。
- **测试迁移的成本在索引与残留**：迁移期的旧链接/旧路径/生成器 OUT 落点（084/087/088）比用例本身更容易造成漂移，收尾须以「逐字节 `--check` + 落点守卫」机检。
- **夜间/全量证据只在收尾跑一次**：夜跑 4/4、L3 8 行 `rc=0` 作为里程碑门槛，日常不为确认空等。

## 4. 遗留（不阻塞 M10）

- `ADR-0046`（CFX 寄存器裁剪与 usage profile）仍 `Proposed`，待逐条确认。
- `SPEC-180t` 关联 ADR 待用户逐条裁定。
- `INFRA-113t`（M10 后清理：退役失效 M1 门控判据、清 ADR-0030/M9 过时 known-fail 基准）`待开始`，留在活任务目录。
- `INTEG-051t` 字段标注「Linux 开发前置独立项；M11 未定义，暂挂 M10，待用户确认」——M11 定义时确认归属（已按 M10 期任务归档）。
- 归档后 `make check-milestone` 的 ① 「无 `m` 册」为预期红，M11 规划立册后回绿。
