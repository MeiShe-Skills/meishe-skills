"""Flutter Android/iOS fixture validation."""

from __future__ import annotations

import shutil
import plistlib
import sys
from pathlib import Path

from .shared import (
    IOS_VALIDATION_MARKER,
    PLATFORM_SCRIPTS,
    assert_contains,
    assert_not_contains,
    create_ios_app,
    fail,
    run,
    run_integration,
    run_integration_apply,
    run_integration_apply_failure,
    run_integration_failure,
    read,
    write,
    write_flutter_android_aar,
)


def create_flutter_target(
    root: Path,
    *,
    android: bool = True,
    ios: bool = True,
    bundle_identifier: str | None = None,
    android_dsl: str = "kts",
    modern_ios_template: bool = False,
) -> None:
    write(
        root / "pubspec.yaml",
        """name: flutter_fixture
environment:
  sdk: '>=3.0.0 <4.0.0'
dependencies:
  flutter:
    sdk: flutter
flutter:
  uses-material-design: true
""",
    )
    write(
        root / "lib" / "main.dart",
        """import 'package:flutter/material.dart';

void main() {
  runApp(const MaterialApp(home: Text('Flutter Demo Home Page')));
}
""",
    )
    write(root / "android" / "gradle.properties", "android.useAndroidX=true\n")
    if android_dsl == "kts":
        write(
            root / "android" / "app" / "build.gradle.kts",
            """android {
    namespace = "com.example.flutter_fixture"

    defaultConfig {
        applicationId = "com.example.flutter_fixture"
    }
}
""",
        )
    elif android_dsl == "groovy":
        write(
            root / "android" / "app" / "build.gradle",
            """android {
    namespace 'com.example.flutter_fixture'

    defaultConfig {
        applicationId 'com.example.flutter_fixture'
    }
}
""",
        )
    else:
        fail(f"Unsupported Flutter Android fixture DSL: {android_dsl}")
    write(
        root
        / "android"
        / "app"
        / "src"
        / "main"
        / "kotlin"
        / "com"
        / "example"
        / "flutter_fixture"
        / "MainActivity.kt",
        """package com.example.flutter_fixture

import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity()
""",
    )
    create_ios_app(root, "Runner")
    write(
        root / "ios" / "Runner.xcodeproj" / "project.pbxproj",
        flutter_ios_project_fixture(bundle_identifier or "com.example.flutter_fixture"),
    )
    if modern_ios_template:
        (root / "ios" / "Podfile").unlink(missing_ok=True)
        write(root / "ios" / "Flutter" / "Debug.xcconfig", '#include "Generated.xcconfig"\n')
        write(root / "ios" / "Flutter" / "Release.xcconfig", '#include "Generated.xcconfig"\n')
        write(root / "ios" / "Flutter" / "Generated.xcconfig", "FLUTTER_ROOT=/fixture/flutter\n")
    write(root / "README.md", "# Flutter Fixture\n\nUser-maintained introduction.\n")
    if not android:
        shutil.rmtree(root / "android")
    if not ios:
        shutil.rmtree(root / "ios")


def flutter_ios_project_fixture(bundle_identifier: str, target_name: str = "Runner") -> str:
    return f"""// !$*UTF8*$!
{{
\tobjects = {{

/* Begin PBXNativeTarget section */
\t\t111111111111111111111111 /* {target_name} */ = {{
\t\t\tisa = PBXNativeTarget;
\t\t\tbuildConfigurationList = 333333333333333333333333 /* Build configuration list for PBXNativeTarget "{target_name}" */;
\t\t\tname = {target_name};
\t\t\tproductName = {target_name};
\t\t\tproductType = "com.apple.product-type.application";
\t\t}};
/* End PBXNativeTarget section */

/* Begin PBXFileReference section */
\t\t7AFA3C8E1D35360C0083082E /* Debug.xcconfig */ = {{isa = PBXFileReference; lastKnownFileType = text.xcconfig; name = Debug.xcconfig; path = Flutter/Debug.xcconfig; sourceTree = \"<group>\"; }};
\t\t9740EEB21CF90195004384FC /* Release.xcconfig */ = {{isa = PBXFileReference; lastKnownFileType = text.xcconfig; name = Release.xcconfig; path = Flutter/Release.xcconfig; sourceTree = \"<group>\"; }};
/* End PBXFileReference section */

/* Begin PBXGroup section */
\t\t9740EEB11CF90186004384FC /* Flutter */ = {{
\t\t\tisa = PBXGroup;
\t\t\tchildren = (
\t\t\t\t7AFA3C8E1D35360C0083082E /* Debug.xcconfig */,
\t\t\t\t9740EEB21CF90195004384FC /* Release.xcconfig */,
\t\t\t);
\t\t\tname = Flutter;
\t\t\tsourceTree = \"<group>\";
\t\t}};
/* End PBXGroup section */

/* Begin XCBuildConfiguration section */
\t\t249021D3217E4FDB00AE95B9 /* Debug */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbaseConfigurationReference = 7AFA3C8E1D35360C0083082E /* Debug.xcconfig */;
\t\t\tbuildSettings = {{
\t\t\t\tINFOPLIST_FILE = {target_name}/Info.plist;
\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = {bundle_identifier};
\t\t\t}};
\t\t\tname = Debug;
\t\t}};
\t\t249021D4217E4FDB00AE95B9 /* Release */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbaseConfigurationReference = 9740EEB21CF90195004384FC /* Release.xcconfig */;
\t\t\tbuildSettings = {{
\t\t\t\tINFOPLIST_FILE = {target_name}/Info.plist;
\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = {bundle_identifier};
\t\t\t}};
\t\t\tname = Release;
\t\t}};
\t\t249021D5217E4FDB00AE95B9 /* Profile */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbaseConfigurationReference = 9740EEB21CF90195004384FC /* Release.xcconfig */;
\t\t\tbuildSettings = {{
\t\t\t\tINFOPLIST_FILE = {target_name}/Info.plist;
\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = {bundle_identifier};
\t\t\t}};
\t\t\tname = Profile;
\t\t}};
\t\t249021D6217E4FDB00AE95B9 /* Debug */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbuildSettings = {{
\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = {bundle_identifier}.{target_name}Tests;
\t\t\t\tTEST_HOST = \"$(BUILT_PRODUCTS_DIR)/{target_name}.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)/{target_name}\";
\t\t\t}};
\t\t\tname = Debug;
\t\t}};
\t\t249021D7217E4FDB00AE95B9 /* Release */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbuildSettings = {{
\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = {bundle_identifier}.{target_name}Tests;
\t\t\t\tTEST_HOST = \"$(BUILT_PRODUCTS_DIR)/{target_name}.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)/{target_name}\";
\t\t\t}};
\t\t\tname = Release;
\t\t}};
\t\t249021D8217E4FDB00AE95B9 /* Profile */ = {{
\t\t\tisa = XCBuildConfiguration;
\t\t\tbuildSettings = {{
\t\t\t\tPRODUCT_BUNDLE_IDENTIFIER = {bundle_identifier}.{target_name}Tests;
\t\t\t\tTEST_HOST = \"$(BUILT_PRODUCTS_DIR)/{target_name}.app/$(BUNDLE_EXECUTABLE_FOLDER_PATH)/{target_name}\";
\t\t\t}};
\t\t\tname = Profile;
\t\t}};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
\t\t333333333333333333333333 /* Build configuration list for PBXNativeTarget "{target_name}" */ = {{
\t\t\tisa = XCConfigurationList;
\t\t\tbuildConfigurations = (
\t\t\t\t249021D3217E4FDB00AE95B9 /* Debug */,
\t\t\t\t249021D4217E4FDB00AE95B9 /* Release */,
\t\t\t\t249021D5217E4FDB00AE95B9 /* Profile */,
\t\t\t);
\t\t}};
/* End XCConfigurationList section */
\t}};
}}
"""

