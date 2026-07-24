"""iOS filesystem, CocoaPods, plist, and static-inspection support.

This module contains platform support only. Framework-specific iOS behavior lives
inside the matching route package.
"""

from __future__ import annotations

import plistlib
import re
from pathlib import Path

from meishe_docking_core import (
    SDK_COPY_SKIP_DIRS,
    Report,
    backup_path,
    read_text,
    rel,
    write_text,
)


def report_ios_signing_configuration(target_root: Path, report: Report) -> None:
    project_files = [
        path
        for path in target_root.rglob("project.pbxproj")
        if not any(part in SDK_COPY_SKIP_DIRS or part == "vendor" for part in path.parts)
    ]
    if not project_files:
        report.add_user_configuration(
            "iOS signing: no app `project.pbxproj` was available for static inspection. Select a user-confirmed Team/certificate in Xcode for first run and record it as temporary configuration."
        )
        return
    teams: set[str] = set()
    styles: set[str] = set()
    identities: set[str] = set()
    for project_file in project_files:
        text = read_text(project_file)
        teams.update(re.findall(r"\bDEVELOPMENT_TEAM\s*=\s*([^;\s]+)", text))
        styles.update(re.findall(r"\bCODE_SIGN_STYLE\s*=\s*([^;\s]+)", text))
        identities.update(re.findall(r'\bCODE_SIGN_IDENTITY\s*=\s*"?([^;\n"]+)', text))
    if teams:
        report.add_input(f"Detected iOS Development Team(s): `{', '.join(sorted(teams))}` (user-specific; verify before handoff).")
    else:
        report.add_user_configuration(
            "iOS signing: no Development Team is configured. For a newly created temporary project, select a Team already available to the user in Xcode, then record the Team ID as temporary bootstrap configuration."
        )
    if styles:
        report.add_input(f"Detected iOS signing style(s): `{', '.join(sorted(styles))}`.")
    if identities:
        report.add_input(f"Detected iOS signing identity setting(s): `{', '.join(sorted(identities))}` (certificate availability still requires Xcode verification).")







IOS_INFO_PLIST_PERMISSIONS = {
    "NSCameraUsageDescription": "App需要您的同意才能访问相机",
    "NSMicrophoneUsageDescription": "App需要您的同意才能访问麦克风",
    "NSPhotoLibraryUsageDescription": "App需要您的同意才能访问相册",
    "NSPhotoLibraryAddUsageDescription": "App需要您的同意才能保存视频或图片到相册",
    "NSAppleMusicUsageDescription": "App需要您的同意才能访问音乐",
    "NSLocalNetworkUsageDescription": "App需要您的同意才能访问本地网络",
    "NSLocationWhenInUseUsageDescription": "App需要您的同意才能在使用期间访问位置信息",
}

def ios_project_root(target_root: Path) -> Path | None:
    ios_root = target_root / "ios"
    if ios_root.exists():
        return ios_root
    if (target_root / "Podfile").exists() or any(target_root.glob("*.xcodeproj")):
        return target_root
    return None

def parse_ios_version(value: str | None) -> tuple[int, ...] | None:
    if not value:
        return None
    parts = value.strip().split(".")
    parsed: list[int] = []
    for part in parts:
        if not part.isdigit():
            return None
        parsed.append(int(part))
    return tuple(parsed)

def ios_version_less_than(current: str | None, required: str) -> bool:
    current_tuple = parse_ios_version(current)
    required_tuple = parse_ios_version(required)
    if current_tuple is None or required_tuple is None:
        return False
    size = max(len(current_tuple), len(required_tuple))
    current_tuple = current_tuple + (0,) * (size - len(current_tuple))
    required_tuple = required_tuple + (0,) * (size - len(required_tuple))
    return current_tuple < required_tuple

