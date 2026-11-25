# m17-idl-022: trace「跳过集」两侧对称化（关闭 `ISS-537`）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-004`（trace 比较器）、`m17-idl-021`（复核遗留）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（`ISS-537`，用户 2026-11-25 指示「立任务修掉」）

`python3 idl/tools/idl_check_trace.py` 全量 **273/274**：唯一红是 `ld.o_rrii_ra` 第 205 条（pc `0x0000ffffff01071c`），只差 `dst` 字段：

- exec 侧：`ra0,ra1,ra2,ra4,ra5,ra6,ra7,ra8,ra61,ra62,ra63`
- QEMU 侧：`ra0,ra1,ra2,ra3,ra4,ra6,ra7,ra8,ra9,ra10,ra62,ra63`

**根因不是平台语义分歧**，而是比较器的 E4 判定**逐侧独立**：

- `spec/SimRISC-00 §2.4`：`ra1..ra63` 只有 `RACNT` 有效区内（`ra[64−RACNT..63]`）是架构可见的，有效区外内容未定义；
- `idl/tools/idl_trace_common.py:reg_delta()` 用**每侧各自维护**的 `ra_ok` 集合决定「这个条目内容来源未定义 ⇒ 不列入 `dst`」；QEMU 与执行器的物理布局不同（环形缓冲 vs 搬移），同一逻辑状态下「来源未定义」的条目集合不同；
- 于是两侧用**不同规则**过滤同一字段，再逐字比较，必然假红（该例 `ra_skip=2131`）。

## 要做

1. `reg_delta()` 把「被跳过」的 RA 条目**名字**一并返回（当前只返回计数）；`ra_skips` 统计口径保持为条目数；
2. QEMU 侧派生（`idl_qemu_trace.py:derive_trace`）与执行器侧派生（`idl_exec_trace.py`）在每条内存记录上附加该跳过集（建议字段名 `skip`，值为寄存器名列表）；
3. `idl_check_trace.py:compare_records()`：逐条取 `skip = set(exec.skip) | set(qemu.skip)`，把两侧 `dst`/`val` 中命中 `skip` 的条目**同时**剔除后再比较（`dst`/`val` 并列，须成对过滤）；
4. 落盘 JSONL 的字段面**保持不变**（写出前剔除 `skip`）；若选择把 `skip` 落到 JSONL，则必须同步 `idl/docs/trace-format.md` §1 并重生成 `idl/docs/trace-sample.jsonl`（`--sample-out`）；
5. 全量 `idl_check_trace` 复跑应 **274/274**；`ra_skips` 计数与 `--self-test`/`--sample-check` 行为不变。

## 不做

- 不改 QEMU/gem5/chipyard 的 RAS 实现（物理布局归各平台任务）；
- 不改 `dst` 的架构语义（「值变化的写回集合」），不放松有效区内的值比较；
- 不改 spec/契约/版本号。

## 约束

- 独立 `git worktree`；不提交 git；只动 `idl/tools/{idl_trace_common.py,idl_qemu_trace.py,idl_exec_trace.py,idl_check_trace.py}`、必要时 `idl/docs/{trace-format.md,trace-sample.jsonl}`、本任务书；
- 证据脚本固定为运行期证据目录内的 `run.sh`；完成区 ≤30 行；`**状态**` 改 `待验收`。

## 验证

1. 全量 `idl_check_trace`：**274/274**、rc=0（`--only ld.o_rrii_ra` 单独绿）；
2. **可达 FAIL ①**：临时禁用第 3 步的并集剔除 ⇒ `ld.o_rrii_ra` 第 205 条复红；`cp`+md5 还原 ⇒ 回绿；
3. **可达 FAIL ②（防掩盖）**：故意把执行器侧有效区内某条目值改错（如 `ra62`，须在窗口内且被写）⇒ 仍必红；还原后回绿——证明剔除只作用于「来源未定义」条目；
4. `make check-idl`（L2 冒烟）rc=0；`check-idl-parse`/`check-knowledge-refs`/`check-spec-refs` rc=0；
5. `git status -uall` 仅上述文件 + 任务书；越界 0。

## 审阅记录

### 第 1 轮 engineer 自审

- **逻辑**：`reg_delta` 的 `ra_ok` 只用于产出比较跳过集，`dst` 保持「有效区内值变化的写回集合」；`call`/`ret` 整栈搬移按**来源槽**继承可比性，直接写仍即时可比。故并集剔除只丢来源未定义条目，注入②（有效值改错）必红。
- **边界**：`_ra_shift` 覆盖 C1/C3b（push，含满栈）与 D3（pop）；RACNT 0→1 须新栈顶确有变化才判 push（防 `rd2ra` 写 `ra0` 误配）；搬移关系不成立即回退 `None`（沿用原「值变化=直接写」口径）。
- **防造假**：全量/单例/两路注入均由 `run.sh` 现场执行并落日志；还原一律 `cp`+md5 对账（注入前后 md5 均打印）；JSONL 键面逐条回读断言。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 仅按任务书做「返回跳过名 + 并集剔除」时，第 205 条只是从 `dst` 红变成 `val` 红 | ✅已修 | 新增 `_ra_shift` 按来源槽继承可比性（识别 push/pop 搬移） | `run.log` 全量 274/274、单例 PASS |
| 若 `dst` 也按新信任集过滤，则注入①（关并集）不再复红，验收②失去可达 FAIL | ✅已修 | `dst` 始终列有效区内全部值变化，信任集只产出 `skips` | `inj1.log` 复现第 205 条 `dst` 差异 |
| 文档 §2.1 覆盖率数字与 §3 E4 口径随实现变化 | ✅已修 | `idl/docs/trace-format.md` §2.1 数字取本次现场测量、§3 E4 补搬移/并集口径 | `run.log` 现场派生 249457/72462/149766 |

