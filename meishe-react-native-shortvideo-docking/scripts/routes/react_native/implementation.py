"""React Native implementation helpers kept inside the React Native route."""

from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import zipfile
from pathlib import Path

from meishe_docking_core import (
    BEGIN,
    END,
    IntegrationError,
    Report,
    TargetPlatforms,
    backup_path,
    copy_file,
    copy_tree_filtered,
    installed_xcode_version,
    is_within,
    package_dependency_version,
    project_file_dependency,
    project_local_path,
    read_text,
    rel,
    replace_external_source_path_refs,
    write_text,
)
from platform_support.ios import ios_project_root
from .constants import REACT_NATIVE_PLUGIN_NAME


REACT_NATIVE_ANDROID_NATIVE_LIBRARIES = (
    "jni/arm64-v8a/libNvStreamingSdkCore.so",
    "jni/arm64-v8a/libNvMSAICutter.so",
    "jni/armeabi-v7a/libNvStreamingSdkCore.so",
    "jni/armeabi-v7a/libNvMSAICutter.so",
)
OPTIONAL_REACT_NATIVE_ANDROID_BEAUTY_SHAPE_RESOURCES = (
    "beauty/shapePackage/facemesh/info.json",
    "beauty/shapePackage/warp/info.json",
)

REACT_NATIVE_DEMO_SERVER_CONFIG = {
    "host": "https://mall.meishesdk.com/api/shortvideo/v1/",
    "assetRequestUrl": "materialcenter/mall/custom/listAllAssemblyMaterial",
    "assetCategoryUrl": "materialcenter/appSdkApi/listTypeAndCategory",
    "assetMusiciansUrl": "materialcenter/appSdkApi/listMusic",
    "assetFontUrl": "materialcenter/listFont",
    "assetDownloadUrl": "materialcenter/mall/custom/materialInteraction",
    "assetPrefabricatedUrl": "materialcenter/beautyAssets/latest",
    "assetAutoCutUrl": "https://creative.meishesdk.com/api/app",
    "assetTagUrl": "materialcenter/listTemplateTag",
    "isAbroad": 1,
}

REACT_NATIVE_IOS_DRAFT_SNAPSHOT_API_MARKERS = (
    "NvTimelineDataManager",
    "newProject(localFilePaths:",
    "NvProEditConfig",
    "storeTimelineData",
    "updateProjectInfoFile",
    "managerAvailable",
    "destroySharedInstance",
)

REACT_NATIVE_ANDROID_PUBLISH_METHOD_2021 = """    private void goPublish(boolean needSaveDraft, boolean needSaveCover, boolean needSaveVideo, String videoPath) {
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
"""

REACT_NATIVE_ANDROID_PUBLISH_METHOD_PATCHED = """    private boolean mPublishEventDispatched;

    private void emitPublishResultOnce(boolean needSaveDraft, String videoPath, String coverImagePath) {
        if (mPublishEventDispatched) {
            return;
        }
        mPublishEventDispatched = true;
        WritableMap maps = Arguments.createMap();
        maps.putBoolean("hasDraft", needSaveDraft);
        maps.putString("coverImagePath", coverImagePath == null ? "" : coverImagePath);
        maps.putString("videoPath", videoPath);
        //目前默认传00
        maps.putString("projectId", "00");
        invokeMethod(VIDEO_EDIT_CHANNEL, VIDEO_EDIT_RESULT_EVENT, maps);
        AppManager.getInstance().finishAllEditActivity();
    }

    private void goPublish(boolean needSaveDraft, boolean needSaveCover, boolean needSaveVideo, String videoPath) {
        if (null == getCurrentActivity()) {
            return;
        }
        mPublishEventDispatched = false;
        NvModuleManager.get().saveCover(PathUtils.getCoverDir(), String.valueOf(System.currentTimeMillis()), mCoverPoint, false,
                new NvModuleManager.OnCoverSavedCallBack() {
                    @Override
                    public void onCoverSaved(String path) {
                        emitPublishResultOnce(needSaveDraft, videoPath, TextUtils.isEmpty(path) ? "" : getSDPath(path));
                    }

                    @Override
                    public void onCoverSaveFailed() {
                        emitPublishResultOnce(needSaveDraft, videoPath, "");
                    }
                });
    }
"""


def read_react_native_aar_entries(aar: Path, label: str) -> set[str]:
    if not aar.is_file():
        raise IntegrationError(f"{label} not found: `{aar}`.")
    try:
        with zipfile.ZipFile(aar) as archive:
            return set(archive.namelist())
    except zipfile.BadZipFile as exc:
        raise IntegrationError(f"{label} is not a valid AAR/ZIP archive: `{aar}`.") from exc


def validate_react_native_android_native_libraries(
    target_root: Path,
    source_plugin: Path,
    report: Report,
) -> None:
    if not (target_root / "android").is_dir():
        return

    plugin_aar = source_plugin / "android" / "libs" / "NvShortVideoCore.aar"
    plugin_entries = read_react_native_aar_entries(plugin_aar, "React Native plugin NvShortVideoCore.aar")
    missing_beauty_resources = [
        resource
        for resource in OPTIONAL_REACT_NATIVE_ANDROID_BEAUTY_SHAPE_RESOURCES
        if not any(entry.lstrip("/").endswith(resource) for entry in plugin_entries)
    ]
    if missing_beauty_resources:
        report.add_vendor_warning(
            "The React Native Android AAR does not contain optional fixed beauty-shape resources: "
            + ", ".join(f"`{item}`" for item in missing_beauty_resources)
            + ". Core RN/ShortVideo flows can still run, but Shape/MicroShape beauty categories may be "
            "empty or incomplete. Obtain the matching resource delivery from Meishe; this is not an "
            "online-material request failure."
        )
    else:
        report.add_input("React Native Android optional Shape/MicroShape beauty resources are present.")
    local_jni_root = source_plugin / "android" / "src" / "main" / "jniLibs"
    missing = [
        entry
        for entry in REACT_NATIVE_ANDROID_NATIVE_LIBRARIES
        if entry not in plugin_entries
        and not (local_jni_root / Path(entry).relative_to("jni")).is_file()
    ]
    if not missing:
        report.add_change("React Native Android native engine libraries are complete for arm64-v8a and armeabi-v7a.")
        return

    formatted = "\n".join(f"- `{entry}`" for entry in missing)
    raise IntegrationError(
        "The supplied official React Native ShortVideo package is incomplete for Android runtime: "
        "`react-native-nvshortvideo/android/libs/NvShortVideoCore.aar` and the plugin `jniLibs` do not contain "
        "the required native engine libraries:\n"
        f"{formatted}\n"
        "Do not continue with a build-only integration and do not ask the user for a native Demo package as a "
        "normal React Native input. Re-download a corrected complete `React Native工程` package from Meishe "
        "Developer Center or contact Meishe support and provide this missing-library list. The RN package itself "
        "must contain the Android runtime libraries before the skill can integrate it."
    )


def merge_react_native_android_permissions(target_root: Path, report: Report) -> None:
    manifest = target_root / "android" / "app" / "src" / "main" / "AndroidManifest.xml"
    if not manifest.exists():
        report.add_warning(f"React Native AndroidManifest.xml not found at `{manifest}`; Android 13 media permissions were not inserted.")
        return

    text = read_text(manifest)
    permission_block = """<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
<uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />"""
    xml_block = f"<!-- {BEGIN} -->\n{permission_block}\n<!-- {END} -->"

    if f"<!-- {BEGIN} -->" in text:
        text = re.sub(r"<!-- BEGIN MEISHE_DUANSHIPIN_DOCKING -->.*?<!-- END MEISHE_DUANSHIPIN_DOCKING -->", xml_block, text, flags=re.S)
    elif "<application" in text:
        text = text.replace("<application", xml_block + "\n\n    <application", 1)
    else:
        text = text.replace("</manifest>", xml_block + "\n</manifest>")

    write_text(manifest, text, target_root, report, "Merged React Native Android 13 media permissions")


def patch_react_native_app_identity(
    target_root: Path,
    android_package_name: str | None,
    ios_bundle_identifier: str | None,
    report: Report,
) -> None:
    android_gradle = target_root / "android" / "app" / "build.gradle"
    android_gradle_kts = target_root / "android" / "app" / "build.gradle.kts"
    gradle_file = android_gradle if android_gradle.exists() else android_gradle_kts

    if not android_package_name:
        detected = None
        if gradle_file.exists():
            match = re.search(r'applicationId\s*(?:=\s*)?["\']([^"\']+)["\']', read_text(gradle_file))
            detected = match.group(1) if match else None
        if detected and detected != "com.meishe.duanshipindemo":
            report.add_warning(
                f"React Native Android applicationId is `{detected}`. The generated official Demo host is verified with "
                "`com.meishe.duanshipindemo`; use `--android-package-name com.meishe.duanshipindemo` for Demo-service validation, "
                "or configure a customer server for the real package."
            )
    elif gradle_file.exists():
        text = read_text(gradle_file)
        text = re.sub(
            r'(\bnamespace\s*(?:=\s*)?)["\'][^"\']+["\']',
            lambda match: f'{match.group(1)}"{android_package_name}"',
            text,
        )
        text = re.sub(
            r'(\bapplicationId\s*(?:=\s*)?)["\'][^"\']+["\']',
            lambda match: f'{match.group(1)}"{android_package_name}"',
            text,
        )
        write_text(gradle_file, text, target_root, report, "Set React Native Android namespace/applicationId")
    elif (target_root / "android").is_dir():
        report.add_warning(
            "React Native Android app Gradle file was not found; the requested Android package name "
            "could not update applicationId."
        )

    if android_package_name:
        source_roots = [
            target_root / "android" / "app" / "src" / "main" / "java",
            target_root / "android" / "app" / "src" / "main" / "kotlin",
        ]
        for source_root in source_roots:
            if not source_root.exists():
                continue
            for source in (
                list(source_root.rglob("MainActivity.kt"))
                + list(source_root.rglob("MainActivity.java"))
                + list(source_root.rglob("MainApplication.kt"))
                + list(source_root.rglob("MainApplication.java"))
            ):
                content = read_text(source)
                content = re.sub(
                    r'^package[ \t]+[A-Za-z0-9_.]+?import[ \t]+',
                    f'package {android_package_name}\n\nimport ',
                    content,
                    count=1,
                    flags=re.M,
                )
                content = re.sub(
                    r'^package[ \t]+[A-Za-z0-9_.]+[ \t]*;?',
                    f'package {android_package_name}',
                    content,
                    count=1,
                    flags=re.M,
                )
                destination = source_root / Path(*android_package_name.split(".")) / source.name
                write_text(destination, content, target_root, report, "Set React Native Android source package")
                if destination != source and source.exists():
                    backup_path(source, target_root, report)
                    if not report.dry_run:
                        source.unlink()
                    report.add_change(
                        f"Removed old React Native Android source path: `{rel(source, target_root)}`"
                    )

    if ios_bundle_identifier:
        xcode_projects = (
            sorted((target_root / "ios").glob("*.xcodeproj/project.pbxproj"))
            if (target_root / "ios").is_dir()
            else []
        )
        for project_file in xcode_projects:
            text = read_text(project_file)
            updated = re.sub(
                r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*"?[^";]+"?;',
                f'PRODUCT_BUNDLE_IDENTIFIER = "{ios_bundle_identifier}";',
                text,
            )
            write_text(project_file, updated, target_root, report, "Set React Native iOS Bundle Identifier")

    if android_package_name:
        report.add_input(f"React Native Android package: `{android_package_name}`")
    if ios_bundle_identifier:
        report.add_input(f"React Native iOS Bundle Identifier: `{ios_bundle_identifier}`")


def patch_package_json(target_root: Path, plugin: Path, report: Report) -> None:
    path = target_root / "package.json"
    if not path.exists():
        raise IntegrationError("package.json not found.")
    data = json.loads(read_text(path))
    deps = data.setdefault("dependencies", {})
    desired = project_file_dependency(plugin, target_root)
    if deps.get("react-native-nvshortvideo") == desired:
        report.add_change("package.json already contains react-native-nvshortvideo dependency.")
    else:
        deps["react-native-nvshortvideo"] = desired
        write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", target_root, report, "Added React Native nvshortvideo file dependency")


def isolate_react_native_tooling(target_root: Path, report: Report) -> None:
    """Keep app lint output separate from copied SDK and generated native dependencies."""
    ignore_path = target_root / ".eslintignore"
    existing = read_text(ignore_path) if ignore_path.exists() else ""
    required = ["vendor/meishe/**"]
    if (target_root / "ios").is_dir():
        required.append("ios/Pods/**")
    if (target_root / "android").is_dir():
        required.extend(["android/.gradle/**", "android/app/build/**"])
    lines = existing.splitlines()
    changed = False
    for item in required:
        if item not in lines:
            lines.append(item)
            changed = True
    if changed:
        content = "\n".join(line for line in lines if line.strip()) + "\n"
        write_text(ignore_path, content, target_root, report, "Isolated React Native app lint from copied third-party SDK/build output")
    else:
        report.add_change("React Native ESLint third-party/build exclusions already present.")
    excluded = ["vendor/meishe"]
    if (target_root / "ios").is_dir():
        excluded.append("ios/Pods")
    if (target_root / "android").is_dir():
        excluded.append("Android build output")
    report.add_next_check(
        "React Native generated-code check: after dependency approval, use the project's existing lint script for `App.tsx`, `App.jsx`, and `src`; "
        f"treat {', '.join(excluded)} diagnostics as third-party SDK/toolchain output. Do not use a package runner that downloads an undeclared linter."
    )


