"""Native Android fixture validation."""

from __future__ import annotations

import json
import io
import zipfile
from pathlib import Path

from .shared import (
    PLATFORM_SCRIPTS,
    assert_contains,
    assert_not_contains,
    fail,
    run,
    run_failure,
    read,
    write,
)


def create_native_android_target(root: Path) -> None:
    write(root / "README.md", "# Native Android Fixture\n\nUser-maintained introduction.\n")
    write(
        root / "settings.gradle",
        """pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = 'NativeAndroidFixture'
include ':app'
""",
    )
    write(root / "gradle.properties", "android.useAndroidX=true\n")
    write(root / "gradlew", "#!/bin/sh\n")
    write(root / "gradlew.bat", "@echo off\r\n")
    write(
        root / "gradle" / "libs.versions.toml",
        """[versions]
coreKtx = "1.19.0"
lifecycleRuntimeKtx = "2.11.0"
activityCompose = "1.13.0"
composeBom = "2026.02.01"
""",
    )
    write(
        root / "app" / "build.gradle",
        """plugins { id 'com.android.application' }

android {
    namespace 'com.example.fixture'
    compileSdk {
        version = release(36) {
            minorApiLevel = 1
        }
    }
    defaultConfig {
        applicationId 'com.example.fixture'
        minSdk 24
        targetSdk 35
    }
}
""",
    )
    write(
        root / "app" / "src" / "main" / "AndroidManifest.xml",
        """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:theme="@android:style/Theme.Material.NoActionBar">
        <activity android:name=".MainActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
""",
    )
    write(
        root / "app" / "src" / "main" / "java" / "com" / "example" / "fixture" / "MainActivity.java",
        """package com.example.fixture;

public class MainActivity extends android.app.Activity {
}
""",
    )

def create_native_android_package(
    root: Path,
    *,
    include_cover_api: bool = True,
    include_beauty_shape_resources: bool = False,
) -> tuple[Path, Path]:
    aar = root / "native" / "android" / "ShortVideo" / "app" / "libs" / "NvShortVideoCore.aar"
    aar.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(aar, "w") as archive:
        archive.writestr("AndroidManifest.xml", '<manifest package="com.meishe.fixture" />')
        classes_jar = io.BytesIO()
        with zipfile.ZipFile(classes_jar, "w") as jar:
            if include_cover_api:
                jar.writestr("com/meishe/module/NvModuleManager.class", b"fixture saveCover")
                jar.writestr(
                    "com/meishe/module/NvModuleManager$OnCoverSavedCallBack.class",
                    b"fixture onCoverSaved onCoverSaveFailed",
                )
                jar.writestr("com/meishe/engine/util/PathUtils.class", b"fixture getCoverDir")
            else:
                jar.writestr("com/meishe/module/NvModuleManager.class", b"fixture unknownCoverApi")
        archive.writestr("classes.jar", classes_jar.getvalue())
        for entry in (
            "jni/arm64-v8a/libNvStreamingSdkCore.so",
            "jni/arm64-v8a/libNvMSAICutter.so",
            "jni/armeabi-v7a/libNvStreamingSdkCore.so",
            "jni/armeabi-v7a/libNvMSAICutter.so",
        ):
            archive.writestr(entry, f"fixture:{entry}".encode())
        if include_beauty_shape_resources:
            for entry in (
                "assets/beauty/shapePackage/facemesh/info.json",
                "assets/beauty/shapePackage/warp/info.json",
            ):
                archive.writestr(entry, "{}")
    license_path = root / "native" / "android" / "ShortVideo" / "app" / "src" / "main" / "assets" / "meishesdk.lic"
    write(license_path, "fixture-license\n")
    return aar, license_path

