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
| **L2 四 scope smoke** | `make check-modules` | 四个固定 scope 的 **smoke** 集（`Process-09 §8`）：`check-inst-smoke` + `check-arch-smoke` + `check-unit` + `check-tset-{libc,llvm,embench}-smoke`。**不含** FP 探针（2026-10-27 用户裁定「L2 只保留四 scope smoke」） | 几十 ~ 几百秒 |
| **L3 全量** | `make check-full` | **inst/arch/unit 全量 + FP 探针 + 集成链**：`check-inst`（`tests/inst` **全量**载体：`base` + `rol`/`atomics`/`clmul`；`rev`/`bitcnt` 未纳入，见 `tests/inst/inventory.md`「门控覆盖」）+ `check-arch`（全 cfx）+ `check-unit-full`（= `check-unit` + `check-lit-full`，见下）+ **4 个 FP 探针**（`fp` 身份无向量 ⇒ 探针是其唯一语义覆盖）+ `test-m6`（全量 lit 生成档 + ir-lli + Embench E2E）。**tset 不直接列出**：smoke 只在 L2、full 只在回归运行；`test-m6` 的 Embench E2E 属集成步骤，**不算** tset smoke 重复（§4；`TESTCASES-082t`）。运行由 `tools/testcases/l3_run.py` 逐成员执行（成员清单真源 = `l3_run.DEFAULT_MEMBERS`），并写只读报告 `<test-artifacts>/l3/<YYYYMMDDTHHMMSSZ>/`（`manifest.tsv`/`meta.json`/`run.log`，与回归运行同格式）| 几百 ~ 几千秒 |
| **回归运行（非三层之一）** | `make night-run` | `tset` full ×3（各 static+dynamic）+ 长 `check-arch`；结果只落只读报告 `.dadao/tests/night/<date>/`，按需消费（`check-night-report`，**观测口径，不阻断收口**）；**独立锁 `night.lock`**（不占 `gate.lock`，不阻断 L1/L2/L3，`NIGHT_LOCK`）；触发点 = 队列空档，`setsid nohup`（`Process-09 §8`） | 小时级 |
| **按需（模块完整）** | 各 `test-*`/`check-*` **单独调** | 模块**全量**、profiling | 不定 |

- **L1 判据**：**只看"仓库是否完整 + 组件是否可用"**，**不得**依赖被测语义的执行结果（那是 L2/L3）。
- **默认 `make check` = 仅 L1**：`check-inst`（全量语义，原 `check-qemu-semantics`）与
  `check-lit`（受控子集）**移出** L1（`INFRA-058t`）。
- **回到 L1 的两条（`TESTCASES-076t`）**：`check-interface`（跨模块静态一致性）与
  `check-code-range`（合成 fixture 自检）**不跑被测语义** ⇒ 按 §3 判据 1 归 L1。
- **层边界（耗时带）的实测校验**（承接原设计稿 `.tao/archive/M7/m7-retrospective.md` 附录 A §五「第 0 步」待办）：第 0 步：**逐门控计时**（`make -n` 不适用；逐目标 `time`），据实测确定 L1/L2/L3 边界与是否值得拆。

### 1.1 门控登记：契约口径与里程碑收尾（2026-10-17）

