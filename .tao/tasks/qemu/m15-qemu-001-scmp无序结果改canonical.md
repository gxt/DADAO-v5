# m15-qemu-001: `scmp` 无序结果改 canonical quiet NaN（spec 已改）

**模块**：qemu
**项目里程碑**：M15
**依赖**：spec 修改已落盘（`a6f11e23`）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改
**状态**：已验证

## 背景（用户 2026-11-19 授权，版本号不变）

`spec/SimRISC-07 §4` 已把 signaling compare 的无序结果从 **sNaN** 改为 **canonical quiet NaN**（对齐 IEEE 754-2019 §6.2.1 的 `shall`）；quiet/signaling 的差别只剩 `NV` 标志。

## 要做

`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch` 的 `FP_CMP_NV_UNORDERED` 分支：无序结果由 sNaN 位型改为 **canonical quiet NaN**（`ft`/`fo` 各自格式），`NV` 置位规则**不变**（signaling 无序即置；quiet 仅 sNaN 置）。

## 验收

1. QEMU 重建后跑 `tests/inst/07-floating-point/ftscmp_orrr_rf.S` 与 `foscmp_orrr_rf.S` ⇒ 通过（现有用例无 NaN，需保证不回归）；
2. **新增/临时**无序用例（qNaN、sNaN、双 NaN × 两种格式）验证结果 == canonical 且 `NV` 符合规则（给真实输出）；
3. 可达 FAIL：改回 sNaN ⇒ 该用例红（`cp`+md5 还原）；
4. `check-patch-tree`（qemu 侧）rc=0。

## 完成区

**测试结果**：运行期证据目录内 `run.sh --inject` **20/20 PASS**（含 1 路注入：改回 sNaN ⇒ canonical 向量点 1 红 ⇒ `cp`+md5 还原 ⇒ 重建回绿）。
- 规范结果（临时无序向量 20 检查点：ft/fo × qNaN/sNaN/双 NaN × scmp/qcmp）：结果字节 20/20 == ft `0x7FC0_0000` / fo `0x7FF8_0000_0000_0000`；`NV` 按规则（scmp 无序恒置、qcmp 仅 sNaN 置）。
- 不回归：`ftqcmp`/`foqcmp` guest rc=0；`ftscmp`/`foscmp` guest rc=**10** = 有序点 1–9 全过、红点是向量点 10 的旧 `TEST_FPCMP_S`（断言 sNaN 位型），按新 spec 已失效（见「待裁定」）。

**修改文件**：`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`（`make_patch.py` 重导出，非手改）；`components/qemu/changelog.md`（新增 M15 节，Process-01 §10）；本任务书。

**验收结果**：`make build-qemu` PASS（二进制 md5 `3a6ed9815effa07bddd036fdbc8e4ad3`）；`check-patch-tree` rc=0、`check-index-blobs` rc=0、`check-component-changelog` rc=0、`check-fp-contract` rc=0、`check-qemu-forms` rc=0；`make check` 仅 `check-temp-dirs` 红（他任务陈旧目录 `m14-linux-*` 5 个，非本任务、未代删），其余全绿；合并态 `git merge master` 后整轮重跑全绿（`master` 是 HEAD 祖先）。

**新发现/坑**：
1. 任务书前提「现有用例无 NaN」**有误**：两册点 10–16 就是 qNaN/sNaN 用例（旧口径结构性断言 sNaN）；`m15-testcases-020` 前言同样有误。
2. `.tao/contracts/contract-fp.md` 第 26/88 行仍写「Signaling Compare 返回 sNaN」，与 `a6f11e23` 后的 spec 冲突；`check-fp-contract` 不覆盖该散文 ⇒ 需单独立契约更新任务。
3. `tools/testcases/arch/min_rom_probe_035t.py` 系**既有红**（与本任务无关）：`load_class_bits_from_spec` 找 `## 7. 浮点分类指令`，spec 现为 `## 5.` ⇒ 探针执行任何用例前即失败；其 CM09/CM10/CM20/CM21 仍按 sNaN 断言，修锚点时须一并改 canonical。

**遗留问题**：验收 1 的 signaling 两册待 `tests/inst` 更新（属 testcases 模块），见「待裁定」。

## 待裁定（需主会话/用户定，engineer 未自决）

**问题**：验收 1 要求 `ftscmp_orrr_rf.S`/`foscmp_orrr_rf.S` 通过；但两册点 10–16 断言的是**旧 sNaN 位型**（`TEST_FPCMP_S` 结构性断言 `[9:0]==0x1FE` / `[12:0]==0xFFE`），新 spec 下必然红（实测 guest rc=10）。本任务按「只动 qemu 侧」执行，未改 `tests/inst`。

**选项**：
- **A（建议）** 交 `m15-testcases-020` 收口：把两册那 7 行改成 `TEST_FPCMP` + canonical 期望（ft `0x7FC00000`、fo `0x7FF8000000000000`，`NV` 不变）；改后 `TEST_FPCMP_S` 无使用者 ⇒ 按 `check-inst-macro-scope` 死宏规则须删除；该任务书前言「没有 NaN/无序用例」需同时订正。
- **B** 扩本任务范围，由我一并改两册 + 宏（跨模块，且与 testcases-020 重叠）。

