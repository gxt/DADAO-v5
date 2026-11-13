# m13-qemu-006: `ldm`/`stm` 基址/索引重叠 ⇒ ILLI（QEMU）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-spec-005`（spec 定稿）
**可并行分片**：否（单组件单写者）
**状态**：已验证

## 用户裁定

`ldm`/`stm` 的基址/索引寄存器**不得**落在被传送的寄存器范围内 ⇒ 违反 ⇒ **ILLI**（原口径「允许重叠、按原始值计算」作废）。

## 范围（只改 QEMU）

1. `target/dadao/insn_trans/` 的 `ldm`/`stm` 译码函数（`trans_block.c.inc` 一族）加检查：
   - **只检查 `ldm`**：RD 形式 `rdHC ∈ [rdHA, rdHA+immu6)` ⇒ 非法；RB 形式 `rbHB ∈ [rbHA, rbHA+immu6)` ⇒ 非法
   - **`stm` 不加检查**（允许重叠：只读传送范围、不写寄存器）
   - **RA/RF 形式：不适用**（范围在 RA/RF bank，基址/索引分别在 RB/RD）
2. 检查必须在**任何元素处理之前**（与既有的 `immu6=0`/范围检查同位置）。
3. 不改其它语义。

## 验收

构造 3 组例：`ldm` RD、`ldm` RB（应 ILLI）；`stm` RD/RB 重叠（应正常执行）：
- 基址落在范围内 ⇒ **ILLI**（且不发访存、不写寄存器）
- 基址在范围外一位（边界）⇒ 正常执行

`check-inst` rc=0；273 例 md5 不变；**可达 FAIL 注入**（去掉检查 ⇒ 该例不再 ILLI）。

## 纪律

- 重建 QEMU 前申报耗时；`JOBS=8`；不占 207/208
- 注入还原 `cp`+md5+`touch`（`cp -p` 假绿坑）
- 不 commit/push、不改台账；状态改 `待验收`
- 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-13）

自审方式：逐行复核 `trans_mem.c.inc` 改动（新增 helper + 8 处 guard）与证据脚本；逐条对照 spec `SimRISC-01 §1/§2`、`legality_rules.yaml::mreg_range_addr_overlap`、`opcodes.yaml` 的合法性表达式（`rdhc < rdha || rdhc >= rdha + immu6`、`rbhb < rbha || rbhb >= rbha + immu6`）。

- **逻辑**：helper 判 `addr ∈ [start, start+len)`，恰为契约表达式的否定；8 个 `ldm` 函数（RD 7 + RB 1）全覆盖，`stm`/`ldm-ra`/`ldm-rf` 零改动（`git diff` 逐行核）。检查与既有 `immu6=0`/范围检查同一 guard、translate 期生效 ⇒ 任意元素前判定。
- **边界**：范围端点（`hc == ha+hd`、`hc == ha-1`）实测正常；`hd==0` 先于 helper 判定，helper 对 len=0 也恒 false（无 UB、无溢出：字段 ≤63）。
- **防造假**：证据 30 项断言全部有可达 FAIL 路径；注入（helper 改 `return false`）⇒ 恰 16 例非法例变红、探针回绿；还原 `cp`+md5+`touch` ⇒ 二进制 md5 与注入前相同。
- **自审发现（均已处置）**：
  1. 生成器把 end 例的 `rd14` 期望泄漏进 before 例 ⇒ 7 例假红；✅改为按例独立构造期望后 37/37。
  2. 内存地址写成 `@ENTRY+0x100000+0x0`（token 只允许单个偏移）⇒ 解析报错；✅改为单一偏移。
  3. dump 模式在 `expected_fault` 例上仍走 SYS_EXIT（拿不到状态）⇒ ✅改用「mapped 重叠 + 正常 expected_state」双向探针：改前 PASS（元素确实写入、覆盖索引/基址寄存器）、改后 ILLI。
- **无未修 finding**，状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-13）

