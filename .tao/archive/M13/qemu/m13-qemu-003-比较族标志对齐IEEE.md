# m13-qemu-003: 比较族标志对齐 IEEE（signaling compare 无序即置 `NV`）

**模块**：qemu
**项目里程碑**：M13
**依赖**：无（QEMU 组件单写者空闲）
**可并行分片**：否（单组件单写者）
**状态**：已验证

## 用户裁定（2026-11-11，原话）

> 「按 IEEE/hardfloat：任何无序都置」

落盘位置：`.tao/knowledge/discussing.md`「已裁定：signaling compare 遇 qNaN 置 `NV`」。

## 背景

`m12-chipyard-013` 报「待裁定」：`ftscmp`/`foscmp`（signaling compare）遇 **qNaN** 操作数是否置 `NV`。

- `spec/SimRISC-07` / `contract-fp` **未写这一条**
- 原口径（任务书 + QEMU）：只有 sNaN 输入置 `NV`，qNaN 不置
- IEEE 754 / hardfloat：signaling compare 对**任何无序**（含 qNaN 操作数）都置 invalid

用户**已裁定按 IEEE/hardfloat**。

## 目标（只做 QEMU 侧）

1. **`ftscmp`/`foscmp`**：操作数中有**任一 NaN**（sNaN 或 qNaN）⇒ 置 `NV`。
2. **`ftqcmp`/`foqcmp`**（quiet compare）：任何 NaN **不置** `NV`（保持不变）。
3. 比较结果本身不变：无序 ⇒ 按 spec 返回 NaN（quiet 版回 qNaN、signaling 版回 sNaN），有序时按 `</=/>` 返回。
4. **不得**顺手改其它 FP 标志路径（`NV`/`NX`/`OF`/`UF`/`DZ` 的算术族语义不在本任务范围）。

## 非范围

- chipyard RTL / 模型 / 向量（`m12-chipyard-023`）
- `spec/SimRISC-07` 正文补写（归 `m12-chipyard-023`，避免两处漂移）
- 其它 FP 指令的标志语义

## 验收标准

1. 构造四组例并逐条给输出：
   - `ftscmp(qNaN, 1.0)` ⇒ `NV=1`，结果 NaN
   - `ftscmp(sNaN, 1.0)` ⇒ `NV=1`，结果 NaN
   - `ftscmp(1.0, 2.0)` ⇒ `NV=0`，结果 `−1`
   - `ftqcmp(qNaN, 1.0)` ⇒ `NV=0`，结果 NaN
2. `fo` 格式同样四组。
3. 既有回归不破：`check-inst`（Tiny 44/44）、273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变、`check-arch-smoke` rc=0。
4. **可达 FAIL 注入**：把 `NV` 条件改回「仅 sNaN」⇒ 新例必须红；`cp`+md5 还原回绿。
5. 一键证据脚本；完成区 ≤30 行、无运行期路径；**「修改文件」与 `git status` 对账**（`ISS-377`）。

## 说明

- 本任务是 `m12-chipyard-023` 的**前置**：QEMU 先对齐，chipyard 才有可信的差分参照。
- QEMU 组件单写者：本任务期间不要有其它任务重建 QEMU。
- 若发现 QEMU 当前**完全不为比较族置任何标志**（`013` 报告如此），需先补上 sNaN 路径再补 qNaN 路径，两步都要有证据。
- `.work` 必须软链到主工作树（`ISS-389`）。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账；**计数从脚本现场输出直接抄**（`ISS-388`/`ISS-391`）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

- **改动逻辑**：`gen_fp_cmp()` 新增 `signal_nv`；`unord`（1/0）OR 进 `rf0` 的 NV 位（`store_rf()`），仅 `ftscmp`/`foscmp` 传 `true`。比较结果与其它标志路径未动。
- **自审发现**：① 恢复注入时 `cp -p` 保留旧 mtime ⇒ ninja 判定无变更、注入二进制残留（末例假红）；✅已修：恢复改 plain `cp`（mtime=now），复验 `restored qNaN/sNaN green`。② 初版向量 sNaN 高字节写进 `wp0` 被低字覆盖；✅已修（`wp1`），pre/post 全绿。③ 初版把 signaling compare 的 unordered 结果写成 qNaN；✅已修（sNaN），12 例按 spec 结果全绿。
- **无未修 finding**，状态可置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-12，判决基于本人重跑）

**判决：Accepted**（附 1 条非阻断 finding，architect 收尾前必修，见末）。