**临时处置**：选 A；证据脚本把「红点恰为点 10 且该行为 `TEST_FPCMP_S`」写成断言，保证「有序部分零回归」有机械证据。

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：补丁 diff（1 文件 10+/11−）、changelog、证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 删 `FP_FT_SNAN`/`FP_FO_SNAN` 后是否留悬空引用 | ✅不修（无问题） | — | 源码 `grep -c 'FP_F[TO]_SNAN'` = 0；`make build-qemu` rc=0（编译即引用检查） |
| F2 `NV` 置位规则是否被误改 | ✅不修（无问题） | — | 源码仍 `nv_rule == FP_CMP_NV_SNAN` ? sNaN 谓词 : `unord`；证据 `src-nv-rule` PASS |
| F3 补丁是否被手工编辑（`@@` 行数/尾部截断风险） | ✅不修（无问题） | — | 由 `make_patch.py` 重导出（`1 written, 68 unchanged`）；`check-patch-tree` rc=0（断言⑥ blob 一致） |
| F4 证据脚本静态判据可能恒真（无 FAIL 路径） | ✅已修 | 注入态增 `inject-static-red` | `--inject`：注入态计数 ft=0 fo=0 sNaN=2 ⇒ 判据可达 FAIL（PASS） |
| F5 证据脚本 `grep '^\t…'` 恒假（GNU BRE 不识别 `\t`） | ✅已修 | `grep -q` → `grep -qP` | 修前 `regress-red-point FAIL`，修后 PASS |
| F6 「合并态」只在旧 master 上验过 | ✅已修 | 分支 `git merge master` 后整轮重跑 | `merge-state` PASS，20/20 PASS |

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 现场 rc）**：
- `运行期证据目录内的 run.sh --inject` ⇒ **rc=1，SUMMARY pass=19 fail=1**；唯一 FAIL = `merge-state`（master 非 HEAD 祖先）。根因＝环境漂移：master 在 engineer 提交（810b7120，20:22:03）后 4 秒起并发前进 30 commits（5e5d7f78 20:22:07 → 2b19ed6d 22:56:18），非交付物缺陷；其完成区「20/20」在其时点为真。其余 19 项全 PASS（canon 20/20 字节、regress rc=0/0/10/10、注入红/还原/回绿、patch-tree rc=0）。**architect 合并后在合并态重跑该脚本 `--inject` ⇒ 20/20、rc=0（含 `merge-state` PASS）。**
- 4 门控（自跑）：`check-patch-tree` rc=0（11 sets/434 patches OK）、`check-fp-contract` rc=0、`check-index-blobs` rc=0、`check-component-changelog` rc=0（40 项）。`check-temp-dirs` rc=2 归属他任务（m14-linux-*×5、m15-gem5-001 陈旧目录、/tmp 共享 70.5%），不背。
- 合并态补证：`git merge-tree --write-tree HEAD master` rc=0、0 CONFLICT；master 未动 `tests/inst`/`components/qemu`/`Makefile`/`tests/ee-tiny` ⇒ 行为类 PASS 可携带（合并归 architect，reviewer 未做 git 写操作）。

**约束核验**：① diff 范围 ✓（`git diff master...HEAD --stat` = 3 文件，与「修改文件」声明一致）；源码 `grep -c 'FP_F[TO]_SNAN'`=0。② 规范值 ✓ 独立读 `spec/SimRISC-07 §4`（无序一律 canonical + NV 规则）与 §1.3（ft `0x7FC0_0000`/fo `0x7FF8_0000_0000_0000`），master 侧 spec 同语义；源码 `FP_FT_QNAN`/`FP_FO_QNAN` 逐字匹配，NV 谓词选择未改。③ 重跑 ✓ 见上 19/20（1 FAIL 判环境归属）。④ reviewer 独立注入（非它那路）：`FP_FO_QNAN` 错一位（…0000→…0001）⇒ build rc=0、run rc=1、**guest rc=11**（fo 段首点红、ft 段 1–10 过）；`cp` 还原 md5=6bf47572…相等、源树 clean（未用 checkout/restore/stash/reset）⇒ 重建 rc=0、回绿 run rc=0/guest rc=0。⑤ 红点=点10 ✓：`__VERIFY_RD→__EXIT pt` 首失配即退 ⇒ 点 1–9 全过；点 10 行静态为 `TEST_FPCMP_S`（`07-floating-point.inc:287`，断言 `[9:0]==0x1FE` 的 sNaN 形态），canonical `0x7FC00000` 提取得 0x1FF 必红于此；flags(NV=01)/sign(0) 两断言先过已被 canon 向量 in-guest 断言证明 ⇒ 排除别处回归。⑥ 术语/构建落点合规。

**新发现（非阻断，交 architect）**：`run.sh` 第 98 行 `'^+#define FP[T O]_SNAN'` 模式笔误（`_` 在字符类外）⇒ 该分量恒真（注入 `FP_FT_SNAN` 文本实测 c=0 而非 2）；但同脚本 `src-cmp-const`（模式正确、可达 FAIL）对同一变异兜底，不影响验收结论，且 run.sh 属运行期证据不入库 ⇒ 不打回，建议收尾顺手改 `FP_F[TO]_SNAN`。

**finding 判定**：F2（contract-fp 仍写 sNaN）**不需新任务**——`m15-spec-007` 已立（5e5d7f78）并合入（7ec7b693），master 的 contract-fp.md L88 已改 canonical。F3（min_rom_probe_035t 锚点 `## 7.`→`## 5.`）**不需新任务**——`m15-testcases-020` 追加范围②已含「修锚点+改 canonical、既有红顺带收」（6d510edf）；待裁定选项 A 亦已被该书吸收（1c90d0e8）。

**判决：Accepted**（唯一 FAIL 判环境漂移归属；4 门控全 0；独立注入红→还原→回绿成立；红点解释核实）。
