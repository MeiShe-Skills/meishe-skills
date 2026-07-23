"""React Native iOS integration and static verification."""

from __future__ import annotations

import json
import re
from pathlib import Path

from meishe_docking_core import (
    Report,
    cocoa_pods_gemfile,
    installed_ruby_version,
    locked_cocoapods_version,
    project_file_dependency,
    read_text,
    replace_external_source_path_refs,
    write_text,
)
from platform_support.ios import (
    inspect_plugin_root,
    ios_project_root,
    patch_ios_app_info_plists,
    plugin_relative_exists,
    plugin_relative_glob_exists,
    report_ios_signing_configuration,
)

from . import implementation
from .constants import REACT_NATIVE_PLUGIN_NAME


OFFICIAL_DEMO_BUNDLE_IDENTIFIER = "com.meishe.duanshipindemo"


def ensure_ruby4_cocoapods_nkf_compatibility(
    target_root: Path,
    report: Report,
    active_ruby_version: tuple[int, ...] | None = None,
) -> bool:
    """Patch only the Ruby 4/CocoaPods 1.15.2 pair reproduced by validation."""
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        return False
    gemfile = cocoa_pods_gemfile(ios_root)
    ruby_version = active_ruby_version if active_ruby_version is not None else installed_ruby_version()
    if (
        gemfile is None
        or not ruby_version
        or ruby_version[0] < 4
        or locked_cocoapods_version(gemfile) != (1, 15, 2)
    ):
        return False
    text = read_text(gemfile)
    if re.search(r"\bgem\s*(?:\(|)\s*['\"]nkf['\"]", text):
        report.add_change("React Native iOS Ruby 4/CocoaPods 1.15.2 project-scoped nkf compatibility already configured.")
        return True
    updated = text.rstrip() + "\n\n# Ruby 4 compatibility for CocoaPods 1.15.2 (CFPropertyList/kconv).\ngem 'nkf'\n"
    write_text(
        gemfile,
        updated,
        target_root,
        report,
        "Added project-scoped Ruby 4/CocoaPods 1.15.2 nkf compatibility",
    )
    return True


def detected_ios_bundle_identifiers(target_root: Path) -> set[str]:
    identities: set[str] = set()
    ios_root = ios_project_root(target_root)
    if ios_root is None:
        return identities
    for project_file in ios_root.glob("*.xcodeproj/project.pbxproj"):
        for identity in re.findall(
            r'PRODUCT_BUNDLE_IDENTIFIER\s*=\s*"?([^";]+)"?;',
            read_text(project_file),
        ):
            value = identity.strip()
            if value and "$(" not in value and not value.lower().endswith("tests"):
                identities.add(value)
    return identities


def uses_official_demo_identity(target_root: Path, requested_identity: str | None) -> bool:
    if requested_identity:
        return requested_identity == OFFICIAL_DEMO_BUNDLE_IDENTIFIER
    return OFFICIAL_DEMO_BUNDLE_IDENTIFIER in detected_ios_bundle_identifiers(target_root)


