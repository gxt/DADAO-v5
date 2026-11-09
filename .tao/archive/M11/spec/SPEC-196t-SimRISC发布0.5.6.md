# SPEC-196t: SimRISC 发布 0.5.6（版本与变更记录重整理）

**模块**：spec
**项目里程碑**：M11
**状态**：已验证

## 用户裁定（原话）

「SimRISC可以发布0.5.6，注意重新整理一下版本与变更记录」

## 背景

13 册 `spec/SimRISC-*` 册头现均为 `0.5.6-rc`（实测逐册确认）。`convert_f2i`（`ADR-0050`）等改动已全部落地并经 M11 验证，`-rc` 的发布时机已到。

## 目标

1. **版本发布**：13 册册头 `0.5.6-rc` → `0.5.6`；`SimRISC-00` 的索引/版本说明同步。
2. **变更记录重整理**（不是简单替换）：
   - 逐册检查现有变更记录是否「按重要性/主题归并」；散碎的同主题条目合并，重复条目去重
   - 确保每条只写「改了什么 + 影响面」，不复述实现细节
   - 倒序（最新在上）与 `check-spec-changelog` 判据一致
   - 13 册之间的同一改动（如 `convert_f2i` 六档舍入）表述一致，不各写一套
3. **只读锁同笔更新**：`manifests/spec-readonly.lock.toml` 的 13 册 sha256。
4. **引用同步**：`spec/README.md`、`contracts/` 中若写死 `0.5.6-rc` 的版本字符串，同步为 `0.5.6`（先 grep 确认范围）。

## 验收标准

1. `make check-spec-readonly` rc=0（13 册哈希同笔更新，其余册不变）
2. `make check-spec-changelog` rc=0（册头与附录首段一致、倒序、格式）
3. `make check-spec-drift` / `check-spec-numbering` / `check-spec-refs` rc=0
4. `grep -rn '0\.5\.6-rc' spec/ .tao/contracts/ docs/ contracts/` 为 0（历史归档/ADR/任务书除外，逐处确认）
5. 13 册版本行逐册核对一致（脚本统计打印，不写死）
6. `make check`（L1）rc=0
7. 完成区 ≤30 行、无运行期路径

## 非范围

- 不改任何指令语义、编码、合法性规则
- 不改已 Accepted 的 ADR
- 不发布 `Machine-v5`（其版本线独立，`m12-spec-001` 已置 `0.4.1-rc`）

## 说明

- 变更记录重整理**不得删掉历史事实**：合并条目可以，但要保留「何时改了什么」的可追溯性（日期/版本段可归并，条目内容不可丢）。

## 完成区