**重跑（HEAD `70a7d477`，命令均在仓库根执行，退出码现场取）**
- `./该任务的运行期证据目录/run.sh` → `== summary: PASS=30 FAIL=0 ==`、`RUNSH_EXIT=0`；`Results: 37 total, 37 passed, 0 failed`；`check-inst` rc=0（`1141 total, 1136 passed, 0 failed, 5 deferred, 0 errors, skipped_profile=44` + `44 total, 44 passed`）；sweep `covered=273`、`md5=2d4d94651346ef673c5a855e024c1489` 不变。
- 改前二进制 `8bea11c1…`：16 红=非法集、8 例 `CFXMEM`、8 例 guest FAIL、探针 rc=0（元素确实写入）；改后 `b366e491…`：16 例全 `0xF8`、合法例全 `0x00`、探针 rc=1 两枚 `Unexpected fault: ILLI`。
- `make check-legality-drift` rc=0（12 chapters OK）；`make check-rule-refs` rc=0（规则 18 条）；`make check-component-changelog` rc=0（32 项）。
- `make check-patch-tree` rc=2：8 条全 `gem5`（decode_*/b1* 断言⑥⑨），**qemu 0 条**；`git diff --name-only 834cebed..HEAD` 仅 3 个任务文件、`components/gem5` 0 行 ⇒ 非本任务所致（`/tmp/opencode/m13-gem5-008` worktree 在册、其任务书 `状态：待验收`）。
- `make check-knowledge-refs` rc=2：唯一具体 `.work/**` 引用在 `m13-spec-005` 任务书 §93（非本任务；本任务 `.work/source/qemu` 属豁免类）。

**独立注入①（RD/RB 字段对调；`cp` 备份 + md5 + `touch` 还原，未用 git checkout）**
- 源 md5 `e9db4a9a…` → 对调 7 处 `a->hc`→`a->hb`、1 处 `a->hb`→`a->hc`（diff 非空）→ `make build-qemu` rc=0（`b366e491…`→`5b7d4b5d…`）→ batch `37 total, 21 passed, 16 failed`（红集 = 16 非法集 `0 1 4 5 8 9 12 13 16 17 20 21 24 25 28 29`）、探针 rc=0。
- 还原：源 md5 回 `e9db4a9a…`、无 `INJECTED` 标记、`git -C .work/source/qemu status` 干净；重建回 `b366e491…`；batch 37/37 rc=0、探针 rc=1（2×ILLI）。前后任务 3 文件 md5 与快照逐项相等（`/tmp/opencode/m13-qemu-006-review/snapshot-before.txt`）。

**审查者自构造 5 例**（编码取 `contracts/opcodes.yaml` 字段布局，独立于 engineer 向量）
- `rdhc==rdha(10)`、`rbhb==rbha(10)` ⇒ 改后均 ILLI；改前两例均红（`Expected fault ILLI, got guest FAIL(0x01)` / `got CFXMEM (0xF1)`）⇒ 边界内端点判据可判。
- `ldm.o-ra`（opc `0x3C`）/ `ldm.o-rf`（opc `0x3E`），索引 `rd12` 数值落在 `[10,14)` ⇒ 均 `exit 0x00`、RA 元素值正确 ⇒ **RA/RF 不适用成立**。
- `stm.w` `rdhc=rd11` 落在 `[rd10,rd14)` ⇒ 正常、4 字入存、`rd11` 保持 `0x100002` ⇒ **stm 允许 + 数据正确 + 索引不变成立**。

**零副作用（reviewer 自证，`-d op` TCG dump）**：同一 mapped 重叠例（PC `ffffff010164`，word `0x28283304`）——改前 TB 含 4×`qemu_ld_i64` + `st_i64 … env,$0x50/$0x58/$0x60/$0x68`（含索引 `rd12`），exit `0x01`；改后同一 TB 仅 `call raise_exception,$0x8,…,$0x28283304` + `exit_tb`，**无任何 `qemu_ld`/寄存器写**，exit `0xF8`。代码侧：8 处 guard 是 trans 函数首条语句、与 `immu6=0`/范围检查同一 `if`，命中即 `gen_exception_illegal(); return true;`（先于 `load_rb/load_rd`，translate 期、任意元素前）。

**约束核验**：只改 `ldm`（RD 7 + RB 1 = `SimRISC-01 §194` 的 8 条；RD 用 `a->hc`、RB 用 `a->hb`，未搞反）；`stm`/`ldm-ra`/`ldm-rf` 零改动（patch 逐行核）；修改文件 3 个与 `git show --stat HEAD` 一致；完成区 16 行、审阅记录 13 行（均 ≤限长）；无绝对运行期路径；HEAD 仅 1 个 `WIP:` 提交（architect），engineer 未自行 commit/push、未改台账。

**判决：Accepted**（非阻塞 finding，交 architect 收口）：① run.sh 的 `8/8`（CFXMEM/guestFAIL）是字面期望而非现场计数（设计变更会假红、不会假绿）；② worktree 根有被忽略的 `build1.log` 残留（`*.log`，随 worktree 删除）；③ `check-knowledge-refs` 悬空引用属 `m13-spec-005`、`check-patch-tree` 8 条属 gem5，均非本任务。

## 完成区

