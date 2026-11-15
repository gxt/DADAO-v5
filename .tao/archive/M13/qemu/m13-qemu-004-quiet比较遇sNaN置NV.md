# m13-qemu-004: quiet compare 遇 sNaN 置 `NV`（跟 IEEE）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-qemu-003`（已合入，signaling 口径）+ `m12-chipyard-014`（合入后再派，避免改差分参照，见 `ISS-395`）
**可并行分片**：否（单组件单写者）
**状态**：已验证

## 用户裁定（2026-11-12，原话）

> 「改为置 NV（跟 IEEE）」

落盘：`.tao/knowledge/discussing.md`「已裁定：quiet compare 遇 sNaN 也置 `NV`」。

## 背景

`m13-qemu-003` 已实现：signaling compare（`ftscmp`/`foscmp`）任何无序 ⇒ `NV`；quiet compare（`ftqcmp`/`foqcmp`）恒不置。

IEEE 754-2019 §5.11 要求 **quiet 谓词遇 sNaN 仍置 invalid**（hardfloat 同）。用户裁定跟 IEEE。

**两条裁定不冲突**：
- signaling：任何无序（含 qNaN 操作数）都置
- quiet：**仅 sNaN** 置（qNaN 输入不置）

## 目标

1. `ftqcmp`/`foqcmp`：任一操作数为 **sNaN** ⇒ 置 `NV`；qNaN 输入**不置**。
2. 结果值不变（无序 ⇒ q 版回 qNaN）。
3. 不得顺带改其它标志路径。

## 验收标准

1. 四组例 × ft/fo 逐条给输出（`rd6` = `rf0[4:0]`）：
   - `ftqcmp(sNaN, 1.0)` ⇒ **`0x1`**
   - `ftqcmp(qNaN, 1.0)` ⇒ **`0x0`**
   - `ftscmp(qNaN, 1.0)` ⇒ `0x1`（保持 003 的口径）
   - `ftqcmp(1.0, 2.0)` ⇒ `0x0`
2. `check-inst`（Vast 991/996、Tiny 44/44）rc=0；273 例 md5 不变。
3. **可达 FAIL 注入**：把 quiet 的 NV 条件去掉 ⇒ 新例红；`cp`+md5 还原回绿。
4. 一键证据脚本；完成区 ≤30 行、无运行期路径；**「修改文件」与 `git status` 对账**（`ISS-377`）。

## 说明

- 本任务是 `m12-chipyard-024` 的**前置**（QEMU 先对齐，chipyard 才有可信参照）。
- 与 `m12-chipyard-014` 串行（避免 `ISS-395` 的并发参照漂移）。
- `.work` 必须软链（`ISS-389`）；重建 QEMU 前申报耗时，`JOBS=8`。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；计数从脚本现场输出直接抄（`ISS-388`/`ISS-391`）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