- **一键证据重跑**：该任务的运行期证据脚本 `run.sh` → `== summary: PASS=43 FAIL=0 ==`、`RUNSH_EXIT=0`，逐条与完成区对齐：pre 12 例 `rd6=0x0`、post 12 例、`Results: 44 total, 44 passed, 0 failed, 0 deferred, 0 errors`、273 例 md5 `2d4d94651346ef673c5a855e024c1489`、`check-arch-smoke` rc=0、注入 `ftscmp(qNaN,1.0) rd6=0x0` 红 → `cp` 还原 md5 `d97e3db810e45038217e870bc75ce2ae` → 回绿。
- **本人独立 18 例**（期望值自写、不读 engineer 的 tsv：ft/fo × {qNaN 左, qNaN 右, sNaN, 有序} × {scmp, qcmp} + 2 例整 FCSR 读）：补丁后 **18/18 PASS、EXIT=0** —— `scmp` 三类 NaN `FCSR[4:0]=0x1`、有序 `0x0`；`qcmp` 任意 NaN（含 sNaN）`0x0`；结果值 signaling→sNaN `7f800001`/`7ff0000000000001`、quiet→qNaN `7fc00000`/`7ff8000000000000`、有序→`-1`。
- **改前二进制**（`qemu-pre.bin` mtime 2026-11-11 00:28，早于任务建立 23:04）跑同 18 例：signaling **6 例全 `rd6=0x0`（含 sNaN）** ⇒ 改前比较族完全不置标志（既有缺陷），`EXIT=1`（7 FAIL）。
- **只读位/其它标志**：整 FCSR 基线 `0x7ff800007fc00000` → `ftscmp(qNaN,1.0)` 后 `0x7ff800007fc00001`：**仅 bit0 变**，`[63:51]`/`[31:22]` 只读 qNaN 位、`[4:1]`、`[33:32]` 全保持；`check-inst` Vast `996 total, 991 passed, 0 failed, 5 deferred`（含 `fp/convert` 整 FCSR 断言 `0x7FF800007FC00010`）+ Tiny 44/44。
- **门控**：`check-index-blobs` RC=0（246 new-file patch OK）；`check-component-changelog` RC=0 PASS（8 文件×4 断言=32 项，现场统计）；`check-patch-tree` RC=2 → **8 条全 `chipyard:`、`grep -c qemu` = 0**；20 分钟后复跑 9 条（多 1 条 ⑦ 脏树）⇒ chipyard 并发写者在途（`.inj-bak` mtime 00:27:50、`WumingFP.scala` 00:29:05、chipyard HEAD 00:01:53 重写），与本任务无关。
- **本人第 2 次注入**（自选例：`ftqcmp` 也置 NV）：`git diff` 非空、build rc=0 ⇒ 3 例 `ftqcmp` NaN `rd6=0x1` 变红、`PASS=15 FAIL=3`、`EXIT=1`；`cp`+md5 还原 `d97e3db810e45038217e870bc75ce2ae` 相等、qemu 源树 `git status` 空、重编 **18/18 PASS、EXIT=0**。
- **纪律**：3 文件与完成区「修改文件」一致（`git show --name-only db5d8686` = patch/changelog/本任务书）；验收前后 `git status --porcelain -uall` 均空、三文件 md5 前后相同、**未 commit**（HEAD 为 architect WIP）；补丁仅 9 行删除（index 行、长度头、旧注释尾、`gen_fp_cmp` 签名、4 调用点）⇒ 无越界改动；完成区 9 行 ≤30、无宿主绝对路径；计数均抄自我方现场输出；注入还原全程 `cp`+md5（未用 git checkout/restore）。我方临时脚本曾落 worktree `review/`，已移出至 `/tmp/opencode/m13-qemu-003-review/`。

**finding（非阻断，§6.5 文档级；architect 收尾必修）**：`make check-knowledge-refs` **RC=2**，唯一红点 = 完成区的**具体**证据脚本路径 `.work/evidence/<本任务ID>/run.sh`（未用占位形；ISS-352「具体 `.work/**` 一律不可复现」，60 份任务书中 8 份用 `<任务ID>` 占位形规避）。改为占位形或文字描述后应 rc=0；不改判决，但收尾前不修则 L1 常红。

