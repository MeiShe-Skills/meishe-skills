"""Select and execute only the React Native subplatforms present in the target."""

from argparse import Namespace
import json
from pathlib import Path

from meishe_docking_core import (
    ConfigurationApplyStep,
    IntegrationError,
    Report,
    TargetPlatforms,
    add_android_gradle_dependency_step,
    add_cocoapods_dependency_step,
    add_node_dependency_step,
    detect_node_install_command,
    read_text,
)

from . import android, common, ios


def _react_native_commands(manager: str) -> tuple[str, str, str]:
    if manager == "npm":
        return (
            "npm start",
            "npm run android -- --deviceId <ANDROID_DEVICE_ID>",
            "npm run ios -- --udid <IOS_DEVICE_UDID>",
        )
    return (
        f"{manager} start",
        f"{manager} android --deviceId <ANDROID_DEVICE_ID>",
        f"{manager} ios --udid <IOS_DEVICE_UDID>",
    )


def _register_configuration_handoffs(
    target_root: Path,
    targets: TargetPlatforms,
    package_manager: str,
    report: Report,
) -> None:
    root = target_root.resolve()
    src_dir = target_root / "src"
    use_ts = (target_root / "tsconfig.json").exists() or (src_dir.exists() and any(src_dir.glob("*.ts")))
    suffix = "ts" if use_ts else "js"
    start_command, android_command, ios_command = _react_native_commands(package_manager)
    shared_steps = [
        ConfigurationApplyStep(
            label="启动 Metro（尚未运行时）",
            condition="Debug 调试且 Metro 尚未运行；已运行时不要重复启动。",
            working_directory=root,
            command=start_command,
            success_marker="终端显示 Metro 已就绪并等待设备连接。",
        ),
        ConfigurationApplyStep(
            label="完整重新加载 JavaScript",
            condition="只修改 `src/` 下的功能或服务器 TS/JS 配置，且当前安装的是 Debug 包。",
            working_directory=root,
            command="在 Metro 终端按 r；若页面仍保留旧 NvVideoConfig，彻底关闭 App 后重新打开。",
            success_marker="App 首页重新加载，重新进入功能时创建新的 NvVideoConfig；不能只依赖 Fast Refresh。",
        ),
    ]
    if targets.android:
        shared_steps.append(
            ConfigurationApplyStep(
                label="重新构建 Android 包",
                condition="当前是 Release 包，或修改了 Android 原生文件、包名、License、资源或 Gradle 配置。",
                working_directory=root,
                command=android_command,
                success_marker="命令成功完成，Debug APK 安装到所选 Android 设备并启动。",
            )
        )
    if targets.ios:
        shared_steps.append(
            ConfigurationApplyStep(
                label="重新构建 iOS 包",
                condition="当前是 Release 包，或修改了 iOS 原生文件、Bundle Identifier、License、资源或签名配置。",
                working_directory=root,
                command=ios_command,
                success_marker="Xcode 构建成功，App 安装到所选 iOS 设备并启动。",
            )
        )
    shared_notes = (
        "修改 TS/JS 配置不需要重新执行 npm/Yarn/pnpm 安装；只有 package.json 或锁文件变化时才重新安装依赖。",
        "不要默认清理缓存；仅在完整 Reload 后仍读取旧 bundle 时，再停止 Metro 并使用项目已有启动命令处理缓存。",
    )
    report.add_configuration_handoff(
        "React Native 功能配置",
        str((root / "src" / f"meisheFeatureConfig.{suffix}").resolve()),
        "拍摄、合拍、相册、编辑、导出、菜单、画幅、水印和模型等 NvVideoConfig 业务能力；双端共用这一份配置。",
        shared_steps,
        shared_notes,
    )
    report.add_configuration_handoff(
        "React Native 服务器配置",
        f"{(root / 'src' / f'meisheShortVideoDocking.{suffix}').resolve()} -> meisheServerConfig",
        "素材服务 host、接口地址、AutoCut 地址和客户鉴权字段；字段必须按美摄或客户服务器合同填写。",
        shared_steps,
        (
            *shared_notes,
            "修改服务器后必须彻底关闭并重新打开 App，再用请求日志和实际素材下载验证；页面能打开不代表服务器配置正确。",
        ),
    )
    if targets.android:
        gradle = root / "android" / "app" / "build.gradle"
        if not gradle.exists():
            gradle = gradle.with_suffix(".gradle.kts")
        report.add_configuration_handoff(
            "React Native Android 身份、License 与原生资源",
            f"{gradle.resolve()}; {(root / 'android/app/src/main/assets/meishesdk.lic').resolve()}",
            "applicationId、Android 签名、正式 License、Android drawable/manifest 等原生打包输入。",
            [
                ConfigurationApplyStep(
                    label="重新构建并安装 Android",
                    condition="修改任一 Android 原生打包输入后。",
                    working_directory=root,
                    command=android_command,
                    success_marker="Gradle 构建和安装成功，设备上的新包身份与 License 对应。",
                )
            ],
            (
                "License 必须匹配最终 applicationId；自定义包名不能复用官方 Demo License。",
                "只改原生打包输入不要求清理 node_modules；依赖声明未变时不要重新安装 JS 依赖。",
            ),
            platforms=("Android",),
        )
    if targets.ios:
        ios_root = root / "ios"
        workspaces = sorted(ios_root.glob("*.xcworkspace"))
        projects = sorted(ios_root.glob("*.xcodeproj"))
        workspace = workspaces[0] if workspaces else ios_root / f"{projects[0].stem if projects else target_root.name}.xcworkspace"
        report.add_configuration_handoff(
            "React Native iOS 身份、签名、License 与原生资源",
            f"{workspace.resolve()} -> Signing & Capabilities; {(root / 'vendor/meishe/react-native-nvshortvideo/ios/Assets/meishesdk.lic').resolve()}",
            "Bundle Identifier、Team、证书、profile、正式 License、Asset Catalog 和 Info.plist。",
            [
                ConfigurationApplyStep(
                    label="打开 workspace 并运行",
                    condition="修改任一 iOS 原生打包输入后；Podfile 和 Pod 依赖未变化时不需要再次 pod install。",
                    working_directory=ios_root,
                    command=f"open \"{workspace.resolve()}\"",
                    success_marker="Xcode 打开 `.xcworkspace`；选择 App scheme 和真机，在 Signing & Capabilities 选择 Team 后点击 Product > Run，构建安装成功。",
                )
            ],
            (
                "License 必须匹配最终 Bundle Identifier，并确认文件属于 App target 的 Copy Bundle Resources。",
                "只有 Podfile、podspec 或 Pod 依赖变化时才重新执行报告中的 CocoaPods 安装命令。",
            ),
            platforms=("iOS",),
        )