def read_podspec_deployment_target(podspec: Path) -> str | None:
    if not podspec.exists():
        return None
    text = read_text(podspec)
    match = re.search(r"\b(?:spec|s)\.ios\.deployment_target\s*=\s*['\"]([^'\"]+)['\"]", text)
    return match.group(1) if match else None

def resolve_ios_build_setting_path(value: str, ios_root: Path) -> Path | None:
    cleaned = value.strip().strip('"').strip("'")
    has_variable = "$(" in cleaned or "${" in cleaned
    has_supported_variable = any(
        token in cleaned
        for token in ("$(SRCROOT)", "${SRCROOT}", "$(PROJECT_DIR)", "${PROJECT_DIR}")
    )
    if not cleaned or (has_variable and not has_supported_variable):
        return None
    ios_root_text = ios_root.as_posix()
    cleaned = cleaned.replace("$(SRCROOT)", ios_root_text)
    cleaned = cleaned.replace("${SRCROOT}", ios_root_text)
    cleaned = cleaned.replace("$(PROJECT_DIR)", ios_root_text)
    cleaned = cleaned.replace("${PROJECT_DIR}", ios_root_text)
    path = Path(cleaned)
    if not path.is_absolute():
        path = ios_root / cleaned
    return path

def find_ios_app_info_plists(target_root: Path) -> list[Path]:
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        return []
    candidates: list[Path] = []
    for pbxproj in sorted(ios_root.glob("*.xcodeproj/project.pbxproj")):
        text = read_text(pbxproj)
        for match in re.finditer(r"INFOPLIST_FILE\s*=\s*([^;]+);", text):
            path = resolve_ios_build_setting_path(match.group(1), ios_root)
            if path and path.name == "Info.plist" and path.exists():
                candidates.append(path.resolve())
    if not candidates:
        for path in sorted(ios_root.glob("*/Info.plist")):
            if path.name == "Info.plist" and path.parent.name not in {"Flutter", "Pods"}:
                candidates.append(path.resolve())
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped

def patch_ios_app_info_plists(
    target_root: Path,
    report: Report,
    label: str,
    *,
    allow_arbitrary_loads: bool = False,
) -> None:
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        report.add_ios_quick_verify(f"{label}: iOS directory not found; skipped iOS static checks.")
        return
    plists = find_ios_app_info_plists(target_root)
    if not plists:
        message = f"{label}: iOS app Info.plist not found; add camera/microphone/photo/music/local-network permissions on Mac."
        report.add_ios_quick_verify(message)
        report.add_toolchain_warning(message)
        return
    for path in plists:
        try:
            with path.open("rb") as fh:
                data = plistlib.load(fh)
        except Exception as exc:
            message = f"{label}: could not parse `{rel(path, target_root)}` as plist ({exc}); update permissions manually on Mac."
            report.add_ios_quick_verify(message)
            report.add_warning(message)
            continue
        changed = False
        for key, value in IOS_INFO_PLIST_PERMISSIONS.items():
            if not data.get(key):
                data[key] = value
                changed = True
        if allow_arbitrary_loads:
            ats = data.setdefault("NSAppTransportSecurity", {})
            if not isinstance(ats, dict):
                ats = {}
                data["NSAppTransportSecurity"] = ats
            if ats.get("NSAllowsArbitraryLoads") is not True:
                ats["NSAllowsArbitraryLoads"] = True
                changed = True
        if changed:
            backup_path(path, target_root, report)
            if not report.dry_run:
                with path.open("wb") as fh:
                    plistlib.dump(data, fh, sort_keys=False)
            report.add_change(f"{label}: updated iOS privacy permissions: `{rel(path, target_root)}`")
            report.add_ios_quick_verify(f"{label}: app Info.plist privacy permissions and ATS patched: `{rel(path, target_root)}`")
        else:
            report.add_change(f"{label}: iOS privacy permissions already present: `{rel(path, target_root)}`")
            report.add_ios_quick_verify(f"{label}: app Info.plist privacy permissions and ATS already present: `{rel(path, target_root)}`")

