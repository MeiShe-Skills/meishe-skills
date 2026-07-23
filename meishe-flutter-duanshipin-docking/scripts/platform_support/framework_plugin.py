"""License placement shared by Flutter and React Native local plugins."""

from __future__ import annotations

import argparse
from pathlib import Path

from meishe_docking_core import LICENSE_HELP, Report, TargetPlatforms, copy_file, is_within, rel


def plugin_license_destinations(
    plugin: Path,
    targets: TargetPlatforms,
    source_plugin: Path | None = None,
) -> list[Path]:
    probe = plugin if plugin.exists() else source_plugin
    destinations: list[Path] = []
    if targets.android and (probe is None or (probe / "android").exists()):
        destinations.append(plugin / "android" / "src" / "main" / "assets" / "meishesdk.lic")
    if targets.ios and probe is not None and (probe / "ios").exists():
        destinations.append(plugin / "ios" / "Assets" / "meishesdk.lic")
    return destinations

def place_plugin_license(
    plugin: Path,
    args: argparse.Namespace,
    target_root: Path,
    report: Report,
    targets: TargetPlatforms,
    source_plugin: Path | None = None,
) -> None:
    destinations = plugin_license_destinations(plugin, targets, source_plugin)
    if args.license_path and not is_within(plugin, target_root):
        report.add_next_check(
            f"License was not copied because the local plugin package is outside the target project: `{plugin}`. "
            f"Copy `{args.license_path}` to the plugin asset location yourself, move/copy the plugin under the target project, or re-run with an approved writable plugin path."
        )
        return
    if args.license_path:
        src = Path(args.license_path)
        report.add_input(f"License: `{src}`")
        if not destinations:
            report.add_warning(
                "License was not copied because the selected framework package has no asset directory for the target platform."
            )
            return
        for dst in destinations:
            copy_file(src, dst, target_root, report, "Copied Meishe license")
        return
    retained = [dst for dst in destinations if dst.exists()]
    if retained:
        for dst in retained:
            report.add_input(f"Existing license retained: `{dst}`")
            report.add_change(f"Retained existing Meishe license: `{rel(dst, target_root)}`")
        return
    report.add_warning(LICENSE_HELP)
    report.add_user_configuration(
        "Production license: register the final package name/Bundle Identifier with Meishe, obtain the matching real `meishesdk.lic`, then re-run with `--license-path`. The no-license first-run path includes a watermark."
    )
