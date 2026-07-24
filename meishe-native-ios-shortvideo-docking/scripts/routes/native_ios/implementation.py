"""Native iOS implementation for Meishe ShortVideo integration."""

from __future__ import annotations

import argparse
import os
import plistlib
import re
import subprocess
from pathlib import Path

from meishe_docking_core import (
    ConfigurationApplyStep,
    IntegrationError,
    LICENSE_HELP,
    SDK_COPY_SKIP_DIRS,
    Report,
    add_cocoapods_dependency_step,
    assert_no_external_dependency_refs,
    copy_demo_banner,
    copy_demo_icons,
    copy_file,
    copy_sdk_package_to_vendor,
    project_local_path,
    read_text,
    replace_external_source_path_refs,
    write_server_handoff,
    write_text,
)
from platform_support.ios import (
    ios_project_root,
    patch_ios_app_info_plists,
    report_ios_signing_configuration,
)
from .constants import DEMO_BANNER_FILE, IOS_NATIVE_SCOPE_NOTE
from .support import (
    IosProjectContext,
    patch_ios_podfile,
    pbx_section,
    resolve_ios_pods_package,
    resolve_ios_project_context,
    validate_ios_pods_package,
)


OFFICIAL_DEMO_BUNDLE_IDENTIFIER = "com.meishe.duanshipindemo"
AUTOCUT_DRAFT_API_MARKERS = (
    "projectInfoForProject:",
    "storeCurrentProjectWithProjectId:",
)
AUTOCUT_DRAFT_SWIFT_API_MARKERS = (
    "NvTimelineDataManager",
    "newProject(localFilePaths:",
    "NvProEditConfig",
    "managerAvailable",
    "destroySharedInstance",
)


def app_target_build_configuration_ids(
    project_context: IosProjectContext,
    project_text: str,
) -> list[str]:
    target_section = pbx_section(project_text, "PBXNativeTarget")
    target_match = next(
        (
            match
            for match in re.finditer(
                r"(?P<id>[A-Fa-f0-9]{8,})\s+/\*.*?\*/\s*=\s*\{(?P<body>.*?)^\s*\};",
                target_section,
                re.M | re.S,
            )
            if re.search(
                rf"(?m)^\s*name\s*=\s*\"?{re.escape(project_context.target_name)}\"?\s*;",
                match.group("body"),
            )
            and re.search(
                r'productType\s*=\s*"?com\.apple\.product-type\.application"?\s*;',
                match.group("body"),
            )
        ),
        None,
    )
    config_list_match = (
        re.search(
            r"buildConfigurationList\s*=\s*([A-Fa-f0-9]{8,})",
            target_match.group("body"),
        )
        if target_match
        else None
    )
    if not config_list_match:
        return []
    list_section = pbx_section(project_text, "XCConfigurationList")
    list_match = re.search(
        rf"{re.escape(config_list_match.group(1))}\s+/\*.*?\*/\s*=\s*\{{(?P<body>.*?)^\s*\}};",
        list_section,
        re.M | re.S,
    )
    if not list_match:
        return []
    configurations = re.search(
        r"buildConfigurations\s*=\s*\((?P<body>.*?)\);",
        list_match.group("body"),
        re.S,
    )
    if not configurations:
        return []
    return re.findall(r"([A-Fa-f0-9]{8,})\s+/\*", configurations.group("body"))


def xcode_build_configuration_pattern(config_id: str) -> re.Pattern[str]:
    return re.compile(
        rf"(?P<prefix>^[ \t]*{re.escape(config_id)}\s+/\*.*?\*/\s*=\s*\{{.*?"
        r"buildSettings\s*=\s*\{)(?P<body>.*?)(?P<suffix>^[ \t]*\};\s*"
        r"(?:\n[ \t]*name\s*=.*?;)?\s*\n[ \t]*\};)",
        re.M | re.S,
    )


def configure_native_ios_bundle_identifier(
    target_root: Path,
    project_context: IosProjectContext,
    requested_bundle_identifier: str | None,
    report: Report,
) -> str | None:
    project_file = project_context.project_path / "project.pbxproj"
    text = read_text(project_file)
    config_ids = app_target_build_configuration_ids(project_context, text)
    if not config_ids:
        raise IntegrationError(
            f"Could not map build configurations for native iOS app target "
            f"`{project_context.target_name}`. Bundle Identifier detection stopped before integration."
        )

    config_section = pbx_section(text, "XCBuildConfiguration")
    identity_pattern = re.compile(
        r"(?m)^(?P<indent>[ \t]*)PRODUCT_BUNDLE_IDENTIFIER\s*=\s*\"?(?P<value>[^\";]+)\"?;"
    )
    identities: set[str] = set()
    config_matches: list[tuple[str, re.Match[str]]] = []
    for config_id in config_ids:
        config_match = xcode_build_configuration_pattern(config_id).search(config_section)
        if not config_match:
            raise IntegrationError(
                f"Could not inspect build configuration `{config_id}` for native iOS app target "
                f"`{project_context.target_name}`. No project files were changed."
            )
        identity_match = identity_pattern.search(config_match.group("body"))
        if not identity_match:
            raise IntegrationError(
                f"Build configuration `{config_id}` for native iOS app target "
                f"`{project_context.target_name}` has no explicit PRODUCT_BUNDLE_IDENTIFIER. "
                "Set it in Xcode or pass --ios-bundle-identifier after normalizing the project."
            )
        identities.add(identity_match.group("value").strip())
        config_matches.append((config_id, config_match))

    if requested_bundle_identifier:
        if not re.fullmatch(
            r"[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+",
            requested_bundle_identifier,
        ):
            raise IntegrationError(
                f"Invalid --ios-bundle-identifier `{requested_bundle_identifier}`. "
                "Use a reverse-DNS identifier such as `com.meishe.duanshipindemo`."
            )
        patched_section = config_section
        patched_count = 0
        for config_id in config_ids:
            config_match = xcode_build_configuration_pattern(config_id).search(patched_section)
            if not config_match:
                raise IntegrationError(
                    f"Could not safely update build configuration `{config_id}` for app target "
                    f"`{project_context.target_name}`. No test or extension target was modified."
                )
            body = config_match.group("body")
            updated_body, count = identity_pattern.subn(
                lambda match: (
                    f"{match.group('indent')}PRODUCT_BUNDLE_IDENTIFIER = "
                    f"{requested_bundle_identifier};"
                ),
                body,
                count=1,
            )
            if count != 1:
                raise IntegrationError(
                    f"Could not safely update PRODUCT_BUNDLE_IDENTIFIER in build configuration "
                    f"`{config_id}` for app target `{project_context.target_name}`."
                )
            if updated_body != body:
                patched_count += 1
                patched_section = (
                    patched_section[: config_match.start("body")]
                    + updated_body
                    + patched_section[config_match.end("body") :]
                )
        if patched_count:
            write_text(
                project_file,
                text.replace(config_section, patched_section, 1),
                target_root,
                report,
                (
                    f"Set native iOS app target `{project_context.target_name}` Bundle Identifier "
                    f"to `{requested_bundle_identifier}` without modifying test or extension targets"
                ),
            )
        else:
            report.add_change(
                f"Native iOS app target `{project_context.target_name}` already uses "
                f"`{requested_bundle_identifier}` in every build configuration."
            )
        effective_bundle_identifier = requested_bundle_identifier
    else:
        if len(identities) != 1:
            choices = ", ".join(f"`{value}`" for value in sorted(identities))
            raise IntegrationError(
                f"Native iOS app target `{project_context.target_name}` uses different Bundle Identifiers "
                f"across build configurations: {choices}. Pass --ios-bundle-identifier <exact value> "
                "to normalize only this app target."
            )
        effective_bundle_identifier = next(iter(identities))

    report.add_input(
        f"Native iOS Bundle Identifier: `{effective_bundle_identifier}` "
        f"(app target `{project_context.target_name}`)."
    )
    if effective_bundle_identifier != OFFICIAL_DEMO_BUNDLE_IDENTIFIER:
        report.add_warning(
            f"Native iOS app target Bundle Identifier is `{effective_bundle_identifier}`. "
            "The Meishe official Demo material service requires the exact Bundle Identifier "
            "`com.meishe.duanshipindemo`; online service requests will not work with the current identity. "
            "For temporary Demo validation pass `--ios-bundle-identifier com.meishe.duanshipindemo`, "
            "or preserve the current identity and configure a customer server, matching License, and service allowlist."
        )
    return effective_bundle_identifier


def detect_xcode_major() -> int | None:
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
        return None
    match = re.search(r"\bXcode\s+(\d+)(?:\.\d+)*", completed.stdout)
    return int(match.group(1)) if match else None


def patch_xcode_26_user_script_sandboxing(
    target_root: Path,
    report: Report,
    project_context: IosProjectContext,
    xcode_major: int | None = None,
    *,
    detect_if_none: bool = True,
) -> bool:
    """Apply the verified CocoaPods script-phase compatibility setting only for Xcode 26."""
    if xcode_major is None and detect_if_none:
        xcode_major = detect_xcode_major()
    if xcode_major is None:
        report.add_toolchain_warning(
            "Xcode version could not be determined; the Xcode 26 CocoaPods script-sandbox compatibility "
            "setting was not applied. Run `xcodebuild -version` and follow the version-specific route "
            "troubleshooting before changing build settings."
        )
        return False
    report.add_input(f"Detected Xcode major version: `{xcode_major}`.")
    if xcode_major != 26:
        report.add_toolchain_warning(
            f"Xcode {xcode_major} is outside the verified Xcode 26 compatibility patch. "
            "`ENABLE_USER_SCRIPT_SANDBOXING` was left unchanged; do not inherit the Xcode 26 patch."
        )
        return False

    project_file = project_context.project_path / "project.pbxproj"
    if not project_file.exists():
        report.add_toolchain_warning(
            f"Xcode 26 was detected, but `{project_context.project_path.name}/project.pbxproj` is missing. "
            "Set User Script Sandboxing to No on the confirmed app target manually."
        )
        return False
    text = read_text(project_file)
    target_section = pbx_section(text, "PBXNativeTarget")
    target_match = next(
        (
            match
            for match in re.finditer(
                r"(?P<id>[A-Fa-f0-9]{8,})\s+/\*.*?\*/\s*=\s*\{(?P<body>.*?)^\s*\};",
                target_section,
                re.M | re.S,
            )
            if re.search(
                rf"(?m)^\s*name\s*=\s*\"?{re.escape(project_context.target_name)}\"?\s*;",
                match.group("body"),
            )
            and re.search(
                r'productType\s*=\s*"?com\.apple\.product-type\.application"?\s*;',
                match.group("body"),
            )
        ),
        None,
    )
    config_list_id = (
        re.search(
            r"buildConfigurationList\s*=\s*([A-Fa-f0-9]{8,})",
            target_match.group("body"),
        )
        if target_match
        else None
    )
    config_ids: list[str] = []
    if config_list_id:
        list_section = pbx_section(text, "XCConfigurationList")
        list_match = re.search(
            rf"{re.escape(config_list_id.group(1))}\s+/\*.*?\*/\s*=\s*\{{(?P<body>.*?)^\s*\}};",
            list_section,
            re.M | re.S,
        )
        if list_match:
            configurations = re.search(
                r"buildConfigurations\s*=\s*\((?P<body>.*?)\);",
                list_match.group("body"),
                re.S,
            )
            if configurations:
                config_ids = re.findall(
                    r"([A-Fa-f0-9]{8,})\s+/\*",
                    configurations.group("body"),
                )
    if not config_ids:
        report.add_toolchain_warning(
            f"Xcode 26 was detected, but build configurations for app target "
            f"`{project_context.target_name}` could not be mapped exactly. "
            "Set User Script Sandboxing to No on that app target manually; test and extension targets were not modified."
        )
        return False

    config_section = pbx_section(text, "XCBuildConfiguration")
    patched_section = config_section
    changed_count = 0
    verified_count = 0
    for config_id in config_ids:
        object_pattern = re.compile(
            rf"(?P<prefix>^[ \t]*{re.escape(config_id)}\s+/\*.*?\*/\s*=\s*\{{.*?"
            r"buildSettings\s*=\s*\{)(?P<body>.*?)(?P<suffix>^[ \t]*\};\s*"
            r"(?:\n[ \t]*name\s*=.*?;)?\s*\n[ \t]*\};)",
            re.M | re.S,
        )
        config_match = object_pattern.search(patched_section)
        if not config_match:
            continue
        body = config_match.group("body")
        setting_pattern = re.compile(
            r"(?m)^(?P<indent>[ \t]*)ENABLE_USER_SCRIPT_SANDBOXING\s*=\s*[^;]+;"
        )
        if setting_pattern.search(body):
            updated_body = setting_pattern.sub(
                lambda match: f"{match.group('indent')}ENABLE_USER_SCRIPT_SANDBOXING = NO;",
                body,
                count=1,
            )
        else:
            indent_match = re.search(r"(?m)^(?P<indent>[ \t]*)[A-Za-z0-9_]+\s*=", body)
            indent = indent_match.group("indent") if indent_match else "\t\t\t\t"
            updated_body = body.rstrip() + f"\n{indent}ENABLE_USER_SCRIPT_SANDBOXING = NO;\n"
        if "ENABLE_USER_SCRIPT_SANDBOXING = NO;" in updated_body:
            verified_count += 1
        if updated_body != body:
            changed_count += 1
            patched_section = (
                patched_section[: config_match.start("body")]
                + updated_body
                + patched_section[config_match.end("body") :]
            )

    if verified_count != len(config_ids):
        report.add_toolchain_warning(
            f"Xcode 26 app target `{project_context.target_name}` has {len(config_ids)} mapped build "
            f"configuration(s), but only {verified_count} could be patched safely. No other target was modified."
        )
        return False
    if changed_count:
        patched = text.replace(config_section, patched_section, 1)
        write_text(
            project_file,
            patched,
            target_root,
            report,
            "Applied verified Xcode 26 CocoaPods script-sandbox compatibility to the app target",
        )
        report.add_change(
            f"Xcode 26 only: set `ENABLE_USER_SCRIPT_SANDBOXING = NO` in the mapped build configurations "
            f"for app target `{project_context.target_name}`; test and extension targets were left unchanged."
        )
        return True
    report.add_change(
        f"Verified Xcode 26 script-sandbox compatibility is already present on app target "
        f"`{project_context.target_name}`."
    )
    return True


