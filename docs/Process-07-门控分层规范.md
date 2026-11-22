# 门控分层规范（L1 / L2 / L3）

> **状态**：生效（2026-10-13）｜**上位依据**：无——属**工程过程规范**（可逆、单项目、无外部契约，不命中 ADR 判据，见 `docs/Process-03`）。
> **缘起**：用户 2026-10-09 提出「门控按规模分三层」（原设计稿 `.tao/knowledge/gate-tiering-design.md`，已并入 `.tao/archive/M7/m7-retrospective.md` 附录 A），用户 2026-10-12 裁定「此事**应有一个工程规范文档专门说明，放到 `docs` 下面**」⇒ 立本规范。
> **关键词**：本规范用「**必须**（MUST）／**应当**（SHOULD）／**可以**（MAY）」表达规范性等级。§1–§5 均标 **MUST**。
> **分工**：`AGENTS.md` 只留**规则 + 指针**（「门控分层与触发点」，≤2 行）；**明细与演进规则**（分层组成 / 归属判据 / 层间不重复 / 可达 FAIL）由本规范承载，**不重复**。

---

## 1. 分层定义与各层组成（MUST）

按**规模/耗时**自上而下分三层；每层 = **一组 `make` 目标**（层间**不重复**列出同一目标，见 §4）。

| 层 | 目标（真源：`Makefile`） | 各层组成 | 目标耗时 |
|---|---|---|---|
| **L1 完整性 / 可用性** | `make check`（**默认**） | **仓库完整性静态检查**（不跑被测语义：patch-tree / spec-drift / 索引卫生 / 编码·合法性·scope·fp 一致性 / ISA 覆盖矩阵漂移 / 引用审计 / 目录·残留·只读 / 测试报告目录卫生（`check-test-reports`） / **组件 changelog 形态**（`check-component-changelog`：列表式 + 按里程碑分节）等）**+ 组件可用性冒烟**（`llc` / `clang --print-targets` / `qemu-system-dadao` 可执行且认识 `dadao`；**不跑被测语义**）**+ issue 台账校验 / `compileall tools`** | 秒 ~ 几十秒 |
| **L2 四 scope smoke** | `make check-modules` | 四个固定 scope 的 **smoke** 集（`Process-09 §8`）：`check-inst-asm`（`.S` 载体全量，单平台 QEMU）+ `check-inst-sig`（签名区逐槽比对，同一批 `.S`、单平台 QEMU）+ `check-arch-smoke` + `check-unit` + `check-tset-{libc,llvm,embench}-smoke`。**不含** FP 探针（2026-10-27 用户裁定「L2 只保留四 scope smoke」）。**inst 的 YAML 代表集门控（`check-inst-smoke`）已删**（`m13-testcases-043`：YAML 全退役；`.S` 全量执行已覆盖同一语料） | 几十 ~ 几百秒 |
| **L3 全量** | `make check-full` | **arch/unit 全量 + 集成链**：`check-arch`（全 cfx）+ `check-unit-full`（= `check-unit` + `check-lit-full`，见下）+ `test-m6`（全量 lit 生成档 + ir-lli + Embench E2E）。**FP 探针已全部退役**：`rnd`/`minmax`/`fma` 由 `m13-testcases-044`、`clmul` 由 `m15-testcases-008`；FP 语义由 `tests/inst/07-floating-point/` 的 `.S` 载体（L2 `check-inst-asm`）+ `tests/unit/llvm/lit` + `e2e/lit` 承担（L3 = `check-arch` + `check-unit-full` + `test-m6` 三成员）。**inst 不在 L3 列**：`.S` 载体的执行门控是 L2 `check-inst-asm`（§4「一个检查只在一层」）；原 L3 `check-inst`（Vast 全量 + Tiny 子集）随 YAML 退役删除（`m13-testcases-043`，用户 2026-11-14 裁定「Vast 明确放弃 ISA 级执行覆盖」）。**tset 不直接列出**：smoke 只在 L2、full 只在回归运行；`test-m6` 的 Embench E2E 属集成步骤，**不算** tset smoke 重复（§4；`TESTCASES-082t`）。运行由 `tools/testcases/l3_run.py` 逐成员执行（成员清单真源 = `l3_run.DEFAULT_MEMBERS`），并写只读报告 `<test-artifacts>/l3/<YYYYMMDDTHHMMSSZ>/`（`manifest.tsv`/`meta.json`/`run.log`，与回归运行同格式）| 几百 ~ 几千秒 |
| **回归运行（非三层之一）** | `make night-run` | `tset` full ×3（各 static+dynamic）+ 长 `check-arch`；结果只落只读报告 `.dadao/tests/night/<date>/`，按需消费（`check-night-report`，**观测口径，不阻断收口**）；**独立锁 `night.lock`**（不占 `gate.lock`，不阻断 L1/L2/L3，`NIGHT_LOCK`）；触发点 = 队列空档，`setsid nohup`（`Process-09 §8`） | 小时级 |
| **按需（模块完整）** | 各 `test-*`/`check-*` **单独调** | 模块**全量**、profiling | 不定 |

- **L1 判据**：**只看"仓库是否完整 + 组件是否可用"**，**不得**依赖被测语义的执行结果（那是 L2/L3）。
- **默认 `make check` = 仅 L1**：`check-inst`（全量语义，原 `check-qemu-semantics`；已随
  YAML 退役删除，`m13-testcases-043`）与
  `check-lit`（受控子集）**移出** L1（`INFRA-058t`）。
- **回到 L1 的两条（`TESTCASES-076t`）**：`check-interface`（跨模块静态一致性）与
  `check-code-range`（合成 fixture 自检）**不跑被测语义** ⇒ 按 §3 判据 1 归 L1。
- **层边界（耗时带）的实测校验**（承接原设计稿 `.tao/archive/M7/m7-retrospective.md` 附录 A §五「第 0 步」待办）：第 0 步：**逐门控计时**（`make -n` 不适用；逐目标 `time`），据实测确定 L1/L2/L3 边界与是否值得拆。

### 1.1 门控登记：契约口径与里程碑收尾（2026-10-17）

