# m15-testcases-007: 故障例链式合并（落点校验后跳下一例，904 → 272 镜像）

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-006`（同改 `tests/inst/**` 与 lds）**必须先合入**；QEMU 侧 `m14-qemu-005/003/004` 已验证（清单见「派发前置」）。**不依赖 gem5 / chipyard 的代码改动**（理由见下）
**可并行分片**：否（同时改共享宏层 `inst_test.inc` + 落点段，单写者）
**预估**：4–6 h
**档位**：大改（异常返回路径的载体结构改 + 全量镜像数变化；复核 ≥4 路注入 + 全量行为对账）
**状态**：待验收

## 背景（用户 2026-11-16 裁定「B」+「等 qemu/gem5/chipyard 修改完后再派发」）

用户原话：「我特意说过，在 monitor 中，发生同步异常后，可以跳转到测试向量程序指定的位置，于是，就可以测试下一个故障例了」。

**机制本来就在**（现场证据）：

- 故障例触发前把落点写进 hmon 返回槽：`tests/inst/macros/inst_test.inc` 的 `__SET_HMON_RETURN`（`LOAD_ADDR rb20, HMON_BASE` + `LOAD_ADDR rb21, TEST_PAD` + `st.o rb21,[rb20,0xF8]`）；
- hmon 从该槽取返回地址并跳回：`tests/shared/bootrom/tiny/hmon.S`「`ld.o rd63,[rb0,HMON_SLOT_RETURN-0x1c]` → `cfx2rc cfx_hmon,cg5,rc3,rd63` → `escape cfx_hmon,[excp_cause_ip,0]`」；
- hmon 全程**只碰 `rd63`（保存到 `0xD8`、末尾恢复）**，寄存器组/内存不改 ⇒ 落点处可继续执行任意代码。

**唯一造成「一例一镜像」的是落点结束方式**：`__TEST_SECTIONS` 的 `__pad` 末段无条件 `SYS_EXIT`。因此 `inst_test.inc` 头部注释「故障例必须一例一镜像——异常不返回到被测指令之后」是**错误表述**，本任务须一并订正。

**现状规模**（现场派生）：**904 镜像 = 271 链例镜像 + 633 故障例镜像**；272 个 `.S` 中 261 个链+故障、10 个只有链例、1 个只有故障例（`00-isa-design/undi_reserved.S`，3 例）；**单文件故障例最多 9 个**（`01-load-store/ldm.*` 6 个文件）。

**空间实测**：`01-load-store/ld.o_rrii_ra.S` 链例镜像 `.text` = 4696 B；`CASE_N=23` 单例镜像 = 4896 B ⇒ 每个故障例体（含 guard）≈ 200 B；9 例最坏 ≈ 6.5 KiB，006 统一后的 `.text` 窗口为 16 KiB。落点段 `.faultpad` 当前 **108 B / 上限 128 B**。

## 目标

1. **链例镜像里也展开全部故障例体**（去掉 `TEST_FAULT*` 的 `.if CASE_N == \pt` 对链例镜像的门），每例唯一标号 `__fc_<点号>`；`-defsym CASE_N=<pt>` **保留**（单例调试路径不变）；
2. **每例末尾的 `__EXIT \pt` 必须保留**：它是「异常没有发生」的检出器（漏报异常 ⇒ 退出码 = 点号，判 FAIL），不得因链化删除；
3. **落点 `__pad` 改为**：读 hmon 的 `cause_id` 槽与期望 one-hot 比对 →
   - 不匹配 ⇒ `SYS_EXIT(点号)`（与现状同）；
   - 匹配 ⇒ 跳**下一例**；最后一例 ⇒ 跳收尾（`__PRINT` 结果缓冲 + `SYS_EXIT(0)`）；
4. **比对改为掩码**：`cause_id` 低 16 位 one-hot 相等即通过（现状是全 64 位 `br.ne`）；否则 `m14-qemu-005` 一填子原因 wyde（`ADR-0056`），633 例会全红；
5. **`__TEST_END` 改为「进入故障链」**；无故障例的 10 个文件仍要「打印 + 退出」（实现方式见「实现约束」）；
6. **`.faultpad` 扩容**（108/128 B 已满）——在 006 统一后的 lds 里放大该段上限并顺移后续段址；`ASSERT` 与 `inst_test.inc` 的 `.equ` 逐项对应；
7. **订正错误注释**（`inst_test.inc` 头部「必须一例一镜像」）+ `tests/inst/README.md` 写「**镜像 = 每 `.S` 一个**，故障例在同一镜像内顺序跑」。

## 实现约束（不规定具体机制，但这些必须成立）

- **下一例地址的取得不得依赖「知道自己是最后一例」以外的额外约定**：可用「guard 写后继地址槽 + 后继未定义时落 0 ⇒ 落点判 0 走收尾」，或「`.faulttab` 表 + 哨兵」，二选一；不得靠 `.S` 逐文件声明「我是最后一例」；
- 落点代码与数据槽必须**只用保留寄存器**（`rd20/rd21/rd22/rd23`、`rb11/rb16/rb20/rb21`），不得占用用例寄存器；
- 结果缓冲长度 `__PRINT TEST_BUF, ...` 只覆盖链例检查点（**故障例结果不写入缓冲**，见「待裁定」）。

## 待裁定（用户未答，勿自行决定）

**故障例的观测值是否记入结果缓冲**（记 ⇒ 三方逐字节比 `cause_id`；不记 ⇒ 只靠落点 in-guest 断言）：

- 建议**不记**：落点已按 spec 派生的 one-hot 做 in-guest 断言，记入缓冲只会把子原因位耦合进三方比对，而三侧对子原因的落地时间可能不同步；
- 若裁定「记」，须同时定义子原因位的比对口径（是否掩掉）并写进验收。

## 派发前置（派发前逐条现场核对，任一未达即不派）

1. `m15-testcases-006` **已合入 master**（同改 `tests/inst/**` 与 lds，串行）；
2. `m14-qemu-005`（页表异常子原因 wyde + TLB-37 条目级 + 5 处全宽断言改掩码）**已验证**；
3. `m14-qemu-006`（`Kaiwu-Vast` 同步异常路由）**已验证**；
4. `m14-qemu-003` / `m14-qemu-004` **已验证**（异步源 mask、`SYS_READC`/`SYS_FLEN` 取字缓冲）；
5. chipyard 与 QEMU 在当前批次镜像上**可跑**（chipyard 只当执行器，**不需改代码**）；
6. 用户点头派发（本任务属批次外新任务）。

## 前置口径裁定（用户 2026-11-16）

原稿第 5 条写「gem5 / chipyard 侧同期修改已验证」，但核对后 **两侧没有任何对应任务书**（`m16` 只有时序模型；`components/gem5` 与 `components/chipyard` 均无 `NONPTW`/`ADWBFAIL`/subcause 实现）⇒ 该条改为「chipyard/QEMU 可跑」。

**本任务不依赖这两侧的 ISA 对齐**，理由（三条硬事实）：

- 故障例全是 **Tiny 镜像**：无 PTW/TLB ⇒ `TLB-37`、子原因位都碰不到；Tiny 无 Vast ⇒ `§5.2` 路由碰不到；
- 落点比对已改**低 16 位掩码** ⇒ `cause_id[63:16]` 不参与判定；
- 链例字节流（4917 检查点）不含 cause。

⇒ gem5 与 chipyard 的 `ADR-0056` 子原因、gem5 的 `§5.2` Vast 路由已**另立 M16 任务**（`m16-gem5-009/010`、`m16-chipyard-003`），**不作为本任务前置**。

## 验收（真实 rc + 输出）

1. **镜像数**：`check-inst-asm` 报 **272/272**（原 904/904），`272 id` 不变；每 `.S` 恰好 1 个镜像；
2. **行为对账**：改前/改后逐例比 **`semi.out` 字节 + 退出码**，**272/272 相同**（链例部分字节流不得变化；故障例退出码 0）；
3. **检查点与故障点不变**：逐文件比「链例数 + 故障例数 + 点号序列」= 基线；
4. **漏报异常仍可检**（核心）：注入「让某故障例的触发指令改成不触发异常的等价指令」⇒ 该镜像 `SYS_EXIT(点号)`（**必红**，不许静默跳过）；
5. **链不串味**：注入「让某例的期望 one-hot 写错」⇒ 恰好该点号失败，且**后续例不再执行**（退出码 = 该点号）；
6. **≥4 路注入**（`cp`+md5 还原）：① 上面的漏报异常；② 期望 one-hot 写错；③ 落点跳转目标 +4（错落）⇒ 立即红或超时（记录）；④ 把掩码比对改回全 64 位并在测试里造一个子原因位非零的场景 ⇒ 红（证明掩码是必要的）；
7. **样本交叉**：从 `01`/`07`/`12-misc` 各抽 1 个文件，用**单例模式**（`CASE_N=<pt>`）跑其故障例，退出码与链式模式一致；
8. 门控：`check-inst-asm`、`check-case-ledger`、`check-inst-macro-scope`（含 S9）、`check-tests-index`、`check-dirs`、`check-no-residue`、L1 `make check`；
9. **行为等价以三方为准**：chipyard / QEMU 至少两侧在**同一批镜像**上逐字节一致（gem5 若未就绪，说明缺侧并保留现场）；
10. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只动 `tests/inst/**`（`inst_test.inc` 的 `TEST_FAULT*`/`__FAULT_GUARD`/`__TEST_SECTIONS`/`__TEST_END` + lds）、`tools/testcases/inst/run_asm_suite.py`（**仅**镜像枚举/`CASE_N` 相关）、`tests/inst/README.md`、本任务书；
- **不改任何用例的期望值、点号、用例顺序**；不改 `tests/arch/**`、`components/**`、`spec/`、`contracts/`；
- 构建/跑批不得与其它任务并行（`ISS-462`）；
- 不提交 git；注入还原 `cp`+md5（**禁 `git checkout/restore`**）；基线钉死 commit（`ISS-458`）。

## 完成区

**测试结果**：一键证据脚本 48/48（含 L1；`SKIP_L1=1` 时 45/45；含 4 路注入 + 单例交叉 + 反例自检）；`check-inst-asm` 272/272；L1 除 3 个外部红外全绿（逐项归因见下）
**修改文件**：`tests/inst/macros/inst_test.inc`、`tests/inst/linker/inst-tiny.lds`、`tests/inst/README.md`、7 个册层 `.inc`（01/02/03/04/05/06/07）与 2 个 `.S`（`add.si_riii_rd.S`、`ret_riii_ra.S`）里的 `TEST_FAULT*` 宏体、`tools/testcases/inst/run_asm_suite.py`
**验收结果**（真实输出）：
- 镜像数：**904 → 272**，每 `.S` 恰 1 个；`check-inst-asm: 272/272 镜像通过（272 个 id；链例 + 故障链 633 例）`
- 行为对账（基线树 `git archive fd4c79f8` ✕ 本树、同一批二进制）：**271/271** 与基线链例镜像 rc + `semi.out` 字节全等；meta（链例数 + 故障点号序列）272/272 相同；`undi_reserved.S`（0 链例）rc=0 / 0 B（基线无镜像）
- 段大小：`.text` 最大 8000 B（≤0x4000）、`.faultpad` 140 B（≤0x200）、`.faulttab` 最大 288 B（≤0x480），`ASSERT` 全绿
- 注入（临时树副本；源树 md5 前后一致）：漏报异常 ⇒ rc=23；期望 one-hot 写错 ⇒ rc=23 且后续例(24)未执行；落点 +4 ⇒ rc=124（超时）；**掩码改回全 64 位 ⇒ rc=24**（Tiny 该例实测 `cause_id=0x0200000000000002`，期望 `0x…02`）⇒ 低 16 位掩码是硬要求
- 单例交叉：`01`/`07`/`12-misc` 共 4 个点，链式 rc=0 = 单例（`CASE_N=<点号>`）rc=0
- 门控：`check-inst-asm`、`check-case-ledger`、`check-inst-macro-scope`（含 S9）、`check-tests-index`、`check-dirs`、`check-no-residue` 全 PASS
- L1 `make check`：3 个红逐项归因，均与本任务改动零交集 —— `check-patch-tree`（components/linux 补丁树断言，他任务在飞）、`check-run-artifacts`（别任务 reviewer 的 `review-*.log` 命名）、`check-milestones-fresh`（`m14-qemu-007` worktree 未登记）；本任务无任何 VIOLATION
**下一例机制**（二选一里的「`.faulttab` + 哨兵」）：表按点号索引存「本例入口 `__fc_<点号>`」；落点读 `点号+1` 槽：非 0 ⇒ 跳下一例，读到 0（`__TEST_SECTIONS` 追加的表尾哨兵）⇒ 跳收尾。⇒ **无「我是最后一例」声明**，且不依赖 `__TEST_END` 与故障例在 `.S` 里的先后（两种排版都存在：50 个文件故障例在 `__TEST_END` 之前）
**新发现/坑**：
- `__PRINT` 是 do-while ⇒ `len=0` 死循环（0 链例文件撞出）；收尾处已用 `.if __NCHECK > 0` 兜住（更彻底修法见遗留）
- Tiny 的 CFXMEM（EA=0）在**链式上下文**里 `cause_id` 高 56 位非零（`0x0200_0000_0000_0002`，单例镜像里是 `0x02`）⇒ 全宽比较必红（ADR-0056 D2 的掩码是必要条件，不是防御性冗余）
- `.faulttab` 用 `.org 点号×8`，要求点号升序且不重号（扫描器 `pts_ok` 已钉；重号会汇编硬报错）
- 撞写者 6 次（`install-host` ×4、chipyard 重建 ×2）；处置 = 等写者退出 + 重跑（3 次），未以重试掩盖根因
**遗留问题**：
- **chipyard 两侧整批核对 BLOCKED（外部）**：`m16-chipyard-003` 正在反复重建 Verilator。已留现场：批次 A（chipyard md5 `1547c9d`）234/272 两侧字节一致、38 红=该 build 的 `GewuFile: malformed excp_cause_id` 断言；同 build 下**基线**镜像（`ld.o_rrii_ra` `CASE_N=24`）同样 rc=255 + 同一条断言 ⇒ 改前即红；新 build（md5 `e723410`）上该基线例 rc=0xF1、合并镜像 rc=0/176 B ⇒ 已不复现。**待该任务合并后重跑整批**
- gem5 两侧未跑（本批未纳入）
- 文档/注释残留（本任务允许文件集外）：248 处 `.S` 注释仍写「一例一镜像」（209 文件）、`tests/inst/MIGRATION.md §2`、`tests/inst/inventory.md`、`docs/Process-07` 仍描述「一例一镜像/两种镜像」⇒ 建议另立清理任务
- 「故障例结果是否记入结果缓冲」仍为**待裁定**（按「不记」实现）；`__PRINT` 的 `len=0` 预判建议收进宏本身

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查，改动源码 + 证据脚本）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 落点首版用「本例体末尾 fall-through 即下一例入口」；实测 50 个文件的故障例排在 `__TEST_END` **之前**，最后一例顺落到 `__TEST_END` 的跳转 ⇒ 回到链首死循环（53 个镜像超时） | ✅已修 | 改为「表按点号索引 + 落点读 `点号+1` 槽 + 表尾哨兵」：`__FAULT_BODY_END` 写 `__fc_<pt>`，`__pad` 查 `FAULTTAB+8+pt*8`，0 ⇒ `jump __fault_finish` | 272/272 rc=0；271/271 字节与基线全等 |
| `__NCHECK==0`（`undi_reserved.S`）时收尾 `__PRINT len=0` 死循环（do-while） | ✅已修 | 收尾打印加 `.if __NCHECK > 0` | 该文件 rc=0 / 0 B，单例 rc=0 |
| 编辑 `.equ` 段时误插一行重复 `TEST_DATA` | ✅已修 | 删除重复行 | `awk` 逐项核 `.equ` ↔ lds 布局一致（B8 ×3） |
| 证据脚本 `cmp_beh`：记录键重复拼 `#0`、失败计数用了两个变量（会「有 FAIL 行仍 PASS」） | ✅已修 | 统一用 `rec["id"]`、单一 `fails` 列表 | H 段篡改一条 sha256 ⇒ rc=1 且定位到文件；还原后回绿 |
| `run.sh` B8 用 `$NF` 取 `.equ` 值，吃到行尾注释 ⇒ 空值假红 | ✅已修 | 改取第 5 字段（`ENTRY + 0x…`） | B8 ×3 OK |
| `inj_one.sh` 的 `mask_full` 用 `set.rd rd22, -1`（汇编成 `set.ow` 全 1，可跑但语义隐晦）；另有两组合成「子原因位」注入属多余 | ✅已修 | 改显式 `set.ow rd22, wp0, 0xFFFF`；删合成注入，改用真实场景（链内 CFXMEM 的 `cause_id` 高 56 位非零） | F4 rc=24（红），F0 对照 rc=0 |
| 证据脚本 E4/E5 原先只归因 `check-patch-tree`，实际 L1 另有 2 个外部红（`check-run-artifacts`、`check-milestones-fresh`） | ✅已修 | 改为「失败目标 ⊆ 外部集 + 逐项归因证据 + 本任务无 VIOLATION」 | 全量 run.sh：E4/E5/E6 全 OK（47/47） |

判决：本轮 finding 全部 ✅已修，无未修项；状态 → `待验收`。

### 第 1 轮 reviewer 验收（独立重跑，非读完成区）

**重跑记录**（本人终端输出）：
- `make check-inst-asm`：`272/272 镜像通过（272 个 id；链例 + 故障链 633 例）`，EXIT=0（9.4s）
- 5 门控（check-dirs/no-residue/case-ledger/tests-index/macro-scope）全 PASS；tests-index「472 条」；macro-scope 仅 S9 WARN（净收益≤0，均非本任务新增）仍 PASS
- 行为对账（独立复现）：`git archive fd4c79f8` 建基线树（272 .S）→ base 904 镜像 + merged 272 镜像（同批二进制），`cmp_beh` PASS：meta（链例数+故障点号）**272/272**、链例镜像 rc+`semi.out` 字节 **271/271** 全等、1 个无链例（`undi_reserved.S`）rc=0/0B
- 容量：`.text` 最大 8000 ≤0x4000、`.faultpad` 140 ≤0x200、`.faulttab` 288 ≤0x480（`ft2it_orri_rf` 34 点）
- 4 路自设计注入（临时树 `cp`，源树 md5 `7a175d97…` 前后一致）：① 哨兵误写 0xDEADBEEF ⇒ **rc=24**；② 掩码回全宽 ⇒ **rc=24**（证实 CFXMEM `cause_id` 高 56 位非零，低 16 位掩码必要）；③ `.org (pt)*8→+8`（槽位错）⇒ **rc=124 超时**；④ 删表尾哨兵 ⇒ **rc=0（记录：哨兵冗余**，被 `.testdata` 前零填充间隙掩盖，防御性保留，机制仍正确）
- 单例交叉：01/07/12-misc 3 点链式 rc=0 = 单例 rc=0

**机制核对**：`.faulttab` 按点号×8 索引 + 表尾哨兵正确（反汇编 `__pad`：`and.o rd20,0xFFFF` 掩码、读 `tab[pt+1]`、0⇒`__fault_finish`）；无故障例 10 文件 `__fault_chain`=`__fault_finish` 同址（`atomic_rmw.S` 实测）走打印+退出；50 文件故障例在 `__TEST_END` 前 / 212 后 / 0 横跨，机制与排版无关。

**越界**：改动仅 `tests/inst/**` + `run_asm_suite.py` + 本任务书，无 `tests/arch`/`components`/`spec`/`contracts`。

**L1 `make check`**：3 红全外部——`check-milestones-fresh`（m14-linux-012、m14-qemu-007）、`check-patch-tree`（qemu/gem5/linux 补丁树断言）、`check-temp-dirs`（m14-linux-005/009 陈旧目录）；本任务**零 VIOLATION**（9 处提及仅路径）。

**findings**：
1. `tests/inst/README.md` L41 链接布局数字与 lds/`.equ` 不符：写 `.faultpad 0x4000–0x4100`、`TEST_FAULTV 0x4100`、`.faulttab 0x4200–0x4600`、「放大到 0x100」；实际 `.faultpad ≤0x200`、`TEST_FAULTV 0x4200`、`.faulttab 0x4300`。**文档级笔误**，建议收尾改正（不阻断）。
2. ④ 删哨兵 ⇒ rc=0：哨兵现布局下被零填充掩盖（冗余防御），机制正确、不阻断。

**未决项（供架构师）**：工作树现有一处**未提交**改动——`tests/inst/macros/inst_test.inc` 删了 `__EXIT \pt`（漏报异常检出器，mtime 07:43），**非本 reviewer 所为**（本 reviewer 全程只在 `/tmp` 临时树注入，源树 md5 自证未动）。现场另有第二个 m15 评审进程（run.sh PID 995325 + `review-inj/inst_test.inc.preI1` 备份，md5=`552afffa…` = HEAD）。请 commit 前核 `git status` 干净并恢复该行；同一任务**只允许一个 reviewer**，请处置并发。

**判决：Accepted**（交付物 64ce03e7 达标；工作树脏为并发进程问题，非交付缺陷）。
