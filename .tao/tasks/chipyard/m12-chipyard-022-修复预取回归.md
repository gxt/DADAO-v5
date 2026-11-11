# m12-chipyard-022: 修复预取回归（`pfAddrLegal` 用复位值地址）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-009`（已合入）；与后续任务串行（单写者）
**可并行分片**：否
**状态**：已验证

## 背景（`ISS-382`，P1）

`m12-chipyard-009` 的 reviewer 发现：**预取自 `m12-chipyard-008` 合入后全部失效**。

证据（400 条直线 `or.o`、无分支）：

```
prefetch=0   demand_fetch=313   exec=618
```

跨 beat 全付 6 拍 SRAM 往返，与「用例短 / 跳转打散」无关。

**根因**（diff 级）：`008` 把 `specBacked(pfReqAddr)` 加进 `pfAddrLegal`，而 `pfReqAddr` 取自**复位值 0 的 `pfReqBeat`**；地址 0 不在 Tiny 三段窗口 ⇒ `pfWanted` 恒假 ⇒ 预取从未发起。`020` 的「p50=1、在飞峰值 4」测于 `008` 之前，故未暴露。

## 目标

1. **修复**：`pfAddrLegal` 改为检查**待发**的 `pfBeat`（而不是已锁存的 `pfReqAddr`）；等价于「先算出下一个要取的 beat 地址，再用它与窗口比对」。
2. **补门控断言**（防止再次静默失效）：直线流用例必须满足 `prefetch > 0`（且 `demand_fetch` 与 `exec` 关系合理）；建议放进 `m12-chipyard-020` 的 `xbeat` 探针或本任务证据脚本，并纳入该类任务的验收。
3. **回归**：273 例 md5 不变；跨 beat 代价恢复 `020` 的水平（直线流 p50 ≤2 拍）；`ldm`/`stm` 不劣化。

## 非范围

- 不改访存语义（`008` 已定）
- 不改控制流/RAS（`009` 已定）
- 不重新设计预取（`020` 已定 4 槽 + 数据优先）

## 验收标准

1. **直线流**：`xbeat`/等价探针实测 `prefetch > 0`，跨 beat p50 ≤2 拍（给出改前/改后对比）
2. **数据优先仍有效**：`fetch_requests_after_data_request = 0`
3. 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变
4. Verilator 构建 rc=0（主控机）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
5. 一键证据脚本（含可达 FAIL 注入：把 `pfAddrLegal` 改回旧写法 ⇒ `prefetch=0` ⇒ 必须 FAIL）
6. 完成区 ≤30 行、无运行期路径；**「修改文件」与 `git status` 对账**（`ISS-377`）

## 说明

- 必须在独立 `git worktree` 内作业（`ISS-368`）；不占用 207/208。
- 组件单写者；补丁走 `make_patch`。
- **根因已定位到一行**，本任务应是小改动（≤30 行）；若发现需要更大改动，停下报告。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-11）

**审查范围**：`WumingCore` 预取地址合法性（`pfNextAddr`/`pfBeat`/`pfReqAddr` 的时序关系）、`gen_probe` 两处收尾、证据脚本断言可达性；逐行核对预取发射与 A 通道 bits 的时序、stale 槽复用、窗口边界。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `pfAddrLegal` 判已锁存地址 ⇒ 复位值 0 永不合法 | ✅已修 | `pfNextAddr = Cat(0, pfBeat, 0)` 并用它做 `specBacked`/`supportsGetSafe` | 注入旧写法 ⇒ `prefetch=0`/p50=8；修复后应用段 218/1 |
| F2 判定地址与 A 通道实际发送的 `pfReqBits` 是否可能不一致 | ❌不修（已核） | 无 | `pfWanted` 时 `pfReqBeat := pfBeat`，下一拍 `pfReqBits(pfReqSlot)` 取同一值；`pfReqValid` 期间 `pfWanted=0`，bits 稳定 |
| F3 stale 槽在回复前被复用会撞 source ID | ❌不修（已核） | 无 | `freeSlot = PriorityEncoder(pfValid.map(!_))`，stale 槽仍 `pfValid=1` ⇒ 回复前不被选；`pfLive` 只影响 beat 号 |
| F4 `UNDI` 收尾在 009 后不终止（harness rc=255、bench 永不 halt） | ✅已修（探针）/ ❌不修（bench 判据） | `xbeat`/`timing` 追加 `SYS_EXIT`；bench 的 halt 判据不在本任务范围，E 段改断 PROBE 计数器 | D/F rc=0；E `after=0`、`during=1` |
| F5 门控是否真能失败 | ✅已验 | `--self-test-inject` 改回旧 `pfAddrLegal` | 注入：`prefetch=0`、p50=8、4 条断言 FAIL；还原 md5 一致、重建 rc=0、回绿 |

**判决**：F1 修复、F4 探针适配、F5 注入可达 FAIL；F2/F3 按上表证据判定不改；状态 → 待验收。

