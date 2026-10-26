# 门控分层规范（L1 / L2 / L3）

> **状态**：生效（2026-10-13）｜**上位依据**：无——属**工程过程规范**（可逆、单项目、无外部契约，不命中 ADR 判据，见 `docs/Process-03`）。
> **缘起**：用户 2026-10-09 提出「门控按规模分三层」（原设计稿 `.tao/knowledge/gate-tiering-design.md`，已归档 `.tao/archive/M7/notes/`），用户 2026-10-12 裁定「此事**应有一个工程规范文档专门说明，放到 `docs` 下面**」⇒ 立本规范。
> **关键词**：本规范用「**必须**（MUST）／**应当**（SHOULD）／**可以**（MAY）」表达规范性等级。§1–§5 均标 **MUST**。
> **分工**：`AGENTS.md` 只留**规则 + 指针**（「门控分层与触发点」，≤2 行）；**明细与演进规则**（分层组成 / 归属判据 / 层间不重复 / 可达 FAIL）由本规范承载，**不重复**。

---

## 1. 分层定义与各层组成（MUST）

按**规模/耗时**自上而下分三层；每层 = **一组 `make` 目标**（层间**不重复**列出同一目标，见 §4）。

| 层 | 目标（真源：`Makefile`） | 各层组成 | 目标耗时 |
|---|---|---|---|
| **L1 完整性 / 可用性** | `make check`（**默认**） | **仓库完整性静态检查**（不跑被测语义：patch-tree / spec-drift / 索引卫生 / 编码·合法性·scope·fp 一致性 / ISA 覆盖矩阵漂移 / 引用审计 / 目录·残留·只读 / **组件 changelog 形态**（`check-component-changelog`：列表式 + 按里程碑分节）等）**+ 组件可用性冒烟**（`llc` / `clang --print-targets` / `qemu-system-dadao` 可执行且认识 `dadao`；**不跑被测语义**）**+ issue 台账校验 / `compileall tools`** | 秒 ~ 几十秒 |
| **L2 模块功能代表集** | `make check-modules` | 各模块的**功能代表集**（受控子集）：`check-lit`（MC/CodeGen/E2E 受控子集）+ `check-interface` + `check-qemu-smoke`（语义**类别代表**子集）+ `test-codegen`/`test-elf`/`test-semihost`/`check-picolibc-tests` | 几十 ~ 几百秒 |
| **L3 较完整** | `make check-full` | **较完整**：`check-inst`（`tests/inst` **全量**载体：`base` + `rol`/`atomics`/`clmul`；`rev`/`bitcnt` 未纳入，见 `tests/inst/inventory.md`「门控覆盖」；旧名 `check-qemu-semantics` = 别名）+ `check-lit-full`（全量生成档）+ Embench（`test-m6`）+ 全量向量回放 | 几百 ~ 几千秒 |
| **按需（模块完整）** | 各 `test-*`/`check-*` **单独调** | 模块**全量**、profiling | 不定 |

- **L1 判据**：**只看"仓库是否完整 + 组件是否可用"**，**不得**依赖被测语义的执行结果（那是 L2/L3）。
- **默认 `make check` = 仅 L1**：`check-qemu-semantics`（全量语义）**移出** L1、`check-lit`/`check-interface`（受控子集）**移出** L1（`INFRA-058t` 落地）。
- **层边界（耗时带）的实测校验**（承接原设计稿 `.tao/archive/M7/notes/gate-tiering-design.md` §五「第 0 步」待办）：第 0 步：**逐门控计时**（`make -n` 不适用；逐目标 `time`），据实测确定 L1/L2/L3 边界与是否值得拆。

### 1.1 门控登记：契约口径与里程碑收尾（2026-10-17）

