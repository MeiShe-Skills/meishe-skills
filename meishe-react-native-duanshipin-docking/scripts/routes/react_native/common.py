"""Framework-level React Native steps shared by its target platforms."""

from __future__ import annotations

from argparse import Namespace
import json
import re
from pathlib import Path

from meishe_docking_core import (
    IntegrationError,
    LICENSE_HELP,
    Report,
    TargetPlatforms,
    assert_no_external_dependency_refs,
    copy_demo_banner,
    copy_demo_icons,
    copy_file,
    copy_sdk_package_to_vendor,
    find_project_plugin_folder,
    find_valid_plugin_folder,
    read_text,
    rel,
    write_server_handoff,
    write_text,
)
from platform_support.ios import ios_project_root

from . import implementation
from .constants import REACT_NATIVE_PACKAGE_HELP, REACT_NATIVE_PLUGIN_NAME


DEMO_BANNER_FILE = "meishe_home_banner.jpg"
OFFICIAL_DEMO_APPLICATION_ID = "com.meishe.duanshipindemo"
WATERMARK_FILE = "meishe_feature_watermark.png"


def copy_react_native_demo_banner(target_root: Path, report: Report) -> None:
    copy_demo_banner(
        target_root / "src" / "assets" / DEMO_BANNER_FILE,
        target_root,
        report,
        "Copied demo home banner for React Native",
    )

def copy_react_native_demo_icons(target_root: Path, report: Report) -> None:
    copy_demo_icons(
        target_root / "src" / "assets",
        target_root,
        report,
        "Copied demo function icon for React Native",
    )


def copy_react_native_watermark_assets(
    target_root: Path,
    targets: TargetPlatforms,
    report: Report,
) -> None:
    source = Path(__file__).resolve().parents[3] / "assets" / "demo-ui" / "icons" / "meishe_icon_edit.png"
    copy_file(
        source,
        target_root / "src" / "assets" / WATERMARK_FILE,
        target_root,
        report,
        "Copied React Native feature watermark source asset",
    )
    if targets.android:
        copy_file(
            source,
            target_root / "android" / "app" / "src" / "main" / "res" / "drawable-nodpi" / WATERMARK_FILE,
            target_root,
            report,
            "Copied React Native Android drawable watermark asset",
        )
    if targets.ios:
        ios_root = ios_project_root(target_root)
        if ios_root:
            catalogs = sorted(
                path
                for path in ios_root.rglob("Assets.xcassets")
                if not any(part in {"Pods", "vendor", ".meishe_docking_backup"} for part in path.parts)
            )
            catalog = catalogs[0] if catalogs else ios_root / "MeisheFeatureAssets.xcassets"
            imageset = catalog / "meishe_feature_watermark.imageset"
            copy_file(
                source,
                imageset / WATERMARK_FILE,
                target_root,
                report,
                "Copied React Native iOS Asset Catalog watermark",
            )
            contents = json.dumps(
                {
                    "images": [
                        {"filename": WATERMARK_FILE, "idiom": "universal", "scale": "1x"},
                        {"idiom": "universal", "scale": "2x"},
                        {"idiom": "universal", "scale": "3x"},
                    ],
                    "info": {"author": "xcode", "version": 1},
                },
                ensure_ascii=True,
                indent=2,
            ) + "\n"
            write_text(imageset / "Contents.json", contents, target_root, report, "Generated React Native iOS watermark Asset Catalog metadata")
            if not catalogs:
                report.add_next_check(
                    "React Native iOS watermark: Xcode had no existing Assets.xcassets. Add `ios/MeisheFeatureAssets.xcassets` to the app target before enabling watermark configuration."
                )


def resolve_react_native_plugin(
    plugin_path: str | None,
    target_root: Path,
    targets: TargetPlatforms,
) -> Path:
    validator = lambda path: validate_react_native_plugin_package(path, targets)
    if not plugin_path:
        return find_project_plugin_folder(target_root, "react-native-nvshortvideo", REACT_NATIVE_PACKAGE_HELP, validator)
    return find_valid_plugin_folder(Path(plugin_path), "react-native-nvshortvideo", REACT_NATIVE_PACKAGE_HELP, validator)

