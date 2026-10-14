# INFRA-071t: `contract-*.md` 迁入 `contracts/`（Phase B）+ `check-contracts-dir` 白名单门控

**模块**：infra
**项目里程碑**：M8
**依赖**：**用户授权**（`INFRA-071t` 立项后由主会话问；**未获授权前不得开工**）
**状态**：待开始

> **立项来源**：`INFRA-070t`（`.tao/knowledge/` 顶层收拢）**Phase A 已完成并 reviewer `Accepted`（主会话收尾）**；**Phase B**（9 个 `contract-*.md` → `contracts/`）因**硬约束冲突**停手 ⇒ 本任务承接（`INFRA-070t` 完成区「遗留问题」+ 第 1 轮 reviewer §⑧）。
>
> **用户裁定原话（2026-10-13，追加）**：「`【INFRA-071t】它的项目里程碑归属怎么定？` / 用户选择 = **改标 M8（推荐）**」（2026-10-13）——本项目里程碑字段由 `M7` 改标为 `M8`（**只改该字段**；任务书仍留 `.tao/tasks/`、不归档）。

## 背景：Phase B 停手原因（引用冲突**逐类计数**）

`INFRA-070t` 的硬约束 = **「不改 `spec/`、`contracts/`、组件补丁」**，只动范围 = `docs/**`、`.tao/knowledge/**`、`.tao/archive/M7/notes/**`、`tools/llvm/**`、`Makefile`、`tools/infra/**`、任务书。而旧路径 `.tao/knowledge/contract-*.md` 的引用**均落在只动范围之外**：

| 类 | 命中（`git grep '\.tao/knowledge/contract-'`，现场行数） | 性质 |
|---|---|---|
| `spec/Toolchain-01-汇编语言.md` | 5 | **只读哈希锁册**（`manifests/spec-readonly.lock.toml` 的 `path`+`sha256`）⇒ 改须**用户事先授权**（`Process-06 §2`） |
| `spec/README.md` | 2 | v5 自定册（不在锁内，但 `spec/` 改动仍须授权） |
| `contracts/`（4 `*.yaml` + `README.md`） | 8 | 含 `abi.yaml` 的 `contract:`（`:30`）/`detail_contract:`（`:59`）**嵌套字段**（**机器读取值**）⇒ 与「内容不动」冲突 |
| `tools/**` | 36 | 生成器/校验器/探针硬编码旧路径（如 `check_fp_contract.py`）；其中 `tools/{testcases,qemu,integ}` = 17 |
| `components/**`（补丁注释 / README） | 13 | 组织/生成/应用/校验受 `docs/Process-01` 约束 |
| `tests/**`（README / 向量脚本） | 12 | 向量/README 引用 |

> 计数为本任务书立项时**现场实测**（`git grep -c`，按行）；`contracts/` 8 = `abi.yaml` 4 + `fp_semantics.yaml`/`legality_rules.yaml`/`opcodes.yaml` 各 1 + `README.md` 1。**执行时须重测**，不采信本节写死值（**计数不写死**）。

**结论**：Phase B **不是**纯 `.tao/knowledge/` 内操作——会触及**只读锁册**与 `contracts/` **内容** ⇒ **须用户按下列待裁定项逐条裁定后方可开工**。

## 待用户裁定项（逐条列选项；立项后由主会话问）

1. **是否授权改只读锁册**：`spec/Toolchain-01-汇编语言.md` 在 `manifests/spec-readonly.lock.toml`（`path`+`sha256` 锁册）。选项：
   - (a) **授权改 + 重算** `sha256` 回填锁册（走 `Process-06 §2` 授权流程）；
   - (b) 授权改但**不重算**（会触发 `check-spec-readonly` 红 —— 不可取）；
   - (c) **不授权** ⇒ `spec/Toolchain-01` 保留旧路径（Phase B 引不同步，须缩范围）。
2. **`contracts/*.yaml` 内嵌旧路径字段如何处置**：`abi.yaml` 的 `contract:`（`:30`）/`detail_contract:`（`:59`）为**机器读取值**。选项：
   - (a) **同批改**新路径（**与「内容不动」冲突，须显式授权**）；
   - (b) **加映射 / 别名**（保留旧字段 + 新增转换层）；
   - (c) **不动**（该 2 字段将指向不存在路径 ⇒ 悬空，须登记 issue）。
