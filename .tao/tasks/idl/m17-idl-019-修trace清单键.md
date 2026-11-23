# m17-idl-019: 修 `idl_check_trace --cases` 的清单键（ISS-518）

**模块**：idl
**项目里程碑**：M17
**依赖**：无
**可并行分片**：否
**预估**：30–60 min
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景

`ISS-518`：`idl/tools/idl_check_trace.py` 的 `--cases` 读取清单时强制 `id` 键，而现行清单 `idl/data/idl_exec_cases.toml` 用 `image`（`[[case]] image = "tests/inst/..."`）⇒ 直接传主清单会报缺键。阶段门控走 `idl_four_way.py` 不触发，属潜伏缺陷。

## 要做

1. `idl/tools/idl_check_trace.py`：`--cases` 同时接受 `image`（现状）与 `id`（旧格式），`id` 只作诊断别名；两者都缺 ⇒ 明确报错；
2. 若 `image` 是相对路径，按仓库根解析（与 `idl_four_way.py` 同口径）；
3. `--self-test` 增两路：`image` 清单可通过、缺键清单报错；
4. 不改清单内容、不改 trace 判据。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；只动该脚本 + 本任务书；完成区 ≤30 行。

## 验证

1. `python3 idl/tools/idl_check_trace.py --cases idl/data/idl_exec_cases.toml --self-test`（或对应子命令）rc=0；
2. 用主清单实际解析 1 例（不需要全量跑 trace）；
3. **可达 FAIL**：临时把清单 `image` 改成 `bogus` ⇒ 明确报错（非 KeyError 栈）；
4. `make check-idl` 仍 272/272（未触碰主路径）。

## 完成区

**测试结果**：运行期证据 `run.sh` **33/33 PASS、rc=0**（逐项打印 expected/actual，含注入 A/B → 预期 FAIL → `cp`+md5 还原 → 回绿，md5 `f951c479…` 前后相同）。
**修改文件**：`idl/tools/idl_check_trace.py`；本任务书（无其它文件）。
**验收结果**：
- `python3 idl/tools/idl_check_trace.py --cases idl/data/idl_exec_cases.toml --self-test` ⇒ **rc=0，9/9 PASS**（image 清单通过 / 缺键 rc=2 指名 `缺 'image'` / 缺文件 rc=2 指名 `不存在`；三路均无 Traceback）。
- 主清单全量解析 ⇒ **272 例**，id 唯一 **272**、`id == Path(image).stem` 不符 **0**、镜像文件缺失 **0**；首例 `ld.o_rrii_rd ← tests/inst/01-load-store/ld.o_rrii_rd.S`。旧格式 `id = "add.st_orrr_rd"` 清单仍可解析（别名保留）。
- 端到端 1 例（不需全量）：`run_inst_tiny --id ld.o_rrii_rd` rc=0 → `idl_check_trace --cases <主清单> --only ld.o_rrii_rd` **rc=0**，`[PASS] ld.o_rrii_rd records=1079 … records/states/exit/out 全等`。
- `make check-idl` ⇒ **272/272**（`check_four_way: 272/272 例四方一致（parties=idl,qemu；主清单 272 / pending 0 / 现场派生 272）`），26 s；`check-dirs`、`check-manifests-guard` 仍 rc=0。
- 可达 FAIL：注入 A（`cid = Path(image).stem` → `case["id"]`，复现 ISS-518）⇒ `--self-test` rc=1、主清单 rc=1 且含 `KeyError`；注入 B（删镜像存在性断言）⇒ bogus 清单加载 rc=0、`--self-test` rc=1；还原后两者 rc=0/2 回绿。
**新发现/坑**：① `image` 用例名取 `Path(image).stem`（同 `idl_four_way.py`），旧 `id` 仅诊断别名；缺键/缺文件/非字符串/TOML 解析错统一 `_fail`（stderr + rc=2），并须断言 stderr 无 `bootrom not found`——否则 `make_cfg` 的 rc=2 会与清单错误同值形成恒真；② `idl_check_trace.py` 自身 `sys.dont_write_bytecode` 在 exec 之后才生效 ⇒ 导入即落 `idl/tools/__pycache__`（`check-manifests-guard` 红），证据脚本须 `PYTHONDONTWRITEBYTECODE=1`；③ 工作树无安装根时，`.dadao/cross-toolchain` symlink 主仓（只读）+ 复制主仓 BootROM（md5 `a5d78816…` 一致）即可跑 `make check-idl`；④ `load_cases` 须在 `make_cfg` 之前，否则清单错误被环境错误掩盖。
**遗留问题**：`build_sample` 的 `SystemExit(str)` 仍 rc=1，与 docstring「2=输入问题」不一致（既有、未在本次范围）；无其它。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 注入 B 两支同果（CLI rc=2 由 `make_cfg` 报 `bootrom not found`，非清单错误 ⇒ 恒真） | ✅已修 | 反例改为直调 `load_cases` | `inject_B_bogus_load_rc_differs unexpected=2 actual=0` |
| 导入即落 `idl/tools/__pycache__`（目录断言红） | ✅已修 | 证据脚本 `export PYTHONDONTWRITEBYTECODE=1`，并 `rm -rf` 已生成缓存 | `find idl -name __pycache__` = 0；`check-manifests-guard` rc=0 |
| TOML 解析错/非字符串 `image` 会冒 `TOMLDecodeError`/`TypeError` 栈 | ✅已修 | `except (OSError, ValueError)`；`image`/`id` 类型校验走 `_fail` | `--self-test` 9/9；bogus/缺键 CLI 均 rc=2 无 Traceback |
| `load_cases` 在 `make_cfg` 之后 ⇒ 清单错误被环境错误掩盖 | ✅已修 | 两行前置交换 | bogus CLI 输出 `image 不存在`，非 `qemu not found` |
| 自检路由 1 用 `json.dumps` 生成 TOML 字符串 | ❌不修 | — | 路径无特殊字符，JSON 字符串与 TOML 基本串在本例等价（实测解析通过） |
| 自检路由数为 3（任务书写「增两路」） | ❌不修 | — | 第 3 路即「验证 3」缺文件反例常驻化；两路要求项均在，无副作用 |

