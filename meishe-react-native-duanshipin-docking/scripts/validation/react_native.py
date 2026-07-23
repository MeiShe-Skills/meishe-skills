"""React Native Android/iOS fixture validation."""

from __future__ import annotations

import json
import plistlib
import shutil
import sys
from pathlib import Path

from meishe_docking_core import Report, add_cocoapods_dependency_step
from routes.react_native.ios import ensure_ruby4_cocoapods_nkf_compatibility

from .shared import (
    IOS_VALIDATION_MARKER,
    PLATFORM_SCRIPTS,
    assert_contains,
    assert_not_contains,
    create_ios_app,
    fail,
    has_xcode_26,
    run_integration,
    run_integration_apply,
    run_integration_apply_failure,
    run_integration_failure,
    read,
    run,
    write,
    write_json,
    write_flutter_android_aar,
)


def create_react_native_target(root: Path, *, android: bool = True, ios: bool = True) -> None:
    write_json(
        root / "package.json",
        {
            "name": "rn-fixture",
            "version": "0.0.1",
            "packageManager": "npm@11.12.1",
            "dependencies": {"react": "19.0.0", "react-native": "0.78.0"},
        },
    )
    write_json(root / "tsconfig.json", {"compilerOptions": {"strict": True}})
    write(root / "README.md", "# RN Fixture\n\nUser-maintained introduction.\n")
    write(root / "jest.config.js", "module.exports = {\n  preset: 'react-native',\n};\n")
    write(
        root / "android" / "app" / "src" / "main" / "AndroidManifest.xml",
        """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:name=".MainApplication" />
</manifest>
""",
    )
    write(
        root / "android" / "gradle.properties",
        "android.useAndroidX=true\n",
    )
    write(root / "android" / "gradlew", "#!/bin/sh\n")
    write(root / "android" / "gradlew.bat", "@echo off\r\n")
    write(
        root / "android" / "build.gradle",
        """buildscript {
    repositories { google(); mavenCentral() }
}

apply plugin: "com.facebook.react.rootproject"
""",
    )
    write(
        root / "android" / "app" / "build.gradle",
        """apply plugin: "com.android.application"

android {
    namespace "rnfixture"
    defaultConfig { applicationId "rnfixture" }
}

dependencies {
    implementation("com.facebook.react:react-android")
}
""",
    )
    write(
        root / "android" / "app" / "src" / "main" / "java" / "rnfixture" / "MainActivity.kt",
        "package rnfixture\n\nimport android.app.Activity\n\nclass MainActivity : Activity()\n",
    )
    write(
        root / "android" / "app" / "src" / "main" / "java" / "rnfixture" / "MainApplication.kt",
        "package rnfixture\n\nclass MainApplication\n",
    )
    write(
        root / "App.tsx",
        """import React from 'react';
import {Colors, Header} from 'react-native/Libraries/NewAppScreen';

function App(): React.JSX.Element {
  return <Header />;
}

export default App;
""",
    )
    create_ios_app(root, "RnFixture")
    write(root / "ios" / "RnFixture" / "AppDelegate.swift", "final class AppDelegate {}\n")
    write(
        root / "ios" / "RnFixture.xcodeproj" / "project.pbxproj",
        """// !$*UTF8*$!
{
  objects = {
/* Begin PBXBuildFile section */
    111111111111111111111111 /* AppDelegate.swift in Sources */ = {isa = PBXBuildFile; fileRef = 222222222222222222222222 /* AppDelegate.swift */; };
/* End PBXBuildFile section */
/* Begin PBXFileReference section */
    222222222222222222222222 /* AppDelegate.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = RnFixture/AppDelegate.swift; sourceTree = "<group>"; };
/* End PBXFileReference section */
/* Begin PBXGroup section */
    333333333333333333333333 /* RnFixture */ = {
      isa = PBXGroup;
      children = (
        222222222222222222222222 /* AppDelegate.swift */,
      );
    };
/* End PBXGroup section */
/* Begin PBXSourcesBuildPhase section */
    444444444444444444444444 /* Sources */ = {
      isa = PBXSourcesBuildPhase;
      files = (
        111111111111111111111111 /* AppDelegate.swift in Sources */,
      );
    };
/* End PBXSourcesBuildPhase section */
  };
}
""",
    )
    write(
        root / "ios" / "Podfile",
        """platform :ios, '15.1'

target 'RnFixture' do
  config = use_native_modules!

  post_install do |installer|
    react_native_post_install(
      installer,
      config[:reactNativePath],
      :mac_catalyst_enabled => false
    )
  end
end
""",
    )
    if not android:
        shutil.rmtree(root / "android")
    if not ios:
        shutil.rmtree(root / "ios")


def validate_react_native_ruby4_cocoapods_compatibility(work: Path) -> None:
    target = work / "rn_target_ruby4_cocoapods"
    create_react_native_target(target, android=False)
    write(
        target / "Gemfile",
        """source 'https://rubygems.org'

gem 'cocoapods', '1.15.2'
""",
    )
    write(
        target / "Gemfile.lock",
        """GEM
  specs:
    cocoapods (1.15.2)
""",
    )
    report = Report(target_root=target, platform="react-native")
    ready = ensure_ruby4_cocoapods_nkf_compatibility(
        target,
        report,
        active_ruby_version=(4, 0, 5),
    )
    if not ready:
        fail("React Native Ruby 4/CocoaPods 1.15.2 compatibility was not detected")
    gemfile = read(target / "Gemfile")
    assert_contains(
        gemfile,
        ["gem 'cocoapods', '1.15.2'", "gem 'nkf'", "Ruby 4 compatibility"],
        "React Native project-scoped Ruby 4 compatibility",
    )
    ensure_ruby4_cocoapods_nkf_compatibility(
        target,
        report,
        active_ruby_version=(4, 0, 5),
    )
    if read(target / "Gemfile").count("gem 'nkf'") != 1:
        fail("React Native Ruby 4 nkf compatibility must be idempotent")
    add_cocoapods_dependency_step(
        target / "ios",
        report,
        "React Native iOS",
        host_platform="darwin",
        active_ruby_version=(4, 0, 5),
        bundled_compatibility_ready=True,
    )
    assert_contains(
        report.to_markdown(),
        [
            "Command/method: `bundle install`",
            "Command/method: `bundle exec pod install`",
            "project-scoped `nkf` compatibility gem",
            "no global Ruby or CocoaPods change is required",
        ],
        "React Native Ruby 4 CocoaPods dependency handoff",
    )


