# INFRA-093t: 测试运行产物与日志的组织规矩（+ L1 门控 check-run-artifacts）

**模块**：infra
**项目里程碑**：M8
**依赖**：无（约束：本册**不动** `.work/log/testcases/**` 存量；搬迁另起一笔，且须等当前动态跑结束）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户要求（原话逐字；渠道 = 主会话当场质问，2026-10-19）
> 「**你自己看看 .work/log 下面是怎么组织的？乱成这样，你告诉我有个文件是公用的？？？？**」

**现场事实（主会话实测，2026-10-19；本册据此立规矩，不得凭记忆改数）**：
- `.work/log/` ≈ **7000+ 文件 / 92 MB**；分模块：`llvm/` 1925、`infra/` 1401、`qemu/` 986、`spec/` 619、`testcases/` 523（其中**平铺 403 项 = 398 文件 + 5 子目录**）、`architect/` 180、`integ/` 168、`musl/` 80。
- `testcases/` **全平铺**：403 项无运行边界；一次跑的全部产物与另一次跑混在同一层。
- **两套命名并存**：`llvm-ts-user-static.json` 与 `llvm-ts-user-static-static.json`；`llvm-ts-user-dynamic.json` 与 `llvm-ts-user-dynamic-dynamic.json`（根因 = `run_llvm_ts_user.py::_round_path()` 在 `both_rounds` 时**再把 mode 拼一次**，`tools/testcases/run_llvm_ts_user.py:2042-2046`）。
- **同义拼写并存**：`.work/log/architect/check_issues.log` vs `.work/log/recheck-061t/check-issues.log`。
- **多个固定名被反复覆盖**：`libc-test-user-{static,dynamic}.{json,log}`、`llvm-ts-user-*`；三个 user-mode 驱动在省略 `--json-out` 时**回落到固定路径**（`DEFAULT_LOG_DIR = ".work/log/testcases"`：`run_libc_test_user_suite.py:172/1369-1372`、`run_llvm_ts_user.py:270/2053-2056`、`run_embench_user_suite.py:113/553-556`）⇒ 一次 `--filter` 子集跑即可把权威结论覆盖成子集（**已发生 2 次**）。

## 接口规范

### 一、规矩（唯一真源；7 条，工程师逐条落到文档）
1. **每次测试跑 = 一个独立目录**：`.work/tests/<UTC时间戳>-<套件>-<档>/`，内含
   - `run.json`（逐例结果记录）、`run.log`（人读日志）、`meta.json`（命令行 / 起止 UTC 时间 / **工具链摘要**：`clang`、`qemu-dadao`、`libc.a` 或 `libc.so` 的 **sha256（或 md5）**）。
   - **禁止**两次跑写同一目录；目录名时间戳格式 `YYYYMMDDTHHMMSSZ`。
2. **权威跑**：只写 `.work/tests/authoritative/<UTC时间戳>-<套件>-<档>/`，各次 **并列、永不覆盖**；另设 `latest` 指针（指向最新权威跑目录）。子集跑（`--filter`）**不得**写 `authoritative/`。
3. **驱动约束**：上述权威目录之外，三个 user-mode 驱动（`run_libc_test_user_suite.py` / `run_llvm_ts_user.py` / `run_embench_user_suite.py`）的 `--json-out` **必填**；未给 ⇒ **报错退出（非 0）**，**删除**固定默认回落。`--report-out` 缺省 = 与 `--json-out` **同目录、同名换 `.log`**（不得回落到 `DEFAULT_LOG_DIR`）。上述驱动即使给了 `--json-out`，也须按第 1 条建 run 目录（`run.json`/`run.log`/`meta.json` 三件套），`--json-out` 相对路径按调用者 CWD 解析。
4. **门控 / 手工日志**：`.work/log/<模块>/<任务号>-<用途>.log`；**禁止**无任务前缀的文件名（`<任务号>` = `INFRA|SPEC|LLVM|QEMU|TESTCASES|INTEG` + 三位数字 + 可选后缀）。门控自身的日志名统一写 `check-<name>.log`（连字符，**禁** `check_<name>.log`）。
5. **归档**：历史 400+ 文件按**任务前缀**移入 `.work/tests/archive/<任务号>/`（**只移不删**；**删不删由用户定**）。本册只定规矩。
6. **搬迁执行**：**拆两步** —— ① 本册先落驱动 / 门控 / 文档；② `.work/log/testcases/` 的实际搬迁**另起一笔**（**必须等当前动态跑结束**，避免动到正在写的产物）。**本册不得移动 / 删除 `.work/log/**` 任何存量文件**。
7. **新门控 `check-run-artifacts`（L1）**：断言 A1–A3（见下），并入 `make check`；`--self-test` 内置可达 FAIL；真实注入一次「FAIL → `cp` 备份 + md5 还原 → 回绿」。

