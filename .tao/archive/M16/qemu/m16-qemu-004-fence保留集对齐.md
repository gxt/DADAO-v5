# m16-qemu-004: QEMU `fence` 保留 cfx 集对齐（ISS-432）

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-qemu-001` 返工合入（同组件写者）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（用户 2026-11-22 选 A）

`ISS-432`（P2）：`fence` 的保留 cfx 集三平台不一致。真源 `Kaiwu §1.2` + `DADAO-12 §1` = **`6–14, 16–31, 35–61`**（`hb≠0` ⇒ `ILLI`）；实测 QEMU 是 **`6–14, 19–61`**（cfx16/17/18 放行、cfx32/33/34 报异常），chipyard/gem5 与 spec 一致。

## 要做

1. QEMU 的 `fence` 保留 cfx 集改为 `6–14, 16–31, 35–61`；`hb≠0` ⇒ `ILLI`。
2. 保留集边界与 `cfx0`/`cfx_umon`=all、`cfx1–63` 指定、六位资源域的现有语义不变。
3. 探针采样：cfx16/17/18（应 `ILLI`）、cfx32/33/34（应放行）、6–14 与 35–61 边界各 1；与 chipyard/gem5 一致。
4. 关闭 `ISS-432`（`issues.yaml`：`status: closed`、`resolved_by: m16-qemu-004`）。

## 不做

- 不改 fence 的六位语义/屏障实现；
- 不改 chipyard/gem5（它们已与 spec 一致）；
- 不写完整 fence 用例（由 `m16-testcases-012`）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py qemu` 幂等；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. 保留集探针：cfx16/17/18 ⇒ `ILLI`；cfx32/33/34 ⇒ 放行；边界 cfx14/15/31/32/35/61 逐条；
2. 与 chipyard/gem5 的同组探针结果一致；
3. **可达 FAIL**：注入「保留集仍 19–61」⇒ 探针红；`cp`+md5 还原后回绿；
4. `check-patch-tree` qemu 段 0 problem、`check-index-blobs`、`check-tasks`、`check-issues` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：`run.sh` rc=0（PASS=15/15）；`run.sh --inject` rc=0（PASS=30/30，3 路可达 FAIL）。探针实测（Tiny 三载体）：cfx16/17/18 + 边界 14/31/35/61 ⇒ `ILLI`（QEMU/gem5/chipyard 三个 rc 全 0）；cfx0/15/32/33/34/62/63 ⇒ 放行，7 个检查点 56 B 签名流三方 md5 全同 `b0889ac7…`；保留例流 0 B 三方全同。
**修改文件**：`components/qemu/patches/target/dadao/insn_trans/trans_ctrl.c.inc.patch`（源码树同路径，1 行语义 + 注释）、`components/qemu/changelog.md`、`.tao/knowledge/issues.yaml`（ISS-432）、本任务书。其余 worktree `git status` 干净。
**验收结果**（真跑 rc，本机）：`make build-qemu` 0；oracle（两份契约互校）0；三载体探针 0；`tests/inst/11-cfx/fence_ciii_cfx.S`（QEMU）0；`check-patch-tree` qemu 69 patch / 0 problem（整跑 rc=1，来自 gem5/chipyard/musl 的既有 ⑥⑨（musl 10 条），与本任务无关）；`check-index-blobs` 0；`make check-tasks` 0；`check_issues.py` 0；`make_patch.py qemu` 二跑 `0 written`（幂等）。注入：old `19–61` / `return false` / `return true` 各 `cp`+md5 `eff67c31` 还原、重建、回绿。
**新发现/坑**：①共享 gem5/chipyard 二进制被并行会话反复重建（跑批中途路径消失/换 md5）⇒ 证据脚本先 `cp` 到证据目录私有副本并在跑前跑后核 md5。②无故障例的 `inst_test.inc` 镜像遇意外异常会因 `TEST_FAULTV=0` 误走 `__EXIT 0`；legal 探针需预置 one-hot=0 + 失败码 `0x7E` 哨兵。③无 `make check-issues` 目标，判据用 `tools/infra/check_issues.py`（`closed` 必填 `closed_in`）。④`make_patch.py` 以脚本所在树为 ROOT，须在任务 worktree 内经 `.work/source/*` 软链运行。
**遗留问题**：无实现遗留。载体说明：三载体共同可用的现成二进制只有 Tiny（Vast RTL sim 为并行会话临时产物）；`fence` 保留集是解码期静态判据、与机型无关，Vast 行为由同一 `trans_fence_ciii_cfx`/decoder 路径覆盖；待 `m16-testcases-012` 做正式用例。另：主工作树 `components/qemu` 补丁在本任务合并前仍是旧内容（子代理不改主工作树）；判据以任务 worktree 的 qemu 段 0 problem 为准。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（本深度无嵌套子代理）：`fence_cfx_reserved` 与 `DADAO_CFX_IS_RESERVED` 的一致性、`hb≠0` 与屏障路径未动、探针 cfx 侧别/编码回读、判据能否真红（三载体逐字节 + 契约 oracle）、`run.sh` 还原与共享产物竞态。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 无故障例的 legal 探针遇误报异常会落到 `TEST_FAULTV=0` ⇒ `__EXIT 0` 假绿 | ✅已修 | 探针开头预置 `TEST_FAULTV` one-hot=0、失败码 `0x7E` | 注入 `return true` ⇒ qemu rc=126 红 |
| F2 共享 gem5/chipyard 被并行会话重建 ⇒ 跑批中途二进制消失/md5 变 | ✅已修 | `run.sh` 先 `cp` 私有副本（md5 前后比对 + `--help` 冒烟），探针用副本并跑后核 md5 | 全量跑 `carrier md5 stable` 三项 PASS；此前首跑曾 `FAIL 二进制在跑批期间被替换` |
| F3 断言“签名流”按 `signature.bin` 找文件，实际产物名 `<stem>.<plat>.out` ⇒ 证据空 | ✅已修 | 改为打印 `*.out` 的 md5 | 日志出现三方同 md5 `b0889ac7…` |
| F4 `restore_pending` 用相对路径拼备份目录 ⇒ 中断还原会落错位置 | ✅已修 | `PENDING` 保存备份绝对路径，还原目标固定 `$SRC/$REL` | 三路注入 `restored by cp + md5` + `git status` 0 |
| F5 oracle 直接 `eval` 契约的 C 风格 `||/&&` ⇒ 语法错、oracle 起不来 | ✅已修 | `_py()` 转 Python 布尔运算符 | oracle 0；`--self-test` 反例被拒 |

