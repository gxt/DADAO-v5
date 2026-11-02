#!/usr/bin/env python3
"""Run scalar tests and real mutations in temporary copies.

Exit 0 proves the listed checks detect their counterexamples; it does NOT mean
repository vector replay or whole-project L2 passed. Use --vectors to also run
the unmodified repository vectors, preserving their nonzero result.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(label, args, expected, logdir):
    result = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, timeout=180)
    (logdir / f'{label}.log').write_text(result.stdout + f'\nEXIT={result.returncode}\n')
    print(f'{label}: expected={expected} actual={result.returncode}', flush=True)
    if result.returncode != expected:
        print(result.stdout)
        raise RuntimeError(f'{label}: unexpected exit code')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vectors', action='store_true', help='also replay original vectors; propagate failures')
    args = parser.parse_args()
    logdir = ROOT / '.work/log/golden/GOLDEN-001t'
    logdir.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'components/golden'
    real_hashes = {p: digest(p) for p in source.glob('*.py')}
    command('evidence-unit', [PYTHON, '-B', '-m', 'unittest', 'discover',
                              '-s', 'components/golden', '-p', 'test_*v5.py', '-v'], 0, logdir)
    temporary = Path('/tmp/opencode/GOLDEN-001t')
    temporary.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='evidence-', dir=temporary) as directory:
        tree = Path(directory)
        shutil.copytree(source, tree / 'components/golden', ignore=shutil.ignore_patterns('__pycache__'))
        (tree / 'contracts').mkdir()
        shutil.copy2(ROOT / 'contracts/opcodes.yaml', tree / 'contracts/opcodes.yaml')
        shutil.copytree(ROOT / 'tests/inst/base', tree / 'tests/inst/base')
        model = tree / 'components/golden/dadao_interp_v5.py'
        original = model.read_bytes()
        original_digest = digest(model)
        # Change the real model's subtraction result. Independent arithmetic
        # tests must catch this, even if an example addition continues to pass.
        text = original.decode()
        needle = 'r = (a - b) & mask'
        if text.count(needle) != 1:
            raise RuntimeError('subtraction mutation target missing or ambiguous')
        model.write_text(text.replace(needle, 'r = (a + b) & mask'))
        if digest(model) == original_digest:
            raise RuntimeError('mutation did not change model')
        print('INJECT arithmetic subtraction->addition: content changed', flush=True)
        command('evidence-mutant-model', [PYTHON, '-B', str(tree / 'components/golden/test_interp_v5.py')], 1, logdir)
        model.write_bytes(original)
        if digest(model) != original_digest:
            raise RuntimeError('temporary model restoration failed')
        command('evidence-restored-model', [PYTHON, '-B', str(tree / 'components/golden/test_interp_v5.py')], 0, logdir)
        print('RESTORED temporary model: SHA256 identical', flush=True)

        # Test actual runner process exit codes for a good vector, then the
        # same vector with exactly one deliberately corrupted assertion.
        vector = dict(id='add.uo_rrrr_rd', mnemonic='add.uo', format='rrrr',
                      encoding={'word': '0x500420C4'}, **{'class': 'semantic'},
                      input_state={'rd': {'rd3': '0x3', 'rd4': '0x4'}},
                      expected_state={'rd': {'rd1': '0x0', 'rd2': '0x7'}},
                      expected_fault=None, expected_pc='0xFC0000000004',
                      status='active', spec_cite='SimRISC-04 §3.1')
        fixture = tree / 'assertions.yaml'
        runner = [PYTHON, '-B', str(tree / 'components/golden/validate_interp_v5.py'), str(fixture)]
        good = yaml.safe_dump([vector])
        fixture.write_text(good)
        command('evidence-vector-good', runner, 0, logdir)
        for label, mutate in (
                ('result', lambda v: v['expected_state']['rd'].__setitem__('rd2', '0x8')),
                ('identity', lambda v: v.__setitem__('id', 'add.so_rrrr_rd')),
                ('pc', lambda v: v.__setitem__('expected_pc', '0xFC0000000008')),
                ('fault', lambda v: v.__setitem__('expected_fault', 'ILLI'))):
            case = yaml.safe_load(good)[0]
            mutate(case)
            fixture.write_text(yaml.safe_dump([case]))
            if fixture.read_text() == good:
                raise RuntimeError(f'{label}: empty injection')
            command(f'evidence-mutant-{label}', runner, 1, logdir)
            fixture.write_text(good)
            command(f'evidence-restored-{label}', runner, 0, logdir)
        fixture.write_text('[]\n')
        command('evidence-empty-input', runner, 1, logdir)
    for path, before in real_hashes.items():
        if digest(path) != before:
            raise RuntimeError(f'real file changed during injection: {path}')
    print('REAL SOURCE SHA256 UNCHANGED', flush=True)
    print('MODEL TESTS AND COUNTEREXAMPLE CHECKS PASS (repository replay is separate)', flush=True)
    if args.vectors:
        result = subprocess.run([PYTHON, '-B', './components/golden/validate_interp_v5.py'], cwd=ROOT)
        print(f'REPOSITORY_REPLAY_EXIT={result.returncode}', flush=True)
        return result.returncode
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as ex:
        print(f'FAIL: {ex}', file=sys.stderr)
        sys.exit(1)