### 二、门控实现口径（`tools/infra/check_run_artifacts.py`）
- **A1 驱动无固定默认输出**（源码级）：
  - 三个驱动的 `--json-out` 必须 `required=True`；源码中不得再出现 `args.json_out if ... else os.path.join(DEFAULT_LOG_DIR, ...)` 形式的固定回落；`DEFAULT_LOG_DIR` 可作为历史常量保留但**不得用于输出**（更干净：删除未用常量）。
  - `--report-out` 的缺省须由 `--json-out` 派生（同目录同名 `.log`）。
  - 反例注入：把某驱动的 `--json-out` 改回 `default=None` + 固定回落 ⇒ 必须 FAIL。
- **A2 运行目录三件套**：`.work/tests/**` 下每个运行目录（匹配 `^\d{8}T\d{6}Z-`，含 `authoritative/` 下）必须同时有 `run.json` / `run.log` / `meta.json`；`meta.json` 须含 `command`（非空）、`started_utc`、`toolchain`，且 `toolchain` 内 `clang` / `qemu` / `libc` 各带**非空** sha256 或 md5。`authoritative/latest` 须存在且指向存在的目录。**无 `.work/tests/**` ⇒ SKIP（不 vacuous PASS、明文打印）**；有 run 目录而缺件 ⇒ FAIL。
- **A3 `.work/log/**` 新文件命名**：只查**新增**（存量豁免，见下）。合法两类：`check-<name>.log`、`<任务号>-<用途>.(log|json|txt)`；其余（含 `check_issues.log`、无任务号名）⇒ FAIL。
  - **存量豁免口径（实现须写进文档）**：落地时在 `.work/log/` 下创建 epoch 标记 `.run-artifacts-epoch`（内容 = 创建时刻 UTC），**mtime ≤ epoch** 的文件豁免；标记不存在 ⇒ A3 SKIP。禁把豁免写成「只查某个目录」。
- 退出码 `0` = PASS / `1` = FAIL；`--root DIR` 供 self-test 用临时树；**不依赖网络、不跑被测语义**。

### 三、文档落点（**只一处**）
- 新建 `docs/Process-08-测试运行产物与日志组织规范.md`：7 条规矩 + A1–A3 门控口径 + 存量豁免（epoch）+ 第 6 条搬迁边界；
- `docs/README.md` 的「工程流程规范」表加一行索引。
- **不新建** `.tao/knowledge/` 文档。

## 验收标准
1. 文档落点一处（`docs/Process-08` + `docs/README.md` 索引行），7 条齐全且与门控逐条对应；第 5/6 条明确「只定规矩、本册不搬迁」。
2. 三个驱动 `--json-out` 必填（缺参 **rc≠0** 且报错信息含 `--json-out`），固定默认回落**已删除**；`--report-out` 缺省与 json 同目录；`DEFAULT_LOG_DIR` 不再参与输出。
3. **实跑小样本两次**（静态档、`--filter` 单个轻量用例、输出落 `.work/tests/<run 目录>/`）：两个 run 目录并存、`run.json`/`run.log`/`meta.json` 齐全且内容独立（两目录文件 md5 各不同），**不覆盖**；`meta.json` 的工具链摘要与 `command -v clang` / `qemu-dadao` / 安装根 libc 的实测 sha256 一致；再跑一次**不带** `--json-out` ⇒ rc≠0。**不得写 / 移动 / 删除 `.work/log/testcases/**`**（附 `find .work/log/testcases -newer <epoch> -type f` 为空或仅本册 epoch 的证据）。
4. `python3 tools/infra/check_run_artifacts.py` rc=0；`--self-test` rc=0（≥3 类注入：A1 固定回落 / A2 缺 `meta.json` 或工具链摘要 / A3 非法名），且干净基线 PASS；真实注入一次 ⇒ rc=1 ⇒ `cp` 备份 + md5 三态一致还原 ⇒ rc=0。
5. `check-run-artifacts` 并入 `make check`（L1）与 `make help`/注释（`docs/Process-07 §1.1` 对应表如涉分层说明则补一行）。
6. 收尾门控：`make check`(L1) / `check-tasks` / `check-knowledge-refs` / `check-no-residue` / `check-milestones-fresh` 全 rc=0；完成区贴真实命令与退出码。
7. 只动任务列出的文件（三个驱动 + 新门控 + `Makefile` + 两份 docs + 本任务书）；不删任何历史日志；不提交 git。