**约束核验**：worktree `git status -uall` = 3 改（1 补丁 + changelog + issues）+ 本任务书；组件源树（`.work/source/qemu`）干净且 `base..HEAD` 恰 1 commit；未改 `spec/`、契约正文、RTL/gem5、fence 六位语义/屏障实现；未升版本号；未提交 git；本记录与完成区无运行期具体路径；术语「寄存器组」。
**判决**：**待验收**（F1–F5 已修；无未修 finding）。

### 第 1 轮 reviewer 验收

**重跑**（仓库根执行运行期证据目录内的 `run.sh`，reviewer 亲自跑，不采信完成区）：
- `./run.sh` → rc=0，`checks: PASS=15 FAIL=0`（62 s）；`./run.sh --inject` → rc=0，`checks: PASS=30 FAIL=0`（126 s，三路注入均「非空注入 → 判红 → `cp`+md5 还原 → 回绿」）。
- **独立注入 ≥2 路**（reviewer 自做，`cp` 备份 + md5，未用 `git checkout/restore/stash`）：路 A 恢复旧 `19–61` ⇒ `./run.sh` rc=1、`checks: PASS=10 FAIL=5`（共享宏检查红、三载体探针红：qemu legal rc=126 / reserved rc=1、qemu 段 problems=2、`make_patch` rc=1）；路 B `return false` ⇒ rc=1、`checks: PASS=9 FAIL=6`（reserved qemu rc=1、`fence_ciii_cfx.S` rc=1）。两路还原后 md5 回到注入前值、源树 `git status` 空、补丁文件 md5 不变，再跑 `./run.sh` rc=0、`PASS=15 FAIL=0`。

**保留集 / 三载体判定**：`fence_cfx_reserved()` 体仅 `return DADAO_CFX_IS_RESERVED(cfxha);`（宏 = `6–14, 16–31, 35–61`），无局部 `19`；`hb≠0 || 保留 ⇒ ILLI` 与六位 pred/succ 屏障代码未动（补丁 diff 仅 1 行语义 + 注释）。探针实测：cfx16/17/18 与边界 14/31/35/61 ⇒ `ILLI`（7 故障例，QEMU/gem5/chipyard rc 全 0）；cfx0/15/32/33/34/62/63 ⇒ 放行 7 检查点 56 B，三方签名 md5 全同 `b0889ac7…`，保留例 0 B 三方全同。

**ISS-432 / 门控**：`status=closed`、`closed_in=M16`、`resolved_by=m16-qemu-004`（脚本判据 rc=0）；reviewer 独立跑 `tools/infra/check_issues.py` rc=0（98 open / 63 closed）；任务树独立跑 `check-patch-tree` → qemu 69 patch / **0 problem**（整跑 rc=1 来自 chipyard/gem5/musl 的 ⑥⑨ 基线红，qemu 段 0 行）；`check-index-blobs` 0、`check-tasks` 0、`make_patch.py qemu` 二跑 `0 written`。

**约束核验**：变更集 = `issues.yaml` + `trans_ctrl.c.inc.patch` + `changelog.md` + 本任务书（`git status -uall` 恰 4 行，与完成区声明一致）；未动 spec/契约正文、未动 gem5/chipyard、未升版本号、未提交 git；术语「寄存器组」；本记录无运行期具体路径。

**finding（非阻断）**：① 完成区称 `check-patch-tree` 整跑红「来自 gem5/chipyard」，实测另有 musl 10 条 ⑥⑨ —— 文档级遗漏，交 architect 收尾改。② `check-knowledge-refs` 基线即红（`ADR-0059` 悬空 2 处，落在 MEMORY 与 milestones-m18，非本任务文件），与本任务无关。

**判决：Accepted**（验收命令块在 reviewer 重跑下全部通过；≥2 路独立注入均真红并 `cp`+md5 回绿；硬约束无违反）。

