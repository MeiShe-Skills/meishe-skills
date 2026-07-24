#!/usr/bin/env python3
"""Integrate Meishe ShortVideo demo docking into a target project."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


SKILL_NAME = "meishe-native-android-shortvideo-docking"
BEGIN = "BEGIN MEISHE_DUANSHIPIN_DOCKING"
END = "END MEISHE_DUANSHIPIN_DOCKING"
SKILL_ROOT = Path(__file__).resolve().parents[1]
DEMO_BANNER_ASSET = SKILL_ROOT / "assets" / "demo-ui" / "meishe_home_banner.jpg"
DEMO_ICON_ASSET_DIR = SKILL_ROOT / "assets" / "demo-ui" / "icons"
DEMO_ICON_FILES = {
    "capture": "meishe_icon_capture.png",
    "dual_capture": "meishe_icon_dual_capture.png",
    "edit": "meishe_icon_edit.png",
    "draft": "meishe_icon_draft.png",
}
DEPENDENCY_USER_EXECUTION_CHOICE = (
    "用户执行（推荐）：Agent 一次性提供当前阶段的全部工作目录、命令/操作、执行顺序和成功标志；"
    "用户执行完毕并返回结果后继续。"
)
DEPENDENCY_AUTOMATIC_EXECUTION_CHOICE = (
    "自动执行：Agent 执行已列出的任务内操作直至当前阶段完成；"
    "该方式会额外消耗 Token 和时间，具体取决于网络、本机缓存、构建和设备状态。"
)
DEPENDENCY_VISIBLE_RESPONSE_RULE = (
    "可见回复要求：选择执行方式时，必须在当前轮次的最终可见回复中重复两个选择及每个步骤的"
    "绝对工作目录、完整命令/操作、顺序、用途和成功标志；不得只留在 commentary、工具输出、"
    "折叠的“处理中”区域或报告文件中，也不得让用户回看上一条消息。"
)
REAL_DEVICE_REQUIREMENT = (
    "真机要求：美摄短视频 Demo 必须运行在真实 Android 设备上；"
    "Android Emulator 和其他虚拟设备不受支持，不能用于运行或验收。"
)

SDK_COPY_SKIP_DIRS = {
    ".dart_tool",
    ".git",
    ".gradle",
    ".gradle-user-home",
    ".hg",
    ".idea",
    ".meishe_docking_backup",
    ".svn",
    ".vscode",
    "__pycache__",
    "build",
    "DerivedData",
    "node_modules",
    "Pods",
}
SELF_CONTAINED_CONFIG_FILE_NAMES = {
    "build.gradle",
    "build.gradle.kts",
    "gradle.properties",
    "settings.gradle",
    "settings.gradle.kts",
}








LICENSE_HELP = (
    "No meishesdk.lic was supplied. The Meishe docs state the SDK can still run "
    "without authorization, but rendered output will include the MEISHE watermark. "
    "For watermark-free output, register at https://www.meishesdk.com, create an app, "
    "configure the target app package name / appid, ask Meishe business support to enable "
    "authorization, download the .lic file from the app information page, and re-run with "
    "--license-path <path-to-meishesdk.lic>."
)



class IntegrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class DependencyStep:
    label: str
    working_directory: Path
    command: str
    purpose: str
    success_marker: str


@dataclass(frozen=True)
class ConfigurationApplyStep:
    label: str
    condition: str
    working_directory: Path
    command: str
    success_marker: str


@dataclass(frozen=True)
class ConfigurationHandoff:
    label: str
    edit_entry: str
    purpose: str
    apply_steps: tuple[ConfigurationApplyStep, ...]
    notes: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()


@dataclass
class Report:
    target_root: Path
    platform: str
    dry_run: bool = False
    changes: list[str] = field(default_factory=list)
    placeholders: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    toolchain_warnings: list[str] = field(default_factory=list)
    vendor_warnings: list[str] = field(default_factory=list)
    user_configurations: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    backups: list[str] = field(default_factory=list)
    next_checks: list[str] = field(default_factory=list)
    dependency_steps: list[DependencyStep] = field(default_factory=list)
    dependency_notes: list[str] = field(default_factory=list)
    configuration_handoffs: list[ConfigurationHandoff] = field(default_factory=list)

    def add_change(self, message: str) -> None:
        self.changes.append(message)

    def add_placeholder(self, message: str) -> None:
        self.placeholders.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)

    def add_toolchain_warning(self, message: str) -> None:
        self.toolchain_warnings.append(message)

    def add_vendor_warning(self, message: str) -> None:
        self.vendor_warnings.append(message)

    def add_user_configuration(self, message: str) -> None:
        self.user_configurations.append(message)

    def add_input(self, message: str) -> None:
        self.inputs.append(message)

    def add_next_check(self, message: str) -> None:
        self.next_checks.append(message)

    def add_dependency_step(
        self,
        label: str,
        working_directory: Path,
        command: str,
        purpose: str,
        success_marker: str,
    ) -> None:
        step = DependencyStep(
            label=label,
            working_directory=working_directory.resolve(),
            command=command,
            purpose=purpose,
            success_marker=success_marker,
        )
        if step not in self.dependency_steps:
            self.dependency_steps.append(step)

    def add_dependency_note(self, message: str) -> None:
        if message not in self.dependency_notes:
            self.dependency_notes.append(message)

    def add_configuration_handoff(
        self,
        label: str,
        edit_entry: str,
        purpose: str,
        apply_steps: Iterable[ConfigurationApplyStep],
        notes: Iterable[str] = (),
        platforms: Iterable[str] = (),
    ) -> None:
        handoff = ConfigurationHandoff(
            label=label,
            edit_entry=edit_entry,
            purpose=purpose,
            apply_steps=tuple(apply_steps),
            notes=tuple(notes),
            platforms=tuple(platforms),
        )
        if handoff not in self.configuration_handoffs:
            self.configuration_handoffs.append(handoff)

    def dependency_installation_items(self) -> list[str]:
        if self.dependency_steps:
            items = [
                "Status: `execution mode choice required`; the integration script did not run dependency downloads, dependency-resolving builds, or device operations.",
                f"Option 1: {DEPENDENCY_USER_EXECUTION_CHOICE}",
                f"Option 2: {DEPENDENCY_AUTOMATIC_EXECUTION_CHOICE}",
                DEPENDENCY_VISIBLE_RESPONSE_RULE,
            ]
        else:
            items = [
                "Status: `deferred`; this host has no executable dependency-installation step for the selected target."
            ]
        items.append(
            "Failure classification: network timeout, DNS, repository, proxy, TLS/certificate, or download-speed failures are dependency-chain issues; source compilation failures are investigated separately as integration/build issues."
        )
        items.append(REAL_DEVICE_REQUIREMENT)
        for index, step in enumerate(self.dependency_steps, start=1):
            items.append(
                f"Step {index} `{step.label}` | Working directory: `{step.working_directory}` | "
                f"Command/method: `{step.command}` | Purpose: {step.purpose} | "
                f"Success: {step.success_marker}"
            )
        items.extend(self.dependency_notes)
        return items

    def configuration_handoff_markdown(self, heading_level: int = 2) -> str:
        heading = "#" * heading_level
        child_heading = "#" * (heading_level + 1)
        if not self.configuration_handoffs:
            return f"{heading} Configuration Handoff\n\n- None\n"

        def table_cell(value: str) -> str:
            return value.replace("|", "\\|").replace("\n", "<br>")

        applicable_platforms = "Android"

        lines = [
            f"{heading} Configuration Handoff",
            "",
            f"- 独立交接文件：`{(self.target_root / 'meishe_configuration_handoff.md').resolve()}`",
            "- 配置文件由 Skill 首次生成，后续接入必须保留用户手动修改。",
            "- 以下命令中的工作目录、文件路径和构建入口均按当前项目生成；`<...DEVICE_ID>` 仅在设备标识无法由静态接入确定时保留。",
            f"- {REAL_DEVICE_REQUIREMENT}",
            "",
            f"{child_heading} 配置修改与生效速览",
            "",
            "| 配置项 | 修改入口 | 适用平台 | 最快生效方式 | 重新构建条件 | 无需执行 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for handoff in self.configuration_handoffs:
            handoff_platforms = "、".join(handoff.platforms) or applicable_platforms
            first_step = handoff.apply_steps[0]
            rebuild_steps = handoff.apply_steps[1:] or handoff.apply_steps[:1]
            rebuild_conditions = "<br>".join(step.condition for step in rebuild_steps)
            unnecessary = "<br>".join(
                note
                for note in handoff.notes
                if any(marker in note for marker in ("无需", "不需要", "不要默认"))
            ) or "见下方注意事项"
            lines.append(
                "| "
                + " | ".join(
                    table_cell(value)
                    for value in (
                        handoff.label,
                        f"`{handoff.edit_entry}`",
                        handoff_platforms,
                        first_step.label,
                        rebuild_conditions,
                        unnecessary,
                    )
                )
                + " |"
            )
        lines.append("")
        for handoff in self.configuration_handoffs:
            lines.extend(
                [
                    f"{child_heading} {handoff.label}",
                    "",
                    f"- 修改入口：`{handoff.edit_entry}`",
                    f"- 修改范围：{handoff.purpose}",
                    "",
                ]
            )
            for index, step in enumerate(handoff.apply_steps, start=1):
                lines.extend(
                    [
                        f"{child_heading}# 生效步骤 {index}：{step.label}",
                        "",
                        f"- 适用条件：{step.condition}",
                        f"- 工作目录：`{step.working_directory.resolve()}`",
                        "- 指令或操作：",
                        "",
                        "```text",
                        step.command,
                        "```",
                        "",
                        f"- 成功标志：{step.success_marker}",
                        "",
                    ]
                )
            if handoff.notes:
                lines.append(f"{child_heading}# 注意事项")
                lines.append("")
                lines.extend(f"- {note}" for note in handoff.notes)
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def configuration_handoff_document(self) -> str:
        return "\n".join(
            [
                "# 美摄短视频配置修改与生效交接",
                "",
                f"- 平台路线：`{self.platform}`",
                f"- 项目根目录：`{self.target_root.resolve()}`",
                "- 修改前先确认字段属于当前路线和 SDK 版本；未知版本不得直接沿用已验证补丁。",
                "",
                self.configuration_handoff_markdown(heading_level=2).strip(),
                "",
            ]
        )

    def to_markdown(self) -> str:
        def section(title: str, items: list[str]) -> str:
            if not items:
                return f"## {title}\n\n- None\n"
            return f"## {title}\n\n" + "\n".join(f"- {item}" for item in items) + "\n"

        status = "dry-run only; no files were written" if self.dry_run else "files were updated"
        next_checks = []
        if self.placeholders:
            next_checks.append("Replace every placeholder before production use.")
        next_checks.extend(
            [
                "Run the app on a real device; emulators are not supported by the ShortVideo module.",
                *self.next_checks,
            ]
        )
        report_sections = [
            section("Inputs", self.inputs),
            section("Planned Changes" if self.dry_run else "Changes", self.changes),
            section("Dependency Installation", self.dependency_installation_items()),
        ]
        report_sections.extend(
            [
                section("Placeholders To Replace", self.placeholders),
                section("User-Specific Configuration", self.user_configurations),
                self.configuration_handoff_markdown(),
                section("Toolchain Compatibility", self.toolchain_warnings),
                section("Third-Party SDK Warnings", self.vendor_warnings),
                section("Warnings", self.warnings),
                section("Planned Backups" if self.dry_run else "Backups", self.backups),
                section("Next Checks", next_checks),
            ]
        )
        return "\n".join(
            [
                "# Meishe ShortVideo Docking Report",
                "",
                f"- Skill: `{SKILL_NAME}`",
                f"- Platform: `{self.platform}`",
                f"- Target: `{self.target_root}`",
                f"- Status: {status}",
                "- SDK copy policy: official downloaded/extracted packages are used only as copy sources; generated dependencies point at project-local files such as `vendor/meishe/...`, app module `libs/`, or project resources.",
                "",
                *report_sections,
            ]
        )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add_android_gradle_dependency_step(
    android_root: Path,
    report: Report,
    label: str,
    host_os_name: str | None = None,
) -> None:
    current_os = host_os_name or os.name
    wrapper = android_root / ("gradlew.bat" if current_os == "nt" else "gradlew")
    if wrapper.exists():
        command = "gradlew.bat :app:assembleDebug" if current_os == "nt" else "./gradlew :app:assembleDebug"
    else:
        command = "Android Studio: File > Sync Project with Gradle Files, then Build > Make Project"
    report.add_dependency_step(
        f"{label} Gradle dependencies and Debug build",
        android_root,
        command,
        "Resolve Android dependencies and verify that the integrated app compiles.",
        "Gradle Sync and the Debug app build finish successfully; network/repository failures are reported separately from source compilation failures.",
    )


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def fs_path(path: Path) -> str:
    resolved = path.resolve()
    text = str(resolved)
    if os.name != "nt" or text.startswith("\\\\?\\"):
        return text
    if text.startswith("\\\\"):
        return "\\\\?\\UNC\\" + text.lstrip("\\")
    return "\\\\?\\" + text


def make_dir(path: Path) -> None:
    os.makedirs(fs_path(path), exist_ok=True)


def copy_file_raw(src: Path, dst: Path) -> None:
    make_dir(dst.parent)
    shutil.copy2(fs_path(src), fs_path(dst))


def write_utf8_text(path: Path, content: str) -> None:
    """Write LF-normalized UTF-8 text on every supported Python runtime."""
    make_dir(path.parent)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def backup_path(path: Path, target_root: Path, report: Report) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    try:
        relative = path.resolve().relative_to(target_root.resolve())
    except ValueError:
        relative = Path(path.name)
    backup = target_root / ".meishe_docking_backup" / stamp / relative
    if not report.dry_run:
        make_dir(backup.parent)
        if path.exists():
            copy_file_raw(path, backup)
    report.backups.append(rel(backup, target_root))
    return backup


def write_text(path: Path, content: str, target_root: Path, report: Report, reason: str) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == content:
        report.add_change(f"Unchanged: `{rel(path, target_root)}`")
        return
    if path.exists():
        backup_path(path, target_root, report)
    if not report.dry_run:
        write_utf8_text(path, content)
    report.add_change(f"{reason}: `{rel(path, target_root)}`")


def write_server_handoff(
    target_root: Path,
    platform: str,
    edit_entry: str,
    autocut_contract: str,
    identity_contract: str,
    transport_guidance: str,
    report: Report,
) -> None:
    content = f"""# 美摄客户服务器配置交接