def validate_native_android_complete(work: Path) -> None:
    target = work / "native_android_target"
    source = work / "native_android_package"
    create_native_android_target(target)
    aar, license_path = create_native_android_package(source)
    command = [
        str(PLATFORM_SCRIPTS["native-android"]),
        "--target-root",
        str(target),
        "--aar-path",
        str(aar),
        "--license-path",
        str(license_path),
        "--package-name",
        "com.meishe.duanshipindemo",
        "--demo-launcher",
    ]
    output = run(
        command,
        "Native Android complete fixture",
    )
    assert_contains(output, ["Wrote report:"], "Native Android integration output")
    assert_contains(
        read(target / "app" / "build.gradle"),
        [
            'namespace "com.meishe.duanshipindemo"',
            'applicationId "com.meishe.duanshipindemo"',
            "force 'androidx.core:core:1.16.0'",
            "force 'androidx.core:core-ktx:1.16.0'",
            'abiFilters "armeabi-v7a", "arm64-v8a"',
            "useLegacyPackaging true",
        ],
        "Native Android aligned Gradle identity",
    )
    gradle_text = read(target / "app" / "build.gradle")
    assert_not_contains(
        gradle_text,
        ["androidx.core:core:1.8.0", "androidx.core:core-ktx:1.8.0", "androidx.multidex:multidex", "multiDexEnabled"],
        "Native Android modern minSdk dependency compatibility",
    )
    assert_contains(
        read(target / "gradle" / "libs.versions.toml"),
        ['coreKtx = "1.16.0"', 'lifecycleRuntimeKtx = "2.9.4"', 'activityCompose = "1.8.2"'],
        "Native Android verified Compose compatibility",
    )
    manifest = read(target / "app" / "src" / "main" / "AndroidManifest.xml")
    assert_contains(
        manifest,
        [
            ".meishe.MeisheShortVideoDemoActivity",
            "android.intent.action.MAIN",
            "android.intent.category.LAUNCHER",
            ".meishe.MeisheShortVideoPublishActivity",
            ".MeisheShortVideoApplication",
        ],
        "Native Android generated manifest",
    )
    if manifest.count("android.intent.action.MAIN") != 1:
        fail("Native Android demo launcher fixture must contain exactly one MAIN action")
    expected_files = [
        target / "app" / "libs" / "NvShortVideoCore.aar",
        target / "app" / "src" / "main" / "assets" / "meishesdk.lic",
        target / "app" / "src" / "main" / "assets" / "config" / "config_example.json",
        target / "app" / "src" / "main" / "java" / "com" / "meishe" / "duanshipindemo" / "MainActivity.java",
        target / "app" / "src" / "main" / "java" / "com" / "meishe" / "duanshipindemo" / "meishe" / "MeisheShortVideoDocking.java",
        target / "app" / "src" / "main" / "java" / "com" / "meishe" / "duanshipindemo" / "meishe" / "MeisheFeatureConfig.java",
        target / "app" / "src" / "main" / "java" / "com" / "meishe" / "duanshipindemo" / "meishe" / "MeisheShortVideoDemoActivity.java",
        target / "app" / "src" / "main" / "java" / "com" / "meishe" / "duanshipindemo" / "meishe" / "MeisheShortVideoPublishActivity.java",
    ]
    for path in expected_files:
        if not path.exists():
            fail(f"Native Android generated file missing: {path}")
    if (target / "app" / "src" / "main" / "java" / "com" / "example" / "fixture" / "MainActivity.java").exists():
        fail("Native Android old source package was not removed")
    config = read(target / "app" / "src" / "main" / "assets" / "config" / "config_example.json")
    assert_contains(
        config,
        [
            '"capture_bottom_menu_template"',
            '"useAutoCut": true',
            '"albumConfig"',
            '"templateConfig"',
        ],
        "Native Android AutoCut config",
    )
    assert_not_contains(
        config,
        ['"useAutoCut": false'],
        "Native Android removed AutoCut restriction",
    )
    config_data = json.loads(config)
    if config_data.get("compileConfig", {}).get("resolution") != 1:
        fail("Native Android generated compile resolution must default to 1 (1080p), not 2 (4K)")
    feature_config_path = (
        target
        / "app"
        / "src"
        / "main"
        / "java"
        / "com"
        / "meishe"
        / "duanshipindemo"
        / "meishe"
        / "MeisheFeatureConfig.java"
    )
    feature_config = read(feature_config_path)
    assert_contains(
        feature_config,
        [
            "原生 Android 专属配置",
            "album.setUseAutoCut(true)",
            "NvCaptureMenuItem.speed",
            "未公开 matting 枚举",
            "NvCaptureBottomMenuItem.template",
            "NvEditMenuItem.text",
            "删除 text 会删除文字入口及其下级功能",
            "setDisableTimeEffect(false)",
            "defaultBottomMenuSelectItem must exist",
            "editConfig.maxVolume must be greater than 0 and no greater than 8",
            "rejects a single-element supportedEditModes list",
        ],
        "Native Android user-editable feature configuration",
    )
    assert_contains(
        read(target / "app" / "src" / "main" / "java" / "com" / "meishe" / "duanshipindemo" / "meishe" / "MeisheShortVideoDocking.java"),
        ["MeisheFeatureConfig.apply"],
        "Native Android feature config entry",
    )
    publish = read(
        target
        / "app"
        / "src"
        / "main"
        / "java"
        / "com"
        / "meishe"
        / "duanshipindemo"
        / "meishe"
        / "MeisheShortVideoPublishActivity.java"
    )
    assert_contains(
        publish,
        [
            "saveDraft.setOnClickListener",
            "exportVideo.setOnClickListener",
            'actionButton("保存封面", false)',
            "PathUtils.getCoverDir()",
            "NvModuleManager.get().saveCover(",
            "onCoverSaveFailed()",
        ],
        "Native Android AutoCut publish actions",
    )
    report = read(target / "meishe_docking_report.md")
    server_handoff = read(target / "meishe_server_config_handoff.md")
    configuration_handoff = read(target / "meishe_configuration_handoff.md")
    readme = read(target / "README.md")
    assert_contains(
        report,
        [
            "Skill: `meishe-native-android-shortvideo-docking`",
            "Set native Android namespace/applicationId",
            "Demoted existing Android launcher activity",
            "Registered native Android demo activity as launcher",
            "self-contained SDK check passed",
            "Native Android AutoCut",
            "Dependency Installation",
            "Status: `execution mode choice required`",
            "用户执行（推荐）",
            "自动执行：Agent 执行已列出的任务内操作",
            "额外消耗 Token 和时间",
            "可见回复要求",
            "折叠的“处理中”区域",
            "真机要求：美摄短视频 Demo 必须运行在真实 Android 设备上",
            "Native Android Gradle dependencies and Debug build",
            "Command/method: `./gradlew :app:assembleDebug`",
            "Native Android compileSdk: `36.1`",
            "PictureInPictureProvider",
            ":app:checkDebugAarMetadata",
            "legacy JNI packaging",
            "compileConfig.resolution at 1 (1080p)",
            "Verified native Android cover API shape detected",
            "Enabled the generated publish-page save-cover entry",
            "does not contain optional fixed beauty-shape resources",
            "Shape/MicroShape beauty categories may be empty or incomplete",
            "Skipped the legacy multidex runtime because minSdk 24",
            "Jetifier remains enabled for compatibility",
            "Configuration Handoff",
            "原生 Android 功能配置",
            "./gradlew :app:installDebug",
            "Updated the managed native Android run guide in README.md",
        ],
        "Native Android report",
    )
    assert_contains(
        configuration_handoff,
        [
            "### 配置修改与生效速览",
            "| 配置项 | 修改入口 | 适用平台 | 最快生效方式 | 重新构建条件 | 无需执行 |",
            "| Android |",
            str(feature_config_path.resolve()),
            str((target / "app" / "src" / "main" / "assets" / "meishesdk.lic").resolve()),
            "./gradlew :app:installDebug",
            "adb shell am force-stop com.meishe.duanshipindemo",
            "MeisheShortVideoDemoActivity",
            "真机要求：美摄短视频 Demo 必须运行在真实 Android 设备上",
            "Android Emulator 和其他虚拟设备不受支持",
            "Gradle 依赖声明未变化时无需重新下载依赖",
        ],
        "Native Android command-level configuration handoff",
    )
    assert_contains(
        readme,
        [
            "User-maintained introduction.",
            "<!-- BEGIN MEISHE_NATIVE_ANDROID_RUN_GUIDE -->",
            "美摄短视频 Demo 运行",
            f"项目根目录：`{target.resolve()}`",
            f"Android 工程目录：`{target.resolve()}`",
            "App module：`app`",
            "applicationId：`com.meishe.duanshipindemo`",
            str(feature_config_path.resolve()),
            "### 依赖安装",
            "Native Android Gradle dependencies and Debug build",
            "### Android Studio 运行",
            "Gradle Sync",
            "### 命令行构建与真机运行",
            "adb devices",
            "./gradlew :app:installDebug",
            "adb shell am force-stop com.meishe.duanshipindemo",
            "com.meishe.duanshipindemo.meishe.MeisheShortVideoDemoActivity",
            "### 配置修改与生效",
            "### 遇到报错",
            "完整原始报错信息",
            "当前 Agent",
            "<!-- END MEISHE_NATIVE_ANDROID_RUN_GUIDE -->",
        ],
        "Native Android managed README run guide",
    )
    assert_not_contains(
        readme,
        ["Xcode", ".xcworkspace", "Product > Run"],
        "Native Android README platform isolation",
    )
    assert_contains(
        server_handoff,
        [
            "`MeisheFeatureConfig.java` 是用户功能配置最终来源",
            "有序菜单删除后由 SDK 重排 UI",
            "1080p 导出默认值",
            "原生 Android 使用当前 SDK 支持的服务配置",
            "标准编辑页",
            "导出视频",
        ],
        "Native Android AutoCut server handoff",
    )
    user_feature_marker = "// USER_FEATURE_CONFIG_MUST_BE_PRESERVED"
    write(feature_config_path, feature_config + f"\n{user_feature_marker}\n")
    run(command, "Native Android repeated integration fixture")
    assert_contains(
        read(feature_config_path),
        [user_feature_marker],
        "Native Android user feature configuration preservation",
    )
    repeated_readme = read(target / "README.md")
    if repeated_readme.count("<!-- BEGIN MEISHE_NATIVE_ANDROID_RUN_GUIDE -->") != 1:
        fail("Native Android repeated integration must keep exactly one managed README run guide")
    assert_contains(
        repeated_readme,
        ["User-maintained introduction.", "<!-- END MEISHE_NATIVE_ANDROID_RUN_GUIDE -->"],
        "Native Android README user content preservation",
    )


