# SPEC-178t: 术语清理：移除地址高 6 位的讨论期简写

**模块**：spec
**项目里程碑**：M10
**依赖**：当前 master
**状态**：已验证

## 背景

`addr[47:42]`（地址高 6 位）在讨论中曾有一个英文简写（即本任务文件名里的那个词），它不是正式术语。规范、ADR、contracts、索引和任务书中仍有使用，容易与 `cfxha`、`addr[47:42]` 混淆。用户已授权修改 spec。

## 目标

1. 将所有**活跃文档**中的该简写改为正式表述：
   - `简写 = 0` → `addr[47:42] = 0`；
   - `简写 = 1..63` → `addr[47:42] = 1..63`；
   - `简写 != 0` → `addr[47:42] != 0`；
   - 首次出现可写“地址高 6 位（`addr[47:42]`）”，后文统一用 `addr[47:42]`。
2. 覆盖范围：`spec/**/*.md`、`.tao/adr/**/*.md`、`.tao/contracts/**/*.md`、`.tao/tasks/**/*.md`、`docs/**/*.md`、`contracts/**`、`components/*/changelog.md`、`tests/**/*.md`。
3. **不改**：
   - `.tao/archive/**`、`.work/**`、`.dadao/**`、`.cache/**` 等历史/生成物；
   - 代码、测试脚本中的注释（除非该文件本身是文档）；
   - 任何语义、编号、接口、测试期望。
4. spec 版本/changelog/sha 按 `docs/Process-06` 规则处理；纯术语变更不得改变语义。

## 验收

- 活跃文档对该简写的全文检索命中为 0（扫描面与命令见 `.work/evidence/SPEC-178t/run.sh`）。
- `make check` rc=0；`check-spec-readonly`、`check-spec-changelog`、`check-knowledge-refs` rc=0。
- 不改 spec 语义；不动 QEMU/LLVM/测试期望。
- 证据 `.work/evidence/<任务号>/run.sh`：注入一个该简写残留→FAIL→删除→PASS；用 `cp`+md5 还原，禁止 checkout/restore。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 同步；临时目录 `/tmp/opencode/SPEC-178t/`。

## 约束

- 只做术语替换；不讨论/不修改 fence 定义。
- 不提交、不 push；不跑 full/夜跑。
- 每处替换保持原句可读；不能机械替换成 `addr[47:42]=0` 后语义含糊。

## 完成区

**状态**：已验证

### 修改文件
- `spec/DADAO-12-SEE-主管系统运行环境.md`：9 行 12 处术语替换（§2/§2.1/§2.2/§4.5/§5.2/§5.6、附录 0.7.3-rc）+ 附录补 1 条术语条目。
- `spec/DADAO-22-SBI-主管系统二进制接口.md`：2 处（§4 服务表 + 单 PTBR 注）+ 附录 0.7.3-rc 补 1 条。
- `spec/Machine-01-测试机运行环境.md`：1 处（附录 0.3.2-rc）+ 同段补 1 条。
- `manifests/spec-readonly.lock.toml`：上述 3 册 sha256 同笔重算 + 变更注释（Machine-01 旧注释同步改写）。
- `components/qemu/changelog.md`、`.tao/adr/adr-0039-…`、`.tao/adr/adr-0043-…`、`.tao/contracts/contract-see.md`：各 1 处。
- `.tao/tasks/integ/INTEG-038t-Step1-地址空间-PTBR-PTW.md`：2 处。
- 本任务书：正文改用语（被移除的词不再出现在内容中；文件名保留原词，路径不计入文档内容）+ 本完成区。
- `.tao/knowledge/milestones.md`：流水行状态 → 待验收，一句改动去掉旧简写。

### 验收命令与结果
- `bash .work/evidence/SPEC-178t/run.sh` ⇒ rc=0，passes=24 fails=0（A/B/C/D/E/F 六组，含注入→FAIL→还原→回绿 8 项自检）。
- A1 残留扫描（spec/.tao/{adr,contracts,tasks,knowledge}/docs/contracts/tests + 锁 + 5 个组件 changelog）命中 = 0。
- `make check` rc=0；`check-spec-readonly` / `check-spec-changelog` / `check-knowledge-refs` 各 rc=0（E1–E4 逐项打印）。
- 语义零漂移：8 个术语替换文件旧简写≡`addr[47:42]` 归一化后行多重集 diff = 仅 3 条附录条目，删除 0 行。
- D1 改动文件集 == 预期 11 个；D2 仓库内无未跟踪残留。