| 目标 | 层 | 判据（机械） |
|---|---|---|
| `make check-contracts-pending` | **L1** | `.tao/contracts/**` 出现「待…定 / 待裁定 / TODO / TBD」标记的行，须同行含 `ADR-<n>` / `ISS-<n>` 指针（只认带编号落点）；行内代码跨度与「」引用不计。计数现场统计。 |
| `make check-contract-relocs` | **L1** | `contract-elf.md §2.2` 与 `contract-dynlink.md §4.3` 的**现行表**逐行比对（类型号 ↔ 名）；只解析两小节内的表格行 ⇒ 历史注记不参与；附加自洽 = 表非空 / 号名唯一 / 号 0 起密集。 |
| `make check-milestones-fresh` | **L1** | **双台账**（`m12-infra-001`，用户 2026-11-08「从 M12 开始……milestones.md 也改为 milestones-m12.md」）：`milestones.md` = M11 及以前、`milestones-m12.md` = M12 起（M13/M14 各另册）；M11 台账**必有**、M12 及以后各册**存在则校验**（不存在 ⇒ 打印跳过，M11 仍校验 ⇒ 非 vacuous），任一红即红。任务号接受旧 `PREFIX-nnn<suffix>` 与新 `mNN-<module>-NNNN`（3–4 位、无后缀）两种。三张表（**表位置即状态**、无状态列）：①「待开始（未开工）」3 格 `| 编号 | 预估时间 | 一句改动 |` —— 任务书状态须为 `待开始` 且**不得含派单时间**（未派单）；②「进行中（已派单：待开始 / 待验收 / 待返工）」4 格 `| 编号 | 派单时间 | 预估时间 | 一句改动 |` —— 任务书状态 ∈ {`待开始`,`待验收`,`待返工`} 且**派单时间必填**（`YYYY-MM-DD HH:MM`；`待开始` 在此表表示「已派单、实现中」）；①② 预估时间匹配 `N h` / `N–M h` / `N 天` / `N–M 天` / `min`；不判次序。③「已验证」3 格 `| 编号 | 完成时间 | 一句改动 |` —— 任务书状态须为 `已验证`；完成时间 `YYYY-MM-DD HH:MM` 且**不得带 `（登记）`**；按完成时间倒序（同时间按编号升序）。三表一句改动均 ≤120 字符；任何表**不得出现状态列/状态值**；编号不重复且不得跨表重复；三表并集覆盖活 `t` 册 + `INTEG-*m` 册所列号 + 正文号（已归档号豁免，全仓无册的悬空号 FAIL）。三标题 / 表头缺失、三表皆空 ⇒ FAIL。`--self-test` 内置十四类注入（进行中缺派单时间 / 待开始行带派单时间 / 派单时间格式非法 / 状态映射不符 / 预估格式非法 / 完成时间带（登记）/ 同号跨表 / 已验证乱序 / 状态列 / 三表次序 / 覆盖缺失 / 缺小节 / 超长 / `.work` 路径）。**R1 台账一致性**（`INFRA-145t`）：`git worktree list` 检出的任务分支或**未合并**本地任务分支（已并入 `master`/`main` 豁免）⇒ 该任务号**不得**在「待开始」、须在「进行中」（册已 `已验证` 则须在「已验证」表），未列入任何表 ⇒ FAIL，逐条指名 `L??`；非 git 树（`--root` 自检树）打印跳过；`--self-test` 另含 R1 六类真 git 临时仓库用例。**A6 双台账路由**：每份台账取其头 `项目里程碑 = M<n>` 断言（缺失 ⇒ FAIL），任务号按任务书 `**项目里程碑**` 字段（无活册的新格式号按 `mNN-` 前缀）定所属台账；行/正文号落在**非所属**台账 ⇒ FAIL（跨台账错放）；归档册豁免；`--file PATH` 选台账（默认 `milestones.md`）。 |
| `make check-archive` | **L1** | `.tao/archive/M<i>/` 结构与册字段（规则 = `docs/Process-04` §5–§8）：① 三件套非空；② 根文件白名单仅三件套（任务书含 m 一律放模块子目录）；③ 子目录只允许 6 个模块名（`notes/` 即 FAIL）；④ 每册 `**状态**` ∈ {`已验证`,`里程碑`}、`**项目里程碑**` 里程碑号 == 归档号；⑤ §1 模块计数 == 模块目录实际册数（现场统计）；⑥ 流水 ID 集合 == `t` 册集合或 `t`+`m` 集合（M7+；M1–M6 日期列 `changelog` 只要求表格非空）、行状态 == 任务书状态；⑦ README 有 MEMORY/指针节、M9 起有终局证据；⑧ `issues-closed.md` 非空壳。`--self-test` 13 类注入（各自可达 FAIL）；`INFRA-117t` 归一后**严格默认**（无过渡 flag），现文全归档 rc=0。 |
| `make check-spec-archive` | **里程碑收尾专项**（随 `check-milestone`；**不入 L1**） | 册头 ∪ 附录声明的每个版本须有 `.tao/archive/SimRISC-<ver>/`：A1 目录存在；A2 目录非空且含 `SimRISC-00*`；A3 文件数 = 派生清单；A4 反向（磁盘 ⊆ 清单）⇒ 双向；**只校验存在性与文件集、不校验内容**；`-rc` 不参与。判定归 `tools/spec/check_spec_archive.py`（判据未改，仅改触发层）。 |
| `make check-spec-archive-verify` | **里程碑收尾专项**（随 `check-milestone`；**不入 L1**） | 归档**内容**：以各目录 `PROVENANCE.md` 的「快照提交」为锚，逐文件 sha256 与该提交树全等 + 「版本组合 sha256」= 按表重算值（拒绝子串/前缀匹配）；无 `PROVENANCE.md` 的既有目录回落派生快照；`-rc` 打印 SKIP。判定归 `tools/spec/gen_spec_archive.py --verify`（判据未改，仅接线）。 |
| `make check-milestone` | **L2 层 / 里程碑收尾专项**（按需；**不入** `check-modules`） | 先跑 `check-spec-archive` + `check-spec-archive-verify`（归档结构 + 内容 sha）+ `check-l3-report`（L3 报告存在性/结构/结果）；**回归运行报告不入本目标**（观测，按需 `check-night-report`，`INFRA-126t`）；再：**里程碑台账**（自动发现 `.tao/knowledge/milestones*.md`：`milestones.md` / `milestones-m12.md` / `milestones-m13.md` / `milestones-m14.md`，或用 `--file` 指定）逐本校验：须有 `项目里程碑 = M<n>` 断言（否则 vacuous FAIL），台账列出的任务号须在 `.tao/tasks/**` 或 `.tao/archive/**` 真实存在（台账零任务号 ⇒ vacuous FAIL）；并接 `check_tasks.py --strict`（漏收尾 = 0）。**核验册（`m` 册）机制已删除**（用户 2026-11-10：可删掉核验册机制；2026-11-08 起 M11 不建 m 册、M12 编号 `mNN-<module>-<NNNN>`）⇒ 不再做册识别、旧册顶替与册内号检查。 |
| `make check-manifests-guard` | **L1** | 全仓 `.manifests.toml` 双向校验：目录直接子文件（清单自身不计）== `files` 键、直接子目录 == `subdirs`（多一个/少一个都红）；带 `sha256` 的条目逐字节校验；`recursive = true` 对子目录递归（单向 ⊆）；`owner` 只打印。零清单 / 清单纯空 ⇒ FAIL。判定归 `tools/infra/check_manifests_guard.py`。第一批清单：`spec/`、`.tao/`、`.tao/knowledge/`（能力并入原「spec 只读册 sha256 锁」与「`.tao/knowledge/` 顶层白名单」两个已删门控）。**必需清单注册表** = `manifests/dir-guard-roots.toml`：登记目录缺清单 / 目录不存在 / 注册表缺失 / 游离清单 ⇒ 均红（删清单不关闭约束）。 |
| `make check-idl-sync` | **L1** | `idl/*.idl` 是语义源，`spec/SimRISC-*` 的 `<!-- IDL:<id> BEGIN -->` … `<!-- IDL:<id> END -->` 之间是**渲染结果**：重渲染后**逐字节**比对（漂移 ⇒ 红）；源 id 不在 `contracts/opcodes.yaml`、`# id:` 重复/缺正文、落点缺标记/空标记/串册、标记嵌套 ⇒ 红。`--self-test` 四类注入（改 spec 块一个字符 / 改源不重渲染 / 删一条 `# id:` 留标记 / 调用未声明的库函数）各自须 FAIL。判定归 `idl/render.py --check`。源 = `m15-spec-001`。 |
| `make check-idl-parse` | **L1** | `idl/idl_parser.py` 用 Python 标准库把 13 个源（12 册 + `idl/lib/fp.idl`）解析成 AST：① 全量解析、operation 条数与 `contracts/opcodes.yaml` 的 `- id:` 独立对账；② 每个 operation/function/enum/常量的**构造签名**（AST 规范化 S 表达式 sha256 + 节点数 + 节点种类计数）与 `idl/idl_parse_fixture.json` 逐条一致（改 `.idl` 或改 AST 形状须显式 `--update` 并评审 diff）；③ **拒绝集**（`idl/idl_parse_cases.toml`）每条必须按**预期类别**报错（子集外构造 `while`/`struct`/`sizeof`/`CSR[]`/复合赋值/变量作复制次数/自减、括号/花括号不配对、类型标注缺失、缺 `;`）——静默跳过 ⇒ 红；④ **接受集**合法样例必须通过且 AST 含预期节点（防过度拒绝 / 空树）。**只做语法、不做语义**：字面量位宽与原文留档，`U04`–`U10` 未定义项不内置假设。`--self-test` 内置注入自检：基线须 PASS，删右括号 / 改一条 operation 的 AST / 子集外 `while` 三类注入各自须 FAIL，还原新拷贝须回绿。判定归 `idl/idl_parser.py --check`。源 = `m17-idl-002`。 |
| `make check-syscall-abi` | **L1** | syscall 参数寄存器组表的三载体（musl `__dadao_argmask` / `src/thread/dadao/syscall_cp.s` 派发 / QEMU `cpu_loop.c:dadao_argmask`）逐项一致（号→掩码全等；asm 子集逐号相等 + 每个 `.Lm<mask>` 块的 `rd2rb`/`rd2rd` 条数 = 掩码位值）+ 完整性（musl 能发出的 syscall 名 ⊆ 表，空表 vacuous FAIL）。工作树在则读树，否则读 `components/**` 补丁（新克隆可跑）；完整性/audit 两项在无 musl/qemu 检出时 SKIP 并打印。 |
| `make check-musl-freshness` | **L1** | 安装根 `libc.so` 必须由**当前** musl 源 + 工具链构建：`build_musl.py` 成功构建后落 `obj/.dadao-musl-source-stamp`（全树内容 sha256）与 `obj/.dadao-toolchain-stamp`；门控比对两戳记 + 安装副本与构建产物 sha256 一致 + `ld-musl-dadao.so.1` 符号链接指向 + **`obj/.dadao-builtins-stamp`**（`libc.so` 的 `LIBCC` 归档内容 sha256，`ISS-293`：DSO 内嵌 builtins，归档变则须 relink）。任一项不符 ⇒ FAIL（提示 `make build-musl-shared`）。无构建树 / 无共享产物 ⇒ SKIP 并打印（L1 在纯静态工作流与新克隆仍可用；有产物而缺戳记 = FAIL）。成本 ~1.3 s。源 = `ISS-258`（协议双侧变更后 `libc.so` 未重建 ⇒ 动态档全灭）。 |
| `make check-builtins-freshness` | **L1** | 工具链消费的**三份** compiler-rt builtins 归档（构建树产物 / 构建树 clang 资源目录副本 / 安装根副本）须同一 sha256，且归档 mtime 与其**每个成员 `.c.o`** 的 mtime 均 ≥ 构建树 `clang` mtime（`ar` 确定性模式成员头无时间戳 ⇒ 成员按名回查构建树对象；`gcc_personality_v0` 类非成员对象不计）。缺构建树 / 安装根 ⇒ SKIP；有产物而缺副本 = FAIL，提示 `make build-builtins` + `make install-host`。`--self-test` 四类注入（篡改安装副本 ⇒ 红；只动 mtime ⇒ 不假红，`ISS-263`）。成本 ~0.1 s。源 = `ISS-293`（`shl` 编码迁移后 builtins 未重建 ⇒ 旧编码残留 ⇒ 新 qemu 按 ILLI 打 SIGILL）。 |
| `make check-run-artifacts` | **L1** | 三个 user-mode 驱动的 `--json-out` 必填且无 `DEFAULT_LOG_DIR` 固定回落（A1）；`.work/tests/**` 与 test-artifacts 根下每个 `^\d{8}T\d{6}Z-` 运行目录须有 `run.json`/`run.log`/`meta.json`，meta 含非空 `command`/`started_utc`/`toolchain.{clang,qemu,libc}` sha256（A2）；`.work/log/**` 新增文件名须为 `check-<name>.log` 或 `<任务号>-<用途>.(log|json|txt)`，存量按 `.run-artifacts-epoch` + `.run-artifacts-baseline` 豁免（A3）。无扫描面 ⇒ SKIP 并打印；`--self-test` 逐条注入可达 FAIL。规则 = `docs/Process-08`。 |
| `make check-test-reports` | **L1** | `docs/TestReports/` 报告卫生（规则 = 该目录 `README.md` + `Process-09`「测试报告归属」）：R1 报告正文无运行期绝对路径（`/tmp/**`、`/home/**`、具体 `.work/**`；规则文本里的 glob 形态不命中）；R2 快照（正文含 `<!-- 现场生成，勿手改 -->`）**首行**须为该标记，且**至少一份**快照存在（标记全删 ⇒ vacuous FAIL）；R3 文件名 `<M>-<主题>[-<后缀>].md`（`M` + 数字、无日期/空白）+ **无二级主题子目录**；R4 册头（前 40 行）含 生成时间/数据来源/机器指纹/复现。`README.md` 是规则册，R1/R2/R4 不查它。`--self-test` 四类注入各自可达 FAIL。源 = `m13-testcases-004`。 |
| `make check-temp-dirs` | **L1** | 陈旧任务临时目录 / 陈旧大文件 + 占用门控（`INFRA-145t`/`INFRA-146t`）：扫 `/tmp/opencode` 与 `$TMPDIR/opencode` 的**直接子目录**，排除 `git worktree list --porcelain` 的活动 worktree（由任务收尾清理）；**在用任务豁免**：目录名以任务号开头（允许 `-<后缀>`）且 `.tao/tasks/**` 任务书 `**状态**` ∈ {`待开始`,`待验收`,`待返工`} ⇒ 视为在用；其余目录（`已验证`/任务号不存在/非任务号名）**mtime > 2 h** ⇒ FAIL（`du` 体积前 5 大 + 陈旧总数/总体积）；根**直接子文件** **> 100 MiB 且 mtime > 2 h** ⇒ 列清单后 FAIL（`--large-file-mib` 可参数化）；根所在文件系统**占用 > 70%** ⇒ FAIL（`df` 实测、容量不写死）；**只报告不删除**；无任何扫描根 ⇒ PASS（不 vacuous 失败）；`--root` 可指向临时树自检。`--self-test` 覆盖陈旧 FAIL / 活动 worktree 豁免 / 在用任务豁免 / 已验证任务 FAIL / 未知任务号 FAIL / 非任务号 FAIL / 大文件 FAIL / 缺根 PASS / 占用阈值注入 / 只列前 5 大 / 只报告不删除。清单口径：`INFRA-145t` 清理清单 119 行 = 116 行带时龄路径 + 3 行裸名（完成区「116」只计带时龄目录；共清理 116 个目录，裸名行为同批无时龄记录项）。 |
| `make check-writer-guards` | **L1** | 共享构建树/安装根的写者护栏自测（`ISS-373`；机制与边界 = §2.1，实现 = `tools/infra/writer_guard.py`）：临时树 + stub 二进制跑四类真实验 —— ① 活跃写者 ⇒ **真实**跑批入口拒绝（rc=75）且不执行二进制；② 跑批期间替换二进制 ⇒ FAIL（"二进制在跑批期间被替换"）；③ stale（pid 不在 / pid 被复用 / JSON 不可解析）可检测、不拦读方、`clean` 可清且幂等、下个写者自动清；④ 正常路径与"读方嵌在自己写者内部"（同 make 树）不误伤；⑤ 状态目录覆盖（`--state-dir`/`DADAO_WRITER_STATE_DIR`）**必告警**（stderr + `state-dir-override.log`），默认路径不告警。接线断言：每个登记的读入口仍调 `start_guard`+`finish_guard`（清单 = `check_writer_guards.READER_ENTRIES`，现场计数）；`Makefile` 的 `WRITER_TARGET_COMPONENTS` 覆盖所有 `build-*`/`install-*` 门控目标、只登记门控目标、组件名 ∈ `writer_guard.COMPONENTS`；`make` 真把写者目标展开成 `writer_guard.py run --component …`（探针 makefile，不跑构建）；本目标在 `_locked-check` 里。不写仓库状态、不碰真实 registry、不跑构建 ⇒ L1。可达 FAIL 的注入方式：删掉任一读入口的 guard 调用（S1 红）、从 `WRITER_TARGET_COMPONENTS` 删一行或写错组件名（S2 红）、让写者目标不再被 `writer-guard`（S3 红）。源 = `m13-infra-003`。 |
| `make check-runner-reap` | **L1** | 合成驱动下外部 `SIGTERM`/`SIGINT`/`SIGHUP` 后子进程（own-session + 同组 + 超时路径）全部回收、诱饵进程存活；不跑 qemu/编译；`proc_reap` 清理钩子被禁用 ⇒ 残留 ⇒ 可达 FAIL（证据脚本注入）。源 = `TESTCASES-085t`。 |
| `make check-night-report` | **按需诊断**（观测口径；**不随** `check-milestone`，不阻断收口；**不入** L1/L2/L3） | `.dadao/tests/night/<最新日期>/` 的三件套（`manifest.tsv`/`meta.json`/`run.log`）存在且非空；`manifest.tsv` 表头 `scope<TAB>suite<TAB>rc<TAB>log` + 数据行 ≥1 + 四列 + `rc` 整数；覆盖 `tset` 三个套件（libc-test/llvm-ts/embench）与 `arch` 行；**任一 rc≠0 ⇒ FAIL**。**未跑回归运行 ⇒ 明确 FAIL**（不是 SKIP）。`--self-test` 八类注入。回归运行 = 观测/按需消费，成员与期望随演进调整（2026-11-06 用户裁定 A，`INFRA-126t`）。源 = `TESTCASES-076t`。 |
| `make check-l3-report` | **里程碑收尾专项**（随 `check-milestone`；**不入** L1/L2/L3） | `.dadao/tests/l3/<最新 UTC 戳>/` 的三件套存在且非空；`meta.json` 的 `command`（指向 check-full）/`started_utc`/`finished_utc`/`commit` 非空 + `toolchain.{clang,qemu}` 有非空 content id（libc/lld 记录但非必需）；`manifest.tsv` 表头 `scope<TAB>suite<TAB>rc<TAB>log` + 四列 + `rc` 整数 + **`log` 文件真实存在且非空**；覆盖 L3 成员表所列 scope（按 `l3_run.DEFAULT_MEMBERS` **现场派生**，非写死四 scope）与 `l3_run.DEFAULT_MEMBERS` 全部成员；**任一 rc≠0 ⇒ FAIL**；`run.log` 的 `[exit marker] rc=N` 须与 manifest 一致（防伪造全绿）。**未跑 L3 ⇒ 明确 FAIL**（不是 SKIP）。`--self-test` 十三类注入。源 = `TESTCASES-083t`。 |
| `make check-install-tools` | **按需（`install-host` 收尾断言；不入 L1）** | 安装根须带齐 `Makefile` 的 `HOST_LLVM_TOOLS` + `HOST_LLVM_TOOL_SYMLINKS`（脚本**解析 Makefile**，不另立第二份清单）：逐个存在、可执行、运行探针 rc=0（`not` 用 `not false`）、尺寸 == 构建树；`--sha`/`--sha-tools` 另比 sha256；别名须为**相对符号链接**、目标可执行且同源；`llvm-readelf -h` 须解析大端 DADAO 探针对象（`ELFDATA2MSB` + `EM_DADAO`）。未跑 `install-host` 的新克隆**必然红** ⇒ 不入 L1（同 `check-milestone` 理由）；挂载点 = `install-host` 收尾。`--self-test` 五类注入。成本 ~0.2 s（`--sha` ≈1.8 s/342 MB）。源 = `ISS-261`。 |
| `make check-inst-asm` | **L2** | `.S` 载体执行门控（`m13-testcases-030` / `ISS-413`）：载体集 = `tests/inst/` 下**含 `.S` 的子目录**（现场派生，册名/册数不写死），每册链接布局取该册目录内的 `.lds`（无则 01 册默认布局）；`<id>.S` 的**镜像 = 每 `.S` 一个**（`m15-testcases-007`：链例 + 该文件的全部故障例顺序跑）：每个镜像比**结果字节流**（`8 × 检查点数`，逐字节），故障例不符 ⇒ 该镜像退出码 ≠ 0（monitor 段 `0xF0|异常位索引` 或 `SYS_EXIT(点号)`）；`-defsym CASE_N=<点号>` = 调试用单例模式（不进本门控）。镜像数/检查点数由目标现场派生，不写死。**单平台 QEMU `kaiwu-tiny`**：chipyard/gem5 三方逐字节是各册任务的验收口径（分钟~小时级，不入 L2）。载体含**非 id 载体**（`tests/inst/00-isa-design/undi_reserved.S`：保留编码 ⇒ UNDI，在 `check_tests_index`/`validate_vectors` 的 `NON_ID_CARRIERS` 逐文件登记）。**Vast 不做 ISA 级执行覆盖**（用户 2026-11-14 裁定，`m13-testcases-043`）：Vast 的 ISA 语义由 `spec/` + M13 三平台差分矩阵承担，不得再以 `check-inst` 作为 Vast 执行证据。前置只要求**已存在**的 `qemu-system-dadao` + 固定 64 KiB 固件（**不挂** `build-bootrom`，L2 不重建共享产物）；read guard 只登记本平台集合真会用的二进制。 |
| `make check-inst-sig` | **L2** | 签名区**槽级**门控（`m17-testcases-001`）：期望值从 `.S` 的 `__CHECK_*` 内联常量（及 `WDATA` 数据区）派生到 `tests/data/inst-signature/`（`expected.tsv` + 输入 `inputs.sha256`；漂移即红，提示 `make inst-signature-data`）；QEMU 逐镜像取签名流，`signature.py` **逐槽**比对，失败给「槽 N 期望 0x… 实际 0x…（来源 `.S:行`）」；正常镜像判红时另编 `-defsym SIG_CONTINUE=1` 诊断镜像（未定义时 `.text` 逐字节不变）取完整流定位；签名流缺失/长度不符 ⇒ **BLOCKED**（不是 PASS）。镜像数/槽数现场派生并与 `tests/case-ledger.tsv` 另一条扫描路径对账；**期望值不从实测反推**；`__CHECK_*` 的**运行期关系**槽（如「两次读回相等」）只判已写（语义由 `.S` 内 `br.eq` 承担）；漏跑（`__NCHECK` 有、`SIGUPD` 无）静态判红。单平台 QEMU，前置同 `check-inst-asm`。 |
| `make check-linux-toolchain` | **L1** | `tools/linux/toolchain_matrix.json`（format 1）每行 `declared == measured == 现场探针实测`；能力探针一律带 target triple（`--target=dadao-unknown-elf` / `llvm-mc -triple=`），且 `toolchain.target` == 脚本 `TARGET`；`required_for_k0` 行须 present/supported；缺口行须有非空规避法 + `workaround_measured=verified` + 现场重验通过；行集合**等于**矩阵覆盖表（缺行/未知行/重复行 ⇒ FAIL）；`docs/TestReports/M14-K0-toolchain-gaps.md` 与矩阵 + 实测的重渲染**逐字一致**（只比「生成时间/机器指纹」两行外）。探针/矩阵不可读 ⇒ FAIL（不 SKIP）；能力探针读安装根（未 `make install-host` ⇒ 红，同 `check-components`）。`--inject` 6 类注入。不跑被测语义（编译探针）⇒ 按 §3 判据 1 归 L1。源 = `m14-infra-001`。 |
| `make check-linux-boot-contract` | **L1** | 三方逐字段一致：`spec/Kaiwu-测试机运行环境.md §6.3` ↔ `.tao/contracts/contract-linux-boot.md` ↔ `contracts/linux-boot.yaml`（boot info 表逐字段偏移/宽度/名/值/语义；内存分区区间与大小由 YAML 现场格式化；进入时状态表；装载规则 id 集合/顺序 + `rule` 逐字 + 每条规则在正文/契约各出现且仅一次）；地址口径硬断言 `VA = PA + 2 TiB`、内核窗口 `[2 TiB, 3 TiB)`、`forbidden_terms` 零命中、旧地址（现场派生）零命中；`not_defined` 每项在正文与契约的「不定义」句逐项点名；输入缺失 ⇒ rc=2。`--self-test` 8 类注入。只读静态比对 ⇒ L1。源 = `m14-spec-001`。 |
| `make check-config-pins` | **L1** | `ISS-470`（F30/F41 两次复发）：`components/linux/patches/arch/dadao/Kconfig.debug.patch` 现场解析出的每个 `config DADAO_*` 必须被**每个**切片脚本的模块级 `CONFIG_PINS` 显式钉住 —— 键集合 **== Kconfig 全集**（缺一个 ⇒ 红并点名「脚本 X 缺符号 Y」；多一个 ⇒ 红，防拼写错），且该脚本的切片由 `config_pins.config_lines()` 派生（`tests/unit/linux/*.py` 与 `tools/linux/*.py` 里不得再有 `"CONFIG_X=v"` 手写切片字面量）；int 符号钉 `"n"`（= 该镜像「置空」）须其 `depends on` 在该镜像下**确实不满足**（Kconfig 对 int 无 `n` 值、不可见时不写行，钉具体值反而会被 `olddefconfig` 丢掉）；`IMAGE_CONFIG`/`IMAGE_ON` 这类期望表须与钉子逐项一致；调 `apply_config_lines` 却没有 `CONFIG_PINS` ⇒ 红（新门控不能逃逸）。Kconfig 解析不到任何符号 ⇒ 红（fail-closed）。计数（脚本/符号/镜像）现场统计、不写死。`--self-test` 6 类注入（缺键 / 多键 / 手写切片 / int 钉 n 但依赖满足 / 无常量脚本 / 空 Kconfig），每类各自可达 FAIL。只读静态（不建、不跑）⇒ L1。源 = `m15-infra-008`。 |
| `make check-linux-k0` | **L2** | K0 收口（跨产物）：K1 `vmlinux` 存在且可解析；K2 ELF64/大端/`e_machine`/`ET_EXEC`/`e_flags` 版本；K3 `e_entry == kernel_base`；K4 程序头类型 ⊆ {LOAD,NOTE,GNU_STACK} + 每 `PT_LOAD` `p_vaddr − p_paddr == va_pa_offset`、页对齐、`p_align ≥ 页大小`、区间 ⊆ 内核镜像区；K5 不与启动保留区 `[ram_base, boot_info 区终点)` 重叠且在 42 位内存窗口内；K6 `llvm-nm -u` 为空；K7 initramfs `newc` 首条目 `.`、末条目 `TRAILER!!!`、含 `init`(0100755) 且 payload sha == 交付的 `/init` == manifest（`init` 自 `m14-linux-031` 起是 busybox 启动脚本，K0 自写 ELF 以 `init.musl` 同装）；K8 临时目录二次生成 sha 相同且 == 交付归档；K9 initramfs ≤ 区上限 + 镜像内用户态 ELF（`init.musl`、`bin/busybox`）无 `PT_INTERP`/`PT_DYNAMIC`；K10/K11 直调两条 L1 脚本逻辑 rc=0；K12 `apply-series --component linux` 两次 rc=0、HEAD 不变、源树干净、`rev-list --count <base>..HEAD` == 现场派生值（非空 series ⇒ 1）；K13 补丁/段/条目计数现场统计。**期望值全部现场派生**（`contracts/linux-boot.yaml` / 矩阵 / 组件锁 / `paths.py`），缺产物/未 provision ⇒ **FAIL 并给 `make linux-*` 命令**（无 SKIP）；构建与 apply-series 超时（rc 124）判 FAIL。含**增量构建**（写 `.work/build/linux`）⇒ 在 `GATE_LOCKED_TARGETS`。`--inject` 8 类注入。源 = `m14-infra-003`。 |
| `make check-linux-k1` | **L2** | K1 收口（Vast 端到端，用户 2026-11-14 裁定：「能进入 `start_kernel`、开启时钟之前打印信息退出，K1 就算完成」）：K1 增量构建 rc=0；K2 `e_entry == kernel_base`；K3 BootROM 索引表 magic/条目数/类型顺序（hmon<smon 各一条）+ 复位向量落在 power 窗口且窗口非空；K4 hmon/smon 入口落在各自 SRAM（`spec/Kaiwu §1.1`）且 ELF 在镜像内；K5 guest `SYS_EXIT` rc=0（**命令行无 `-d/-D`**，输出无转储标记）；K6 boot info 15 字段 == 契约/现场推导的 `kernel_size`；K7 `entry_va` == 契约入口 == `e_entry` == `kernel_base`；K8 smon 移交态（`ptw_enable` == 契约、传入 PTBR == 契约、预建表只 1 个超页）；K9 内核自建表（L1 索引 `kernel_start >> 29`、P/SP/SPF、`PTBR` == `swapper_pg_dir` 的 PA、`[15:0]` 被清零、确实改变）；K10 切换后仍能执行（同一 VA 已映射 + 两处 VA→PA + marker 回读）；K11 阶段各出现 1 次且顺序为 入口→报告→PTW→建表→安装→切换后→`start_kernel`→退出；K12 停止点（marker 1 次、`ra` 在 `start_kernel` 内、**退出行是最后一行**）；K13 反向断言（无 `panic`/具名 fault/拒绝行；`CFXMEM` 只有那 1 次预先声明且已恢复的探针；无 init/syscall/IRQ/timer 痕迹）。期望值全部现场派生（`contracts/linux-boot.yaml` / machine profile / ELF 程序头 / `llvm-nm`）；含**增量构建** ⇒ 在 `GATE_LOCKED_TARGETS`。`--inject` 4 路注入（magic/PTBR 未映射/退出码/删 marker）；`--selfcheck` 12 组（含镜像与 BootROM 副本）。与 K0 不重叠：K0 查「能否交接」，K1 查「内核跑起来并退出」。源 = `m14-linux-005`。 |
| `make check-linux-k2` | **L2** | K2 收口（Vast 端到端，用户 2026-11-16 裁定：出口判据收窄为 4 条）：**E** 同步异常通道（预先声明的 `CFXMEM` 分类正确=名字+`ip`+`info` 后恢复；未声明同类 ⇒ 具名终止、不递归；退出码 == `spec/Kaiwu §7.1` 的 supv+CFXMEM）；**T** 时钟（`cfx_time` freq == `contract-see §3`、`time` 严格单调、tick 间隔 == freq/HZ（`HZ` 从该镜像 `.config` 现场解析）、`margin = period/2` 且 4×实测最大偏差 ≤ margin）；**M** 屏蔽（屏蔽窗内 tick 冻结、解除后恰 +1；帧内不嵌套、`escape` 后补投 +1）；**R** 不回归（`check-linux-k0` / `check-linux-k1` 子门控 rc=0，计数从各自输出现场解析）。复用断言 **S** 端到端阶段顺序（power→hmon→smon→入口→`start_kernel`→`setup_arch`→`time_init`→同步向量→异步向量→两轴 mask→tick→屏蔽窗→`SYS_EXIT`）与 **X** 退出码 A′ 分段（PASS `0x00` / guest `0x01-0x7f` / 其它 cfx `0x80|cfxHA` / monitor `0xc0|mode<<4|bit`；自检码全集静态扫描）。期望值全部现场派生（`spec/DADAO-13 §2`、`spec/Kaiwu §7.1`、`contract-see §3`、镜像 `.config`、ELF 程序头、BootROM 镜像）；三镜像（`defconfig` / trap 自检 / irq 探针）+ 增量构建 ⇒ 在 `GATE_LOCKED_TARGETS`。`--inject` 4 路（异步向量未映射 / 周期 0 / 只开一轴 / 终止码进 guest 段，均 `cp`+md5 还原后重建回绿）；`--selfcheck` 7 组。与 K0/K1 不重叠：K0 查「能否交接」、K1 查「跑起来并退出」、K2 查「异常通道 + 时间 + 屏蔽」。源 = `m14-linux-009`。 |
| `make check-linux-k5` | **L2** | K5 收口（Vast 端到端；用户 2026-11-16/17 裁定：只跑代表例，全量 case 由 `k5_*_probe.py` 各自单独跑；用户 2026-11-20 裁定范围 B：含 shared futex 与基本信号投递，不含 pthread create/join）：**S** 用户态闭环（`m14-linux-023`：镜像只带本探针、`/init.musl` 自己跑起来（`init: pid=` / `brk +65536` / 退出 0）、`write`/`exit` 往返、errno 为 `rd8 = -errno` 落在 `contract-syscall §9` 的 `[-4095,-1]` 且 `rd1` 不参与、`rb3`(rbtp) 帧与用户读回一致、cg5 帧字段（`CFXTRAP` ← `spec/DADAO-13 §2`、上一模式 ← `spec/DADAO-12 §1`、`immu18` ← 桩反汇编））；**C** clone/线程（`m14-linux-024`：`CLONE_VM` 共享 mm/ASID 且 `mm_users` +1 再回落、`CLONE_SETTLS` 子 rbtp == tls、子 `rd8=0` + 父返 tid、`CLONE_THREAD` 同 tgid、fork 对照私有 mm、`lr;sc` 成败值 ← `spec/SimRISC-12 §1`）；**F** futex/原子（`m14-linux-025`：`FUTEX_WAIT` 在桶锁下复核 ⇒ `-EAGAIN`、唤醒不丢、`lr`…`sc` 不跨 syscall；**shared futex 在匿名页上可用** —— `m14-linux-035` 的 rmap 成果：页有 mapping ⇒ `WAKE=0`、错值 `WAIT=-EAGAIN`、`PAGE_MAPPING_ANON` 的等价不变量 = `folio_test_anon` + 非 NULL mapping，静态对账 `mm/rmap.c` 的 `*_MAPPING_ANON` 与 `get_futex_key()` 的 anon 分支）；**T** 时钟（`m14-linux-026`：clocksource 单调且与 `sched_clock()` 同源、`set_next_event()` 写绝对比较值与投递间隔 ∈ `[period/2, 2*period]`、tick 一投递一 jiffy、`ktime_get()` 已离开 jiffies 后备源）；**G** 信号（`m14-linux-027`+`046`：无 VMA/只读写的用户访问投 `SIGSEGV`（非 `DADAO_PF_FATAL`）、`exit`/`exit_group`、`RLIMIT_STACK` 继承、信号帧四组/`ra` 栈/`rf0` 往返、无 handler ⇒ 默认动作；信号号 ← uapi `signal.h`，僵尸态 ← `sched.h`）；**P** 64 KiB ABI（`m14-linux-028`：`AT_PAGESZ` == `.config` 的 `CONFIG_PAGE_SHIFT` == `spec/DADAO-12 §2.2.2`、`mmap` 页对齐、`PT_LOAD` 数与逐段对齐（数取自构建出的 `/init.musl`）、`brk` 整页）；**R** 反向断言（六路控制台均无 `dadao: die` 具名终止、无 `unknown cause`、无 panic/oops/新 WARNING、无 `-d`、自检只开始一次；§4a 退役「新文案在 / 旧文案不在」+ 处置/替代判据记录；K3 退役符号与目标在活树 0 命中）。七镜像（S/C/F/T/G/P + 静态 R）⇒ 在 `GATE_LOCKED_TARGETS`。`--inject` 6 路（errno 写 `rd1` ⇒ S 红 / `CLONE_SETTLS` 不设 rbtp ⇒ C 红 / SIGSEGV 走 `DADAO_PF_FATAL` ⇒ G 红 / `AT_PAGESZ` 写 4096 ⇒ P 红 / 退役文案回潮 ⇒ R 红 ×2，均 `cp`+md5 还原后重建回绿）；`--selfcheck` 8 次翻转（S/C×2/F/T/G/P/R）全 PASS。源 = `m14-linux-029`。 |
| `make check-linux-k6` | **L2** | K6 收口（Vast 端到端；用户 2026-11-16 裁定「只跑代表例」）：**S** 启动（镜像 = 构建产物：`CONFIG_DADAO_K6_SHELL=y`、全部阶段探针关；initramfs 的 `/init` 与 `busybox` 逐 sha256 对上生成器/构建产物；`/init -> busybox sh`、ash 横幅、提示符各一次，且内核把 `/init` 当 init 执行）；**C** 五条代表命令（`echo`/`mkdir`/`cat`/`ls`/`rm` 的输出与 rc，含 `mkdir` 已存在、`rm` 已删除两个失败臂，以及 `mkdir -> 写 -> ls -> rm -> ls` 的文件系统效果；命令项数与用例数现场统计）；**E** 脚本最后的 `exit N` == QEMU 进程状态（PID 1 退出即会话结束；超时 rc 124 判 FAIL）；**R** 反向断言（无 `dadao: die`/`die-no-vma`/`unknown cause`/panic/oops/recursive supv、无阶段探针、无 `-d`）+ `Makefile`（PHONY/锁/L2/help）接线 + §4a.3 退役（新文案在 / 旧文案不在 / 替代指向 / 本节有记录）。镜像 = busybox + initramfs + kernel 增量构建 ⇒ 在 `GATE_LOCKED_TARGETS`。`--inject` 5 路（`/init` 不 exec sh、改提示符、少装 `cat`、PID 1 退出码写 0、`K6_SHELL` 关 ⇒ 各自判红；退役文案回潮 ⇒ R 红，均 `cp`+md5 还原后重建回绿）；`--selfcheck` 四组各一次翻转。源 = `m18-linux-003`。 |

