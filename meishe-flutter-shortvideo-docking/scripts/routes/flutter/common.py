"""Framework-level Flutter integration steps shared by its target platforms."""

from __future__ import annotations

from argparse import Namespace
import json
import re
from pathlib import Path

from meishe_docking_core import (
    DEMO_ICON_FILES,
    IntegrationError,
    Report,
    TargetPlatforms,
    assert_no_external_dependency_refs,
    copy_demo_banner,
    copy_demo_icons,
    copy_file,
    copy_sdk_package_to_vendor,
    replace_external_source_path_refs,
    read_text,
    write_server_handoff,
    write_text,
)
from platform_support.framework_plugin import place_plugin_license
from platform_support.ios import ios_project_root

from . import implementation


DEMO_BANNER_FILE = "meishe_home_banner.jpg"
WATERMARK_FILE = "meishe_feature_watermark.png"


def validate_target(target_root: Path) -> None:
    pubspec = target_root / "pubspec.yaml"
    if not pubspec.exists():
        raise IntegrationError("Flutter target must contain pubspec.yaml.")
    if not re.search(r"(?m)^\s+sdk:\s*flutter\s*$", read_text(pubspec)):
        raise IntegrationError(
            "Flutter target pubspec.yaml must declare the Flutter SDK dependency (`sdk: flutter`)."
        )


def ensure_flutter_pubspec_asset(target_root: Path, report: Report) -> None:
    path = target_root / "pubspec.yaml"
    text = read_text(path)
    asset_lines = [
        "    - assets/meishe_home_banner.jpg",
        *(f"    - assets/{filename}" for filename in DEMO_ICON_FILES.values()),
        f"    - assets/{WATERMARK_FILE}",
    ]
    missing_asset_lines = [line for line in asset_lines if line not in text]
    if not missing_asset_lines:
        report.add_change("Flutter pubspec.yaml already declares the demo home banner and function icon assets.")
        return
    asset_block = "\n".join(missing_asset_lines)
    if re.search(r"(?m)^flutter:\s*$", text):
        if re.search(r"(?m)^flutter:\s*\n(?:[ \t]+[^\n]*\n)*?[ \t]{2}assets:\s*$", text):
            text = re.sub(
                r"(?m)^([ \t]{2}assets:\s*)$",
                r"\1\n" + asset_block,
                text,
                count=1,
            )
        else:
            text = re.sub(
                r"(?m)^flutter:\s*$",
                "flutter:\n  assets:\n" + asset_block,
                text,
                count=1,
            )
    else:
        text = text.rstrip() + "\n\nflutter:\n  assets:\n" + asset_block + "\n"
    write_text(path, text, target_root, report, "Declared Flutter demo home banner and function icon assets")

def copy_flutter_demo_banner(target_root: Path, report: Report) -> None:
    copy_demo_banner(
        target_root / "assets" / DEMO_BANNER_FILE,
        target_root,
        report,
        "Copied demo home banner for Flutter",
    )
    ensure_flutter_pubspec_asset(target_root, report)

def copy_flutter_demo_icons(target_root: Path, report: Report) -> None:
    copy_demo_icons(
        target_root / "assets",
        target_root,
        report,
        "Copied demo function icon for Flutter",
    )
    ensure_flutter_pubspec_asset(target_root, report)


