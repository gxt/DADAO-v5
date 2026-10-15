# INFRA-083t: `.cache/embench-iot` checkout 清理（`ISS-204` 转执行）

**模块**：infra
**项目里程碑**：M8
**依赖**：`INFRA-074t`（来源 = 其第 2 轮 reviewer「非阻断建议②」，`已验证`）；`INFRA-051t`（embench-iot 组件接入——`.cache/embench-iot.git` 裸镜像与该工作树由其建立，`已验证`；**只读**引用其结论）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 背景与立项来源
- **问题**：`.cache/embench-iot/`（无 `.git` 后缀）**不是裸仓库**，而是 **checkout**（`git -C .cache/embench-iot rev-parse --is-bare-repository` = `false`，目录内含 `.git/` 工作树，`du -sh` ≈ **30 MB**）。
- **违反的约定**：用户 2026-10-13 约定「`.cache` 下面应该是裸仓库，然后在 `.work` 下面有 `source` 和 `build`」——落 `AGENTS.md`「目录结构 / 工作区落点」+ `.tao/knowledge/lessons.md` 目录落点条目；同处的 `.cache/embench-iot.git`（**bare**，2.3 MB）才是约定形态。
- **来源**：`INFRA-074t` 第 2 轮 reviewer 验收「非阻断建议②」⇒ architect 登记 `ISS-204`（`open`，`scope: [infra]`，2026-10-14）。**本任务即 `ISS-204` 的执行落点**（转执行，2026-10-15，architect）。
- **性质**：历史遗留 / 落点不合约定（**非缺陷、非静默**）；正确的裸镜像**已存在且为超集** ⇒ 删除该 checkout **不丢可复现性**。
- **与 `DADAO-0628` 无对照**（纯本仓工作区卫生事项）。

## 目标
删除 `.cache/embench-iot/`（那个 checkout），使 `.cache/` 恢复「**只放裸仓库**」；**保留** `.cache/embench-iot.git`。

## 现场事实（architect 预核，2026-10-15；**执行时须重跑**）
| 项 | 观测值 |
| --- | --- |
| `.cache/embench-iot` `--is-bare-repository` | `false`（确为 checkout，非裸仓库） |
| `.cache/embench-iot` `status --porcelain`（**含** `--ignored`） | **空**（工作树干净、无未跟踪/被忽略残留） |
| `.cache/embench-iot` `HEAD` | `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70` |
| `.cache/embench-iot.git` `--is-bare-repository` / `HEAD` | `true` / **同值** `09c2ed8c…`（== `manifests/components.lock.toml` `name = "embench-iot"` 的 `commit`） |
| checkout 的 9 个 ref（`master`/`origin/HEAD`/4× `origin/*`/4× tag） | 裸镜像中均有对应 ref；裸镜像另含 `refs/pull/*` ⇒ 裸镜像是**超集** |
| 独有对象检查 | checkout `rev-list --objects --all` = **1480 对象**，逐个在裸镜像 `git cat-file -e` **全命中、0 缺失** ⇒ **无独有对象** |
| `du -sh` | checkout ≈ **30 MB** vs `.cache/embench-iot.git` **2.3 MB** |
| git 归属 | `.gitignore` 含规则 `.cache/` ⇒ 删除**不产生 git 改动**（`git status` 不受影响） |

> 上表值以**执行时真实输出**为准；若与上表不符 ⇒ 按「安全核验」处置。

## 动手前必做的安全核验（**硬要求**；逐条留真实输出 + 退出码）
> **任一不过 ⇒ 停手、保留现场、报告**（**不得先删后查**；失败即为「需用户裁定」类留问）。
1. **身份核验**：`git -C .cache/embench-iot rev-parse --is-bare-repository` = **`false`**（确为 checkout）。若 = `true` ⇒ 停手报告。
2. **无独有内容**：`git -C .cache/embench-iot status --porcelain`（**应空**）；**若非空 ⇒ 停手报告**。建议加做**对象级**佐证：`git -C .cache/embench-iot rev-list --objects --all` 的 OID 逐个在裸镜像 `cat-file -e`（期望全命中）。
3. **HEAD 关系**：记录 checkout `HEAD`，与 `.cache/embench-iot.git` `HEAD` + 锁册 `commit` 比对；**若与 `09c2ed8c…` 有偏差 ⇒ 报告**（并说明是否影响删除）。
4. **可重建**：`.work/source/embench-iot`（若存在）能由裸镜像重建——`make fetch` rc=0（幂等），且**真实重建证据** = 由裸镜像 clone/fetch 到**临时目录** rc=0 且 `git -C <临时目录> cat-file -e 09c2ed8c…^{commit}` rc=0。
   （重建能力真源 = 裸镜像含锁册 `commit` 的全部对象；`tools/infra/fetch.py` 只以 `.cache/<name>.git` 作 mirror，**不读** `.cache/embench-iot/`。）

## 范围
**做**：删除 `.cache/embench-iot/`（`rm -rf`，**删除前先过上面 4 项**）+ 删除前后取证 + 重建验证 + 门控 + `ISS-204` `notes` 追加「转执行」一句。
**不做**（✗）：
- **不删** `.cache/embench-iot.git`（裸镜像，`fetch` / 锁册依赖）；
- **不动** `components/embench-iot/**`（补丁集**入 git**、不受影响）；
- **不改** `manifests/components.lock.toml`；
- **不清理** `.work/source/embench-iot`（构建源；本任务范围外）。

## 验收标准
1. **安全核验 4 项全过**，逐条**真实输出 + 退出码**留证 `.work/evidence/<任务ID>/`（任务 ID = `INFRA-083t`）。
2. **删除前后对照证据**：删前 `du -sh .cache/embench-iot`（≈30 MB）+ `ls -d`；删后 `.cache/` 列出**无** `embench-iot`（仅 `embench-iot.git`）、`git -C .cache/embench-iot.git rev-parse HEAD` 与删前**同值**。
3. **重建仍可行**：删除后 `make fetch` rc=0（幂等；日志含 `embench-iot.git already has 09c2ed8c3b70`〔或等价〕）+ 由裸镜像重建到**临时目录** rc=0 + `make status` rc=0（`status.py` 输出正常、无新增 `unavailable`）。
4. **门控**：`make check`（L1）rc=0 + `make check-patch-tree` rc=0。
5. `.tao/knowledge/issues.yaml`：`ISS-204` `notes` **只追加**一句「转执行：落点 = `INFRA-083t`（2026-10-15，architect）」；`status` **保持 `open`**、`resolved_by` 保持 `null`（关闭留 `/complete`）；`python3 tools/infra/check_issues.py` rc=0。
6. 完成区与审阅记录按规范填写（完成区 ≤30 行）；长输出留 `.work/log/infra/`；临时产物一律 `/tmp/opencode/<任务ID>/`。

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
（审查者独立验证的重跑记录、约束核验、判决）