def official_example_allows_arbitrary_loads(source_pods_package: Path) -> bool:
    example_root = source_pods_package / "Example"
    if not example_root.exists():
        return False
    for plist_path in sorted(example_root.rglob("Info.plist")):
        try:
            with plist_path.open("rb") as fh:
                data = plistlib.load(fh)
        except Exception:
            continue
        if data.get("NSAppTransportSecurity", {}).get("NSAllowsArbitraryLoads") is True:
            return True
    return False


def supports_native_ios_autocut_draft_fallback(source_pods_package: Path) -> bool:
    objc_text = "\n".join(
        read_text(candidate)
        for candidate in source_pods_package.rglob("NvShortVideoCore-Swift.h")
    )
    swift_text = "\n".join(
        read_text(candidate)
        for candidate in source_pods_package.rglob("*.swiftinterface")
    )
    return all(marker in objc_text for marker in AUTOCUT_DRAFT_API_MARKERS) and all(
        marker in swift_text for marker in AUTOCUT_DRAFT_SWIFT_API_MARKERS
    )


def find_first_named_file(root: Path, names: set[str]) -> Path | None:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [dirname for dirname in dirnames if dirname not in SDK_COPY_SKIP_DIRS]
        for filename in sorted(filenames):
            if filename in names:
                return Path(dirpath) / filename
    return None


def copy_ios_demo_config_files(target_root: Path, package_root: Path, report: Report) -> None:
    dst_dir = target_root / "MeisheShortVideo"
    for name in ("Config.swift", "NvHttpRequestDelegate.swift"):
        src = find_first_named_file(package_root, {name})
        if src:
            copy_file(src, dst_dir / name, target_root, report, f"Copied native iOS demo config file `{name}`")
        else:
            report.add_warning(f"Native iOS: `{name}` was not found under `{package_root}`; copy it from the official demo if your project needs the native demo helper.")


def copy_ios_demo_ui_assets(target_root: Path, report: Report) -> None:
    assets_dir = target_root / "MeisheShortVideo" / "Assets"
    copy_demo_banner(assets_dir / DEMO_BANNER_FILE, target_root, report, "Copied demo home banner for native iOS")
    copy_demo_icons(assets_dir, target_root, report, "Copied demo function icon for native iOS")


def create_native_ios_style_helper(target_root: Path, report: Report) -> None:
    content = r"""import UIKit

enum MeisheShortVideoStyle {
    static let homeBackground = color(0x171D26)
    static let pageBackground = color(0x101010)
    static let panelBackground = color(0x222832)
    static let rowBackground = color(0x424954)
    static let textPrimary = UIColor.white
    static let textSecondary = color(0xD8D8D8)
    static let textMuted = color(0x9CA3AF)
    static let accent = color(0xFC3E5A)

    static func color(_ hex: Int, alpha: CGFloat = 1) -> UIColor {
        UIColor(
            red: CGFloat((hex >> 16) & 0xff) / 255.0,
            green: CGFloat((hex >> 8) & 0xff) / 255.0,
            blue: CGFloat(hex & 0xff) / 255.0,
            alpha: alpha
        )
    }

    static func label(_ text: String, size: CGFloat, weight: UIFont.Weight = .regular, color: UIColor = textPrimary) -> UILabel {
        let label = UILabel()
        label.text = text
        label.textColor = color
        label.font = .systemFont(ofSize: size, weight: weight)
        label.numberOfLines = 0
        label.translatesAutoresizingMaskIntoConstraints = false
        return label
    }

    static func rounded(_ view: UIView, radius: CGFloat) {
        view.layer.cornerRadius = radius
        view.layer.masksToBounds = true
    }

    static func image(named name: String) -> UIImage? {
        let base = name
            .replacingOccurrences(of: ".png", with: "")
            .replacingOccurrences(of: ".jpg", with: "")
        let candidates = [
            name,
            base,
            "Assets/\(name)",
            "Assets/\(base)",
            "MeisheShortVideo/Assets/\(name)",
            "MeisheShortVideo/Assets/\(base)"
        ]
        for candidate in candidates {
            if let image = UIImage(named: candidate) {
                return image
            }
        }
        return nil
    }

    static func image(fromFile path: String?) -> UIImage? {
        guard let path = path, !path.isEmpty else { return nil }
        return UIImage(contentsOfFile: path)
    }

    static func fallbackDraftTitle(date: Date = Date()) -> String {
        let formatter = DateFormatter()
        formatter.dateFormat = "MMdd"
        return "草稿-\(formatter.string(from: date))"
    }

    static func firstStringValue(from object: NSObject, keys: [String]) -> String? {
        for key in keys {
            let selector = NSSelectorFromString(key)
            guard object.responds(to: selector) else { continue }
            if let value = object.value(forKey: key) as? String {
                let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
                if !trimmed.isEmpty {
                    return trimmed
                }
            }
        }
        return nil
    }

    static func thumbnail(path: String?, fallbackTitle: String) -> UIView {
        let container = UIView()
        container.translatesAutoresizingMaskIntoConstraints = false
        container.backgroundColor = color(0x1D1D1D)
        rounded(container, radius: 8)

        let imageView = UIImageView()
        imageView.translatesAutoresizingMaskIntoConstraints = false
        imageView.contentMode = .scaleAspectFill
        imageView.clipsToBounds = true
        imageView.image = image(fromFile: path)
        container.addSubview(imageView)
        NSLayoutConstraint.activate([
            imageView.leadingAnchor.constraint(equalTo: container.leadingAnchor),
            imageView.trailingAnchor.constraint(equalTo: container.trailingAnchor),
            imageView.topAnchor.constraint(equalTo: container.topAnchor),
            imageView.bottomAnchor.constraint(equalTo: container.bottomAnchor)
        ])

        if imageView.image == nil {
            let fallback = label(fallbackTitle, size: 13, weight: .semibold, color: textMuted)
            fallback.textAlignment = .center
            fallback.numberOfLines = 2
            container.addSubview(fallback)
            NSLayoutConstraint.activate([
                fallback.leadingAnchor.constraint(equalTo: container.leadingAnchor, constant: 8),
                fallback.trailingAnchor.constraint(equalTo: container.trailingAnchor, constant: -8),
                fallback.centerYAnchor.constraint(equalTo: container.centerYAnchor)
            ])
        }

        let playCircle = UIView()
        playCircle.translatesAutoresizingMaskIntoConstraints = false
        playCircle.backgroundColor = color(0x000000, alpha: 0.42)
        rounded(playCircle, radius: 22)
        container.addSubview(playCircle)

        let play = label(">", size: 22, weight: .bold)
        play.textAlignment = .center
        playCircle.addSubview(play)

        NSLayoutConstraint.activate([
            playCircle.widthAnchor.constraint(equalToConstant: 44),
            playCircle.heightAnchor.constraint(equalToConstant: 44),
            playCircle.centerXAnchor.constraint(equalTo: container.centerXAnchor),
            playCircle.centerYAnchor.constraint(equalTo: container.centerYAnchor),
            play.centerXAnchor.constraint(equalTo: playCircle.centerXAnchor, constant: 1),
            play.centerYAnchor.constraint(equalTo: playCircle.centerYAnchor, constant: -1)
        ])
        return container
    }

    static func topBar(title: String, owner: UIViewController, action: Selector) -> UIView {
        let bar = UIView()
        bar.translatesAutoresizingMaskIntoConstraints = false
        bar.backgroundColor = pageBackground

        let back = UIButton(type: .system)
        back.translatesAutoresizingMaskIntoConstraints = false
        back.setTitle("<", for: .normal)
        back.titleLabel?.font = .systemFont(ofSize: 30, weight: .regular)
        back.tintColor = .white
        back.addTarget(owner, action: action, for: .touchUpInside)
        bar.addSubview(back)

        let titleLabel = label(title, size: 18, weight: .semibold)
        titleLabel.textAlignment = .center
        bar.addSubview(titleLabel)

        NSLayoutConstraint.activate([
            back.leadingAnchor.constraint(equalTo: bar.leadingAnchor, constant: 16),
            back.centerYAnchor.constraint(equalTo: bar.centerYAnchor),
            back.widthAnchor.constraint(equalToConstant: 44),
            back.heightAnchor.constraint(equalToConstant: 44),
            titleLabel.centerXAnchor.constraint(equalTo: bar.centerXAnchor),
            titleLabel.centerYAnchor.constraint(equalTo: bar.centerYAnchor),
            titleLabel.leadingAnchor.constraint(greaterThanOrEqualTo: back.trailingAnchor, constant: 12),
            titleLabel.trailingAnchor.constraint(lessThanOrEqualTo: bar.trailingAnchor, constant: -72)
        ])
        return bar
    }

    static func actionButton(title: String, filled: Bool) -> UIButton {
        let button = UIButton(type: .system)
        button.translatesAutoresizingMaskIntoConstraints = false
        button.setTitle(title, for: .normal)
        button.titleLabel?.font = .systemFont(ofSize: 16, weight: .semibold)
        button.tintColor = .white
        button.backgroundColor = filled ? rowBackground : color(0x1D1D1D)
        button.layer.borderWidth = filled ? 0 : 1
        button.layer.borderColor = color(0x3F4652).cgColor
        rounded(button, radius: 24)
        return button
    }
}

final class MeisheShortVideoTapControl: UIControl {
    private var tapAction: (() -> Void)?

    func onTap(_ action: @escaping () -> Void) {
        tapAction = action
        removeTarget(self, action: #selector(runTapAction), for: .touchUpInside)
        addTarget(self, action: #selector(runTapAction), for: .touchUpInside)
    }

    override func point(inside point: CGPoint, with event: UIEvent?) -> Bool {
        return bounds.insetBy(dx: -8, dy: -8).contains(point)
    }

    @objc private func runTapAction() {
        tapAction?()
    }
}
"""
    write_text(
        target_root / "MeisheShortVideo" / "MeisheShortVideoStyle.swift",
        content,
        target_root,
        report,
        "Generated native iOS Swift UI support",
    )