def create_flutter_plugin(
    root: Path,
    *,
    complete_ios: bool,
    complete_android_native: bool = True,
    include_android_beauty_shape_resources: bool = True,
    include_android: bool = True,
) -> Path:
    plugin = root / "flutter" / "nvshortvideo"
    write(
        plugin / "pubspec.yaml",
        """name: nvshortvideo
version: 0.0.1
        """,
    )
    if include_android:
        write(
            plugin / "android" / "build.gradle",
            """dependencies {
    implementation 'com.blankj:utilcode:1.30.6'
    implementation 'com.permissionx.guolindev:permission-support:1.4.0'
}
""",
        )
        write(
            plugin / "android" / "src" / "main" / "java" / "com" / "meishe" / "nvshortvideo" / "VideoEditPlugin.java",
            """switch (methodName) {
    case CONFIG_SERVER_INFO:
        NvModuleManager.get().initModel();
        break;
}

    private void goPublish(boolean needSaveDraft, boolean needSaveCover, boolean needSaveVideo, String videoPath) {
        if (null == mVideoEditChannel) {
            return;
        }
        NvModuleManager.get().saveCover(PathUtils.getCoverDir(), String.valueOf(System.currentTimeMillis()), mCoverPoint, false,
                new NvModuleManager.OnCoverSavedCallBack() {
                    @Override
                    public void onCoverSaved(String path) {
                        Map<String, Object> arguments = new TreeMap<>();
                        arguments.put("hasDraft", needSaveDraft);
                        arguments.put("coverImagePath", path);
                        arguments.put("videoPath", videoPath);
                        //目前默认传00
                        arguments.put("projectId", "00");
                        mVideoEditChannel.invokeMethod("VideoEditResultEvent", arguments);
                        AppManager.getInstance().finishAllEditActivity();
                    }

                    @Override
                    public void onCoverSaveFailed() {
                    }
                });
    }
""",
        )
        write_flutter_android_aar(
            plugin / "android" / "libs" / "NvShortVideoCore.aar",
            include_native_libraries=complete_android_native,
            include_beauty_shape_resources=include_android_beauty_shape_resources,
        )
    if complete_ios:
        write(
            plugin / "ios" / "nvshortvideo.podspec",
            """Pod::Spec.new do |s|
  s.name = 'nvshortvideo'
  s.ios.deployment_target = '13.0'
end
""",
        )
        write(
            plugin / "ios" / "Classes" / "VideoEditPlugin.swift",
            """import UIKit

let ConfigServerInfo = "ConfigServerInfo"
let DownloadPrefabricatedMaterialCompletionMethod = "DownloadPrefabricatedMaterialCompletionMethod"
let SaveDraftMethod = "SaveDraftMethod"
let CompileVideoMethod = "CompileVideoMethod"
let VideoEditResultEvent = "VideoEditResultEvent"
let DeleteDraftMethod = "DeleteDraftMethod"
let ExitVideoEditMethod = "ExitVideoEditMethod"

final class VideoEditPlugin {
    private var moduleManager: NvModuleManager?
    private var requestDelegate: NvHttpRequestDelegate?

    init() {
        self.moduleManager = NvModuleManager.sharedInstance()
        self.requestDelegate = NvHttpRequestDelegate()
    }

    func handle(methodName: String, args: [String: Any]?, completion: (Any?, Error?) -> Void) {
        if methodName == ConfigServerInfo {
            completion(nil, nil)
        } else if methodName == DownloadPrefabricatedMaterialCompletionMethod {
            completion(true, nil)
        } else if methodName == DeleteDraftMethod {
            let projectId = args?["projectId"] as? String
            if let projectId, !projectId.isEmpty, NvModuleManager.deleteDraft(projectId) {
                completion(nil, nil)
                return
            }
            completion(nil, NSError(domain: "", code: -1))
        } else if methodName == ExitVideoEditMethod {
            let projectId = args?["projectId"] as? String
            if let projectId {
                _ = moduleManager?.exitVideoEdit(projectId)
            }
            completion(nil, nil)
        } else if methodName == SaveDraftMethod {
            let infoString = args?["draftInfo"] as? String
            if moduleManager?.saveCurrentDraft(withDraftInfo: infoString) == true {
                completion(nil, nil)
            } else {
                completion(nil, NSError(domain: "", code: -1))
            }
        } else if methodName == CompileVideoMethod {
            completion(nil, nil)
        }
    }

    public func publish(
        withProjectId projectId: String,
        coverImagePath: String?,
        hasDraft: Bool,
        videoPath: String?,
        description: String?,
        videoEdit videoEditNavigationController: UINavigationController
    ) {
        videoEditNavigationController.dismiss(animated: true) {
            self.sendFlutterMethod(VideoEditResultEvent, arguments: [:], channel: self.mainChannel)
        }
    }
}
""",
        )
        write(plugin / "ios" / "Assets" / ".keep", "")
        write(plugin / "ios" / "Frameworks" / "NvShortVideoCore.xcframework" / ".keep", "")
        write(
            plugin
            / "ios"
            / "Frameworks"
            / "NvShortVideoCore.xcframework"
            / "ios-arm64"
            / "NvShortVideoCore.framework"
            / "Modules"
            / "NvShortVideoCore.swiftmodule"
            / "arm64-apple-ios.swiftinterface",
            """public class NvTimelineDataManager {
  public class func managerAvailable() -> Swift.Bool
  public class func destroySharedInstance(destroyContext: Swift.Bool)
  public func newProject(localFilePaths: [Swift.String], configration: NvProEditConfig) -> Swift.Bool
}
public class NvProEditConfig {}
public class NvProjectManager {
  public class func storeTimelineData()
  public class func updateProjectInfoFile()
}
""",
        )
    else:
        write(plugin / "ios" / "nvshortvideo.podspec", "Pod::Spec.new do |s|\n  s.name = 'nvshortvideo'\nend\n")
    return plugin

