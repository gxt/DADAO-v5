# m15-qemu-002: 窄 `lr` 三条序改「只写低 W 位、高位保持」（QEMU）

**模块**：qemu
**项目里程碑**：M15
**依赖**：无（`m15-idl-020` D3 已给依据；IDL 侧已于 2026-11-19 裁定完成）
**可并行分片**：否（QEMU 单写者）
**预估**：1–2 h
**档位**：小改
**状态**：待验收

## 背景（`m15-idl-020 IDL 差异盘点` D3）

**用户 2026-11-19 裁定**：窄 `lr`（`lr.t`/`lr.w`/`lr.b`，各 `.nn`/`.an`/`.ar` 三序，**共 9 条**）**只写目标寄存器低 W 位、高位保持原值**（非零扩展、非符号扩展）。IDL 已按此实现（`idl/SimRISC-01.idl` 的 9 条 `lr` body）。

**QEMU 侧仍是整 64 位零扩展**：`components/qemu/patches/target/dadao/insn_trans/trans_atomic.c.inc.patch` 的 `store_rd(a->hc, val)`（`m15-idl-020` 复核定位）

`MEMORY.md` 与 `m15-idl-012` R2 已登记「实现侧需据此修正」，本任务即该修正。

## 要做

把 9 条窄 `lr`（`lr.{t,w,b}.{nn,an,ar}`）的结果写回改成：**读目标寄存器旧值 → 只替换低 W 位（`.t`=32、`.w`=16、`.b`=8）→ 写回**；`lr.o`（64 位）**不动**。

**oracle 是 IDL**：以 `idl/SimRISC-01.idl` 对应 9 条 body 的语义为准（`render.py` 已保证它与 spec 一致），**不得**按 RISC-V/ARM 的零扩展习惯实现。

## 验收（逐条贴真实 rc）

1. **行为与 IDL 一致**：9 条各给「高位置哨兵旧值 → `lr` → 高 W 位保持、低 W 位为新值」的实测（QEMU 侧用例或探针）；
2. **`lr.o` 不回归**（仍整 64 位）；
3. **不回归**：`check-qemu-semantics` 与既有 `lr` 相关用例
4. **可达 FAIL**：把某条改回整 64 位零扩展 ⇒ 对应用例红（`cp`+md5 还原 + 重建）；
5. `check-patch-tree` **QEMU 段 0 问题**；合并态（`Process-07 §5a`）。

## 完成区

**测试结果**：`make build-qemu` rc=0；探针 15 检查点全过（9 条窄 `lr`×3 序 + 2 条 `lr.o` + 4 条异位/最高位窗口），IDL oracle 逐点 15/15；注入 `.t` 回退整 64 位写回 ⇒ guest rc=1（点 1 红），`cp`+md5 还原（md5 相等）⇒ 重建回绿；`make check-inst-asm`（L2）rc=0 `272/272 镜像 / 632 例`；`make check`（L1）除 `check-syscall-abi` 因本 worktree 无共享 linux 源码树而 `FileNotFoundError`（与本改动无关；补上共享源码后 85/85 rc=0）外全绿（227 项 PASS）；合并态（master `7282b64d` + 本任务 diff 的临时树）`make check` 同结论、`run_asm_suite` 272/272，最终 diff 上的四处相关门控（`check-component-changelog`/`check-patch-tree`/`check-index-blobs`/`check-case-ledger`）另在合并态复跑 rc=0。

**修改文件**：① `components/qemu/patches/target/dadao/translate.c.patch`（新增 `store_rd_narrow()`，`gen_lr()` 对 `width==8` 走 `store_rd`、窄宽度走切片写；由 `make make-patch qemu` 重生成 index/hunk）；② `tests/inst/12-misc/lr.{t,w,b}.{nn,an,ar}_orrr_rd.S` 9 个载体（期望值按 §1.1 订正 + 顶部「写宽」注释）；③ `tests/case-ledger.tsv`（`--write` 重生成，108 行 = 9×12）；④ `components/qemu/changelog.md`（M15 一条）。

**验收结果**（真实输出）
1. `run_asm_suite: 272/272 镜像通过（272 个 id；链例 + 故障链 632 例）` / `check-inst-asm: PASS`
2. 探针 `[PASS] lr_highbits_probe.S chain 检查点 15 / {'qemu': 120} B / rc {'qemu': 0}`
3. 逐条实测（哨兵 `0xDEADBEEFCAFEF00D`、拍 `0x0123456789ABCDEF`）：`lr.t.{nn,an,ar}`→`0xDEADBEEF01234567`；`lr.w.*`→`0xDEADBEEFCAFE0123`；`lr.b.*`→`0xDEADBEEFCAFEF001`；`lr.o.{nn,ar}`→`0x0123456789ABCDEF`（整 64 位）；异位窗 `lr.t@+4`→`0xDEADBEEF44556677`、`lr.w@+2`→`0xDEADBEEFCAFE2233`、`lr.b@+1`→`0xDEADBEEFCAFEF011`；`0x80000000` 窗 → `0xDEADBEEF80000000`（非 sext）
4. `[PASS] 反例被检出（.t 回退 64 位写回）期望=guest rc 1 实际=rc 1`；`[PASS] 还原 md5 对账 期望=… 实际=…`（两值相等）；重建后 QEMU md5 回到注入前值
5. `check-patch-tree` rc=0（qemu **69 份 / 0 问题**）；`check-index-blobs` rc=0；`check-case-ledger` rc=0（现场 5672 条）；证据脚本 = 运行期证据目录内的 `run.sh`（默认 7 项检查，`--inject` 走反例门控，`--full` 追加全册回归）