def create_native_ios_feature_config(target_root: Path, report: Report) -> Path:
    path = target_root / "MeisheShortVideo" / "MeisheFeatureConfig.swift"
    if path.exists():
        report.add_change("Retained user-editable native iOS feature configuration: `MeisheShortVideo/MeisheFeatureConfig.swift`")
        return path

    content = r"""import UIKit
import NvShortVideoCore

/// 原生 iOS 专属配置。只修改本文件，不要套用 Android、React Native 或 Flutter 的枚举名。
/// SDK 根据有序菜单数组创建控件：删除数组项会删除入口并重排其余 UI，禁止写入空字符串作为占位。
enum MeisheFeatureConfig {
    static func apply(to config: NvVideoConfig) {
        // 全局颜色；最后一个参数是透明度。
        config.primaryColor = color(0xFC3E5A)
        config.backgroundColor = color(0x000000)
        config.panelBackgroundColor = color(0x1C1C1C)
        config.textColor = color(0xFFFFFF)
        config.secondaryTextColor = color(0x6C6C77)
        // 是否显示设备本地音乐入口；读取本地音乐仍受系统权限约束。
        config.enableLocalMusic = true
        // 文字阴影偏移与颜色。
        config.shadowOffset = CGSize(width: 0, height: 0.5)
        config.shadowColor = color(0x000000, alpha: 0.5)

        // 相册顶部标签：0=全部，1=视频，2=图片。
        config.albumConfig.type = 0
        // 相册最大选择数，必须大于 0。
        config.albumConfig.maxSelectCount = 50
        // 编辑素材选择页是否显示一键成片；不会自动删除拍摄页模板模式。
        config.albumConfig.useAutoCut = true

        // 一键成片/自适应模板最大可选片段数，必须大于 0。
        config.templateConfig.maxSelectCount = 50
        // 模板页面是否显示一键成片。
        config.templateConfig.useAutoCut = true
        // 一键成片推荐模板最大数量，必须大于 0。
        config.templateConfig.maxRecommandTemplateCount = 20

        // 拍摄右侧菜单，有序。删除 speed 可去掉快慢速，删除 matting 可去掉抠像；其余入口自动上移。
        config.captureConfig.captureMenuItems = [
            NvCaptureMenu.device,
            NvCaptureMenu.speed,
            NvCaptureMenu.timer,
            NvCaptureMenu.beauty,
            NvCaptureMenu.makeup,
            NvCaptureMenu.prop,
            NvCaptureMenu.matting,
            NvCaptureMenu.flashlight,
            NvCaptureMenu.filter,
            NvCaptureMenu.original
        ]
        // 拍摄底部模式，有序且不能为空；template 存在时必须放在最后。
        config.captureConfig.captureBottomMenuItems = [
            NvCaptureBottomMenu.image,
            NvCaptureBottomMenu.video,
            NvCaptureBottomMenu.smart,
            NvCaptureBottomMenu.template
        ]
        // 默认拍摄模式必须同时存在于 captureBottomMenuItems。
        config.captureConfig.defaultBottomMenuSelectItem = NvCaptureBottomMenu.video
        // 默认摄像头：0=后置，1=前置。
        config.captureConfig.captureDeviceIndex = 1
        // 拍摄预览分辨率只支持 720/1080。
        config.captureConfig.resolution = .resolution1080
        // 是否忽略设备旋转信息。
        config.captureConfig.ignoreVideoRotation = true
        // 照片进入编辑后的默认时长，单位毫秒，必须大于 0。
        config.captureConfig.imageDuration = 3000
        // 拍照完成、进入编辑前是否把原图保存到系统相册。
        config.captureConfig.autoSavePhotograph = false
        // 普通录制档位，单位毫秒；每组必须满足 0 <= minDuration < maxDuration。
        config.captureConfig.timeRanges = [timePair(3000, 15000), timePair(3000, 60000)]
        // 快拍时长范围，单位毫秒。
        config.captureConfig.smartTimeRange = timePair(0, 15000)
        // 滤镜默认强度，官方配置范围为 0.0-1.0。
        config.captureConfig.filterDefaultValue = 0.8
        // 是否在拍摄页显示相册快捷入口。
        config.captureConfig.enableCaptureAlbum = false
        // true 会在进入拍摄时自动关闭原声/麦克风。
        config.captureConfig.autoDisablesMic = false
        // iOS 有效帧率范围为 5-30；已验证默认值为 30。
        config.captureConfig.fps = 30
        // recordConfiguration 支持 bitrate、gopsize、video encoder name；未知底层键禁止写入。
        config.captureConfig.recordConfiguration = [:]

        // beautyConfig 可分别裁剪 categoricalArray、beautyEffectArray、beautyShapeArray、
        // beautyMicroShapeArray、beautyAdjustArray；元素必须使用当前 iOS SDK 的 NvBeauty*Item 常量。

        // 合拍右侧菜单独立于普通拍摄菜单，有序；删除项后合拍页面同步重排。
        config.captureConfig.dualMenuItems = [
            NvCaptureMenu.device,
            NvCaptureMenu.speed,
            NvCaptureMenu.timer,
            NvCaptureMenu.beauty,
            NvCaptureMenu.makeup,
            NvCaptureMenu.prop,
            NvCaptureMenu.matting,
            NvCaptureMenu.flashlight,
            NvCaptureMenu.filter,
            NvCaptureMenu.original,
            NvCaptureMenu.dualType
        ]
        // 小窗左/上边距与底图宽/高的比例，建议保持在 0.0-1.0。
        config.captureConfig.dualConfig.left = 17.0 / 375.0
        config.captureConfig.dualConfig.top = 18.0 / 666.67
        // 小窗短边与底图宽度比例，必须大于 0 且不宜超过 1。
        config.captureConfig.dualConfig.limitWidth = 153.5 / 375.0
        // 默认合拍样式必须包含在 supportedTypes 位掩码中。
        config.captureConfig.dualConfig.defaultType = .leftRight
        config.captureConfig.dualConfig.supportedTypes = Int(NvDualType.leftRight.rawValue)
            | Int(NvDualType.topDown.rawValue)
            | Int(NvDualType.leftRect.rawValue)
            | Int(NvDualType.leftCircle.rawValue)
            | Int(NvDualType.topCircle.rawValue)
        // 是否自动禁用麦克风；muteOriginal 控制是否默认关闭原视频声音。
        config.captureConfig.dualConfig.autoDisablesMic = false
        config.captureConfig.dualConfig.muteOriginal = true

        // 编辑右侧菜单，有序。删除 text 会删除文字入口及其下级功能，后续入口自动上移，不留空白。
        // iOS 2.0.2.1 只公开以下七项；发布、下载、自动字幕不是该 iOS 数组的合法常量。
        config.editConfig.editMenuItems = [
            NvEditMenuItemConstants.edit,
            NvEditMenuItemConstants.text,
            NvEditMenuItemConstants.sticker,
            NvEditMenuItemConstants.effect,
            NvEditMenuItemConstants.filter,
            NvEditMenuItemConstants.audio,
            NvEditMenuItemConstants.record
        ]
        // 编辑预览分辨率、帧率；预览配置不等于最终导出配置。
        config.editConfig.resolution = .resolution1080
        config.editConfig.fps = 25
        // 特效、录音最小时长以及图片默认时长，单位毫秒，均不得为负数。
        config.editConfig.minEffectDuration = 500
        config.editConfig.minAudioDuration = 1000
        config.editConfig.defaultImageDuration = 4000
        // 字幕默认颜色与可选颜色，格式为 #RRGGBB。
        config.editConfig.captionColor = "#FFFFFF"
        config.editConfig.captionColorList = ["#FFFFFF", "#000000", "#0099F6", "#50C23B", "#FFC840", "#FF8500", "#FF3350", "#E40069", "#B200C0", "#F8808A", "#FEBF7C", "#262626", "#363636", "#555555", "#737373", "#989898", "#B2B2B2", "#C7C7C7", "#DBDBDB", "#F0F0F0"]
        // 字幕样式是位掩码：无、背景、半透明背景、描边。
        config.editConfig.supportedCaptionStyles = Int(NvImageCaptionStyle.none.rawValue)
            | Int(NvImageCaptionStyle.bg.rawValue)
            | Int(NvImageCaptionStyle.bgAlpha.rawValue)
            | Int(NvImageCaptionStyle.outline.rawValue)
        // firstAsset 按首个素材决定画幅；fixed 使用 editMode。
        config.editConfig.editModeSource = .firstAsset
        config.editConfig.editMode = .mode9v16
        // 用户可选画幅位掩码；fixed 的 editMode 必须包含在其中。
        config.editConfig.supportedEditModes = Int(NvEditMode.mode9v16.rawValue)
            | Int(NvEditMode.mode16v9.rawValue)
            | Int(NvEditMode.mode3v4.rawValue)
            | Int(NvEditMode.mode4v3.rawValue)
            | Int(NvEditMode.mode1v1.rawValue)
            | Int(NvEditMode.mode18v9.rawValue)
            | Int(NvEditMode.mode9v18.rawValue)
            | Int(NvEditMode.mode8v9.rawValue)
            | Int(NvEditMode.mode9v8.rawValue)
        // 编辑滤镜默认强度 0.0-1.0；最大音量稳定范围 (0,8]。
        config.editConfig.filterDefaultValue = 0.8
        config.editConfig.maxVolume = 4
        // 原生 iOS 2.0.2.1 的 NvEditConfig 未公开 disableTimeEffect，禁止照搬 Android/RN/Flutter 字段。

        // 导出分辨率支持 720/1080/4K；4K 必须经过设备内存和性能验证。
        config.compileConfig.resolution = .resolution1080
        config.compileConfig.fps = 25
        // bitrate != -1 时优先使用精确码率；-1 时使用 bitrateGrade。
        config.compileConfig.bitrateGrade = NvsCompileBitrateGradeHigh
        config.compileConfig.bitrate = -1
        // 封面图片格式以及导出后是否保存到系统相册。
        config.compileConfig.imageType = .png
        config.compileConfig.autoSaveVideo = true
        // watermarkConfig/coverWatermarkConfig 需要真实 NvImageConfig、尺寸、偏移和位置，默认不设置。
        // configure 可设置底层合成键值；未知键禁止写入，bitrate/fps 冲突时以上显式字段优先。
        config.compileConfig.configure = [:]

        // modelConfig 路径必须指向与当前 iOS SDK 匹配的真实模型文件，不得伪造或跨版本复制。
        // iOS 2.0.2.1 可配置：use240、fakeface、face、face240、avatar、hand、humanseg、skysegment、
        // eyecontour、advancedbeauty、facecommon；该版本未公开 RN/Flutter 的 AutoCut 模型路径字段。

        validate(config)
    }

    static func validate(_ config: NvVideoConfig) {
        let bottom = config.captureConfig.captureBottomMenuItems
        precondition(!bottom.isEmpty, "captureBottomMenuItems must contain at least one capture mode")
        precondition(bottom.contains(config.captureConfig.defaultBottomMenuSelectItem), "defaultBottomMenuSelectItem must exist in captureBottomMenuItems")
        if let templateIndex = bottom.firstIndex(of: NvCaptureBottomMenu.template) {
            precondition(templateIndex == bottom.count - 1, "NvCaptureBottomMenu.template must be the last bottom menu item")
        }
        precondition(Set(config.captureConfig.captureMenuItems).count == config.captureConfig.captureMenuItems.count, "captureMenuItems contains duplicates")
        precondition(Set(bottom).count == bottom.count, "captureBottomMenuItems contains duplicates")
        precondition(Set(config.captureConfig.dualMenuItems).count == config.captureConfig.dualMenuItems.count, "dualMenuItems contains duplicates")
        precondition(Set(config.editConfig.editMenuItems).count == config.editConfig.editMenuItems.count, "editMenuItems contains duplicates")
        precondition(config.albumConfig.maxSelectCount > 0 && config.templateConfig.maxSelectCount > 0, "album/template maxSelectCount must be greater than 0")
        precondition(config.editConfig.maxVolume > 0 && config.editConfig.maxVolume <= 8, "editConfig.maxVolume must be greater than 0 and no greater than 8")
    }

    private static func timePair(_ minDuration: Int64, _ maxDuration: Int64) -> NvTimePair {
        let pair = NvTimePair()
        pair.minDuration = minDuration
        pair.maxDuration = maxDuration
        return pair
    }

    private static func color(_ hex: Int, alpha: CGFloat = 1) -> UIColor {
        UIColor(
            red: CGFloat((hex >> 16) & 0xff) / 255,
            green: CGFloat((hex >> 8) & 0xff) / 255,
            blue: CGFloat(hex & 0xff) / 255,
            alpha: alpha
        )
    }
}
"""
    write_text(path, content, target_root, report, "Generated user-editable native iOS feature configuration")
    report.add_user_configuration(
        "Native iOS feature entry: edit `MeisheShortVideo/MeisheFeatureConfig.swift`. Menu arrays are ordered and drive SDK UI reflow; the skill preserves this file on later runs."
    )
    return path


