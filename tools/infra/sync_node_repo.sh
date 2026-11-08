#!/usr/bin/env bash
# sync_node_repo.sh — 把主控机当前 master 同步到构建节点，并把节点工作树恢复干净。
#
# 背景（用户 2026-11-09）：「server207 中的仓库已经非常乱了……建议每次远程任务之后
# 都同步一次仓库」。节点只承担构建/运行/调试，**所有仓库修改在主控机**；节点工作树
# 出现改动或未跟踪文件，说明同步方式（rsync 文件 / 手动 checkout）没有更新 git 状态。
#
# 做法：git bundle（只含 master）+ ssh fetch + reset --hard + clean -fd。
#   - `.work/`、`.cache/` 是 gitignore，`clean -fd` 不会删（不加 -x）。
#   - 节点上若有本地改动，会先打印清单再丢弃（符合「节点不承担仓库修改」）。
#
# 用法:
#   tools/infra/sync_node_repo.sh                 # 用 $DADAO_NODES
#   tools/infra/sync_node_repo.sh gxt@host1,gxt@host2
#   REPO=~/DADAO-v5 tools/infra/sync_node_repo.sh # 节点仓库路径（默认 ~/DADAO-v5）
#
# 退出码: 0 = 全部节点 HEAD 与主控机一致且工作树干净；非零 = 任一节点失败。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

HOSTS="${1:-${DADAO_NODES:-}}"
REMOTE_REPO="${REPO:-}"
BUNDLE_DIR="$ROOT/.work/node-sync"
BUNDLE="$BUNDLE_DIR/DADAO-v5-master.bundle"

if [ -z "$HOSTS" ]; then
    echo "sync-node-repo: ERROR: 没有节点清单；传参数或用 DADAO_NODES" >&2
    exit 2
fi

mkdir -p "$BUNDLE_DIR"
LOCAL_HEAD="$(git rev-parse master)"
echo "sync-node-repo: local master = $LOCAL_HEAD"
git bundle create "$BUNDLE" master >/dev/null
echo "sync-node-repo: bundle = $BUNDLE ($(du -h "$BUNDLE" | cut -f1))"

fail=0
IFS=',' read -ra ARR <<< "$HOSTS"
for host in "${ARR[@]}"; do
    host="${host// /}"
    [ -n "$host" ] || continue
    echo "---- $host"
    scp -q "$BUNDLE" "$host:DADAO-v5-master.bundle"
    if ! ssh -o BatchMode=yes "$host" "REMOTE_REPO='$REMOTE_REPO' WANT='$LOCAL_HEAD' bash -s" <<'EOF'
set -euo pipefail
target="${REMOTE_REPO:-$HOME/DADAO-v5}"
cd "$target"
dirty="$(git status --porcelain -uall | wc -l)"
if [ "$dirty" -ne 0 ]; then
    echo "  [warn] 节点工作树不干净（$dirty 项），将被 reset+clean 丢弃："
    git status --porcelain -uall | head -10 | sed 's/^/    /'
fi
git fetch ~/DADAO-v5-master.bundle master >/dev/null 2>&1
git reset --hard FETCH_HEAD >/dev/null
git clean -fd >/dev/null
node_head="$(git rev-parse HEAD)"
left="$(git status --porcelain -uall | wc -l)"
echo "  head=$node_head dirty=$left"
[ "$left" -eq 0 ] || { echo "  [fail] 清理后仍不干净" >&2; exit 1; }
[ "$node_head" = "$WANT" ] || { echo "  [fail] HEAD 与主控机不一致（want $WANT）" >&2; exit 1; }
EOF
    then
        echo "  [fail] $host"
        fail=1
        continue
    fi
done

if [ "$fail" -ne 0 ]; then
    echo "sync-node-repo: FAIL（至少一个节点失败）" >&2
    exit 1
fi
echo "sync-node-repo: PASS（全部节点 = $LOCAL_HEAD 且工作树干净）"