### 第 1 轮 reviewer 复核

**重跑**（reviewer 亲跑，仓库根、运行期证据目录内 `run.sh` 无参）：**RC=0、37 PASS / 0 FAIL**；现场 `idl_check_trace: 274/274 …共 249457 条指令记录`、`ra_skip=72462 rd8_skip=149766`（与文档 §2.1、完成区一致）；`--only ld.o_rrii_ra` `[PASS] … ra_skip=2311`；JSONL 键面 `checked 1323 1323 bad 0`、`--sample-check` PASS、样例重生成逐字节相同、exec 自检 `11/11`、check 自检 rc=0；`make check-idl`（`check-idl: PASS`、`[FAIL]`=0）/`check-idl-parse`/`check-knowledge-refs`/`check-spec-refs` 均 **rc=0**。
**可达 FAIL ①**（脚本内）：关并集剔除 ⇒ `rc=1`、`第 205 条（pc 0x0000ffffff01071c）dst: exec […] != QEMU […]`；`cp`+md5 还原（`c3d3d3f4…`）⇒ 回绿 `rc=0`。
**可达 FAIL ②**（脚本内）：第 188 条改 `ra62` ⇒ `rc=1`、`val: exec …0xdead000000000062`；还原（`54b6dca7…`）⇒ 回绿 `rc=0`。
**独立注入（reviewer 自做，非 engineer 自检）**：禁用 `reg_delta` 跳过集产出 ⇒ 同一 `run.sh` **RC=1、13 FAIL**（`273/274`、`ra_skip=0`、自检 10/11），红即 ISS-537 原始 `dst` 差异；`cp`+md5 还原（`2b9eebe7…` 与注入前相等）⇒ 再跑同一脚本 **RC=0、37 PASS**。
**`_ra_shift` 判据**：全 274 例普查（`ra_skip>0` 仅 5 例，覆盖 72462/72462 = 100%）——`push` 仅 `call_*` 触发、`pop` 仅 `ret_*`、`rd2ra_orri_ra` 零触发；`shift=None` 却「值变进 skip」= **0**（直写必比）；合成 16 用例全 PASS（中段真写⇒回退 `None`、rd2ra 只改 ra0/栈顶、C2 折叠、满栈压栈、pop 中段真写、搬移值仍列 dst）。
**掩盖面**：`两侧都列+值不同+被并集剔` = **11 条**，全在 `ld.o_rrii_ra` 第 205 条（满栈 push、两侧 `old_ok` 皆空、前值已不同的未定义中段）；架构可见的新栈顶 `ra63` 两侧相等且未被剔；`未被剔却值不同` = 0、`dst 不对称未解掉` = 0。
**约束**：变更面 = 5 个 idl 文件 + 任务书（`.dadao` 软链 gitignored、不在集内）；`dst` 仍「有效区内值变化全列」（搬移值也列、由比较器成对剔）；`ra_skips = len(skips)` 条目数；未动 spec/契约/版本号；审查前后 6 文件 `git status` 与 md5 逐项一致、无残留。
**判决：Accepted**。残余风险（不阻断，供架构师知悉）：并集剔除按两侧 lineage 取并，理论上「一侧判未定义即丢弃」可致假阴——实测 11/249457 条且均属 §2.4 未定义中段；`_ra_shift` 最窄误判面为「满栈且 62 条目全等时 C2 折叠被认作 push」，现网 0 次。

## 完成区

**测试结果**：一键证据 `run.sh` **37 PASS / 0 FAIL，rc=0**；全量 `idl_check_trace` **274/274**（rc=0，249457 条记录，`[FAIL]`=0）；`--only ld.o_rrii_ra` 绿（ra_skip=2311）；样例 `--sample-check` PASS 且重生成逐字节相同；`idl_exec_trace --self-test` 11/11、`idl_check_trace --self-test` 9/9；`make check-idl` 274/274 PASS、`check-idl-parse`/`check-knowledge-refs`/`check-spec-refs` rc=0。
**修改文件**：`idl/tools/idl_trace_common.py`（`_ra_shift` + `reg_delta` 返回跳过集）、`idl/tools/idl_qemu_trace.py`、`idl/tools/idl_exec_trace.py`（内存记录附 `skip`）、`idl/tools/idl_check_trace.py`（并集成对剔除）、`idl/docs/trace-format.md`（§2.1 数字/§3 E4 口径）、本任务书。
**验收结果**：① 关并集剔除 ⇒ `第 205 条（pc 0x0000ffffff01071c）dst` 复红（rc=1，还原 ISS-537 原始 exec/QEMU dst 差异）；`cp`+md5 还原（`c3d3d3f4…`）⇒ 回绿。② 执行器侧 `ra62` 值改错（现场选点第 188 条，两侧 `dst` 均列且不在并集）⇒ `val: exec …0xdead000000000062` 复红（rc=1）；还原（`54b6dca7…`）⇒ 回绿。落盘 JSONL 两侧各 1323 条，键序仍 `seq/pc/insn/id/mn/dst/val/exc`、含 `skip` 的行 = 0。
**新发现/坑**：仅「返回跳过名 + 并集剔除」不足：旧 `ra_ok` 把整栈搬移造成的值变化当作定义写，两侧对 undefined 内容的信任集不同，第 205 条会从 `dst` 红转成 `val` 红。改为按来源槽继承可比性后，`dst` 仍列有效区内全部值变化、比较器并集剔除；`ra_skip` 该例 2131→2311、全量 72462（口径仍为条目数）。
**遗留问题**：无。ISS-537 待主会话收尾关闭；docs §2.1 数字已同步本次 274 例现场测量（`ra_skip` 72462、`rd8_skip` 149766、249457 条）。