def validate_react_native_plugin_package(plugin: Path, targets: TargetPlatforms | None = None) -> None:
    package_json = plugin / "package.json"
    android_dir = plugin / "android"
    if not package_json.exists():
        raise IntegrationError(
            "Invalid React Native plugin package. `react-native-nvshortvideo` is required and "
            f"`{plugin}` does not contain package.json."
        )
    try:
        data = json.loads(read_text(package_json).lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        raise IntegrationError(f"Invalid package.json in React Native plugin package: {package_json}") from exc
    package_name = str(data.get("name", ""))
    if "react-native-nvshortvideo" not in package_name and plugin.name != "react-native-nvshortvideo":
        raise IntegrationError(
            "Invalid React Native plugin package. Expected package name/path to be "
            f"`react-native-nvshortvideo`, got `{package_name or plugin.name}`."
        )
    if (targets is None or targets.android) and not android_dir.exists():
        raise IntegrationError(
            "Invalid React Native plugin package. The real `react-native-nvshortvideo` package "
            f"must contain an Android plugin directory at `{android_dir}`."
        )


def resolve_source(args: Namespace, target_root: Path, targets: TargetPlatforms) -> Path:
    return resolve_react_native_plugin(args.plugin_path, target_root, targets)


def read_android_application_id(target_root: Path) -> str | None:
    for gradle in (
        target_root / "android" / "app" / "build.gradle",
        target_root / "android" / "app" / "build.gradle.kts",
    ):
        if not gradle.exists():
            continue
        match = re.search(
            r'applicationId\s*(?:=\s*)?["\']([^"\']+)["\']',
            read_text(gradle),
        )
        if match:
            return match.group(1)
    return None


def find_official_demo_android_license(args: Namespace, source_plugin: Path) -> Path | None:
    supplied = Path(args.plugin_path).resolve() if args.plugin_path else source_plugin.resolve()
    search_root = supplied if supplied.is_dir() else supplied.parent
    matches = []
    for candidate in search_root.rglob("meishesdk.lic"):
        normalized = candidate.as_posix()
        if normalized.endswith("/android/app/src/main/assets/meishesdk.lic"):
            matches.append(candidate)
    if len(matches) > 1:
        raise IntegrationError(
            "The supplied React Native package contains multiple Android Demo licenses. "
            "Pass the intended matching file explicitly with `--license-path`."
        )
    return matches[0] if matches else None


def place_react_native_license(
    plugin: Path,
    source_plugin: Path,
    args: Namespace,
    target_root: Path,
    targets: TargetPlatforms,
    report: Report,
) -> None:
    android_app_license = target_root / "android" / "app" / "src" / "main" / "assets" / "meishesdk.lic"
    ios_plugin_license = plugin / "ios" / "Assets" / "meishesdk.lic"
    destinations = []
    if targets.android:
        destinations.append(android_app_license)
    if targets.ios and (source_plugin / "ios").is_dir():
        destinations.append(ios_plugin_license)

    if args.license_path:
        source = Path(args.license_path)
        report.add_input(f"License: `{source}`")
        for destination in destinations:
            copy_file(source, destination, target_root, report, "Copied matching React Native Meishe license")
        if not destinations:
            report.add_warning("The selected React Native targets expose no valid License destination.")
        return

    retained = [destination for destination in destinations if destination.exists()]
    for destination in retained:
        report.add_input(f"Existing license retained: `{destination}`")
        report.add_change(f"Retained existing Meishe license: `{rel(destination, target_root)}`")

    requested_android_package = args.android_package_name or args.package_name
    application_id = (
        requested_android_package or read_android_application_id(target_root)
        if targets.android
        else None
    )
    auto_placed_android = False
    if targets.android and android_app_license not in retained:
        if application_id == OFFICIAL_DEMO_APPLICATION_ID:
            demo_license = find_official_demo_android_license(args, source_plugin)
            if demo_license:
                copy_file(
                    demo_license,
                    android_app_license,
                    target_root,
                    report,
                    "Copied official RN Android Demo license into final app assets",
                )
                report.add_input(
                    "RN Android Demo License auto-placement matched the official applicationId and the explicitly supplied official package."
                )
                auto_placed_android = True
            else:
                report.add_warning(
                    "The final RN Android applicationId is `com.meishe.duanshipindemo`, but the explicitly supplied official package does not contain an Example app License at `android/app/src/main/assets/meishesdk.lic`."
                )
        else:
            report.add_warning(
                f"RN Android applicationId `{application_id or 'unknown'}` is not the official Demo identity. "
                "The skill did not reuse an official Demo License; provide a License matching the final applicationId with `--license-path`."
            )

    available_count = len(retained) + (1 if auto_placed_android else 0)
    if available_count < len(destinations):
        report.add_warning(LICENSE_HELP)
    report.add_user_configuration(
        "Production license: register the final applicationId/Bundle Identifier with Meishe and re-run with its matching `meishesdk.lic` via `--license-path`. RN Android packages the file from `android/app/src/main/assets/meishesdk.lic`."
    )


def prepare(
    args: Namespace,
    target_root: Path,
    source_plugin: Path,
    targets: TargetPlatforms,
    report: Report,
) -> Path:
    implementation.patch_react_native_app_identity(
        target_root,
        args.android_package_name or args.package_name,
        args.ios_bundle_identifier or args.package_name,
        report,
    )
    plugin = copy_sdk_package_to_vendor(
        target_root,
        source_plugin,
        REACT_NATIVE_PLUGIN_NAME,
        report,
        "React Native",
        validator=lambda path: validate_react_native_plugin_package(path, targets),
    )
    report.add_input(
        "React Native plugin: the selected official `react-native-nvshortvideo` package is used for every RN target platform present."
    )
    place_react_native_license(plugin, source_plugin, args, target_root, targets, report)
    return plugin


def configure_project(target_root: Path, plugin: Path, source_plugin: Path, report: Report) -> None:
    implementation.install_react_native_plugin_dependency(target_root, plugin, source_plugin, report)
    implementation.isolate_react_native_tooling(target_root, report)
    implementation.configure_react_native_jest(target_root, report)


def finish(target_root: Path, source_plugin: Path, plugin: Path, report: Report) -> None:
    copy_react_native_demo_banner(target_root, report)
    copy_react_native_demo_icons(target_root, report)
    copy_react_native_watermark_assets(target_root, TargetPlatforms.detect(target_root, "React Native"), report)
    suffix = implementation.generate_react_native_wrapper(target_root, report)
    implementation.generate_react_native_demo(target_root, suffix, report)
    report.add_user_configuration(
        f"Server entry: edit `src/meisheShortVideoDocking.{suffix}` -> `meisheServerConfig`; follow the React Native route's server configuration section before replacing demo values."
    )
    write_server_handoff(
        target_root,
        "react-native",
        f"src/meisheShortVideoDocking.{suffix} -> meisheServerConfig",
        "官方 React Native 共享配置使用 `https://creative.meishesdk.com/api/app` 基础地址；Android bridge 直接消费基础地址，iOS bridge 按官方契约补齐端点。不要为了统一字符串而改成原生 iOS 完整路径。",
        "官方 Demo 服务仅用于已登记的 `com.meishe.duanshipindemo` 应用身份；Android applicationId 和 iOS Bundle Identifier 可分别配置，但都必须与服务白名单及 License 匹配。",
        "iOS 客户服务确实使用 HTTP 时，只添加真实域名的最小 ATS 例外；Android 则使用最小 Network Security Config。官方 Demo 身份临时启用的宽松策略不得带入正式项目。",
        report,
    )
    report.add_next_check(
        "React Native AutoCut: manually verify edit album, template page, and capture template entry; the generated result must enter the standard editor, then Next must reach save-draft/export publishing."
    )
    assert_no_external_dependency_refs(target_root, source_plugin, "React Native", report)
