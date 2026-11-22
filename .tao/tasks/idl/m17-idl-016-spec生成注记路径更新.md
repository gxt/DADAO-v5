# m17-idl-016: spec 生成注记路径更新（263 块）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-012`（生成器已迁 `idl/tools/idl_render.py`）
**可并行分片**：否
**预估**：30–60 min
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

`m17-idl-012` 把生成器从 `idl/render.py` 迁到 `idl/tools/idl_render.py`，但 21 册 `spec/SimRISC-*` 的 263 个生成块首行仍写「由 `idl/render.py` 生成」——该路径已不存在，成为坏指针。012 故意未重渲染（避免本任务外的大 diff），本任务收尾。

## 要做

1. `idl/tools/idl_render.py` 的生成注记改为**不含具体路径**的稳定写法（如「本块由 IDL 源生成，禁手改；生成器见 `idl/tools/`」），避免以后再改名又要全量重渲染;
2. 用该工具重渲染 21 册（只更新 263 个块的首行注记，块内容与散文逐字节不变）；
3. 更新 `spec/.manifests.toml` 中受影响的册 sha256（按现场重算）；
4. `spec/README.md` 等若有 `idl/render.py` 旧引用，一并改成新路径（或泛指 `idl/tools/`）；
5. **不升版本号**、不改语义/散文/.idl 源。

## 不做

- 不改任何 operation 正文、不新开 spec 版本段；
- 不改 `spec/` 之外的语义/清单。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动 `idl/tools/idl_render.py`、21 册 spec、`spec/.manifests.toml`、`spec/README.md`（如需）、本任务书；
- 完成区 ≤30 行、不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl-sync` rc=0（`idl-render: PASS … 263 块逐字节一致`）；
2. `make check-manifests-guard`、`check-spec-numbering`、`check-spec-changelog`、`check-spec-purity`、`check-spec-cite-targets` rc=0；
3. `grep -rn "idl/render\.py" spec/` 命中 **0**；
4. **diff 审计**：`git diff --numstat` 中每册增删行数 == 该册块数（只换注记行）+ sha 行；**块内容零变化**（可用 `idl_render.py --check` 前后对比或抽 3 册逐块比对）；
5. **可达 FAIL**：手改一个块的注记行 ⇒ `idl_render.py --check` rc≠0；`cp`+md5 还原后回绿。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