def create_native_ios_home_view_controller(target_root: Path, report: Report) -> None:
    content = r"""import UIKit
import Network
import NvShortVideoCore

final class MeisheShortVideoHomeViewController: UIViewController {
    private let moduleManager = NvModuleManager.sharedInstance()
    private let videoConfig = NvVideoConfig()
    private let dependencyDelegate = NvHttpRequestDelegate()
    private enum ServerConfig {
        // The official demo service only accepts the official demo bundle identifier.
        static let officialDemoBundleIdentifier = "com.meishe.duanshipindemo"
        static let officialDemoHost = "https://mall.meishesdk.com/api/shortvideo/v1"
        static let host: String? = officialDemoHost
        static let assetAutoCutUrl: String? = "https://creative.meishesdk.com/api/app/aivideo/asset/all/1"
        static let clientId: String? = nil
        static let clientSecret: String? = nil
        static let assemblyId: String? = nil
    }
    private var actionRows: [UIControl] = []
    private var loadingOverlay = UIView()
    private let statusLabel = MeisheShortVideoStyle.label("", size: 17, weight: .regular)
    private let retryButton = MeisheShortVideoStyle.actionButton(title: "重试", filled: true)
    private var isMaterialRequestInProgress = false
    private var isMaterialReady = false

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = MeisheShortVideoStyle.homeBackground
        navigationController?.setNavigationBarHidden(true, animated: false)
        moduleManager.delegate = self
        configureFeatures()
        setWebConfig()
        buildView()
        prepareMaterialsInBackground()
    }

    private func configureFeatures() {
        MeisheFeatureConfig.apply(to: videoConfig)
    }

    private func buildView() {
        let scroll = UIScrollView()
        scroll.translatesAutoresizingMaskIntoConstraints = false
        scroll.alwaysBounceVertical = false
        scroll.delaysContentTouches = false
        scroll.canCancelContentTouches = true
        view.addSubview(scroll)

        let root = UIStackView()
        root.translatesAutoresizingMaskIntoConstraints = false
        root.axis = .vertical
        root.spacing = 0
        root.layoutMargins = UIEdgeInsets(top: 34, left: 24, bottom: 56, right: 24)
        root.isLayoutMarginsRelativeArrangement = true
        scroll.addSubview(root)

        let title = MeisheShortVideoStyle.label("素材上新", size: 30, weight: .bold)
        root.addArrangedSubview(title)

        let banner = UIImageView(image: MeisheShortVideoStyle.image(named: "meishe_home_banner.jpg"))
        banner.translatesAutoresizingMaskIntoConstraints = false
        banner.contentMode = .scaleAspectFill
        banner.backgroundColor = MeisheShortVideoStyle.panelBackground
        banner.isUserInteractionEnabled = false
        MeisheShortVideoStyle.rounded(banner, radius: 12)
        root.addArrangedSubview(banner)
        root.setCustomSpacing(18, after: banner)

        let bannerHeight = min(148, max(108, UIScreen.main.bounds.height * 0.18))
        NSLayoutConstraint.activate([
            scroll.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            scroll.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            scroll.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            scroll.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            root.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor),
            root.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor),
            root.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor),
            root.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor),
            root.widthAnchor.constraint(equalTo: scroll.frameLayoutGuide.widthAnchor),
            banner.heightAnchor.constraint(equalToConstant: bannerHeight)
        ])
        root.setCustomSpacing(12, after: title)

        let panel = UIStackView()
        panel.translatesAutoresizingMaskIntoConstraints = false
        panel.axis = .vertical
        panel.spacing = 10
        panel.layoutMargins = UIEdgeInsets(top: 22, left: 20, bottom: 16, right: 20)
        panel.isLayoutMarginsRelativeArrangement = true
        MeisheShortVideoStyle.rounded(panel, radius: 14)
        let panelBackground = UIView()
        panelBackground.translatesAutoresizingMaskIntoConstraints = false
        panelBackground.backgroundColor = MeisheShortVideoStyle.panelBackground
        panelBackground.isUserInteractionEnabled = false
        panel.insertSubview(panelBackground, at: 0)
        root.addArrangedSubview(panel)
        NSLayoutConstraint.activate([
            panelBackground.leadingAnchor.constraint(equalTo: panel.leadingAnchor),
            panelBackground.trailingAnchor.constraint(equalTo: panel.trailingAnchor),
            panelBackground.topAnchor.constraint(equalTo: panel.topAnchor),
            panelBackground.bottomAnchor.constraint(equalTo: panel.bottomAnchor)
        ])

        panel.addArrangedSubview(MeisheShortVideoStyle.label("请选择所需的功能", size: 16))
        panel.addArrangedSubview(MeisheShortVideoStyle.label("功能列表", size: 23, weight: .bold))
        panel.addArrangedSubview(actionRow(icon: "meishe_icon_capture.png", title: "拍摄") { [weak self] in
            self?.openCapture()
        })
        panel.addArrangedSubview(actionRow(icon: "meishe_icon_dual_capture.png", title: "合拍") { [weak self] in
            self?.openDualCapture()
        })
        panel.addArrangedSubview(actionRow(icon: "meishe_icon_edit.png", title: "编辑") { [weak self] in
            self?.openEdit()
        })
        panel.addArrangedSubview(actionRow(icon: "meishe_icon_draft.png", title: "草稿") { [weak self] in
            self?.openDrafts()
        })

        buildLoadingOverlay()
    }

    private func buildLoadingOverlay() {
        loadingOverlay.translatesAutoresizingMaskIntoConstraints = false
        loadingOverlay.backgroundColor = MeisheShortVideoStyle.color(0x101317, alpha: 0.82)
        view.addSubview(loadingOverlay)

        let stack = UIStackView()
        stack.translatesAutoresizingMaskIntoConstraints = false
        stack.axis = .vertical
        stack.alignment = .center
        stack.spacing = 18
        loadingOverlay.addSubview(stack)

        statusLabel.textAlignment = .center
        stack.addArrangedSubview(statusLabel)
        retryButton.addTarget(self, action: #selector(retryMaterials), for: .touchUpInside)
        stack.addArrangedSubview(retryButton)

        NSLayoutConstraint.activate([
            loadingOverlay.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            loadingOverlay.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            loadingOverlay.topAnchor.constraint(equalTo: view.topAnchor),
            loadingOverlay.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            stack.centerXAnchor.constraint(equalTo: loadingOverlay.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: loadingOverlay.centerYAnchor),
            stack.leadingAnchor.constraint(greaterThanOrEqualTo: loadingOverlay.leadingAnchor, constant: 28),
            stack.trailingAnchor.constraint(lessThanOrEqualTo: loadingOverlay.trailingAnchor, constant: -28),
            retryButton.widthAnchor.constraint(equalToConstant: 120),
            retryButton.heightAnchor.constraint(equalToConstant: 48)
        ])
        loadingOverlay.isHidden = true
    }

    private func actionRow(icon: String, title: String, action: @escaping () -> Void) -> UIControl {
        let row = MeisheShortVideoTapControl()
        row.translatesAutoresizingMaskIntoConstraints = false
        row.backgroundColor = MeisheShortVideoStyle.rowBackground
        MeisheShortVideoStyle.rounded(row, radius: 25)

        let stack = UIStackView()
        stack.translatesAutoresizingMaskIntoConstraints = false
        stack.axis = .horizontal
        stack.alignment = .center
        stack.spacing = 18
        stack.isUserInteractionEnabled = false
        row.addSubview(stack)

        let iconView = UIImageView(image: MeisheShortVideoStyle.image(named: icon))
        iconView.translatesAutoresizingMaskIntoConstraints = false
        iconView.contentMode = .scaleAspectFit
        stack.addArrangedSubview(iconView)

        let label = MeisheShortVideoStyle.label(title, size: 18, weight: .bold, color: MeisheShortVideoStyle.color(0xE8EAEE))
        stack.addArrangedSubview(label)

        let chevron = MeisheShortVideoStyle.label(">", size: 22, weight: .regular, color: MeisheShortVideoStyle.color(0xB5BBC5))
        chevron.textAlignment = .right
        stack.addArrangedSubview(chevron)

        row.onTap(action)
        actionRows.append(row)

        NSLayoutConstraint.activate([
            row.heightAnchor.constraint(equalToConstant: 50),
            stack.leadingAnchor.constraint(equalTo: row.leadingAnchor, constant: 22),
            stack.trailingAnchor.constraint(equalTo: row.trailingAnchor, constant: -20),
            stack.centerYAnchor.constraint(equalTo: row.centerYAnchor),
            iconView.widthAnchor.constraint(equalToConstant: 24),
            iconView.heightAnchor.constraint(equalToConstant: 24),
            chevron.widthAnchor.constraint(equalToConstant: 20)
        ])
        return row
    }

    private func setWebConfig() {
        guard let request = moduleManager.netDelegate else { return }
        request.dependencyDelegate = dependencyDelegate
        let usesOfficialDemoHost = ServerConfig.host == ServerConfig.officialDemoHost
        let canUseConfiguredHost = !usesOfficialDemoHost
            || Bundle.main.bundleIdentifier == ServerConfig.officialDemoBundleIdentifier
        if let host = ServerConfig.host, !host.isEmpty, canUseConfiguredHost {
            request.setHost(host)
        }
        if let assetAutoCutUrl = ServerConfig.assetAutoCutUrl,
           !assetAutoCutUrl.isEmpty,
           canUseConfiguredHost {
            request.assetAutoCutUrl = assetAutoCutUrl
        }
        if !canUseConfiguredHost {
            print("Meishe official demo service requires bundle identifier \(ServerConfig.officialDemoBundleIdentifier). Configure a customer server for the current app.")
        }
        if isCurrentLanguageNoChinese() {
            request.isAbroad = 1
        }
        _ = moduleManager.prepareDownloadFolders()
        preloadWhenNetworkIsReady()
    }

    private func preloadWhenNetworkIsReady() {
        let monitor = NWPathMonitor()
        monitor.pathUpdateHandler = { [weak self] path in
            if path.status == .satisfied {
                DispatchQueue.main.async {
                    self?.moduleManager.preloadedResource()
                }
                monitor.cancel()
            }
        }
        monitor.start(queue: DispatchQueue(label: "MeisheShortVideo.Network"))
    }

    private func isCurrentLanguageNoChinese() -> Bool {
        guard let language = Locale.preferredLanguages.first else { return false }
        return !language.hasPrefix("zh")
    }

    private func runAfterMaterials(_ action: @escaping () -> Void) {
        moduleManager.downloadPrefabricatedMaterialCompletion(nil)
        action()
    }

    private func prepareMaterialsInBackground() {
        guard !isMaterialReady, !isMaterialRequestInProgress else { return }
        isMaterialRequestInProgress = true
        moduleManager.downloadPrefabricatedMaterialCompletion { [weak self] isFinish in
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.isMaterialRequestInProgress = false
                self.isMaterialReady = isFinish
                if !isFinish {
                    print("Meishe online material preparation failed. Check customer material server credentials.")
                }
            }
        }
    }

    private func downloadMaterials(message: String, afterReady: (() -> Void)?) {
        if isMaterialReady {
            setLoading(false, message: "", canRetry: false)
            afterReady?()
            return
        }
        if isMaterialRequestInProgress {
            setLoading(true, message: "素材准备中...", canRetry: false)
            return
        }
        isMaterialRequestInProgress = true
        setLoading(true, message: message, canRetry: false)
        moduleManager.downloadPrefabricatedMaterialCompletion { [weak self] isFinish in
            DispatchQueue.main.async {
                guard let self = self else { return }
                self.isMaterialRequestInProgress = false
                self.isMaterialReady = isFinish
                if isFinish {
                    self.setLoading(false, message: "", canRetry: false)
                    afterReady?()
                } else {
                    self.setLoading(true, message: "素材准备失败，请检查权限、网络和服务配置。", canRetry: true)
                }
            }
        }
    }

    private func setLoading(_ loading: Bool, message: String, canRetry: Bool) {
        loadingOverlay.isHidden = !loading
        statusLabel.text = message
        retryButton.isHidden = !canRetry
        actionRows.forEach { row in
            row.isEnabled = true
            row.alpha = 1
        }
    }

    @objc private func retryMaterials() {
        downloadMaterials(message: "素材准备中...", afterReady: nil)
    }

    private func openCapture() {
        runAfterMaterials { [weak self] in
            guard let self, let navigationController = self.navigationController else { return }
            self.moduleManager.startCapture(withPresent: navigationController, config: self.videoConfig, music: nil) { _ in }
        }
    }

    private func openDualCapture() {
        runAfterMaterials { [weak self] in
            guard let self, let navigationController = self.navigationController else { return }
            self.moduleManager.startDualCapture(withPresent: navigationController, config: self.videoConfig) { _ in }
        }
    }

    private func openEdit() {
        runAfterMaterials { [weak self] in
            guard let self, let navigationController = self.navigationController else { return }
            self.moduleManager.startEdit(withPresent: navigationController, config: self.videoConfig) { _ in }
        }
    }

    private func openDrafts() {
        let drafts = MeisheShortVideoDraftsViewController(videoConfig: videoConfig)
        navigationController?.pushViewController(drafts, animated: true)
    }
}

extension MeisheShortVideoHomeViewController: NvModuleManagerDelegate {
    func publish(
        withProjectId projectId: String,
        coverImagePath: String?,
        hasDraft: Bool,
        videoPath: String?,
        description: String?,
        videoEdit videoEditNavigationController: UINavigationController
    ) {
        let publish = MeisheShortVideoPublishViewController(
            projectId: projectId,
            coverImagePath: coverImagePath,
            hasDraft: hasDraft,
            videoPath: videoPath,
            draftDescription: description,
            videoEditNavigationController: videoEditNavigationController
        )
        videoEditNavigationController.pushViewController(publish, animated: true)
    }
}
"""
    write_text(
        target_root / "MeisheShortVideo" / "MeisheShortVideoHomeViewController.swift",
        content,
        target_root,
        report,
        "Generated native iOS Swift home view controller",
    )