- **计数类文档的同步时点**（2026-10-22 用户裁定）：`contract-isa.md` 等**分桶计数**（`m9`/`excluded`/`fp` 的条数与族数）**不随单任务改**，一律在**里程碑收尾**统一同步；单任务只同步其机械门控的期望值（`check_scope.py` / `check_fp_contract.py`），避免同一数字反复返工。
- 各检查均 **fail-closed**（扫描面为空 / 有 `m` 册而当前册缺失或册内零任务号 / 表被删空 ⇒ FAIL），可达 FAIL 见各脚本 `--self-test`。
- `check-milestone` 的层归属按 §3 判据定位：它**不跑被测语义**，但**只在里程碑收尾时成立**（归档 / L3 报告等收口产物日常不存在），故登记为 **L2 层 / 收尾专项**、不并入日常 `check-modules`（否则 L2 常态红）；触发点 = 里程碑收尾。**`m` 册自 M11 起可选**（用户 2026-11-08 裁定），是否建册不再构成本目标红的理由。
- `check-spec-archive` / `check-spec-archive-verify` 同属**收尾专项**：归档是只读历史快照，只在发布/里程碑边界变化（用户 2026-10-25 裁定：结构与 sha 都只在里程碑收尾做一次）⇒ 由 `check-milestone` 前置承载，**不入 L1**（`INFRA-109t` 前 `check-spec-archive` 在 L1）。