def validate_flutter_complete(work: Path) -> None:
    target = work / "flutter_target"
    source = work / "flutter_source_complete"
    create_flutter_target(
        target,
        bundle_identifier="com.example.flutterFixture",
        modern_ios_template=True,
    )
    plugin = create_flutter_plugin(source, complete_ios=True)
    identity_args = ["--package-name", "com.meishe.duanshipindemo"]
    output = run_integration(target, "flutter", plugin, identity_args)
    assert_contains(
        output,
        [
            "Skill: `meishe-flutter-duanshipin-docking`",
            "Flutter plugin: the selected official `nvshortvideo` package is used",
            "Status: `passed`",
            IOS_VALIDATION_MARKER,
            "Flutter iOS: podspec found",
            "Flutter iOS: vendored xcframeworks found",
            "Flutter iOS: bridge completion check passed",
            "Flutter iOS official-Demo compatibility",
            "Patched verified Flutter iOS AutoCut draft lifecycle and publish ordering",
            "Flutter: self-contained SDK check passed",
            "lib/meishe_short_video_docking.dart",
            "flutter analyze lib",
            "Dependency Installation",
            "Status: `execution mode choice required`",
            "用户执行（推荐）",
            "自动执行：Agent 执行已列出的任务内操作",
            "额外消耗 Token 和时间",
            "可见回复要求",
            "折叠的“处理中”区域",
            "真机要求：美摄短视频 Demo 必须运行在已连接的真实设备上",
            "Flutter packages",
            "Command/method: `flutter pub get`",
            "Flutter Android dependencies and Debug build",
            "Command/method: `flutter build apk --debug`",
            "Flutter Android package: `com.meishe.duanshipindemo`",
            "Flutter iOS Bundle Identifier: `com.meishe.duanshipindemo`",
            "Set Flutter Android namespace/applicationId",
            "Moved Flutter Android MainActivity",
            "Set Flutter iOS `Runner` app/test Bundle Identifier",
            "Generated Flutter iOS Podfile for the no-pub app template",
            "Configured Flutter iOS Profile.xcconfig",
            "Assigned Flutter iOS `Runner` Profile.xcconfig",
            "Generated Flutter dual-platform run guide in README",
            "Podfile will be generated with explicit iOS 13.0",
        ],
        "Flutter complete dry-run",
    )
    assert_not_contains(
        output,
        [
            "Flutter iOS: bridge file missing",
            "Flutter iOS readiness failed",
            "AutoCut draft compatibility was skipped",
        ],
        "Flutter dry-run planned vendor state",
    )
    if sys.platform == "darwin":
        assert_contains(
            output,
            ["Flutter iOS CocoaPods", "Command/method: `pod install`"],
            "Flutter iOS dependency handoff",
        )
        if not (
            output.index("Flutter packages")
            < output.index("Flutter iOS CocoaPods")
            < output.index("Flutter Android dependencies and Debug build")
        ):
            fail("Flutter dual-platform dependency steps must be Pub, iOS, then Android")
    elif output.index("Flutter packages") >= output.index("Flutter Android dependencies and Debug build"):
        fail("Flutter Pub dependencies must precede the Android build step")
    run_integration_apply(target, "flutter", plugin, identity_args)
    demo = read(target / "lib" / "meishe_short_video_demo.dart")
    publish = read(target / "lib" / "meishe_short_video_publish.dart")
    wrapper = read(target / "lib" / "meishe_short_video_docking.dart")
    feature_config = read(target / "lib" / "meishe_feature_config.dart")
    self_check = read(target / "meishe_flutter_ios_self_check.md")
    server_handoff = read(target / "meishe_server_config_handoff.md")
    configuration_handoff = read(target / "meishe_configuration_handoff.md")
    android_build = read(target / "android" / "app" / "build.gradle.kts")
    android_activity = target / "android" / "app" / "src" / "main" / "kotlin"
    old_activity = android_activity / "com" / "example" / "flutter_fixture" / "MainActivity.kt"
    new_activity = android_activity / "com" / "meishe" / "duanshipindemo" / "MainActivity.kt"
    ios_project = read(target / "ios" / "Runner.xcodeproj" / "project.pbxproj")
    podfile = read(target / "ios" / "Podfile")
    pubspec = read(target / "pubspec.yaml")
    readme = read(target / "README.md")
    with (target / "ios" / "Runner" / "Info.plist").open("rb") as fh:
        info_plist = plistlib.load(fh)
    if info_plist.get("NSAppTransportSecurity", {}).get("NSAllowsArbitraryLoads") is not True:
        fail("Flutter official Demo identity must enable its verified temporary ATS compatibility")
    assert_contains(
        pubspec,
        ["- assets/meishe_feature_watermark.png"],
        "Flutter watermark pubspec asset declaration",
    )
    for watermark in (
        target / "assets" / "meishe_feature_watermark.png",
        target / "android" / "app" / "src" / "main" / "res" / "drawable-nodpi" / "meishe_feature_watermark.png",
        target / "ios" / "MeisheFeatureAssets.xcassets" / "meishe_feature_watermark.imageset" / "meishe_feature_watermark.png",
        target / "ios" / "MeisheFeatureAssets.xcassets" / "meishe_feature_watermark.imageset" / "Contents.json",
    ):
        if not watermark.is_file():
            fail(f"Flutter generated watermark asset missing: {watermark}")
    assert_contains(
        android_build,
        [
            'namespace = "com.meishe.duanshipindemo"',
            'applicationId = "com.meishe.duanshipindemo"',
        ],
        "Flutter Android Kotlin DSL identity",
    )
    if old_activity.exists() or not new_activity.is_file():
        fail("Flutter Android MainActivity must move to the requested package source path")
    assert_contains(
        read(new_activity),
        ["package com.meishe.duanshipindemo"],
        "Flutter Android MainActivity package",
    )
    assert_contains(
        ios_project,
        [
            "PRODUCT_BUNDLE_IDENTIFIER = com.meishe.duanshipindemo;",
            "PRODUCT_BUNDLE_IDENTIFIER = com.meishe.duanshipindemo.RunnerTests;",
            "Profile.xcconfig",
            "baseConfigurationReference = 4D454953484550524F46494C /* Profile.xcconfig */;",
        ],
        "Flutter iOS Runner/RunnerTests identity and Profile assignment",
    )
    assert_not_contains(
        ios_project,
        ["com.example.flutterFixture"],
        "Flutter iOS stale identity removal",
    )
    assert_contains(
        podfile,
        [
            "platform :ios, '13.0'",
            "flutter_ios_podfile_setup",
            "flutter_install_all_ios_pods",
            "use_frameworks!",
        ],
        "Flutter iOS generated Podfile",
    )
    for mode, filename in (("debug", "Debug.xcconfig"), ("release", "Release.xcconfig"), ("profile", "Profile.xcconfig")):
        assert_contains(
            read(target / "ios" / "Flutter" / filename),
            [
                f'Pods-Runner.{mode}.xcconfig',
                '#include "Generated.xcconfig"',
            ],
            f"Flutter iOS {filename}",
        )
    assert_contains(
        readme,
        [
            "User-maintained introduction.",
            "<!-- BEGIN MEISHE_FLUTTER_RUN_GUIDE -->",
            "Flutter packages",
            "flutter pub get",
            "Flutter iOS CocoaPods",
            "pod install",
            "Flutter Android dependencies and Debug build",
            "flutter build apk --debug",
            "flutter run -d <ANDROID_DEVICE_ID>",
            "flutter run -d <IOS_DEVICE_ID>",
            "Android Emulator、iOS Simulator",
            "不能用于运行或验收",
            "Runner.xcworkspace",
            "Signing & Capabilities",
            "Configuration Handoff",
            str((target / "lib" / "meishe_feature_config.dart").resolve()),
            "Hot Restart",
        ],
        "Flutter dual-platform README run guide",
    )
    assert_contains(
        configuration_handoff,
        [
            "### 配置修改与生效速览",
            "| 配置项 | 修改入口 | 适用平台 | 最快生效方式 | 重新构建条件 | 无需执行 |",
            "| Android、iOS |",
            str((target / "lib" / "meishe_feature_config.dart").resolve()),
            str((target / "lib" / "meishe_short_video_docking.dart").resolve()),
            "大写 R（Hot Restart）",
            "flutter run -d <ANDROID_DEVICE_ID>",
            "flutter run -d <IOS_DEVICE_ID>",
            "真机要求：美摄短视频 Demo 必须运行在已连接的真实设备上",
            "不需要重新执行 flutter pub get",
            "不要默认执行 flutter clean",
            "Signing & Capabilities",
        ],
        "Flutter command-level configuration handoff",
    )
    user_feature_marker = "// USER_FEATURE_CONFIG_MUST_BE_PRESERVED"
    write(
        target / "lib" / "meishe_feature_config.dart",
        feature_config + f"\n{user_feature_marker}\n",
    )
    run_integration_apply(target, "flutter", plugin, identity_args)
    assert_contains(
        read(target / "lib" / "meishe_feature_config.dart"),
        [user_feature_marker],
        "Flutter user feature configuration preservation",
    )
    rerun_readme = read(target / "README.md")
    if rerun_readme.count("<!-- BEGIN MEISHE_FLUTTER_RUN_GUIDE -->") != 1:
        fail("Flutter README integration block must remain idempotent")
    assert_contains(
        rerun_readme,
        ["User-maintained introduction."],
        "Flutter README user content preservation",
    )
    gradle_properties = read(target / "android" / "gradle.properties")
    android_bridge = read(
        target
        / "vendor"
        / "meishe"
        / "nvshortvideo"
        / "android"
        / "src"
        / "main"
        / "java"
        / "com"
        / "meishe"
        / "nvshortvideo"
        / "VideoEditPlugin.java"
    )
    ios_bridge = read(
        target
        / "vendor"
        / "meishe"
        / "nvshortvideo"
        / "ios"
        / "Classes"
        / "VideoEditPlugin.swift"
    )
    ios_draft_bridge = read(
        target
        / "vendor"
        / "meishe"
        / "nvshortvideo"
        / "ios"
        / "Classes"
        / "NvDraftSnapshotBridge.swift"
    )
    assert_contains(
        gradle_properties,
        ["android.useAndroidX=true", "android.enableJetifier=true"],
        "Flutter AndroidX/Jetifier compatibility",
    )
    assert_contains(
        android_bridge,
        [
            "NvModuleManager.get().initModel();",
            "methodCallListener.completion(null, null);",
            "private void emitPublishResultOnce(",
            'emitPublishResultOnce(needSaveDraft, videoPath, "");',
            'mVideoEditChannel.invokeMethod("VideoEditResultEvent", arguments);',
            "AppManager.getInstance().finishAllEditActivity();",
        ],
        "Flutter Android config and AutoCut publish compatibility",
    )
    if android_bridge.index('mVideoEditChannel.invokeMethod("VideoEditResultEvent", arguments);') >= android_bridge.index(
        "AppManager.getInstance().finishAllEditActivity();"
    ):
        fail("Flutter Android AutoCut publish event must be emitted before editor shutdown")
    assert_contains(
        ios_bridge,
        [
            "pendingPublishProjectId",
            "pendingDraftProjectId",
            "pendingDraftStaged",
            "pendingDraftCommitted",
            "pendingPublishProjectId = projectId",
            "pendingDraftProjectId = moduleManager?.projectId",
            "NvDraftSnapshotBridge.stageProject(",
            "NvShortVideoPendingDraftProjectId",
            "saveCurrentDraft(withDraftInfo: infoString)",
            "NvModuleManager.projectInfoForProject(draftProjectId)",
            "project was not added to the draft list",
            "NvDraftSnapshotBridge.deleteRenderedMedia(projectId: projectId)",
        ],
        "Flutter iOS AutoCut draft persistence bridge",
    )
    send_position = ios_bridge.index("sendFlutterMethod(VideoEditResultEvent")
    dismiss_position = ios_bridge.index("dismiss(animated: true)", send_position)
    if send_position >= dismiss_position:
        fail("Flutter iOS publish event must be sent before the SDK editor is dismissed")
    stage_position = ios_bridge.index("NvDraftSnapshotBridge.stageProject(")
    if stage_position >= send_position:
        fail("Flutter iOS AutoCut draft must be staged before publishing to Dart")
    assert_not_contains(
        ios_bridge,
        ["NvProjectManager.storeCurrentProject(\n                    projectId: projectId"],
        "Flutter iOS temporary callback project ID isolation",
    )
    assert_contains(
        ios_draft_bridge,
        [
            "NvAutoCutDraftMedia",
            "NvTimelineDataManager.sharedInstance()",
            "newProject(",
            "localFilePaths: [durableVideoURL.path]",
            "let draftProjectId = model.projectId",
            "mediaByProject[draftProjectId]",
            "deleteRenderedMedia(projectId: String)",
        ],
        "Flutter iOS AutoCut standard draft helper",
    )
    assert_contains(
        publish,
        [
            "resizeToAvoidBottomInset: true",
            "behavior: HitTestBehavior.translucent",
            "FocusManager.instance.primaryFocus?.unfocus()",
            "keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag",
        ],
        "Flutter iOS publish keyboard handling",
    )
    assert_contains(
        demo,
        [
            "import 'dart:async';",
            "import 'dart:io';",
            "with WidgetsBindingObserver",
            "WidgetsBinding.instance.addObserver(this)",
            "WidgetsBinding.instance.addPostFrameCallback",
            "state == AppLifecycleState.resumed",
            "Future<void>? _materialPreparation",
            "bool get _isPreparingMaterials => _materialPreparation != null",
            "if (_materialReady || _isPreparingMaterials)",
            "unawaited(request.whenComplete(()",
            "_materialReady = true",
            "_prepareWarning = null",
            "预制美颜资源正在后台准备，不影响核心功能。",
            "canRetry: !_isPreparingMaterials",
            "onRetry: _prepareMaterialsInBackground",
            "void _observeFeatureMaterialRefresh(Future<bool> request)",
            "refreshMaterials && Platform.isIOS",
            "await _ensureServerConfigured();",
            "MeisheShortVideoDocking.downloadPrefabricatedMaterial()",
            "refreshMaterials: true",
        ],
        "Flutter generated background material preparation",
    )
    assert_contains(
        wrapper,
        [
            "static Future<bool> downloadPrefabricatedMaterial() async",
            "await shortVideoOperator().downloadPrefabricatedMaterial()",
            "static NvVideoConfig createVideoConfig()",
            "import 'meishe_feature_config.dart';",
            "return MeisheFeatureConfig.apply(config);",
            '"assetAutoCutUrl": "https://creative.meishesdk.com/api/app"',
        ],
        "Flutter generated material and AutoCut wrapper",
    )
    assert_contains(
        feature_config,
        [
            "Flutter 专属配置",
            "config.albumConfig.useAutoCut = true;",
            "NvCaptureMenuItem.speed",
            "NvCaptureMenuItem.matting",
            "NvCaptureBottomMenuItem.template",
            "NvEditMenuItem.text",
            "删除 text 会删除文字入口及其下级功能",
            "static NvVideoConfig apply",
            "defaultBottomMenuSelectItem must exist",
            "editConfig.maxVolume must be greater than 0 and no greater than 8",
            "meishe_feature_watermark.png",
            "must reference a real watermark image",
            "width and height must be greater than 0",
            "offsets must be non-negative",
            "position is required",
        ],
        "Flutter user-editable feature configuration",
    )
    assert_contains(
        self_check,
        [
            "Flutter iOS 素材请求自检",
            "NSAllowsArbitraryLoads = true",
            "先等待服务配置回执",
            "`_runFeature` 直接非阻塞发起素材刷新",
            "`refreshMaterials: true`",
            "不调用受首页单飞状态保护的 `_prepareMaterialsInBackground()`",
            "Android 点击路径不变",
            "分别从编辑素材选择、模板页和拍摄模板菜单进入一键成片",
            "hasDraft = false",
            "回调 `projectId` 是临时任务 ID",
            "NvDraftSnapshotBridge",
            "skill 只包含代码，不包含视频",
            "导出视频",
            "invalid JSON",
            "fxExpression is not authorised",
            "flutter run -d <IOS_DEVICE_ID>",
            "devicectl",
        ],
        "Flutter iOS generated self-check",
    )
    assert_contains(
        server_handoff,
        [
            "https://creative.meishesdk.com/api/app",
            "Android bridge 直接消费基础地址",
            "iOS bridge 按官方契约处理端点",
            "标准编辑页",
            "导出视频",
        ],
        "Flutter AutoCut server handoff",
    )
    assert_not_contains(
        demo + wrapper,
        [
            "bool _isPreparing = true",
            "enabled: !_isPreparing",
            "素材下载未完成",
            "素材准备中...",
            ".timeout(timeout, onTimeout: () => false)",
            "_activeMaterialRequests",
            "_prepareMaterialsInBackground(force: true)",
            "(!force &&",
            "Future<void> _runFeature(Future<dynamic> Function() action) async {\n    _prepareMaterialsInBackground();",
            "<YOUR_MEISHE_CLIENT_ID>",
            "<YOUR_MEISHE_CLIENT_SECRET>",
            "<YOUR_MEISHE_ASSEMBLY_ID>",
        ],
        "Flutter generated non-blocking material preparation",
    )
    run_feature_start = demo.index("Future<void> _runFeature(")
    run_feature = demo[
        run_feature_start : demo.index("\n  @override\n  Widget build", run_feature_start)
    ]
    assert_contains(
        run_feature,
        [
            "if (refreshMaterials && Platform.isIOS)",
            "await _ensureServerConfigured();",
            "_observeFeatureMaterialRefresh(",
            "MeisheShortVideoDocking.downloadPrefabricatedMaterial()",
            "await action();",
        ],
        "Flutter iOS runFeature direct material refresh",
    )
    assert_not_contains(
        run_feature,
        [
            "_prepareMaterialsInBackground()",
            "_downloadPrefabricatedMaterials()",
            "_materialPreparation",
            "_isPreparingMaterials",
        ],
        "Flutter iOS entry refresh isolation from home single-flight state",
    )
    flutter_entries = {
        "capture": demo[demo.index("label: '拍摄'") : demo.index("label: '合拍'")],
        "dual capture": demo[demo.index("label: '合拍'") : demo.index("label: '编辑'")],
        "edit": demo[demo.index("label: '编辑'") : demo.index("label: '草稿'")],
    }
    for label, block in flutter_entries.items():
        assert_contains(
            block,
            ["_runFeature(", "refreshMaterials: true"],
            f"Flutter iOS {label} entry material refresh",
        )

