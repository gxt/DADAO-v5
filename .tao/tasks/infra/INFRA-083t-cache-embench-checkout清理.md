# INFRA-083t: `.cache/embench-iot` checkout 清理（`ISS-204` 转执行）

**模块**：infra
**项目里程碑**：M8
**依赖**：`INFRA-074t`（来源 = 其第 2 轮 reviewer「非阻断建议②」，`已验证`）；`INFRA-051t`（embench-iot 组件接入——`.cache/embench-iot.git` 裸镜像与该工作树由其建立，`已验证`；**只读**引用其结论）
**状态**：已验证

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
**测试结果**：`.work/evidence/INFRA-083t/run.sh` 默认 23/23 PASS rc=0；`--inject` 14/14 PASS rc=0（3 条真注入 FAIL 路径 + `cp`+md5 还原回绿）；`--gate-only` 删除前 6/6 PASS / 删除后 8/8 PASS rc=0；`preflight.sh` 删除前 rc=0（`total=1480 missing=0 unique=1 unknown=0`）。
**修改文件**：① `.cache/embench-iot/`（**删除**；`.gitignore` 含 `.cache/` ⇒ `git status` 无变化）；② 新增 `.work/evidence/INFRA-083t/{run.sh, preflight.sh, unique-objects/8cfb515b….content}`；③ 新增 `.work/log/infra/INFRA-083t-{preflight,objects,unique-objects,gate-predelete,gate-postdelete,delete,run-final,inject}.log`；④ 本任务书（完成区 + 自审 + 状态）；⑤ `.tao/knowledge/issues.yaml` **未改**——`ISS-204` 的「转执行：落点 = `INFRA-083t`（2026-10-15，architect）」句已由 architect 于 `7c3080b` 追加（实测出现 1 次；`status: open` / `resolved_by: null` 未变）⇒ 不重复追加。
**验收结果**：①安全核验（删除前真跑，逐条留 `.work/log/infra/INFRA-083t-preflight.log`）：S1 `is-bare-repository`=`false` rc=0；S2 `status --porcelain --ignored` 空 rc=0；S3 checkout HEAD = bare HEAD = 锁册 `commit` = `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`；S4a `rev-list --objects --all`=1480，裸镜像 `cat-file -e` **全命中 missing=0**；S4b **强核验**（可达∪悬空=2418，其中悬空 938）：独有对象 **1 个**（见「新发现①」，已留证）。
②删除前后：`.cache/embench-iot` `30M` → `ls` rc=2（不存在）；`.cache/embench-iot.git` `2.3M`（apparent 2.2M）不变、HEAD 同值；`.cache/` 仅余 `*.git/` + `refs/`。
③重建：`make fetch` rc=0，日志含 `fetch: mirror embench-iot.git already has 09c2ed8c3b70; skipping fetch`；裸镜像 clone 到 `/tmp/opencode/INFRA-083t/` rc=0 且 `cat-file -e 09c2ed8c…^{commit}` rc=0；`.work/source/embench-iot` 仍可用 rc=0（未动）。
④`make status` rc=0，列出 `embench-iot enabled 09c2ed8c3b70…`，无新增 `unavailable`。
⑤门控 rc 全 0：`make check`=0（尾部 `repository checks (L1): PASS`）/ `check-patch-tree`=0（`129 patches OK`）/ `check-no-residue`=0 / `check-tasks`=0 / `check_issues.py`=0（`35 open, 8 closed`）。
**新发现/坑**：① **独有对象强核验（可达∪悬空）发现 1 个悬空 blob** `8cfb515b17cd4db472d511a78b5570f4f42c916d`（20 B，内容 `# DADAO placeholder`，`git hash-object -w` 遗留）——architect 预核「无独有对象」只覆盖 `rev-list --objects --all`；已留证 + OID 重算一致（内容→OID 同值、字节可重建）⇒ 无不可复现损失、不阻塞；已把该口径固化为 `run.sh` 的 S4b 永久检查（建议核验口径补「∪ `fsck --unreachable`」）。② `fetch` 日志 `From …/.cache/embench-iot`（无 `.git`）**不是**依赖被删 checkout：git 显示 remote URL 时剥掉尾 `.git`（对照实验已证），`origin` 实为 `.cache/embench-iot.git`。③ `du` 单次调用按 inode 去重：`du -sh A B` 把硬链接块记给先出现者（bare 曾假显示 132K，实为 2.3M）⇒ 测量须**逐路径单独调用**。④ checkout 与 `.work/source/embench-iot`、bare 的 pack 是**硬链接同 inode（link=3）**⇒ 删 checkout 只减链，不释放裸镜像对象。
**遗留问题**：无。`ISS-204` 保持 `open`、`resolved_by: null`（**关闭归 `/complete`**）。

## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：本轮改动 = 删除 `.cache/embench-iot` + 新增 2 个脚本（`run.sh` 安全门/删除后不变量/注入自检；`preflight.sh` 删除前取证）+ 证据/日志。逐行审查后自纠 6 项、披露 2 项：

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 首轮 `--inject` 汇总 `FAIL=2`：安全门内部 `chk` 计数把**预期注入**的 FAIL 重复计入全局 | ✅已修 | 注入用例调用 gate 前后保存/恢复 `n_pass`/`n_fail`，判定只由外层 `chk` 承担 | `--inject` 由 `FAIL=2` ⇒ `PASS=14 FAIL=0` rc=0（`.work/log/infra/INFRA-083t-inject.log`） |
| F2 `du -sh A B` 单次调用按 inode 去重 ⇒ preflight 首版日志 bare 假显示 `132K`（与预核 2.3MB 不符） | ✅已修 | 改为**逐路径单独调用**并记录 apparent-size | 复测 `co=30M bare=2.3M`、`apparent bare=2.2M`（与预核一致，见 preflight 日志） |
| F3 preflight 的 `du(disk) co=… bare=…` 曾用同次去重值（误导） | ✅已修 | 同行改用独立调用结果并加注 | 同 F2 日志 |
| F4 `printf '[INFO ] P2 .cache/$NAME.git …'` 变量未展开（输出字面 `$NAME`） | ✅已修 | 改 `printf '… %s …' "$NAME"`，实跑核对 | `run-final.log` 打印 `.cache/embench-iot.git du -sh = 2.3M` |
| F5 `awk '{print $3}'` 解析 `git fsck --unreachable` 输出不鲁棒（非「unreachable <type> <oid>」行会被误取） | ✅已修 | 两脚本改 `grep -oE '[0-9a-f]{40}$'` | 临时 checkout 上等价性校验 `938 = 938`，且能捕获注入对象（`grep -c` = 1） |
| F6 `INJ0` 曾硬编码 `rc=0`（恒真，违反「禁恒真」） | ✅已修 | 捕获 `git clone` 真实 rc 后判定 | `--inject` 输出 `INJ0 … rc=0`（来自真实编码） |
| F7 `preflight.sh` 系**删除前一次性**脚本，删除后重跑会报错、易被误判为坏 | ✅已修 | 加显式守卫（`[ ! -d "$CO" ]` ⇒ 说明 + `exit 2` + 指路 `run.sh`） | 实测：`rc=2` + 说明输出（未产生误导性日志） |
| F8 悬空独有 blob（见「新发现①」）——非本轮引入，属**核验口径缺口** | ✅已处置（继续推进 + 披露） | 内容留证 + OID 重算校验；口径固化为 `run.sh` S4b 永久检查（未留证 ⇒ STOP） | `S4b unique=1 unknown=0 rc=0`；`--inject` 注入未留证对象 ⇒ STOP 且 FAIL 指名 S4b |
| F9 任务书「`ISS-204` notes 只追加一句」已由 architect 于 `7c3080b` 完成 | ❌不重复执行 | **不改** `issues.yaml`（重复追加会造成重复句） | `grep -c` = 1；`git show 7c3080b -- issues.yaml` 见该句；`status: open`/`resolved_by: null` 未变；`check_issues.py` rc=0 |
| F10 越界/副作用自查 | ✅无越界 | 仅删 `.cache/embench-iot`；未动裸镜像 / `components/embench-iot/**` / 锁册 / `.work/source/embench-iot`；未 `git add`/`commit`；注入还原一律 `cp`+md5（无 `git checkout/restore/stash`） | `git status --porcelain -uall` 仅本任务书 1 项；`.cache/` 仅余 `*.git/`+`refs/`；`INJ4/INJ5/INJ6` PASS；objects 日志 md5 注入前=还原后=`9cd0bd…` |

**判决**：F1–F8 已修/已处置、F9 不重复执行（附证据）、F10 无越界 ⇒ 无未修 finding；任务状态置 **`待验收`**。

