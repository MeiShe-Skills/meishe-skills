"""Native iOS CocoaPods package resolution and Podfile patching."""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass
from pathlib import Path

from meishe_docking_core import (
    BEGIN,
    END,
    IntegrationError,
    Report,
    find_valid_plugin_folder,
    read_text,
    write_text,
)

from .constants import IOS_NATIVE_PACKAGE_HELP


@dataclass(frozen=True)
class IosProjectContext:
    project_path: Path
    target_name: str
    workspace_path: Path
    scheme_name: str | None


def pbx_section(text: str, name: str) -> str:
    match = re.search(
        rf"/\* Begin {re.escape(name)} section \*/(?P<body>.*?)/\* End {re.escape(name)} section \*/",
        text,
        re.S,
    )
    return match.group("body") if match else ""


def pbx_native_app_targets(project_path: Path) -> dict[str, str]:
    project_file = project_path / "project.pbxproj"
    if not project_file.exists():
        return {}
    section = pbx_section(read_text(project_file), "PBXNativeTarget")
    targets: dict[str, str] = {}
    for match in re.finditer(
        r"(?P<id>[A-Fa-f0-9]{8,})\s+/\*.*?\*/\s*=\s*\{(?P<body>.*?)^\s*\};",
        section,
        re.M | re.S,
    ):
        body = match.group("body")
        if not re.search(
            r'productType\s*=\s*"?com\.apple\.product-type\.application"?\s*;',
            body,
        ):
            continue
        name_match = re.search(r"(?m)^\s*name\s*=\s*\"?([^\";]+)\"?\s*;", body)
        if name_match:
            targets[name_match.group(1).strip()] = match.group("id")
    return targets


def podfile_target_names(target_root: Path) -> set[str]:
    podfile = target_root / "Podfile"
    if not podfile.exists():
        return set()
    return {
        match.group(1)
        for match in re.finditer(r"(?m)^\s*target\s+['\"]([^'\"]+)['\"]\s+do", read_text(podfile))
    }


def shared_scheme_targets(target_root: Path) -> dict[str, set[str]]:
    schemes: dict[str, set[str]] = {}
    for path in sorted(
        candidate
        for candidate in target_root.rglob("*.xcscheme")
        if "xcshareddata" in candidate.parts
        and "vendor" not in candidate.parts
        and "Pods" not in candidate.parts
    ):
        targets = {
            value.strip()
            for value in re.findall(r'BlueprintName\s*=\s*"([^"]+)"', read_text(path))
            if value.strip()
        }
        if path.stem:
            targets.add(path.stem)
        schemes[path.stem] = targets
    return schemes


def _unique_candidate(candidates: set[str], source: str) -> str | None:
    if len(candidates) == 1:
        return next(iter(candidates))
    if len(candidates) > 1:
        choices = ", ".join(f"`{value}`" for value in sorted(candidates))
        raise IntegrationError(
            f"Could not uniquely infer the native iOS app target from {source}. "
            f"Candidates: {choices}. Pass --ios-target <exact Xcode app target>."
        )
    return None