## 2. 触发点（MUST）

- **任务收尾**（`/dispatch` 后、`/complete` 前）：跑 **L2**（`make check-modules`）。
- **归档结构**（`check-archive`）：属 **L1**（`make check` 默认包含）——归档是只读历史，结构与册字段可随时静态核；**不新增收尾专项**（`INFRA-116t`）。
- **里程碑 / `/complete`**：跑 **L3**（`make check-full`；它逐成员落 `.dadao/tests/l3/<UTC>/` 报告）；里程碑收尾另跑 **`make check-milestone`**（归档结构 + 内容 sha + `m` 册（可选；有则校验、无则跳过）+ 漏收尾 = 0 + **L3 报告** `check-l3-report`）——归档门控**只在此触发**（`INFRA-109t`）；**回归运行报告不参与收口**（观测，按需 `check-night-report`，`INFRA-126t`）。
- **回归运行**：队列空档由**主会话** `setsid nohup make night-run > log 2>&1 &` 启动（一次只跑一个；**独立锁 `night.lock`**，与日常门控互不阻塞）；报告供**按需诊断**（`make check-night-report`）消费，红项按「真缺陷 / 语料假设过时 / 环境」分诊——**观测结果不阻断收口**（2026-11-06 用户裁定 A，`INFRA-126t`；独立化 `INFRA-127t`）。
- **某模块全量**：按需**单独调**该模块目标（不进 L1/L2）。
- **同工作树互斥（MUST）**：写共享状态的目标（构建树 `.work/build/**`、安装根 `.dadao/**`、SDK 产物目录 `.dadao/tests/**`）与跑这些写者的门控**串行化**——`Makefile` 的 `GATE_LOCKED_TARGETS`（**单一真源**，文档不另列清单）经 `tools/infra/gate_lock.py` 在 `.dadao/gate.lock` 上取 `flock(2)`，独立进程**排队**或 fail-fast，嵌套（同一 make 树）放行。语义：等待上界 `GATE_LOCK_WAIT`（默认 3600 s，超时 rc=75 并打印持有者 pid/开始时间/目标/命令，**不得**无限阻塞）；`GATE_LOCK_FAILFAST=1` ⇒ 立即 rc=75；锁不可用（父目录不可写 / 无 `flock`）⇒ rc=69 且**不运行**目标（禁静默跳过）。`--self-test` 覆盖「嵌套放行 / 独立进程拒绝 / 锁不可用报错」三类。**回归运行不在此列**（`INFRA-127t`）：它只读产物、只写自己的报告目录，用**独立锁** `NIGHT_LOCK`（`.dadao/night.lock`，`NIGHT_LOCK_WAIT` 可配），由外层 `night-run` 持有并把 `GATE_LOCK=$(NIGHT_LOCK)` 传给成员 ⇒ 回归运行小时级运行期间 L1/L2/L3 与构建照常拿 `gate.lock`，互不阻塞。源 = `ISS-229`（L2/L3 与 `install-host` 并发读到瞬态不完整的安装根 ⇒ Embench 假 FAIL；手动 `build-mc` 与 L2 内 `install-host` 并发 ⇒ 构建树写坏）。
- **安装根的工具链二进制只由 `install-host` 写入（MUST）**：`make install-host` 管理的二进制（`HOST_TOOLCHAIN_BIN` / `HOST_TOOLS_BIN` 等）不得手工替换。手工 `cp`/替换安装根属**例外手法**（`QEMU-066t` 先例），仅限「重建不可行或紧急兜底」，且必须：① 完成区写明理由与来源（构建树路径）；② 逐件核对 md5/sha256 与构建树一致；③ 之后补跑 `make install-host` 回归正轨。**例外手法不改变新鲜度判据**（`check-install-tools`/`check-builtins-freshness`/`check-musl-freshness` 比的是「安装根 vs 构建树」，副本不一致照样红）⇒ 只能兜底、不能替代重建。源 = `ISS-300`。
- **理由**：分层后「L1 绿、L2/L3 红」会成为常态 ⇒ **触发点缺失则"按需层"必然腐烂**（设计稿已识别此风险）。

### 2.1 共享构建树/安装根的写者护栏（`ISS-373`）

**问题**：任务 worktree 把 `.work`/`.dadao` 软链到主工作树，于是**一个会话重建二进制时，另一个会话的跑批正在读它** —— `m16-gem5-008` 重建 `gem5.opt` 期间三个复核任务读到 0 字节/半截/已被替换的文件 ⇒ 假红；反过来读到**旧**二进制 ⇒ 假绿。`gate.lock`（§2）只串行化**同一 make 树内的门控目标**，对"直接跑 `python3 tools/testcases/...`"的读方一无所知，也**不告诉读方**二进制正在被替换。

**机制（实现真源 = `tools/infra/writer_guard.py`；组件/路径表 = 其 `COMPONENTS`）**：

