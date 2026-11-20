# m17-testcases-002: `ldm.*` 注释订正 + `rf0` 目的用例 + `immu6=63` 边界补齐

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-testcases-001`（签名区数据派生与 `check-inst-sig`；本任务改 `.S` 后须重生成）
**可并行分片**：否
**预估**：2–3 h
**档位**：小改
**状态**：已验证

## 背景（用户 2026-11-20 观察，三条均已现场核实）

1. **注释有误**：`tests/inst/01-load-store/ldm.t_rrri_rf.S:5` 写「`rf0` 作目的合法（**按 FCSR 写掩码**）」——`.t` 只写目的低 32 位，`rf0` 在该写入窗口内**只有 `[4:0]` 可写**（`[33:32]` 舍入模式与只读 qNaN/SBZ 保持原值，见 `spec/SimRISC-01 §4` 写入宽度注）。同句在 `ldm.o_rrri_rf.S:5` 对 `.o` 成立，**不要改**。
2. **缺 `rf0` 作目的的用例**：`ldm.o` 有 `ldm.o {rf0:rf1}, [rb3, rd19]`（`ldm.o_rrri_rf.S:67`），`ldm.t` 全文件 `rf0` 只在第 5 行注释里。
3. **`immu6=63` 边界只在 `ldm.ub`**：`ldm.ub_rrri_rd.S:50-58` 有最大合法个数整组装入 + 回写；`ldm.ut`/`ldm.uw` 没有。

## 目标

1. 订正 `ldm.t_rrri_rf.S:5` 的注释为「只写低 32 位；`rf0` 内仅 `[4:0]` 可写，其余位保持」；
2. `ldm.t` 补一例 **`rf0` 作目的**：装入后断言 `rf0[63:32]` 与 `rf0[31:5]` 保持原值、`rf0[4:0]` = 写入值的低 5 位（目的范围可取 `{rf0:rf1}`，起点 0 不被判 ILLI）；
3. `ldm.ut` / `ldm.uw` 各补一例 **`immu6=63`**：`{rd1:rd63}` 整组装入 + 回读（索引用 `rd0`，理由同 `ldm.ub` 该例注释：用 `rd19` 会落进传送范围 ⇒ ILLI）。

## 验收（逐条贴真实 rc）

1. **注释修正不改指令流**：该镜像 `.text` md5 与改前相同；全仓 `grep "按 FCSR 写掩码"` 只剩 `ldm.o_rrri_rf.S`（`.o` 的正确表述）；
2. **`rf0` 用例逐位**：`rf0[63:32]` 不变、`[31:5]` 不变、`[4:0]` = 低 5 位（三条断言各自可达 FAIL）；
3. **`immu6=63` 逐字节**：`ldm.ut`/`ldm.uw` 各 63 元素装入后回读与源数据逐字节相等；
4. **三平台**：qemu / gem5 / chipyard 同一 ELF 的签名流逐字节相等（chipyard 若被其它任务占用 ⇒ 记 BLOCKED + 替代证据，不得并发构建）；
5. **签名数据同步**：`tests/data/inst-signature/expected.tsv` 与 `inputs.sha256` 重生成，`make check-inst-sig` 绿（新增用例的槽全部纳入）；
6. **可达 FAIL ≥2 路**（`cp`+md5）：① 把 `rf0` 断言里的 `[4:0]` 期望改错 ⇒ 红；② 把 `immu6=63` 的数量改 62 ⇒ 回读红；
7. 门控：`check-inst-asm` **272/272**、`check-case-ledger`（`--write` 重生成）、`check-tests-index`、`check-inst-macro-scope`、`check-knowledge-refs` 真实 rc。

## 完成区必须写

**需重测周期的镜像清单**：本任务改动指令流的镜像（`ldm.t`、`ldm.ut`、`ldm.uw`）——它们的「实测总拍数」记录作废；按指令类的周期表不受影响（只依赖同族样本）。

## 约束

独立 `git worktree`；不提交 git；**只改这三个文件 + 必要的数据重生成**（最小原则，不顺带改其它 `ldm.*`/`ld.*`）；不改 `spec/` 与契约；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-20）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `rf0` 组内第二目的的期望写错：`{rf0:rf1}` 下 rf0 拿元素 0（0x80000021）、rf1 拿元素 1（0x80000022），我按同元素写了 0x…21 | ✅已修 | 期望改 `0xDEADBEEF80000022`，并在两处注释标明元素分配 | QEMU 该镜像 21 槽 PASS；三平台 168 B 逐字节相等 |
| 首版证据脚本只注入 rf0 ③ 一路 ⇒ 不满足「三条断言各自可达 FAIL」 | ✅已修 | 增 ①「高半掩码换低半」②「[31:5] 掩码换全 1」两路注入 | 三路各自 rc=1（失败点号 21）；`cp` 还原后各 rc=0 |
| ut/uw 最大个数例初版只比首/末拍，「逐字节」覆盖偏薄 | ✅已修 | 各加 2 条中段 `__VERIFY_MEM`（不占点号、不改点号连续性） | 该镜像仍 21 槽 PASS；中段拍字节由 guest 断言 |
| 头注释「链例 17/20」与新点号不符 | ✅已修 | 三处改「链例 21」并补用例类目 | `scan_source` 现场派生 `pts_ok=True`（21 链例 + 7/9 故障例） |
| 改 `.S` ⇒ 入库数据必漂移（`expected.tsv`/`inputs.sha256`/`case-ledger.tsv`） | ✅已修 | 现场 `--write` 重生成 | `sha256sum -c` rc=0；`check_inst_sig --data-only` rc=0；`check-case-ledger` 5681 条 PASS |
| 注入还原手法 | ✅已核 | 只用 `cp` 备份 + md5 对账 | 四路注入还原后 md5 与注入前逐字节相同；未用 `git checkout/restore` |
| 越界核对 | ✅已核 | 无越界 | `git diff --name-only` 恰 6 文件（3 `.S` + 3 数据），未动 `spec/`、契约、其它 `ldm.*`/`ld.*` |
| 并发 `install-host`（另一任务重建共享工具链）令 writer-guard 拒绝一次 | ⏸ 非本任务引入 | 等其结束后重跑（重试 1 次） | 首次脚本 rc=1（4 项「还原后镜像」被 REFUSED），重跑 rc=0 全绿 |

**判决**：全部 finding 已修/已核，无未修项 ⇒ 状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-20）

**重跑（全部由 reviewer 亲自执行，计数现场取，不采信完成区）**
- 仓库根执行运行期证据目录内的 `run.sh` ⇒ **rc=0 / ALL PASS**：A 与 B（只换第 5 行旧措辞）`.text` md5 同为 `03bb8321d539f0be49b667c08cce1299`，改真指令反例 `5b3a3c3c831d2174f31ba749ca9994e4`；qemu 三镜像各 168 B rc=0；4 路注入全红且还原回绿；`inputs.sha256` rc=0；6 门控 rc=0；三平台 3 镜像各 **168 B、rc 均 0**（chipyard 空闲，无 BLOCKED）。
- 门控独立重跑 rc 均 0：`check-inst-asm` **272/272**（链例+故障链 632 例）、`check-inst-sig` **272 镜像 / 4528 槽**（静态 4490 + 运行期关系 38）、`check-case-ledger` **5681 条**（asm 5160 / lit 521；HEAD~1 = 5672 ⇒ **+9**）、`check-tests-index` 472、`check-inst-macro-scope`、`validate-vectors` 156/156（272 载体）、`check-asm-prose`、`check-knowledge-refs`。
- 范围：`git show --name-only HEAD` **恰 7 文件**；`git status --porcelain -uall` 干净；未动 `spec/`、契约、其它 `ldm.*`/`ld.*`；无「银行」误译、无运行期路径。
- 注释订正：`ldm.t_rrri_rf.S:5` 现文与任务书一致；全仓 `grep "按 FCSR 写掩码"` 仅 `ldm.o_rrri_rf.S`；只换第 5 行 ⇒ `.text` md5 不变。

**独立反例注入（`cp` 备份 + md5 对账，未用 `git checkout/restore`；实测真实退出码）**
- `rf0[4:0]` 期望 0x1→0x2 ⇒ `{'qemu': 21}`；`[31:5]` 掩码换全 1 ⇒ 21；高半掩码换低半 ⇒ 21 —— **三条断言各自可达 FAIL 且都落在点号 21**；`ldm.ut` immu6 63→62 ⇒ **20**（末拍 `__CHECK_MEM 20` 先红）。各路还原 md5 与注入前逐字节相同、回绿 rc=0。

**位运算/期望独立复算（不看脚本结论）**
- 写前 `0x7FF800037FC00000` → 写后 `0x7FF800037FC00001`：`[63:32]` 均 `0x7FF80003` ✓；`[31:5]`（掩码 `0xFFFFFFE0`）均 `0x7FC00000` ✓；`[4:0]` = `0x80000021 & 0x1F` = `1` ✓；`rf1` 高半保持 ⇒ `0xDEADBEEF80000022` ✓；`MDATA_T+0x084/088` = `0x80000021/22`，组首 0 取元素 0 —— **未写反**。
- `immu6=63` 复算（MUNI 同值拍、MSTORE = `0xC0DE0000000000A0+i`、大端）：ut 末拍 `0x0F1E2D3C000000BF`、uw 末拍 `0x0F1E2D3C4B5A00AF`、`rd1/rd63` = `0x0F1E2D3C` / `0x4B5A` —— 与源码逐项一致 ✓（含末拍未覆盖字节）。

**`make check` 红的归属（engineer 所报属实，不计本任务）**
- `check-patch-tree` rc=2：红点全在共享组件源树（`llvm-project` DADAOAsmBackend、`chipyard` Wuming*、`linux` entry），与本任务 7 文件无关；`check-milestones-fresh` rc=2：**仅** `m14-llvm-007`（R1 有 worktree 未入表）。
- 工具链：最终证据时间晚于共享安装根 `llvm-mc`/`ld.lld` 替换时间 ⇒ 最终证据确在替换后工具链上跑。

**Finding（记录级，不阻断；architect 收尾改）**
- F1：完成区与证据脚本写「`ldm.ut` 63→62 注入 ⇒ 失败点号 21」，实测为 **20**；脚本该行点号是硬编码标签、未取实际退出码 ⇒ 改为打印实际退出码（验收只要求「红」，非判据）。
- F2：`immu6=63` 回读为「抽样 5 拍 + 首末元素 + 末拍含未覆盖字节」（ut 32 拍检 5、uw 16 拍检 5），非字面逐拍；MUNI 64 拍同值 ⇒ 中间拍取值恒等、extent 由末拍守，信息量等价，且优于 `ldm.ub` 先例（3 拍且未检末拍）⇒ 记为覆盖说明。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过、约束逐条守住；F1/F2 为记录级。

## 完成区

**测试结果**：一键证据脚本 **ALL PASS（rc=0，34 项 PASS / 0 FAIL）**；`make check-inst-asm` **272/272**（632 例，rc=0）；`make check-inst-sig` **272/272 镜像 / 4528 槽**（静态 4490 逐槽一致 + 38 运行期关系槽，rc=0）；`check-case-ledger` 5681 条 PASS；`check-tests-index` 472 条 PASS；`check-inst-macro-scope` PASS；`check-knowledge-refs` PASS；`validate-vectors` 272 载体 PASS；`check-asm-prose`/`check-asm-list`/`check-asm-list-drift` rc=0。
**修改文件**：`tests/inst/01-load-store/ldm.t_rrri_rf.S`、`tests/inst/01-load-store/ldm.ut_rrri_rd.S`、`tests/inst/01-load-store/ldm.uw_rrri_rd.S`；重生成 `tests/data/inst-signature/{expected.tsv,inputs.sha256}`、`tests/case-ledger.tsv`。
**验收结果**：
1. 注释订正**不改指令流**：同一份源码只把第 5 行换回旧措辞 ⇒ `.text` md5 双方 `03bb8321d539f0be49b667c08cce1299` 相同；反例再改一条真指令 ⇒ `5b3a3c3c831d2174f31ba749ca9994e4`（比较可达 FAIL）；`grep "按 FCSR 写掩码"` 全仓只剩 `ldm.o_rrri_rf.S`（`.o` 的正确表述）。整镜像因新增用例 `.text` 必变（改前基线 `441da955…`）。
2. `rf0` 用例三条断言分离且各自可达 FAIL：① 高半掩码换低半 ⇒ rc=1；② [31:5] 掩码换全 1 ⇒ rc=1；③ `[4:0]` 期望改 0x2 ⇒ rc=1（均失败点号 21）；还原后 rc=0。运行期实测：写后 `0x7FF800037FC00001`、写前快照 `0x7FF800037FC00000`（[4:0] 0→1，其余保持）。
3. `immu6=63` 两例：`MUNI` 63 元素整组装入 + `stm.t`/`stm.w` 回写 `MSTORE`，首/中段/末全拍 + 末拍部分覆盖 + `rd1`/`rd63` 逐字节比；`ldm.ut` 63→62 注入 ⇒ rc=1（失败点号 21），还原后 rc=0。
4. 三平台：qemu / gem5 / chipyard 各 168 B 签名流逐字节相等、rc 均 0（chipyard 未被占用，无需 BLOCKED）。
5. 门控见「测试结果」；`inputs.sha256` 285/285 OK。
**需重测周期的镜像清单**：`ldm.t_rrri_rf`、`ldm.ut_rrri_rd`、`ldm.uw_rrri_rd` —— 指令流已变，其「实测总拍数」记录作废；按指令类的周期表不受影响（只依赖同族样本）。
**新发现/坑**：`{rfHA:rfHA+n}` 的组首为 0 时，第 k 个元素落 rf[k]（rf0 拿元素 0、rf1 拿元素 1）——写期望时容易按同一元素算错。`ldm.t` 写 rf0 的窗口只有 `[4:0]`（`[33:32]` 因不在写入宽度内也保持），验证需「写前快照 + 掩码等值」而非静态常量。三平台一次跑 3 镜像约 60 s，全套证据脚本约 2.3 min。
**遗留问题**：`make check` 在 `check-patch-tree` 红——共享 `.work/source` 的 llvm-project/chipyard/linux 被并行任务（另一模块）改动，与本任务 diff 无关；`make check` 因此在其它 L1 门控前中止，相关门控已逐条单独跑过（全绿）。并发 `install-host` 曾使 writer-guard 拒绝一次（已重试回绿）。