**三问**：① 语义与用户裁定一致、`qcmp` 独立 —— 是：`signal_nv` 仅 `ftscmp`/`foscmp` 传 `true`，`ftqcmp`/`foqcmp` 传 `false` 且**完全不写 rf0**（该分支无 `store_rf` 调用），实测任意 NaN `FCSR[4:0]=0x0`。② 改前连 sNaN 都不置 —— 是（既有缺陷）：pre 二进制 signaling 6 例全 `0x0`，本任务先补 sNaN 再补 qNaN 一步到位。③ 无顺带影响 —— 补丁 7 个 hunk 全在 `gen_fp_cmp` 与 4 个调用点，Vast 0 failed、273 sweep md5 不变、整 FCSR 只读位实测保持。

## 完成区

**测试结果**：一键证据脚本（运行期证据目录）→ `PASS=43 FAIL=0`、EXIT=0（含注入自检）。
**原状核实**：保存的**改动前**二进制跑 12 例（ft/fo qNaN、sNaN、有序、q 版），`rd6=FCSR[4:0]` 全为 `0x0`——确认比较族**完全不置任何标志**（含 sNaN 路径），需先补 sNaN 再补 qNaN。
**四组例实测**（`rd5` 结果 / `rd6=FCSR[4:0]`；改动后）：`ftscmp(qNaN,1.0)` `7f800001`/`0x1`；`ftscmp(sNaN,1.0)` `7f800001`/`0x1`；`ftscmp(1.0,2.0)` `ffffffffffffffff`/`0x0`；`ftqcmp(qNaN,1.0)` `7fc00000`/`0x0`；`fo` 同四组：`7ff0000000000001`/`0x1`、`7ff0000000000001`/`0x1`、`ffffffffffffffff`/`0x0`、`7ff8000000000000`/`0x0`；另加 qNaN 在右（signaling，NV=1）与 q 版 sNaN（NV=0）各 2 例，12/12 与期望一致。
**门控**：`check-inst` rc=0（`Results: 44 total, 44 passed, 0 failed, 0 deferred, 0 errors`）；`inst_sweep.py emit` 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变；`check-arch-smoke` rc=0；`check-index-blobs` rc=0；`check-component-changelog` PASS。
**可达 FAIL 注入**：NV 条件改回「仅 sNaN」→ `ftscmp(qNaN,1.0)` 实测 `rd6=0x0`（期望 1，红）、`ftscmp(sNaN,1.0)` `rd6=0x1`（绿）；`cp`+md5 还原（`d97e3db810e45038217e870bc75ce2ae`）、重编后两例回绿。
**修改文件**：`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`、`components/qemu/changelog.md`（+ 本任务书）；`git status -uall` 与之一致；`.work/source/qemu` 干净（HEAD=base+1）。
**新发现/坑**：① 恢复源码用 `cp -p` 会保留旧 mtime，ninja 不重编（注入残留），须 plain `cp`/`touch`；② 同源两次链接的 QEMU 二进制 md5 不同（构建非确定），判据只认行为/门控，勿以二进制 md5 判定；③ 任务 worktree 除 `.work` 外还需 `.dadao` 软链，否则门控解析到空安装根（自决）。
**遗留问题**：`check-patch-tree` rc=2，8 条全部来自 **chipyard** worktree 脏树（他任务并行写者），qemu 侧 0 条；本任务 worktree 内 scratch/`sweep` 运行期产物收尾时清理，未归档。

#### 收尾（architect，2026-11-12 00:46）

- reviewer **Accepted**：改后 18 例独立复核 **18/18 PASS**；改前二进制 `qemu-pre.bin`（mtime 早于任务建立）同 18 例 **7 FAIL** ⇒ 确认属**既有缺陷**（比较族原本完全不置任何标志，含 sNaN）。
- `qcmp` 分支**完全不写 `rf0`**（无 `store_rf` 调用）；scmp 三类 NaN ⇒ `0x1`、有序 ⇒ `0x0`；结果值 signaling→sNaN、quiet→qNaN、有序→`-1`。
- 未波及其它 FP 标志：整 FCSR 基线 `0x7ff800007fc00000` → 比较后 `…01`，只读位 `[63:51]`/`[31:22]`、`[33:32]`、`[4:1]` 全保持；`check-inst` Vast 996=991+5 deferred、Tiny 44/44；273 md5 不变。
- `check-patch-tree` rc=2 的 8–9 条**全为 `chipyard:`**（并发写者在途），qemu 侧 `grep -c qemu` = 0。
- 完成区运行期路径已按 `ISS-352` 改占位形，`check-knowledge-refs` 回绿。
- 注入 2 组（工程师 + reviewer 自选 `ftqcmp` 也置 NV）均先红后绿。