| 目标 | 层 | 判据（机械） |
|---|---|---|
| `make check-contracts-pending` | **L1** | `.tao/contracts/**` 出现「待…定 / 待裁定 / TODO / TBD」标记的行，须同行含 `ADR-<n>` / `ISS-<n>` 指针（只认带编号落点）；行内代码跨度与「」引用不计。计数现场统计。 |
| `make check-contract-relocs` | **L1** | `contract-elf.md §2.2` 与 `contract-dynlink.md §4.3` 的**现行表**逐行比对（类型号 ↔ 名）；只解析两小节内的表格行 ⇒ 历史注记不参与；附加自洽 = 表非空 / 号名唯一 / 号 0 起密集。 |
| `make check-milestones-fresh` | **L1** | **双台账**（`m12-infra-001`，用户 2026-11-08「从 M12 开始……milestones.md 也改为 milestones-m12.md」）：`milestones.md` = M11 及以前、`milestones-m12.md` = M12 起；M11 台账**必有**、M12 台账**存在则校验**（不存在 ⇒ 打印跳过，M11 仍校验 ⇒ 非 vacuous），任一红即红。任务号接受旧 `PREFIX-nnn<suffix>` 与新 `mNN-<module>-NNNN`（3–4 位、无后缀）两种。三张表（**表位置即状态**、无状态列）：①「待开始（未开工）」3 格 `| 编号 | 预估时间 | 一句改动 |` —— 任务书状态须为 `待开始` 且**不得含派单时间**（未派单）；②「进行中（已派单：待开始 / 待验收 / 待返工）」4 格 `| 编号 | 派单时间 | 预估时间 | 一句改动 |` —— 任务书状态 ∈ {`待开始`,`待验收`,`待返工`} 且**派单时间必填**（`YYYY-MM-DD HH:MM`；`待开始` 在此表表示「已派单、实现中」）；①② 预估时间匹配 `N h` / `N–M h` / `N 天` / `N–M 天` / `min`；不判次序。③「已验证」3 格 `| 编号 | 完成时间 | 一句改动 |` —— 任务书状态须为 `已验证`；完成时间 `YYYY-MM-DD HH:MM` 且**不得带 `（登记）`**；按完成时间倒序（同时间按编号升序）。三表一句改动均 ≤120 字符；任何表**不得出现状态列/状态值**；编号不重复且不得跨表重复；三表并集覆盖活 `t` 册 + `INTEG-*m` 册所列号 + 正文号（已归档号豁免，全仓无册的悬空号 FAIL）。三标题 / 表头缺失、三表皆空 ⇒ FAIL。`--self-test` 内置十四类注入（进行中缺派单时间 / 待开始行带派单时间 / 派单时间格式非法 / 状态映射不符 / 预估格式非法 / 完成时间带（登记）/ 同号跨表 / 已验证乱序 / 状态列 / 三表次序 / 覆盖缺失 / 缺小节 / 超长 / `.work` 路径）。**R1 台账一致性**（`INFRA-145t`）：`git worktree list` 检出的任务分支或**未合并**本地任务分支（已并入 `master`/`main` 豁免）⇒ 该任务号**不得**在「待开始」、须在「进行中」（册已 `已验证` 则须在「已验证」表），未列入任何表 ⇒ FAIL，逐条指名 `L??`；非 git 树（`--root` 自检树）打印跳过；`--self-test` 另含 R1 六类真 git 临时仓库用例。**A6 双台账路由**：每份台账取其头 `项目里程碑 = M<n>` 断言（缺失 ⇒ FAIL），任务号按任务书 `**项目里程碑**` 字段（无活册的新格式号按 `mNN-` 前缀）定所属台账；行/正文号落在**非所属**台账 ⇒ FAIL（跨台账错放）；归档册豁免；`--file PATH` 选台账（默认 `milestones.md`）。 |
| `make check-archive` | **L1** | `.tao/archive/M<i>/` 结构与册字段（规则 = `docs/Process-04` §5–§8）：① 三件套非空；② 根文件白名单仅三件套（任务书含 m 一律放模块子目录）；③ 子目录只允许 6 个模块名（`notes/` 即 FAIL）；④ 每册 `**状态**` ∈ {`已验证`,`里程碑`}、`**项目里程碑**` 里程碑号 == 归档号；⑤ §1 模块计数 == 模块目录实际册数（现场统计）；⑥ 流水 ID 集合 == `t` 册集合或 `t`+`m` 集合（M7+；M1–M6 日期列 `changelog` 只要求表格非空）、行状态 == 任务书状态；⑦ README 有 MEMORY/指针节、M9 起有终局证据；⑧ `issues-closed.md` 非空壳。`--self-test` 13 类注入（各自可达 FAIL）；`INFRA-117t` 归一后**严格默认**（无过渡 flag），现文全归档 rc=0。 |
| `make check-spec-archive` | **里程碑收尾专项**（随 `check-milestone`；**不入 L1**） | 册头 ∪ 附录声明的每个版本须有 `.tao/archive/SimRISC-<ver>/`：A1 目录存在；A2 目录非空且含 `SimRISC-00*`；A3 文件数 = 派生清单；A4 反向（磁盘 ⊆ 清单）⇒ 双向；**只校验存在性与文件集、不校验内容**；`-rc` 不参与。判定归 `tools/spec/check_spec_archive.py`（判据未改，仅改触发层）。 |
| `make check-spec-archive-verify` | **里程碑收尾专项**（随 `check-milestone`；**不入 L1**） | 归档**内容**：以各目录 `PROVENANCE.md` 的「快照提交」为锚，逐文件 sha256 与该提交树全等 + 「版本组合 sha256」= 按表重算值（拒绝子串/前缀匹配）；无 `PROVENANCE.md` 的既有目录回落派生快照；`-rc` 打印 SKIP。判定归 `tools/spec/gen_spec_archive.py --verify`（判据未改，仅接线）。 |
| `make check-milestone` | **L2 层 / 里程碑收尾专项**（按需；**不入** `check-modules`） | 先跑 `check-spec-archive` + `check-spec-archive-verify`（归档结构 + 内容 sha）+ `check-l3-report`（L3 报告存在性/结构/结果）；**回归运行报告不入本目标**（观测，按需 `check-night-report`，`INFRA-126t`）；再：**里程碑台账**（自动发现 `.tao/knowledge/milestones*.md`：`milestones.md` / `milestones-m12.md` / `milestones-m13.md`，或用 `--file` 指定）逐本校验：须有 `项目里程碑 = M<n>` 断言（否则 vacuous FAIL），台账列出的任务号须在 `.tao/tasks/**` 或 `.tao/archive/**` 真实存在（台账零任务号 ⇒ vacuous FAIL）；并接 `check_tasks.py --strict`（漏收尾 = 0）。**核验册（`m` 册）机制已删除**（用户 2026-11-10：可删掉核验册机制；2026-11-08 起 M11 不建 m 册、M12 编号 `mNN-<module>-<NNNN>`）⇒ 不再做册识别、旧册顶替与册内号检查。 |
| `make check-knowledge-dir` | **L1** | `.tao/knowledge/` **顶层**只允许显式白名单文件（台账集合）与子目录（子目录不限）；白名单外文件 / 目录缺失 / 顶层空（vacuous）⇒ FAIL。计数现场统计。判定归 `tools/infra/check_knowledge_dir.py`（判据未改，仅改触发层：`INFRA-112t` 回 L1；2026-10-26 曾随 `SPEC-176t` 临移到 `check-milestone`）。 |
| `make check-syscall-abi` | **L1** | syscall 参数银行表的三载体（musl `__dadao_argmask` / `src/thread/dadao/syscall_cp.s` 派发 / QEMU `cpu_loop.c:dadao_argmask`）逐项一致（号→掩码全等；asm 子集逐号相等 + 每个 `.Lm<mask>` 块的 `rd2rb`/`rd2rd` 条数 = 掩码位值）+ 完整性（musl 能发出的 syscall 名 ⊆ 表，空表 vacuous FAIL）。工作树在则读树，否则读 `components/**` 补丁（新克隆可跑）；完整性/audit 两项在无 musl/qemu 检出时 SKIP 并打印。 |
| `make check-musl-freshness` | **L1** | 安装根 `libc.so` 必须由**当前** musl 源 + 工具链构建：`build_musl.py` 成功构建后落 `obj/.dadao-musl-source-stamp`（全树内容 sha256）与 `obj/.dadao-toolchain-stamp`；门控比对两戳记 + 安装副本与构建产物 sha256 一致 + `ld-musl-dadao.so.1` 符号链接指向 + **`obj/.dadao-builtins-stamp`**（`libc.so` 的 `LIBCC` 归档内容 sha256，`ISS-293`：DSO 内嵌 builtins，归档变则须 relink）。任一项不符 ⇒ FAIL（提示 `make build-musl-shared`）。无构建树 / 无共享产物 ⇒ SKIP 并打印（L1 在纯静态工作流与新克隆仍可用；有产物而缺戳记 = FAIL）。成本 ~1.3 s。源 = `ISS-258`（协议双侧变更后 `libc.so` 未重建 ⇒ 动态档全灭）。 |
| `make check-builtins-freshness` | **L1** | 工具链消费的**三份** compiler-rt builtins 归档（构建树产物 / 构建树 clang 资源目录副本 / 安装根副本）须同一 sha256，且归档 mtime 与其**每个成员 `.c.o`** 的 mtime 均 ≥ 构建树 `clang` mtime（`ar` 确定性模式成员头无时间戳 ⇒ 成员按名回查构建树对象；`gcc_personality_v0` 类非成员对象不计）。缺构建树 / 安装根 ⇒ SKIP；有产物而缺副本 = FAIL，提示 `make build-builtins` + `make install-host`。`--self-test` 四类注入（篡改安装副本 ⇒ 红；只动 mtime ⇒ 不假红，`ISS-263`）。成本 ~0.1 s。源 = `ISS-293`（`shl` 编码迁移后 builtins 未重建 ⇒ 旧编码残留 ⇒ 新 qemu 按 ILLI 打 SIGILL）。 |
| `make check-run-artifacts` | **L1** | 三个 user-mode 驱动的 `--json-out` 必填且无 `DEFAULT_LOG_DIR` 固定回落（A1）；`.work/tests/**` 与 test-artifacts 根下每个 `^\d{8}T\d{6}Z-` 运行目录须有 `run.json`/`run.log`/`meta.json`，meta 含非空 `command`/`started_utc`/`toolchain.{clang,qemu,libc}` sha256（A2）；`.work/log/**` 新增文件名须为 `check-<name>.log` 或 `<任务号>-<用途>.(log|json|txt)`，存量按 `.run-artifacts-epoch` + `.run-artifacts-baseline` 豁免（A3）。无扫描面 ⇒ SKIP 并打印；`--self-test` 逐条注入可达 FAIL。规则 = `docs/Process-08`。 |
| `make check-test-reports` | **L1** | `docs/TestReports/` 报告卫生（规则 = 该目录 `README.md` + `Process-09`「测试报告归属」）：R1 报告正文无运行期绝对路径（`/tmp/**`、`/home/**`、具体 `.work/**`；规则文本里的 glob 形态不命中）；R2 快照（正文含 `<!-- 现场生成，勿手改 -->`）**首行**须为该标记，且**至少一份**快照存在（标记全删 ⇒ vacuous FAIL）；R3 文件名 `<M>-<主题>[-<后缀>].md`（`M` + 数字、无日期/空白）+ **无二级主题子目录**；R4 册头（前 40 行）含 生成时间/数据来源/机器指纹/复现。`README.md` 是规则册，R1/R2/R4 不查它。`--self-test` 四类注入各自可达 FAIL。源 = `m13-testcases-004`。 |
| `make check-temp-dirs` | **L1** | 陈旧任务临时目录 / 陈旧大文件 + 占用门控（`INFRA-145t`/`INFRA-146t`）：扫 `/tmp/opencode` 与 `$TMPDIR/opencode` 的**直接子目录**，排除 `git worktree list --porcelain` 的活动 worktree（由任务收尾清理）；**在用任务豁免**：目录名以任务号开头（允许 `-<后缀>`）且 `.tao/tasks/**` 任务书 `**状态**` ∈ {`待开始`,`待验收`,`待返工`} ⇒ 视为在用；其余目录（`已验证`/任务号不存在/非任务号名）**mtime > 2 h** ⇒ FAIL（`du` 体积前 5 大 + 陈旧总数/总体积）；根**直接子文件** **> 100 MiB 且 mtime > 2 h** ⇒ 列清单后 FAIL（`--large-file-mib` 可参数化）；根所在文件系统**占用 > 70%** ⇒ FAIL（`df` 实测、容量不写死）；**只报告不删除**；无任何扫描根 ⇒ PASS（不 vacuous 失败）；`--root` 可指向临时树自检。`--self-test` 覆盖陈旧 FAIL / 活动 worktree 豁免 / 在用任务豁免 / 已验证任务 FAIL / 未知任务号 FAIL / 非任务号 FAIL / 大文件 FAIL / 缺根 PASS / 占用阈值注入 / 只列前 5 大 / 只报告不删除。清单口径：`INFRA-145t` 清理清单 119 行 = 116 行带时龄路径 + 3 行裸名（完成区「116」只计带时龄目录；共清理 116 个目录，裸名行为同批无时龄记录项）。 |
| `make check-runner-reap` | **L1** | 合成驱动下外部 `SIGTERM`/`SIGINT`/`SIGHUP` 后子进程（own-session + 同组 + 超时路径）全部回收、诱饵进程存活；不跑 qemu/编译；`proc_reap` 清理钩子被禁用 ⇒ 残留 ⇒ 可达 FAIL（证据脚本注入）。源 = `TESTCASES-085t`。 |
| `make check-night-report` | **按需诊断**（观测口径；**不随** `check-milestone`，不阻断收口；**不入** L1/L2/L3） | `.dadao/tests/night/<最新日期>/` 的三件套（`manifest.tsv`/`meta.json`/`run.log`）存在且非空；`manifest.tsv` 表头 `scope<TAB>suite<TAB>rc<TAB>log` + 数据行 ≥1 + 四列 + `rc` 整数；覆盖 `tset` 三个套件（libc-test/llvm-ts/embench）与 `arch` 行；**任一 rc≠0 ⇒ FAIL**。**未跑回归运行 ⇒ 明确 FAIL**（不是 SKIP）。`--self-test` 八类注入。回归运行 = 观测/按需消费，成员与期望随演进调整（2026-11-06 用户裁定 A，`INFRA-126t`）。源 = `TESTCASES-076t`。 |
| `make check-l3-report` | **里程碑收尾专项**（随 `check-milestone`；**不入** L1/L2/L3） | `.dadao/tests/l3/<最新 UTC 戳>/` 的三件套存在且非空；`meta.json` 的 `command`（指向 check-full）/`started_utc`/`finished_utc`/`commit` 非空 + `toolchain.{clang,qemu}` 有非空 content id（libc/lld 记录但非必需）；`manifest.tsv` 表头 `scope<TAB>suite<TAB>rc<TAB>log` + 四列 + `rc` 整数 + **`log` 文件真实存在且非空**；覆盖四 scope（inst/arch/unit/tset）与 `l3_run.DEFAULT_MEMBERS` 全部成员；**任一 rc≠0 ⇒ FAIL**；`run.log` 的 `[exit marker] rc=N` 须与 manifest 一致（防伪造全绿）。**未跑 L3 ⇒ 明确 FAIL**（不是 SKIP）。`--self-test` 十二类注入。源 = `TESTCASES-083t`。 |
| `make check-install-tools` | **按需（`install-host` 收尾断言；不入 L1）** | 安装根须带齐 `Makefile` 的 `HOST_LLVM_TOOLS` + `HOST_LLVM_TOOL_SYMLINKS`（脚本**解析 Makefile**，不另立第二份清单）：逐个存在、可执行、运行探针 rc=0（`not` 用 `not false`）、尺寸 == 构建树；`--sha`/`--sha-tools` 另比 sha256；别名须为**相对符号链接**、目标可执行且同源；`llvm-readelf -h` 须解析大端 DADAO 探针对象（`ELFDATA2MSB` + `EM_DADAO`）。未跑 `install-host` 的新克隆**必然红** ⇒ 不入 L1（同 `check-milestone` 理由）；挂载点 = `install-host` 收尾。`--self-test` 五类注入。成本 ~0.2 s（`--sha` ≈1.8 s/342 MB）。源 = `ISS-261`。 |
| `make check-generator-sync` | **L2** | 6 个向量生成器（`ctrl-jump/call/ret`、`ctrl-br`、`mem`、`isa`、`misc`、`bitcnt`）以 `--check` 从真源重渲染，与落盘向量**逐字节**一致（只读）；任一漂移 ⇒ FAIL。`rev` 在 L1 `check-rev-vectors`，此处不重复（§4）。源 = `INFRA-115t`。 |

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