def create_native_ios_drafts_view_controller(
    target_root: Path,
    report: Report,
    autocut_draft_fallback_supported: bool,
) -> None:
    content = r"""import UIKit
import NvShortVideoCore

final class MeisheShortVideoDraftsViewController: UIViewController {
    private let videoConfig: NvVideoConfig
    private var drafts: [NvEditProjectInfo] = []
    private let contentStack = UIStackView()

    init(videoConfig: NvVideoConfig = NvVideoConfig()) {
        self.videoConfig = videoConfig
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) {
        self.videoConfig = NvVideoConfig()
        super.init(coder: coder)
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = MeisheShortVideoStyle.pageBackground
        buildView()
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        reloadDrafts()
    }

    private func buildView() {
        let root = UIStackView()
        root.translatesAutoresizingMaskIntoConstraints = false
        root.axis = .vertical
        root.backgroundColor = MeisheShortVideoStyle.pageBackground
        view.addSubview(root)

        root.addArrangedSubview(MeisheShortVideoStyle.topBar(title: "本地草稿箱", owner: self, action: #selector(goBack)))

        let scroll = UIScrollView()
        scroll.translatesAutoresizingMaskIntoConstraints = false
        root.addArrangedSubview(scroll)

        contentStack.translatesAutoresizingMaskIntoConstraints = false
        contentStack.axis = .vertical
        contentStack.spacing = 20
        contentStack.layoutMargins = UIEdgeInsets(top: 28, left: 24, bottom: 42, right: 24)
        contentStack.isLayoutMarginsRelativeArrangement = true
        scroll.addSubview(contentStack)

        NSLayoutConstraint.activate([
            root.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            root.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            root.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            root.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            root.arrangedSubviews[0].heightAnchor.constraint(equalToConstant: 58),
            contentStack.leadingAnchor.constraint(equalTo: scroll.contentLayoutGuide.leadingAnchor),
            contentStack.trailingAnchor.constraint(equalTo: scroll.contentLayoutGuide.trailingAnchor),
            contentStack.topAnchor.constraint(equalTo: scroll.contentLayoutGuide.topAnchor),
            contentStack.bottomAnchor.constraint(equalTo: scroll.contentLayoutGuide.bottomAnchor),
            contentStack.widthAnchor.constraint(equalTo: scroll.frameLayoutGuide.widthAnchor)
        ])
    }

    private func reloadDrafts() {
        drafts = NvModuleManager.projectList()

        contentStack.arrangedSubviews.forEach { $0.removeFromSuperview() }
        if drafts.isEmpty {
            renderEmptyState()
        } else {
            renderDraftRows()
        }
    }

    private func renderEmptyState() {
        let empty = MeisheShortVideoStyle.label("没有草稿啦！", size: 24, weight: .regular)
        empty.textAlignment = .center
        contentStack.addArrangedSubview(empty)
        NSLayoutConstraint.activate([
            empty.heightAnchor.constraint(greaterThanOrEqualToConstant: 360)
        ])
    }

    private func renderDraftRows() {
        let notice = MeisheShortVideoStyle.label("温馨提示： 卸载应用后，草稿也会被删除", size: 20, weight: .regular)
        contentStack.addArrangedSubview(notice)
        for draft in drafts {
            contentStack.addArrangedSubview(row(for: draft))
        }
    }

    private func row(for draft: NvEditProjectInfo) -> UIControl {
        let row = MeisheShortVideoTapControl()
        row.translatesAutoresizingMaskIntoConstraints = false
        row.backgroundColor = .clear
        row.onTap { [weak self] in
            self?.openDraft(draft)
        }
        let longPress = UILongPressGestureRecognizer(target: self, action: #selector(confirmDeleteDraft(_:)))
        longPress.cancelsTouchesInView = false
        row.addGestureRecognizer(longPress)

        let stack = UIStackView()
        stack.translatesAutoresizingMaskIntoConstraints = false
        stack.axis = .horizontal
        stack.alignment = .center
        stack.spacing = 26
        stack.isUserInteractionEnabled = false
        row.addSubview(stack)

        let title = draftTitle(draft)
        let thumbnail = MeisheShortVideoStyle.thumbnail(path: draft.coverImagePath, fallbackTitle: title)
        stack.addArrangedSubview(thumbnail)

        let titleLabel = MeisheShortVideoStyle.label(title, size: 22, weight: .regular)
        stack.addArrangedSubview(titleLabel)

        NSLayoutConstraint.activate([
            row.heightAnchor.constraint(equalToConstant: 110),
            stack.leadingAnchor.constraint(equalTo: row.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: row.trailingAnchor),
            stack.topAnchor.constraint(equalTo: row.topAnchor),
            stack.bottomAnchor.constraint(equalTo: row.bottomAnchor),
            thumbnail.widthAnchor.constraint(equalToConstant: 96),
            thumbnail.heightAnchor.constraint(equalToConstant: 96)
        ])
        return row
    }

    private func draftTitle(_ draft: NvEditProjectInfo) -> String {
        if let value = draft.projectDescription?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty {
            return value
        }
        if let value = draft.defaultProjectDescription?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty {
            return value
        }
        return MeisheShortVideoStyle.fallbackDraftTitle()
    }

    private func openDraft(_ draft: NvEditProjectInfo) {
        NvModuleManager.sharedInstance().reeditProject(draft, presentViewController: self, config: videoConfig)
    }

    @objc private func confirmDeleteDraft(_ gesture: UILongPressGestureRecognizer) {
        guard gesture.state == .began, let row = gesture.view else { return }
        let index = contentStack.arrangedSubviews.firstIndex(of: row)
        let draftIndex = drafts.isEmpty ? nil : index.map { max($0 - 1, 0) }
        guard let draftIndex, drafts.indices.contains(draftIndex) else { return }
        let draft = drafts[draftIndex]
        let alert = UIAlertController(title: "删除草稿", message: "确定删除这个草稿吗？", preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "取消", style: .cancel))
        alert.addAction(UIAlertAction(title: "删除", style: .destructive) { [weak self] _ in
            if NvModuleManager.deleteDraft(draft.projectId) {
                __AUTOCUT_DRAFT_DELETE_CLEANUP__
                self?.reloadDrafts()
            }
        })
        present(alert, animated: true)
    }

    @objc private func goBack() {
        navigationController?.popViewController(animated: true)
    }
}
"""
    delete_cleanup = (
        "MeisheAutoCutDraftStore.deleteRenderedMedia(projectId: draft.projectId)"
        if autocut_draft_fallback_supported
        else ""
    )
    content = content.replace("__AUTOCUT_DRAFT_DELETE_CLEANUP__", delete_cleanup)
    write_text(
        target_root / "MeisheShortVideo" / "MeisheShortVideoDraftsViewController.swift",
        content,
        target_root,
        report,
        "Generated native iOS Swift drafts view controller",
    )


def native_ios_autocut_draft_store_source() -> str:
    return r"""enum MeisheAutoCutDraftStore {
    private static let mediaDirectoryName = "NvAutoCutDraftMedia"
    private static let mediaDefaultsKey = "NvShortVideoRenderedDraftMedia"

    static func stageRenderedVideo(
        videoPath: String?,
        projectDescription: String,
        coverImagePath: String?
    ) -> String? {
        guard let localPath = normalizedLocalPath(videoPath),
              FileManager.default.fileExists(atPath: localPath) else {
            print("[MeisheAutoCutDraft] rendered video is unavailable path=\(videoPath ?? "nil")")
            return nil
        }
        guard let durableVideoURL = copyToPersistentStorage(localPath: localPath) else {
            return nil
        }

        var keepDurableVideo = false
        defer {
            if !keepDurableVideo {
                try? FileManager.default.removeItem(at: durableVideoURL)
            }
        }

        if NvTimelineDataManager.managerAvailable() {
            NvTimelineDataManager.destroySharedInstance(destroyContext: false)
        }
        let manager = NvTimelineDataManager.sharedInstance()
        defer {
            NvTimelineDataManager.destroySharedInstance(destroyContext: false)
        }

        let created = manager.newProject(
            localFilePaths: [durableVideoURL.path],
            configration: NvProEditConfig()
        )
        guard created,
              let model = manager.timelineModel,
              !model.projectId.isEmpty else {
            print("[MeisheAutoCutDraft] standard project creation failed path=\(durableVideoURL.path)")
            return nil
        }

        let draftProjectId = model.projectId
        let stored = NvProjectManager.storeCurrentProject(
            projectId: draftProjectId,
            projectDescription: projectDescription
        )
        if stored,
           let coverImagePath,
           !coverImagePath.isEmpty,
           let image = UIImage(contentsOfFile: coverImagePath) {
            _ = NvProjectManager.updateCover(image: image, projectId: draftProjectId)
        }

        let persisted = stored && NvModuleManager.projectInfoForProject(draftProjectId) != nil
        if persisted {
            var mediaByProject = renderedMediaByProject()
            mediaByProject[draftProjectId] = durableVideoURL.path
            persistRenderedMediaByProject(mediaByProject)
            keepDurableVideo = true
        }
        print("[MeisheAutoCutDraft] staged taskSource=\(localPath) draftProjectId=\(draftProjectId) durableSource=\(durableVideoURL.path) persisted=\(persisted)")
        return persisted ? draftProjectId : nil
    }

    static func deleteRenderedMedia(projectId: String) {
        var mediaByProject = renderedMediaByProject()
        guard let mediaPath = mediaByProject.removeValue(forKey: projectId) else {
            return
        }

        do {
            if FileManager.default.fileExists(atPath: mediaPath) {
                try FileManager.default.removeItem(atPath: mediaPath)
            }
            persistRenderedMediaByProject(mediaByProject)
            print("[MeisheAutoCutDraft] deleted projectId=\(projectId) path=\(mediaPath)")
        } catch {
            print("[MeisheAutoCutDraft] cleanup failed projectId=\(projectId) error=\(error)")
        }
    }

    private static func normalizedLocalPath(_ rawPath: String?) -> String? {
        guard let rawPath, !rawPath.isEmpty else { return nil }
        if rawPath.hasPrefix("file://"), let url = URL(string: rawPath) {
            return url.path
        }
        return rawPath
    }

    private static func copyToPersistentStorage(localPath: String) -> URL? {
        let fileManager = FileManager.default
        guard let documentsURL = fileManager.urls(for: .documentDirectory, in: .userDomainMask).first else {
            return nil
        }
        let mediaDirectoryURL = documentsURL.appendingPathComponent(mediaDirectoryName, isDirectory: true)
        let sourceURL = URL(fileURLWithPath: localPath)
        let fileExtension = sourceURL.pathExtension.isEmpty ? "mp4" : sourceURL.pathExtension
        let destinationURL = mediaDirectoryURL
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension(fileExtension)

        do {
            try fileManager.createDirectory(at: mediaDirectoryURL, withIntermediateDirectories: true)
            try fileManager.copyItem(at: sourceURL, to: destinationURL)
            print("[MeisheAutoCutDraft] copied source=\(localPath) destination=\(destinationURL.path)")
            return destinationURL
        } catch {
            print("[MeisheAutoCutDraft] copy failed source=\(localPath) error=\(error)")
            return nil
        }
    }

    private static func renderedMediaByProject() -> [String: String] {
        UserDefaults.standard.dictionary(forKey: mediaDefaultsKey) as? [String: String] ?? [:]
    }

    private static func persistRenderedMediaByProject(_ mediaByProject: [String: String]) {
        if mediaByProject.isEmpty {
            UserDefaults.standard.removeObject(forKey: mediaDefaultsKey)
        } else {
            UserDefaults.standard.set(mediaByProject, forKey: mediaDefaultsKey)
        }
    }
}

"""