### 遗留
- 代码/测试脚本注释（`components/qemu/patches/**`、`tools/testcases/arch/min_rom_probe_integ038t.py`）按任务书「不改代码注释」保留原词，不在扫描面。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查 11 个改动文件 diff + 证据脚本（`run.sh` / `check_no_drift.py`）；判决：finding 全部处置，可待验收。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| §5.2 第 10 步替换时丢了「地址」二字（超出术语范围） | ✅已修 | 复原为「或地址 `addr[47:42] != 0` 时」 | C1 零漂移 PASS（归一化 diff 删除 0 行） |
| 完成区写任务书路径 ⇒ 路径含被移除词，A1 自命中 | ✅已修 | 改写为「本任务书」，不写路径 | A1 命中=0；F7 还原后回 0 |
| 先改 DADAO-12 后重算锁 sha，首次重算已失效 | ✅已修 | 再次重算（`4e1485b0…`） | E2 `check-spec-readonly` rc=0 |
| 任务书先引用 `.work/evidence/SPEC-178t/run.sh` 而脚本未落地 ⇒ `check-knowledge-refs` 悬空 FAIL | ✅已修 | 先落证据脚本再引用 | E1 `make check` rc=0 |
| 任务书正文保留原词会与「活跃文档 0 命中」冲突 | ✅处置（披露） | 正文改用正式表述 + 「简写」占位；文件名保留原词 | A1=0；任务书目标/验收语义未变 |
| spec 是否升版本号 | ✅判定 | 三册均处未发布 `-rc`（0.7.3-rc/0.7.3-rc/0.3.2-rc）⇒ 段内追加条目，不升号 | `check-spec-changelog` rc=0（册头==段首） |
| 扫描面是否覆盖锁/知识库 | ✅加严 | 扫描面 ⊃ 任务书覆盖（+`.tao/knowledge`、锁、全部组件 changelog） | A1 覆盖 8 目录 + 6 文件 |

### 第 1 轮 reviewer 验收（2026-10-29）

**重跑记录（独立执行，均 workdir 内相对路径）**：
- `bash .work/evidence/SPEC-178t/run.sh` ⇒ **rc=0，passes=24 fails=0**（A1=0 命中、C1 零漂移 8/8、D1 11 文件一致、D2 0 未跟踪、E1–E4 门控 rc=0、F1–F8 注入自检全过），与完成区声明逐条一致。
- 四门控单独重跑（退出码取被检命令自身）：`make check` rc=0；`make check-spec-readonly` rc=0；`make check-spec-changelog` rc=0；`make check-knowledge-refs` rc=0。
- 独立反例注入（与脚本自检不同文件：`.tao/adr/adr-0043-boot-handoff.md`，cp 备份 77e50786… + md5 对账）：注入后 `run.sh` **rc=1**（A1 FAIL 实际=1、结果 fails=4）⇒ `cp` 还原后 md5 相等、`run.sh` **rc=0 回绿**（passes=24 fails=0）。脚本有可达 FAIL 路径，非恒真。
- 快照对账：验收前/后 `git status --porcelain -uall` 逐行 diff 一致（11 个 M、无未跟踪残留）；spec 三册 + 锁 + adr-0043 md5 与注入前相同 ⇒ 注入已还原。
- 残留扫描独立重跑：`grep -RIn 'high6' spec .tao/{adr,contracts,tasks,knowledge} docs contracts tests manifests/spec-readonly.lock.toml components/*/changelog.md` ⇒ **0 命中**（rc=1=无匹配）；全仓残留仅 `components/qemu/patches/**` 与 `tools/testcases/arch/min_rom_probe_integ038t.py` 的代码/脚本注释——任务书明确排除、完成区已披露，符合约束。
- 版本/锁一致性：三册 sha256 现算 == 锁值（`4e1485b0…`/`2e4670b8…`/`eb5a2d47…`）；版本号未升（0.7.3-rc/0.7.3-rc/0.3.2-rc），附录条目段内追加，`check-spec-changelog` rc=0 佐证册头==段首；仅 3 册 sha 变更，其余 18 册未动。
- diff 逐行审查：11 个改动文件仅术语替换（`high6=X`→`addr[47:42] = X`）+ 3 条附录术语条目 + 锁注释/sha + milestones/任务书状态（待开始→待验收）；无语义/编号/接口/测试期望变化，归档/生成物未触碰。任务书/里程碑状态一致（均 `待验收`）。

**Finding（非阻断，留 architect 收尾处置）**：DADAO-12 §2.1 把 `（bits[47:42]）` 一并改为 ``（`addr[47:42]`）``（含加反引号）——超出「只替换 high6」字面范围，但归一化后语义等价（零漂移检查将其与 addr[47:42] 视为同一位段）、无语义影响；同册 §5.2 仍有裸写 `bits[47:42]`，风格不完全统一，可留待后续。

**判决：Accepted**——验收命令全部在 reviewer 自身重跑下通过、约束无违反、注入→FAIL→还原→回绿真实。可提交（提交权归 architect）。
