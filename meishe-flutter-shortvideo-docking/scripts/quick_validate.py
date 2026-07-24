#!/usr/bin/env python3
"""Standalone quick validation for the Flutter Meishe skill."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from validation.config_capabilities import validate_feature_capability_catalogs
from validation.flutter import (
    validate_external_path_detection,
    validate_flutter_android_only,
    validate_flutter_complete,
    validate_flutter_ios_only,
    validate_flutter_missing_android_beauty_resources,
    validate_flutter_missing_android_native_libraries,
    validate_flutter_missing_ios,
    validate_flutter_missing_targets,
    validate_flutter_platform_identities,
    validate_flutter_optional_toolchain,
    validate_flutter_renamed_ios_target,
    validate_flutter_sdk_atomic_replace,
    validate_flutter_unverified_android_publish_shape,
    validate_flutter_unverified_ios_autocut_draft_shape,
)
from validation.shared import run
from validation.skill_structure import validate_skill_structure


SKILL_ROOT = Path(__file__).resolve().parents[1]
PYTHON_SCRIPTS = sorted((SKILL_ROOT / "scripts").rglob("*.py"))


def main() -> int:
    validate_skill_structure(
        route_module="flutter",
        capability_track="flutter",
        entry_script="integrate_flutter.py",
        docs_track="flutter",
        platforms=("android", "ios"),
        route_references=(
            "references/flutter.md",
            "references/flutter/common.md",
            "references/flutter/feature-configuration.md",
            "references/flutter/android.md",
            "references/flutter/ios.md",
            "references/flutter/android-troubleshooting.md",
            "references/flutter/ios-troubleshooting.md",
            "references/packages/flutter.md",
            "references/verified/flutter.md",
        ),
    )
    validate_feature_capability_catalogs()
    run(["-m", "py_compile", *[str(path) for path in PYTHON_SCRIPTS]], "Flutter py_compile")
    with tempfile.TemporaryDirectory(prefix="meishe_flutter_skill_validate_") as tmp:
        work = Path(tmp)
        validate_flutter_complete(work)
        validate_flutter_android_only(work)
        validate_flutter_ios_only(work)
        validate_flutter_renamed_ios_target(work)
        validate_flutter_platform_identities(work)
        validate_flutter_optional_toolchain(work)
        validate_flutter_missing_targets(work)
        validate_flutter_missing_ios(work)
        validate_flutter_missing_android_beauty_resources(work)
        validate_flutter_missing_android_native_libraries(work)
        validate_flutter_sdk_atomic_replace(work)
        validate_flutter_unverified_android_publish_shape(work)
        validate_flutter_unverified_ios_autocut_draft_shape(work)
        validate_external_path_detection(work)
    print("quick_validate passed: flutter")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"quick_validate failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