## 完成区
**测试结果**：三驱动小样本全 green —— `libc-test` 静态 `functional/{fcntl,fnmatch}` 各 1/1 PASS（两次独立跑，耗时 21 s / 21 s）；`llvm-ts-user` 静态 `evalloop$` 1/1 PASS、`--link-mode both` static+dynamic 各 1/1 PASS（json 后缀各一次）；`embench-user` 静态 `-O0` 19/19 PASS。`check-run-artifacts` 默认 rc=0、`--self-test` 5/5 PASS；证据脚本 18/18 checks、rc=0；`make check` rc=0。
**修改文件**：`tools/testcases/run_artifacts.py`（新，运行目录/meta 助手）、`tools/testcases/run_libc_test_user_suite.py`、`tools/testcases/run_llvm_ts_user.py`、`tools/testcases/run_embench_user_suite.py`、`tools/infra/check_run_artifacts.py`（新，L1 门控）、`Makefile`、`docs/Process-08-测试运行产物与日志组织规范.md`（新）、`docs/README.md`、`docs/Process-07-门控分层规范.md`（§1.1 一行）、本任务书；gitignored：`.work/evidence/INFRA-093t/run.sh`、`.work/log/.run-artifacts-{epoch,baseline}`（新建，未改存量）。
**修改文件（补正，收尾 2026-10-19）**：另含 `.tao/knowledge/milestones.md`（`INFRA-093t` 状态行）—— 上一行漏列；落地提交 `d003468` 实际含该文件（reviewer 第 1 轮披露）。
**验收结果**（真实命令/rc）：`python3 tools/infra/check_run_artifacts.py` → rc=0（A1×3 PASS / A2 0 目录 / A3 5965 存量豁免）；`--self-test` → rc=0（baseline 0 + 4 注入各 rc=1）；`./.work/evidence/INFRA-093t/run.sh` → rc=0（含真实 A1 注入 rc=1 + `cp`/md5 三态还原 rc=0）；`make check` → rc=0；`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check-milestones-fresh`/`check_issues` 均 rc=0。两次 libc 跑目录并存：`one/work/20261018T232249Z-libc-test-user-static` 与 `two/work/20261018T232310Z-libc-test-user-static`，`run.json`/`run.log`/`meta.json` md5 两两不同；meta 的 clang/qemu/libc sha256 与实测一致。`find .work/log/testcases -newermt <epoch> -type f` = **0**。
**计数时点（补正，2026-10-19）**：上一行「A2 0 目录」与「`find … -newermt <epoch> -type f` = 0」均为 **2026-10-19 07:1x–07:3x 时点**（证据脚本 07:17、提交 `d003468` 07:37 前）；后随 `TESTCASES-051t`／`llvm-ts` 在飞产物变化（现值 19 目录 / 11 文件），**非阻断**。
**新发现/坑**：① 任务书要求 `docs/Process-08` + `docs/README.md` 索引，派单文字只写「docs/Process-07」——按任务书落 Process-08，另在 Process-07 §1.1 补门控登记一行。② 仅靠 mtime ≤ epoch 不够：落地时正在写的旧文件被改写会把 mtime 变新 ⇒ 追加 `.run-artifacts-baseline`（落地时全量路径快照）做存量豁免，`llvm-ts-user-*` 过渡豁免单列。③ A3 任务号正则初版漏了 `PREFIX-` 连字符，self-test 基线当场抓红（已修）。④ 运行目录建在 `--work-dir` 下（默认 `.dadao/tests/<套件>`），A2 同时扫 `.work/tests/**` 与 test-artifacts 根，避免新目录永远落在扫描面外。⑤ `--json-out` 收紧为必填会打断未带该参的存量证据脚本（如 `.work/evidence/QEMU-063t/run.sh`）；已在 Process-08 §3 给迁移命令，存量脚本未改。
**遗留问题**：① 按派单**未改** `**状态**`（仍 `待开始`）。② 第 5/6 条只定规矩：`.work/log/testcases/**` 存量搬迁另起一笔、待当前动态跑结束；过渡豁免 `llvm-ts-user-*` 待搬迁后删除。③ 未跑 `install-host`/L2/L3；未 commit/push。④ 存量 `.work/evidence/**` 调用点仅文档迁移说明，未逐一回填 `--json-out`。

## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：`run_artifacts.py` + 三个驱动 diff + `check_run_artifacts.py` + Makefile/docs；逐行审查，并以 self-test / 小样本 / 证据脚本实跑对齐。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| A1 用跨驱动共享 `problems` 判断本驱动成败（前一驱动红会连坐后续） | ✅已修 | 每驱动改局部 `local` 列表 | self-test 基线 3×A1 PASS；单驱动注入仅该行红 |
| A2 `rel` 用 `roots[0]`、PASS 判断用全局 `any(rel in p)`，多根/多目录会误判 | ✅已修 | 每目录局部 `local` + 统一 `rel` | `--root` 实跑 A2 PASS；注入缺 meta FAIL |
| A3 任务号正则缺 `PREFIX-` 连字符，合法名 `INFRA-093t-demo.log` 被误判 | ✅已修 | `TASK_ID` 加 `-` | self-test 基线由 rc=1 → rc=0 |
| A3 失败仍打印 `[PASS]`（结论由 final 汇总兜底，易误读） | ✅已修 | `bad>0` 打印 `[FAIL]` | 注入后行首为 `[FAIL] A3` |
| LLVM `run.json` 在 `write_artifacts` 与 `write_run_dir` 重复写两次 | ✅已修 | 删前一处，`run_dir` 参数一并移除 | llvm 静态/both 小样本 rc=0，三件套齐全 |
| 运行目录与 spec 的 `.work/tests` 表述可能漂移 | ✅已修 | A2 扫描 `.work/tests` + test-artifacts 根；Process-08 明写默认 `--work-dir` | `--root` 实跑抓到真实驱动目录；`make check` rc=0 |
| `--json-out` 必填破坏存量证据脚本 | ⏸延后（须另册） | Process-08 §3 给迁移命令；本册不改 `.work/evidence/**` | 任务书第 6/7 条边界 |

**判决**：findings 全部已修或按边界延后；无未修阻断项。按派单不改 `**状态**`，返回主会话。

#### 第 1 轮 reviewer 验收

**范围**：规矩 7 条 / 门控 A1–A3 + `--self-test` / 三驱动 `--json-out` 收紧 / 实跑抽查 / 如实性抽查。工作区对账：开工/收尾 `git status --porcelain -uall` 均 0 行；交付物 9 文件 md5 前后全等；`.work/log` 全量 mtime 快照 diff 为空（⇒ 未动任何存量日志）。

**规矩逐条**（真源 `docs/Process-08` + `tools/infra/check_run_artifacts.py`）：
① 独立运行目录 ✓：`create_run_dir` 同秒碰撞等待、不复用目录；实跑 libc/embench 各得独立目录、三件套齐；meta 的 clang/qemu/libc/lld/libc_a/libc_so sha256 我对实测文件重算逐一相等。
② `authoritative/` + `latest` ✓：A2 校验 latest 存在且指向目录；我注入「latest 指向不存在目录」⇒ rc=1（`A2 .../latest does not point at a directory`）。子集跑不写 `authoritative/` 仅文档+调用者约束（ISS-282 ①）。
③ `--json-out` 必填 ✓：三驱动均 `required=True`；`DEFAULT_LOG_DIR` grep 0 处；`--report-out` 缺省 = `splitext(json_out)[0]+".log"`；缺参实测三驱动各 rc=2 且报错含 `--json-out`。
④ 日志命名 ✓：A3 双正则 = `check-<name>.log` / `<任务号>-<用途>.(log|json|txt)`；self-test 注入 `check_issues.log` 抓红；epoch+baseline 豁免口径写入文档。
⑤ 归档只移不删 ✓：§1.5 明文「只移不删、删不删由用户定」；本册未搬（只查规矩）。
⑥ 搬迁另起一笔 ✓：§1.6 边界明文；实测 `.work/log/testcases/` 仍 532 文件、`.work/tests/` 下无 `archive/` 子目录 ⇒ 本册确实未搬。
⑦ 新门控 ✓：A1×3 / A2 / A3 + `--self-test`（基线绿 + 4 注入各 rc=1），已入 `make check`（日志见 `check-run-artifacts: PASS`）。

