"""Run the public submission checks and preserve their actual outputs and exit codes.

Run in src/: python -m lab9.verify_submission [--full]
The full mode rebuilds evaluation reports, mutation scorecard and A/A evidence.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys

from lab8.console import utf8_stdio


def main() -> int:
    utf8_stdio()
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    out = Path("reports")
    out.mkdir(exist_ok=True)
    steps = [
        ("lab9.smoke", [], 0),
        ("lab9.evalset", ["--check"], 0),
        ("lab9.evalset", ["--v2"], 0),
        ("pytest", ["-q", "-m", "student", "-o", "addopts=", "-k", "lab9"], 0),
        ("pytest", ["-q", "tests/test_lab9_evalset.py", "-o", "addopts=", "--basetemp", "reports/pytest-tmp"], 0),
        ("lab9.evidence", [], 0),
        ("lab9.judge", ["--csv", "data/eval/judge_tone_public.csv", "--audit", "5"], 0),
        ("lab9.judge", ["--csv", "data/eval/judge_helpful_public.csv", "--audit", "5"], 1),
    ]
    if args.full:
        for shape, target, spec in [
            ("swarm", "baseline_v1.json", "config/metric_spec.yaml"),
            ("fixed", "eval_fixed.json", "config/metric_spec.yaml"),
            ("seeded_regression", "eval_seeded_regression.json", "config/metric_spec.yaml"),
            ("swarm", "baseline_v2.json", "config/metric_spec_v2.yaml"),
            ("slice_regression", "eval_slice_regression.json", "config/metric_spec_v2.yaml"),
        ]:
            steps.append(("lab9.eval", ["--shape", shape, "--out", f"reports/{target}", "--spec", spec], 0))
    for shape, expected in (("swarm", 0), ("fixed", 0), ("seeded_regression", 1)):
        report = "baseline_v1" if shape == "swarm" else f"eval_{shape}"
        steps.append(("lab9.gate", ["--pr", f"reports/{report}.json", "--baseline", "reports/baseline_v1.json"], expected))
    steps += [
        ("lab9.ci_check", ["--pr", "reports/baseline_v1.json", "--baseline", "reports/baseline_v1.json"], 0),
        ("lab9.traps", ["--pr", "reports/eval_slice_regression.json", "--baseline", "reports/baseline_v2.json", "--spec", "config/metric_spec_v2.yaml"], 0),
    ]
    for trap in ("evaluator_errors_as_nan", "dropped_failing_rows", "cherry_picked_seeds", "loosened_spec"):
        trap_spec = f"reports/traps/{trap}.spec.yaml" if trap == "loosened_spec" else "config/metric_spec_v2.yaml"
        argv = ["--pr", f"reports/traps/{trap}.json", "--baseline", "reports/baseline_v2.json", "--spec", trap_spec]
        if trap == "loosened_spec":
            argv += ["--base-spec", "config/metric_spec_v2.yaml"]
        steps.append(("lab9.gate", argv, 1))
    if args.full:
        steps += [
            ("lab9.mutation", ["--detect"], 0),
            ("lab9.mutation", ["--spec", "config/metric_spec_v2.yaml", "--baseline", "reports/baseline_v2.json"], 0),
            ("lab9.mutation", ["--spec", "config/metric_spec_v2.yaml", "--aa", "66,77,88,99,110"], 0),
        ]
    env = dict(os.environ, PYTHONUTF8="1")
    failures = 0
    with (out / "validation.log").open("w", encoding="utf-8") as log:
        for module, argv, expected in steps:
            command = [sys.executable, "-m", module, *argv]
            heading = f"python -m {module} {' '.join(argv)}\n"
            print(heading, end="", flush=True)
            log.write(heading)
            log.flush()
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", env=env)
            output = result.stdout + result.stderr
            print(output, end="", flush=True)
            log.write(output)
            verdict = f"exit={result.returncode}, expected={expected}\n"
            print(verdict, flush=True)
            log.write(verdict)
            log.flush()
            failures += result.returncode != expected
        summary = f"verification: {len(steps) - failures}/{len(steps)} checks matched expected exit codes\n"
        print(summary)
        log.write(summary)
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
