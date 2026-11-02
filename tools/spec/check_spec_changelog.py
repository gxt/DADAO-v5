#!/usr/bin/env python3
"""文末「附录：版本与变更记录」结构性校验（SPEC-134t；SPEC-165t 收窄扫描面）。

**扫描面（SPEC-165t）**：SimRISC 系列的变更记录**只保留在 `SimRISC-00`**——01–12
只校验「**不得**有变更记录附录」+ 册头版本；DADAO / Toolchain / Machine 各册
（独立手册）仍逐册校验。

断言（任一不满足 ⇒ 非零退出）：
1. 受检册文末有 `## 附录：版本与变更记录`（二级、**不加章节号**），且为**最后一个** `##`
   标题（其下不允许再出现任何 `##`/`#`）；SimRISC-01–12 **不得**出现该附录；
2. 附录内的三级标题形态：顶部 = `### <X.Y.Z>-rc（未发布）`（若有未发布改动），
   其余 = `### <X.Y.Z>（<日期或说明>）`；
3. **逆序**：所有三级标题的版本号（去掉 `-rc` 后）自顶向下**严格递减**；`-rc` 段必须在
   首位，且其数值版本 = 下一个（首个非 `-rc` 段）版本 +1（z 位）；
4. **册头一致**：附录顶部段版本 == 册头版本（`> **版本：V**`；v5 自定册取「状态」行
   `生效（V，`）；册头若为 `-rc`，则附录顶部段须为同值 `-rc`；
5. **无表格**：附录段内不得含表格行（`|`）；
6. **不带任务号 / ADR 号**：附录段内不得出现 `SPEC-`/`QEMU-`/`LLVM-`/`INFRA-` 等任务号
   或 `ADR-`、`ISS-` 号；
7. **互锁组一致**：`SimRISC-00..12` 一组（比 **13 册册头版本**）、`AEE↔ABI`、
   `SEE↔SBI`、`HEE↔HBI`，组内版本必须一致。

所有计数**现场统计**（不写死）。
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LOCK = REPO / "manifests" / "spec-readonly.lock.toml"

APPENDIX_RE = re.compile(r"^##\s+附录：版本与变更记录\s*$")
H2_RE = re.compile(r"^##\s")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
# 版本段标题：`0.5.5-rc（未发布）` / `0.5.4（2026-09-28）` / `0.9.2（上游基线，日期不详）`
SEG_RE = re.compile(r"^(\d+(?:\.\d+){1,2})(-rc)?（(.+)）$")
HEADER_VER_RE = re.compile(r"^>\s*\*\*版本[：:]\s*(\d+(?:\.\d+){1,2}(?:-rc)?)")
HEADER_STATUS_VER_RE = re.compile(r"^>\s*\*\*状态\*\*[：:].*?（(\d+(?:\.\d+){1,2}(?:-rc)?)")

TASK_ID_RE = re.compile(r"\b(?:SPEC|QEMU|LLVM|INFRA|TESTCASES|INTEG|GOLDEN|GEM5|SAIL|DOCS|ADR|ISS)-\d+")
TABLE_ROW_RE = re.compile(r"^\s*\|")

# 互锁组（组内版本必须一致）。注意：锁文件的 `group`
# （`simrisc-00..12` / `dadao-1x` / `dadao-2x` …）与该语义分组的粒度不同，故按每册名显式归类。
_LOCK_GROUP_TO_INTERLOCK = {
    "simrisc-00..12": ["simrisc-00..12"],
    "dadao-1x": ["aee-abi", "see-sbi", "hee-hbi"],
    "dadao-2x": ["aee-abi", "see-sbi", "hee-hbi"],
    "toolchain-01": [],
    "machine-01": [],
}


def interlock_group(path: str):
    """按册名判定语义互锁组：SimRISC 一组；DADAO-{11,21} / {12,22} / {13,23} 各一组。"""
    if "SimRISC-" in path:
        return "simrisc-00..12"
    m = re.search(r"DADAO-(\d+)", path)
    if m:
        return {"11": "aee-abi", "21": "aee-abi",
                "12": "see-sbi", "22": "see-sbi",
                "13": "hee-hbi", "23": "hee-hbi"}.get(m.group(1))
    return None


INTERLOCK_GROUPS = ("simrisc-00..12", "aee-abi", "see-sbi", "hee-hbi")


def lock_entries():
    """Return [(path, group)] in lock-file order."""
    out = []
    lines = LOCK.read_text().splitlines()
    cur = {}
    for line in lines:
        m = re.match(r'path\s*=\s*"([^"]+)"', line)
        if m:
            cur = {"path": m.group(1)}
            continue
        m = re.match(r'group\s*=\s*"([^"]+)"', line)
        if m and cur:
            cur["group"] = m.group(1)
            out.append((cur["path"], cur["group"]))
            cur = {}
    return out


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def main():
    entries = lock_entries()
    errors = []
    stats = {"files": 0, "segments": 0, "rc_segments": 0, "bullets": 0}
    top_versions = {}     # group -> set（版本段顶部段版本）
    header_versions = {}  # group -> set（册头版本，SPEC-165t）

    for rel, group in entries:
        p = REPO / rel
        stats["files"] += 1
        lines = p.read_text(encoding="utf-8").splitlines()

        # ── 0. SimRISC-01..12：变更记录只保留在 SimRISC-00（SPEC-165t）──
        is_simrisc = "SimRISC-" in rel
        if is_simrisc and "SimRISC-00" not in rel:
            if any(APPENDIX_RE.match(l) for l in lines):
                errors.append(f"{rel}: 变更记录附录只允许出现在 SimRISC-00（本册须删除）")
            hver = None
            for l in lines:
                hm = HEADER_VER_RE.match(l) or HEADER_STATUS_VER_RE.match(l)
                if hm:
                    hver = hm.group(1)
                    break
            if hver is None:
                errors.append(f"{rel}: 未找到册头版本行（`> **版本：V**`）")
            else:
                header_versions.setdefault("simrisc-00..12", set()).add(hver)
            continue

        # ── 1. 附录标题存在且为最后一节 ──
        idxs = [i for i, l in enumerate(lines) if APPENDIX_RE.match(l)]
        if len(idxs) != 1:
            errors.append(f"{rel}: 未找到唯一的 `## 附录：版本与变更记录`（命中 {len(idxs)}）")
            continue
        ai = idxs[0]
        tail = lines[ai + 1:]
        for j, l in enumerate(tail, ai + 2):
            if H2_RE.match(l) or l.startswith("# "):
                errors.append(f"{rel}:L{j}: 附录段之后仍有 `##`/`#` 标题: {l[:60]}")
                break

        # ── 册头版本 ──
        header_ver = None
        for l in lines[:ai]:
            m = HEADER_VER_RE.match(l) or HEADER_STATUS_VER_RE.match(l)
            if m:
                header_ver = m.group(1)
                break

        # ── 2/3. 三级标题解析 + 逆序 ──
        segs = []  # (lineno, version_str, is_rc, date_text)
        for j, l in enumerate(tail, ai + 2):
            m = H3_RE.match(l)
            if not m:
                continue
            text = m.group(1)
            sm = SEG_RE.match(text)
            if not sm:
                errors.append(f"{rel}:L{j}: 版本段标题形态不符 `### <版本>（<日期>）`: {text[:60]}")
                continue
            segs.append((j, sm.group(1), bool(sm.group(2)), sm.group(3)))

        if not segs:
            errors.append(f"{rel}: 附录内无版本段（`###`）")
            continue
        stats["segments"] += len(segs)

        # `-rc` 只在首位
        for k, (j, v, isrc, _d) in enumerate(segs):
            if isrc and k != 0:
                errors.append(f"{rel}:L{j}: `-rc` 段出现在非首位（第 {k+1} 段）")
        if segs[0][2]:
            stats["rc_segments"] += 1
            # `-rc` 数值 = 下一段 +1（z 位）
            if len(segs) >= 2:
                rc = vtuple(segs[0][1])
                nx = vtuple(segs[1][1])
                if not (rc[0] == nx[0] and rc[1] == nx[1] and rc[2] == nx[2] + 1):
                    errors.append(
                        f"{rel}: `-rc` 段 {segs[0][1]} 不是下一段 {segs[1][1]} 的 z+1")

        # 严格递减（去 -rc）
        vers = [vtuple(v) for (_j, v, _r, _d) in segs]
        for k in range(1, len(vers)):
            if not (vers[k - 1] > vers[k]):
                errors.append(
                    f"{rel}: 版本段非严格逆序：{'.'.join(map(str,vers[k-1]))} → "
                    f"{'.'.join(map(str,vers[k]))}")

        # ── 4. 册头一致 ──
        top_v = segs[0][1]
        if header_ver is not None:
            hv = header_ver[:-3] if header_ver.endswith("-rc") else header_ver
            tv = top_v
            is_rc_hdr = header_ver.endswith("-rc")
            if hv != tv:
                errors.append(f"{rel}: 册头版本 {header_ver} 与附录顶部段 {top_v} 不一致")
            elif is_rc_hdr != segs[0][2]:
                errors.append(
                    f"{rel}: 册头 `-rc` 状态（{is_rc_hdr}）与附录顶部段 `-rc`（{segs[0][2]}）不一致")
        else:
            errors.append(f"{rel}: 未在附录之前找到册头版本行（`> **版本：V**` / 状态行）")

        grp = interlock_group(rel) or rel
        top_versions.setdefault(grp, set()).add(top_v)
        header_versions.setdefault(grp, set()).add(header_ver)

        # ── 5/6. 表格 / 任务号 ──
        for j, l in enumerate(tail, ai + 2):
            if TABLE_ROW_RE.match(l):
                errors.append(f"{rel}:L{j}: 附录段内出现表格行")
            for m in TASK_ID_RE.finditer(l):
                errors.append(f"{rel}:L{j}: 附录段内出现任务号/ADR/ISS 号: {m.group(0)}")

        # bullets 计数 + 段非空（每段 ≥1 条目；`- ` 归其**上方**最近的版本段）
        cur_name = None
        cur_bullets = 0
        seg_counts = []
        for j, l in enumerate(tail, ai + 2):
            m3 = H3_RE.match(l)
            if m3:
                if cur_name is not None:
                    seg_counts.append((cur_name, cur_bullets))
                cur_name = m3.group(1)
                cur_bullets = 0
                continue
            if l.startswith("- "):
                cur_bullets += 1
                stats["bullets"] += 1
        if cur_name is not None:
            seg_counts.append((cur_name, cur_bullets))
        for name, nb in seg_counts:
            if nb == 0:
                errors.append(f"{rel}: 版本段 `{name}` 无条目（每段须 ≥1 条）")

    # ── 7. 互锁组（SimRISC 组比 13 册册头版本；其余组比顶部段版本）──
    for g in INTERLOCK_GROUPS:
        vs = header_versions.get(g, set()) if g == "simrisc-00..12" \
            else top_versions.get(g, set())
        if len(vs) > 1:
            label = "册头版本" if g == "simrisc-00..12" else "顶部段版本"
            errors.append(f"互锁组 {g} 组内{label}不一致: {sorted(vs)}")

    print(f"files={stats['files']}  segments={stats['segments']}  "
          f"rc_segments={stats['rc_segments']}  bullets={stats['bullets']}  "
          f"simrisc_header_versions={sorted(header_versions.get('simrisc-00..12', set()))}")
    if errors:
        print(f"check-spec-changelog: FAIL ({len(errors)} violation(s))")
        for e in errors:
            print("  " + e)
        return 1
    print("check-spec-changelog: PASS（变更记录集中于 SimRISC-00；01–12 无附录；"
          "逆序/册头/无表格/无任务号/互锁一致）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