- **状态文件**：`$(WRITER_STATE_DIR)`（默认 `$(SDK_DIR)/writers`，即 `.dadao/writers/`），**每个活跃写者一个 JSON**：`<component>.json`（已被占用时 `<component>.<pid>.json`，绝不覆盖活记录）。字段 = `{schema, component, target, pid, pid_start, host, started, duration, expires, git_head, cwd, cmd, token}`；写入走"临时文件 + `rename(2)`"（读方永不见半截 JSON）。
- **写者侧**：`Makefile` 的 `WRITER_TARGET_COMPONENTS`（**单一真源**：`<target>:<component>[,<component>…]`）里每个目标由 `writer_guard.py run` 包一层 —— 登记发生在**拿到 `gate.lock` 之后、真正开始写之前**（排队等锁期间不算"正在写"），结束（`finally` + `SIGTERM/INT/HUP` 处理器）删除；状态目录不可写 ⇒ **rc=69 且不运行目标**（不静默跳过）。**逐目标组件**：`build-mc*`/`build-lld`/`build-builtins`/`install-cfx-aliases` ⇒ `llvm`；`build-qemu*` ⇒ `qemu`；`build-gem5` ⇒ `gem5`；`build-bootrom` ⇒ `bootrom`；`build-{picolibc,musl,musl-shared}` ⇒ `sysroot`；`linux-*` ⇒ `linux`；`install-host` 同时写安装根的 LLVM 工具与 QEMU 二进制 ⇒ `llvm,qemu`。
- **嵌套放行**：记录持有者的 pid 是当前进程的**祖先**（同一 make 树：`install-host → build-mc`、`install-host → check-install-tools`）⇒ 是同一段写，内层**不再登记、不覆盖外层记录**。同理读方遇到"祖先写者"不拒绝（前置写已完成）。
- **stale 判定（机械，不靠记忆）**：① `pid` 不存在（`kill(pid,0)`⇒ESRCH）；② `pid` 存活但 `/proc/<pid>/stat` 的 start-time ≠ 记录里的 `pid_start`（pid 被复用/重启后撞号）；③ 记录来自**别的 host**、或 `/proc` 不可用 ⇒ 只能按 `expires`（`started + duration`）判过期；④ JSON 不可解析 ⇒ **读方按"活跃"处理（fail-closed）**，`clean` 可删。**`expires` 已过但 pid 仍活 ⇒ 不判 stale**（长构建不是死构建），只报 `overdue`，读方仍拒。清理时机：**下次同组件写者启动时自动清**（`purge_stale`），或手动 `python3 tools/infra/writer_guard.py clean`。
- **读方 fail-closed**（`writer_guard.start_guard` / `finish_guard`；接线清单见 `check_writer_guards.READER_ENTRIES`）：启动时**按所读二进制路径派生组件**，若该组件有活跃**外来**写者 ⇒ **拒绝启动 rc=75**（打印组件/目标/pid/host/起始时间，提示等待）；**启动与结束各记一次所读二进制的 md5**，`结束 ≠ 启动` ⇒ **FAIL（"二进制在跑批期间被替换"）**、退出码非零（含"启动时不存在、结束时出现"）。入口未显式调 `finish_guard` 就退出时，`atexit` 兜底复核并强制非零（不会静默放过）。
- **`--allow-concurrent`（`DADAO_ALLOW_CONCURRENT=1`）的边界**：**只**用于"明知有写者、仍要观察"的情形（如并发窗口内做冒烟诊断、或用 `build-*` 的写者窗口验证读方行为）。使用时**必须**：① 在结论里标注该次运行的二进制是移动的、结果不可作验收证据；② 覆盖自动追加到 `$(WRITER_STATE_DIR)/overrides.log`（时间/读方/argv/cwd/组件/写者记录）。**验收/证据/里程碑类运行不得使用**；需要它才能跑通 ⇒ 应先等写者结束（`gate.lock` 会排队）。
- **状态目录覆盖（`DADAO_WRITER_STATE_DIR` / `--state-dir`）不得静默**：该钩子（门控自测必须）会把 registry 指向别处、从而使读方护栏可能失效 ⇒ **生效即告警**：stderr 打 `WARNING: writer-state-dir overridden via …; the writer registry (and therefore the read guard) may be bypassed`，并追加到 `<state>/state-dir-override.log`（时间/pid/来源/argv/cwd）。只用于自测/诊断，不得用于验收/证据运行。
- **与 `gate.lock` 的关系**：**不改变**其语义（嵌套放行、等待上界、rc 75/69 均不变）；写者登记**叠加在锁内**，读方护栏独立于锁（直接调用的跑批入口不取锁）。
- **覆盖边界**：读方护栏覆盖已接线的跑批/证据入口（`tools/testcases/**` 的 suite/probe 驱动与 `picolibc_tests.py`、`tests/unit/gem5/check_tiny_hmon`、`tools/qemu/{semantics_gate,k0_boot_probe,user_mode_smoke}`、`l3_run`/`night_run`）；**逐任务一次性探针**（`tools/testcases/arch/min_rom_probe_*.py`）与 **lit 本身**（`check-lit`/`check-lit-full` 的 RUN 行直接调 `llvm-mc`/`qemu-system-dadao`）**未接线** —— 前者靠任务书 md5 断言，后者是门控目标、由 `gate.lock` 串行化（直接手工跑 lit 时不在保护范围内）。新增跑批入口须接线并登记进 `READER_ENTRIES`（`S1` 会红）。
- **门控（L1）**：`make check-writer-guards`（`tools/infra/check_writer_guards.py`）在临时树里用 stub 二进制跑四类真实验（写者活跃 ⇒ **真实**跑批入口拒绝且不执行二进制；跑批中替换 ⇒ FAIL；stale 可清理且不拦读方；正常路径/嵌套不误伤），外加接线断言（读入口仍调 guard；`WRITER_TARGET_COMPONENTS` 覆盖所有 `build-*`/`install-*` 门控目标且组件名真实存在；`make` 真把写者目标展开成 `writer_guard.py run`；本目标在 L1 里）。归 **L1**（不跑被测语义、只读静态 + stub 自测，秒级；§3 判据 1）。

### 2.2 跑批进度可见性（用户 2026-11-15）

- **逐例完成行必须即产即 flush**：embench 用 `--jsonl-out` 追加（`docs/Process-08 §1.9`），驱动日志每例 `flush`；报进度前**必须从节点取回**这些行与 `ps -eo etime,args` —— 主控机副本长期 0 字节，**不得**作依据。
- **禁止**引用入库报告 / 上一次 `--json-out` 的旧值报进度；看板 `tools/testcases/tset/embench/progress.py` 只读节点日志 + `ps`，ETA 无数据标 `n/a`（不猜）。

## 3. 「新检查进哪一层」的归属规则（MUST）

新增检查（门控 / 目标）时，按下列**机械判据**定层（不手工权衡）：

1. **只看仓库完整性 / 组件可用性，不跑被测语义** ⇒ **L1**（静态检查、清单校验、哈希漂移门控、可用性冒烟）。
2. **跑被测语义，但只取"各类别代表 / 受控子集"**（数十 ~ 数百秒量级）⇒ **L2**。
3. **跑被测语义的全量 / 大套件**（数百 ~ 数千秒）⇒ **L3**。

- **代表集必须机械派生，禁止手工挑**：L2 的"各类别都有"由**类别清单**机械派生（按 `contracts/` 格式类 / 指令 `scope` / QEMU 语义类别等），**不得**人工挑选（`INFRA-058t` `check-qemu-smoke` 即此法）。
- **计数不写死**：代表集规模、覆盖率等一律**现场统计**，不得在门控/文档写死具体数字（`AGENTS.md`「验证脚本反例门控」）。
- **判据不确定时**：以「**是否跑被测语义**」+「**全量还是子集**」两问定位；仍不确定 ⇒ 先落 L2，待规模实测后上/下移（**迁移须同步 `Makefile` + 本表 + `AGENTS.md` 指针**）。

## 4. 层间不重复（MUST）

- **同一检查只在"一层"被"直接"列出**；某目标被上层**前置依赖**而间接跑到**不算重复**。
- **unit scope 的 L2/L3 分工（2026-10-27 用户裁定「一个检查只在一层」严格化）**：
  `check-unit` **只在 L2** 直接列出；L3 用 **`check-unit-full`**（= `check-unit` +
  `check-lit-full`）⇒ `check-unit` 在 L3 只是**前置依赖**（§4 明文允许），
  既拿到 unit 全量，又不违反「一层一列」。**不设任何例外。**
- **tset scope 的 L2/回归运行分工（2026-10-27 用户裁定，`TESTCASES-082t`）**：
  `check-tset-{libc,llvm,embench}-smoke` **只在 L2** 直接列出；tset **full** 只在回归运行
  （`night-run`）；**L3 不直接列任何 tset 目标**（`test-m6` 的 Embench E2E 是集成步骤，
  不构成 tset smoke 的重复）。同样**不设例外**。
- `Makefile` 中以注释标注每层成员与"已从 L1 移出"的目标，作为**机械可核**的层归属记录。

## 4a. 阶段推进即退役过时判据（MUST）

新阶段的门控落地后，**前一阶段门控中已被取代或不再合适的断言必须退役（删除或改写）**，不得留成恒真项、误导项或与新阶段口径冲突的重复项；退役须同时写明**替代判据的来源**（哪个新门控/哪条断言接手）。依据：用户 2026-11-16 口径「每推进一个阶段，前面的不合适的门控就可以关闭了」。

（`ISS-444` 即按本条处置：K2 门控 `check-linux-k2` 落地后，K1 门控里"阶段顺序只能间接证明"一类的断言按新口径退役。）

### 4a.1 `m14-linux-015`（K3 收口）的退役记录

K3 门控 `check-linux-k3` 落地后，K1/K2 门控里「同一地址只有那一个预先声明的 `CFXMEM`」与「未注册的 `CFXMEM` ⇒ 具名终止」两类断言**只在本镜像成立**（两个镜像都钉住 `CONFIG_DADAO_K3_PF_SELFTEST=0`，即无 mm 子系统），故按 §4a **改限定语**（不删除）。删除数 = 0：无「TLB 维护为空 stub」「TLB 不参与」类断言（`grep -n 'stub\|不参与\|旁路' tests/unit/linux/check_k1.py tests/unit/linux/check_k2.py` 零命中），故无删除对象。

| 门控 | 断言（锚点） | 处置 | 新文案 / 替代判据 |
|---|---|---|---|
| `tests/unit/linux/check_k1.py` | K13 CFXMEM 计数 | 改限定语 | 「本镜像内（`CONFIG_DADAO_K1_EARLY_STOP=y`、无 mm 子系统）CFXMEM 只出现 1 次：唯一一次预先声明的探针」；替代 = check-linux-k3 F 组 |
| `tests/unit/linux/check_k1.py` | K13 CFXMEM resumed | 改限定语 | 「本镜像内（无 mm 子系统）该 CFXMEM 是被处理过的探针（resumed）」；替代 = check-linux-k3 F 组 |
| `tests/unit/linux/check_k1.py` | K13 后置子系统痕迹 | 改限定语 | 加「无 mm 子系统 ⇒ 无页故障通道痕迹」，措辞改为「无 K1 之后的子系统迹象」；替代 = check-linux-k3 F 组 |
| `tests/unit/linux/check_k2.py` | E8 未声明 CFXMEM 退出码 | 改限定语 | 「本镜像内（无 mm 子系统）…；K3 起同址由页故障通道接住」；替代 = check-linux-k3 F 组 |

**保留**（在这些门控自己的镜像内仍成立，不是退役对象，理由同列）：K8「预建表只覆盖 1 个超页（探针 VA 切换前未映射）」（smon 移交态，K1 出口判据）、K9 内核自建表（L1 索引/P/SP/SPF/PTBR PDF，K1 自建表仍只有超页）、K14「该 PA 作为 VA 未映射」（K1 镜像无 mm 子系统，半主机按 PA 取值不变）、`FATAL_PATTERNS` 的具名 fault/页表拒绝、K2 的 E2/E3（注册探针命中与恢复是 K2 出口判据，K3 的页故障通道正是架在它之上）、K2 的 X6/X8（退出码分段与 cause 大类无关）。

**保留（补充核对：任务书口径 `grep` 命中的另外三处）**：按「CFXMEM|TLB|tlb|page|页表|未映射|PTW」在 `check_k1.py`/`check_k2.py` 现场 `grep` 的其余命中逐条核对，结论同为**保留**：

