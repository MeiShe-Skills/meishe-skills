#!/usr/bin/env python3
"""Standalone quick validation for the native Android Meishe skill."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from validation.config_capabilities import validate_feature_capability_catalogs
from validation.native_android import (
    validate_native_android_beauty_resource_preflight,
    validate_native_android_complete,
    validate_native_android_unverified_cover_api,
    validate_native_android_unsupported_compile_sdk,
)
from validation.shared import run
from validation.skill_structure import validate_skill_structure


SKILL_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SCRIPTS = sorted((SKILL_ROOT / "scripts").rglob("*.py"))


def main() -> int:
    validate_skill_structure(
        route_module="native_android",
        capability_track="native-android",
        entry_script="integrate_native_android.py",
        docs_track="native",
        platforms=("android",),
        route_references=(
            "references/native-android.md",
            "references/native-android-feature-configuration.md",
            "references/native-android-troubleshooting.md",
            "references/aar-acquisition.md",
            "references/android-source-config-summary.md",
            "references/packages/native-android.md",
            "references/verified/native-android.md",
        ),
    )
    validate_feature_capability_catalogs()
    run(["-m", "py_compile", *[str(path) for path in PYTHON_SCRIPTS]], "Native Android py_compile")
    with tempfile.TemporaryDirectory(prefix="meishe_native_android_skill_validate_") as tmp:
        work = Path(tmp)
        validate_native_android_complete(work)
        validate_native_android_beauty_resource_preflight(work)
        validate_native_android_unverified_cover_api(work)
        validate_native_android_unsupported_compile_sdk(work)
    print("quick_validate passed: native-android")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"quick_validate failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