def create_native_ios_publish_view_controller(
    target_root: Path,
    report: Report,
    autocut_draft_fallback_supported: bool,
) -> None:
    content = r"""import UIKit
import NvShortVideoCore

__AUTOCUT_DRAFT_STORE__
final class MeisheShortVideoPublishViewController: UIViewController {
    private let moduleManager = NvModuleManager.sharedInstance()
    private let projectId: String
    private let coverImagePath: String?
    private let hasDraft: Bool
    private let initialVideoPath: String?
    private let draftDescription: String?
    private weak var videoEditNavigationController: UINavigationController?

    private let scrollView = UIScrollView()
    private let draftInput = UITextView()
    private let statusLabel = MeisheShortVideoStyle.label("请选择保存草稿或导出视频", size: 15, color: MeisheShortVideoStyle.textSecondary)
    private let progressView = UIProgressView(progressViewStyle: .bar)
    private let saveDraftButton = MeisheShortVideoStyle.actionButton(title: "保存草稿", filled: false)
    private let exportButton = MeisheShortVideoStyle.actionButton(title: "导出视频", filled: true)

    init(
        projectId: String,
        coverImagePath: String?,
        hasDraft: Bool,
        videoPath: String?,
        draftDescription: String?,
        videoEditNavigationController: UINavigationController
    ) {
        self.projectId = projectId
        self.coverImagePath = coverImagePath
        self.hasDraft = hasDraft
        self.initialVideoPath = videoPath
        self.draftDescription = draftDescription
        self.videoEditNavigationController = videoEditNavigationController
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) {
        self.projectId = ""
        self.coverImagePath = ""
        self.hasDraft = true
        self.initialVideoPath = nil
        self.draftDescription = nil
        super.init(coder: coder)
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = MeisheShortVideoStyle.pageBackground
        bindCompileDelegate()
        buildView()
        configureKeyboardHandling()
    }

    deinit {
        NotificationCenter.default.removeObserver(self)
    }

    private func buildView() {
        let root = UIStackView()
        root.translatesAutoresizingMaskIntoConstraints = false
        root.axis = .vertical
        root.backgroundColor = MeisheShortVideoStyle.pageBackground
        view.addSubview(root)

        root.addArrangedSubview(MeisheShortVideoStyle.topBar(title: "作品发布", owner: self, action: #selector(returnToEditor)))

        scrollView.translatesAutoresizingMaskIntoConstraints = false
        root.addArrangedSubview(scrollView)

        let content = UIStackView()
        content.translatesAutoresizingMaskIntoConstraints = false
        content.axis = .vertical
        content.spacing = 0
        content.layoutMargins = UIEdgeInsets(top: 24, left: 24, bottom: 42, right: 24)
        content.isLayoutMarginsRelativeArrangement = true
        scrollView.addSubview(content)

        let notice = MeisheShortVideoStyle.label("温馨提示： 卸载应用后，草稿也会被删除", size: 20, weight: .regular)
        content.addArrangedSubview(notice)
        content.setCustomSpacing(34, after: notice)

        content.addArrangedSubview(projectRow())
        content.setCustomSpacing(40, after: content.arrangedSubviews.last!)

        configureDraftInput()
        content.addArrangedSubview(draftInput)
        content.setCustomSpacing(16, after: draftInput)

        content.addArrangedSubview(statusLabel)
        content.setCustomSpacing(12, after: statusLabel)

        progressView.translatesAutoresizingMaskIntoConstraints = false
        progressView.progressTintColor = MeisheShortVideoStyle.accent
        progressView.trackTintColor = MeisheShortVideoStyle.color(0x333943)
        progressView.isHidden = true
        content.addArrangedSubview(progressView)
        content.setCustomSpacing(22, after: progressView)

        __AUTOCUT_DRAFT_BUTTON_VISIBILITY__
        saveDraftButton.addTarget(self, action: #selector(saveDraft), for: .touchUpInside)
        content.addArrangedSubview(saveDraftButton)
        content.setCustomSpacing(12, after: saveDraftButton)

        exportButton.addTarget(self, action: #selector(exportVideo), for: .touchUpInside)
        content.addArrangedSubview(exportButton)

        NSLayoutConstraint.activate([
            root.leadingAnchor.constraint(equalTo: view.leadingAnchor),
            root.trailingAnchor.constraint(equalTo: view.trailingAnchor),
            root.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor),
            root.bottomAnchor.constraint(equalTo: view.bottomAnchor),
            root.arrangedSubviews[0].heightAnchor.constraint(equalToConstant: 58),
            content.leadingAnchor.constraint(equalTo: scrollView.contentLayoutGuide.leadingAnchor),
            content.trailingAnchor.constraint(equalTo: scrollView.contentLayoutGuide.trailingAnchor),
            content.topAnchor.constraint(equalTo: scrollView.contentLayoutGuide.topAnchor),
            content.bottomAnchor.constraint(equalTo: scrollView.contentLayoutGuide.bottomAnchor),
            content.widthAnchor.constraint(equalTo: scrollView.frameLayoutGuide.widthAnchor),
            draftInput.heightAnchor.constraint(equalToConstant: 68),
            progressView.heightAnchor.constraint(equalToConstant: 4),
            saveDraftButton.heightAnchor.constraint(equalToConstant: 48),
            exportButton.heightAnchor.constraint(equalToConstant: 48)
        ])
    }

    private func projectRow() -> UIView {
        let row = UIView()
        row.translatesAutoresizingMaskIntoConstraints = false

        let stack = UIStackView()
        stack.translatesAutoresizingMaskIntoConstraints = false
        stack.axis = .horizontal
        stack.alignment = .center
        stack.spacing = 26
        row.addSubview(stack)

        let coverPath = coverImagePath?.isEmpty == false ? coverImagePath : initialVideoPath
        let thumbnail = MeisheShortVideoStyle.thumbnail(path: coverPath, fallbackTitle: projectTitle())
        stack.addArrangedSubview(thumbnail)

        let titleLabel = MeisheShortVideoStyle.label(projectTitle(), size: 22, weight: .regular)
        stack.addArrangedSubview(titleLabel)

        NSLayoutConstraint.activate([
            row.heightAnchor.constraint(equalToConstant: 100),
            stack.leadingAnchor.constraint(equalTo: row.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: row.trailingAnchor),
            stack.topAnchor.constraint(equalTo: row.topAnchor),
            stack.bottomAnchor.constraint(equalTo: row.bottomAnchor),
            thumbnail.widthAnchor.constraint(equalToConstant: 96),
            thumbnail.heightAnchor.constraint(equalToConstant: 96)
        ])
        return row
    }

    private func configureDraftInput() {
        draftInput.translatesAutoresizingMaskIntoConstraints = false
        draftInput.text = draftDescription
        draftInput.textColor = .white
        draftInput.font = .systemFont(ofSize: 15)
        draftInput.backgroundColor = MeisheShortVideoStyle.color(0x1D1D1D)
        draftInput.textContainerInset = UIEdgeInsets(top: 10, left: 10, bottom: 10, right: 10)
        MeisheShortVideoStyle.rounded(draftInput, radius: 8)

        let toolbar = UIToolbar()
        toolbar.sizeToFit()
        toolbar.items = [
            UIBarButtonItem(barButtonSystemItem: .flexibleSpace, target: nil, action: nil),
            UIBarButtonItem(title: "完成", style: .done, target: self, action: #selector(dismissKeyboard))
        ]
        draftInput.inputAccessoryView = toolbar
    }

    private func configureKeyboardHandling() {
        let tap = UITapGestureRecognizer(target: self, action: #selector(dismissKeyboard))
        tap.cancelsTouchesInView = false
        view.addGestureRecognizer(tap)
        scrollView.keyboardDismissMode = .interactive

        NotificationCenter.default.addObserver(
            self,
            selector: #selector(keyboardWillChangeFrame(_:)),
            name: UIResponder.keyboardWillChangeFrameNotification,
            object: nil
        )
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(keyboardWillHide(_:)),
            name: UIResponder.keyboardWillHideNotification,
            object: nil
        )
    }

    @objc private func dismissKeyboard() {
        view.endEditing(true)
    }

    @objc private func keyboardWillChangeFrame(_ notification: Notification) {
        guard let frameValue = notification.userInfo?[UIResponder.keyboardFrameEndUserInfoKey] as? NSValue else { return }
        let frame = view.convert(frameValue.cgRectValue, from: nil)
        updateKeyboardInset(max(0, view.bounds.maxY - frame.minY))

        if draftInput.isFirstResponder {
            let inputFrame = draftInput.convert(draftInput.bounds, to: scrollView).insetBy(dx: 0, dy: -16)
            scrollView.scrollRectToVisible(inputFrame, animated: true)
        }
    }

    @objc private func keyboardWillHide(_ notification: Notification) {
        updateKeyboardInset(0)
    }

    private func updateKeyboardInset(_ bottom: CGFloat) {
        UIView.animate(withDuration: 0.25) {
            self.scrollView.contentInset.bottom = bottom
            self.scrollView.verticalScrollIndicatorInsets.bottom = bottom
        }
    }

    private func projectTitle() -> String {
        if let draftDescription = draftDescription {
            let trimmed = draftDescription.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty {
                return trimmed
            }
        }
        return MeisheShortVideoStyle.fallbackDraftTitle()
    }

    private func bindCompileDelegate() {
        moduleManager.compileDelegate = self
    }

    @objc private func saveDraft() {
        __AUTOCUT_DRAFT_SAVE_IMPLEMENTATION__
    }

    @objc private func exportVideo() {
        progressView.isHidden = false
        progressView.progress = 0
        statusLabel.text = "视频导出中..."
        let ok = moduleManager.compileCurrentTimeline()
        if !ok {
            statusLabel.text = "导出启动失败，请检查 SDK 状态。"
            progressView.isHidden = true
        }
    }

    @objc private func returnToEditor() {
        navigationController?.popViewController(animated: true)
    }

    private func finishEditingFlow() {
        let finish = { [weak self] in
            guard let self else { return }
            _ = self.moduleManager.exitVideoEdit(self.projectId)
        }

        if let editNavigationController = videoEditNavigationController,
           let presenter = editNavigationController.presentingViewController,
           let outerPresenter = presenter.presentingViewController {
            outerPresenter.dismiss(animated: true, completion: finish)
        } else if let editNavigationController = videoEditNavigationController,
                  editNavigationController.presentingViewController != nil {
            editNavigationController.dismiss(animated: true, completion: finish)
        } else {
            navigationController?.popToRootViewController(animated: true)
            finish()
        }
    }
}

extension MeisheShortVideoPublishViewController: NvModuleManagerCompileStateDelegate {
    func didCompileCompleted(_ outputPath: String?, error: Error?) {
        DispatchQueue.main.async { [weak self] in
            guard let self = self else { return }
            self.progressView.progress = 1
            self.statusLabel.text = error == nil ? "导出完成：\(outputPath ?? "")" : "导出失败：\(error?.localizedDescription ?? "未知错误")"
        }
    }

    func didCompileFloatProgress(_ progress: Float) {
        DispatchQueue.main.async { [weak self] in
            let normalized = progress > 1 ? progress / 100 : progress
            let clamped = max(0, min(normalized, 1))
            self?.progressView.isHidden = false
            self?.progressView.progress = clamped
            self?.statusLabel.text = "视频导出中 \(Int(clamped * 100))%"
        }
    }

    func didGenerateImagesType(_ type: Int32, results: [String]?, error: Error?) {
        DispatchQueue.main.async { [weak self] in
            if let error {
                self?.statusLabel.text = "图片生成失败：\(error.localizedDescription)"
            }
        }
    }
}
"""
    if autocut_draft_fallback_supported:
        button_visibility = """// ShortVideo 2.0.2.1 reports hasDraft=false for AutoCut. Its callback ID
        // is a temporary task ID, so the rendered result is converted to a standard draft on save.
        saveDraftButton.isHidden = false"""
        save_implementation = r"""saveDraftButton.isEnabled = false
        statusLabel.text = hasDraft ? "正在保存草稿..." : "正在保存一键成片草稿..."

        let description = draftInput.text ?? ""
        var savedDraftProjectId = projectId
        var persisted = false

        if hasDraft {
            let standardSaved = moduleManager.saveCurrentDraft(withDraftInfo: description)
            persisted = standardSaved && isDraftListable(projectId: projectId)
            if !persisted {
                let fallbackSaved = NvProjectManager.storeCurrentProject(
                    projectId: projectId,
                    projectDescription: description
                )
                persisted = fallbackSaved && isDraftListable(projectId: projectId)
            }
        } else {
            let renderedVideoPath: String? = initialVideoPath?.isEmpty == false
                ? initialVideoPath
                : moduleManager.publishInfo.videoPath
            if let stagedProjectId = MeisheAutoCutDraftStore.stageRenderedVideo(
                videoPath: renderedVideoPath,
                projectDescription: description,
                coverImagePath: coverImagePath
            ) {
                savedDraftProjectId = stagedProjectId
                persisted = isDraftListable(projectId: stagedProjectId)
            }
        }

        print(
            "[MeisheAutoCutDraft] save taskId=\(projectId) draftProjectId=\(savedDraftProjectId) " +
            "hasDraft=\(hasDraft) persisted=\(persisted)"
        )
        saveDraftButton.isEnabled = true
        statusLabel.text = persisted ? "草稿已保存" : "草稿保存失败：项目未进入草稿列表。"
        if persisted {
            finishEditingFlow()
        }
    }

    private func isDraftListable(projectId: String) -> Bool {
        guard !projectId.isEmpty else { return false }
        return NvModuleManager.projectInfoForProject(projectId) != nil"""
    else:
        button_visibility = "saveDraftButton.isHidden = !hasDraft"
        save_implementation = r"""let ok = moduleManager.saveCurrentDraft(withDraftInfo: draftInput.text)
        statusLabel.text = ok ? "草稿已保存" : "草稿保存失败，请检查 SDK 状态。"
        if ok {
            finishEditingFlow()
        }"""
    content = content.replace(
        "__AUTOCUT_DRAFT_STORE__",
        native_ios_autocut_draft_store_source() if autocut_draft_fallback_supported else "",
    )
    content = content.replace("__AUTOCUT_DRAFT_BUTTON_VISIBILITY__", button_visibility)
    content = content.replace("__AUTOCUT_DRAFT_SAVE_IMPLEMENTATION__", save_implementation)
    write_text(
        target_root / "MeisheShortVideo" / "MeisheShortVideoPublishViewController.swift",
        content,
        target_root,
        report,
        "Generated native iOS Swift publish view controller",
    )


def create_native_ios_swift_ui(
    target_root: Path,
    report: Report,
    autocut_draft_fallback_supported: bool,
) -> None:
    copy_ios_demo_ui_assets(target_root, report)
    create_native_ios_style_helper(target_root, report)
    create_native_ios_feature_config(target_root, report)
    create_native_ios_home_view_controller(target_root, report)
    create_native_ios_drafts_view_controller(target_root, report, autocut_draft_fallback_supported)
    create_native_ios_publish_view_controller(target_root, report, autocut_draft_fallback_supported)


def place_ios_license(target_root: Path, args: argparse.Namespace, report: Report) -> None:
    if args.license_path:
        copy_file(Path(args.license_path), target_root / "MeisheShortVideo" / "meishesdk.lic", target_root, report, "Copied iOS license file")
        report.add_next_check("Native iOS: add `MeisheShortVideo/meishesdk.lic` to the Xcode target bundle resources if Xcode did not add it automatically.")
    else:
        report.add_warning(LICENSE_HELP)
        report.add_user_configuration(
            "Production license: register the final Bundle Identifier with Meishe, obtain the matching real `meishesdk.lic`, then re-run with `--license-path` and verify target membership. The no-license first-run path includes a watermark."
        )