def validate_flutter_missing_ios(work: Path) -> None:
    target = work / "flutter_target_missing"
    source = work / "flutter_source_missing"
    create_flutter_target(target)
    plugin = create_flutter_plugin(source, complete_ios=False)
    output = run_integration(target, "flutter", plugin)
    assert_contains(
        output,
        [
            "Status: `warning`",
            "Flutter iOS readiness failed",
            "Provide the complete official Flutter package from Meishe Developer Center (`Flutter工程`)",
            "do not substitute the native iOS `Pods-NvShortVideoEdit` package",
        ],
        "Flutter missing-iOS dry-run",
    )

def validate_flutter_missing_android_native_libraries(work: Path) -> None:
    target = work / "flutter_target_missing_android_native"
    source = work / "flutter_source_missing_android_native"
    create_flutter_target(target)
    plugin = create_flutter_plugin(source, complete_ios=True, complete_android_native=False)
    output = run_integration_failure(target, "flutter", plugin)
    assert_contains(
        output,
        [
            "Flutter Android runtime validation cannot continue",
            "libNvStreamingSdkCore.so",
            "libNvMSAICutter.so",
            "--aar-path <path>",
        ],
        "Flutter missing Android native libraries",
    )

    original_pubspec = read(target / "pubspec.yaml")
    run_integration_apply_failure(target, "flutter", plugin)
    if (target / "vendor" / "meishe" / "nvshortvideo").exists():
        fail("Flutter failed preflight must not create the project-local SDK directory")
    if read(target / "pubspec.yaml") != original_pubspec:
        fail("Flutter failed preflight must not modify pubspec.yaml")

    supplement = work / "flutter_android_native_supplement" / "NvShortVideoCore.aar"
    write_flutter_android_aar(supplement, include_native_libraries=True)
    run(
        [
            str(PLATFORM_SCRIPTS["flutter"]),
            "--target-root",
            str(target),
            "--plugin-path",
            str(plugin),
            "--aar-path",
            str(supplement),
        ],
        "Flutter Android native-library supplement apply",
    )
    for entry in (
        "arm64-v8a/libNvStreamingSdkCore.so",
        "arm64-v8a/libNvMSAICutter.so",
        "armeabi-v7a/libNvStreamingSdkCore.so",
        "armeabi-v7a/libNvMSAICutter.so",
    ):
        generated = target / "vendor" / "meishe" / "nvshortvideo" / "android" / "src" / "main" / "jniLibs" / entry
        if not generated.is_file():
            fail(f"Flutter Android supplement did not generate `{generated}`")


