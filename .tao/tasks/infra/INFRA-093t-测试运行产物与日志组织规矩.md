# INFRA-093t: 测试运行产物与日志的组织规矩（+ L1 门控 check-run-artifacts）

**模块**：infra
**项目里程碑**：M8
**依赖**：无（约束：本册**不动** `.work/log/testcases/**` 存量；搬迁另起一笔，且须等当前动态跑结束）
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
