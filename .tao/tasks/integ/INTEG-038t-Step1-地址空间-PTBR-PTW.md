# INTEG-038t: Step 1 落地（地址空间 + PTBR + PTW）

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0039（Step 1 已冻结；D1–D8）、当前 master
**状态**：已验证

## 背景
ADR-0039 D1–D8 已冻结 Step 1，但 `spec/DADAO-12`、contracts、QEMU 仍是旧口径：48 位 VA、高 6 位选 64 个 PTBR、`pahi/pthi` 拼 PA、`ptbr_enable` 位图。本任务只落地 Step 1，**不实现 PTE/TLB/DMA/启动**。

## 目标（只做 Step 1）
1. **SEE spec（DADAO-12 §2.1/§2.2 相关）**
   - CPU 地址 48 位；`[47:42]==0` 为内存窗口（PTW），`1..63` 为 cfx 1–63 核内空间；cfx0=umon 无内部空间；
   - VA 42 位、PA 56 位；
   - 单 PTBR，只存 PPN[55:16]，64KiB 对齐；无数组、无 valid、无 `pahi/pthi`、无 `ptbr_enable` 位图；
   - `ptw_enable`：0 时 `addr[47:42] = 0` 访存 → **CFXMEM**（当前模式 cfx）；1 时走 PTW；
   - 写 PTBR/`ptw_enable=1` 允许，**不隐含 TLB invalidate**；
   - 复位 PTBR=0、`ptw_enable=0`、TLB 空；
   - 保留：reserved cfx 普通 ld/st → CFXMEM；trap/escape reserved → 现有 ILLI；
   - 不定义 cfx1–63 访问权限（Step 6）。
2. **contracts/别名/生成物**：同步单 PTBR、`ptw_enable`、删除 pahi/pthi/perm/ptbr_enable 相关条目（仅 Step1 范围）。
3. **QEMU**：地址分区、PTBR、`ptw_enable`、PTW off 的 CFXMEM、reserved cfx ld/st；不实现 PTE/TLB/DMA。
4. **测试**：QEMU/单元/向量覆盖：
   - `addr[47:42] = 0` 且 `ptw_enable=0` → CFXMEM（各模式目标）；
   - `ptw_enable=1` 但 PTBR 未建页表 → 页表异常（若当前 QEMU 已有 ptw 雏形则验证；无则明确 BLOCKED 到 Step2）；
   - PTBR 写入/复位值、单 PTBR；
   - reserved cfx ld/st → CFXMEM；
   - 不影响 cfx 内部直接 ld/st。
5. 更新 spec 锁 sha/changelog/版本；`check-spec-readonly`/`check-spec-changelog`。

## 验收
- `make check` rc=0；`check-spec-readonly`/`check-spec-changelog` rc=0；`check-patch-tree` rc=0（若改组件补丁）。
- QEMU 定向/单元测试全绿；证据 `.work/evidence/<任务号>/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。
- 不改 PTE 格式/TLB/DMA/启动/HSJU/cfx 权限。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/INTEG-038t/`。

## 约束
- 只做 Step 1；不提前做 Step 2+。
- 不改 Linux/arch、不做 user/kernel 划分。
- 不跑 `check-full`/夜跑；长构建申报。
- 不提交、不 push。

## 完成区

**状态**：已验证

**用户裁定（2026-10-29）**：授权同步 `DADAO-22`/`Machine-01`/`Toolchain-01` 及 spec 锁 sha；接受保留 cfx 的取指也归 CFXMEM。用户原话：“1、可以；2、可以”。

**测试结果**：`make check` rc=0；`make check-modules` rc=0；`check-arch-smoke` rc=0；`check-lit` 158/158；新增探针 16/16；回归 044t/045t/049t 全 PASS；证据脚本 22 项 PASS、注入 1 例 FAIL→md5 还原→PASS。