def validate_flutter_missing_android_beauty_resources(work: Path) -> None:
    target = work / "flutter_target_missing_android_beauty"
    source = work / "flutter_source_missing_android_beauty"
    create_flutter_target(target, ios=False)
    plugin = create_flutter_plugin(
        source,
        complete_ios=True,
        include_android_beauty_shape_resources=False,
    )
    output = run_integration(target, "flutter", plugin)
    assert_contains(
        output,
        [
            "does not contain optional fixed beauty-shape resources",
            "Shape/MicroShape beauty categories may be empty or incomplete",
            "not an online-material request failure",
        ],
        "Flutter Android optional beauty resource warning",
    )


def validate_flutter_android_only(work: Path) -> None:
    target = work / "flutter_target_android_only"
    source = work / "flutter_source_android_only"
    create_flutter_target(target, ios=False, android_dsl="groovy")
    plugin = create_flutter_plugin(source, complete_ios=True)
    identity_args = ["--package-name", "com.customer.flutterandroid"]
    output = run_integration(target, "flutter", plugin, identity_args)
    assert_contains(
        output,
        [
            "Flutter Android native engine libraries are complete",
            "Flutter packages",
            "Flutter Android dependencies and Debug build",
            "Command/method: `flutter build apk --debug`",
            "Flutter Android package: `com.customer.flutterandroid`",
            "Generated Flutter Android run guide in README",
        ],
        "Flutter Android-only route",
    )
    assert_not_contains(
        output,
        ["Flutter iOS:", "iOS Quick Verify", "iOS signing", "pod install", IOS_VALIDATION_MARKER],
        "Flutter Android-only route isolation",
    )
    run_integration_apply(target, "flutter", plugin, identity_args)
    wrapper = read(target / "lib" / "meishe_short_video_docking.dart")
    bridge = read(
        target
        / "vendor"
        / "meishe"
        / "nvshortvideo"
        / "android"
        / "src"
        / "main"
        / "java"
        / "com"
        / "meishe"
        / "nvshortvideo"
        / "VideoEditPlugin.java"
    )
    assert_contains(
        read(target / "lib" / "meishe_feature_config.dart"),
        ["config.albumConfig.useAutoCut = true;", "NvCaptureBottomMenuItem.template", "NvEditMenuItem.text"],
        "Flutter Android-only feature config",
    )
    assert_contains(wrapper, ["MeisheFeatureConfig.apply"], "Flutter Android-only wrapper")
    assert_contains(
        bridge,
        ["private void emitPublishResultOnce(", 'emitPublishResultOnce(needSaveDraft, videoPath, "");'],
        "Flutter Android-only AutoCut publish fallback",
    )
    assert_contains(
        read(target / "android" / "app" / "build.gradle"),
        [
            'namespace "com.customer.flutterandroid"',
            'applicationId "com.customer.flutterandroid"',
        ],
        "Flutter Android Groovy identity",
    )
    android_readme = read(target / "README.md")
    android_handoff = read(target / "meishe_configuration_handoff.md")
    assert_contains(
        android_readme,
        ["flutter run -d <ANDROID_DEVICE_ID>", "flutter build apk --debug"],
        "Flutter Android-only README",
    )
    assert_not_contains(
        android_readme,
        ["### iOS", "pod install", ".xcworkspace", "<IOS_DEVICE_ID>"],
        "Flutter Android-only README isolation",
    )
    assert_contains(
        android_handoff,
        ["Hot Restart", "flutter run -d <ANDROID_DEVICE_ID>", "Flutter Android 身份、License 与原生资源"],
        "Flutter Android-only configuration handoff",
    )
    assert_not_contains(
        android_handoff,
        ["<IOS_DEVICE_ID>", ".xcworkspace", "Flutter iOS 身份"],
        "Flutter Android-only configuration handoff isolation",
    )