def create_react_native_plugin(
    root: Path,
    *,
    complete_ios: bool,
    complete_android_native: bool = True,
    include_android_beauty_shape_resources: bool = True,
    include_android: bool = True,
    include_demo_license: bool = True,
) -> Path:
    plugin = root / "react_native" / "react-native-nvshortvideo"
    write_json(plugin / "package.json", {"name": "react-native-nvshortvideo", "version": "0.0.1"})
    if include_android:
        write(plugin / "android" / "build.gradle", "apply plugin: 'com.android.library'\n")
        write(
            plugin / "android" / "src" / "main" / "java" / "com" / "meishe" / "nvshortvideo" / "VideoEditPlugin.java",
            """    private void goPublish(boolean needSaveDraft, boolean needSaveCover, boolean needSaveVideo, String videoPath) {
        if (null == getCurrentActivity()) {
            return;
        }
        NvModuleManager.get().saveCover(PathUtils.getCoverDir(), String.valueOf(System.currentTimeMillis()), mCoverPoint, false,
                new NvModuleManager.OnCoverSavedCallBack() {
                    @Override
                    public void onCoverSaved(String path) {
                        WritableMap maps = Arguments.createMap();
                        maps.putBoolean("hasDraft", needSaveDraft);
                        maps.putString("coverImagePath", getSDPath(path));
                        maps.putString("videoPath", videoPath);
                        //目前默认传00
                        maps.putString("projectId", "00");
                        invokeMethod(VIDEO_EDIT_CHANNEL, VIDEO_EDIT_RESULT_EVENT, maps);
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
            plugin / "react-native-nvshortvideo.podspec",
            """Pod::Spec.new do |s|
  s.name = 'react-native-nvshortvideo'
  s.ios.deployment_target = '13.0'
end
""",
        )
        write(plugin / "ios" / "Classes" / "NvShortVideo.swift", "class NvShortVideo {}\n")
        write(
            plugin / "ios" / "Classes" / "VideoEditPlugin.m",
            """#import <NvStreamingSdkCore/NvstreamingSdkCore.h>

@interface VideoEditPlugin()

@property (nonatomic, strong) NvModuleManager* moduleManager;
@property (nonatomic, strong) NvHttpRequestDelegate *requestDelegate;
@end

@implementation VideoEditPlugin

- (instancetype)init {
    self = [super init];
    if (self) {
        self.moduleManager = NvModuleManager.sharedInstance;
        self.moduleManager.delegate = self;
        self.moduleManager.compileDelegate = self;
        [self.moduleManager prepareDownloadFolders];
    }
    return self;
}

- (NSArray<NSString *> *)supportedEvents {
    return @[VideoEditMethodChannel];
}

- (void)handleMethod:(NSString*)methodName
           arguments:(NSDictionary*)arguments
          completion:(nullable void (^)(NSObject * _Nullable response, NSError * _Nullable error))completion {
    if ([methodName isEqualToString:DeleteDraftMethod]) {
        NSString* projectId = arguments[@"projectId"];
        if (projectId && projectId.length > 0) {
            if ([NvModuleManager deleteDraft:projectId]) {
                completion(nil, nil);
                return;
            }
        }
        completion(nil, [NSError errorWithDomain:@"" code:-1 userInfo:@{NSLocalizedDescriptionKey:@"projectId error, draft does not exist"}]);
    } else if([methodName isEqualToString:ExitVideoEditMethod]) {
        NSString* projectId = arguments[@"projectId"];
        if (projectId) {
            [self.moduleManager exitVideoEdit:projectId];
        }
        completion(nil, nil);
    } else if ([methodName isEqualToString:@"FixtureMethod"]) {
        completion(nil, nil);
    } else if([methodName isEqualToString:SaveDraftMethod]) {
        NSString* infoString = arguments[@"draftInfo"];
        if ([self.moduleManager saveCurrentDraftWithDraftInfo:infoString]) {
            completion(nil, nil);
        } else {
            completion(nil, [NSError errorWithDomain:@"" code:-1 userInfo:@{NSLocalizedDescriptionKey:@"Save draft error"}]);
        }
    } else if([methodName isEqualToString:CompileVideoMethod]) {
        completion(nil, nil);
    }
}

- (void)publishWithProjectId:(NSString *)projectId coverImagePath:(NSString *)coverImagePath hasDraft:(BOOL)hasDraft videoPath:(NSString *)videoPath description:(NSString *)description videoEdit:(UINavigationController *)videoEditNavigationController {
    if (videoEditNavigationController.presentingViewController.presentingViewController) {
        UIViewController* presentingVc = [NvSPUtils keyWindow].rootViewController;
        [presentingVc dismissViewControllerAnimated:YES completion:^{
            [self sendEventWithName:VideoEditMethodChannel body:@{@"method":VideoEditResultEvent}];
        }];
    } else {
        [videoEditNavigationController dismissViewControllerAnimated:YES completion:^{
            [self sendEventWithName:VideoEditMethodChannel body:@{@"method":VideoEditResultEvent}];
        }];
    }
}

- (void)didCompileFloatProgress:(float)progress {
}

@end
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
        write(plugin / "react-native-nvshortvideo.podspec", "Pod::Spec.new do |s|\n  s.name = 'react-native-nvshortvideo'\nend\n")
    if include_demo_license:
        write(
            root / "react_native" / "react-native-nvshortvideo-example" / "android" / "app" / "src" / "main" / "assets" / "meishesdk.lic",
            "official-demo-license-fixture\n",
        )
    return plugin

def validate_react_native_complete(work: Path) -> None:
    target = work / "rn_target"
    source = work / "rn_source_complete"
    create_react_native_target(target)
    plugin = create_react_native_plugin(source, complete_ios=True)
    identity_args = ["--package-name", "com.meishe.duanshipindemo"]
    output = run_integration(target, "react-native", source, identity_args)
    assert_contains(
        output,
        [
            "Skill: `meishe-react-native-duanshipin-docking`",
            "React Native plugin: the selected official `react-native-nvshortvideo` package is used",
            "React Native Android native engine libraries are complete",
            "Status: `passed`",
            IOS_VALIDATION_MARKER,
            "React Native iOS readiness passed for static quick checks.",
            "React Native: self-contained SDK check passed",
            "Merged React Native Android 13 media permissions",
            "Enabled AndroidX/Jetifier for React Native ShortVideo",
            "Added React Native app/libs AAR dependency",
            "Third-Party SDK Warnings",
            "User-Specific Configuration",
            "src/meisheShortVideoDocking.ts",
            "React Native Android package: `com.meishe.duanshipindemo`",
            "React Native iOS Bundle Identifier: `com.meishe.duanshipindemo`",
            "React Native iOS official-Demo compatibility",
            "meishe_react_native_ios_self_check.md",
            "Dependency Installation",
            "Status: `execution mode choice required`",
            "用户执行（推荐）",
            "自动执行：Agent 执行已列出的任务内操作",
            "额外消耗 Token 和时间",
            "可见回复要求",
            "折叠的“处理中”区域",
            "真机要求：美摄短视频 Demo 必须运行在已连接的真实设备上",
            "React Native JavaScript packages",
            "Command/method: `npm install`",
            "React Native Android Gradle dependencies and Debug build",
            "Generated React Native dual-platform run guide in README",
            "RN Android Demo License auto-placement matched",
            "Configuration Handoff",
            "React Native 功能配置",
            "完整重新加载 JavaScript",
            "不能只依赖 Fast Refresh",
            "React Native Android 身份、License 与原生资源",
            "React Native iOS 身份、签名、License 与原生资源",
        ],
        "React Native complete dry-run",
    )
    if sys.platform == "darwin":
        assert_contains(
            output,
            ["React Native iOS CocoaPods", "Command/method: `pod install`"],
            "React Native iOS dependency handoff",
        )
        if not (
            output.index("React Native JavaScript packages")
            < output.index("React Native iOS CocoaPods")
            < output.index("React Native Android Gradle dependencies and Debug build")
        ):
            fail("React Native dual-platform dependency steps must be JS, iOS, then Android")
    elif output.index("React Native JavaScript packages") >= output.index(
        "React Native Android Gradle dependencies and Debug build"
    ):
        fail("React Native JavaScript dependencies must precede the Android build step")
    run_integration_apply(target, "react-native", source, identity_args)

    wrapper = read(target / "src" / "meisheShortVideoDocking.ts")
    feature_config = read(target / "src" / "meisheFeatureConfig.ts")
    demo = read(target / "src" / "MeisheShortVideoDemo.tsx")
    publish = read(target / "src" / "MeisheShortVideoPublish.tsx")
    app = read(target / "App.tsx")
    podfile = read(target / "ios" / "Podfile")
    eslint_ignore = read(target / ".eslintignore")
    jest_config = read(target / "jest.config.js")
    jest_setup = read(target / "jest.setup.js")
    jest_feature_test = read(target / "__tests__" / "MeisheFeatureConfig-test.ts")
    readme = read(target / "README.md")
    report = read(target / "meishe_docking_report.md")
    ios_self_check = read(target / "meishe_react_native_ios_self_check.md")
    server_handoff = read(target / "meishe_server_config_handoff.md")
    configuration_handoff = read(target / "meishe_configuration_handoff.md")
    handoff_rows = {
        line.split(" | ", 1)[0].lstrip("| ").strip(): line
        for line in configuration_handoff.splitlines()
        if line.startswith("| React Native ")
    }
    expected_platforms = {
        "React Native 功能配置": "Android、iOS",
        "React Native 服务器配置": "Android、iOS",
        "React Native Android 身份、License 与原生资源": "Android",
        "React Native iOS 身份、签名、License 与原生资源": "iOS",
    }
    for label, platform in expected_platforms.items():
        row = handoff_rows.get(label, "")
        if f" | {platform} | " not in row:
            fail(f"React Native configuration handoff platform mismatch for {label}: {row}")
    android_manifest = read(target / "android" / "app" / "src" / "main" / "AndroidManifest.xml")
    android_app_gradle = read(target / "android" / "app" / "build.gradle")
    android_root_gradle = read(target / "android" / "build.gradle")
    android_activity = read(target / "android" / "app" / "src" / "main" / "java" / "com" / "meishe" / "duanshipindemo" / "MainActivity.kt")
    bridge = read(
        target
        / "vendor"
        / "meishe"
        / "react-native-nvshortvideo"
        / "ios"
        / "Classes"
        / "VideoEditPlugin.m"
    )
    swift_bridge = read(target / "ios" / "RnFixture" / "NvDraftSnapshotBridge.swift")
    xcode_project = read(target / "ios" / "RnFixture.xcodeproj" / "project.pbxproj")
    android_bridge = read(
        target
        / "vendor"
        / "meishe"
        / "react-native-nvshortvideo"
        / "android"
        / "src"
        / "main"
        / "java"
        / "com"
        / "meishe"
        / "nvshortvideo"
        / "VideoEditPlugin.java"
    )
    with (target / "ios" / "RnFixture" / "Info.plist").open("rb") as fh:
        info_plist = plistlib.load(fh)
    assert_contains(
        publish,
        [
            "KeyboardAvoidingView",
            "TouchableWithoutFeedback onPress={Keyboard.dismiss}",
            "behavior={Platform.OS === 'ios' ? 'padding' : undefined}",
            "keyboardDismissMode={Platform.OS === 'ios' ? 'interactive' : 'on-drag'}",
            'keyboardShouldPersistTaps="handled"',
            "</ScrollView>\n          <View style={styles.actions}>",
            "borderTopWidth: StyleSheet.hairlineWidth",
        ],
        "React Native iOS publish keyboard handling and fixed actions",
    )
    assert_contains(
        wrapper,
        [
            "DeviceEventEmitter",
            "NativeEventEmitter",
            "nativeVideoEditModule.sendMessageToNative",
            "method: 'ConfigServerInfo'",
            "return callFirst(['configServerInfo'], config)",
            "VideoEditMethodChannel",
            "VideoEditResultEvent",
            "VideoEditCallbackMethodChannel",
            "DidCompileProgressMethod",
            "DidCompileCompletedMethod",
            "DidCoverImageChangedMethod",
            "subscribeToPublish(handler",
            "export function createMeisheVideoConfig(): NvVideoConfig",
            "import { applyMeisheFeatureConfig } from './meisheFeatureConfig'",
            "return applyMeisheFeatureConfig(config);",
            "assetAutoCutUrl: 'https://creative.meishesdk.com/api/app',",
            "compactServerConfig",
            "value !== undefined && value !== null && value !== ''",
        ],
        "React Native generated publish subscription and AutoCut config",
    )
    assert_not_contains(
        wrapper,
        [
            "void callFirst(['setVideoEditEventHandler'], (event",
            "function isPublishEvent",
            "<YOUR_MEISHE_CLIENT_ID>",
            "<YOUR_MEISHE_CLIENT_SECRET>",
            "<YOUR_MEISHE_ASSEMBLY_ID>",
        ],
        "React Native direct Android/iOS publish subscription",
    )
    assert_contains(
        feature_config,
        [
            "React Native 专属配置",
            "config.albumConfig.useAutoCut = true;",
            "NvCaptureMenuItem.speed",
            "NvCaptureMenuItem.matting",
            "NvCaptureBottomMenuItem.template",
            "NvEditMenuItem.text",
            "删除 text 会删除文字入口及其下级功能",
            "validateMeisheFeatureConfig(config)",
            "defaultBottomMenuSelectItem must exist",
            "editConfig.maxVolume must be greater than 0 and no greater than 8",
            "meishe_feature_watermark.png",
            "NvCompileConfig creates empty watermark objects by default",
            "no image means the feature is disabled",
            "width and height must be greater than 0",
            "offsets must be non-negative",
            "position is required",
        ],
        "React Native user-editable feature configuration",
    )
    assert_not_contains(
        feature_config,
        ["must reference a real watermark image"],
        "React Native SDK-default empty watermark compatibility",
    )
    assert_contains(
        demo,
        [
            "MeisheShortVideoDocking.subscribeToPublish",
            "publishSubscription.remove()",
            "setScreen('publish')",
            "useMemo(() => createMeisheVideoConfig(), [])",
        ],
        "React Native generated publish flow",
    )
    assert_not_contains(
        demo,
        [
            "setVideoEditEventHandler",
            "isPublishEvent",
            "void prepareMaterials()",
            "void task.then",
            "onPress={() => void",
        ],
        "React Native generated publish flow",
    )
    assert_contains(
        app,
        [
            "import { MeisheShortVideoDemo } from './src/MeisheShortVideoDemo';",
            "return <MeisheShortVideoDemo />;",
        ],
        "React Native 0.78 default app replacement",
    )
    assert_not_contains(
        app,
        ["react-native/Libraries/NewAppScreen"],
        "React Native 0.78 default app replacement",
    )
    assert_contains(
        demo,
        [
            "InteractionManager.runAfterInteractions",
            "const materialReady = useRef<boolean>(false)",
            "if (state === 'active' && !materialReady.current)",
            "if (materialReady.current)",
            "const completed = await MeisheShortVideoDocking.downloadPrefabricatedMaterial()",
            "if (completed !== true)",
            "function observeFeatureMaterialRefresh(task: Promise<unknown>)",
            "refreshMaterials && Platform.OS === 'ios'",
            "observeFeatureMaterialRefresh(MeisheShortVideoDocking.downloadPrefabricatedMaterial())",
            "startVideoCapture(videoConfig), true",
            "materialReady.current = true",
            "label=\"草稿\" onPress={() => setScreen('drafts')}",
        ],
        "React Native single-flight deferred material preparation",
    )
    assert_not_contains(
        demo,
        [
            "async function runFeature(action: () => Promise<unknown> | unknown) {\n    void prepareMaterials();",
            "label=\"草稿\" onPress={() => { void prepareMaterials();",
            "await MeisheShortVideoDocking.downloadPrefabricatedMaterial();\n        materialReady.current = true",
        ],
        "React Native feature interaction material-preparation isolation",
    )
    run_feature_start = demo.index("async function runFeature(")
    run_feature = demo[
        run_feature_start : demo.index("\n\n  if (screen === 'publish')", run_feature_start)
    ]
    assert_contains(
        run_feature,
        [
            "if (refreshMaterials && Platform.OS === 'ios')",
            "await MeisheShortVideoDocking.configureServer();",
            "observeFeatureMaterialRefresh(MeisheShortVideoDocking.downloadPrefabricatedMaterial())",
            "await action();",
        ],
        "React Native iOS runFeature direct material refresh",
    )
    assert_not_contains(
        run_feature,
        ["prepareMaterials()", "preparePromise.current"],
        "React Native iOS entry refresh isolation from home single-flight state",
    )
    react_native_entries = {
        "capture": demo[demo.index('label="拍摄"') : demo.index('label="合拍"')],
        "dual capture": demo[demo.index('label="合拍"') : demo.index('label="编辑"')],
        "edit": demo[demo.index('label="编辑"') : demo.index('label="草稿"')],
    }
    for label, block in react_native_entries.items():
        assert_contains(
            block,
            ["runFeature(", ", true)"],
            f"React Native iOS {label} entry material refresh",
        )
    if has_xcode_26():
        assert_contains(
            output + podfile,
            [
                "Verified compatibility patch matched: React Native `0.78.0` with Xcode `26.",
                "fmt 11.0.2's consteval parser is rejected by the Xcode 26 compiler.",
                "FMT_USE_CONSTEVAL=0",
                "post_integrate do |installer|",
                "#if !defined(FMT_USE_CONSTEVAL)",
            ],
            "React Native Xcode 26 fmt Podfile compatibility",
        )
    else:
        assert_contains(
            output,
            ["React Native 0.78.x detected, but Xcode is unavailable"],
            "React Native unavailable-Xcode compatibility boundary",
        )
        assert_not_contains(
            podfile,
            ["FMT_USE_CONSTEVAL=0", "post_integrate do |installer|"],
            "React Native unavailable-Xcode patch guard",
        )
    assert_contains(
        eslint_ignore,
        ["vendor/meishe/**", "ios/Pods/**", "android/.gradle/**", "android/app/build/**"],
        "React Native third-party lint isolation",
    )
    assert_contains(
        jest_config,
        ["setupFilesAfterEnv: ['<rootDir>/jest.setup.js']", "<rootDir>/.meishe_docking_backup/"],
        "React Native Jest isolation",
    )
    assert_contains(
        jest_setup,
        [
            "/* eslint-env jest */",
            "const success = () => jest.fn",
            "downloadPrefabricatedMaterial: success()",
            "this.albumConfig = { useAutoCut: false, maxSelectCount: 50 };",
            "this.templateConfig = { useAutoCut: false, maxSelectCount: 50 };",
            "this.captureConfig = { captureBottomMenuItems: [], captureMenuItems: [], dualMenuItems: [] };",
            "this.editConfig = { editMenuItems: [], maxVolume: 4 };",
            "watermarkConfig: { watermark: null, width: 0, height: 0, offsetX: 0, offsetY: 0, position: 0 }",
            "coverWatermarkConfig: { watermark: null, width: 0, height: 0, offsetX: 0, offsetY: 0, position: 0 }",
            "NvCaptureBottomMenuItem: captureBottomMenuItem",
            "NvCaptureMenuItem: captureMenuItem",
            "NvDualConfig: class NvDualConfig",
            "NvVideoPreviewResolution",
            "template: 'capture_bottom_menu_template'",
            "NvVideoCompileEvent",
        ],
        "React Native native-module Jest mock",
    )
    assert_contains(
        jest_feature_test,
        [
            "applyMeisheFeatureConfig(new NvVideoConfig())",
            "typeof config.albumConfig.useAutoCut",
            "config.editConfig.maxVolume).toBeLessThanOrEqual(8)",
            "validateMeisheFeatureConfig(config)).not.toThrow()",
            "config.compileConfig.watermarkConfig.watermark = null",
            "config.compileConfig.watermarkConfig.watermark = { imageName: 'meishe_feature_watermark' }",
            "config.compileConfig.watermarkConfig.width = 0",
            "toThrow('width and height')",
            "config.editConfig.maxVolume = 0",
            "toThrow('maxVolume')",
        ],
        "React Native generated feature configuration Jest test",
    )
    assert_contains(
        readme,
        [
            "User-maintained introduction.",
            "BEGIN MEISHE_REACT_NATIVE_RUN_GUIDE",
            "美摄短视频 Demo 运行",
            f"项目根目录：`{target.resolve()}`",
            "npm install",
            "npm start",
            "npm run android -- --deviceId <ANDROID_DEVICE_ID>",
            "RnFixture.xcworkspace",
            "npm run ios -- --udid <IOS_DEVICE_UDID>",
            "Android Emulator、iOS Simulator",
            "不能用于运行或验收",
            "Signing & Capabilities",
            "com.meishe.duanshipindemo",
            "END MEISHE_REACT_NATIVE_RUN_GUIDE",
            "Configuration Handoff",
            str((target / "src" / "meisheFeatureConfig.ts").resolve()),
            "在 Metro 终端按 r",
            "不能只依赖 Fast Refresh",
        ],
        "React Native generated dual-platform README run guide",
    )
    assert_contains(
        configuration_handoff,
        [
            "### 配置修改与生效速览",
            "| 配置项 | 修改入口 | 适用平台 | 最快生效方式 | 重新构建条件 | 无需执行 |",
            "| Android、iOS |",
            str((target / "src" / "meisheFeatureConfig.ts").resolve()),
            str((target / "src" / "meisheShortVideoDocking.ts").resolve()),
            "npm start",
            "npm run android -- --deviceId <ANDROID_DEVICE_ID>",
            "npm run ios -- --udid <IOS_DEVICE_UDID>",
            "真机要求：美摄短视频 Demo 必须运行在已连接的真实设备上",
            "只有 package.json 或锁文件变化时才重新安装依赖",
            "Fast Refresh",
            "Signing & Capabilities",
        ],
        "React Native command-level configuration handoff",
    )
    assert_contains(
        android_manifest,
        [
            "android.permission.READ_MEDIA_IMAGES",
            "android.permission.READ_MEDIA_VIDEO",
            "android.permission.READ_MEDIA_AUDIO",
        ],
        "React Native Android media permissions",
    )
    assert_contains(
        android_app_gradle,
        [
            'implementation fileTree(dir: "libs", include: ["*.jar", "*.aar"])',
            'namespace "com.meishe.duanshipindemo"',
            'applicationId "com.meishe.duanshipindemo"',
        ],
        "React Native Android app AAR dependency",
    )
    if android_root_gradle.index("google()") > android_root_gradle.index("maven.aliyun.com/repository/public"):
        fail("React Native Android repositories must resolve standard Android/RN artifacts before legacy mirrors")
    assert_contains(
        android_activity,
        ["package com.meishe.duanshipindemo\n\nimport android.app.Activity"],
        "React Native Android source package",
    )
    if not (target / "android" / "app" / "src" / "main" / "assets" / "meishesdk.lic").is_file():
        fail("React Native official Demo fixture must package the License from Android app assets")
    for watermark in (
        target / "src" / "assets" / "meishe_feature_watermark.png",
        target / "android" / "app" / "src" / "main" / "res" / "drawable-nodpi" / "meishe_feature_watermark.png",
        target / "ios" / "MeisheFeatureAssets.xcassets" / "meishe_feature_watermark.imageset" / "meishe_feature_watermark.png",
        target / "ios" / "MeisheFeatureAssets.xcassets" / "meishe_feature_watermark.imageset" / "Contents.json",
    ):
        if not watermark.is_file():
            fail(f"React Native generated watermark asset missing: {watermark}")
    if not info_plist.get("NSLocationWhenInUseUsageDescription"):
        fail("React Native generated Info.plist must contain a non-empty location permission description")
    if info_plist.get("NSAppTransportSecurity", {}).get("NSAllowsArbitraryLoads") is not True:
        fail("React Native official-Demo iOS fixture must match the verified official ATS compatibility setting")
    assert_contains(
        ios_self_check,
        [
            "拍摄页的美颜、滤镜、贴纸或音乐在线列表为空",
            "ConfigServerInfo",
            "downloadPrefabricatedMaterial()",
            "com.meishe.duanshipindemo",
            "`runFeature` 直接非阻塞触发素材刷新",
            "不调用受首页单飞状态保护的 `prepareMaterials()`",
            "进入拍摄，逐项检查美颜、滤镜、贴纸和音乐在线列表",
            "分别从编辑素材选择、模板页和拍摄模板菜单进入一键成片",
            "一键成片进入作品发布后看不到“保存草稿”",
            "NvDraftSnapshotBridge",
            "运行时沙箱",
            "VideoEditCallbackMethodChannel",
            "导出视频",
        ],
        "React Native iOS generated material-request self-check",
    )
    assert_contains(
        server_handoff,
        [
            "https://creative.meishesdk.com/api/app",
            "Android bridge 直接消费基础地址",
            "iOS bridge 按官方契约补齐端点",
            "标准编辑页",
            "导出视频",
        ],
        "React Native AutoCut server handoff",
    )
    assert_contains(
        bridge,
        [
            "bindModuleManagerDelegates",
            "[self bindModuleManagerDelegates];",
            "pendingPublishProjectId",
            "pendingDraftProjectId",
            "pendingDraftStaged",
            "pendingDraftCommitted",
            "self.pendingPublishProjectId = projectId;",
            "self.pendingDraftProjectId = self.moduleManager.projectId;",
            "stageProjectWithProjectId:self.pendingDraftProjectId",
            "NvShortVideoPendingDraftDefaultsKey",
            "deleteRenderedMediaWithProjectId",
            "saveCurrentDraftWithDraftInfo:infoString",
            "projectInfoForProject:draftProjectId",
            "project was not added to the draft list",
            "[self sendEventWithName:VideoEditMethodChannel body:eventBody];",
        ],
        "React Native patched iOS AutoCut draft and publish bridge",
    )
    send_position = bridge.index("[self sendEventWithName:VideoEditMethodChannel body:eventBody];")
    dismiss_position = bridge.index("dismissViewControllerAnimated:YES completion:nil")
    if send_position >= dismiss_position:
        fail("React Native patched iOS bridge must emit the publish event before dismissing the editor")
    stage_position = bridge.index("stageProjectWithProjectId:self.pendingDraftProjectId")
    event_position = bridge.index("[self sendEventWithName:VideoEditMethodChannel body:eventBody];")
    if stage_position >= event_position:
        fail("React Native iOS AutoCut draft must be staged before publishing to JS")
    assert_not_contains(
        bridge,
        ["storeCurrentProjectWithProjectId:projectId"],
        "React Native iOS temporary callback project ID isolation",
    )
    assert_contains(
        swift_bridge,
        [
            "NvAutoCutDraftMedia",
            "NvTimelineDataManager.sharedInstance()",
            "newProject(",
            "localFilePaths: [durableVideoURL.path]",
            "let draftProjectId = model.projectId",
            "mediaByProject[draftProjectId]",
            "deleteRenderedMedia(projectId: String)",
        ],
        "React Native iOS AutoCut standard draft helper",
    )
    assert_contains(
        xcode_project,
        ["NvDraftSnapshotBridge.swift", "NvDraftSnapshotBridge.swift in Sources"],
        "React Native iOS draft helper target membership",
    )
    assert_contains(
        android_bridge,
        [
            "private void emitPublishResultOnce(",
            'emitPublishResultOnce(needSaveDraft, videoPath, "");',
            "invokeMethod(VIDEO_EDIT_CHANNEL, VIDEO_EDIT_RESULT_EVENT, maps);",
            "AppManager.getInstance().finishAllEditActivity();",
        ],
        "React Native Android AutoCut publish fallback",
    )
    if android_bridge.index("invokeMethod(VIDEO_EDIT_CHANNEL, VIDEO_EDIT_RESULT_EVENT, maps);") >= android_bridge.index(
        "AppManager.getInstance().finishAllEditActivity();"
    ):
        fail("React Native Android AutoCut publish event must be emitted before editor shutdown")
    assert_contains(
        publish,
        [
            "MeisheShortVideoDocking.saveDraft(draftInfo)",
            "MeisheShortVideoDocking.compileCurrentTimeline({})",
            "rawValue >= 0 && rawValue <= 1 ? rawValue * 100 : rawValue",
        ],
        "React Native AutoCut publish actions",
    )

    user_feature_marker = "// USER_FEATURE_CONFIG_MUST_BE_PRESERVED"
    write(
        target / "src" / "meisheFeatureConfig.ts",
        feature_config + f"\n{user_feature_marker}\n",
    )
    run_integration_apply(target, "react-native", source, identity_args)
    assert_contains(
        read(target / "src" / "meisheFeatureConfig.ts"),
        [user_feature_marker],
        "React Native user feature configuration preservation",
    )
    repeat_output = read(target / "meishe_docking_report.md")
    assert_contains(
        repeat_output,
        ["React Native app entry already uses the generated Meishe demo component."],
        "React Native idempotent app entry report",
    )
    assert_not_contains(
        repeat_output,
        ["and add it to your app navigation"],
        "React Native idempotent app entry report",
    )
    repeated_readme = read(target / "README.md")
    if repeated_readme.count("BEGIN MEISHE_REACT_NATIVE_RUN_GUIDE") != 1:
        fail("React Native repeated integration must keep exactly one managed README run guide")
    assert_contains(
        repeated_readme,
        ["User-maintained introduction.", "END MEISHE_REACT_NATIVE_RUN_GUIDE"],
        "React Native idempotent README run guide",
    )

def validate_react_native_missing_ios(work: Path) -> None:
    target = work / "rn_target_missing"
    source = work / "rn_source_missing"
    create_react_native_target(target)
    plugin = create_react_native_plugin(source, complete_ios=False)
    output = run_integration(target, "react-native", plugin)
    assert_contains(
        output,
        [
            "Status: `warning`",
            "React Native iOS readiness failed",
            "Provide the complete official React Native package from Meishe Developer Center (`React Native工程`)",
            "do not substitute the native iOS `Pods-NvShortVideoEdit` package",
        ],
        "React Native missing-iOS dry-run",
    )

def validate_react_native_missing_android_native_libraries(work: Path) -> None:
    target = work / "rn_target_missing_android_native"
    source = work / "rn_source_missing_android_native"
    create_react_native_target(target)
    plugin = create_react_native_plugin(
        source,
        complete_ios=True,
        complete_android_native=False,
    )
    output = run_integration_failure(target, "react-native", plugin)
    assert_contains(
        output,
        [
            "official React Native ShortVideo package is incomplete for Android runtime",
            "libNvStreamingSdkCore.so",
            "libNvMSAICutter.so",
            "do not ask the user for a native Demo package",
            "corrected complete `React Native工程` package",
        ],
        "React Native missing Android native libraries",
    )


def validate_react_native_missing_android_beauty_resources(work: Path) -> None:
    target = work / "rn_target_missing_android_beauty"
    source = work / "rn_source_missing_android_beauty"
    create_react_native_target(target, ios=False)
    plugin = create_react_native_plugin(
        source,
        complete_ios=True,
        include_android_beauty_shape_resources=False,
    )
    output = run_integration(target, "react-native", plugin)
    assert_contains(
        output,
        [
            "does not contain optional fixed beauty-shape resources",
            "Shape/MicroShape beauty categories may be empty or incomplete",
            "not an online-material request failure",
        ],
        "React Native Android optional beauty resource warning",
    )


def validate_react_native_android_only(work: Path) -> None:
    target = work / "rn_target_android_only"
    source = work / "rn_source_android_only"
    create_react_native_target(target, ios=False)
    plugin = create_react_native_plugin(source, complete_ios=True)
    output = run_integration(target, "react-native", plugin)
    assert_contains(
        output,
        [
            "React Native Android native engine libraries are complete",
            "Merged React Native Android 13 media permissions",
            "React Native JavaScript packages",
            "React Native Android Gradle dependencies and Debug build",
            "Command/method: `./gradlew :app:assembleDebug`",
        ],
        "React Native Android-only route",
    )
    assert_not_contains(
        output,
        ["React Native iOS", "iOS Quick Verify", "iOS signing", "pod install", IOS_VALIDATION_MARKER],
        "React Native Android-only route isolation",
    )
    license_path = work / "rn_android_only_license" / "meishesdk.lic"
    write(license_path, "fixture-license\n")
    run_integration_apply(
        target,
        "react-native",
        plugin,
        ["--license-path", str(license_path)],
    )
    android_readme = read(target / "README.md")
    android_handoff = read(target / "meishe_configuration_handoff.md")
    assert_contains(
        android_readme,
        ["### Android", "npm run android", "Android Studio"],
        "React Native Android-only README",
    )
    assert_not_contains(
        android_readme,
        ["### iOS", ".xcworkspace", "npm run ios"],
        "React Native Android-only README isolation",
    )
    assert_contains(
        android_handoff,
        ["npm start", "npm run android", "React Native Android 身份、License 与原生资源"],
        "React Native Android-only configuration handoff",
    )
    assert_not_contains(
        android_handoff,
        ["npm run ios", "<IOS_DEVICE_ID>", ".xcworkspace", "React Native iOS 身份"],
        "React Native Android-only configuration handoff isolation",
    )
    local_plugin = target / "vendor" / "meishe" / "react-native-nvshortvideo"
    if not (target / "android" / "app" / "src" / "main" / "assets" / "meishesdk.lic").is_file():
        fail("React Native Android-only route must place the License in final app assets")
    if (local_plugin / "android" / "src" / "main" / "assets" / "meishesdk.lic").exists():
        fail("React Native Android-only route must not rely on the library plugin asset for App License packaging")
    if (local_plugin / "ios" / "Assets" / "meishesdk.lic").exists():
        fail("React Native Android-only route must not place an iOS license")
    assert_contains(
        read(target / "src" / "meisheFeatureConfig.ts"),
        ["config.albumConfig.useAutoCut = true;", "NvCaptureBottomMenuItem.template", "NvEditMenuItem.text"],
        "React Native Android-only feature config",
    )
    assert_contains(
        read(local_plugin / "android" / "src" / "main" / "java" / "com" / "meishe" / "nvshortvideo" / "VideoEditPlugin.java"),
        ["private void emitPublishResultOnce(", 'emitPublishResultOnce(needSaveDraft, videoPath, "");'],
        "React Native Android-only AutoCut publish fallback",
    )


def validate_react_native_custom_identity_rejects_demo_license(work: Path) -> None:
    target = work / "rn_target_custom_identity_license"
    source = work / "rn_source_custom_identity_license"
    create_react_native_target(target, ios=False)
    create_react_native_plugin(source, complete_ios=True, include_demo_license=True)
    output = run_integration(target, "react-native", source)
    assert_contains(
        output,
        [
            "RN Android applicationId `rnfixture` is not the official Demo identity",
            "did not reuse an official Demo License",
            "--license-path",
        ],
        "React Native custom identity Demo License isolation",
    )
    run_integration_apply(target, "react-native", source)
    if (target / "android" / "app" / "src" / "main" / "assets" / "meishesdk.lic").exists():
        fail("React Native custom applicationId must not reuse the official Demo License")


def validate_react_native_ios_only(work: Path) -> None:
    target = work / "rn_target_ios_only"
    source = work / "rn_source_ios_only"
    create_react_native_target(target, android=False)
    plugin = create_react_native_plugin(source, complete_ios=True, include_android=False)
    output = run_integration(target, "react-native", plugin)
    assert_contains(
        output,
        ["React Native iOS readiness passed for static quick checks.", IOS_VALIDATION_MARKER],
        "React Native iOS-only route",
    )
    assert_not_contains(
        output,
        [
            "React Native Android",
            "AndroidX/Jetifier",
            "Android 13 media permissions",
            "Gradle dependencies and Debug build",
        ],
        "React Native iOS-only route isolation",
    )
    run_integration_apply(target, "react-native", plugin)
    ios_readme = read(target / "README.md")
    ios_handoff = read(target / "meishe_configuration_handoff.md")
    assert_contains(
        ios_readme,
        ["### iOS", "RnFixture.xcworkspace", "npm run ios -- --udid <IOS_DEVICE_UDID>"],
        "React Native iOS-only README",
    )
    assert_not_contains(
        ios_readme,
        ["### Android", "npm run android", "Android Studio"],
        "React Native iOS-only README isolation",
    )
    assert_contains(
        ios_handoff,
        ["npm start", "npm run ios -- --udid <IOS_DEVICE_UDID>", "RnFixture.xcworkspace", "React Native iOS 身份、签名、License 与原生资源"],
        "React Native iOS-only configuration handoff",
    )
    assert_not_contains(
        ios_handoff,
        ["npm run android", "<ANDROID_DEVICE_ID>", "React Native Android 身份"],
        "React Native iOS-only configuration handoff isolation",
    )
    assert_contains(
        read(target / "src" / "meisheFeatureConfig.ts"),
        [
            "config.albumConfig.useAutoCut = true;",
            "config.templateConfig.useAutoCut = true;",
            "NvCaptureBottomMenuItem.template",
            "NvCaptureMenuItem.matting",
        ],
        "React Native iOS-only feature config",
    )
    assert_contains(
        read(target / "src" / "meisheShortVideoDocking.ts"),
        ["assetAutoCutUrl: 'https://creative.meishesdk.com/api/app',", "applyMeisheFeatureConfig"],
        "React Native iOS-only wrapper",
    )
    with (target / "ios" / "RnFixture" / "Info.plist").open("rb") as fh:
        info_plist = plistlib.load(fh)
    if info_plist.get("NSAppTransportSecurity", {}).get("NSAllowsArbitraryLoads") is True:
        fail("React Native customer-identity iOS fixture must not enable global NSAllowsArbitraryLoads")
    assert_contains(
        read(target / "meishe_react_native_ios_self_check.md"),
        ["React Native iOS 素材请求自检", "客户或正式工程必须核对全部接口/CDN"],
        "React Native iOS-only self-check handoff",
    )


def validate_react_native_conflicting_lockfiles(work: Path) -> None:
    target = work / "rn_target_conflicting_lockfiles"
    source = work / "rn_source_conflicting_lockfiles"
    create_react_native_target(target, ios=False)
    package_json = json.loads(read(target / "package.json"))
    package_json.pop("packageManager", None)
    write_json(target / "package.json", package_json)
    write(target / "yarn.lock", "# fixture\n")
    write_json(target / "package-lock.json", {"name": "rn-fixture", "lockfileVersion": 3})
    plugin = create_react_native_plugin(source, complete_ios=True)
    original_app = read(target / "App.tsx")
    output = run_integration_failure(target, "react-native", plugin)
    assert_contains(
        output,
        [
            "package manager is ambiguous",
            "yarn.lock",
            "package-lock.json",
            "package.json#packageManager",
        ],
        "React Native conflicting package managers",
    )
    if (target / "vendor" / "meishe").exists() or read(target / "App.tsx") != original_app:
        fail("React Native package-manager ambiguity must fail before target writes")


def validate_react_native_unverified_android_publish_shape(work: Path) -> None:
    target = work / "rn_target_unverified_publish"
    source = work / "rn_source_unverified_publish"
    create_react_native_target(target, ios=False)
    plugin = create_react_native_plugin(source, complete_ios=True)
    bridge = plugin / "android" / "src" / "main" / "java" / "com" / "meishe" / "nvshortvideo" / "VideoEditPlugin.java"
    text = read(bridge).replace(
        "public void onCoverSaveFailed() {\n                    }",
        "public void onCoverSaveFailed() {\n                        logUnknownVersion();\n                    }",
        1,
    )
    write(bridge, text)
    output = run_integration(target, "react-native", plugin)
    assert_contains(
        output,
        [
            "does not match the verified ShortVideo 2.0.2.1 source shape",
            "No vendor patch was applied",
        ],
        "React Native unverified AutoCut publish bridge warning",
    )
    assert_not_contains(
        output,
        ["Patched verified React Native Android AutoCut publish fallback"],
        "React Native unverified AutoCut publish bridge guard",
    )
    run_integration_apply(target, "react-native", plugin)
    local_bridge = read(
        target
        / "vendor"
        / "meishe"
        / "react-native-nvshortvideo"
        / "android"
        / "src"
        / "main"
        / "java"
        / "com"
        / "meishe"
        / "nvshortvideo"
        / "VideoEditPlugin.java"
    )
    assert_contains(local_bridge, ["logUnknownVersion();"], "React Native unverified bridge retained")
    assert_not_contains(local_bridge, ["private void emitPublishResultOnce("], "React Native unverified bridge not patched")


def validate_react_native_unverified_ios_autocut_draft_shape(work: Path) -> None:
    target = work / "rn_target_unverified_ios_draft"
    source = work / "rn_source_unverified_ios_draft"
    create_react_native_target(target, android=False)
    plugin = create_react_native_plugin(source, complete_ios=True, include_android=False)
    bridge = plugin / "ios" / "Classes" / "VideoEditPlugin.m"
    text = read(bridge).replace(
        "NvHttpRequestDelegate *requestDelegate;",
        "NvHttpRequestDelegate *requestDelegateV2;",
        1,
    )
    write(bridge, text)
    output = run_integration(target, "react-native", plugin)
    assert_contains(
        output,
        [
            "does not match the verified ShortVideo 2.0.2.1 AutoCut draft source shape",
            "No draft persistence patch was applied",
        ],
        "React Native unverified iOS AutoCut draft bridge warning",
    )
    assert_not_contains(
        output,
        ["Patched verified React Native iOS AutoCut draft lifecycle and publish callback ordering"],
        "React Native unverified iOS AutoCut draft bridge guard",
    )
    run_integration_apply(target, "react-native", plugin)
    local_bridge = read(
        target
        / "vendor"
        / "meishe"
        / "react-native-nvshortvideo"
        / "ios"
        / "Classes"
        / "VideoEditPlugin.m"
    )
    assert_contains(local_bridge, ["requestDelegateV2"], "React Native unverified iOS bridge retained")
    assert_not_contains(
        local_bridge,
        ["pendingPublishProjectId", "storeCurrentProjectWithProjectId", "bindModuleManagerDelegates"],
        "React Native unverified iOS bridge not partially patched",
    )


def validate_react_native_missing_targets(work: Path) -> None:
    target = work / "rn_target_no_platforms"
    source = work / "rn_source_no_platforms"
    create_react_native_target(target, android=False, ios=False)
    plugin = create_react_native_plugin(source, complete_ios=True)
    output = run_integration_failure(target, "react-native", plugin)
    assert_contains(
        output,
        ["React Native target must contain an `android/` directory, an `ios/` directory, or both."],
        "React Native missing target platforms",
    )


def validate_react_native_platform_identities(work: Path) -> None:
    target = work / "rn_target_platform_identities"
    source = work / "rn_source_platform_identities"
    create_react_native_target(target)
    project_file = target / "ios" / "RnFixture.xcodeproj" / "project.pbxproj"
    write(
        project_file,
        read(project_file).replace(
            "  objects = {",
            '  PRODUCT_BUNDLE_IDENTIFIER = "com.example.oldios";\n  objects = {',
            1,
        ),
    )
    plugin = create_react_native_plugin(source, complete_ios=True)
    identity_args = [
        "--android-package-name",
        "com.customer.rn.android",
        "--ios-bundle-identifier",
        "com.customer.rn.ios",
    ]
    run_integration_apply(target, "react-native", plugin, identity_args)
    android_gradle = read(target / "android" / "app" / "build.gradle")
    ios_project = read(project_file)
    readme = read(target / "README.md")
    report = read(target / "meishe_docking_report.md")
    assert_contains(
        android_gradle,
        ['namespace "com.customer.rn.android"', 'applicationId "com.customer.rn.android"'],
        "React Native Android-specific identity",
    )
    assert_not_contains(
        android_gradle,
        ["com.customer.rn.ios"],
        "React Native Android identity isolation",
    )
    assert_contains(
        ios_project,
        ['PRODUCT_BUNDLE_IDENTIFIER = "com.customer.rn.ios";'],
        "React Native iOS-specific identity",
    )
    assert_not_contains(
        ios_project,
        ["com.customer.rn.android"],
        "React Native iOS identity isolation",
    )
    assert_contains(
        readme,
        [
            "Android applicationId：`com.customer.rn.android`",
            "iOS Bundle Identifier：`com.customer.rn.ios`",
        ],
        "React Native separate identity handoff",
    )
    assert_contains(
        report,
        [
            "official Demo material service requires the exact Bundle Identifier",
            "`com.meishe.duanshipindemo`",
            "`--ios-bundle-identifier com.meishe.duanshipindemo`",
            "customer server, matching License, and service allowlist",
        ],
        "React Native customer iOS identity warning",
    )

    conflict_target = work / "rn_target_platform_identity_conflict"
    conflict_source = work / "rn_source_platform_identity_conflict"
    create_react_native_target(conflict_target)
    conflict_plugin = create_react_native_plugin(conflict_source, complete_ios=True)
    failure = run_integration_apply_failure(
        conflict_target,
        "react-native",
        conflict_plugin,
        [
            "--package-name",
            "com.customer.shared",
            "--android-package-name",
            "com.customer.android",
        ],
    )
    assert_contains(
        failure,
        ["Conflicting Android package name values", "--package-name", "--android-package-name"],
        "React Native identity conflict",
    )
    if (conflict_target / "vendor").exists():
        fail("React Native identity conflict must fail before files are written")


def validate_react_native_optional_toolchain(work: Path) -> None:
    target = work / "rn_target_optional_toolchain"
    create_react_native_target(target)
    script = PLATFORM_SCRIPTS["react-native"].with_name("toolchain_validate.py")
    output = run(
        [str(script), "--target-root", str(target)],
        "React Native optional toolchain skip",
    )
    assert_contains(
        output,
        ["toolchain_validate skipped", "No dependency was downloaded"],
        "React Native optional toolchain boundary",
    )


def validate_react_native_unverified_version(work: Path) -> None:
    target = work / "rn_target_unverified"
    source = work / "rn_source_unverified"
    create_react_native_target(target)
    package_data = json.loads(read(target / "package.json"))
    package_data["dependencies"]["react-native"] = "0.79.3"
    write_json(target / "package.json", package_data)
    plugin = create_react_native_plugin(source, complete_ios=True)
    output = run_integration(target, "react-native", plugin)
    assert_contains(
        output,
        [
            "Toolchain Compatibility",
            "No automatic fmt patch was applied for React Native `0.79.3`",
            "only verifies this patch for React Native 0.78.x + Xcode 26.x",
        ],
        "React Native unverified-version warning",
    )
    assert_not_contains(
        output,
        ["Patched React Native iOS Podfile for RN 0.78 fmt compatibility with Xcode 26"],
        "React Native unverified-version patch guard",
    )