### 第 1 轮 reviewer 验收（2026-11-11，reviewer 亲跑）

**重跑记录**（worktree 根、相对路径；长输出留运行期日志目录 `m12-chipyard-022-reviewer-*`）：

- 全量一键证据脚本 ×2（基线 + 收口）→ `summary: PASS=44 FAIL=0`、退出码 0：273 例 md5 `2d4d9465…` 三向一致 + `cmp` byte-exact；`prefetch=338 demand_fetch=20 exec=605`，按窗口拆 prefetch sram/hmon/boot=218/13/107、demand=1/3/16 ⇒ 应用段 218/1、全程 338/20，与完成区逐数吻合；跨 beat `n=199 p50=1 max=1 gt2=0 hist{1:199}`、`inner_all_one=true`；latency n=20 max=6 ⇒ 槽需 3 ≤ 4；`fetch_requests_after_data_request=0`、`during=1`、burst `234−34=200`；elab/Verilator rc=0、`%Error`=0、`pfValid_0..3`=4；apply-series/source-state/patch-tree rc=0；L2 rc=0（lit 163/163 + E2E 全过、`module checks (L2): PASS`）。
- 改前基线亲证（注入回旧写法重建）→ `prefetch=0 demand_fetch=304`、`cross_p50=8 gt2=199 hist{8:199}`、4 条断言 FAIL；demand 按窗口 84/8/212 ⇒ 完成区「304 / 应用段 212」逐数吻合（任务书背景 313 为 009 的 UNDI 收尾口径，`before/` 实测 313/207，自洽）。
- `--self-test-inject` 亲跑 → 退出码 0：注入 ⇒ `prefetch=0`/`p50=8` 4 条 FAIL ⇒ `cp`+md5 还原 `116e94fd…` 一致 ⇒ 重建 rc=0 ⇒ `restore -> PASS`。
- reviewer 独立注入①：`pfNextAddr` 中 `pfBeat`→`pfBeat + 8.U`（重建后 `WumingCore.sv` 确含 `_pfBeat_T + 45'h8`）⇒ D 段 `prefetch=338/p50=1` 与基线**完全一致、未 FAIL**：该注入只改**判定**地址，实际发送仍走 `pfReqBeat := pfBeat`，且 +8 仍在 sram 窗口内 ⇒ 行为中性扰动（如实记录，非门控漏判）。
- reviewer 独立注入②（窗口外构造）：`pfNextAddr + 2^40`（推出 sram/hmon/bootrom 三窗）⇒ 重建 ⇒ `ONLY=D` **rc=1、4 条 FAIL**（`prefetch=0`/`demand=304`/`p50=8`/`gt2=199`），xbeat 日志 **prefetch 事件=0、零窗口外地址上总线**；`ONLY=C` **rc=0**、273 例 md5 仍 `2d4d9465…` ⇒ 窗口外目标不发预取、需求路径不受影响（不越权、不误取）；`cp` 还原 md5 `116e94fd…`=审前 ⇒ 全量回绿 `PASS=44 FAIL=0`。
- L1 红项归属（亲跑 + 对照 master）：三红 target = `check-knowledge-refs`（唯一 offender 在 **009 任务书**的运行期证据路径引用；master 已于 `b5c59847` 改为「运行期证据目录」措辞、主树该门控 rc=0）、`check-run-artifacts`（night 日志、m13-gem5 的 `.c`）、`check-temp-dirs`（m13-* 临时目录）；本任务命中 0。

**约束核验**：① 独立 worktree、分支=任务号 ✔；② 未 commit（HEAD 仍 `6f423912`）、未 push、未改台账 ✔；③ 4 交付文件 md5 与审前快照逐一相同（`b6e4f6c6…`/`456d54e7…`/`86807158…`/`faeba4a6…`）✔；④ 完成区 17 行 ≤30、零运行期路径 ✔；⑤ 判定地址 ≡ 发送地址（同拍 `pfReqBeat := pfBeat` 锁存、`!pfReqValid` 防重发）✔；⑥ `specBacked + supportsGetSafe` 仍在 `pfAddrLegal`、`pfWanted` 保留 `!dataBusy`（数据优先）✔；⑦ 核心净增 +5 行（1155→1160）≤30 ✔；⑧ 直线流 `prefetch>0` 新断言存在且可达 FAIL（`prefetch>=1`、`demand<=50`、`p50<=2`、`gt2<=1` 均被我实测打红过）✔。

**findings（不阻断，交 architect）**：

- F-a 证据脚本 `ONLY` 非空但不匹配任何 section 时 `PASS=0 FAIL=0` 却退出 0（实测 `ONLY=B,C,D`）⇒ 建议加「至少跑到 1 个 section」护栏。
- F-b E 段不校验 bench 自身退出码、`PROBE verdict=FAIL`（仅因 `core halted` 判据自 009 起失效，`halted_cycle=0`；engineer 已披露为遗留）⇒ 数据优先 4 项计数断言真跑真判；建议后续任务按 009 异常模型更新 bench 收尾。
- F-c `prefetch>0` 断言落在运行期证据脚本（任务书允许的落点）⇒ 仓库内暂无常驻门控，同类任务须复用该脚本；如需常驻建议升格至 `tools/`。
- F-d 分支基线 `80ced673` 落后 master（`b5c59847` 已修 009 的运行期路径引用，其后 master 仍在推进），合并回 master 后 L1 该红自动消失；architect 合并时留意。