| 位置 | 断言（现场 `grep`） | 属内存/故障/TLB 类？ | 保留理由（为什么不退役） |
|---|---|---|---|
| `tests/unit/linux/check_k1.py` | K6「`page_size_log2` == log2(契约页大小)」（boot info 字段 `bootinfo3.6`） | 属（页大小），但**不是阶段判据** | 断言对象是**交接块里的字段**，不是内核分页行为：K1 查「hmon 交来的页大小字段对不对」，K3 门控 B2 查「新镜像自己的 `.config` 页几何 == 契约」（同一契约条目、不同载体），互不取代、也不冲突 |
| `tests/unit/linux/check_k1.py` | K11 阶段序（`STAGE_ANCHORS` 含 `ptw-announce`/`table-build`/`install`/`post-switch` 四段 + `ONE_SHOT` 里 10 条 `K1 ptw *` 行：`vec`/`ids`/`pre`/`map`/`post`/`new`/`text`/`boot`/`mark`/`done`） | 属（页表/PTW），但**是 K1 的出口判据** | K1 判「内核自建一张表、切换后仍能执行、且阶段各一次有序」；K3 的 M/T 组判「表项字段与失效命令语义（L2 表、`tlb_control`、ASID）」，对象不同（K1 是 RAM 超页的一次切换，K3 是两级表与 TLB 接口），且 K3 镜像必须重新满足 K1 的全部入口前提 |
| `tests/unit/linux/check_k2.py` | X9「自报的 `CFXMEM`/`ILLI` 不落 guest 段（与自检点可区分）」 | 属（退出码分段），与 K3 X 组同源但**对象不同** | X9 判**内核自报的四个预测码**（`spec/Kaiwu §7.1` 派生的自证）；K3 的 X 组判**实测 rc** 与 K3 自检码全集，两者同源不同物：删掉 X9 会让「内核自报值与 spec 一致」这条消失，而 K3 不检查内核的自报预测 |

**机械断言**：`check-linux-k5` 的 R 组按本节锚点核对四处一致 —— 新文案存在、旧文案不存在、替代判据指向 check-linux-k5 的 S/G 组、本节有记录；任一不一致即红（可达 FAIL：`--inject` 的退役文案回潮路把旧文案加回 `k4_fork_probe.py`；K3 收口门控本身已随 K3 阶段退役，见 §4a.2）。

### 4a.2 `m14-linux-029`（K5 收口）的退役记录

K5 收口门控 `check-linux-k5` 落地后，「用户态还没闭环 / K3 还是最后阶段」时成立的断言与文案按 §4a 三态处置；同时按用户
2026-11-20 裁定（「内核开发每进展一个阶段，原有阶段的测试随时可以退役」）**整体退役 K3 阶段**。

| 门控 / 位置 | 断言或文案（锚点） | 处置 | 新文案 / 替代判据 |
|---|---|---|---|
| `tests/unit/linux/k4_fork_probe.py` | `F3 已移 017`（F3 的 init/栈判据被推迟） | 改限定语 | `F3 的替代判据 = check-linux-k5 S 组`（`/init.musl` 真跑）；替代 = check-linux-k5 S 组 |
| `tests/unit/linux/k4_fork_probe.py` | `无 017 的 switch_to`（以「没有第二次切换」证明边界） | 改限定语 | `本镜像按 K4 自己的边界判据停在 K4 边界`；替代 = check-linux-k5 C/G 组（用户任务与线程真被调度） |
| `tests/unit/linux/k4_stack_probe.py` | `the vehicle the task book allows while the U-mode closure of m14-linux-016/017 is still open` | 改限定语 | 「每个『没有增长』用例都以具名终止结束，故仍用 supv 车辆；用户态车辆是 K5 的 s1/s6」；替代 = check-linux-k5 G 组 |
| `tests/unit/linux/check_k2.py` | `neither K3 probe may leak in`（镜像切片注释） | 改限定语 | `no milestone probe may leak in`；替代 = check-linux-k5 各组的镜像切片（K3 已退役） |
| `components/linux/patches/arch/dadao/Kconfig.debug.patch` | `A real user process pressing on its stack needs the U-mode closure of …` | 改限定语 | 「用户进程压栈是 K5 收口的（s1/s6）；不增长的用例仍在此具名收尾」；替代 = check-linux-k5 G 组 |
| `tests/unit/linux/check_k1.py` / `check_k2.py` | §4a.1 的「替代判据 = check-linux-k3 F 组」 | 改限定语（再指向） | 「替代判据 = check-linux-k5 S/G 组」；替代 = check-linux-k5 S/G 组 |
| `tests/unit/linux/check_k3.py`、`k3_page_probe.py`、`k3_pt_probe.py`、`k3_{pf,pt}_selftest.c`、`make check-linux-k3` | 整个 K3 阶段 | 删除 | 替代 = check-linux-k5 的 S/G 组（页故障通道的用户态读法）+ 各 `k4_*_probe.py`（K4 边界用例）；`contract-see §6.1.1` 与 `spec/Kaiwu §7.1` 的解析器移入 `k4_cow_probe.py` |
| `arch/dadao/mm/fault.c`（`035` 为 K3 保留） | `current->mm == NULL` 的 PA 直通窗口臂（静态 window 注册表、`vm_private_data` 取页、frag/superpage 分支） | 删除 | 替代 = 通用臂 `handle_mm_fault()`（`m14-linux-035`）+ K5 的 S/G 组；K3 已无判据依赖它 |
| `arch/dadao/Kconfig.debug`、`mm/Makefile`、`kernel/setup.c`、`include/asm/setup.h` | `DADAO_K3_PT_SELFTEST` / `DADAO_K3_PF_SELFTEST` 及其调用点 | 删除 | 替代 = K5 门控与各探针；退役符号在活树 0 命中 |

**机械断言**：`check-linux-k5` 的 R 组按上表锚点双向核对（新文案在 / 旧文案不在）、要求本节有记录并指向替代判据，且
K3 的退役符号/目标在 `Makefile`、`tests/unit/linux`、`tools/linux`、`components/linux/{series,patches}` 中 0 命中
（可达 FAIL：`--selfcheck` 的 R 组注入旧文案回潮、`--inject` 同理）。

### 4a.3 `m18-linux-003`（K6 收口）的退役记录

K6 门控 `check-linux-k6` 落地后，「用户态应用尚未跑通 / busybox 不能启动」类断言与文案按 §4a 三态处置。
审计面 = `tests/unit/linux/`（K5 及以前门控/探针）、`tools/linux/`、`components/linux/patches/`、`Makefile`，
关键词 = `用户态|busybox|未跑通|未支持|cannot start`；与本类相关的 6 处逐条列在下面（其余命中是 applet 名、
生成器注释或探针的 `user-mode` 功能陈述，不属本类）。**组件补丁本任务不改**（硬约束），故补丁内两处按「保留」记录理由，
能力收口由 `check-linux-k6` 断言。

| 位置 | 断言或文案（锚点） | 处置 | 新文案 / 替代判据 |
|---|---|---|---|
| `tests/unit/linux/k4_switch_probe.py` | `trigger: busybox cannot start for want of K5's …`（S7 的 `init.musl` 触发条件） | 改限定语 | K6 (`check-linux-k6`) is the vehicle that starts busybox's `sh`；替代 = check-linux-k6 S/C 组 |
| `tests/unit/linux/k4_switch_probe.py` | `Reaching it needs F16 (the boot stops inside kernel_init_freeable())` | 改限定语 | this probe image keeps its own `/init.musl` target（hook 只答 4 个调用）；替代 = check-linux-k6 + 本镜像自己的 `/init.musl` 判据 |
| `tests/unit/linux/k4_switch_probe.py` | S5 的 `needs the per-task user-mode frame`（umon 入口仍一个静态帧） | 保留 | 现行 `kernel/trap.S` 仍是 `dadao_umon_frame` 单帧（现场核对），S5 判据不因 K6 改变 |
| `tests/unit/linux/k4_kthread_probe.py` | `父任务此刻没有 mm（kernel_init 尚未 execve）` | 保留 | 该断言属 K4 kthread 镜像的 K3 用例，跑在 `kernel_init` execve 之前，当前仍成立 |
| `components/linux/patches/init/main.c.patch` | `the missing piece is the syscall surface`（K4 switch 探针为何改 `rdinit`） | 保留 | 组件补丁本任务不改；该句描述本镜像 hook 的边界，busybox 需要这些调用仍是真的；能力收口 = check-linux-k6 |
| `components/linux/patches/arch/dadao/kernel/k4_switch_selftest.c.patch` | `until then the honest target is /init.musl` | 保留 | 同上：hook 只答 MVP init 的四个调用，本镜像目标仍是 `/init.musl`；能力收口 = check-linux-k6 |

**机械断言**：`check-linux-k6` 的 R 组按上表核对 —— 两处改限定语的新文案在 / 旧文案不在，六条审计行均在本节留下
「位置 + 锚点 + 处置」（保留项必须出现「保留」二字），且每个改限定语行给出替代判据。可达 FAIL：
`--inject retired-back` 把旧文案加回 `k4_switch_probe.py` ⇒ R 红；`--selfcheck` 另验一次。

## 5. 每层须可达 FAIL（MUST）

- **每层的每个门控/检查必须"能失败"**：断言/用例须有**可达 FAIL 路径**（禁恒真、禁"两支写同一结果"）；覆盖类检查须**现场统计、不写死**。
- **结构断言**：除"确有命中"外，还须断言**结构**（成对 / 条数 / 行数 == 真源），防"空转绿灯"（`AGENTS.md`「验证脚本反例门控」）。
- **vacuous fail-closed**：扫描面为空（"没东西可查"）⇒ 判 **FAIL**，不得因"没命中"而报绿。
- **验收留证**：新门控须给「**注入反例 → FAIL → 还原 → 回绿**」真实输出（`cp` + md5 还原，**禁** `git checkout`/`restore`/`stash`）。

## 5a. 验收必验「合并态」（MUST，2026-11-19）

- **判据**：任务自测全绿**不等于**合入后全绿。收尾前必须把本任务 diff 套到**当前 master** 上再跑相关门控（或 `git merge master` 后在分支上跑），证明合并态 rc=0。
- **两类必查**：
  1. **共享数据文件的合并语义**：`spec/.manifests.toml` 的 `sha256` 必须**按合入后 master 侧的文件内容重算**（分支上的旧值会在合入后判红）；清单条目冲突须两行都保留。
  2. **扫全仓/扫全文的门控**：新增或改动的检查若扫描面是**全仓**或**全文（含注释）**，它会对**别人已合入的产物**判红 ⇒ 必须在合并态下跑一次，必要时把范围内的他册一并修掉（实例：`m15-idl-014` 的解码变量门控命中 `SimRISC-04`/`09` 的注释）。
- **反例**：分支自测绿、合入即红两次（`m15-idl-009` 漏提批次导致只合了批 1；`m15-idl-014` 合入后 04 注释命中）——两者都在「合并态」这一步才暴露。

## 5b. 基线必须是「本任务提交不动的引用」（MUST，2026-11-19 定为第四例）

- **规则**：证据脚本里凡是「修前/基线」比对，基线一律取**固定 commit、固定 blob 或固定 md5 常量**；**禁止**用 `HEAD`、`HEAD^`、`git log -1 -- <path>` 之类的**相对引用**。
- **为什么**：本任务的提交会移动这些引用 ⇒ 提交后断言必然恒红（或恒真），且**在分支自测时是绿的**，只有合入/提交后才暴露。
- **同类实例（截至 2026-11-19 已四例）**：`m15-testcases-016`（`git show HEAD:<旧路径>` ⇒ 空 blob）、`m15-infra-004`（`git log -1 -- <旧路径>` ⇒ 命中删除提交）、`m15-idl-011`/`003`（`git show HEAD:<spec>` 当散文基线 ⇒ 新增标记恒 0）、`m15-idl-017`（`git show HEAD:<库文件>` 当修前快照 ⇒ 提交后恒红）。
- **自检口径**：写完证据脚本后**先把改动提交、再跑一遍**；只有提交态仍 rc=0 才算通过（与「提交后仍须回绿」同源）。
- **判定「只改了本任务书」的固定写法（MUST，2026-11-20 第五/六例）**：**禁止**断言「工作树恰有 N 个未提交改动」（提交后必假 FAIL）。一律用：
  - `git show --name-only --format= HEAD` **只含本任务书**（提交态主判据）；
  - 且 `git status --porcelain -uall` **为空或仅含本任务书**（0/1 都过）；
  - 需要跨多提交时用 `git diff <固定 base>...HEAD --name-only`。
  实例：`m14-linux-036`（§8）、`m14-linux-038`（E3/E4）、`m14-linux-042`（`tree_state` 期望串 `clean(committed)` vs 实际串 `clean`，两串永不可能相等）、`m16-chipyard-013`（C9）各因此被打回一轮。**只读盘点类任务的派单提示必须显式写出这条**，否则子代理不读本规范。