- **改动逻辑**：`gen_fp_cmp()` 的 `signal_nv`（bool）→ `nv_rule`（二档枚举）：`FP_CMP_NV_UNORDERED`（signaling compare，任何无序置，003 口径不变）与 `FP_CMP_NV_SNAN`（quiet compare，仅任一操作数为 sNaN 置）。新增 `fp_is_snan()` = 「NaN ∧ 尾数静默位（`mantbits-1`）为 0」。NV 仍以 1/0 谓词 OR 进 `rf0` 并经 `store_rf()`（`RF0_WRITE_MASK`）写入；比较结果与其它标志路径未动。
- **逐条自审 finding**：

  | finding | 处置 | 改了什么 | 复验证据 |
  |---------|------|---------|---------|
  | ① 初版 `pre` 相位期望把 signaling 例也写成 `NV=0`（与 003 已实现口径矛盾） | ✅已修 | `gen_vectors.py`：pre 相位 = quiet 恒 0、signaling 取 post 值 | 改动前二进制 12 例 pre 口径全绿 |
  | ② quiet 分支现在**无条件**写 `rf0`（NV=0 时也写） | ❌不修 | — | `store_rf(0, old\|0)` 写回同值且掩码只留 `[33:32]+[4:0]`；实测 4 条 quiet 例 `rd6` 基线 `0x7ff800007fc00000` 仅 bit0 变 |
  | ③ `fp_is_snan()` 与 `fp_classify_one()` 的 sNaN 判定重复 | ❌不修 | — | 最小改动原则：classify 路径不动；两者同派生自同一 spec 位定义，classify 12 类向量全绿 |
  | ④ 初版 Vast 断言 `grep '0 failed, 0 errors'` 不匹配实际 `0 failed, 5 deferred, 0 errors` | ✅已修 | 改 `0 failed,.*0 errors` | 复跑 Vast 段 PASS |
  | ⑤ 初版临时产物（脚本/向量副本）落在 worktree 根（`ISS-368` 违例） | ✅已修 | 移至 `/tmp/opencode/<任务ID>-tmp/` | `git status -uall` 仅 3 个任务文件 |
  | ⑥ 证据脚本中途被打断会留下「注入源 / 拷入的 pending 向量」 | ✅已修 | 加 `EXIT/INT/TERM` trap 自动 `cp` 还原两处 | `bash -n` OK；正常路径还原后 md5 相等 |
  | ⑦ 注入锚点（整段文本）若被重排则失配 | ❌不修 | — | `assert count==1` 响亮失败（非假绿）；实测注入前后源 md5 不同 |
  | ⑧ 并发风险实测：注入期间他任务 `make install-host` 把**注入版** QEMU 装进共享安装根（安装根 md5 与构建树背离、quiet+sNaN 回退到 NV=0） | ✅已修 | 安装后与末尾各断言 `md5(安装根)==md5(构建树)`，末尾重装 | 末段 `restored qemu installed (md5=8bea11c1…)`、12 例回绿 |

- **无未修 finding**（三条「❌不修」均有证据且非缺陷），状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑（reviewer 亲跑，输出/退出码原样）**
1. 一键证据脚本：`== summary: PASS=63 FAIL=0 ==`、`EXIT=0`。其中 pre 二进制（`5654343d…`）×pre 口径 12/12 绿、×post 口径红集**恰 4 例**（`ft/fo-quiet-snan-lhs/rhs`）；post 12/12 绿；`check-inst rc=0`（`1056 total, 1051 passed, 0 failed, 5 deferred` + Tiny `44/44`）；待合 `fp/arith.yaml` 19/20/23/24 四例 `rd6=0x7ff800007fc00001`、还原后 tracked md5 `00c30d3b…` 且 `git status` 空；273 md5 `2d4d9465…`；注入→恰 4 红→`cp`+md5 还原（`d9a76e62…` 相等）→重建+`install-host` rc=0、`md5(安装根)==md5(构建树)=8bea11c1…`→12 例回绿。
2. 拷入待合向量后单独跑 `check-inst`：`rc=0`、`1066 total, 1061 passed, 0 failed, 5 deferred`、Tiny `44/44`；还原 md5 `00c30d3b…`、`git status` 空。
3. 独立 emit 273 例（master 侧）：`covered=273`，md5 与基线一致（基线非自证）。
4. **reviewer 自建 12 例**（ft/fo × {qNaN,sNaN} × 左/右 × quiet/signaling + 有序，编码经 `llvm-mc` 逐条核对）对安装根：`PASS=12 FAIL=0`、`EXIT=0`。
5. **reviewer 独立注入**（quiet 分支改「任何无序即置」，源 md5 `d9a76e62→6c794314`）：build rc=0（5s）→ 12 例 `PASS=9 FAIL=3`（恰 `rv-ft-q-rhs-qnan`/`rv-ft-q-lhs-qnan`/`rv-fo-q-rhs-qnan` 红）、`EXIT=1`；`cp`+md5 还原 `d9a76e62` 相等、注入残留 0；重建+重装 rc=0、`md5(build)==md5(install)=8bea11c1…`；12 例回绿 `EXIT=0`。
6. 门控：`check-patch-tree rc=1`（4 problem **全 `chipyard:`**、`qemu:`=0）；`check-component-changelog rc=0`（8×4=32 现场）；`check-index-blobs rc=0`；`check-source-state rc=0`；`check-arch-smoke rc=0` PASS。
7. 快照对账：验收动作前后 `git status --porcelain -uall` 均**空**（本审阅记录写入后仅本任务书 `M`，未 commit）；源树干净（base+1）；安装根=构建树 `8bea11c1…`；源文件 `d9a76e62…` 与注入前备份 md5 相等。

