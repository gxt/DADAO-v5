# ADR-0016: DADAO 安装根与产物布局（`.dadao/` 重定位）

**状态**：Accepted
**日期**：2026-10-02
**关联**：ADR-0002（构建编排）、ADR-0004（测试机）、ADR-0005（组件锁多源）、ADR-0009（QEMU harness 方法论）；任务：待建（`INFRA-019t` 起，编号待定）

## Context（背景）

- 当前**无 install 概念**：LLVM/QEMU 均为 `.work/build/{llvm,qemu}` 的 out-of-tree 构建，门控与执行器**就地**取可执行（如 `run_qemu_test.py` 默认 `.work/build/qemu/qemu-system-dadao`）。无 `--prefix`/`DESTDIR`/sysroot。
- `.dadao/` 当前是**参考仓库只读工作树**（`.dadao/DADAO-0628`、`.dadao/DADAO`），由 `make fetch-refs` 重建，位于 `.gitignore`；被 `manifests/references.lock.toml`、`README.md`、`AGENTS.md`、`.tao/knowledge/MEMORY.md`、`tools/infra/{fetch_refs,status}.py` 引用。
- 目标：① 产物 install 根化，**免重建复用**；② 区分 **host 工具链**与 **target sysroot**（交叉编译头部/库）；③ 测试向量**运行产物**归位；④ **定位机制**单一真源，支持改名；⑤ 便于后续 Dockerfile 从单一根抓取。
- 约束：`tests/vectors/**` 为**独立 oracle、必须入库**，**不得**移入 gitignored 目录；不得弱化任何门控；保留"从源码重建"的能力。
- 路径约束：`/home/ubuntu/tao` 是指向 `/mnt/tao` 的**符号链接**；脚本须统一使用**真实路径**。

## Decision（决策）

> D1–D11 已于 2026-10-02 经用户**逐条确认**（全部保留）。

- **D1**：`.dadao/` 重新定位为 **DADAO target SDK 安装/产物根**（gitignored，不入库）；**不再**承载参考仓库。
- **D2**：参考仓库**工作树**迁至 **`.cache/refs/<id>/`**，与其**裸镜像** `.cache/refs/<id>.git`（路径已由 ADR-0002 约定，**不变**）同处；`manifests/references.lock.toml` 的 `path` 由 `.dadao/<id>` 改为 `.cache/refs/<id>`；同步 `tools/infra/fetch_refs.py`、`tools/infra/status.py`、`.gitignore` 与 `README.md`/`AGENTS.md`/`MEMORY.md`。
- **D3**：**host 工具链 prefix = `.dadao/cross-toolchain`**（用户锁定）。LLVM 经 `cmake --install` 安装至此。
- **D4**：**QEMU 的 host 可执行 install 到 `.dadao/cross-toolchain/bin`**（与 LLVM 工具同根；用户锁定）。
- **D5**：**target sysroot 根 = `.dadao/dadao-unknown-elf`**（含 `include/`、`lib/`）。
- **D6**：**测试向量运行产物根 = `.dadao/tests/`**（用户锁定）；`tests/vectors/**` 的**向量源不移动**（独立 oracle、须入库）。
- **D7**：**统一"定位机制"**：单一真源（`manifests/` 新字段，如 `install_root`/`sysroot`/`artifact_root`）+ 解析模块（供 Makefile 与 Python 共用）；脚本/Makefile **禁止硬编码**这些路径；**改名只改一处**即生效。
- **D8**：**路径规范化 = 真实路径**（`/mnt/tao/...`）：Python 保持 `Path(__file__).resolve()`，Makefile 用 `$(realpath …)`；`~/tao` 仅作交互便利；加**机械守卫**防混用（同一产物路径不得同时出现两种前缀）。
- **D9**：**门控/执行器**（`run_qemu_test.py`、lit、各 `check_*`）改从 **install 根**取可执行；`.work/` 仅作 **build 区**；**保留从源码重建**路径（install 只是缓存）。
- **D10**：后续 **Dockerfile 从 `.dadao/` 抓取**（本 ADR 仅记方向，不实现）。
- **D11**：**install 范围 = 只装所需工具集**（用户锁定）：如 `llvm-mc`/`llvm-objdump`/`FileCheck`/`not`（+ 现有构建目标集），**不做** `cmake --install` 全量安装。

### 目标布局

```
.cache/                              # 持久对象库（gitignored）
├── llvm-project.git   qemu.git      # 组件裸镜像（现有）
└── refs/
    ├── DADAO-0628.git   DADAO.git   # 参考裸镜像（现有，ADR-0002 约定）
    ├── DADAO-0628/                  # 参考工作树（从 .dadao/ 迁入，D2）
    └── DADAO/

.dadao/                              # DADAO target SDK 安装/产物根（gitignored）
├── cross-toolchain/                 # host 工具链 prefix（D3）
│   ├── bin/                         # llvm-mc, llvm-objdump, FileCheck, not,
│   │                                #   qemu-system-dadao …（D4）
│   ├── lib/  include/  share/
├── dadao-unknown-elf/               # target sysroot（D5）
│   ├── include/
│   └── lib/
└── tests/                           # 测试向量运行产物（D6）
```

## Rationale（理由）

- **`.dadao/` 重定位 vs 另起新名**：`.dadao/` 语义上就是"DADAO 目标世界"，重定位后可成为单一 SDK/打包根，利于 Dockerfile 抓取；代价是需把参考仓库移出（D2）。
- **参考仓库放 `.cache/refs/`**：与裸镜像同区，`fetch-refs` 行为不变，只是工作树路径改；`.cache/` 本就是 gitignored 的持久对象库。
- **host / target 分离**（D3 vs D5）：`llvm-mc`、`qemu-system-dadao` 是**跑在开发机**上的可执行；交叉编译所需的 `include/lib` 才是 **target sysroot**。二者混放会污染语义、妨碍 Docker 打包。
- **只装所需工具集**（D11）：`cmake --install` 全量安装体积大且含无关组件；限定集合可显著减小 SDK 体积。
- **定位机制单一真源**（D7）+ **真实路径**（D8）：支持改名（用户明确要求）并消除 `~/tao`↔`/mnt/tao` 混用导致的构建缓存/门控不一致。
- **否决**：把 `tests/vectors/**` 向量源移入 `.dadao/`（破坏"入库 + 独立 oracle"）；把参考仓库与安装根混在同一目录（语义撞车）。

## Consequences（影响）

- **正面**：产物可复用（免重建）；SDK 单一根，便于 Docker/分发；host/target 语义清晰；路径与定位可改名、可守卫。
- **负面/成本**：
  - 移动参考路径波及 `status`/`check_spec_drift`（README 组件映射）/文档；迁移后需重跑 `make fetch-refs`。
  - 门控改路径若不彻底会**假绿** ⇒ 须以"注入反例"证明门控仍承重。
  - install 增加磁盘占用（受 D11 限制）。
  - 引入 install 步骤 ⇒ 需保证"**从源码可重建**"不被 install 缓存掩盖（`.work` 仍为唯一构建真源）。
- **后续约束**：新增脚本/目标必须经 D7 定位机制取路径，禁止硬编码；产物路径一律真实路径；Dockerfile 从 `.dadao/` 抓取。

## 状态说明

- 本 ADR 已于 2026-10-02 由用户**逐条确认 D1–D11（全部保留）** ⇒ 置 **Accepted**。
- 落地任务：`INFRA-019t` 起（编号与拆分见后续；改共享文件的任务须**串行**）。
- 决策若后续变更：**新增 ADR 或标 `Superseded`**，不直接改写已 `Accepted` 的决策。
