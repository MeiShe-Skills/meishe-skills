"""Flutter Android integration steps."""

from argparse import Namespace
import re
from pathlib import Path

from . import implementation
from meishe_docking_core import Report, backup_path, read_text, rel, write_text


def patch_flutter_android_app_identity(target_root: Path, package_name: str, report: Report) -> None:
    app_root = target_root / "android" / "app"
    build_files = [path for path in (app_root / "build.gradle", app_root / "build.gradle.kts") if path.exists()]
    if not build_files:
        report.add_warning("Flutter Android app build.gradle[.kts] was not found; application identity was not updated.")
        return

    for build_file in build_files:
        text = read_text(build_file)
        original = text
        for key in ("namespace", "applicationId"):
            text, _ = re.subn(
                rf"(\b{key}\s*(?:=\s*)?)[\"'][^\"']+[\"']",
                rf'\g<1>"{package_name}"',
                text,
            )
        if text != original:
            write_text(
                build_file,
                text,
                target_root,
                report,
                f"Set Flutter Android namespace/applicationId: `{rel(build_file, target_root)}`",
            )
        elif package_name in text:
            report.add_change(f"Flutter Android namespace/applicationId already uses `{package_name}`.")
        else:
            report.add_warning(
                f"Flutter Android identity shape was not recognized in `{rel(build_file, target_root)}`; set namespace and applicationId to `{package_name}` manually."
            )

    activity_files = sorted(
        path
        for source_root in (app_root / "src" / "main" / "kotlin", app_root / "src" / "main" / "java")
        if source_root.is_dir()
        for path in source_root.rglob("MainActivity.*")
        if path.suffix in {".kt", ".java"}
    )
    if not activity_files:
        report.add_warning("Flutter Android MainActivity source was not found; verify its package matches the application identity.")
    for activity in activity_files:
        source_root = next(
            root
            for root in (app_root / "src" / "main" / "kotlin", app_root / "src" / "main" / "java")
            if root in activity.parents
        )
        text = read_text(activity)
        if not re.search(r"(?m)^\s*package\s+[A-Za-z_][\w.]*\s*;?\s*$", text):
            report.add_warning(f"Flutter Android MainActivity package was not recognized: `{rel(activity, target_root)}`.")
            continue
        updated = re.sub(
            r"(?m)^(\s*package\s+)[A-Za-z_][\w.]*(\s*;?\s*)$",
            rf"\g<1>{package_name}\g<2>",
            text,
            count=1,
        )
        desired = source_root.joinpath(*package_name.split("."), activity.name)
        if desired == activity:
            write_text(activity, updated, target_root, report, "Set Flutter Android MainActivity package")
            continue
        backup_path(activity, target_root, report)
        write_text(
            desired,
            updated,
            target_root,
            report,
            f"Moved Flutter Android MainActivity to `{rel(desired, target_root)}`",
        )
        if not report.dry_run:
            activity.unlink()
            parent = activity.parent
            while parent != source_root:
                try:
                    parent.rmdir()
                except OSError:
                    break
                parent = parent.parent
    report.add_input(f"Flutter Android package: `{package_name}`")


def preflight(
    args: Namespace,
    target_root: Path,
    source_plugin: Path,
    report: Report,
) -> None:
    implementation.ensure_flutter_android_native_libraries(
        args,
        target_root,
        source_plugin,
        source_plugin,
        report,
        apply_changes=False,
    )


def integrate(
    args: Namespace,
    target_root: Path,
    plugin: Path,
    source_plugin: Path,
    report: Report,
) -> None:
    android_package_name = args.android_package_name or args.package_name
    if android_package_name:
        patch_flutter_android_app_identity(target_root, android_package_name, report)
    implementation.enable_flutter_androidx_jetifier(target_root, plugin if plugin.exists() else source_plugin, report)
    implementation.ensure_flutter_android_native_libraries(args, target_root, plugin, source_plugin, report)
    implementation.patch_flutter_plugin_android_config_callback(target_root, plugin, report)
    implementation.patch_flutter_android_publish_bridge(target_root, plugin, report, source_plugin)
