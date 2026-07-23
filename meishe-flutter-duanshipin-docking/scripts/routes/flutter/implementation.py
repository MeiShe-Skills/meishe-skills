"""Flutter implementation helpers kept inside the Flutter route."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from meishe_docking_core import (
    IntegrationError,
    Report,
    TargetPlatforms,
    backup_path,
    find_project_plugin_folder,
    find_valid_plugin_folder,
    project_local_path,
    read_text,
    rel,
    write_text,
)
from .constants import FLUTTER_PACKAGE_HELP


FLUTTER_ANDROID_NATIVE_LIBRARIES = (
    "jni/arm64-v8a/libNvStreamingSdkCore.so",
    "jni/arm64-v8a/libNvMSAICutter.so",
    "jni/armeabi-v7a/libNvStreamingSdkCore.so",
    "jni/armeabi-v7a/libNvMSAICutter.so",
)
OPTIONAL_FLUTTER_ANDROID_BEAUTY_SHAPE_RESOURCES = (
    "beauty/shapePackage/facemesh/info.json",
    "beauty/shapePackage/warp/info.json",
)

FLUTTER_DEMO_SERVER_CONFIG = {
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

FLUTTER_ANDROID_PUBLISH_METHOD_2021 = """    private void goPublish(boolean needSaveDraft, boolean needSaveCover, boolean needSaveVideo, String videoPath) {
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
"""

FLUTTER_ANDROID_PUBLISH_METHOD_PATCHED = """    private boolean mPublishEventDispatched;

    private void emitPublishResultOnce(boolean needSaveDraft, String videoPath, String coverImagePath) {
        if (mPublishEventDispatched) {
            return;
        }
        mPublishEventDispatched = true;
        Map<String, Object> arguments = new TreeMap<>();
        arguments.put("hasDraft", needSaveDraft);
        arguments.put("coverImagePath", coverImagePath == null ? "" : coverImagePath);
        arguments.put("videoPath", videoPath);
        //目前默认传00
        arguments.put("projectId", "00");
        mVideoEditChannel.invokeMethod("VideoEditResultEvent", arguments);
        AppManager.getInstance().finishAllEditActivity();
    }

    private void goPublish(boolean needSaveDraft, boolean needSaveCover, boolean needSaveVideo, String videoPath) {
        if (null == mVideoEditChannel) {
            return;
        }
        mPublishEventDispatched = false;
        NvModuleManager.get().saveCover(PathUtils.getCoverDir(), String.valueOf(System.currentTimeMillis()), mCoverPoint, false,
                new NvModuleManager.OnCoverSavedCallBack() {
                    @Override
                    public void onCoverSaved(String path) {
                        emitPublishResultOnce(needSaveDraft, videoPath, path);
                    }

                    @Override
                    public void onCoverSaveFailed() {
                        emitPublishResultOnce(needSaveDraft, videoPath, "");
                    }
                });
    }
"""


def resolve_flutter_plugin(
    plugin_path: str | None,
    target_root: Path,
    targets: TargetPlatforms,
) -> Path:
    validator = lambda path: validate_flutter_plugin_package(path, targets)
    if not plugin_path:
        return find_project_plugin_folder(target_root, "nvshortvideo", FLUTTER_PACKAGE_HELP, validator)
    return find_valid_plugin_folder(Path(plugin_path), "nvshortvideo", FLUTTER_PACKAGE_HELP, validator)


def validate_flutter_plugin_package(plugin: Path, targets: TargetPlatforms | None = None) -> None:
    pubspec = plugin / "pubspec.yaml"
    if not pubspec.exists():
        raise IntegrationError(
            "Invalid Flutter plugin package. The official Flutter short-video package must contain "
            f"`nvshortvideo/pubspec.yaml`; missing at `{pubspec}`."
        )
    text = read_text(pubspec)
    if not re.search(r"(?m)^\ufeff?name:\s*nvshortvideo\s*$", text):
        raise IntegrationError(
            "Invalid Flutter plugin package. Expected `name: nvshortvideo` in "
            f"`{pubspec}`."
        )
    if targets and targets.android and not (plugin / "android").is_dir():
        raise IntegrationError(
            f"Invalid Flutter plugin package for Android. Missing `{plugin / 'android'}`."
        )


def patch_flutter_plugin_android_config_callback(target_root: Path, plugin: Path, report: Report) -> None:
    java_file = plugin / "android" / "src" / "main" / "java" / "com" / "meishe" / "nvshortvideo" / "VideoEditPlugin.java"
    if not java_file.exists():
        report.add_warning(
            "Flutter plugin Android bridge was not patched because "
            f"`{rel(java_file, target_root)}` was not found."
        )
        return
    text = read_text(java_file)
    config_match = re.search(
        r"case CONFIG_SERVER_INFO:(?P<body>.*?)(?P<tail>\n\s*)break;",
        text,
        flags=re.S,
    )
    if not config_match:
        report.add_warning(
            "Flutter plugin Android bridge was not patched because the "
            "`CONFIG_SERVER_INFO` branch shape was not recognized. Ensure it calls "
            "`methodCallListener.completion(null, null)` after `initModel()`."
        )
        return
    if "methodCallListener.completion(" in config_match.group("body"):
        report.add_change("Flutter plugin Android ConfigServerInfo callback already completes.")
        return
    if "NvModuleManager.get().initModel();" not in config_match.group("body"):
        report.add_warning(
            "Flutter plugin Android bridge was not patched because the "
            "`CONFIG_SERVER_INFO` branch no longer calls `initModel()` in the expected location. "
            "Ensure it calls `methodCallListener.completion(null, null)` before `break`."
        )
        return
    replacement = (
        "case CONFIG_SERVER_INFO:"
        + config_match.group("body")
        + config_match.group("tail")
        + "methodCallListener.completion(null, null);\n"
        + config_match.group("tail")
        + "break;"
    )
    text = text[: config_match.start()] + replacement + text[config_match.end() :]
    write_text(
        java_file,
        text,
        target_root,
        report,
        "Patched Flutter plugin Android ConfigServerInfo callback",
    )


def patch_flutter_android_publish_bridge(
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
            f"Flutter Android bridge was not found at `{bridge}`; AutoCut publish fallback was not applied."
        )
        return

    text = read_text(read_bridge)
    if "private void emitPublishResultOnce(" in text:
        report.add_change("Flutter Android AutoCut publish fallback already present.")
        return
    if FLUTTER_ANDROID_PUBLISH_METHOD_2021 not in text:
        report.add_warning(
            "Flutter Android `goPublish` does not match the verified ShortVideo 2.0.2.1 source shape. "
            "No vendor patch was applied; manually verify that cover-save failure still emits `VideoEditResultEvent`."
        )
        return

    patched = text.replace(
        FLUTTER_ANDROID_PUBLISH_METHOD_2021,
        FLUTTER_ANDROID_PUBLISH_METHOD_PATCHED,
        1,
    )
    write_text(
        bridge,
        patched,
        target_root,
        report,
        "Patched verified Flutter Android AutoCut publish fallback",
    )


def enable_flutter_androidx_jetifier(target_root: Path, plugin: Path, report: Report) -> None:
    android_root = target_root / "android"
    if not android_root.is_dir():
        return
    plugin_gradle = plugin / "android" / "build.gradle"
    if not plugin_gradle.exists():
        report.add_toolchain_warning(
            "Flutter Android plugin build.gradle is missing; AndroidX/Support dependency compatibility could not be inspected."
        )
        return
    plugin_text = read_text(plugin_gradle)
    legacy_markers = (
        "com.blankj:utilcode:1.30.6",
        "com.permissionx.guolindev:permission-support:1.4.0",
    )
    if not any(marker in plugin_text for marker in legacy_markers):
        report.add_toolchain_warning(
            "Flutter plugin does not match the verified 2.0.2.0 Android dependency shape; Jetifier was not enabled automatically. Build first and inspect the actual dependency error before patching."
        )
        return

    properties = android_root / "gradle.properties"
    text = read_text(properties) if properties.exists() else ""
    original = text
    for key, value in (("android.useAndroidX", "true"), ("android.enableJetifier", "true")):
        if re.search(rf"(?m)^{re.escape(key)}=", text):
            text = re.sub(rf"(?m)^{re.escape(key)}=.*$", f"{key}={value}", text)
        else:
            text = text.rstrip() + f"\n{key}={value}\n"
    if text != original:
        write_text(
            properties,
            text,
            target_root,
            report,
            "Enabled AndroidX/Jetifier for verified Flutter ShortVideo legacy support dependencies",
        )
    else:
        report.add_change("Flutter AndroidX/Jetifier compatibility properties already set.")


def read_aar_entries(aar: Path, label: str) -> set[str]:
    if not aar.is_file():
        raise IntegrationError(f"{label} not found: `{aar}`.")
    try:
        with zipfile.ZipFile(aar) as archive:
            return set(archive.namelist())
    except zipfile.BadZipFile as exc:
        raise IntegrationError(f"{label} is not a valid AAR/ZIP archive: `{aar}`.") from exc


def ensure_flutter_android_native_libraries(
    args: argparse.Namespace,
    target_root: Path,
    plugin: Path,
    source_plugin: Path,
    report: Report,
    *,
    apply_changes: bool = True,
) -> None:
    if not (target_root / "android").is_dir():
        return

    inspect_plugin = plugin if plugin.exists() else source_plugin
    plugin_aar = inspect_plugin / "android" / "libs" / "NvShortVideoCore.aar"
    plugin_entries = read_aar_entries(plugin_aar, "Flutter plugin NvShortVideoCore.aar")
    missing_beauty_resources = [
        resource
        for resource in OPTIONAL_FLUTTER_ANDROID_BEAUTY_SHAPE_RESOURCES
        if not any(entry.lstrip("/").endswith(resource) for entry in plugin_entries)
    ]
    if missing_beauty_resources:
        report.add_vendor_warning(
            "The Flutter Android AAR does not contain optional fixed beauty-shape resources: "
            + ", ".join(f"`{item}`" for item in missing_beauty_resources)
            + ". Core Flutter/ShortVideo flows can still run, but Shape/MicroShape beauty categories "
            "may be empty or incomplete. Obtain the matching resource delivery from Meishe; this is "
            "not an online-material request failure."
        )
    elif apply_changes:
        report.add_input("Flutter Android optional Shape/MicroShape beauty resources are present.")
    missing = [entry for entry in FLUTTER_ANDROID_NATIVE_LIBRARIES if entry not in plugin_entries]
    local_jni_root = inspect_plugin / "android" / "src" / "main" / "jniLibs"
    missing = [
        entry
        for entry in missing
        if not (local_jni_root / Path(entry).relative_to("jni")).is_file()
    ]
    if not missing:
        if apply_changes:
            report.add_change("Flutter Android native engine libraries are complete for arm64-v8a and armeabi-v7a.")
        return

    if not args.aar_path:
        formatted = "\n".join(f"- `{entry}`" for entry in missing)
        raise IntegrationError(
            "Flutter Android runtime validation cannot continue because the official Flutter plugin's "
            "`android/libs/NvShortVideoCore.aar` is missing required native engine libraries:\n"
            f"{formatted}\n"
            "Provide a version-compatible official Android `NvShortVideoCore.aar` containing these libraries "
            "with `--aar-path <path>`. The skill extracts only the native `.so` files into the project-local "
            "Flutter plugin and does not replace its Java/UI implementation."
        )

    supplement_aar = Path(args.aar_path).expanduser().resolve()
    supplement_entries = read_aar_entries(supplement_aar, "Flutter Android native-library supplement AAR")
    supplement_missing = [entry for entry in FLUTTER_ANDROID_NATIVE_LIBRARIES if entry not in supplement_entries]
    if supplement_missing:
        formatted = "\n".join(f"- `{entry}`" for entry in supplement_missing)
        raise IntegrationError(
            "The supplied Flutter Android supplement AAR does not contain all required native libraries:\n"
            f"{formatted}\nAAR: `{supplement_aar}`"
        )

    if not apply_changes:
        return

    report.add_input(
        f"Flutter Android native-library supplement AAR: `{supplement_aar}` "
        "(only verified `.so` entries are copied; Flutter Java/UI code remains from the selected plugin)."
    )
    if report.dry_run:
        report.add_change(
            "Would extract Flutter Android native engine libraries for arm64-v8a and armeabi-v7a into "
            "`vendor/meishe/nvshortvideo/android/src/main/jniLibs`."
        )
        return

    with zipfile.ZipFile(supplement_aar) as archive:
        for entry in FLUTTER_ANDROID_NATIVE_LIBRARIES:
            relative = Path(entry).relative_to("jni")
            destination = plugin / "android" / "src" / "main" / "jniLibs" / relative
            content = archive.read(entry)
            if destination.exists() and destination.read_bytes() == content:
                report.add_change(f"Unchanged: `{rel(destination, target_root)}`")
                continue
            if destination.exists():
                backup_path(destination, target_root, report)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            report.add_change(
                f"Extracted Flutter Android native engine library: `{rel(destination, target_root)}`"
            )


def patch_pubspec(target_root: Path, plugin: Path, report: Report) -> None:
    path = target_root / "pubspec.yaml"
    if not path.exists():
        raise IntegrationError("pubspec.yaml not found.")
    text = read_text(path)
    dependency = f"  nvshortvideo:\n    path: {project_local_path(plugin, target_root)}\n"
    if re.search(r"^\s*nvshortvideo\s*:", text, re.M):
        text = re.sub(r"(?m)^  nvshortvideo:\n(?:    [^\n]*\n?)*", dependency, text, count=1)
        write_text(path, text, target_root, report, "Updated Flutter nvshortvideo path dependency")
    elif re.search(r"^dependencies:\s*$", text, re.M):
        text = re.sub(r"^dependencies:\s*$", "dependencies:\n" + dependency.rstrip(), text, count=1, flags=re.M)
        write_text(path, text, target_root, report, "Added Flutter nvshortvideo path dependency")
    else:
        text = text.rstrip() + "\n\ndependencies:\n" + dependency
        write_text(path, text, target_root, report, "Added Flutter nvshortvideo path dependency")


def generate_flutter_feature_config(target_root: Path, report: Report) -> Path:
    path = target_root / "lib" / "meishe_feature_config.dart"
    if path.exists():
        report.add_change(f"Retained user-editable Flutter feature configuration: `{rel(path, target_root)}`")
        return path

    content = r"""import 'package:flutter/widgets.dart';
import 'package:nvshortvideo/nvshortvideo.dart';

/// Flutter 专属配置。只修改本文件，不要到 ios/ 或 android/ 中重复配置功能菜单。
/// SDK 根据菜单数组动态创建控件：删除数组项会同时删除入口并重排其余 UI，禁止用 null 或空占位项。
abstract final class MeisheFeatureConfig {
  static NvVideoConfig apply(NvVideoConfig config) {
    // 全局颜色使用 #RRGGBB；shadowColor 使用 #RRGGBBAA。
    config.primaryColor = '#FC3E5A';
    config.backgroundColor = '#000000';
    config.panelBackgroundColor = '#1C1C1C';
    config.textColor = '#FFFFFF';
    config.secondaryTextColor = '#6C6C77';
    // 是否显示设备本地音乐入口；读取本地音乐仍受系统权限约束。
    config.enableLocalMusic = true;
    // 文字阴影偏移和颜色，dx/dy 分别为横向/纵向偏移。
    config.shadowOffset = const Size(0, 0.5);
    config.shadowColor = '#00000080';

    // 相册顶部标签：0=全部，1=视频，2=图片。
    config.albumConfig.type = 0;
    // 相册最大选择数，必须大于 0。
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
    config.captureConfig.captureMenuItems = <NvCaptureMenuItem>[
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
    config.captureConfig.captureBottomMenuItems = <NvCaptureBottomMenuItem>[
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
    config.captureConfig.timeRanges = <NvTimePair>[
      NvTimePair(3000, 15000),
      NvTimePair(3000, 60000),
    ];
    // 快拍时长范围，单位毫秒。
    config.captureConfig.smartTimeRange = NvTimePair(0, 15000);
    // 滤镜默认强度，官方配置范围为 0.0-1.0。
    config.captureConfig.filterDefaultValue = 0.8;
    // 是否在拍摄页显示相册快捷入口。
    config.captureConfig.enableCaptureAlbum = false;
    // true 会在进入拍摄时自动关闭原声/麦克风。
    config.captureConfig.autoDisablesMic = false;
    // 拍摄帧率；已验证配置为 30，修改前需确认目标设备和桥接支持范围。
    config.captureConfig.fps = 30;
    // recordConfiguration 支持 bitrate、gopsize、video encoder name；未知底层键禁止写入。
    // config.captureConfig.recordConfiguration = <String, dynamic>{'video encoder name': 'hevc', 'gopsize': 30};

    // 合拍右侧菜单独立于普通拍摄菜单，有序；删除项后合拍页面同步重排。
    config.captureConfig.dualMenuItems = <NvCaptureMenuItem>[
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
    final dual = NvDualConfig();
    // 小窗左/上边距与底图宽/高的比例，建议保持在 0.0-1.0。
    dual.left = 17.0 / 375.0;
    dual.top = 18.0 / 666.67;
    // 小窗短边与底图宽度比例，必须大于 0 且不宜超过 1。
    dual.limitWidth = 153.5 / 375.0;
    // 默认合拍样式必须存在于 supportedTypes。
    dual.defaultType = NvDualType.leftRight;
    // 可选样式集合：左右、上下、左矩形、左圆、上圆。
    dual.supportedTypes = <NvDualType>[NvDualType.leftRight, NvDualType.topDown, NvDualType.leftRect, NvDualType.leftCircle, NvDualType.topCircle];
    // 是否自动禁用麦克风；muteOriginal 控制是否默认关闭原视频声音。
    dual.autoDisablesMic = false;
    dual.muteOriginal = true;
    config.captureConfig.dualConfig = dual;

    // 编辑右侧菜单，有序。删除 text 会删除文字入口及其下级功能，后续入口自动上移，不留空白。
    // release/download 关系到发布/保存入口，删除前必须确认仍有可达的发布与导出流程。
    config.editConfig.editMenuItems = <NvEditMenuItem>[
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
    config.editConfig.minAudioDuration = 1000;
    config.editConfig.defaultImageDuration = 3000;
    // 字幕默认颜色与可选颜色，格式为 #RRGGBB。
    config.editConfig.captionColor = '#FFFFFF';
    config.editConfig.captionColorList = <String>['#FFFFFF', '#000000', '#0099F6', '#50C23B', '#FFC840', '#FF8500', '#FF3350', '#E40069', '#B200C0', '#F8808A', '#FEBF7C', '#262626', '#363636', '#555555', '#737373', '#989898', '#B2B2B2', '#C7C7C7', '#DBDBDB', '#F0F0F0'];
    // 字幕样式集合：无、背景、半透明背景、描边。
    config.editConfig.supportedCaptionStyles = <NvImageCaptionStyle>[NvImageCaptionStyle.none, NvImageCaptionStyle.bg, NvImageCaptionStyle.bgAlpha, NvImageCaptionStyle.outline];
    // firstAsset 按首个素材决定画幅；fixed 使用 editMode。
    config.editConfig.editModeSource = NvEditModeSource.firstAsset;
    config.editConfig.editMode = NvEditMode.NvEditMode9v16;
    // 用户可选画幅列表；fixed 的 editMode 必须包含在此列表中。
    config.editConfig.supportedEditModes = <NvEditMode>[NvEditMode.NvEditMode9v16, NvEditMode.NvEditMode16v9, NvEditMode.NvEditMode3v4, NvEditMode.NvEditMode4v3, NvEditMode.NvEditMode1v1, NvEditMode.NvEditMode18v9, NvEditMode.NvEditMode9v18, NvEditMode.NvEditMode8v9, NvEditMode.NvEditMode9v8];
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
    // 生成资源：assets/meishe_feature_watermark.png、Android drawable-nodpi、iOS Asset Catalog 中同名 imageset。
    // configure 可设置底层合成键值；未知键禁止写入，bitrate/fps 冲突时以上显式字段优先。

    // modelConfig 的路径必须指向与当前 SDK 匹配的真实模型文件。不要伪造或跨版本复制模型。
    // 可配置字段：use240、fakeface、face、face240、avatar、hand、humanseg、skysegment、eyecontour、
    // advancedbeauty、facecommon、autoCutActivity、autoCutFaceAttri、autoCutFace、autoCutImagecls、autoCutPf、autoCutPhoto。

    validate(config);
    return config;
  }

  static void validate(NvVideoConfig config) {
    final bottom = config.captureConfig.captureBottomMenuItems;
    if (bottom.isEmpty) {
      throw ArgumentError('captureBottomMenuItems must contain at least one capture mode');
    }
    if (!bottom.contains(config.captureConfig.defaultBottomMenuSelectItem)) {
      throw ArgumentError('defaultBottomMenuSelectItem must exist in captureBottomMenuItems');
    }
    final templateIndex = bottom.indexOf(NvCaptureBottomMenuItem.template);
    if (templateIndex >= 0 && templateIndex != bottom.length - 1) {
      throw ArgumentError('NvCaptureBottomMenuItem.template must be the last bottom menu item');
    }
    _assertUnique('captureMenuItems', config.captureConfig.captureMenuItems);
    _assertUnique('captureBottomMenuItems', bottom);
    _assertUnique('dualMenuItems', config.captureConfig.dualMenuItems);
    _assertUnique('editMenuItems', config.editConfig.editMenuItems);
    if (config.albumConfig.maxSelectCount <= 0 || config.templateConfig.maxSelectCount <= 0) {
      throw ArgumentError('album/template maxSelectCount must be greater than 0');
    }
    if (config.editConfig.maxVolume <= 0 || config.editConfig.maxVolume > 8) {
      throw ArgumentError('editConfig.maxVolume must be greater than 0 and no greater than 8');
    }
    _validateWatermark('compileConfig.watermarkConfig', config.compileConfig.watermarkConfig);
    _validateWatermark('compileConfig.coverWatermarkConfig', config.compileConfig.coverWatermarkConfig);
  }

  static void _validateWatermark(String name, dynamic watermark) {
    if (watermark == null) {
      return;
    }
    if (watermark.watermark == null) {
      throw ArgumentError('$name must reference a real watermark image');
    }
    if (watermark.width is! num || watermark.height is! num || watermark.width <= 0 || watermark.height <= 0) {
      throw ArgumentError('$name width and height must be greater than 0');
    }
    if (watermark.offsetX is! num || watermark.offsetY is! num || watermark.offsetX < 0 || watermark.offsetY < 0) {
      throw ArgumentError('$name offsets must be non-negative');
    }
    if (watermark.position == null) {
      throw ArgumentError('$name position is required');
    }
  }

  static void _assertUnique<T>(String name, List<T> items) {
    if (items.toSet().length != items.length) {
      throw ArgumentError('$name contains duplicate menu items');
    }
  }
}
"""
    write_text(path, content, target_root, report, "Generated user-editable Flutter feature configuration")
    report.add_user_configuration(
        f"Flutter feature entry: edit `{rel(path, target_root)}`. Menu arrays are ordered and drive SDK UI reflow; the skill preserves this file on later runs."
    )
    return path


def generate_flutter_wrapper(target_root: Path, report: Report) -> None:
    generate_flutter_feature_config(target_root, report)
    config = json.dumps(FLUTTER_DEMO_SERVER_CONFIG, ensure_ascii=False, indent=2)
    content = f"""import 'package:nvshortvideo/nvshortvideo.dart';
import 'meishe_feature_config.dart';

class MeisheShortVideoDocking {{
  static final Map<String, dynamic> defaultServerConfig = {config};

  const MeisheShortVideoDocking._();

  static NvVideoConfig createVideoConfig() {{
    final config = NvVideoConfig();
    return MeisheFeatureConfig.apply(config);
  }}

  static Future<void> configureServer([
    Map<String, dynamic>? overrides,
    Duration timeout = const Duration(seconds: 6),
  ]) async {{
    final config = Map<String, dynamic>.from(defaultServerConfig);
    if (overrides != null) {{
      config.addAll(overrides);
    }}
    await shortVideoOperator().configServerInfo(config).timeout(timeout);
  }}

  static Future<bool> downloadPrefabricatedMaterial() async {{
    final result = await shortVideoOperator().downloadPrefabricatedMaterial();
    return result == true;
  }}

  static Future<dynamic> startVideoCapture({{NvVideoConfig? config, NvMusicInfo? musicInfo}}) {{
    return shortVideoOperator().startVideoCapture(config: config ?? createVideoConfig(), musicInfo: musicInfo);
  }}

  static Future<dynamic> startVideoDualCapture({{NvVideoConfig? config}}) {{
    return shortVideoOperator().startVideoDualCapture(config: config ?? createVideoConfig());
  }}

  static Future<dynamic> startVideoDualCaptureWithVideo(String videoPath, {{NvVideoConfig? config}}) {{
    return shortVideoOperator().startVideoDualCaptureWithVideo(videoPath, config: config ?? createVideoConfig());
  }}

  static Future<dynamic> startSelectFilesForEdit({{NvVideoConfig? config}}) {{
    return shortVideoOperator().startSelectFilesForEdit(config: config ?? createVideoConfig());
  }}

  static Future<dynamic> getDraftList() {{
    return shortVideoOperator().getDraftList();
  }}

  static Future<dynamic> reeditDraft(String projectId, {{NvVideoConfig? config}}) {{
    return shortVideoOperator().reeditDraft(projectId, config: config ?? createVideoConfig());
  }}

  static Future<dynamic> deleteDraft(String projectId) {{
    return shortVideoOperator().deleteDraft(projectId);
  }}

  static Future<dynamic> saveDraft(String info) {{
    return shortVideoOperator().saveDraft(info);
  }}

  static Future<dynamic> compileCurrentTimeline([Map<String, dynamic>? configure]) {{
    return shortVideoOperator().compileCurrentTimeline(configure ?? <String, dynamic>{{}});
  }}

  static Future<NvPublishInfo> getPublishInfo() {{
    return shortVideoOperator().getPublishInfo();
  }}

  static void exitEdit(String projectId) {{
    shortVideoOperator().exitEdit(projectId);
  }}

  static void setVideoEditEventHandler(void Function(NvVideoEditEvent event, Map info)? handler) {{
    shortVideoOperator().setVideoEditEventHandler(handler);
  }}

  static void setDraftUpdateHandler(void Function()? handler) {{
    shortVideoOperator().setDraftUpdateHandler(handler);
  }}

  static void setVideoCompileEventHandler(void Function(NvVideoCompileEvent event, Map info)? handler) {{
    shortVideoOperator().setVideoCompileEventHandler(handler);
  }}
}}
"""
    write_text(target_root / "lib" / "meishe_short_video_docking.dart", content, target_root, report, "Generated Flutter docking wrapper")


def generate_flutter_demo(target_root: Path, report: Report) -> None:
    content = """import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:nvshortvideo/nvshortvideo.dart';

import 'meishe_short_video_docking.dart';
import 'meishe_short_video_drafts.dart';
import 'meishe_short_video_publish.dart';

class MeisheShortVideoDemoPage extends StatefulWidget {
  const MeisheShortVideoDemoPage({super.key});

  @override
  State<MeisheShortVideoDemoPage> createState() => _MeisheShortVideoDemoPageState();
}

class _MeisheShortVideoDemoPageState extends State<MeisheShortVideoDemoPage>
    with WidgetsBindingObserver {
  final NvVideoConfig _videoConfig = MeisheShortVideoDocking.createVideoConfig();
  Future<void>? _serverConfiguration;
  Future<void>? _materialPreparation;
  bool _materialReady = false;
  String? _prepareWarning;

  bool get _isPreparingMaterials => _materialPreparation != null;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    MeisheShortVideoDocking.setVideoEditEventHandler((event, info) {
      if (event == NvVideoEditEvent.publish && mounted) {
        Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => MeisheShortVideoPublishPage(projectInfo: Map<String, dynamic>.from(info)),
          ),
        );
      }
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) {
        _prepareMaterialsInBackground();
      }
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _prepareMaterialsInBackground();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    MeisheShortVideoDocking.setVideoEditEventHandler(null);
    super.dispose();
  }

  Future<void> _ensureServerConfigured() async {
    final existing = _serverConfiguration;
    if (existing != null) {
      await existing;
      return;
    }

    final request = MeisheShortVideoDocking.configureServer();
    _serverConfiguration = request;
    try {
      await request;
    } catch (_) {
      if (identical(_serverConfiguration, request)) {
        _serverConfiguration = null;
      }
      rethrow;
    }
  }

  void _prepareMaterialsInBackground() {
    if (_materialReady || _isPreparingMaterials) {
      return;
    }

    final request = _downloadPrefabricatedMaterials();
    _materialPreparation = request;
    setState(() {
      _prepareWarning = null;
    });
    unawaited(request.whenComplete(() {
      if (!identical(_materialPreparation, request)) {
        return;
      }
      _materialPreparation = null;
      if (mounted) {
        setState(() {});
      }
    }));
  }

  Future<void> _downloadPrefabricatedMaterials() async {
    try {
      await _ensureServerConfigured();
      final prepared = await MeisheShortVideoDocking.downloadPrefabricatedMaterial();
      if (prepared) {
        _materialReady = true;
        _prepareWarning = null;
      } else if (!_materialReady) {
        _prepareWarning = '预制美颜资源暂未准备完成，核心功能可正常使用。';
      }
    } catch (_) {
      if (!_materialReady) {
        _prepareWarning = '预制美颜资源暂未准备完成，联网后将自动重试。';
      }
    }
  }

  void _observeFeatureMaterialRefresh(Future<bool> request) {
    unawaited(request.then((prepared) {
      _materialReady = prepared;
      _prepareWarning = prepared ? null : '预制美颜资源暂未准备完成，核心功能可正常使用。';
      if (mounted) {
        setState(() {});
      }
    }).catchError((Object _) {
      _materialReady = false;
      _prepareWarning = '预制美颜资源暂未准备完成，联网后将自动重试。';
      if (mounted) {
        setState(() {});
      }
    }));
  }

  Future<void> _runFeature(
    Future<dynamic> Function() action, {
    bool refreshMaterials = false,
  }) async {
    if (refreshMaterials && Platform.isIOS) {
      try {
        await _ensureServerConfigured();
        _observeFeatureMaterialRefresh(
          MeisheShortVideoDocking.downloadPrefabricatedMaterial(),
        );
      } catch (_) {
        _materialReady = false;
        _prepareWarning = '服务配置暂未完成，在线素材可能不可用。';
        if (mounted) {
          setState(() {});
        }
      }
    }
    try {
      await action();
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$error')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final materialStatus = _materialReady
        ? null
        : _isPreparingMaterials
            ? '预制美颜资源正在后台准备，不影响核心功能。'
            : _prepareWarning;
    final screenHeight = MediaQuery.sizeOf(context).height;
    final topPadding = (screenHeight * 0.038).clamp(24.0, 34.0).toDouble();
    final bottomPadding = (screenHeight * 0.075).clamp(48.0, 70.0).toDouble();
    final titleSize = (screenHeight * 0.036).clamp(28.0, 32.0).toDouble();
    final bannerTopGap = (screenHeight * 0.015).clamp(10.0, 14.0).toDouble();
    final bannerHeight = (screenHeight * 0.18).clamp(108.0, 148.0).toDouble();
    final panelTopGap = (screenHeight * 0.026).clamp(16.0, 22.0).toDouble();
    final panelTopPadding = (screenHeight * 0.026).clamp(18.0, 24.0).toDouble();
    return Scaffold(
      backgroundColor: const Color(0xFF171D26),
      body: Stack(
        children: [
          SafeArea(
            child: ListView(
              padding: EdgeInsets.fromLTRB(24, topPadding, 24, bottomPadding),
              children: [
                Text(
                  '素材上新',
                  style: TextStyle(color: Colors.white, fontSize: titleSize, fontWeight: FontWeight.w800),
                ),
                SizedBox(height: bannerTopGap),
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Image.asset(
                    'assets/meishe_home_banner.jpg',
                    height: bannerHeight,
                    width: double.infinity,
                    fit: BoxFit.cover,
                  ),
                ),
                SizedBox(height: panelTopGap),
                Container(
                  padding: EdgeInsets.fromLTRB(20, panelTopPadding, 20, 16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF222832),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        '请选择所需的功能',
                        style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w400),
                      ),
                      const SizedBox(height: 4),
                      const Text(
                        '功能列表',
                        style: TextStyle(color: Colors.white, fontSize: 23, fontWeight: FontWeight.w800),
                      ),
                      const SizedBox(height: 14),
                      _FeatureRow(
                        iconAsset: 'assets/meishe_icon_capture.png',
                        label: '拍摄',
                        onTap: () => _runFeature(
                          () => MeisheShortVideoDocking.startVideoCapture(config: _videoConfig),
                          refreshMaterials: true,
                        ),
                      ),
                      _FeatureRow(
                        iconAsset: 'assets/meishe_icon_dual_capture.png',
                        label: '合拍',
                        onTap: () => _runFeature(
                          () => MeisheShortVideoDocking.startVideoDualCapture(config: _videoConfig),
                          refreshMaterials: true,
                        ),
                      ),
                      _FeatureRow(
                        iconAsset: 'assets/meishe_icon_edit.png',
                        label: '编辑',
                        onTap: () => _runFeature(
                          () => MeisheShortVideoDocking.startSelectFilesForEdit(config: _videoConfig),
                          refreshMaterials: true,
                        ),
                      ),
                      _FeatureRow(
                        iconAsset: 'assets/meishe_icon_draft.png',
                        label: '草稿',
                        onTap: () {
                          Navigator.of(context).push(
                            MaterialPageRoute<void>(
                              builder: (_) => MeisheShortVideoDraftsPage(videoConfig: _videoConfig),
                            ),
                          );
                        },
                      ),
                      if (materialStatus != null)
                        _PrepareStatus(
                          message: materialStatus,
                          canRetry: !_isPreparingMaterials,
                          onRetry: _prepareMaterialsInBackground,
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PrepareStatus extends StatelessWidget {
  const _PrepareStatus({
    required this.message,
    required this.canRetry,
    required this.onRetry,
  });

  final String message;
  final bool canRetry;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 2),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFF303742),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Text(
              message,
              style: const TextStyle(color: Color(0xFFD7DCE5), fontSize: 13, height: 1.25),
            ),
          ),
          if (canRetry) ...[
            const SizedBox(width: 10),
            TextButton(
              onPressed: onRetry,
              style: TextButton.styleFrom(
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                minimumSize: Size.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text('重试'),
            ),
          ],
        ],
      ),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  const _FeatureRow({
    required this.iconAsset,
    required this.label,
    required this.onTap,
  });

  final String iconAsset;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: InkWell(
          borderRadius: BorderRadius.circular(25),
          onTap: onTap,
          child: Container(
            height: 50,
            padding: const EdgeInsets.symmetric(horizontal: 22),
            decoration: BoxDecoration(
              color: const Color(0xFF424954),
              borderRadius: BorderRadius.circular(25),
            ),
            child: Row(
              children: [
                Image.asset(iconAsset, width: 24, height: 24),
                const SizedBox(width: 18),
                Expanded(
                  child: Text(
                    label,
                    style: const TextStyle(color: Color(0xFFE8EAEE), fontSize: 18, fontWeight: FontWeight.w800),
                  ),
                ),
                const Icon(Icons.chevron_right, color: Color(0xFFB5BBC5), size: 23),
              ],
            ),
          ),
      ),
    );
  }
}
"""
    write_text(target_root / "lib" / "meishe_short_video_demo.dart", content, target_root, report, "Generated Flutter demo page")
    main_path = target_root / "lib" / "main.dart"
    if main_path.exists():
        main_text = read_text(main_path)
        should_replace_main = (
            "Flutter Demo Home Page" in main_text
            or "_counter" in main_text
            or (
                "ShortVideoHomePage" in main_text
                and (
                    "_showResultDialog('Publish callback'" in main_text
                    or "_DraftListSheet" in main_text
                    or "startSelectFilesForEdit(config: _videoConfig)" in main_text
                )
            )
        )
        if should_replace_main:
            app_content = """import 'package:flutter/material.dart';

import 'meishe_short_video_demo.dart';

void main() {
  runApp(const MeisheShortVideoDemoApp());
}

class MeisheShortVideoDemoApp extends StatelessWidget {
  const MeisheShortVideoDemoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return const MaterialApp(
      debugShowCheckedModeBanner: false,
      home: MeisheShortVideoDemoPage(),
    );
  }
}
"""
            write_text(main_path, app_content, target_root, report, "Replaced default Flutter screen with Meishe demo entry")
        else:
            report.add_next_check("Flutter: import `MeisheShortVideoDemoPage` from `lib/meishe_short_video_demo.dart` and add it to your app navigation or use it as the home page.")
    else:
        report.add_next_check("Flutter: import `MeisheShortVideoDemoPage` from `lib/meishe_short_video_demo.dart` and add it to your app navigation or use it as the home page.")

    generate_flutter_publish_page(target_root, report)
    generate_flutter_drafts_page(target_root, report)
    update_flutter_widget_test(target_root, report)


def generate_flutter_publish_page(target_root: Path, report: Report) -> None:
    content = """import 'dart:io';

import 'package:flutter/material.dart';
import 'package:nvshortvideo/nvshortvideo.dart';

import 'meishe_short_video_docking.dart';

class MeisheShortVideoPublishPage extends StatefulWidget {
  const MeisheShortVideoPublishPage({super.key, required this.projectInfo});

  final Map<String, dynamic> projectInfo;

  @override
  State<MeisheShortVideoPublishPage> createState() => _MeisheShortVideoPublishPageState();
}

class _MeisheShortVideoPublishPageState extends State<MeisheShortVideoPublishPage> {
  late final TextEditingController _draftController;
  String _status = '请选择保存草稿或导出视频';
  double? _progress;

  String get _projectId => '${widget.projectInfo['projectId'] ?? ''}';

  @override
  void initState() {
    super.initState();
    _draftController = TextEditingController(text: '${widget.projectInfo['draftInfo'] ?? ''}');
    MeisheShortVideoDocking.setVideoCompileEventHandler((event, info) async {
      if (event == NvVideoCompileEvent.progress) {
        final progress = (info['progress'] as num?)?.toDouble();
        if (!mounted) {
          return;
        }
        setState(() {
          _progress = progress == null ? null : progress / 100;
          _status = progress == null ? '导出中...' : '导出中 ${progress.toStringAsFixed(0)}%';
        });
      } else if (event == NvVideoCompileEvent.complete) {
        final outputPath = info['outputPath'];
        final errorCode = info['errorCode'];
        try {
          await MeisheShortVideoDocking.getPublishInfo();
        } catch (_) {
          // Publish info is optional for this generated page.
        }
        if (!mounted) {
          return;
        }
        setState(() {
          _progress = null;
          _status = outputPath == null || '$outputPath'.isEmpty
              ? '导出结束，错误码：$errorCode'
              : '导出成功：$outputPath';
        });
      } else if (event == NvVideoCompileEvent.coverImageSelected) {
        final coverImagePath = info['coverImagePath'];
        if (coverImagePath != null) {
          setState(() => widget.projectInfo['coverImagePath'] = coverImagePath);
        }
      }
    });
  }

  @override
  void dispose() {
    MeisheShortVideoDocking.setVideoCompileEventHandler(null);
    if (_projectId.isNotEmpty) {
      MeisheShortVideoDocking.exitEdit(_projectId);
    }
    _draftController.dispose();
    super.dispose();
  }

  Future<void> _saveDraft() async {
    try {
      setState(() => _status = '正在保存草稿...');
      await MeisheShortVideoDocking.saveDraft(_draftController.text);
      if (mounted) {
        Navigator.of(context).pop();
      }
    } catch (error) {
      if (mounted) {
        setState(() => _status = '保存草稿失败：$error');
      }
    }
  }

  Future<void> _exportVideo() async {
    try {
      setState(() {
        _progress = 0;
        _status = '导出中...';
      });
      await MeisheShortVideoDocking.compileCurrentTimeline();
    } catch (error) {
      if (mounted) {
        setState(() {
          _progress = null;
          _status = '导出失败：$error';
        });
      }
    }
  }

  DateTime _projectDate() {
    for (final key in ['updateTime', 'modifyTime', 'modifiedTime', 'createTime', 'creationTime', 'timestamp']) {
      final value = widget.projectInfo[key];
      if (value is int) {
        return DateTime.fromMillisecondsSinceEpoch(value > 100000000000 ? value : value * 1000);
      }
      if (value is String && value.isNotEmpty) {
        final asInt = int.tryParse(value);
        if (asInt != null) {
          return DateTime.fromMillisecondsSinceEpoch(asInt > 100000000000 ? asInt : asInt * 1000);
        }
        final parsed = DateTime.tryParse(value);
        if (parsed != null) {
          return parsed;
        }
      }
    }
    return DateTime.now();
  }

  String _projectTitle() {
    final draftInfo = _draftController.text.trim();
    if (draftInfo.isNotEmpty) {
      return draftInfo;
    }
    final defaultDescription = '${widget.projectInfo['defaultProjectDescription'] ?? ''}'.trim();
    if (defaultDescription.isNotEmpty && defaultDescription.toLowerCase() != 'draft') {
      return defaultDescription;
    }
    final date = _projectDate();
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '草稿-$month$day';
  }

  String _coverPath() {
    for (final key in ['coverImagePath', 'coverPath', 'thumbnailPath', 'thumbnail']) {
      final value = '${widget.projectInfo[key] ?? ''}'.trim();
      if (value.isNotEmpty) {
        return value;
      }
    }
    return '';
  }

  Widget _buildCover(String coverPath) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(10),
      child: SizedBox(
        width: 96,
        height: 96,
        child: Stack(
          fit: StackFit.expand,
          children: [
            if (coverPath.isEmpty)
              Container(color: const Color(0xFF2A2A2A), child: const Icon(Icons.movie, color: Colors.white54, size: 34))
            else
              Image.file(
                File(coverPath),
                fit: BoxFit.cover,
                errorBuilder: (context, error, stackTrace) => Container(
                  color: const Color(0xFF2A2A2A),
                  child: const Icon(Icons.movie, color: Colors.white54, size: 34),
                ),
              ),
            const Center(
              child: Icon(Icons.play_circle_outline, color: Colors.white, size: 52),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton({
    required String label,
    required VoidCallback onPressed,
    bool primary = true,
  }) {
    return SizedBox(
      height: 48,
      child: TextButton(
        onPressed: onPressed,
        style: TextButton.styleFrom(
          foregroundColor: Colors.white,
          backgroundColor: primary ? const Color(0xFF424954) : const Color(0xFF30343B),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        ),
        child: Text(label, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final coverPath = _coverPath();
    return Scaffold(
      backgroundColor: const Color(0xFF101010),
      resizeToAvoidBottomInset: true,
      body: SafeArea(
        child: GestureDetector(
          behavior: HitTestBehavior.translucent,
          onTap: () => FocusManager.instance.primaryFocus?.unfocus(),
          child: Column(
            children: [
            SizedBox(
              height: 70,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.chevron_left, color: Colors.white, size: 34),
                    ),
                  ),
                  const Text(
                    '作品发布',
                    style: TextStyle(color: Colors.white, fontSize: 25, fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ),
            Expanded(
              child: ListView(
                keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                padding: const EdgeInsets.fromLTRB(24, 24, 24, 42),
                children: [
                  const Text(
                    '温馨提示： 卸载应用后，草稿也会被删除',
                    style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w400),
                  ),
                  const SizedBox(height: 34),
                  Row(
                    children: [
                      _buildCover(coverPath),
                      const SizedBox(width: 26),
                      Expanded(
                        child: Text(
                          _projectTitle(),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w400),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 40),
                  TextField(
                    controller: _draftController,
                    onChanged: (_) => setState(() {}),
                    minLines: 2,
                    maxLines: 3,
                    style: const TextStyle(color: Colors.white, fontSize: 15),
                    decoration: InputDecoration(
                      hintText: '草稿描述',
                      hintStyle: const TextStyle(color: Color(0xFF777777)),
                      filled: true,
                      fillColor: const Color(0xFF1D1D1D),
                      contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: Color(0xFF404040), width: 0.5),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(8),
                        borderSide: const BorderSide(color: Color(0xFF6A707A), width: 0.5),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _status,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Color(0xFFD8D8D8), fontSize: 15, height: 1.4),
                  ),
                  if (_progress != null) ...[
                    const SizedBox(height: 12),
                    LinearProgressIndicator(
                      value: _progress,
                      minHeight: 4,
                      backgroundColor: const Color(0xFF3A3A3A),
                      valueColor: const AlwaysStoppedAnimation<Color>(Colors.white),
                    ),
                  ],
                  const SizedBox(height: 22),
                  _buildActionButton(label: '保存草稿', onPressed: _saveDraft, primary: false),
                  const SizedBox(height: 12),
                  _buildActionButton(label: '导出视频', onPressed: _exportVideo),
                ],
              ),
            ),
            ],
          ),
        ),
      ),
    );
  }
}
"""
    write_text(target_root / "lib" / "meishe_short_video_publish.dart", content, target_root, report, "Generated Flutter publish page")


def update_flutter_widget_test(target_root: Path, report: Report) -> None:
    test_path = target_root / "test" / "widget_test.dart"
    if not test_path.exists():
        return

    current = read_text(test_path)
    if not any(marker in current for marker in ("MyApp", "MeisheShortVideoApp", "MeisheShortVideoDemoApp", "Flutter Demo Home Page")):
        return

    pubspec = read_text(target_root / "pubspec.yaml")
    match = re.search(r"(?m)^name:\s*([A-Za-z0-9_]+)\s*$", pubspec)
    package_name = match.group(1) if match else target_root.name.replace("-", "_")
    content = f"""import 'package:{package_name}/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {{
  testWidgets('shows ShortVideo demo actions', (tester) async {{
    await tester.pumpWidget(const MeisheShortVideoDemoApp());

    expect(find.text('素材上新'), findsOneWidget);
    expect(find.text('功能列表'), findsOneWidget);
    expect(find.text('拍摄'), findsOneWidget);
    expect(find.text('合拍'), findsOneWidget);
    expect(find.text('编辑'), findsOneWidget);
    expect(find.text('草稿'), findsOneWidget);

    // Drain the mock server-configuration timeout used without a native host.
    await tester.pump(const Duration(seconds: 7));
  }});
}}
"""
    write_text(test_path, content, target_root, report, "Updated Flutter widget test for Meishe demo entry")


def generate_flutter_drafts_page(target_root: Path, report: Report) -> None:
    content = """import 'dart:io';

import 'package:flutter/material.dart';
import 'package:nvshortvideo/nvshortvideo.dart';

import 'meishe_short_video_docking.dart';

class MeisheShortVideoDraftsPage extends StatefulWidget {
  const MeisheShortVideoDraftsPage({super.key, required this.videoConfig});

  final NvVideoConfig videoConfig;

  @override
  State<MeisheShortVideoDraftsPage> createState() => _MeisheShortVideoDraftsPageState();
}

class _MeisheShortVideoDraftsPageState extends State<MeisheShortVideoDraftsPage> {
  List<Map<String, dynamic>> _drafts = [];
  bool _isLoading = true;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    MeisheShortVideoDocking.setDraftUpdateHandler(_loadDrafts);
    _loadDrafts();
  }

  @override
  void dispose() {
    MeisheShortVideoDocking.setDraftUpdateHandler(null);
    super.dispose();
  }

  List<Map<String, dynamic>> _normalizeDrafts(dynamic result) {
    final source = result is Map ? result['response'] ?? result['data'] ?? result['drafts'] : result;
    if (source is List) {
      return source.whereType<Map>().map((item) => Map<String, dynamic>.from(item)).toList();
    }
    return <Map<String, dynamic>>[];
  }

  Future<void> _loadDrafts() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final result = await MeisheShortVideoDocking.getDraftList();
      final drafts = _normalizeDrafts(result);
      if (mounted) {
        setState(() {
          _drafts = drafts;
          _isLoading = false;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _isLoading = false;
          _errorMessage = '$error';
        });
      }
    }
  }

  Future<void> _openDraft(Map<String, dynamic> draft) async {
    final projectId = '${draft['projectId'] ?? ''}';
    if (projectId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('草稿缺少 projectId')),
      );
      return;
    }
    await MeisheShortVideoDocking.reeditDraft(projectId, config: widget.videoConfig);
  }

  Future<void> _deleteDraft(Map<String, dynamic> draft) async {
    final projectId = '${draft['projectId'] ?? ''}';
    if (projectId.isEmpty) {
      return;
    }
    final shouldDelete = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('删除草稿'),
        content: const Text('确认删除这个本地草稿？'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('取消')),
          TextButton(onPressed: () => Navigator.of(context).pop(true), child: const Text('删除')),
        ],
      ),
    );
    if (shouldDelete != true) {
      return;
    }
    await MeisheShortVideoDocking.deleteDraft(projectId);
    await _loadDrafts();
  }

  String _draftTitle(Map<String, dynamic> draft) {
    final draftInfo = '${draft['draftInfo'] ?? ''}'.trim();
    if (draftInfo.isNotEmpty) {
      return draftInfo;
    }
    final defaultDescription = '${draft['defaultProjectDescription'] ?? ''}'.trim();
    if (defaultDescription.isNotEmpty && defaultDescription.toLowerCase() != 'draft') {
      return defaultDescription;
    }
    final date = _draftDate(draft);
    final month = date.month.toString().padLeft(2, '0');
    final day = date.day.toString().padLeft(2, '0');
    return '草稿-$month$day';
  }

  DateTime _draftDate(Map<String, dynamic> draft) {
    for (final key in ['updateTime', 'modifyTime', 'modifiedTime', 'createTime', 'creationTime', 'timestamp']) {
      final value = draft[key];
      if (value is int) {
        return DateTime.fromMillisecondsSinceEpoch(value > 100000000000 ? value : value * 1000);
      }
      if (value is String && value.isNotEmpty) {
        final asInt = int.tryParse(value);
        if (asInt != null) {
          return DateTime.fromMillisecondsSinceEpoch(asInt > 100000000000 ? asInt : asInt * 1000);
        }
        final parsed = DateTime.tryParse(value);
        if (parsed != null) {
          return parsed;
        }
      }
    }
    return DateTime.now();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF101010),
      body: SafeArea(
        child: Column(
          children: [
            SizedBox(
              height: 70,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Align(
                    alignment: Alignment.centerLeft,
                    child: IconButton(
                      onPressed: () => Navigator.of(context).pop(),
                      icon: const Icon(Icons.chevron_left, color: Colors.white, size: 34),
                    ),
                  ),
                  const Text(
                    '本地草稿箱',
                    style: TextStyle(color: Colors.white, fontSize: 25, fontWeight: FontWeight.w500),
                  ),
                ],
              ),
            ),
            Expanded(
              child: RefreshIndicator(
                onRefresh: _loadDrafts,
                child: _buildDraftContent(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDraftContent() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: Colors.white));
    }
    if (_errorMessage != null) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          const SizedBox(height: 280),
          Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Text(
                '草稿加载失败：$_errorMessage',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white, fontSize: 18),
              ),
            ),
          ),
        ],
      );
    }
    if (_drafts.isEmpty) {
      return ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 360),
          Center(
            child: Text(
              '没有草稿啦！',
              style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w400),
            ),
          ),
        ],
      );
    }
    return ListView.builder(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(24, 24, 24, 32),
      itemCount: _drafts.length + 1,
      itemBuilder: (context, index) {
        if (index == 0) {
          return const Padding(
            padding: EdgeInsets.only(bottom: 34),
            child: Text(
              '温馨提示： 卸载应用后，草稿也会被删除',
              style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w400),
            ),
          );
        }
        final draft = _drafts[index - 1];
        final coverPath = '${draft['coverImagePath'] ?? ''}';
        return GestureDetector(
          onTap: () => _openDraft(draft),
          onLongPress: () => _deleteDraft(draft),
          child: Padding(
            padding: const EdgeInsets.only(bottom: 22),
            child: Row(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: SizedBox(
                    width: 96,
                    height: 96,
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        if (coverPath.isEmpty)
                          Container(color: const Color(0xFF2A2A2A), child: const Icon(Icons.movie, color: Colors.white54, size: 40))
                        else
                          Image.file(
                            File(coverPath),
                            fit: BoxFit.cover,
                            errorBuilder: (context, error, stackTrace) => Container(
                              color: const Color(0xFF2A2A2A),
                              child: const Icon(Icons.movie, color: Colors.white54, size: 40),
                            ),
                          ),
                        const Center(
                          child: Icon(Icons.play_circle_outline, color: Colors.white, size: 52),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 26),
                Expanded(
                  child: Text(
                    _draftTitle(draft),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w400),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
"""
    write_text(target_root / "lib" / "meishe_short_video_drafts.dart", content, target_root, report, "Generated Flutter drafts page")