- **判据的「任务书必须在改动集里」要另行处理 squash 合入后的情形**（2026-11-20，`m16-gem5-019` 残余）：`merge-base(HEAD, master)..HEAD` 在**分支已 squash 入 master 且树干净**时为空 ⇒ 若判据同时要求「改动集含本任务书」，会在收尾后假红。任务收尾后通常不再重跑证据脚本，故可接受；若要彻底稳，去掉「必须含本任务书」或用「分支包含判据」。
- **首选写法：判「本任务改了哪些文件」用「基线提交范围 ∪ 工作树」**（2026-11-20 第八例，`m16-chipyard-013` C9 实证）：即 `(merge-base(HEAD, master)..HEAD) ∪ git status --porcelain` 的路径集合必须全部落在**允许目录**内且包含本任务书。这样**未提交态、提交态、以及收尾台账单独一笔提交**三种情形都能回绿，比「工作树恰 N 项」或「HEAD 只含本任务书」都更稳（后者在台账 follow-up 提交时会误红）。
- **基线参数的缺省值不得是相对引用**（MUST，2026-11-20 第七例）：证据脚本的 `BASE_REF`/`--baseline` 之类参数**必须必填**；缺省取 `HEAD` 会让「与基线比对」退化为同源自比（恒真绿）。实例：`m15-spec-005`（`BASE_REF` 缺省 `HEAD`，注释理由「本任务不改 git 历史」不成立——`HEAD` 就是本次 WIP）。
- **断言的期望值与实际值必须同源派生**（MUST，2026-11-20）：不得一侧写死字面量、另一侧从现场取值——那样的比较要么恒真要么恒假。允许的写法是「两侧都取同一变量」或「期望为常量 0/空、实际为计数/状态行数」。

## 6. 与其它规范 / 文档的关系

- `AGENTS.md`「门控分层与触发点」= **规则 + 指针**（层名 / 触发点一句话 + 指向本规范）；**本规范 = 明细与演进规则**，二者**不重复**。
- `docs/Process-05`（里程碑 TDD）= 向量/门控的**开发方法**（L1 编码 / L2 结构 / L3 执行，**测什么**）；本规范 = **工程门控的规模分层与归属**（**怎么组织/何时跑**）——两者维度不同，`Process-05` 的 L1/L2/L3 指**测试向量层次**，本规范的 L1/L2/L3 指**门控目标层次**，**同名不同指**，引用时须写清。
- `docs/Process-01`（组件补丁）/ `Process-06`（`spec/` 保护）等**与层归属无关**；`check-patch-tree`/`check-manifests-guard` 各按其规范实现，**归属 L1**（不跑被测语义）。

## 7. 文件防护门控清单（防新增 / 防修改）

> 本节的定位：盘点 `Makefile` 里全部 `^check-[a-z0-9-]*:` 目标（现场 `grep -c "^check-[a-z0-9-]*:" Makefile` = **64** 个，另加 1 个经 `gate-locked-rule` 生成的 `check-manifests-guard`），回答三个问题——① 是否扫描文件系统、扫描面是什么；② 是否**防新增**（白名单 / 许可集 / 命名规则 / 覆盖要求）；③ 是否**防修改**（sha256 锁 / git blob / 逐字节比对 / 生成物一致性）。判据一律**读脚本源码或本规范 §1.1**，不凭门控名猜。
>
> **防新增 / 防修改**两列的取值口径（简写，详见各脚本）：
> - 防新增：`白名单`（顶层只允许既定模式）｜`命名规则`（新文件名须匹配）｜`覆盖`（新文件/载体须被某清单双向覆盖，删/漏即红）｜`结构`（目录封闭集合）｜`—`（不防新增）。
> - 防修改：`sha256 锁`（锁文件重算比对）｜`git blob`（补丁 index/内容 blob 重算）｜`逐字节`（重生成产物字节级比对）｜`一致性`（跨文件/跨载体机械核对，非哈希）｜`git 状态`（clean + base+N）｜`—`（不防修改）。
>
> 清单行数 = 现场 `grep -c` 值 **64** + `gate-locked-rule` 生成的 `check-manifests-guard` **1** = **65** 行；删/增门控时两处同笔更新。不在此列的还有：`check`/`check-modules`/`check-full`/`check-lit*`/`check-inst-asm`/`check-arch*`/`check-unit*`/`check-tset-*`/`test-*`/`check-linux-k0..k3` 等 —— 它们是 `GATE_LOCKED_TARGETS` 经 `gate-locked-rule` 生成的 `_locked-*` 包装目标（真源在 `_locked-check`/`_locked-check-modules`/`_locked-check-full`），**不匹配** `^check-*:`，故不在本清单；其防新增/防修改语义由成员门控承担。