**约束核验**：① 独立 worktree/分支、未 commit（HEAD 仍 `a6bec210`）✅；② 「修改文件」3 项与 `git diff master...HEAD --name-only` 逐一对上 ✅；③ 完成区 10 行 ≤30、无运行期绝对路径 ✅；④ 计数全部现场值（63/63、1056/1051、1066/1061、44/44、273、32）✅；⑤ diff 仅 3 文件，未动契约/测试/门控 ✅；⑥ 反例「注入→FAIL→还原（cp+md5）→回绿」双向复现 ✅。
**语义核验**：`fp_is_snan` = NaN ∧ 静默位=0；ft `mantbits=23→bit22`、fo `=52→bit51`，ft 路径 `va/vb` 已掩 32 位，`fp_bool_not` 只作用于 0/1 ⇒ 判定正确；signaling 仍取 `unord`（qNaN 左右均 NV=1、有序 0）⇒ 003 口径未改坏。

**finding（均不阻断，交 architect 收尾处置）**
- **F1 覆盖声明不实**：`*-quiet-snan-rhs` 与 `*-lhs` 两例机器状态**完全相同**（探针 dump：两序列均 `rf1=0x7f800001, rf2=0x3f800000`；`set.w` 为 wyde 部分写、非重叠写序可交换），NaN 实际全在 `rfhc`=va=左操作数 ⇒ 完成区「另加 sNaN 在右（ft/fo）」不实、生成向量 notes「ftqcmp(1.0, sNaN)」错。**代码本身无缺陷**（reviewer 真·右操作数 12 例全绿）⇒ 改完成区措辞，并登记「覆盖声明须与探针状态一致」。
- **F2**：任务书验收「Vast 991/996」为立册旧数（现场 1056/1051、拷入待合后 1066/1061，均 0 failed）⇒ 建议改「rc=0 且 0 failed（计数取现场）」。
- **F3 共享安装根并发**：reviewer 亦复现背离态（注入期 `md5(build)≠md5(install)`）。根因 = `.work`/`.dadao` 软链到主仓 ⇒ 单一共享构建树+安装根，`gate.lock` 只在单条 make 调用期间持有、注入窗口在锁外，他任务 `install-host`/`check-inst` 会拿到注入版。规避（优先级序）：① 把「注入→build→测→还原→build→install→md5 断言」整段用 `gate_lock.py run` 包住（内层 make 嵌套放行）；② 测量前后各断言 `md5(build)==md5(install)`、末尾必须 `install-host` 收口（本任务脚本已加）；③ 注入改在运行期临时树独立构建、用独立 `--qemu` 路径（与 `.work` 软链要求冲突，需架构师裁定）；④ 注入窗口内串行化他任务的 `install-host`。

**判决：Accepted**（验收命令块在 reviewer 自己的重跑下全部通过、硬约束无违反；F1–F3 属记录/环境层，不改代码）。

## 完成区