def integrate_react_native(args: Namespace, target_root: Path, report: Report) -> None:
    package_json = target_root / "package.json"
    if not package_json.exists():
        raise IntegrationError("React Native target must contain package.json.")
    try:
        package_data = json.loads(read_text(package_json).lstrip("\ufeff"))
    except json.JSONDecodeError as exc:
        raise IntegrationError(f"React Native target has invalid package.json: {package_json}") from exc
    dependencies = {
        **(package_data.get("dependencies", {}) if isinstance(package_data.get("dependencies"), dict) else {}),
        **(package_data.get("devDependencies", {}) if isinstance(package_data.get("devDependencies"), dict) else {}),
    }
    if not dependencies.get("react-native"):
        raise IntegrationError("React Native target package.json must declare a `react-native` dependency.")
    detect_node_install_command(target_root, package_data)
    targets = TargetPlatforms.detect(target_root, "React Native")
    source_plugin = common.resolve_source(args, target_root, targets)
    if targets.android:
        android.validate_package_runtime(target_root, source_plugin, report)
    plugin = common.prepare(args, target_root, source_plugin, targets, report)
    if targets.android:
        android.integrate(target_root, plugin, source_plugin, report)
    common.configure_project(target_root, plugin, source_plugin, report)
    ruby4_nkf_ready = False
    if targets.ios:
        ios.integrate(
            target_root,
            plugin,
            source_plugin,
            report,
            args.ios_bundle_identifier or args.package_name,
        )
        ruby4_nkf_ready = ios.ensure_ruby4_cocoapods_nkf_compatibility(target_root, report)
    common.finish(target_root, source_plugin, plugin, report)
    add_node_dependency_step(target_root, report, package_data)
    if targets.ios:
        add_cocoapods_dependency_step(
            target_root / "ios",
            report,
            "React Native iOS",
            bundled_compatibility_ready=ruby4_nkf_ready,
        )
    if targets.android:
        add_android_gradle_dependency_step(target_root / "android", report, "React Native Android")
    manager = detect_node_install_command(target_root, package_data).split()[0]
    _register_configuration_handoffs(target_root, targets, manager, report)
    common.implementation.update_react_native_readme(
        target_root,
        targets,
        args.android_package_name or args.package_name,
        args.ios_bundle_identifier or args.package_name,
        report,
    )