def validate_native_android_beauty_resource_preflight(work: Path) -> None:
    target = work / "native_android_beauty_resources"
    source = work / "native_android_beauty_resources_package"
    create_native_android_target(target)
    aar, _ = create_native_android_package(source, include_beauty_shape_resources=True)
    run(
        [
            str(PLATFORM_SCRIPTS["native-android"]),
            "--target-root",
            str(target),
            "--aar-path",
            str(aar),
            "--package-name",
            "com.meishe.duanshipindemo",
        ],
        "Native Android optional beauty resources fixture",
    )
    report = read(target / "meishe_docking_report.md")
    assert_contains(
        report,
        ["Optional Shape/MicroShape beauty resources are present in the selected AAR."],
        "Native Android beauty resource preflight",
    )
    assert_not_contains(
        report,
        ["does not contain optional fixed beauty-shape resources"],
        "Native Android complete beauty resource preflight",
    )


def validate_native_android_unverified_cover_api(work: Path) -> None:
    target = work / "native_android_unverified_cover"
    source = work / "native_android_unverified_cover_package"
    create_native_android_target(target)
    aar, _ = create_native_android_package(source, include_cover_api=False)
    run(
        [
            str(PLATFORM_SCRIPTS["native-android"]),
            "--target-root",
            str(target),
            "--aar-path",
            str(aar),
            "--package-name",
            "com.meishe.duanshipindemo",
        ],
        "Native Android unverified cover API fixture",
    )
    report = read(target / "meishe_docking_report.md")
    publish = read(
        target
        / "app"
        / "src"
        / "main"
        / "java"
        / "com"
        / "meishe"
        / "duanshipindemo"
        / "meishe"
        / "MeisheShortVideoPublishActivity.java"
    )
    assert_contains(
        report,
        ["does not exactly match the verified `saveCover`/`PathUtils.getCoverDir` callback shape"],
        "Native Android unverified cover API report",
    )
    assert_not_contains(
        publish,
        ["PathUtils.getCoverDir()", "NvModuleManager.get().saveCover(", 'actionButton("保存封面", false)'],
        "Native Android unverified cover API generation guard",
    )


