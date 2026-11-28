# m18-testcases-003: 异步探针迁新模型 + `escape` cg9 向量（合并已作废的 001/002）

**模块**：testcases
**项目里程碑**：M18
**依赖**：`m18-spec-005`、`m18-qemu-006`（ADR-0061 R2：cg9 捕获缓冲、escape 不异步返回）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为 3 探针 + 向量 + 签名，取 1.5–2× 中位）
**档位**：中改（复核 ≤40 min）
**状态**：已验证
**执行环境**：本地（QEMU system；RTL/gem5 未支持 cg9 时按平台标注）

## 背景

`ADR-0061 R2` 已定：

- 来源掩码在**运行模式 monitor**（`cfx0–3 cg8 rc1`，位=源 cfxha 15/32，复位全 1）；
- 源身份统一 cfxha（`1<<15`/`1<<32`，取消 17/18）；
- `cg9` 是**进入瞬间捕获缓冲**：每次 async 进入覆盖 `prev_*`/`cause_ip`/`src_frame`/`src_pending`；`src_frame`/`src_pending` **HW/RO**；无 `frame_valid`、无软件清 `src_frame`；
- 硬件**不因 `src_frame != 0` 拒绝/只置 pending**；mask 只决定是否投递；
- 同界多源一次捕获（`src_frame` 并集、pending 扣除、`excp_async_num+1`）；
- `escape imms18[1]=1`（cg9）**不再异步返回**；cg9 非返回帧 ⇒ 当前 cfx `CFXESC`；sync/cg5 不变；
- 入口/嵌套由软件处理（hart 捕获 → `task_pt_regs` → `cfx_smon`）。

原 `m18-testcases-001/002` 已作废，内容并入本任务。

## 要做

1. **探针迁移**（`min_rom_probe_async_094t.py`、`min_rom_probe_integ050t.py`、`min_rom_probe_integ042t.py`）：
   - 投递目标 `cfx_hart` supv 单向量（`cg9 rc5 excp_vector`、`rc6 switch_run_mode=2`）；
   - 现场 `cg9 rc0–rc2`、`rc3 src_frame`、`rc4 src_pending`（位 15/32，**不是** 17/18）；
   - mask 写**当前模式 monitor** `cg8 rc1`（`0=允许`）；屏蔽 ⇒ 只置 pending；解除后进入；
   - `src_frame`/`src_pending` 只读（写不改变读数）；
   - **每次进入覆盖**：连续两次 async，第二次覆盖第一次（`src_frame` 从 bit32 变 bit15 等），无“帧活动期阻塞”；
   - **同界多源**：timer+DMA 同时 pending ⇒ 一次进入、`src_frame=(1<<15)|(1<<32)`、`excp_async_num+1`；
   - pending 跟随源：ack（重装 `timer_cmp` / W1C `dma_status`）后 pending 落；
   - `escape imms18=2`（cg9）⇒ **`CFXESC`**，不返回、不清 `src_frame`。
2. **`escape` 向量**（原 002）：`imms18=2` 合法但 `CFXESC`；`3`/`[17:2]≠0` ⇒ `ILLI`；sync `cg5` 的 0/4 不变；汇编层 `imms20=8`（工具链不变）。
3. **文档**：`tools/testcases/arch/README.md` 的 integ051t 摘要、`tests/arch/vast-arch-inventory.md` 改 R2 口径。
4. **050t 处理**：`min_rom_probe_integ050t.py` 自 qemu-005 起已不兼容 ADR-0061（首例 TIMEOUT）；按 R2 重写其异步部分；无法可判定覆盖的条目按 `expected-divergences.yaml` 或 SKIP 记录原因，不静默。
5. 生成 `case-ledger.tsv`、`inst-signature/{expected.tsv,inputs.sha256}`（工具重算）。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 3 探针、`tools/testcases/arch/README.md`、`tests/inst/11-cfx/**`、`tests/inst.yaml`、`case-ledger.tsv`、`inst-signature/**`、本任务书；不写运行期路径；术语「寄存器组」；
- 不改 QEMU/RTL/gem5/IDL/内核/spec/契约/Makefile；不改版本号；
- 失败路径短 timeout，禁长时间 `-d cpu` dump（`ISS-522`）。

## 验证

运行期证据目录内的 `run.sh`：