def copy_flutter_watermark_assets(
    target_root: Path,
    targets: TargetPlatforms,
    report: Report,
) -> None:
    source = Path(__file__).resolve().parents[3] / "assets" / "demo-ui" / "icons" / "meishe_icon_edit.png"
    copy_file(source, target_root / "assets" / WATERMARK_FILE, target_root, report, "Copied Flutter watermark asset")
    ensure_flutter_pubspec_asset(target_root, report)
    if targets.android:
        copy_file(
            source,
            target_root / "android" / "app" / "src" / "main" / "res" / "drawable-nodpi" / WATERMARK_FILE,
            target_root,
            report,
            "Copied Flutter Android drawable watermark asset",
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
            copy_file(source, imageset / WATERMARK_FILE, target_root, report, "Copied Flutter iOS Asset Catalog watermark")
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
            write_text(imageset / "Contents.json", contents, target_root, report, "Generated Flutter iOS watermark Asset Catalog metadata")
            if not catalogs:
                report.add_next_check(
                    "Flutter iOS watermark: Xcode had no existing Assets.xcassets. Add `ios/MeisheFeatureAssets.xcassets` to Runner before enabling watermark configuration."
                )


def resolve_source(args: Namespace, target_root: Path, targets: TargetPlatforms) -> Path:
    return implementation.resolve_flutter_plugin(args.plugin_path, target_root, targets)


def prepare(
    args: Namespace,
    target_root: Path,
    source_plugin: Path,
    targets: TargetPlatforms,
    report: Report,
) -> Path:
    plugin = copy_sdk_package_to_vendor(
        target_root,
        source_plugin,
        "nvshortvideo",
        report,
        "Flutter",
        validator=lambda path: implementation.validate_flutter_plugin_package(path, targets),
    )
    report.add_input(
        "Flutter plugin: the selected official `nvshortvideo` package is used for every Flutter target platform present."
    )
    implementation.patch_pubspec(target_root, plugin, report)
    replace_external_source_path_refs(
        target_root,
        source_plugin,
        plugin,
        [target_root / "pubspec.lock", target_root / ".flutter-plugins-dependencies"],
        report,
        "Flutter",
    )
    place_plugin_license(plugin, args, target_root, report, targets, source_plugin)
    return plugin


def finish(target_root: Path, source_plugin: Path, plugin: Path, report: Report) -> None:
    copy_flutter_demo_banner(target_root, report)
    copy_flutter_demo_icons(target_root, report)
    copy_flutter_watermark_assets(target_root, TargetPlatforms.detect(target_root, "Flutter"), report)
    implementation.generate_flutter_wrapper(target_root, report)
    implementation.generate_flutter_demo(target_root, report)
    report.add_user_configuration(
        "Server entry: edit `lib/meishe_short_video_docking.dart` -> `defaultServerConfig`; follow the Flutter route's server configuration section before replacing demo values."
    )
    write_server_handoff(
        target_root,
        "flutter",
        "lib/meishe_short_video_docking.dart -> MeisheShortVideoDocking.defaultServerConfig",
        "官方 Flutter 共享配置使用 `https://creative.meishesdk.com/api/app` 基础地址；Android bridge 直接消费基础地址，iOS bridge 按官方契约处理端点。不要为了统一字符串而改成原生 iOS 完整路径。",
        "官方 Demo 服务仅用于已登记的 `com.meishe.duanshipindemo` 应用身份；Android applicationId 和 iOS Bundle Identifier 可分别配置，但都必须与服务白名单及 License 匹配。",
        "iOS 客户服务确实使用 HTTP 时，只添加真实域名的最小 ATS 例外；Android 则使用最小 Network Security Config。官方 Demo 身份临时启用的宽松策略不得带入正式项目。",
        report,
    )
    report.add_next_check(
        "Flutter AutoCut: manually verify edit album, template page, and capture template entry; the generated result must enter the standard editor, then Next must reach save-draft/export publishing."
    )
    report.add_next_check(
        "Flutter generated-code check: run `flutter analyze lib`; review `vendor/meishe` warnings separately as third-party SDK output."
    )
    assert_no_external_dependency_refs(target_root, source_plugin, "Flutter", report)


def update_flutter_readme(
    target_root: Path,
    targets: TargetPlatforms,
    android_package_name: str | None,
    ios_bundle_identifier: str | None,
    report: Report,
) -> None:
    readme = target_root / "README.md"
    existing = read_text(readme) if readme.exists() else f"# {target_root.name}\n"
    begin = "<!-- BEGIN MEISHE_FLUTTER_RUN_GUIDE -->"
    end = "<!-- END MEISHE_FLUTTER_RUN_GUIDE -->"
    root = target_root.resolve()
    guide_label = "dual-platform" if targets.android and targets.ios else ("Android" if targets.android else "iOS")
    if targets.android and targets.ios:
        real_device_note = (
            "真机要求：必须连接真实 Android/iOS 设备；Android Emulator、iOS Simulator "
            "和其他虚拟设备不受支持，不能用于运行或验收。"
        )
    elif targets.android:
        real_device_note = (
            "真机要求：必须连接真实 Android 设备；Android Emulator 和其他虚拟设备"
            "不受支持，不能用于运行或验收。"
        )
    else:
        real_device_note = (
            "真机要求：必须连接真实 iPhone 或 iPad；iOS Simulator 和其他虚拟设备"
            "不受支持，不能用于运行或验收。"
        )
    lines = [
        begin,
        "## 美摄短视频 Demo 运行",
        "",
        f"- 项目根目录：`{root}`",
        f"- **{real_device_note}**",
    ]
    if targets.android:
        lines.append(
            f"- Android applicationId：`{android_package_name or '保持项目现有值（见 Android app build.gradle）'}`"
        )
    if targets.ios:
        lines.append(
            f"- iOS Bundle Identifier：`{ios_bundle_identifier or '保持项目现有值（见 Xcode app target）'}`"
        )
    lines.extend(
        [
        "- 美摄 Flutter 插件：`vendor/meishe/nvshortvideo`",
        "",
        "### 依赖安装",
        "",
        "首次运行或依赖声明变化后，先按 `meishe_docking_report.md` 的审批流程执行：",
        "",
        ]
    )
    for step in report.dependency_steps:
        if not step.label.startswith("Flutter"):
            continue
        lines.extend(
            [
                f"- `{step.label}`",
                "",
                "```sh",
                f"cd {step.working_directory}",
                step.command,
                "```",
                "",
            ]
        )
    if targets.android:
        lines.extend(
            [
                "### Android",
                "",
                "```sh",
                f"cd {root}",
                "flutter run -d <ANDROID_DEVICE_ID>",
                "```",
                "",
                f"Android Studio 可打开 `{root / 'android'}`，完成 Gradle Sync 后选择 `app` 和目标设备，再点击 Run。",
                "",
            ]
        )
    if targets.ios:
        ios_root = root / "ios"
        workspaces = sorted(ios_root.glob("*.xcworkspace"))
        if workspaces:
            workspace = workspaces[0]
        else:
            projects = sorted(ios_root.glob("*.xcodeproj"))
            workspace = ios_root / f"{projects[0].stem if projects else 'Runner'}.xcworkspace"
        lines.extend(
            [
                "### iOS",
                "",
                "**推荐运行方式：Xcode**",
                "",
                "CocoaPods 完成后执行：",
                "",
                "```sh",
                f"open \"{workspace}\"",
                "```",
                "",
                "在 Xcode 中选择 App scheme、用户自己的签名 Team 和真实 iPhone/iPad，执行 `Product > Run`。必须打开 `.xcworkspace`，不要打开 `.xcodeproj`。",
                "",
                "**命令行运行方式（必须同时提供）**",
                "",
                "```sh",
                f"cd {root}",
                "flutter run -d <IOS_DEVICE_ID>",
                "```",
                "",
            ]
        )
    lines.extend(report.configuration_handoff_markdown(heading_level=3).splitlines())
    lines.append("")
    lines.extend(
        [
            "### 遇到报错",
            "",
            "- 受操作系统、Flutter/Dart、Ruby/CocoaPods、JDK/Gradle、Xcode、网络、签名和设备环境差异影响，手动接入或运行可能报错。",
            "- 遇到任何报错，请复制执行命令和完整原始报错信息发给当前 Agent 继续处理；不要只截取最后一行，也不需要自行猜测修复。",
            "",
            "### 美摄配置边界",
            "",
            "- 官方 Demo 服务验证保持 `com.meishe.duanshipindemo`；客户包名需要客户服务器、正式 License 和签名配置。",
            "- 服务配置入口：`lib/meishe_short_video_docking.dart` 中的 `defaultServerConfig`。",
            "- 静态构建不替代真机功能验收；需要真机时选择“用户执行”或“自动执行”，自动执行会额外消耗 Token 和时间。",
            end,
        ]
    )
    block = "\n".join(lines)
    if begin in existing and end in existing:
        updated = re.sub(
            rf"{re.escape(begin)}.*?{re.escape(end)}",
            block,
            existing,
            flags=re.S,
        )
    else:
        updated = existing.rstrip() + "\n\n" + block + "\n"
    write_text(readme, updated, target_root, report, f"Generated Flutter {guide_label} run guide in README")