- 平台：`{platform}`
- 修改入口：`{edit_entry}`
- 当前生成值用于 Demo 首次运行/接入验证，不代表客户服务已经验证。
- 一键成片接口约定：{autocut_contract}

## 修改前必须取得

- 客户服务 `host` 与各接口路径；不要从官方 Demo 地址推测客户路径。
- `clientId`、`clientSecret`、`assemblyId` 及其测试/生产环境。
- package name / Bundle Identifier 白名单要求、测试账号、网络/VPN要求和预期素材。
- AutoCut 是否启用及独立 `assetAutoCutUrl`（如有）。

## 字段

按服务合同修改 `host`、`assetRequestUrl`、`assetCategoryUrl`、`assetMusiciansUrl`、`assetFontUrl`、`assetDownloadUrl`、`assetPrefabricatedUrl`、`assetAutoCutUrl`、`assetTagUrl`、`clientId`、`clientSecret`、`assemblyId`、`isAbroad`。未要求的字段保持空值或合同默认值，不伪造凭据。

{identity_contract}

## 手工验收

1. 清理旧缓存或卸载测试 App，真机重新安装并授予权限。
2. 确认最终请求 URL、HTTP 状态和业务码，且客户模式没有误请求官方 Demo host。
3. 验证分类、列表、封面、至少一个在线素材下载和编辑使用。
4. 验证预制素材回调；失败不得阻塞拍摄、合拍、编辑、草稿。
5. 验证编辑素材选择、模板页和拍摄页模板入口都能进入一键成片；生成结果必须进入标准编辑页。
6. 在标准编辑页点击下一步，验证作品发布页、保存草稿、草稿继续编辑和导出视频闭环。
7. 用客户端请求日志、服务端日志和预期素材清单交叉确认后，才能标记客户服务器已验证。

