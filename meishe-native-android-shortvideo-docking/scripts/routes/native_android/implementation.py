"""Native Android implementation for Meishe ShortVideo integration."""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import zipfile
from pathlib import Path

from meishe_docking_core import (
    BEGIN,
    ConfigurationApplyStep,
    END,
    LICENSE_HELP,
    IntegrationError,
    Report,
    add_android_gradle_dependency_step,
    assert_no_external_dependency_refs,
    backup_path,
    copy_demo_banner,
    copy_demo_icons,
    copy_file,
    insert_or_replace_block,
    read_text,
    rel,
    write_server_handoff,
    write_text,
)
from .constants import AAR_HELP, ANDROID_STUDIO_PROJECT_HELP, DEMO_BANNER_FILE, MINIMAL_CONFIG_JSON


VERIFIED_COMPOSE_DEPENDENCY_REPLACEMENTS = (
    ("coreKtx", "1.19.0", "1.16.0"),
    ("lifecycleRuntimeKtx", "2.11.0", "2.9.4"),
    ("activityCompose", "1.13.0", "1.8.2"),
)
OPTIONAL_BEAUTY_SHAPE_RESOURCES = (
    "beauty/shapePackage/facemesh/info.json",
    "beauty/shapePackage/warp/info.json",
)


def inspect_native_android_beauty_resources(aar: Path, report: Report) -> tuple[str, ...]:
    """Report optional beauty-shape resources that are not packaged in the selected AAR."""
    try:
        with zipfile.ZipFile(aar) as archive:
            names = tuple(name.lstrip("/") for name in archive.namelist())
    except (OSError, zipfile.BadZipFile):
        missing = OPTIONAL_BEAUTY_SHAPE_RESOURCES
    else:
        missing = tuple(
            resource
            for resource in OPTIONAL_BEAUTY_SHAPE_RESOURCES
            if not any(name.endswith(resource) for name in names)
        )
    if missing:
        report.add_vendor_warning(
            "The selected AAR does not contain optional fixed beauty-shape resources: "
            + ", ".join(f"`{item}`" for item in missing)
            + ". Core capture/edit flows can still run, but Shape/MicroShape beauty categories may be "
            "empty or incomplete. Obtain the matching resource delivery from Meishe before enabling "
            "those categories; do not treat this warning as a network-material failure."
        )
    else:
        report.add_input("Optional Shape/MicroShape beauty resources are present in the selected AAR.")
    return missing


def aar_supports_verified_save_cover(aar: Path) -> bool:
    """Match only the public 2.0.1.0 cover API shape verified by this skill."""
    try:
        with zipfile.ZipFile(aar) as aar_zip:
            classes_jar = aar_zip.read("classes.jar")
        with zipfile.ZipFile(io.BytesIO(classes_jar)) as jar:
            names = set(jar.namelist())
            manager_name = "com/meishe/module/NvModuleManager.class"
            callback_name = "com/meishe/module/NvModuleManager$OnCoverSavedCallBack.class"
            path_utils_name = "com/meishe/engine/util/PathUtils.class"
            if not {manager_name, callback_name, path_utils_name}.issubset(names):
                return False
            manager = jar.read(manager_name)
            callback = jar.read(callback_name)
            path_utils = jar.read(path_utils_name)
            return all(
                marker in payload
                for marker, payload in (
                    (b"saveCover", manager),
                    (b"onCoverSaved", callback),
                    (b"onCoverSaveFailed", callback),
                    (b"getCoverDir", path_utils),
                )
            )
    except (KeyError, OSError, zipfile.BadZipFile):
        return False


def copy_android_demo_banner(app_module: Path, target_root: Path, report: Report) -> None:
    copy_demo_banner(
        app_module / "src" / "main" / "res" / "drawable-nodpi" / DEMO_BANNER_FILE,
        target_root,
        report,
        "Copied demo home banner for native Android",
    )

def copy_android_demo_icons(app_module: Path, target_root: Path, report: Report) -> None:
    copy_demo_icons(
        app_module / "src" / "main" / "res" / "drawable-nodpi",
        target_root,
        report,
        "Copied demo function icon for native Android",
    )


def resolve_aar(args: argparse.Namespace, target_root: Path, report: Report) -> Path:
    candidates: list[Path] = []
    if args.aar_path:
        candidates.append(Path(args.aar_path))
    try:
        app_module = find_app_module(find_android_root(target_root))
    except IntegrationError:
        app_module = None
    if app_module is not None:
        candidates.append(app_module / "libs" / "NvShortVideoCore.aar")
    candidates.extend(target_root.rglob("NvShortVideoCore.aar"))
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.exists() and resolved.suffix.lower() == ".aar":
            report.add_input(f"AAR: `{resolved}`")
            return resolved
    raise IntegrationError(AAR_HELP)


def find_android_root(target_root: Path) -> Path:
    if (target_root / "settings.gradle").exists() or (target_root / "settings.gradle.kts").exists():
        return target_root
    android = target_root / "android"
    if (android / "settings.gradle").exists() or (android / "settings.gradle.kts").exists():
        return android
    raise IntegrationError(ANDROID_STUDIO_PROJECT_HELP)


def find_app_module(android_root: Path) -> Path:
    app = android_root / "app"
    if (app / "build.gradle").exists() or (app / "build.gradle.kts").exists():
        return app
    for build_file in android_root.rglob("build.gradle*"):
        text = read_text(build_file)
        if "com.android.application" in text:
            return build_file.parent
    raise IntegrationError("Android app module not found.")


def find_build_file(module: Path) -> Path:
    for name in ("build.gradle", "build.gradle.kts"):
        path = module / name
        if path.exists():
            return path
    raise IntegrationError(f"Build file not found in {module}")


def find_manifest(app_module: Path) -> Path:
    manifest = app_module / "src" / "main" / "AndroidManifest.xml"
    if not manifest.exists():
        raise IntegrationError(f"AndroidManifest.xml not found at {manifest}")
    return manifest


def parse_android_compile_sdk(build_text: str) -> tuple[int, int] | None:
    release_match = re.search(
        r"compileSdk\s*\{.*?version\s*=\s*release\((\d+)\)(.*?)(?:\n\s*\}|$)",
        build_text,
        flags=re.S,
    )
    if release_match:
        minor_match = re.search(r"minorApiLevel\s*=\s*(\d+)", release_match.group(2))
        return int(release_match.group(1)), int(minor_match.group(1)) if minor_match else 0

    for pattern in (
        r"\bcompileSdk(?:Version)?\s*=\s*(\d+)",
        r"\bcompileSdk(?:Version)?\s+(\d+)",
    ):
        match = re.search(pattern, build_text)
        if match:
            return int(match.group(1)), 0
    return None


def native_android_core_compatibility_version(compile_sdk: tuple[int, int] | None) -> str | None:
    if compile_sdk is None:
        return None
    major, _ = compile_sdk
    if major < 34:
        raise IntegrationError(
            f"Native Android compileSdk {major} is below the supported integration floor 34. "
            "Raise compileSdk to 34 or newer before integrating the ShortVideo AAR."
        )
    if compile_sdk == (36, 1):
        return "1.16.0"
    return None


def align_verified_native_android_compose_dependencies(
    android_root: Path,
    build_file: Path,
    target_root: Path,
    report: Report,
) -> str | None:
    build_text = read_text(build_file)
    compile_sdk = parse_android_compile_sdk(build_text)
    core_version = native_android_core_compatibility_version(compile_sdk)
    if compile_sdk is None:
        report.add_warning(
            "Could not statically resolve native Android compileSdk. The integration will not force an AndroidX Core "
            "version; verify `checkDebugAarMetadata` and Kotlin compilation during the user-approved Gradle build."
        )
        return None

    major, minor = compile_sdk
    display_sdk = f"{major}.{minor}" if minor else str(major)
    report.add_input(f"Native Android compileSdk: `{display_sdk}`")

    catalog = android_root / "gradle" / "libs.versions.toml"
    if catalog.exists() and major < 37:
        catalog_text = read_text(catalog)
        updated_catalog = catalog_text
        changed: list[str] = []
        if compile_sdk == (36, 1):
            for key, incompatible, compatible in VERIFIED_COMPOSE_DEPENDENCY_REPLACEMENTS:
                pattern = rf'(?m)^(\s*{re.escape(key)}\s*=\s*"){re.escape(incompatible)}("\s*)$'
                updated_catalog, count = re.subn(pattern, rf'\g<1>{compatible}\g<2>', updated_catalog)
                if count:
                    changed.append(f"{key} {incompatible} -> {compatible}")

        residual_patterns = (
            r'(?im)^\s*[^#\n]*core[^=\n]*=\s*"1\.19\.0"',
            r'(?im)^\s*[^#\n]*lifecycle[^=\n]*=\s*"2\.11\.0"',
        )
        residual = [pattern for pattern in residual_patterns if re.search(pattern, updated_catalog)]
        if residual:
            raise IntegrationError(
                f"Native Android compileSdk {display_sdk} is incompatible with AndroidX Core 1.19.0 or "
                "Lifecycle 2.11.0. Only the exact verified compileSdk 36.1 Android Studio catalog keys can be "
                "adjusted automatically; align custom or unverified dependencies before integration."
            )
        if updated_catalog != catalog_text:
            write_text(
                catalog,
                updated_catalog,
                target_root,
                report,
                "Aligned verified Compose template dependencies with native Android compileSdk",
            )
            report.add_change(
                "Applied verified Android Studio Compose compatibility: " + ", ".join(changed) + "."
            )

    direct_replacements = (
        ("androidx.core:core-ktx:1.19.0", "androidx.core:core-ktx:1.16.0"),
        ("androidx.lifecycle:lifecycle-runtime-ktx:2.11.0", "androidx.lifecycle:lifecycle-runtime-ktx:2.9.4"),
        ("androidx.activity:activity-compose:1.13.0", "androidx.activity:activity-compose:1.8.2"),
    )
    if compile_sdk == (36, 1):
        updated_build = build_text
        for incompatible, compatible in direct_replacements:
            updated_build = updated_build.replace(incompatible, compatible)
        if updated_build != build_text:
            write_text(
                build_file,
                updated_build,
                target_root,
                report,
                "Aligned direct Compose dependencies with native Android compileSdk",
            )

    if core_version:
        report.add_change(
            f"Selected AndroidX Core `{core_version}` for compileSdk `{display_sdk}`; this avoids the "
            "`PictureInPictureProvider` linkage failure caused by forcing Core 1.8.0."
        )
    else:
        report.add_change(
            f"Preserved host AndroidX resolution for compileSdk `{display_sdk}`; no ShortVideo Core downgrade was added."
        )
    report.add_next_check(
        "Native Android compatibility: the user-approved Debug build must pass `:app:checkDebugAarMetadata` and "
        "Kotlin/Java compilation; treat minimum compile SDK errors separately from ShortVideo AAR/runtime failures."
    )
    return core_version