## 3. 「新检查进哪一层」的归属规则（MUST）

新增检查（门控 / 目标）时，按下列**机械判据**定层（不手工权衡）：

1. **只看仓库完整性 / 组件可用性，不跑被测语义** ⇒ **L1**（静态检查、清单校验、哈希漂移门控、可用性冒烟）。
2. **跑被测语义，但只取"各类别代表 / 受控子集"**（数十 ~ 数百秒量级）⇒ **L2**。
3. **跑被测语义的全量 / 大套件**（数百 ~ 数千秒）⇒ **L3**。

- **代表集必须机械派生，禁止手工挑**：L2 的"各类别都有"由**类别清单**机械派生（按 `contracts/` 格式类 / 指令 `scope` / QEMU 语义类别等），**不得**人工挑选（`INFRA-058t` `check-qemu-smoke` 即此法）。
- **计数不写死**：代表集规模、覆盖率等一律**现场统计**，不得在门控/文档写死具体数字（`lessons §2`）。
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

## 5. 每层须可达 FAIL（MUST）

- **每层的每个门控/检查必须"能失败"**：断言/用例须有**可达 FAIL 路径**（禁恒真、禁"两支写同一结果"）；覆盖类检查须**现场统计、不写死**。
- **结构断言**：除"确有命中"外，还须断言**结构**（成对 / 条数 / 行数 == 真源），防"空转绿灯"（`lessons §2.20`/`§2.21`）。
- **vacuous fail-closed**：扫描面为空（"没东西可查"）⇒ 判 **FAIL**，不得因"没命中"而报绿。
- **验收留证**：新门控须给「**注入反例 → FAIL → 还原 → 回绿**」真实输出（`cp` + md5 还原，**禁** `git checkout`/`restore`/`stash`）。

## 6. 与其它规范 / 文档的关系

- `AGENTS.md`「门控分层与触发点」= **规则 + 指针**（层名 / 触发点一句话 + 指向本规范）；**本规范 = 明细与演进规则**，二者**不重复**。
- `docs/Process-05`（里程碑 TDD）= 向量/门控的**开发方法**（L1 编码 / L2 结构 / L3 执行，**测什么**）；本规范 = **工程门控的规模分层与归属**（**怎么组织/何时跑**）——两者维度不同，`Process-05` 的 L1/L2/L3 指**测试向量层次**，本规范的 L1/L2/L3 指**门控目标层次**，**同名不同指**，引用时须写清。
- `docs/Process-01`（组件补丁）/ `Process-06`（`spec/` 保护）等**与层归属无关**；`check-patch-tree`/`check-spec-readonly` 各按其规范实现，**归属 L1**（不跑被测语义）。