3. **只动范围是否扩到 `tools/**` / `components/**` / `tests/**`**：选项：
   - (a) **全扩**（一次改净，含生成器/探针/README）；
   - (b) 仅扩 `tools/**`（生成器面）；
   - (c) **均不扩** ⇒ 引用不同步 ⇒ `check-knowledge-refs`/`check-spec-refs` 悬空红（不可取）。

> **不得臆造用户已授权**：以上三项未获用户**逐条确认**前，本任务 `**状态**` 保持 `待开始`，**不得 `/dispatch`**（`AGENTS.md`「下发前预检 #5」；类比「ADR decision 逐条确认」）。

## 接口规范

- **输入**：`INFRA-070t` §追加范围（下）+ 用户对上述 **3 项**的逐条裁定。
- **输出**（沿用 `INFRA-070t` §追加范围）：
  1. **9 个 `contract-*.md` 迁入 `contracts/` 顶层**（**禁**建子目录 ✗；引用**全量同步**，现场 `grep` before/after 计数）。
  2. **命名**：**不统一前缀** ⇒ 4 个 `*.yaml` **不改名**；`.md` **保留 `contract-` 前缀**。
  3. **格式**：**保持 YAML**（不转 TOML）。
  4. **`contracts/README.md`** 内容 = **两张清单**（叙述型 `.md` / 机器数据 `.yaml`，逐行一句话）+ **一行指针** → `spec/README.md`「投影表」+ **一行分工规则**：*"扁平锁/清单 → TOML（如 `manifests/*.toml`）；嵌套合约数据 → YAML（本目录）"*。
  5. **`check-contracts-dir` 白名单门控**：`contracts/` 顶层**只允许** `*.yaml` / `contract-*.md` / `README.md` / 子目录 ⇒ 白名单外即 **FAIL**；**纳入 L1**。
- **约束**：**不改** `spec/`（除裁定项 1 授权范围）、`tests/vectors/`、组件补丁（除裁定项 3 授权范围）；**计数不写死**。

## 验收标准

（沿用 `INFRA-070t` §验收 **8–10**，全部以**现场真实输出**为准）

8. **迁入生效**：`contracts/` 顶层含 **9 个** `.md`（`ls` 证据）；**旧路径 `.tao/knowledge/contract-*.md` 不再存在**；引用全量同步（`grep` before/after 计数）；`check-knowledge-refs` rc=0。
9. **命名/格式未动**：`git diff --name-status` 显示 4 个 `*.yaml` **无 `R`（未改名）**、内容未变；`contracts/README.md` 含两清单 + 指针 + 分工规则（`grep` 真实输出）。
10. **`check-contracts-dir`**：常态 rc=0；注入白名单外文件 ⇒ **FAIL** ⇒ 还原 ⇒ 回绿；**已入 `make check`**。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-071t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；显式 staging（禁 `git add -A`）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动**用户授权后**的范围；越界须披露。
5. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
6. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
7. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
8. **计数不写死**。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 用户授权落纸（2026-10-14，architect 追加；**只追加**）

**用户裁定（2026-10-14，原话 = 「1、a；2、a；3、a」；渠道 = 经主会话问答）**——对应上文 §待用户裁定项 逐条：

| 待裁定项 | 裁定 | 性质 / 备注 |
|---|---|---|
| ① **只读锁册** `spec/Toolchain-01`（`manifests/spec-readonly.lock.toml` 哈希锁册） | **(a) 授权改 + 重算 `sha256`** | 性质 = **引用同步**，**非语义改动** |
| ② **`contracts/*.yaml` 内嵌旧路径字段**（8 处） | **(a) 改字段值指向新路径** | `contract:` / `detail_contract:` 等 |
| ③ **只动范围** | **(a) 扩到 `tools/**` / `components/**` / `tests/**`** | **唯一能闭合**；⚠️ 写明：`components/**` **仅改注释** ⇒ **不重建**（构建成本规则豁免，理由留证） |

**结论**：**授权已得，可执行**（上述 3 项均已逐条裁定）。`**状态**` 仍为 `待开始`（**不改**），由后续执行任务推进。

## 审阅记录