### 第 1 轮 reviewer 复核

| 核验项 | reviewer 重跑真实结果 |
|---|---|
| 1 运行期证据目录内 `run.sh`（参数 = 仓库根） | rc=0，**33 PASS / 0 FAIL**（首跑 + 注入还原后复跑各一次，md5 `f951c479…` 前后相同） |
| 2 `--cases <主清单> --self-test` | rc=0，**9/9 PASS** |
| 3 主清单全量解析 | 272 例、唯一 272、`id == Path(image).stem` 不符 0、缺镜像 0、现场派生 272、首例 `ld.o_rrii_rd ← tests/inst/01-load-store/ld.o_rrii_rd.S` |
| 4 `make check-idl` | rc=0，`check_four_way: 272/272 例四方一致（…主清单 272 / pending 0 / 现场派生 272）`；另 `check-manifests-guard`、`check-dirs` rc=0 |
| 独立反例 C（脚本主键 `image`→`images`，非工程 A/B） | `run.sh` **rc=1、13 项 FAIL**；`cp`+md5 还原后复跑 rc=0 回绿 |
| 独立反例 D（旧别名键 `id`→`name`，非工程 A/B） | `run.sh` **rc=1、`legacy_id_alias` FAIL**；cp+md5 还原相等、复跑回绿 |
| 清单侧反例 5 路 | `images` 键 ⇒ rc=2 指名缺 `image`；镜像不存在 ⇒ rc=2 指名；`id`≠stem ⇒ 取 stem（`id` 仅别名）rc=0；TOML 语法错 ⇒ rc=2；`image` 非字符串 ⇒ rc=2 —— 均无 Traceback，且报清单错而非 `bootrom not found`（证 `load_cases` 前置） |
| 端到端 | `run_inst_tiny --id ld.o_rrii_rd` rc=0 → `idl_check_trace --cases <主清单> --only ld.o_rrii_rd` rc=0，`[PASS] ld.o_rrii_rd` |
| 越界 | `git status -uall` 仅脚本 + 任务书 2 文件；`idl/data/idl_exec_cases.toml` md5 `b6382ef8…` == HEAD（未改） |
| 遗留核实 | `build_sample` 的 `SystemExit(str)`（HEAD 同款、diff 未触碰其体）⇒ 既有行为，非本任务引入 |

findings（非阻断）：① `run.sh` 末行「注入 A/B 已还原」在注入窗口打印当次 `orig_md5`，措辞易误读（数字本身真实）；② `check_idl_count` 在清单解析失败时 expected 为空串（实测仍 FAIL，非恒真）。证据脚本逐项断言均有可达 FAIL（被 C/D 注入实测打红），无恒真、无两支同果。
另记：`make check-knowledge-refs` 本树 rc=2，3 处 `.work/**` 全在同批派发的 `m19-infra-001` 任务书（HEAD 即有、非本任务文件、本轮未触碰）⇒ 基线红，归 architect 收尾处置，不阻本任务。
**判决：Accepted**