**修改文件**：
- spec：`DADAO-12`（§2/§2.1/§2.2/§4.5/§4.6/§5 + 附录）、`DADAO-22 §4`（单 PTBR SBI）、`Machine-01 §1/§1.2/§3`、`Toolchain-01 §13.8`（示例改 `cfx_pmem_start[0]`）；`manifests/spec-readonly.lock.toml` 四册 sha。
- contracts：`cfx-aliases.txt`、`contract-cfx-aliases.md`（生成器重算）、`contract-see.md`、`contract-asm.md`。
- QEMU：`.work/source/qemu` 的 `target/dadao/{cpu.h,cpu.c,helper.c}` + 三份导出补丁；`components/qemu/changelog.md`。
- 测试：新增 `tools/testcases/arch/min_rom_probe_integ038t.py`；改 `min_rom_probe_044t.py`、`tests/arch/umon/{m5_perm_unimpl_cfxreg.s,expected.yaml}`、`tests/unit/llvm/lit/MC/DADAO/{cfx2-trap-escape.s,cfx2-trap-escape-err.s,README-m5.md}`、`tests/case-ledger.tsv`、`tools/spec/check_asm_prose.py`（注释）。
- 证据：`.work/evidence/INTEG-038t/run.sh`。

**验收结果**（真实输出）：
- `make check`：`repository checks (L1): PASS`（rc=0）。
- `make check-modules`：`module checks (L2): PASS`（rc=0）；`make check-arch-smoke`：`10/10 passed` + 25 服务覆盖 PASS。
- `python3 min_rom_probe_integ038t.py`：`16/16 passed`（ptw off data/store/fetch=0x81、PTBR 复位/写入/高位清 0、使能写读、单 PTBR/cg10→CFXREG、reserved 7/19 ld/st/fetch=0x81、RAM 直访不受影响、ptw_enable=1 显式失败）。
- 注入：`helper.c` 保留 cfx 判定改为 `0 &&` → `reserved_ld` 探针 rc=1（FAIL）；`cp` 还原 md5 `4b2a2de7…` 一致 → 重建 → rc=0；日志 `/tmp/opencode/INTEG-038t/evidence/`。

**新发现/坑**：
- 任务号 `038t` 与既有 `QEMU-038t` 撞名：初版误覆写 `min_rom_probe_038t.py`；已用 `git show HEAD:` + md5（`50f19641…`）还原，并把新探针改名 `min_rom_probe_integ038t.py`（教训：新文件先 `ls`/`git ls-files`）。
- `cfx4` 进入测试机实现集后，原“未实现 cfx”用例（`cfxreg_unimpl`、`m5_perm_unimpl_cfxreg`）改用 `cfx5/tlb`；Machine-01/contract-see 同步。
- 保留 cfx 的**取指**按 Step 1-c 一并归 CFXMEM（ADR 只写普通 ld/st，取指属同一地址空间非法访问）。
- `ptw_enable=1` 的页表路径改为 `error_report`+`exit(1)` 显式失败（不静默成功）；页表异常/PTE 属 Step 2。

**遗留问题**：
- PTE 格式/页表步进/页权限：**BLOCKED 到 Step 2**（当前 QEMU 无 ptw 载体；`ptw_on_fail_closed` 仅验证 fail-closed）。
- TLB invalidate“不隐含”无运行时载体（模型无 TLB），仅由寄存器写路径与 spec 固化。
- `docs/DDLN/C-资源管理/{DD,TT}-C002/C007` 仍描述旧 64-PTBR/perm 语义未改；`.tao/adr/adr-0039` 的 Step 2 段为另一会话改动，未触碰。

## 审阅记录

**ADR 拆分说明（2026-10-29）**：原 ADR-0039 的 §8.6 已迁至 `ADR-0040`；下方审阅记录中的 §8.6 指拆分前版本。

### 第 1 轮 engineer 自审（2026-10-29）