def resolve_ios_project_context(target_root: Path, args: argparse.Namespace) -> IosProjectContext:
    projects = sorted(target_root.glob("*.xcodeproj"))
    if not projects:
        raise IntegrationError("No root-level native iOS `.xcodeproj` was found.")

    targets_by_project = {project: pbx_native_app_targets(project) for project in projects}
    app_targets = {
        target_name
        for project_targets in targets_by_project.values()
        for target_name in project_targets
    }
    requested_target = getattr(args, "ios_target", None)
    if requested_target:
        if app_targets and requested_target not in app_targets:
            choices = ", ".join(f"`{value}`" for value in sorted(app_targets))
            raise IntegrationError(
                f"--ios-target `{requested_target}` is not an application target in the Xcode project. "
                f"Detected app targets: {choices}."
            )
        target_name = requested_target
    else:
        if len(app_targets) == 1:
            target_name = next(iter(app_targets))
        elif len(app_targets) > 1:
            pod_matches = app_targets & podfile_target_names(target_root)
            candidates = pod_matches or app_targets
            scheme_matches = {
                candidate
                for scheme_targets in shared_scheme_targets(target_root).values()
                for candidate in scheme_targets
                if candidate in candidates
            }
            if len(scheme_matches) == 1:
                target_name = next(iter(scheme_matches))
            elif len(candidates) == 1:
                target_name = next(iter(candidates))
            else:
                choices = ", ".join(f"`{value}`" for value in sorted(app_targets))
                raise IntegrationError(
                    "Multiple native iOS application targets were detected without a unique Podfile or "
                    f"shared-scheme match: {choices}. Pass --ios-target <exact Xcode app target>."
                )
        else:
            target_name = _unique_candidate(
                podfile_target_names(target_root),
                "root Podfile target declarations",
            )
        if target_name is None:
            raise IntegrationError(
                "Could not infer the native iOS app target from PBXNativeTarget or Podfile declarations. "
                "Pass --ios-target <exact Xcode app target>."
            )

    matching_projects = [
        project for project, project_targets in targets_by_project.items() if target_name in project_targets
    ]
    if len(matching_projects) == 1:
        project_path = matching_projects[0]
    elif not matching_projects and len(projects) == 1:
        project_path = projects[0]
    else:
        choices = ", ".join(f"`{project.name}`" for project in matching_projects or projects)
        raise IntegrationError(
            f"Could not uniquely map iOS target `{target_name}` to an Xcode project. Candidates: {choices}."
        )

    workspaces = sorted(
        path for path in target_root.glob("*.xcworkspace") if path.name != "Pods.xcworkspace"
    )
    preferred_workspace = target_root / f"{project_path.stem}.xcworkspace"
    if preferred_workspace in workspaces:
        workspace_path = preferred_workspace
    elif len(workspaces) == 1:
        workspace_path = workspaces[0]
    elif len(workspaces) > 1:
        choices = ", ".join(f"`{path.name}`" for path in workspaces)
        raise IntegrationError(
            f"Could not uniquely map target `{target_name}` to an Xcode workspace. Candidates: {choices}."
        )
    else:
        workspace_path = preferred_workspace

    matching_schemes = [
        scheme_name
        for scheme_name, scheme_targets in shared_scheme_targets(target_root).items()
        if target_name in scheme_targets
    ]
    scheme_name = _unique_candidate(set(matching_schemes), f"shared schemes for target `{target_name}`")
    return IosProjectContext(
        project_path=project_path,
        target_name=target_name,
        workspace_path=workspace_path,
        scheme_name=scheme_name,
    )

def resolve_ios_pods_package(plugin_path: str | None) -> Path:
    if not plugin_path:
        raise IntegrationError(IOS_NATIVE_PACKAGE_HELP)
    return find_valid_plugin_folder(Path(plugin_path), "Pods-NvShortVideoEdit", IOS_NATIVE_PACKAGE_HELP, validate_ios_pods_package)

def validate_ios_pods_package(plugin: Path) -> None:
    if not (plugin / "NvShortVideoEdit.podspec").exists():
        raise IntegrationError(
            "Invalid native iOS package. Expected `Pods-NvShortVideoEdit/NvShortVideoEdit.podspec` "
            f"under `{plugin}`."
        )

def ruby_block(block: str) -> str:
    return f"# {BEGIN}\n{block.rstrip()}\n# {END}"

def insert_or_replace_ruby_block(text: str, block: str) -> str:
    begin = f"# {BEGIN}"
    end = f"# {END}"
    wrapped = ruby_block(block)
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if pattern.search(text):
        return pattern.sub(wrapped, text)
    return text.rstrip() + "\n\n" + wrapped + "\n"

def patch_ios_podfile(target_root: Path, pods_package: Path, ios_target: str, report: Report) -> None:
    podfile = target_root / "Podfile"
    rel_pod_path = os.path.relpath(pods_package.resolve(), target_root.resolve()).replace("\\", "/")
    if not rel_pod_path.startswith("."):
        rel_pod_path = "./" + rel_pod_path
    pod_line = (
        f"  pod 'NvShortVideoEdit',    :path => '{rel_pod_path}', "
        ":inhibit_warnings => true"
    )
    block = f"""target '{ios_target}' do
{pod_line}
end"""
    if podfile.exists():
        text = read_text(podfile)
        if "platform :ios" not in text:
            text = "platform :ios, '12.0'\n" + text
        if "use_frameworks!" not in text:
            text = re.sub(r"(?m)^platform :ios, .*$", lambda m: m.group(0) + "\nuse_frameworks!", text, count=1)
        if "NvShortVideoEdit" in text:
            text = re.sub(
                r"(?m)^\s*pod\s+['\"]NvShortVideoEdit['\"].*$",
                pod_line,
                text,
            )
        elif re.search(rf"target\s+['\"]{re.escape(ios_target)}['\"]\s+do\s*\n", text):
            text = re.sub(
                rf"(target\s+['\"]{re.escape(ios_target)}['\"]\s+do\s*\n)",
                rf"\1{pod_line}\n",
                text,
                count=1,
            )
        else:
            text = insert_or_replace_ruby_block(text, block)
    else:
        text = f"""platform :ios, '12.0'
use_frameworks!

{ruby_block(block)}
"""
    write_text(podfile, text, target_root, report, "Updated native iOS Podfile for NvShortVideoEdit")
