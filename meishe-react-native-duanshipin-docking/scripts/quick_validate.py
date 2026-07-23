#!/usr/bin/env python3
"""Standalone quick validation for the React Native Meishe skill."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from validation.config_capabilities import validate_feature_capability_catalogs
from validation.react_native import (
    validate_react_native_android_only,
    validate_react_native_complete,
    validate_react_native_conflicting_lockfiles,
    validate_react_native_custom_identity_rejects_demo_license,
    validate_react_native_ios_only,
    validate_react_native_missing_android_beauty_resources,
    validate_react_native_missing_android_native_libraries,
    validate_react_native_missing_ios,
    validate_react_native_missing_targets,
    validate_react_native_platform_identities,
    validate_react_native_optional_toolchain,
    validate_react_native_ruby4_cocoapods_compatibility,
    validate_react_native_unverified_android_publish_shape,
    validate_react_native_unverified_ios_autocut_draft_shape,
    validate_react_native_unverified_version,
)
from validation.shared import run
from validation.skill_structure import validate_skill_structure


SKILL_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SCRIPTS = sorted((SKILL_ROOT / "scripts").rglob("*.py"))


def main() -> int:
    validate_skill_structure(
        route_module="react_native",
        capability_track="react-native",
        entry_script="integrate_react_native.py",
        docs_track="react-native",
        platforms=("android", "ios"),
        route_references=(
            "references/react-native.md",
            "references/react-native/common.md",
            "references/react-native/feature-configuration.md",
            "references/react-native/android.md",
            "references/react-native/ios.md",
            "references/react-native/android-troubleshooting.md",
            "references/react-native/ios-troubleshooting.md",
            "references/packages/react-native.md",
            "references/verified/react-native.md",
        ),
    )
    validate_feature_capability_catalogs()
    run(["-m", "py_compile", *[str(path) for path in PYTHON_SCRIPTS]], "React Native py_compile")
    with tempfile.TemporaryDirectory(prefix="meishe_rn_skill_validate_") as tmp:
        work = Path(tmp)
        validate_react_native_complete(work)
        validate_react_native_ruby4_cocoapods_compatibility(work)
        validate_react_native_conflicting_lockfiles(work)
        validate_react_native_android_only(work)
        validate_react_native_custom_identity_rejects_demo_license(work)
        validate_react_native_ios_only(work)
        validate_react_native_platform_identities(work)
        validate_react_native_optional_toolchain(work)
        validate_react_native_missing_targets(work)
        validate_react_native_missing_ios(work)
        validate_react_native_missing_android_beauty_resources(work)
        validate_react_native_missing_android_native_libraries(work)
        validate_react_native_unverified_version(work)
        validate_react_native_unverified_android_publish_shape(work)
        validate_react_native_unverified_ios_autocut_draft_shape(work)
    print("quick_validate passed: react-native")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"quick_validate failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