| 门控 | 层级 | 扫描面 | 防新增 | 防修改 | 判据出处 | 缺口 |
|---|---|---|---|---|---|---|
| `check-wuming-cycles` | 按需（独立，不入 L1） | `docs/core-wuming-cycle-model.md` + `contracts/wuming-cycles.yaml` + gem5 源 `wuming_cycles.{hh,cc}` | 覆盖（264 id 全覆盖） | 逐字节（重新解析比对） | `tools/gem5/gen_wuming_cycles.py:22-24` | 不入 L1，仅按需；周期文档非只读锁 |
| `check-linux-toolchain` | L1 | `tools/linux/toolchain_matrix.json` + 能力探针 | 覆盖（矩阵行集合==覆盖表） | 一致性（declared==measured==实测） | `tests/unit/linux/check_toolchain.py`（矩阵行集合断言） | 无白名单 |
| `check-linux-boot-contract` | L1 | `spec/Kaiwu §6.3` ↔ `contract-linux-boot` ↔ `contracts/linux-boot.yaml` | — | 一致性（三方逐字段） | `tests/unit/linux/check_boot_contract.py` | 无 |
| `check-config-pins` | L1 | `components/linux/patches/arch/dadao/Kconfig.debug.patch` + `tools/linux/*.py` | 覆盖（每个切片脚本的 `CONFIG_PINS` 键集合 == Kconfig 全集；调 `apply_config_lines` 的脚本必须有该字典） | 一致性（键集合 / int 的 `depends on` 可见性 / `IMAGE_CONFIG`·`IMAGE_ON` 期望表 == 钉子 / 无写死切片） | `tests/unit/linux/check_config_pins.py`（`run_checks`/`audit_scripts`） | 只扫 `tools/linux/`；不核内核侧 Kconfig 语义、不跑构建 |
| `check-spec-drift` | L1 | `.tao/contracts/contract-*.md` + `README.md` 版本表 + `.tao/adr/` | — | 一致性（版本号/ADR 状态） | `tools/infra/check_spec_drift.py:5-11` | 只核版本头与 ADR 状态，**不核契约正文内容** |
| `check-spec-numbering` | L1 | `spec/*.md` 标题 | — | 一致性（章节号结构） | `tools/spec/check_numbering.py:5-23` | 无 |
| `check-spec-changelog` | L1 | `spec/*.md` 附录变更记录 | — | 一致性（逆序/册头一致/无表格） | `tools/spec/check_spec_changelog.py:8-23` | 无 |
| `check-spec-purity` | L1 | `spec/*.md` 禁用词 | **黑名单**（禁用词表，拦项目痕迹混入规范；非新增白名单） | — | `tools/spec/check_spec_purity.py:38-45` | 只拦禁用词，**不拦新增 spec 册**（见 §7.1 ③） |
| `check-spec-cite-targets` | L1 | `spec_cite` 目标（opcodes.yaml/测试向量） | — | 一致性（书+目标存在） | `tools/spec/check_spec_cite_targets.py:39-45` | 无 |
| `check-spec-archive` | 里程碑 | `.tao/archive/SimRISC-*/` | 覆盖（声明版本目录必须存在） | —（只校验存在性与文件集） | `tools/spec/check_spec_archive.py:7-17` | 内容不校验（由 verify 补） |
| `check-spec-archive-verify` | 里程碑 | `.tao/archive/SimRISC-*/` 内容 | — | sha256 锁（逐文件 + 组合） | `tools/spec/gen_spec_archive.py:430-487` | 无 |
| `check-patch-tree` | L1 | `components/*/patches` + `series` | 白名单（一文件一补丁/目标路径唯一/patches 纯镜像） | git blob（断言⑥内容一致 + ⑦⑧⑨） | `tools/infra/check_patch_tree.py:7-35,379-431` | 断言④⑥ 需 `.work/source` 在盘才跑 |
| `check-index-blobs` | L1 | `components/*/patches/*.patch` 的 new-file index | — | git blob（`hash-object --stdin` 重算） | `tools/infra/check_index_blobs.py:124-132` | 只覆盖 new-file，修改类 patch 跳过 |
| `check-source-state` | 按需（E7，不入 L1） | `.work/source/<name>` | — | git 状态（clean + base+expected） | `tools/infra/check_patch_tree.py:489-544` | 不入 L1，手动跑 |
| `check-tasks` | 报告（默认 rc=0；`check-tasks --strict` 由 `check-milestone` 与 `check-full` 调用，漏收尾即红） | `.tao/tasks/**` | — | 一致性（任务书↔台账/收尾） | `tools/infra/check_tasks.py:11-31` | 默认不阻断，`--strict` 才拦 |
| `check-run-artifacts` | L1 | `tests/ee-user` 驱动 + `.work/tests/**` + `.work/log/**` | 命名规则（运行目录三件套 + log 新名） | —（meta 的 sha256 只核非空） | `tools/infra/check_run_artifacts.py:6-25,299-347` | 无 |
| `check-test-reports` | L1 | `docs/TestReports/*.md` | 命名规则（`<M>-主题`；无二级子目录） | —（快照首行标记） | `tools/infra/check_test_reports.py:44-47` | 无 |
| `check-temp-dirs` | L1 | `/tmp/opencode` + `$TMPDIR/opencode` | —（只报陈旧、不删） | — | `tools/infra/check_temp_dirs.py:11-26` | 只报告不删除；不扫仓库内 |
| `check-writer-guards` | L1 | 临时树 stub 二进制 | — | 一致性（读方 md5 结束≠启动 FAIL） | `tools/infra/check_writer_guards.py:11-38` | 自测型，不扫真实 registry |
| `check-disk` | 按需（运维） | 文件系统占用 | — | — | `tools/infra/check_disk.py:2-13` | 运维守卫，非门控 |
| `check-milestone` | 里程碑 | 归档 + 台账 + L3 报告 + 同步异常 | 覆盖（台账任务号必须存在） | sha256 锁（归档内容）+ 一致性（报告） | `Makefile:1351` | 收尾专项 |
| `check-sync-nonmaskable` | 里程碑 | `spec/DADAO-12/22/23` 异常原因表 | — | 一致性（异步源白名单） | `tools/spec/check_sync_nonmaskable.py:41-45` | 无 |
| `check-spec-refs` | L1 | `.tao/contracts/contract-*.md` 的 spec 引用 | — | 一致性（引用可解析） | `tools/infra/check_spec_refs.py:4-25` | 无 |
| `check-knowledge-refs` | L1 | `AGENTS.md`/`spec`/`knowledge`/`tasks`/`contracts` 的 `.work/**` 引用 | 白名单（具体 `.work/**` 引用一律 FAIL） | —（悬空引用） | `tools/infra/check_knowledge_refs.py:12-52` | 无 |
| `check-manifests-guard` | L1 | 全仓 `.manifests.toml` 所在目录（`manifests/dir-guard-roots.toml` 登记：`spec/`、`idl/`、`.tao/`、`.tao/knowledge/`、`components/`） | 双向白名单（直接子文件 == `files`、直接子目录 == `subdirs`） | sha256 锁（条目可带）+ 递归（`recursive=true` 单向 ⊆） | `tools/infra/check_manifests_guard.py:89-236` | 清单自身可被改（加/删条目不红）⇒ 变更依据看 `git log`；`owner` 只打印 |
| `check-idl-sync` | L1 | `idl/*.idl` + `spec/SimRISC-*` 的 IDL 标记段 | 覆盖（源 operation ↔ 落点双向）+ 命名规则（`SimRISC-NN.idl`、id ∈ `opcodes.yaml`） | 逐字节（重渲染比对） | `idl/render.py`（`render_all`/`run`） | 只核标记段内的块；标记外的散文不核 |
| `check-idl-parse` | L1 | `idl/*.idl` + `idl/lib/*.idl`（13 个源） | 覆盖（每条 operation 都有构造签名）+ 命名规则（`# id:` 全局唯一、与 `opcodes.yaml` 对账）+ 拒绝集（子集外构造必须报错） | 一致性（AST 签名 ⇔ fixture）+ 接受集（合法样例必须通过） | `idl/idl_parser.py:check` | 只核语法，不核语义；fixture 可被 `--update` 改（变更依据看 `git log`） |
| `check-contracts-dir` | L1 | `.tao/contracts/` + `contracts/` 顶层 | 白名单（glob + 显式名） | — | `tools/infra/check_contracts_dir.py:41-50` | **子目录不限** |
| `check-syscall-abi` | L1 | musl/QEMU/gem5 参数寄存器组表 + `syscall.tbl` | — | sha256 锁（syscall.tbl）+ 一致性（四载体逐项） | `tools/qemu/check_syscall_abi.py:6-40` | 无 |
| `check-musl-freshness` | L1 | musl 构建树 + 安装根 | — | sha256 锁 + 戳记（源/toolchain/builtins） | `tools/infra/check_musl_freshness.py:16-36,159` | 无 |
| `check-builtins-freshness` | L1 | compiler-rt 归档三副本 + sidecar | — | sha256 锁 + 逐成员 `.c.o` | `tools/infra/check_builtins_freshness.py:27-48` | 无 |
| `check-install-tools` | 按需（install-host 收尾） | 安装根 `HOST_LLVM_TOOLS` + symlinks | — | sha256（`--sha`，默认 size+version） | `tools/infra/check_install_tools.py:21-43` | 默认只比 size，`--sha` 按需 |
| `check-milestones-fresh` | L1 | `.tao/knowledge/milestones*.md` | 覆盖（三表并集覆盖任务书） | 一致性（分类/状态/格式） | `tools/infra/check_milestones_fresh.py:36-64` | 无 |
| `check-archive` | L1 | `.tao/archive/M<i>/` | 白名单（三件套 + 模块子目录封闭） | —（结构） | `tools/infra/check_archive.py:7-27,51` | 无 |
| `check-component-changelog` | L1 | `components/*/changelog.md` + `tests/tset/*/changelog.md` | 覆盖（带补丁集套件必须有） | —（形态） | `tools/infra/check_component_changelog.py:10-17,42` | 无 |
| `check-contracts-pending` | L1 | `.tao/contracts/**` | — | —（待定标记须带 ADR/ISS 指针） | `tools/infra/check_contracts_pending.py:43-50` | 无 |
| `check-contract-relocs` | L1 | `contract-elf §2.2` ↔ `contract-dynlink §4.3` | — | 一致性（两表逐行） | `tools/infra/check_contract_relocs.py:9-24` | 无 |
| `check-cfx-aliases` | L1 | `.tao/contracts/contract-cfx-aliases.md` | — | 逐字节（重生成比对） | `tools/spec/check_cfx_aliases.py:2-12` | 无 |
| `check-cfx-alias-table` | L1 | `contracts/cfx-aliases.txt` | — | 逐字节（spec 投影） | `tools/llvm/gen_cfx_alias_table.py:37-41` | 无 |
| `check-cfx-alias-install` | 按需（需 install-host） | 三副本（源/构建树/安装根） | — | sha256 锁（逐字节） | `tools/llvm/check_cfx_alias_install.py:9-19,46-51` | 需 install-host，不入 L1 |
| `check-cfx-vectors` | L1 | cfx MC 编码向量 | — | 一致性（独立 oracle 重派生） | `tests/unit/llvm/lit/MC/DADAO/validate_cfx_vectors.py` | 无 |
| `check-dirs` | L1 | `manifests/install-dirs.lock.toml` + 版本文件 symlink 前缀 | —（路径守卫） | — | `tools/infra/check_dirs.py:4-16,38-46` | 无 |
| `check-no-residue` | L1 | `git ls-files --others` 残留 pattern | 命名规则（`*_tmp*`/`*_gate*`/`*.orig`/`*.rej`） | — | `tools/infra/check_dirs.py:186-238` | 白名单仅 `.tao/tasks`/`.work` |
| `check-components` | L1 | 安装根 `llc`/`clang`/`qemu` 可用性 | — | — | `tools/infra/check_components.py:7-13` | 无 |
| `check-width-sizes` | L1 | 编译探针（64 位 + DWARF64） | — | — | `tools/llvm/check-width-sizes.py:15-33` | 无 |
| `check-code-range` | L1 | 合成 fixture ELF | — | — | `tools/infra/check_code_range.py:44-45` | 无 |
| `check-runner-reap` | L1 | 合成驱动 + 伪 qemu | — | — | `tools/testcases/check_runner_reap.py:4-21` | 无 |
| `check-asm-list` | L1 | `spec/*.md` 嵌入表 vs `gen_asm_list.py` | — | 逐字节（重生成比对） | `tools/spec/check_asm_list_consistency.py:2-8` | 无 |
| `check-asm-list-drift` | L1 | `.tao/contracts/contract-asm-list.md` | — | 逐字节 | `tools/spec/check_asm_list_drift.py:4-15,63-68` | 无 |
| `check-asm-prose` | L1 | `spec`/`docs`/`contract`/`adr` 代码块 | — | 一致性（旧格式检测） | `tools/spec/check_asm_prose.py:11-39` | 无 |
| `check-spec-codeblocks` | L1 | `spec/**/*.md` ```simrisc 代码块 | — | 一致性（mnemonic/operand 计数） | `tools/spec/check_spec_codeblocks.py:19-40` | 无 |
| `check-legality-drift` | L1 | `spec/SimRISC-01..12` LEGALITY 块 | — | 逐字节（整块比对） | `tools/spec/check_legality_drift.py:9-16` | 无 |
| `check-legality-invariants` | L1 | `contracts/*.yaml` | — | 一致性（规则改名旧 id 0 命中） | `tools/spec/check_legality_invariants.py:6-24,57-59` | 无 |
| `check-interface` | L1 | 跨模块 ADR/contract/patch 接口 | — | 一致性（内联期望值） | `tools/infra/check_interface_alignment.py:4-14` | 无 |
| `check-instrinfo` | L1 | `DADAOInstrInfo*.td.patch` ↔ `opcodes.yaml` | — | 一致性（编码身份 join） | `tools/llvm/validate_instrinfo.py:26-39` | 无 |
| `check-isa-coverage` | L1 | 覆盖矩阵 `tsv`/`md` | — | 逐字节（重派生比对） | `tools/llvm/gen_isa_coverage.py:33-34` | 无 |
| `check-case-ledger` | L1 | `tests/case-ledger.tsv` | —（删除哨兵） | 逐字节（身份清单） | `tools/infra/check_case_ledger.py:13-27,137-165` | 无 |
| `check-tests-index` | L1 | `tests/*.yaml` + 载体 | 白名单（scope 合法 / 载体↔索引双向 / YAML 残留禁止 / 非 id 逐文件登记） | — | `tools/testcases/check_tests_index.py:7-35,421-494` | 无 |
| `check-inst-macro-scope` | L1 | `tests/inst/**` | 白名单（宏三层作用域 / 死宏 0） | — | `tools/testcases/check_inst_macro_scope.py:7-38` | 无 |
| `check-decodetree-repro` | L1 | `Makefile` build-qemu recipe + decodetree 两 seed | — | 一致性（PYTHONHASHSEED 可复现） | `tools/qemu/check_decodetree_repro.py:2-19` | 无 |
| `check-qemu-forms` | L1 | `components/qemu/patches` `helper.c.patch` | — | 一致性（符号 0 命中哨兵） | `tools/qemu/semantics_gate.py:28-34` | 无 |
| `check-scope` | L1 | `opcodes.yaml` scope 分区 | — | 一致性（分区不变量） | `tools/spec/check_scope.py:6-19` | 无 |
| `check-rule-refs` | L1 | `opcodes.yaml` ↔ `legality_rules.yaml` | — | 一致性（双向 + 豁免文件） | `tools/spec/check_rule_refs.py:4-17` | 无 |
| `check-fp-contract` | L1 | `fp_semantics.yaml` ↔ `opcodes.yaml` ↔ `contract-fp.md` | — | 一致性（三方 + 规则派生） | `tools/spec/check_fp_contract.py:4-22` | 无 |
| `check-night-report` | 按需诊断（观测） | `.dadao/tests/night/<date>/` 三件套 | — | 一致性（rc==0，不阻断收口） | `tools/testcases/check_night_report.py:8-20` | 观测不阻断 |
| `check-l3-report` | 里程碑 | `.dadao/tests/l3/<UTC>/` 三件套 | — | 一致性（rc + exit marker 防伪造） | `tools/testcases/check_l3_report.py:10-23` | 无 |

### 7.1 缺口分析（本清单核心产出）

> 只给事实与缺口，**不提改造方案**（改造另立任务）。

**① 无白名单（防新增）目录清单** —— 逐个目录判定「是否被某门控约束只能放什么」：

- `tests/` —— **部分约束**：`check-tests-index` 约束 `tests/*.yaml` 的 scope 合法、载体↔索引双向、`tests/inst/` 下 YAML 残留禁止、非 id 载体逐文件登记；`check-inst-macro-scope` 约束 `tests/inst/**` 宏三层作用域。但 **`tests/` 下新增任意新子目录/新文件（非索引条目、非载体后缀）无白名单**。
- `tools/` —— **无白名单**：`check-dirs` 只扫 symlink 前缀违规，`check-no-residue` 只拦残留 pattern，`compileall` 只证语法。新增 `tools/xxx/foo.py` 不被任何门控拦截。「脚本入仓须在模块 `README.md` 登记」只是 `AGENTS.md` 规则，**无机械门控**。
- `.tao/tasks/` —— **无白名单**（可任意新增任务书），但 `check-milestones-fresh` 的 **A2 覆盖**会拦「有任务书但未入台账三表」的新任务书；`.tao/adr/` 仅做悬空引用解析。
- `docs/` —— **无白名单**：`check-test-reports` 只约束 `docs/TestReports/`；`docs/` 其余（Process-0x、DDLN、`core-wuming-cycle-model.md` 等）新增文件无门控。
- `.tao/` —— **部分约束**：`knowledge/`/`contracts/` 顶层白名单 + `archive/M<i>/` 结构封闭（`m15-infra-005` 起 `.tao/` 与 `.tao/knowledge/` 顶层改由 `.manifests.toml` 双向约束，`knowledge/` 白名单脚本已删）；但 **`.tao/adr/` 与 `.tao/tasks/` 无白名单**（任务书命名由 `check-tasks` 报告型 + `check-milestones-fresh` 覆盖承担，不拦命名）。
- `components/` —— **无白名单**：`check-patch-tree` 只约束 `patches/` 纯镜像 + `series`，`check-component-changelog` 只约束 `changelog.md` 形态，`manifest-check` 只查 `patch_dir`/`series` 存在。**`components/<name>/` 下新增任意文件（非补丁、非 changelog）无门控**。
- `manifests/` —— **无白名单**：`manifest-check` 校验 `install-dirs`/`components`/`references` 内容，但**不防新增 `manifests/*.toml`**。
- `contracts/` —— **顶层有白名单**（`*.yaml`/`README.md`/`cfx-aliases.txt`），但 **`contracts/` 子目录不限**。

**② 只靠「人不改」（无哈希/blob 校验）的受保护文件清单**：

- `manifests/reference-snapshots.toml` —— 记录每份参考材料的 `sha256`，但**全仓无任何门控核对它**（`grep -rn "reference-snapshots" Makefile tools/` 零命中）——连「人不改」都不如：改了也不会红。
- `manifests/components.lock.toml` 的 `commit` / `manifests/references.lock.toml` 的 `head` —— `manifest_check.py:45,110` 只查 40-hex 格式，**不核对实际 fetch 到的 commit**。
- `manifests/install-dirs.lock.toml` —— `check_dirs.py:34-73` 只校验键值 + 相对路径，无 hash。
- `contracts/*.yaml`（`opcodes.yaml` 等编码真源）—— **无 sha256 锁**；防漂移靠多路一致性门控（`check-scope`/`check-instrinfo`/`check-isa-coverage`/`check-fp-contract`/`check-rule-refs`）间接兜住，但 `opcodes.yaml` 自身**无逐字节锁**。
- `.tao/contracts/contract-*.md`（人读契约正文）—— `check-spec-drift` 只核版本头/ADR 状态（`check_spec_drift.py:5-11`），**不核正文内容**。
- `.tao/adr/*.md` —— 无 hash、无白名单。
- `docs/*.md`（Process-0x / DDLN）—— 无 hash、无白名单。

**③ 冗余与空白（各 ≥1 例）**：

- **冗余**：
  - 汇编指令表**同源三锁**：`check-asm-list`（spec 嵌入表逐字节） + `check-asm-list-drift`（`contract-asm-list.md` 逐字节） + `gen_asm_list.py` 都从 `opcodes.yaml` 投影同一份表 —— 同一数据三条门控。
  - cfx 别名**同源三层**：`check-cfx-aliases`（`contract-cfx-aliases.md` 逐字节） + `check-cfx-alias-table`（`cfx-aliases.txt` 逐字节） + `check-cfx-alias-install`（三副本 sha256）都从同一 spec 投影同一份别名 —— 三层锁同一数据。
- **空白**：
  - 「新增 `.py`/工具脚本必须登记」**无机械门控**（`tools/` 无白名单、无 README 登记断言）。
  - `manifests/reference-snapshots.toml` 的 `sha256` **无任何门控核对**（见 ②）。
  - ~~`spec/` 新增册**逃锁**~~（**已关闭**，`m15-infra-005`）：原只读册门控只重算锁内条目的 sha256、无反向断言，新增一册 `spec/SimRISC-13-*.md` 不红；现由 `check-manifests-guard` 双向集合（`spec/.manifests.toml`）覆盖——新增 / 删除 / 改 `sha256` 三类均红（`--self-test` 六类注入）。
