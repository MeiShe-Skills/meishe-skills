"""Select and execute only the Flutter subplatforms present in the target."""

from argparse import Namespace
from pathlib import Path

from meishe_docking_core import (
    ConfigurationApplyStep,
    IntegrationError,
    Report,
    TargetPlatforms,
    add_cocoapods_dependency_step,
)

from . import android, common, ios


def _register_configuration_handoffs(
    target_root: Path,
    targets: TargetPlatforms,
    report: Report,
) -> None:
    root = target_root.resolve()
    shared_steps = [
        ConfigurationApplyStep(
            label="Hot Restart 当前 Debug 会话",
            condition="只修改 Dart 功能或服务器配置，且 `flutter run` 仍在运行。",
            working_directory=root,
            command="在 flutter run 终端按大写 R（Hot Restart），不要只执行小写 r 的 Hot Reload。",
            success_marker="Flutter 根 Widget 和 Meishe NvVideoConfig 重新创建，首页重新出现。",
        )
    ]
    if targets.android:
        shared_steps.append(
            ConfigurationApplyStep(
                label="重新运行 Android",
                condition="没有活动调试会话、当前是 Release 包，或修改了 Android 原生文件、包名、License、资源或 Gradle 配置。",
                working_directory=root,
                command="flutter run -d <ANDROID_DEVICE_ID>",
                success_marker="Flutter/Gradle 构建成功，App 安装到指定 Android 设备并启动。",
            )
        )
    if targets.ios:
        shared_steps.append(
            ConfigurationApplyStep(
                label="重新运行 iOS",
                condition="没有活动调试会话、当前是 Release 包，或修改了 iOS 原生文件、Bundle Identifier、License、资源或签名配置。",
                working_directory=root,
                command="flutter run -d <IOS_DEVICE_ID>",
                success_marker="Flutter/Xcode 构建成功，App 安装到指定 iOS 设备并启动。",
            )
        )
    shared_notes = (
        "修改 Dart 配置不需要重新执行 flutter pub get；只有 pubspec.yaml 或锁文件依赖变化时才重新解析依赖。",
        "不要默认执行 flutter clean；仅在 Hot Restart 和完整重建后仍命中旧产物时，将 clean 作为缓存排障步骤。",
    )
    report.add_configuration_handoff(
        "Flutter 功能配置",
        str((root / "lib" / "meishe_feature_config.dart").resolve()),
        "拍摄、合拍、相册、编辑、导出、菜单、画幅、水印和模型等 NvVideoConfig 业务能力；双端共用这一份 Dart 配置。",
        shared_steps,
        shared_notes,
    )
    report.add_configuration_handoff(
        "Flutter 服务器配置",
        f"{(root / 'lib/meishe_short_video_docking.dart').resolve()} -> MeisheShortVideoDocking.defaultServerConfig",
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
            "Flutter Android 身份、License 与原生资源",
            f"{gradle.resolve()}; {(root / 'vendor/meishe/nvshortvideo/android/src/main/assets/meishesdk.lic').resolve()}",
            "applicationId、Android 签名、正式 License、Android drawable/manifest 等原生打包输入。",
            [
                ConfigurationApplyStep(
                    label="重新构建并运行 Android",
                    condition="修改任一 Android 原生打包输入后。",
                    working_directory=root,
                    command="flutter run -d <ANDROID_DEVICE_ID>",
                    success_marker="Flutter/Gradle 构建安装成功，设备上的新包身份与 License 对应。",
                )
            ],
            ("License 必须匹配最终 applicationId。", "依赖声明未变时不需要 flutter pub get 或 flutter clean。"),
            platforms=("Android",),
        )
    if targets.ios:
        ios_root = root / "ios"
        ios_target = ios.flutter_ios_app_target_name(ios_root)
        ios_project = ios.flutter_ios_project_path(ios_root, ios_target)
        workspaces = sorted(path for path in ios_root.glob("*.xcworkspace") if path.name != "Pods.xcworkspace")
        preferred_workspace = ios_root / f"{ios_project.stem}.xcworkspace"
        if preferred_workspace in workspaces:
            workspace = preferred_workspace
        elif len(workspaces) == 1:
            workspace = workspaces[0]
        elif not workspaces:
            workspace = preferred_workspace
        else:
            raise IntegrationError(
                "Could not uniquely determine the Flutter iOS workspace for configuration handoff."
            )
        report.add_configuration_handoff(
            "Flutter iOS 身份、签名、License 与原生资源",
            f"{workspace.resolve()} -> {ios_target} / Signing & Capabilities; {(root / 'vendor/meishe/nvshortvideo/ios/Assets/meishesdk.lic').resolve()}",
            "Bundle Identifier、Team、证书、profile、正式 License、Asset Catalog 和 Info.plist。",
            [
                ConfigurationApplyStep(
                    label="打开 workspace 并运行",
                    condition="修改任一 iOS 原生打包输入后；Podfile 和 Pod 依赖未变化时不需要再次 pod install。",
                    working_directory=ios_root,
                    command=f"open \"{workspace.resolve()}\"",
                    success_marker=f"Xcode 打开 {workspace.name}；选择 {ios_target}、真机和 Team 后点击 Product > Run，构建安装成功。",
                )
            ],
            (
                f"License 必须匹配最终 Bundle Identifier，并确认资源属于 {ios_target} target。",
                "只有 Podfile、podspec 或 Pod 依赖变化时才重新执行报告中的 CocoaPods 安装命令。",
            ),
            platforms=("iOS",),
        )


def integrate_flutter(args: Namespace, target_root: Path, report: Report) -> None:
    common.validate_target(target_root)
    targets = TargetPlatforms.detect(target_root, "Flutter")
    source_plugin = common.resolve_source(args, target_root, targets)
    if targets.android:
        android.preflight(args, target_root, source_plugin, report)
    plugin = common.prepare(args, target_root, source_plugin, targets, report)
    if targets.android:
        android.integrate(args, target_root, plugin, source_plugin, report)
    if targets.ios:
        ios.integrate(
            target_root,
            plugin,
            source_plugin,
            args.ios_bundle_identifier or args.package_name,
            report,
        )
    common.finish(target_root, source_plugin, plugin, report)
    report.add_dependency_step(
        "Flutter packages",
        target_root,
        "flutter pub get",
        "Resolve the Flutter app and project-local Meishe plugin dependencies.",
        "the command exits with code 0 and `.dart_tool/package_config.json` is generated or updated.",
    )
    if targets.ios:
        add_cocoapods_dependency_step(target_root / "ios", report, "Flutter iOS")
    if targets.android:
        report.add_dependency_step(
            "Flutter Android dependencies and Debug build",
            target_root,
            "flutter build apk --debug",
            "Resolve Android/Gradle dependencies and verify that the integrated Flutter Android app compiles.",
            "the command exits with code 0 and produces a Debug APK under `build/app/outputs/flutter-apk/`.",
        )
    _register_configuration_handoffs(target_root, targets, report)
    common.update_flutter_readme(
        target_root,
        targets,
        args.android_package_name or args.package_name,
        args.ios_bundle_identifier or args.package_name,
        report,
    )
