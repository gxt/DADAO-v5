#!/usr/bin/env python3
"""Reproduce GEM5-002t checks without rebuilding unchanged compiler inputs."""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]


def run(name, command, *, env=None, expect_failure=False):
    result = subprocess.run(command, cwd=ROOT, env=env, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            timeout=60)
    print(result.stdout, end="", flush=True)
    print(f"{name}: expected={'nonzero' if expect_failure else '0'} "
          f"actual={result.returncode}", flush=True)
    if (result.returncode == 0) == expect_failure:
        raise RuntimeError(f"{name}: unexpected exit code")
    return result.stdout.strip()


def require(name, condition):
    print(f"{name}: expected=PASS actual={'PASS' if condition else 'FAIL'}",
          flush=True)
    if not condition:
        raise RuntimeError(name)


def digest(paths):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inject", action="store_true",
                        help="check corrupt-patch rejection in a scratch index")
    args = parser.parse_args()
    manifest_path = ROOT / "manifests/components.lock.toml"
    manifest = tomllib.loads(manifest_path.read_text())
    matches = [c for c in manifest["component"] if c["name"] == "gem5"]
    require("component enabled exactly once",
            len(matches) == 1 and matches[0]["enabled"])
    component = matches[0]
    base = component["commit"]
    source = ROOT / manifest.get("work_root", ".work") / "source/gem5"
    mirror = ROOT / ".cache/gem5.git"
    series = ROOT / component["patch_series"]
    entries = [s.strip() for s in series.read_text().splitlines()
               if s.strip() and not s.lstrip().startswith("#")]
    patches = [ROOT / component["patch_dir"] / s for s in entries]
    require("nonempty sorted unique series",
            bool(entries) and entries == sorted(set(entries)))
    files = [manifest_path, series, *patches]
    before = digest(files)
    status_before = run("source snapshot",
                        ["git", "-C", str(source), "status", "--porcelain"])
    require("source clean", not status_before)
    tag = run("release tag", ["git", "-C", str(mirror), "rev-parse",
                             f"refs/tags/{component['shallow_ref']}^{{commit}}"])
    require("tag equals manifest SHA", tag == base)
    count = run("base+1", ["git", "-C", str(source), "rev-list",
                          "--count", f"{base}..HEAD"])
    require("exactly one customization commit", count == "1")
    shallow = run("shallow mirror", ["git", "-C", str(mirror), "rev-parse",
                                    "--is-shallow-repository"])
    require("shallow checkout policy", not component.get("shallow") or
            shallow == "true")
    scratch_root = Path("/tmp/opencode/GEM5-002t")
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch_root) as directory:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(directory) / "index"))
        git = ["git", "-C", str(source)]

        def replay(paths):
            run("read locked base", git + ["read-tree", base], env=env)
            run("apply complete series", git + ["apply", "--cached",
                *map(str, paths)], env=env)
            tree = run("replayed tree", git + ["write-tree"], env=env)
            expected = run("source HEAD tree",
                           git + ["rev-parse", "HEAD^{tree}"])
            require("patch replay equals source", tree == expected)
            for patch in paths:
                text = patch.read_text()
                require(f"hunk/blob {patch.name}",
                        text.count("diff --git ") == 1 and "\n@@ " in text
                        and "\nindex " in text)

        replay(patches)
        if args.inject:
            damaged = Path(directory) / "corrupt.patch"
            # Remove the entire diff; git also accepts leading junk and some
            # malformed new-file hunks, so those are not reliable injections.
            damaged.write_text("corrupted: no valid diff remains\n")
            require("injection changed bytes",
                    damaged.read_bytes() != patches[0].read_bytes())
            run("reset scratch index", git + ["read-tree", base], env=env)
            run("corrupt patch rejected",
                git + ["apply", "--cached", str(damaged)], env=env,
                expect_failure=True)
            replay(patches)
    # Actual idempotent component entry point: the verified base+1 path skips.
    run("apply idempotence", ["python3", "./tools/gem5/apply_series.py"])
    binary = source / "build/NULL/gem5.opt"
    require("upstream NULL binary exists", binary.is_file())
    info = run("upstream runtime build info", [str(binary), "--build-info"])
    require("runtime release version", "25.1.0.1" in info)
    run("upstream runtime help", [str(binary), "--help"])
    status_after = run("source final snapshot",
                       ["git", "-C", str(source), "status", "--porcelain"])
    require("source snapshot unchanged", status_after == status_before)
    require("all input SHA256 unchanged", digest(files) == before)
    print(f"GEM5-002t baseline: PASS ({len(patches)} patches); "
          "repository-wide closure gates must be checked separately")


if __name__ == "__main__":
    main()