def package_from_text(text: str) -> str | None:
    for pattern in (
        r'package\s*=\s*"([^"]+)"',
        r'namespace\s+["\']([^"\']+)["\']',
        r'applicationId\s+["\']([^"\']+)["\']',
        r'namespace\s*=\s*["\']([^"\']+)["\']',
        r'applicationId\s*=\s*["\']([^"\']+)["\']',
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def resolve_package(args: argparse.Namespace, manifest: Path, build_file: Path) -> str:
    if args.package_name:
        return args.package_name
    manifest_package = package_from_text(read_text(manifest))
    if manifest_package:
        return manifest_package
    build_package = package_from_text(read_text(build_file))
    if build_package:
        return build_package
    raise IntegrationError("Could not infer package name. Pass --package-name.")


def patch_native_android_app_identity(
    app_module: Path,
    build_file: Path,
    package_name: str | None,
    target_root: Path,
    report: Report,
) -> None:
    build_text = read_text(build_file)
    current_package = package_from_text(build_text)
    if not package_name:
        if current_package and current_package != "com.meishe.duanshipindemo":
            report.add_warning(
                f"Native Android applicationId is `{current_package}`. The official Demo package and bundled Demo license use "
                "`com.meishe.duanshipindemo`; pass `--package-name com.meishe.duanshipindemo` for official-service validation, "
                "or keep the final package and configure its matching license/customer server."
            )
        return

    updated = re.sub(
        r'(\bnamespace\s*(?:=\s*)?)["\'][^"\']+["\']',
        lambda match: f'{match.group(1)}"{package_name}"',
        build_text,
    )
    updated = re.sub(
        r'(\bapplicationId\s*(?:=\s*)?)["\'][^"\']+["\']',
        lambda match: f'{match.group(1)}"{package_name}"',
        updated,
    )
    write_text(build_file, updated, target_root, report, "Set native Android namespace/applicationId")

    if current_package and current_package != package_name:
        old_parts = tuple(current_package.split("."))
        new_parts = tuple(package_name.split("."))
        source_roots = [
            path
            for source_set in (app_module / "src").glob("*")
            for path in (source_set / "java", source_set / "kotlin")
            if path.exists()
        ]
        for source_root in source_roots:
            sources = sorted(source_root.rglob("*.java")) + sorted(source_root.rglob("*.kt"))
            for source in sources:
                relative = source.relative_to(source_root)
                relative_parts = relative.parts
                destination = source
                if relative_parts[: len(old_parts)] == old_parts:
                    destination = source_root.joinpath(*new_parts, *relative_parts[len(old_parts) :])
                content = read_text(source).replace(current_package, package_name)
                write_text(destination, content, target_root, report, "Set native Android source package")
                if destination != source and source.exists():
                    backup_path(source, target_root, report)
                    if not report.dry_run:
                        source.unlink()
                    report.add_change(f"Removed old native Android source path: `{rel(source, target_root)}`")

    report.add_input(f"Native Android package: `{package_name}`")


def merge_manifest_permissions(manifest: Path, target_root: Path, report: Report) -> None:
    text = read_text(manifest)
    permission_block = """<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />
<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />
<uses-permission android:name="android.permission.READ_MEDIA_AUDIO" />
<uses-permission android:name="android.permission.READ_MEDIA_VIDEO" />
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
<uses-permission android:name="android.permission.VIBRATE" />
<uses-permission android:name="android.permission.WAKE_LOCK" />
<uses-permission android:name="android.permission.ACCESS_NOTIFICATION_POLICY" />
<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />
<uses-permission android:name="android.permission.CHANGE_WIFI_STATE" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.EXPAND_STATUS_BAR" />"""
    xml_block = f"<!-- {BEGIN} -->\n{permission_block}\n<!-- {END} -->"
    if f"<!-- {BEGIN} -->" in text:
        text = re.sub(r"<!-- BEGIN MEISHE_DUANSHIPIN_DOCKING -->.*?<!-- END MEISHE_DUANSHIPIN_DOCKING -->", xml_block, text, flags=re.S)
    elif "<application" in text:
        text = text.replace("<application", xml_block + "\n\n    <application", 1)
    else:
        text = text.replace("</manifest>", xml_block + "\n</manifest>")
    write_text(manifest, text, target_root, report, "Merged ShortVideo permissions")


def get_application_name(manifest_text: str) -> str | None:
    match = re.search(r"<application\b([^>]*)>", manifest_text, re.S)
    if not match:
        return None
    attrs = match.group(1)
    name = re.search(r'android:name\s*=\s*"([^"]+)"', attrs)
    return name.group(1) if name else None


def set_application_name(manifest: Path, app_name: str, target_root: Path, report: Report) -> None:
    text = read_text(manifest)
    if get_application_name(text):
        return
    text = re.sub(r"(<application\b[^>]*)\s*/>", r"\1>", text, count=1, flags=re.S)
    def repl(match: re.Match[str]) -> str:
        return f'<application{match.group(1)}\n        android:name="{app_name}">'
    new_text = re.sub(r"<application\b([^>]*)>", repl, text, count=1, flags=re.S)
    if "</application>" not in new_text:
        new_text = new_text.replace("</manifest>", "    </application>\n</manifest>", 1)
    write_text(manifest, new_text, target_root, report, "Set generated Application class in manifest")


def java_path_for_package(app_module: Path, package_name: str, class_name: str) -> Path:
    return app_module / "src" / "main" / "java" / Path(*package_name.split(".")) / f"{class_name}.java"


def create_native_android_feature_config(app_module: Path, package_name: str, target_root: Path, report: Report) -> Path:
    helper_package = f"{package_name}.meishe"
    path = app_module / "src" / "main" / "java" / Path(*helper_package.split(".")) / "MeisheFeatureConfig.java"
    if path.exists():
        report.add_change(f"Retained user-editable native Android feature configuration: `{rel(path, target_root)}`")
        return path

    content = f"""package {helper_package};

import com.meishe.config.NvAlbumConfig;
import com.meishe.config.NvBeautyConfig;
import com.meishe.config.NvCaptureConfig;
import com.meishe.config.NvCompileConfig;
import com.meishe.config.NvDualConfig;
import com.meishe.config.NvEditConfig;
import com.meishe.config.NvTemplateConfig;
import com.meishe.config.NvTimePair;
import com.meishe.config.NvVideoConfig;

import java.util.Arrays;
import java.util.HashSet;
import java.util.List;

/**
 * 原生 Android 专属配置。只修改本文件，不要套用 iOS、React Native 或 Flutter 的枚举名。
 * SDK 根据有序菜单集合创建控件：删除集合项会删除入口并重排其余 UI，禁止写入 null 作为占位。
 */
public final class MeisheFeatureConfig {{
    private MeisheFeatureConfig() {{
    }}

    public static NvVideoConfig apply(NvVideoConfig config) {{
        if (config == null) {{
            config = new NvVideoConfig();
        }}

        // 全局颜色使用 #RRGGBB。
        config.setPrimaryColor("#FC3E5A");
        config.setBackgroundColor("#111111");
        config.setPanelBackgroundColor("#1F1F1F");
        config.setTextColor("#FFFFFF");
        config.setSecondaryTextColor("#9E9E9E");
        // 是否显示设备本地音乐入口；读取本地音乐仍受系统权限约束。
        config.setEnableLocalMusic(false);
        // shadowColor/shadowOffset 由 NvVideoConfig 提供；修改前应使用当前 AAR 的 NvShadowOffsetConfig 类型。

        NvAlbumConfig album = config.getAlbumConfig();
        if (album == null) {{
            album = new NvAlbumConfig();
            config.setAlbumConfig(album);
        }}
        // 相册顶部标签：0=全部，1=视频，2=图片。
        album.setType(0);
        // 相册最大选择数，必须大于 0。
        album.setMaxSelectCount(50);
        // 编辑素材选择页是否显示一键成片；不会自动删除拍摄页模板模式。
        album.setUseAutoCut(true);

        NvTemplateConfig template = config.getTemplateConfig();
        if (template == null) {{
            template = new NvTemplateConfig();
            config.setTemplateConfig(template);
        }}
        // 一键成片/自适应模板最大可选片段数，必须大于 0。
        template.setMaxSelectCount(50);
        // 模板页面是否显示一键成片。
        template.setUseAutoCut(true);
        // 一键成片推荐模板最大数量，必须大于 0。
        template.setMaxRecommandTemplateCount(20);

        NvCaptureConfig capture = config.getCaptureConfig();
        if (capture == null) {{
            capture = new NvCaptureConfig();
            config.setCaptureConfig(capture);
        }}
        // 拍摄右侧菜单，有序。删除 speed 可去掉快慢速，后续入口自动上移。
        // 当前已验证原生 Android AAR 未公开 matting 枚举，禁止照搬 iOS/RN/Flutter 的抠像项。
        capture.setCaptureMenuItems(Arrays.asList(
                NvCaptureConfig.NvCaptureMenuItem.device,
                NvCaptureConfig.NvCaptureMenuItem.speed,
                NvCaptureConfig.NvCaptureMenuItem.timer,
                NvCaptureConfig.NvCaptureMenuItem.beauty,
                NvCaptureConfig.NvCaptureMenuItem.makeup,
                NvCaptureConfig.NvCaptureMenuItem.prop,
                NvCaptureConfig.NvCaptureMenuItem.flashlight,
                NvCaptureConfig.NvCaptureMenuItem.filter,
                NvCaptureConfig.NvCaptureMenuItem.original
        ));
        // AAR 还公开 segment 枚举，但当前官方功能配置文档未定义其行为，默认不启用，不能猜测为抠像。
        // 拍摄底部模式，有序且不能为空；template 存在时必须放在最后。
        capture.setCaptureBottomMenuItems(Arrays.asList(
                NvCaptureConfig.NvCaptureBottomMenuItem.image,
                NvCaptureConfig.NvCaptureBottomMenuItem.video,
                NvCaptureConfig.NvCaptureBottomMenuItem.smart,
                NvCaptureConfig.NvCaptureBottomMenuItem.template
        ));
        // 默认拍摄模式必须同时存在于 captureBottomMenuItems。
        capture.setDefaultBottomMenuSelectItem(NvCaptureConfig.NvCaptureBottomMenuItem.video);
        // 默认摄像头：0=后置，1=前置。
        capture.setCaptureDeviceIndex(1);
        // 拍摄预览分辨率只支持 720/1080。
        capture.setResolution(NvCompileConfig.NvVideoPreviewResolution.NvVideoPreviewResolution_1080);
        // 是否忽略设备旋转信息。
        capture.setIgnoreVideoRotation(true);
        // 照片进入编辑后的默认时长，单位毫秒，必须大于 0。
        capture.setImageDuration(3000);
        // 拍照完成、进入编辑前是否把原图保存到系统相册。
        capture.setAutoSavePhotograph(false);
        // 普通录制档位，单位毫秒；每组必须满足 0 <= minDuration < maxDuration。
        capture.setTimeRanges(Arrays.asList(timePair(2000, 15000), timePair(2000, 60000)));
        // 快拍时长范围，单位毫秒。
        capture.setSmartTimeRange(timePair(2000, 60000));
        // 滤镜默认强度，官方配置范围为 0.0-1.0。
        capture.setFilterDefaultValue(0.8);
        // 是否在拍摄页显示相册快捷入口。
        capture.setEnableCaptureAlbum(false);
        // true 会在进入拍摄时自动关闭原声/麦克风。
        capture.setAutoDisablesMic(false);
        // 拍摄帧率；Android 超过 30 时实际录制可能达不到预设值。
        capture.setFps(30);
        // recordConfiguration 支持 bitrate、gopsize、video encoder name；未知底层键禁止写入。

        // 美颜分类与子项。删除数组项会删除对应面板入口；values() 表示保留当前 AAR 的全部公开项。
        NvBeautyConfig beauty = new NvBeautyConfig();
        beauty.setCategoricalArray(Arrays.asList(NvBeautyConfig.NvBeautyCategorical.values()));
        beauty.setBeautyEffectArray(Arrays.asList(NvBeautyConfig.NvBeautyEffect.values()));
        beauty.setBeautyShapeArray(Arrays.asList(NvBeautyConfig.NvBeautyShape.values()));
        beauty.setBeautyMicroShapeArray(Arrays.asList(NvBeautyConfig.NvBeautyMicroShape.values()));
        beauty.setBeautyAdjustArray(Arrays.asList(NvBeautyConfig.NvBeautyAdjust.values()));
        capture.setBeautyConfig(beauty);

        // 合拍右侧菜单独立于普通拍摄菜单，有序；删除项后合拍页面同步重排。
        capture.setDualMenuItems(Arrays.asList(
                NvCaptureConfig.NvCaptureMenuItem.device,
                NvCaptureConfig.NvCaptureMenuItem.speed,
                NvCaptureConfig.NvCaptureMenuItem.timer,
                NvCaptureConfig.NvCaptureMenuItem.beauty,
                NvCaptureConfig.NvCaptureMenuItem.makeup,
                NvCaptureConfig.NvCaptureMenuItem.prop,
                NvCaptureConfig.NvCaptureMenuItem.flashlight,
                NvCaptureConfig.NvCaptureMenuItem.filter,
                NvCaptureConfig.NvCaptureMenuItem.original,
                NvCaptureConfig.NvCaptureMenuItem.dualtype
        ));
        NvDualConfig dual = new NvDualConfig();
        // 小窗左/上边距与底图宽/高的比例，建议保持在 0.0-1.0。
        dual.setLeft(17.0 / 375.0);
        dual.setTop(18.0 / 666.67);
        // 小窗短边与底图宽度比例，必须大于 0 且不宜超过 1。
        dual.setLimitWidth(153.5 / 375.0);
        // 默认合拍样式必须存在于 supportedTypes。
        dual.setDefaultType(NvDualConfig.NvDualType.leftRight);
        dual.setSupportedTypes(Arrays.asList(
                NvDualConfig.NvDualType.leftRight,
                NvDualConfig.NvDualType.topDown,
                NvDualConfig.NvDualType.leftRect,
                NvDualConfig.NvDualType.leftCircle,
                NvDualConfig.NvDualType.topCircle
        ));
        // 是否自动禁用麦克风；该 AAR 未公开 RN/Flutter 的 muteOriginal 字段。
        dual.setAutoDisablesMic(false);
        capture.setDualConfig(dual);

        NvEditConfig edit = config.getEditConfig();
        if (edit == null) {{
            edit = new NvEditConfig();
            config.setEditConfig(edit);
        }}
        // 编辑右侧菜单，有序。删除 text 会删除文字入口及其下级功能，后续入口自动上移，不留空白。
        // release/download 关系到发布/保存入口，删除前必须确认仍有可达的发布与导出流程。
        edit.setEditMenuItems(Arrays.asList(
                NvEditConfig.NvEditMenuItem.release,
                NvEditConfig.NvEditMenuItem.download,
                NvEditConfig.NvEditMenuItem.edit,
                NvEditConfig.NvEditMenuItem.text,
                NvEditConfig.NvEditMenuItem.sticker,
                NvEditConfig.NvEditMenuItem.effect,
                NvEditConfig.NvEditMenuItem.filter,
                NvEditConfig.NvEditMenuItem.caption,
                NvEditConfig.NvEditMenuItem.audio,
                NvEditConfig.NvEditMenuItem.record
        ));
        // 编辑预览分辨率、帧率；预览配置不等于最终导出配置。
        edit.setResolution(NvCompileConfig.NvVideoPreviewResolution.NvVideoPreviewResolution_1080);
        edit.setFps(30);
        // 特效、录音最小时长以及图片默认时长，单位毫秒，均不得为负数。
        edit.setMinEffectDuration(100);
        edit.setMinAudioDuration(10000);
        edit.setDefaultImageDuration(4000);
        // 字幕默认颜色与可选颜色，格式为 #RRGGBB。
        edit.setCaptionColor("#FFFFFF");
        edit.setCaptionColorList(Arrays.asList("#FFFFFF", "#000000", "#0099F6", "#50C23B", "#FFC840", "#FF8500", "#FF3350", "#E40069", "#B200C0", "#F8808A", "#FEBF7C", "#262626", "#363636", "#555555", "#737373", "#989898", "#B2B2B2", "#C7C7C7", "#DBDBDB", "#F0F0F0"));
        // 字幕样式集合：无、背景、半透明背景、描边。
        edit.setSupportedCaptionStyles(Arrays.asList(NvEditConfig.NvImageCaptionStyle.values()));
        // firstAsset 按首个素材决定画幅；fixed 使用 editMode。
        edit.setEditModeSource(NvEditConfig.NvEditModeSource.firstAsset);
        edit.setEditMode(NvEditConfig.NvEditMode.NvEditMode9v16);
        // 用户可选画幅列表。当前 AAR 的单元素列表会在 SDK 中失败，生成校验会事先拒绝；
        // 自定义多元素列表也不作稳定承诺，只设置初始画幅时优先修改 editModeSource/editMode。
        edit.setSupportedEditModes(Arrays.asList(NvEditConfig.NvEditMode.values()));
        // 编辑滤镜默认强度 0.0-1.0；最大音量稳定范围 (0,8]。
        edit.setFilterDefaultValue(0.5f);
        edit.setMaxVolume(8f);
        // true 会移除反复、慢动作时间特效能力。
        edit.setDisableTimeEffect(false);
        // bubbleConfig 可配置编辑图标、时长图标、标题主题、背景色和背景模糊样式；需要真实资源时再设置。

        NvCompileConfig compile = config.getCompileConfig();
        if (compile == null) {{
            compile = new NvCompileConfig();
            config.setCompileConfig(compile);
        }}
        // 导出分辨率支持 720/1080/4K；4K 必须经过设备内存和性能验证。
        compile.setResolution(NvCompileConfig.NvVideoCompileResolution.NvVideoCompileResolution_1080);
        compile.setFps(30);
        // bitrate != -1 时优先使用精确码率；-1 时使用 bitrateGrade。
        compile.setBitrateGrade(NvCompileConfig.NvsCompileVideoBitrateGrade.NvsCompileBitrateGradeLow);
        compile.setBitrate(-1);
        // 封面图片格式以及导出后是否保存到系统相册。
        compile.setImageType(NvCompileConfig.NvExportImageType.NvExportImageTypePNG);
        compile.setAutoSaveVideo(true);
        // watermarkConfig/coverWatermarkConfig 需要真实 NvImageConfig、尺寸、偏移和位置，默认不设置。
        // configure 可设置底层合成键值；未知键禁止写入，bitrate/fps 冲突时以上显式字段优先。

        // modelConfig 路径必须指向与当前 AAR 匹配的真实模型文件，不得伪造或跨版本复制。
        // 可配置：use240、fakeface、face、face240、avatar、makeup、hand、humanseg、eyecontour、
        // advancedBeautyModel、faceCommonModel、autoCutActivity、autoCutFaceAttri、autoCutFace、
        // autoCutImagecls、autoCutPf、autoCutPhoto。

        validate(config);
        return config;
    }}

    public static void validate(NvVideoConfig config) {{
        NvCaptureConfig capture = config.getCaptureConfig();
        List<NvCaptureConfig.NvCaptureBottomMenuItem> bottom = capture.getCaptureBottomMenuItems();
        if (bottom == null || bottom.isEmpty()) {{
            throw new IllegalArgumentException("captureBottomMenuItems must contain at least one capture mode");
        }}
        if (!bottom.contains(capture.getDefaultBottomMenuSelectItem())) {{
            throw new IllegalArgumentException("defaultBottomMenuSelectItem must exist in captureBottomMenuItems");
        }}
        int templateIndex = bottom.indexOf(NvCaptureConfig.NvCaptureBottomMenuItem.template);
        if (templateIndex >= 0 && templateIndex != bottom.size() - 1) {{
            throw new IllegalArgumentException("template must be the last capture bottom menu item");
        }}
        assertUnique("captureMenuItems", capture.getCaptureMenuItems());
        assertUnique("captureBottomMenuItems", bottom);
        assertUnique("dualMenuItems", capture.getDualMenuItems());
        assertUnique("editMenuItems", config.getEditConfig().getEditMenuItems());
        if (config.getAlbumConfig().getMaxSelectCount() <= 0 || config.getTemplateConfig().getMaxSelectCount() <= 0) {{
            throw new IllegalArgumentException("album/template maxSelectCount must be greater than 0");
        }}
        NvEditConfig edit = config.getEditConfig();
        if (edit.getMaxVolume() <= 0f || edit.getMaxVolume() > 8f) {{
            throw new IllegalArgumentException("editConfig.maxVolume must be greater than 0 and no greater than 8");
        }}
        List<NvEditConfig.NvEditMode> supportedEditModes = edit.getSupportedEditModes();
        if (supportedEditModes != null && supportedEditModes.size() == 1) {{
            throw new IllegalArgumentException(
                    "The verified native Android AAR rejects a single-element supportedEditModes list; use editModeSource/editMode for the initial aspect ratio"
            );
        }}
    }}

    private static void assertUnique(String name, List<?> items) {{
        if (items != null && new HashSet<>(items).size() != items.size()) {{
            throw new IllegalArgumentException(name + " contains duplicate menu items");
        }}
    }}

    private static NvTimePair timePair(long minDuration, long maxDuration) {{
        NvTimePair pair = new NvTimePair();
        pair.setMinDuration(minDuration);
        pair.setMaxDuration(maxDuration);
        return pair;
    }}
}}
"""
    write_text(path, content, target_root, report, "Generated user-editable native Android feature configuration")
    report.add_user_configuration(
        f"Native Android feature entry: edit `{rel(path, target_root)}`. Menu lists are ordered and drive SDK UI reflow; the skill preserves this file on later runs."
    )
    return path


def create_helper(app_module: Path, package_name: str, target_root: Path, report: Report) -> None:
    helper_package = f"{package_name}.meishe"
    helper = app_module / "src" / "main" / "java" / Path(*helper_package.split(".")) / "MeisheShortVideoDocking.java"
    content = f"""package {helper_package};

import android.app.Activity;
import android.app.Application;
import android.os.Bundle;
import android.content.Intent;

import com.meishe.config.NvVideoConfig;
import com.meishe.module.ModuleConstants;
import com.meishe.module.NvModuleManager;
import com.meishe.module.bean.NvMusicInfo;
import com.meishe.module.interfaces.ModuleManager;

public final class MeisheShortVideoDocking {{
    public static final String LICENSE_PATH = "assets:/meishesdk.lic";
    public static final String CONFIG_PATH = "assets:/config/config_example.json";

    private MeisheShortVideoDocking() {{
    }}

    public static void init(Application application) {{
        NvModuleManager.get().init(application);
        NvModuleManager.get().initSdk(LICENSE_PATH);
        NvModuleManager.get().initModel();
        NvModuleManager.get().initConfig(CONFIG_PATH);
        registerPublishCallback();
    }}

    private static void registerPublishCallback() {{
        NvModuleManager.get().setModuleManagerCallback((activity, needSaveDraft, needSaveCover, needSaveVideo, videoPath) -> {{
            Bundle bundle = new Bundle();
            bundle.putBoolean("intent_key_can_save_draft", needSaveDraft);
            bundle.putBoolean("intent_key_can_save_cover", needSaveCover);
            bundle.putBoolean("intent_key_can_save_video", needSaveVideo);
            bundle.putString("intent_key_video_path", videoPath);
            Intent intent = new Intent(activity, MeisheShortVideoPublishActivity.class);
            intent.putExtras(bundle);
            activity.startActivity(intent);
        }});
    }}

    public static NvVideoConfig getConfigOrDefault() {{
        NvVideoConfig config = NvModuleManager.get().getConfig();
        return MeisheFeatureConfig.apply(config == null ? new NvVideoConfig() : config);
    }}

    public static void downloadPrefabricatedMaterial(Activity activity, ModuleManager.OnAssetsRequestListener listener) {{
        NvModuleManager.get().downloadPrefabricatedMaterial(activity, listener);
    }}

    public static void openCapture(Activity activity, NvVideoConfig config, NvMusicInfo musicInfo, ModuleManager.OnAssetsRequestListener listener) {{
        NvModuleManager.get().openCapture(activity, config == null ? getConfigOrDefault() : config, musicInfo, listener);
    }}

    public static void openEdit(Activity activity, NvVideoConfig config, ModuleManager.OnAssetsRequestListener listener) {{
        NvModuleManager.get().openEdit(activity, config == null ? getConfigOrDefault() : config, listener);
    }}

    public static void startDualCapture(Activity activity, NvVideoConfig config, ModuleManager.OnAssetsRequestListener listener) {{
        NvModuleManager.get().startDualCapture(activity, config == null ? getConfigOrDefault() : config, listener);
    }}

    public static void openDraft(Activity activity, NvVideoConfig config) {{
        NvModuleManager.get().openDraftActivity(activity, config == null ? getConfigOrDefault() : config, ModuleConstants.DRAFT_ACTIVITY);
    }}
}}
"""
    write_text(helper, content, target_root, report, "Generated native Android helper")


def create_native_demo_activity(app_module: Path, package_name: str, target_root: Path, report: Report) -> None:
    helper_package = f"{package_name}.meishe"
    activity = app_module / "src" / "main" / "java" / Path(*helper_package.split(".")) / "MeisheShortVideoDemoActivity.java"
    content = f"""package {helper_package};

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.ArrayList;
import java.util.List;

import com.meishe.module.interfaces.ModuleManager;

public class MeisheShortVideoDemoActivity extends Activity {{
    private TextView statusView;
    private TextView retryView;
    private View loadingOverlay;
    private final List<View> actionRows = new ArrayList<>();
    private boolean isMaterialRequestInProgress;
    private boolean isMaterialReady;
    private Runnable pendingMaterialAction;

    private final ModuleManager.OnAssetsRequestListener assetsRequestListener = isSuccess -> runOnUiThread(() -> {{
        isMaterialRequestInProgress = false;
        isMaterialReady = isSuccess;
        if (isSuccess) {{
            setLoading(false, "", false);
            Runnable action = pendingMaterialAction;
            pendingMaterialAction = null;
            if (action != null) {{
                action.run();
            }}
        }} else {{
            pendingMaterialAction = null;
            setLoading(true, "素材准备失败，请检查权限、网络和服务配置。", true);
        }}
    }});

    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        getWindow().setStatusBarColor(Color.parseColor("#171D26"));

        FrameLayout scene = new FrameLayout(this);
        scene.setBackgroundColor(Color.parseColor("#171D26"));
        ScrollView scrollView = new ScrollView(this);
        scrollView.setFillViewport(true);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int horizontalPadding = dp(24);
        root.setPadding(horizontalPadding, dp(34), horizontalPadding, dp(56));
        scrollView.addView(root, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        TextView titleView = new TextView(this);
        titleView.setText("素材上新");
        titleView.setTextColor(Color.WHITE);
        titleView.setTextSize(30);
        titleView.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        root.addView(titleView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        ImageView bannerView = new ImageView(this);
        bannerView.setImageResource(getResources().getIdentifier("meishe_home_banner", "drawable", getPackageName()));
        bannerView.setScaleType(ImageView.ScaleType.CENTER_CROP);
        bannerView.setBackground(rounded("#222833", 12));
        bannerView.setClipToOutline(true);
        LinearLayout.LayoutParams bannerParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, screenHeightPercent(0.18f, 108, 148));
        bannerParams.topMargin = dp(12);
        root.addView(bannerView, bannerParams);

        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        panel.setPadding(dp(20), dp(22), dp(20), dp(16));
        panel.setBackground(rounded("#222832", 14));
        LinearLayout.LayoutParams panelParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        panelParams.topMargin = dp(18);
        root.addView(panel, panelParams);

        TextView hintView = new TextView(this);
        hintView.setText("请选择所需的功能");
        hintView.setTextColor(Color.WHITE);
        hintView.setTextSize(16);
        panel.addView(hintView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        TextView listTitleView = new TextView(this);
        listTitleView.setText("功能列表");
        listTitleView.setTextColor(Color.WHITE);
        listTitleView.setTextSize(23);
        listTitleView.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        LinearLayout.LayoutParams listTitleParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        listTitleParams.topMargin = dp(6);
        panel.addView(listTitleView, listTitleParams);

        addActionRow(panel, "meishe_icon_capture", "拍摄", () -> runAfterMaterials("打开拍摄", () -> MeisheShortVideoDocking.openCapture(this, null, null, assetsRequestListener)));
        addActionRow(panel, "meishe_icon_dual_capture", "合拍", () -> runAfterMaterials("打开合拍", () -> MeisheShortVideoDocking.startDualCapture(this, null, assetsRequestListener)));
        addActionRow(panel, "meishe_icon_edit", "编辑", () -> runAfterMaterials("打开编辑", () -> MeisheShortVideoDocking.openEdit(this, null, assetsRequestListener)));
        addActionRow(panel, "meishe_icon_draft", "草稿", () -> runAfterMaterials("打开草稿", () -> MeisheShortVideoDocking.openDraft(this, null)));

        scene.addView(scrollView, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        loadingOverlay = createLoadingOverlay();
        scene.addView(loadingOverlay, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        setContentView(scene);
        downloadMaterials("素材准备中...", null);
    }}

    private View createLoadingOverlay() {{
        LinearLayout overlay = new LinearLayout(this);
        overlay.setOrientation(LinearLayout.VERTICAL);
        overlay.setGravity(Gravity.CENTER);
        overlay.setBackgroundColor(Color.parseColor("#CC101317"));
        overlay.setPadding(dp(28), dp(28), dp(28), dp(28));

        statusView = new TextView(this);
        statusView.setTextColor(Color.WHITE);
        statusView.setTextSize(17);
        statusView.setGravity(Gravity.CENTER);
        overlay.addView(statusView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        retryView = new TextView(this);
        retryView.setText("重试");
        retryView.setGravity(Gravity.CENTER);
        retryView.setTextColor(Color.WHITE);
        retryView.setTextSize(16);
        retryView.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        retryView.setBackground(rounded("#3F4652", 24));
        retryView.setOnClickListener(view -> downloadMaterials("素材准备中...", null));
        LinearLayout.LayoutParams retryParams = new LinearLayout.LayoutParams(dp(120), dp(48));
        retryParams.topMargin = dp(18);
        overlay.addView(retryView, retryParams);
        return overlay;
    }}

    private void addActionRow(LinearLayout root, String iconName, String text, Runnable action) {{
        LinearLayout row = new LinearLayout(this);
        row.setGravity(Gravity.CENTER_VERTICAL);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(dp(22), 0, dp(20), 0);
        row.setBackground(rounded("#424954", 25));
        row.setOnClickListener(view -> {{
            if (isMaterialReady) {{
                action.run();
            }}
        }});

        ImageView iconView = new ImageView(this);
        iconView.setImageResource(getResources().getIdentifier(iconName, "drawable", getPackageName()));
        row.addView(iconView, new LinearLayout.LayoutParams(dp(24), dp(24)));

        TextView labelView = new TextView(this);
        labelView.setText(text);
        labelView.setTextColor(Color.parseColor("#E8EAEE"));
        labelView.setTextSize(18);
        labelView.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        LinearLayout.LayoutParams labelParams = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1);
        labelParams.leftMargin = dp(18);
        row.addView(labelView, labelParams);

        TextView chevronView = new TextView(this);
        chevronView.setText("›");
        chevronView.setTextColor(Color.parseColor("#B5BBC5"));
        chevronView.setTextSize(23);
        row.addView(chevronView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout.LayoutParams rowParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(50));
        rowParams.topMargin = dp(10);
        root.addView(row, rowParams);
        actionRows.add(row);
    }}

    private void runAfterMaterials(String label, Runnable action) {{
        if (isMaterialReady) {{
            runSdkAction(label, action);
            return;
        }}
        downloadMaterials("素材准备中...", () -> runSdkAction(label, action));
    }}

    private void downloadMaterials(String message, Runnable afterReady) {{
        if (isMaterialReady) {{
            setLoading(false, "", false);
            if (afterReady != null) {{
                afterReady.run();
            }}
            return;
        }}
        if (isMaterialRequestInProgress) {{
            pendingMaterialAction = afterReady;
            setLoading(true, "素材准备中...", false);
            return;
        }}
        isMaterialRequestInProgress = true;
        pendingMaterialAction = afterReady;
        setLoading(true, message, false);
        try {{
            MeisheShortVideoDocking.downloadPrefabricatedMaterial(this, assetsRequestListener);
            statusView.postDelayed(() -> {{
                if (isMaterialRequestInProgress) {{
                    statusView.setText("素材仍在准备中，请检查网络和服务配置。");
                }}
            }}, 60000);
        }} catch (Throwable error) {{
            isMaterialRequestInProgress = false;
            pendingMaterialAction = null;
            setLoading(true, "素材准备失败：" + error.getMessage(), true);
        }}
    }}

    private void runSdkAction(String label, Runnable action) {{
        try {{
            action.run();
        }} catch (Throwable error) {{
            setLoading(true, label + "失败：" + error.getMessage(), true);
        }}
    }}

    private void setLoading(boolean isLoading, String message, boolean canRetry) {{
        setActionsEnabled(!isLoading && isMaterialReady);
        loadingOverlay.setVisibility(isLoading ? View.VISIBLE : View.GONE);
        if (statusView != null) {{
            statusView.setText(message);
        }}
        if (retryView != null) {{
            retryView.setVisibility(canRetry ? View.VISIBLE : View.GONE);
        }}
    }}

    private void setActionsEnabled(boolean enabled) {{
        for (View actionRow : actionRows) {{
            actionRow.setEnabled(enabled);
            actionRow.setAlpha(enabled ? 1f : 0.55f);
        }}
    }}

    private GradientDrawable rounded(String color, int radiusDp) {{
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(Color.parseColor(color));
        drawable.setCornerRadius(dp(radiusDp));
        return drawable;
    }}

    private int screenHeightPercent(float percent, int minDp, int maxDp) {{
        int value = (int) (getResources().getDisplayMetrics().heightPixels * percent);
        return Math.max(dp(minDp), Math.min(dp(maxDp), value));
    }}

    private int dp(int value) {{
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }}
}}
"""
    write_text(activity, content, target_root, report, "Generated native Android demo activity")


def create_native_publish_activity(
    app_module: Path,
    package_name: str,
    target_root: Path,
    report: Report,
    supports_save_cover: bool,
) -> None:
    helper_package = f"{package_name}.meishe"
    activity = app_module / "src" / "main" / "java" / Path(*helper_package.split(".")) / "MeisheShortVideoPublishActivity.java"
    cover_import = "import com.meishe.engine.util.PathUtils;\n" if supports_save_cover else ""
    cover_field = "    private ImageView coverView;\n" if supports_save_cover else ""
    cover_declaration = "coverView = new ImageView(this);" if supports_save_cover else "ImageView coverView = new ImageView(this);"
    save_cover_button = """
        TextView saveCover = actionButton("保存封面", false);
        saveCover.setVisibility(getIntent().getBooleanExtra("intent_key_can_save_cover", true) ? View.VISIBLE : View.GONE);
        saveCover.setOnClickListener(view -> saveCover());
        LinearLayout.LayoutParams coverParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
        coverParams.topMargin = dp(12);
        content.addView(saveCover, coverParams);
""" if supports_save_cover else ""
    save_cover_method = """
    private void saveCover() {
        setStatus("正在保存封面...");
        NvModuleManager.get().saveCover(
                PathUtils.getCoverDir(),
                String.valueOf(System.currentTimeMillis()),
                0L,
                false,
                new NvModuleManager.OnCoverSavedCallBack() {
                    @Override
                    public void onCoverSaved(String path) {
                        runOnUiThread(() -> {
                            if (!TextUtils.isEmpty(path) && BitmapFactory.decodeFile(path) != null) {
                                coverView.setImageBitmap(BitmapFactory.decodeFile(path));
                            }
                            setStatus("封面已保存：" + path);
                        });
                    }

                    @Override
                    public void onCoverSaveFailed() {
                        runOnUiThread(() -> setStatus("封面保存失败"));
                    }
                }
        );
    }

""" if supports_save_cover else ""
    content = f"""package {helper_package};

import android.app.Activity;
import android.graphics.BitmapFactory;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.text.TextUtils;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

import java.util.Calendar;
import java.util.Locale;

import com.meicam.sdk.NvsTimeline;
import com.meishe.draft.DraftManager;
{cover_import}import com.meishe.libbase.manager.AppManager;
import com.meishe.module.NvModuleManager;
import com.meishe.module.bean.NvPublishInfo;

public class MeisheShortVideoPublishActivity extends Activity {{
    private EditText draftInput;
    private TextView statusView;
    private TextView projectTitleView;
    private ProgressBar progressBar;
{cover_field}    private NvPublishInfo publishInfo;

    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        publishInfo = getPublishInfoSafely();
        setContentView(buildContentView());
    }}

    @Override
    public void onBackPressed() {{
        exitToHome();
    }}

    private View buildContentView() {{
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(16, 16, 16));
        root.addView(buildTopBar(), new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(70)));

        ScrollView scrollView = new ScrollView(this);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(24), dp(24), dp(24), dp(42));
        scrollView.addView(content, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        root.addView(scrollView, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        TextView notice = text("温馨提示： 卸载应用后，草稿也会被删除", 20, Typeface.NORMAL);
        content.addView(notice, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout projectRow = new LinearLayout(this);
        projectRow.setOrientation(LinearLayout.HORIZONTAL);
        projectRow.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout.LayoutParams rowParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        rowParams.topMargin = dp(34);
        content.addView(projectRow, rowParams);

        projectRow.addView(buildCoverView(), new LinearLayout.LayoutParams(dp(96), dp(96)));
        projectTitleView = text(projectTitle(), 22, Typeface.NORMAL);
        projectTitleView.setMaxLines(2);
        LinearLayout.LayoutParams titleParams = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        titleParams.leftMargin = dp(26);
        projectRow.addView(projectTitleView, titleParams);

        draftInput = new EditText(this);
        draftInput.setTextColor(Color.WHITE);
        draftInput.setHintTextColor(Color.rgb(119, 119, 119));
        draftInput.setTextSize(15);
        draftInput.setHint("草稿描述");
        draftInput.setMinLines(2);
        draftInput.setMaxLines(3);
        draftInput.setGravity(Gravity.TOP | Gravity.START);
        draftInput.setPadding(dp(14), dp(10), dp(14), dp(10));
        draftInput.setBackground(roundRect(Color.rgb(29, 29, 29), 8));
        draftInput.setOnFocusChangeListener((view, hasFocus) -> projectTitleView.setText(projectTitle()));
        LinearLayout.LayoutParams inputParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(68));
        inputParams.topMargin = dp(40);
        content.addView(draftInput, inputParams);

        statusView = text("请选择保存草稿或导出视频", 15, Typeface.NORMAL);
        statusView.setTextColor(Color.rgb(216, 216, 216));
        statusView.setMaxLines(3);
        LinearLayout.LayoutParams statusParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        statusParams.topMargin = dp(16);
        content.addView(statusView, statusParams);

        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setVisibility(View.GONE);
        LinearLayout.LayoutParams progressParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(4));
        progressParams.topMargin = dp(12);
        content.addView(progressBar, progressParams);

{save_cover_button}

        TextView saveDraft = actionButton("保存草稿", false);
        saveDraft.setVisibility(getIntent().getBooleanExtra("intent_key_can_save_draft", true) ? View.VISIBLE : View.GONE);
        saveDraft.setOnClickListener(view -> saveDraft());
        LinearLayout.LayoutParams saveParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
        saveParams.topMargin = dp(22);
        content.addView(saveDraft, saveParams);

        TextView exportVideo = actionButton("导出视频", true);
        exportVideo.setVisibility(getIntent().getBooleanExtra("intent_key_can_save_video", true) ? View.VISIBLE : View.GONE);
        exportVideo.setOnClickListener(view -> exportVideo());
        LinearLayout.LayoutParams exportParams = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(48));
        exportParams.topMargin = dp(12);
        content.addView(exportVideo, exportParams);

        return root;
    }}

    private View buildTopBar() {{
        FrameLayout topBar = new FrameLayout(this);
        TextView back = text("‹", 40, Typeface.NORMAL);
        back.setGravity(Gravity.CENTER);
        back.setOnClickListener(view -> exitToHome());
        FrameLayout.LayoutParams backParams = new FrameLayout.LayoutParams(dp(56), dp(56), Gravity.START | Gravity.CENTER_VERTICAL);
        backParams.leftMargin = dp(12);
        topBar.addView(back, backParams);

        TextView title = text("作品发布", 25, Typeface.NORMAL);
        title.setGravity(Gravity.CENTER);
        topBar.addView(title, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.MATCH_PARENT, Gravity.CENTER));
        return topBar;
    }}

    private View buildCoverView() {{
        FrameLayout frame = new FrameLayout(this);
        frame.setBackground(roundRect(Color.rgb(42, 42, 42), 10));
        frame.setClipToOutline(false);

        {cover_declaration}
        coverView.setScaleType(ImageView.ScaleType.CENTER_CROP);
        String coverPath = coverPath();
        if (!TextUtils.isEmpty(coverPath) && BitmapFactory.decodeFile(coverPath) != null) {{
            coverView.setImageBitmap(BitmapFactory.decodeFile(coverPath));
        }} else {{
            coverView.setBackgroundColor(Color.rgb(42, 42, 42));
        }}
        frame.addView(coverView, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        TextView play = text("▶", 46, Typeface.NORMAL);
        play.setGravity(Gravity.CENTER);
        frame.addView(play, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        return frame;
    }}

    private TextView actionButton(String label, boolean primary) {{
        TextView button = text(label, 17, Typeface.BOLD);
        button.setGravity(Gravity.CENTER);
        button.setBackground(roundRect(primary ? Color.rgb(66, 73, 84) : Color.rgb(48, 52, 59), 24));
        return button;
    }}

    private TextView text(String value, int sp, int style) {{
        TextView textView = new TextView(this);
        textView.setText(value);
        textView.setTextColor(Color.WHITE);
        textView.setTextSize(sp);
        textView.setTypeface(Typeface.DEFAULT, style);
        return textView;
    }}

    private void saveDraft() {{
        setStatus("正在保存草稿...");
        NvModuleManager.get().saveDraft(draftInput.getText().toString(), 0L, new DraftManager.DraftSaveCallBack() {{
            @Override
            public void onSaveSuccess(boolean isNew) {{
                runOnUiThread(() -> {{
                    setStatus("草稿已保存");
                    exitToHome();
                }});
            }}
        }});
    }}

    private void exportVideo() {{
        setStatus("导出中...");
        progressBar.setProgress(0);
        progressBar.setVisibility(View.VISIBLE);
        NvModuleManager.saveVideoToAlbum(new NvModuleManager.OnCompileVideoListener() {{
            @Override
            public void compileProgress(NvsTimeline timeline, int progress) {{
                runOnUiThread(() -> {{
                    progressBar.setProgress(Math.max(0, Math.min(100, progress)));
                    setStatus("导出中 " + progress + "%");
                }});
            }}

            @Override
            public void compileFinished(NvsTimeline timeline) {{
            }}

            @Override
            public void compileFailed(NvsTimeline timeline) {{
                runOnUiThread(() -> setStatus("导出失败"));
            }}

            @Override
            public void compileCompleted(NvsTimeline nvsTimeline, String compileVideoPath, boolean isCanceled) {{
                runOnUiThread(() -> {{
                    progressBar.setVisibility(View.GONE);
                    setStatus(isCanceled ? "导出已取消" : "导出成功：" + compileVideoPath);
                }});
            }}

            @Override
            public void compileVideoCancel() {{
                runOnUiThread(() -> {{
                    progressBar.setVisibility(View.GONE);
                    setStatus("导出已取消");
                }});
            }}

            public void onCompileCompleted(String compileVideoPath, boolean isHardwareEncoder, int errorType, String stringInfo, int flags) {{
            }}

            public void onCompileCompleted(boolean isHardwareEncoder, int errorType, String stringInfo, int flags) {{
            }}
        }});
    }}

{save_cover_method}    private void setStatus(String status) {{
        statusView.setText(status);
    }}

    private NvPublishInfo getPublishInfoSafely() {{
        try {{
            return NvModuleManager.get().getPublishInfo();
        }} catch (Throwable ignored) {{
            return null;
        }}
    }}

    private String coverPath() {{
        if (publishInfo != null && !TextUtils.isEmpty(publishInfo.getCoverPath())) {{
            return publishInfo.getCoverPath();
        }}
        return "";
    }}

    private String projectTitle() {{
        if (draftInput != null && draftInput.getText() != null && draftInput.getText().toString().trim().length() > 0) {{
            return draftInput.getText().toString().trim();
        }}
        Calendar calendar = Calendar.getInstance();
        return String.format(Locale.CHINA, "草稿-%02d%02d", calendar.get(Calendar.MONTH) + 1, calendar.get(Calendar.DAY_OF_MONTH));
    }}

    private void exitToHome() {{
        try {{
            AppManager.getInstance().finishAllEditActivity();
        }} catch (Throwable ignored) {{
        }}
        finish();
    }}

    private GradientDrawable roundRect(int color, int radiusDp) {{
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(color);
        drawable.setCornerRadius(dp(radiusDp));
        return drawable;
    }}

    private int dp(int value) {{
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }}
}}
"""
    write_text(activity, content, target_root, report, "Generated native Android publish activity")


def demote_existing_launcher(manifest: Path, target_root: Path, report: Report) -> None:
    text = read_text(manifest)
    changed = False

    def replace_activity(match: re.Match[str]) -> str:
        nonlocal changed
        block = match.group(0)
        if ".meishe.MeisheShortVideoDemoActivity" in block:
            return block
        if "android.intent.action.MAIN" not in block or "android.intent.category.LAUNCHER" not in block:
            return block
        updated = re.sub(
            r"\s*<intent-filter>.*?android\.intent\.action\.MAIN.*?android\.intent\.category\.LAUNCHER.*?</intent-filter>",
            "",
            block,
            count=1,
            flags=re.S,
        )
        changed = changed or updated != block
        return updated

    updated = re.sub(r"<activity\b[^>]*>.*?</activity>", replace_activity, text, flags=re.S)
    if changed:
        write_text(manifest, updated, target_root, report, "Demoted existing Android launcher activity")
    else:
        report.add_change("No existing Android launcher activity required demotion.")


def register_native_demo_activity(
    manifest: Path,
    target_root: Path,
    report: Report,
    force_launcher: bool = False,
) -> None:
    text = read_text(manifest)
    has_launcher = not force_launcher and "android.intent.action.MAIN" in text and "android.intent.category.LAUNCHER" in text
    if has_launcher:
        entry = '        <activity android:name=".meishe.MeisheShortVideoDemoActivity" android:exported="false" />'
    else:
        entry = """        <activity
            android:name=".meishe.MeisheShortVideoDemoActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />

                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>"""
    if ".meishe.MeisheShortVideoDemoActivity" in text:
        if not has_launcher and "android:exported=\"false\"" in text:
            text = re.sub(
                r'\s*<activity\s+android:name="\.meishe\.MeisheShortVideoDemoActivity"\s+android:exported="false"\s*/>',
                "\n" + entry,
                text,
                count=1,
            )
            write_text(manifest, text, target_root, report, "Promoted native Android demo activity to launcher")
            return
        report.add_change("Native Android demo activity already registered in manifest.")
        return
    text = re.sub(r"(<application\b[^>]*)\s*/>", r"\1>\n    </application>", text, count=1, flags=re.S)
    if "</application>" not in text:
        report.add_warning("Could not register MeisheShortVideoDemoActivity because </application> was not found in AndroidManifest.xml.")
        return
    text = text.replace("</application>", f"{entry}\n    </application>", 1)
    reason = "Registered native Android demo activity as launcher" if not has_launcher else "Registered native Android demo activity"
    write_text(manifest, text, target_root, report, reason)


def register_native_publish_activity(manifest: Path, target_root: Path, report: Report) -> None:
    text = read_text(manifest)
    if ".meishe.MeisheShortVideoPublishActivity" in text:
        report.add_change("Native Android publish activity already registered in manifest.")
        return
    text = re.sub(r"(<application\b[^>]*)\s*/>", r"\1>\n    </application>", text, count=1, flags=re.S)
    if "</application>" not in text:
        report.add_warning("Could not register MeisheShortVideoPublishActivity because </application> was not found in AndroidManifest.xml.")
        return
    entry = '        <activity android:name=".meishe.MeisheShortVideoPublishActivity" android:exported="false" />'
    text = text.replace("</application>", f"{entry}\n    </application>", 1)
    write_text(manifest, text, target_root, report, "Registered native Android publish activity")


def create_application(app_module: Path, package_name: str, target_root: Path, report: Report) -> str:
    class_name = "MeisheShortVideoApplication"
    path = java_path_for_package(app_module, package_name, class_name)
    content = f"""package {package_name};

import android.app.Application;

import {package_name}.meishe.MeisheShortVideoDocking;

public class {class_name} extends Application {{
    @Override
    public void onCreate() {{
        super.onCreate();
        MeisheShortVideoDocking.init(this);
    }}
}}
"""
    write_text(path, content, target_root, report, "Generated native Android Application")
    return f".{class_name}"


def integrate_existing_application(app_module: Path, package_name: str, app_name: str, target_root: Path, report: Report) -> None:
    if app_name.startswith("."):
        full_name = package_name + app_name
    elif "." not in app_name:
        full_name = package_name + "." + app_name
    else:
        full_name = app_name
    relative = Path(*full_name.split("."))
    candidates = [
        app_module / "src" / "main" / "java" / relative.with_suffix(".java"),
        app_module / "src" / "main" / "kotlin" / relative.with_suffix(".kt"),
    ]
    path = next((item for item in candidates if item.exists()), None)
    if path is None:
        report.add_warning(f"Application class `{full_name}` not found; call `{package_name}.meishe.MeisheShortVideoDocking.init(this)` from Application.onCreate().")
        return
    text = read_text(path)
    if "MeisheShortVideoDocking.init(this)" in text:
        report.add_change(f"Application already initializes Meishe helper: `{rel(path, target_root)}`")
        return
    if path.suffix == ".java" and "super.onCreate();" in text:
        import_line = f"import {package_name}.meishe.MeisheShortVideoDocking;\n"
        if import_line not in text:
            text = re.sub(r"(package\s+[^;]+;\s*)", r"\1\n" + import_line, text, count=1)
        text = text.replace("super.onCreate();", "super.onCreate();\n        MeisheShortVideoDocking.init(this);", 1)
        write_text(path, text, target_root, report, "Inserted Meishe initialization into Application")
    else:
        report.add_warning(f"Could not safely patch `{rel(path, target_root)}`; call `MeisheShortVideoDocking.init(this)` from Application.onCreate().")


def patch_android_build_gradle(
    build_file: Path,
    target_root: Path,
    report: Report,
    core_compatibility_version: str | None,
) -> None:
    text = read_text(build_file)
    is_kts = build_file.suffix == ".kts"
    min_sdk_match = re.search(r"\bminSdk(?:Version)?\s*(?:=\s*)?(\d+)", text)
    min_sdk = int(min_sdk_match.group(1)) if min_sdk_match else None
    needs_multidex_library = min_sdk is None or min_sdk < 21
    if needs_multidex_library:
        multidex_dependency = (
            '    implementation("androidx.multidex:multidex:2.0.0")\n'
            if is_kts
            else "    implementation 'androidx.multidex:multidex:2.0.0'\n"
        )
        multidex_config = "        multiDexEnabled = true\n" if is_kts else "        multiDexEnabled true\n"
    else:
        multidex_dependency = ""
        multidex_config = ""
    if core_compatibility_version:
        if is_kts:
            compatibility_block = f'''\nconfigurations.all {{
    exclude(group = "com.android.support")
    resolutionStrategy.force(
        "androidx.core:core:{core_compatibility_version}",
        "androidx.core:core-ktx:{core_compatibility_version}",
    )
}}
'''
        else:
            compatibility_block = f'''\nconfigurations.all {{
    exclude group: 'com.android.support'

    resolutionStrategy {{
        force 'androidx.core:core:{core_compatibility_version}'
        force 'androidx.core:core-ktx:{core_compatibility_version}'
    }}
}}
'''
    elif is_kts:
        compatibility_block = '''\nconfigurations.all {
    exclude(group = "com.android.support")
}
'''
    else:
        compatibility_block = '''\nconfigurations.all {
    exclude group: 'com.android.support'
}
'''
    if is_kts:
        block = """dependencies {
    implementation(fileTree(mapOf("dir" to "libs", "include" to listOf("*.aar"))))
""" + multidex_dependency + """\
    implementation("androidx.appcompat:appcompat:1.0.0")
    implementation("com.google.android.material:material:1.0.0")
    implementation("androidx.recyclerview:recyclerview:1.1.0")
    implementation("androidx.constraintlayout:constraintlayout:1.1.3")
    implementation("com.google.code.gson:gson:2.8.5")
    implementation("com.squareup.okhttp3:okhttp:4.9.2")
    implementation("com.squareup.okhttp3:logging-interceptor:4.9.2")
    implementation("com.github.bumptech.glide:glide:4.16.0")
    annotationProcessor("com.github.bumptech.glide:compiler:4.16.0")
    implementation("com.github.zjupure:webpdecoder:2.7.4.16.0")
    implementation("com.permissionx.guolindev:permission-support:1.4.0")
    implementation("com.scwang.smart:refresh-layout-kernel:2.0.1")
    implementation("com.scwang.smart:refresh-header-classics:2.0.1")
    implementation("androidx.room:room-runtime:2.4.1")
    annotationProcessor("androidx.room:room-compiler:2.4.1")
    implementation("androidx.media3:media3-exoplayer:1.1.1")
    implementation("androidx.media3:media3-ui:1.1.1")
    implementation("org.greenrobot:eventbus:3.2.0")
    implementation("com.blankj:utilcodex:1.31.1")
    implementation("com.github.CymChad:BaseRecyclerViewAdapterHelper:2.9.50")
}
""" + compatibility_block + """

android {
    defaultConfig {
""" + multidex_config + """\
        ndk {
            abiFilters += listOf("armeabi-v7a", "arm64-v8a")
        }
    }
    packagingOptions {
        jniLibs {
            useLegacyPackaging = true
        }
    }
}"""
    else:
        processor = "kapt" if "kotlin-kapt" in text or "id 'kotlin-kapt'" in text else "annotationProcessor"
        block = f"""dependencies {{
    implementation fileTree(dir: 'libs', include: ['*.aar'])
{multidex_dependency}\
    implementation 'androidx.appcompat:appcompat:1.0.0'
    implementation 'com.google.android.material:material:1.0.0'
    implementation 'androidx.recyclerview:recyclerview:1.1.0'
    implementation 'androidx.constraintlayout:constraintlayout:1.1.3'
    implementation 'com.google.code.gson:gson:2.8.5'
    implementation 'com.squareup.okhttp3:okhttp:4.9.2'
    implementation 'com.squareup.okhttp3:logging-interceptor:4.9.2'
    implementation 'com.github.bumptech.glide:glide:4.16.0'
    {processor} 'com.github.bumptech.glide:compiler:4.16.0'
    implementation 'com.github.zjupure:webpdecoder:2.7.4.16.0'
    implementation 'com.permissionx.guolindev:permission-support:1.4.0'
    implementation 'com.scwang.smart:refresh-layout-kernel:2.0.1'
    implementation 'com.scwang.smart:refresh-header-classics:2.0.1'
    implementation 'androidx.room:room-runtime:2.4.1'
    {processor} 'androidx.room:room-compiler:2.4.1'
    implementation 'androidx.media3:media3-exoplayer:1.1.1'
    implementation 'androidx.media3:media3-ui:1.1.1'
    implementation 'org.greenrobot:eventbus:3.2.0'
    implementation 'com.blankj:utilcodex:1.31.1'
    implementation 'com.github.CymChad:BaseRecyclerViewAdapterHelper:2.9.50'
}}
""" + compatibility_block + f"""

android {{
    defaultConfig {{
{multidex_config}\
        ndk {{
            abiFilters "armeabi-v7a", "arm64-v8a"
        }}
    }}
    packagingOptions {{
        jniLibs {{
            useLegacyPackaging true
        }}
    }}
}}"""
    new_text = insert_or_replace_block(text, block, "line")
    write_text(build_file, new_text, target_root, report, "Patched Android Gradle dependencies")
    report.add_change(
        "Aligned native Android packaging with the official Demo: armeabi-v7a/arm64-v8a and legacy JNI packaging."
    )
    if needs_multidex_library:
        report.add_change(
            "Enabled the AndroidX multidex runtime because minSdk is below 21 or could not be determined safely."
        )
    else:
        report.add_change(f"Skipped the legacy multidex runtime because minSdk {min_sdk} has platform multidex support.")


def patch_android_settings_repositories(android_root: Path, target_root: Path, report: Report) -> None:
    settings = android_root / "settings.gradle"
    is_kts = False
    if not settings.exists():
        settings = android_root / "settings.gradle.kts"
        is_kts = True
    if not settings.exists():
        report.add_warning("Android settings.gradle/settings.gradle.kts not found; add Aliyun/JitPack repositories if dependency resolution fails.")
        return
    text = read_text(settings)
    if "maven.aliyun.com/repository/public" in text and "jitpack.io" in text:
        report.add_change(f"Android dependency repositories already present: `{rel(settings, target_root)}`")
        return

    if is_kts:
        repo_lines = """        maven(url = "https://maven.aliyun.com/repository/public/")
        maven(url = "https://maven.aliyun.com/repository/gradle-plugin")
        maven(url = "https://maven.aliyun.com/nexus/content/groups/public/")
        maven(url = "https://maven.aliyun.com/nexus/content/repositories/jcenter")
        maven(url = "https://maven.aliyun.com/nexus/content/repositories/google")
        maven(url = "https://maven.aliyun.com/nexus/content/repositories/gradle-plugin")
        maven(url = "https://jitpack.io")
"""
    else:
        repo_lines = """        maven { url 'https://maven.aliyun.com/repository/public/' }
        maven { url 'https://maven.aliyun.com/repository/gradle-plugin' }
        maven { url 'https://maven.aliyun.com/nexus/content/groups/public/' }
        maven { url 'https://maven.aliyun.com/nexus/content/repositories/jcenter' }
        maven { url 'https://maven.aliyun.com/nexus/content/repositories/google' }
        maven { url 'https://maven.aliyun.com/nexus/content/repositories/gradle-plugin' }
        maven { url 'https://jitpack.io' }
"""

    marker = "dependencyResolutionManagement"
    start = text.find(marker)
    search_from = start if start >= 0 else 0
    repo_start = text.find("repositories", search_from)
    brace = text.find("{", repo_start)
    if repo_start < 0 or brace < 0:
        report.add_warning(f"Could not patch repositories in `{rel(settings, target_root)}`; add Aliyun/JitPack repositories manually.")
        return
    text = text[: brace + 1] + "\n" + repo_lines + text[brace + 1 :]
    write_text(settings, text, target_root, report, "Added Meishe Android dependency repositories")


def place_license(dst: Path, args: argparse.Namespace, target_root: Path, report: Report) -> None:
    if args.license_path:
        src = Path(args.license_path)
        copy_file(src, dst, target_root, report, "Copied Meishe license")
        report.add_input(f"License: `{src}`")
    elif dst.exists():
        report.add_input(f"Existing license retained: `{dst}`")
        report.add_change(f"Retained existing Meishe license: `{rel(dst, target_root)}`")
    else:
        report.add_warning(LICENSE_HELP)
        report.add_user_configuration(
            "Production license: register the final package name/Bundle Identifier with Meishe, obtain the matching real `meishesdk.lic`, then re-run with `--license-path`. The no-license first-run path includes a watermark."
        )


def place_config(dst: Path, target_root: Path, report: Report) -> None:
    content = json.dumps(MINIMAL_CONFIG_JSON, ensure_ascii=False, indent=2) + "\n"
    write_text(dst, content, target_root, report, "Generated minimal ShortVideo config")
    report.add_change("Generated config avoids official demo-only image resources such as `ic_meicam`, `logo_splash`, and `package1`.")


def enable_native_androidx_jetifier(android_root: Path, target_root: Path, report: Report) -> None:
    gradle_properties = android_root / "gradle.properties"
    text = read_text(gradle_properties) if gradle_properties.exists() else ""
    original = text
    for key, value in (("android.useAndroidX", "true"), ("android.enableJetifier", "true")):
        if re.search(rf"^{re.escape(key)}=", text, re.M):
            text = re.sub(rf"^{re.escape(key)}=.*$", f"{key}={value}", text, flags=re.M)
        else:
            text = text.rstrip() + f"\n{key}={value}\n"

    if text != original:
        write_text(gradle_properties, text, target_root, report, "Enabled AndroidX/Jetifier for native Android ShortVideo")
    else:
        report.add_change("Native AndroidX/Jetifier properties already set.")
    report.add_toolchain_warning(
        "Jetifier remains enabled for compatibility with the verified vendor dependency set. A Gradle "
        "deprecation warning for `android.enableJetifier` is a toolchain warning, not evidence that the "
        "ShortVideo AAR failed; remove it only after a clean dependency report confirms every dependency is AndroidX."
    )


def update_native_android_readme(
    target_root: Path,
    android_root: Path,
    app_module: Path,
    package_name: str,
    feature_config_path: Path,
    gradle_command: str,
    report: Report,
) -> None:
    """Create or refresh the managed native-Android run guide without replacing user README text."""
    module_name = ":".join(app_module.relative_to(android_root).parts)
    activity = f"{package_name}/{package_name}.meishe.MeisheShortVideoDemoActivity"
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
    block = f"""<!-- BEGIN MEISHE_NATIVE_ANDROID_RUN_GUIDE -->
## 美摄短视频 Demo 运行

- 项目根目录：`{target_root.resolve()}`
- Android 工程目录：`{android_root.resolve()}`
- App module：`{module_name}`
- applicationId：`{package_name}`
- 功能配置：`{feature_config_path.resolve()}`
- 运行与验收设备：真实 Android 设备；Android Emulator 和其他虚拟设备不受支持。

### 依赖安装

{dependency_section}

### Android Studio 运行

1. 用 Android Studio 打开 `{android_root.resolve()}`。
2. 等待 Gradle Sync 完成，选择 App module `{module_name}` 和已连接的真实 Android 设备。
3. 执行 Run，安装并启动 Debug App；若生成的短视频页不是 launcher，请从现有入口跳转，或使用下方 ADB 命令直接启动。

### 命令行构建与真机运行

```bash
cd "{android_root.resolve()}"
adb devices
{gradle_command}
adb shell am force-stop {package_name}
adb shell am start -n {activity}
```

### 配置修改与生效

{configuration_section}

### 遇到报错

受本机操作系统、Android/Java/Gradle 工具链、依赖缓存、网络、签名和设备状态差异影响，手动接入或运行期间可能报错。请把**执行的完整命令**和**完整原始报错信息**（不要只复制最后一行）发给当前 Agent 处理，不要求自行猜测修复。

<!-- END MEISHE_NATIVE_ANDROID_RUN_GUIDE -->"""
    readme = target_root / "README.md"
    existing = read_text(readme) if readme.exists() else ""
    pattern = re.compile(
        r"<!-- BEGIN MEISHE_NATIVE_ANDROID_RUN_GUIDE -->.*?"
        r"<!-- END MEISHE_NATIVE_ANDROID_RUN_GUIDE -->",
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
        "Updated the managed native Android run guide in README.md",
    )


def integrate_native_android(args: argparse.Namespace, target_root: Path, aar: Path, report: Report) -> None:
    android_root = find_android_root(target_root)
    app_module = find_app_module(android_root)
    build_file = find_build_file(app_module)
    manifest = find_manifest(app_module)
    core_compatibility_version = align_verified_native_android_compose_dependencies(
        android_root,
        build_file,
        target_root,
        report,
    )
    patch_native_android_app_identity(app_module, build_file, args.package_name, target_root, report)
    package_name = resolve_package(args, manifest, build_file)
    report.add_input(f"Android root: `{android_root}`")
    report.add_input(f"App module: `{app_module}`")
    report.add_input(f"Package name: `{package_name}`")
    supports_save_cover = aar_supports_verified_save_cover(aar)
    inspect_native_android_beauty_resources(aar, report)
    if supports_save_cover:
        report.add_input("Verified native Android cover API shape detected in the selected AAR.")
        report.add_change("Enabled the generated publish-page save-cover entry using the verified AAR API shape.")
    else:
        report.add_warning(
            "The selected native Android AAR does not exactly match the verified `saveCover`/`PathUtils.getCoverDir` callback shape. The publish page will not guess or generate a save-cover call."
        )

    local_aar = app_module / "libs" / "NvShortVideoCore.aar"
    copy_file(aar, local_aar, target_root, report, "Copied ShortVideo AAR")
    report.add_input(f"Native Android project-local AAR copy: `{local_aar}`")
    patch_android_settings_repositories(android_root, target_root, report)
    enable_native_androidx_jetifier(android_root, target_root, report)
    patch_android_build_gradle(build_file, target_root, report, core_compatibility_version)
    merge_manifest_permissions(manifest, target_root, report)
    place_license(app_module / "src" / "main" / "assets" / "meishesdk.lic", args, target_root, report)
    place_config(app_module / "src" / "main" / "assets" / "config" / "config_example.json", target_root, report)
    copy_android_demo_banner(app_module, target_root, report)
    copy_android_demo_icons(app_module, target_root, report)
    feature_config_path = create_native_android_feature_config(app_module, package_name, target_root, report)
    create_helper(app_module, package_name, target_root, report)
    create_native_demo_activity(app_module, package_name, target_root, report)
    create_native_publish_activity(app_module, package_name, target_root, report, supports_save_cover)
    if args.demo_launcher:
        demote_existing_launcher(manifest, target_root, report)
    register_native_demo_activity(manifest, target_root, report, force_launcher=args.demo_launcher)
    register_native_publish_activity(manifest, target_root, report)

    manifest_text = read_text(manifest)
    existing_app = get_application_name(manifest_text)
    if existing_app:
        integrate_existing_application(app_module, package_name, existing_app, target_root, report)
    else:
        app_name = create_application(app_module, package_name, target_root, report)
        set_application_name(manifest, app_name, target_root, report)

    report.add_placeholder("Replace server placeholders in generated wrappers/config if your deployment uses a customer-hosted material server.")
    report.add_user_configuration(
        "Android signing/package: replace temporary debug signing with the user's keystore and keep the final package name consistent with the Meishe app/license registration."
    )
    report.add_user_configuration(
        "Customer server: follow `references/customer-server.md`; update the generated project configuration only after Meishe provides the server contract and credentials."
    )
    write_server_handoff(
        target_root,
        "native-android",
        f"{package_name}.meishe.MeisheFeatureConfig and app/src/main/assets/config/config_example.json",
        "`MeisheFeatureConfig.java` 是用户功能配置最终来源：有序菜单删除后由 SDK 重排 UI，默认开启 `useAutoCut` 和拍摄页模板入口，并使用已验证的 1080p 导出默认值。原生 Android 使用当前 SDK 支持的服务配置；客户服务需按美摄合同提供 AutoCut 地址和应用身份白名单。",
        "官方 Demo 服务只允许已登记的 Android applicationId `com.meishe.duanshipindemo`；其他 applicationId 必须使用匹配的客户服务和 License。",
        "客户服务确实使用 HTTP 时，只为真实域名添加最小 Android Network Security Config，不要全局允许明文流量。",
        report,
    )
    report.add_next_check(
        "Native Android AutoCut: manually verify edit album, template page, and capture template entry; the generated result must enter the standard editor, then Next must reach save-draft/export publishing."
    )
    report.add_next_check(
        "Native Android template export: keep compileConfig.resolution at 1 (1080p) for the validated default; resolution 2 is 4K and must only be enabled after device-memory validation."
    )
    add_android_gradle_dependency_step(android_root, report, "Native Android")
    module_parts = app_module.relative_to(android_root).parts
    install_task = ":" + ":".join((*module_parts, "installDebug"))
    gradle_command = f"gradlew.bat {install_task}" if sys.platform == "win32" else f"./gradlew {install_task}"
    apply_steps = [
        ConfigurationApplyStep(
            label="重新编译并安装 Debug 包",
            condition="修改 MeisheFeatureConfig.java、config_example.json、License、包名、签名或 Android 原生资源后。",
            working_directory=android_root,
            command=gradle_command,
            success_marker="Gradle 输出 BUILD SUCCESSFUL，新的 Debug APK 安装到已连接 Android 设备。",
        ),
        ConfigurationApplyStep(
            label="重新启动生成的短视频入口",
            condition="安装成功后需要确认新配置；不依赖原项目是否把短视频页设为 launcher。",
            working_directory=android_root,
            command=(
                f"adb shell am force-stop {package_name}\n"
                f"adb shell am start -n {package_name}/{package_name}.meishe.MeisheShortVideoDemoActivity"
            ),
            success_marker="设备打开 MeisheShortVideoDemoActivity，重新进入功能时应用新的 NvVideoConfig。",
        ),
    ]
    report.add_configuration_handoff(
        "原生 Android 功能配置",
        str(feature_config_path.resolve()),
        "拍摄、合拍、相册、编辑、导出、菜单、画幅、水印和模型等 NvVideoConfig 业务能力；这是 JSON 初始化后的最终覆盖入口。",
        apply_steps,
        (
            "Java 配置会编译进 APK，修改后不能只重启旧安装包，必须重新构建并安装。",
            "Gradle 依赖声明未变化时无需重新下载依赖；不要把 clean 作为默认步骤。",
        ),
    )
    report.add_configuration_handoff(
        "原生 Android 初始 JSON、License 与应用身份",
        (
            f"{(app_module / 'src/main/assets/config/config_example.json').resolve()}; "
            f"{(app_module / 'src/main/assets/meishesdk.lic').resolve()}; {build_file.resolve()}"
        ),
        "SDK 初始 JSON、正式 License、applicationId、签名和原生打包资源；功能最终值仍以 MeisheFeatureConfig.java 为准。",
        apply_steps,
        (
            "License 必须匹配最终 applicationId；客户服务器字段必须按美摄合同添加，不能猜测官方 Demo 地址或鉴权值。",
            "只改配置和资源时无需 Gradle Sync；仅在 build.gradle 或依赖声明变化后再同步依赖。",
        ),
    )
    if args.demo_launcher:
        report.add_next_check(f"Native Android: launch the app normally; `{package_name}.meishe.MeisheShortVideoDemoActivity` is the generated launcher.")
    else:
        report.add_next_check(f"Native Android: start `{package_name}.meishe.MeisheShortVideoDemoActivity` from your existing launcher or route to see the generated ShortVideo demo entry.")
    update_native_android_readme(
        target_root,
        android_root,
        app_module,
        package_name,
        feature_config_path,
        gradle_command,
        report,
    )
    assert_no_external_dependency_refs(target_root, aar, "Native Android", report)