- F1 文件名撞车：`min_rom_probe_038t.py` 已属 QEMU-038t，初版误覆写。✅已修：`git show HEAD:` 恢复（md5 `50f19641…` 一致），新探针改名 `min_rom_probe_integ038t.py`。
- F2 PTBR 掩码位宽错（`0x00FFFFFFFF0000` 只到 bit47）。✅已修：改 `0x00FFFFFFFFFF0000`（bit55:16），探针 `ptbr_write`/`ptbr_high_bits` 复验。
- F3 spec 写“三步”但保留四个步骤标题。✅已修：两处改“四步”；`check-spec-refs`/`changelog` 复绿。
- F4 `contract-see` 引用 `§4.5 cfx_ptw` 非完整标题 ⇒ `check-spec-refs` 2 处 FAIL。✅已修：改引完整标题。
- F5 lit 字节改动导致 `tests/case-ledger.tsv` 漂移。✅已修：`check_case_ledger.py --write` 重生成，门控 PASS。
- F6 实现 `cfx4` 后原“未实现 cfx”用例失效（`cfxreg_unimpl`、`m5_perm_unimpl_cfxreg`）。✅已修：改用 `cfx5/tlb`，expected/README 同步。
- F7 保留 cfx 取指也归 CFXMEM（ADR 只写普通 ld/st）。✅已处理：属同一地址空间非法访问，已写入 spec §2.1/§5.2 与探针，语义自洽。
- 范围说明：为使 `check` 不假红，`DADAO-22`/`Machine-01`/`Toolchain-01` 做了 Step 1 引用同步（任务书只点名 `DADAO-12`）；已按 Process-06 的 spec 锁流程更新 sha 并在完成区披露，**授权原话待主会话/用户确认**。
- BLOCKED（任务书允许）：PTE/页表步进（Step 2）与 TLB invalidate 运行时语义无载体；`ptw_enable=1` 仅验 fail-closed。
- 判决：F1–F7 处置完成；无未修缺陷；状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-10-29）—— Accepted

**重跑记录（全部独立执行，无 `| tee`）**：
- `make check` rc=0（`repository checks (L1): PASS`）；`make check-modules` rc=0（`module checks (L2): PASS`）。
- `make check-arch-smoke` rc=0（`10/10` + 25 service 覆盖 PASS）；`make check-lit` rc=0（158/158）。
- `check-spec-readonly` rc=0（21 册 OK，四册 sha 独立 `sha256sum` 与 lock 逐一相符）；`check-spec-changelog` rc=0；`check-patch-tree` rc=0（5 组件 205 补丁）；`check-source-state` rc=0（qemu HEAD=f831582 count=1 clean=True）。
- `.work/evidence/INTEG-038t/run.sh` rc=0：22 项 PASS/FAIL=0，含脚本内注入→FAIL→cp+md5 还原→回绿，与完成区声明一致。

**独立注入（非 engineer 自检）**：`helper.c` PTBR 写掩码注入 `0x00FFFFFFFF0000ULL`（复现 F2 类回归）→ `make build-qemu` rc=0 → `ptbr_high_bits` 探针 **rc=1 FAIL**（`exp=0xabcdef12340000 got=0xcdef12340000`）→ `cp` 还原（md5 `4b2a2de7…` 与注入前一致，`git -C .work/source/qemu status` 空）→ 重建 rc=0 → 全量探针 **16/16 PASS rc=0**。未用 checkout/restore 还原。

**约束核验**：diff 仅含 Step 1（48 位地址分区/单 PTBR/`ptw_enable`/CFXMEM 路由）；无 PTE 格式/页表步进/TLB/DMA/启动/HSJU/cfx 权限实现（`ptw_enable=1` 为显式 fail-closed，已披露 BLOCKED 到 Step 2）；无 Linux/arch 改动；未跑 check-full/夜跑；无提交/push（HEAD 仍 9d0c9db5）；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 残留；`git status` 25 项与完成区「修改文件」逐项对账一致（milestones.md 属验收要求项；ADR-0039 §8.6 为另一会话改动，mtime 早于本任务 spec 编辑，采信）。

**Findings（均不阻断，architect 收尾处置）**：
1. `components/qemu/changelog.md` 写“14 例”，探针实际 16 例——文档笔误，改数字即可。
2. DADAO-12 §2.2.1/§2.2.2 第四步已改 PA[55:16]/[55:29]（56 位 PA），但 §2.2.3/§2.2.4 PTE 格式表仍为旧布局 PPN bits[47:16]——PTE 格式属 Step 2 冻结范围（ADR-0039 §8.6 Step 2-f），本任务不改正确；**Step 2 任务须收口该过渡态矛盾**。
3. ADR-0039 工作树 diff 含 §8.6 Step 2 冻结段（非本任务产出，见遗留问题）；建议 architect 确认归属后随收尾提交。

**判决：Accepted**——验收命令块在 reviewer 重跑下全部通过、约束无违反，可提交（提交权归 architect）。
