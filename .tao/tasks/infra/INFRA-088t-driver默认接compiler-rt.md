# INFRA-088t: DADAO driver **默认**接 compiler-rt builtins（`ISS-262` 执行落点）

**模块**：infra
**项目里程碑**：M8
**依赖**：`INFRA-079t`（builtins 独立库 + `-rtlib=compiler-rt` opt-in 接线 + 安装规则；**待验收**）；`ISS-262`（用户裁定 ①，`open`）；`ADR-0027 D1`–`D5`（库范围/归属/共用口径）；`ISS-210`（安装根新鲜度）、`ISS-229`（重建/门控串行）、`ISS-263`（工具链戳记只用稳定内容属性）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 用户裁定

> **用户原话（逐字；渠道 = 经主会话问答，2026-10-17 深夜）**：「**ISS-262: 1；ISS-259：2；ISS**」
> 主会话据此复述请其确认的两条之一：`ISS-262` = ① **默认就接 compiler-rt** ✓

- **现状（`INFRA-079t` B1/B2 现场）**：driver **仅在**显式 `-rtlib=compiler-rt` 时追加独立 builtins archive；**默认（无 `-rtlib`）archive-free**，`-print-libgcc-file-name` 默认走 `libgcc` 分支。`ISS-262` 即此措辞差异（`ADR-0027 D5` 只规定「独立库、不属任何 libc、picolibc/musl 共用」，未规定默认选择）。
- **裁定**：**默认即接**——不带 `-rtlib` 的链接也追加同一独立 archive，且 `-print-libgcc-file-name`（默认）指向**真实存在**的 archive 路径。
- **前置证据已备（B2 实测）**：用 link-only wrapper 模拟「默认打开」⇒ `build-picolibc` 的 `libc.a`（md5 `f0a982a0…`）与 `build-musl-shared` 的 `libc.so`（sha256 `d5fa2da3…`）与正常构建**逐字节相同**，无重复符号 / undefined / 行为变化 ⇒ 默认切换在现有两消费方上**无观测回归**。

## 接口规范

- **输入**：`INFRA-079t` B1 的 driver 接线（`-rtlib=compiler-rt` 分支）与安装规则；`ADR-0027 D5`；B2 的模拟取证记录（`.work/log/infra/INFRA-079t-B2-*`、`.work/evidence/INFRA-079t-B2/run.sh`）。
- **输出**：
  1. `components/llvm-project/patches/clang/lib/Driver/ToolChains/DADAO.cpp.patch` **就地重导出**（默认分支追加 archive；「一文件一补丁」，`make_patch` 口径）；必要时同步 `components/llvm-project/changelog.md`（M8 条目）。
  2. 组件检出 `.work/source/llvm-project` 与补丁一致（`base+N`、`clean`）。
  3. 证据：`.work/evidence/<任务ID>/run.sh`（default + `--inject`）+ `.work/log/<模块>/**`。
  4. 本册完成区 + `milestones.md` 行 + `ISS-262` 处置（验收后 `closed` + `resolved_by: INFRA-088t`）。
- **约束**：
  - **最小 diff**：只改「默认选择」与 `-print-libgcc-file-name` 的默认指向；**不改** archive 内容/成员、不改 `-shared`/`-fPIC`/`-dynamic-linker` 口径、不改 lld/musl。
  - 显式 `-rtlib=compiler-rt` 行为**不变**；显式 `-rtlib=libgcc` 仍走原分支（不静默串 archive）。
  - **不改** `spec/`、`contracts/`、`.tao/contracts/**`（`docs/Process-06`）；不改测试集内容（`patchless`）。
  - 改 `components/**` ⇒ **必须** `make install-host`（`ISS-210`）；`install-host` 与 `build-*` **单跑、不并发**（`ISS-229`）、申报预计耗时、`JOBS=8`。

## 验收标准

1. **默认端到端（主判据）**：**不带 `-rtlib`** 链接含 libcall 的程序（复用 `INFRA-079t-A`/`B1` 的 **189 项独立 oracle** 与 **14 libcall 探针**，`-O0`/`-O2` 各一轮）⇒ link **rc=0**；`qemu-dadao` 运行 **rc=0**（大端）；`-###` 链接行含 builtins archive 路径（**真实存在**）。
2. **`-print-libgcc-file-name`（默认）**：输出路径 `exists=yes` 且与 `-rtlib=compiler-rt` 同值；显式 `-rtlib=libgcc` 行为不变（现场对比留证）。
3. **安装根复核**：`make install-host`（单跑）后，**默认**链接吃安装根 archive、端到端 rc=0；`make check-musl-freshness` **PASS**（`ISS-263` 口径：判据只用 size/mtime/版本串 + 产物 sha256）。
4. **无回归（构建）**：`make build-musl` / `make build-musl-shared` / `make build-picolibc` 各 rc=0；产物与改动前**逐字节相同**，或每处差异**逐条归因**（禁止「应该没影响」式结论）。
5. **无回归（测试，复跑四组）**：`TESTCASES-046t` 静态 **38/38**、动态 **38/38**；`TESTCASES-047t` 静态 **303 / 0 / 9 / 25**、动态 **298 / 0 / 8 / 31**；逐例与基线比对 **transitions=0**（列出比对脚本与输出）。
6. **可达 FAIL**：≥2 注入 —— ① 去掉默认追加 ⇒ 默认链接出现 `undefined symbol`（rc=1）；② 默认 archive 路径指向不存在文件 ⇒ 检查 FAIL；`cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）。
7. **门控（各留自身 rc）**：`make check`(L1)、`check-patch-tree`、`check-index-blobs`、`check-source-state`、`check-musl-freshness`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`check-component-changelog`、`python3 tools/infra/check_issues.py`。
8. 完成区（**≤30 行**）与真实输出**逐条对齐**；`ISS-262` 处置落纸。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-088t/`；命令一律在 **workdir（= 仓库根）** 内、**相对路径**；禁 `cd` 出界；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；**禁** `cmd | tee` 吞码；复杂输出留 `.work/log/infra/`。
4. **只动任务范围**，越界须披露。
5. **失败保留现场并继续推进**（派修 / 绕行 / 有据重试并记次数 / 登记后跳过）；**只在需用户语义裁定**时留问。
6. **计数不写死**；证据脚本 `run.sh` 非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」。
7. 改 `components/**` ⇒ 组件**最后一次** `commit --amend` 之后重建，再 `install-host`（否则安装根与补丁不自洽）。
8. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立重跑、约束核验、判决）