def configure_react_native_jest(target_root: Path, report: Report) -> None:
    jest_config = target_root / "jest.config.js"
    if not jest_config.exists():
        report.add_warning("React Native jest.config.js was not found; native ShortVideo Jest mock was not configured.")
        return

    setup = """/* eslint-env jest */

jest.mock('react-native-nvshortvideo', () => {
  const success = () => jest.fn(() => Promise.resolve(true));
  const values = names => Object.fromEntries(names.map(name => [name, name]));
  const operator = {
    configServerInfo: success(),
    downloadPrefabricatedMaterial: success(),
    startVideoCaptrue: success(),
    startVideoDualCaptrue: success(),
    startVideoDualCaptrueWithVideo: success(),
    startSeleteFilesForEdit: success(),
    getDraftList: jest.fn(() => Promise.resolve([])),
    reeditDraft: success(),
    deleteDraft: success(),
    saveDraft: success(),
    compileCurrentTimeline: success(),
    getPublishInfo: jest.fn(() => Promise.resolve({})),
    exitEdit: success(),
    setVideoEditEventHandler: jest.fn(),
    setDraftUpdateHandler: jest.fn(),
    setVideoCompileEventHandler: jest.fn(),
  };
  const captureBottomMenuItem = {
    image: 'capture_bottom_menu_image',
    video: 'capture_bottom_menu_video',
    smart: 'capture_bottom_menu_smart',
    template: 'capture_bottom_menu_template',
  };
  const captureMenuItem = values(['device', 'speed', 'timer', 'beauty', 'makeup', 'prop', 'matting', 'flashlight', 'filter', 'original', 'dualtype']);
  const dualType = values(['leftRight', 'topDown', 'leftRect', 'leftCircle', 'topCircle']);
  const editMenuItem = values(['release', 'download', 'edit', 'text', 'sticker', 'effect', 'filter', 'caption', 'audio', 'record']);
  const editMode = values(['NvEditMode9v16', 'NvEditMode16v9', 'NvEditMode3v4', 'NvEditMode4v3', 'NvEditMode1v1', 'NvEditMode18v9', 'NvEditMode9v18', 'NvEditMode8v9', 'NvEditMode9v8']);

  return {
    NvShortVideo: { shareInstance: () => operator },
    NvVideoConfig: class NvVideoConfig {
      constructor() {
        this.albumConfig = { useAutoCut: false, maxSelectCount: 50 };
        this.templateConfig = { useAutoCut: false, maxSelectCount: 50 };
        this.captureConfig = { captureBottomMenuItems: [], captureMenuItems: [], dualMenuItems: [] };
        this.editConfig = { editMenuItems: [], maxVolume: 4 };
        this.compileConfig = {
          watermarkConfig: { watermark: null, width: 0, height: 0, offsetX: 0, offsetY: 0, position: 0 },
          coverWatermarkConfig: { watermark: null, width: 0, height: 0, offsetX: 0, offsetY: 0, position: 0 },
        };
        this.modelConfig = {};
      }
    },
    NvCaptureBottomMenuItem: captureBottomMenuItem,
    NvCaptureMenuItem: captureMenuItem,
    NvDualConfig: class NvDualConfig {},
    NvDualType: dualType,
    NvEditMenuItem: editMenuItem,
    NvEditMode: editMode,
    NvEditModeSource: values(['firstAsset', 'fixed']),
    NvExportImageType: values(['NvExportImageTypePNG', 'NvExportImageTypeJPEG']),
    NvImageCaptionStyle: values(['none', 'bg', 'bgAlpha', 'outline']),
    NvsCompileVideoBitrateGrade: values(['NvsCompileBitrateGradeLow', 'NvsCompileBitrateGradeMedium', 'NvsCompileBitrateGradeHigh']),
    NvTimePair: class NvTimePair {
      constructor(minDuration, maxDuration) {
        this.minDuration = minDuration;
        this.maxDuration = maxDuration;
      }
    },
    NvVideoCompileResolution: values(['NvVideoCompileResolution_720', 'NvVideoCompileResolution_1080', 'NvVideoCompileResolution_4K']),
    NvVideoPreviewResolution: values(['NvVideoPreviewResolution_720', 'NvVideoPreviewResolution_1080']),
    NvVideoEditEvent: { publish: 'publish' },
    NvVideoCompileEvent: {
      progress: 'progress',
      complete: 'complete',
      coverImageSelected: 'coverImageSelected',
    },
  };
});
"""
    write_text(target_root / "jest.setup.js", setup, target_root, report, "Generated React Native Jest mock for native ShortVideo bridge")

    suffix = "ts" if (target_root / "tsconfig.json").exists() else "js"
    test = """import { NvVideoConfig } from 'react-native-nvshortvideo';
import { applyMeisheFeatureConfig, validateMeisheFeatureConfig } from '../src/meisheFeatureConfig';

test('Meishe feature configuration preserves editable values and rejects invalid boundaries', () => {
  const config = applyMeisheFeatureConfig(new NvVideoConfig());
  expect(typeof config.albumConfig.useAutoCut).toBe('boolean');
  expect(typeof config.templateConfig.useAutoCut).toBe('boolean');
  expect(config.editConfig.maxVolume).toBeGreaterThan(0);
  expect(config.editConfig.maxVolume).toBeLessThanOrEqual(8);
  expect(() => validateMeisheFeatureConfig(config)).not.toThrow();

  config.compileConfig.watermarkConfig.watermark = null;
  expect(() => validateMeisheFeatureConfig(config)).not.toThrow();
  config.compileConfig.watermarkConfig.watermark = { imageName: 'meishe_feature_watermark' };
  config.compileConfig.watermarkConfig.width = 0;
  config.compileConfig.watermarkConfig.height = 0;
  expect(() => validateMeisheFeatureConfig(config)).toThrow('width and height');

  config.editConfig.maxVolume = 0;
  expect(() => validateMeisheFeatureConfig(config)).toThrow('maxVolume');
});
"""
    write_text(
        target_root / "__tests__" / f"MeisheFeatureConfig-test.{suffix}",
        test,
        target_root,
        report,
        "Generated React Native feature configuration Jest test",
    )

    text = read_text(jest_config)
    if "jest.setup.js" not in text:
        if "module.exports = {" in text:
            text = text.replace(
                "module.exports = {",
                "module.exports = {\n  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],\n  modulePathIgnorePatterns: ['<rootDir>/.meishe_docking_backup/'],",
                1,
            )
            write_text(jest_config, text, target_root, report, "Configured React Native Jest native mock and backup isolation")
        else:
            report.add_warning("React Native Jest config shape is not recognized; add jest.setup.js and ignore .meishe_docking_backup manually.")
    else:
        report.add_change("React Native Jest native mock and backup isolation already configured.")


