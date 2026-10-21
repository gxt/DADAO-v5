# INFRA-101t: 新鲜度门控改用内容标识（build-id）替代 mtime 代理

**模块**：infra
**项目里程碑**：M9（工程效率）
**依赖**：`INFRA-096t`（新鲜度门控落地）、`INFRA-098t`（`llvm-nm`/`llvm-readelf` 入安装根）、`INFRA-099t`（门控互斥，已落地）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现状（**先读，勿重复查证；仍须现场复核**）

### 现象（2026-10-22，`LLVM-122t` 夜跑现场）

- 改 `.td` ⇒ `build-mc` 重 link `clang`（确定性构建，**内容逐字节相同**）⇒ 安装根里 `clang` 的 **mtime 变**；
- `check-musl-freshness` / `check-builtins-freshness` 双双判 stale ⇒ 强制重建 musl / builtins；
- 因 L2（`check-modules`）经 `test-semihost` **内嵌 `install-host`**，一次 L2 就触发一次重装 + 重建；
- engineer + reviewer 各跑一次 L2 ⇒ **双倍**。`LLVM-122t` 单册因此耗时 **4 h 28 min**（其余 FP 册 ~20 min）。

### 现场事实（代码位置，2026-10-22 核）

- `tools/infra/build_musl.py:276-288`：`toolchain_stamp()` 对 `STAMP_TOOLS = ("clang","ld.lld")` 生成
  `"<tool> -> <realpath> size=<bytes> **mtime=<ns>** <--version 首行>"`，写入 `obj/.dadao-toolchain-stamp`；
  `check_musl_freshness.py` 重算并**逐字比较**。
- `tools/infra/check_builtins_freshness.py:187-207`：判据是 `archive mtime >= clang mtime` 与"归档成员 mtime 不早于 clang"。
- `Makefile:401-402` 的 `atomic-install` = `cp -aL` + `mv`（**mtime 由 `cp -a` 保留**；问题不在拷贝，在**源被重建**）。
- `ctime` 已在 `ISS-263` 中明确排除（重拷贝会 bump ctime，不是工具链变化）。
- **两个工具都带 GNU build-id**（现场 `readelf -n`）：
  - `clang`：`de2e20d7e585817e19924fa5b26746ca5099cb59`
  - `ld.lld`：`585596725c4908cd13d42a9b4303dbfc77ec6a55`

### 结论

现状**并未判断"内容是否变化"**，只判断 mtime；确定性重建 ⇒ 假 stale。应改为**内容派生标识**。

## 目标

1. `toolchain_stamp()` 用 **build-id**（无 build-id 时退 `sha256`）替代 `mtime`；
2. builtins 门控用"**归档构建时记录的 clang build-id** == 当前 build-id"替代 mtime 排序；
3. **旧 stamp 迁移**：无 build-id 的旧 stamp ⇒ 首次判 stale（一次重建），并在输出里明示"migrating stamp"；
4. 结果：**重建但内容相同 ⇒ 绿**；**内容真变 ⇒ 红**。

## 接口规范

- **输入**：`tools/infra/build_musl.py`、`tools/infra/check_musl_freshness.py`、`tools/infra/check_builtins_freshness.py`、`Makefile`（builtins 归档处需写 sidecar 记录）。
- **输出**：
  1. build-id 读取实现（**优先纯 Python 解析 ELF note**，避免依赖 `readelf` 是否存在；退路 `sha256` 且打印警告）；
  2. musl stamp 新格式（含 `build-id=`，不含 `mtime=`）；
  3. builtins sidecar（如 `obj/.dadao-builtins-toolchain`，记录 `clang build-id` + `ld.lld build-id`）与门控改写；
  4. 两个门控各自 `--self-test` 覆盖新判据；
  5. 证据 `.work/evidence/<任务ID>/run.sh`。
- **约束**：不改构建产物本身、不改 `spec/`/`contracts/`、不改门控**语义**（仍要求"对象由当前工具链产生"）；不 commit/push。

## 设计要点（**不预设唯一实现**，但下列各点必须覆盖）

### A. 内容标识

- 主：ELF `NT_GNU_BUILD_ID`（读 note，成本 KB 级）；两个工具均有 ⇒ 正常路径不退化。
- 退路：无 build-id（非 GNU ld 工具链）⇒ `sha256`（并打印一次警告，说明成本）。
- **禁止**把 mtime/size 作为"内容"判据的任何组成部分（size 可留作显示，不作判据）。

### B. musl stamp

```
clang -> /path/to/clang build-id=de2e20d7… <--version 首行>
ld.lld -> /path/to/ld.lld build-id=5855967… <--version 首行>
```

- 旧格式（含 `mtime=`）⇒ 视为 stale + 打印 `stamp format migrated`；
- 比较仍是**逐字字符串相等**（最小改动）。

### C. builtins 门控

- 归档生成处写 sidecar：`clang build-id=<...>`、`ld.lld build-id=<...>`、`source digest`（沿用既有 source stamp 思路）；
- `check_builtins_freshness.py` 判据改为 sidecar 的 build-id == 当前 build-id；**不再**用 mtime 排序；
- 旧归档无 sidecar ⇒ stale（一次重建）。

### D. 不得借机放宽

- 其它断言（成员清单、source digest、`--self-test` 的注入）**保持不动**；只替换"工具链是否变化"的判据。

## 验收标准

1. `toolchain_stamp()` 输出**不含 `mtime=`**、含 `build-id=`（现场打印）。
2. **仅 mtime 变**（`touch` 安装根 clang）⇒ **两个门控都绿**（真实输出）。
3. **内容变**（改 stamp 里记录的 build-id，或换一个不同 build-id 的二进制到临时树）⇒ **红**（真实输出）。
4. **真实工作流**：`touch` 一个 `.td` 源 → `make install-host`（重 link，内容相同）→ `make check-musl-freshness` **rc=0**、`make check-builtins-freshness` **rc=0**，**无需** `build-musl-shared`。
5. **旧 stamp 迁移**：把 stamp 写回旧格式 ⇒ 判 stale 且输出含 `migrated`；重建后转新格式。
6. 两个门控 `--self-test` 全绿，且**新增注入各可达 FAIL**（内容变必须红 / 仅 mtime 变必须绿）。
7. `make check`（L1）rc=0；`make check-modules`（L2）rc=0；`check-run-artifacts` rc=0。
8. 完成区 ≤30 行、与真实输出逐条对齐；`milestones.md` 一行。

## 做（阶段）

1. 现场复核（stamp 路径、builtins 门控逻辑、build-id 读取方式）。
2. 实现 build-id 读取 + musl stamp 改造 + 迁移提示。
3. builtins sidecar + 门控改写。
4. 四种注入（mtime-only 绿 / 内容变红 / 旧 stamp 迁移 / 正常重建绿）。
5. L1/L2 + 完成区。

## 可达 FAIL（**≥2，须真实注入并回绿**）

- 仅 `touch` clang（mtime 变、内容不变）⇒ 期望**绿**；若实现仍用 mtime ⇒ 红（证明判据确实换了）。
- 把 sidecar/stamp 里记录的 build-id 改成另一个值 ⇒ 期望**红**；还原 ⇒ 绿。

## 已知边界（**披露，不自行扩面**）

- 不改变 L2 内嵌 `install-host` 的结构（另一议题：`--no-rebuild` 快速路径）。
- 不处理 `clang` 无 build-id 的构建配置（退路 sha256 已覆盖）。
- 不动 `ISS-263` 的 ctime 排除逻辑。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
