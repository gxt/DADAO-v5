# m16-qemu-002: 影子 D-Cache 数据通路

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-qemu-001`（`cache-model` 属性 + cfx5 寄存器面）
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景

用户 2026-11-22 选 B：QEMU 用完整影子写回 D-Cache，`cache-model=on` 时只给 arch 测试，`off` 保持直通。`m16-qemu-001` 已落属性与寄存器面；本任务实现**影子 D-Cache 的存储与访存通路**，不含 cfx5 命令（下一件 `m16-qemu-003`）。

## 要做

1. **影子存储**：per-hart（当前单 hart）`tag/valid/dirty` + 行数据，几何与 RTL 一致：8 路 × 128 组 × 64 B = 64 KiB。
2. **访存代理**：`cache-model=on` 时在 PA RAM 前加一层 `MemoryRegionOps`；guest `ld/st`：
   - 读命中：读影子；
   - 读缺失：从底层 RAM 填充整行（64 B），再返回；
   - 写命中：只改影子并置 dirty；
   - 写缺失：写分配（先填充再合并）；
   - 淘汰：脏行整行写回底层 RAM。
3. **直连通道**：DMA（`cfx_pmem`）与镜像装载直连底层 RAM，绕过影子；`off` 时不建代理，行为与现状完全一致。
4. **取指**：本任务只做数据侧；I 侧仍走现有取指路径（命令语义在 `m16-qemu-003`）。
5. **不实现 cfx5 命令**：`cache_ctrl` 的 clean/invalidate/flush 留到下一件；本任务只保证数据通路正确。

## 不做

- 不实现 cfx5 命令、不做 I-Cache 语义；
- 不改 Linux/K0 路径（`off` 默认）；
- 不改 `src/cpu/simple/**`。

## 约束

- 独立 `git worktree`；**不提交 git**；组件改动按 `docs/Process-01` 导出；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `off`：现有 QEMU 代表例（`check-arch-smoke`、K0/inst 一条）rc=0，行为与改前一致；
2. `on`：最小程序（读→写→再读）命中/缺失统计符合几何；同一程序 `on`/`off` 签名一致（功能不因 cache 改变）；
3. **可达 FAIL**：注入「写命中不置 dirty」⇒ 淘汰时不写回，后续 DMA 读到旧值 ⇒ 红；注入「行宽 32 B」⇒ 几何/命中统计红；`cp`+md5 还原后回绿；
4. `check-patch-tree` qemu 段 0 problem、`check-index-blobs`、`make check-tasks` 记录 rc；
5. `--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` rc=0 **10/10**（build 1 + 数据通路 10 例 1 + arch smoke 3 + 静态 5）；`run.sh --inject` rc=0 **29/29**（四路反例：写命中不置 dirty / 行宽 32 B / DMA 走影子 / 游离 `.patch`；前三路 md5 变更→判红→`cp` 还原 md5 相等→回绿，游离 `.patch` 路工具 rc=1、qemu 问题行 1→判红→删除→patches 树 md5 相等→回绿）。数据通路 10 例：读缺失填充、读命中读影子、`off` 直通、最小读→写→再读、写命中 dirty + 淘汰写回、写缺失写分配、64 B 行宽（0/32/56 同行、64 另起一行）、8 路共存 + 第 9 行淘汰首行、128 组不相交（set 0 / set 64 各 8 路）、`on`/`off` 签名一致；末者两模型断言同一组值。命中/缺失/写回统计按现场几何取界（如 `eight_way_set` 读缺失 ≥9、`write_hit` 写回 ≥1），退出时 `dadao-dcache: ways=8 sets=128 line=64 …` 逐例核几何三字段。
**修改文件**（7）：`components/qemu/patches/hw/dadao/dadao-machine.c.patch`、`patches/target/dadao/{cpu.c,cpu.h,helper.c}.patch`、`components/qemu/{README.md,changelog.md}`、本任务书。
**验收结果**（真实 rc）：`make build-qemu` 0（新增代码 0 warning）；`make_patch.py qemu` 0，二次运行 4 份补丁 md5 不变（幂等；注入还原后再验同）；`check-patch-tree` qemu **69 patch / 0 problem**（整跑 rc=0）；`check-index-blobs` 0、`check-component-changelog` 0、`make check-tasks` 0、`check-interface` 0、`check-dirs`/`check-no-residue`/`check-spec-refs`/`check-contracts-dir`/`check-manifests-guard` 均 0；`check-knowledge-refs` **rc=2 预存**（`ADR-0059` 缺文件 + `m17-idl-014` 具体 `.work` 引用，均非本任务文件）。`off` 回归（构建二进制直跑 check-arch-smoke 同内容三成员）：`run_arch --level smoke` 10/10、`min_rom_probe_046t` 25/25、`carrier_tlb` 29/29，逐条 rc=0；`integ042t`（`DADAO_TEST_PROFILE=vast`，与 check-arch 同口径）本任务二进制与主仓基线二进制均 **25/25** 且逐条同名 ⇒ `off` 未回归（此前记的 13/25 系漏设 profile：该探针 `_MACH` 默认 tiny、prelude 默认 vast，混用两套几何的假红，非实现差异）。`check-patch-tree` 判据已按复核意见改为「qemu 段问题行 = 全部 `qemu:` 行减 `N patch(es)`/`empty patch set…` 两条信息行，且整跑 rc 必须为 0」：游离 `.patch` 时 rc=1、problems=1 ⇒ 判红；删除后 rc=0、patches 树 md5 相等 ⇒ 回绿。
**新发现/坑**：① 行 PA 重建必须带组号（`(tag<<7)|set`），否则 set≠0 的填充/整行写回全落到错误 PA——探针 2 例当场判红后才暴露。② `-d cpu` 在 DMA 轮询下产生 GB 级日志，探针改「guest 内比较 + 退出码」通道（0x40+序号定位失败项）。③ 脏行未写回时 semihosting 的 PA 读必须同样走影子，否则 SYS_EXIT 的退出码块读不到（调试钩子的 RAM 半区重定向）。④ `off` 恒等性由「`dcache==NULL` ⇒ 重定向恒等 + 页表/调试仍调原 `address_space_*`」保证，不靠复制开关分支。⑤ 宿主 `/tmp` 曾被其它会话占满，构建统一 `TMPDIR` 落到运行期目录。⑥ `integ042t` 的 `_MACH` 默认 `tiny`、`node_probe_prelude` 默认 `vast`，漏设 `DADAO_TEST_PROFILE` 会把两套几何混用（先得 13/25 假红）；跑该探针必须显式给 profile。
**遗留问题**：① `cache_enable` 的 D 位为 0 时数据侧是否旁路、关闭时脏行如何处置未定（CACHE-07/08 只规定维护命令 no-op），随 `m16-qemu-003` 与命令一起定；② I 侧未建模（任务书 §4），自修改代码需 cfx5 I-invalidate（qemu-003）；③ 替换策略为每组轮询（CACHE-05 自由项），非 LRU；④ 无 in-tree 永久探针（`m16-testcases-009` 落）；⑤ 统计行仅在 `on` 退出时打 stderr（`off` 无），若上层要求静默可改 `-d`/trace；⑥ `run_inst_tiny`/`k0_boot_probe` 依赖安装根 `llvm-mc`，本 worktree 无安装根未直跑，以 arch smoke 同内容成员替代；⑦ 建议后续给 `integ042t` 统一默认 profile（或断言 `_MACH` 与 prelude 一致），避免漏设即假红。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（本深度无嵌套子代理）：影子存储与查找、行 PA 重建、`tlb_fill` 仅数据侧重定向、`off` 三处恒等性（重定向 / 页表读写 / 调试视图）、`MemoryRegionOps` 字节序（`DEVICE_BIG_ENDIAN` + 1..8 B）与 `impl/valid` 分片、PTW 与 A/D 回写经影子的一致性、`on` 才建代理与退出统计副作用、三处注入锚点唯一性、探针每条断言的可达 FAIL。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 行 PA 重建用 `tag<<13` 丢掉组号 ⇒ set≠0 的填充/写回落到错误 PA（探针 2 例红） | ✅已修 | `dadao_dcache_line_pa(c,set,tag)` 用 `(tag<<7)|set` | 探针 10/10；`read_hit`/`sets_128` 由红转绿 |
| F2 探针驱动重复调用构造器 + 死代码行 | ✅已修 | `check_case` 只 `P.build_rom(fn(model))` 一次 | 10 例重跑全绿 |
| F3 `run.sh` 先写 `logs/` 后建目录 ⇒ 首跑 `make_patch` 判为失败 | ✅已修 | 提前 `mkdir -p "$HERE/logs"` | `run.sh` 10/10 |
| F4 `VAR=… run …` 对函数调用的导出不可靠 | ✅已修 | 改 `run "…" env DADAO_TEST_PROFILE=vast python3 …` | 三个 smoke 成员 rc=0 |
| F5 `-nographic` 把监控提示符拼到统计行前，解析恒失败 | ✅已修 | 加 `-monitor none` + 子串匹配 | 统计行逐例被识别 |
| F6 `fill_sram_line` 写入 `value+k` 与“整行同值”断言不符 | ✅已修 | 统一写 `value` | `line_width_64` 绿 |
| F7 行宽注入只靠统计字段报红，缺数据侧判据 | ✅已修 | `line_width_64` 用 0/32/56 同行 + 64 另起一行 | 注入 32 B ⇒ rc 0x41 红 |

**约束核验**：`git status -uall` = 4 补丁 + `README.md` + `changelog.md` + 本任务书；组件源树干净且 `base..HEAD` 恰 1 commit；未改 `src/cpu/simple/**`、`spec/`、契约正文、RTL/gem5；未升版本号；未提交 git；本记录无运行期具体路径；术语「寄存器组」。
**判决**：**待验收**（F1–F7 已修；遗留 ①–⑥ 登记待裁/后续任务）。

### 第 1 轮 reviewer 验收（2026-11-22，判 Needs Revision）

**重跑记录**（均在 worktree 仓库根、相对路径执行，输出为我本人终端原样）
- 运行期证据目录内 `run.sh`：`checks: PASS=10 FAIL=0` / `RESULT: PASS`，rc=0。
- 同目录 `run.sh --inject`：`checks: PASS=25 FAIL=0`，rc=0；三路反例各「md5 变更 → probe 红（rc 0x42 / 0x41 / 0x41）→ `cp` 还原 md5 相等 → 重建 → 回绿」。
- 我**独立注入 3 路**（不经脚本，`cp` 备份 + md5 对账）：写不置 dirty `fee23803→e24185a9`、行宽 32 B `5ad06d2d→47c65504`、DMA 走影子 `fee23803→468c9a81`；三路均判红（`write_hit…` rc=1/0x42、`line_width_64` rc=1/0x41、`write_hit…` rc=1/0x41），还原 md5 相等、重建后回绿 rc=0；组件源树 `git status` 空，无 `git checkout/restore/stash`。
- `off` 回归（我直跑三成员，同内容）：`run_arch --level smoke --cache-model off` **10/10** rc=0；`min_rom_probe_046t` **25 服务全过** rc=0；`carrier_tlb` **29/29** rc=0。
- `integ042t` A/B：本任务二进制 **25/25** rc=0、主仓基线二进制 **25/25** rc=0（见 F2）。
- 补丁：`make_patch.py qemu` rc=0 且 4 份补丁 md5 前后相同（幂等）；`check-patch-tree` rc=0、`qemu: 69 patch(es)`、全仓 `11 patch set(s), 458 patches OK`、0 problem 行；`check-index-blobs`/`check-component-changelog`/`check-tasks` rc=0（脚本内）；`check-knowledge-refs` rc=2 预存（ADR-0059 悬空 2 处 + idl 任务书 1 处具体 `.work` 引用，均非本任务文件）。

**数据通路/直连判定**（读 4 份补丁 + 组件源树）：几何 8 路 × 128 组 × 64 B（`cpu.h` 常量 + 行数组 + 每组替换游标）；读缺失整行 `address_space_read` 填充、读命中读影子、写命中置 dirty、写缺失先填后合（写分配）、脏行淘汰整行写回；`tlb_fill` 仅在 `map:` 处 `access_type != MMU_INST_FETCH` 才重定向（I 侧不重定向）；页表读取与 A/D 回写经 `dadao_dcache_read/write`；调试/semihosting 的 RAM 半区 PA 视图重定向（退出码块脏行可见）；DMA（`pmem_dma_pa`）与镜像装载（`load_image_targphys_as`、boot info 写）走真实 PA 直连底层 RAM；`off` 不建代理，`dcache == NULL` 三处恒等。另跑 `run_arch --level smoke --cache-model on` 10/10 rc=0（`on` 不破 smoke）。

**遗留 1 口径**：QEMU 数据通路**不看** `cache_enable` D 位、不旁路，与 `m16-chipyard-017` 同口径——DADAO-12 §4.6 与 CACHE-07/08/23 对该位只规定「该侧不被维护」，CACHE-30 可观测量清单无旁路项 ⇒ 与 spec 一致，「0=关闭」是否隐含旁路属口径待裁定（任务书遗留①已登记，不改本任务）。当前实现下 D=0 仍走影子 ⇒ 脏行照常在淘汰时写回，**不存在**「关闭即脏行滞留」；`cache-model=off` 根本不建影子、无脏行。**若日后裁 D=0 旁路，必须同批规定切换前写回/失效既有脏行**，否则脏行滞留；另进程退出不写回脏行，现无宿主侧 RAM 读者故无害，属 `m16-qemu-003` clean/flush 范围。

**判决：Needs Revision**（仅 F1 一项阻断；其余全部达标）

- **F1（阻断：证据脚本门控/退出码不一致）**：`run.sh` 的 `check-patch-tree qemu 段 0 problem` 计数正则 `^check-patch-tree: qemu: (assertion|[0-9]+ problem)` 只匹配 `assertion` 开头的错误行。实测：向 qemu 补丁集放一个游离 `.patch` ⇒ 工具 rc=1 且输出 `check-patch-tree: qemu: patch not listed in series: …`，该正则得 `QEMU_PROBLEMS=0` ⇒ `run.sh` 打 `[PASS] check-patch-tree qemu segment: 0 problem … whole-run rc=1` 并以 rc=0 退出（**门控红而证据脚本绿**）；反向注入（源树弄脏 ⇒ `qemu: assertion ⑦/⑥` ⇒ 计数 2 ⇒ FAIL）证明只覆盖⑦–⑩类。改法：把「qemu 段问题行」定义为除 `qemu: N patch(es)`、`qemu: empty patch set…` 两条信息行之外的全部 `^check-patch-tree: qemu:` 行（即问题行数现场派生），保持 `qemu 段 0 problem` 才 PASS；改后重跑运行期证据目录内 `run.sh` 并记录 rc（预期 rc=0、PASS 数不变）。
- **F2（数字，非阻断）**：完成区 `integ042t 13/25 与基线 13/25` 现场复跑为**两台二进制均 25/25**（`25/25 passed`，rc=0），差异更可能源于当时环境（宿主临时目录被占满）；「非本任务引入」结论方向不变，建议收尾订正数字。

**约束核验（本轮）**：变更面 = 4 补丁 + `README.md` + `changelog.md` + 本任务书，注入前后 `git status -uall` 快照逐行相同、组件源树空、游离补丁已删；未动 `src/cpu/simple/**`、`spec/`、契约正文，未升版本号，未提交 git；本记录无运行期具体路径；术语「寄存器组」。

### 第 2 轮 engineer 自审（返工：reviewer F1/F2）

**返工点**：qemu 段问题行旧正则只匹配 `assertion`/`N problem` 两种行首；游离 `.patch` 的 `qemu: patch not listed in series: …`（工具 rc=1）被算成 0 problem ⇒ 门控红、脚本绿。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1（reviewer F1）qemu 段计数漏行 ⇒ 可达假绿 | ✅已修 | `run.sh` 抽 `patch_tree_judge()`：问题行 = 全部 `^check-patch-tree: qemu:` 行减两条信息行（`N patch(es)` / `empty patch set…`），现场派生 | 游离 `.patch`：工具 rc=1、problems=1 ⇒ `[PASS] inject stray-patch: judgement turns red`（并打印该问题行）；删除后 rc=0、problems=0 ⇒ 回绿 |
| R2（F1 后半）缺退出码断言 | ✅已修 | PASS 条件 = `rc==0 && problems==0 && patches>0` | 正常态 `qemu=69 patches, qemu_problems=0, whole-run rc=0`；rc=1 即判红（同上） |
| R3（reviewer F2）完成区 `integ042t` 数字 | ✅已修 | 按 `DADAO_TEST_PROFILE=vast` 复跑，两台二进制均 25/25；根因是 `integ042t._MACH` 默认 tiny、prelude 默认 vast，漏设 profile 时混用两套几何（非环境、非实现差异） | `DADAO_TEST_PROFILE=vast … integ042t` 两跑均 `25/25 passed` rc=0；无 env 时两跑均 13/25（对称假红） |
| R4 新判据缺注入覆盖 | ✅已修 | `--inject` 增第 4 路（游离 patch：基线绿→创建→判红→删除→patches 树 md5 对账→回绿），`EXIT` trap 兜底删除 | `--inject` rc=0 **29/29**；`md5 2da72f95 equal`；收尾源树 `git status` 空、目录内无 `zz-stray-inject.patch` |

**真实输出（本轮重跑）**：`run.sh` rc=0 `checks: PASS=10 FAIL=0 (cases=10)` / `RESULT: PASS`，patch-tree 行 `qemu=69 patches, qemu_problems=0, whole-run rc=0`；`run.sh --inject` rc=0 `checks: PASS=29 FAIL=0 (cases=10)`，游离 patch 段依次打印 `    | check-patch-tree: qemu: patch not listed in series: components/qemu/patches/zz-stray-inject.patch`、`[PASS] … judgement turns red | rc=1 qemu_problems=1 patches=69`、`[PASS] … restored (patches tree md5) | md5 2da72f95 equal`、`[PASS] … back to green | qemu=69 patches, qemu_problems=0, whole-run rc=0`。

**约束核验（本轮）**：变更面仍为 4 补丁 + `README.md` + `changelog.md` + 本任务书（本轮只改运行期证据脚本与任务书，补丁/源树未动：`make_patch` 幂等、源树 `git status` 空、`base..HEAD` 1 commit）；未动 `src/cpu/simple/**`、`spec/`、契约正文、RTL/gem5；未升版本号；未提交 git；本记录无运行期具体路径；术语「寄存器组」。
**判决**：**待验收**（R1–R4 已修；遗留 ①–⑦ 登记）。

### 第 2 轮 reviewer 验收（2026-11-22，判 Accepted）

**重跑记录**（均在 worktree 仓库根、相对路径执行；以下为我本人终端原样输出与退出码）
- 运行期证据目录内 `run.sh`：`checks: PASS=10 FAIL=0 (cases=10)` / `RESULT: PASS`，**rc=0**；patch-tree 行 `qemu=69 patches, qemu_problems=0, whole-run rc=0`。
- 同目录 `run.sh --inject`：`checks: PASS=29 FAIL=0 (cases=10)`，**rc=0**；三路源注入各「md5 变更 → probe 红（rc 66/65/65 = 0x42/0x41/0x41）→ `cp` 还原 md5 相等 → 重建 → 回绿」；第 4 路游离 `.patch`：`baseline green (qemu=69, problems=0)` → `rc=1 qemu_problems=1 patches=69` 并打印问题行 `qemu: patch not listed in series: …` → 删除后 `patches tree md5 2da72f95 equal` → `back to green (qemu=69, problems=0, rc=0)`。
- **我独立注入 1 路**（不经脚本，自建 `components/qemu/patches/zz-reviewer-stray.patch`）：基线 `check-patch-tree` **rc=0**、qemu 仅 `69 patch(es)` 1 行；注入后 **rc=1**、qemu 行 = 问题行 1 + 信息行 1（`all=2 info=1 problems=1`）；删除后 **rc=0**、`all=1 info=1 problems=0`、`69 patch(es)`、patches 树 md5 `2da72f95` 相等；全程只新建/`rm`，未用 `git checkout/restore/stash`。
- **`CPT_RC!=0` 必 FAIL**（我另注入非 qemu 组件游离补丁整跑 `run.sh`）：`[FAIL] check-patch-tree qemu segment: 0 problem | rc=1 rc=1 qemu_problems=0 patches=69`、`checks: PASS=8 FAIL=2`、`RESULT: FAIL`、**EXIT=1**；删除后 `check-patch-tree` rc=0、qemu `69 patch(es)`、树 md5 恢复 `2da72f95`。
- `patch_tree_judge`（读脚本核）：问题行 = 全部 `^check-patch-tree: qemu:` 行 − `N patch(es)`/`empty patch set…` 两条信息行，现场派生；PASS 需 `rc==0 && problems==0 && patches>0`，任一不满足即 `return 1` ⇒ `bad`；`grep -c … || true` 只吞退出码不吞计数，`patches` 为空即判红；问题行逐条打印到 `|` 行。
- 数据通路/`off` 回归（我直跑，同内容）：`probe.py` **10/10** rc=0（含 `off_bypasses_cache`、`on_off_signature`）；`run_arch --level smoke --cache-model off` **10 case × 1 平台 PASS** rc=0；`min_rom_probe_046t` `service coverage: all 25 service ids exercised` + `RESULT: PASS` rc=0；`carrier_tlb` **29/29 checks passed** rc=0。
- `integ042t` A/B：`DADAO_TEST_PROFILE=vast` 本任务二进制 **25/25 passed** rc=0、主仓基线二进制 **25/25 passed** rc=0；不设 env 两台均 **13/25** rc=1（对称假红）。根因记录属实：探针 `_MACH = _machine_profile.load(… or "tiny")`（`min_rom_probe_integ042t.py:52`）、`node_probe_prelude.PROFILE = … or "vast"`（`node_probe_prelude.py:55`）。

**约束核验**：注入前/后 `git status --porcelain -uall` 快照逐行相同（恰 7 文件：4 补丁 + `README.md` + `changelog.md` + 本任务书），patches 树 md5 始终 `2da72f95`、无游离残留，组件源树 `git status` 空；分支 `master..HEAD` 0 commit（未提交 git）；未动 `src/cpu/simple/**`、`spec/`、契约正文；未升版本号；本记录无具体运行期路径；术语「寄存器组」。

**观察（非阻断）**：`patch_tree_judge` 把 `qemu: source worktree absent; skipping…` 这类信息行也计为问题 ⇒ 源树缺失时会假红（保守方向，且此时 build 已先失败），后续可与 `check_patch_tree.py` 的信息行清单对齐。

**判决：Accepted**（第 1 轮唯一阻断 F1 已按要求修复并经我独立注入与 `CPT_RC` 反例复核；F2 数字已订正且复跑属实）