| 目标 | 层 | 判据（机械） |
|---|---|---|
| `make check-contracts-pending` | **L1** | `.tao/contracts/**` 出现「待…定 / 待裁定 / TODO / TBD」标记的行，须同行含 `ADR-<n>` / `ISS-<n>` 指针（只认带编号落点）；行内代码跨度与「」引用不计。计数现场统计。 |
| `make check-contract-relocs` | **L1** | `contract-elf.md §2.2` 与 `contract-dynlink.md §4.3` 的**现行表**逐行比对（类型号 ↔ 名）；只解析两小节内的表格行 ⇒ 历史注记不参与；附加自洽 = 表非空 / 号名唯一 / 号 0 起密集。 |
| `make check-milestones-fresh` | **L1** | `milestones.md`「任务流水」逐行：状态 == 任务书 `**状态**`；活 `t` 册 + `INTEG-*m` 册所列号 + 正文号须全部入表（已归档号豁免，全仓无册的悬空号 FAIL）；一句改动 ≤120 字符；按完成时间倒序（未完成 = 登记时间 + `（登记）`，同时按编号升序）；恰好 4 格、状态枚举、`已验证` 不得带登记注。`--self-test` 内置五类注入。 |
| `make check-spec-archive` | **里程碑收尾专项**（随 `check-milestone`；**不入 L1**） | 册头 ∪ 附录声明的每个版本须有 `.tao/archive/SimRISC-<ver>/`：A1 目录存在；A2 目录非空且含 `SimRISC-00*`；A3 文件数 = 派生清单；A4 反向（磁盘 ⊆ 清单）⇒ 双向；**只校验存在性与文件集、不校验内容**；`-rc` 不参与。判定归 `tools/spec/check_spec_archive.py`（判据未改，仅改触发层）。 |
| `make check-spec-archive-verify` | **里程碑收尾专项**（随 `check-milestone`；**不入 L1**） | 归档**内容**：以各目录 `PROVENANCE.md` 的「快照提交」为锚，逐文件 sha256 与该提交树全等 + 「版本组合 sha256」= 按表重算值（拒绝子串/前缀匹配）；无 `PROVENANCE.md` 的既有目录回落派生快照；`-rc` 打印 SKIP。判定归 `tools/spec/gen_spec_archive.py --verify`（判据未改，仅接线）。 |
| `make check-milestone` | **L2 层 / 里程碑收尾专项**（按需；**不入** `check-modules`） | 先跑 `check-spec-archive` + `check-spec-archive-verify`（归档结构 + 内容 sha）；再：当前里程碑（`milestones.md` 中 `项目里程碑 = M<n>` 断言的最大 n）在 `.tao/tasks/**` 有对应 `m` 册（自报里程碑须一致）；该册所列任务号在 `.tao/tasks/**` 或 `.tao/archive/**` 真实存在（册内零任务号 ⇒ vacuous FAIL）；并接 `check_tasks.py --strict`（漏收尾 = 0）。 |
| `make check-knowledge-dir` | **里程碑收尾专项**（随 `check-milestone`；2026-10-26 用户裁定「从L1摘除，放到里程碑check里」） | `.tao/knowledge/` **顶层**只允许显式白名单文件（台账集合）与子目录（子目录不限）；白名单外文件 / 目录缺失 / 顶层空（vacuous）⇒ FAIL。计数现场统计。判定归 `tools/infra/check_knowledge_dir.py`（判据未改，仅改触发层）。 |
| `make check-syscall-abi` | **L1** | syscall 参数银行表的三载体（musl `__dadao_argmask` / `src/thread/dadao/syscall_cp.s` 派发 / QEMU `cpu_loop.c:dadao_argmask`）逐项一致（号→掩码全等；asm 子集逐号相等 + 每个 `.Lm<mask>` 块的 `rd2rb`/`rd2rd` 条数 = 掩码位值）+ 完整性（musl 能发出的 syscall 名 ⊆ 表，空表 vacuous FAIL）。工作树在则读树，否则读 `components/**` 补丁（新克隆可跑）；完整性/audit 两项在无 musl/qemu 检出时 SKIP 并打印。 |
| `make check-musl-freshness` | **L1** | 安装根 `libc.so` 必须由**当前** musl 源 + 工具链构建：`build_musl.py` 成功构建后落 `obj/.dadao-musl-source-stamp`（全树内容 sha256）与 `obj/.dadao-toolchain-stamp`；门控比对两戳记 + 安装副本与构建产物 sha256 一致 + `ld-musl-dadao.so.1` 符号链接指向 + **`obj/.dadao-builtins-stamp`**（`libc.so` 的 `LIBCC` 归档内容 sha256，`ISS-293`：DSO 内嵌 builtins，归档变则须 relink）。任一项不符 ⇒ FAIL（提示 `make build-musl-shared`）。无构建树 / 无共享产物 ⇒ SKIP 并打印（L1 在纯静态工作流与新克隆仍可用；有产物而缺戳记 = FAIL）。成本 ~1.3 s。源 = `ISS-258`（协议双侧变更后 `libc.so` 未重建 ⇒ 动态档全灭）。 |
| `make check-builtins-freshness` | **L1** | 工具链消费的**三份** compiler-rt builtins 归档（构建树产物 / 构建树 clang 资源目录副本 / 安装根副本）须同一 sha256，且归档 mtime 与其**每个成员 `.c.o`** 的 mtime 均 ≥ 构建树 `clang` mtime（`ar` 确定性模式成员头无时间戳 ⇒ 成员按名回查构建树对象；`gcc_personality_v0` 类非成员对象不计）。缺构建树 / 安装根 ⇒ SKIP；有产物而缺副本 = FAIL，提示 `make build-builtins` + `make install-host`。`--self-test` 四类注入（篡改安装副本 ⇒ 红；只动 mtime ⇒ 不假红，`ISS-263`）。成本 ~0.1 s。源 = `ISS-293`（`shl` 编码迁移后 builtins 未重建 ⇒ 旧编码残留 ⇒ 新 qemu 按 ILLI 打 SIGILL）。 |
| `make check-run-artifacts` | **L1** | 三个 user-mode 驱动的 `--json-out` 必填且无 `DEFAULT_LOG_DIR` 固定回落（A1）；`.work/tests/**` 与 test-artifacts 根下每个 `^\d{8}T\d{6}Z-` 运行目录须有 `run.json`/`run.log`/`meta.json`，meta 含非空 `command`/`started_utc`/`toolchain.{clang,qemu,libc}` sha256（A2）；`.work/log/**` 新增文件名须为 `check-<name>.log` 或 `<任务号>-<用途>.(log|json|txt)`，存量按 `.run-artifacts-epoch` + `.run-artifacts-baseline` 豁免（A3）。无扫描面 ⇒ SKIP 并打印；`--self-test` 逐条注入可达 FAIL。规则 = `docs/Process-08`。 |
| `make check-install-tools` | **按需（`install-host` 收尾断言；不入 L1）** | 安装根须带齐 `Makefile` 的 `HOST_LLVM_TOOLS` + `HOST_LLVM_TOOL_SYMLINKS`（脚本**解析 Makefile**，不另立第二份清单）：逐个存在、可执行、运行探针 rc=0（`not` 用 `not false`）、尺寸 == 构建树；`--sha`/`--sha-tools` 另比 sha256；别名须为**相对符号链接**、目标可执行且同源；`llvm-readelf -h` 须解析大端 DADAO 探针对象（`ELFDATA2MSB` + `EM_DADAO`）。未跑 `install-host` 的新克隆**必然红** ⇒ 不入 L1（同 `check-milestone` 理由）；挂载点 = `install-host` 收尾。`--self-test` 五类注入。成本 ~0.2 s（`--sha` ≈1.8 s/342 MB）。源 = `ISS-261`。 |