**新发现/坑**：
- 任务书写 `insn_trans/trans_atomic.c.inc.patch`，**该文件不存在**；实际落点是 `translate.c.patch` 的 `gen_lr()`（`m15-idl-020` 完成区写的也是 `translate.c.patch`）。
- 既有 9 个 `lr` 载体**隐含假设「rd 初值为 0 且零扩展」**（例 5 起哨兵已落在 rd2），语义一改即红 ⇒ 必须同步订正期望，并由 `--write` 重生成 `tests/case-ledger.tsv`（该门控按用例行文本做删除哨兵）。
- `check-qemu-semantics` 已于 TESTCASES-076t 退役，现行等价 = `check-inst-asm`（qemu-only L2）；它走**共享安装根**二进制，独立 worktree 里需做任务侧安装根镜像（只读符号链 + 把 `qemu-system-dadao` 指本任务构建），**不得写共享安装根**。
- 建议沉淀：`check-inst-asm` 默认跑安装根旧二进制时，别处的已修 bug（`m15-qemu-001` 的 `ftscmp`/`foscmp`）会假红 —— 判读「本任务回归」前先核二进制来源。

**遗留问题**：
- 本任务只改 QEMU；gem5/chipyard 仍整 64 位零扩展 ⇒ 三平台 `.S` 载体在 gem5/chipyard 上会红，待同批 `m15-gem5-002`/`m16-chipyard-014` 落地（L2 `check-inst-asm` 只跑 qemu，门控不受影响）。
- **台账待主会话处理**：`milestones-m15.md` 的 `m15-qemu-002` 行仍在「待开始」（本任务书已置 `待验收`）⇒ `check-milestones-fresh` 报 A1/R1；台账更新归派单侧，本任务未改共享台账。

## 审阅记录

### 第 1 轮 engineer 自审

审查对象：`translate.c` 的 `store_rd_narrow()`/`gen_lr()`、9 个载体期望值、`case-ledger.tsv`、changelog、运行期证据脚本 + oracle。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 窄写必须在 `rd0` 上无副作用（否则破坏硬连零） | ✅已修 | `store_rd_narrow()` 首行 `n == 0` 早退，与 `store_rd()` 同口径 | 载体「rdHC=rd0」例（点 14）全绿 |
| `mask = 1ULL << (8*width)` 的位宽风险 | ✅不修 | 只在 `width ∈ {1,2,4}` 调用（`gen_lr` 分支保证），位移 ≤ 32 无 UB；`.o` 走 `store_rd` 原路径 | `lr.o` 点 10/11 实测仍整 64 位 |
| 探针点 13 期望算错（`P1+2` 窗应为 `0x2233`，初写 `0x3344`） | ✅已修 | 探针与 oracle 的 `k=2` 窗改 `0x2233` | 修前 guest rc=13 红 → 修后 rc=0 绿（真实检出，非伪造） |
| 证据脚本基线用 `HEAD~1`（违反 Process-07 §5b） | ✅已修 | 基线改为 `manifests/components.lock.toml` 锁定的 qemu commit（固定值） | 补丁↔源码一致 / `git apply --check` 两项 rc=0，patch 头 `base=c3d48b7d1e89` |
| 只改 patch 文件不足以保证被测代码正确（源码与补丁可能漂移） | ✅已修 | 证据脚本新增「补丁↔组件源码净差逐字节比对」+「pin 基线临时树 `git apply --check`」 | 两项均 `[PASS]` |
| `check-inst-asm` 首跑 261/272（9 lr + 2 fp）被误读为回归 | ✅已修 | 定位为走共享安装根旧二进制（`ftscmp`/`foscmp` 缺 `m15-qemu-001` 修复）；改任务侧安装根镜像指本任务构建 | 重跑 `check-inst-asm: PASS` `272/272` |
| 12-misc 载体改期望会破 `check-case-ledger` | ✅已修 | `python3 tools/infra/check_case_ledger.py --write` 重生成（108 行 = 9×12，其余行未动） | `check-case-ledger: PASS（现场身份 5672 条）` |
| changelog 末尾多余空行 | ✅已修 | 规整为单个结尾换行 | `git diff --stat` 4 行插入，无尾随空行 |

