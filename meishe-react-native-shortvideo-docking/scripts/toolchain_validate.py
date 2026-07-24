#!/usr/bin/env python3
"""Run optional React Native generated-code checks without installing dependencies."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(command: list[str], target_root: Path, label: str) -> None:
    completed = subprocess.run(command, cwd=target_root, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"{label} failed with exit code {completed.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-root", required=True)
    parser.add_argument(
        "--require-tools",
        action="store_true",
        help="Fail instead of skipping when project-local Jest/ESLint is unavailable.",
    )
    args = parser.parse_args()
    target_root = Path(args.target_root).expanduser().resolve()
    if not (target_root / "package.json").is_file():
        raise SystemExit(f"React Native package.json not found: {target_root}")

    commands: list[tuple[list[str], str]] = []
    jest = target_root / "node_modules" / ".bin" / "jest"
    test_files = sorted((target_root / "__tests__").glob("MeisheFeatureConfig-test.*"))
    if jest.is_file() and test_files:
        commands.append(([str(jest), str(test_files[0]), "--runInBand"], "React Native Jest"))
    eslint = target_root / "node_modules" / ".bin" / "eslint"
    lint_inputs = [
        path
        for path in (
            target_root / "src" / "meisheFeatureConfig.ts",
            target_root / "src" / "meisheFeatureConfig.js",
            *test_files,
        )
        if path.is_file()
    ]
    if eslint.is_file() and lint_inputs:
        commands.append(([str(eslint), *[str(path) for path in lint_inputs]], "React Native ESLint"))

    if not commands:
        message = (
            "toolchain_validate skipped: project-local Jest/ESLint inputs are unavailable; "
            "run the approved package installation first. No dependency was downloaded."
        )
        if args.require_tools:
            raise SystemExit(message)
        print(message)
        return 0
    for command, label in commands:
        run(command, target_root, label)
    print("toolchain_validate passed: react-native")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