**测试结果**：一键证据 `run.sh` → `PASS=30 FAIL=0`、rc=0（现场计数）。三组例实测（37 例：A `ldm` RD 28 / B `ldm` RB 4 / C `stm` 5，非法 16）：
- A `ldm` RD（`ldm.ub/uw/ut/sb/sw/st/o`）：`rdhc` 在 `[rdha,rdha+immu6)` ⇒ 14 例全 `exit=0xF8`（ILLI）；`rdhc=rd14`（恰在外一位）与 `rdhc=rd9`（范围前一位）⇒ `exit=0x00`，加载值与符号扩展按 spec 逐条相符。
- B `ldm.o` RB：`rbhb` 在 `[rbha,rbha+immu6)` ⇒ ILLI（`0xF8`）；`rbhb=rb14`/`rb9` ⇒ 正常，`rb10..rb13` 加载值全对。
- C `stm` RD/RB 重叠（`stm.b/w/t/o`-rd + `stm.o`-rb，索引/基址落在存储范围）⇒ 全部 `exit=0x00`，存储内容与未变寄存器逐项一致。
- 不发访存/不写寄存器：改前二进制对 unmapped 重叠例 fault `CFXMEM`（8 例，证明会发起访问）、mapped 重叠例跑到 guest FAIL（8 例）；两枚 mapped 探针改前 PASS（元素确实写入并覆盖 `rdhc`/`rbhb`）、改后 `Unexpected fault: ILLI`（元素零生效）。

**修改文件**（与 `git status` 对账，3 个）：`components/qemu/patches/target/dadao/insn_trans/trans_mem.c.inc.patch`（`make_patch.py` 导出，1 written / 65 unchanged）、`components/qemu/changelog.md`（M13 一条）、本任务书。组件源 `.work/source/qemu` 按 E1/E4 收敛为 base+1 单提交、工作树干净；未 commit/push 本仓库、未改台账。

**验收结果**：`check-inst` rc=0——Vast `1141 total, 1136 passed, 0 failed, 5 deferred, 0 errors, skipped_profile=44`；Tiny `44 total, 44 passed`（现场日志）。273 例 sweep `covered=273`、md5 `2d4d94651346ef673c5a855e024c1489` 不变。门控：`check-component-changelog`/`check-legality-drift`（12 章）/`check-rule-refs`（规则 18 条）均 rc=0；`check-patch-tree` qemu 命中 0 条，8 条全属并发写者 gem5（`m13-gem5-008` 进行中）。改前后二进制 md5：`8bea11c1…` → `b366e491…`。注入：`git diff --name-only` 非空 ⇒ 恰 16 例非法例变红、探针回绿 ⇒ `cp`+md5+`touch` 还原 `e9db4a9a…`、重建二进制 md5 回到 `b366e491…`、37/37 回绿。

**新发现/坑**：① 向量内存地址 token 只允许**单个** `+0x…` 偏移（`@ENTRY+0x100000+0x1` 非法）；② `expected_fault` 例在 dump 模式下仍走 SYS_EXIT，拿不到状态 ⇒ 「元素零生效」要用「无 fault 的 mapped 探针」双向证；③ 生成器复用期望 dict 会串味（end 例的 `rd14` 漏进 before 例），期望须按例独立构造；④ 安装根二进制可作改前基线（md5+行为双重核验），无需回滚重建。

**遗留问题**：无（持久向量册的 overlap 用例归 `m13-testcases-013`，见 `m13-spec-005` 非范围）。

#### 收尾（architect，2026-11-13 08:25）

- reviewer **Accepted**：`run.sh` 30/0；37/37；`check-inst` rc=0（1141/1136/0 failed/5 deferred）；273 md5 不变。
- **检查位置正确**：8 处 guard 均为 trans 函数首条语句、与 `immu6=0`/范围检查同一 `if`，**先于 `load_rb/load_rd` 与任何 `tcg_gen_*`**。
- **字段未搞反**：RD 7 条用 `mhc`、RB 1 条用 `mhb`；reviewer 自选「字段对调」注入 ⇒ 恰 16 例非法集变红 ⇒ 字段是载荷性的。
- **`stm` 允许 / RA/RF 不适用**：reviewer 自造 5 例（含 `stm.w rdhc` 落在范围 ⇒ 正常、4 字入存、索引保持原值；`ldm.o-ra`/`rf` 索引数值落块内 ⇒ 正常）。
- **零副作用双证**：① 改前/改后二进制对照（8 例 `CFXMEM` ⇒ 改后 ILLI，不再发起访问）；② TCG 级 `-d op` dump——改前 TB 含 4×`qemu_ld_i64` + 4 个 `st_i64`、改后仅 `raise_exception` + `exit_tb`。
- 文档级（`ISS-418`）：`run.sh` 的 `8/8` 是字面期望而非现场计数（设计变更会假红、不会假绿）。

