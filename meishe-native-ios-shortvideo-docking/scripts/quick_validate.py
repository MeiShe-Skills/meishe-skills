#!/usr/bin/env python3
"""Standalone quick validation for the native iOS Meishe skill."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from validation.config_capabilities import validate_feature_capability_catalogs
from validation.native_ios import (
    validate_native_ios_complete,
    validate_native_ios_customer_identity,
    validate_native_ios_explicit_bundle_identifier,
    validate_native_ios_missing_package,
    validate_native_ios_project_identity_and_podfile_scoping,
    validate_native_ios_unknown_autocut_draft_api,
    validate_native_ios_xcode26_patch,
)
from validation.shared import run
from validation.skill_structure import validate_skill_structure


SKILL_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SCRIPTS = sorted((SKILL_ROOT / "scripts").rglob("*.py"))


def main() -> int:
    validate_skill_structure(
        route_module="native_ios",
        capability_track="native-ios",
        entry_script="integrate_native_ios.py",
        docs_track="native",
        platforms=("ios",),
        route_references=(
            "references/native-ios.md",
            "references/native-ios-feature-configuration.md",
            "references/native-ios-troubleshooting.md",
            "references/packages/native-ios.md",
            "references/verified/native-ios.md",
        ),
    )
    validate_feature_capability_catalogs()
    run(["-m", "py_compile", *[str(path) for path in PYTHON_SCRIPTS]], "Native iOS py_compile")
    with tempfile.TemporaryDirectory(prefix="meishe_native_ios_skill_validate_") as tmp:
        work = Path(tmp)
        validate_native_ios_complete(work)
        validate_native_ios_project_identity_and_podfile_scoping(work)
        validate_native_ios_xcode26_patch(work)
        validate_native_ios_unknown_autocut_draft_api(work)
        validate_native_ios_customer_identity(work)
        validate_native_ios_explicit_bundle_identifier(work)
        validate_native_ios_missing_package(work)
    print("quick_validate passed: native-ios")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"quick_validate failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