**判决**：**Accepted** —— 验收命令块在 reviewer 自己的重跑下全绿（PASS=44 FAIL=0、退出 0），两次独立注入均「注入 → FAIL/行为可判 → `cp`+md5 还原 → 回绿」，硬约束逐条无违反，L1 红项逐条核为他任务。

## 完成区

**测试结果**：一键证据脚本 A–G 全绿（PASS=44 / FAIL=0，退出码 0）；注入自检 `--self-test-inject` 退出码 0（改回旧 `pfAddrLegal` ⇒ `prefetch=0`、跨 beat p50=8 ⇒ 脚本 FAIL；`cp`+md5 还原 ⇒ 重建 rc=0 ⇒ 回绿）。
**修改文件**：
- `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch`（改源树后 `make_patch` 重导出）
- `components/chipyard/changelog.md`
- `tools/chipyard/fetch_probe/gen_probe.py`（`xbeat`/`timing` 改 `SYS_EXIT` 收尾）
- `.tao/tasks/chipyard/m12-chipyard-022-修复预取回归.md`（本任务书）
（`git status --porcelain -uall` = 上述 4 项，无其它改动）
**验收结果**：
- 直线流（400 条 `or.o`，应用段）：`prefetch` 0 → 218、需求取指 212 → 1（全程 0→338 / 304→20）；跨 beat 199 次 p50 8 → 1、最大 8 → 1、>2 拍 199 → 0；同拍内恒 1 拍
- 数据优先：`fetch_requests_after_data_request=0`，数据停顿期间取指请求 ≤1，200 拍数据 burst 耗时不变
- 273 例 md5 `2d4d94651346ef673c5a855e024c1489` 三向一致（YAML/本次/基线），逐字节相同
- Verilator/elaboration rc=0、`%Error`=0；`pfValid_0..3`=4、无第 5 槽
- `apply-series`/`check-source-state`/`check-patch-tree` rc=0；L2 rc=0 全绿；L1 整体非 0 但红项全为他任务（他任务日志名/临时目录、`m12-chipyard-009` 任务书的 `.work` 引用），本任务零命中
**新发现/坑**：① `m12-009` 起 `UNDI` 不再 halt 而是进 hmon 异常路径，`fetch_probe` 的 `UNDI` 收尾在 harness 上会 rc=255/无限异常循环——探针改用 `SYS_EXIT`；② 同因，独立 bench 的「core halted」判据对 `UNDI` 收尾恒假（018 既有，非本任务），数据优先改由 PROBE 计数器断言；③ 预取失败是静默的（`pfWanted` 恒假无任何诊断），已由本任务 `prefetch>0` 门控兜住，建议同类任务复用。
**遗留问题**：无（范围外：bench 的 halt 判据待后续任务按 `009` 的异常模型更新）。

#### 收尾（architect，2026-11-11 10:33）

- reviewer **Accepted**：`pfAddrLegal` 判 `pfNextAddr = Cat(0, pfBeat, 0)`（待发 beat），发送侧 `pfReqBeat := pfBeat` 同拍锁存 ⇒ **判定地址 ≡ 发送地址**。
- 改前（注入旧写法复现）：`prefetch=0 / demand=304（应用段 212）/ p50=8 / gt2=199`；改后：`prefetch=338（应用段 218）/ demand=20（应用段 1）/ p50=1 / gt2=0`，与完成区逐数一致。
- **不越权**：全部预取/需求地址落在 sram/hmon/bootrom 三窗内；reviewer 注入 `pfNextAddr + 2^40` ⇒ `ONLY=D` rc=1、窗口外地址**零总线事件**，`ONLY=C` 273 例 md5 不变。
- 数据优先：`after=0`、`during=1`、burst 200 拍不变。
- **门控缺口已补**：证据脚本 D 段 `prefetch >= 1`（另有 `demand<=50`、`p50<=2`、`gt2<=1`）；reviewer 两次独立注入均打红，确认 020 脚本原本无此断言。
- L2 rc=0（163/163）；`apply-series`/`check-source-state`/`check-patch-tree` rc=0；273 例 md5 `2d4d9465…` 三向一致。
- 遗留转 `ISS-385`：F-a `ONLY` 不匹配任何 section 时 `PASS=0 FAIL=0` 仍退出 0（需「至少跑 1 个 section」护栏）；F-b E 段不校验 bench 退出码（`core halted` 判据自 009 起失效，`halted_cycle=0`）；F-c `prefetch>0` 只在运行期证据脚本、仓库内无常驻门控（建议升格 `tools/`）。