def write_native_ios_self_check(
    target_root: Path,
    report: Report,
    autocut_draft_fallback_supported: bool,
) -> None:
    draft_note = (
        "- 当前输入包匹配 ShortVideo `2.0.2.1` 草稿与时间线 API：普通编辑继续使用 `saveCurrentDraft`；一键成片回调 ID 只作为临时任务 ID，保存时把渲染结果复制到 App 运行时沙箱，并通过 `NvTimelineDataManager.newProject` 创建新的标准可编辑草稿。草稿删除时同步清理该运行时媒体副本。"
        if autocut_draft_fallback_supported
        else "- 当前输入包未同时匹配已验证的一键成片草稿和 Swift 时间线 API 形状；生成页保留 SDK `hasDraft` 行为，不对未知版本强行应用转换补丁。"
    )
    content = f"""# 原生 iOS 素材请求自检

## 典型现象

- 拍摄、合拍、编辑和草稿能够打开，但美颜、滤镜、贴纸或音乐等在线素材列表为空。
- 内置效果仍可使用，因此页面能打开不代表素材请求成功。

## 已验证原因

1. 官方 Demo 服务要求 Bundle Identifier 精确为 `com.meishe.duanshipindemo`。
2. ShortVideo `2.0.2.1` 官方原生 iOS Example 的应用 plist 使用 `NSAllowsArbitraryLoads = true`；临时官方 Demo 身份未对齐该 ATS 配置时，素材/CDN子链路可能被拦截。
3. 官方 Demo 在进入拍摄、合拍和编辑前都会再次非阻塞触发预制素材下载；只在首页准备一次不等价。

## 生成代码自检

- 只有目标 Bundle Identifier 为 `com.meishe.duanshipindemo`，且输入官方包 Example plist 本身声明全局 ATS 时，才把 `NSAllowsArbitraryLoads = true` 写入应用 plist。
- 客户 Bundle Identifier 不启用全局 ATS，只能根据真实 API/CDN域名配置最小例外。
- plist 补丁只能修改 Xcode 应用 Target 的 Info.plist，不得递归修改 `vendor/meishe/Pods-NvShortVideoEdit` 中的 Example、framework 或 xcframework plist。
- `MeisheShortVideoHomeViewController.setWebConfig()` 长期持有并设置 `dependencyDelegate`，然后配置 host、准备下载目录和网络预加载。
- `MeisheFeatureConfig.apply(to:)` 从用户可编辑 Swift 文件应用有序菜单、AutoCut、拍摄、编辑和导出配置；删除菜单项会让 SDK 重排 UI，不使用隐藏占位。原生 iOS 使用完整 `assetAutoCutUrl`。
- 拍摄、合拍和编辑入口在打开 SDK 页面前必须无条件、非阻塞调用 `downloadPrefabricatedMaterialCompletion(nil)`；首页请求的 `isMaterialRequestInProgress` 状态不能跳过这次刷新，失败也不得阻塞四个主要入口。
- ShortVideo `2.0.2.1` 的 `NvHttpRequest` 不提供可写的 `clientId`、`clientSecret`、`assemblyId` 属性，生成代码不得直接访问它们；客户鉴权必须按美摄提供的请求委托和服务合同实现。
- iOS 的 `hasDraft` 表示 SDK 建议发布页是否显示草稿按钮，不表示草稿已经持久化。一键成片在已验证版本会返回 `false`。
{draft_note}

## 手工验收

美摄短视频 Demo 必须安装到真实 iPhone 或 iPad；iOS Simulator 和其他虚拟设备不受支持，不能用于运行或验收。

1. 清理旧缓存或重新安装 App，首次启动后允许相机、麦克风、相册和本地网络权限。
2. 进入编辑，逐项检查美颜、滤镜、贴纸和音乐在线列表，至少下载并实际使用一个在线素材。
3. 分别从编辑素材选择、模板页和拍摄模板菜单进入一键成片，确认生成结果进入标准编辑页。
4. 在标准编辑页点击下一步，分别验证保存草稿、草稿继续编辑和导出视频。
5. 若仍为空，检查 Xcode 日志中的 ATS、最终请求 URL、HTTP 状态、业务码、Bundle Identifier 白名单和 CDN 错误。
6. 同时确认素材失败不会阻塞拍摄、合拍、编辑、作品发布、草稿保存和草稿继续编辑。

正式项目必须核对全部 API 与 CDN 域名，把全局 ATS 收紧为最小域名例外。需要真机完成以上验收时，先列出全部设备操作、原因和预期信息，让用户选择“用户执行”或“自动执行”；自动执行会额外消耗 Token 和时间。
"""
    write_text(
        target_root / "meishe_native_ios_self_check.md",
        content,
        target_root,
        report,
        "Generated native iOS material-request self-check handoff",
    )


def write_ios_handoff(
    target_root: Path,
    pods_package: Path,
    ios_target: str,
    official_demo_ats_enabled: bool,
    autocut_draft_fallback_supported: bool,
    report: Report,
) -> None:
    rel_pods_package = project_local_path(pods_package, target_root)
    ats_note = (
        "Official-Demo ATS compatibility: the supplied package Example declares "
        "`NSAllowsArbitraryLoads = true`, so it is mirrored only for the temporary "
        "`com.meishe.duanshipindemo` app. Replace it with verified domain-specific exceptions before production."
        if official_demo_ats_enabled
        else "ATS: global `NSAllowsArbitraryLoads` was not enabled; customer apps must use only verified domain-specific exceptions."
    )
    draft_note = (
        "AutoCut draft compatibility: the callback `projectId` remains the temporary SDK task ID. On save, generated code copies the rendered result into the app runtime sandbox, creates a new standard editable draft through `NvTimelineDataManager.newProject`, verifies the new draft ID in `NvModuleManager.projectList`, and removes the mapped media when that draft is deleted. No media file is bundled in the skill."
        if autocut_draft_fallback_supported
        else "AutoCut draft compatibility: the supplied SDK did not match both the verified project-manager and Swift timeline API shapes, so unknown-version conversion code was not generated."
    )
    content = f"""# Meishe Native iOS ShortVideo Handoff

- Xcode target: `{ios_target}`
- Real-device requirement: run and accept the Meishe ShortVideo Demo only on a physical iPhone or iPad; iOS Simulator and other virtual devices are unsupported.
- Local CocoaPods package: `{pods_package}`
- Pod dependency: `pod 'NvShortVideoEdit', :path => './{rel_pods_package}', :inhibit_warnings => true`
- Podfile boundary: preserve existing sources and `post_install`; add `platform :ios, '12.0'` / `use_frameworks!` only when missing, and never rewrite unrelated Pod targets.
- Permissions: camera, microphone, photo library, Apple Music, location, and local network.
- {ats_note}
- License: optional for running; without a real `.lic`, output contains a MEISHE watermark.
- Generated Swift UI/config: `MeisheFeatureConfig.swift`, `MeisheShortVideoHomeViewController.swift`, `MeisheShortVideoDraftsViewController.swift`, `MeisheShortVideoPublishViewController.swift`, and `MeisheShortVideoStyle.swift`. The feature file is generated once and retained on later runs.
- Command-level configuration handoff: `meishe_configuration_handoff.md`; it records absolute edit paths, the workspace command, Target Membership, Build & Run steps, and success markers for this generated project.
- Copied UI assets: `MeisheShortVideo/Assets/meishe_home_banner.jpg` and the four `meishe_icon_*` images.
- API anchors: `NvModuleManager.sharedInstance()`, `downloadPrefabricatedMaterialCompletion`, `startCapture`, `startDualCapture`, `startEdit`, `NvModuleManager.projectList()`, `reeditProject`, `deleteDraft`, `saveCurrentDraft`, `compileCurrentTimeline`, and `exitVideoEdit`.
- Demo UI style: follow the bundled skill reference `references/demo-ui-style.md`.
- Feature configuration: edit `MeisheShortVideo/MeisheFeatureConfig.swift`; ordered menu arrays remove entries and reflow SDK UI. Default AutoCut remains enabled and completion follows the standard editor, then Next opens the generated save-draft/export page.
- {draft_note}

## Next Xcode Steps

1. Follow the report's dependency-installation choice before CocoaPods is run; the integration script never downloads Pods by itself.
2. After the approved CocoaPods step succeeds, open the generated `.xcworkspace`, not the `.xcodeproj`.
3. Add `MeisheShortVideo/*.swift` (including `MeisheFeatureConfig.swift`) and `MeisheShortVideo/Assets/*` to the intended app target if Xcode did not add them automatically.
4. Add `MeisheShortVideo/meishesdk.lic` to bundle resources if a real license was supplied.
5. Wire your app's entry/navigation to present or push `MeisheShortVideoHomeViewController`.
6. If your SDK version requires explicit compile delegate registration for publish progress, bind `NvModuleManagerCompileStateDelegate` to `MeisheShortVideoPublishViewController` according to Xcode's module headers.
7. Verify the generated UI against the enhanced docs:
   - `assets/shortvideo-docs/markdown/native_quickstart/doc_ch/quickstart_ch.md`
   - `assets/shortvideo-docs/markdown/native_quickstart/doc_ch/functionConfiguration_ch.md`
   - `assets/shortvideo-docs/markdown/native_quickstart/doc_ch/PrefabricatedMaterial_ch.md`

## Server Configuration

- The generated demo mirrors the official iOS demo: `host` is `https://mall.meishesdk.com/api/shortvideo/v1` and `assetAutoCutUrl` is `https://creative.meishesdk.com/api/app/aivideo/asset/all/1`.
- The official demo service requires the app Bundle Identifier to be exactly `com.meishe.duanshipindemo`. For a user-provided project with another Bundle Identifier, tell the user this restriction before runtime verification; do not silently change the existing app identity.
- For a project created in the current task, run integration with `--ios-bundle-identifier com.meishe.duanshipindemo`. For an existing project, omit the option to preserve the current App Target identity, or pass it explicitly only after the user requests the change.
- `--ios-bundle-identifier` updates only the confirmed application target build configurations; test and extension targets are not modified.
- Configuration entry: `MeisheShortVideo/MeisheShortVideoHomeViewController.swift` -> `ServerConfig`.
- To use another Bundle Identifier, replace `host` with the customer server base URL and update `assetAutoCutUrl` only when required. ShortVideo 2.0.2.1 does not expose writable `clientId`, `clientSecret`, or `assemblyId` properties on `NvHttpRequest`; customer authentication must follow Meishe's request delegate/service contract.
- Obtain the server contract, deployment, credentials, Bundle Identifier allowlist, and expected test account from Meishe/customer backend support. Then verify material categories, list data, thumbnails, downloads, prefabricated resources, AutoCut (when enabled), and core editing separately on a real device.
- Full field mapping and verification checklist: skill reference `references/customer-server.md`.
- Empty online material lists: follow `meishe_native_ios_self_check.md` before changing SDK code.

## User-Specific Settings

- The first-run configuration is for integration verification, not production handoff.
- In Xcode, replace any temporary Team, certificate, and provisioning profile with the user's signing configuration.
- Use the final Bundle Identifier consistently for signing, the customer server allowlist, and the formal Meishe license.
- Replace the no-license/watermark path with the matching production `meishesdk.lic` before release.

## Required Demo UI

- Home screen: dark background, title `素材上新`, fixed `meishe_home_banner`, panel text `请选择所需的功能` / `功能列表`, and four rows `拍摄`, `合拍`, `编辑`, `草稿` with the matching custom icons.
- Keep the home content within one viewport. Use screen-height percentages or Auto Layout constraints for banner height, spacing, and bottom whitespace; keep row height around 46-52 pt and preserve visible bottom whitespace.
- Do not add footer text such as `拍动 v2.0.0`, `用户协议`, or `隐私协议`.
- When entering Home, configure the official demo service only for `com.meishe.duanshipindemo`, then start prefabricated material download in the background. Online material preparation failures must not block the four main demo entries.
- Capture, dual-capture, and edit taps unconditionally call `downloadPrefabricatedMaterialCompletion(nil)` before opening the SDK page. The home background request state must not suppress this per-entry refresh.
- AutoCut entry coverage: edit album, template page, and the capture template menu must all remain available. Generated AutoCut results continue in the standard editor; Next opens the publish page for save draft or export video.
- Draft screen: title `本地草稿箱`; empty state `没有草稿啦！`; non-empty state shows `温馨提示： 卸载应用后，草稿也会被删除`, a thumbnail with play overlay, and `草稿-MMDD` or a meaningful draft description.
- Draft data comes from `NvModuleManager.projectList()`, re-edit uses `reeditProject`, and delete uses a long-press confirmation flow that calls `NvModuleManager.deleteDraft(projectId)`.
- Publish / Next screen: when SDK edit, capture, or dual-capture flows emit the publish callback, render a dark `作品发布` page with the same compact project row as drafts, thumbnail/play overlay, `草稿-MMDD` fallback title, save-draft/export/progress controls, and no light English form UI.
"""
    write_text(target_root / "meishe_native_ios_handoff.md", content, target_root, report, "Generated native iOS handoff notes")