def inspect_plugin_root(local_plugin: Path, source_plugin: Path | None, report: Report, label: str) -> Path:
    if local_plugin.exists():
        return local_plugin
    if source_plugin and source_plugin.exists():
        report.add_ios_quick_verify(
            f"{label}: inspecting source plugin because dry-run has not created `{rel(local_plugin, report.target_root)}` yet."
        )
        return source_plugin
    return local_plugin

def plugin_relative_exists(
    inspection_root: Path,
    local_plugin: Path,
    relative_path: str,
    target_root: Path,
    report: Report,
    label: str,
    description: str,
    *,
    is_dir: bool = False,
) -> bool:
    inspected = inspection_root / relative_path
    display = local_plugin / relative_path
    exists = inspected.is_dir() if is_dir else inspected.exists()
    if exists:
        report.add_ios_quick_verify(f"{label}: {description} found: `{rel(display, target_root)}`")
        return True
    message = f"{label}: {description} missing: `{rel(display, target_root)}`"
    report.add_ios_quick_verify(message)
    report.add_warning(message)
    return False

def plugin_relative_glob_exists(
    inspection_root: Path,
    local_plugin: Path,
    relative_glob_parent: str,
    pattern: str,
    target_root: Path,
    report: Report,
    label: str,
    description: str,
) -> bool:
    inspected_parent = inspection_root / relative_glob_parent
    matches = sorted(inspected_parent.glob(pattern)) if inspected_parent.exists() else []
    display = local_plugin / relative_glob_parent / pattern
    if matches:
        report.add_ios_quick_verify(f"{label}: {description} found: `{rel(display, target_root)}` ({len(matches)} match(es))")
        return True
    message = f"{label}: {description} missing: `{rel(display, target_root)}`"
    report.add_ios_quick_verify(message)
    report.add_warning(message)
    return False

def patch_ios_podfile_min_version(target_root: Path, report: Report, label: str, minimum_version: str) -> None:
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        return
    podfile = ios_root / "Podfile"
    if not podfile.exists():
        message = f"{label}: iOS Podfile not found; create/refresh the iOS project before running `pod install` on Mac."
        report.add_ios_quick_verify(message)
        report.add_vendor_warning(message)
        return
    text = read_text(podfile)
    explicit = re.search(r"(?m)^(\s*platform\s+:ios\s*,\s*)(['\"])(\d+(?:\.\d+){0,2})(['\"])(.*)$", text)
    if explicit:
        current = explicit.group(3)
        if ios_version_less_than(current, minimum_version):
            replacement = f"{explicit.group(1)}{explicit.group(2)}{minimum_version}{explicit.group(4)}{explicit.group(5)}"
            text = text[: explicit.start()] + replacement + text[explicit.end() :]
            write_text(podfile, text, target_root, report, f"{label}: raised iOS Podfile deployment target to {minimum_version}")
            report.add_ios_quick_verify(f"{label}: Podfile deployment target raised from {current} to {minimum_version}.")
        else:
            report.add_ios_quick_verify(f"{label}: Podfile deployment target {current} satisfies plugin minimum {minimum_version}.")
        return
    if re.search(r"(?m)^\s*platform\s+:ios\s*,", text):
        report.add_ios_quick_verify(
            f"{label}: Podfile uses a variable/expression for iOS deployment target; verify it is >= {minimum_version} on Mac."
        )
        return
    report.add_ios_quick_verify(f"{label}: Podfile has no explicit `platform :ios`; verify minimum {minimum_version} on Mac.")

def swift_method_branch_has_completion(text: str, method_constant: str) -> bool:
    marker = f"methodName == {method_constant}"
    start = text.find(marker)
    if start < 0:
        return False
    next_match = re.search(r"\n\s*\}\s*else\s+if\s+methodName\s*==", text[start + len(marker) :])
    end = start + len(marker) + next_match.start() if next_match else len(text)
    return "completion(" in text[start:end]