def update_react_native_readme(
    target_root: Path,
    targets: TargetPlatforms,
    android_package_name: str | None,
    ios_bundle_identifier: str | None,
    report: Report,
) -> None:
    """Append or refresh a route-local run guide without replacing user README content."""
    readme = target_root / "README.md"
    existing = read_text(readme) if readme.exists() else f"# {target_root.name}\n"
    begin = "<!-- BEGIN MEISHE_REACT_NATIVE_RUN_GUIDE -->"
    end = "<!-- END MEISHE_REACT_NATIVE_RUN_GUIDE -->"
    root = target_root.resolve()
    node_step = next(
        (step for step in report.dependency_steps if step.label == "React Native JavaScript packages"),
        None,
    )
    node_command = node_step.command if node_step else "npm install"
    manager = node_command.split()[0]
    start_command = f"{manager} start"
    android_command = (
        f"{manager} run android -- --deviceId <ANDROID_DEVICE_ID>"
        if manager == "npm"
        else f"{manager} android --deviceId <ANDROID_DEVICE_ID>"
    )
    ios_command = (
        f"{manager} run ios -- --udid <IOS_DEVICE_UDID>"
        if manager == "npm"
        else f"{manager} ios --udid <IOS_DEVICE_UDID>"
    )
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
        "- 美摄 RN 包：`vendor/meishe/react-native-nvshortvideo`",
        "",
        "### 依赖安装",
        "",
        "首次运行或依赖声明变化后，先按 `meishe_docking_report.md` 的审批流程执行以下项目内命令：",
        "",
        ]
    )
    for step in report.dependency_steps:
        if not step.label.startswith("React Native"):
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
    lines.extend(
        [
            "### Metro",
            "",
            "在独立终端持续运行：",
            "",
            "```sh",
            f"cd {root}",
            start_command,
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
                android_command,
                "```",
                "",
                f"Android Studio 可直接打开 `{root / 'android'}`，完成 Gradle Sync 后选择 `app` 和目标设备，再点击 Run。",
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
            workspace = ios_root / f"{projects[0].stem if projects else target_root.name}.xcworkspace"
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
                "保持上方 Metro 终端运行，再执行：",
                "",
                "```sh",
                f"cd {root}",
                ios_command,
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
            "- 受操作系统、Node/包管理器、Ruby/CocoaPods、JDK/Gradle、Xcode、网络、签名和设备环境差异影响，手动接入或运行可能报错。",
            "- 遇到任何报错，请复制执行命令和完整原始报错信息发给当前 Agent 继续处理；不要只截取最后一行，也不需要自行猜测修复。",
            "",
            "### 美摄配置边界",
            "",
            "- 官方 Demo 服务验证保持 `com.meishe.duanshipindemo`；客户包名需要客户服务器、正式 License 和签名配置。",
            "- 服务配置入口：`src/meisheShortVideoDocking.ts` 或同名 `.js` 文件中的 `meisheServerConfig`。",
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
    write_text(readme, updated, target_root, report, f"Generated React Native {guide_label} run guide in README")


def patch_package_lock_dependency(target_root: Path, plugin: Path, report: Report) -> None:
    path = target_root / "package-lock.json"
    if not path.exists():
        return
    try:
        data = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        report.add_warning(f"React Native package-lock.json could not be parsed ({exc}); run your package manager once after integration.")
        return

    local_path = project_local_path(plugin, target_root)
    desired = f"file:{local_path}"
    changed = False
    packages = data.get("packages")
    if isinstance(packages, dict):
        root_package = packages.setdefault("", {})
        if isinstance(root_package, dict):
            deps = root_package.setdefault("dependencies", {})
            if isinstance(deps, dict) and deps.get(REACT_NATIVE_PLUGIN_NAME) != desired:
                deps[REACT_NATIVE_PLUGIN_NAME] = desired
                changed = True
        node_entry = packages.setdefault(f"node_modules/{REACT_NATIVE_PLUGIN_NAME}", {})
        if isinstance(node_entry, dict):
            if node_entry.get("resolved") != local_path:
                node_entry["resolved"] = local_path
                changed = True
            if node_entry.get("link") is not True:
                node_entry["link"] = True
                changed = True
        local_entry = packages.setdefault(local_path, {})
        if isinstance(local_entry, dict):
            try:
                plugin_data = json.loads(read_text(plugin / "package.json"))
            except (OSError, json.JSONDecodeError):
                plugin_data = {}
            for key in ("name", "version"):
                value = plugin_data.get(key)
                if value and local_entry.get(key) != value:
                    local_entry[key] = value
                    changed = True
        for key in list(packages):
            if (
                key not in {"", local_path, f"node_modules/{REACT_NATIVE_PLUGIN_NAME}"}
                and REACT_NATIVE_PLUGIN_NAME in key
                and (":\\" in key or key.startswith("/") or "Downloads" in key or "Edge Download" in key)
            ):
                del packages[key]
                changed = True

    deps = data.get("dependencies")
    if isinstance(deps, dict):
        entry = deps.setdefault(REACT_NATIVE_PLUGIN_NAME, {})
        if isinstance(entry, dict):
            if entry.get("version") != desired:
                entry["version"] = desired
                changed = True
            if entry.get("resolved") != local_path:
                entry["resolved"] = local_path
                changed = True

    if changed:
        write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", target_root, report, "Updated React Native package-lock.json to project-local nvshortvideo dependency")
    else:
        report.add_change("React Native package-lock.json already points at the project-local nvshortvideo dependency.")


def ensure_react_native_node_module(target_root: Path, plugin: Path, report: Report) -> None:
    node_modules = target_root / "node_modules"
    if not node_modules.exists():
        return

    dependency_dir = node_modules / REACT_NATIVE_PLUGIN_NAME
    if dependency_dir.exists() or dependency_dir.is_symlink():
        try:
            if dependency_dir.resolve() == plugin.resolve():
                report.add_change("node_modules/react-native-nvshortvideo already points to the project-local vendor copy.")
                return
        except OSError:
            pass
        if not report.dry_run:
            if dependency_dir.is_symlink() or dependency_dir.is_file():
                dependency_dir.unlink()
            else:
                shutil.rmtree(dependency_dir)
        report.add_change("Removed existing node_modules/react-native-nvshortvideo so it can be replaced with the project-local vendor copy.")

    if report.dry_run:
        report.add_change("Would link or copy node_modules/react-native-nvshortvideo from the project-local vendor copy.")
        return

    dependency_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(plugin, dependency_dir, target_is_directory=True)
        report.add_change("Linked node_modules/react-native-nvshortvideo to the project-local vendor copy.")
    except OSError:
        copy_tree_filtered(plugin, dependency_dir, target_root, report, "React Native plugin into node_modules fallback copy")


def install_react_native_plugin_dependency(target_root: Path, plugin: Path, source_plugin: Path, report: Report) -> None:
    patch_package_json(target_root, plugin, report)
    patch_package_lock_dependency(target_root, plugin, report)
    replace_external_source_path_refs(
        target_root,
        source_plugin,
        plugin,
        [target_root / "yarn.lock", target_root / "pnpm-lock.yaml", target_root / "package-lock.json"],
        report,
        "React Native",
    )
    ensure_react_native_node_module(target_root, plugin, report)
    report.add_input(f"React Native dependency: `{project_file_dependency(plugin, target_root)}`")


def enable_react_native_androidx_jetifier(target_root: Path, report: Report) -> None:
    gradle_properties = target_root / "android" / "gradle.properties"
    if not gradle_properties.exists():
        report.add_warning(f"React Native Android gradle.properties not found at `{gradle_properties}`; Jetifier was not enabled.")
        return

    text = read_text(gradle_properties)
    original = text
    for key, value in (("android.useAndroidX", "true"), ("android.enableJetifier", "true")):
        if re.search(rf"^{re.escape(key)}=", text, re.M):
            text = re.sub(rf"^{re.escape(key)}=.*$", f"{key}={value}", text, flags=re.M)
        else:
            text = text.rstrip() + f"\n{key}={value}\n"

    if text != original:
        write_text(gradle_properties, text, target_root, report, "Enabled AndroidX/Jetifier for React Native ShortVideo")
    else:
        report.add_change("React Native AndroidX/Jetifier properties already set.")


def add_react_native_android_repositories(target_root: Path, report: Report) -> None:
    build_gradle = target_root / "android" / "build.gradle"
    if not build_gradle.exists():
        report.add_warning(f"React Native Android root build.gradle not found at `{build_gradle}`; Meishe Maven mirror repositories were not inserted.")
        return

    text = read_text(build_gradle)
    block = """// BEGIN MEISHE_REACT_NATIVE_REPOSITORIES
allprojects {
    repositories {
        google()
        mavenCentral()
        maven { url 'https://www.jitpack.io' }
        mavenLocal()
        maven { url 'https://maven.aliyun.com/repository/public/' }
        maven { url 'https://maven.aliyun.com/repository/gradle-plugin' }
        maven { url 'https://maven.aliyun.com/nexus/content/groups/public/' }
        maven { url 'https://maven.aliyun.com/nexus/content/repositories/jcenter' }
        maven { url 'https://maven.aliyun.com/nexus/content/repositories/google' }
        maven { url 'https://maven.aliyun.com/nexus/content/repositories/gradle-plugin' }
    }
}
// END MEISHE_REACT_NATIVE_REPOSITORIES
"""
    if "// BEGIN MEISHE_REACT_NATIVE_REPOSITORIES" in text:
        updated = re.sub(
            r"// BEGIN MEISHE_REACT_NATIVE_REPOSITORIES.*?// END MEISHE_REACT_NATIVE_REPOSITORIES\n?",
            block,
            text,
            count=1,
            flags=re.S,
        )
        if updated == text:
            report.add_change("React Native Android Maven repositories already use standard-first order with Meishe fallbacks.")
        else:
            write_text(build_gradle, updated, target_root, report, "Updated React Native Android Maven repository order")
        return

    legacy_block = """allprojects {
    repositories {
        maven { url 'https://maven.aliyun.com/repository/public/' }
        maven { url 'https://maven.aliyun.com/repository/gradle-plugin' }
        maven { url 'https://maven.aliyun.com/nexus/content/groups/public/' }
        maven { url 'https://maven.aliyun.com/nexus/content/repositories/jcenter' }
        maven { url 'https://maven.aliyun.com/nexus/content/repositories/google' }
        maven { url 'https://maven.aliyun.com/nexus/content/repositories/gradle-plugin' }
        maven { url 'https://www.jitpack.io' }
        google()
        mavenCentral()
        mavenLocal()
    }
}
"""
    if legacy_block in text:
        text = text.replace(legacy_block, block, 1)
        write_text(build_gradle, text, target_root, report, "Reordered React Native Android repositories with standard sources first")
        return

    if 'apply plugin: "com.facebook.react.rootproject"' in text:
        text = text.replace('apply plugin: "com.facebook.react.rootproject"', block + '\napply plugin: "com.facebook.react.rootproject"', 1)
    else:
        text = text.rstrip() + "\n\n" + block
    write_text(build_gradle, text, target_root, report, "Added standard-first React Native repositories with Meishe official-demo fallbacks")


def copy_react_native_plugin_aars(
    target_root: Path,
    plugin: Path,
    report: Report,
    source_plugin: Path | None = None,
) -> None:
    inspection_plugin = plugin if plugin.exists() else source_plugin
    plugin_libs = (inspection_plugin or plugin) / "android" / "libs"
    app_libs = target_root / "android" / "app" / "libs"
    if not plugin_libs.exists():
        report.add_warning(f"React Native plugin AAR directory not found at `{plugin_libs}`; app/libs AAR copy was skipped.")
        return

    aars = sorted(plugin_libs.glob("*.aar"))
    if not aars:
        report.add_warning(f"No AAR files were found in `{plugin_libs}`; app/libs AAR copy was skipped.")
        return

    for aar in aars:
        reason = "Would copy React Native plugin AAR into Android app/libs" if report.dry_run else "Copied React Native plugin AAR into Android app/libs"
        copy_file(aar, app_libs / aar.name, target_root, report, reason)


def patch_react_native_app_aars(target_root: Path, report: Report) -> None:
    build_gradle = target_root / "android" / "app" / "build.gradle"
    if not build_gradle.exists():
        report.add_warning(f"React Native Android app build.gradle not found at `{build_gradle}`; app/libs AAR dependency was not inserted.")
        return

    text = read_text(build_gradle)
    dependency = '    implementation fileTree(dir: "libs", include: ["*.jar", "*.aar"])'
    if 'fileTree(dir: "libs"' in text or "fileTree(dir: 'libs'" in text:
        report.add_change("React Native Android app/libs fileTree dependency already present.")
        return
    if "dependencies {" not in text:
        report.add_warning(f"`dependencies {{` not found in `{build_gradle}`; app/libs AAR dependency was not inserted.")
        return
    text = text.replace("dependencies {", "dependencies {\n" + dependency + "\n", 1)
    write_text(build_gradle, text, target_root, report, "Added React Native app/libs AAR dependency")


def patch_react_native_plugin_gradle(
    target_root: Path,
    plugin: Path,
    report: Report,
    source_plugin: Path | None = None,
) -> None:
    build_gradle = plugin / "android" / "build.gradle"
    read_gradle = build_gradle
    if not read_gradle.exists() and report.dry_run and source_plugin is not None:
        source_gradle = source_plugin / "android" / "build.gradle"
        if source_gradle.exists():
            read_gradle = source_gradle
    if not read_gradle.exists():
        report.add_warning(f"React Native plugin build.gradle not found at `{build_gradle}`; Gradle compatibility patch was skipped.")
        return
    if not is_within(plugin, target_root):
        report.add_next_check(
            f"React Native plugin Gradle patch was skipped because the plugin package is outside the target project: `{plugin}`. "
            "If Android build fails in the plugin module, copy the plugin folder under the target project and re-run with that path, or patch the external plugin package deliberately."
        )
        return

    content = """apply plugin: 'com.android.library'

android {
    namespace 'com.meishe.nvshortvideo'
    compileSdkVersion rootProject.ext.has('compileSdkVersion') ? rootProject.ext.compileSdkVersion : 34

    defaultConfig {
        minSdkVersion rootProject.ext.has('minSdkVersion') ? rootProject.ext.minSdkVersion : 23
        targetSdkVersion rootProject.ext.has('targetSdkVersion') ? rootProject.ext.targetSdkVersion : 34
        versionCode 1
        versionName "1.0"
    }

    lint {
        abortOnError false
    }

    repositories {
        flatDir {
            dirs './libs'
        }
    }
}

repositories {
    google()
    mavenCentral()
    maven { url 'https://jitpack.io' }
}

configurations.configureEach {
    exclude group: 'com.android.support'
}

dependencies {
    compileOnly fileTree(dir: "libs", include: ["*.jar", '*.aar'])
    implementation 'com.facebook.react:react-android'

    implementation 'androidx.multidex:multidex:2.0.0'
    implementation 'com.google.android.material:material:1.0.0'
    implementation 'androidx.appcompat:appcompat:1.0.0'
    implementation 'androidx.recyclerview:recyclerview:1.1.0'
    implementation 'androidx.constraintlayout:constraintlayout:1.1.3'
    implementation 'com.squareup.okhttp3:okhttp:4.9.2'
    implementation 'com.google.code.gson:gson:2.8.5'
    implementation 'com.zlc.glide:webpdecoder:1.4.4.9.0'
    implementation 'com.blankj:utilcodex:1.31.1'
    implementation 'com.github.CymChad:BaseRecyclerViewAdapterHelper:2.9.50'
    implementation 'com.github.bumptech.glide:glide:4.9.0'
    annotationProcessor 'com.github.bumptech.glide:compiler:4.9.0'
    implementation 'com.permissionx.guolindev:permission-support:1.4.0'
    implementation 'com.scwang.smart:refresh-layout-kernel:2.0.1'
    implementation 'com.scwang.smart:refresh-header-classics:2.0.1'
    implementation 'androidx.room:room-runtime:2.2.5'
    annotationProcessor 'androidx.room:room-compiler:2.2.5'
    implementation 'androidx.media3:media3-exoplayer:1.1.1'
    implementation 'androidx.media3:media3-ui:1.1.1'
    implementation 'org.greenrobot:eventbus:3.2.0'
}
"""
    write_text(build_gradle, content, target_root, report, "Patched React Native plugin Android Gradle for current AGP/AndroidX")


def patch_react_native_android_publish_bridge(
    target_root: Path,
    plugin: Path,
    report: Report,
    source_plugin: Path | None = None,
) -> None:
    bridge = plugin / "android" / "src" / "main" / "java" / "com" / "meishe" / "nvshortvideo" / "VideoEditPlugin.java"
    read_bridge = bridge
    if not read_bridge.exists() and report.dry_run and source_plugin is not None:
        source_bridge = source_plugin / "android" / "src" / "main" / "java" / "com" / "meishe" / "nvshortvideo" / "VideoEditPlugin.java"
        if source_bridge.exists():
            read_bridge = source_bridge
    if not read_bridge.exists():
        report.add_warning(
            f"React Native Android bridge was not found at `{bridge}`; AutoCut publish fallback was not applied."
        )
        return

    text = read_text(read_bridge)
    if "private void emitPublishResultOnce(" in text:
        report.add_change("React Native Android AutoCut publish fallback already present.")
        return
    if REACT_NATIVE_ANDROID_PUBLISH_METHOD_2021 not in text:
        report.add_warning(
            "React Native Android `goPublish` does not match the verified ShortVideo 2.0.2.1 source shape. "
            "No vendor patch was applied; manually verify that cover-save failure still emits `VideoEditResultEvent`."
        )
        return

    patched = text.replace(
        REACT_NATIVE_ANDROID_PUBLISH_METHOD_2021,
        REACT_NATIVE_ANDROID_PUBLISH_METHOD_PATCHED,
        1,
    )
    write_text(
        bridge,
        patched,
        target_root,
        report,
        "Patched verified React Native Android AutoCut publish fallback",
    )


def install_react_native_ios_draft_snapshot_bridge(target_root: Path, report: Report) -> bool:
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        return False
    app_delegates = sorted(ios_root.glob("*/AppDelegate.swift"))
    app_delegates.extend(sorted(ios_root.glob("*/AppDelegate.mm")))
    app_delegates.extend(sorted(ios_root.glob("*/AppDelegate.m")))
    projects = sorted(
        project
        for project in ios_root.glob("*.xcodeproj/project.pbxproj")
        if project.parent.name != "Pods.xcodeproj"
    )
    if not app_delegates or not projects:
        report.add_warning(
            "React Native iOS AutoCut draft patch requires a standard app target with `AppDelegate` and an `.xcodeproj`; no vendor patch was applied."
        )
        return False

    app_dir = app_delegates[0].parent
    project = next((item for item in projects if item.parent.stem == app_dir.name), projects[0])
    helper_path = app_dir / "NvDraftSnapshotBridge.swift"
    helper_source = read_text(Path(__file__).parent / "templates" / "NvDraftSnapshotBridge.swift")
    project_text = read_text(project)

    if "NvDraftSnapshotBridge.swift in Sources" not in project_text:
        build_section = "/* End PBXBuildFile section */"
        reference_section = "/* End PBXFileReference section */"
        group_blocks = re.findall(
            r"[ \t]*[A-F0-9]{24}(?: /\*.*?\*/)? = \{\n[ \t]*isa = PBXGroup;.*?\n[ \t]*\};",
            project_text,
            re.DOTALL,
        )
        app_group = next((block for block in group_blocks if "AppDelegate" in block), None)
        source_blocks = re.findall(
            r"[ \t]*[A-F0-9]{24} /\* Sources \*/ = \{\n[ \t]*isa = PBXSourcesBuildPhase;.*?\n[ \t]*\};",
            project_text,
            re.DOTALL,
        )
        source_block = next((block for block in source_blocks if "AppDelegate" in block), None)
        if source_block is None and len(source_blocks) == 1:
            source_block = source_blocks[0]
        if (
            build_section not in project_text
            or reference_section not in project_text
            or app_group is None
            or source_block is None
        ):
            report.add_warning(
                f"React Native iOS Xcode project shape was not recognized at `{project}`; the Swift draft helper was not added and no vendor patch was applied."
            )
            return False

        seed = str(project.resolve()).encode("utf-8")
        file_id = hashlib.sha1(seed + b":NvDraftSnapshotBridge:file").hexdigest()[:24].upper()
        build_id = hashlib.sha1(seed + b":NvDraftSnapshotBridge:build").hexdigest()[:24].upper()
        project_text = project_text.replace(
            build_section,
            f"\t\t{build_id} /* NvDraftSnapshotBridge.swift in Sources */ = {{isa = PBXBuildFile; fileRef = {file_id} /* NvDraftSnapshotBridge.swift */; }};\n{build_section}",
            1,
        )
        project_text = project_text.replace(
            reference_section,
            f"\t\t{file_id} /* NvDraftSnapshotBridge.swift */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; name = NvDraftSnapshotBridge.swift; path = {app_dir.name}/NvDraftSnapshotBridge.swift; sourceTree = \"<group>\"; }};\n{reference_section}",
            1,
        )
        patched_group = app_group.replace(
            "children = (\n",
            f"children = (\n\t\t\t\t{file_id} /* NvDraftSnapshotBridge.swift */,\n",
            1,
        )
        project_text = project_text.replace(app_group, patched_group, 1)
        patched_sources = source_block.replace(
            "files = (\n",
            f"files = (\n\t\t\t\t{build_id} /* NvDraftSnapshotBridge.swift in Sources */,\n",
            1,
        )
        project_text = project_text.replace(source_block, patched_sources, 1)
        write_text(project, project_text, target_root, report, "Added React Native iOS draft helper to app target sources")

    write_text(
        helper_path,
        helper_source,
        target_root,
        report,
        "Generated React Native iOS AutoCut draft snapshot helper",
    )
    return True


def supports_react_native_ios_draft_snapshot_api(plugin: Path) -> bool:
    swift_text = "\n".join(read_text(path) for path in plugin.rglob("*.swiftinterface"))
    return all(marker in swift_text for marker in REACT_NATIVE_IOS_DRAFT_SNAPSHOT_API_MARKERS)


def patch_react_native_ios_publish_bridge(
    target_root: Path,
    plugin: Path,
    report: Report,
    source_plugin: Path | None = None,
) -> None:
    bridge = plugin / "ios" / "Classes" / "VideoEditPlugin.m"
    read_bridge = bridge
    if not read_bridge.exists() and report.dry_run and source_plugin is not None:
        source_bridge = source_plugin / "ios" / "Classes" / "VideoEditPlugin.m"
        if source_bridge.exists():
            read_bridge = source_bridge
    if not read_bridge.exists():
        report.add_warning(
            f"React Native iOS bridge was not found at `{bridge}`; the edit-to-publish callback patch was skipped."
        )
        return
    if not is_within(plugin, target_root):
        report.add_next_check(
            f"React Native iOS bridge patch was skipped because the plugin package is outside the target project: `{plugin}`."
        )
        return

    text = read_text(read_bridge)
    original = text
    inspection_plugin = plugin if plugin.exists() else source_plugin
    if inspection_plugin is None or not supports_react_native_ios_draft_snapshot_api(inspection_plugin):
        report.add_warning(
            "React Native iOS SDK does not expose the verified ShortVideo 2.0.2.1 timeline snapshot API shape; no AutoCut draft vendor patch was applied."
        )
        return
    if "NvDraftSnapshotBridge" in text:
        required_existing = (
            "pendingDraftProjectId",
            "pendingDraftStaged",
            "stageProjectWithProjectId",
            "NvShortVideoPendingDraftDefaultsKey",
            "deleteRenderedMediaWithProjectId",
        )
        if not all(marker in text for marker in required_existing):
            report.add_warning(
                f"React Native iOS AutoCut draft patch is only partially present in `{bridge}`; no vendor rewrite was applied."
            )
            return
        if not install_react_native_ios_draft_snapshot_bridge(target_root, report):
            return
        report.add_change("React Native iOS AutoCut draft and edit-to-publish bridge compatibility patch already present.")
        return

    interface_anchor = "#import <NvStreamingSdkCore/NvstreamingSdkCore.h>\n\n@interface VideoEditPlugin()"
    property_anchor = "@property (nonatomic, strong) NvHttpRequestDelegate *requestDelegate;"
    save_draft_method = """    } else if([methodName isEqualToString:SaveDraftMethod]) {
        NSString* infoString = arguments[@"draftInfo"];
        if ([self.moduleManager saveCurrentDraftWithDraftInfo:infoString]) {
            completion(nil, nil);
        } else {
            completion(nil, [NSError errorWithDomain:@"" code:-1 userInfo:@{NSLocalizedDescriptionKey:@"Save draft error"}]);
        }
"""
    exit_method = """    } else if([methodName isEqualToString:ExitVideoEditMethod]) {
        NSString* projectId = arguments[@"projectId"];
        if (projectId) {
            [self.moduleManager exitVideoEdit:projectId];
        }
        completion(nil, nil);
"""
    publish_pattern = re.compile(
        r"- \(void\)publishWithProjectId:\(NSString \*\)projectId .*?\n\}\n\n(?=- \(void\)didCompileFloatProgress:)",
        re.DOTALL,
    )
    missing_shapes = []
    for present, label in (
        (interface_anchor in text, "verified imports/interface"),
        (property_anchor in text, "requestDelegate property"),
        (
            "self.moduleManager.delegate = self;\n        self.moduleManager.compileDelegate = self;\n        [self.moduleManager prepareDownloadFolders];" in text,
            "verified init delegate setup",
        ),
        (save_draft_method in text, "verified SaveDraftMethod branch"),
        (exit_method in text, "verified ExitVideoEditMethod branch"),
        (publish_pattern.search(text) is not None, "verified publish delegate"),
        ("if ([NvModuleManager deleteDraft:projectId])" in text, "verified DeleteDraftMethod branch"),
        ("- (NSArray<NSString *> *)supportedEvents" in text, "supportedEvents"),
        ("- (void)handleMethod:(NSString*)methodName" in text, "handleMethod"),
    ):
        if not present:
            missing_shapes.append(label)
    if missing_shapes:
        report.add_warning(
            "React Native iOS bridge does not match the verified ShortVideo 2.0.2.1 AutoCut draft source shape "
            f"({', '.join(missing_shapes)} missing). No draft persistence patch was applied."
        )
        return
    if not install_react_native_ios_draft_snapshot_bridge(target_root, report):
        return

    snapshot_interface = """#import <NvStreamingSdkCore/NvstreamingSdkCore.h>

static NSString * const NvShortVideoPendingDraftDefaultsKey = @"NvShortVideoPendingDraftProjectId";

@interface NvDraftSnapshotBridge : NSObject
+ (void)startCapture;
+ (void)stopCapture;
+ (nullable NSString *)stageProjectWithProjectId:(NSString *)projectId
                              projectDescription:(NSString *)projectDescription
                                   coverImagePath:(nullable NSString *)coverImagePath
                                        videoPath:(nullable NSString *)videoPath;
+ (void)deleteRenderedMediaWithProjectId:(NSString *)projectId;
@end

@interface VideoEditPlugin()"""
    text = text.replace(interface_anchor, snapshot_interface, 1)
    text = text.replace(
        property_anchor,
        property_anchor
        + "\n@property (nonatomic, copy) NSString *pendingPublishProjectId;"
        + "\n@property (nonatomic, copy) NSString *pendingDraftProjectId;"
        + "\n@property (nonatomic, assign) BOOL pendingPublishHasDraft;"
        + "\n@property (nonatomic, assign) BOOL pendingDraftStaged;"
        + "\n@property (nonatomic, assign) BOOL pendingDraftCommitted;",
        1,
    )

    init_anchor = """        self.moduleManager.delegate = self;
        self.moduleManager.compileDelegate = self;
        [self.moduleManager prepareDownloadFolders];"""
    init_replacement = """        [self bindModuleManagerDelegates];
        [self.moduleManager prepareDownloadFolders];
        NSUserDefaults *defaults = [NSUserDefaults standardUserDefaults];
        NSString *stalePendingDraftId = [defaults stringForKey:NvShortVideoPendingDraftDefaultsKey];
        if (stalePendingDraftId.length > 0) {
            [NvModuleManager deleteDraft:stalePendingDraftId];
            [NvDraftSnapshotBridge deleteRenderedMediaWithProjectId:stalePendingDraftId];
            [defaults removeObjectForKey:NvShortVideoPendingDraftDefaultsKey];
        }"""
    if init_anchor not in text:
        report.add_warning("React Native iOS verified init shape changed; no vendor patch was written.")
        return
    text = text.replace(init_anchor, init_replacement, 1)

    bind_method = """- (void)bindModuleManagerDelegates {
    self.moduleManager.delegate = self;
    self.moduleManager.compileDelegate = self;
}

"""
    text = text.replace("- (NSArray<NSString *> *)supportedEvents", bind_method + "- (NSArray<NSString *> *)supportedEvents", 1)
    handle_signature = """- (void)handleMethod:(NSString*)methodName
           arguments:(NSDictionary*)arguments
          completion:(nullable void (^)(NSObject * _Nullable response, NSError * _Nullable error))completion {
"""
    text = text.replace(handle_signature, handle_signature + "    [self bindModuleManagerDelegates];\n", 1)

    for call in (
        "[self.moduleManager startCaptureWithPresent:",
        "[self.moduleManager startDualCaptureWithPresent:",
        "[self.moduleManager startEditWithPresent:",
        "[self.moduleManager reeditProject:",
    ):
        text = text.replace(call, "[NvDraftSnapshotBridge startCapture];\n        " + call)

    delete_anchor = """            if ([NvModuleManager deleteDraft:projectId]) {
                completion(nil, nil);"""
    text = text.replace(
        delete_anchor,
        """            if ([NvModuleManager deleteDraft:projectId]) {
                [NvDraftSnapshotBridge deleteRenderedMediaWithProjectId:projectId];
                completion(nil, nil);""",
        1,
    )
    exit_replacement = """    } else if([methodName isEqualToString:ExitVideoEditMethod]) {
        NSString* projectId = arguments[@"projectId"];
        if (self.pendingDraftStaged && !self.pendingDraftCommitted && self.pendingDraftProjectId.length > 0) {
            [NvModuleManager deleteDraft:self.pendingDraftProjectId];
            [NvDraftSnapshotBridge deleteRenderedMediaWithProjectId:self.pendingDraftProjectId];
            [[NSUserDefaults standardUserDefaults] removeObjectForKey:NvShortVideoPendingDraftDefaultsKey];
            NSLog(@"[MeisheDraft] discarded staged draftProjectId=%@", self.pendingDraftProjectId);
        }
        if (projectId) {
            [self.moduleManager exitVideoEdit:projectId];
        }
        self.pendingPublishProjectId = nil;
        self.pendingDraftProjectId = nil;
        self.pendingDraftStaged = NO;
        self.pendingDraftCommitted = NO;
        completion(nil, nil);
"""
    text = text.replace(exit_method, exit_replacement, 1)

    save_replacement = """    } else if([methodName isEqualToString:SaveDraftMethod]) {
        NSString* infoString = arguments[@"draftInfo"] ?: @"";
        NSString* draftProjectId = self.pendingDraftProjectId.length > 0
            ? self.pendingDraftProjectId
            : self.moduleManager.projectId;
        if (draftProjectId.length == 0) {
            completion(nil, [NSError errorWithDomain:@"NvShortVideoDraft" code:-1 userInfo:@{NSLocalizedDescriptionKey:@"Save draft error: missing SDK draft projectId"}]);
            return;
        }

        NvEditProjectInfo *savedProject = [NvModuleManager projectInfoForProject:draftProjectId];
        BOOL standardSaved = NO;
        BOOL persisted = self.pendingDraftStaged && savedProject != nil;
        if (!persisted && self.pendingPublishHasDraft) {
            standardSaved = [self.moduleManager saveCurrentDraftWithDraftInfo:infoString];
            savedProject = [NvModuleManager projectInfoForProject:draftProjectId];
            persisted = standardSaved && savedProject != nil;
        }
        BOOL descriptionUpdated = persisted
            ? [NvModuleManager updateProject:draftProjectId description:infoString]
            : NO;
        if (persisted) {
            self.pendingDraftCommitted = YES;
            [[NSUserDefaults standardUserDefaults] removeObjectForKey:NvShortVideoPendingDraftDefaultsKey];
            completion(@{@"projectId": draftProjectId, @"publishTaskId": self.pendingPublishProjectId ?: @""}, nil);
        } else {
            completion(nil, [NSError errorWithDomain:@"NvShortVideoDraft" code:-2 userInfo:@{NSLocalizedDescriptionKey:@"Save draft error: project was not added to the draft list"}]);
        }
"""
    text = text.replace(save_draft_method, save_replacement, 1)

    publish_method = """- (void)publishWithProjectId:(NSString *)projectId coverImagePath:(NSString *)coverImagePath hasDraft:(BOOL)hasDraft videoPath:(NSString *)videoPath description:(NSString *)description videoEdit:(UINavigationController *)videoEditNavigationController {
    self.pendingPublishProjectId = projectId;
    self.pendingDraftProjectId = self.moduleManager.projectId;
    self.pendingPublishHasDraft = hasDraft;
    self.pendingDraftCommitted = NO;
    [NvDraftSnapshotBridge stopCapture];
    if (!hasDraft && self.pendingDraftProjectId.length > 0) {
        NSString *renderedVideoPath = videoPath.length > 0 ? videoPath : self.moduleManager.publishInfo.videoPath;
        NSString *stagedProjectId = [NvDraftSnapshotBridge stageProjectWithProjectId:self.pendingDraftProjectId
                                                                  projectDescription:description ?: @""
                                                                       coverImagePath:coverImagePath
                                                                            videoPath:renderedVideoPath];
        self.pendingDraftProjectId = stagedProjectId;
        self.pendingDraftStaged = stagedProjectId.length > 0;
    } else {
        self.pendingDraftStaged = NO;
    }
    if (self.pendingDraftStaged) {
        [[NSUserDefaults standardUserDefaults] setObject:self.pendingDraftProjectId forKey:NvShortVideoPendingDraftDefaultsKey];
    } else {
        [[NSUserDefaults standardUserDefaults] removeObjectForKey:NvShortVideoPendingDraftDefaultsKey];
    }

    NSDictionary *eventBody = @{
        @"method": VideoEditResultEvent,
        @"arguments": @{
            @"coverImagePath": coverImagePath ?: @"",
            @"hasDraft": @(hasDraft),
            @"draftInfo": description ?: @"",
            @"projectId": projectId,
            @"videoPath": videoPath ?: @""
        }
    };
    [self sendEventWithName:VideoEditMethodChannel body:eventBody];

    if (videoEditNavigationController.presentingViewController.presentingViewController) {
        UIViewController* presentingVc = [NvSPUtils keyWindow].rootViewController;
        [presentingVc dismissViewControllerAnimated:YES completion:nil];
    } else {
        [videoEditNavigationController dismissViewControllerAnimated:YES completion:nil];
    }
}

"""
    text, publish_count = publish_pattern.subn(publish_method, text, count=1)
    if publish_count != 1:
        report.add_warning("React Native iOS publish callback changed during patching; no vendor patch was written.")
        return

    required_markers = (
        "[self bindModuleManagerDelegates];",
        "self.pendingDraftProjectId = self.moduleManager.projectId;",
        "stageProjectWithProjectId:self.pendingDraftProjectId",
        "self.pendingDraftCommitted = YES;",
        "deleteRenderedMediaWithProjectId",
        "[self sendEventWithName:VideoEditMethodChannel body:eventBody];",
    )
    if not all(marker in text for marker in required_markers):
        report.add_warning(f"React Native iOS bridge compatibility patch is incomplete in `{bridge}`; no partial vendor rewrite was written.")
        return
    if text == original and bridge.exists():
        report.add_change("React Native iOS AutoCut draft and edit-to-publish bridge compatibility patch already present.")
        return
    write_text(
        bridge,
        text,
        target_root,
        report,
        "Patched verified React Native iOS AutoCut draft lifecycle and publish callback ordering",
    )


def patch_react_native_ios_podfile_compatibility(target_root: Path, report: Report) -> None:
    ios_root = ios_project_root(target_root)
    podfile = ios_root / "Podfile" if ios_root else None
    if podfile is None or not podfile.exists():
        return

    text = read_text(podfile)
    marker = "fmt 11.0.2's consteval parser is rejected by the Xcode 26 compiler."
    if marker in text and "post_integrate do |installer|" in text:
        report.add_change("React Native iOS Xcode 26 fmt compatibility patch already present in Podfile.")
        return

    post_install_pattern = re.compile(
        r"(    react_native_post_install\(\n.*?\n    \)\n)(  end\nend\n)",
        re.DOTALL,
    )
    fmt_settings = """

    # fmt 11.0.2's consteval parser is rejected by the Xcode 26 compiler.
    installer.pods_project.targets.each do |pod_target|
      next unless pod_target.name == 'fmt'

      pod_target.build_configurations.each do |build_config|
        definitions = build_config.build_settings['GCC_PREPROCESSOR_DEFINITIONS'] || ['$(inherited)']
        definitions = [definitions] unless definitions.is_a?(Array)
        definitions << 'FMT_USE_CONSTEVAL=0' unless definitions.include?('FMT_USE_CONSTEVAL=0')
        build_config.build_settings['GCC_PREPROCESSOR_DEFINITIONS'] = definitions
      end
    end
"""
    text, count = post_install_pattern.subn(
        lambda match: match.group(1) + fmt_settings + match.group(2),
        text,
        count=1,
    )
    if count != 1:
        report.add_warning(
            f"React Native iOS Podfile shape was not recognized at `{podfile}`; Xcode 26 fmt compatibility was not inserted."
        )
        return

    post_integrate = """

post_integrate do |installer|
  fmt_base = File.join(installer.sandbox.root.to_s, 'fmt/include/fmt/base.h')
  next unless File.exist?(fmt_base)

  source = File.read(fmt_base)
  detection = '// Detect consteval, C++20 constexpr extensions and std::is_constant_evaluated.'
  unless source.include?("#if !defined(FMT_USE_CONSTEVAL)\\n#{detection}")
    source.sub!(detection, "#if !defined(FMT_USE_CONSTEVAL)\\n#{detection}")
    source.sub!("#endif\\n#if FMT_USE_CONSTEVAL\\n", "#endif\\n#endif\\n#if FMT_USE_CONSTEVAL\\n")
    File.chmod(0644, fmt_base)
    File.write(fmt_base, source)
  end
end
"""
    text = text.rstrip() + post_integrate
    write_text(
        podfile,
        text,
        target_root,
        report,
        "Patched React Native iOS Podfile for RN 0.78 fmt compatibility with Xcode 26",
    )


def apply_verified_react_native_version_patches(target_root: Path, report: Report) -> None:
    react_native_version = package_dependency_version(target_root, "react-native")
    xcode_version = installed_xcode_version()
    xcode_label = ".".join(str(part) for part in xcode_version) if xcode_version else "unavailable"

    if react_native_version and re.match(r"^[~^]?0\.78(?:\.|$)", react_native_version) and xcode_version and xcode_version[0] == 26:
        report.add_input(
            f"Verified compatibility patch matched: React Native `{react_native_version}` with Xcode `{xcode_label}`."
        )
        patch_react_native_ios_podfile_compatibility(target_root, report)
        return

    if react_native_version and re.match(r"^[~^]?0\.78(?:\.|$)", react_native_version) and xcode_version is None:
        report.add_toolchain_warning(
            "React Native 0.78.x detected, but Xcode is unavailable (for example on Windows). The verified Xcode 26/fmt 11.0.2 patch was not applied. Re-run the skill on the Mac that will build the app, then follow the report's dependency-installation choice."
        )
        return

    report.add_toolchain_warning(
        f"No automatic fmt patch was applied for React Native `{react_native_version or 'unknown'}` with Xcode `{xcode_label}`. The skill only verifies this patch for React Native 0.78.x + Xcode 26.x; diagnose other combinations from their actual build error before patching."
    )


def generate_react_native_feature_config(target_root: Path, suffix: str, report: Report) -> Path:
    path = target_root / "src" / f"meisheFeatureConfig.{suffix}"
    if path.exists():
        report.add_change(f"Retained user-editable React Native feature configuration: `{rel(path, target_root)}`")
        return path

    signature = "(config: NvVideoConfig): NvVideoConfig" if suffix == "ts" else "(config)"
    array_signature = "(name: string, items: unknown[])" if suffix == "ts" else "(name, items)"
    watermark_signature = "(name: string, watermark: unknown)" if suffix == "ts" else "(name, watermark)"
    watermark_cast = "const value = watermark as { watermark?: unknown; nvImageConfig?: unknown; width?: number; height?: number; offsetX?: number; offsetY?: number; position?: unknown };" if suffix == "ts" else "const value = watermark;"
    content = r"""import {
  NvCaptureBottomMenuItem,
  NvCaptureMenuItem,
  NvDualConfig,
  NvDualType,
  NvEditMenuItem,
  NvEditMode,
  NvEditModeSource,
  NvExportImageType,
  NvImageCaptionStyle,
  NvsCompileVideoBitrateGrade,
  NvTimePair,
  NvVideoCompileResolution,
  NvVideoConfig,
  NvVideoPreviewResolution,
} from 'react-native-nvshortvideo';

// React Native 专属配置。只修改本文件，不要到 ios/ 或 android/ 中重复配置功能菜单。
// SDK 根据菜单数组动态创建控件：删除数组项会同时删除入口并重排其余 UI，不要用 null、空字符串或隐藏样式占位。
export function applyMeisheFeatureConfig__SIGNATURE__ {
  // 全局颜色使用 #RRGGBB；shadowColor 使用 #RRGGBBAA。
  config.primaryColor = '#FC3E5A';
  config.backgroundColor = '#000000';
  config.panelBackgroundColor = '#1C1C1C';
  config.textColor = '#FFFFFF';
  config.secondaryTextColor = '#6C6C77';
  // 是否在音乐页面显示设备本地音乐入口；读取本地音乐仍受系统权限约束。
  config.enableLocalMusic = true;
  // 文字阴影偏移和颜色。width/height 分别为横向/纵向偏移。
  config.shadowOffset = { width: 0, height: 0.5 };
  config.shadowColor = '#00000080';

  // 相册顶部标签：0=全部，1=视频，2=图片。
  config.albumConfig.type = 0;
  // 相册最大选择数，必须大于 0；模板自身还受 templateConfig.maxSelectCount 限制。
  config.albumConfig.maxSelectCount = 50;
  // 编辑素材选择页是否显示一键成片；不会自动删除拍摄页模板模式。
  config.albumConfig.useAutoCut = true;

  // 一键成片/自适应模板最大可选片段数，必须大于 0。
  config.templateConfig.maxSelectCount = 50;
  // 模板页面是否显示一键成片。
  config.templateConfig.useAutoCut = true;
  // 一键成片推荐模板最大数量，必须大于 0。
  config.templateConfig.maxRecommandTemplateCount = 20;

  // 拍摄右侧菜单，有序。删除 speed 可去掉快慢速，删除 matting 可去掉抠像；其余入口自动上移。
  config.captureConfig.captureMenuItems = [
    NvCaptureMenuItem.device,
    NvCaptureMenuItem.speed,
    NvCaptureMenuItem.timer,
    NvCaptureMenuItem.beauty,
    NvCaptureMenuItem.makeup,
    NvCaptureMenuItem.prop,
    NvCaptureMenuItem.matting,
    NvCaptureMenuItem.flashlight,
    NvCaptureMenuItem.filter,
    NvCaptureMenuItem.original,
  ];
  // 拍摄底部模式，有序且不能为空；template 存在时必须放在最后。
  config.captureConfig.captureBottomMenuItems = [
    NvCaptureBottomMenuItem.image,
    NvCaptureBottomMenuItem.video,
    NvCaptureBottomMenuItem.smart,
    NvCaptureBottomMenuItem.template,
  ];
  // 默认拍摄模式必须同时存在于 captureBottomMenuItems。
  config.captureConfig.defaultBottomMenuSelectItem = NvCaptureBottomMenuItem.video;
  // 默认摄像头：0=后置，1=前置。
  config.captureConfig.captureDeviceIndex = 1;
  // 拍摄预览分辨率只支持 720/1080。
  config.captureConfig.resolution = NvVideoPreviewResolution.NvVideoPreviewResolution_1080;
  // 是否忽略设备旋转信息。
  config.captureConfig.ignoreVideoRotation = true;
  // 照片进入编辑后的默认时长，单位毫秒，必须大于 0。
  config.captureConfig.imageDuration = 3000;
  // 拍照完成、进入编辑前是否把原图保存到系统相册。
  config.captureConfig.autoSavePhotograph = false;
  // 普通录制档位，单位毫秒；每组必须满足 0 <= minDuration < maxDuration。
  config.captureConfig.timeRanges = [
    new NvTimePair(3000, 15000),
    new NvTimePair(3000, 60000),
  ];
  // 快拍时长范围，单位毫秒。
  config.captureConfig.smartTimeRange = new NvTimePair(0, 15000);
  // 滤镜默认强度，官方配置范围为 0.0-1.0。
  config.captureConfig.filterDefaultValue = 0.8;
  // 是否在拍摄页显示相册快捷入口。
  config.captureConfig.enableCaptureAlbum = false;
  // true 会在进入拍摄时自动关闭原声/麦克风。
  config.captureConfig.autoDisablesMic = false;
  // 拍摄帧率；已验证配置为 30，修改前需确认目标设备和原生桥接支持范围。
  config.captureConfig.fps = 30;
  // recordConfiguration 可设置 bitrate、gopsize、video encoder name；键和值必须遵循美摄底层录制 API。
  // config.captureConfig.recordConfiguration = new Map([['video encoder name', 'hevc'], ['gopsize', 30]]);

  // 合拍右侧菜单独立于普通拍摄菜单，有序；删除项后合拍页面同步重排。
  config.captureConfig.dualMenuItems = [
    NvCaptureMenuItem.device,
    NvCaptureMenuItem.speed,
    NvCaptureMenuItem.timer,
    NvCaptureMenuItem.beauty,
    NvCaptureMenuItem.makeup,
    NvCaptureMenuItem.prop,
    NvCaptureMenuItem.matting,
    NvCaptureMenuItem.flashlight,
    NvCaptureMenuItem.filter,
    NvCaptureMenuItem.original,
    NvCaptureMenuItem.dualtype,
  ];
  const dual = new NvDualConfig();
  // 小窗左/上边距与底图宽/高的比例，建议保持在 0.0-1.0。
  dual.left = 17.0 / 375.0;
  dual.top = 18.0 / 666.67;
  // 小窗短边与底图宽度比例，必须大于 0 且不宜超过 1。
  dual.limitWidth = 153.5 / 375.0;
  // 默认合拍样式必须存在于 supportedTypes。
  dual.defaultType = NvDualType.leftRight;
  // 可选样式集合：左右、上下、左矩形、左圆、上圆。
  dual.supportedTypes = [NvDualType.leftRight, NvDualType.topDown, NvDualType.leftRect, NvDualType.leftCircle, NvDualType.topCircle];
  // 是否自动禁用麦克风；muteOriginal 控制是否默认关闭原视频声音。
  dual.autoDisablesMic = false;
  dual.muteOriginal = true;
  config.captureConfig.dualConfig = dual;

  // 编辑右侧菜单，有序。删除 text 会删除文字入口及其下级功能，后续入口自动上移，不留空白。
  // release/download 关系到发布/保存入口，删除前必须确认仍有可达的发布与导出流程。
  config.editConfig.editMenuItems = [
    NvEditMenuItem.release,
    NvEditMenuItem.download,
    NvEditMenuItem.edit,
    NvEditMenuItem.text,
    NvEditMenuItem.sticker,
    NvEditMenuItem.effect,
    NvEditMenuItem.filter,
    NvEditMenuItem.caption,
    NvEditMenuItem.audio,
    NvEditMenuItem.record,
  ];
  // 编辑预览分辨率、帧率；预览配置不等于最终导出配置。
  config.editConfig.resolution = NvVideoPreviewResolution.NvVideoPreviewResolution_1080;
  config.editConfig.fps = 25;
  // 特效、录音最小时长以及图片默认时长，单位毫秒，均不得为负数。
  config.editConfig.minEffectDuration = 500;
  config.editConfig.minAudioDuration = 500;
  config.editConfig.defaultImageDuration = 4000;
  // 字幕默认颜色与可选颜色，格式为 #RRGGBB。
  config.editConfig.captionColor = '#FFFFFF';
  config.editConfig.captionColorList = ['#FFFFFF', '#000000', '#0099F6', '#50C23B', '#FFC840', '#FF8500', '#FF3350', '#E40069', '#B200C0', '#F8808A', '#FEBF7C', '#262626', '#363636', '#555555', '#737373', '#989898', '#B2B2B2', '#C7C7C7', '#DBDBDB', '#F0F0F0'];
  // 字幕样式集合：无、背景、半透明背景、描边。
  config.editConfig.supportedCaptionStyles = [NvImageCaptionStyle.none, NvImageCaptionStyle.bg, NvImageCaptionStyle.bgAlpha, NvImageCaptionStyle.outline];
  // firstAsset 按首个素材决定画幅；fixed 使用 editMode。
  config.editConfig.editModeSource = NvEditModeSource.firstAsset;
  config.editConfig.editMode = NvEditMode.NvEditMode9v16;
  // 用户可选画幅列表；fixed 的 editMode 必须包含在此列表中。
  config.editConfig.supportedEditModes = [NvEditMode.NvEditMode9v16, NvEditMode.NvEditMode16v9, NvEditMode.NvEditMode3v4, NvEditMode.NvEditMode4v3, NvEditMode.NvEditMode1v1, NvEditMode.NvEditMode18v9, NvEditMode.NvEditMode9v18, NvEditMode.NvEditMode8v9, NvEditMode.NvEditMode9v8];
  // 编辑滤镜默认强度 0.0-1.0；最大音量稳定范围为 (0,8]，0 会在调用 SDK 前被拒绝。
  config.editConfig.filterDefaultValue = 0.8;
  config.editConfig.maxVolume = 4;
  // true 会移除反复、慢动作时间特效能力。
  config.editConfig.disableTimeEffect = false;

  // 导出分辨率支持 720/1080/4K；4K 必须经过设备内存和性能验证。
  config.compileConfig.resolution = NvVideoCompileResolution.NvVideoCompileResolution_1080;
  config.compileConfig.fps = 25;
  // bitrate != -1 时优先使用精确码率；-1 时使用 bitrateGrade。
  config.compileConfig.bitrateGrade = NvsCompileVideoBitrateGrade.NvsCompileBitrateGradeHigh;
  config.compileConfig.bitrate = -1;
  // 封面图片格式以及导出后是否保存到系统相册。
  config.compileConfig.imageType = NvExportImageType.NvExportImageTypePNG;
  config.compileConfig.autoSaveVideo = true;
  // watermarkConfig/coverWatermarkConfig 默认不设置。启用前必须使用真实图片、正数宽高、非负偏移和合法位置。
  // 生成资源：src/assets/meishe_feature_watermark.png、Android drawable-nodpi、iOS Asset Catalog 中同名 imageset。
  // configure 可设置底层合成键值；未知键禁止写入，bitrate/fps 冲突时以上显式字段优先。

  // modelConfig 的路径必须指向与当前 SDK 匹配的真实模型文件。不要伪造或跨版本复制模型。
  // 可配置字段：use240、fakeface、face、face240、avatar、hand、humanseg、skysegment、eyecontour、
  // advancedbeauty、facecommon、autoCutActivity、autoCutFaceAttri、autoCutFace、autoCutImagecls、autoCutPf、autoCutPhoto。

  validateMeisheFeatureConfig(config);
  return config;
}

function assertUnique__ARRAY_SIGNATURE__ {
  if (new Set(items).size !== items.length) {
    throw new Error(`${name} contains duplicate menu items`);
  }
}

function validateWatermarkConfig__WATERMARK_SIGNATURE__ {
  if (watermark == null) {
    return;
  }
  __WATERMARK_CAST__
  if (value.watermark == null && value.nvImageConfig == null) {
    // NvCompileConfig creates empty watermark objects by default. The image
    // reference enables watermarking; no image means the feature is disabled.
    return;
  }
  if (!Number.isFinite(Number(value.width)) || !Number.isFinite(Number(value.height)) || Number(value.width) <= 0 || Number(value.height) <= 0) {
    throw new Error(`${name} width and height must be greater than 0`);
  }
  if (!Number.isFinite(Number(value.offsetX)) || !Number.isFinite(Number(value.offsetY)) || Number(value.offsetX) < 0 || Number(value.offsetY) < 0) {
    throw new Error(`${name} offsets must be non-negative`);
  }
  if (value.position == null) {
    throw new Error(`${name} position is required`);
  }
}

export function validateMeisheFeatureConfig__SIGNATURE__ {
  const bottom = config.captureConfig.captureBottomMenuItems;
  if (bottom.length === 0) {
    throw new Error('captureBottomMenuItems must contain at least one capture mode');
  }
  if (!bottom.includes(config.captureConfig.defaultBottomMenuSelectItem)) {
    throw new Error('defaultBottomMenuSelectItem must exist in captureBottomMenuItems');
  }
  const templateIndex = bottom.indexOf(NvCaptureBottomMenuItem.template);
  if (templateIndex >= 0 && templateIndex !== bottom.length - 1) {
    throw new Error('NvCaptureBottomMenuItem.template must be the last bottom menu item');
  }
  assertUnique('captureMenuItems', config.captureConfig.captureMenuItems);
  assertUnique('captureBottomMenuItems', bottom);
  assertUnique('dualMenuItems', config.captureConfig.dualMenuItems);
  assertUnique('editMenuItems', config.editConfig.editMenuItems);
  if (config.albumConfig.maxSelectCount <= 0 || config.templateConfig.maxSelectCount <= 0) {
    throw new Error('album/template maxSelectCount must be greater than 0');
  }
  if (config.editConfig.maxVolume <= 0 || config.editConfig.maxVolume > 8) {
    throw new Error('editConfig.maxVolume must be greater than 0 and no greater than 8');
  }
  validateWatermarkConfig('compileConfig.watermarkConfig', config.compileConfig.watermarkConfig);
  validateWatermarkConfig('compileConfig.coverWatermarkConfig', config.compileConfig.coverWatermarkConfig);
  return config;
}
"""
    content = (
        content.replace("__SIGNATURE__", signature)
        .replace("__ARRAY_SIGNATURE__", array_signature)
        .replace("__WATERMARK_SIGNATURE__", watermark_signature)
        .replace("__WATERMARK_CAST__", watermark_cast)
    )
    write_text(path, content, target_root, report, "Generated user-editable React Native feature configuration")
    report.add_user_configuration(
        f"React Native feature entry: edit `{rel(path, target_root)}`. Menu arrays are ordered and drive SDK UI reflow; the skill preserves this file on later runs."
    )
    return path


def generate_react_native_wrapper(target_root: Path, report: Report) -> str:
    src_dir = target_root / "src"
    use_ts = (target_root / "tsconfig.json").exists() or (src_dir.exists() and any(src_dir.glob("*.ts")))
    suffix = "ts" if use_ts else "js"
    generate_react_native_feature_config(target_root, suffix, report)
    config_lines = []
    for key, value in REACT_NATIVE_DEMO_SERVER_CONFIG.items():
        literal = repr(value) if isinstance(value, str) else json.dumps(value)
        config_lines.append(f"  {key}: {literal},")
    config = "{\n" + "\n".join(config_lines) + "\n}"
    type_ann = ": any" if use_ts else ""
    event_ann = ": any" if use_ts else ""
    publish_handler_ann = ": (info: any) => void" if use_ts else ""
    content = f"""import {{ DeviceEventEmitter, NativeEventEmitter, NativeModules, Platform }} from 'react-native';
import {{ NvShortVideo, NvVideoConfig }} from 'react-native-nvshortvideo';
import {{ applyMeisheFeatureConfig }} from './meisheFeatureConfig';

export {{ NvCaptureBottomMenuItem, NvVideoCompileEvent, NvVideoConfig, NvVideoEditEvent }} from 'react-native-nvshortvideo';

export const meisheServerConfig = {config};

export function createMeisheVideoConfig(){': NvVideoConfig' if use_ts else ''} {{
  const config = new NvVideoConfig();
  return applyMeisheFeatureConfig(config);
}}

function operator(){type_ann} {{
  return NvShortVideo.shareInstance();
}}

const nativeVideoEditModule = NativeModules.VideoEditPlugin;
const videoEditEmitter = Platform.OS === 'ios' && nativeVideoEditModule
  ? new NativeEventEmitter(nativeVideoEditModule)
  : DeviceEventEmitter;
let iosCompileSubscription{': { remove: () => void } | null' if use_ts else ''} = null;

function callFirst(names{': string[]' if use_ts else ''}, ...args{': any[]' if use_ts else ''}){type_ann} {{
  const op = operator();
  for (const name of names) {{
    if (typeof op[name] === 'function') {{
      return Promise.resolve(op[name](...args));
    }}
  }}
  throw new Error(`react-native-nvshortvideo does not expose ${{names.join(' or ')}}`);
}}

function configureServer(config{': Record<string, unknown>' if use_ts else ''}){': Promise<unknown>' if use_ts else ''} {{
  if (Platform.OS === 'ios' && typeof nativeVideoEditModule?.sendMessageToNative === 'function') {{
    return nativeVideoEditModule.sendMessageToNative({{
      method: 'ConfigServerInfo',
      arguments: config,
    }});
  }}
  return callFirst(['configServerInfo'], config);
}}

function compactServerConfig(config{': Record<string, unknown>' if use_ts else ''}){': Record<string, unknown>' if use_ts else ''} {{
  return Object.fromEntries(
    Object.entries(config).filter(([, value]) => value !== undefined && value !== null && value !== ''),
  );
}}

export const MeisheShortVideoDocking = {{
  configureServer(overrides = {{}}) {{
    return configureServer(compactServerConfig({{ ...meisheServerConfig, ...overrides }}));
  }},

  downloadPrefabricatedMaterial() {{
    return callFirst(['downloadPrefabricatedMaterial']);
  }},

  startVideoCapture(config = createMeisheVideoConfig(), musicInfo = undefined) {{
    return callFirst(['startVideoCaptrue', 'startVideoCapture'], config, musicInfo);
  }},

  startVideoDualCapture(config = createMeisheVideoConfig()) {{
    return callFirst(['startVideoDualCaptrue', 'startVideoDualCapture'], config);
  }},

  startVideoDualCaptureWithVideo(videoPath{': string' if use_ts else ''}, config = createMeisheVideoConfig()) {{
    return callFirst(['startVideoDualCaptrueWithVideo', 'startVideoDualCaptureWithVideo'], videoPath, config);
  }},

  startSelectFilesForEdit(config = createMeisheVideoConfig()) {{
    return callFirst(['startSeleteFilesForEdit', 'startSelectFilesForEdit'], config);
  }},

  getDraftList() {{
    return callFirst(['getDraftList']);
  }},

  reeditDraft(projectId{': string' if use_ts else ''}, config = createMeisheVideoConfig()) {{
    return callFirst(['reeditDraft'], projectId, config);
  }},

  deleteDraft(projectId{': string' if use_ts else ''}) {{
    return callFirst(['deleteDraft'], projectId);
  }},

  saveDraft(info{': string' if use_ts else ''}) {{
    return callFirst(['saveDraft'], info);
  }},

  compileCurrentTimeline(configure = {{}}) {{
    return callFirst(['compileCurrentTimeline'], configure);
  }},

  getPublishInfo() {{
    return callFirst(['getPublishInfo']);
  }},

  exitEdit(projectId{': string' if use_ts else ''}) {{
    return callFirst(['exitEdit'], projectId);
  }},

  setVideoEditEventHandler(handler{': ((event: any, info: any) => void) | undefined | null' if use_ts else ''}) {{
    return callFirst(['setVideoEditEventHandler'], handler ?? undefined);
  }},

  subscribeToPublish(handler{publish_handler_ann}) {{
    return videoEditEmitter.addListener('VideoEditMethodChannel', (body{event_ann}) => {{
      if (body?.method === 'VideoEditResultEvent') {{
        handler(body.arguments || {{}});
      }}
    }});
  }},

  setDraftUpdateHandler(handler{': (() => void) | undefined | null' if use_ts else ''}) {{
    return callFirst(['setDraftUpdateHandler'], handler ?? undefined);
  }},

  setVideoCompileEventHandler(handler{': ((event: any, info: any) => void) | undefined | null' if use_ts else ''}) {{
    if (Platform.OS === 'ios') {{
      iosCompileSubscription?.remove();
      iosCompileSubscription = null;
      if (handler) {{
        iosCompileSubscription = videoEditEmitter.addListener('VideoEditCallbackMethodChannel', (body{event_ann}) => {{
          const info = body?.arguments || {{}};
          if (body?.method === 'DidCompileProgressMethod') {{
            handler(NvVideoCompileEvent.progress, info);
          }} else if (body?.method === 'DidCompileCompletedMethod') {{
            handler(NvVideoCompileEvent.complete, info);
          }} else if (body?.method === 'DidCoverImageChangedMethod') {{
            handler(NvVideoCompileEvent.coverImageSelected, info);
          }}
        }});
      }}
      return Promise.resolve();
    }}
    return callFirst(['setVideoCompileEventHandler'], handler ?? undefined);
  }},
}};
"""
    write_text(target_root / "src" / f"meisheShortVideoDocking.{suffix}", content, target_root, report, "Generated React Native docking wrapper")
    report.add_user_configuration(
        f"React Native customer server: pass only real non-empty `clientId`, `clientSecret`, and `assemblyId` values through `MeisheShortVideoDocking.configureServer(overrides)` in `src/meisheShortVideoDocking.{suffix}`. Empty values are removed before the native bridge call."
    )
    return suffix


def generate_react_native_demo(target_root: Path, suffix: str, report: Report) -> None:
    use_ts = suffix == "ts"
    demo_suffix = "tsx" if use_ts else "jsx"
    error_expr = "error instanceof Error ? error.message : String(error)" if use_ts else "String(error)"
    screen_type = "type Screen = 'home' | 'publish' | 'drafts';\ntype MaterialState = 'preparing' | 'ready' | 'failed';\n\n" if use_ts else ""
    screen_state = "useState<Screen>('home')" if use_ts else "useState('home')"
    project_state = "useState<any>(null)" if use_ts else "useState(null)"
    material_state = "useState<MaterialState>('preparing')" if use_ts else "useState('preparing')"
    prepare_error_state = "useState<string | undefined>(undefined)" if use_ts else "useState(undefined)"
    prepare_promise_ref = "useRef<Promise<void> | null>(null)" if use_ts else "useRef(null)"
    material_ready_ref = "useRef<boolean>(false)" if use_ts else "useRef(false)"
    feature_props = "type FeatureRowProps = { icon: any; label: string; onPress: () => void };\n\n" if use_ts else ""
    feature_props_ann = ": FeatureRowProps" if use_ts else ""
    content = f"""import React, {{ useEffect, useMemo, useRef, useState }} from 'react';
import {{ ActivityIndicator, AppState, Image, InteractionManager, Platform, Pressable, SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, useWindowDimensions, View }} from 'react-native';

import {{ createMeisheVideoConfig, MeisheShortVideoDocking }} from './meisheShortVideoDocking';
import {{ MeisheShortVideoDrafts }} from './MeisheShortVideoDrafts';
import {{ MeisheShortVideoPublish }} from './MeisheShortVideoPublish';

{screen_type}export function MeisheShortVideoDemo() {{
  const videoConfig = useMemo(() => createMeisheVideoConfig(), []);
  const [screen, setScreen] = {screen_state};
  const [projectInfo, setProjectInfo] = {project_state};
  const [materialState, setMaterialState] = {material_state};
  const [prepareError, setPrepareError] = {prepare_error_state};
  const preparePromise = {prepare_promise_ref};
  const materialReady = {material_ready_ref};
  const {{ height: screenHeight }} = useWindowDimensions();
  const topPadding = Math.max(24, Math.min(34, screenHeight * 0.038));
  const bottomPadding = Math.max(48, Math.min(70, screenHeight * 0.075));
  const titleSize = Math.max(28, Math.min(32, screenHeight * 0.036));
  const bannerTopGap = Math.max(10, Math.min(14, screenHeight * 0.015));
  const bannerHeight = Math.max(108, Math.min(148, screenHeight * 0.18));
  const panelTopGap = Math.max(16, Math.min(22, screenHeight * 0.026));
  const panelTopPadding = Math.max(18, Math.min(24, screenHeight * 0.026));

  useEffect(() => {{
    const initialPreparation = InteractionManager.runAfterInteractions(() => {{
      prepareMaterials().catch(() => undefined);
    }});
    const appStateSubscription = AppState.addEventListener('change', state => {{
      if (state === 'active' && !materialReady.current) {{
        prepareMaterials().catch(() => undefined);
      }}
    }});
    const publishSubscription = MeisheShortVideoDocking.subscribeToPublish((info{': any' if use_ts else ''}) => {{
      setProjectInfo(info || {{}});
      setScreen('publish');
    }});
    return () => {{
      initialPreparation.cancel();
      appStateSubscription.remove();
      publishSubscription.remove();
    }};
  }}, []);

  function prepareMaterials(){': Promise<void>' if use_ts else ''} {{
    if (materialReady.current) {{
      return Promise.resolve();
    }}
    if (preparePromise.current) {{
      return preparePromise.current;
    }}

    setMaterialState('preparing');
    setPrepareError(undefined);
    const task = (async () => {{
      try {{
        await MeisheShortVideoDocking.configureServer();
        const completed = await MeisheShortVideoDocking.downloadPrefabricatedMaterial();
        if (completed !== true) {{
          throw new Error('SDK 预制素材下载未完成');
        }}
        materialReady.current = true;
        setMaterialState('ready');
      }} catch (error) {{
        materialReady.current = false;
        setMaterialState('failed');
        setPrepareError({error_expr});
      }} finally {{
        preparePromise.current = null;
      }}
    }})();
    preparePromise.current = task;
    return task;
  }}

  function observeFeatureMaterialRefresh(task{': Promise<unknown>' if use_ts else ''}) {{
    setMaterialState('preparing');
    setPrepareError(undefined);
    task.then(completed => {{
      if (completed === true) {{
        materialReady.current = true;
        setMaterialState('ready');
        return;
      }}
      materialReady.current = false;
      setMaterialState('failed');
      setPrepareError('SDK 预制素材下载未完成');
    }}).catch(error => {{
      materialReady.current = false;
      setMaterialState('failed');
      setPrepareError({error_expr});
    }});
  }}

  async function runFeature(action{': () => Promise<unknown> | unknown' if use_ts else ''}, refreshMaterials = false) {{
    if (refreshMaterials && Platform.OS === 'ios') {{
      try {{
        await MeisheShortVideoDocking.configureServer();
        observeFeatureMaterialRefresh(MeisheShortVideoDocking.downloadPrefabricatedMaterial());
      }} catch (error) {{
        materialReady.current = false;
        setMaterialState('failed');
        setPrepareError({error_expr});
      }}
    }}
    try {{
      await action();
    }} catch (error) {{
      setPrepareError({error_expr});
    }}
  }}

  if (screen === 'publish') {{
    return (
      <MeisheShortVideoPublish
        projectInfo={{projectInfo || {{}}}}
        onBack={{() => setScreen('home')}}
      />
    );
  }}

  if (screen === 'drafts') {{
    return (
      <MeisheShortVideoDrafts
        videoConfig={{videoConfig}}
        onBack={{() => setScreen('home')}}
      />
    );
  }}

  return (
    <SafeAreaView style={{styles.safeArea}}>
      <StatusBar barStyle="light-content" backgroundColor="#171D26" />
      <ScrollView contentContainerStyle={{[styles.container, {{ paddingTop: topPadding, paddingBottom: bottomPadding }}]}} showsVerticalScrollIndicator={{false}}>
        <Text style={{[styles.title, {{ fontSize: titleSize }}]}}>素材上新</Text>
        <Image source={{require('./assets/meishe_home_banner.jpg')}} style={{[styles.banner, {{ height: bannerHeight, marginTop: bannerTopGap }}]}} resizeMode="cover" />
        <View style={{[styles.panel, {{ marginTop: panelTopGap, paddingTop: panelTopPadding }}]}}>
          <Text style={{styles.panelHint}}>请选择所需的功能</Text>
          <Text style={{styles.panelTitle}}>功能列表</Text>
          <View style={{styles.actionList}}>
            <FeatureRow icon={{require('./assets/meishe_icon_capture.png')}} label="拍摄" onPress={{() => runFeature(() => MeisheShortVideoDocking.startVideoCapture(videoConfig), true)}} />
            <FeatureRow icon={{require('./assets/meishe_icon_dual_capture.png')}} label="合拍" onPress={{() => runFeature(() => MeisheShortVideoDocking.startVideoDualCapture(videoConfig), true)}} />
            <FeatureRow icon={{require('./assets/meishe_icon_edit.png')}} label="编辑" onPress={{() => runFeature(() => MeisheShortVideoDocking.startSelectFilesForEdit(videoConfig), true)}} />
            <FeatureRow icon={{require('./assets/meishe_icon_draft.png')}} label="草稿" onPress={{() => setScreen('drafts')}} />
          </View>
        </View>
        {{materialState !== 'ready' ? (
          <Pressable style={{styles.materialStatus}} onPress={{() => {{ prepareMaterials().catch(() => undefined); }}}}>
            {{materialState === 'preparing' ? <ActivityIndicator color="#AEB5C0" size="small" /> : null}}
            <Text style={{styles.materialStatusText}} numberOfLines={{2}}>
              {{materialState === 'preparing' ? '素材正在后台准备' : `素材准备未完成，点击重试${{prepareError ? `：${{prepareError}}` : ''}}`}}
            </Text>
          </Pressable>
        ) : null}}
      </ScrollView>
    </SafeAreaView>
  );
}}

{feature_props}function FeatureRow({{ icon, label, onPress }}{feature_props_ann}) {{
  return (
    <Pressable style={{styles.actionRow}} onPress={{onPress}}>
      <Image source={{icon}} style={{styles.actionIcon}} resizeMode="contain" />
      <Text style={{styles.actionText}}>{{label}}</Text>
      <Text style={{styles.chevron}}>›</Text>
    </Pressable>
  );
}}

const styles = StyleSheet.create({{
  safeArea: {{
    flex: 1,
    backgroundColor: '#171D26',
  }},
  container: {{
    paddingHorizontal: 24,
  }},
  title: {{
    color: '#ffffff',
    fontWeight: '800',
  }},
  banner: {{
    width: '100%',
    borderRadius: 12,
    overflow: 'hidden',
  }},
  panel: {{
    borderRadius: 14,
    backgroundColor: '#222832',
    paddingHorizontal: 20,
    paddingBottom: 16,
  }},
  panelHint: {{
    color: '#ffffff',
    fontSize: 16,
  }},
  panelTitle: {{
    color: '#ffffff',
    fontSize: 23,
    fontWeight: '800',
    marginTop: 4,
  }},
  actionList: {{
    marginTop: 14,
  }},
  actionRow: {{
    minHeight: 50,
    marginBottom: 10,
    borderRadius: 25,
    backgroundColor: '#424954',
    paddingHorizontal: 22,
    flexDirection: 'row',
    alignItems: 'center',
  }},
  actionIcon: {{
    width: 24,
    height: 24,
  }},
  actionText: {{
    flex: 1,
    marginLeft: 18,
    color: '#E8EAEE',
    fontSize: 18,
    fontWeight: '800',
  }},
  chevron: {{
    color: '#B5BBC5',
    fontSize: 23,
  }},
  materialStatus: {{
    minHeight: 42,
    marginTop: 12,
    paddingHorizontal: 14,
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 8,
    backgroundColor: '#222832',
  }},
  materialStatusText: {{
    flex: 1,
    marginLeft: 10,
    color: '#AEB5C0',
    fontSize: 13,
  }},
}});
"""
    demo_path = target_root / "src" / f"MeisheShortVideoDemo.{demo_suffix}"
    write_text(demo_path, content, target_root, report, "Generated React Native demo component")
    generate_react_native_publish(target_root, suffix, report)
    generate_react_native_drafts(target_root, suffix, report)

    app_path = find_react_native_entry_component(target_root)

    if app_path.exists():
        app_text = read_text(app_path)
        should_replace_app = (
            "@react-native/new-app-screen" in app_text
            or "react-native/Libraries/NewAppScreen" in app_text
            or "Welcome to React Native" in app_text
            or "react-native-nvshortvideo 本地插件包" in app_text
            or "pendingActions" in app_text
            or (
                "MeisheShortVideoDemo" not in app_text
                and (
                    "NvVideoResultComponent" in app_text
                    or "NvDraftListComponent" in app_text
                    or (
                        "NavigationContainer" in app_text
                        and "HomeScreen" in app_text
                        and "NvVideoPlayerPreView" in app_text
                    )
                )
            )
            or (
                "MeisheShortVideoDocking.getDraftList()" in app_text
                and "setVideoEditEventHandler" not in app_text
            )
        )
        if "MeisheShortVideoDemo" in app_text:
            report.add_change("React Native app entry already uses the generated Meishe demo component.")
        elif should_replace_app:
            import_path = react_native_demo_import_path(app_path, demo_path)
            app_content = f"""import React from 'react';

import {{ MeisheShortVideoDemo }} from '{import_path}';

function App() {{
  return <MeisheShortVideoDemo />;
}}

export default App;
"""
            write_text(app_path, app_content, target_root, report, "Replaced default React Native screen with Meishe demo entry")
        else:
            report.add_next_check(f"React Native: import `MeisheShortVideoDemo` from `{rel(demo_path, target_root)}` and add it to your app navigation.")
    else:
        report.add_next_check(f"React Native: import `MeisheShortVideoDemo` from `{rel(demo_path, target_root)}` and add it to your app entry.")


def find_react_native_entry_component(target_root: Path) -> Path:
    for name in ("App.tsx", "App.jsx", "App.js"):
        candidate = target_root / name
        if candidate.exists():
            return candidate

    index_path = target_root / "index.js"
    if index_path.exists():
        index_text = read_text(index_path)
        if re.search(r"from\s+['\"]\./src/App['\"]", index_text) or re.search(r"require\(['\"]\./src/App['\"]\)", index_text):
            for suffix in ("tsx", "jsx", "js"):
                candidate = target_root / f"src/App.{suffix}"
                if candidate.exists():
                    return candidate

    return target_root / "App.tsx"


def react_native_demo_import_path(app_path: Path, demo_path: Path) -> str:
    relative_path = demo_path.with_suffix("").resolve().relative_to(app_path.parent.resolve())
    import_path = relative_path.as_posix()
    if not import_path.startswith("."):
        import_path = f"./{import_path}"
    return import_path


def generate_react_native_publish(target_root: Path, suffix: str, report: Report) -> None:
    use_ts = suffix == "ts"
    demo_suffix = "tsx" if use_ts else "jsx"
    error_expr = "error instanceof Error ? error.message : String(error)" if use_ts else "String(error)"
    props_type = "type PublishProps = { projectInfo: any; onBack: () => void };\n\n" if use_ts else ""
    props_ann = ": PublishProps" if use_ts else ""
    info_ann = ": any" if use_ts else ""
    draft_info_ann = ": string" if use_ts else ""
    content = f"""import React, {{ useEffect, useMemo, useState }} from 'react';
import {{ Image, Keyboard, KeyboardAvoidingView, Platform, Pressable, SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, TextInput, TouchableWithoutFeedback, View }} from 'react-native';

import {{ MeisheShortVideoDocking, NvVideoCompileEvent }} from './meisheShortVideoDocking';

{props_type}function isCompileEvent(event{info_ann}, expected{info_ann}) {{
  return event === expected ||
    (event != null && expected != null && Number(event) === Number(expected)) ||
    String(event).toLowerCase() === String(expected).toLowerCase();
}}

function projectDate(projectInfo{info_ann}) {{
  for (const key of ['updateTime', 'modifyTime', 'modifiedTime', 'createTime', 'creationTime', 'timestamp']) {{
    const value = projectInfo?.[key];
    if (typeof value === 'number' && Number.isFinite(value)) {{
      return new Date(value > 100000000000 ? value : value * 1000);
    }}
    if (typeof value === 'string' && value.length > 0) {{
      const asNumber = Number(value);
      if (Number.isFinite(asNumber)) {{
        return new Date(asNumber > 100000000000 ? asNumber : asNumber * 1000);
      }}
      const parsed = new Date(value);
      if (!Number.isNaN(parsed.getTime())) {{
        return parsed;
      }}
    }}
  }}
  return new Date();
}}

function projectTitle(projectInfo{info_ann}, draftInfo{draft_info_ann}) {{
  const explicitTitle = draftInfo.trim() || String(projectInfo?.defaultProjectDescription ?? '').trim();
  if (explicitTitle && explicitTitle.toLowerCase() !== 'draft') {{
    return explicitTitle;
  }}
  const date = projectDate(projectInfo);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `草稿-${{month}}${{day}}`;
}}

function projectCoverPath(projectInfo{info_ann}) {{
  return String(projectInfo?.coverImagePath ?? projectInfo?.coverPath ?? projectInfo?.thumbnailPath ?? projectInfo?.thumbnail ?? '');
}}

export function MeisheShortVideoPublish({{ projectInfo, onBack }}{props_ann}) {{
  const projectId = useMemo(() => String(projectInfo?.projectId ?? ''), [projectInfo]);
  const [draftInfo, setDraftInfo] = useState(String(projectInfo?.draftInfo ?? ''));
  const [status, setStatus] = useState('请选择保存草稿或导出视频');
  const [progress, setProgress] = useState{('<number | undefined>' if use_ts else '')}(undefined);
  const coverPath = projectCoverPath(projectInfo);
  const title = projectTitle(projectInfo, draftInfo);

  useEffect(() => {{
    MeisheShortVideoDocking.setVideoCompileEventHandler((event{info_ann}, info{info_ann}) => {{
      if (isCompileEvent(event, NvVideoCompileEvent.progress)) {{
        const rawValue = Number(info?.progress ?? 0);
        const percentage = rawValue >= 0 && rawValue <= 1 ? rawValue * 100 : rawValue;
        setProgress(Number.isFinite(percentage) ? percentage / 100 : undefined);
        setStatus(Number.isFinite(percentage) ? `导出中 ${{percentage.toFixed(0)}}%` : '导出中...');
      }} else if (isCompileEvent(event, NvVideoCompileEvent.complete)) {{
        const outputPath = info?.outputPath;
        const errorCode = info?.errorCode;
        MeisheShortVideoDocking.getPublishInfo().catch(() => undefined);
        setProgress(undefined);
        setStatus(outputPath ? `导出成功：${{outputPath}}` : `导出结束，错误码：${{errorCode ?? 'unknown'}}`);
      }} else if (isCompileEvent(event, NvVideoCompileEvent.coverImageSelected)) {{
        setStatus('封面已更新');
      }}
    }});
    return () => {{
      MeisheShortVideoDocking.setVideoCompileEventHandler(null);
      if (projectId) {{
        MeisheShortVideoDocking.exitEdit(projectId);
      }}
    }};
  }}, [projectId]);

  async function saveDraft() {{
    try {{
      setStatus('正在保存草稿...');
      await MeisheShortVideoDocking.saveDraft(draftInfo);
      onBack();
    }} catch (error) {{
      setStatus(`保存草稿失败：${{{error_expr}}}`);
    }}
  }}

  async function exportVideo() {{
    try {{
      setProgress(0);
      setStatus('导出中...');
      await MeisheShortVideoDocking.compileCurrentTimeline({{}});
    }} catch (error) {{
      setProgress(undefined);
      setStatus(`导出失败：${{{error_expr}}}`);
    }}
  }}

  return (
    <SafeAreaView style={{styles.safeArea}}>
      <StatusBar barStyle="light-content" backgroundColor="#101010" />
      <TouchableWithoutFeedback onPress={{Keyboard.dismiss}} accessible={{false}}>
        <KeyboardAvoidingView style={{styles.keyboardArea}} behavior={{Platform.OS === 'ios' ? 'padding' : undefined}}>
          <View style={{styles.topBar}}>
            <Pressable style={{styles.backHitArea}} onPress={{onBack}}>
              <Text style={{styles.backIcon}}>‹</Text>
            </Pressable>
            <Text style={{styles.pageTitle}}>作品发布</Text>
          </View>
          <ScrollView
            contentContainerStyle={{styles.container}}
            keyboardDismissMode={{Platform.OS === 'ios' ? 'interactive' : 'on-drag'}}
            keyboardShouldPersistTaps="handled">
            <Text style={{styles.notice}}>温馨提示： 卸载应用后，草稿也会被删除</Text>
            <View style={{styles.projectRow}}>
              <View style={{styles.coverWrap}}>
                {{coverPath ? <Image source={{{{ uri: coverPath }}}} style={{styles.cover}} /> : <View style={{styles.coverPlaceholder}} />}}
                <Text style={{styles.playIcon}}>▶</Text>
              </View>
              <Text style={{styles.projectTitle}} numberOfLines={{2}}>{{title}}</Text>
            </View>
            <TextInput
              style={{styles.input}}
              multiline
              value={{draftInfo}}
              onChangeText={{setDraftInfo}}
              placeholder="草稿描述"
              placeholderTextColor="#777777"
            />
            <Text style={{styles.status}} numberOfLines={{3}}>{{status}}</Text>
            {{progress !== undefined ? <View style={{styles.progressTrack}}><View style={{[styles.progressFill, {{ width: `${{Math.max(0, Math.min(progress, 1)) * 100}}%` }}]}} /></View> : null}}
          </ScrollView>
          <View style={{styles.actions}}>
            <Pressable style={{[styles.actionButton, styles.secondaryButton]}} onPress={{saveDraft}}>
              <Text style={{styles.actionText}}>保存草稿</Text>
            </Pressable>
            <Pressable style={{styles.actionButton}} onPress={{exportVideo}}>
              <Text style={{styles.actionText}}>导出视频</Text>
            </Pressable>
          </View>
        </KeyboardAvoidingView>
      </TouchableWithoutFeedback>
    </SafeAreaView>
  );
}}

const styles = StyleSheet.create({{
  safeArea: {{
    flex: 1,
    backgroundColor: '#101010',
  }},
  keyboardArea: {{
    flex: 1,
  }},
  topBar: {{
    height: 70,
    alignItems: 'center',
    justifyContent: 'center',
  }},
  backHitArea: {{
    position: 'absolute',
    left: 12,
    width: 56,
    height: 56,
    alignItems: 'center',
    justifyContent: 'center',
  }},
  backIcon: {{
    color: '#ffffff',
    fontSize: 40,
    lineHeight: 44,
  }},
  pageTitle: {{
    color: '#ffffff',
    fontSize: 25,
    fontWeight: '500',
  }},
  container: {{
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 42,
  }},
  notice: {{
    marginBottom: 34,
    color: '#ffffff',
    fontSize: 20,
  }},
  projectRow: {{
    marginBottom: 22,
    flexDirection: 'row',
    alignItems: 'center',
  }},
  coverWrap: {{
    width: 96,
    height: 96,
    overflow: 'hidden',
    borderRadius: 10,
    backgroundColor: '#2A2A2A',
    alignItems: 'center',
    justifyContent: 'center',
  }},
  cover: {{
    width: '100%',
    height: '100%',
  }},
  coverPlaceholder: {{
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#2A2A2A',
  }},
  playIcon: {{
    position: 'absolute',
    color: '#ffffff',
    fontSize: 46,
  }},
  projectTitle: {{
    flex: 1,
    marginLeft: 26,
    color: '#ffffff',
    fontSize: 22,
  }},
  input: {{
    minHeight: 64,
    marginTop: 18,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: '#404040',
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    color: '#ffffff',
    backgroundColor: '#1D1D1D',
    fontSize: 15,
    textAlignVertical: 'top',
  }},
  status: {{
    marginTop: 16,
    color: '#d8d8d8',
    fontSize: 15,
    lineHeight: 21,
  }},
  progressTrack: {{
    height: 4,
    marginTop: 12,
    overflow: 'hidden',
    borderRadius: 2,
    backgroundColor: '#3A3A3A',
  }},
  progressFill: {{
    height: 4,
    backgroundColor: '#ffffff',
  }},
  actions: {{
    paddingHorizontal: 24,
    paddingTop: 12,
    paddingBottom: 12,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: '#303030',
    backgroundColor: '#101010',
    gap: 12,
  }},
  actionButton: {{
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 24,
    backgroundColor: '#424954',
    paddingHorizontal: 18,
  }},
  secondaryButton: {{
    backgroundColor: '#30343B',
  }},
  actionText: {{
    color: '#ffffff',
    fontSize: 17,
    fontWeight: '700',
  }},
}});
"""
    write_text(target_root / "src" / f"MeisheShortVideoPublish.{demo_suffix}", content, target_root, report, "Generated React Native publish component")


def generate_react_native_drafts(target_root: Path, suffix: str, report: Report) -> None:
    use_ts = suffix == "ts"
    demo_suffix = "tsx" if use_ts else "jsx"
    error_expr = "error instanceof Error ? error.message : String(error)" if use_ts else "String(error)"
    props_type = "type DraftsProps = { videoConfig: any; onBack: () => void };\n\n" if use_ts else ""
    props_ann = ": DraftsProps" if use_ts else ""
    any_ann = ": any" if use_ts else ""
    array_state = "useState<any[]>([])" if use_ts else "useState([])"
    content = f"""import React, {{ useCallback, useEffect, useState }} from 'react';
import {{ ActivityIndicator, Alert, Image, Pressable, SafeAreaView, ScrollView, StatusBar, StyleSheet, Text, View }} from 'react-native';

import {{ MeisheShortVideoDocking }} from './meisheShortVideoDocking';

{props_type}function normalizeDrafts(result{any_ann}) {{
  const source = result?.response ?? result?.data ?? result?.drafts ?? result;
  return Array.isArray(source) ? source : [];
}}

function draftDate(draft{any_ann}) {{
  for (const key of ['updateTime', 'modifyTime', 'modifiedTime', 'createTime', 'creationTime', 'timestamp']) {{
    const value = draft?.[key];
    if (typeof value === 'number' && Number.isFinite(value)) {{
      return new Date(value > 100000000000 ? value : value * 1000);
    }}
    if (typeof value === 'string' && value.length > 0) {{
      const asNumber = Number(value);
      if (Number.isFinite(asNumber)) {{
        return new Date(asNumber > 100000000000 ? asNumber : asNumber * 1000);
      }}
      const parsed = new Date(value);
      if (!Number.isNaN(parsed.getTime())) {{
        return parsed;
      }}
    }}
  }}
  return new Date();
}}

function draftTitle(draft{any_ann}) {{
  const draftInfo = String(draft?.draftInfo ?? '').trim();
  if (draftInfo) {{
    return draftInfo;
  }}
  const defaultDescription = String(draft?.defaultProjectDescription ?? '').trim();
  if (defaultDescription && defaultDescription.toLowerCase() !== 'draft') {{
    return defaultDescription;
  }}
  const date = draftDate(draft);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `草稿-${{month}}${{day}}`;
}}

export function MeisheShortVideoDrafts({{ videoConfig, onBack }}{props_ann}) {{
  const [drafts, setDrafts] = {array_state};
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState{('<string | undefined>' if use_ts else '')}(undefined);

  const loadDrafts = useCallback(async () => {{
    setIsLoading(true);
    setErrorMessage(undefined);
    try {{
      const result = await MeisheShortVideoDocking.getDraftList();
      const nextDrafts = normalizeDrafts(result);
      setDrafts(nextDrafts);
      setIsLoading(false);
    }} catch (error) {{
      setIsLoading(false);
      setErrorMessage({error_expr});
    }}
  }}, []);

  useEffect(() => {{
    MeisheShortVideoDocking.setDraftUpdateHandler(loadDrafts);
    loadDrafts();
    return () => {{
      MeisheShortVideoDocking.setDraftUpdateHandler(null);
    }};
  }}, [loadDrafts]);

  async function openDraft(draft{any_ann}) {{
    const projectId = String(draft?.projectId ?? '');
    if (!projectId) {{
      Alert.alert('草稿缺少 projectId');
      return;
    }}
    await MeisheShortVideoDocking.reeditDraft(projectId, videoConfig);
  }}

  function deleteDraft(draft{any_ann}) {{
    const projectId = String(draft?.projectId ?? '');
    if (!projectId) {{
      return;
    }}
    Alert.alert('删除草稿', '确认删除这个本地草稿？', [
      {{ text: '取消', style: 'cancel' }},
      {{
        text: '删除',
        style: 'destructive',
        onPress: async () => {{
          await MeisheShortVideoDocking.deleteDraft(projectId);
          setDrafts(current => current.filter(item => String(item?.projectId ?? '') !== projectId));
        }},
      }},
    ]);
  }}

  return (
    <SafeAreaView style={{styles.safeArea}}>
      <StatusBar barStyle="light-content" backgroundColor="#101010" />
      <View style={{styles.topBar}}>
        <Pressable style={{styles.backHitArea}} onPress={{onBack}}>
          <Text style={{styles.backIcon}}>‹</Text>
        </Pressable>
        <Text style={{styles.title}}>本地草稿箱</Text>
      </View>
      {{isLoading ? (
        <View style={{styles.centerContent}}>
          <ActivityIndicator color="#ffffff" size="large" />
        </View>
      ) : errorMessage ? (
        <ScrollView contentContainerStyle={{styles.centerScroll}}>
          <Text style={{styles.emptyText}}>草稿加载失败：{{errorMessage}}</Text>
        </ScrollView>
      ) : drafts.length === 0 ? (
        <ScrollView contentContainerStyle={{styles.centerScroll}}>
          <Text style={{styles.emptyText}}>没有草稿啦！</Text>
        </ScrollView>
      ) : (
        <ScrollView contentContainerStyle={{styles.listContent}}>
          <Text style={{styles.notice}}>温馨提示： 卸载应用后，草稿也会被删除</Text>
          {{drafts.map((draft{any_ann}, index{': number' if use_ts else ''}) => {{
            const projectId = String(draft?.projectId ?? index);
            const coverPath = String(draft?.coverImagePath || '');
            return (
              <Pressable
                key={{projectId}}
                style={{styles.draftRow}}
                onPress={{() => openDraft(draft)}}
                onLongPress={{() => deleteDraft(draft)}}>
                <View style={{styles.coverWrap}}>
                  {{coverPath ? <Image source={{{{ uri: coverPath }}}} style={{styles.cover}} /> : <View style={{styles.coverPlaceholder}} />}}
                  <Text style={{styles.playIcon}}>▷</Text>
                </View>
                <Text style={{styles.draftTitle}} numberOfLines={{2}}>{{draftTitle(draft)}}</Text>
              </Pressable>
            );
          }})}}
        </ScrollView>
      )}}
    </SafeAreaView>
  );
}}

const styles = StyleSheet.create({{
  safeArea: {{
    flex: 1,
    backgroundColor: '#101010',
  }},
  topBar: {{
    height: 70,
    alignItems: 'center',
    justifyContent: 'center',
  }},
  backHitArea: {{
    position: 'absolute',
    left: 12,
    width: 52,
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
  }},
  backIcon: {{
    color: '#ffffff',
    fontSize: 40,
    lineHeight: 44,
  }},
  title: {{
    color: '#ffffff',
    fontSize: 25,
    fontWeight: '500',
  }},
  centerContent: {{
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  }},
  centerScroll: {{
    flexGrow: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
    paddingBottom: 120,
  }},
  emptyText: {{
    color: '#ffffff',
    fontSize: 22,
    textAlign: 'center',
  }},
  listContent: {{
    paddingHorizontal: 24,
    paddingTop: 24,
    paddingBottom: 32,
  }},
  notice: {{
    marginBottom: 34,
    color: '#ffffff',
    fontSize: 20,
  }},
  draftRow: {{
    marginBottom: 22,
    flexDirection: 'row',
    alignItems: 'center',
  }},
  coverWrap: {{
    width: 96,
    height: 96,
    overflow: 'hidden',
    borderRadius: 10,
    backgroundColor: '#2A2A2A',
    alignItems: 'center',
    justifyContent: 'center',
  }},
  cover: {{
    width: '100%',
    height: '100%',
  }},
  coverPlaceholder: {{
    ...StyleSheet.absoluteFillObject,
    backgroundColor: '#2A2A2A',
  }},
  playIcon: {{
    position: 'absolute',
    color: '#ffffff',
    fontSize: 46,
  }},
  draftTitle: {{
    flex: 1,
    marginLeft: 26,
    color: '#ffffff',
    fontSize: 22,
  }},
}});
"""
    write_text(target_root / "src" / f"MeisheShortVideoDrafts.{demo_suffix}", content, target_root, report, "Generated React Native drafts component")