#### 第 1 轮 reviewer 验收
**分支/快照**：`INFRA-083t-exec`（`16c3e71`）；审查前后 `git status --porcelain -uall` 均空、6 个目标文件 md5 逐一对账一致（含我注入还原后）；本次审查唯一写入 = 本审阅记录。
**重跑记录**（真实输出/退出码，workdir=仓库根）：
- 现状：`ls -d .cache/embench-iot` ⇒ rc=2（不存在 ✓）；`.cache/embench-iot.git` 在（`du -sh` = 2.3M ✓）；`.cache/*/` 9 个 `*.git` 逐个 `--is-bare-repository` = `true`，仅 `refs/` 非 git（只读参照树，既有正常形态）⇒ 无非裸目录 ✓。
- 可重建：bare `rev-parse HEAD` = `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70` = 锁册 `commit`；`cat-file -e …^{commit}` rc=0。`git clone --local` rc=128（`failed to create link: Invalid cross-device link`，`/tmp`=`/dev/sda1` vs 仓=`/dev/sdc1`，**环境因素**）⇒ 等价取证 `git clone` rc=0 且 `git clone --local --no-hardlinks` rc=0，克隆内 `cat-file -e 09c2ed8c…^{commit}` rc=0、HEAD 同值 ⇒ **可从裸镜像重建** ✓。
- `make fetch` rc=0，含 `fetch: mirror embench-iot.git already has 09c2ed8c3b70; skipping fetch`；`make status` rc=0 ⇒ `embench-iot enabled  09c2ed8c3b70…`，无 `unavailable` ✓。复核 finding②：`git -C .work/source/embench-iot remote -v` ⇒ `origin=/mnt/tao/DADAO-v5/.cache/embench-iot.git`（git 显示剥尾 `.git`）⇒ **不依赖被删 checkout**，成立 ✓。
- 门控：`make check` rc=0（`repository checks (L1): PASS`）/ `check-patch-tree` rc=0（`4 component(s), 129 patches OK`）/ `check-no-residue` rc=0 / `check-tasks` rc=0（2 条报告型提示、不阻断）/ `check_issues.py` rc=0（`35 open, 8 closed`）。
- 证据脚本：`run.sh` rc=0（PASS=23 FAIL=0）；`--inject` rc=0（PASS=14 FAIL=0，`[FAIL] S2 dirty`/`S4b unique`/`EV objects` 三条真 FAIL 路径实见）；`--gate-only` rc=0（PASS=8 FAIL=0，删后 8 项与完成区一致）。
- **reviewer 独立反例注入**：篡改留证内容文件（+1 字节）⇒ `--gate-only` **rc=1**、`[FAIL ] EV unique: 留证对象可重建`（`missing=1`，指名 `8cfb515b…`）；`cp`+md5 还原（`db1be3fa…` 前后一致）⇒ 重跑 rc=0（PASS=8 FAIL=0）⇒ 可达 FAIL 路径真实。
**脚本审核**：`run.sh` 逐条核 S1–S4b 均有可达 FAIL 路径（`gfail`/`chk` 按真实 rc 判定，无恒真；INJ0 捕真实 clone rc）；覆盖计数现场统计（`wc -l`/循环）非写死；注入还原 `cp`+md5（INJ7/INJ9/INJ10）无 `git checkout/restore/stash`；`preflight.sh` 有删除后守卫（rc=2 + 指路 `run.sh`）✓。
**独有悬空 blob 独立结论**：留证日志记 `all-oids=2418（reachable=1480 ∪ unreachable=938）unique=1`；内容文件 20 B `# DADAO placeholder\n`，`git hash-object --stdin` 重算 = `8cfb515b17cd4db472d511a78b5570f4f42c916d`（= OID ✓）；裸镜像 `cat-file -e` rc=1（确为独有 ✓）；临时树 `printf '# DADAO placeholder\n' | git hash-object -w --stdin` 重得同 OID（**字节可重建** ✓）。**删掉可接受**：内容全量留证且可字节重建，无不可复现损失 ⇒ 非 finding；口径已固化 S4b ✓。
**约束核验**：① 只读核验 `.cache`，未做任何删除/移动（`make fetch` 幂等后 bare HEAD 与目录状态不变）✓；② 相对路径、未出界 ✓；③ 未 `git add`/`commit`/`push` ✓；④ 还原一律 `cp`+md5 ✓；⑤ 完成区未改（12 行原样）✓；⑥ 完成区「修改文件」对齐：`git show --stat 16c3e71` 仅任务书，`issues.yaml` 未动（转执行句 `grep -c`=1，来在 `7c3080b`；`status: open`/`resolved_by: null` 未变）✓；⑦ 遗留「无」成立（`ISS-204` 关闭归 `/complete`）✓。
**非阻断备注**：验收口径「`git clone --local` ⇒ rc=0」在 `/tmp` 跨设备场景不可达（EXDEV 硬链失败），建议口径改「clone（允许 copy 回退）」。
**判决**：**Accepted**——验收标准 1–6 全过、无未修 finding；独有悬空 blob 判「可字节重建、无不可复现损失」证据充分、删掉可接受。