**重跑记录（真实 rc）**：`python3 tools/infra/check_run_artifacts.py` → 0（A1×3 PASS；A2 19 个运行目录全 PASS；A3 51 checked / 0 illegal / 5965 exempt）；`--self-test`（`DADAO_TMP=/tmp/opencode/review-093t/selftest`）→ 0（5/5）；`make check` → 0（内含 check-run-artifacts / knowledge-refs / no-residue / check_issues）；`make check-patch-tree` → 0（`181 patches OK`）；`make check-musl-freshness` → 0；`make check-milestones-fresh` → 0；`make check-tasks` → 0；`./.work/evidence/INFRA-093t/run.sh` 重跑 → 0（`18/18 checks passed`，逐条与完成区一致；其自带注入 md5 `9a1cd69d…→dad3dad0…→9a1cd69d…` 还原；脚本 TMP 落 `/tmp/opencode/INFRA-093t/evidence`，任务自身 tmp 命名空间、未写仓库）。

**我的独立注入（`cp`+md5，禁 git 还原）**：`run_embench_user_suite.py` 的 `"--json-out", required=True` → `default=None`（md5 `fe9b9bea…→9594423c…`）⇒ 门控 rc=1、仅该驱动 `[FAIL] A1 ... not required=True (required=None)`；`cp` 还原后 md5 三态全等、rc=0 回绿。另一独立注入 = A2「latest 悬空」（临时树 `--root`）⇒ rc=1。证据脚本重跑前后我再记 md5，三驱动无残留。

**实跑抽查（输出全落 `/tmp/opencode/review-093t/run/`，未写 `.work/log/**`）**：libc-test 静态 `--filter functional/fcntl` rc=0（1/1 pass，21.2 s）⇒ `20261019T021719Z-libc-test-user-static/{run.json,run.log,meta.json}`；embench 静态 `--opt O0` rc=0（19/19）⇒ `20261019T021752Z-embench-user-static/` 同三件套；meta 字段齐（suite/mode/command/cwd/started_utc/finished_utc/duration_seconds/toolchain），目录名 `YYYYMMDDTHHMMSSZ-<套件>-<档>` ✓。

**如实性抽查**：① 证据脚本 18/18 rc=0 —— 复现一致 ✓；② 两次 libc 跑目录并存、三件套 md5 两两不同 —— 复现一致 ✓；③ `make check` rc=0 / 补丁 181 —— 复现一致 ✓；④ embench `-O0` 19/19、libc 1/1、21 s —— 复现一致 ✓；⑤ 「`find .work/log/testcases -newermt <epoch> -type f` = 0」**我现值 11**（2 个 `llvm-ts-user-*` 在飞动态跑遗留名 + 9 个 `TESTCASES-051t-*` 于 09:25–09:40 由后续任务写入）⇒ 判「过期快照」非伪造，但该数应补测量时刻（我不改完成区，交收尾）；⑥ 「A2 0 目录」现为 19 目录（后续任务所建、全 PASS）——同为时间漂移。

**发现**（非阻断，已登记 `ISS-282`）：① 子集跑→`authoritative/` 无驱动/门控强制；② `Process-08` §1.1 的 `finished_utc` A2 不查（文档严于门控）；③ `INFLIGHT_LEGACY` + baseline 过渡豁免待搬迁任务后删除。另披露：落地提交 `d003468` 除完成区「修改文件」所列外还改了 `.tao/knowledge/milestones.md`（INFRA-093t 行，台账登记 2 字段）——完成区声明漏列，交收尾补正。

**判决：Accepted** —— 验收命令块在我自己的重跑下全过、7 条规矩逐条无违反、反例注入可达 FAIL 且已还原；上述 4 项均为非阻断遗留/披露，交 architect 定夺。**声明**：未改完成区 / `**状态**`；未 `git add`/`commit`/`push`；注入均 `cp`+md5 还原（md5 全等），收尾快照 `git status --porcelain -uall` = 0 行，与开工一致。