def validate_flutter_ios_only(work: Path) -> None:
    target = work / "flutter_target_ios_only"
    source = work / "flutter_source_ios_only"
    create_flutter_target(
        target,
        android=False,
        bundle_identifier="com.example.flutterFixture",
        modern_ios_template=True,
    )
    plugin = create_flutter_plugin(source, complete_ios=True, include_android=False)
    identity_args = ["--package-name", "com.customer.flutterios"]
    output = run_integration(target, "flutter", plugin, identity_args)
    assert_contains(
        output,
        [
            "Flutter iOS: podspec found",
            "Flutter iOS: bridge completion check passed",
            "Flutter iOS Bundle Identifier: `com.customer.flutterios`",
            "Generated Flutter iOS run guide in README",
            IOS_VALIDATION_MARKER,
        ],
        "Flutter iOS-only route",
    )
    assert_not_contains(
        output,
        ["Flutter Android", "AndroidX/Jetifier", "native engine libraries", "flutter build apk --debug"],
        "Flutter iOS-only route isolation",
    )
    run_integration_apply(target, "flutter", plugin, identity_args)
    assert_contains(
        read(target / "lib" / "meishe_feature_config.dart"),
        [
            "config.albumConfig.useAutoCut = true;",
            "config.templateConfig.useAutoCut = true;",
            "NvCaptureBottomMenuItem.template",
            "NvCaptureMenuItem.matting",
        ],
        "Flutter iOS-only feature config",
    )
    assert_contains(
        read(target / "lib" / "meishe_short_video_docking.dart"),
        ['"assetAutoCutUrl": "https://creative.meishesdk.com/api/app"', "MeisheFeatureConfig.apply"],
        "Flutter iOS-only wrapper",
    )
    with (target / "ios" / "Runner" / "Info.plist").open("rb") as fh:
        info_plist = plistlib.load(fh)
    if info_plist.get("NSAppTransportSecurity", {}).get("NSAllowsArbitraryLoads") is True:
        fail("Flutter customer Bundle Identifier must not enable global NSAllowsArbitraryLoads")
    if not (target / "meishe_flutter_ios_self_check.md").exists():
        fail("Flutter iOS integration must generate the material-request self-check handoff")
    assert_contains(
        read(target / "ios" / "Runner.xcodeproj" / "project.pbxproj"),
        [
            "PRODUCT_BUNDLE_IDENTIFIER = com.customer.flutterios;",
            "PRODUCT_BUNDLE_IDENTIFIER = com.customer.flutterios.RunnerTests;",
        ],
        "Flutter iOS-only identity",
    )
    ios_readme = read(target / "README.md")
    ios_handoff = read(target / "meishe_configuration_handoff.md")
    assert_contains(
        ios_readme,
        ["pod install", "Runner.xcworkspace", "flutter run -d <IOS_DEVICE_ID>"],
        "Flutter iOS-only README",
    )
    assert_not_contains(
        ios_readme,
        ["### Android", "flutter build apk --debug", "<ANDROID_DEVICE_ID>"],
        "Flutter iOS-only README isolation",
    )
    assert_contains(
        ios_handoff,
        ["Hot Restart", "flutter run -d <IOS_DEVICE_ID>", "Runner.xcworkspace", "Flutter iOS 身份、签名、License 与原生资源"],
        "Flutter iOS-only configuration handoff",
    )
    assert_not_contains(
        ios_handoff,
        ["<ANDROID_DEVICE_ID>", "Flutter Android 身份"],
        "Flutter iOS-only configuration handoff isolation",
    )