def validate_native_android_unsupported_compile_sdk(work: Path) -> None:
    target = work / "native_android_unsupported_compile_sdk"
    source = work / "native_android_unsupported_package"
    create_native_android_target(target)
    build_file = target / "app" / "build.gradle"
    build_text = read(build_file)
    build_text = build_text.replace(
        """compileSdk {
        version = release(36) {
            minorApiLevel = 1
        }
    }""",
        "compileSdk 33",
    )
    write(build_file, build_text)
    aar, _ = create_native_android_package(source)

    output = run_failure(
        [
            str(PLATFORM_SCRIPTS["native-android"]),
            "--target-root",
            str(target),
            "--aar-path",
            str(aar),
            "--package-name",
            "com.meishe.duanshipindemo",
        ],
        "Native Android unsupported compileSdk fixture",
    )
    assert_contains(
        output,
        ["compileSdk 33", "supported integration floor 34"],
        "Native Android unsupported compileSdk failure",
    )
    if (target / "app" / "libs" / "NvShortVideoCore.aar").exists():
        fail("Unsupported native Android compileSdk must fail before copying the AAR")
    assert_contains(
        read(target / "gradle" / "libs.versions.toml"),
        ['coreKtx = "1.19.0"', 'lifecycleRuntimeKtx = "2.11.0"', 'activityCompose = "1.13.0"'],
        "Unsupported native Android compileSdk must not rewrite the version catalog",
    )