def write_react_native_ios_self_check(target_root: Path, report: Report) -> None:
    content = """# React Native iOS 素材请求自检

## 典型现象

- 拍摄、合拍、编辑和草稿能够打开，但拍摄页的美颜、滤镜、贴纸或音乐在线列表为空。
- 首页可能错误显示素材准备完成，重新进入前台后也不再重试。
- 一键成片进入作品发布后看不到“保存草稿”，或点击保存后草稿箱仍为空。

## 已验证原因

1. 官方 RN JS API 的 `configServerInfo()` 不返回原生 Promise，直接 `await` 不能确认 iOS `ConfigServerInfo` 已完成。
2. `downloadPrefabricatedMaterial()` 失败时可能 resolve `false`；忽略返回值会把失败误记为成功。
3. ShortVideo `2.0.2.1` 官方 RN iOS Demo 在进入功能前会再次触发预制素材下载。
4. 官方 Demo 的素材/CDN链路要求其示例 ATS 配置；官方 Demo 身份的临时工程若收紧 ATS，在线素材可能为空。
5. ShortVideo `2.0.2.1` 的 iOS 一键成片回调可能给出 `hasDraft = false`；该值只控制官方发布页是否展示草稿入口，不代表回调项目已经写入草稿列表。只信任 `saveCurrentDraft` 的布尔值也可能产生“提示成功但列表为空”。

## 生成代码自检

- `src/meisheShortVideoDocking.ts|js`：iOS 通过 `NativeModules.VideoEditPlugin.sendMessageToNative` 等待 `ConfigServerInfo` 原生回执，并保留 Android 官方操作器回退。
- 同一 wrapper 显式开启两个 `useAutoCut` 和 image/video/smart/template 拍摄菜单；共享 `assetAutoCutUrl` 保持官方 `/api/app` 基础地址。
- `src/MeisheShortVideoDemo.tsx|jsx`：仅当素材下载结果严格为 `true` 时标记完成。
- `src/MeisheShortVideoPublish.tsx|jsx`：保存与导出操作固定在安全区域底部，不依赖滚动到底部才能看到。
- 已验证的 `2.0.2.1` iOS bridge 区分 AutoCut 临时任务 ID 与标准草稿 ID。`hasDraft = false` 时先暂存可编辑模型；没有模型则把渲染视频复制到 App 运行时沙箱并用 `NvTimelineDataManager.newProject` 新建标准草稿。只有新草稿可列出时才允许 JS 保存成功，删除/放弃草稿会清理映射媒体。
- iOS 导出事件必须直接监听 `VideoEditCallbackMethodChannel`，把 `DidCompileProgressMethod`、`DidCompileCompletedMethod` 和 `DidCoverImageChangedMethod` 映射为 RN 事件；进度同时兼容 `0...1` 与 `0...100`。Android 继续使用官方 operator handler。
- publish 事件先发送给 RN 页面，再关闭 SDK 编辑器；保存失败时发布页必须保留并显示原生错误，不得直接返回首页。
- iOS 点击拍摄、合拍或编辑时：先确认服务配置，再由 `runFeature` 直接非阻塞触发素材刷新，最后打开功能；三个入口都传入刷新标志，且入口不调用受首页单飞状态保护的 `prepareMaterials()`。刷新失败不得阻塞入口。
- 官方 Demo Bundle Identifier `com.meishe.duanshipindemo`：临时验证工程与官方 RN Demo 保持 `NSAllowsArbitraryLoads = true`。客户或正式工程必须核对全部接口/CDN后改为域名级最小例外。

## 手工验收

1. 清理旧缓存或重新安装 App，首次启动后允许所需权限。
2. 首页素材状态应从准备中变为可用；失败状态应能点击重试，恢复前台后也会重试。
3. 进入拍摄，逐项检查美颜、滤镜、贴纸和音乐在线列表；至少下载并实际使用一个在线素材。
4. 分别从编辑素材选择、模板页和拍摄模板菜单进入一键成片，确认生成结果进入标准编辑页。
5. 在标准编辑页点击下一步，确认发布页底部始终可见“保存草稿”和“导出视频”；保存后进入草稿箱，确认对应 `projectId` 可见并可继续编辑。
6. 若保存报错或草稿打开后全黑，不要把返回首页当作成功；检查临时 task ID、生成的 draft ID、`NvDraftSnapshotBridge` 暂存日志、运行时媒体路径以及 `projectInfoForProject` 反查结果。
7. 若导出一直停在“导出中”，检查 JS 是否订阅 `VideoEditCallbackMethodChannel`，不得只依赖官方 operator 的旧事件封装。
7. 若在线列表仍为空，检查 Xcode 日志中的 `ConfigServerInfo`、ATS、HTTP 状态、业务码、Bundle Identifier 白名单和 CDN 下载错误，不要仅以页面能打开判定网络成功。

需要真机完成以上验收时，先列出全部设备操作、原因和预期信息，让用户选择“用户执行”或“自动执行”；自动执行会额外消耗 Token 和时间。
"""
    write_text(
        target_root / "meishe_react_native_ios_self_check.md",
        content,
        target_root,
        report,
        "Generated React Native iOS material-request self-check handoff",
    )


