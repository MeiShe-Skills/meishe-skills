"""Shared fixture I/O and integration process helpers."""

from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
import zipfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
PLATFORM_SCRIPTS = {
    "native-ios": SKILL_ROOT / "scripts" / "integrate_native_ios.py",
}
IOS_VALIDATION_MARKER = (
    "Manual runtime validation required: quick verify does not run dependency installation"
    if sys.platform == "darwin"
    else "Mac validation required: CocoaPods installation"
)


def has_xcode_26() -> bool:
    try:
        completed = subprocess.run(
            ["xcodebuild", "-version"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return completed.stdout.startswith("Xcode 26.")

def fail(message: str) -> None:
    raise AssertionError(message)

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)

def write_json(path: Path, data: object) -> None:
    write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")

def write_plist(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as fh:
        plistlib.dump(data, fh, sort_keys=False)

def assert_contains(text: str, needles: list[str], label: str) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        fail(f"{label} missing expected text: {missing}")

def assert_not_contains(text: str, needles: list[str], label: str) -> None:
    present = [needle for needle in needles if needle in text]
    if present:
        fail(f"{label} contains unexpected text: {present}")

def run(args: list[str], label: str) -> str:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=SKILL_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode != 0:
        tail = completed.stdout[-3000:]
        fail(f"{label} failed with exit code {completed.returncode}:\n{tail}")
    return completed.stdout

def run_failure(args: list[str], label: str) -> str:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=SKILL_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if completed.returncode == 0:
        fail(f"{label} unexpectedly succeeded:\n{completed.stdout[-3000:]}")
    return completed.stdout

def write_flutter_android_aar(path: Path, *, include_native_libraries: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("AndroidManifest.xml", "<manifest package=\"com.meishe.fixture\" />")
        if include_native_libraries:
            for entry in (
                "jni/arm64-v8a/libNvStreamingSdkCore.so",
                "jni/arm64-v8a/libNvMSAICutter.so",
                "jni/armeabi-v7a/libNvStreamingSdkCore.so",
                "jni/armeabi-v7a/libNvMSAICutter.so",
            ):
                archive.writestr(entry, f"fixture:{entry}".encode())


def create_ios_app(root: Path, app_name: str) -> None:
    write(
        root / "ios" / "Podfile",
        f"""platform :ios, '12.0'

target '{app_name}' do
end
""",
    )
    write_plist(root / "ios" / app_name / "Info.plist", {"CFBundleName": app_name})

def run_integration(target: Path, platform: str, plugin: Path, extra_args: list[str] | None = None) -> str:
    return run(
        [
            str(PLATFORM_SCRIPTS[platform]),
            "--target-root",
            str(target),
            "--plugin-path",
            str(plugin),
            *(extra_args or []),
            "--dry-run",
        ],
        f"{platform} dry-run",
    )

def run_integration_apply(target: Path, platform: str, plugin: Path, extra_args: list[str] | None = None) -> str:
    return run(
        [
            str(PLATFORM_SCRIPTS[platform]),
            "--target-root",
            str(target),
            "--plugin-path",
            str(plugin),
            *(extra_args or []),
        ],
        f"{platform} apply",
    )

def run_integration_failure(target: Path, platform: str, plugin: Path) -> str:
    return run_failure(
        [
            str(PLATFORM_SCRIPTS[platform]),
            "--target-root",
            str(target),
            "--plugin-path",
            str(plugin),
            "--dry-run",
        ],
        f"{platform} expected failure",
    )


def run_integration_apply_failure(
    target: Path,
    platform: str,
    plugin: Path,
    extra_args: list[str] | None = None,
) -> str:
    return run_failure(
        [
            str(PLATFORM_SCRIPTS[platform]),
            "--target-root",
            str(target),
            "--plugin-path",
            str(plugin),
            *(extra_args or []),
        ],
        f"{platform} expected apply failure",
    )