def validate_flutter_unverified_android_publish_shape(work: Path) -> None:
    target = work / "flutter_target_unverified_publish"
    source = work / "flutter_source_unverified_publish"
    create_flutter_target(target, ios=False)
    plugin = create_flutter_plugin(source, complete_ios=True)
    bridge = plugin / "android" / "src" / "main" / "java" / "com" / "meishe" / "nvshortvideo" / "VideoEditPlugin.java"
    text = read(bridge).replace(
        "public void onCoverSaveFailed() {\n                    }",
        "public void onCoverSaveFailed() {\n                        logUnknownVersion();\n                    }",
        1,
    )
    write(bridge, text)
    output = run_integration(target, "flutter", plugin)
    assert_contains(
        output,
        [
            "does not match the verified ShortVideo 2.0.2.1 source shape",
            "No vendor patch was applied",
        ],
        "Flutter unverified AutoCut publish bridge warning",
    )
    assert_not_contains(
        output,
        ["Patched verified Flutter Android AutoCut publish fallback"],
        "Flutter unverified AutoCut publish bridge guard",
    )
    run_integration_apply(target, "flutter", plugin)
    local_bridge = read(
        target
        / "vendor"
        / "meishe"
        / "nvshortvideo"
        / "android"
        / "src"
        / "main"
        / "java"
        / "com"
        / "meishe"
        / "nvshortvideo"
        / "VideoEditPlugin.java"
    )
    assert_contains(local_bridge, ["logUnknownVersion();"], "Flutter unverified bridge retained")
    assert_not_contains(local_bridge, ["private void emitPublishResultOnce("], "Flutter unverified bridge not patched")


def validate_flutter_unverified_ios_autocut_draft_shape(work: Path) -> None:
    target = work / "flutter_target_unverified_ios_draft"
    source = work / "flutter_source_unverified_ios_draft"
    create_flutter_target(target, android=False)
    plugin = create_flutter_plugin(source, complete_ios=True, include_android=False)
    bridge = plugin / "ios" / "Classes" / "VideoEditPlugin.swift"
    write(bridge, read(bridge).replace("private var moduleManager: NvModuleManager?", "private var moduleManagerV2: NvModuleManager?", 1))
    output = run_integration(target, "flutter", plugin)
    assert_contains(
        output,
        [
            "does not match the verified ShortVideo 2.0.2.1 AutoCut draft source shape",
            "vendor bridge was left unchanged",
        ],
        "Flutter unverified iOS AutoCut draft bridge warning",
    )
    assert_not_contains(
        output,
        ["Patched verified Flutter iOS AutoCut draft lifecycle and publish ordering"],
        "Flutter unverified iOS AutoCut draft bridge guard",
    )
    run_integration_apply(target, "flutter", plugin)
    local_bridge = read(target / "vendor" / "meishe" / "nvshortvideo" / "ios" / "Classes" / "VideoEditPlugin.swift")
    assert_contains(local_bridge, ["moduleManagerV2"], "Flutter unverified iOS bridge retained")
    assert_not_contains(
        local_bridge,
        ["pendingPublishProjectId", "NvProjectManager.storeCurrentProject"],
        "Flutter unverified iOS bridge not partially patched",
    )


def validate_flutter_sdk_atomic_replace(work: Path) -> None:
    target = work / "flutter_target_atomic_replace"
    source = work / "flutter_source_atomic_replace"
    create_flutter_target(target, ios=False)
    plugin = create_flutter_plugin(source, complete_ios=True)
    run_integration_apply(target, "flutter", plugin)
    local_plugin = target / "vendor" / "meishe" / "nvshortvideo"
    stale = local_plugin / "stale-from-older-sdk.txt"
    write(stale, "stale\n")

    run_integration_apply(target, "flutter", plugin)
    if stale.exists():
        fail("Atomic SDK replacement must remove files absent from the new SDK package")
    backups = list((target / ".meishe_docking_backup").rglob("stale-from-older-sdk.txt"))
    if not backups:
        fail("Atomic SDK replacement must retain the previous SDK directory in backup")
    backup_root = target / ".meishe_docking_backup"
    backup_entries_before = {
        path.relative_to(backup_root).as_posix(): path.read_bytes()
        for path in backup_root.rglob("*")
        if path.is_file()
    }
    run_integration_apply(target, "flutter", plugin)
    backup_entries_after = {
        path.relative_to(backup_root).as_posix(): path.read_bytes()
        for path in backup_root.rglob("*")
        if path.is_file()
    }
    if backup_entries_after != backup_entries_before:
        before_keys = set(backup_entries_before)
        after_keys = set(backup_entries_after)
        changed = sorted(
            key
            for key in before_keys & after_keys
            if backup_entries_before[key] != backup_entries_after[key]
        )
        fail(
            "Unchanged SDK input must not change the deterministic SDK backup manifest; "
            f"added={sorted(after_keys - before_keys)}, removed={sorted(before_keys - after_keys)}, "
            f"changed={changed}"
        )
    assert_contains(
        read(target / "meishe_docking_report.md"),
        ["SDK source is unchanged; retained the validated project-local vendor copy"],
        "Flutter unchanged SDK rerun",
    )