判决：finding 全部处置；越界范围已披露（`tests/inst` 9 个载体 + `case-ledger.tsv` + qemu changelog —— 均为「语义订正后门控回绿」的必需项）。状态置 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 独立执行，workdir = 本任务 worktree，HEAD = `3baa35bf`）**
- `make check-patch-tree` → **rc=0**：`qemu: 69 patch(es)`、`11 patch set(s), 442 patches OK`（qemu 段 0 问题）；`make check-index-blobs` → **rc=0**（`342 new-file patch(es) OK`）；`make check-case-ledger` → **rc=0**（`现场身份 5672 条（asm 5151 / lit 521）`）
- `make check-inst-asm` → **rc=0**（两次，注入前/还原后同）：`run_asm_suite: 272/272 镜像通过（272 个 id；链例 + 故障链 632 例）` / `check-inst-asm: PASS`
- 运行期证据目录内 `run.sh` → **rc=0，`PASS=7 FAIL=0`**：探针 15 检查点 / 120 B / rc 0、`oracle: ALL PASS`、补丁↔源码一致（`base=c3d48b7d1e89`）、`git apply --check` rc 0、12-misc 回归 28/28
- 探针逐点抽核（reviewer 对 IDL 手算）：`.t`→`DEADBEEF01234567`、`.w`→`DEADBEEFCAFE0123`、`.b`→`DEADBEEFCAFEF001`、`.o`→`0123456789ABCDEF`（整 64 位）、`0x80000000` 窗→`DEADBEEF80000000`（**非 sext**）；与 `idl/SimRISC-12.idl` 9 条 body（`rd[rdHC][31:0]/[15:0]/[7:0] = value[...]`）逐条一致，`.o` 为 `rd[rdHC] = value`
- **独立注入（reviewer 自做，`cp` 备份 + md5，未用 git checkout）**：组件源码 `gen_lr()` 改回整 64 位写 ⇒ `make build-qemu` rc=0（qemu md5 `7d17bd18…`→`80d952b1…`）⇒ 重跑同一 `run.sh` → **rc=1，`FAIL=4`**：探针 `rc {'qemu': 1}` / 0 B、`补丁↔源码一致` 实际=不同、`check-patch-tree` rc=2、12-misc 回归 **9 个 `lr.{t,w,b}` 全红**（首红点 = 点 5，与链上哨兵落位一致）；`cp` 还原 + md5 相等（`34a34f62…`）+ 源码 `git status` 空 ⇒ 重建 rc=0、qemu md5 回 `7d17bd18…` ⇒ 重跑 `run.sh` rc=0 `PASS=7 FAIL=0`、`check-inst-asm` 272/272

**语义与文件核验**
- `translate.c.patch`：`store_rd_narrow()` = `(old & ~mask) | (val & mask)`、`mask = 2^(8W)−1`、`n==0` 早退与 `store_rd` 同口径；`gen_lr()` 中 `width == 8` 走 `store_rd`（**`.o` 未被误改**，探针点 10/11 实测整 64 位），窄宽度走切片写；`gen_lr` 全部调用点宽 ∈ {1,2,4,8}（`trans_mem.c.inc`）
- 9 个载体期望按链上前值重算：点 1–4 高位仍 0 故不变，点 5 起哨兵高位保持 → `case-ledger.tsv` 108 行增删**全在 `lr.{t,w,b}`**（非 lr 行 0），`lr.o` 载体未动；`git show --stat` 13 文件与完成区「修改文件」一致，未动 spec/契约/判据

**任务书前提偏差（reviewer 判：属实，属任务书勘误，非返工项）**
1. 任务书写 `insn_trans/trans_atomic.c.inc.patch` —— 补丁集与 QEMU 源码**均无** `trans_atomic.c.inc`；`gen_lr` 定义在 `translate.c`、由 `trans_mem.c.inc` 调用 ⇒ 实际落点 `translate.c.patch` 属实
2. 任务书验收 3 的 `check-qemu-semantics` —— `make check-qemu-semantics` 报 `No rule to make target`；Makefile 注释载明旧名已于 `TESTCASES-076t` 删除、现行名 = `check-inst-asm` 等 ⇒ 属实，等价门控 `check-inst-asm` 已 rc=0
3. （reviewer 新发现）任务书两处写 oracle = `idl/SimRISC-01.idl`，该文件 0 条 `lr`；9 条窄 `lr` body 在 `idl/SimRISC-12.idl` ⇒ 任务书指针有误，engineer 实际按 SimRISC-12 实现与取证（正确）
4. gem5/chipyard 侧仍零扩展、三平台 `.S` 在那边红 —— 同批 `m15-gem5-002`/`m16-chipyard-014` 落地前属预期，**不作阻断**

**判决：Accepted** —— 验收 1/2/4/5 在我的重跑下全过（验收 3 按偏差 2 的等价门控核）；独立注入可达 FAIL、还原回绿、md5 对账相等；无凑绿、无越界、无弱化断言。上述 4 条任务书偏差由 architect 收尾时勘误。