正式项目不要把长期凭据提交到公共仓库，应接入项目自己的安全配置层。
{transport_guidance}
"""
    write_text(
        target_root / "meishe_server_config_handoff.md",
        content,
        target_root,
        report,
        "Generated customer-server edit and manual verification handoff",
    )




def files_have_same_content(left: Path, right: Path) -> bool:
    if not left.is_file() or not right.is_file() or left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as left_fh, right.open("rb") as right_fh:
        while True:
            left_chunk = left_fh.read(1024 * 1024)
            right_chunk = right_fh.read(1024 * 1024)
            if left_chunk != right_chunk:
                return False
            if not left_chunk:
                return True


def copy_file(src: Path, dst: Path, target_root: Path, report: Report, reason: str) -> None:
    if not src.exists() and not report.dry_run:
        raise IntegrationError(f"Source file not found: {src}")
    if src.exists() and dst.exists() and src.resolve() == dst.resolve():
        report.add_change(f"Already in place: `{rel(dst, target_root)}`")
        return
    if src.exists() and dst.exists() and files_have_same_content(src, dst):
        report.add_change(f"Unchanged: `{rel(dst, target_root)}`")
        return
    if dst.exists():
        backup_path(dst, target_root, report)
    if not report.dry_run:
        copy_file_raw(src, dst)
    report.add_change(f"{reason}: `{rel(dst, target_root)}`")


def iter_self_contained_config_files(target_root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(target_root):
        dirnames[:] = [dirname for dirname in dirnames if dirname not in SDK_COPY_SKIP_DIRS]
        current = Path(dirpath)
        for filename in filenames:
            if filename in SELF_CONTAINED_CONFIG_FILE_NAMES or filename.endswith((".gradle", ".gradle.kts")):
                yield current / filename


def assert_no_external_dependency_refs(target_root: Path, source_path: Path | None, platform_label: str, report: Report) -> None:
    if source_path is None:
        return
    source = source_path.expanduser().resolve()
    markers = {"D:\\Edge Download", "D:/Edge Download", "\\Downloads\\", "/Downloads/"}
    if not is_within(source, target_root):
        markers.add(str(source))
        markers.add(source.as_posix())
    hits: list[str] = []
    lowered_markers = {marker.lower() for marker in markers if marker}
    for config_file in iter_self_contained_config_files(target_root):
        try:
            text = config_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lowered_text = text.lower()
        for marker in lowered_markers:
            if marker and marker in lowered_text:
                hits.append(f"`{rel(config_file, target_root)}` contains `{marker}`")
                break
    if hits:
        formatted = "; ".join(hits[:8])
        more = f"; plus {len(hits) - 8} more" if len(hits) > 8 else ""
        report.add_warning(f"{platform_label}: self-contained SDK check failed. External download/package paths remain in config files: {formatted}{more}.")
    else:
        report.add_change(f"{platform_label}: self-contained SDK check passed; project config files do not reference the external package path.")


def copy_demo_banner(dst: Path, target_root: Path, report: Report, reason: str) -> None:
    copy_file(DEMO_BANNER_ASSET, dst, target_root, report, reason)


def copy_demo_icons(dst_dir: Path, target_root: Path, report: Report, reason: str) -> None:
    for filename in DEMO_ICON_FILES.values():
        copy_file(DEMO_ICON_ASSET_DIR / filename, dst_dir / filename, target_root, report, reason)
















def insert_or_replace_block(text: str, block: str, style: str) -> str:
    if style == "xml":
        begin = f"<!-- {BEGIN} -->"
        end = f"<!-- {END} -->"
    else:
        begin = f"// {BEGIN}"
        end = f"// {END}"
    wrapped = f"{begin}\n{block.rstrip()}\n{end}"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.S)
    if pattern.search(text):
        return pattern.sub(wrapped, text)
    return text.rstrip() + "\n\n" + wrapped + "\n"


GENERATED_PLUGIN_SEARCH_DIRS = {
    ".dart_tool",
    ".gradle",
    ".gradle-user-home",
    ".meishe_docking_backup",
    "build",
    "node_modules",
    "Pods",
}


def write_report(report: Report) -> None:
    if report.configuration_handoffs:
        handoff_path = report.target_root / "meishe_configuration_handoff.md"
        report.add_change(f"Generated command-level configuration handoff: `{rel(handoff_path, report.target_root)}`")
        if not report.dry_run:
            write_utf8_text(handoff_path, report.configuration_handoff_document())
    markdown = report.to_markdown()
    if report.dry_run:
        print(markdown)
        return
    report_path = report.target_root / "meishe_docking_report.md"
    write_utf8_text(report_path, markdown)
    print(f"Wrote report: {report_path}")


FIXED_PLATFORM = "native-android"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Integrate Meishe ShortVideo into a native Android app.")
    parser.add_argument("--target-root", required=True, help="Target project root.")
    parser.add_argument("--aar-path", required=True, help="Path to the official NvShortVideoCore.aar.")
    parser.add_argument("--license-path", help="Path to the real meishesdk.lic.")
    parser.add_argument("--package-name", help="Override the native Android application package name.")
    parser.add_argument(
        "--demo-launcher",
        action="store_true",
        help="For native Android, make the generated Meishe demo activity the launcher and demote the existing launcher entry.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print intended changes without writing files.")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    target_root = Path(args.target_root).resolve()
    if not target_root.exists():
        raise IntegrationError(f"Target root not found: {target_root}")
    report = Report(target_root=target_root, platform=FIXED_PLATFORM, dry_run=args.dry_run)

    from routes.native_android.orchestrator import integrate_native_android_route

    integrate_native_android_route(args, target_root, report)

    write_report(report)
    return 0


def main_for_platform(platform: str, argv: Iterable[str]) -> int:
    user_args = list(argv)
    if platform != FIXED_PLATFORM:
        raise IntegrationError(f"This skill only supports `{FIXED_PLATFORM}`, not `{platform}`.")
    if any(arg == "--platform" or arg.startswith("--platform=") for arg in user_args):
        raise IntegrationError(
            f"This is the fixed `{platform}` entry point; do not pass --platform. "
            "Use the frozen aggregate skill only when compatibility dispatch is required."
        )
    return main(user_args)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except IntegrationError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(2)