**测试结果**：验收 10/10（运行期证据脚本 normal），反例注入 4/4（`--inject`，均先 FAIL 再 md5 还原回绿）。
**修改文件**：`spec/SimRISC-00…12`（13 册册头；00 另含附录）；`manifests/spec-readonly.lock.toml`（13 sha256 + 授权注记）；`README.md`（标题 + 版本表）；`.tao/contracts/contract-isa.md`、`contract-fp.md`（仅版本头）；本任务书；运行期证据脚本（未入库）。
**验收结果**：
- `make check-spec-readonly` → `21 read-only spec volume(s) OK`，rc=0。
- `make check-spec-changelog` → PASS，`files=21 segments=48 rc_segments=8 bullets=228 simrisc_header_versions=['0.5.6']`，rc=0。
- `make check-spec-drift` / `check-spec-numbering` / `check-spec-refs` → PASS，rc 全 0。
- `grep -rn '0.5.6-rc' spec/ .tao/contracts/ docs/ contracts/ README.md` → 0 命中。
- 13 册逐册版本行现场统计：`count=13 unique=0.5.6`（无写死）。
- `make check`（L1）→ `repository checks (L1): PASS`，rc=0。
- 变更记录重整理：0.5.6 段 `12 → 8` 条（现场统计）；首行标注「编码不兼容」；同主题合并（编码面 3→1、格式转换 2→1、浮点语义 2→1、文档 1 条保留）。
**新发现/坑**：
- 变更记录自 SPEC-165t 起集中于 `SimRISC-00`（01–12 无附录），13 册同改动一致性由单一真源保证。
- 发布须同步根 `README.md` 已发布/在研版本与 `contract-isa`/`contract-fp` 版本头，否则 `check-spec-drift` 红。
- 新建 worktree 无安装根；L1 需共享 host toolchain，运行期符号链接解决（未入库）。
- 分支基线比 master 少「台账移入进行中」一笔，L1 台账 R1 会红；FF 至任务基线 `f6cfc06f` 后绿（未改台账内容）。
- 锁文件历史注释仍含旧 `0.5.6-rc` 字样（历史事实，按「不改写历史」保留）。
**遗留问题**：
- `check-spec-archive` 预期红：缺 `SimRISC-0.5.6` 归档（清单从 git 历史派生，须在发布提交落地后生成）。归档由 architect 在合并后执行 `python3 tools/spec/gen_spec_archive.py --apply` 并复跑；`spec/README.md` 无归档表，不需要回填（N3）。
- 按任务约束未 commit、未 push。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-09）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 12 条合并为 8 条是否丢历史事实 | ✅已核 | 按主题合并：编码面 3→1、格式转换 2→1、浮点语义 2→1，逐条映射保留 | C10 `old=12 new=8 missing=0` |
| F2 根 README / 合约版本头未随发布同步 | ✅已修 | 根 README 标题与版本表、`contract-isa`/`contract-fp` 版本头 → 0.5.6 | C6 drift PASS |
| F3 改册未同笔改锁 | ✅已修 | 13 册 sha256 同笔重算 + 授权注记 | C4 readonly 21 OK；C9 13/13 |
| F4 证据脚本 C10 初版误报（grep 转义/段范围） | ✅已修 | 限定 0.5.6 段并修正 `cmp\.` 匹配 | normal 10/10 |
| F5 worktree 基线缺台账提交致 L1 R1 红 | ✅已修 | FF 至 `f6cfc06f`（仅纳入台账状态，未改内容） | L1 PASS |
| F6 新 worktree 无安装根致 L1 缺 `llvm-mc` | ✅已修 | 运行期链接共享 host toolchain（未入库） | L1 PASS |
| F7 缺 `SimRISC-0.5.6` 归档 | ⏸延后 | 归档快照须取发布提交，提交前无法生成 | 见遗留问题 |

判决：无未修 finding（F7 为提交时序依赖，已留可执行指令）。

### 第 1 轮 reviewer 验收（2026-11-09）

**判决：Accepted** —— 验收 1–7 在 reviewer 亲自重跑下全过、约束无违反、反例独立注入可达 FAIL。

**重跑记录**（全部为 reviewer 本机执行，不采信完成区转述）：
- `make check-spec-readonly` → `21 read-only spec volume(s) OK`，rc=0
- `make check-spec-changelog` → `files=21 segments=48 rc_segments=8 bullets=228 simrisc_header_versions=['0.5.6']`，rc=0
- `make check-spec-drift` → `9 合约 / 错误 0`，rc=0；`check-spec-numbering` → `files=21 changelog=9`，rc=0；`check-spec-refs` → `1095 引用 / 失败 0`，rc=0
- `make check`（L1）→ `repository checks (L1): PASS`，rc=0（`_locked-check` 前置**不含** `check-spec-archive`）
- `grep -rn '0\.5\.6-rc' spec/ .tao/contracts/ docs/ contracts/ README.md` → 无命中（rc=1）；全仓其余命中逐处核为锁历史注释 / 任务书 / ADR / 归档 / 台账历史记录
- 13 册册头现场统计 `count=13 unique=0.5.6`；01–12 diff 各仅 1 行版本行；01–12 无版本段（单一真源在 00）
- 证据脚本 `normal` → `checks=10 failed=0` rc=0；`--inject` → `4/4 reachable FAIL + restore` rc=0（还原 md5 与快照一致）

