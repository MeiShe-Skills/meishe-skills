#!/usr/bin/env python3
"""Run optional Flutter generated-code checks without installing dependencies."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def run(command: list[str], target_root: Path, label: str) -> None:
    completed = subprocess.run(command, cwd=target_root, check=False)
    if completed.returncode != 0:
        raise SystemExit(f"{label} failed with exit code {completed.returncode}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-root", required=True)
    parser.add_argument("--flutter-bin", help="Explicit Flutter executable path.")
    parser.add_argument(
        "--require-tools",
        action="store_true",
        help="Fail instead of skipping when Flutter or resolved project dependencies are unavailable.",
    )
    args = parser.parse_args()
    target_root = Path(args.target_root).expanduser().resolve()
    if not (target_root / "pubspec.yaml").is_file():
        raise SystemExit(f"Flutter pubspec.yaml not found: {target_root}")
    flutter = args.flutter_bin or shutil.which("flutter")
    package_config = target_root / ".dart_tool" / "package_config.json"
    if not flutter or not package_config.is_file():
        message = (
            "toolchain_validate skipped: Flutter or `.dart_tool/package_config.json` is unavailable; "
            "run the approved `flutter pub get` first. No dependency was downloaded."
        )
        if args.require_tools:
            raise SystemExit(message)
        print(message)
        return 0

    analyze_inputs = ["lib"]
    if (target_root / "test").is_dir():
        analyze_inputs.append("test")
    run([flutter, "analyze", *analyze_inputs], target_root, "Flutter analyze")
    if (target_root / "test").is_dir():
        run([flutter, "test"], target_root, "Flutter test")
    print("toolchain_validate passed: flutter")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