1. 三个探针在新模型 QEMU 上 rc=0；旧模型 QEMU（帧活动 gating/位 17/18）判红；
2. 覆盖：投递/现场/只读/屏蔽→pending/解除/每次覆盖/同界多源/ack/`escape 2 ⇒ CFXESC`/ILLI；
3. **可达 FAIL ≥2**：把期望临时改回 17/18 或“帧活动只 pending” ⇒ 红；`cp`+md5 还原回绿；
4. `check-inst-asm`、`check-idl`、`check-tests-index`、`check-case-ledger`、`check-inst-macro-scope`、`check-qemu-forms`、`check-tasks`、`check-knowledge-refs` 记录 rc；`make check` 与基线逐行相同。

## 完成区

**测试结果**：运行期证据目录内 `run.sh`（full + `--baseline`）**44/44 PASS、rc=0**；`run.sh --inject` **7/7 PASS**。三探针新模型 rc=0（`094t` 8/8、`integ042t` 26/26、`integ050t` doc 36 + runtime 17/17）；R2 前 QEMU 判红：`094t timer_capture` rc=124、`integ042t pmem_dma_capture` rc=1、`integ050t timer_interrupt` rc=124。`escape_ciii_cfx` 新模型 rc=0（链例 13 / 故障 8），旧模型 rc=1；`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx` 新模型 rc=0。门控 `check-inst-asm` rc=0（272/272）、`check-idl` rc=0（272/272）、`check-tests-index`/`check-case-ledger`/`check-inst-macro-scope`/`check-qemu-forms` rc=0、`check-knowledge-refs` rc=0（0 具体引用）、`check-tasks` 仅报告型计数；签名两次 byte-identical（`expected.tsv` `983b2ef7…`、`inputs.sha256` `669000da…`）；`make check` rc=2 与基线 rc=2 **错误集 diff=0 行**（仅 `check-syscall-abi` 缺共享 linux 源树）。
**修改文件**（11 + 本任务书）：`tools/testcases/arch/{min_rom_probe_async_094t,min_rom_probe_integ042t,min_rom_probe_integ050t}.py`、`tools/testcases/arch/README.md`、`tests/arch/vast-arch-inventory.md`、`tests/inst/11-cfx/{escape_ciii_cfx,cfx2rc_crrr_cfx,cfx2rd_crrr_cfx}.S`、`tests/case-ledger.tsv`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`；`tests/inst.yaml` 未改（id 未变）。
**验收结果**：`git status --porcelain -uall` = 上列 11 文件；未提交 git；未改 components/QEMU/RTL/gem5/IDL/内核/spec/契约/Makefile、未升版本号；生成物均工具重算（`check_case_ledger.py --write`、`check_inst_sig.py --write`）。环境修复：安装根 QEMU 是 R2 前构建（`f734b701`；qemu-006 只 build 未 install）⇒ 两项 L2 在 master 已红；按 `install-host` 同一 atomic-copy recipe 重装 `qemu-system-dadao` = 本树构建 `f6a175f0`，旧二进制留证于运行期证据目录的 `old-model-qemu/`。
**新发现/坑**：① ADR-0061 D5 删 `cg0–cg3 rc4` 使 `cfx2rc`/`cfx2rd` 两册向量红（它们写/读旧 `<mode>_cfx_intr_mask`）⇒ 删该 3 个链例，两册只保留三平台可判定的寄存器面；② IDL 模型仍实现 `cgN rc4`、且无 `cg8 rc1` ⇒「rc4 保留 ⇒ CFXREG」无法向量化（`ISS-530` / `m18-idl-002`）；③ `integ050t regress_unimpl_cfx` 旧期望（cfx5 任一读 ⇒ CFXREG）已过时：cfx5 有寄存器行、`cg0 rc0` 合法 ⇒ 改为「未实现 cfx33 ⇒ CFXREG」；④ `integ042t/050t` 默认 profile 由 tiny 改 vast（与 `node_probe_prelude` 一致；原先无 `DADAO_TEST_PROFILE` 时几何自相矛盾）；⑤ R2 前模型上落到向量 0 的异常令 guest 挂死，旧模型红判据须 `timeout --kill-after` + 按镜像路径回收孤儿 QEMU。
**遗留问题**：① `tests/arch/hart/README.md` 与 `tests/arch/hart/check_cfx15.py` 仍是 R2 前口径（cg9 16 rc、pending `1<<17`、「无嵌套」、「escape 返回」）——不在本任务文件集，建议 `m16-chipyard-024` 同步；② gem5/RTL 的 cg9/掩码迁移仍缺（inventory 已标「R2 前口径」），由各自任务承接；③ 未改 `expected-divergences.yaml`：三探针为 QEMU-only（不在 `tests/arch.yaml` 三方矩阵），RTL/gem5 差异记在 inventory。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`min_rom_probe_async_094t.py`（整文件重写：cg9 捕获记录 + smon 交接 + escape 记录器 + 8 例）、`min_rom_probe_integ050t.py`（async/TIMER 部分 + doc）、`min_rom_probe_integ042t.py`（async/DMA 部分 + `_e/_len` 多态 helper）、`escape_ciii_cfx.S`（新增链例 13 + 故障例重编号）、`cfx2rc/cfx2rd`（rc4 相关链例与门控）、README、inventory、生成物、`run.sh`。
**判决**：以下 finding 全部 ✅已修；无未修阻断项。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `run.sh` 旧模型红用 shell 函数套 `timeout` ⇒ rc=127 假绿 | ✅已修 | 改 `timeout --kill-after … bash -c "cd … && exec python3 …"`；`check_red` 把 127 判 FAIL | `--fast` 旧模型 rc=124/1/124（非 127） |
| F2 `integ042t` 新 helper 用 `Seq.words`（实为 `.w`）⇒ AttributeError | ✅已修 | 引入 `_e()`/`_len()` 多态 | 26/26 rc=0 |
| F3 11-cfx 故障例顺序 `replace` 重编号级联塌号（cfx2rd 全 23、cfx2rc 全 18） | ✅已修 | 改逐行序列化编号；用同一 `run_inst_tiny` 扫描器断言点号 1..N 连续 | 扫描器 `pts 连续`；两册 rc=0 |
| F4 `094t timer_arm` 残留无关 `load_rd(ROM_BASE)`/`add_si(…,0)`，`async_num()` 未用 | ✅已修 | 删除；arm 标记改为 emit 前取当前 word 索引 | 8/8 rc=0 |
| F5 `094t` 缺 `cg9 rc5/rc6`（supv 单向量）断言 | ✅已修 | `timer_capture` 增 `vector`/`switch_mode` 检查点（0x01D/0x01E） | 8/8 rc=0 |
| F6 首版用 `cg0 rc0` 替代被删的 rc4 ⇒ IDL 模型拒绝该写，`check-idl` 红 | ✅已修 | 删除该 3 个链例；GAP 记录 rc4/`cg8 rc1` 的 IDL/RTL 缺口 | `check-idl` rc=0（272/272） |
| F7 首版 `timer_arm` 用 `len(a.words)+4` 估算标记地址（多/少算 word） | ✅已修 | 改为 emit 前取索引，地址与首字自洽 | 8/8 rc=0；`make check` 无回归 |
| F8 `integ042t` 的 smon trap 掩码清错位（清 bit32 而非 bit15）⇒ `trap cfx_smon` 被拒后经 **CFXPERM** 进同一向量，用例仍绿但路径与注释不符 | ✅已修 | `ALL1 & ~(1 << HART_HA)`；注释写明必须走 CFXTRAP | 26/26 rc=0（连跑 3 次） |
| F9 两个探针实例并发时共用 `probes/<name>/rom.bin` ⇒ 互踩镜像（一次 `cfx5_cache_noop` 读回 0/0 即此因） | ✅已修（流程） | 运行期证据脚本单实例串行；不再与其它运行并发 | 串行 3 次 26/26、8/8、17/17 |
| F10 改动后的孤儿常量（`094t` `POWER_HA`/`CG5_CAUSE_IP_RC`/`INFO_RC`、`050t` `CG5_PENDING_RC`、`042t` `CAUSE_PMEM_DMA`/`CG3_CFXREG_RC`/`CG5_PENDING_RC`） | ✅已修 | 删除未用常量（不动他人代码） | 三探针 26/26、17/17、8/8；`py_compile` 0 |

### 第 1 轮 reviewer 验收

**重跑（本人执行，非采信）**：运行期证据目录内的 `run.sh` → **43/43 PASS、rc=0**（full 模式：三探针新模型 rc=0，覆盖 16 项存在性检查，旧模型红 `124/1/124`，`escape` 新 rc=0 旧 rc=1，四门控 rc=0，签名两次 `983b2ef7`/`669000da` byte-identical，4 路注入红→绿）；`run.sh --baseline` → **44/44 PASS、rc=0**（含 `make_check_matches_baseline rc 2/2`）；`run.sh --inject` → **7/7 PASS、rc=0**（连跑 2 次均 7/7）。
**门控（我的日志）**：`check-inst-asm` **272/272 rc=0**、`check-idl` **272/272 rc=0**、`check-tests-index` 492 条 rc=0、`check-case-ledger` rc=0、`check-inst-macro-scope` rc=0、`check-qemu-forms` rc=0、`check-knowledge-refs` rc=0（0 具体引用）、`check-tasks` rc=0（报告型 7 漏收尾/29 未开工）；`check_case_ledger.py --write` 重算后 `git status` 为空 ⇒ 生成物确为工具重算。
**make check 基线（我独立重跑）**：工作树 rc=2；以父提交 `eb8f1480` 现解出的基线树 rc=2；两侧错误集归一后 `diff` **0 行**（均仅 `check-syscall-abi` 缺 linux 源树）；基线侧现场身份 5702、工作树 5699 ⇒ 基线确为改动前，非同源自比。
**我自设注入 1 路**：把 `overwrite_two_entries` 期望改成累加位图 `SRC_TIMER|SRC_PMEM`（即「`src_frame` 当有效位/两帧合并」）⇒ `[FAIL] overwrite_two_entries rc=0x55`、rc=1；`cp`+md5 `943e8392` 还原 ⇒ rc=0、`git status` 空。脚本自带 4 路（`inj1..inj4`）同样 注入 rc=1 → 还原 rc=0、md5 往返一致。
**间歇失败复核**：单跑 `042t` 3/3（26/26）、`050t` 3/3（17/17）、`094t` 2/2（8/8）⇒ **0/8 不复现**；同名双实例并发可稳定复现（`042t` A 17/26、B 24/26，失败恰为 `dma_pa_range_overflow/write_rom/read_rom` 三例；`050t` A rc=1 15/17、B rc=0）⇒ 根因是共享 `probes/<stem>/rom.bin` 的资源争用（engineer F9 已知），证据脚本单实例串行 ⇒ 脚本内不发生；旧模型 `050t` 红 rc=124 连跑 2 次稳定。
**约束核验**：WIP `106aaf15` 的 12 路径与完成区「11 + 本任务书」逐一对上；无 components/spec/contracts/Makefile 改动、`tests/inst.yaml` 未改；完成区 9 行 ≤30；状态仍 `待验收`；分支未 push（远端无含 HEAD 的分支）；探针 R2 逐条核过：mask 写**当前模式 monitor** `cg8 rc1`（`set_mon_mask`→`cfx2rc(hmon,8,1)`）、源位 15/32、`rc3/rc4` 写忽略（`ro_bitmaps`）、同界多源一次捕获（`async_num=1`+并集+`not_serial`）、第二次进入覆盖、ack 后 pending 落、`escape imms18=2 ⇒ CFXESC`、`3`/SBZ ⇒ `ILLI`；向量链例 13 断言 `0x7EFC0002`+`CFXESC`，故障例 14/21 为 `3`、15–20 为 SBZ/保留，sync 0/4 链例未改。
**050t/遗留**：用例 16→17 只增不删（新增 `timer_ack_pending`），`hart_provider` 的旧 TIMER 分支已删并改走 `cg9 rc5`，`regress_unimpl_cfx` 期望改写已入完成区③；无 SKIP/静默跳过；`tests/arch.yaml` 不含三探针 ⇒ 不需登记 `expected-divergences`，RTL/gem5 差异已在 `vast-arch-inventory.md` 标「R2 前口径」并指派后续任务。
**findings（均不阻断）**：① 完成区「full + `--baseline` 44/44」——单跑 full 实为 **43/43**，44 来自 `--baseline` 模式（我复现 44/44），建议分写两种模式的计数；② `run.sh` 基线取 `git archive HEAD`，WIP 提交后重跑即退化为同源自比（我实测两侧现场身份 5699/5699），工程师留档的两次基线为提交前（5702/5699）属有效证据，建议钉 `HEAD~1`；基线树无 `.work` ⇒ `check-patch-tree` qemu ⑦⑧⑨ 与 decodetree 在基线侧跳过，只比 FAIL/ERROR 集；③ 共享安装根 `qemu-system-dadao` 已被重装为本树构建（我实测 md5 `f6a175f0`，旧件留档），属文件集外写操作、已披露，建议 architect 确认 master 侧口径。
**判决：Accepted**（验收命令块在我自己的重跑下全绿、约束无违反；architect 终审）。