- **计数类文档的同步时点**（2026-10-22 用户裁定）：`contract-isa.md` 等**分桶计数**（`m9`/`excluded`/`fp` 的条数与族数）**不随单任务改**，一律在**里程碑收尾**统一同步；单任务只同步其机械门控的期望值（`check_scope.py` / `check_fp_contract.py`），避免同一数字反复返工。
- 各检查均 **fail-closed**（扫描面为空 / 无 `m` 册 / 表被删空 ⇒ FAIL），可达 FAIL 见各脚本 `--self-test`。
- `check-milestone` 的层归属按 §3 判据定位：它**不跑被测语义**，但**只在里程碑收尾时成立**（`m` 册未建前必然红），故登记为 **L2 层 / 收尾专项**、不并入日常 `check-modules`（否则 L2 常态红）；触发点 = 里程碑 / 模块 `m` 册核验前。
- `check-spec-archive` / `check-spec-archive-verify` 同属**收尾专项**：归档是只读历史快照，只在发布/里程碑边界变化（用户 2026-10-25 裁定：结构与 sha 都只在里程碑收尾做一次）⇒ 由 `check-milestone` 前置承载，**不入 L1**（`INFRA-109t` 前 `check-spec-archive` 在 L1）。

## 2. 触发点（MUST）

- **任务收尾**（`/dispatch` 后、`/complete` 前）：跑 **L2**（`make check-modules`）。
- **里程碑 / `/complete`**：跑 **L3**（`make check-full`）；里程碑收尾另跑 **`make check-milestone`**（归档结构 + 内容 sha + `m` 册 + 漏收尾 = 0）——归档门控**只在此触发**（`INFRA-109t`）。
- **某模块全量**：按需**单独调**该模块目标（不进 L1/L2）。
- **同工作树互斥（MUST）**：写共享状态的目标（构建树 `.work/build/**`、安装根 `.dadao/**`、SDK 产物目录 `.dadao/tests/**`）与跑这些写者的门控**串行化**——`Makefile` 的 `GATE_LOCKED_TARGETS`（**单一真源**，文档不另列清单）经 `tools/infra/gate_lock.py` 在 `.dadao/gate.lock` 上取 `flock(2)`，独立进程**排队**或 fail-fast，嵌套（同一 make 树）放行。语义：等待上界 `GATE_LOCK_WAIT`（默认 3600 s，超时 rc=75 并打印持有者 pid/开始时间/目标/命令，**不得**无限阻塞）；`GATE_LOCK_FAILFAST=1` ⇒ 立即 rc=75；锁不可用（父目录不可写 / 无 `flock`）⇒ rc=69 且**不运行**目标（禁静默跳过）。`--self-test` 覆盖「嵌套放行 / 独立进程拒绝 / 锁不可用报错」三类。源 = `ISS-229`（L2/L3 与 `install-host` 并发读到瞬态不完整的安装根 ⇒ Embench 假 FAIL；手动 `build-mc` 与 L2 内 `install-host` 并发 ⇒ 构建树写坏）。
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

- **同一检查只在"一层"被"直接"列出**；某目标被上层**前置依赖**而间接跑到（如 `test-semihost` 自带 `check`）**不算重复**。
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