def validate_flutter_missing_targets(work: Path) -> None:
    target = work / "flutter_target_no_platforms"
    source = work / "flutter_source_no_platforms"
    create_flutter_target(target, android=False, ios=False)
    plugin = create_flutter_plugin(source, complete_ios=True)
    output = run_integration_failure(target, "flutter", plugin)
    assert_contains(
        output,
        ["Flutter target must contain an `android/` directory, an `ios/` directory, or both."],
        "Flutter missing target platforms",
    )


def validate_flutter_renamed_ios_target(work: Path) -> None:
    target = work / "flutter_target_renamed_ios"
    source = work / "flutter_source_renamed_ios"
    create_flutter_target(
        target,
        android=False,
        bundle_identifier="com.example.renamed",
        modern_ios_template=True,
    )
    ios_root = target / "ios"
    shutil.move(
        ios_root / "Runner.xcodeproj",
        ios_root / "ShellProject.xcodeproj",
    )
    shutil.move(ios_root / "Runner", ios_root / "ShortVideoApp")
    write(
        ios_root / "ShellProject.xcodeproj" / "project.pbxproj",
        flutter_ios_project_fixture("com.example.renamed", target_name="ShortVideoApp"),
    )
    plugin = create_flutter_plugin(source, complete_ios=True)
    identity_args = ["--ios-bundle-identifier", "com.customer.flutter.ios"]
    output = run_integration(target, "flutter", plugin, identity_args)
    assert_contains(
        output,
        [
            "Flutter iOS app target: `ShortVideoApp`",
            "Set Flutter iOS `ShortVideoApp` app/test Bundle Identifier",
            "ShellProject.xcworkspace",
            "ShortVideoApp / Signing & Capabilities",
        ],
        "Flutter renamed iOS target dry-run",
    )
    run_integration_apply(target, "flutter", plugin, identity_args)
    podfile = read(ios_root / "Podfile")
    assert_contains(
        podfile,
        ["project 'ShortVideoApp'", "target 'ShortVideoApp' do"],
        "Flutter renamed iOS Podfile",
    )
    assert_not_contains(podfile, ["target 'Runner' do"], "Flutter renamed iOS target isolation")
    for filename, mode in (
        ("Debug.xcconfig", "debug"),
        ("Release.xcconfig", "release"),
        ("Profile.xcconfig", "profile"),
    ):
        xcconfig = read(ios_root / "Flutter" / filename)
        assert_contains(
            xcconfig,
            [f"Pods-ShortVideoApp/Pods-ShortVideoApp.{mode}.xcconfig"],
            f"Flutter renamed iOS {filename}",
        )
        assert_not_contains(xcconfig, ["Pods-Runner"], f"Flutter renamed iOS {filename} isolation")
    handoff = read(target / "meishe_configuration_handoff.md")
    assert_contains(
        handoff,
        ["ShellProject.xcworkspace", "ShortVideoApp", "Product > Run"],
        "Flutter renamed iOS configuration handoff",
    )


def validate_flutter_platform_identities(work: Path) -> None:
    target = work / "flutter_target_platform_identities"
    source = work / "flutter_source_platform_identities"
    create_flutter_target(target, bundle_identifier="com.example.flutter")
    plugin = create_flutter_plugin(source, complete_ios=True)
    identity_args = [
        "--android-package-name",
        "com.customer.flutter.android",
        "--ios-bundle-identifier",
        "com.customer.flutter.ios",
    ]
    run_integration_apply(target, "flutter", plugin, identity_args)
    android_gradle = read(target / "android" / "app" / "build.gradle.kts")
    ios_project = read(target / "ios" / "Runner.xcodeproj" / "project.pbxproj")
    readme = read(target / "README.md")
    report = read(target / "meishe_docking_report.md")
    assert_contains(
        android_gradle,
        [
            'namespace = "com.customer.flutter.android"',
            'applicationId = "com.customer.flutter.android"',
        ],
        "Flutter Android-specific identity",
    )
    assert_not_contains(
        android_gradle,
        ["com.customer.flutter.ios"],
        "Flutter Android identity isolation",
    )
    assert_contains(
        ios_project,
        ["PRODUCT_BUNDLE_IDENTIFIER = com.customer.flutter.ios;"],
        "Flutter iOS-specific identity",
    )
    assert_not_contains(
        ios_project,
        ["com.customer.flutter.android"],
        "Flutter iOS identity isolation",
    )
    assert_contains(
        readme,
        [
            "Android applicationId：`com.customer.flutter.android`",
            "iOS Bundle Identifier：`com.customer.flutter.ios`",
        ],
        "Flutter separate identity handoff",
    )
    assert_contains(
        report,
        [
            "official Demo material service requires the exact Bundle Identifier",
            "`com.meishe.duanshipindemo`",
            "`--ios-bundle-identifier com.meishe.duanshipindemo`",
            "customer server, matching License, and service allowlist",
        ],
        "Flutter customer iOS identity warning",
    )

    conflict_target = work / "flutter_target_platform_identity_conflict"
    conflict_source = work / "flutter_source_platform_identity_conflict"
    create_flutter_target(conflict_target, bundle_identifier="com.example.flutter")
    conflict_plugin = create_flutter_plugin(conflict_source, complete_ios=True)
    failure = run_integration_apply_failure(
        conflict_target,
        "flutter",
        conflict_plugin,
        [
            "--package-name",
            "com.customer.shared",
            "--ios-bundle-identifier",
            "com.customer.ios",
        ],
    )
    assert_contains(
        failure,
        ["Conflicting iOS Bundle Identifier values", "--package-name", "--ios-bundle-identifier"],
        "Flutter identity conflict",
    )
    if (conflict_target / "vendor").exists():
        fail("Flutter identity conflict must fail before files are written")


def validate_flutter_optional_toolchain(work: Path) -> None:
    target = work / "flutter_target_optional_toolchain"
    create_flutter_target(target)
    script = PLATFORM_SCRIPTS["flutter"].with_name("toolchain_validate.py")
    output = run(
        [str(script), "--target-root", str(target)],
        "Flutter optional toolchain skip",
    )
    assert_contains(
        output,
        ["toolchain_validate skipped", "No dependency was downloaded"],
        "Flutter optional toolchain boundary",
    )


def validate_external_path_detection(work: Path) -> None:
    target = work / "flutter_target_external_path"
    source = work / "flutter_source_external_path"
    create_flutter_target(target)
    write(target / "pubspec.lock", "path: D:\\Edge Download\\ShortVideo_Flutter\\flutter\\nvshortvideo\n")
    plugin = create_flutter_plugin(source, complete_ios=True)
    output = run_integration(target, "flutter", plugin)
    assert_contains(
        output,
        [
            "self-contained SDK check failed",
            "External download/package paths remain in config files",
            "pubspec.lock",
        ],
        "External path detection dry-run",
    )