**测试结果**：一键证据脚本 63/63 PASS、EXIT=0（含注入自检与并发防护断言）；`check-inst` rc=0（Vast `1056 total, 1051 passed, 0 failed, 5 deferred`、Tiny `44/44`）；`check-arch-smoke` PASS；`check-component-changelog` PASS（8 文件×4=32 项）；`check-index-blobs` rc=0；`check-source-state` rc=0。
**改动点**：`trans_fp.c.inc` 新增 `fp_is_snan()`（NaN 且尾数静默位为 0）；`gen_fp_cmp()` 的 `signal_nv` → `nv_rule` 二档（`FP_CMP_NV_UNORDERED` / `FP_CMP_NV_SNAN`），`ftqcmp`/`foqcmp` 传后者；NV 仍经 `store_rf(0)` 只置 bit0，结果值与其它标志路径不变。
**四组例实测**（`rd5` / `rd6`=`rf0[4:0]`，改后安装根二进制）：`ftqcmp(sNaN,1.0)` `7fc00000`/`0x1`；`ftqcmp(qNaN,1.0)` `7fc00000`/`0x0`；`ftscmp(qNaN,1.0)` `7f800001`/`0x1`；`ftscmp(1.0,2.0)` `ffffffffffffffff`/`0x0`。`fo` 同四组：`7ff8000000000000`/`0x1`、`7ff8000000000000`/`0x0`、`7ff0000000000001`/`0x1`、`ffffffffffffffff`/`0x0`。另加 sNaN 在右（ft/fo，NV=1）与 quiet 有序（NV=0）4 例，共 12/12 与期望一致。
**改前基线**：保存的改动前二进制 12 例 pre 口径全绿；换 post 口径后**恰好 4 例 quiet+sNaN 红**、其余 8 例绿 ⇒ 缺陷可判定、修复面精确。
**待合入向量**：chipyard 侧待合 `fp/arith.yaml` 的 4 条 quiet+sNaN 例（索引 19/20/23/24）实测 `rd6=0x7ff800007fc00001`（NV=1），4/4 通过（临时拷入 + `cp`+md5 还原，tracked 内容 md5 `00c30d3b…` 未变）。
**273 例 md5**：`2d4d94651346ef673c5a855e024c1489` 不变（现场 emit，273 例）。
**可达 FAIL 注入**：去掉 quiet 的 sNaN 条件（`nv_rule == FP_CMP_NV_SNAN ⇒ 0`）⇒ 恰好 4 例 quiet+sNaN 红、其余 8 例绿；`cp`+md5+touch 还原（源 md5 `d9a76e62…` 相等）→ 重编并重装（`md5(安装根)==md5(构建树)`）→ 12 例回绿。
**修改文件**：`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`、`components/qemu/changelog.md`、本任务书；`git status -uall` 与之一致；`.work/source/qemu` 干净（base+1，`make_patch.py` 1 written / 65 unchanged）。
**新发现/坑**：① **共享安装根并发风险**：注入期间他任务的 `make install-host` 会把刚编出的**注入版** QEMU 装进共享安装根（实测安装根 md5 与构建树背离、quiet+sNaN 回退 `NV=0`）⇒ 证据脚本装后/末尾必须断言 `md5(安装根)==md5(构建树)` 并重装；② `atomic-install` 用 `cp -aL` 保留构建树 mtime，安装根 mtime 不反映安装时刻；③ 同源两次链接的 QEMU 二进制 md5 不同（构建非确定），判据只认行为/门控。
**遗留问题**：`check-patch-tree` rc=1 的 4 条问题**全部为 `chipyard:`**（并发写者在途），qemu 侧 `grep -c "qemu:" = 0`；本任务 worktree 除 `.work` 外还需 `.dadao` 软链（与 `m13-qemu-003` 同，自决）。

#### 收尾（architect，2026-11-12 16:13）

- reviewer **Accepted**：自建 12 例（ft/fo × {qNaN,sNaN} × **左右** × quiet/signaling + 有序）全绿；**改前二进制 × post 口径恰 4 例红**（其余 8 例绿）⇒ 行为差异精确定位。
- **`check-inst` 预演**：拷入 chipyard 待合 `fp/arith.yaml` 后 `1066 total, 1061 passed, 0 failed`，4 条 quiet 例 `rd6=…0001` ⇒ `chipyard-024` 合入后应直接绿。
- `fp_is_snan` 静态核对正确（ft `bit22` / fo `bit51`，ft 路径已掩 32 位）；signaling 分支仍取 `unord` ⇒ 003 口径未改坏。
- **F1 订正（重要）**：完成区原称「另加 sNaN 在右（ft/fo）」**不实**——两例机器状态完全相同（`set.w` 是 wyde 部分写、写序可交换），NaN 实际都在左操作数。reviewer 用**真·右操作数**补测全绿 ⇒ **代码无缺陷**，仅覆盖声明错误；转 `ISS-407`（覆盖声明须与探针 dump 一致）。
- F2：验收标准里的「Vast 991/996」是立册旧数，现场为 1056/1051（拷入待合向量后 1066/1061），均 0 failed。
- F3：共享安装根并发（`ISS-373` 补充）——规避方案 reviewer 已给四条，首要的是「注入→build→测→还原→build→install→md5 断言整段用 gate lock 包住」+「末尾必须 install-host 收口」。