def update_native_ios_readme(
    target_root: Path,
    project_context: IosProjectContext,
    effective_bundle_identifier: str,
    report: Report,
) -> None:
    """Create or refresh the managed native-iOS run guide without replacing user README text."""
    workspace = project_context.workspace_path.resolve()
    scheme = project_context.scheme_name or "<APP_SCHEME>"
    app_product = project_context.target_name
    derived_data = target_root / ".meishe-xcodebuild"
    app_path = (
        derived_data
        / "Build"
        / "Products"
        / "Debug-iphoneos"
        / f"{app_product}.app"
    )
    dependency_lines = []
    for step in report.dependency_steps:
        dependency_lines.extend(
            (
                f"- **{step.label}**",
                f"  - 工作目录：`{step.working_directory}`",
                f"  - 命令：`{step.command}`",
                f"  - 成功标志：{step.success_marker}",
            )
        )
    dependency_section = "\n".join(dependency_lines) or "- 当前未生成依赖安装命令。"
    configuration_section = report.configuration_handoff_markdown(heading_level=3).strip()
    block = f"""<!-- BEGIN MEISHE_NATIVE_IOS_RUN_GUIDE -->
## 美摄短视频 Demo 运行

- 项目根目录：`{target_root.resolve()}`
- Xcode workspace：`{workspace}`
- App Scheme：`{scheme}`
- Bundle Identifier：`{effective_bundle_identifier}`
- 运行与验收设备：真实 iPhone 或 iPad；iOS Simulator 和其他虚拟设备不受支持。

### 依赖安装

{dependency_section}

### 推荐运行方式：Xcode

1. 运行 `open "{workspace}"` 打开实际 `.xcworkspace`，不要打开 `.xcodeproj`。
2. 在 Xcode 顶部选择 App Scheme `{scheme}` 和真实 iPhone/iPad。
3. 在 `Signing & Capabilities` 选择正确的 Team、证书和 provisioning profile。
4. 执行 `Product > Run`（Command-R）。

### 命令行运行方式（必须同时提供）

命令行流程与推荐的 Xcode 流程必须同时保留。将设备占位符替换为 `xcrun devicectl list devices` 检测到的真实设备 ID：

```bash
xcrun devicectl list devices
xcodebuild -workspace "{workspace}" -scheme "{scheme}" -configuration Debug -destination 'id=<IOS_DEVICE_UDID>' -derivedDataPath "{derived_data.resolve()}" -allowProvisioningUpdates build
xcrun devicectl device install app --device <IOS_DEVICE_UDID> "{app_path.resolve()}"
xcrun devicectl device process launch --device <IOS_DEVICE_UDID> "{effective_bundle_identifier}"
```

### 配置修改与生效

{configuration_section}

### 遇到报错

受本机操作系统、Xcode/工具链、依赖缓存、网络、签名和设备状态差异影响，手动接入或运行期间可能报错。请把**执行的完整命令**和**完整原始报错信息**（不要只复制最后一行）发给当前 Agent 处理，不要求自行猜测修复。

<!-- END MEISHE_NATIVE_IOS_RUN_GUIDE -->"""
    readme = target_root / "README.md"
    existing = read_text(readme) if readme.exists() else ""
    pattern = re.compile(
        r"<!-- BEGIN MEISHE_NATIVE_IOS_RUN_GUIDE -->.*?"
        r"<!-- END MEISHE_NATIVE_IOS_RUN_GUIDE -->",
        re.S,
    )
    if pattern.search(existing):
        updated = pattern.sub(block, existing, count=1)
    else:
        updated = existing.rstrip()
        if updated:
            updated += "\n\n"
        updated += block
    write_text(
        readme,
        updated.rstrip() + "\n",
        target_root,
        report,
        "Updated the managed native iOS run guide in README.md",
    )


def integrate_native_ios(args: argparse.Namespace, target_root: Path, report: Report) -> None:
    source_pods_package = resolve_ios_pods_package(args.plugin_path)
    package_root = Path(args.plugin_path).resolve() if args.plugin_path else source_pods_package.parent
    project_context = resolve_ios_project_context(target_root, args)
    ios_target = project_context.target_name
    effective_bundle_identifier = configure_native_ios_bundle_identifier(
        target_root,
        project_context,
        getattr(args, "ios_bundle_identifier", None),
        report,
    )
    official_demo_identity = effective_bundle_identifier == OFFICIAL_DEMO_BUNDLE_IDENTIFIER
    package_example_ats = official_example_allows_arbitrary_loads(source_pods_package)
    official_demo_ats_enabled = official_demo_identity and package_example_ats
    autocut_draft_fallback_supported = supports_native_ios_autocut_draft_fallback(source_pods_package)
    pods_package = copy_sdk_package_to_vendor(
        target_root,
        source_pods_package,
        "Pods-NvShortVideoEdit",
        report,
        "Native iOS",
        validator=validate_ios_pods_package,
    )
    report.add_input(f"iOS target: `{ios_target}`")
    report.add_input(f"Xcode project: `{project_context.project_path.name}`")
    report.add_input(f"Xcode workspace: `{project_context.workspace_path.name}`")
    report.add_input(f"Native iOS package: `{package_root}`")
    report.add_input(f"NvShortVideoEdit source pod path: `{source_pods_package}`")
    report.add_input(f"NvShortVideoEdit project-local pod path: `{pods_package}`")
    report.add_warning(IOS_NATIVE_SCOPE_NOTE)
    report_ios_signing_configuration(target_root, report)
    patch_xcode_26_user_script_sandboxing(target_root, report, project_context)
    patch_ios_podfile(target_root, pods_package, ios_target, report)
    replace_external_source_path_refs(target_root, source_pods_package, pods_package, [target_root / "Podfile.lock"], report, "Native iOS")
    patch_ios_app_info_plists(
        target_root,
        report,
        "Native iOS",
        allow_arbitrary_loads=official_demo_ats_enabled,
    )
    if official_demo_ats_enabled:
        report.add_user_configuration(
            "Native iOS official-Demo compatibility: the supplied package Example declares `NSAllowsArbitraryLoads = true`, so it is enabled only for temporary `com.meishe.duanshipindemo` Demo-service validation. Replace it with verified domain-specific ATS exceptions before production."
        )
    elif official_demo_identity:
        report.add_ios_quick_verify(
            "Native iOS: the official Demo identity was detected, but the supplied package Example does not declare global ATS; NSAllowsArbitraryLoads was not enabled."
        )
    else:
        report.add_ios_quick_verify(
            "Native iOS: global NSAllowsArbitraryLoads was not enabled for a customer Bundle Identifier; use only verified domain-specific ATS exceptions."
        )
    copy_ios_demo_config_files(target_root, package_root, report)
    if autocut_draft_fallback_supported:
        report.add_change(
            "Native iOS ShortVideo 2.0.2.1 AutoCut draft and timeline API shapes matched; enabled rendered-result conversion to a standard editable draft."
        )
    else:
        report.add_warning(
            "Native iOS AutoCut draft fallback was not applied because the supplied SDK does not expose the verified project-manager and Swift timeline API shapes. Preserve `hasDraft` behavior and verify this SDK version manually."
        )
    create_native_ios_swift_ui(target_root, report, autocut_draft_fallback_supported)
    write_native_ios_self_check(target_root, report, autocut_draft_fallback_supported)
    place_ios_license(target_root, args, report)
    write_ios_handoff(
        target_root,
        pods_package,
        ios_target,
        official_demo_ats_enabled,
        autocut_draft_fallback_supported,
        report,
    )
    report.add_user_configuration(
        "Xcode signing: select the user's Team, development/distribution certificate, and provisioning profile. Any temporary Team used for first launch must be replaced before handoff or release."
    )
    report.add_user_configuration(
        "Server entry: edit `MeisheShortVideo/MeisheShortVideoHomeViewController.swift` -> `ServerConfig`; follow `references/customer-server.md` for fields, Bundle Identifier constraints, and manual verification."
    )
    write_server_handoff(
        target_root,
        "native-ios",
        "MeisheShortVideo/MeisheShortVideoHomeViewController.swift -> ServerConfig",
        "原生 iOS `NvHttpRequest.assetAutoCutUrl` 使用完整地址 `https://creative.meishesdk.com/api/app/aivideo/asset/all/1`；不得改成 RN/Flutter bridge 使用的基础地址。客户服务按美摄合同替换。",
        "官方 Demo host 仅允许 Bundle Identifier `com.meishe.duanshipindemo`；其他 Bundle Identifier 必须使用美摄提供/部署的客户服务和匹配 License。",
        "客户服务确实使用 HTTP 时，只添加真实域名的最小 ATS 例外。官方 Demo 身份临时启用的 `NSAllowsArbitraryLoads` 不得带入正式项目。",
        report,
    )
    report.add_next_check(
        "Native iOS AutoCut: manually verify edit album, template page, and capture template entry; the generated result must enter the standard editor, then Next must reach save-draft/export publishing."
    )
    add_cocoapods_dependency_step(target_root, report, "Native iOS")
    workspace = project_context.workspace_path
    shared_scheme = project_context.scheme_name
    if shared_scheme:
        report.add_input(f"Detected shared app scheme: `{shared_scheme}`.")
        run_instruction = (
            f"在 Xcode 左侧选择项目 -> TARGETS/{ios_target} -> Signing & Capabilities 选择 Team；\n"
            f"顶部选择已检测到的 {shared_scheme} scheme 和目标设备；执行 Product > Run（快捷键 Command-R）。"
        )
    else:
        report.add_toolchain_warning(
            "No unique shared app scheme was detected. The handoff will not guess a scheme name; "
            "list workspace schemes after `pod install`, then select the confirmed app scheme in Xcode."
        )
        run_instruction = (
            f"先执行：xcodebuild -list -workspace \"{workspace.resolve()}\"；\n"
            f"在 Xcode 左侧选择项目 -> TARGETS/{ios_target} -> Signing & Capabilities 选择 Team；\n"
            "顶部选择列表中确认的 App scheme 和目标设备；执行 Product > Run（快捷键 Command-R）。"
        )
    scheme_for_command = shared_scheme or "<APP_SCHEME>"
    derived_data = target_root / ".meishe-xcodebuild"
    app_path = (
        derived_data
        / "Build"
        / "Products"
        / "Debug-iphoneos"
        / f"{ios_target}.app"
    )
    command_line_run = (
        "xcrun devicectl list devices\n"
        f"xcodebuild -workspace \"{workspace.resolve()}\" -scheme \"{scheme_for_command}\" "
        "-configuration Debug -destination 'id=<IOS_DEVICE_UDID>' "
        f"-derivedDataPath \"{derived_data.resolve()}\" -allowProvisioningUpdates build\n"
        f"xcrun devicectl device install app --device <IOS_DEVICE_UDID> \"{app_path.resolve()}\"\n"
        f"xcrun devicectl device process launch --device <IOS_DEVICE_UDID> \"{effective_bundle_identifier}\""
    )
    feature_config = target_root / "MeisheShortVideo" / "MeisheFeatureConfig.swift"
    server_config = target_root / "MeisheShortVideo" / "MeisheShortVideoHomeViewController.swift"
    xcode_steps = [
        ConfigurationApplyStep(
            label="推荐使用 Xcode 打开 workspace",
            condition="修改 Swift 功能配置、服务器、Bundle Identifier、License、签名或 iOS 资源后；Pod 依赖未变化时无需再次 pod install。",
            working_directory=target_root,
            command=f"open \"{workspace.resolve()}\"",
            success_marker="Xcode 打开 `.xcworkspace`，不是 `.xcodeproj`。",
        ),
        ConfigurationApplyStep(
            label="推荐使用 Xcode 重新构建并安装到 iOS 设备",
            condition="workspace 已打开且目标 Swift/资源均属于 App target。",
            working_directory=target_root,
            command=run_instruction,
            success_marker="Xcode 显示 Build Succeeded，设备安装并启动新 App，重新进入功能时使用新 NvVideoConfig。",
        ),
        ConfigurationApplyStep(
            label="命令行重新构建、安装并启动 iOS（必须同时提供）",
            condition="已使用 devicectl 检测真实设备 ID，并确认 workspace、App Scheme、Bundle Identifier 和签名。",
            working_directory=target_root,
            command=command_line_run,
            success_marker="xcodebuild 显示 BUILD SUCCEEDED，devicectl 完成安装并按 Bundle Identifier 启动 App。",
        ),
    ]
    report.add_configuration_handoff(
        "原生 iOS 功能配置",
        str(feature_config.resolve()),
        "拍摄、合拍、相册、编辑、导出、菜单、画幅、水印和模型等 NvVideoConfig 业务能力。",
        xcode_steps,
        (
            "Swift 配置会编译进 App，修改后不能只重启旧安装包，必须重新 Build & Run。",
            "确认 MeisheFeatureConfig.swift 勾选 App target 的 Target Membership；不要把其他路线的枚举写入此文件。",
            "Podfile 和 Pod 依赖未变化时无需 pod install；不要默认 Clean Build Folder。",
            "Xcode 是 iOS 推荐运行方式；命令行运行方式也必须完整提供，不得称为备选或省略。",
        ),
    )
    report.add_configuration_handoff(
        "原生 iOS 服务器、License 与签名",
        (
            f"{server_config.resolve()} -> ServerConfig; "
            f"{(target_root / 'MeisheShortVideo/meishesdk.lic').resolve()}; {workspace.resolve()} -> Signing & Capabilities"
        ),
        "素材服务 host/AutoCut 地址、正式 License、Bundle Identifier、Team、证书、profile、ATS 和原生资源。",
        xcode_steps,
        (
            "官方 Demo 服务只允许 `com.meishe.duanshipindemo`；客户 Bundle Identifier 必须使用匹配的客户服务和正式 License。",
            "修改服务器后彻底关闭并重新启动 App，再检查请求 URL、HTTP/业务码和实际素材下载；页面能打开不代表配置正确。",
            "确认 meishesdk.lic 位于 App target 的 Copy Bundle Resources。",
            "Xcode 是 iOS 推荐运行方式；命令行运行方式也必须完整提供，不得称为备选或省略。",
        ),
    )
    update_native_ios_readme(
        target_root,
        project_context,
        effective_bundle_identifier,
        report,
    )
    assert_no_external_dependency_refs(target_root, source_pods_package, "Native iOS", report)
    assert_no_external_dependency_refs(target_root, package_root, "Native iOS package root", report)