**独立注入**（reviewer 自选，engineer 未用例）：
- A `SimRISC-00` 册头改回 `0.5.6-rc` ⇒ `check-spec-readonly` rc=**2**（MISMATCH 1/21）、`check-spec-changelog` rc=**2**（互锁组 `['0.5.6','0.5.6-rc']`）；`cp`+md5 还原 `f6ec4dc8…` ⇒ 双双 rc=0
- B 锁中 `SimRISC-07` sha 改一位 ⇒ `check-spec-readonly` rc=**2**（FAIL 1/21）；还原 `db409313…` ⇒ rc=0
- 终态对账：18 文件 `md5sum -c` **全 OK**；`git status` 与注入前快照**逐行一致**（18 行）

**约束核验**：18 改动文件与完成区「修改文件」逐项一致（13 册 + 锁 + 根 README + 2 合约 + 任务书）；工作树 **0 commit**、无 untracked 残留；`f6cfc06f` 仅改 `milestones.md` 1 行、**纯 ff 无 merge**；完成区 22 行 ≤30、无运行期路径；锁 13 sha 与实际文件逐一 MATCH、其余 8 册 same 且 MATCH。

**findings（文档级，不阻断，交 architect 收尾改）**：
- N1 新 0.5.6 段丢旧第 3 条的「（DADAO-12）」括注，建议回填
- N2 新段以「8 条浮点→整数」替代旧第 8 条的 8 个指令名；语义/计数均保留，清单在 `SimRISC-07 §1.1` 单一真源
- N3 遗留「回填 `spec/README.md` 归档行」**目标不存在**（该文件 100 行无归档表，全仓无 `| 0.5.x | <sha> |` 行）；0.5.5 后该动作已无门控要求
- N4 `check-spec-archive` 第二红 = worktree 缺 `.cache/refs/DADAO.wiki`（`make fetch-refs` 可解），属环境非发布；补缓存后仅剩 A1 红，完成区未区分

**三问**：① 归并**未丢事实**（12/12 逐条映射、0 整条删除，仅 N1/N2 两处细节省略）；② 锁**只动 13 册**（另 +4 行授权注记，其余 8 册逐字未动）；③ archive 遗留**处置合理** —— 该门控**不在 L1**（挂 `check-milestone`，Makefile 注释「结构与内容 sha 都不入 L1」），A1 红由发布必然产生（清单从 git 历史派生，`--list` 现无 `0.5.6` 条目、末版 `0.5.6-rc` 快照 = 当前 HEAD），快照须取发布提交 ⇒ 与 `SPEC-172t` L77/L81 同款路径；**归档由 architect 在发布提交落地后**执行 `python3 tools/spec/gen_spec_archive.py --apply` 并复跑 `make check-spec-archive`（`check-milestone` 触发点），不属本任务阻断。

#### 收尾（architect，2026-11-09 04:17）

- 判决 **Accepted**：reviewer 自跑五项门控全绿、独立注入（册头回 `-rc` / 锁 sha 改一位）均红且 md5 还原回绿。
- **变更记录归并**：旧 12 条 → 新 8 条**逐条映射 12/12、0 整条删除**；两处细节级省略已按 N1/N2 回填（`（DADAO-12）` 括注、8 个 f2i 指令名），锁同步重算。
- **锁**：21 条中 13 条 CHANGED 且 MATCH，其余 8 条不变。
- **N4**：`check-spec-archive` 的两类红已区分——A1（清单从 git 历史派生，发布前必然红）与「缺 `.cache/refs/DADAO.wiki`」（环境，`make fetch-refs` 可解）。
- 归档：合并后由 architect 执行 `gen_spec_archive.py --apply` + `make check-spec-archive`。