def quick_verify_react_native_ios(
    target_root: Path,
    plugin: Path,
    source_plugin: Path,
    report: Report,
    requested_identity: str | None,
) -> None:
    if ios_project_root(target_root) is None:
        report.add_ios_quick_verify("React Native iOS: target has no `ios/` directory; skipped static iOS checks.")
        return
    inspection_root = inspect_plugin_root(plugin, source_plugin, report, "React Native iOS")
    official_demo_identity = uses_official_demo_identity(target_root, requested_identity)
    detected_identities = (
        {requested_identity}
        if requested_identity
        else detected_ios_bundle_identifiers(target_root)
    )
    patch_ios_app_info_plists(
        target_root,
        report,
        "React Native iOS",
        allow_arbitrary_loads=official_demo_identity,
    )
    if official_demo_identity:
        report.add_user_configuration(
            "React Native iOS official-Demo compatibility: `NSAllowsArbitraryLoads = true` is enabled only for the temporary `com.meishe.duanshipindemo` Demo-service validation path. Review all API/CDN domains and replace it with narrow ATS exceptions before production."
        )
    else:
        identity_label = (
            ", ".join(f"`{value}`" for value in sorted(detected_identities))
            if detected_identities
            else "an unrecognized existing App Target identity"
        )
        report.add_warning(
            "React Native iOS official Demo material service requires the exact Bundle Identifier "
            f"`com.meishe.duanshipindemo`, but the current iOS identity is {identity_label}. "
            "Online service requests will not work with that identity. For temporary Demo validation use "
            "`--ios-bundle-identifier com.meishe.duanshipindemo`; otherwise keep the existing identity and "
            "configure a customer server, matching License, and service allowlist."
        )
        report.add_ios_quick_verify(
            "React Native iOS: global NSAllowsArbitraryLoads was not enabled for a customer Bundle Identifier; use only verified domain-specific ATS exceptions."
        )
    ios_root = ios_project_root(target_root)
    if ios_root and (ios_root / "Podfile").exists():
        report.add_ios_quick_verify("React Native iOS: Podfile found; left `use_frameworks!` unchanged for RN compatibility.")
    else:
        message = "React Native iOS readiness failed: iOS Podfile not found."
        report.add_ios_quick_verify(message)
        report.add_vendor_warning(message)

    package_json = target_root / "package.json"
    expected_dependency = project_file_dependency(plugin, target_root)
    if package_json.exists():
        try:
            deps = json.loads(read_text(package_json)).get("dependencies", {})
            actual_dependency = deps.get(REACT_NATIVE_PLUGIN_NAME) if isinstance(deps, dict) else None
        except json.JSONDecodeError:
            actual_dependency = None
        if actual_dependency == expected_dependency:
            report.add_ios_quick_verify(f"React Native iOS: package.json uses project-local plugin dependency `{expected_dependency}`.")
        else:
            report.add_ios_quick_verify(
                f"React Native iOS: package.json dependency will be normalized to `{expected_dependency}` by integration."
            )

    missing_required = []
    checks = [
        ("react-native-nvshortvideo.podspec", "podspec", False),
        ("ios/Classes", "native bridge source directory", True),
        ("ios/Assets", "iOS assets directory", True),
    ]
    for relative_path, description, is_dir in checks:
        if not plugin_relative_exists(
            inspection_root,
            plugin,
            relative_path,
            target_root,
            report,
            "React Native iOS",
            description,
            is_dir=is_dir,
        ):
            missing_required.append(relative_path)
    if not plugin_relative_glob_exists(
        inspection_root,
        plugin,
        "ios/Frameworks",
        "*.xcframework",
        target_root,
        report,
        "React Native iOS",
        "vendored xcframeworks",
    ):
        missing_required.append("ios/Frameworks/*.xcframework")
    if missing_required:
        report.add_vendor_warning(
            "React Native iOS readiness failed: copied plugin is missing "
            + ", ".join(missing_required)
            + ". Provide the complete official React Native package from Meishe Developer Center (`React Native工程`) for iOS verification; do not substitute the native iOS `Pods-NvShortVideoEdit` package."
        )
    else:
        report.add_ios_quick_verify("React Native iOS readiness passed for static quick checks.")


def integrate(
    target_root: Path,
    plugin: Path,
    source_plugin: Path,
    report: Report,
    requested_identity: str | None,
) -> None:
    report_ios_signing_configuration(target_root, report)
    replace_external_source_path_refs(
        target_root,
        source_plugin,
        plugin,
        [target_root / "ios" / "Podfile.lock"],
        report,
        "React Native iOS",
    )
    implementation.patch_react_native_ios_publish_bridge(target_root, plugin, report, source_plugin)
    implementation.apply_verified_react_native_version_patches(target_root, report)
    quick_verify_react_native_ios(target_root, plugin, source_plugin, report, requested_identity)
    write_react_native_ios_self_check(target_root, report)
    report.add_user_configuration(
        "React Native iOS signing: set the user's Team/certificate/profile in Xcode. Temporary signing used for first launch is not a production setting."
    )
    report.add_next_check(
        "React Native iOS: after the approved dependency steps complete, build the generated workspace and manually follow `meishe_react_native_ios_self_check.md` on a real device."
    )
