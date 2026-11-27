# m16-gem5-022: I 侧自修改实证 + monitor 脏行修复

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-021`（cfx5 命令）合入
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景（用户 2026-11-22 裁定）

`m16-gem5-021` 报“I 侧 invalidate 后取指仍执行旧字”，但检查发现：

- gem5 `DadaoL1DCache` 是**写回**；现有 `cfx5_selfmod.s` 是 base probe（无 cfx5、无 `D|clean`），不能证明 cfx5 I 侧不可用；
- RTL `WumingCache` 是 **VIPT**，但索引在 64 KiB 页内（`PA[15:0]==VA[15:0]`，无别名）⇒ 用 PA 索引/标签正确，021 的 `Request::PHYSICAL` 不是错。

用户选 B（修 gem5 自修改支持），但采纳“先证伪”的拆法：本任务先补**正确构造**的 I 侧用例；只有它仍失败，才立 `m16-gem5-023` 改取指侧模型。同时修 021 发现的 020 接线隐患。

## 要做

1. **正确 I 侧自修改用例**（落 `tests/arch/cache/` 或运行期证据）：
   - 写新指令到代码行；
   - `cfx5 cache_ctrl = D | clean | 单行`（必要时区间）把脏行写回内存；
   - `cfx5 cache_ctrl = I | invalidate | 同一 PA`（单行/区间）；
   - 跳转到该地址取指，断言执行**新指令**。
   - 单行与区间各至少 1 例；同一 ELF 在 `cache-model=on` 下跑。
2. **判定**：
   - 若用例 PASS ⇒ 记录“021 不缺命令层，只是缺正确用例”，不立 023；
   - 若用例 FAIL（已 clean D）⇒ 保留现场、写清证据，交给 `m16-gem5-023`（改 `src/cpu/simple/**` 或取指缓冲），本任务不改模型。
3. **修 020 的 monitor 脏行隐患**：`cache-model=on` 的 Vast BootROM 交接阶段写入的页表/monitor 数据留在 L1 脏行；`D|invalidate|all`（或覆盖这些脏行的单行/区间）会丢弃它们，下一次异常进入 monitor 失败直至 `UNDI` 死循环。**reviewer 订正**：现象已复现（去掉绕行后 `simulate() limit reached`），但“monitor 段经 D-Cache 拷入且不写回、内存旧内容”的机制未复现（drop 体 invalidate 后仍存活）；先定位具体致命脏行，再修。修法二选一：
   - monitor/BootROM 段写入走直连/写穿（不进 D-Cache）；
   - 或启动移交后对 monitor 行 `D|clean`（写回），并在文档写明。
   验收：`D|invalidate|all` 后触发一次异常，monitor 仍能处理（不死循环）。
4. **不回归**：021 的 D 侧语义（clean/invalidate/flush、范围/使能/异常）、`off` 下 01 册 38/38 与 `run_m5_e2e --profile vast` 10/10。

## 不做

- 不改 `src/cpu/simple/**`（留给 023，仅当本任务证伪失败）；
- 不改 cfx5 寄存器/命令语义（021）；
- 不改 QEMU/chipyard。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py gem5` 幂等；
- 不写运行期路径；术语「寄存器组」；
- 证据脚本记录重建耗时与环境。

## 验证

运行期证据目录内的 `run.sh`：

1. 新 I 侧用例（单行、区间）在 `on` 下 PASS；若 FAIL，给出“已 clean D 仍旧字”的完整现场并标记 023；
2. `D|invalidate|all` 后异常进入 monitor 不死循环（修复前复现、修复后通过）；
3. `off` 下 01 册 38/38、vast 10/10；021 的 D 侧用例不回归；
4. **可达 FAIL**：注入「不 clean D」⇒ 新用例应按预期失败（证明用例确实依赖 clean）；注入「monitor 交接脏行不写回」⇒ invalidate 后死循环复现；`cp`+md5 还原并重建回绿；
5. `check-gem5-decode`、`check-patch-tree` gem5 段、`check-index-blobs`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh --inject all` → **24/24 PASS（rc=0）**。I 侧自修改：`on` 下单行与 PA 区间各 1 例均执行**新**立即数（guest rc 0x10）；同一 body 去掉 `D|clean` 即执行**旧**立即数（0x92）⇒ **021 只缺正确用例，不立 023**。monitor：`D|invalidate|all` 与 `I+D|invalidate|all` 后各触发一次 `CFXREG` 异常，monitor 均处理并回到测试体（0x10）；pre-fix 注入同一用例为 `simulate() limit reached`（rc=125）。off 01 册 38/38、vast 10/10；021 的 D 侧 A–F 向量 0x10 不回归。
**修改文件**：组件源 1 个：`src/arch/dadao/node_cfx.cc`（已收敛 `base+1`、补丁已导出）；`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch`；`components/gem5/changelog.md`；本任务书；运行期证据（`run.sh`、`cfx5_imod.s`/`cfx5_mon.s`/`cfx5_thrash.s`/`cfx5_dside.s`、`diagnosis-prefix.txt`，gitignored）。
**验收结果**（真实 rc）：`check-gem5-decode` 0；`check-tasks` 0；`check-index-blobs` 0；`check-patch-tree` gem5 段 0 problem（整树 rc=2、22 条断言均在既有段）；`make_patch.py gem5` `0 written, 106 unchanged`；scope（`components/gem5/patches/src/{cpu,mem}` 相对 HEAD 0 文件）0。环境 Linux 6.8.0-149 x86_64 / nproc=64；`gem5.opt` 首建 136 s、每次注入/还原重建 **116 s**；BootROM md5 `d5571847…`。两路注入：不 clean D ⇒ 0x92；交接不 flush ⇒ monitor 死循环（limit，rc=125）→ `cp`+md5 还原 `faec4969…` → 重建回绿。
**新发现/坑**：① 021 的 base probe 用 `ld.uw`/`st.w` 只改了指令字的高 16 位（opcode 半），补丁本身是空操作，其「I 侧取指不可见」结论作废。② monitor 致命脏行定位：invalidate 时 D 持有 hmon 段 `0xfff00000000..0x140` 的脏行（`diagnosis-prefix.txt` 实证）；pmem `0x83ff00000000` 的脏行是推断（diagnosis 无对应行，地址与 geometry 相符）；pre-fix 下一次 monitor 入口 decode 得 `emi=0`（UNDI→同向量死循环）。`physProxy` 功能读会看到 cache 脏数据（boot/DMA 因此看似正常），取指 refill 走内存得 0；交接时 flush D 后同一条 invalidate 不再致命。③ 汇编标签 `ran` 是保留 token，不能用。
**遗留问题**：① `components/gem5/README.md` 的 Node「已知限制」仍写「无 cache/时序」，自 020/021 起已过期（建议随下次 gem5 文档任务更新，本任务不动以免扩大改动）；② `m16-testcases-009` 可把 `cfx5_imod.s`（单行+区间）与 `cfx5_mon.s` 收编进 `tests/arch/cache/`；③ 交接 flush 是测试机模型策略（契约把 cache 组织留给实现，RTL 的 monitor 在内部 SRAM 不经 cache），QEMU/chipyard 侧不在本任务范围。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（本深度无嵌套子代理）：`nodeFlushDAtHandoff()` 的触发点/闸门、与 021 cfx5 判序的独立性、off 路径、I 侧用例的「确实改了被执行的字」与可达 FAIL、证据脚本的注入/还原与计数。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 021 的 I 侧探针把 16 位 opcode 半当补丁，结论无效 | ✅已修 | 新用例改指令的 16 位立即数（`ld.uw/st.w` 偏移 +2），并断言替换值 ≠ 原值（0x94） | 单行/区间 0x10；去 clean 0x92；`diagnosis-prefix.txt` |
| F2 交接 flush 只覆盖 D 且为整 cache（不是精确 monitor 行） | ❌不修（设计） | 交接时 D 只有 boot 写；整侧 flush 即契约的 `flush|all`，`exist` bit1=0 时 no-op | off 38/38 + vast 10/10 逐字节不变 |
| F3 flush 触发点若含 semihosting 会打断退出路径 | ✅已修 | 只匹配 power→hmon（cfxCode 63→3）与 hmon→body（3→0）；semihosting `immu18≥0x3FF00` 在上游分支已返回 | 021 A–F 与全部用例 0x10 |
| F4 证据脚本 scope 检查错把「上游→patch 系列」的既有改动当越界 | ✅已修 | 改为比较本任务 patch 集相对任务 HEAD（`patches/src/{cpu,mem}`） | `--inject all` 中 scope PASS（0 文件） |
| F5 证据脚本 `exit_cause()` 读错日志名，注入红判据误报 | ✅已修 | `$WORK/run-$tag/log` → `$WORK/run-$tag/$tag.log` | 重跑 `--inject all`：monflush 红判据 PASS |
| F6 注入期间组件源变脏会让门控变红 | ❌不修（口径） | 门控只在基线跑；注入只验行为并 `cp`+md5 还原后重建回绿 | 收尾 `make_patch.py` `0 written`、组件源干净 |

**约束核验**：改动集 = 组件源 1 + 补丁 1 + `changelog.md` + 本任务书（证据 gitignored）；`src/cpu/simple/**`、`src/mem/cache/**` 未改；`spec/`/契约未改；未提交 git；术语「寄存器组」。
**判决**：**待验收**（F1–F6 均有处置；F2/F6 为设计/口径并已披露）。

### 第 1 轮 reviewer 验收

**重跑（仓库根执行运行期证据目录内的 `run.sh`，不采信完成区）**：`run.sh` → `SUMMARY: pass=17 fail=0 inject=none`、rc=0（17:59:01→18:03:25；Linux 6.8.0-149 x86_64、nproc=64、BootROM md5 `d5571847…`）。`run.sh --inject all` → `SUMMARY: pass=24 fail=0`、rc=0，两路注入均真红：不 clean D ⇒ guest 146(0x92)；交接不 flush ⇒ 源码变更 → 重建 124 s → `GEM5_EXIT_CODE=0`、`GEM5_EXIT_CAUSE=simulate() limit reached`、rc=125 → `cp`+md5 还原 `faec4969…` → 重建 115 s → 回绿 guest 16。收尾再跑 `run.sh` → pass=17 fail=0、rc=0。
**独立注入①（reviewer 自写变异，全程 `cp`+md5，未用 git checkout/restore/stash）**：组件源 `cacheSideExec` 中让 `inst && op∈{invalidate,flush}` 直接 return（关掉全部 I 侧维护）→ 重建 116 s → `run.sh` rc=1、`pass=14 fail=3`；行为红 = `on: self-mod WITHOUT D clean` 期望 0x92 实得 **16**（另 2 条红是注入使源树与补丁不一致：patch-tree gem5 2 problems、make_patch 非 `0 written`，非交付物缺陷）→ `cp`+md5 还原 `faec4969…`/`d6a977cd…` → 重建 113 s → `run.sh` rc=0、`pass=17 fail=0`；收尾 `git status` 3 文件与验收前快照逐行一致。
**独立注入②（0x94 守卫）**：把 `cfx5_imod.s` 的 `stub_new` 立即数改成 0x1111（替换值＝原值）⇒ guest **148(0x94)**，守卫可达。
**I 侧证伪：成立**。`cfx5_imod.s` 构造逐条核过＝warm-up 执行目标行 → `ld.uw/st.w` 改 `set.zw rd20,wp0` 指令字 offset+2 的 16 位立即数并回读 → `D|clean` 0x4005/0x4009 → `I|invalidate` 0x8006/0x800A → 跳转；单行/区间 guest 均 16、去 clean 146、替换＝原值 148。021 base probe 实测：两 stub 字节 `4c50 1111` / `4c50 3333`（大端，`set.zw` 编码 `4c50_<imm>`），`ld.uw [rb9,0]`/`st.w [rb8,0]` 读写的是 opcode 半 `4c50`＝原值 ⇒ **补丁空操作**、立即数仍 0x1111 ⇒ 0x92 恒真、与 I 侧行为无关 ⇒ 021「I 侧取指不可见」结论作废成立。
**monitor 脏行：成立**。`nodeFlushDAtHandoff()` 由 `nodeTrap` 在 `power→hmon(cfxCode 63→3)`、`hmon→测试体(3→0)` 两处调用；semihosting `immu18≥0x3FF00` 在其上游已 return、`exist bit1=0` 早退 ⇒ off 下 no-op；实现＝`cacheSideExec(D, flush, all)` 即 `CLEAN|INVALIDATE` 逐行写回。`cfx5_mon.s` 两条 invalidate（0x4002、0xC002）后各取一次 CFXREG 且 `FAULT_RECORD==4` ⇒ guest 16；`diagnosis-prefix.txt` 实证 hmon 段 `0xfff00000000..0x140` 脏行、失效后 refill `data=0`、`emi=0` 连续取指（`hmon_base`/`pmem_base` 与 geometry 一致）。
**不回归与门控（我自跑）**：off 01 册 38/38 无 FAIL 行、vast 10/10、021 D 侧 A–F guest 16（`cfx5_dside.s` 与 021 的 `cfx5_main.s` 逐字节相同）；`check-gem5-decode` rc=0、`check-tasks` rc=0、`check-index-blobs` rc=0（354 new-file OK）、`check-patch-tree` rc=2 但 **gem5 段 0 problem**（22 条＝musl 10＋qemu 8＋chipyard 4，均非本任务文件）、`make_patch.py gem5` rc=0 `0 written, 106 unchanged`；补丁 `patch -p1` 应用后与组件源 diff 为空、blob `4dc64cff…` 与补丁 `index 0000000..4dc64cf` 一致；改动集＝组件源 1＋补丁 1＋changelog＋本任务书，`src/cpu/simple/**`、`src/mem/cache/**`、`spec/`、契约未改；未提交 git；术语「寄存器组」；本任务书 0 处运行期/绝对路径；`check-knowledge-refs` rc=2，唯一悬空在 M18 台账（并行会话 `59f3f7ec` 引入、非本任务文件，与本次写入的审阅记录无关）。
**finding**：F1 **收尾必办**（非 engineer 返工）：021 结论作废只落在本任务书/changelog，台账 `milestones-m16.md` 的 021 行与 `issues.yaml` 均无记录 ⇒ 请架构师收尾提交补一笔（不改写 021 既有完成区）；F2 测试强度（不阻断）：关掉全部 I 侧维护后两条**正向**用例（clean→0x10）仍绿，I 侧命令的可观测性由 **noclean 断言**（期望 0x92）承载，我的注入正是把它打红；F3 文档级：完成区「pmem `0x83ff00000000` 脏行」在 `diagnosis-prefix.txt` 内无对应行（地址与 geometry 相符）；F4 文档级：`run.sh` 的 `off: 01 book 38/38` FAIL 分支 rc 写死 0（不影响 NFAIL 与退出码）；F5 文档级：区间例 `addr_size=0x40` 仅跨 1 行，证据目录残留未用的 `cfx5_ddrop.s`（完成区未列）。
**判决：Accepted** —— 基线与 `--inject all` 两份验收命令块在我自己的重跑下全绿、两路注入真红并 `cp`+md5 还原重建回绿、独立第三路注入真红后回绿、约束无违反；F1 为收尾必办，最终接受由架构师终审。
